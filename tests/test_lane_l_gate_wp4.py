"""WP-4 (BL-188, owner ruling R50): the R5(a) trigger gates the production Lane L step.

End to end through the real ``present`` CLI on a disposable upstream: a repository is sealed once;
then upstream moves and the next Lane L run must (relevant change) spend its provider call, (change
touching nothing relevant) spend none and leave the sealed candidate exactly as it was, and
(changed paths unreadable) fail closed to the call. Pure-function controls cover the gate's
decision table without a git repository.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from support import commit_all, head_revision
from test_lane_l_hosted import (
    CLEAN_README,
    SLUG,
    Hosted,
    Provider,
    accept_reply,
    digest_tree,
)

from repo_presenter import lane_l_gate
from repo_presenter.lane_l_gate import (
    OUTCOME_HELD_NO_TRIGGER,
    decide,
)
from repo_presenter.lane_l_trigger import (
    OUTCOME_NO_ACTION_JUSTIFIED,
    LaneLSeal,
    compute_baseline,
    compute_trigger,
)

DETECTORS = {"broken_link": "1"}


def _sealed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Hosted, str]:
    """A clean-README repository sealed once (one provider call), then re-run unchanged so the
    TC-008a proof rerun has replayed; returns the hosted environment and the sealed revision."""
    hosted = Hosted(tmp_path, monkeypatch, CLEAN_README)
    provider = Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("seal", hosted.facts("seal")) == 0
    assert provider.calls >= 1
    return hosted, head_revision(hosted.upstream)


def _move_upstream(hosted: Hosted, path: str, text: str) -> None:
    target = hosted.upstream / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    commit_all(hosted.upstream, f"touch {path}")


def _record(hosted: Hosted, tag: str) -> dict:
    return json.loads((hosted.root / f"work-{tag}" / lane_l_gate.TRIGGER_RECORD_FILENAME).read_text("utf-8"))


def test_an_irrelevant_upstream_change_spends_no_provider_call_and_keeps_the_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted, sealed_revision = _sealed(tmp_path, monkeypatch)
    before = digest_tree(hosted.bundle())
    _move_upstream(hosted, "CHANGELOG.md", "# Changes\n\n- a release note\n")
    assert head_revision(hosted.upstream) != sealed_revision
    provider = Provider(monkeypatch)  # no replies scripted: any call raises
    assert hosted.lane_l("next", hosted.facts("next")) == 0
    assert provider.calls == 0
    record = _record(hosted, "next")
    assert record["outcome"] == OUTCOME_NO_ACTION_JUSTIFIED
    assert record["triggered"] is False and record["spends_provider_call"] is False
    assert record["baseline_revision"] == sealed_revision
    assert digest_tree(hosted.bundle()) == before  # the sealed candidate stands untouched


def test_a_relevant_upstream_change_triggers_the_one_provider_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted, sealed_revision = _sealed(tmp_path, monkeypatch)
    _move_upstream(hosted, "widget.py", "def render():\n    return 2\n")
    provider = Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("next", hosted.facts("next")) == 0
    assert provider.calls >= 1
    record = _record(hosted, "next")
    assert record["triggered"] is True and record["outcome"] == "EDIT_CANDIDATE"
    assert record["relevant_paths"] == ["widget.py"]
    assert hosted.manifest()["revision"] == head_revision(hosted.upstream) != sealed_revision


def test_unreadable_changed_paths_fail_closed_to_a_provider_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted, _ = _sealed(tmp_path, monkeypatch)
    _move_upstream(hosted, "CHANGELOG.md", "# Changes\n")  # irrelevant, but nobody can tell
    monkeypatch.setattr(lane_l_gate, "changed_paths_between", lambda clone, baseline, head: None)
    provider = Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("next", hosted.facts("next")) == 0
    assert provider.calls >= 1
    record = _record(hosted, "next")
    assert record["triggered"] is True
    assert "failing closed" in record["reason"]


def test_a_cell_with_no_lane_l_seal_is_a_real_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted = Hosted(tmp_path, monkeypatch, CLEAN_README)
    provider = Provider(monkeypatch, default=accept_reply())
    assert hosted.lane_l("first", hosted.facts("first")) == 0
    assert provider.calls >= 1
    assert _record(hosted, "first")["baseline_source"] == "none"


# --- the decision table, without git --------------------------------------------------------------


def _trigger(paths):
    seal = LaneLSeal("a" * 40, DETECTORS)
    baseline = compute_baseline("o/r", current_detector_versions=DETECTORS, last_lane_l_seal=seal)
    return compute_trigger("o/r", baseline=baseline, head_revision="b" * 40, changed_paths_since_baseline=paths)


def test_untriggered_with_a_finding_is_held_not_justified_and_spends_nothing() -> None:
    held = decide(_trigger(["CHANGELOG.md"]), has_findings=True, probes_clean=False)
    assert held.outcome == OUTCOME_HELD_NO_TRIGGER and not held.spends_provider_call


def test_untriggered_clean_is_no_action_justified_only_with_clean_probes() -> None:
    assert decide(_trigger([]), has_findings=False, probes_clean=True).outcome == OUTCOME_NO_ACTION_JUSTIFIED
    # a finding the probes did not clear is never waved through as "nothing to do"
    assert decide(_trigger([]), has_findings=True, probes_clean=None).outcome == OUTCOME_HELD_NO_TRIGGER


def test_triggered_and_unknown_paths_spend_the_call() -> None:
    assert decide(_trigger(["src/a.py"]), has_findings=False, probes_clean=True).spends_provider_call
    assert decide(_trigger(None), has_findings=False, probes_clean=True).spends_provider_call


def test_an_old_detector_set_is_not_a_baseline(tmp_path: Path) -> None:
    trigger = lane_l_gate.compute_gate_trigger(
        "o/r", tmp_path, tmp_path, "c" * 40, detector_versions=DETECTORS,
        changed_paths=lambda *_: ("README.md",),
    )
    assert trigger.triggered and trigger.baseline.source == "none"


def test_sealed_lane_l_reads_revision_and_detectors(tmp_path: Path) -> None:
    root = tmp_path / "candidates" / SLUG / "lane-l"
    (root / ("d" * 40)).mkdir(parents=True)
    (root / "CURRENT").write_text("d" * 40, encoding="utf-8")
    (root / ("d" * 40) / "dependencies.json").write_text(
        json.dumps({"source": {"revision": "d" * 40}, "detectors": DETECTORS}), encoding="utf-8"
    )
    seal = lane_l_gate.sealed_lane_l(tmp_path, SLUG.replace("__", "/"))
    assert seal == LaneLSeal("d" * 40, DETECTORS)
    assert lane_l_gate.sealed_lane_l(tmp_path, "x/y") is None
