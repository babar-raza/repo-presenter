"""Hosted acceptance writer: turns one audited seed run into the per-candidate acceptance records
the counter reads (docs/DELIVERY_PLAN_2026-11-07.md section 5.3, "Attestation").

Run only by ``.github/workflows/acceptance-write.yml`` on ``main`` (environment:
acceptance-audit): it decrypts the seed manifest, reads the COMMITTED, FROZEN auditor findings,
applies the audit gates, and writes ONE file, ``acceptance-records-<seed_run_id>.json``. The
workflow then attests that file; ``ops/checks/portfolio_delivery_count.py`` counts a record only
when ``gh attestation verify`` ties the file to this exact workflow on ``main``.

Fail closed: a missing key, an empty seeded or clean population, a gate below threshold or an
unreadable finding sets ``audit_passed`` false for EVERY record and the file still records why.
Only a CLEAN CONTROL (the real sealed candidate, unmodified) can ever pass; a seeded copy is
audit material, never a candidate. ``--dry-run`` takes a plaintext manifest, never reads a key,
and marks the document ``dry_run`` so the counter ignores it.

Deterministic adjudication of flags (docs/DECISION_LOG.md 2026-11-12; BL-013): after the findings are
frozen, every flag is checked by ``deterministic_adjudications`` -- no model, nothing of the auditor's:
CONFIRMED when the repository's claim detector (``readme.validation.claims.claim_findings``) proves the
flagged line contradicts the pinned facts; REFUTED when the flagged line of an UNMODIFIED, re-certifying
seal is a deterministic derivation from the pinned facts (a Lane R line the renderer printed, not an
author; a Lane L line an evidenced zero-call correction wrote) and the claim detector finds nothing there.
Anything else stays unadjudicated (fail closed). A committed adjudication file can add to it; a CONFIRMED
verdict is never overturned by a later REFUTED one.

The false-flag population is the clean controls that can become accepted records: a control whose seal
does not re-certify under current code at the audited revision is already known not to be a clean
candidate by an independent deterministic check decided without the findings (R33), so it is reported
(``controls_not_recertified``) and left out of the false-flag rate, never counted for or against the
auditor; it can never be accepted either way.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Collection, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.audit.score import (  # noqa: E402
    FLAGGED_VERDICTS,
    ScoringError,
    false_flag_rate,
    seeded_recall,
)
from repo_presenter.acceptance.audit.seed import (  # noqa: E402
    CLEAN_SHAPE,
    decrypt_seed_manifest,
    key_manifest_by_case_id,
)

SCHEMA = "acceptance-records/1"
SEEDED_RECALL_MIN = 0.90
FALSE_FLAG_RATE_MAX = 0.10
VERDICTS = frozenset({"supported", "false", "unverifiable"})

#: (repository, lane) -> (revision, certified): what ``repo_presenter.recertify`` says about the
#: latest seal under current code. Injected so tests and the dry run never touch the network.
Recertified = Mapping[tuple[str, str], tuple[str, bool]]


def recertified_from_remote(remote: str = "origin") -> Recertified:
    from repo_presenter.recertify import portfolio_recertification

    results, _history = portfolio_recertification(
        remote=remote, registry=REPO_ROOT / "data" / "registry.json", prompts_dir=REPO_ROOT / "prompts"
    )
    return {(r.repository, r.lane): (r.revision, bool(r.certified)) for r in results}


def evidence_validity(findings: Sequence[Mapping[str, Any]]) -> tuple[bool, str]:
    """Structural validity only: every finding names a path, a positive line and a known verdict.
    That a cited line really holds the claim needs the pinned source clone and is NOT checked
    here, so the document records ``citations_checked: structural``."""
    for index, item in enumerate(findings):
        if item.get("verdict") not in VERDICTS:
            return False, f"finding {index} has verdict {item.get('verdict')!r}"
        if not str(item.get("path") or "").strip():
            return False, f"finding {index} cites no path"
        line = item.get("line")
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            return False, f"finding {index} cites line {line!r}"
        if not str(item.get("candidate_id") or "").strip():
            return False, f"finding {index} names no candidate"
    return True, ""


def _adjudication_index(adjudications: Sequence[Mapping[str, Any]]) -> dict[tuple[str, int], str]:
    """(case_id, line) -> 'confirmed' | 'refuted' for flags raised on clean controls. An
    adjudication is a second, independent check of the flag against the pinned source: a CONFIRMED
    flag is a real defect in the candidate (the candidate fails, the auditor was right); a REFUTED
    flag is an auditor false flag. Anything else is ignored, so an unadjudicated flag keeps
    counting against the auditor (fail closed). CONFIRMED wins over REFUTED for the same line."""
    index: dict[tuple[str, int], str] = {}
    for item in adjudications:
        verdict = item.get("adjudication")
        line = item.get("line")
        if verdict in ("confirmed", "refuted") and isinstance(line, int) and not isinstance(line, bool):
            key = (str(item.get("candidate_id")), line)
            if index.get(key) != "confirmed":
                index[key] = verdict
    return index


# --- deterministic adjudication (see the module docstring) -------------------------------------------


class CaseEvidence(NamedTuple):
    """What the deterministic adjudicator knows about one audited seal, none of it from the auditor:
    its lane, the facts it was sealed with, its sealed README, the lines of that README that are
    deterministic derivations from those facts, and whether it re-certifies at the audited revision."""

    lane: str
    facts: Any
    sealed: str
    derived: frozenset[int]
    certified: bool


def contradicted_lines(text: str, facts: Any) -> frozenset[int]:
    """The 1-based lines of ``text`` the claim detector proves contradict ``facts``."""
    from repo_presenter.readme.validation.claims import claim_findings

    lines: set[int] = set()
    for finding in claim_findings(text, facts):
        last = finding.last if finding.last is not None else finding.line
        lines.update(range(finding.line + 1, last + 2))
    return frozenset(lines)


def derived_lines(lane: str, sealed: str, facts: Any, bundle: Path | None = None, original: str = "") -> frozenset[int]:
    """The lines of ``sealed`` that are deterministic derivations from ``facts``.

    Lane R: every non-blank line the renderer printed rather than an author (``scope.line_sections``
    with the authored table rows, the production Lane R review's own split). Lane L: the lines the
    correction changed, when ``corrections.json`` records a deterministic, zero-call run whose every
    edit cites evidence that is all SUPPORTED; otherwise none."""
    from repo_presenter.readme.review.llm_review import lane_l_changed_lines
    from repo_presenter.readme.review.scope import authored_table_lines, line_sections

    rows = sealed.splitlines()
    if lane == "R":
        sections = line_sections(sealed, True, authored_table_lines(sealed, facts))
        return frozenset(n for n, (row, section) in enumerate(zip(rows, sections), 1)
                         if row.strip() and section is None)
    if bundle is None or not (bundle / "corrections.json").is_file() or not original:
        return frozenset()
    record = json.loads((bundle / "corrections.json").read_text(encoding="utf-8"))
    stability = record.get("stability") or {}
    edits = record.get("edits") or []
    evidenced = all(
        isinstance(edit, Mapping) and edit.get("evidence")
        and all(isinstance(e, Mapping) and e.get("status") == "SUPPORTED" for e in edit["evidence"])
        for edit in edits
    )
    if not edits or not evidenced or stability.get("deterministic") is not True or stability.get("provider_calls") != 0:
        return frozenset()
    return lane_l_changed_lines(sealed, original)


def deterministic_adjudications(
    findings: Sequence[Mapping[str, Any]],
    texts: Mapping[str, str],
    evidence: Mapping[str, CaseEvidence],
    contradicted_by: Callable[[str, Any], frozenset[int]] = contradicted_lines,
) -> list[dict[str, Any]]:
    """One adjudication per flagged (case, line) the deterministic checks decide (module docstring)."""
    out: list[dict[str, Any]] = []
    done: set[tuple[str, int]] = set()
    contradicted: dict[str, frozenset[int]] = {}
    for item in findings:
        case_id, line = str(item.get("candidate_id")), item.get("line")
        if item.get("verdict") not in FLAGGED_VERDICTS or not isinstance(line, int) or (case_id, line) in done:
            continue
        case, text = evidence.get(case_id), texts.get(case_id)
        if case is None or text is None:
            continue
        done.add((case_id, line))
        if case_id not in contradicted:
            contradicted[case_id] = contradicted_by(text, case.facts)
        if line in contradicted[case_id]:
            out.append({"candidate_id": case_id, "line": line, "adjudication": "confirmed",
                        "rule": "claim_detector", "evidence": "the claim detector proves this line contradicts the pinned facts"})
        elif case.certified and text == case.sealed and line in case.derived:
            out.append({"candidate_id": case_id, "line": line, "adjudication": "refuted",
                        "rule": "derived_from_pinned_facts",
                        "evidence": f"unmodified re-certifying Lane {case.lane} seal; the line is a deterministic "
                                    "derivation from the pinned facts and the claim detector finds no contradiction"})
    return out


def case_evidence(
    case_index: Sequence[Mapping[str, Any]],
    history: Mapping[tuple[str, str], Sequence[Any]],
    recertified: Recertified,
) -> dict[str, CaseEvidence]:
    """``CaseEvidence`` for every case whose audited seal is readable in ``history``."""
    from repo_presenter.core.facts import read_facts

    found: dict[str, CaseEvidence] = {}
    for entry in case_index:
        repository, lane, revision = str(entry["repository"]), str(entry["lane"]), str(entry["revision"])
        seal = next((s for s in reversed(list(history.get((repository, lane), ())))
                     if s.revision == revision and getattr(s, "bundle", None) is not None and not s.error), None)
        if seal is None:
            continue
        bundle = Path(seal.bundle)
        try:
            facts = read_facts(bundle / "facts.json")
            sealed = (bundle / "README.md").read_text(encoding="utf-8")
            original_path = bundle / "README.original.md"
            original = original_path.read_text(encoding="utf-8") if original_path.is_file() else ""
        except (OSError, ValueError):
            continue
        seal_revision, certified = recertified.get((repository, lane), ("", False))
        found[str(entry["case_id"])] = CaseEvidence(
            lane=lane, facts=facts, sealed=sealed,
            derived=derived_lines(lane, sealed, facts, bundle, original),
            certified=bool(certified) and seal_revision == revision,
        )
    return found


def evaluate_gates(
    manifest: Sequence[Mapping[str, Any]],
    findings: Sequence[Mapping[str, Any]],
    adjudications: Sequence[Mapping[str, Any]] = (),
    not_recertified: Collection[str] = (),
) -> tuple[dict[str, Any], list[str]]:
    """(gate numbers, reasons the audit fails). An empty reason list means every gate holds."""
    reasons: list[str] = []
    gates: dict[str, Any] = {
        "seeded_recall": None, "false_flag_rate": None,
        "thresholds": {"seeded_recall_min": SEEDED_RECALL_MIN, "false_flag_rate_max": FALSE_FLAG_RATE_MAX},
        "citations_checked": "structural",
    }
    valid, why = evidence_validity(findings)
    gates["evidence_validity"] = valid
    if not valid:
        reasons.append(f"evidence validity: {why}")
    excluded = set(not_recertified)
    clean_ids = [str(m["candidate_id"]) for m in manifest
                 if m.get("shape") == CLEAN_SHAPE and str(m["candidate_id"]) not in excluded]
    gates["controls_not_recertified"] = sorted(
        str(m["candidate_id"]) for m in manifest if m.get("shape") == CLEAN_SHAPE and str(m["candidate_id"]) in excluded
    )
    try:
        recall = seeded_recall(findings, manifest)
        gates["seeded_recall"] = {"matched": recall.matched, "total": recall.total, "rate": recall.rate}
        if recall.rate < SEEDED_RECALL_MIN:
            reasons.append(f"seeded recall {recall.rate:.3f} < {SEEDED_RECALL_MIN}")
    except (ScoringError, KeyError) as error:
        reasons.append(f"seeded recall undefined: {error}")
    try:
        adjudicated = _adjudication_index(adjudications)
        # A flag an independent check CONFIRMED is a true finding, not an auditor false flag.
        counted = [
            f for f in findings
            if adjudicated.get((str(f.get("candidate_id")), f.get("line"))) != "confirmed"
        ]
        flag = false_flag_rate(counted, clean_ids)
        gates["false_flag_rate"] = {"matched": flag.matched, "total": flag.total, "rate": flag.rate}
        if flag.rate > FALSE_FLAG_RATE_MAX:
            reasons.append(f"false-flag rate {flag.rate:.3f} > {FALSE_FLAG_RATE_MAX}")
    except ScoringError as error:
        reasons.append(f"false-flag rate undefined: {error}")
    return gates, reasons


def build_records_document(
    seed_run_id: str,
    case_index: Sequence[Mapping[str, Any]],
    manifest: Sequence[Mapping[str, Any]],
    findings: Sequence[Mapping[str, Any]],
    recertified: Recertified,
    *,
    dry_run: bool = False,
    adjudications: Sequence[Mapping[str, Any]] = (),
    verbatim_baseline: Callable[[str, int], bool] | None = None,
) -> dict[str, Any]:
    shapes = {str(m.get("candidate_id")): m.get("shape") for m in manifest}
    not_recertified = []
    for entry in case_index:
        seal_revision, certified = recertified.get((str(entry["repository"]), str(entry["lane"])), ("", False))
        if shapes.get(str(entry["case_id"])) == CLEAN_SHAPE and not (certified and seal_revision == str(entry["revision"])):
            not_recertified.append(str(entry["case_id"]))
    gates, reasons = evaluate_gates(manifest, findings, adjudications, not_recertified)
    adjudicated = _adjudication_index(adjudications)
    lanes = {str(e["case_id"]): str(e["lane"]) for e in case_index}
    # R21/R20: a CONFIRMED defect on a Lane L line that is verbatim maintainer text in the baseline
    # README is a recorded residual (the candidate did not introduce it), not a blocker.
    residuals: dict[str, list[int]] = {}

    def _residual(case_id: str, line: Any) -> bool:
        if (
            verbatim_baseline is not None and lanes.get(case_id) == "L"
            and adjudicated.get((case_id, line)) == "confirmed" and isinstance(line, int)
            and verbatim_baseline(case_id, line)
        ):
            residuals.setdefault(case_id, []).append(line)
            return True
        return False

    # a candidate is blocked by any flag that was not REFUTED by the independent check, or that is
    # a Lane L residual
    flagged = {
        str(f.get("candidate_id")) for f in findings
        if f.get("verdict") in FLAGGED_VERDICTS
        and adjudicated.get((str(f.get("candidate_id")), f.get("line"))) != "refuted"
        and not _residual(str(f.get("candidate_id")), f.get("line"))
    }
    batch_passed = not reasons
    records: list[dict[str, Any]] = []
    for entry in case_index:
        case_id = str(entry["case_id"])
        repository, lane, revision = str(entry["repository"]), str(entry["lane"]), str(entry["revision"])
        clean = shapes.get(case_id) == CLEAN_SHAPE
        seal_revision, certified = recertified.get((repository, lane), ("", False))
        validated = bool(certified) and seal_revision == revision
        records.append({
            "case_id": case_id, "repository": repository, "lane": lane, "revision": revision,
            "role": "clean_control" if clean else "seeded",
            "deterministically_validated": validated,
            "mechanism_verdicts": {"recertify": validated},
            "canaries": {},
            "audit_passed": bool(batch_passed and clean and case_id not in flagged),
            **({"residual_lines": sorted(set(residuals[case_id]))} if case_id in residuals else {}),
        })
    # Post-audit diagnostics: this document is written only AFTER the findings are frozen, so
    # naming what was missed cannot leak into the audit it describes.
    caught = {(str(f.get("candidate_id")), f.get("line")) for f in findings if f.get("verdict") in FLAGGED_VERDICTS}
    missed = [
        {"case_id": str(m["candidate_id"]), "shape": m.get("shape"), "operator": m.get("operator"), "line": m.get("line")}
        for m in manifest
        if m.get("shape") != CLEAN_SHAPE and (str(m["candidate_id"]), m.get("line")) not in caught
    ]
    return {
        "schema": SCHEMA, "seed_run_id": str(seed_run_id), "dry_run": dry_run,
        "gates": gates, "batch_passed": batch_passed, "failed_reasons": reasons,
        "missed_seeded": missed,
        "adjudications": [dict(a) for a in adjudications],
        "records": records,
    }


def baseline_checker(case_index: Sequence[Mapping[str, Any]], candidates_dir: Path) -> Callable[[str, int], bool]:
    """(case_id, 1-based line) -> True when that candidate line, stripped, is a non-empty line of the
    upstream README at the audited revision (fetched once per case; unreachable means False, so a
    missing baseline never turns a blocker into a residual)."""
    import urllib.request

    by_case = {str(e["case_id"]): e for e in case_index}
    cache: dict[str, tuple[list[str], set[str]] | None] = {}

    def load(case_id: str) -> tuple[list[str], set[str]] | None:
        if case_id not in cache:
            entry = by_case[case_id]
            try:
                cand = (candidates_dir / f"{case_id}.md").read_text(encoding="utf-8").splitlines()
                request = urllib.request.Request(
                    f"https://api.github.com/repos/{entry['repository']}/readme?ref={entry['revision']}",
                    headers={"Accept": "application/vnd.github.raw", "User-Agent": "acceptance-writer"}
                    | ({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    base = {ln.strip() for ln in response.read().decode("utf-8").splitlines() if ln.strip()}
                cache[case_id] = (cand, base)
            except Exception:  # noqa: BLE001 -- unverifiable is not verbatim
                cache[case_id] = None
        return cache[case_id]

    def verbatim(case_id: str, line: int) -> bool:
        loaded = load(case_id)
        if loaded is None or not 1 <= line <= len(loaded[0]):
            return False
        text = loaded[0][line - 1].strip()
        return bool(text) and text in loaded[1]

    return verbatim


def recertified_with_history(remote: str, scratch: Path) -> tuple[Recertified, dict[tuple[str, str], list[Any]]]:
    """``recertified_from_remote`` plus the seal history it read, kept readable under ``scratch``."""
    from repo_presenter.recertify import portfolio_recertification

    results, history = portfolio_recertification(
        remote=remote, registry=REPO_ROOT / "data" / "registry.json", prompts_dir=REPO_ROOT / "prompts",
        scratch=scratch,
    )
    return {(r.repository, r.lane): (r.revision, bool(r.certified)) for r in results}, history


def read_texts(case_index: Sequence[Mapping[str, Any]], candidates_dir: Path) -> dict[str, str]:
    """The audited case texts, as the auditor read them."""
    texts = {}
    for entry in case_index:
        path = candidates_dir / f"{entry['case_id']}.md"
        if path.is_file():
            texts[str(entry["case_id"])] = path.read_text(encoding="utf-8")
    return texts


def main(
    argv: Sequence[str] | None = None,
    *,
    recertify: Callable[[], Recertified] | None = None,
    evidence: Callable[[Sequence[Mapping[str, Any]], Recertified], Mapping[str, CaseEvidence]] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed-run-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True, help="seed_manifest.enc (plain JSON with --dry-run)")
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--case-index", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path, default=None,
                        help="frozen JSON list of independent adjudications of flags on clean controls")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)

    if args.dry_run:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    else:
        key_hex = os.environ.get("AUDIT_SEED_KEY")
        if not key_hex:
            print("FAIL: AUDIT_SEED_KEY is not set", file=sys.stderr)
            return 1
        manifest = decrypt_seed_manifest(args.manifest.read_bytes(), bytes.fromhex(key_hex))
    manifest = key_manifest_by_case_id(manifest)
    findings = json.loads(args.findings.read_text(encoding="utf-8"))
    case_index = json.loads(args.case_index.read_text(encoding="utf-8"))
    adjudications = json.loads(args.adjudications.read_text(encoding="utf-8")) if args.adjudications else []
    import tempfile

    with tempfile.TemporaryDirectory(prefix="acceptance-writer-") as work:
        history: dict[tuple[str, str], list[Any]] = {}
        if recertify is not None:
            recertified = recertify()
        else:
            recertified, history = recertified_with_history(args.remote, Path(work))
        cases = (evidence or (lambda index, recert: case_evidence(index, history, recert)))(case_index, recertified)
        derived = deterministic_adjudications(
            findings, read_texts(case_index, args.case_index.parent / "candidates"), cases
        )
    print(f"deterministic adjudication: {sum(a['adjudication'] == 'confirmed' for a in derived)} confirmed, "
          f"{sum(a['adjudication'] == 'refuted' for a in derived)} refuted")
    adjudications = [*adjudications, *derived]
    document = build_records_document(
        args.seed_run_id, case_index, manifest, findings, recertified, dry_run=args.dry_run,
        adjudications=adjudications,
        verbatim_baseline=None if args.dry_run else baseline_checker(case_index, args.case_index.parent / "candidates"),
    )
    args.out.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    passed = sum(1 for r in document["records"] if r["audit_passed"])
    print(f"batch_passed={document['batch_passed']} audit_passed={passed}/{len(document['records'])}")
    for reason in document["failed_reasons"]:
        print(f"  - {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
