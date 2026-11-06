#!/usr/bin/env python
"""Release-gate-card check (TC-011): per-lane independent acceptance, and upstream delivery as its
own, separately gated outcome.

Re-authored 2026-11-06 to owner ruling R4 (`docs/CONSOLIDATED_GOALS_2026-11-06.md`): about 25
accepted Lane R candidates and about 25 accepted Lane L candidates, **counted independently** --
the product sets may differ, neither lane is measured by the other. The previous version required
the SAME >=25 repositories pipeline-good on BOTH lanes and conflated acceptance with live upstream
delivery by counting only entries of a hand-editable `evidence/delivery_ledger.json`. Both are
gone: no editable marker or ledger file is read as evidence by this check.

Five outcomes are measured, separately and per lane, never collapsed into one number:

  (a)/(b) independently_accepted -- the lane's durable state record (state refs on the remote) is
      pipeline-good (ACCEPTED / READY_FOR_PROPOSAL) AND its sealed bundle (the durable bundle ref,
      falling back to the committed `candidates/` tree) verifies, belongs to that lane and that
      repository, and carries a review verdict that is an ACCEPT made by a MODEL reviewer, recorded
      under calibration status PASSED, at exactly the reviewer logic and prompt version that
      `data/reviewer_calibration.json` currently certifies as PASSED (read fail-closed by
      `repo_presenter.readme.review.calibration_status.load_calibration`). A pipeline-good record
      whose model ACCEPT was made under a NOT_PASSED (or otherwise non-matching) reviewer is
      reported as `pipeline_good_uncalibrated` and never counts; any other pipeline-good record
      that cannot be traced to a sealed model ACCEPT is `pipeline_good_unreviewed` (reason given).
  (c) publication_ready -- independently accepted AND the repository is on the owner's R3
      allowlist (`data/upstream_write_allowlist.json`) for `pull_request`. The remaining R3 gates
      (single owner per effect under TC-002, no duplicate, first PR as draft, a valid write
      authorization and token) are runtime gates enforced by `propose.effect` at the moment of
      the write and cannot be decided statically; this outcome is the static precondition.
  (d) effect_executed -- the durable record names a proposal (PR number) AND GitHub's API
      confirms that PR exists on that repository with that head branch.
  (e) live_verified -- (d) AND GitHub's API reports the PR merged AND the upstream default-branch
      README is byte-identical to the sealed candidate's README.md.

Gates (exit 0 only when the selected gate holds; the full report prints either way):
  --per-lane N        (TC-011's release threshold) lane R independently_accepted >= N AND
                      lane L independently_accepted >= N, each lane counted on its own.
  --live-verified N   (the separately gated upstream-delivery outcome) live_verified >= N in
                      lane R plus lane L. Not part of TC-011's acceptance.
A bare positional integer is read as --per-lane, for compatibility with the old invocation.

Usage: python ops/checks/portfolio_delivery_count.py [--per-lane N] [--live-verified N] [--json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

CALIBRATION = REPO_ROOT / "data" / "reviewer_calibration.json"
ALLOWLIST = REPO_ROOT / "data" / "upstream_write_allowlist.json"
REGISTRY = REPO_ROOT / "data" / "registry.json"

PIPELINE_GOOD = frozenset({"ACCEPTED", "READY_FOR_PROPOSAL"})
REVIEW_VERDICT_NAME = "review_verdict.json"
README_NAME = "README.md"

# outcome buckets for a pipeline-good lane (exactly one applies)
ACCEPTED = "independently_accepted"
UNCALIBRATED = "pipeline_good_uncalibrated"
UNREVIEWED = "pipeline_good_unreviewed"


@dataclass(frozen=True)
class SealedEvidence:
    """What the counter needs from one lane's sealed bundle, already integrity-verified."""

    source: str  # "durable-ref" or "committed"
    manifest: dict[str, Any]
    review: dict[str, Any] | None  # the raw review_verdict.json, None when absent
    readme: bytes | None


@dataclass
class LaneOutcome:
    repository: str
    lane: str
    record_state: str
    pipeline_good: bool = False
    bucket: str = ""  # ACCEPTED / UNCALIBRATED / UNREVIEWED, "" when not pipeline-good
    reason: str = ""
    publication_ready: bool = False
    effect_executed: bool = False
    live_verified: bool = False
    evidence_source: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def independently_accepted(self) -> bool:
        return self.bucket == ACCEPTED


def classify_review(review: dict[str, Any] | None, calibration: Any) -> tuple[str, str]:
    """(bucket, reason) for a pipeline-good lane's sealed review verdict. Pure.

    ``calibration`` is a ``calibration_status.Calibration`` (fail-closed reading of the committed
    file). Only an ACCEPT by a model reviewer, recorded under PASSED, at the logic and prompt
    version the committed calibration certifies as PASSED, is independently accepted.
    """
    if review is None:
        return UNREVIEWED, "the sealed bundle carries no review_verdict.json"
    if review.get("verdict") != "ACCEPT":
        return UNREVIEWED, f"sealed review verdict is {review.get('verdict')!r}, not ACCEPT"
    if review.get("model_verdict") is None:
        return UNREVIEWED, "deterministic-only verdict: no model review was made"
    if review.get("model_verdict") != "ACCEPT":
        return UNREVIEWED, f"model verdict is {review.get('model_verdict')!r}, not ACCEPT"
    # From here on the candidate has a model ACCEPT; whether it counts is purely calibration.
    if calibration.status != "PASSED":
        why = f": {calibration.problem}" if getattr(calibration, "problem", "") else ""
        return UNCALIBRATED, f"committed reviewer calibration is {calibration.status}{why}"
    if review.get("calibration_status") != "PASSED":
        return UNCALIBRATED, (
            f"the ACCEPT was made under calibration {review.get('calibration_status')!r}, not PASSED"
        )
    if str(review.get("reviewer_logic_version", "")) != calibration.reviewer_logic_version:
        return UNCALIBRATED, (
            f"reviewed by reviewer logic {review.get('reviewer_logic_version')!r}; PASSED "
            f"calibration certifies {calibration.reviewer_logic_version!r}"
        )
    if str(review.get("prompt_version", "")) != calibration.prompt_version:
        return UNCALIBRATED, (
            f"reviewed at prompt {review.get('prompt_version')!r}; PASSED calibration certifies "
            f"{calibration.prompt_version!r}"
        )
    return ACCEPTED, "sealed model ACCEPT under a PASSED, version-matching reviewer calibration"


def allowlisted_for_pr(allowlist: dict[str, Any], repository: str) -> bool:
    for entry in allowlist.get("repositories", []) or []:
        if isinstance(entry, dict) and entry.get("repository") == repository:
            return "pull_request" in (entry.get("effects") or [])
    return False


GitHub = Callable[[list[str]], bytes | None]


def gh_api(args: list[str]) -> bytes | None:
    """``gh api <args>``; None on any failure (fail closed: unverifiable is not verified)."""
    try:
        done = subprocess.run(["gh", "api", *args], capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def classify_lane(
    repository: str,
    lane: str,
    record: Any,
    evidence: SealedEvidence | None,
    evidence_error: str,
    calibration: Any,
    allowlist: dict[str, Any],
    github: GitHub,
) -> LaneOutcome:
    """One repository-lane's five outcomes. ``record`` is a ``RepositoryRecord`` or None."""
    state = "NO_RECORD" if record is None else str(record.state)
    out = LaneOutcome(repository=repository, lane=lane, record_state=state)
    out.pipeline_good = state in PIPELINE_GOOD
    if out.pipeline_good:
        if evidence is None:
            out.bucket, out.reason = UNREVIEWED, evidence_error or "no sealed bundle"
        else:
            out.evidence_source = evidence.source
            if str(evidence.manifest.get("state")) not in PIPELINE_GOOD:
                out.bucket, out.reason = UNREVIEWED, (
                    f"sealed bundle state is {evidence.manifest.get('state')!r}"
                )
            else:
                out.bucket, out.reason = classify_review(evidence.review, calibration)
    out.publication_ready = out.independently_accepted and allowlisted_for_pr(allowlist, repository)

    proposal = None if record is None else record.proposal
    if proposal is not None and proposal.number is not None:
        raw = github([f"repos/{proposal.repository}/pulls/{proposal.number}"])
        pr = None
        if raw is not None:
            try:
                pr = json.loads(raw)
            except ValueError:
                pr = None
        if not isinstance(pr, dict):
            out.notes.append(f"PR #{proposal.number} could not be confirmed via the GitHub API")
        elif (pr.get("head") or {}).get("ref") != proposal.branch:
            out.notes.append(f"PR #{proposal.number} head is not the recorded branch {proposal.branch!r}")
        else:
            out.effect_executed = True
            if pr.get("merged") is True and evidence is not None and evidence.readme is not None:
                live = github(
                    [f"repos/{repository}/readme", "-H", "Accept: application/vnd.github.raw"]
                )
                if live is not None and live == evidence.readme:
                    out.live_verified = True
                else:
                    out.notes.append("merged, but the live README does not equal the sealed candidate")
    return out


def read_sealed(lane_root: Path, lane: str, repository: str, source: str) -> SealedEvidence:
    """Verify ``lane_root``'s CURRENT bundle and read the parts the counter needs. Raises on any
    integrity failure (the caller records it as the reason the lane is not accepted)."""
    from repo_presenter.core.candidates import CURRENT_FILENAME, verify_bundle

    revision = (lane_root / CURRENT_FILENAME).read_text(encoding="utf-8").strip()
    bundle = lane_root / revision
    manifest = verify_bundle(bundle, lane)
    if manifest is None:
        raise ValueError(f"{source} bundle has no manifest at CURRENT {revision}")
    if manifest.get("repository") not in (None, repository):
        raise ValueError(f"{source} bundle names repository {manifest.get('repository')!r}")
    files = manifest.get("files", {})
    review = None
    if REVIEW_VERDICT_NAME in files:  # only manifest-sealed files are evidence
        review = json.loads((bundle / REVIEW_VERDICT_NAME).read_text(encoding="utf-8"))
    readme = (bundle / README_NAME).read_bytes() if README_NAME in files else None
    return SealedEvidence(source=source, manifest=manifest, review=review, readme=readme)


def load_evidence(repository: str, lane: str, stored: frozenset[str], scratch: Path):
    """(SealedEvidence | None, error). Durable bundle ref first, committed candidates/ second."""
    from repo_presenter.core.candidates import CANDIDATES_DIRNAME, lane_directory
    from repo_presenter.core.state.bundle_store import bundle_ref, export_bundle

    errors = []
    if bundle_ref(repository, lane) in stored:
        try:
            root = export_bundle(repository, lane, scratch / lane)
            return read_sealed(root, lane, repository, "durable-ref"), ""
        except Exception as exc:  # noqa: BLE001 -- any failure is a reason, never a count
            errors.append(f"durable bundle ref: {exc}")
    committed = lane_directory(REPO_ROOT / CANDIDATES_DIRNAME / repository.replace("/", "__"), lane)
    if (committed / "CURRENT").is_file():
        try:
            return read_sealed(committed, lane, repository, "committed"), ""
        except Exception as exc:  # noqa: BLE001
            errors.append(f"committed bundle: {exc}")
    return None, "; ".join(errors) or "no sealed bundle (neither a durable bundle ref nor a committed one)"


def summarize(outcomes: list[LaneOutcome], calibration: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "reviewer_calibration": calibration.status
        + (f" ({calibration.problem})" if calibration.problem else ""),
    }
    for lane in ("R", "L"):
        rows = [o for o in outcomes if o.lane == lane]
        buckets = Counter(o.bucket for o in rows if o.pipeline_good)
        summary[f"lane_{lane.lower()}"] = {
            "records": sum(1 for o in rows if o.record_state != "NO_RECORD"),
            "pipeline_good": sum(1 for o in rows if o.pipeline_good),
            ACCEPTED: buckets[ACCEPTED],
            UNCALIBRATED: buckets[UNCALIBRATED],
            UNREVIEWED: buckets[UNREVIEWED],
            "publication_ready": sum(1 for o in rows if o.publication_ready),
            "effect_executed": sum(1 for o in rows if o.effect_executed),
            "live_verified": sum(1 for o in rows if o.live_verified),
            "accepted_repositories": sorted(o.repository for o in rows if o.independently_accepted),
        }
    return summary


def evaluate(summary: dict[str, Any], per_lane: int | None, live_verified: int | None) -> list[str]:
    """The failed gate conditions (empty = the selected gate holds). Pure."""
    failures = []
    if per_lane is not None:
        for lane in ("r", "l"):
            got = summary[f"lane_{lane}"][ACCEPTED]
            if got < per_lane:
                failures.append(f"Lane {lane.upper()} independently_accepted {got} < {per_lane}")
    if live_verified is not None:
        got = summary["lane_r"]["live_verified"] + summary["lane_l"]["live_verified"]
        if got < live_verified:
            failures.append(f"live_verified (R+L) {got} < {live_verified}")
    return failures


def collect(remote: str = "origin") -> tuple[list[LaneOutcome], Any]:
    from repo_presenter.core.portfolio_matrix import stored_bundle_refs
    from repo_presenter.core.registry.loader import load_registry
    from repo_presenter.core.state.git_backend import GitStateBackend
    from repo_presenter.readme.review.calibration_status import load_calibration

    calibration = load_calibration(CALIBRATION)
    allowlist = json.loads(ALLOWLIST.read_text(encoding="utf-8")) if ALLOWLIST.exists() else {}
    entries = load_registry(REGISTRY).entries
    stored = stored_bundle_refs(remote)
    outcomes: list[LaneOutcome] = []
    with tempfile.TemporaryDirectory(prefix="p1-count-") as tmp:
        backends = {lane: GitStateBackend(remote=remote, lane=lane) for lane in ("R", "L")}
        try:
            for entry in entries:
                for lane in ("R", "L"):
                    record = backends[lane].load(entry.repository)
                    evidence, error = (None, "")
                    if record is not None and str(record.state) in PIPELINE_GOOD:
                        evidence, error = load_evidence(entry.repository, lane, stored, Path(tmp))
                    outcomes.append(
                        classify_lane(
                            entry.repository, lane, record, evidence, error,
                            calibration, allowlist, gh_api,
                        )
                    )
        finally:
            for backend in backends.values():
                backend.close()
    return outcomes, calibration


def main(argv: list[str]) -> int:
    if argv and argv[0].isdigit():  # old positional form: "<minimum>" == --per-lane
        argv = ["--per-lane", argv[0], *argv[1:]]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--per-lane", type=int, default=None)
    parser.add_argument("--live-verified", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)
    if args.per_lane is None and args.live_verified is None:
        args.per_lane = 25

    outcomes, calibration = collect(args.remote)
    summary = summarize(outcomes, calibration)
    if args.json:
        print(json.dumps({"summary": summary, "lanes": [asdict(o) for o in outcomes]}, indent=2))
    else:
        print(f"reviewer_calibration: {summary['reviewer_calibration']}")
        for lane in ("r", "l"):
            row = dict(summary[f"lane_{lane}"])
            names = row.pop("accepted_repositories")
            print(f"lane {lane.upper()}: " + "  ".join(f"{k}={v}" for k, v in row.items()))
            if names:
                print(f"  accepted: {', '.join(names)}")
        for o in outcomes:
            if o.pipeline_good and not o.independently_accepted:
                print(f"  [{o.lane}] {o.repository}: {o.bucket} -- {o.reason}")
            for note in o.notes:
                print(f"  [{o.lane}] {o.repository}: {note}")

    failures = evaluate(summary, args.per_lane, args.live_verified)
    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    gates = []
    if args.per_lane is not None:
        gates.append(f"each lane independently_accepted >= {args.per_lane}")
    if args.live_verified is not None:
        gates.append(f"live_verified >= {args.live_verified}")
    print("OK: " + "; ".join(gates))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
