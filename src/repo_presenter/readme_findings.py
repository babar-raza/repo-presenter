"""The findings register: every defect either lane detects gets exactly one durable row.

TC-025 point 3: today a defect a detector cannot repair is reported inside one run's own
artifacts (``corrections.json``'s ``unapplied`` list, a Lane R review's blocking findings) and
nowhere else -- there is no portfolio-wide, cross-run view of what is still owed. This module is
that view: a small, append-only (by dedup key) JSON register, read and written only through the
two functions below, over whatever path the caller gives them.

``data/readme_findings.json`` is the register this repository actually runs against -- the
supervisor seeds it empty (``{"schema_version": 1, "findings": []}``); ``ops/gatectl.py``'s
``GLOBAL_DENY`` forbids any taskcard, this one included, from declaring ``data/**`` as a
``write_path``, so this module is written and tested against temporary fixture copies only. The
real file is only ever touched by a real pipeline run that imports this module and calls
``append_finding`` with its own path (the default), never by a test and never by this card's own
commit.

A finding's identity is ``(repository, description)``: a later run that reports the very same
repository and description updates that one row in place (its evidence, route and status
refreshed; its ``first_seen_at`` kept, so age is the time since it was FIRST seen, never reset by
being seen again) rather than appending a duplicate. A finding not reported again on a later run is
left exactly as it was -- it ages, it is never silently dropped; only an explicit
``resolve_finding`` call (recording that the defect is gone) moves it to ``RESOLVED``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_FINDINGS_PATH = Path("data/readme_findings.json")

#: Which lane owns a finding going forward. A defect found while an R5(a) upstream-change trigger
#: was present is ``LANE_L``'s to repair (or refuse and hand to Lane R itself, same as today); a
#: defect found with no upstream trigger at all is routed straight to ``LANE_R`` as an owned,
#: visible finding -- never silently dropped for lack of a reason to run Lane L again.
LANE_L = "lane_l"
LANE_R = "lane_r"
ROUTES: tuple[str, ...] = (LANE_L, LANE_R)

STATUS_OPEN = "OPEN"
STATUS_RESOLVED = "RESOLVED"
STATUSES: tuple[str, ...] = (STATUS_OPEN, STATUS_RESOLVED)


class FindingsRegisterError(ValueError):
    """The findings register file (or a call against it) is not the shape this module owns."""


@dataclass(frozen=True)
class FindingRecord:
    """One row: a repository's one named defect, where it is owned, and its state."""

    repository: str
    description: str
    evidence: str
    route: str
    status: str
    first_seen_at: str  # ISO 8601 date ("YYYY-MM-DD"); the register names no machine or time of day
    resolved_at: str | None = None
    #: Optional "must-correct" obligation (owner priority: Lane R candidates sealed with real,
    #: independently confirmed false claims). ``quote`` is the exact README text that is wrong,
    #: ``truth`` one sentence of what the source says instead; ``evidence`` carries the
    #: ``path:line@revision`` that proves it. Both default to empty and are written to the register
    #: only when set, so a row without them is byte-identical to the original schema and every
    #: pre-existing register still loads.
    quote: str = ""
    truth: str = ""

    def __post_init__(self) -> None:
        if not self.repository:
            raise FindingsRegisterError("a finding needs a repository")
        if not self.description:
            raise FindingsRegisterError("a finding needs a description")
        if self.route not in ROUTES:
            raise FindingsRegisterError(f"unknown route {self.route!r}; expected one of {ROUTES}")
        if self.status not in STATUSES:
            raise FindingsRegisterError(
                f"unknown status {self.status!r}; expected one of {STATUSES}"
            )
        _parse_date(self.first_seen_at, field="first_seen_at")
        if self.resolved_at is not None:
            _parse_date(self.resolved_at, field="resolved_at")
        if self.status == STATUS_OPEN and self.resolved_at is not None:
            raise FindingsRegisterError("an OPEN finding carries no resolved_at")
        if self.status == STATUS_RESOLVED and self.resolved_at is None:
            raise FindingsRegisterError("a RESOLVED finding needs a resolved_at")

    def age_days(self, *, today: date | None = None) -> int:
        """How many days since this finding was first seen (never since it was last touched)."""
        now = today if today is not None else date.today()
        return (now - _parse_date(self.first_seen_at, field="first_seen_at")).days

    def key(self) -> tuple[str, str]:
        """The dedup identity: a later report of the same repository and description is this same
        row, updated in place, never a duplicate."""
        return (self.repository, self.description)

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "repository": self.repository,
            "description": self.description,
            "evidence": self.evidence,
            "route": self.route,
            "status": self.status,
            "first_seen_at": self.first_seen_at,
            "resolved_at": self.resolved_at,
        }
        if self.quote:
            record["quote"] = self.quote
        if self.truth:
            record["truth"] = self.truth
        return record

    @classmethod
    def from_record(cls, raw: Any) -> FindingRecord:
        if not isinstance(raw, dict):
            raise FindingsRegisterError(f"a finding record must be an object, not {type(raw)!r}")
        try:
            return cls(
                repository=str(raw["repository"]),
                description=str(raw["description"]),
                evidence=str(raw.get("evidence", "")),
                route=str(raw["route"]),
                status=str(raw["status"]),
                first_seen_at=str(raw["first_seen_at"]),
                resolved_at=None if raw.get("resolved_at") is None else str(raw["resolved_at"]),
                quote=str(raw.get("quote") or ""),
                truth=str(raw.get("truth") or ""),
            )
        except KeyError as exc:
            raise FindingsRegisterError(f"a finding record is missing {exc.args[0]!r}") from exc


def _parse_date(value: str, *, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise FindingsRegisterError(f"{field} must be an ISO 8601 date, not {value!r}") from exc


def read_findings(path: Path = DEFAULT_FINDINGS_PATH) -> list[FindingRecord]:
    """Every row on record at ``path``, in the file's own order. A missing file is an empty
    register (the supervisor's own seed, ``{"schema_version": 1, "findings": []}``, is not the
    only honest starting point -- a path nothing has written yet means the same thing)."""
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FindingsRegisterError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
        raise FindingsRegisterError(
            f"{path} does not carry schema_version {SCHEMA_VERSION}: {raw.get('schema_version') if isinstance(raw, dict) else raw!r}"
        )
    findings = raw.get("findings", [])
    if not isinstance(findings, list):
        raise FindingsRegisterError(f"{path}'s findings must be a list")
    return [FindingRecord.from_record(row) for row in findings]


def _write(path: Path, records: list[FindingRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=lambda record: record.key())
    document = {
        "schema_version": SCHEMA_VERSION,
        "findings": [record.to_record() for record in ordered],
    }
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def append_finding(
    path: Path = DEFAULT_FINDINGS_PATH,
    *,
    repository: str,
    description: str,
    evidence: str,
    route: str,
    first_seen_at: str,
    status: str = STATUS_OPEN,
    quote: str | None = None,
    truth: str | None = None,
) -> FindingRecord:
    """Record one defect a lane's own detectors found. A finding already on record for this exact
    ``(repository, description)`` is updated in place (its evidence, route and status refreshed,
    its ``first_seen_at`` left exactly as it was); otherwise a new row is appended. Returns the
    row as it stands after the write. ``quote``/``truth`` (the must-correct obligation) are set
    when given and otherwise left as the existing row has them."""
    records = read_findings(path)
    index_by_key = {record.key(): index for index, record in enumerate(records)}
    key = (repository, description)
    if key in index_by_key:
        index = index_by_key[key]
        resolved_at = records[index].resolved_at if status == STATUS_RESOLVED else None
        updated = replace(
            records[index],
            evidence=evidence,
            route=route,
            status=status,
            resolved_at=resolved_at,
            quote=records[index].quote if quote is None else quote,
            truth=records[index].truth if truth is None else truth,
        )
        records[index] = updated
    else:
        updated = FindingRecord(
            repository=repository,
            description=description,
            evidence=evidence,
            route=route,
            status=status,
            first_seen_at=first_seen_at,
            quote=quote or "",
            truth=truth or "",
        )
        records.append(updated)
    _write(path, records)
    return updated


def resolve_finding(
    path: Path = DEFAULT_FINDINGS_PATH,
    *,
    repository: str,
    description: str,
    resolved_at: str,
) -> FindingRecord | None:
    """Mark the ``(repository, description)`` row RESOLVED as of ``resolved_at``; idempotent (a
    second call with the same inputs changes nothing further). Returns the updated row, or None
    when no such row is on record (resolving a finding nothing ever reported is not an error the
    caller needs to handle, but it changes nothing)."""
    records = read_findings(path)
    for index, record in enumerate(records):
        if record.key() == (repository, description):
            updated = replace(record, status=STATUS_RESOLVED, resolved_at=resolved_at)
            records[index] = updated
            _write(path, records)
            return updated
    return None


def must_correct_rows(
    repository: str, path: Path = DEFAULT_FINDINGS_PATH
) -> list[FindingRecord]:
    """The OPEN Lane R rows of one repository that carry a ``quote``: the false README claims a
    candidate for that repository must not print (``readme/validation/must_correct.py``, BC-18).
    A missing register is an empty list; an unreadable one raises ``FindingsRegisterError``, which
    the blocking check treats as "nothing owed"."""
    return [
        record
        for record in read_findings(path)
        if record.repository == repository
        and record.route == LANE_R
        and record.status == STATUS_OPEN
        and record.quote
    ]
