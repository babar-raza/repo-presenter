"""The typed shape of one upstream-defect handoff.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/issues/model.py``, 2026-10-24, per the owner's ruling that this repository adopts
the old repo's real, production-proven issue-automation model rather than inventing its own
(``project/state.yaml``'s ``DECIDE_NEXT_ISSUE_FILINGS``, ``docs/DECISION_LOG.md``'s 2026-10-24
entry). Zero external dependencies (stdlib only), so this is a clean, bounded port on its own --
nothing about this module needed adapting beyond the import path.

This module does not run a JSON-Schema validator itself; it is a typed reader that fails closed
on a shape the rest of the issue-automation pipeline cannot safely reason about.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

Status = Literal["HANDOFF_PENDING", "HANDOFF_ACKNOWLEDGED", "FILED", "RESOLVED_UPSTREAM"]
STATUSES: tuple[Status, ...] = (
    "HANDOFF_PENDING",
    "HANDOFF_ACKNOWLEDGED",
    "FILED",
    "RESOLVED_UPSTREAM",
)
_STATUSES_REQUIRING_ISSUE_REF = frozenset({"FILED", "RESOLVED_UPSTREAM"})

# Mirrors `gh issue close --reason`'s own two values -- the only two reasons a RESOLVED_UPSTREAM
# transition may ever carry: "completed" for a genuine upstream fix, "not planned" for a
# check-version change or a false positive. Never set for any other status.
CloseReason = Literal["completed", "not planned"]
CLOSE_REASONS: tuple[CloseReason, ...] = ("completed", "not planned")
_STATUSES_REQUIRING_CLOSE_REASON = frozenset({"RESOLVED_UPSTREAM"})

# The defect classes a handoff may name in its optional `defect_class` field. The ids are fixed
# here and would be mirrored in a schema's enum if/when one is added; a redetector/classifier
# registers behavior under each. Not every class here has a corresponding detector in this
# repository yet -- the set is carried over from the old repo's own vocabulary so a future
# detector's handoffs validate against a name already agreed, not a newly invented one.
DEFECT_CLASSES: tuple[str, ...] = (
    "LICENSE_MISSING_ROOT",
    "LICENSE_MISMATCH",
    "MANIFEST_PLACEHOLDER_METADATA",
    "README_MISSING_OR_PLACEHOLDER",
    "SOURCE_UNPARSEABLE",
    "BUILD_OR_TESTS_FAIL",
    "EXAMPLE_FAILS",
    "INSTALL_FAILS",
)


class HandoffError(ValueError):
    """A handoff artifact on disk does not have the shape the rest of the pipeline depends on."""


@dataclass(frozen=True)
class TriggeringCheck:
    """The exact check, or repository-level disposition, that fired."""

    id: str
    version: str
    causal_stage: Literal["EXTRACTING"]


@dataclass(frozen=True)
class EvidenceEntry:
    """One ``{path, detail}`` record -- the same shape ``Fact.evidence`` already uses."""

    path: str
    detail: str | None


@dataclass(frozen=True)
class IssueRef:
    """The filed issue this handoff became, once creation is authorized. Never set here."""

    number: int
    url: str


@dataclass(frozen=True)
class Handoff:
    """One evidence-backed upstream-defect handoff."""

    schema_version: int
    repository: str
    source_revision: str
    defect_fingerprint: str
    triggering_check: TriggeringCheck
    evidence: tuple[EvidenceEntry, ...]
    claim: str
    suggested_issue_title: str
    suggested_issue_body: str
    status: Status
    issue_ref: IssueRef | None
    close_reason: CloseReason | None = None
    # Optional and additive: absent on a handoff drafted before a class registry exists. When
    # set, it names the registry entry that detected the defect.
    defect_class: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        """The dedup ledger's own key: ``(repository, defect_fingerprint)``."""
        return (self.repository, self.defect_fingerprint)


def _require(payload: dict[str, Any], field: str, path: Path) -> Any:
    if field not in payload:
        raise HandoffError(f"{path}: missing required field {field!r}")
    return payload[field]


def handoff_from_dict(payload: dict[str, Any], *, path: Path) -> Handoff:
    """Build a `Handoff` from parsed JSON, failing closed on a missing or malformed field."""
    triggering = _require(payload, "triggering_check", path)
    if not isinstance(triggering, dict):
        raise HandoffError(f"{path}: triggering_check must be an object")
    triggering_check = TriggeringCheck(
        id=_require(triggering, "id", path),
        version=_require(triggering, "version", path),
        causal_stage=_require(triggering, "causal_stage", path),
    )
    if triggering_check.causal_stage != "EXTRACTING":
        raise HandoffError(
            f"{path}: triggering_check.causal_stage is {triggering_check.causal_stage!r}, "
            "not EXTRACTING"
        )
    raw_evidence = _require(payload, "evidence", path)
    if not isinstance(raw_evidence, list) or not raw_evidence:
        raise HandoffError(f"{path}: evidence must be a non-empty list")
    evidence = tuple(
        EvidenceEntry(path=_require(e, "path", path), detail=e.get("detail")) for e in raw_evidence
    )
    status = _require(payload, "status", path)
    if status not in STATUSES:
        raise HandoffError(f"{path}: unknown status {status!r}")
    raw_issue_ref = payload.get("issue_ref")
    issue_ref = (
        None
        if raw_issue_ref is None
        else IssueRef(number=raw_issue_ref["number"], url=raw_issue_ref["url"])
    )
    if status in _STATUSES_REQUIRING_ISSUE_REF and issue_ref is None:
        raise HandoffError(f"{path}: status {status!r} requires issue_ref to be set")
    if status not in _STATUSES_REQUIRING_ISSUE_REF and issue_ref is not None:
        raise HandoffError(f"{path}: status {status!r} must not carry an issue_ref")
    raw_close_reason = _require(payload, "close_reason", path)
    close_reason: CloseReason | None
    if raw_close_reason is None:
        close_reason = None
    elif raw_close_reason in CLOSE_REASONS:
        close_reason = raw_close_reason
    else:
        raise HandoffError(f"{path}: unknown close_reason {raw_close_reason!r}")
    if status in _STATUSES_REQUIRING_CLOSE_REASON and close_reason is None:
        raise HandoffError(f"{path}: status {status!r} requires close_reason to be set")
    if status not in _STATUSES_REQUIRING_CLOSE_REASON and close_reason is not None:
        raise HandoffError(f"{path}: status {status!r} must not carry a close_reason")
    defect_class = payload.get("defect_class")
    if defect_class is not None and defect_class not in DEFECT_CLASSES:
        raise HandoffError(f"{path}: unknown defect_class {defect_class!r}")
    return Handoff(
        schema_version=_require(payload, "schema_version", path),
        repository=_require(payload, "repository", path),
        source_revision=_require(payload, "source_revision", path),
        defect_fingerprint=_require(payload, "defect_fingerprint", path),
        triggering_check=triggering_check,
        evidence=evidence,
        claim=_require(payload, "claim", path),
        suggested_issue_title=_require(payload, "suggested_issue_title", path),
        suggested_issue_body=_require(payload, "suggested_issue_body", path),
        status=status,
        issue_ref=issue_ref,
        close_reason=close_reason,
        defect_class=defect_class,
    )


def load_handoff(path: Path) -> Handoff:
    """Read and parse one handoff artifact from disk."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"{path}: cannot read/parse as JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise HandoffError(f"{path}: top level must be a JSON object")
    return handoff_from_dict(payload, path=path)


def handoff_to_dict(handoff: Handoff) -> dict[str, Any]:
    """The JSON-serializable shape. ``defect_class`` is written only when set, so a handoff
    drafted without one serializes exactly as it did before the field existed."""
    payload = asdict(handoff)
    if payload["defect_class"] is None:
        del payload["defect_class"]
    return payload


def write_handoff(handoff: Handoff, path: Path) -> None:
    """Write a handoff artifact to disk -- to advance ``status``/``issue_ref`` on an existing
    one, or to author a genuinely new finding. Never a GitHub write either way."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(handoff_to_dict(handoff), indent=2, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
