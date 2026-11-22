# ruff: noqa: F811, F401
"""BL-711: the cascade's hard wall-clock stop. Hosted Words Java runs 44943578461, 44952689353 and 44977866731
ended 'cancelled' at the runner's 90-minute cap: the 3,000 s time-box only stops a repair round from STARTING,
so a round already running (hundreds of serial model calls) was bounded by nothing and a cancelled step records
no stage. Past the hard stop no provider call and no stage starts; the run ends as a recorded failure."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.cascade import CASCADE_HARD_STOP_SECONDS, CASCADE_TIMEBOX_SECONDS
from repo_presenter.core.errors import CascadeTimeBoxError, JobError, PresenterError
from repo_presenter.core.llm.ledger import Ledger
from tests.test_cascade_s10 import Replies, Run, authored, clean_gates, review_reply
from tests.test_cascade_timebox import Ticking


@pytest.fixture
def run(tmp_path: Path) -> Run:
    return Run(tmp_path)


def test_the_hard_stop_is_after_the_time_box_and_leaves_room_inside_the_job_timeout() -> None:
    assert CASCADE_TIMEBOX_SECONDS < CASCADE_HARD_STOP_SECONDS <= 5400 - 300


def test_the_error_is_not_a_job_error_so_no_retry_or_degrade_path_swallows_it() -> None:
    assert issubclass(CascadeTimeBoxError, PresenterError) and not issubclass(CascadeTimeBoxError, JobError)


def test_a_call_past_the_hard_stop_is_refused_before_it_is_sent(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.jsonl")
    ledger.reserve_provider_call()  # no stop set: unchanged
    ledger.hard_stop = lambda: None
    ledger.reserve_provider_call()
    ledger.hard_stop = lambda: "over the limit in stage X"
    with pytest.raises(CascadeTimeBoxError, match="stage X"):
        ledger.reserve_provider_call()


def test_a_run_past_the_hard_stop_ends_with_the_stage_and_makes_no_further_call(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = Replies(monkeypatch, *authored(), review_reply())
    with pytest.raises(CascadeTimeBoxError) as raised:
        run.cascade(hard_stop_seconds=35.0, clock=Ticking(10.0))
    assert "hard time limit of 35s" in str(raised.value) and "stage '" in str(raised.value)
    assert len(provider.payloads) < 9  # the nine authoring-side calls never all ran
    progress = (run.out / "progress.json").read_text(encoding="utf-8")
    assert "stage" in progress  # the last stage reached is on disk for the failure record


def test_negative_control_without_a_reached_stop_the_run_is_unchanged(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    provider = Replies(monkeypatch, *authored(), review_reply())
    result = run.cascade(hard_stop_seconds=10**9, clock=Ticking(10.0))
    assert provider.replies == [] and result.review_verdict.verdict == "ACCEPT"
