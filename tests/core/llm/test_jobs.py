"""The run_job boundary: caching, re-asking, recover, and the ledger -- all hermetic.

Adapted (own test, inspired by the old repository-presenter project's
``tests/core/llm/test_jobs.py``, not a verbatim port -- that file loads real ``prompts/*.yaml``
manifests this repository does not have yet; see core/llm/prompts.py's own module docstring) for
migration/reuse-manifest.yaml's "readme/composition/" entry.

No network call is made anywhere in this file: ``repo_presenter.core.llm.jobs.transport.
build_client`` is monkeypatched to a fake client whose ``chat.completions.create`` returns
scripted, in-memory completions. This proves the caching/re-ask/recover MECHANISM works; it does
not and cannot prove the real ``GPT_OSS_ENDPOINT`` gateway answers a real request (see
core/llm/jobs.py's own module docstring for that finding).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import JobError, OutputRejectedError
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.llm import jobs as jobs_module
from repo_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import (
    LoadedManifest,
    Output,
    Packet,
    PacketField,
    PromptManifest,
    Sampling,
)

CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")
CONTEXT = JobContext("org/repo", "a" * 40)
FACTS = FactsDocument(
    "org/repo",
    "a" * 40,
    (
        Fact("identity:repository", "identity", "org/repo", (Evidence("data/registry.json"),)),
        Fact("package:name", "package", "widget", (Evidence("setup.py"),)),
    ),
)
_SCHEMA = {
    "type": "object",
    "required": ["summary", "fact_ids"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "fact_ids": {"type": "array", "items": {"type": "string"}},
    },
}


def _manifest() -> LoadedManifest:
    manifest = PromptManifest(
        prompt_id="repository_investigation",
        version="1",
        stage="S3",
        purpose="test",
        model_route="qwen3-next",
        route_rationale="test",
        sampling=Sampling(temperature=0.0, max_output_tokens=100, response_format="json_schema"),
        schema_preface="Reply against this schema:",
        rejection_template="Fix: $errors",
        packet=Packet(fields=(PacketField(name="repository", type="string", description="x"),)),
        output=Output(contract="TestV1", binding="fact_ids", schema=_SCHEMA),
        system="You are a test job.",
        user_template="Repository: $repository",
    )
    return LoadedManifest(manifest, Path("test.yaml"), "deadbeef" * 8)


def _completion(content: Any, model: str = "qwen3-next", finish_reason: str = "stop") -> Any:
    message = SimpleNamespace(content=json.dumps(content))
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], model=model, id="req-1", usage=usage)


class _FakeCompletions:
    def __init__(self, replies: list[Any]) -> None:
        self.replies = replies
        self.requests: list[dict[str, Any]] = []

    def create(self, **payload: Any) -> Any:
        self.requests.append(payload)
        return self.replies.pop(0)


class _FakeClient:
    def __init__(self, replies: list[Any]) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(replies))


def _wire(monkeypatch: pytest.MonkeyPatch, *replies: Any) -> _FakeClient:
    client = _FakeClient(list(replies))
    monkeypatch.setattr(jobs_module.transport, "build_client", lambda config: client)
    return client


def _store(tmp_path: Path) -> CallStore:
    return CallStore(tmp_path / "calls")


def _ledger(tmp_path: Path) -> Ledger:
    return Ledger(tmp_path / "calls.jsonl")


def test_a_valid_first_reply_is_accepted_and_stored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _wire(monkeypatch, _completion({"summary": "ok", "fact_ids": ["identity:repository"]}))
    result = run_job(
        _manifest(),
        {"repository": "org/repo"},
        config=CONFIG,
        facts=FACTS,
        ledger=_ledger(tmp_path),
        store=_store(tmp_path),
        context=CONTEXT,
    )
    assert result.output == {"summary": "ok", "fact_ids": ["identity:repository"]}
    assert result.cache_reused is False
    assert result.attempts == 1
    assert len(client.chat.completions.requests) == 1


def test_the_same_request_later_reuses_the_store_with_zero_provider_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, ledger = _store(tmp_path), _ledger(tmp_path)
    _wire(monkeypatch, _completion({"summary": "ok", "fact_ids": []}))
    first = run_job(
        _manifest(), {"repository": "org/repo"}, config=CONFIG, facts=FACTS, ledger=ledger,
        store=store, context=CONTEXT,
    )
    assert first.cache_reused is False
    # A second client that would error if called at all: zero provider calls proves the reuse.
    client = _wire(monkeypatch, _completion({"summary": "should not be used", "fact_ids": []}))
    second = run_job(
        _manifest(), {"repository": "org/repo"}, config=CONFIG, facts=FACTS, ledger=ledger,
        store=store, context=CONTEXT,
    )
    assert second.cache_reused is True
    assert second.output == {"summary": "ok", "fact_ids": []}
    assert second.provider_calls == 0
    assert client.chat.completions.requests == []


def test_an_unknown_fact_id_is_rejected_then_the_reask_fixes_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _wire(
        monkeypatch,
        _completion({"summary": "bad", "fact_ids": ["package:nonexistent"]}),
        _completion({"summary": "good", "fact_ids": ["package:name"]}),
    )
    result = run_job(
        _manifest(), {"repository": "org/repo"}, config=CONFIG, facts=FACTS,
        ledger=_ledger(tmp_path), store=_store(tmp_path), context=CONTEXT,
    )
    assert result.output["fact_ids"] == ["package:name"]
    assert result.attempts == 2


def test_two_rejections_with_no_recover_fails_the_job_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _wire(
        monkeypatch,
        _completion({"summary": "bad", "fact_ids": ["nope:one"]}),
        _completion({"summary": "still bad", "fact_ids": ["nope:two"]}),
    )
    with pytest.raises(OutputRejectedError, match="output rejected twice"):
        run_job(
            _manifest(), {"repository": "org/repo"}, config=CONFIG, facts=FACTS,
            ledger=_ledger(tmp_path), store=_store(tmp_path), context=CONTEXT,
        )


def test_recover_fixes_a_final_rejection_the_model_could_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``recover=`` runs only after the second attempt is still rejected, never on the first."""
    _wire(
        monkeypatch,
        _completion({"summary": "bad", "fact_ids": ["nope:one"]}),
        _completion({"summary": "still bad", "fact_ids": ["nope:two"]}),
    )

    def recover(raw: dict[str, Any]) -> dict[str, Any] | None:
        return {**raw, "fact_ids": ["package:name"]}

    result = run_job(
        _manifest(), {"repository": "org/repo"}, config=CONFIG, facts=FACTS,
        ledger=_ledger(tmp_path), store=_store(tmp_path), context=CONTEXT, recover=recover,
    )
    assert result.output["fact_ids"] == ["package:name"]
    repaired = list((tmp_path / "calls").glob("*.repaired-2.json"))
    assert len(repaired) == 1


def test_recover_is_never_tried_on_the_first_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recover= that would fix attempt 1 is irrelevant: the model's own re-ask is always tried
    first, and here it succeeds, so recover must never even be called."""
    calls: list[Any] = []
    _wire(
        monkeypatch,
        _completion({"summary": "bad", "fact_ids": ["nope:one"]}),
        _completion({"summary": "good", "fact_ids": ["package:name"]}),
    )

    def recover(raw: dict[str, Any]) -> dict[str, Any] | None:
        calls.append(raw)
        return {**raw, "fact_ids": ["package:name"]}

    result = run_job(
        _manifest(), {"repository": "org/repo"}, config=CONFIG, facts=FACTS,
        ledger=_ledger(tmp_path), store=_store(tmp_path), context=CONTEXT, recover=recover,
    )
    assert result.attempts == 2
    assert calls == []


def test_a_truncated_reply_fails_closed_without_a_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _wire(
        monkeypatch, _completion({"summary": "x", "fact_ids": []}, finish_reason="length")
    )
    with pytest.raises(JobError, match="output truncated"):
        run_job(
            _manifest(), {"repository": "org/repo"}, config=CONFIG, facts=FACTS,
            ledger=_ledger(tmp_path), store=_store(tmp_path), context=CONTEXT,
        )
    assert len(client.chat.completions.requests) == 1


def test_checks_can_reject_an_otherwise_schema_valid_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _wire(
        monkeypatch,
        _completion({"summary": "too short", "fact_ids": []}),
        _completion({"summary": "a proper summary now", "fact_ids": []}),
    )

    def checks(output: dict[str, Any]) -> list[str]:
        return [] if len(output["summary"]) > 10 else ["summary is too short"]

    result = run_job(
        _manifest(), {"repository": "org/repo"}, config=CONFIG, facts=FACTS,
        ledger=_ledger(tmp_path), store=_store(tmp_path), context=CONTEXT, checks=checks,
    )
    assert result.output["summary"] == "a proper summary now"


def test_the_ledger_records_every_physical_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _wire(
        monkeypatch,
        _completion({"summary": "bad", "fact_ids": ["nope:one"]}),
        _completion({"summary": "good", "fact_ids": ["package:name"]}),
    )
    ledger = _ledger(tmp_path)
    run_job(
        _manifest(), {"repository": "org/repo"}, config=CONFIG, facts=FACTS, ledger=ledger,
        store=_store(tmp_path), context=CONTEXT,
    )
    records = ledger.records()
    outcomes = [r.outcome for r in records]
    # Attempt 1: the call itself succeeds (HTTP 200), then the parsed output is separately
    # marked rejected; attempt 2: the call succeeds and the output is accepted.
    assert outcomes == ["success", "response_invalid", "success"]
    assert all(r.job == "repository_investigation" for r in records)
