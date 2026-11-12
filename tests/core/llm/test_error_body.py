"""A gateway error keeps a truncated, redacted body so an HTTP 400 can be told apart (context
overflow vs malformed request) - Words .NET planning, 2026-11-10, was a bare 'HTTP 400'."""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.llm.jobs import _ERROR_BODY_LIMIT, _error_body

CONFIG = GatewayConfig(base_url="https://gw.example/v1", api_key="sk-live-secret-123")


def _exc(text):
    return SimpleNamespace(response=SimpleNamespace(text=text))


def test_the_body_is_appended_whitespace_collapsed() -> None:
    body = '{"error": {"message": "maximum context length is 262144 tokens"}}\n'
    assert _error_body(_exc(body), CONFIG) == ": " + " ".join(body.split())  # type: ignore[arg-type]


def test_the_body_is_truncated_and_the_live_key_redacted() -> None:
    text = "key sk-live-secret-123 " + "x" * 2000
    out = _error_body(_exc(text), CONFIG)  # type: ignore[arg-type]
    assert "sk-live-secret-123" not in out and len(out) <= _ERROR_BODY_LIMIT + len(": ") + 20


def test_an_empty_or_unreadable_body_adds_nothing() -> None:
    assert _error_body(_exc(""), CONFIG) == ""  # type: ignore[arg-type]
    assert _error_body(SimpleNamespace(response=None), CONFIG) == ""  # type: ignore[arg-type]
