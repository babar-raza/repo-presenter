"""Stage 8 (TRACKING): apply_file_result records a filing/dedup/reopen outcome onto the handoff
and appends one occurrence-ledger entry per distinct re-detection, idempotently and purely."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from repo_presenter.issues.file import FileResult
from repo_presenter.issues.model import (
    IssueRef,
)
from repo_presenter.issues.track import (
    LedgerError,
    OccurrenceEntry,
    apply_file_result,
    load_ledger,
    write_ledger,
)

from .factory import FP, REPO, T1, T2, _handoff, _result


def test_filed_result_sets_status_issue_ref_and_records_first_occurrence():
    h = _handoff()
    upd = apply_file_result(h, _result(), observed_at=T1)
    assert upd.handoff.status == "FILED"
    assert upd.handoff.issue_ref == IssueRef(7, f"https://github.com/{REPO}/issues/7")
    assert len(upd.ledger) == 1
    e = upd.ledger[0]
    assert (e.key, e.revision, e.observed_at, e.count, e.issue_number, e.event) == (
        h.key, "r1", T1, 1, 7, "FILED")


def test_input_handoff_is_not_mutated_and_nothing_is_lost():
    h = _handoff()
    upd = apply_file_result(h, _result(), observed_at=T1)
    assert h.status == "HANDOFF_PENDING" and h.issue_ref is None
    for field in ("evidence", "claim", "defect_fingerprint", "defect_class", "source_revision",
                  "suggested_issue_body", "triggering_check"):
        assert getattr(upd.handoff, field) == getattr(h, field)


def test_applying_the_same_result_twice_records_one_occurrence():
    h = _handoff()
    first = apply_file_result(h, _result(), observed_at=T1)
    second = apply_file_result(first.handoff, _result(), observed_at=T2, ledger=first.ledger)
    assert second.ledger == first.ledger
    assert second.handoff == first.handoff


def test_redetection_at_a_new_revision_appends_with_incremented_count():
    first = apply_file_result(_handoff("r1"), _result(), observed_at=T1)
    again = apply_file_result(
        replace(first.handoff, source_revision="r2"),
        _result(filed=False), observed_at=T2, ledger=first.ledger)
    assert [e.count for e in again.ledger] == [1, 2]
    assert [e.revision for e in again.ledger] == ["r1", "r2"]
    assert again.ledger[1].event == "DEDUPED"
    assert again.ledger[0] == first.ledger[0]  # append-only: earlier entry untouched


def test_reconciled_and_reopened_events():
    r = apply_file_result(_handoff(), _result(filed=False, reconciled=True), observed_at=T1)
    assert r.ledger[0].event == "RECONCILED"
    reopened = FileResult(
        repository=REPO, defect_fingerprint=FP, authorized=True, filed=False, reason="reopened",
        issue_ref=IssueRef(7, "u"), reopened=True)
    resolved = _handoff("r3", status="RESOLVED_UPSTREAM", close_reason="completed",
                        issue_ref=IssueRef(7, "u"))
    out = apply_file_result(resolved, reopened, observed_at=T2)
    assert out.handoff.status == "FILED" and out.handoff.close_reason is None
    assert out.ledger[0].event == "REOPENED"


def test_refusal_without_issue_ref_changes_nothing():
    h = _handoff()
    upd = apply_file_result(h, _result(filed=False, issue=False), observed_at=T1)
    assert upd.handoff == h and upd.ledger == ()


def test_result_for_a_different_defect_or_repository_is_rejected():
    with pytest.raises(ValueError):
        apply_file_result(_handoff(), _result(fp="sha256:" + "b" * 64), observed_at=T1)
    with pytest.raises(ValueError):
        apply_file_result(_handoff(), _result(repo="o/other"), observed_at=T1)


def test_updated_handoff_round_trips_through_the_model(tmp_path: Path):
    upd = apply_file_result(_handoff(), _result(), observed_at=T1)
    from repo_presenter.issues.model import load_handoff, write_handoff

    write_handoff(upd.handoff, tmp_path / "h.json")
    assert load_handoff(tmp_path / "h.json") == upd.handoff


def test_ledger_persists_and_round_trips(tmp_path: Path):
    upd = apply_file_result(_handoff(), _result(), observed_at=T1)
    p = tmp_path / "ledger.json"
    write_ledger(upd.ledger, p)
    assert load_ledger(p) == upd.ledger
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(LedgerError):
        load_ledger(p)


def test_entry_type_is_frozen():
    e = OccurrenceEntry(key=(REPO, FP), revision="r", observed_at=T1, count=1,
                        issue_number=1, event="FILED")
    with pytest.raises(FrozenInstanceError):
        e.count = 2  # type: ignore[misc]
