"""Hosted ``present``: one repository, one durable transaction, one cascade, one sealed candidate.

Wires the durable-state backend (``core/state/``) around the present-equivalent cascade
(``cascade.py``): the transaction's recovery, dedup, and lease discipline come from
``core/state/present_transaction.py``; the work itself is one pinned clone, the Lane L facts, the
whole S3-S8 cascade under one invocation, the independent review, and the first seal. The
transaction's committed outcome is derived from what the run actually left on disk, never from a
second guess.

The hosted run is two jobs with a trust boundary between them (``.github/workflows/present.yml``):

    python -m repo_presenter.present --stage facts   --repository <owner>/<repo> --ecosystem <eco>
    python -m repo_presenter.present --stage cascade --repository <owner>/<repo> --ecosystem <eco>
        [--lane R|L]

Two equal lanes (``plans/PLAN_lane_l_hosted.md``). ``--lane R`` (the default) is the full Lane R
cascade S3-S10; ``--lane L`` corrects the live README with minimal evidenced edits and has the final
README independently reviewed (``lane_l_run.py``). They share the facts handoff, the independent
reviewer, the sealer and the durable-state transaction, and each lane is its own transaction (its own
state record, its own candidate pointer, its own seal): a failure in one never touches the other.

``facts`` clones the pinned revision and builds the facts (both lanes read them), which executes untrusted
repository code (example builds); it holds no secrets, needs no state backend and no provider
configuration, and writes only ``facts.json`` plus a manifest (``facts_handoff.py``). ``cascade``
holds the provider key and the state token and executes no repository code: it verifies the facts
artifact, re-clones the SAME pinned revision for README reads, and runs the lane (the Lane R cascade,
or the Lane L correction engine on the validated facts), the review, the seal and the durable
transaction. ``--stage combined`` (the default) runs both in one process for
local and offline use only and is refused when ``GITHUB_ACTIONS`` is set.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from repo_presenter.cascade import (
    DEFAULT_PROMPTS_PATH,
    DEFAULT_REGISTRY_PATH,
    preflight_cascade,
    run_cascade,
)
from repo_presenter.core.candidates import CANDIDATES_DIRNAME, LANE_L, LANE_R, LANES
from repo_presenter.core.config import GatewayConfig, load_gateway_config
from repo_presenter.core.errors import ConfigError, OutputRejectedError, PresenterError
from repo_presenter.core.facts import write_facts
from repo_presenter.core.git_safety.clone import clone_pinned, pinned_read_only_clone
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.core.state.bundle_store import publish_bundle
from repo_presenter.core.version_set import current_fingerprint
from repo_presenter.core.state.cas import StateBackend
from repo_presenter.core.state.git_backend import GitStateBackend
from repo_presenter.core.state.present_transaction import (
    STATE_TOKEN_VARIABLE,
    PresentOutcome,
    classify_present_outcome,
    run_present_transaction,
)
from repo_presenter.facts_handoff import FactsManifest, load_handoff, write_handoff
from repo_presenter.lane_l import build_lane_l_facts
from repo_presenter.lane_l_run import preflight_lane_l, run_lane_l
from repo_presenter.readme.bundle.seal import SealInputs, seal_candidate
from repo_presenter.readme.correction.report import (
    OUTCOME_REFUSED,
    lane_r_recommendation,
)
from repo_presenter.readme.review.llm_review import blocked_predicate, m8_blocking_units
from repo_presenter.readme.review.verdict import ReviewUnavailable
from repo_presenter.readme.validation.blocking import blocking_failures

READ_TOKEN_VARIABLE = "REPOSITORY_PRESENTER_READ_TOKEN"
DEFAULT_WORKDIR = Path(".present-work")
DEFAULT_FACTS_DIR = Path(".present-facts")
STAGES = ("facts", "cascade", "combined")
# Sealed bundles live in the checkout's committed candidates/ tree (or a restored copy of it),
# never in the disposable workdir: a rerun can only prove a no-op against a bundle that outlives
# the run that sealed it.
DEFAULT_CANDIDATES_ROOT = Path(".")


class PresentFailure(PresenterError):
    """The pipeline reached an expected, typed refusal (the independent review rejected the
    candidate, so nothing was sealed). Recorded as a failed transaction with this message."""


def _clone_url(repository: str) -> str:
    return f"https://github.com/{repository}.git"


def facts_pipeline(
    *,
    repository: str,
    ecosystem: str,
    workdir: Path,
    facts_dir: Path,
    registry_path: Path,
) -> FactsManifest:
    """The untrusted-code half: clone the default branch (public, no credential), build the facts
    (this executes the repository's examples), and write the facts artifact."""
    clone = pinned_read_only_clone(
        _clone_url(repository), workdir / "clone", token=None
    )
    document = build_lane_l_facts(
        repository,
        clone.path,
        ecosystem,
        source_revision=clone.revision,
        workspace=workdir / "examples",
        entry=require_listed(load_registry(registry_path), repository),
    )
    return write_handoff(document, ecosystem, facts_dir)



def report_findings(verdict: Any, *, out: Any = None) -> None:
    """Print each blocking finding of a rejected candidate to the job log: hosted run artifacts are
    not always readable afterwards, and a reject that names no quote cannot be judged true or false."""
    stream = out if out is not None else sys.stdout
    for finding in verdict.blocking_findings:
        label = finding.finding_id or finding.rule
        print(
            f"finding {label} [{finding.rule}] section={finding.section_id or '-'}: {finding.message}",
            file=stream,
        )
        if finding.quote:
            print(f"  quote: {finding.quote[:600]!r}", file=stream)
        if finding.evidence:
            print(f"  evidence: {finding.evidence[:600]}", file=stream)


def report_repairs(out_dir: Path, *, out: Any = None) -> None:
    """Print each repair attempt of a blocked candidate (outcome, check, the units it changed and
    to what, the reason it was not repaired): a hosted run's workdir is not readable afterwards,
    and a block that names no attempt cannot be diagnosed (2026-11-06 round 3, Email .NET)."""
    stream = out if out is not None else sys.stdout
    path = out_dir / "repairs.json"
    try:
        attempts = json.loads(path.read_text(encoding="utf-8")).get("attempts", {})
    except (OSError, ValueError, AttributeError):
        return
    for attempt in attempts.values() if isinstance(attempts, dict) else attempts:
        if not isinstance(attempt, dict):
            continue
        changes = [
            str(change.get("after", ""))[:240] for change in attempt.get("changes") or []
        ]
        print(
            f"repair {attempt.get('outcome')} {attempt.get('label')}: "
            f"{'; '.join(changes) or '-'}"
            + (f" | reason: {str(attempt.get('reason'))[:400]}" if attempt.get("reason") else ""),
            file=stream,
        )

def recertify_instead(
    *,
    lane: str,
    repository: str,
    clone_path: Path,
    candidates_root: Path,
    prompts_path: Path,
    registry_path: Path,
) -> bool:
    """Owner rule (2026-11-06): a mechanism-version change alone never regenerates a sealed
    candidate. Re-certify the lane's sealed bundle under current code from its stored outputs --
    re-render, the full blocking validation, the deterministic reviewer rules (Lane R); the
    correction engine and its holdouts (Lane L) -- with ZERO provider calls. True when it
    RECERTIFIED (the re-certified seal replaces the local bundle; ``publish`` pushes it as a NEW
    commit on the bundle ref, so the original seal stays in the ref's history). False on
    NEEDS_REPAIR: the original seal is untouched and the generation pipeline runs."""
    from repo_presenter.lane_l import tree_paths_of
    from repo_presenter.recertify import SourceSnapshot, recertify_local

    readme = clone_path / "README.md"
    source = SourceSnapshot(
        tree_paths=tuple(tree_paths_of(clone_path)),
        readme=readme.read_bytes() if readme.is_file() else None,
    )
    try:
        rec = recertify_local(
            candidates_root=candidates_root,
            entry=require_listed(load_registry(registry_path), repository),
            lane=lane,
            source=source,
            prompts=load_manifests(prompts_path),
            write=True,
        )
    except Exception as exc:  # noqa: BLE001 -- a re-certification that cannot run regenerates
        print(f"recertify (Lane {lane}): not possible ({type(exc).__name__}: {exc}); "
              "running the generation pipeline")
        return False
    print(
        f"recertify (Lane {lane}): {rec.outcome}"
        + (f"; failing: {', '.join(rec.failing_checks)}" if rec.failing_checks else "")
        + ("; README re-rendered" if rec.readme_changed else "")
    )
    for detail in rec.details[:12]:
        print(f"  {detail[:500]}")
    return rec.recertified


def restore_sealed_bundle(
    repository: str, lane: str, candidates_root: Path, *, remote: str, token: str | None
) -> None:
    """A runner whose cache missed has no local bundle; the durable bundle ref still holds the
    latest seal. Export it, so preflight can re-certify it instead of regenerating. Any failure
    leaves things as they were (preflight then sees no bundle and the pipeline runs)."""
    from repo_presenter.core.candidates import CURRENT_FILENAME, lane_directory
    from repo_presenter.core.state.bundle_store import BundleStoreError, export_bundle

    slug_dir = candidates_root / CANDIDATES_DIRNAME / repository.replace("/", "__")
    if (lane_directory(slug_dir, lane) / CURRENT_FILENAME).is_file():
        return
    try:
        export_bundle(repository, lane, candidates_root / CANDIDATES_DIRNAME, remote=remote, token=token)
        print(f"restored the latest seal of lane {lane} from its bundle ref")
    except (BundleStoreError, OSError) as exc:
        print(f"no stored seal restored for lane {lane}: {exc}")


def _cascade_and_seal(
    *,
    repository: str,
    ecosystem: str,
    clone_path: Path,
    facts_path: Path,
    workdir: Path,
    candidates_root: Path,
    config: GatewayConfig,
    prompts_path: Path,
    registry_path: Path,
) -> None:
    decision = preflight_cascade(
        repository, clone_path, facts_path=facts_path, candidates_root=candidates_root,
        prompts_path=prompts_path,
    )
    print(f"preflight (Lane R): skip={decision.can_skip_provider_call}: {decision.reason}")
    if decision.can_skip_provider_call:
        return  # the proven sealed bundle stays exactly as sealed; no provider call is made
    if decision.recertify and recertify_instead(
        lane=LANE_R, repository=repository, clone_path=clone_path,
        candidates_root=candidates_root, prompts_path=prompts_path, registry_path=registry_path,
    ):
        return  # re-certified under current code with zero provider calls
    result = run_cascade(
        repository,
        ecosystem,
        clone_path,
        facts_path=facts_path,
        out_dir=workdir / "cascade",
        config=config,
        prompts_path=prompts_path,
        registry_path=registry_path,
    )
    verdict = result.review_verdict
    if verdict.verdict != "ACCEPT":
        report_findings(verdict)
        report_repairs(result.out_dir)
        raise PresentFailure(
            f"independent review returned {verdict.verdict} with "
            f"{len(verdict.blocking_findings)} blocking finding(s) of {len(verdict.findings)}; "
            f"nothing sealed; {blocked_predicate(verdict)}"
        )
    if not verdict.model_reviewed:
        failed = blocking_failures(result.validation)
        report_repairs(result.out_dir)
        failing = ", ".join(check["id"] for check in failed)
        for check in failed:
            for failure in list(check.get("failures") or [])[:12]:
                print(f"blocking {check['id']}: {str(failure.get('detail', ''))[:500]}")
        raise PresentFailure(
            "no LLM review of this candidate was made, and a deterministic-only "
            "verdict is never sealed"
            + (f"; blocking checks still fail: {failing}" if failing else "")
            + "; nothing sealed"
        )
    m8_blocked = m8_blocking_units(verdict.unit_reviews)
    if m8_blocked:
        # TC-013/TC-024's seal-path contract: a deterministic REJECT or the old reviewer's own
        # REJECT already raised above; this is the same non-negotiable-5 block, now in M8's
        # vocabulary (readme.review.prose_judge, TC-023) for whichever unit(s) it rejected.
        raise PresentFailure(
            "M8 prose judge rejected unit(s): " + ", ".join(m8_blocked) + "; nothing sealed"
        )
    seal_candidate(
        SealInputs(
            entry=result.entry,
            source_revision=result.source_revision,
            facts=result.document,
            prompts=load_manifests(prompts_path),
            out_dir=result.out_dir,
            facts_path=result.facts_path,
            candidates_root=candidates_root,
            provider_calls=result.provider_calls,
            invocation=result.invocation,
        )
    )


def _lane_l_and_seal(
    *,
    repository: str,
    ecosystem: str,
    clone_path: Path,
    facts_path: Path,
    workdir: Path,
    candidates_root: Path,
    config: GatewayConfig,
    prompts_path: Path,
    registry_path: Path,
) -> None:
    """Lane L's counterpart of :func:`_cascade_and_seal`: correct the live README, judge the final
    README, and seal only a candidate a model reviewed and accepted. A defect the engine may not
    repair is a refusal that names Lane R, never a seal."""
    decision = preflight_lane_l(
        repository, clone_path, facts_path=facts_path, candidates_root=candidates_root,
        prompts_path=prompts_path,
    )
    print(f"preflight (Lane L): skip={decision.can_skip_provider_call}: {decision.reason}")
    if decision.can_skip_provider_call:
        return  # the proven sealed bundle stays exactly as sealed; no provider call is made
    if decision.recertify and recertify_instead(
        lane=LANE_L, repository=repository, clone_path=clone_path,
        candidates_root=candidates_root, prompts_path=prompts_path, registry_path=registry_path,
    ):
        return  # re-certified under current code with zero provider calls
    result = run_lane_l(
        repository,
        ecosystem,
        clone_path,
        facts_path=facts_path,
        out_dir=workdir / "lane-l",
        config=config,
        prompts_path=prompts_path,
        registry_path=registry_path,
    )
    verdict = result.review_verdict
    if verdict.verdict != "ACCEPT":
        report_findings(verdict)
        recommendation = (
            f"; {lane_r_recommendation(result.correction)}"
            if result.outcome == OUTCOME_REFUSED
            else ""
        )
        raise PresentFailure(
            f"Lane L: independent review returned {verdict.verdict} with "
            f"{len(verdict.blocking_findings)} blocking finding(s) of {len(verdict.findings)}; "
            f"nothing sealed; {blocked_predicate(verdict)}{recommendation}"
        )
    if not verdict.model_reviewed:
        raise PresentFailure(
            "Lane L: no LLM review of this candidate was made, and a deterministic-only "
            "verdict is never sealed; nothing sealed"
        )
    m8_blocked = m8_blocking_units(verdict.unit_reviews)
    if m8_blocked:
        raise PresentFailure(
            "Lane L: M8 prose judge rejected unit(s): "
            + ", ".join(m8_blocked)
            + "; nothing sealed"
        )
    seal_candidate(
        SealInputs(
            entry=result.entry,
            source_revision=result.source_revision,
            facts=result.document,
            prompts=load_manifests(prompts_path),
            out_dir=result.out_dir,
            facts_path=result.facts_path,
            candidates_root=candidates_root,
            provider_calls=result.provider_calls,
            invocation=result.invocation,
            lane=LANE_L,
        )
    )


def _lane_and_seal(lane: str, **kwargs: Any) -> None:
    """The one place a lane is chosen: everything either lane needs is passed by name."""
    if lane == LANE_L:
        _lane_l_and_seal(**kwargs)
    elif lane == LANE_R:
        _cascade_and_seal(**kwargs)
    else:
        raise ConfigError(f"unknown lane {lane!r}: expected one of {LANES}")


def cascade_pipeline(
    *,
    repository: str,
    ecosystem: str,
    workdir: Path,
    facts_dir: Path,
    candidates_root: Path,
    config: GatewayConfig,
    read_token: str | None,
    prompts_path: Path,
    registry_path: Path,
    expected_facts_sha256: str | None = None,
    lane: str = LANE_R,
) -> None:
    """The credentialed half: runs no repository code and never builds facts. The facts artifact is
    verified and validated first; the clone is re-taken at exactly the revision the artifact records
    (a default branch that has moved fails closed) and is only read."""
    manifest, document = load_handoff(
        facts_dir,
        repository=repository,
        ecosystem=ecosystem,
        expected_sha256=expected_facts_sha256,
    )
    clone = clone_pinned(
        _clone_url(repository),
        manifest.source_revision,
        workdir / "clone",
        token=read_token,
    )
    facts_path = workdir / "facts.json"
    write_facts(document, facts_path)
    _lane_and_seal(
        lane,
        repository=repository,
        ecosystem=ecosystem,
        clone_path=clone.path,
        facts_path=facts_path,
        workdir=workdir,
        candidates_root=candidates_root,
        config=config,
        prompts_path=prompts_path,
        registry_path=registry_path,
    )


def combined_pipeline(
    *,
    repository: str,
    ecosystem: str,
    workdir: Path,
    candidates_root: Path,
    config: GatewayConfig,
    read_token: str | None,
    prompts_path: Path,
    registry_path: Path,
    lane: str = LANE_R,
) -> None:
    """Facts and the lane in one process: local and offline use only, never hosted."""
    clone = pinned_read_only_clone(
        _clone_url(repository), workdir / "clone", token=read_token
    )
    document = build_lane_l_facts(
        repository,
        clone.path,
        ecosystem,
        source_revision=clone.revision,
        workspace=workdir / "examples",
        entry=require_listed(load_registry(registry_path), repository),
    )
    facts_path = workdir / "facts.json"
    write_facts(document, facts_path)
    _lane_and_seal(
        lane,
        repository=repository,
        ecosystem=ecosystem,
        clone_path=clone.path,
        facts_path=facts_path,
        workdir=workdir,
        candidates_root=candidates_root,
        config=config,
        prompts_path=prompts_path,
        registry_path=registry_path,
    )


def run_present(
    *,
    backend: StateBackend,
    entry: RegistryEntry,
    candidates_root: Path,
    holder_id: str,
    workflow_run_id: str | None,
    pipeline: Callable[[], None],
    lane: str = LANE_R,
    publish: Callable[[], None] | None = None,
    version_set: str | None = None,
) -> int:
    """Run ``pipeline`` under the durable transaction for ``entry``; returns the exit code.

    Any typed failure of the pipeline becomes a recorded failed transaction (never a silently
    dropped lease); an untyped exception is a defect and propagates after the lease is released.

    ``publish`` runs once the pipeline has sealed, still inside the transaction: it makes the sealed
    bundle durable (``core/state/bundle_store.py``). A candidate whose bundle could not be stored
    is recorded as a failure, not as ready, because a result that only lives in an expiring cache
    is not a result.

    No demotion (owner version-set rules, ``core/version_set.py``): a failed run is recorded as a
    failed ATTEMPT on the transaction record, naming the ``version_set`` fingerprint it ran under,
    and never publishes -- so the lane's bundle-ref history (every earlier seal, under whatever
    version set it was sealed) is left exactly as it was. The record may still route to
    INVALIDATED for its own state machine; no count reads it.
    """
    failure: dict[str, str] = {}
    attempt = f"attempt under version set {version_set[:12]}: " if version_set else ""

    def run() -> int:
        try:
            pipeline()
        except OutputRejectedError as exc:
            failure["detail"] = (
                "model output was rejected by the job's own checks after its bounded re-asks "
                f"(retryable: a re-run asks the model again): {type(exc).__name__}: {exc}"
            )
            failure["class"] = "transient"
            return 1
        except ReviewUnavailable as exc:
            failure["detail"] = (
                "no valid independent review could be obtained, so nothing was sealed "
                f"(retryable: a re-run asks the reviewer again): {exc.reason}"
                + "".join(f"; {error}" for error in exc.errors[:3])
            )
            failure["class"] = "transient"
            return 1
        except PresenterError as exc:
            failure["detail"] = f"{type(exc).__name__}: {exc}"
            return 1
        if publish is not None:
            try:
                publish()
            except PresenterError as exc:
                failure["detail"] = (
                    "sealed locally; bundle not durably published (a rerun republishes from the "
                    f"restored bundle with zero provider calls): {type(exc).__name__}: {exc}"
                )
                failure["class"] = "transient"
                print(f"::error::{failure['detail']}", file=sys.stderr)
                return 1
        return 0

    def classify(exit_code: int) -> PresentOutcome:
        if exit_code != 0:
            return PresentOutcome(
                kind="failed",
                detail=attempt + failure.get("detail", f"present exited {exit_code}"),
                failure_class="transient"
                if failure.get("class") == "transient"
                else None,
            )
        try:
            return classify_present_outcome(candidates_root, entry, exit_code, lane=lane)
        except PresenterError as exc:
            # A bundle that fails its own integrity check is a recorded failure, never an
            # exception that leaves the durable record describing an earlier run.
            return PresentOutcome(kind="failed", detail=f"{attempt}{type(exc).__name__}: {exc}")

    return run_present_transaction(
        backend=backend,
        repository=entry.repository,
        provider_repository_id=entry.provider_identity.repository_id,
        holder_id=holder_id,
        run=run,
        classify=classify,
        workflow_run_id=workflow_run_id,
        lane=lane,
    )


def _refuse(message: str, exit_code: int) -> int:
    print(f"::error::present refused before any work: {message}", file=sys.stderr)
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo_presenter.present",
        description="Present one listed repository under the durable-state transaction.",
    )
    parser.add_argument("--stage", choices=STAGES, default="combined")
    parser.add_argument(
        "--lane",
        choices=LANES,
        default=LANE_R,
        help="R: the full Lane R cascade (default). L: correct the live README (Lane L).",
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ecosystem", required=True)
    parser.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR)
    parser.add_argument("--facts-dir", type=Path, default=DEFAULT_FACTS_DIR)
    parser.add_argument("--expected-facts-sha256", default=None)
    parser.add_argument("--candidates-root", type=Path, default=DEFAULT_CANDIDATES_ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS_PATH)
    parser.add_argument("--state-remote", default="origin")
    parser.add_argument("--workflow-run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument(
        "--restore-sealed-bundle",
        action="store_true",
        help="when no local bundle exists, export the lane's latest seal from its bundle ref first "
        "(so a mechanism-only change re-certifies it instead of regenerating)",
    )
    args = parser.parse_args(argv)

    if (
        args.stage == "combined"
        and os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    ):
        return _refuse(
            "the combined stage runs repository code beside the provider key and state token and "
            "is not allowed on a hosted runner; use --stage facts and --stage cascade",
            ConfigError.exit_code,
        )

    try:
        entry = require_listed(load_registry(args.registry), args.repository)
        if entry.ecosystem != args.ecosystem:
            raise ConfigError(
                f"{args.repository} is registered as {entry.ecosystem!r}, not {args.ecosystem!r}"
            )
        config = load_gateway_config(os.environ) if args.stage != "facts" else None
    except PresenterError as exc:
        return _refuse(str(exc), exc.exit_code)

    if args.stage == "facts":
        try:
            manifest = facts_pipeline(
                repository=args.repository,
                ecosystem=args.ecosystem,
                workdir=args.workdir,
                facts_dir=args.facts_dir,
                registry_path=args.registry,
            )
        except PresenterError as exc:
            print(
                f"::error::facts stage failed: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            return exc.exit_code
        print(
            f"facts: {manifest.repository}@{manifest.source_revision} "
            f"sha256 {manifest.facts_sha256}"
        )
        return 0

    assert config is not None
    read_token = os.environ.get(READ_TOKEN_VARIABLE) or None
    state_token = os.environ.get(STATE_TOKEN_VARIABLE) or None

    def pipeline() -> None:
        if args.restore_sealed_bundle:
            restore_sealed_bundle(
                args.repository, args.lane, args.candidates_root,
                remote=args.state_remote, token=state_token,
            )
        if args.stage == "combined":
            combined_pipeline(
                repository=args.repository,
                ecosystem=args.ecosystem,
                workdir=args.workdir,
                candidates_root=args.candidates_root,
                config=config,
                read_token=read_token,
                prompts_path=args.prompts,
                registry_path=args.registry,
                lane=args.lane,
            )
        else:
            cascade_pipeline(
                repository=args.repository,
                ecosystem=args.ecosystem,
                workdir=args.workdir,
                facts_dir=args.facts_dir,
                candidates_root=args.candidates_root,
                config=config,
                read_token=read_token,
                prompts_path=args.prompts,
                registry_path=args.registry,
                expected_facts_sha256=args.expected_facts_sha256,
                lane=args.lane,
            )

    def publish() -> None:
        publication = publish_bundle(
            args.repository,
            args.lane,
            args.candidates_root / CANDIDATES_DIRNAME / args.repository.replace("/", "__"),
            remote=args.state_remote,
            token=state_token,
        )
        print(
            f"bundle: {publication.ref} {publication.commit[:12]} "
            f"({publication.files} files, {'pushed' if publication.changed else 'unchanged'})"
        )

    try:
        version_set: str | None = current_fingerprint(args.lane, load_manifests(args.prompts))
    except Exception as exc:  # noqa: BLE001 -- the label is informational; the run decides
        print(f"version set: not computable ({type(exc).__name__}: {exc})")
        version_set = None
    else:
        print(f"version set (Lane {args.lane}): {version_set[:12]}")

    with GitStateBackend(
        remote=args.state_remote, token=state_token, lane=args.lane
    ) as backend:
        exit_code = run_present(
            version_set=version_set,
            backend=backend,
            entry=entry,
            candidates_root=args.candidates_root,
            holder_id=f"present:{args.workflow_run_id or os.getpid()}",
            workflow_run_id=args.workflow_run_id,
            pipeline=pipeline,
            lane=args.lane,
            publish=publish,
        )
        record = backend.load(args.repository)

    state = record.state if record is not None else "NO_RECORD"
    print(
        f"present: {args.repository} lane {args.lane} exit {exit_code}, durable state {state}"
    )
    failure = getattr(record, "failure", None) if exit_code else None
    if failure is not None:
        print(f"failure ({failure.classification}): {failure.detail}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
