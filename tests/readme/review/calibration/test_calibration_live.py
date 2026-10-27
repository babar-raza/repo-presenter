"""The live adapter, driven by a scripted client: counting, the hard cap, cache bypass, outcomes."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.review.calibration.corpus import Base, build_corpus
from repo_presenter.readme.review.calibration.harness import (
    ACCEPT,
    REJECT,
    UNAVAILABLE,
    BudgetExhausted,
    compute_metrics,
    run_corpus,
)
from repo_presenter.readme.review.calibration.reviewers import (
    LiveReviewer,
    physical_calls,
)
from tests.readme.review.calibration.synthetic import make_source

PROMPTS = load_manifests(Path(__file__).resolve().parents[4] / "prompts")
CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")
QUOTE = "- **Export SVG.** It exports vector output to `.svg` through `SvgExporter`."
QUOTE_LINE = 8  # the line of the synthetic candidate that holds QUOTE


def completion(content: Any, model: str = "qwen3-next") -> Any:
    text = content if isinstance(content, str) else json.dumps(content)
    choice = SimpleNamespace(
        message=SimpleNamespace(content=text), finish_reason="stop"
    )
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], model=model, id="req", usage=usage)


class ScriptedClient:
    def __init__(self, replies: list[Any]) -> None:
        self.replies = list(replies)
        self.requests = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **payload: Any) -> Any:
        self.requests += 1
        return self.replies.pop(0)


def install(monkeypatch: pytest.MonkeyPatch, replies: list[Any]) -> ScriptedClient:
    client = ScriptedClient(replies)
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    return client


ACCEPT_REPLY = {"verdict": "ACCEPT", "findings": [], "preserve": []}


def reject_reply(lines: list[int] | None = None) -> dict[str, Any]:
    finding = {
        "id": "F01",
        "section_id": "key_capabilities",
        "causal_stage": "S6",
        "criterion": "presentation",
        "claim_kind": "quality",
        "text": "reads badly",
        "lines": [QUOTE_LINE] if lines is None else lines,
        "fact_ids": [],
        "repair": "reword",
    }
    return {"verdict": "REJECT_PRESENTATION", "findings": [finding], "preserve": []}


@pytest.fixture
def clean(tmp_path):
    return next(
        c for c in build_corpus([Base(make_source(tmp_path))]) if c.role == "clean"
    )


def reviewer(tmp_path: Path, cap: int = 10, store: str = "s") -> LiveReviewer:
    return LiveReviewer(
        prompts=PROMPTS,
        config=CONFIG,
        ledger_path=tmp_path / "ledger.jsonl",
        store_dir=tmp_path / store,
        cap=cap,
    )


def test_an_accept_is_one_counted_call_with_a_valid_first_reply(
    tmp_path, clean, monkeypatch
):
    client = install(monkeypatch, [completion(ACCEPT_REPLY)])
    outcome = reviewer(tmp_path)(clean)
    assert outcome.verdict == ACCEPT and outcome.calls == 1 and client.requests == 1
    assert outcome.first_reply_json_valid and outcome.first_reply_contract_valid
    assert (
        outcome.model_served == "qwen3-next"
        and physical_calls(tmp_path / "ledger.jsonl") == 1
    )


def test_a_blocking_finding_is_a_reject_with_its_claim_kind(
    tmp_path, clean, monkeypatch
):
    install(monkeypatch, [completion(reject_reply())])
    outcome = reviewer(tmp_path)(clean)
    assert outcome.verdict == REJECT and outcome.blocking_kinds == ("quality",)


def test_a_contract_breaking_first_reply_is_re_asked_and_flagged(
    tmp_path, clean, monkeypatch
):
    client = install(
        monkeypatch,
        [
            completion(reject_reply([9999])),
            completion(ACCEPT_REPLY),
        ],
    )
    outcome = reviewer(tmp_path)(clean)
    assert outcome.verdict == ACCEPT and outcome.calls == 2 and client.requests == 2
    assert (
        outcome.first_reply_json_valid is True
        and outcome.first_reply_contract_valid is False
    )


def test_two_unparseable_replies_are_unavailable_never_accept(
    tmp_path, clean, monkeypatch
):
    install(monkeypatch, [completion(""), completion("")])
    outcome = reviewer(tmp_path)(clean)
    assert outcome.verdict == UNAVAILABLE and outcome.calls == 2
    assert outcome.first_reply_json_valid is False and "re-ask" in outcome.detail


def test_the_cap_is_enforced_inside_a_review_and_across_reviewers(
    tmp_path, clean, monkeypatch
):
    install(monkeypatch, [completion(reject_reply("not in the candidate"))] * 2)
    with pytest.raises(BudgetExhausted):
        reviewer(tmp_path, cap=1)(clean)
    assert (
        physical_calls(tmp_path / "ledger.jsonl") == 1
    )  # the second call was refused unsent
    with pytest.raises(BudgetExhausted, match="cap is 1"):
        reviewer(tmp_path, cap=1, store="other")(clean)


def test_the_same_store_replays_for_free_and_a_fresh_store_asks_again(
    tmp_path, clean, monkeypatch
):
    client = install(monkeypatch, [completion(ACCEPT_REPLY), completion(ACCEPT_REPLY)])
    first = reviewer(tmp_path)(clean)
    replay = reviewer(tmp_path)(clean)
    assert (first.calls, replay.calls) == (1, 0) and client.requests == 1
    assert replay.first_reply_json_valid is None  # no reply was sent
    fresh = reviewer(tmp_path, store="fresh")(clean)
    assert fresh.calls == 1 and client.requests == 2


def test_the_harness_counts_the_live_calls_and_stops_at_the_cap(tmp_path, monkeypatch):
    cases = build_corpus([Base(make_source(tmp_path))])
    install(monkeypatch, [completion(ACCEPT_REPLY)] * len(cases))
    run = run_corpus(cases, reviewer(tmp_path, cap=4))
    # a case whose reviewable text equals an earlier case's (a mutant of renderer-printed text such
    # as the install line) is the same request: it replays for free and costs no call
    assert len(run.results) >= 4 and "cap is 4" in run.stopped
    metrics = compute_metrics(run)
    assert metrics.calls == 4 == physical_calls(tmp_path / "ledger.jsonl")


def test_a_fresh_store_per_call_makes_every_repeat_a_real_call(
    tmp_path, clean, monkeypatch
):
    client = install(monkeypatch, [completion(ACCEPT_REPLY)] * 3)
    live = LiveReviewer(
        prompts=PROMPTS,
        config=CONFIG,
        ledger_path=tmp_path / "ledger.jsonl",
        store_dir=tmp_path / "s",
        cap=10,
        fresh_store_per_call=True,
    )
    run = run_corpus([clean], live, repeats=3)
    assert [o.calls for o in run.results[0].outcomes] == [
        1,
        1,
        1,
    ] and client.requests == 3
    assert compute_metrics(run).stability == 1.0


def test_a_sectionwise_review_counts_first_replies_per_unit_and_sums_tokens(
    tmp_path, clean, monkeypatch
):
    from functools import partial

    from repo_presenter.readme.review import llm_review
    from repo_presenter.readme.review.sectionwise import plan_units

    monkeypatch.setattr(llm_review, "plan_units", partial(plan_units, max_chars=150))
    units = plan_units(clean.readme, max_chars=150)
    assert len(units) >= 3
    # unit 1 answers cleanly; unit 2's first reply is not JSON and its re-ask is; unit 3 cites a
    # line it was not shown, then answers; the rest answer cleanly
    replies = [
        completion(ACCEPT_REPLY),
        completion("not json"),
        completion(ACCEPT_REPLY),
        completion(reject_reply([1])),
        completion(ACCEPT_REPLY),
        *[completion(ACCEPT_REPLY)] * (len(units) - 3),
    ]
    client = install(monkeypatch, replies)
    outcome = reviewer(tmp_path)(clean)
    assert outcome.verdict == ACCEPT and outcome.units == len(units)
    assert outcome.calls == len(units) + 2 == client.requests
    assert outcome.unit_replies == len(units)
    assert outcome.unit_json_valid == len(units) - 1  # the "not json" unit
    assert (
        outcome.unit_contract_valid == len(units) - 2
    )  # that one and the unseen-line unit
    assert (
        outcome.first_reply_json_valid is False
        and outcome.first_reply_contract_valid is False
    )
    assert outcome.tokens == 15 * outcome.calls
    metrics = compute_metrics(run_corpus([clean], lambda case: outcome))
    assert (
        metrics.first_replies == len(units)
        and metrics.first_reply_json_valid == len(units) - 1
    )
    assert metrics.first_reply_contract_valid == len(units) - 2
    assert metrics.tokens == outcome.tokens and metrics.units == len(units)
