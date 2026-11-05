"""Stage 11 (REMOTE CLOSURE): close_handoff additionally comments and closes the upstream issue,
only after local re-verification AND the same gates as filing (+ an explicit approval record for
'not planned'). Fake transports only."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from support import make_permit

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.github.token_provenance import TokenDecision
from repo_presenter.issues.approval import evidence_digest, handoff_id
from repo_presenter.issues.close import (
    CloseRefusal,
    RemoteClose,
    close_handoff,
    close_handoff_with_outcome,
)
from repo_presenter.issues.file import AUTHORIZATION_VARIABLE
from repo_presenter.issues.model import IssueRef

from .factory import REPO, _handoff

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
ENV = {AUTHORIZATION_VARIABLE: "1"}
FIXED = {"example:x": Fact(id="example:x", kind="example", value="now compiles",
                           evidence=(Evidence(path="README.md", detail="ok"),), polarity="SUPPORTED")}
BROKEN = {"example:x": replace(FIXED["example:x"], polarity="CONTRADICTED")}


def filed(repository: str = REPO):
    return replace(_handoff(repository=repository), status="FILED",
                   issue_ref=IssueRef(7, f"https://github.com/{repository}/issues/7"))


class Store:
    def __init__(self, records: dict[str, str] | None = None) -> None:
        self.records = records or {}

    def read(self, identifier: str) -> str | None:
        return self.records.get(identifier)


def approval(h, *, approver="owner-login") -> Store:
    rec = {
        "handoff_id": handoff_id(h), "repository": h.repository,
        "evidence_digest": evidence_digest(h), "approver": approver,
        "approved_at": (NOW - timedelta(hours=1)).isoformat(),
        "expires_at": (NOW + timedelta(days=6)).isoformat(),
    }
    return Store({handoff_id(h): json.dumps(rec)})


def close_approval(h, *, reason_text="false positive: check version changed", close_reason="not planned",
                   approver="owner-login") -> Store:
    rec = {
        "handoff_id": handoff_id(h), "repository": h.repository, "close_reason": close_reason,
        "reason_text": reason_text, "approver": approver,
        "approved_at": (NOW - timedelta(hours=1)).isoformat(),
        "expires_at": (NOW + timedelta(days=6)).isoformat(),
    }
    return Store({handoff_id(h) + ".close": json.dumps(rec)})


class Comments:
    """A fake GET /issues/{n}/comments: serves the given comment bodies in pages of ``page_size``;
    ``status`` simulates an unreachable/denied read. Counts reads."""

    def __init__(self, bodies: list[str] | None = None, *, status: int = 200, page_size: int = 100):
        self.bodies, self.status, self.page_size, self.reads = bodies or [], status, page_size, 0

    def __call__(self, url: str, token: str | None) -> tuple[int, Any]:
        self.reads += 1
        if self.status != 200:
            return self.status, None
        page = int(url.rsplit("page=", 1)[1])
        start = (page - 1) * self.page_size
        return 200, [{"body": b} for b in self.bodies[start:start + self.page_size]]


class W:
    def __init__(self, status: int = 200) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status = status

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status, {}


def remote(h, *, env=ENV, token="w", approvals=None, close_approvals=None, effect="issue_close",
           verify=None, comment=None, patch=None, fetch=None, **kw) -> RemoteClose:
    return RemoteClose(
        token=token, environment=env, permit=make_permit(h.repository, effect=effect),
        approvals=approvals if approvals is not None else approval(h),
        verify_token=verify or (lambda t: TokenDecision(True, t)),
        close_approvals=close_approvals, now=lambda: NOW,
        comment=comment or W(201), patch=patch or W(200), fetch=fetch or Comments(), **kw,
    )


def test_completed_close_comments_with_evidence_then_closes_completed(tmp_path: Path):
    h, out = filed(), tmp_path / "h.json"
    c, p = W(201), W(200)
    outcome = close_handoff_with_outcome(
        h, current_facts_by_id=FIXED, reason="completed", path=out,
        remote=remote(h, comment=c, patch=p))
    assert outcome.handoff.status == "RESOLVED_UPSTREAM" and out.exists()
    assert outcome.commented and outcome.closed_remote
    assert c.calls[0][0].endswith("/repos/babar-raza/repo-presenter/issues/7/comments")
    body = c.calls[0][2]["body"]
    assert "VERIFIED_RESOLVED" in body and "now compiles" in body and "README.md" in body
    assert p.calls == [("https://api.github.com/repos/babar-raza/repo-presenter/issues/7", "w",
                        {"state": "closed", "state_reason": "completed"})]


def test_without_a_remote_client_close_is_local_only(tmp_path: Path):
    assert close_handoff(filed(), current_facts_by_id=FIXED, reason="completed",
                         path=tmp_path / "h.json").status == "RESOLVED_UPSTREAM"


@pytest.mark.parametrize("facts", [BROKEN, {}], ids=["still-reproduces", "not-verifiable"])
def test_unverified_resolution_is_never_closed_remotely(tmp_path: Path, facts):
    h, c, p = filed(), W(201), W(200)
    with pytest.raises(CloseRefusal):
        close_handoff(h, current_facts_by_id=facts, reason="completed", path=tmp_path / "h.json",
                      remote=remote(h, comment=c, patch=p))
    assert c.calls == [] and p.calls == [] and not (tmp_path / "h.json").exists()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda h: {"env": {}},                          # kill switch off
        lambda h: {"env": {AUTHORIZATION_VARIABLE: "no"}},
        lambda h: {"token": ""},
        lambda h: {"approvals": Store()},               # no approval record
        lambda h: {"verify": lambda t: TokenDecision(False, None, reason="bad")},
        lambda h: {"expected_repository": "x/y"},
    ],
    ids=["switch-off", "switch-no", "no-token", "no-approval", "bad-token", "target-mismatch"],
)
def test_every_gate_refuses_before_any_write_and_writes_nothing_locally(tmp_path: Path, mutate):
    h, c, p = filed(), W(201), W(200)
    with pytest.raises(CloseRefusal):
        close_handoff(h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
                      remote=remote(h, comment=c, patch=p, **mutate(h)))
    assert c.calls == [] and p.calls == [] and not (tmp_path / "h.json").exists()


def test_permit_for_another_effect_or_repository_is_refused(tmp_path: Path):
    h, c, p = filed(), W(201), W(200)
    for bad in (remote(h, effect="issue_filing", comment=c, patch=p),):
        with pytest.raises(CloseRefusal):
            close_handoff(h, current_facts_by_id=FIXED, reason="completed",
                          path=tmp_path / "h.json", remote=bad)
    other = replace(h, repository="o/other")
    with pytest.raises(CloseRefusal):
        close_handoff(h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
                      remote=replace(remote(h), permit=make_permit(other.repository, effect="issue_close")))
    assert c.calls == [] and p.calls == []


def test_remote_close_without_an_issue_ref_is_refused(tmp_path: Path):
    h = replace(filed(), issue_ref=None)  # constructed directly; the model forbids it on disk
    with pytest.raises(CloseRefusal):
        close_handoff(h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
                      remote=remote(h))


def test_close_against_another_repository_never_reaches_the_writers(tmp_path: Path):
    h = filed("aspose-3d-foss/Aspose.3D-FOSS-for-Python")
    c, p = W(201), W(200)
    with pytest.raises(Exception) as err:
        close_handoff(h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
                      remote=remote(h, comment=c, patch=p))
    assert type(err.value).__name__ == "UpstreamWriteForbiddenError"
    assert c.calls == [] and p.calls == [] and not (tmp_path / "h.json").exists()


def test_remote_failure_leaves_local_state_unwritten(tmp_path: Path):
    h = filed()
    with pytest.raises(Exception, match="HTTP 500"):
        close_handoff(h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
                      remote=remote(h, patch=W(500)))
    assert not (tmp_path / "h.json").exists()


# ----------------------------- 'not planned' -----------------------------


def test_not_planned_local_close_still_skips_reverification_pinned(tmp_path: Path):
    """Pin of today's behavior: locally, 'not planned' does NOT re-detect (a defect that still
    reproduces may be closed as not planned)."""
    out = tmp_path / "h.json"
    r = close_handoff(filed(), current_facts_by_id=BROKEN, reason="not planned", path=out)
    assert r.close_reason == "not planned" and out.exists()


def test_not_planned_remote_requires_an_approval_record_with_a_reason(tmp_path: Path):
    h, c, p = filed(), W(201), W(200)
    with pytest.raises(CloseRefusal, match="close approval"):
        close_handoff(h, current_facts_by_id=BROKEN, reason="not planned", path=tmp_path / "h.json",
                      remote=remote(h, comment=c, patch=p))  # no close_approvals at all
    with pytest.raises(CloseRefusal, match="close approval"):
        close_handoff(h, current_facts_by_id=BROKEN, reason="not planned", path=tmp_path / "h.json",
                      remote=remote(h, comment=c, patch=p, close_approvals=Store()))
    assert c.calls == [] and p.calls == [] and not (tmp_path / "h.json").exists()


@pytest.mark.parametrize(
    "kw",
    [{"reason_text": "   "}, {"close_reason": "completed"}, {"approver": "ci[bot]"}],
    ids=["blank-reason", "wrong-close-reason", "bot-approver"],
)
def test_invalid_close_approval_is_refused(tmp_path: Path, kw):
    h, c, p = filed(), W(201), W(200)
    with pytest.raises(CloseRefusal):
        close_handoff(h, current_facts_by_id=BROKEN, reason="not planned", path=tmp_path / "h.json",
                      remote=remote(h, comment=c, patch=p, close_approvals=close_approval(h, **kw)))
    assert c.calls == [] and p.calls == []


def test_expired_or_other_handoffs_close_approval_is_refused(tmp_path: Path):
    h = filed()
    later = replace(remote(h, close_approvals=close_approval(h)), now=lambda: NOW + timedelta(days=30))
    with pytest.raises(CloseRefusal):
        close_handoff(h, current_facts_by_id=BROKEN, reason="not planned", path=tmp_path / "h.json",
                      remote=later)
    other = replace(h, defect_fingerprint="sha256:" + "c" * 64)
    with pytest.raises(CloseRefusal):
        close_handoff(h, current_facts_by_id=BROKEN, reason="not planned", path=tmp_path / "h.json",
                      remote=remote(h, close_approvals=close_approval(other)))


def test_approved_not_planned_remote_close_posts_the_recorded_reason_then_closes_not_planned(tmp_path: Path):
    h, c, p = filed(), W(201), W(200)
    out = close_handoff_with_outcome(
        h, current_facts_by_id=BROKEN, reason="not planned", path=tmp_path / "h.json",
        remote=remote(h, comment=c, patch=p, close_approvals=close_approval(h)))
    assert out.handoff.close_reason == "not planned" and out.closed_remote
    assert "false positive: check version changed" in c.calls[0][2]["body"]
    assert "owner-login" in c.calls[0][2]["body"]
    assert p.calls[0][2] == {"state": "closed", "state_reason": "not_planned"}


# --- idempotence across a partial failure (comment posted, close failed) -------------------------


def test_a_retry_after_a_failed_close_does_not_post_the_closing_comment_twice(tmp_path: Path) -> None:
    h = filed()
    posted = W(201)
    # Run 1: the comment lands, the close PATCH fails with HTTP 500 -> raises, handoff stays FILED.
    with pytest.raises(Exception, match="HTTP 500"):
        close_handoff(h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
                      remote=remote(h, comment=posted, patch=W(500)))
    assert len(posted.calls) == 1
    first_body = posted.calls[0][2]["body"]
    assert "repo-presenter:closing-comment:" in first_body
    # Run 2 (the retry): the issue now already holds that comment; only the close is attempted.
    patch = W(200)
    outcome = close_handoff_with_outcome(
        h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
        remote=remote(h, comment=posted, patch=patch, fetch=Comments([first_body])))
    assert len(posted.calls) == 1, "the closing comment was posted a second time"
    assert outcome.commented is False and outcome.comment_already_present is True
    assert outcome.closed_remote is True and len(patch.calls) == 1
    assert outcome.handoff.status == "RESOLVED_UPSTREAM"


def test_the_first_attempt_posts_the_comment_when_the_issue_has_none(tmp_path: Path) -> None:
    h = filed()
    posted = W(201)
    outcome = close_handoff_with_outcome(
        h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
        remote=remote(h, comment=posted, fetch=Comments(["an unrelated human comment"])))
    assert len(posted.calls) == 1 and outcome.commented and not outcome.comment_already_present


def test_a_marker_from_a_different_close_reason_is_not_treated_as_this_closing_comment(
    tmp_path: Path,
) -> None:
    from repo_presenter.issues.close import closing_marker

    h = filed()
    other = closing_marker(h, "not planned")  # a different reason's marker
    posted = W(201)
    outcome = close_handoff_with_outcome(
        h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
        remote=remote(h, comment=posted, fetch=Comments([other])))
    assert len(posted.calls) == 1 and outcome.commented


def test_the_marker_is_found_on_a_later_page_of_comments(tmp_path: Path) -> None:
    from repo_presenter.issues.close import closing_marker

    h = filed()
    filler = [f"comment {i}" for i in range(100)]  # exactly one full page, marker on page 2
    posted = W(201)
    outcome = close_handoff_with_outcome(
        h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
        remote=remote(h, comment=posted, fetch=Comments([*filler, closing_marker(h, "completed")])))
    assert posted.calls == [] and outcome.comment_already_present


@pytest.mark.parametrize("status", [-1, 403, 404, 500])
def test_an_unreadable_comment_list_posts_nothing_and_closes_nothing(tmp_path: Path, status: int) -> None:
    """Absence is never guessed from a failed read: no comment, no close, handoff stays FILED."""
    h = filed()
    posted, patch = W(201), W(200)
    path = tmp_path / "h.json"
    with pytest.raises(Exception):
        close_handoff(h, current_facts_by_id=FIXED, reason="completed", path=path,
                      remote=remote(h, comment=posted, patch=patch, fetch=Comments(status=status)))
    assert posted.calls == [] and patch.calls == [] and not path.exists()


def test_the_comment_read_is_not_made_when_a_gate_refuses(tmp_path: Path) -> None:
    h = filed()
    reads = Comments()
    with pytest.raises(CloseRefusal):
        close_handoff(h, current_facts_by_id=FIXED, reason="completed", path=tmp_path / "h.json",
                      remote=remote(h, env={}, fetch=reads))
    assert reads.reads == 0
