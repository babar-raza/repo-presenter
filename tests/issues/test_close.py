"""Real tests for issues/close.py (2026-11-04, TC-010): a FILED handoff may only close as
'completed' when re-detection confirms the defect no longer reproduces; closing anything not
FILED is refused; 'not planned' does not require re-detection."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repo_presenter.core.facts import Evidence, Fact  # noqa: E402
from repo_presenter.issues.close import CloseRefusal, close_handoff, redetect  # noqa: E402
from repo_presenter.issues.model import EvidenceEntry, Handoff, IssueRef, TriggeringCheck  # noqa: E402


def _filed_handoff(fingerprint: str = "example:x") -> Handoff:
    return Handoff(
        schema_version=1,
        repository="o/r",
        source_revision="a" * 40,
        defect_fingerprint=fingerprint,
        triggering_check=TriggeringCheck(id=fingerprint, version="1", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="README.md", detail=None),),
        claim="bad",
        suggested_issue_title="t",
        suggested_issue_body="b",
        status="FILED",
        issue_ref=IssueRef(number=4, url="https://github.com/o/r/issues/4"),
    )


def test_redetect_true_when_fact_no_longer_contradicted():
    handoff = _filed_handoff()
    fixed_fact = Fact(id="example:x", kind="example", value="now fine",
                       evidence=(Evidence(path="README.md"),), polarity="SUPPORTED")
    assert redetect(handoff, {"example:x": fixed_fact}) is True


def test_redetect_false_when_fact_still_contradicted():
    handoff = _filed_handoff()
    still_broken = Fact(id="example:x", kind="example", value="still bad",
                         evidence=(Evidence(path="README.md"),), polarity="CONTRADICTED")
    assert redetect(handoff, {"example:x": still_broken}) is False


def test_redetect_true_when_fact_no_longer_exists_at_all():
    handoff = _filed_handoff()
    assert redetect(handoff, {}) is True


def test_close_completed_succeeds_when_redetection_confirms_fix(tmp_path: Path):
    handoff = _filed_handoff()
    fixed_fact = Fact(id="example:x", kind="example", value="now fine",
                       evidence=(Evidence(path="README.md"),), polarity="SUPPORTED")
    out = tmp_path / "handoff.json"
    resolved = close_handoff(
        handoff, current_facts_by_id={"example:x": fixed_fact}, reason="completed", path=out,
    )
    assert resolved.status == "RESOLVED_UPSTREAM"
    assert resolved.close_reason == "completed"
    assert out.exists()


def test_close_completed_refused_when_defect_still_reproduces(tmp_path: Path):
    handoff = _filed_handoff()
    still_broken = Fact(id="example:x", kind="example", value="still bad",
                         evidence=(Evidence(path="README.md"),), polarity="CONTRADICTED")
    out = tmp_path / "handoff.json"
    with pytest.raises(CloseRefusal, match="still CONTRADICTED"):
        close_handoff(
            handoff, current_facts_by_id={"example:x": still_broken}, reason="completed", path=out,
        )
    assert not out.exists()  # a refused close must write nothing


def test_close_not_planned_does_not_require_redetection(tmp_path: Path):
    handoff = _filed_handoff()
    still_broken = Fact(id="example:x", kind="example", value="still bad",
                         evidence=(Evidence(path="README.md"),), polarity="CONTRADICTED")
    out = tmp_path / "handoff.json"
    resolved = close_handoff(
        handoff, current_facts_by_id={"example:x": still_broken}, reason="not planned", path=out,
    )
    assert resolved.status == "RESOLVED_UPSTREAM"
    assert resolved.close_reason == "not planned"


def test_closing_a_handoff_that_was_never_filed_is_refused(tmp_path: Path):
    pending = Handoff(
        schema_version=1, repository="o/r", source_revision="a" * 40,
        defect_fingerprint="example:x",
        triggering_check=TriggeringCheck(id="example:x", version="1", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="README.md", detail=None),),
        claim="bad", suggested_issue_title="t", suggested_issue_body="b",
        status="HANDOFF_PENDING", issue_ref=None,
    )
    out = tmp_path / "handoff.json"
    with pytest.raises(CloseRefusal, match="only FILED"):
        close_handoff(pending, current_facts_by_id={}, reason="not planned", path=out)
    assert not out.exists()
