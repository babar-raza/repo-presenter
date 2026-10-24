"""Per-handoff owner approval for upstream issue filing (``issues/approval.py``).

Every refusal here is a negative control for the incident this module closes: a single
repository variable used to authorize filing every pending handoff into an Aspose repository. No
test makes a live GitHub call; the git store is exercised against disposable local repositories.

Ported (ADAPT, a representative subset -- not the old repo's full ~625-line file, which also
covers ``file_handoff``/``plan_filing``, not yet ported here; see
``project/state.yaml``'s ``DECIDE_NEXT_ISSUE_FILINGS``) from the old repository-presenter
project's own ``tests/components/issues/test_approval.py``, 2026-10-24.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.issues.approval import (
    MAX_APPROVAL_LIFETIME,
    ApprovalProvenanceError,
    GitApprovalStore,
    approval_relative_path,
    evidence_digest,
    handoff_id,
    parse_approval,
    verify_approval,
)
from repo_presenter.issues.model import EvidenceEntry, Handoff, IssueRef, TriggeringCheck
from repo_presenter.core.git_safety.git import run_git
from support import commit_all, init_git_repository

REPO = "aspose-html-foss/Aspose.HTML-FOSS-for-Python"
REVISION = "bf0f1e7a6d29ca9e14de576fe3ff1aa49ddbaf11"
FINGERPRINT = "sha256:ae9f06b95a4cc18609d64276e4a831bf9260ed6ea9c613f36cf2876478ea849a"
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _handoff(**changes: Any) -> Handoff:
    base = Handoff(
        schema_version=1,
        repository=REPO,
        source_revision=REVISION,
        defect_fingerprint=FINGERPRINT,
        triggering_check=TriggeringCheck(id="BC-02", version="2", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="pyproject.toml", detail="bad build-backend"),),
        claim=f"At revision {REVISION}, {REPO} cannot be built.",
        suggested_issue_title="build-backend does not exist",
        suggested_issue_body="## Summary\n\nbroken.\n",
        status="HANDOFF_PENDING",
        issue_ref=None,
    )
    return replace(base, **changes)


def _approval_text(handoff: Handoff, **overrides: Any) -> str:
    record = {
        "handoff_id": handoff_id(handoff),
        "repository": handoff.repository,
        "evidence_digest": evidence_digest(handoff),
        "approver": "owner-login",
        "approved_at": (NOW - timedelta(hours=1)).isoformat(),
        "expires_at": (NOW + timedelta(days=6)).isoformat(),
    }
    for key, value in overrides.items():
        if key == "digest":
            record["evidence_digest"] = value
        else:
            record[key] = value.isoformat() if isinstance(value, datetime) else value
    return json.dumps(record)


class _MemoryStore:
    def __init__(self, records: dict[str, str] | None = None) -> None:
        self.records = dict(records or {})

    def read(self, identifier: str) -> str | None:
        return self.records.get(identifier)


def _fresh(handoff: Handoff, **overrides: Any) -> _MemoryStore:
    return _MemoryStore({handoff_id(handoff): _approval_text(handoff, **overrides)})


# ---------------------------------------------------------------------------
# the digest
# ---------------------------------------------------------------------------


def test_the_digest_covers_everything_that_would_be_filed_and_where() -> None:
    base = evidence_digest(_handoff())
    assert base == evidence_digest(_handoff())
    for changed in (
        _handoff(suggested_issue_body="different body"),
        _handoff(suggested_issue_title="different title"),
        _handoff(claim="a different claim"),
        _handoff(source_revision="0" * 40),
        _handoff(repository="aspose-tex-foss/Aspose.TeX-FOSS-for-Python"),
        _handoff(evidence=(EvidenceEntry(path="pyproject.toml", detail="other"),)),
        _handoff(triggering_check=TriggeringCheck("BC-02", "3", "EXTRACTING")),
    ):
        assert evidence_digest(changed) != base


def test_lifecycle_fields_are_not_part_of_the_digest() -> None:
    filed = _handoff(status="FILED", issue_ref=IssueRef(number=1, url="https://x/issues/1"))
    assert evidence_digest(filed) == evidence_digest(_handoff())


def test_the_handoff_id_names_owner_name_and_fingerprint() -> None:
    assert (
        handoff_id(_handoff())
        == f"aspose-html-foss__Aspose.HTML-FOSS-for-Python__{FINGERPRINT[7:]}"
    )


# ---------------------------------------------------------------------------
# verify_approval: record shape
# ---------------------------------------------------------------------------


def test_a_valid_record_is_approved() -> None:
    handoff = _handoff()
    verdict = verify_approval(handoff, _fresh(handoff), now=lambda: NOW)
    assert verdict.approved is True
    assert verdict.record is not None
    assert verdict.record.approver == "owner-login"


def _edit(**changes: Any) -> Any:
    def mutate(text: str) -> str:
        record = json.loads(text)
        for key, value in changes.items():
            if value is None:
                del record[key]
            else:
                record[key] = value
        return json.dumps(record)

    return mutate


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (_edit(approver="github-actions[bot]"), "bot"),
        (_edit(approver=""), "approver"),
        (_edit(extra="field"), "unknown field"),
        (_edit(approved_at=None), "missing field"),
        (lambda t: "[1, 2]", "mapping"),
        (_edit(evidence_digest="md5:abc"), "evidence_digest"),
        (lambda t: "{not json", "JSON"),
        (_edit(repository="../evil"), "repository"),
        (_edit(approved_at="2026-10-05T10:00:00"), "timezone"),
        (_edit(approved_at=20261005), "timestamp"),
        (_edit(expires_at="soon"), "timestamp"),
    ],
)
def test_a_malformed_record_is_refused(mutation: Any, expected: str) -> None:
    handoff = _handoff()
    store = _MemoryStore({handoff_id(handoff): mutation(_approval_text(handoff))})
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert expected in verdict.reason


def test_a_standing_approval_longer_than_the_maximum_window_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(handoff, expires_at=NOW + MAX_APPROVAL_LIFETIME + timedelta(days=1))
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "standing authorization" in verdict.reason


def test_a_z_suffixed_timestamp_parses() -> None:
    handoff = _handoff()
    text = _approval_text(
        handoff, approved_at=NOW, expires_at=NOW + timedelta(days=3)
    ).replace("+00:00", "Z")
    assert parse_approval(text).expires_at == datetime(2026, 10, 8, 12, tzinfo=UTC)


# ---------------------------------------------------------------------------
# verify_approval: the required negative controls plus target binding
# ---------------------------------------------------------------------------


def test_no_record_is_refused() -> None:
    verdict = verify_approval(_handoff(), _MemoryStore(), now=lambda: NOW)
    assert verdict.approved is False
    assert "no approval record" in verdict.reason


def test_a_mismatched_digest_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(handoff, digest="sha256:" + "0" * 64)
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "approval digest mismatch" in verdict.reason


def test_a_handoff_changed_after_approval_needs_a_fresh_approval() -> None:
    original = _handoff()
    store = _fresh(original)
    edited = _handoff(suggested_issue_body="## Summary\n\nsomething the owner never read\n")
    store.records[handoff_id(edited)] = store.records[handoff_id(original)]
    verdict = verify_approval(edited, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "digest mismatch" in verdict.reason


def test_an_expired_record_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(
        handoff, approved_at=NOW - timedelta(days=10), expires_at=NOW - timedelta(days=3)
    )
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "expired" in verdict.reason


def test_a_record_dated_in_the_future_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(handoff, approved_at=NOW + timedelta(days=1), expires_at=NOW + timedelta(days=2))
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "future" in verdict.reason


def test_a_record_approving_another_repository_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(handoff, repository="aspose-tex-foss/Aspose.TeX-FOSS-for-Python")
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "target mismatch" in verdict.reason


def test_a_record_filed_under_another_handoffs_id_is_refused() -> None:
    handoff = _handoff()
    other = _handoff(defect_fingerprint="sha256:" + "1" * 64)
    store = _MemoryStore({handoff_id(handoff): _approval_text(other)})
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "different handoff" in verdict.reason


def test_an_untrusted_store_is_refused() -> None:
    class Untrusted:
        def read(self, identifier: str) -> str | None:
            raise ApprovalProvenanceError("the record was authored or committed by a bot identity")

    verdict = verify_approval(_handoff(), Untrusted(), now=lambda: NOW)
    assert verdict.approved is False
    assert "provenance" in verdict.reason


# ---------------------------------------------------------------------------
# GitApprovalStore: a record must be committed, human-authored, in the run's own commit
# ---------------------------------------------------------------------------


def _commit_record(
    repo: Path, handoff: Handoff, *, name: str = "Owner", email: str = "owner@example.com"
) -> None:
    target = repo / approval_relative_path(handoff_id(handoff))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_approval_text(handoff), encoding="utf-8")
    assert run_git(["config", "user.name", name], cwd=repo).returncode == 0
    assert run_git(["config", "user.email", email], cwd=repo).returncode == 0
    commit_all(repo, "approve a handoff")


def test_a_committed_human_record_is_read_and_verified(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    _commit_record(repo, handoff)
    verdict = verify_approval(handoff, GitApprovalStore(repo, "HEAD"), now=lambda: NOW)
    assert verdict.approved is True


def test_a_record_that_exists_only_in_the_working_tree_is_invisible(tmp_path: Path) -> None:
    """A file a step wrote during the run is not approval: only the checked-out commit is."""
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    target = repo / approval_relative_path(handoff_id(handoff))
    target.parent.mkdir(parents=True)
    target.write_text(_approval_text(handoff), encoding="utf-8")
    verdict = verify_approval(handoff, GitApprovalStore(repo, "HEAD"), now=lambda: NOW)
    assert verdict.approved is False
    assert "no approval record" in verdict.reason


def test_a_record_committed_after_the_trigger_commit_is_invisible(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    trigger = run_git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
    handoff = _handoff()
    _commit_record(repo, handoff)
    assert (
        verify_approval(handoff, GitApprovalStore(repo, trigger), now=lambda: NOW).approved
        is False
    )
    assert (
        verify_approval(handoff, GitApprovalStore(repo, "HEAD"), now=lambda: NOW).approved is True
    )


@pytest.mark.parametrize(
    ("name", "email"),
    [
        ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com"),
        ("CI", "bot[bot]@x.io"),
    ],
)
def test_a_bot_authored_record_is_refused(tmp_path: Path, name: str, email: str) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    _commit_record(repo, handoff, name=name, email=email)
    verdict = verify_approval(handoff, GitApprovalStore(repo, "HEAD"), now=lambda: NOW)
    assert verdict.approved is False
    assert "provenance" in verdict.reason and "bot" in verdict.reason


def test_a_shallow_clone_cannot_prove_who_introduced_the_record(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    _commit_record(repo, handoff)
    clone = tmp_path / "clone"
    result = run_git(["clone", "-q", "--depth", "1", repo.as_uri(), str(clone)], cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    verdict = verify_approval(handoff, GitApprovalStore(clone, "HEAD"), now=lambda: NOW)
    assert verdict.approved is False
    assert "shallow" in verdict.reason


def test_a_bad_ref_or_a_non_repository_fails_closed(tmp_path: Path) -> None:
    handoff = _handoff()
    with pytest.raises(ApprovalProvenanceError):
        GitApprovalStore(tmp_path, "--output=evil")
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    verdict = verify_approval(handoff, GitApprovalStore(plain, "HEAD"), now=lambda: NOW)
    assert verdict.approved is False
