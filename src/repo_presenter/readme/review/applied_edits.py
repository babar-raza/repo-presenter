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
from repo_presenter.readme.review.verdict import MODEL_ACCEPT, REJECT_VERDICTS

__all__ = [
    "APPLIED_EDITS_ERROR",
    "WORDING_DETECTORS",
    "drop_carried_claim_findings",
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


#: Detectors whose edit only renames a thing the maintainers' sentence already states (BL-870): the
#: aspose.com product's proper name ("the commercial Aspose.PDF for .NET" -> "Aspose.PDF for .NET --
#: Enterprise Edition", the mission naming rule). The edit asserts nothing the sentence did not, so the
#: rest of the line is still the maintainers' own text and the Lane L review (which judges THE EDITS)
#: is not asked about it. Every detector that writes a value or a description (counts, versions, member
#: lists) is deliberately absent: its line is the edit's claim and stays reviewed.
WORDING_DETECTORS = frozenset({"enterprise_edition_naming"})

CARRIED_CLAIM_NOTE = (
    "the cited line equals a live-README line once the wording-only edit {detector} ({replacement!r} "
    "replaced {original!r}) is undone, so the claim is the maintainers' own sentence that this edit "
    "only renamed a product in; a Lane L review judges the edits, not the carried text (BL-870)"
)


def _squashed(text: str) -> str:
    return " ".join(text.split())


def drop_carried_claim_findings(
    reply: Any,
    *,
    all_edits: Sequence[Mapping[str, Any]],
    candidate_readme: str,
    original_readme: str,
    changed: frozenset[int],
) -> list[dict[str, Any]]:
    """Remove each ``unsupported_claim`` finding whose every cited line is a live-README line that a
    wording-only edit renamed a product in (BL-870; hosted Lane L PDF Cpp run 45007577791, F01: the
    opening's "strict subset of Aspose.PDF for .NET -- Enterprise Edition library" faulted as unsupported,
    when the maintainers wrote "strict subset of the commercial Aspose.PDF for .NET library" and the
    only edit renamed the product).

    ``all_edits`` is every edit of the run as ``original``/``replacement`` rows (``edit_rows``). A line
    qualifies only when every edit whose replacement stands on it is wording-only and undoing them gives
    a line the live README has verbatim (whitespace aside): a line any other
    edit wrote (a count, a description, a version) is never void, and neither is a finding of another
    kind. Same bookkeeping as ``reply.drop_maintainer_unsupported_findings``: each drop is noted in
    ``reply[CONTRACT_NOTES_KEY]``, and a reject verdict left with no finding becomes ACCEPT. Idempotent."""
    findings = reply.get("findings") if isinstance(reply, dict) else None
    if not isinstance(findings, list) or not findings or not all_edits:
        return []
    candidate = candidate_readme.splitlines()
    live = {_squashed(row) for row in original_readme.splitlines() if row.strip()}
    kept: list[Any] = []
    notes: list[dict[str, Any]] = []
    for finding in findings:
        cited = finding.get("lines") if isinstance(finding, dict) else None
        verdict_note = None
        if (
            isinstance(finding, dict)
            and finding.get("claim_kind") == "unsupported_claim"
            and isinstance(cited, list)
            and cited
            and all(isinstance(n, int) and 1 <= n <= len(candidate) for n in cited)
        ):
            written = [n for n in range(min(cited), max(cited) + 1) if candidate[n - 1].strip()]
            reverted_by: list[Mapping[str, Any]] = []
            ok = bool(written) and all(n in changed for n in written)
            for number in written if ok else ():
                line = candidate[number - 1]
                standing = [
                    edit for edit in all_edits if str(edit["replacement"]).strip() and str(edit["replacement"]) in line
                ]
                for edit in standing:
                    line = line.replace(str(edit["replacement"]), str(edit["original"]), 1)
                if (
                    _squashed(line) not in live
                    or not standing
                    or any(edit.get("detector") not in WORDING_DETECTORS for edit in standing)
                ):
                    ok = False
                    break
                reverted_by.extend(standing)
            if ok:
                first = next(edit for edit in reverted_by if edit.get("detector") in WORDING_DETECTORS)
                verdict_note = {
                    "rule": "BL-870",
                    "dropped_finding": str(finding.get("id", "?")),
                    "claim_kind": "unsupported_claim",
                    "lines": written,
                    "reason": CARRIED_CLAIM_NOTE.format(
                        detector=first["detector"],
                        replacement=first["replacement"],
                        original=first["original"],
                    ),
                }
        if verdict_note is not None:
            notes.append(verdict_note)
            continue
        kept.append(finding)
    if not notes:
        return []
    verdict = reply.get("verdict")
    if not kept and verdict in REJECT_VERDICTS:
        notes.append(
            {
                "rule": "BL-870",
                "verdict_changed": [verdict, MODEL_ACCEPT],
                "reason": "the reply's only finding was void by the Lane L contract; a reject verdict "
                "needs a finding",
            }
        )
        reply["verdict"] = MODEL_ACCEPT
    findings[:] = kept
    reply.setdefault("contract_notes", []).extend(notes)
    return notes
