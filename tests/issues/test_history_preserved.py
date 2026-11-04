"""Whole-lifecycle test against an in-memory fake of the one allowed repository: file -> track ->
redetect -> close -> recurrence -> reopen. The fake issue's labels, body and comments must only
grow (history preserved), no second issue may ever appear, and with the kill switch off the fake
is not touched at all. No real network."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from support import make_permit

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.github.client import API_ROOT, find_issue_with_marker
from repo_presenter.github.token_provenance import TokenDecision
from repo_presenter.issues.approval import evidence_digest, handoff_id
from repo_presenter.issues.close import RemoteClose, close_handoff
from repo_presenter.issues.dedup import fingerprint_marker
from repo_presenter.issues.file import AUTHORIZATION_VARIABLE, file_handoff
from repo_presenter.issues.model import load_handoff
from repo_presenter.issues.track import apply_file_result

from .factory import FP, REPO, T1, T2, _handoff

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
ENV = {AUTHORIZATION_VARIABLE: "1"}
ISSUES = f"{API_ROOT}/repos/{REPO}/issues"


class FakeGitHub:
    def __init__(self) -> None:
        self.issues: dict[int, dict[str, Any]] = {}
        self.writes = 0

    def post(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.writes += 1
        if url == ISSUES:
            n = len(self.issues) + 1
            self.issues[n] = {"number": n, "html_url": f"https://github.com/{REPO}/issues/{n}",
                              "state": "open", "title": payload["title"], "body": payload["body"],
                              "labels": list(payload.get("labels", [])), "comments": []}
            return 201, self.issues[n]
        m = re.fullmatch(re.escape(ISSUES) + r"/(\d+)/comments", url)
        assert m, url
        self.issues[int(m[1])]["comments"].append(payload["body"])
        return 201, {}

    def patch(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.writes += 1
        m = re.fullmatch(re.escape(ISSUES) + r"/(\d+)", url)
        assert m, url
        self.issues[int(m[1])]["state"] = payload["state"]
        self.issues[int(m[1])]["state_reason"] = payload["state_reason"]
        return 200, {}

    def fetch(self, url: str, token: str | None) -> tuple[int, Any]:
        return 200, [dict(i) for i in self.issues.values()] if "page=1" in url else []


class Store:
    def __init__(self, h: Any) -> None:
        rec = {"handoff_id": handoff_id(h), "repository": h.repository,
               "evidence_digest": evidence_digest(h), "approver": "owner-login",
               "approved_at": (NOW - timedelta(hours=1)).isoformat(),
               "expires_at": (NOW + timedelta(days=6)).isoformat()}
        self.r = {handoff_id(h): json.dumps(rec)}

    def read(self, i: str) -> str | None:
        return self.r.get(i)


def _file(gh: FakeGitHub, h, env=ENV):
    owner, name = REPO.split("/")
    return file_handoff(
        h, token="w", environment=env, approvals=Store(h), now=lambda: NOW,
        permit=make_permit(REPO, effect="issue_filing"),
        verify_token=lambda t: TokenDecision(True, t),
        existing=lambda: find_issue_with_marker(owner, name, fingerprint_marker(FP), token="w",
                                                fetch=gh.fetch),
        create=gh.post, comment=gh.post, patch=gh.patch,
    )


def test_history_is_preserved_across_the_whole_lifecycle(tmp_path: Path):
    gh, path = FakeGitHub(), tmp_path / "h.json"
    h1 = _handoff("rev1")

    # file
    r1 = _file(gh, h1)
    assert r1.filed and len(gh.issues) == 1
    issue = gh.issues[1]
    body0, labels0 = issue["body"], list(issue["labels"])
    assert fingerprint_marker(FP) in body0 and labels0 == ["repo-presenter", "defect:example_fails"]
    t1 = apply_file_result(h1, r1, observed_at=T1)
    assert t1.handoff.status == "FILED"

    # still open + re-detected: dedup only, nothing written
    writes = gh.writes
    r_dup = _file(gh, _handoff("rev1b"))
    assert r_dup.filed is False and r_dup.reopened is False and gh.writes == writes

    # redetect -> close (completed), remote
    fixed = {"example:x": Fact(id="example:x", kind="example", value="now compiles",
                               evidence=(Evidence(path="README.md"),), polarity="SUPPORTED")}
    fh = t1.handoff
    closed = close_handoff(
        fh, current_facts_by_id=fixed, reason="completed", path=path,
        remote=RemoteClose(token="w", environment=ENV, permit=make_permit(REPO, effect="issue_close"),
                           approvals=Store(fh), verify_token=lambda t: TokenDecision(True, t),
                           now=lambda: NOW, comment=gh.post, patch=gh.patch))
    assert closed.status == "RESOLVED_UPSTREAM" and load_handoff(path) == closed
    assert issue["state"] == "closed" and issue["state_reason"] == "completed"
    assert len(issue["comments"]) == 1 and "VERIFIED_RESOLVED" in issue["comments"][0]

    # recurrence: closed + re-detected -> reopen, same issue
    h3 = _handoff("rev3")
    r3 = _file(gh, h3)
    assert r3.reopened and not r3.filed and r3.issue_ref.number == 1
    t3 = apply_file_result(h3, r3, observed_at=T2, ledger=t1.ledger)
    assert t3.handoff.status == "FILED" and [e.event for e in t3.ledger] == ["FILED", "REOPENED"]
    assert [e.count for e in t3.ledger] == [1, 2]

    assert len(gh.issues) == 1
    assert issue["state"] == "open"
    assert issue["body"] == body0 and issue["labels"] == labels0
    assert len(issue["comments"]) == 2
    assert "VERIFIED_RESOLVED" in issue["comments"][0]          # earlier history intact
    assert "rev3" in issue["comments"][1] and "Recurrence" in issue["comments"][1]
    assert t3.handoff.evidence == h3.evidence and t3.handoff.claim == h3.claim


def test_kill_switch_off_writes_nothing_at_any_stage(tmp_path: Path):
    gh = FakeGitHub()
    h = _handoff()
    assert _file(gh, h, env={}).filed is False
    assert gh.writes == 0 and gh.issues == {}
    # an existing closed issue is not reopened either, and a remote close is refused
    assert _file(gh, h).filed
    gh.issues[1]["state"] = "closed"
    writes, snapshot = gh.writes, json.dumps(gh.issues, sort_keys=True)
    assert _file(gh, _handoff("rev2"), env={AUTHORIZATION_VARIABLE: "0"}).reopened is False
    assert gh.writes == writes and json.dumps(gh.issues, sort_keys=True) == snapshot
    fh = replace(h, status="FILED", issue_ref=_file(gh, _handoff("rev2")).issue_ref)
    gh.issues[1]["state"] = "open"
    import pytest

    from repo_presenter.issues.close import CloseRefusal

    fixed = {"example:x": Fact(id="example:x", kind="example", value="ok",
                               evidence=(Evidence(path="README.md"),), polarity="SUPPORTED")}
    writes = gh.writes
    with pytest.raises(CloseRefusal):
        close_handoff(fh, current_facts_by_id=fixed, reason="completed", path=tmp_path / "x.json",
                      remote=RemoteClose(token="w", environment={},
                                         permit=make_permit(REPO, effect="issue_close"),
                                         approvals=Store(fh), verify_token=lambda t: TokenDecision(True, t),
                                         now=lambda: NOW, comment=gh.post, patch=gh.patch))
    assert gh.writes == writes and gh.issues[1]["state"] == "open"
