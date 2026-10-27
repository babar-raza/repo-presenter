"""Account for the kept inherited units the finished README does not print.

S4 decides a unit's fate before any plan exists. A unit it keeps as written (``VERIFIED_PRESERVE``
or ``VERIFIED_MOVE``) is printed by the renderer only when the renderer's own placement
(``composition/placement.py``) says ``placed``. Three placements print nothing, and each is a fact
the renderer decides, not a guess:

* ``overlap``: the destination section's planned content already states the unit's cited facts, so
  the kept unit is dropped as covered (BC-05's "the plan's own content covers it");
* ``owned_elsewhere`` for a heading: the renderer prints its own headings and never an inherited
  one as written (``renders_verbatim``), so a kept sub-heading such as the API reference's
  ``### Main`` is never printed;
* ``owned_elsewhere`` for a Mermaid block: the renderer draws its own At a Glance diagram.

A unit left ``kept`` in those three cases claims an effect that does not happen, and the reviewer
(``disposition_coverage``/``live_readme_loss``) rightly refuses it. The disposition that matches
what happened is ``SUPERSEDE_REDUNDANT`` into the same section, citing the facts that section was
built from. This stage rewrites exactly those entries, from the renderer's own placement decisions,
deterministically: no model is asked and no fact is invented (every cited ID is a fact of the
document, taken from the placement, the entry itself or the plan). A unit is left alone when the
facts to cite cannot be found, or when a dropped list does not in fact state all its items
(``validation.units._dropped_list_failures``); those are repair work, not accounting.

The rewrite never changes what renders: the caller re-renders with the accounted dispositions and
keeps them only when the README is byte-identical.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from repo_presenter.readme.composition.placement import (
    PLACED,
    Placement,
    planned_fact_ids,
    renderer_fact_ids,
)
from repo_presenter.readme.reconciliation.dispositions import rendering_fact_ids
from repo_presenter.readme.review.independent_reviewer import unprinted_kept_units
from repo_presenter.readme.validation.failures import Candidate
from repo_presenter.readme.validation.text import section_texts
from repo_presenter.readme.validation.units import _dropped_list_failures, placements_of

ACCOUNTING_FILENAME = "accounting.json"
RATIONALE_OVERLAP = (
    "Not printed again: {section} already states this material from the facts it cites, "
    "so the kept unit is redundant."
)
RATIONALE_HEADING = (
    "Heading owned by the renderer: {section} prints its own headings, so this inherited "
    "heading is not printed as written."
)
RATIONALE_DIAGRAM = (
    "Superseded by the At a Glance diagram the renderer draws from the verified formats "
    "and capabilities."
)
MERMAID_FENCE = "mermaid"


@dataclass(frozen=True)
class Accounted:
    """One disposition rewritten to what the render did, with the facts it now cites."""

    unit_id: str
    was: str
    destination: str
    reason: str
    fact_ids: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "was": self.was,
            "now": "SUPERSEDE_REDUNDANT",
            "destination_section": self.destination,
            "reason": self.reason,
            "fact_ids": list(self.fact_ids),
        }


def _is_mermaid(text: str) -> bool:
    first = text.lstrip().splitlines()[0].strip() if text.strip() else ""
    return (
        first.startswith(("```", "~~~")) and first[3:].strip().lower() == MERMAID_FENCE
    )


def _diagram_fact_ids(plan: Mapping[str, Any], known: frozenset[str]) -> list[str]:
    """The facts the At a Glance diagram is drawn from: the formats and the capabilities it names."""
    glance = plan.get("at_a_glance") or {}
    titles = set(glance.get("capability_titles", []))
    ids: set[str] = set(glance.get("input_format_ids", [])) | set(
        glance.get("output_format_ids", [])
    )
    for capability in plan.get("core_capabilities", []):
        if capability.get("title") in titles:
            ids.update(capability.get("fact_ids", []))
    return sorted(ids & known)


def _drawn(plan: Mapping[str, Any], readme: str) -> bool:
    """Whether the renderer drew its At a Glance diagram into this README."""
    included = {
        str(item.get("section_id"))
        for item in plan.get("sections", [])
        if item.get("include")
    }
    return (
        "at_a_glance" in included
        and bool(plan.get("at_a_glance"))
        and f"```{MERMAID_FENCE}" in readme
    )


def _covering_facts(
    placement: Placement,
    entry: Mapping[str, Any],
    candidate: Candidate,
    known: frozenset[str],
) -> list[str]:
    """Facts that show ``placement.destination`` covers an overlapped unit: the facts the entry
    cites that the plan's section content rests on, the placement's own overlap (a section name
    there stands for what that section renders), and the unit's own citations."""
    ids = {fact_id for fact_id in placement.overlap if fact_id in known}
    for name in placement.overlap:
        if name not in known:
            ids.update(rendering_fact_ids(name, candidate.facts))
    ids.update(fact_id for fact_id in entry.get("fact_ids") or [] if fact_id in known)
    return sorted(ids & known)


def _heading_facts(
    placement: Placement, candidate: Candidate, known: frozenset[str]
) -> list[str]:
    """The facts the destination section's renderer prints beneath its own headings."""
    ids = planned_fact_ids(candidate.plan, placement.destination)
    if not ids:
        ids = renderer_fact_ids(placement.destination, candidate.facts, candidate.plan)
    return sorted(ids & known)


def _lists_state_their_items(candidate: Candidate, placement: Placement) -> bool:
    texts = section_texts(candidate.readme)
    return not _dropped_list_failures(candidate, placement, texts)


def _decide(
    placement: Placement,
    entry: Mapping[str, Any],
    candidate: Candidate,
    known: frozenset[str],
) -> tuple[str, str, list[str]] | None:
    """``(destination, rationale, fact_ids)`` for a kept unit the render did not print, or ``None``
    when it cannot be accounted deterministically."""
    unit_id = placement.unit_id
    section = placement.destination
    if placement.outcome == "overlap":
        facts = _covering_facts(placement, entry, candidate, known)
        if not facts or not _lists_state_their_items(candidate, placement):
            return None
        return (
            section,
            RATIONALE_OVERLAP.format(section=section.replace("_", " ")),
            facts,
        )
    if placement.outcome != "owned_elsewhere":
        return None
    if unit_id.endswith(".heading"):
        facts = _heading_facts(placement, candidate, known)
        if not facts:
            return None
        return (
            section,
            RATIONALE_HEADING.format(section=section.replace("_", " ")),
            facts,
        )
    if unit_id.endswith(".code_block") and _is_mermaid(placement.text):
        facts = _diagram_fact_ids(candidate.plan, known)
        if not facts or not _drawn(candidate.plan, candidate.readme):
            return None
        return "at_a_glance", RATIONALE_DIAGRAM, facts
    return None


def _uncited_diagram(
    entry: Mapping[str, Any], candidate: Candidate, known: frozenset[str]
) -> tuple[str, str, list[str]] | None:
    """The accounting for an inherited Mermaid block S4 dropped without citing a fact (``OMIT_
    UNSUPPORTED`` with no fact_ids, or ``DEFER_UNRESOLVED``) while the renderer drew its own At a
    Glance diagram: that diagram takes its place, drawn from the facts the plan names."""
    unit = next(
        (
            f
            for f in candidate.facts.by_kind("inherited_unit")
            if f.id == entry.get("unit_id")
        ),
        None,
    )
    if (
        unit is None
        or not unit.id.endswith(".code_block")
        or not _is_mermaid(unit.value)
        or entry.get("fact_ids")
        or entry.get("disposition") not in {"OMIT_UNSUPPORTED", "DEFER_UNRESOLVED"}
        or not _drawn(candidate.plan, candidate.readme)
    ):
        return None
    facts = _diagram_fact_ids(candidate.plan, known)
    return ("at_a_glance", RATIONALE_DIAGRAM, facts) if facts else None


def account_unprinted_units(
    candidate: Candidate,
) -> tuple[dict[str, Any], list[Accounted]]:
    """``candidate.dispositions`` with each kept-but-unprinted unit accounted as redundant, and the
    list of what was rewritten. Pure: the candidate's own dispositions are not touched."""
    known = frozenset(fact.id for fact in candidate.facts.facts)
    unprinted = {
        unit
        for unit, _disposition in unprinted_kept_units(
            candidate.readme, facts=candidate.facts, dispositions=candidate.dispositions
        )
    }
    by_unit = {p.unit_id: p for p in placements_of(candidate)}
    settled = copy.deepcopy(candidate.dispositions)
    accounted: list[Accounted] = []
    for entry in settled.get("dispositions", []):
        unit_id = str(entry.get("unit_id", ""))
        placement = by_unit.get(unit_id)
        if (
            unit_id in unprinted
            and placement is not None
            and entry.get("disposition") in PLACED
        ):
            decided = _decide(placement, entry, candidate, known)
            reason = placement.outcome
        else:
            decided = _uncited_diagram(entry, candidate, known)
            reason = "uncited_diagram"
        if decided is None:
            continue
        destination, rationale, fact_ids = decided
        was = str(entry.get("disposition"))
        entry["disposition"] = "SUPERSEDE_REDUNDANT"
        entry["destination_section"] = destination
        entry["fact_ids"] = fact_ids
        entry["rationale"] = rationale
        accounted.append(Accounted(unit_id, was, destination, reason, tuple(fact_ids)))
    return settled, accounted


def accounting_document(accounted: list[Accounted]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "accounted": [item.to_json() for item in accounted],
    }
