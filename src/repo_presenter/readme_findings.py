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

import hashlib
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

#: How a disposition cites a register row as its evidence (``FindingRecord.citation_id``): the
#: row's stable key, hashed, under a prefix no fact kind uses. ``core/llm/binding.py`` accepts such
#: an ID only when it names an OPEN must-correct row of the very repository being judged
#: (``readme/validation/must_correct.py::open_finding_citations``), so a model cannot invent one.
CITATION_PREFIX = "finding:"


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

    def citation_id(self) -> str:
        """The ID a disposition cites this row by: ``finding:`` and 12 hex digits of the sha256 of
        its dedup key. Stable for as long as the row is (its key never changes), and unique per
        repository, so a citation can never be read as another repository's row."""
        digest = hashlib.sha256(f"{self.repository}\n{self.description}".encode())
        return CITATION_PREFIX + digest.hexdigest()[:12]

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


#: How a row records that its claim was disproved rather than fixed: a RESOLVED row whose
#: ``evidence`` starts with this word (the 2026-11-13 convention, e.g. the two Email .NET 26.7.0
#: rows a SUPPORTED registry fact refuted). The schema has OPEN/RESOLVED only; a refuted row is
#: RESOLVED with this marker and is never a regression check -- its quote may be true text.
REFUTED_MARKER = "REFUTED"


def is_refuted(record: FindingRecord) -> bool:
    """Whether ``record`` was disproved (its claim was true after all), not corrected."""
    return record.evidence.lstrip().upper().startswith(REFUTED_MARKER)


def regression_rows(
    repository: str, route: str = LANE_R, path: Path = DEFAULT_FINDINGS_PATH
) -> list[FindingRecord]:
    """Every quoted row of one repository and route that is a permanent regression check (owner,
    2026-11-13: "an already caught problem should not reappear"): OPEN rows (owed a correction)
    AND RESOLVED rows (corrected once; printing the quote again is a regression), never a refuted
    row (``is_refuted``). BC-18 (``readme/validation/must_correct.py``) fails a candidate of that
    route that prints any of these quotes. A missing register is an empty list; an unreadable one
    raises ``FindingsRegisterError``."""
    return [
        record
        for record in read_findings(path)
        if record.repository == repository
        and record.route == route
        and record.quote
        and not is_refuted(record)
    ]


# --- importing an independent fact-check review ------------------------------------------------

#: The verdicts of an independent fact-check review that are factual defects and become register
#: rows. ``INTERNAL_WORDING`` and ``MISPLACED`` are owned by deterministic checks (BL-002, BL-004)
#: and are imported only when an item says ``"register": true`` (also factually wrong).
FACTUAL_VERDICTS: tuple[str, ...] = ("FALSE", "UNSUPPORTED", "MISLEADING")


def _squashed(text: str) -> str:
    return " ".join(text.split())


def review_description(verdict: str, quote: str) -> str:
    """The dedup description of an imported review row: the verdict and the quote's first 90
    characters (the a963daa convention, ``confirmed false claim: <quote[:90]>``)."""
    return f"confirmed {verdict.strip().lower()} claim: {_squashed(quote)[:90]}"


def import_review(
    path: Path,
    *,
    repository: str,
    readme: str,
    items: list[dict[str, Any]],
    first_seen_at: str,
    route: str = LANE_R,
) -> tuple[list[FindingRecord], list[tuple[dict[str, Any], str]]]:
    """Register one repository's independent fact-check items as OPEN rows (``append_finding``,
    so a re-import updates in place and never duplicates). Returns ``(registered, skipped)``,
    each skipped item with its reason.

    An item is ``{"quote", "verdict", "truth", "evidence"}`` plus optional ``"register"`` (bool;
    default: the verdict is in ``FACTUAL_VERDICTS``) and ``"occurrences"`` (int, default 1). The
    quote must be the README's exact text (whitespace-squashed, as BC-18 matches) and printed
    exactly ``occurrences`` times in ``readme`` -- an over-broad quote that also matches correct
    text (the 2026-11-13 bare ``dotnet build`` row) is refused, never registered. Nothing is
    written unless every item to register passes."""
    text = _squashed(readme)
    planned: list[dict[str, Any]] = []
    skipped: list[tuple[dict[str, Any], str]] = []
    problems: list[str] = []
    for item in items:
        verdict = str(item.get("verdict", "")).upper()
        wanted = item.get("register")
        if wanted is None:
            wanted = verdict in FACTUAL_VERDICTS
        if not wanted:
            skipped.append((item, str(item.get("skip_reason") or f"verdict {verdict} not registered")))
            continue
        quote = str(item.get("quote", ""))
        expected = int(item.get("occurrences", 1))
        found = text.count(_squashed(quote)) if _squashed(quote) else 0
        if found != expected:
            problems.append(f"quote printed {found} time(s), expected {expected}: {quote[:80]!r}")
            continue
        if not str(item.get("truth", "")).strip() or not str(item.get("evidence", "")).strip():
            problems.append(f"quote has no truth or evidence: {quote[:80]!r}")
            continue
        planned.append(item)
    if problems:
        raise FindingsRegisterError(f"{repository}: " + "; ".join(problems))
    registered = [
        append_finding(
            path,
            repository=repository,
            description=review_description(str(item["verdict"]), str(item["quote"])),
            evidence=str(item["evidence"]),
            route=route,
            first_seen_at=first_seen_at,
            quote=str(item["quote"]),
            truth=str(item["truth"]),
        )
        for item in planned
    ]
    return registered, skipped


def main(argv: list[str] | None = None) -> int:
    """``python -m repo_presenter.readme_findings import --repository R --readme README.md
    --review items.json --date YYYY-MM-DD [--register PATH]``: register a review's factual items."""
    import argparse

    parser = argparse.ArgumentParser(prog="repo_presenter.readme_findings")
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="register an independent fact-check review's items")
    imp.add_argument("--repository", required=True)
    imp.add_argument("--readme", type=Path, required=True, help="the reviewed (sealed) README")
    imp.add_argument("--review", type=Path, required=True, help="JSON list of review items")
    imp.add_argument("--date", required=True, help="first_seen_at, YYYY-MM-DD")
    imp.add_argument("--register", type=Path, default=DEFAULT_FINDINGS_PATH)
    args = parser.parse_args(argv)
    raw = json.loads(args.review.read_text(encoding="utf-8"))
    items = raw.get("items", raw) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        print(f"FAIL: {args.review} holds no item list")
        return 1
    try:
        registered, skipped = import_review(
            args.register,
            repository=args.repository,
            readme=args.readme.read_text(encoding="utf-8"),
            items=items,
            first_seen_at=args.date,
        )
    except FindingsRegisterError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"{args.repository}: registered {len(registered)}, skipped {len(skipped)}")
    for item, reason in skipped:
        print(f"  skipped [{item.get('verdict')}] {str(item.get('quote', ''))[:70]!r}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
