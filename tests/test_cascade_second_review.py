# ruff: noqa: F811, F401
"""BL-430: a candidate the production review accepts is reviewed a second time over the packet the
independent audit uses, and a blocking finding of either sample on author-written text blocks it.

Offline, zero provider calls beyond the scripted replies of ``tests/test_cascade_s10.py``. The negative
controls are as load-bearing as the positives: a second sample that finds nothing leaves the verdict
exactly as it was, a finding on text the renderer printed is not counted, a rejected candidate is never
sampled again, and the default is on.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.cascade import run_cascade
from tests.test_cascade_s10 import (
    GPU,
    HUB_LINE,
    Replies,
    Run,
    _authored_with_hub,
    _fixed_git_revision,
    claim_finding,
    clean_gates,
    review_reply,
)


@pytest.fixture
def run(tmp_path: Path) -> Run:
    return Run(tmp_path)


def test_the_production_default_is_two_samples() -> None:
    source = inspect.getsource(cascade_module)
    assert re.search(r"^SECOND_REVIEW = True$", source, re.MULTILINE)
    assert inspect.signature(run_cascade).parameters["second_review"].default is None


def test_off_means_one_review_and_no_second_sample_records(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    provider = Replies(monkeypatch, *_authored_with_hub(f"The widget class renders. {GPU}"), review_reply())
    result = run.cascade(second_review=False)

    assert provider.reviewer_calls == 1 and result.review_verdict.verdict == "ACCEPT"
    assert not any("sample" in r for r in result.review_verdict.unit_reviews)


def test_a_second_sample_that_finds_nothing_leaves_the_verdict_and_records_its_units(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    provider = Replies(
        monkeypatch, *_authored_with_hub(f"The widget class renders. {GPU}"), review_reply(), review_reply()
    )
    result = run.cascade(second_review=True)

    assert provider.replies == [] and provider.reviewer_calls == 2
    verdict = result.review_verdict
    assert verdict.verdict == "ACCEPT" and verdict.findings == ()
    first = [r for r in verdict.unit_reviews if not r.get("sample")]
    second = [r for r in verdict.unit_reviews if r.get("sample") == "audit_packet"]
    assert [r["unit"] for r in first] == ["u1"] and [r["unit"] for r in second] == ["s2-u1"]
    assert first[0]["request_sha256"] != second[0]["request_sha256"]  # a different packet, a fresh request
    assert run.verdict_file() == verdict


def test_a_rejected_candidate_is_never_sampled_a_second_time(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None, capsys: pytest.CaptureFixture[str]
) -> None:
    # production REJECT -> the degrade -> production ACCEPT -> the second sample (once)
    provider = Replies(
        monkeypatch,
        *_authored_with_hub(f"The widget class renders. {GPU}"),
        review_reply("REJECT_PRESENTATION", claim_finding(HUB_LINE)),
        review_reply(),
        review_reply(),
    )
    result = run.cascade(review_repair_rounds=0, second_review=True)

    assert provider.replies == [] and provider.reviewer_calls == 3
    assert result.review_verdict.verdict == "ACCEPT"
    assert capsys.readouterr().err.count("second review sample (audit packet) start") == 1


def test_a_finding_of_the_second_sample_on_a_line_the_renderer_printed_is_not_counted(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    # line 1 is the title: the audit packet shows it, the production review never reads it and no
    # repair or degrade can change what the renderer printed
    provider = Replies(
        monkeypatch,
        *_authored_with_hub(f"The widget class renders. {GPU}"),
        review_reply(),
        review_reply("REJECT_PRESENTATION", claim_finding(1, section="opening")),
    )
    result = run.cascade(review_repair_rounds=0, second_review=True)

    assert provider.replies == [] and provider.reviewer_calls == 2
    assert result.review_verdict.verdict == "ACCEPT" and result.review_verdict.findings == ()
    assert GPU in (run.out / "README.coherent.md").read_text(encoding="utf-8")


def test_a_blocking_finding_of_the_second_sample_on_authored_text_is_withheld_by_the_degrade(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None, capsys: pytest.CaptureFixture[str]
) -> None:
    # production sample ACCEPT; the audit-packet sample flags the GPU sentence; the degrade withholds it;
    # both samples then accept the degraded candidate
    provider = Replies(
        monkeypatch,
        *_authored_with_hub(f"The widget class renders. {GPU}"),
        review_reply(),
        review_reply("REJECT_PRESENTATION", claim_finding(HUB_LINE)),
        review_reply(),
        review_reply(),
    )
    result = run.cascade(review_repair_rounds=0, second_review=True)

    assert provider.replies == []
    assert provider.reviewer_calls == 4
    readme = (run.out / "README.coherent.md").read_text(encoding="utf-8")
    assert GPU not in readme and "### Widget" in readme
    units = json.loads((run.out / "content_units.coherent.json").read_text(encoding="utf-8"))
    assert [r["rule"] for r in units["degrade_records"]] == ["BL-240"]
    verdict = result.review_verdict
    assert verdict.verdict == "ACCEPT"
    assert [r["unit"] for r in verdict.unit_reviews if r.get("sample")] == ["s2-u1"]
    err = capsys.readouterr().err
    assert "S10 second review sample (audit packet) start" in err
    assert "S10 second review sample end: REJECT" in err


def test_a_repeat_of_the_audit_packet_is_the_stores_replay_not_a_fresh_sample(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    """Why there is exactly one second sample: the call store replays an identical request (the no-re-roll
    rule), so a second cascade over the same bytes asks the provider for nothing."""
    first = Replies(
        monkeypatch, *_authored_with_hub(f"The widget class renders. {GPU}"), review_reply(), review_reply()
    )
    run.cascade(second_review=True)
    assert first.reviewer_calls == 2

    again = Replies(monkeypatch)  # no replies left: any provider call would raise
    result = run.cascade(second_review=True)
    assert again.payloads == [] and result.review_verdict.verdict == "ACCEPT"
