"""Placement of inherited units at render: the decision the renderer and the validator share.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/placement.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry).

Placement is exclusive, never additive, on fact-ID overlap: a unit whose cited facts intersect the
destination's own plan-driven content is dropped, because the planned, freshly authored content
already covers that material. Fact-ID overlap only nominates a unit for dropping; the destination's
text decides it (``coverage.uncovered``/``uncovered_block``). A code block the plan or the renderer
already owns renders through them, not verbatim; any other unit renders as written.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import unquote

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.facts import Fact, FactsDocument
from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL
from repo_presenter.readme.composition.coverage import Destinations, uncovered, uncovered_block
from repo_presenter.readme.composition.source_topics import root_heading, unit_topic
from repo_presenter.readme.evidence.facts.commands import CI_MATRIX_FACT_ID, RELEASE_WORKFLOW_FACT_ID
from repo_presenter.readme.evidence.facts.links import heading_slug

PLACED = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
PLACING = frozenset(
    {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE", "CORRECT_WITH_EVIDENCE"}
)
_RENDERED_ELSEWHERE = frozenset({"heading", "badge_row", "html_block"})
Outcome = Literal["placed", "overlap", "owned_elsewhere", "excluded"]
_STATED_BY: Mapping[str, tuple[str, ...]] = {
    "install": ("installation", "dependencies"),
    "furniture": ("license", "third_party_notices"),
}


@dataclass(frozen=True)
class Placement:
    unit_id: str
    destination: str
    text: str
    outcome: Outcome
    overlap: tuple[str, ...] = ()
    read_with: tuple[str, ...] = ()


def renders_verbatim(unit_id: str, value: str, ecosystem: str) -> bool:
    """Whether a placed inherited unit is rendered verbatim in its destination."""
    unit_type = unit_id.rsplit(".", 1)[-1]
    if unit_type != "code_block":
        return unit_type not in _RENDERED_ELSEWHERE
    first = value.splitlines()[0].strip() if value.strip() else ""
    language = first[3:].strip().lower() if first.startswith("```") else ""
    return language not in ({"mermaid"} | spec_for(ecosystem).example_fences)


def planned_fact_ids(plan: dict[str, Any], section: str) -> frozenset[str]:
    """The fact and unit IDs the plan's own content for ``section`` rests on."""
    ids: set[str] = set()
    if section == "key_capabilities":
        for item in plan.get("core_capabilities", []):
            ids.update(item.get("fact_ids", []))
    elif section == "scope_limitations":
        for item in plan.get("material_limitations", []):
            ids.update(item.get("fact_ids", []))
            ids.update(item.get("unit_ids", []))
    elif section == "api_reference":
        for hub in plan.get("api_hubs", []):
            ids.add(str(hub.get("symbol_fact_id", "")))
            ids.update(hub.get("fact_ids", []))
    elif section == "at_a_glance":
        glance = plan.get("at_a_glance") or {}
        ids.update(glance.get("input_format_ids", []))
        ids.update(glance.get("output_format_ids", []))
    for link in plan.get("links", []):
        if link.get("section_id") == section:
            ids.add(str(link.get("link_fact_id", "")))
    return frozenset(i for i in ids if i)


def rendered_example_ids(plan: Mapping[str, Any]) -> dict[str, str]:
    """Every example the plan renders, mapped to the included section that prints it."""
    included = {
        str(entry.get("section_id")) for entry in plan.get("sections", []) if entry.get("include")
    }
    where: dict[str, str] = {}
    if "quick_start" in included:
        for key in ("quick_start_example_id", "second_quick_start_example_id"):
            example_id = plan.get(key)
            if example_id:
                where[str(example_id)] = "quick_start"
    if "additional_examples" in included:
        for example_id in plan.get("additional_example_ids", []):
            where.setdefault(str(example_id), "additional_examples")
    return where


_UNIT_ORDINAL = re.compile(r"^inherited_unit:(\d+)")
_EXAMPLE_UNIT = re.compile(r"unit (inherited_unit:\S+)")


def _unit_ordinal(unit_id: str) -> int | None:
    """The block-ordinal of this unit's source block, parsed from its own ID."""
    match = _UNIT_ORDINAL.match(unit_id)
    return int(match.group(1)) if match else None


def _example_code_block_ordinals(facts: FactsDocument) -> dict[str, int]:
    """Each example fact's own code-block ordinal, read back from its own evidence."""
    ordinals: dict[str, int] = {}
    for fact in facts.by_kind("example"):
        detail = fact.evidence[0].detail if fact.evidence else None
        match = _EXAMPLE_UNIT.search(detail or "")
        if match is None:
            continue
        ordinal = _unit_ordinal(match.group(1))
        if ordinal is not None:
            ordinals[fact.id] = ordinal
    return ordinals


def _adjacent_rendered_examples(
    unit_id: str, rendered: frozenset[str], example_ordinals: Mapping[str, int]
) -> frozenset[str]:
    """The rendered example IDs whose own code block sits immediately beside ``unit_id``."""
    ordinal = _unit_ordinal(unit_id)
    if ordinal is None:
        return frozenset()
    return frozenset(
        example_id
        for example_id in rendered
        if example_id in example_ordinals and abs(example_ordinals[example_id] - ordinal) == 1
    )


_SECTION_LEAD_IN_DESTINATIONS = frozenset({"quick_start", "additional_examples"})


def _section_heading_ordinals(dispositions: Mapping[str, Any]) -> dict[str, int]:
    """``quick_start``'s and ``additional_examples``' own smallest preserved-heading ordinal."""
    ordinals: dict[str, int] = {}
    for entry in dispositions.get("dispositions", []):
        destination = entry.get("destination_section")
        unit_id = str(entry.get("unit_id", ""))
        if destination not in _SECTION_LEAD_IN_DESTINATIONS or not unit_id.endswith(".heading"):
            continue
        ordinal = _unit_ordinal(unit_id)
        if ordinal is None:
            continue
        if ordinal < ordinals.get(destination, ordinal + 1):
            ordinals[destination] = ordinal
    return ordinals


def _adjacent_section_opening(
    unit_id: str, destination: str, heading_ordinals: Mapping[str, int], rendered: frozenset[str]
) -> frozenset[str]:
    """Every example the plan renders, when ``unit_id`` sits immediately after the section's own
    original heading."""
    ordinal = _unit_ordinal(unit_id)
    heading_ordinal = heading_ordinals.get(destination)
    if ordinal is None or heading_ordinal is None or ordinal - heading_ordinal != 1:
        return frozenset()
    return rendered


_RENDERER_OWNED_ASSETS = (
    "build_test_asset:tests",
    "build_test_asset:ci",
    CI_MATRIX_FACT_ID,
    RELEASE_WORKFLOW_FACT_ID,
)


_STOCK_CONSTRUCTOR_SUMMARY = re.compile(
    r"^Initializes a new instance of the (?P<type>[\w.]+) class\.?$"
)


def has_member_summary(fact: Fact) -> bool:
    """Whether a member carries its own documentation summary."""
    docstring = (fact.attributes or {}).get("docstring") or ""
    stock = _STOCK_CONSTRUCTOR_SUMMARY.match(docstring)
    named = stock.group("type").rsplit(".", 1)[-1] if stock is not None else None
    if named is not None and fact.value.rsplit(".", 1)[-1] == named:
        return False
    return bool(docstring)


def api_reference_hub_methods(
    plan: Mapping[str, Any], facts: FactsDocument
) -> dict[str, list[Fact]]:
    """Every verified, documented method ``public_symbol`` grouped by the hub symbol's own
    display value it belongs to."""
    methods = [
        fact
        for fact in facts.by_kind("public_symbol")
        if fact.polarity == "SUPPORTED"
        and (fact.attributes or {}).get("symbol_kind") == "method"
        and has_member_summary(fact)
    ]
    by_owner: dict[str, list[Fact]] = {}
    for fact in methods:
        by_owner.setdefault(fact.value.rsplit(".", 1)[0], []).append(fact)
    by_id = {fact.id: fact for fact in facts.facts}
    owned: dict[str, list[Fact]] = {}
    for hub in plan.get("api_hubs", []):
        symbol = by_id.get(str(hub.get("symbol_fact_id", "")))
        if symbol is not None:
            owned[symbol.value] = by_owner.get(symbol.value, [])
    return owned


def api_reference_covered_fact_ids(plan: Mapping[str, Any], facts: FactsDocument) -> frozenset[str]:
    """Every fact ID the renderer's API Reference actually displays."""
    symbols = [fact for fact in facts.by_kind("public_symbol") if fact.polarity == "SUPPORTED"]
    kinds: dict[str, list[Fact]] = {}
    for fact in symbols:
        kinds.setdefault((fact.attributes or {}).get("symbol_kind", ""), []).append(fact)
    covered = {fact.id for fact in (*kinds.get("class", []), *kinds.get("enum", []))}
    for methods in api_reference_hub_methods(plan, facts).values():
        covered.update(fact.id for fact in methods)
    return frozenset(covered)


def _documentation_resources_issues_fact_id(facts: FactsDocument) -> frozenset[str]:
    """The renderer always appends its own "Open an issue" line from ``identity:repository``."""
    identity = next((f for f in facts.by_kind("identity") if f.id == "identity:repository"), None)
    if identity is not None and identity.polarity == "SUPPORTED":
        return frozenset({"identity:repository"})
    return frozenset()


def renderer_fact_ids(
    section: str, facts: FactsDocument, plan: Mapping[str, Any] | None = None
) -> frozenset[str]:
    """The facts a mixed section's own deterministic content rests on."""
    if section == "api_reference":
        return api_reference_covered_fact_ids(plan or {}, facts)
    if section == "documentation_resources":
        return _documentation_resources_issues_fact_id(facts)
    if section != "development_testing":
        return frozenset()
    return frozenset(
        fact.id
        for fact in facts.by_kind("build_test_asset")
        if fact.id in _RENDERER_OWNED_ASSETS and fact.polarity == "SUPPORTED"
    )


def planned_heading_slugs(plan: Mapping[str, Any]) -> frozenset[str]:
    """The anchor slugs of every semantic-shell heading this candidate will actually render."""
    included = {
        str(entry.get("section_id")) for entry in plan.get("sections", []) if entry.get("include")
    }
    return frozenset(
        heading_slug(section.heading)
        for section in SEMANTIC_SHELL
        if section.id in included and section.heading
    )


_INTRA_DOC_ANCHOR = re.compile(r"\[([^\]]+)\]\(#([^)\s]+)\)")


def resolve_intra_document_anchors(text: str, planned_slugs: frozenset[str]) -> str:
    """``text`` with every intra-document anchor resolved against ``planned_slugs``."""

    def resolve(match: re.Match[str]) -> str:
        label, slug = match.group(1), unquote(match.group(2)).lower()
        return match.group(0) if slug in planned_slugs else label

    return _INTRA_DOC_ANCHOR.sub(resolve, text)


def _table_owes_its_rows(unit_id: str, destination: str, *, text_known: bool) -> bool:
    """A kept table destined for Scope and Limitations is printed, never dropped on a shared
    fact."""
    return not text_known and unit_id.endswith(".table") and destination == "scope_limitations"


def _entries_by_ordinal(dispositions: Mapping[str, Any]) -> dict[int, list[Mapping[str, Any]]]:
    """Every disposition keyed by the source-block ordinal of the unit it decides."""
    found: dict[int, list[Mapping[str, Any]]] = {}
    for entry in dispositions.get("dispositions", []):
        ordinal = _unit_ordinal(str(entry.get("unit_id", "")))
        if ordinal is not None:
            found.setdefault(ordinal, []).append(entry)
    return found


def _introduces_nothing_rendered(
    unit_id: str,
    text: str,
    destination: str,
    *,
    by_ordinal: Mapping[int, list[Mapping[str, Any]]],
    by_id: Mapping[str, Fact],
    ecosystem: str,
    example_sections: Mapping[str, str],
    example_ordinals: Mapping[str, int],
) -> bool:
    """Whether ``text`` is a kept sentence that introduces something when what it introduces is
    not rendered right after it in ``destination``."""
    if unit_id.rsplit(".", 1)[-1] != "paragraph" or not text.rstrip().endswith(":"):
        return False
    ordinal = _unit_ordinal(unit_id)
    if ordinal is None:
        return False
    if any(
        section == destination and example_ordinals.get(example_id) == ordinal + 1
        for example_id, section in example_sections.items()
    ):
        return False
    for entry in by_ordinal.get(ordinal + 1, ()):
        following = by_id.get(str(entry.get("unit_id", "")))
        if (
            following is not None
            and entry.get("disposition") in PLACED
            and entry.get("destination_section") == destination
            and renders_verbatim(following.id, following.value, ecosystem)
        ):
            return False
    return True


def _drop_orphaned_lead_ins(result: list[Placement]) -> list[Placement]:
    """``result`` with every kept lead-in dropped whose block was."""
    at: dict[int, list[Placement]] = {}
    for decision in result:
        ordinal = _unit_ordinal(decision.unit_id)
        if ordinal is not None:
            at.setdefault(ordinal, []).append(decision)
    kept: list[Placement] = []
    for decision in result:
        ordinal = _unit_ordinal(decision.unit_id)
        following = (
            [d for d in at.get(ordinal + 1, ()) if d.destination == decision.destination]
            if ordinal is not None
            else []
        )
        if (
            decision.outcome == "placed"
            and decision.unit_id.rsplit(".", 1)[-1] == "paragraph"
            and decision.text.rstrip().endswith(":")
            and following
            and all(d.outcome == "overlap" for d in following)
        ):
            marks = tuple(sorted({mark for d in following for mark in d.overlap}))
            decision = Placement(
                decision.unit_id,
                decision.destination,
                decision.text,
                "overlap",
                marks,
                decision.read_with,
            )
        kept.append(decision)
    return kept


def placements(
    plan: dict[str, Any],
    dispositions: dict[str, Any],
    facts: FactsDocument,
    ecosystem: str,
    destinations: Callable[[], Destinations] | None = None,
) -> list[Placement]:
    """Every preserved or moved unit with the outcome the three rules give it."""
    included = {
        str(entry.get("section_id")) for entry in plan.get("sections", []) if entry.get("include")
    }
    planned_slugs = planned_heading_slugs(plan)
    by_id = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    example_sections = rendered_example_ids(plan)
    rendered_examples = frozenset(example_sections)
    example_ordinals = _example_code_block_ordinals(facts)
    section_heading_ordinals = _section_heading_ordinals(dispositions)
    by_ordinal = _entries_by_ordinal(dispositions)
    root = root_heading(tuple(by_id.values()))
    shown: Destinations | None = None
    result: list[Placement] = []
    for entry in dispositions.get("dispositions", []):
        unit_id = str(entry.get("unit_id", ""))
        destination = entry.get("destination_section")
        if entry.get("disposition") not in PLACED or not destination:
            continue
        unit = by_id.get(unit_id)
        if unit is None:
            continue
        if not renders_verbatim(unit_id, unit.value, ecosystem):
            result.append(Placement(unit_id, destination, unit.value, "owned_elsewhere"))
            continue
        if destination not in included:
            result.append(Placement(unit_id, destination, unit.value, "excluded"))
            continue
        lead_in_of = _adjacent_rendered_examples(
            unit_id, rendered_examples, example_ordinals
        ) | _adjacent_section_opening(
            unit_id, destination, section_heading_ordinals, rendered_examples
        )
        covered = (
            planned_fact_ids(plan, destination)
            | renderer_fact_ids(destination, facts, plan)
            | lead_in_of
        )
        overlap = (
            ()
            if unit_id.endswith(".code_block")
            or _table_owes_its_rows(unit_id, destination, text_known=destinations is not None)
            else tuple(sorted(set(entry.get("fact_ids") or []) & covered))
        )
        if (
            not overlap
            and unit_id in covered
            and not unit_id.endswith(".code_block")
            and not _table_owes_its_rows(unit_id, destination, text_known=destinations is not None)
        ):
            overlap = (unit_id,)
        text = unit.value
        also: tuple[str, ...] = ()
        topical = False
        if destinations is not None:
            also = tuple(
                section
                for section in _STATED_BY.get(unit_topic(unit, root) or "", ())
                if section != destination
            )
            if (
                also
                and not overlap
                and (unit_id.endswith(".code_block") or not text.rstrip().endswith(":"))
            ):
                overlap, topical = also, True
        if overlap and destinations is not None:
            if shown is None:
                shown = destinations()
            if unit_id.endswith(".code_block"):
                remainder = uncovered_block(text, shown, also)
            else:
                remainder = uncovered(
                    unit_id,
                    text,
                    shown,
                    destination,
                    by_link=destination == "documentation_resources",
                    lead_in=bool(set(overlap) & lead_in_of),
                    also=also,
                    only_also=topical,
                )
            if remainder and not _introduces_nothing_rendered(
                unit_id,
                remainder,
                destination,
                by_ordinal=by_ordinal,
                by_id=by_id,
                ecosystem=ecosystem,
                example_sections=example_sections,
                example_ordinals=example_ordinals,
            ):
                text, overlap = remainder, ()
        outcome: Outcome = "overlap" if overlap else "placed"
        if outcome == "placed" and not unit_id.endswith(".code_block"):
            text = resolve_intra_document_anchors(text, planned_slugs)
        result.append(Placement(unit_id, destination, text, outcome, overlap, also))
    return _drop_orphaned_lead_ins(result)


def placed_texts(decisions: list[Placement]) -> dict[str, list[str]]:
    """The verbatim texts each section renders, in disposition order."""
    texts: dict[str, list[str]] = {}
    for placement in decisions:
        if placement.outcome == "placed":
            texts.setdefault(placement.destination, []).append(placement.text)
    return texts
