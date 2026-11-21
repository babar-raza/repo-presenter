# ruff: noqa: F811, F401
"""BL-530: the audit-packet sample is drawn twice and both draws must be clean.

One draw was not repeatable (a seal clean on its seal-time draw flagged on 2 to 3 of 4 fresh draws of the identical
packet). Draw 1 is the BL-430 request byte for byte (stored call stores replay, no existing seal changes); draw 2 is a
different request (``review_scope.draw``), so the store never replays it. A flag in either draw on authored text is a
blocking finding for the usual repair/degrade machinery. Offline, scripted provider.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter import present
from repo_presenter.readme.review.llm_review import merge_second_sample, planned_requests
from repo_presenter.readme.review.verdict import ReviewVerdict
from tests.readme.review.review_support import CANDIDATE, FACTS, llm
from tests.readme.review.test_llm_review import CONTEXT, DISPOSITIONS, PLAN, PROMPTS, VALIDATION
from tests.readme.review.test_second_sample_bl430 import EXPORTS, _sample
from tests.test_cascade_s10 import (
    GPU,
    HUB_LINE,
    Replies,
    Run,
    _authored_with_hub,
    claim_finding,
    clean_gates,
    review_reply,
)
from tests.test_preflight_wiring import LaneRWorld
from tests.test_lane_l_hosted import digest_tree
from tests.test_refresh_bl440 import _current, _stage


@pytest.fixture
def run(tmp_path: Path) -> Run:
    return Run(tmp_path)


@pytest.fixture(autouse=True)
def two_draws(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("repo_presenter.cascade.SECOND_DRAW", True)


def test_the_production_default_is_two_draws() -> None:
    assert re.search(r"^SECOND_DRAW = True$", inspect.getsource(cascade_module), re.MULTILINE)


def test_draw_one_is_the_unchanged_request_and_draw_two_is_a_different_one(tmp_path: Path) -> None:
    base = dict(
        prompts=PROMPTS, context=CONTEXT, candidate_readme=CANDIDATE, original_readme=CANDIDATE,
        facts=FACTS, plan=PLAN, dispositions=DISPOSITIONS, validation=VALIDATION,
    )
    default = planned_requests(**base, rendered=False, audit=True)[2]
    first = planned_requests(**base, rendered=False, audit=True, draw=1)[2]
    second = planned_requests(**base, rendered=False, audit=True, draw=2)[2]
    assert [r.request_sha256 for r in default] == [r.request_sha256 for r in first]
    assert all("draw" not in r.packet["review_scope"] for r in first)
    assert all(r.packet["review_scope"]["draw"] == 2 for r in second)
    assert not set(r.request_sha256 for r in first) & set(r.request_sha256 for r in second)


def test_a_flag_in_the_second_draw_blocks_with_s3_ids_and_records() -> None:
    first = merge_second_sample(_sample(), _sample(), candidate_readme=CANDIDATE, facts=FACTS)
    flagged = llm("unsupported_claim", quote=EXPORTS, section_id="key_capabilities", finding_id="F01")
    union = merge_second_sample(
        first, _sample(flagged, model_verdict="REJECT_FACTUAL"), candidate_readme=CANDIDATE, facts=FACTS, draw=2
    )
    assert union.verdict == "REJECT"
    assert [f.finding_id for f in union.blocking_findings] == ["S3-F01"]
    assert [r["unit"] for r in union.unit_reviews] == ["u1", "s2-u1", "s3-u1"]


def test_two_clean_draws_accept_and_both_are_recorded(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None
) -> None:
    provider = Replies(
        monkeypatch, *_authored_with_hub(f"The widget class renders. {GPU}"),
        review_reply(), review_reply(), review_reply(),
    )
    result = run.cascade(second_review=True)
    assert provider.replies == [] and provider.reviewer_calls == 3
    units = [r["unit"] for r in result.review_verdict.unit_reviews]
    assert units == ["u1", "s2-u1", "s3-u1"] and result.review_verdict.verdict == "ACCEPT"


def test_a_flag_in_only_the_second_draw_is_withheld_by_the_degrade(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = Replies(
        monkeypatch, *_authored_with_hub(f"The widget class renders. {GPU}"),
        review_reply(), review_reply(), review_reply("REJECT_PRESENTATION", claim_finding(HUB_LINE)),
        review_reply(), review_reply(), review_reply(),
    )
    result = run.cascade(review_repair_rounds=0, second_review=True)
    assert provider.replies == [] and provider.reviewer_calls == 6
    readme = (run.out / "README.coherent.md").read_text(encoding="utf-8")
    assert GPU not in readme
    units = json.loads((run.out / "content_units.coherent.json").read_text(encoding="utf-8"))
    assert [r["rule"] for r in units["degrade_records"]] == ["BL-240"]
    assert result.review_verdict.verdict == "ACCEPT"
    assert "S10 second review draw 2 end: REJECT" in capsys.readouterr().err


def test_a_flag_in_the_first_draw_never_starts_the_second(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None, capsys: pytest.CaptureFixture[str]
) -> None:
    Replies(
        monkeypatch, *_authored_with_hub(f"The widget class renders. {GPU}"),
        review_reply(), review_reply("REJECT_PRESENTATION", claim_finding(HUB_LINE)),
        review_reply(), review_reply(), review_reply(),
    )
    run.cascade(review_repair_rounds=0, second_review=True)
    assert capsys.readouterr().err.count("draw 2 (audit packet) start") == 1  # only for the degraded re-review


def test_a_second_draw_is_not_taken_once_the_timebox_has_passed(
    run: Run, monkeypatch: pytest.MonkeyPatch, clean_gates: None, capsys: pytest.CaptureFixture[str]
) -> None:
    ticks = iter(range(0, 10**6, 1))
    provider = Replies(
        monkeypatch, *_authored_with_hub(f"The widget class renders. {GPU}"), review_reply(), review_reply()
    )
    run.cascade(second_review=True, timebox_seconds=5.0, clock=lambda: float(next(ticks)))
    # whichever stage the box ends at, the run finished with a verdict and never needed a third review call
    assert provider.reviewer_calls <= 2


def test_a_refresh_whose_second_draw_flags_keeps_the_old_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = LaneRWorld(tmp_path, monkeypatch)
    bundle = world.seal_proven()
    before, pointer = digest_tree(bundle), _current(world)
    flagged = llm("unsupported_claim", quote=EXPORTS, section_id="key_capabilities", finding_id="F01")
    clean = merge_second_sample(_sample(), _sample(), candidate_readme=CANDIDATE, facts=FACTS)
    verdict = merge_second_sample(
        clean, _sample(flagged, model_verdict="REJECT_FACTUAL"), candidate_readme=CANDIDATE, facts=FACTS, draw=2
    )
    assert verdict.verdict == "REJECT"
    monkeypatch.setattr(
        present, "run_cascade",
        lambda *a, **k: SimpleNamespace(review_verdict=verdict, out_dir=world.root / "work" / "cascade"),
    )
    for name in ("keep_blocking", "report_findings", "report_repairs"):
        monkeypatch.setattr(present, name, lambda *a, **k: None)
    error = _stage(world, refresh=True)
    assert isinstance(error, present.PresentFailure) and "nothing sealed" in str(error)
    assert digest_tree(bundle) == before and _current(world) == pointer
