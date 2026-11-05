"""Stage 8 (TRACKING): record what happened upstream onto the handoff, and keep an append-only
ledger of every distinct re-detection of the defect.

Pure: nothing here performs I/O except the explicit ``write_ledger``/``load_ledger`` helpers
(local files only, never a GitHub call), and ``apply_file_result`` returns new values instead of
mutating its arguments. A ledger entry is never edited or removed; recording the same
re-detection again is a no-op (idempotent), so replaying a result after a crash cannot inflate
the count. The handoff keeps its evidence, claim, fingerprint and every other field untouched --
only ``status``/``issue_ref``/``close_reason`` advance, exactly the lifecycle fields
``approval.evidence_digest`` already excludes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from repo_presenter.issues.file import FileResult
from repo_presenter.issues.model import Handoff, IssueRef

OccurrenceEvent = Literal["FILED", "DEDUPED", "RECONCILED", "REOPENED"]


class LedgerError(ValueError):
    """A ledger file on disk does not have the shape this module writes."""


@dataclass(frozen=True)
class OccurrenceEntry:
    """One re-detection of a defect. ``key`` is ``Handoff.key``; ``observed_at`` is supplied by
    the caller (this module never reads a clock); ``count`` is the 1-based position of this
    occurrence among the key's entries."""

    key: tuple[str, str]
    revision: str
    observed_at: str
    count: int
    issue_number: int
    event: OccurrenceEvent


@dataclass(frozen=True)
class TrackingUpdate:
    handoff: Handoff
    ledger: tuple[OccurrenceEntry, ...]


def _event(result: FileResult) -> OccurrenceEvent:
    if result.reopened:
        return "REOPENED"
    if result.filed:
        return "FILED"
    if result.reconciled:
        return "RECONCILED"
    return "DEDUPED"


def apply_file_result(
    handoff: Handoff,
    file_result: FileResult,
    *,
    observed_at: str,
    ledger: tuple[OccurrenceEntry, ...] = (),
) -> TrackingUpdate:
    """Advance ``handoff`` to ``FILED`` with ``file_result.issue_ref`` and append one ledger
    entry. A result with no ``issue_ref`` (a refusal or error) changes nothing. A result for a
    different repository or fingerprint raises ``ValueError``."""
    if (file_result.repository, file_result.defect_fingerprint) != handoff.key:
        raise ValueError("file result belongs to a different defect than this handoff")
    ref: IssueRef | None = file_result.issue_ref
    if ref is None:
        return TrackingUpdate(handoff, ledger)
    updated = replace(handoff, status="FILED", issue_ref=ref, close_reason=None)
    event = _event(file_result)
    for entry in ledger:
        if (entry.key, entry.revision, entry.issue_number, entry.event) == (
            handoff.key,
            handoff.source_revision,
            ref.number,
            event,
        ):
            return TrackingUpdate(updated, ledger)  # already recorded
    count = sum(1 for e in ledger if e.key == handoff.key) + 1
    entry = OccurrenceEntry(
        key=handoff.key,
        revision=handoff.source_revision,
        observed_at=observed_at,
        count=count,
        issue_number=ref.number,
        event=event,
    )
    return TrackingUpdate(updated, (*ledger, entry))


def _entry_to_dict(e: OccurrenceEntry) -> dict[str, Any]:
    return {
        "repository": e.key[0],
        "defect_fingerprint": e.key[1],
        "revision": e.revision,
        "observed_at": e.observed_at,
        "count": e.count,
        "issue_number": e.issue_number,
        "event": e.event,
    }


def write_ledger(ledger: tuple[OccurrenceEntry, ...], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps([_entry_to_dict(e) for e in ledger], indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def load_ledger(path: Path) -> tuple[OccurrenceEntry, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise LedgerError(f"{path}: top level must be a JSON list")
        return tuple(
            OccurrenceEntry(
                key=(d["repository"], d["defect_fingerprint"]),
                revision=d["revision"],
                observed_at=d["observed_at"],
                count=int(d["count"]),
                issue_number=int(d["issue_number"]),
                event=d["event"],
            )
            for d in payload
        )
    except LedgerError:
        raise
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise LedgerError(f"{path}: cannot read ledger: {exc}") from exc
