"""Shared handoff/file-result builders for the stage tests (tracking, labels, reopen, close)."""
from __future__ import annotations

from repo_presenter.issues.file import FileResult
from repo_presenter.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
)

REPO = "babar-raza/repo-presenter"
FP = "sha256:" + "a" * 64
T1 = "2026-11-04T10:00:00+00:00"
T2 = "2026-11-05T10:00:00+00:00"


def _handoff(revision: str = "r1", **kw) -> Handoff:
    base: dict = {
        "schema_version": 1, "repository": REPO, "source_revision": revision,
        "defect_fingerprint": FP,
        "triggering_check": TriggeringCheck(id="example:x", version="1", causal_stage="EXTRACTING"),
        "evidence": (EvidenceEntry(path="README.md", detail="line 4"),),
        "claim": "the example fails", "suggested_issue_title": "t", "suggested_issue_body": "b",
        "status": "HANDOFF_PENDING", "issue_ref": None, "defect_class": "EXAMPLE_FAILS",
    }
    base.update(kw)
    return Handoff(**base)


def _result(*, filed=True, number=7, reconciled=False, repo=REPO, fp=FP, issue=True) -> FileResult:
    return FileResult(
        repository=repo, defect_fingerprint=fp, authorized=True, filed=filed, reason="x",
        issue_ref=IssueRef(number, f"https://github.com/{REPO}/issues/{number}") if issue else None,
        reconciled=reconciled,
    )
