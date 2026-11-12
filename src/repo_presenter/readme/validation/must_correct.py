"""BC-18: a false claim the findings register owes a correction for is no longer printed.

The register (``readme_findings``) holds, per repository, the exact README text an independent
reviewer confirmed false (``quote``) and the one sentence of what the source says (``truth``).
Nothing in the pipeline used to force the candidate to stop printing it: a Lane R candidate could
seal with the claim intact. This check fails while an OPEN Lane R row's quote is still in the
rendered README, and names where it is printed so the existing per-unit S4 patch (an inherited unit,
``repair/loop.py::_repair_reconciliation``) or per-section S6 repair (an authored section) is handed
the quote and the truth as its instruction.

It is a no-op -- and so changes no existing seal's outcome -- when the register is missing, empty or
unreadable for the repository, when the candidate is Lane L, or when no open row carries a quote.
"""

from __future__ import annotations

from repo_presenter.readme.validation.failures import Candidate, Failure
from repo_presenter.readme.validation.text import section_texts
from repo_presenter.readme.validation.units import placements_of
from repo_presenter.readme_findings import (
    DEFAULT_FINDINGS_PATH,
    FindingRecord,
    FindingsRegisterError,
    must_correct_rows,
)


def _squash(text: str) -> str:
    return " ".join(text.split())


def _instruction(row: FindingRecord) -> str:
    truth = row.truth or "remove or correct the claim"
    return (
        f"The README text {row.quote!r} is false ({row.description}). Correct it: {truth}"
        + (f" (evidence: {row.evidence})" if row.evidence else "")
    )


def must_correct_failures(candidate: Candidate) -> list[Failure]:
    """One failure per place an open register quote is still printed."""
    if candidate.lane.upper() in ("L", "LANE_L"):
        return []
    try:
        rows = must_correct_rows(
            candidate.entry.repository,
            candidate.findings_path if candidate.findings_path is not None else DEFAULT_FINDINGS_PATH,
        )
    except (OSError, ValueError, FindingsRegisterError):
        return []
    if not rows:
        return []
    readme = _squash(candidate.readme)
    printed = [row for row in rows if _squash(row.quote) in readme]
    if not printed:
        return []
    placed = [(p.unit_id, _squash(p.text)) for p in placements_of(candidate) if p.outcome == "placed"]
    sections = {name: _squash(text) for name, text in section_texts(candidate.readme).items()}
    failures: list[Failure] = []
    for row in printed:
        quote = _squash(row.quote)
        instruction = _instruction(row)
        detail = f"open finding ({row.description}) still printed: {instruction}"
        units = [unit for unit, text in placed if quote in text]
        if units:
            failures.extend(
                Failure("RECONCILING", detail, unit=unit, quote=row.quote, instruction=instruction)
                for unit in units
            )
            continue
        named = [name for name, text in sections.items() if quote in text]
        failures.extend(
            Failure("COMPOSING", detail, section=name, quote=row.quote, instruction=instruction)
            for name in (named or [None])
        )
    return failures
