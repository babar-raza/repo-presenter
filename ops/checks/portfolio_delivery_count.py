#!/usr/bin/env python
"""Release-gate-card check (TC-011): per-lane independent acceptance, and upstream delivery as its
own, separately gated outcome.

Re-authored 2026-11-06 to owner ruling R4 (`docs/CONSOLIDATED_GOALS_2026-11-06.md`): about 25
accepted Lane R candidates and about 25 accepted Lane L candidates, **counted independently** --
the product sets may differ, neither lane is measured by the other. The previous version required
the SAME >=25 repositories pipeline-good on BOTH lanes and conflated acceptance with live upstream
delivery by counting only entries of a hand-editable `evidence/delivery_ledger.json`. Both are
gone: no editable marker or ledger file is read as evidence by this check.

Re-based 2026-11-06 on the owner's version-set rules (`repo_presenter.core.version_set`): ONE
version set for every candidate that counts, and a version bump never invalidates a sealed
candidate. Counting therefore reads the SEAL HISTORY (every commit on the lane's durable bundle
ref, `bundle_store.seal_history`, plus the committed `candidates/` tree), never the transaction
record's latest state -- a failed re-run under a new version set moves that record ACCEPTED ->
INVALIDATED, but cannot remove an earlier seal. Seals are GROUPED BY version-set fingerprint: the
headline numbers are the CURRENT fingerprint's (the only set that can form a release set); every
older fingerprint is reported separately under `older_version_sets` and never summed in. The
calibration rule below is applied within each version set. The record is still read for the
latest attempt's state (`record_state`, informational) and its proposal (outcomes (d)/(e)).

2026-11-09 (TC-007 landed; see TC-011.yaml's own re-author note): the counting logic below
(`classify_review`, `classify_lane`) still reads `data/reviewer_calibration.json`, which is
frozen forever at `NOT_PASSED` (R10/R18) -- this is now a REAL known gap, not an oversight: a
live run of this script before this note was added printed the misleading
"committed reviewer calibration is NOT_PASSED" against every pipeline-good candidate, even
though `data/acceptance_calibration.json` (TC-013's real, new contract) had just reached PASSED
for the first time. The REAL blocker for `independently_accepted` is not calibration any more --
it is that no candidate has a real, attested M9 audit record yet (`acceptance/record.py`'s own
docstring: "live proof is TC-014's and later M1's own closeout evidence, not this card's"), and
this script has no attestation-record reader to wire in, because no such committed artifact
exists yet (the hosted audit workflows are untestable until this branch merges to `main` --
GitHub refuses `workflow_dispatch` for a workflow file not on the default branch). Rather than
fabricate a stand-in attestation reader against nothing real, this version adds a SEPARATE,
honest `acceptance_calibration` summary field (`repo_presenter.acceptance.record.load_certificates`)
reported ALONGSIDE the frozen `reviewer_calibration` field, so a reader is never misled into
thinking TC-013's real contract is still failing -- the counting logic itself is swapped onto the
new contract, with real attestation reading, in a later, separately-tracked piece of work.

Re-based again 2026-11-06 (owner rule: "a version bump never invalidates a seal or forces
regeneration", ``repo_presenter.recertify``): the headline is no longer "seals whose fingerprint
equals the current one" -- that dropped every count to 0 on each bump. A repository/lane now
COUNTS when its LATEST durable seal re-certifies under current code (``recertify`` in dry mode:
re-render, full blocking validation, deterministic reviewer rules; zero provider calls) or was
sealed by current code. The seal's version set is reported as provenance only. A latest seal that
is NEEDS_REPAIR is reported with its failing checks (the seal itself is kept). A model ACCEPT made
by an uncalibrated reviewer is reported as needing a review-only pass (no regeneration), never
silently dropped.

Five outcomes are measured, separately and per lane, never collapsed into one number:

  (a)/(b) independently_accepted -- the lane has a seal under the version set being counted whose
      manifest state is pipeline-good (ACCEPTED / READY_FOR_PROPOSAL), which verifies, belongs to
      that lane and that repository, and carries a review verdict that is an ACCEPT made by a MODEL reviewer, recorded
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
PROMPTS = REPO_ROOT / "prompts"

PIPELINE_GOOD = frozenset({"ACCEPTED", "READY_FOR_PROPOSAL"})
REVIEW_VERDICT_NAME = "review_verdict.json"
README_NAME = "README.md"
DEPENDENCIES_NAME = "dependencies.json"

# outcome buckets for a pipeline-good lane (exactly one applies)
ACCEPTED = "independently_accepted"
UNCALIBRATED = "pipeline_good_uncalibrated"
UNREVIEWED = "pipeline_good_unreviewed"
NO_ACTION = "no_action_justified"  # R16: a Lane L seal byte-identical to the live README is never accepted


@dataclass(frozen=True)
class SealedEvidence:
    """What the counter needs from one lane's sealed bundle, already integrity-verified."""

    source: str  # "durable-ref" or "committed"
    manifest: dict[str, Any]
    review: dict[str, Any] | None  # the raw review_verdict.json, None when absent
    readme: bytes | None
    version_set: str = ""  # the seal's full version-set fingerprint
    commit: str = ""  # the bundle-ref commit (a durable-ref seal only)


@dataclass
class LaneOutcome:
    repository: str
    lane: str
    record_state: str  # the latest ATTEMPT's transaction-record state; informational only
    pipeline_good: bool = False
    version_set: str = ""  # short fingerprint of the version set this outcome is counted in
    current: bool = True  # counted in the CURRENT version set (False: an older set, never summed)
    bucket: str = ""  # ACCEPTED / UNCALIBRATED / UNREVIEWED, "" when not pipeline-good
    reason: str = ""
    publication_ready: bool = False
    effect_executed: bool = False
    live_verified: bool = False
    evidence_source: str = ""
    notes: list[str] = field(default_factory=list)
    # re-certification of the latest seal under current code (``repo_presenter.recertify``)
    certification: str = ""  # RECERTIFIED / NEEDS_REPAIR / "" when not assessed
    sealed_by_current: bool = False
    failing_checks: list[str] = field(default_factory=list)
    regenerations: int = 0
    needs_review_only_pass: bool = False
    no_action: bool = False  # Lane L only: the sealed README equals the live README at ``revision``
    revision: str = ""  # the upstream revision the latest seal was made at; an audit binds to it

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
    """One repository-lane's five outcomes within one version set. ``record`` is a
    ``RepositoryRecord`` or None, read ONLY for the latest attempt's state (reported, never
    counted) and its proposal; ``evidence`` is the seal being counted. Whether the lane counts is
    decided by the seal alone, so a later failed attempt (record INVALIDATED) cannot demote it."""
    state = "NO_RECORD" if record is None else str(record.state)
    out = LaneOutcome(repository=repository, lane=lane, record_state=state)
    if evidence is None:
        if evidence_error:
            out.notes.append(evidence_error)
    else:
        out.evidence_source = evidence.source
        out.version_set = evidence.version_set[:12]
        if str(evidence.manifest.get("state")) not in PIPELINE_GOOD:
            out.bucket, out.reason = UNREVIEWED, (
                f"sealed bundle state is {evidence.manifest.get('state')!r}"
            )
        else:
            out.pipeline_good = True
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
    from repo_presenter.core.version_set import fingerprint

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
    if DEPENDENCIES_NAME not in files:
        raise ValueError(f"{source} bundle seals no {DEPENDENCIES_NAME}: no version set to count it in")
    dependencies = json.loads((bundle / DEPENDENCIES_NAME).read_text(encoding="utf-8"))
    readme = (bundle / README_NAME).read_bytes() if README_NAME in files else None
    return SealedEvidence(
        source=source, manifest=manifest, review=review, readme=readme,
        version_set=fingerprint(dependencies, lane),
    )


def from_seal_record(seal: Any) -> SealedEvidence | None:
    """A ``bundle_store.SealRecord`` (one commit of the durable bundle ref) as evidence, or None
    when that commit did not verify or sealed no dependencies record."""
    from repo_presenter.core.version_set import fingerprint

    if seal.error or seal.dependencies is None:
        return None
    return SealedEvidence(
        source="durable-ref",
        manifest={"state": seal.manifest_state, "revision": seal.revision},
        review=seal.review,
        readme=seal.readme,
        version_set=fingerprint(seal.dependencies, seal.lane),
        commit=seal.commit,
    )


_RANK = {ACCEPTED: 0, UNCALIBRATED: 1, UNREVIEWED: 2}


def best_by_version_set(
    seals: list[SealedEvidence], calibration: Any
) -> dict[str, SealedEvidence]:
    """``{version-set fingerprint: the seal that represents the lane in that set}``. Pure.

    Within one set the strongest seal stands (independently accepted, then uncalibrated, then
    unreviewed, then a non-terminal manifest state), the LATEST of equals. A later seal can
    therefore never take a set's count away from an earlier one: seals are immutable, and only a
    seal under the same set competes for it."""
    best: dict[str, tuple[int, SealedEvidence]] = {}
    for seal in seals:  # oldest first
        if str(seal.manifest.get("state")) in PIPELINE_GOOD:
            rank = _RANK[classify_review(seal.review, calibration)[0]]
        else:
            rank = len(_RANK)
        held = best.get(seal.version_set)
        if held is None or rank <= held[0]:
            best[seal.version_set] = (rank, seal)
    return {key: seal for key, (_rank, seal) in best.items()}


def lane_seals(repository: str, lane: str, history: dict, scratch: Path) -> tuple[list[SealedEvidence], list[str]]:
    """(every seal of the lane as evidence -- durable bundle-ref history then the committed
    ``candidates/`` tree --, the reasons any seal could not be read)."""
    from repo_presenter.core.candidates import CANDIDATES_DIRNAME, lane_directory

    seals: list[SealedEvidence] = []
    errors: list[str] = []
    for record in history.get((repository, lane), ()):
        evidence = from_seal_record(record)
        if evidence is None:
            errors.append(
                f"durable seal {record.commit[:12]}: {record.error or 'no dependencies record'}"
            )
        else:
            seals.append(evidence)
    committed = lane_directory(REPO_ROOT / CANDIDATES_DIRNAME / repository.replace("/", "__"), lane)
    if (committed / "CURRENT").is_file():
        try:
            seals.append(read_sealed(committed, lane, repository, "committed"))
        except Exception as exc:  # noqa: BLE001 -- any failure is a reason, never a count
            errors.append(f"committed bundle: {exc}")
    return seals, errors


def summarize(
    outcomes: list[LaneOutcome], calibration: Any, acceptance_certificates: Any = None
) -> dict[str, Any]:
    """Headline numbers are the CURRENT version set's only (``o.current``); every older set is
    reported on its own under ``older_version_sets`` and never added to them.

    ``acceptance_certificates`` (2026-11-09, TC-007 landed): the REAL, new TC-013 acceptance
    contract's global completeness (``repo_presenter.acceptance.record.AcceptanceCertificates``,
    ``data/acceptance_calibration.json`` against ``data/acceptance_responsibility.json``) --
    reported ALONGSIDE the frozen, historical ``reviewer_calibration`` field, never in place of
    it, and NOT YET used by ``independently_accepted``'s own counting logic below. That logic
    still reads the frozen ``data/reviewer_calibration.json`` path, because TC-011's real switch
    to the new contract additionally needs a real, attested audit-record reader (TC-014's hosted
    writer; see ``acceptance/record.py``'s own docstring: "live proof is TC-014's and later M1's
    own closeout evidence, not this card's") which does not exist as a committed artifact yet --
    building a fake stand-in for it here would be worse than leaving this honestly open. Optional
    only so every existing call site and test keeps working unchanged; omitting it reports
    ``acceptance_calibration: "not measured"`` rather than silently guessing PASSED."""
    if acceptance_certificates is None:
        acceptance_status = "not measured"
    elif acceptance_certificates.complete:
        acceptance_status = "PASSED"
    else:
        acceptance_status = f"NOT_PASSED: {acceptance_certificates.problem}" if acceptance_certificates.problem else "NOT_PASSED"
    summary: dict[str, Any] = {
        "reviewer_calibration": calibration.status
        + (f" ({calibration.problem})" if calibration.problem else ""),
        "acceptance_calibration": acceptance_status,
    }
    for lane in ("R", "L"):
        lane_rows = [o for o in outcomes if o.lane == lane]
        rows = [o for o in lane_rows if o.current]
        buckets = Counter(o.bucket for o in rows if o.pipeline_good)
        older: dict[str, dict[str, int]] = {}
        for o in lane_rows:
            if o.current or not o.pipeline_good:
                continue
            group = older.setdefault(o.version_set, {"pipeline_good": 0, ACCEPTED: 0, UNCALIBRATED: 0, UNREVIEWED: 0})
            group["pipeline_good"] += 1
            group[o.bucket] = group.get(o.bucket, 0) + 1
        counted_sets = {o.version_set for o in rows if o.pipeline_good}
        summary[f"lane_{lane.lower()}"] = {
            # provenance only: the version sets the counted seals were sealed under
            "version_set": ",".join(sorted(k for k in counted_sets if k))
            or next((o.version_set for o in rows if o.version_set), ""),
            "records": sum(1 for o in rows if o.record_state != "NO_RECORD"),
            "pipeline_good": sum(1 for o in rows if o.pipeline_good),
            ACCEPTED: buckets[ACCEPTED],
            UNCALIBRATED: buckets[UNCALIBRATED],
            UNREVIEWED: buckets[UNREVIEWED],
            NO_ACTION: buckets[NO_ACTION],
            "publication_ready": sum(1 for o in rows if o.publication_ready),
            "effect_executed": sum(1 for o in rows if o.effect_executed),
            "live_verified": sum(1 for o in rows if o.live_verified),
            "accepted_repositories": sorted(o.repository for o in rows if o.independently_accepted),
            "recertified": sum(1 for o in rows if o.certification == "RECERTIFIED"),
            "needs_repair": {
                o.repository: o.failing_checks for o in rows if o.certification == "NEEDS_REPAIR"
            },
            "needs_review_only_pass": sorted(o.repository for o in rows if o.needs_review_only_pass),
            "regenerated_more_than_once": {
                o.repository: o.regenerations for o in rows if o.regenerations > 1
            },
            "older_version_sets": dict(sorted(older.items())),
        }
    return summary


def evaluate(summary: dict[str, Any], per_lane: int | None, live_verified: int | None) -> list[str]:
    """The failed gate conditions (empty = the selected gate holds). Pure. Only the CURRENT
    version set's numbers are gated: an older set can never form a release set."""
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


def certified_outcomes(
    repository: str,
    lane: str,
    record: Any,
    seals: list[SealedEvidence],
    certification: Any,
    calibration: Any,
    allowlist: dict[str, Any],
    github: GitHub,
) -> list[LaneOutcome]:
    """The headline outcome of a lane whose LATEST durable seal was re-certified
    (``certification`` is a ``recertify.Recertification`` of that seal), plus one provenance row
    per other version set the lane has seals under. Pure apart from ``github``.

    The lane counts when the latest seal is RECERTIFIED under current code (or was sealed by it)
    and its preserved model review verdict passes the calibration rule. The seal's version set is
    provenance: a bump never zeroes the count. NEEDS_REPAIR is reported with its checks."""
    latest = next((s for s in seals if s.commit and s.commit == certification.seal_commit), None)
    certified = bool(certification.certified) and latest is not None
    head = classify_lane(
        repository, lane, record, latest if certified else None, "", calibration, allowlist, github
    )
    head.current = True
    head.certification = certification.outcome
    head.sealed_by_current = bool(certification.sealed_by_current)
    head.failing_checks = list(certification.failing_checks)
    head.regenerations = int(certification.regenerations)
    head.revision = str(getattr(certification, "revision", "") or "")
    head.version_set = (certification.sealed_version_set or "")[:12]
    if latest is not None:
        head.evidence_source = latest.source
    if not certified:
        head.reason = (
            f"latest seal {certification.seal_commit[:12]} is NEEDS_REPAIR under current code: "
            f"{', '.join(certification.failing_checks) or 'unreadable'} (the seal itself is kept)"
        )
        head.notes.append(head.reason)
    elif head.bucket == UNCALIBRATED:
        head.needs_review_only_pass = True
        head.reason += "; needs a review-only pass under a PASSED reviewer (no regeneration)"
    if lane == "L" and certified and latest is not None and latest.readme is not None and head.revision:
        live = github([f"repos/{repository}/contents/README.md?ref={head.revision}", "-H", "Accept: application/vnd.github.raw"])
        if live is not None and live.replace(b"\r\n", b"\n") == latest.readme.replace(b"\r\n", b"\n"):
            head.no_action = True
            head.notes.append("sealed README is byte-identical to the live README (R16: NO_ACTION_JUSTIFIED, never accepted)")
    if certification.regenerations > 1:
        head.notes.append(f"candidate regenerated {certification.regenerations} times")
    result = [head]
    for key, evidence in sorted(best_by_version_set(seals, calibration).items()):
        if latest is not None and key == latest.version_set:
            continue
        older = classify_lane(repository, lane, None, evidence, "", calibration, allowlist, github)
        older.current = False
        older.publication_ready = False
        result.append(older)
    return result


def outcomes_for_lane(
    repository: str,
    lane: str,
    record: Any,
    seals: list[SealedEvidence],
    errors: list[str],
    current: str,
    calibration: Any,
    allowlist: dict[str, Any],
    github: GitHub,
    certification: Any = None,
) -> list[LaneOutcome]:
    """With ``certification`` (the re-certification of the lane's latest durable seal), the
    headline is :func:`certified_outcomes`'s. Without one (a lane with no durable seal), one
    outcome counted under the CURRENT version set (always, even with no seal under it) plus one per
    older version set the lane has a seal under. Pure apart from ``github``."""
    if certification is not None:
        return certified_outcomes(
            repository, lane, record, seals, certification, calibration, allowlist, github
        )
    by_set = best_by_version_set(seals, calibration)
    head = classify_lane(
        repository, lane, record, by_set.get(current), "; ".join(errors),
        calibration, allowlist, github,
    )
    head.current = True
    head.version_set = current[:12]
    result = [head]
    for key, evidence in sorted(by_set.items()):
        if key == current:
            continue
        # No record: the attempt and its proposal belong to the current outcome only.
        older = classify_lane(repository, lane, None, evidence, "", calibration, allowlist, github)
        older.current = False
        older.publication_ready = False  # an older set can never form a release set
        result.append(older)
    return result


ATTESTATION_REPO = "babar-raza/repo-presenter"
ACCEPTANCE_WRITER = f"{ATTESTATION_REPO}/.github/workflows/acceptance-write.yml"
RECORD_BRANCH_PREFIX = "acceptance-record/"
RECORDS_SCHEMA = "acceptance-records/1"

#: (branch, file name, bytes) for every acceptance-records file found on a bot record branch.
RecordFetcher = Callable[[], list[tuple[str, str, bytes]]]


def fetch_record_files(remote: str = "origin") -> list[tuple[str, str, bytes]]:
    """Every ``acceptance-records-*.json`` on every ``acceptance-record/*`` branch. Any git failure
    yields nothing for that branch: an unreachable record is not a record."""
    def git(*args: str) -> bytes | None:
        try:
            done = subprocess.run(["git", *args], capture_output=True, timeout=120, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return done.stdout if done.returncode == 0 else None

    listing = git("ls-remote", "--heads", remote, f"{RECORD_BRANCH_PREFIX}*")
    found: list[tuple[str, str, bytes]] = []
    for line in (listing or b"").decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[1].startswith("refs/heads/"):
            continue
        branch = parts[1].removeprefix("refs/heads/")
        ref = f"refs/remotes/{remote}/{branch}"
        if git("fetch", "-q", remote, f"+refs/heads/{branch}:{ref}") is None:
            continue
        names = git("ls-tree", "--name-only", ref) or b""
        for name in names.decode("utf-8", "replace").splitlines():
            if name.startswith("acceptance-records-") and name.endswith(".json"):
                blob = git("show", f"{ref}:{name}")
                if blob is not None:
                    found.append((branch, name, blob))
    return found


def _gh_with_repo(args: list[str]) -> "subprocess.CompletedProcess[bytes]":
    # `gh attestation verify` refuses to run without --repo/--owner; the acceptance contract's
    # own wrapper (acceptance/record.py) does not pass one.
    return subprocess.run([*args, "--repo", ATTESTATION_REPO], capture_output=True, timeout=120, check=False)


def read_attested_acceptances(
    fetcher: RecordFetcher | None = None,
    gh_runner: Any = None,
    remote: str = "origin",
) -> dict[tuple[str, str], str]:
    """{(repository, lane): revision} for every clean-control record that is INDEPENDENTLY ACCEPTED
    or higher under ``acceptance.record.classify`` with a VERIFIED attestation from the hosted
    acceptance writer on ``main``. A missing branch, file, attestation or field is simply absent;
    nothing here raises. A ``dry_run`` document or one with another schema is ignored."""
    from repo_presenter.acceptance.record import (
        DELIVERED, INDEPENDENTLY_ACCEPTED, LIVE_VERIFIED, PUBLICATION_READY, classify,
    )

    counted = {INDEPENDENTLY_ACCEPTED, PUBLICATION_READY, DELIVERED, LIVE_VERIFIED}
    try:
        files = (fetcher or (lambda: fetch_record_files(remote)))()
    except Exception:  # noqa: BLE001 -- a broken fetch is "no records", never a crash or a pass
        return {}
    accepted: dict[tuple[str, str], str] = {}
    with tempfile.TemporaryDirectory(prefix="acc-records-") as tmp:
        for index, (branch, name, blob) in enumerate(files):
            try:
                document = json.loads(blob)
                records = document["records"]
                if document.get("schema") != RECORDS_SCHEMA or document.get("dry_run") is not False:
                    continue
                path = Path(tmp) / f"{index}-{Path(name).name}"
                path.write_bytes(blob)
                for record in records:
                    if record.get("role") != "clean_control":
                        continue
                    state = classify(
                        str(record["repository"]), str(record["lane"]),
                        sealed=True,
                        deterministically_validated=record.get("deterministically_validated") is True,
                        mechanism_verdicts=dict(record.get("mechanism_verdicts") or {}),
                        canaries=dict(record.get("canaries") or {}),
                        audit_passed=record.get("audit_passed") is True,
                        attestation_path=path,
                        expected_workflow=ACCEPTANCE_WRITER,
                        gh_runner=gh_runner or _gh_with_repo,
                    )
                    if state in counted:
                        accepted[(str(record["repository"]), str(record["lane"]))] = str(record.get("revision", ""))
            except Exception:  # noqa: BLE001 -- malformed record: contributes nothing
                continue
    return accepted


def apply_attested(
    outcomes: list[LaneOutcome], attested: dict[tuple[str, str], str], allowlist: dict[str, Any]
) -> None:
    """Make an attested acceptance record the ONLY road into the accepted bucket. The frozen
    ``reviewer_calibration`` path may still have produced ACCEPTED in ``classify_lane``; that is
    demoted here unless an attested record exists, and only the CURRENT version set can count."""
    for o in outcomes:
        if not o.pipeline_good:
            continue
        if o.no_action:
            o.bucket = NO_ACTION
            o.reason = "R16: the sealed Lane L README equals the live README; terminal NO_ACTION_JUSTIFIED, never accepted"
            o.publication_ready = False
            continue
        audited_revision = attested.get((o.repository, o.lane))
        if o.current and audited_revision and audited_revision == o.revision:
            o.bucket = ACCEPTED
            o.reason = "attested independently-accepted record from the hosted acceptance writer"
        elif o.bucket == ACCEPTED:
            o.bucket = UNCALIBRATED
            o.reason = "no attested independently-accepted record (M9 audit not passed or not attested)"
        o.publication_ready = o.independently_accepted and allowlisted_for_pr(allowlist, o.repository)


def collect(remote: str = "origin", record_fetcher: RecordFetcher | None = None, gh_runner: Any = None) -> tuple[list[LaneOutcome], Any, Any]:
    from repo_presenter.acceptance.record import load_certificates
    from repo_presenter.core.registry.loader import load_registry
    from repo_presenter.core.state.git_backend import GitStateBackend
    from repo_presenter.core.version_set import current_fingerprints
    from repo_presenter.readme.review.calibration_status import load_calibration
    from repo_presenter.recertify import portfolio_recertification

    calibration = load_calibration(CALIBRATION)
    acceptance_certificates = load_certificates()
    allowlist = json.loads(ALLOWLIST.read_text(encoding="utf-8")) if ALLOWLIST.exists() else {}
    entries = load_registry(REGISTRY).entries
    current = current_fingerprints(PROMPTS)
    # Dry re-certification of every bundle ref's latest seal (zero provider calls, read-only); its
    # seal history is the same one the counter reads, fetched once.
    results, history = portfolio_recertification(
        remote=remote, registry=REGISTRY, prompts_dir=PROMPTS
    )
    certifications = {(r.repository, r.lane): r for r in results}
    outcomes: list[LaneOutcome] = []
    with tempfile.TemporaryDirectory(prefix="p1-count-") as tmp:
        backends = {lane: GitStateBackend(remote=remote, lane=lane) for lane in ("R", "L")}
        try:
            for entry in entries:
                for lane in ("R", "L"):
                    record = backends[lane].load(entry.repository)
                    seals, errors = lane_seals(entry.repository, lane, history, Path(tmp))
                    outcomes.extend(
                        outcomes_for_lane(
                            entry.repository, lane, record, seals, errors, current[lane],
                            calibration, allowlist, gh_api,
                            certification=certifications.get((entry.repository, lane)),
                        )
                    )
        finally:
            for backend in backends.values():
                backend.close()
    apply_attested(outcomes, read_attested_acceptances(record_fetcher, gh_runner, remote), allowlist)
    return outcomes, calibration, acceptance_certificates


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

    outcomes, calibration, acceptance_certificates = collect(args.remote)
    summary = summarize(outcomes, calibration, acceptance_certificates)
    if args.json:
        print(json.dumps({"summary": summary, "lanes": [asdict(o) for o in outcomes]}, indent=2))
    else:
        print(f"reviewer_calibration: {summary['reviewer_calibration']}")
        print(f"acceptance_calibration: {summary['acceptance_calibration']}")
        for lane in ("r", "l"):
            row = dict(summary[f"lane_{lane}"])
            names = row.pop("accepted_repositories")
            print(f"lane {lane.upper()}: " + "  ".join(f"{k}={v}" for k, v in row.items()))
            if names:
                print(f"  accepted: {', '.join(names)}")
        for o in outcomes:
            if o.certification == "NEEDS_REPAIR":
                print(f"  [{o.lane}] {o.repository}: NEEDS_REPAIR -- {', '.join(o.failing_checks)}")
            if o.pipeline_good and not o.independently_accepted:
                where = "current" if o.current else "older"
                print(f"  [{o.lane}] {o.repository} ({where} set {o.version_set}): "
                      f"{o.bucket} -- {o.reason}")
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
