"""The deterministic edits a Lane L correction wrote, as evidence for the review of the lines they wrote.

A Lane L detector such as ``stale_type_count`` writes a number it computed from SUPPORTED facts (385
public types = the type-level ``public_symbol`` facts it counted). That number appears in no fact
*value* and not in the live README, so the independent reviewer -- which sees fact values, not
counts -- faulted the edited line as an unsupported claim (PDF FOSS for Python, Cells FOSS for Go,
2026-11-10). The edit's derivation is the evidence, and only the evidence of that one written term:

* the review packet lists each applied edit (detector, original -> replacement, rationale, the
  SUPPORTED fact ids it cites) beside the changed lines it wrote, so the reviewer can judge the edit
  with its derivation in hand; and
* a finding that calls such a term unsupported, citing a line that edit wrote, with no other
  unevidenced term in its quote, is a contract error quoted back in the one re-ask. It is the same
  mechanism as :data:`llm_review.UNCHANGED_TEXT_ERROR`: nothing is cleared silently, and no
  ``unsupported_claim`` ever gets a clearance (``clearances.py``). The reviewer stays free to fault
  the edit for any other reason (a wrong place, an incoherent sentence), and every term of the quote
  that the edit did not write must still be evidenced by a fact value or the live README.

The number is not trusted on the edit's say-so: BC-14 rule (h) and ``claim_contradiction`` re-derive
it from the same facts over the final README (``lane_l_review.holdout_findings``), and a replacement
citing no SUPPORTED fact is never listed here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.review.audit import distinctive_terms
from repo_presenter.readme.review.matching import loosely_in

__all__ = [
    "APPLIED_EDITS_ERROR",
    "applied_edit_rows",
    "applied_edits_for_lines",
    "evidenced_edit_errors",
]

#: Detectors whose replacement is a value computed from the facts they cite (not a wording choice).
DERIVED_DETECTORS = frozenset({"stale_type_count", "stale_package_version"})

APPLIED_EDITS_ERROR = (
    "finding {finding}: the only term of this claim that nothing else evidences, {terms}, was "
    "written by the deterministic edit {detector} on line {line} ({original!r} -> {replacement!r}), "
    "which derives it from SUPPORTED facts {fact_ids} and which the validators re-derive from the "
    "same facts; it is evidenced. Withdraw this finding, or cite a different defect of the edit "
    "(where it was placed, how the sentence reads)"
)


def applied_edit_rows(edits: Sequence[Any], facts: FactsDocument) -> list[dict[str, Any]]:
    """The listable form of ``edits``: derived-value edits whose every cited fact is SUPPORTED."""
    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    rows: list[dict[str, Any]] = []
    for edit in edits:
        fact_ids = tuple(getattr(edit, "fact_ids", ()) or ())
        replacement = str(getattr(edit, "replacement", "") or "")
        if (
            getattr(edit, "detector", "") not in DERIVED_DETECTORS
            or not fact_ids
            or not replacement.strip()
            or not all(fact_id in supported for fact_id in fact_ids)
        ):
            continue
        rows.append(
            {
                "detector": edit.detector,
                "original": str(edit.original),
                "replacement": replacement,
                "rationale": str(edit.rationale),
                "fact_ids": list(fact_ids),
            }
        )
    return rows


def _has(line: str, replacement: str) -> bool:
    return re.search(rf"(?<![\w.]){re.escape(replacement.strip())}(?![\w])", line) is not None


def applied_edits_for_lines(
    rows: Sequence[Mapping[str, Any]], candidate_readme: str, lines: Sequence[int]
) -> list[dict[str, Any]]:
    """The edits among ``rows`` whose replacement text stands on any of the candidate ``lines``
    (1-based), each with the ``lines`` it stands on."""
    text = candidate_readme.splitlines()
    out: list[dict[str, Any]] = []
    for row in rows:
        where = [n for n in lines if 1 <= n <= len(text) and _has(text[n - 1], str(row["replacement"]))]
        if where:
            out.append({**row, "lines": where})
    return out


def evidenced_edit_errors(
    output: Mapping[str, Any],
    *,
    rows: Sequence[Mapping[str, Any]],
    candidate_readme: str,
    original_readme: str,
    facts: FactsDocument,
    changed: frozenset[int],
) -> list[str]:
    """Contract errors for ``unsupported_claim`` findings that fault only a term an applied
    deterministic edit wrote (see the module docstring). A finding that also names any other term no
    fact value or live-README text evidences is left to block."""
    if not rows:
        return []
    candidate_rows = candidate_readme.splitlines()
    supported = [fact for fact in facts.facts if fact.polarity == "SUPPORTED"]
    errors: list[str] = []
    for finding in output.get("findings", []) or []:
        if not isinstance(finding, Mapping) or finding.get("claim_kind") != "unsupported_claim":
            continue
        cited = [n for n in finding.get("lines") or [] if isinstance(n, int)]
        if not cited:
            continue
        first, last = min(cited), max(cited)
        span = [n for n in range(first, last + 1) if n in changed and 1 <= n <= len(candidate_rows)]
        quote = "\n".join(candidate_rows[n - 1] for n in range(first, last + 1) if 1 <= n <= len(candidate_rows))
        terms = distinctive_terms(quote)
        if not terms:
            continue
        for edit in applied_edits_for_lines(rows, candidate_readme, span):
            replacement = str(edit["replacement"]).strip()
            written = [t for t in terms if t == replacement]
            others = [t for t in terms if t != replacement]
            unevidenced = [
                t
                for t in others
                if not any(loosely_in(t, f.value) for f in supported) and not loosely_in(t, original_readme)
            ]
            if written and not unevidenced:
                errors.append(
                    APPLIED_EDITS_ERROR.format(
                        finding=finding.get("id", "?"),
                        terms=written,
                        detector=edit["detector"],
                        line=edit["lines"][0],
                        original=edit["original"],
                        replacement=replacement,
                        fact_ids=edit["fact_ids"][:4],
                    )
                )
                break
    return errors
