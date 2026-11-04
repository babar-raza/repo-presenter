"""Issues lifecycle (project goal G3), end to end, against fake transports only.

2026-11-04 (TC-010; extended by the G3 lifecycle audit). No test here makes a real network call:
every transport is the in-memory ``FakeGitHub`` below, whose write path applies the SAME
``assert_write_allowed`` guard the real ``default_post`` applies. All external issue writes remain
owner-restricted to ``babar-raza/repo-presenter`` (github/client.py).

Lifecycle audit: stage -> implementing code -> existing tests -> status
-----------------------------------------------------------------------
1. Discovery      issues/discovery.py::discover_handoffs            tests/issues/test_discovery.py
                  COVERED  - CONTRADICTED facts become HANDOFF_PENDING handoffs, deterministically.
2. Classification issues/discovery.py::KIND_TO_DEFECT_CLASS,        test_discovery.py, test_model.py
                  issues/model.py::DEFECT_CLASSES
                  COVERED  - unmapped kinds skipped; unknown defect_class rejected on load. (Static
                  kind->class map only; no severity/priority classification exists.)
3. Evidence       issues/model.py::EvidenceEntry, approval.py::      test_model.py, test_approval.py
                  evidence_digest
                  COVERED  - evidence copied verbatim, required non-empty, digest-bound to approval.
4. Deduplication  issues/dedup.py (marker + check_dedup),           test_dedup.py, test_file.py
                  file.py::plan_filing(existing=)
                  COVERED  - upstream search open+closed, inconclusive search refuses, lost-response
                  reconcile. (Caller must inject ``existing``; file_handoff does not require it.)
5. Authorization  approval.py::verify_approval, file.py::           test_approval.py, test_file.py,
                  write_authorized (kill switch), registry         tests/github/test_write_guard.py
                  write_gate permit, github/token_provenance.py
                  COVERED  - fail closed on each of the four gates, before any network call.
6. Filing         issues/file.py::file_handoff -> client.create_issue  test_file.py
                  COVERED  - one POST, marker appended, target locked to babar-raza/repo-presenter
                  by client.assert_write_allowed (a refusal surfaces as FileResult.error).
7. Assignment     no code (create_issue sends only title/body)      none
                  MISSING  - no assignee/label/owner routing. Proposed minimal design: optional
                  ``assignees``/``labels`` tuple on create_issue's payload, supplied by the caller's
                  registry entry; same assert_write_allowed guard; <30 lines. NOT implemented here.
8. Tracking       issues/model.py (status, issue_ref, key)          test_model.py (shape only)
                  PARTIAL  - a Handoff records FILED + issue_ref, but no code applies a FileResult
                  to a Handoff, and nothing records re-detections (last_seen, count, revision).
                  Proposed: ``track.py`` with ``apply_file_result(handoff, FileResult)`` and an
                  append-only occurrence ledger keyed by Handoff.key. NOT implemented here.
9. Re-detection   issues/close.py::redetect (three outcomes),       test_close.py
                  discovery determinism + plan_filing dedup
                  PARTIAL  - redetect exists and is safe (absence is NOT_VERIFIABLE), and a
                  re-discovered defect dedups to its issue; but it is only wired to closing, and
                  a defect that recurs after closure is deduped to the closed issue (no reopen).
10. Resolution    issues/close.py::redetect -> VERIFIED_RESOLVED    test_close.py
                  COVERED  - requires the fact present and no longer CONTRADICTED.
11. Closure       issues/close.py::close_handoff                    test_close.py
                  PARTIAL  - guarded local transition FILED -> RESOLVED_UPSTREAM only. There is no
                  remote close (no PATCH issue state, no closing comment, no close authorization
                  record), and reason="not planned" closes with no re-verification at all.

Safety properties asserted below, each with a negative control (the same scenario with the
protection removed must exhibit the failure the protection prevents):
no false filing (stale recheck), no duplicate (dedup), no unauthorized write, no write outside
babar-raza/repo-presenter, no premature closure, no loss of issue history.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.issues.approval import evidence_digest, handoff_id
from repo_presenter.issues.close import CloseRefusal, close_handoff
from repo_presenter.issues.discovery import discover_handoffs
from repo_presenter.issues.file import plan_filing
from repo_presenter.issues.model import IssueRef


class _FakeApprovalStore:
    def __init__(self, records: dict[str, str]) -> None:
        self._records = records

    def read(self, identifier: str) -> str | None:
        return self._records.get(identifier)


def _approval_text(handoff, *, approver: str = "a-human") -> str:
    now = datetime.now(UTC)
    return json.dumps({
        "handoff_id": handoff_id(handoff),
        "repository": handoff.repository,
        "evidence_digest": evidence_digest(handoff),
        "approver": approver,
        "approved_at": now.isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
    })


def _contradicted_example_doc() -> FactsDocument:
    fact = Fact(
        id="example:readme-snippet-1", kind="example",
        value="the README's first example does not compile",
        evidence=(Evidence(path="README.md", detail="line 42"),), polarity="CONTRADICTED",
    )
    return FactsDocument(repository="aspose-x-foss/Aspose.X-FOSS-for-Python",
                          source_revision="a" * 40, facts=(fact,))


def test_full_lifecycle_discover_approve_plan_file_redetect_close(tmp_path: Path):
    # 1. Discovery: a real CONTRADICTED fact becomes a real handoff.
    doc = _contradicted_example_doc()
    handoffs = discover_handoffs(doc, extractor_version="1")
    assert len(handoffs) == 1
    handoff = handoffs[0]

    # 2. Approval + dedup + recheck, via the EXISTING, already-tested plan_filing: approved,
    # not already filed upstream, and the defect still reproduces -- ready to file.
    store = _FakeApprovalStore({handoff_id(handoff): _approval_text(handoff)})
    plan = plan_filing(
        handoff,
        existing=lambda: None,  # dedup: nothing filed yet
        recheck=lambda: type("R", (), {"still_fires": True, "note": "still contradicted"})(),
        approvals=store,
    )
    assert plan.ready, plan.refusal
    assert plan.already_filed is None

    # 3. Simulate the real filing outcome this plan would produce (file_handoff's own network
    # path is already covered by tests/issues/test_file.py -- here we only need a FILED handoff
    # to hand to close()).
    filed = type(handoff)(**{**handoff.__dict__, "status": "FILED",
                             "issue_ref": IssueRef(number=9, url="https://github.com/x/y/issues/9")})

    # 4. Re-detection: the defect is now fixed (fresh facts show SUPPORTED).
    fixed_fact = Fact(id="example:readme-snippet-1", kind="example", value="now compiles",
                       evidence=(Evidence(path="README.md"),), polarity="SUPPORTED")

    # 5. Close: only succeeds because re-detection genuinely confirms the fix.
    out = tmp_path / "handoff.json"
    resolved = close_handoff(
        filed, current_facts_by_id={"example:readme-snippet-1": fixed_fact},
        reason="completed", path=out,
    )
    assert resolved.status == "RESOLVED_UPSTREAM"
    assert out.exists()


def test_full_lifecycle_refuses_filing_without_approval():
    doc = _contradicted_example_doc()
    handoff = discover_handoffs(doc, extractor_version="1")[0]
    plan = plan_filing(handoff, approvals=_FakeApprovalStore({}))  # no record committed
    assert not plan.ready
    assert "no approval record" in plan.refusal


def test_full_lifecycle_refuses_filing_when_already_filed_upstream_dedup():
    doc = _contradicted_example_doc()
    handoff = discover_handoffs(doc, extractor_version="1")[0]
    store = _FakeApprovalStore({handoff_id(handoff): _approval_text(handoff)})
    existing_ref = IssueRef(number=4, url="https://github.com/x/y/issues/4")
    plan = plan_filing(handoff, existing=lambda: existing_ref, approvals=store)
    assert not plan.ready  # not "ready to file" -- it's already filed
    assert plan.already_filed == existing_ref
    assert plan.refusal is None  # recognized, not refused


def test_full_lifecycle_refuses_close_when_redetection_finds_the_defect_still_live(tmp_path: Path):
    doc = _contradicted_example_doc()
    handoff = discover_handoffs(doc, extractor_version="1")[0]
    filed = type(handoff)(**{**handoff.__dict__, "status": "FILED",
                             "issue_ref": IssueRef(number=9, url="https://github.com/x/y/issues/9")})
    still_broken = Fact(id="example:readme-snippet-1", kind="example", value="still broken",
                         evidence=(Evidence(path="README.md"),), polarity="CONTRADICTED")
    out = tmp_path / "handoff.json"
    with pytest.raises(CloseRefusal):
        close_handoff(filed, current_facts_by_id={"example:readme-snippet-1": still_broken},
                       reason="completed", path=out)
    assert not out.exists()


# ===========================================================================
# G3 lifecycle audit: one finding driven through every stage against a fake GitHub.
# ===========================================================================
from dataclasses import replace

from support import make_permit

from repo_presenter.github import client as _client
from repo_presenter.github.client import (
    API_ROOT,
    UpstreamWriteForbiddenError,
    assert_write_allowed,
    create_issue,
)
from repo_presenter.github.token_provenance import TokenDecision
from repo_presenter.issues.dedup import (
    body_with_marker,
    check_dedup,
    fingerprint_marker,
)
from repo_presenter.issues.file import (
    AUTHORIZATION_VARIABLE,
    file_handoff,
)
from repo_presenter.issues.model import load_handoff

ALLOWED_REPO = "babar-raza/repo-presenter"
UPSTREAM_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
FACT_ID = "example:readme-snippet-1"
ENABLED = {AUTHORIZATION_VARIABLE: "1"}


class FakeGitHub:
    """In-memory issue tracker. ``write`` applies the real write guard, then records the call."""

    def __init__(self) -> None:
        self.issues: list[dict] = []
        self.write_calls: list[tuple[str, dict]] = []
        self.fetch_calls: list[str] = []

    def fetch(self, url: str, token: str | None):
        self.fetch_calls.append(url)
        return 200, [dict(i) for i in self.issues]

    def write(self, url: str, token: str, payload: dict):
        assert_write_allowed(url)  # exactly what default_post does before any request
        self.write_calls.append((url, payload))
        number = len(self.issues) + 1
        self.issues.append({
            "number": number, "html_url": f"https://github.com/{ALLOWED_REPO}/issues/{number}",
            "body": payload["body"], "title": payload["title"], "state": "open",
            "labels": [], "comments": [],
        })
        return 201, {"number": number, "html_url": self.issues[-1]["html_url"]}


def _doc(repo: str, polarity: str = "CONTRADICTED", revision: str = "a" * 40) -> FactsDocument:
    fact = Fact(id=FACT_ID, kind="example", value="the README's first example does not compile",
                evidence=(Evidence(path="README.md", detail="line 42"),), polarity=polarity)
    return FactsDocument(repository=repo, source_revision=revision, facts=(fact,))


def _discover(repo: str = ALLOWED_REPO, **kw):
    return discover_handoffs(_doc(repo, **kw), extractor_version="1")[0]


def _ok_token(token: str) -> TokenDecision:
    return TokenDecision(True, token)


def _dedup_lookup(gh: FakeGitHub, handoff):
    owner, name = handoff.repository.split("/", 1)

    def lookup():
        found = check_dedup(owner, name, handoff.defect_fingerprint, token="t", fetch=gh.fetch)
        return None if found is None else IssueRef(number=found.number, url=found.url)

    return lookup


def _still_fires(value: bool):
    return lambda: type("R", (), {"still_fires": value, "note": "n"})()


def _file(handoff, gh, *, approvals="approved", environment=ENABLED, dedup=True,
          recheck=True, permit=None, **kw):
    if approvals == "approved":
        approvals = _FakeApprovalStore({handoff_id(handoff): _approval_text(handoff)})
    elif approvals == "none":
        approvals = _FakeApprovalStore({})
    return file_handoff(
        handoff, token="t", environment=environment, create=gh.write,
        existing=_dedup_lookup(gh, handoff) if dedup else None,
        recheck=_still_fires(True) if recheck else None,
        approvals=approvals, expected_repository=handoff.repository,
        permit=permit or make_permit(handoff.repository, effect="issue_filing"),
        verify_token=_ok_token, **kw,
    )


# -- stages 1-3: discovery, classification, evidence ------------------------------------------

def test_discovery_classification_and_evidence_attached():
    h = _discover()
    assert h.status == "HANDOFF_PENDING" and h.issue_ref is None
    assert h.defect_class == "EXAMPLE_FAILS"  # classification
    assert [(e.path, e.detail) for e in h.evidence] == [("README.md", "line 42")]  # evidence
    assert _discover().defect_fingerprint == h.defect_fingerprint  # deterministic


def test_no_false_finding_from_supported_or_unmapped_facts():
    assert discover_handoffs(_doc(ALLOWED_REPO, polarity="SUPPORTED"), extractor_version="1") == []
    odd = Fact(id="identity:x", kind="identity", value="v",
               evidence=(Evidence(path="p"),), polarity="CONTRADICTED")
    doc = FactsDocument(repository=ALLOWED_REPO, source_revision="a" * 40, facts=(odd,))
    assert discover_handoffs(doc, extractor_version="1") == []


# -- stage 4/6: dedup and filing --------------------------------------------------------------

def test_authorization_granted_files_exactly_one_issue_at_the_allowed_repository():
    gh, h = FakeGitHub(), _discover()
    result = _file(h, gh)
    assert result.filed and result.issue_ref is not None
    assert len(gh.write_calls) == 1
    url, payload = gh.write_calls[0]
    assert url == f"{API_ROOT}/repos/{ALLOWED_REPO}/issues"
    assert fingerprint_marker(h.defect_fingerprint) in payload["body"]


def test_dedup_against_an_existing_open_issue_files_nothing_new():
    gh, h = FakeGitHub(), _discover()
    gh.issues.append({"number": 3, "html_url": "https://github.com/x/y/issues/3", "state": "open",
                      "body": f"earlier\n{fingerprint_marker(h.defect_fingerprint)}"})
    result = _file(h, gh)
    assert not result.filed and result.issue_ref == IssueRef(3, "https://github.com/x/y/issues/3")
    assert gh.write_calls == []


def test_negative_control_without_the_dedup_check_a_duplicate_is_filed():
    gh, h = FakeGitHub(), _discover()
    assert _file(h, gh).filed
    second = _file(h, gh, dedup=False)  # protection removed
    assert second.filed and len(gh.write_calls) == 2  # the duplicate the real path prevents
    gh2, h2 = FakeGitHub(), _discover()
    _file(h2, gh2)
    _file(h2, gh2)  # protection in place
    assert len(gh2.write_calls) == 1


def test_stale_finding_is_not_filed_and_negative_control():
    gh, h = FakeGitHub(), _discover()
    res = file_handoff(
        h, token="t", environment=ENABLED, create=gh.write, existing=_dedup_lookup(gh, h),
        recheck=_still_fires(False),
        approvals=_FakeApprovalStore({handoff_id(h): _approval_text(h)}),
        permit=make_permit(ALLOWED_REPO, effect="issue_filing"), verify_token=_ok_token,
    )
    assert not res.filed and gh.write_calls == []
    assert _file(h, gh, recheck=False).filed  # control: without the recheck the stale one files


# -- stage 5: authorization -------------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    {"environment": {}},                      # kill switch off
    {"environment": {AUTHORIZATION_VARIABLE: "0"}},
    {"approvals": "none"},                    # no per-handoff approval record
])
def test_authorization_refused_writes_nothing(kwargs):
    gh, h = FakeGitHub(), _discover()
    result = _file(h, gh, **kwargs)
    assert not result.filed and gh.write_calls == [] and gh.issues == []


def test_expired_or_changed_evidence_approval_writes_nothing():
    gh, h = FakeGitHub(), _discover()
    changed = replace(h, evidence=(*h.evidence, type(h.evidence[0])("x.md", "new")))
    store = _FakeApprovalStore({handoff_id(h): _approval_text(h)})  # approved the OLD evidence
    assert not _file(changed, gh, approvals=store).filed and gh.write_calls == []
    future = lambda: datetime.now(UTC) + timedelta(days=30)
    assert not _file(h, gh, approvals=store, now=future).filed and gh.write_calls == []


def test_a_permit_for_another_repository_is_refused_before_anything_happens():
    gh, h = FakeGitHub(), _discover()
    with pytest.raises(ValueError, match="permit"):
        _file(h, gh, permit=make_permit("someone/else", effect="issue_filing"))
    assert gh.write_calls == [] and gh.fetch_calls == []


# -- stage 6 safety: no write outside babar-raza/repo-presenter ---------------------------------

def test_every_gate_open_for_an_upstream_slug_still_makes_no_request(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("an HTTP request was attempted for an upstream target")

    for verb in ("post", "patch", "put"):
        monkeypatch.setattr(_client.httpx, verb, boom)
    gh, h = FakeGitHub(), _discover(UPSTREAM_REPO)
    result = file_handoff(  # real default_post transport, all four gates satisfied
        h, token="t", environment=ENABLED, existing=lambda: None,
        approvals=_FakeApprovalStore({handoff_id(h): _approval_text(h)}),
        permit=make_permit(UPSTREAM_REPO, effect="issue_filing"), verify_token=_ok_token,
    )
    assert not result.filed and result.error and "write refused" in result.reason
    # and via the fake, whose write applies the same guard: nothing is recorded
    result2 = _file(h, gh)
    assert not result2.filed and gh.write_calls == [] and gh.issues == []


def test_create_issue_raises_for_an_upstream_slug_before_any_request(monkeypatch):
    monkeypatch.setattr(_client.httpx, "post", lambda *a, **k: pytest.fail("request made"))
    with pytest.raises(UpstreamWriteForbiddenError):
        create_issue("aspose-3d-foss", "Aspose.3D-FOSS-for-Python", title="t", body="b", token="t")


# -- stages 8-9: re-detection updates tracking, never re-files ----------------------------------

def test_redetection_of_the_same_defect_records_the_existing_issue_not_a_new_one():
    gh, h = FakeGitHub(), _discover()
    first = _file(h, gh)
    tracked = replace(h, status="FILED", issue_ref=first.issue_ref)
    rediscovered = _discover(revision="b" * 40)  # next run, new revision, same defect
    assert rediscovered.defect_fingerprint == tracked.defect_fingerprint
    again = _file(rediscovered, gh)
    assert not again.filed and again.issue_ref == first.issue_ref  # tracking points at issue #1
    assert len(gh.write_calls) == 1 and len(gh.issues) == 1
    # an already-FILED handoff is itself never re-filed
    assert not _file(tracked, gh).filed and len(gh.write_calls) == 1


def test_a_closed_issue_still_dedups_known_gap_no_reopen():
    gh, h = FakeGitHub(), _discover()
    _file(h, gh)
    gh.issues[0]["state"] = "closed"
    again = _file(h, gh)
    assert not again.filed and len(gh.write_calls) == 1  # documents: recurrence is not reopened


# -- stages 10-11: resolution and closure, history -----------------------------------------------

def _filed(gh: FakeGitHub, h):
    return replace(h, status="FILED", issue_ref=_file(h, gh).issue_ref)


def test_closure_only_after_independent_reverification(tmp_path: Path):
    gh, h = FakeGitHub(), _discover()
    filed = _filed(gh, h)
    out = tmp_path / "h.json"
    still = Fact(id=FACT_ID, kind="example", value="v", evidence=(Evidence(path="p"),),
                 polarity="CONTRADICTED")
    for facts in ({FACT_ID: still}, {}):  # still broken; and evidence absent (not proof of a fix)
        with pytest.raises(CloseRefusal):
            close_handoff(filed, current_facts_by_id=facts, reason="completed", path=out)
        assert not out.exists()
    with pytest.raises(CloseRefusal):  # a never-filed handoff cannot be closed at all
        close_handoff(h, current_facts_by_id={}, reason="not planned", path=out)
    fixed = replace(still, polarity="SUPPORTED")
    closed = close_handoff(filed, current_facts_by_id={FACT_ID: fixed}, reason="completed",
                           path=out)
    assert closed.status == "RESOLVED_UPSTREAM" and closed.close_reason == "completed"


def test_issue_history_is_preserved_through_the_whole_lifecycle(tmp_path: Path):
    gh, h = FakeGitHub(), _discover()
    filed = _filed(gh, h)
    gh.issues[0]["labels"] = ["bug", "needs-triage"]
    gh.issues[0]["comments"] = ["maintainer: reproduced", "maintainer: fix in PR 12"]
    before = {k: (list(v) if isinstance(v, list) else v) for k, v in gh.issues[0].items()}
    _file(_discover(revision="c" * 40), gh)  # re-detection pass
    out = tmp_path / "h.json"
    fixed = Fact(id=FACT_ID, kind="example", value="v", evidence=(Evidence(path="p"),),
                 polarity="SUPPORTED")
    close_handoff(filed, current_facts_by_id={FACT_ID: fixed}, reason="completed", path=out)
    assert gh.issues[0] == before  # comments, labels, body, state untouched by every stage
    assert len(gh.write_calls) == 1  # no PATCH/comment/delete was ever issued
    reloaded = load_handoff(out)  # the local record keeps evidence, claim and issue linkage
    assert reloaded.evidence == filed.evidence and reloaded.claim == filed.claim
    assert reloaded.issue_ref == filed.issue_ref
    assert reloaded.defect_fingerprint == filed.defect_fingerprint


def test_marker_is_not_duplicated_when_body_already_has_it():
    h = _discover()
    once = body_with_marker(h.suggested_issue_body, h.defect_fingerprint)
    assert body_with_marker(once, h.defect_fingerprint) == once
