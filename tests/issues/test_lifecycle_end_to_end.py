"""2026-11-04 (TC-010): the complete issues lifecycle, chained through its ACTUAL callers --
discovery -> approval -> plan_filing (dedup/recheck/authorization, all existing, already-tested
modules) -> close -- demonstrated end to end with real refusal, deduplication, authorization,
and verified-closing behavior, per the follow-up directive's explicit demand ("Test the complete
issues lifecycle through an actual caller... not just one manually executed CLI operation").

No real network call is made anywhere in this file (file.py's own plan_filing takes injectable
callables for exactly this reason); this proves the NEW modules (discovery, close) interoperate
correctly with the EXISTING, already-tested ones (approval, file), not that a live GitHub call
works (tests/propose/test_effect.py and tests/github/test_token_provenance.py already cover that
pattern for the propose path).
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repo_presenter.core.facts import Evidence, Fact, FactsDocument  # noqa: E402
from repo_presenter.issues.approval import evidence_digest, handoff_id  # noqa: E402
from repo_presenter.issues.close import CloseRefusal, close_handoff  # noqa: E402
from repo_presenter.issues.discovery import discover_handoffs  # noqa: E402
from repo_presenter.issues.file import plan_filing  # noqa: E402
from repo_presenter.issues.model import IssueRef  # noqa: E402


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
