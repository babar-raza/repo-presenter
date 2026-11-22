"""Owner decision 2026-11-22: issue writes are authorised for the sandbox (`babar-raza/repo-presenter`) only, enforced
in code by the same variable that selects the propose sandbox (`REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY`). The
conftest of this package lifts the scope for the lifecycle tests; every test here runs the REAL scope."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest
from support import make_permit

from repo_presenter import sandbox_scope
from repo_presenter.github.token_provenance import TokenDecision
from repo_presenter.issues import monitor
from repo_presenter.issues.close import CloseRefusal, _remote_gates
from repo_presenter.issues.file import (
    AUTHORIZATION_VARIABLE,
    LEGACY_AUTHORIZATION_VARIABLE,
)
from repo_presenter.issues.file import file_handoff as _file_handoff
from repo_presenter.issues.pilot import PilotEntry

from .factory import _handoff
from .test_close_remote import filed, remote

SANDBOX = "babar-raza/repo-presenter"
UPSTREAM = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"
VAR = sandbox_scope.SANDBOX_VARIABLE
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
PILOT = PilotEntry(
    repository=UPSTREAM, effects=frozenset({"issue", "issue_comment"}), mode="live", bot_login="repository-presenter[bot]",
    recheck_comment_interval_days=7, unchanged_revision_comment_interval_days=30,
)


class Create:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return 201, {"number": 9, "html_url": "https://x/issues/9"}


@pytest.mark.parametrize("repository", [SANDBOX, SANDBOX.upper()])
def test_the_sandbox_the_variable_names_is_the_only_cleared_repository(repository: str) -> None:
    assert sandbox_scope.issue_write_refusal(repository, {VAR: SANDBOX}) is None


@pytest.mark.parametrize("environment", [{}, {VAR: ""}, {VAR: "*"}, {VAR: UPSTREAM}, {VAR: "babar-raza/other"}])
def test_an_upstream_repository_is_never_cleared_whatever_the_variable_says(environment: dict[str, str]) -> None:
    for repository in (UPSTREAM, "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"):
        assert sandbox_scope.issue_write_refusal(repository, environment) is not None


def test_the_wildcard_and_an_unset_variable_clear_nothing_not_even_the_sandbox() -> None:
    assert sandbox_scope.issue_write_refusal(SANDBOX, {VAR: "*"}) is not None
    assert sandbox_scope.issue_write_refusal(SANDBOX, {}) is not None


def test_filing_to_an_upstream_repository_is_refused_with_every_other_gate_open_and_makes_no_call() -> None:
    handoff = _handoff(repository=UPSTREAM)
    create = Create()
    for name in (AUTHORIZATION_VARIABLE, LEGACY_AUTHORIZATION_VARIABLE):
        result = _file_handoff(handoff, token="ghs_w", environment={name: "1", VAR: SANDBOX}, create=create,
                               permit=make_permit(UPSTREAM, effect="issue_filing"), verify_token=lambda t: TokenDecision(True, t))
        assert result.filed is False and result.authorized is False and "sandbox only" in result.reason
    assert create.calls == []


def test_filing_to_the_sandbox_passes_the_scope_gate_and_reaches_the_next_gate() -> None:
    handoff = _handoff(repository=SANDBOX)
    result = _file_handoff(handoff, token=None, environment={LEGACY_AUTHORIZATION_VARIABLE: "1", VAR: SANDBOX},
                           permit=make_permit(SANDBOX, effect="issue_filing"), verify_token=lambda t: TokenDecision(True, t))
    assert "sandbox only" not in result.reason and result.authorized is True  # refused later: no token


def test_a_remote_close_on_an_upstream_repository_is_refused_before_any_write() -> None:
    h = filed(UPSTREAM)
    with pytest.raises(CloseRefusal, match="sandbox only"):
        _remote_gates(h, "completed", remote(h, env={LEGACY_AUTHORIZATION_VARIABLE: "1", VAR: SANDBOX}))


def test_a_remote_close_on_the_sandbox_passes_the_scope_gate() -> None:
    h = filed(SANDBOX)
    assert _remote_gates(h, "completed", remote(h, env={LEGACY_AUTHORIZATION_VARIABLE: "1", VAR: SANDBOX})) == (None, None)


def test_the_maintenance_cycle_stays_a_dry_run_for_an_upstream_pilot_even_when_everything_else_is_open() -> None:
    doc = {"dry_run_cycles": 3}
    token = TokenDecision(True, "ghs_x")
    open_env = {LEGACY_AUTHORIZATION_VARIABLE: "1", VAR: SANDBOX}
    blockers = monitor.live_blockers(replace(PILOT, mode="live"), doc, open_env, token)
    assert len(blockers) == 1 and "sandbox only" in blockers[0]
    sandbox_pilot = replace(PILOT, repository=SANDBOX)
    assert monitor.live_blockers(sandbox_pilot, doc, open_env, token) == []
    assert any("sandbox only" in b for b in monitor.live_blockers(sandbox_pilot, doc, {LEGACY_AUTHORIZATION_VARIABLE: "1"}, token))


def test_the_issues_workflow_hands_the_variable_to_the_maintain_step() -> None:
    from pathlib import Path

    text = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "issues.yml").read_text(encoding="utf-8")
    assert "REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY: ${{ vars.REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY }}" in text
