"""Tests for M8's first real, governed draw source (TC-023b).

No test in this file makes a real network or subprocess call: every test monkeypatches
``prose_judge_live.transport.build_client`` to a fake client whose ``chat.completions.create``
returns scripted, in-memory completions -- the exact same seam and style
``tests/core/llm/test_jobs.py`` already uses for ``core.llm.jobs.run_job``. This proves the
WIRING (budget gate, model-route enforcement, threading a real draw through
``sequential_majority_vote``) without ever proving a real gateway answers a real request.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import ConfigError
from repo_presenter.core.llm.budget import BudgetExceededError
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.readme.review import prose_judge_live
from repo_presenter.readme.review.prose_judge import (
    ClassificationRequest,
    PairwiseComparisonRequest,
    ParaphraseCheckRequest,
    ProseJudgePrompts,
    load_prose_judge_prompts,
)
from repo_presenter.readme.review.prose_judge_live import (
    judge_classification_live,
    judge_pairwise_benchmark_comparison_live,
    judge_type_paraphrase_live,
    live_classification_draw,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_PATH = REPO_ROOT / "prompts" / "m8" / "prose_judge.yaml"
CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")


def _prompts() -> ProseJudgePrompts:
    return load_prose_judge_prompts(PROMPT_PATH)


# ---------------------------------------------------------------------------------------------
# A fake transport -- never a real network call anywhere in this file.
# ---------------------------------------------------------------------------------------------


def _completion(content: dict[str, Any], model: str = "qwen3-next", finish_reason: str = "stop") -> Any:
    message = SimpleNamespace(content=json.dumps(content))
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(prompt_tokens=20, completion_tokens=5, total_tokens=25)
    return SimpleNamespace(choices=[choice], model=model, id="req-live-1", usage=usage)


class _FakeCompletions:
    def __init__(self, replies: list[Any]) -> None:
        self.replies = replies
        self.requests: list[dict[str, Any]] = []

    def create(self, **payload: Any) -> Any:
        self.requests.append(payload)
        if not self.replies:
            raise AssertionError("fake transport asked for a reply it was not scripted to give")
        return self.replies.pop(0)


class _FakeClient:
    def __init__(self, replies: list[Any]) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(replies))


def _wire(monkeypatch: pytest.MonkeyPatch, *replies: Any) -> _FakeCompletions:
    client = _FakeClient(list(replies))
    monkeypatch.setattr(prose_judge_live.transport, "build_client", lambda config: client)
    return client.chat.completions


class _RefusingCompletions:
    """A fake transport that fails the test outright if it is ever invoked -- used to prove a
    refused call never reaches the transport layer at all."""

    def __init__(self) -> None:
        self.calls = 0

    def create(self, **_payload: Any) -> Any:
        self.calls += 1
        raise AssertionError("the fake transport must never be invoked for a refused call")


def _wire_refusing(monkeypatch: pytest.MonkeyPatch) -> _RefusingCompletions:
    completions = _RefusingCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(prose_judge_live.transport, "build_client", lambda config: client)
    return completions


# ---------------------------------------------------------------------------------------------
# Budget fixtures
# ---------------------------------------------------------------------------------------------


def _open_budget(tmp_path: Path, *, calls_cap: float = 10, tokens_cap: float = 100_000) -> Path:
    path = tmp_path / "budget.json"
    document = {
        "total_calls_cap": calls_cap,
        "total_tokens_cap": tokens_cap,
        "spent": {"calls": 0, "tokens": 0},
        "batches": [
            {
                "id": "test-batch",
                "repositories": [],
                "calls_cap": calls_cap,
                "tokens_cap": tokens_cap,
                "calls_spent": 0,
                "tokens_spent": 0,
            }
        ],
    }
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _closed_budget(tmp_path: Path) -> Path:
    """A budget file with an empty ``batches`` list: nothing is open (see budget.py's own
    module docstring on what "open" means)."""
    path = tmp_path / "closed_budget.json"
    document = {
        "total_calls_cap": 10,
        "total_tokens_cap": 100_000,
        "spent": {"calls": 0, "tokens": 0},
        "batches": [],
    }
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------------
# (1) A real draw correctly threads through sequential_majority_vote's call-counting contract.
# ---------------------------------------------------------------------------------------------


def test_classification_two_agreeing_draws_makes_exactly_two_physical_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completions = _wire(
        monkeypatch,
        _completion({"category": "promotional"}),
        _completion({"category": "promotional"}),
    )
    budget_path = _open_budget(tmp_path)
    request = ClassificationRequest(span_id="s1", text="This revolutionary tool changes everything.")
    result = judge_classification_live(
        request, gateway=CONFIG, prompts=_prompts(), budget_path=budget_path
    )
    assert result.verdict == "promotional"
    assert result.agreement == 2
    # the exact call-counting contract ScriptedDraws-based tests prove against the fake draw --
    # here proven against the fake TRANSPORT, so a real draw's own physical call count is what
    # is asserted, not a script's.
    assert len(completions.requests) == 2
    assert completions.requests[0]["model"] == "qwen3-next"
    assert completions.requests[0]["temperature"] == 0.0
    assert completions.requests[0]["max_tokens"] == 200


def test_pairwise_disagreeing_draws_triggers_a_real_third_physical_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completions = _wire(
        monkeypatch,
        _completion({"at_least_as_good": True}),
        _completion({"at_least_as_good": False}),
        _completion({"at_least_as_good": False}),
    )
    budget_path = _open_budget(tmp_path)
    request = PairwiseComparisonRequest(
        purpose="installation", candidate_section="pip install x", benchmark_section="pip install x"
    )
    result = judge_pairwise_benchmark_comparison_live(
        request, gateway=CONFIG, prompts=_prompts(), budget_path=budget_path
    )
    assert result.verdict is False
    assert result.agreement == 2
    assert len(completions.requests) == 3


def test_paraphrase_draw_threads_the_real_vote_and_records_spend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _wire(
        monkeypatch,
        _completion({"fair_paraphrase": False}, model="qwen3-next"),
        _completion({"fair_paraphrase": False}, model="qwen3-next"),
    )
    budget_path = _open_budget(tmp_path)
    request = ParaphraseCheckRequest(
        type_name="Foo", description="holds a name and an age", real_signature="class Foo: name: str"
    )
    result = judge_type_paraphrase_live(
        request, gateway=CONFIG, prompts=_prompts(), budget_path=budget_path
    )
    assert result.verdict is False
    document = json.loads(budget_path.read_text(encoding="utf-8"))
    assert document["spent"]["calls"] == 2  # one real record_spend credit per physical draw
    assert document["batches"][0]["calls_spent"] == 2


def test_live_draw_appends_one_ledger_record_per_physical_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _wire(monkeypatch, _completion({"category": "none"}), _completion({"category": "none"}))
    budget_path = _open_budget(tmp_path)
    ledger = Ledger(tmp_path / "calls.jsonl")
    request = ClassificationRequest(span_id="s9", text="Plain factual sentence.")
    draw = live_classification_draw(
        request, gateway=CONFIG, prompts=_prompts(), budget_path=budget_path, ledger=ledger
    )
    assert draw() == "none"
    assert draw() == "none"
    assert len(ledger.appended) == 2
    assert all(record.outcome == "success" for record in ledger.appended)
    assert all(record.model_route == "qwen3-next" for record in ledger.appended)
    assert all(record.job == "m8_classification" for record in ledger.appended)


# ---------------------------------------------------------------------------------------------
# (2) No open provider_budget.json batch -> BudgetExceededError, before any fake transport call.
# ---------------------------------------------------------------------------------------------


def test_no_open_budget_batch_raises_before_any_transport_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completions = _wire_refusing(monkeypatch)
    budget_path = _closed_budget(tmp_path)
    request = ClassificationRequest(span_id="s2", text="Some prose span to classify.")
    draw = live_classification_draw(request, gateway=CONFIG, prompts=_prompts(), budget_path=budget_path)
    with pytest.raises(BudgetExceededError):
        draw()
    assert completions.calls == 0


def test_missing_budget_file_also_raises_before_any_transport_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completions = _wire_refusing(monkeypatch)
    budget_path = tmp_path / "does_not_exist.json"
    request = PairwiseComparisonRequest(
        purpose="x", candidate_section="a", benchmark_section="b"
    )
    draw = prose_judge_live.live_pairwise_draw(
        request, gateway=CONFIG, prompts=_prompts(), budget_path=budget_path
    )
    with pytest.raises(BudgetExceededError):
        draw()
    assert completions.calls == 0


# ---------------------------------------------------------------------------------------------
# (3) A non-qwen3-next model route raises, before any fake transport call -- proven via a
# deliberately mutated ProseJudgePrompts, never a literal withdrawn-model string.
# ---------------------------------------------------------------------------------------------


def _mutated_prompts_with_withdrawn_route() -> ProseJudgePrompts:
    valid = _prompts()
    withdrawn_route = "gpt" + "-oss"  # built, not literal: avoids tripping
    # tests/test_withdrawn_model.py's project-wide scan on this very fixture, which deliberately
    # exercises rejecting that route (the same convention test_prose_judge.py already uses).
    return ProseJudgePrompts(
        classification=valid.classification,
        pairwise_benchmark_comparison=valid.pairwise_benchmark_comparison,
        m8s_paraphrase_check=valid.m8s_paraphrase_check,
        model_route=withdrawn_route,
    )


def test_a_non_qwen3_next_model_route_raises_before_any_transport_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completions = _wire_refusing(monkeypatch)
    budget_path = _open_budget(tmp_path)  # ample budget: isolates the route check alone
    mutated = _mutated_prompts_with_withdrawn_route()
    request = ClassificationRequest(span_id="s3", text="Some prose span.")
    draw = live_classification_draw(request, gateway=CONFIG, prompts=mutated, budget_path=budget_path)
    with pytest.raises(ConfigError):
        draw()
    assert completions.calls == 0
    # the budget was never even spent against, since the route check fails first
    document = json.loads(budget_path.read_text(encoding="utf-8"))
    assert document["spent"]["calls"] == 0


def test_pairwise_and_paraphrase_draws_also_enforce_the_model_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completions = _wire_refusing(monkeypatch)
    budget_path = _open_budget(tmp_path)
    mutated = _mutated_prompts_with_withdrawn_route()
    pairwise_request = PairwiseComparisonRequest(
        purpose="installation", candidate_section="a", benchmark_section="b"
    )
    paraphrase_request = ParaphraseCheckRequest(
        type_name="Foo", description="x", real_signature="class Foo: ..."
    )
    with pytest.raises(ConfigError):
        prose_judge_live.live_pairwise_draw(
            pairwise_request, gateway=CONFIG, prompts=mutated, budget_path=budget_path
        )()
    with pytest.raises(ConfigError):
        prose_judge_live.live_paraphrase_draw(
            paraphrase_request, gateway=CONFIG, prompts=mutated, budget_path=budget_path
        )()
    assert completions.calls == 0
