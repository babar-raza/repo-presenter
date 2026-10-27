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
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, NamedTuple

from repo_presenter.readme.composition.placement import (
    PLACED,
    Placement,
    planned_fact_ids,
    renderer_fact_ids,
)
from repo_presenter.readme.reconciliation.dispositions import rendering_fact_ids
from repo_presenter.readme.review.independent_reviewer import (
    heading_printed,
    unprinted_kept_units,
)
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
RATIONALE_EXAMPLE_CODE = (
    "Printed by the example section from the verified example fact it cites, with any usings the "
    "compiler needed supplied above the inherited code."
)
RATIONALE_EXAMPLE_HEADING = (
    "Heading owned by the renderer: the example section prints its own title for the example "
    "this heading introduced."
)
RATIONALE_LEAD_HEADING = (
    "Omitted with the example it introduced: that example is contradicted ({facts}), so its "
    "heading has nothing left to introduce."
)
MERMAID_FENCE = "mermaid"
EXAMPLE_SECTIONS = frozenset({"quick_start", "additional_examples"})
_FENCE = re.compile(
    r"^(?:```|~~~)[^\n]*\n(.*?)\n(?:```|~~~)[ \t]*$", re.MULTILINE | re.DOTALL
)
_ORDINAL = re.compile(r"inherited_unit:(\d+)\.")
_EXAMPLE_UNIT = re.compile(r"\bunit (inherited_unit:\d+\.code_block)\b")
RATIONALE_CONTRADICTED_OMISSION = (
    "Omitted because the example is contradicted ({facts}): it failed verification against this "
    "revision, so it may not be restored."
)


@dataclass(frozen=True)
class Accounted:
    """One disposition rewritten to what the render did, with the facts it now cites."""

    unit_id: str
    was: str
    destination: str | None
    reason: str
    fact_ids: tuple[str, ...]
    now: str = "SUPERSEDE_REDUNDANT"

    def to_json(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "was": self.was,
            "now": self.now,
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


class _Decision(NamedTuple):
    destination: str | None
    rationale: str
    fact_ids: list[str]
    disposition: str = "SUPERSEDE_REDUNDANT"


def _normalised(text: str) -> str:
    return "\n".join(
        line.rstrip() for line in text.replace("\r\n", "\n").splitlines()
    ).strip()


def _fence_bodies(readme: str) -> list[str]:
    return [_normalised(match.group(1)) for match in _FENCE.finditer(readme)]


def _code_body(unit_text: str) -> str | None:
    match = _FENCE.match(unit_text.strip())
    return _normalised(match.group(1)) if match else None


def _unit_values(candidate: Candidate) -> dict[str, str]:
    return {fact.id: fact.value for fact in candidate.facts.by_kind("inherited_unit")}


def _examples(
    entry: Mapping[str, Any], candidate: Candidate, polarity: str, known: frozenset[str]
) -> list[str]:
    """The example facts ``entry`` cites that have ``polarity``."""
    wanted = {
        fact.id
        for fact in candidate.facts.by_kind("example")
        if fact.polarity == polarity
    }
    return sorted(
        fact_id
        for fact_id in entry.get("fact_ids") or []
        if fact_id in wanted and fact_id in known
    )


def _unit_examples(
    unit_id: str, candidate: Candidate, polarity: str, known: frozenset[str]
) -> list[str]:
    """The example facts with ``polarity`` whose own evidence names the inherited code block
    ``unit_id`` as the fence they verified. The link lives in the example fact (the extractor
    wrote it when it lifted the fence), so it is the proof even when S4's row cites no fact."""
    return sorted(
        fact.id
        for fact in candidate.facts.by_kind("example")
        if fact.polarity == polarity
        and fact.id in known
        and any(
            (match := _EXAMPLE_UNIT.search(evidence.detail)) is not None
            and match.group(1) == unit_id
            for evidence in fact.evidence
        )
    )


def _code_printed(unit_text: str, candidate: Candidate) -> bool:
    """Whether the README prints the inherited code block's body verbatim inside some fence (the
    example section may put supplied usings above it, so containment, not equality)."""
    body = _code_body(unit_text)
    return body is not None and any(
        body in printed for printed in _fence_bodies(candidate.readme)
    )


def _payload_row(
    heading_id: str, candidate: Candidate
) -> tuple[str, Mapping[str, Any]] | None:
    """The disposition row of the first code block under the inherited heading ``heading_id``
    (the example the heading introduces), stopping at the next heading."""
    match = _ORDINAL.match(heading_id)
    if match is None:
        return None
    start = int(match.group(1))
    ordered = sorted(
        (int(m.group(1)), unit)
        for unit in _unit_values(candidate)
        if (m := _ORDINAL.match(unit)) is not None and int(m.group(1)) > start
    )
    rows = {
        str(row.get("unit_id")): row
        for row in candidate.dispositions.get("dispositions", [])
    }
    for _, unit in ordered:
        if unit.endswith(".heading"):
            return None
        if unit.endswith(".code_block") and unit in rows:
            return unit, rows[unit]
    return None


def _example_heading(
    entry: Mapping[str, Any], candidate: Candidate, known: frozenset[str], section: str
) -> _Decision | None:
    """A kept heading that introduced a SUPPORTED example the section prints under its own title."""
    payload = _payload_row(str(entry.get("unit_id", "")), candidate)
    if payload is None:
        return None
    unit_id, row = payload
    facts = _examples(row, candidate, "SUPPORTED", known)
    text = _unit_values(candidate).get(unit_id, "")
    if not facts or not _code_printed(text, candidate):
        return None
    return _Decision(section, RATIONALE_EXAMPLE_HEADING, facts)


def _lead_heading_omitted(
    entry: Mapping[str, Any], candidate: Candidate, known: frozenset[str]
) -> _Decision | None:
    """A kept heading whose only content was an example S4 omitted because a fact contradicts it:
    the heading goes with the example, citing the same fact."""
    if not str(entry.get("unit_id", "")).endswith(".heading"):
        return None
    payload = _payload_row(str(entry["unit_id"]), candidate)
    if payload is None:
        return None
    _, row = payload
    if row.get("disposition") != "OMIT_UNSUPPORTED":
        return None
    facts = _examples(row, candidate, "CONTRADICTED", known)
    if not facts:
        return None
    return _Decision(
        None,
        RATIONALE_LEAD_HEADING.format(facts=", ".join(facts)),
        facts,
        "OMIT_UNSUPPORTED",
    )


def _uncited_heading(
    entry: Mapping[str, Any], candidate: Candidate, known: frozenset[str]
) -> _Decision | None:
    """A heading S4 already superseded into a renderer-owned section without citing any fact: the
    reviewer counts a supersession only when a fact backs it, so cite the facts the destination
    section is built from. Only when the heading is in fact not printed."""
    unit_id = str(entry.get("unit_id", ""))
    value = _unit_values(candidate).get(unit_id)
    destination = entry.get("destination_section")
    if (
        value is None
        or not unit_id.endswith(".heading")
        or entry.get("disposition") != "SUPERSEDE_REDUNDANT"
        or any(fact_id in known for fact_id in entry.get("fact_ids") or [])
        or not isinstance(destination, str)
        or heading_printed(value, candidate.readme)
    ):
        return None
    included = {
        str(item.get("section_id"))
        for item in candidate.plan.get("sections", [])
        if item.get("include")
    }
    if destination not in included:
        return None
    ids = planned_fact_ids(candidate.plan, destination) or renderer_fact_ids(
        destination, candidate.facts, candidate.plan
    )
    facts = sorted(ids & known)
    if not facts and destination in EXAMPLE_SECTIONS:
        # An example section is built from example facts, not planned facts: the heading goes
        # with the SUPPORTED example it introduced, printed under the section's own title.
        facts = _example_payload_facts(
            unit_id, candidate, "SUPPORTED", known, printed=True
        )
    if not facts:
        return None
    rationale = str(entry.get("rationale") or "").strip() or RATIONALE_HEADING.format(
        section=destination.replace("_", " ")
    )
    return _Decision(destination, rationale, facts)


def _example_payload_facts(
    heading_id: str,
    candidate: Candidate,
    polarity: str,
    known: frozenset[str],
    *,
    printed: bool,
) -> list[str]:
    """The ``polarity`` example facts of the code block under the inherited heading
    ``heading_id``; with ``printed`` only when the README prints that block's body."""
    payload = _payload_row(heading_id, candidate)
    if payload is None:
        return []
    unit_id, _row = payload
    if printed and not _code_printed(
        _unit_values(candidate).get(unit_id, ""), candidate
    ):
        return []
    return _unit_examples(unit_id, candidate, polarity, known)


def _uncited_contradicted_omission(
    entry: Mapping[str, Any], candidate: Candidate, known: frozenset[str]
) -> _Decision | None:
    """An inherited example block S4 already omitted because a fact contradicts it, but whose
    ``fact_ids`` are empty (the contradiction is only in the rationale prose). The reviewer counts
    an omission only when it cites a fact, so cite the CONTRADICTED example fact the extractor
    linked to that very block. The same for the heading that introduced it. Nothing is invented
    and nothing renders differently: the unit stays omitted."""
    unit_id = str(entry.get("unit_id", ""))
    if (
        entry.get("disposition") != "OMIT_UNSUPPORTED"
        or any(fact_id in known for fact_id in entry.get("fact_ids") or [])
        or unit_id not in _unit_values(candidate)
    ):
        return None
    if unit_id.endswith(".code_block"):
        facts = _unit_examples(unit_id, candidate, "CONTRADICTED", known)
    elif unit_id.endswith(".heading"):
        facts = _example_payload_facts(
            unit_id, candidate, "CONTRADICTED", known, printed=False
        )
    else:
        return None
    if not facts:
        return None
    rationale = str(entry.get("rationale") or "").strip() or (
        RATIONALE_CONTRADICTED_OMISSION.format(facts=", ".join(facts))
    )
    return _Decision(None, rationale, facts, "OMIT_UNSUPPORTED")


def _decide(
    placement: Placement,
    entry: Mapping[str, Any],
    candidate: Candidate,
    known: frozenset[str],
) -> _Decision | None:
    """The accounting for a kept unit the render did not print, or ``None`` when it cannot be
    accounted deterministically."""
    unit_id = placement.unit_id
    section = placement.destination
    if placement.outcome == "overlap":
        facts = _covering_facts(placement, entry, candidate, known)
        if not facts or not _lists_state_their_items(candidate, placement):
            return None
        return _Decision(
            section, RATIONALE_OVERLAP.format(section=section.replace("_", " ")), facts
        )
    if placement.outcome != "owned_elsewhere":
        return None
    if unit_id.endswith(".heading"):
        facts = _heading_facts(placement, candidate, known)
        if not facts and section in EXAMPLE_SECTIONS:
            return _example_heading(entry, candidate, known, section)
        if not facts:
            return None
        return _Decision(
            section, RATIONALE_HEADING.format(section=section.replace("_", " ")), facts
        )
    if unit_id.endswith(".code_block") and _is_mermaid(placement.text):
        facts = _diagram_fact_ids(candidate.plan, known)
        if not facts or not _drawn(candidate.plan, candidate.readme):
            return None
        return _Decision("at_a_glance", RATIONALE_DIAGRAM, facts)
    if unit_id.endswith(".code_block") and section in EXAMPLE_SECTIONS:
        facts = _examples(entry, candidate, "SUPPORTED", known)
        if not facts or not _code_printed(
            _unit_values(candidate).get(unit_id, ""), candidate
        ):
            return None
        return _Decision(section, RATIONALE_EXAMPLE_CODE, facts)
    return None


def _uncited_diagram(
    entry: Mapping[str, Any], candidate: Candidate, known: frozenset[str]
) -> _Decision | None:
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
    return _Decision("at_a_glance", RATIONALE_DIAGRAM, facts) if facts else None


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
        decided: _Decision | None = None
        reason = ""
        if (
            unit_id in unprinted
            and placement is not None
            and entry.get("disposition") in PLACED
        ):
            decided = _decide(placement, entry, candidate, known)
            reason = placement.outcome
            if decided is None:
                decided = _lead_heading_omitted(entry, candidate, known)
                reason = "lead_heading_omitted"
        if decided is None:
            decided = _uncited_diagram(entry, candidate, known)
            reason = "uncited_diagram"
        if decided is None:
            decided = _uncited_contradicted_omission(entry, candidate, known)
            reason = "uncited_contradicted_omission"
        if decided is None:
            decided = _uncited_heading(entry, candidate, known)
            reason = "uncited_heading"
        if decided is None:
            continue
        was = str(entry.get("disposition"))
        entry["disposition"] = decided.disposition
        entry["destination_section"] = decided.destination
        entry["fact_ids"] = decided.fact_ids
        entry["rationale"] = decided.rationale
        accounted.append(
            Accounted(
                unit_id,
                was,
                decided.destination,
                reason,
                tuple(decided.fact_ids),
                decided.disposition,
            )
        )
    return settled, accounted


def accounting_document(accounted: list[Accounted]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "accounted": [item.to_json() for item in accounted],
    }
