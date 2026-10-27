"""Bridges an independent-reviewer ``ReviewVerdict`` into this repository's already-REUSE-ported
``readme.repair.targeted`` ``Defect`` model (BUILD_INDEPENDENT_REVIEWER's still-open item: "decide
where a REJECT hands off to repair").

``readme.repair.targeted.review_defects`` already exists, is REUSE-ported verbatim from the old
repository, and already does the hard, previously-bug-prone part: routing a review finding to the
cascade stage that may actually revise it, including the specific case this module exists because
of -- a finding whose quoted text matches a unit the candidate *inherited and placed verbatim*
(``composition/placement.py``'s ``placed_texts()``) is rerouted to S4 (reconciliation) and marked
``misrouted``, because S6 authoring never wrote that text and cannot revise it. This was not a
theoretical concern: the independent reviewer's first real finding (project/state.yaml's
RUN_INDEPENDENT_REVIEW_P2_COHORT_2026_10_24, aspose-font-foss/Aspose.Font-FOSS-for-Python) turned
out to be exactly this case -- a broken install command inherited verbatim from the live upstream
README, not written by this project's own authoring pipeline at all. A bridge that always guessed
``causal_stage="S6"`` without ever checking placement would have misrouted that exact real finding
to a repair stage that cannot touch it.

This module does not build a repair loop (no ``repair/rounds.py``-equivalent exists in this
repository) -- it stops at producing typed, correctly routed ``Defect`` records, ready for
whenever one exists. ``review_candidate``'s own two v1 rules are deterministic only (no judgment
rules yet), so ``build_defects`` only ever considers findings that already carry a
``Finding.refuted_by`` -- an annotate-only judgment finding never becomes a repair target, by the
same no-quiet-demotion discipline ``independent_reviewer.py`` enforces for the verdict itself.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.placement import placed_texts, placements
from repo_presenter.readme.repair.targeted import Defect, review_defects
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict

#: Stands in for a reviewer prompt's hash in ``defect_fingerprint``'s ``context`` (old repo's
#: review_defects was built for an LLM reviewer; this one is deterministic-only in v1). Bump this
#: whenever a rule's own matching logic changes meaning, so a stale fingerprint from before the
#: change never short-circuits a fresh repair attempt as "already tried" (the same contract an
#: LLM reviewer's own prompt hash serves).
RULESET_VERSION = "independent_reviewer.v2.deterministic_only"

#: Rules whose finding is, by what the rule measures, about a disposition: a kept unit that is not
#: printed is S4's claim that did not hold. The other rules measure authored text (S6).
S4_RULES = frozenset({"disposition_coverage"})


def _llm_sections(units: Sequence[Mapping[str, Any]]) -> set[str]:
    """The set of sections ``section_authoring`` actually wrote a unit for. A deterministic
    section (badges, identity, navigation, ...) never appears here, because S6 never authors it
    -- derived from this cascade's own real output, not a fixed guess at which sections an LLM
    owns (a repository's plan can include or exclude sections per its own facts)."""
    return {str(unit["section"]) for unit in units if unit.get("section")}


def _locate_section(quote: str, units: Sequence[Mapping[str, Any]], placed: Mapping[str, list[str]]) -> str | None:
    """Where a finding's quote actually lives, checked in the order that matters: inherited/
    placed content first (authoring never wrote it, so a defect there can never be an S6 matter
    regardless of what a caller might otherwise assume), then authored units."""
    if not quote:
        return None
    for section, texts in placed.items():
        if any(quote in text for text in texts):
            return section
    for unit in units:
        text = unit.get("text")
        if isinstance(text, str) and quote in text:
            section = unit.get("section")
            return str(section) if section else None
    return None


def build_defects(
    verdict: ReviewVerdict,
    *,
    units: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
    ecosystem: str,
    repairer: str = "",
) -> list[Defect]:
    """Every deterministic REJECT finding in ``verdict``, routed to a ``Defect``.

    ``placements()``/``placed_texts()`` need real ``inherited_unit`` facts to find anything
    (project/state.yaml's root_cause_traced_2026_10_24: every facts.json this repository had
    written to disk before 2026-10-24 had none, a persistence gap in
    ``scripts/run_lane_r_render.py``, now fixed going forward). Calling this against such a
    ``facts`` is not an error -- ``placed`` is simply empty and every finding routes as if
    nothing was inherited, which is honest given what the caller's evidence actually contains,
    never a silent assumption that nothing was.
    """
    placed = placed_texts(placements(dict(plan), dict(dispositions), facts, ecosystem))
    llm_sections = _llm_sections(units)
    findings = [finding for finding in verdict.findings if finding.refuted_by is not None]
    review = {
        "reviewer": {"prompt_sha256": RULESET_VERSION},
        "findings": [
            {
                "id": f"{finding.rule}:{index}",
                "section_id": _locate_section(finding.quote, units, placed),
                "causal_stage": "S4" if finding.rule in S4_RULES else "S6",
                "criterion": finding.rule,
                "quote": finding.quote,
                "message": finding.message,
            }
            for index, finding in enumerate(findings)
        ],
    }
    return review_defects(review, facts, llm_sections, repairer, placed)
