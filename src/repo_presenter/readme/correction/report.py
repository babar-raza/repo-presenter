"""The correction report: what a Lane L run did to the live README, as a document a reader can check.

``corrections_document`` is the sealed ``corrections.json``: every edit with the evidence that
dictates it, every defect the engine could not repair, and the facts about the run itself (the
confinement proof, determinism and idempotence). Nothing in it is machine- or time-specific, so a
rerun over the same inputs writes the same bytes (``plans/PLAN_lane_l_hosted.md`` L4).

Three outcomes exist (plan L2), and only the first two are candidates:

* ``CORRECTED``: at least one evidenced edit, and no defect left unrepaired;
* ``NO_CHANGE_WARRANTED``: no edit and no defect. The live README is the candidate, byte for byte.
  This is a legitimate result, never a fabricated improvement (mission section 11: "actual
  improvement relative to the live README"): the live README is judged and, when it stands, kept;
* ``REFUSED_LANE_R_RECOMMENDED``: a detector found a defect that no deterministic edit can repair
  (a failing example, a format the README over-claims, a link with no unique target). It is neither
  silently omitted nor masked (mission section 6): the run is refused, nothing is sealed, and the
  typed finding names Lane R as the lane that can rewrite what Lane L may not.

Which detectors report a *defect* and which only report an *opportunity* is a closed table
(:data:`INFORMATIONAL_DETECTORS`); a detector this module has never heard of is a defect detector,
so a new detector can fail closed but never quietly be ignored.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from repo_presenter.core.errors import PresenterError
from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.correction.model import (
    Context,
    CorrectionResult,
    Edit,
    Finding,
)
from repo_presenter.readme.review.findings import Finding as ReviewFinding

SCHEMA_VERSION = 1
CORRECTIONS_FILENAME = "corrections.json"

OUTCOME_CORRECTED = "CORRECTED"
OUTCOME_NO_CHANGE = "NO_CHANGE_WARRANTED"
OUTCOME_REFUSED = "REFUSED_LANE_R_RECOMMENDED"
#: The outcomes that may be sealed as a candidate.
CANDIDATE_OUTCOMES = frozenset({OUTCOME_CORRECTED, OUTCOME_NO_CHANGE})

#: Detectors whose findings are an opportunity (verified information the README does not state and
#: that only authored prose can add), not a falsehood or a break in what the README does state.
#: Everything else a detector reports is a defect the run could not repair.
INFORMATIONAL_DETECTORS: frozenset[str] = frozenset({"report_gaps"})
#: Report-only reasons that mean an addition was legitimately not made. A skipped *fix* carries a
#: different reason (or none) and stays a defect.
NOT_A_DEFECT_REASONS: frozenset[str] = frozenset(
    {
        "ALREADY_SHOWN",
        "RE_ENABLE_CONDITION_UNMET",
        "CONTRADICTS_README_PUBLICATION_CLAIM",
        "NEEDS_INSTALL_FIRST",
        "NOT_IN_VERIFIED_CHAIN",
        "NO_BUILD_RECEIPT",
        "BUILD_RECEIPT_FAILED",
        "DOCS_HOLDS_NO_DOCUMENTATION",
        "NO_EVIDENCE_OF_ABSENCE",
    }
)
RULE_UNREPAIRED_DEFECT = "lane_l_unrepaired_defect"

_VALUE_LIMIT = 160
_UNIT_LINES = re.compile(r"^lines (\d+)-(\d+);")


class CorrectionRunError(PresenterError):
    """The run cannot honestly correct this README (no README to correct, bytes the engine cannot
    represent, facts that do not describe the clone). Typed; recorded as a failed transaction."""


def is_defect(finding: Finding) -> bool:
    """Whether an engine finding is a defect the run left unrepaired."""
    if finding.detector in INFORMATIONAL_DETECTORS:
        return False
    return finding.report_only_reason not in NOT_A_DEFECT_REASONS


def unrepaired_defects(result: CorrectionResult) -> list[Finding]:
    """The engine's findings that are defects, in the engine's own (line, detector) order."""
    return [finding for finding in result.findings if is_defect(finding)]


def defect_findings(result: CorrectionResult) -> list[ReviewFinding]:
    """Each unrepaired defect as a deterministic review finding. Always blocking and never
    clearable: the engine reported it, so only a README without the defect (or a Lane R rewrite)
    can resolve it."""
    findings: list[ReviewFinding] = []
    for defect in unrepaired_defects(result):
        findings.append(
            ReviewFinding(
                rule=RULE_UNREPAIRED_DEFECT,
                source="deterministic",
                claim_kind="contradiction",
                message=(
                    f"{defect.detector} found a defect at line {defect.line} that no "
                    f"deterministic edit can repair: {defect.reason}"
                ),
                quote=defect.text,
                evidence=defect.reason,
                fact_ids=defect.fact_ids,
                repair="Lane R can rewrite what Lane L is not allowed to; this README is not sealed",
            )
        )
    return findings


def outcome_of(result: CorrectionResult) -> str:
    if unrepaired_defects(result):
        return OUTCOME_REFUSED
    return OUTCOME_CORRECTED if result.edits else OUTCOME_NO_CHANGE


def lane_r_recommendation(result: CorrectionResult) -> str:
    """The sentence a refusal ends with: which defects Lane L could not repair."""
    defects = unrepaired_defects(result)
    shown = "; ".join(f"{d.detector} line {d.line}: {d.reason}" for d in defects[:5])
    more = f" (+{len(defects) - 5} more)" if len(defects) > 5 else ""
    return (
        f"Lane L left {len(defects)} defect(s) it may not repair ({shown}{more}); "
        "Lane R is the recommended lane for this repository"
    )


def edit_record(ctx: Context, index: int, edit: Edit) -> dict[str, Any]:
    """One edit as the report states it: what was quoted, what replaced it, and the evidence."""
    evidence: list[dict[str, Any]] = []
    for fact_id in edit.fact_ids:
        fact = ctx.fact(fact_id)
        evidence.append(
            {
                "fact_id": fact_id,
                "status": fact.polarity if fact is not None else "ABSENT",
                "kind": fact.kind if fact is not None else None,
                "value": fact.value[:_VALUE_LIMIT] if fact is not None else None,
            }
        )
    for locator in (
        edit.locators
    ):  # a structure fix cites the README line, an addition a tree path
        in_tree = locator.startswith("tree:")
        evidence.append(
            {
                "fact_id": None,
                "status": "TREE_PATH" if in_tree else "README_TEXT",
                "kind": "tree_path" if in_tree else "readme_structure",
                "value": locator,
            }
        )
    return {
        "index": index,
        "kind": edit.kind,
        "detector": edit.detector,
        "line": ctx.readme.count("\n", 0, edit.start) + 1,
        "start": edit.start,
        "end": edit.end,
        "original": edit.original,
        "replacement": edit.replacement,
        "rationale": edit.rationale,
        "evidence": evidence,
    }


def corrections_document(
    ctx: Context,
    result: CorrectionResult,
    *,
    original_sha256: str,
    corrected_sha256: str,
    deterministic: bool,
    idempotent: bool,
) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    for edit in result.edits:
        kinds[edit.kind] = kinds.get(edit.kind, 0) + 1
    unapplied = [
        {
            "detector": finding.detector,
            "line": finding.line,
            "text": finding.text[:_VALUE_LIMIT],
            "reason": finding.reason,
            "fact_ids": list(finding.fact_ids),
            "defect": is_defect(finding),
            **(
                {"report_only_reason": finding.report_only_reason}
                if finding.report_only_reason
                else {}
            ),
            **({"candidate": finding.candidate} if finding.candidate else {}),
        }
        for finding in result.findings
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "lane": "L",
        "outcome": outcome_of(result),
        "repository": ctx.facts.repository,
        "source_revision": ctx.facts.source_revision,
        "readme_path": ctx.readme_path,
        "original_sha256": original_sha256,
        "corrected_sha256": corrected_sha256,
        "summary": dict(sorted(kinds.items())),
        "edits": [
            edit_record(ctx, index, edit) for index, edit in enumerate(result.edits)
        ],
        "unapplied": unapplied,
        "confinement": {
            "verified": True,
            "statement": (
                "the corrected text with every edit's span removed equals the original with the "
                "same spans removed"
            ),
            "edits": len(result.edits),
        },
        "stability": {
            "deterministic": deterministic,
            "idempotent": idempotent,
            "provider_calls": 0,
        },
    }


def canonical_json(document: Mapping[str, Any]) -> bytes:
    """The bytes every JSON artifact of a Lane L run is written as: sorted, indented, UTF-8, LF."""
    return (
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def inherited_unit_spans(facts: FactsDocument) -> list[tuple[str, int, int]]:
    """``(unit id, first line, last line)`` of every inherited README unit the facts record."""
    spans: list[tuple[str, int, int]] = []
    for fact in facts.facts:
        if fact.kind != "inherited_unit" or not fact.evidence:
            continue
        match = _UNIT_LINES.match(fact.evidence[0].detail or "")
        if match is not None:
            spans.append((fact.id, int(match.group(1)), int(match.group(2))))
    return spans


def correction_dispositions(ctx: Context, edits: Sequence[Edit]) -> dict[str, Any]:
    """The edits as inherited-unit dispositions, in the shape the reviewer reads.

    A replacement edit changes text inside the inherited unit holding its first line; that unit is
    accounted ``CORRECT_WITH_EVIDENCE`` under the facts that dictate the edit (or, for a fix whose
    evidence is the README's own line, under the unit itself). A pure insertion removes nothing, so
    it accounts for nothing. Every other unit is untouched and has no disposition: Lane L keeps
    what it does not edit.
    """
    spans = inherited_unit_spans(ctx.facts)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for edit in edits:
        if edit.start == edit.end:
            continue
        line = ctx.readme.count("\n", 0, edit.start) + 1
        unit = next((uid for uid, first, last in spans if first <= line <= last), None)
        if unit is None or unit in seen:
            continue
        seen.add(unit)
        rows.append(
            {
                "unit_id": unit,
                "disposition": "CORRECT_WITH_EVIDENCE",
                "destination_section": None,
                "fact_ids": list(edit.fact_ids or (unit,)),
                "rationale": edit.rationale,
            }
        )
    return {"dispositions": rows}
