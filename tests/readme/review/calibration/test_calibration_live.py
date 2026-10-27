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


def completion(content: Any, model: str = "gpt-oss") -> Any:
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


def reject_reply(quote: str = QUOTE) -> dict[str, Any]:
    finding = {
        "id": "F01",
        "section_id": "key_capabilities",
        "causal_stage": "S6",
        "criterion": "presentation",
        "claim_kind": "quality",
        "text": "reads badly",
        "quote": quote,
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
        outcome.model_served == "gpt-oss"
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
            completion(reject_reply("a sentence the candidate never contains")),
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
    assert len(run.results) == 4 and "cap is 4" in run.stopped
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
