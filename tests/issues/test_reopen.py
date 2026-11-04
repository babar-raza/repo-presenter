"""Stage 9 (REOPEN ON RECURRENCE): a closed upstream issue whose defect is re-detected is
REOPENED (never re-filed, never silently deduplicated), behind exactly the filing gates."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from support import make_permit

from repo_presenter.github.client import CreatedIssue
from repo_presenter.github.token_provenance import TokenDecision
from repo_presenter.issues import file as file_mod
from repo_presenter.issues.approval import evidence_digest, handoff_id
from repo_presenter.issues.file import AUTHORIZATION_VARIABLE, file_handoff, plan_filing

from .factory import REPO, _handoff

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
ENV = {AUTHORIZATION_VARIABLE: "1"}
CLOSED = CreatedIssue(number=7, url=f"https://github.com/{REPO}/issues/7", state="closed")
OPEN = CreatedIssue(number=7, url=f"https://github.com/{REPO}/issues/7", state="open")


class _Store:
    def __init__(self, handoff: Any, *, approve: bool = True) -> None:
        rec = {
            "handoff_id": handoff_id(handoff), "repository": handoff.repository,
            "evidence_digest": evidence_digest(handoff), "approver": "owner-login",
            "approved_at": (NOW - timedelta(hours=1)).isoformat(),
            "expires_at": (NOW + timedelta(days=6)).isoformat(),
        }
        self.records = {handoff_id(handoff): json.dumps(rec)} if approve else {}

    def read(self, identifier: str) -> str | None:
        return self.records.get(identifier)


class _W:
    def __init__(self, status: int = 200) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status = status

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status, {"number": 7, "html_url": "u"}


class _Recheck:
    def __init__(self, still_fires: bool | None = True) -> None:
        self.still_fires, self.note = still_fires, "n"


def _run(handoff=None, *, found=CLOSED, approve=True, env=ENV, token="w", recheck=None, **kw):
    handoff = handoff or _handoff()
    w = {"create": _W(201), "comment": _W(201), "patch": _W(200)}
    result = file_handoff(
        handoff, token=token, environment=env, approvals=_Store(handoff, approve=approve),
        permit=kw.pop("permit", make_permit(handoff.repository, effect="issue_filing")),
        verify_token=lambda t: TokenDecision(True, t), now=lambda: NOW,
        existing=lambda: found, recheck=recheck, **w, **kw,
    )
    return result, w


def _plan(found, **kw):
    h = _handoff()
    return plan_filing(h, existing=lambda: found, approvals=_Store(h), now=lambda: NOW, **kw)


def test_still_open_issue_is_deduplicated_only():
    plan = _plan(OPEN)
    assert plan.already_filed is not None and plan.reopen is None
    assert plan.action == "DEDUP"
    result, w = _run(found=OPEN)
    assert result.reopened is False and result.issue_ref.number == 7
    assert not any(x.calls for x in w.values())


def test_closed_issue_plans_a_reopen_not_a_new_issue_nor_a_silent_dedup():
    plan = _plan(CLOSED)
    assert plan.action == "REOPEN"
    assert plan.reopen is not None and plan.reopen.number == 7
    assert plan.already_filed is None and plan.ready is False and plan.refusal is None


def test_a_plain_issue_ref_without_state_is_treated_as_open():
    from repo_presenter.issues.model import IssueRef

    assert _plan(IssueRef(7, "u")).action == "DEDUP"


def test_closed_with_defect_no_longer_firing_is_refused_not_reopened():
    plan = _plan(CLOSED, recheck=lambda: _Recheck(False))
    assert plan.action == "REFUSED" and "no longer fires" in plan.refusal
    plan = _plan(CLOSED, recheck=lambda: _Recheck(None))
    assert plan.action == "REFUSED"


def test_authorized_recurrence_comments_then_reopens_and_creates_nothing():
    result, w = _run(recheck=lambda: _Recheck(True))
    assert result.reopened is True and result.filed is False and not result.error
    assert result.issue_ref.number == 7
    assert w["create"].calls == []
    assert [c[0].rsplit("/", 2)[-2:] for c in w["comment"].calls] == [["7", "comments"]]
    assert "recurrence" in w["comment"].calls[0][2]["body"].lower()
    assert w["patch"].calls[0][0] == "https://api.github.com/repos/babar-raza/repo-presenter/issues/7"
    assert w["patch"].calls[0][2] == {"state": "open", "state_reason": "reopened"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"env": {}},                      # kill switch off
        {"env": {AUTHORIZATION_VARIABLE: "0"}},
        {"token": ""},                    # no token
        {"approve": False},               # no approval record
        {"expected_repository": "x/y"},   # target mismatch
    ],
)
def test_reopen_refused_without_authorization_makes_no_write(kwargs):
    result, w = _run(**kwargs)
    assert result.reopened is False
    assert not any(x.calls for x in w.values())


def test_reopen_refused_with_a_rejected_token_or_wrong_permit():
    h = _handoff()
    w = {"create": _W(201), "comment": _W(201), "patch": _W(200)}
    result = file_handoff(
        h, token="w", environment=ENV, approvals=_Store(h), now=lambda: NOW,
        permit=make_permit(h.repository, effect="issue_filing"),
        verify_token=lambda t: TokenDecision(False, t, code="X", reason="bad"),
        existing=lambda: CLOSED, **w,
    )
    assert result.reopened is False and not any(x.calls for x in w.values())
    with pytest.raises(ValueError):
        file_handoff(
            h, token="w", environment=ENV, approvals=_Store(h), now=lambda: NOW,
            permit=make_permit(h.repository, effect="issue_close"),
            verify_token=lambda t: TokenDecision(True, t), existing=lambda: CLOSED, **w,
        )
    assert not any(x.calls for x in w.values())


def test_reopen_against_a_repository_other_than_ours_never_reaches_the_writer():
    """The handoff targets an external repo and every gate is open: the guarded client
    primitive still refuses before the injected writer is called."""
    result, w = _run(_handoff(repository="aspose-3d-foss/Aspose.3D-FOSS-for-Python"))
    assert result.error is True and result.reopened is False
    assert w["comment"].calls == [] and w["patch"].calls == []


def test_labels_are_sent_on_create_but_never_changed_on_reopen():
    h = _handoff()
    result, w = _run(h, found=None)
    assert result.filed is True
    assert w["create"].calls[0][2]["labels"] == ["repo-presenter", "defect:example_fails"]
    assert "assignees" not in w["create"].calls[0][2]
    result, w = _run(h, found=CLOSED)
    assert result.reopened is True
    assert set(w["patch"].calls[0][2]) == {"state", "state_reason"}


def test_module_exposes_the_plain_gates():
    assert file_mod.write_authorized(ENV)
