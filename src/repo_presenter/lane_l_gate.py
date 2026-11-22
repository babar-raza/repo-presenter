"""The R5(a) gate of the production Lane L step (WP-4, BL-188; owner ruling R50, 2026-11-22).

``lane_l_trigger`` (TC-025) is the pure decision: a baseline revision, whether anything relevant
changed upstream since it, and the three-outcome taxonomy. It had no production caller. This module
is the thin, read-only layer that gives it the inputs a hosted Lane L run has on hand and decides
what the run may spend:

* the BASELINE is the latest sealed Lane L candidate in the candidates root (its ``dependencies.json``
  names the source revision and the detector set it ran under); with no such seal, or one sealed
  under another detector set, there is no baseline and the run is a real attempt (a never-sealed
  cell still owes its first seal; a newly added detector may find what the old seal could not);
* the CHANGED PATHS are ``git diff --name-only <baseline> <head>`` in the pinned clone (the baseline
  commit is fetched read-only when the shallow clone lacks it); any failure is "unknown";
* a TRIGGER (a relevant path changed, or anything is unknown) lets the run proceed to its one
  provider call; NO trigger means the call is not made: ``NO_ACTION_JUSTIFIED`` when the live README
  carries no finding and every deterministic probe is clean (the existing seal stands untouched), and
  otherwise a held attempt that names the finding (R5 strict: a defect alone, with no relevant
  upstream change, is not a reason to spend a call).

Zero provider calls here; nothing is written to any repository.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from repo_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    LANE_L,
    lane_directory,
)
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.lane_l_trigger import (
    OUTCOME_EDIT_CANDIDATE,
    OUTCOME_NO_ACTION_JUSTIFIED,
    LaneLSeal,
    TriggerResult,
    classify_outcome,
    trigger_for_repository,
)
from repo_presenter.readme.correction.detectors import DETECTOR_VERSIONS

DEPENDENCIES_FILENAME = "dependencies.json"
TRIGGER_RECORD_FILENAME = "lane-l-trigger.json"
#: The outcome of an untriggered run that still has a finding the engine could not clear: no call
#: is made and nothing is sealed, and the cell says why (never silence, never an unearned no-action).
OUTCOME_HELD_NO_TRIGGER = "HELD_NO_TRIGGER"

ChangedPaths = Callable[[Path, str, str], "tuple[str, ...] | None"]


class LaneLNoProviderCall(Exception):
    """Raised by ``run_lane_l`` after its deterministic stages when the R5(a) gate says the run
    spends no provider call. Carries the decision; the caller records it and returns or fails."""

    def __init__(self, decision: GateDecision) -> None:
        super().__init__(decision.reason)
        self.decision = decision


@dataclass(frozen=True)
class GateDecision:
    """What the gate decided and why; ``record()`` is what a run writes down."""

    repository: str
    triggered: bool
    outcome: str
    spends_provider_call: bool
    reason: str
    baseline_source: str
    baseline_revision: str | None
    head_revision: str | None
    relevant_paths: tuple[str, ...] = ()

    def record(self) -> dict[str, Any]:
        row = asdict(self)
        row["relevant_paths"] = list(self.relevant_paths[:40])
        return row


def sealed_lane_l(candidates_root: Path, repository: str) -> LaneLSeal | None:
    """The latest sealed Lane L candidate's source revision and detector set, or ``None`` when there
    is none or it cannot be read (an unreadable seal is no baseline: the run is then a real attempt)."""
    lane_root = lane_directory(candidates_root / CANDIDATES_DIRNAME / repository.replace("/", "__"), LANE_L)
    pointer = lane_root / CURRENT_FILENAME
    try:
        revision = pointer.read_text(encoding="utf-8").strip()
        document = json.loads((lane_root / revision / DEPENDENCIES_FILENAME).read_text(encoding="utf-8"))
        source = str(document["source"]["revision"])
        detectors = {str(k): str(v) for k, v in dict(document["detectors"]).items()}
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return LaneLSeal(source, detectors) if revision and source else None


def changed_paths_between(clone: Path, baseline: str, head: str) -> tuple[str, ...] | None:
    """Paths that differ between two commits of the pinned clone, or ``None`` when that cannot be
    established (the baseline commit is fetched read-only first when the shallow clone lacks it)."""
    if run_git(["cat-file", "-e", f"{baseline}^{{commit}}"], cwd=clone).returncode != 0:
        from repo_presenter.core.git_safety.clone import _github_read_auth_env

        url = run_git(["remote", "get-url", "origin"], cwd=clone).stdout.strip()
        fetched = run_git(
            ["fetch", "--no-tags", "--depth", "1", "origin", baseline],
            cwd=clone, timeout=180, env=_github_read_auth_env(url, None),
        )
        if fetched.returncode != 0 or run_git(
            ["cat-file", "-e", f"{baseline}^{{commit}}"], cwd=clone
        ).returncode != 0:
            return None
    diff = run_git(["diff", "--name-only", "--no-renames", "-z", baseline, head], cwd=clone)
    if diff.returncode != 0:
        return None
    return tuple(path for path in diff.stdout.split("\0") if path)


def compute_gate_trigger(
    repository: str,
    clone_path: Path,
    candidates_root: Path,
    head_revision: str,
    *,
    detector_versions: Mapping[str, str] = DETECTOR_VERSIONS,
    changed_paths: ChangedPaths | None = None,
) -> TriggerResult:
    """R5(a) for this run: baseline from the latest Lane L seal, changed paths from the clone.
    Every unknown fails closed to ``triggered`` (``lane_l_trigger.compute_trigger``)."""
    seal = sealed_lane_l(candidates_root, repository)
    current = dict(detector_versions)
    paths: tuple[str, ...] | None = None
    if seal is not None and dict(seal.detector_versions) == current and seal.source_revision != head_revision:
        try:
            paths = (changed_paths or changed_paths_between)(clone_path, seal.source_revision, head_revision)
        except Exception:  # noqa: BLE001 -- unknowable changes fail closed, never skip
            paths = None
    return trigger_for_repository(
        repository,
        current_detector_versions=current,
        head_revision=head_revision,
        changed_paths_since_baseline=paths,
        last_lane_l_seal=seal,
    )


def decide(
    trigger: TriggerResult, *, has_findings: bool, probes_clean: bool | None,
    head_revision: str | None = None,
) -> GateDecision:
    """The gate's decision from the trigger and the deterministic results of this run. A triggered
    run (or one with unknown inputs) proceeds; an untriggered run never spends a provider call."""
    baseline = trigger.baseline
    base: dict[str, Any] = {
        "repository": trigger.repository,
        "triggered": trigger.triggered,
        "baseline_source": baseline.source,
        "baseline_revision": baseline.revision,
        "head_revision": head_revision,
        "relevant_paths": trigger.changed_paths,
    }
    if trigger.triggered:
        return GateDecision(
            outcome=OUTCOME_EDIT_CANDIDATE, spends_provider_call=True, reason=trigger.reason, **base
        )
    outcome = classify_outcome(
        readme_exists=True, trigger=trigger, has_findings=has_findings, probes_clean=probes_clean
    )
    if outcome == OUTCOME_NO_ACTION_JUSTIFIED:
        return GateDecision(
            outcome=outcome, spends_provider_call=False,
            reason=f"{trigger.reason}; the live README carries no finding and every probe is clean: "
            "no provider call, the sealed candidate stands", **base,
        )
    return GateDecision(
        outcome=OUTCOME_HELD_NO_TRIGGER, spends_provider_call=False,
        reason=f"{trigger.reason}; a finding remains but no relevant upstream change since the "
        "sealed baseline: no provider call (R5 strict), nothing sealed", **base,
    )


OUTCOME_PROOF_RERUN = "PROOF_RERUN_REPLAY"


def proof_rerun(trigger: TriggerResult, head_revision: str) -> GateDecision | None:
    """The head equals the sealed baseline: this is the established proof rerun (TC-008a), which
    replays the stored model reply from the call store and makes no provider call by itself, so the
    gate stands aside and only records the decision. ``None`` for any other trigger state."""
    if trigger.triggered or trigger.baseline.revision != head_revision:
        return None
    return GateDecision(
        repository=trigger.repository, triggered=False, outcome=OUTCOME_PROOF_RERUN,
        spends_provider_call=False,
        reason=f"{trigger.reason}; the proof rerun replays the stored review (call store), zero provider calls",
        baseline_source=trigger.baseline.source, baseline_revision=trigger.baseline.revision,
        head_revision=head_revision,
    )


def write_record(decision: GateDecision, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / TRIGGER_RECORD_FILENAME
    path.write_text(json.dumps(decision.record(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path
