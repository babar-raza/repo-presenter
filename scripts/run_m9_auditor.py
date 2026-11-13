"""M9 hosted blind auditor and frozen-findings resolver (owner, 2026-11-13, R37: the M9 round runs itself
on GitHub Actions; earlier rounds' auditors were supervisor subagents).

``audit`` reviews every case of one seed batch with the EXISTING independent reviewer
(``readme.review.llm_review.review_with_model``: job ``independent_review``, ``prompts/independent_review.yaml``,
its configured route, its contract, ledger, call store and the R25/R31 budget gate inside ``run_job``)
plus its deterministic claim-contradiction rule, and writes the findings in exactly the shape
``run_m9_scorer.py`` and ``run_acceptance_writer.py`` read::

    [{"candidate_id": <case_id>, "claim": ..., "verdict": "supported|false|unverifiable",
      "path": "<case_id>.md", "line": <1-based line of the case text>, "evidence": ...}, ...]

Blindness: its only inputs are the public ``case_index.json``, the case texts (``candidates/<case_id>.md``)
and each case's own seal (``bundle_store.seal_history``: the facts, plan and dispositions it was sealed
with, and the live README it was made from -- the same pinned evidence the reviewer always uses). It never
takes the encrypted manifest or the key; the workflow job that runs it has no ``acceptance-audit``
environment and downloads only the candidates artifact. Each case is reviewed as a whole document
(``rendered=False``, no Lane L edit scope), so nothing tells the reviewer which lines differ from the seal.

Verdict mapping: a finding the reviewer's own clearances proved false is ``supported``; a BLOCKING
``contradiction``/``name_denial`` is ``false`` (class A/D9: a checkable claim the facts contradict); any
other BLOCKING finding is ``unverifiable`` (class D: not grounded). A finding's line is the case line that
holds the first line of its quote (the reviewer derives the quote from the lines it cites); a finding with
no locatable line is written at line ``len(lines) + 1``, past the end of the text: it still flags its
candidate (fail closed for a clean control) and can never match a seeded line by accident.

Fail closed: a case whose review stays unavailable after one retry, a budget refusal or a missing seal ends
the run with exit 1 and NO findings file, so nothing incomplete is ever frozen; the workflow's bounded
attempts (``run_m9_seeder.MAX_AUDIT_ATTEMPTS``) decide what happens next.

Adjudication of flags on clean controls (docs/DECISION_LOG.md 2026-11-12) is NOT done here: a second pass
of the same model, prompt and evidence is not an independent check, so hosted rounds leave every flag
unadjudicated, which ``run_acceptance_writer.py`` counts against both the candidate and the auditor (fail
closed). Independent adjudications enter only as a committed file on main through the run-request
``acceptance-write`` override.

``resolve`` copies a FROZEN findings file out of git for the scorer and the writer: from main (the
checkout), or from the hosted auditor's bot branch ``audit-findings/run-<seed_run_id>``, which must hold
exactly one commit, made by github-actions[bot], on top of a commit of main, adding only
``evidence/build/GATE5_DELIVERY_PROGRAM/M9_AUDIT/findings-<seed_run_id>.json``.

    python scripts/run_m9_auditor.py audit --case-index DIR/case_index.json --candidates DIR/candidates \\
        --out findings.json [--max-calls 600]
    python scripts/run_m9_auditor.py resolve --seed-run-id ID --findings-path PATH [--findings-ref REF] --out FILE
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_rr_spec = importlib.util.spec_from_file_location("run_request", REPO_ROOT / "scripts" / "run_request.py")
run_request = importlib.util.module_from_spec(_rr_spec)
_rr_spec.loader.exec_module(run_request)

FALSE_KINDS = frozenset({"contradiction", "name_denial"})
DEFAULT_MAX_CALLS = 600


class AuditError(RuntimeError):
    """The audit cannot produce a complete, honest findings file."""


# --- findings: one reviewer verdict -> M9 finding rows ------------------------------------------------


def locate(quote: str, rows: Sequence[str]) -> int | None:
    """The 1-based line of ``rows`` holding the first non-blank line of ``quote`` (exact, then contained)."""
    first = next((ln.strip() for ln in (quote or "").splitlines() if ln.strip()), "")
    if not first:
        return None
    for index, row in enumerate(rows):
        if row.strip() == first:
            return index + 1
    for index, row in enumerate(rows):
        if first in row:
            return index + 1
    return None


def findings_for(case_id: str, text: str, findings: Sequence[Any]) -> list[dict[str, Any]]:
    """The M9 rows for one case from the reviewer's final ``Finding`` objects (see module docstring)."""
    rows = text.splitlines()
    past_end = len(rows) + 1
    out: list[dict[str, Any]] = []
    for finding in findings:
        if finding.status == "CLEARED":
            verdict = "supported"
        elif finding.claim_kind in FALSE_KINDS:
            verdict = "false"
        else:
            verdict = "unverifiable"
        line = locate(finding.quote, rows)
        out.append({
            "candidate_id": case_id,
            "claim": f"[{finding.claim_kind}] {finding.message}".strip()[:2000],
            "verdict": verdict,
            "path": f"{case_id}.md",
            "line": line if line is not None else past_end,
            "evidence": (finding.evidence or finding.rule or finding.source)[:500],
            "located": line is not None,
        })
    return out


# --- sources: each case's own seal, as the reviewer's evidence -----------------------------------------


def seal_for(history: Mapping[tuple[str, str], Sequence[Any]], repository: str, lane: str, revision: str) -> Any:
    """The latest materialized seal of ``(repository, lane)`` at ``revision`` (the seeder takes the latest)."""
    for seal in reversed(list(history.get((repository, lane), ()))):
        if seal.revision == revision and seal.bundle is not None and not seal.error:
            return seal
    raise AuditError(f"no readable seal of {repository} lane {lane} at {revision}")


def source_for(seal: Any, case_id: str) -> Any:
    """The reviewer's ``SourceCandidate`` for one seal, judged as a whole document (``rendered=False``)."""
    from repo_presenter.core.facts import read_facts
    from repo_presenter.core.registry.loader import load_registry, require_listed
    from repo_presenter.readme.bundle.recheck import original_readme
    from repo_presenter.readme.review.calibration.sources import (
        build_source,
        load_lane_l_bundle_candidate,
    )

    bundle = Path(seal.bundle)
    if seal.lane == "L":
        return load_lane_l_bundle_candidate(bundle, name=case_id)

    def read(name: str) -> dict[str, Any]:
        path = bundle / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    facts = read_facts(bundle / "facts.json")
    entry = require_listed(load_registry(REPO_ROOT / "data" / "registry.json"), seal.repository)
    sealed = (bundle / "README.md").read_text(encoding="utf-8", newline="")
    patch_path = bundle / "README.patch.diff"
    original = original_readme(sealed, patch_path.read_text(encoding="utf-8", newline="")) if patch_path.is_file() else None
    if original is None:
        from repo_presenter.recertify import fetch_source

        with tempfile.TemporaryDirectory(prefix="m9-audit-src-") as work:
            snapshot = fetch_source(seal.repository, seal.revision, Path(work))
        if snapshot.readme is None:
            raise AuditError(f"the live README of {seal.repository}@{seal.revision} cannot be read")
        original = snapshot.readme.decode("utf-8", errors="replace")
    units_name = "content_units.coherent.json" if (bundle / "content_units.coherent.json").is_file() else "content_units.json"
    source = build_source(
        name=case_id, entry=entry, facts=facts, plan=read("plan.json"), units=read(units_name),
        dispositions=read("dispositions.json"), investigation=read("investigation.json"),
        original=original, tree_paths=[], scratch=bundle, recorded_readme=sealed,
    )
    return dataclasses.replace(source, rendered=False)


# --- the audit -------------------------------------------------------------------------------------------

#: (source, case text) -> the reviewer's ReviewVerdict; raises ReviewUnavailable when no valid review exists.
Reviewer = Callable[[Any, str], Any]


def audit_cases(
    case_index: Sequence[Mapping[str, Any]],
    texts: Mapping[str, str],
    sources: Callable[[Mapping[str, Any]], Any],
    review: Reviewer,
    *,
    retries: int = 1,
) -> list[dict[str, Any]]:
    """Every case reviewed, in case-index order; ``AuditError`` when any case has no valid review after
    ``retries`` more attempts (a partial findings file is never returned)."""
    from repo_presenter.readme.review.verdict import ReviewUnavailable

    findings: list[dict[str, Any]] = []
    for entry in case_index:
        case_id = str(entry["case_id"])
        if case_id not in texts:
            raise AuditError(f"case {case_id} has no candidate text")
        source = sources(entry)
        verdict, problem = None, None
        for _attempt in range(retries + 1):
            try:
                verdict = review(source, texts[case_id])
                break
            except ReviewUnavailable as error:
                problem = error
        if verdict is None:
            raise AuditError(f"case {case_id}: no valid review ({getattr(problem, 'reason', problem)})")
        rows = findings_for(case_id, texts[case_id], verdict.findings)
        findings.extend(rows)
        print(f"{case_id} {entry.get('lane')} {verdict.verdict}: {len(rows)} findings", file=sys.stderr)
    return findings


def live_reviewer(ledger_path: Path, store_dir: Path, max_calls: int) -> Reviewer:
    """The existing reviewer as the gateway runs it (GPT_OSS_ENDPOINT/GPT_OSS_API_KEY from the environment,
    never printed), every attempt a ledger record, the program budget checked by ``run_job``."""
    from repo_presenter.core.config import load_gateway_config
    from repo_presenter.core.llm.jobs import CallStore, JobContext
    from repo_presenter.core.llm.ledger import Ledger
    from repo_presenter.core.llm.prompts import load_manifests
    from repo_presenter.readme.review.independent_reviewer import claim_contradiction_rule
    from repo_presenter.readme.review.llm_review import review_with_model

    prompts = load_manifests(REPO_ROOT / "prompts")
    config = load_gateway_config(os.environ)
    ledger = Ledger(ledger_path, call_budget=max_calls)
    store = CallStore(store_dir)

    def review(source: Any, text: str) -> Any:
        return review_with_model(
            prompts=prompts, config=config, ledger=ledger, store=store,
            context=JobContext(repository=source.repository, source_revision=source.facts.source_revision),
            candidate_readme=text, original_readme=source.original, facts=source.facts,
            plan=source.plan, dispositions=source.dispositions, validation=source.validation,
            deterministic_findings=tuple(claim_contradiction_rule(text, source.facts)),
            rendered=False,
        )

    return review


def cmd_audit(args: argparse.Namespace) -> int:
    from repo_presenter.core.state.bundle_store import seal_history

    case_index = json.loads(args.case_index.read_text(encoding="utf-8"))
    texts = {
        str(e["case_id"]): (args.candidates / f"{e['case_id']}.md").read_text(encoding="utf-8")
        for e in case_index if (args.candidates / f"{e['case_id']}.md").is_file()
    }
    work = args.work or Path(tempfile.mkdtemp(prefix="m9-audit-"))
    history = seal_history(remote=args.remote, scratch=work / "seals")
    review = live_reviewer(work / "ledger.jsonl", work / "calls", args.max_calls)

    def sources(entry: Mapping[str, Any]) -> Any:
        seal = seal_for(history, str(entry["repository"]), str(entry["lane"]), str(entry["revision"]))
        return source_for(seal, str(entry["case_id"]))

    try:
        findings = audit_cases(case_index, texts, sources, review)
    except AuditError as error:
        print(f"FAIL: {error}; no findings written", file=sys.stderr)
        return 1
    valid, why = evidence_validity(findings)
    if not valid:
        print(f"FAIL: findings are not structurally valid ({why}); none written", file=sys.stderr)
        return 1
    args.out.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    flagged = sum(1 for f in findings if f["verdict"] != "supported")
    print(f"audited {len(case_index)} cases: {len(findings)} findings, {flagged} flagged -> {args.out}")
    return 0


def evidence_validity(findings: Sequence[Mapping[str, Any]]) -> tuple[bool, str]:
    """The acceptance writer's own structural check (imported, never re-implemented)."""
    spec = importlib.util.spec_from_file_location("run_acceptance_writer", REPO_ROOT / "scripts" / "run_acceptance_writer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evidence_validity(findings)


# --- resolve: the frozen findings file, from main or from the hosted auditor's bot branch ---------------


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True, cwd=cwd).stdout


def resolve_findings(
    seed_run_id: str, findings_path: str, findings_ref: str = "", *, remote: str = "origin",
    base_branch: str = "main", cwd: Path | None = None,
) -> bytes:
    """The bytes of the frozen findings file (see module docstring); ``AuditError`` otherwise."""
    if not run_request.is_run_id(seed_run_id):
        raise AuditError(f"seed run id {seed_run_id!r} is not a run id")
    if findings_path != run_request.findings_path_for(seed_run_id):
        raise AuditError(f"findings path {findings_path!r} is not {run_request.findings_path_for(seed_run_id)!r}")
    try:
        _git("fetch", "--no-tags", "--quiet", remote, f"+refs/heads/{base_branch}:refs/m9/base", cwd=cwd)
        if not findings_ref:
            return subprocess.run(["git", "show", f"refs/m9/base:{findings_path}"], capture_output=True,
                                  check=True, cwd=cwd).stdout
        if findings_ref != run_request.findings_ref_for(seed_run_id):
            raise AuditError(f"findings ref {findings_ref!r} is not {run_request.findings_ref_for(seed_run_id)!r}")
        _git("fetch", "--no-tags", "--quiet", remote, f"+refs/heads/{findings_ref}:refs/m9/findings", cwd=cwd)
        tip = _git("rev-parse", "refs/m9/findings", cwd=cwd).strip()
        parents = _git("rev-list", "--parents", "-n", "1", tip, cwd=cwd).split()[1:]
        if len(parents) != 1:
            raise AuditError(f"{findings_ref} tip {tip} has {len(parents)} parents, not one")
        if subprocess.run(["git", "merge-base", "--is-ancestor", parents[0], "refs/m9/base"],
                          capture_output=True, cwd=cwd).returncode != 0:
            raise AuditError(f"{findings_ref} is not one commit on top of a commit of {base_branch}")
        changed = _git("diff", "--name-only", "--no-renames", parents[0], tip, cwd=cwd).split()
        if changed != [findings_path]:
            raise AuditError(f"{findings_ref} changes {changed}, not only {findings_path}")
        emails = _git("log", "-1", "--format=%ae%n%ce", tip, cwd=cwd).split()
        if emails != [run_request.BOT_EMAIL, run_request.BOT_EMAIL]:
            raise AuditError(f"{findings_ref} tip was not made by github-actions[bot] ({emails})")
        return subprocess.run(["git", "show", f"{tip}:{findings_path}"], capture_output=True, check=True,
                              cwd=cwd).stdout
    except subprocess.CalledProcessError as error:
        raise AuditError(f"git failed: {(error.stderr or '').strip() or error}") from error


def cmd_resolve(args: argparse.Namespace) -> int:
    try:
        blob = resolve_findings(args.seed_run_id, args.findings_path, args.findings_ref, remote=args.remote)
        json.loads(blob)
    except (AuditError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(blob)
    print(f"resolved {args.findings_path} from {args.findings_ref or 'main'} -> {args.out}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--case-index", type=Path, required=True)
    audit.add_argument("--candidates", type=Path, required=True)
    audit.add_argument("--out", type=Path, required=True)
    audit.add_argument("--remote", default="origin")
    audit.add_argument("--work", type=Path, default=None, help="ledger, call store and seal scratch")
    audit.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--seed-run-id", required=True)
    resolve.add_argument("--findings-path", required=True)
    resolve.add_argument("--findings-ref", default="")
    resolve.add_argument("--out", type=Path, required=True)
    resolve.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)
    return cmd_audit(args) if args.command == "audit" else cmd_resolve(args)


if __name__ == "__main__":
    raise SystemExit(main())
