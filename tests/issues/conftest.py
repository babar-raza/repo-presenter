"""The owner's 'sandbox only' scope for issue writes (2026-11-22, ``sandbox_scope.issue_write_refusal``) is
tested for real in ``test_sandbox_scope.py`` (mark ``real_sandbox_scope``). Every other issue test exercises the
lifecycle mechanics on stand-in repositories, so the scope is lifted for them here: it would otherwise refuse
every stand-in target before the gate each test is about."""

from __future__ import annotations

import pytest

from repo_presenter import sandbox_scope


@pytest.fixture(autouse=True)
def _issue_scope_lifted(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("real_sandbox_scope") is None and request.module.__name__.rsplit(".", 1)[-1] != "test_sandbox_scope":
        monkeypatch.setattr(sandbox_scope, "issue_write_refusal", lambda repository, environment: None)
