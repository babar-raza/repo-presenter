"""Loading a handoff artifact fails closed on a missing field, an unknown status, a
causal_stage other than EXTRACTING, or a status/issue_ref mismatch.

Ported (ADAPT) from the old repository-presenter project's own
tests/components/issues/test_model.py, 2026-10-24. The old file's two tests reading real
backfilled fixture artifacts under its own evidence/upstream-defects/ tree are replaced here with
locally-constructed round-trips -- this repository has no such committed fixtures (nothing has
filed an issue through this path yet).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_presenter.issues.model import (
    EvidenceEntry,
    Handoff,
    HandoffError,
    IssueRef,
    TriggeringCheck,
    handoff_to_dict,
    load_handoff,
    write_handoff,
)


def _minimal_payload(**overrides: object) -> dict:
    payload = {
        "schema_version": 1,
        "repository": "o/r",
        "source_revision": "a" * 40,
        "defect_fingerprint": "sha256:" + "b" * 64,
        "triggering_check": {"id": "BC-02", "version": "2", "causal_stage": "EXTRACTING"},
        "evidence": [{"path": "https://pypi.org/pypi/x/json", "detail": "not found"}],
        "claim": "a plain factual sentence",
        "suggested_issue_title": "title",
        "suggested_issue_body": "body",
        "status": "HANDOFF_PENDING",
        "issue_ref": None,
        "close_reason": None,
    }
    payload.update(overrides)
    return payload


def test_missing_required_field_fails_closed(tmp_path: Path) -> None:
    payload = _minimal_payload()
    del payload["claim"]
    path = tmp_path / "h.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HandoffError, match="claim"):
        load_handoff(path)


def test_unknown_status_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    path.write_text(json.dumps(_minimal_payload(status="DONE")), encoding="utf-8")
    with pytest.raises(HandoffError, match="status"):
        load_handoff(path)


def test_causal_stage_other_than_extracting_fails_closed(tmp_path: Path) -> None:
    payload = _minimal_payload()
    payload["triggering_check"]["causal_stage"] = "COMPOSING"
    path = tmp_path / "h.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HandoffError, match="EXTRACTING"):
        load_handoff(path)


def test_filed_without_issue_ref_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    path.write_text(json.dumps(_minimal_payload(status="FILED")), encoding="utf-8")
    with pytest.raises(HandoffError, match="issue_ref"):
        load_handoff(path)


def test_pending_with_issue_ref_fails_closed(tmp_path: Path) -> None:
    payload = _minimal_payload(issue_ref={"number": 1, "url": "https://github.com/o/r/issues/1"})
    path = tmp_path / "h.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HandoffError, match="issue_ref"):
        load_handoff(path)


def test_resolved_without_close_reason_fails_closed(tmp_path: Path) -> None:
    payload = _minimal_payload(
        status="RESOLVED_UPSTREAM",
        issue_ref={"number": 1, "url": "https://github.com/o/r/issues/1"},
    )
    path = tmp_path / "h.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HandoffError, match="close_reason"):
        load_handoff(path)


def test_unknown_close_reason_fails_closed(tmp_path: Path) -> None:
    payload = _minimal_payload(
        status="RESOLVED_UPSTREAM",
        issue_ref={"number": 1, "url": "https://github.com/o/r/issues/1"},
        close_reason="fixed",
    )
    path = tmp_path / "h.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HandoffError, match="close_reason"):
        load_handoff(path)


def test_resolved_with_each_valid_close_reason_round_trips(tmp_path: Path) -> None:
    for reason in ("completed", "not planned"):
        payload = _minimal_payload(
            status="RESOLVED_UPSTREAM",
            issue_ref={"number": 1, "url": "https://github.com/o/r/issues/1"},
            close_reason=reason,
        )
        path = tmp_path / f"h-{reason.replace(' ', '_')}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        handoff = load_handoff(path)
        assert handoff.close_reason == reason


def test_malformed_json_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(HandoffError):
        load_handoff(path)


def _sample_handoff() -> Handoff:
    return Handoff(
        schema_version=1,
        repository="aspose-html-foss/Aspose.HTML-FOSS-for-Python",
        source_revision="a" * 40,
        defect_fingerprint="sha256:" + "b" * 64,
        triggering_check=TriggeringCheck("BC-02", "2", "EXTRACTING"),
        evidence=(EvidenceEntry(path="pyproject.toml", detail="bad build-backend"),),
        claim="a plain factual sentence",
        suggested_issue_title="title",
        suggested_issue_body="body",
        status="HANDOFF_PENDING",
        issue_ref=None,
    )


def test_write_handoff_round_trips(tmp_path: Path) -> None:
    original = _sample_handoff()
    out = tmp_path / "sub" / "out.json"
    write_handoff(original, out)
    reloaded = load_handoff(out)
    assert reloaded == original
    assert out.read_text(encoding="utf-8").endswith("\n")


def test_handoff_to_dict_round_trips_through_from_dict() -> None:
    original = _sample_handoff()
    payload = handoff_to_dict(original)
    assert payload["repository"] == original.repository
    assert payload["evidence"][0] == {
        "path": original.evidence[0].path,
        "detail": original.evidence[0].detail,
    }
    assert payload["issue_ref"] is None


def test_evidence_entry_and_issue_ref_are_plain_frozen_records() -> None:
    entry = EvidenceEntry(path="p", detail="d")
    ref = IssueRef(number=1, url="https://github.com/o/r/issues/1")
    assert entry.path == "p" and ref.number == 1
    handoff = Handoff(
        schema_version=1,
        repository="o/r",
        source_revision="a" * 40,
        defect_fingerprint="sha256:" + "b" * 64,
        triggering_check=TriggeringCheck("BC-02", "1", "EXTRACTING"),
        evidence=(entry,),
        claim="claim",
        suggested_issue_title="t",
        suggested_issue_body="b",
        status="FILED",
        issue_ref=ref,
    )
    assert handoff.key == ("o/r", "sha256:" + "b" * 64)
    assert handoff.close_reason is None  # default: never set for any status but RESOLVED_UPSTREAM
