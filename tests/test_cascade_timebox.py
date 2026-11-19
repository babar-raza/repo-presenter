# ruff: noqa: F811, F401
"""BL-270: the cascade's progress lines and its wall-clock time-box, offline, with an injected clock.

Reuses the scripted-provider fixtures of ``tests/test_cascade_s10.py``. Zero provider calls.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from repo_presenter.cascade import CASCADE_TIMEBOX_SECONDS
from tests.test_cascade_s10 import (
    GPU,
    HUB_LINE,
    REPAIRED_TEXT,
    Replies,
    Run,
    _authored_with_hub,
    _fixed_git_revision,
    authored,
    claim_finding,
    clean_gates,
    opening_finding,
    repaired_pass,
    review_reply,
)

PROGRESS = re.compile(r"cascade progress: (?P<event>.*) \| elapsed (?P<t>\d+)s \| provider calls (?P<n>-?\d+)")


class Ticking:
    """A deterministic clock: every reading advances ``step`` seconds."""

    def __init__(self, step: float = 10.0) -> None:
        self.now = 0.0
        self.step = step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


@pytest.fixture
def run(tmp_path: Path) -> Run:
    return Run(tmp_path)


def test_the_default_timebox_leaves_room_for_the_last_round_inside_the_job_timeout() -> None:
    assert 0 < CASCADE_TIMEBOX_SECONDS <= 3600


def test_an_expired_timebox_starts_no_repair_round_and_the_degrade_then_runs(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None, capsys: pytest.CaptureFixture[str]
) -> None:
    # The reply queue holds no repair reply: a repair round that started would pop an empty list.
    provider = Replies(
        monkeypatch,
        *_authored_with_hub(f"The widget class renders. {GPU}"),
        review_reply("REJECT_PRESENTATION", claim_finding(HUB_LINE)),
        review_reply(),
    )
    result = run.cascade(review_repair_rounds=2, timebox_seconds=0.0, clock=Ticking())

    assert provider.replies == [] and provider.reviewer_calls == 2
    assert result.review_verdict.verdict == "ACCEPT"
    readme = (run.out / "README.coherent.md").read_text(encoding="utf-8")
    assert GPU not in readme
    units = json.loads((run.out / "content_units.coherent.json").read_text(encoding="utf-8"))
    assert [r["rule"] for r in units["degrade_records"]] == ["BL-240"]
    err = capsys.readouterr().err
    assert "S10: time-box reached, no review repair round starts" in err
    assert "degrade pass 1 start" in err


def test_without_the_deadline_the_repair_runs_exactly_as_before(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    fingerprint = run.fingerprint("opening", "specificity")
    provider = Replies(
        monkeypatch,
        *authored(),
        review_reply("REJECT_PRESENTATION", opening_finding()),
        *repaired_pass(fingerprint, REPAIRED_TEXT),
        review_reply(),
    )
    result = run.cascade(timebox_seconds=10**9, clock=Ticking())

    assert provider.replies == [] and result.provider_calls == 12 and result.rounds == 2
    assert result.review_verdict.verdict == "ACCEPT"
    assert REPAIRED_TEXT in (run.out / "README.coherent.md").read_text(encoding="utf-8")


def test_progress_lines_come_in_stage_order_with_elapsed_and_calls(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None, capsys: pytest.CaptureFixture[str]
) -> None:
    fingerprint = run.fingerprint("opening", "specificity")
    Replies(
        monkeypatch,
        *authored(),
        review_reply("REJECT_PRESENTATION", opening_finding()),
        *repaired_pass(fingerprint, REPAIRED_TEXT),
        review_reply(),
    )
    run.cascade(clock=Ticking())

    lines = [m for m in map(PROGRESS.search, capsys.readouterr().err.splitlines()) if m]
    events = [m["event"] for m in lines]
    expected = [
        "S3 investigation start",
        "S3 investigation end",
        "S9 settle round 1 of 1: compose start",
        "S9 settle round 1 of 1: judged",
        "S10 review start (repair round 0 of 4)",
        "S10 review end: REJECT",
        "S9 settle round 1 of 1: compose start",
        "S9 settle round 1 of 1: judged",
        "S10 review start (repair round 1 of 4)",
        "S10 review end: ACCEPT",
        "S9/S10 end after 2 settle round(s): ACCEPT",
        "cascade end: ACCEPT",
    ]
    cursor = 0
    for want in expected:
        cursor = next(i for i in range(cursor, len(events)) if events[i].startswith(want)) + 1
    elapsed = [int(m["t"]) for m in lines]
    calls = [int(m["n"]) for m in lines]
    assert elapsed == sorted(elapsed) and elapsed[0] > 0
    assert calls == sorted(calls) and calls[-1] == 12
