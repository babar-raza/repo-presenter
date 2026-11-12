"""TC-014 M9: SCORING LOGIC for the independent sampled audit.

Pure arithmetic over already-computed inputs: completed audit findings, a decrypted seed
manifest (``seed.py``'s records, already decrypted by whatever later hosted step holds the real
key - this module never calls ``seed.decrypt_seed_manifest`` itself), and caller-supplied sets of
clean-control / unseeded-accepted candidate ids. No provider call, no network, no subprocess, no
filesystem access.

Computes the three numbers the M9 protocol gates on
(``docs/design/2026-11-06-acceptance-redesign.md`` section 4.3):

* **seeded recall** - of the seeded (non-clean) defects, the fraction the auditor's findings
  correctly flagged at the right candidate and the right line.
* **false-flag rate** - of the clean-control candidates, the fraction the auditor incorrectly
  flagged any defect on.
* **defective-accepted rate** - of unseeded, already-accepted candidates in the sample, the
  fraction with at least one class A/D/D9 finding (design doc section 4.3's ladder: 0 of the
  first 5, then <= 1 of 10, <= 2 of 25 - this module computes the rate; the ladder threshold
  itself is a gate-time decision outside this card's scope).

Verdict semantics this module relies on. A ``Finding`` carries only
``candidate_id, claim, verdict (supported|false|unverifiable), path, line`` - there is no separate
"defect class" field on a finding. The class-audit definitions ``seed.py`` seeds make the mapping
to this three-valued verdict unambiguous without one: a class A or D9 defect is a FALSE checkable
claim once seeded, so a correct catch is ``verdict == "false"``; a class D defect is an UNGROUNDED
claim that is neither provably true nor false, so a correct catch is ``verdict == "unverifiable"``.
So "the auditor flagged a defect at this location" is simply ``verdict != "supported"``, for any
shape ``seed.py`` seeds there (including D14/D15, which M9's own design-doc gate does not require
seeding blind but ``seed.py`` builds anyway for reuse by M8's corpus - see that module's
docstring). This module never assumes which shapes are present; it scores whatever the caller's
manifest and finding population actually contain.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE

__all__ = [
    "Finding",
    "AuditMetric",
    "AuditScorecard",
    "ScoringError",
    "FLAGGED_VERDICTS",
    "seeded_recall",
    "false_flag_rate",
    "defective_accepted_rate",
    "score_audit_batch",
]

Verdict = Literal["supported", "false", "unverifiable"]

#: A finding counts as "the auditor flagged a defect here" for any verdict other than
#: ``supported`` - see the module docstring for why ``false``/``unverifiable`` together cover
#: every seeded shape without a separate defect-class field on ``Finding``.
FLAGGED_VERDICTS: frozenset[str] = frozenset({"false", "unverifiable"})


class ScoringError(ValueError):
    """Raised on an empty population (never a vacuous rate) or a malformed finding/seed-record
    mapping missing a required key."""


@dataclass(frozen=True)
class Finding:
    """One completed audit finding: a claim the auditor checked, with ``path:line`` evidence that
    code outside this module re-checks exists and holds the cited text (this module trusts that
    the caller already did so - it only counts verdicts)."""

    candidate_id: str
    claim: str
    verdict: Verdict
    path: str
    line: int


@dataclass(frozen=True)
class AuditMetric:
    """``matched`` out of ``total`` - the common shape of all three gate numbers this module
    computes. ``total`` is never zero: an empty population is a ``ScoringError``, never a vacuous
    ``rate`` of ``0.0`` or ``1.0`` that could be misread as a passing or failing measurement that
    was never actually taken."""

    matched: int
    total: int

    def __post_init__(self) -> None:
        if self.total <= 0:
            raise ScoringError("cannot compute a rate over an empty population (total <= 0)")
        if not (0 <= self.matched <= self.total):
            raise ScoringError(
                f"matched ({self.matched}) must be between 0 and total ({self.total})"
            )

    @property
    def rate(self) -> float:
        return self.matched / self.total


@dataclass(frozen=True)
class AuditScorecard:
    """The three gate numbers for one audit batch, bundled."""

    seeded_recall: AuditMetric
    false_flag_rate: AuditMetric
    defective_accepted_rate: AuditMetric


def _as_finding(item: Finding | Mapping[str, Any]) -> Finding:
    if isinstance(item, Finding):
        return item
    try:
        return Finding(
            candidate_id=item["candidate_id"],
            claim=item.get("claim", ""),
            verdict=item["verdict"],
            path=item.get("path", ""),
            line=item["line"],
        )
    except KeyError as error:
        raise ScoringError(f"finding is missing required key {error}") from error


def _seed_record_identity(record: Mapping[str, Any]) -> tuple[str, str, int]:
    """``(candidate_id, shape, line)`` for one decrypted seed-manifest entry, failing closed (a
    ``ScoringError``, never a silent default) when a non-clean record lacks the ``line`` a real
    seeding call always attaches."""
    try:
        candidate_id = record["candidate_id"]
        shape = record["shape"]
    except KeyError as error:
        raise ScoringError(f"seed record is missing required key {error}") from error
    if shape == CLEAN_SHAPE:
        return candidate_id, shape, -1
    line = record.get("line")
    if line is None:
        raise ScoringError(
            f"seeded record for candidate {candidate_id!r} (shape {shape!r}) has no line"
        )
    return candidate_id, shape, line


def _is_caught(candidate_id: str, line: int, findings: Sequence[Finding]) -> bool:
    return any(
        finding.candidate_id == candidate_id
        and finding.line == line
        and finding.verdict in FLAGGED_VERDICTS
        for finding in findings
    )


def _is_flagged_at_all(candidate_id: str, findings: Sequence[Finding]) -> bool:
    return any(
        finding.candidate_id == candidate_id and finding.verdict in FLAGGED_VERDICTS
        for finding in findings
    )


def seeded_recall(
    findings: Iterable[Finding | Mapping[str, Any]],
    seed_records: Iterable[Mapping[str, Any]],
) -> AuditMetric:
    """Of the SEEDED (non-clean) records in ``seed_records`` (the decrypted seed manifest), the
    fraction with a finding on the same ``candidate_id`` at the same ``line`` and a verdict other
    than ``supported``. Raises ``ScoringError`` if ``seed_records`` contains zero non-clean
    records - seeded recall is undefined, not zero, over an empty seeded population."""
    resolved_findings = [_as_finding(item) for item in findings]
    seeded = [
        identity
        for identity in (_seed_record_identity(record) for record in seed_records)
        if identity[1] != CLEAN_SHAPE
    ]
    if not seeded:
        raise ScoringError("seeded_recall: no seeded (non-clean) records given")
    matched = sum(
        1
        for candidate_id, _shape, line in seeded
        if _is_caught(candidate_id, line, resolved_findings)
    )
    return AuditMetric(matched=matched, total=len(seeded))


def false_flag_rate(
    findings: Iterable[Finding | Mapping[str, Any]],
    clean_control_ids: Iterable[str],
) -> AuditMetric:
    """Of the clean-control candidate ids, the fraction the auditor incorrectly flagged ANY
    defect on (any finding with a verdict other than ``supported``). Raises ``ScoringError`` on
    an empty ``clean_control_ids``."""
    resolved_findings = [_as_finding(item) for item in findings]
    ids = list(clean_control_ids)
    if not ids:
        raise ScoringError("false_flag_rate: no clean-control candidate ids given")
    matched = sum(1 for candidate_id in ids if _is_flagged_at_all(candidate_id, resolved_findings))
    return AuditMetric(matched=matched, total=len(ids))


def defective_accepted_rate(
    findings: Iterable[Finding | Mapping[str, Any]],
    unseeded_accepted_ids: Iterable[str],
) -> AuditMetric:
    """Of the unseeded, already-accepted candidate ids in the sample, the fraction with at least
    one class A/D/D9 finding - operationally, any finding with a verdict other than ``supported``
    (see the module docstring for why that is the right proxy with this ``Finding`` schema).
    Raises ``ScoringError`` on an empty ``unseeded_accepted_ids``."""
    resolved_findings = [_as_finding(item) for item in findings]
    ids = list(unseeded_accepted_ids)
    if not ids:
        raise ScoringError("defective_accepted_rate: no unseeded accepted candidate ids given")
    matched = sum(1 for candidate_id in ids if _is_flagged_at_all(candidate_id, resolved_findings))
    return AuditMetric(matched=matched, total=len(ids))


def score_audit_batch(
    findings: Iterable[Finding | Mapping[str, Any]],
    seed_records: Iterable[Mapping[str, Any]],
    clean_control_ids: Iterable[str],
    unseeded_accepted_ids: Iterable[str],
) -> AuditScorecard:
    """All three gate numbers for one audit batch, computed from the same ``findings`` list.
    ``findings`` is consumed once per metric (each call re-iterates it), so a generator must be
    materialised by the caller first if it is not already a concrete sequence."""
    findings = list(findings)
    return AuditScorecard(
        seeded_recall=seeded_recall(findings, seed_records),
        false_flag_rate=false_flag_rate(findings, clean_control_ids),
        defective_accepted_rate=defective_accepted_rate(findings, unseeded_accepted_ids),
    )
