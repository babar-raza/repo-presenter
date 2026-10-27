"""BC-04, BC-05 and BC-08: units cite facts, every inherited unit is accounted for, kept content survives.

ADAPT (import paths, public names, one memo) from the old repository-presenter project's
``components/readme/validation/registry.py``: ``_check_units`` (BC-04), ``_check_dispositions``
and ``_dropped_list_failures`` (BC-05), ``protected_fragments`` and ``_check_protected`` (BC-08),
and the placement helpers they share. The per-section ``unit_checks`` call is the same function
the authoring stage already runs (``readme/composition/authoring.py``); BC-04 re-runs it on the
final units and adds the rendered-prose identifier rule.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from typing import Any

from repo_presenter.core.examples import collapse_blank_runs
from repo_presenter.core.facts import Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    allowed_identifiers,
    cited_inherited_identifiers,
    identifier_allowed,
    surface_members,
    unit_checks,
    verified_members,
)
from repo_presenter.readme.composition.components.identity import product_name
from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL
from repo_presenter.readme.composition.list_coverage import (
    OWED_SECTIONS,
    list_items,
    missing_items,
)
from repo_presenter.readme.composition.placement import Placement
from repo_presenter.readme.composition.renderer import (
    ENTERPRISE_SENTENCE_LEAD,
    RenderContext,
)
from repo_presenter.readme.composition.retained_examples import (
    active_retained,
    block_lines,
)
from repo_presenter.readme.validation.deferrals import review_deferrals
from repo_presenter.readme.validation.failures import Candidate, CausalStage, Failure
from repo_presenter.readme.validation.text import (
    COMMAND,
    SPAN,
    fence_body,
    normalized,
    outside_fences,
    section_texts,
    sha256,
    unit_type,
)

# The placement dispositions the renderer acts on (kept as written, moved, or corrected).
PLACING = frozenset(
    {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE", "CORRECT_WITH_EVIDENCE"}
)
# The sections whose rendered text must state every item of a list kept as written that placement
# dropped as covered: the authored limitation and summary slots, and the one authored line per
# link of Documentation and Resources.
LIST_OBLIGED = OWED_SECTIONS | {"documentation_resources"}


def placements_of(candidate: Candidate) -> list[Placement]:
    """Exactly what the renderer placed, decided on the document as it renders with no kept unit
    placed (``RenderContext.placements``). Several checks ask, so the answer is remembered on the
    candidate for as long as the artifacts it is a function of are unchanged."""
    signature = sha256(
        json.dumps(
            [candidate.plan, candidate.units, candidate.dispositions],
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    )
    remembered = getattr(candidate, "_placement_memo", None)
    if remembered is not None and remembered[0] == signature:
        decisions: list[Placement] = remembered[1]
        return decisions
    context = RenderContext(
        candidate.entry,
        candidate.facts.canonical(),
        candidate.plan,
        candidate.units,
        candidate.dispositions,
    )
    decisions = context.placements
    object.__setattr__(candidate, "_placement_memo", (signature, decisions))
    return decisions


def placed_texts(candidate: Candidate) -> list[str]:
    return [p.text for p in placements_of(candidate) if p.outcome == "placed"]


def verbatim_lines(candidate: Candidate) -> frozenset[str]:
    """The stripped lines of every placed inherited prose unit's verbatim text.

    README_CONTRACT.md section 7, check 8 (protected content preserved) requires a placed unit to
    render exactly as the upstream wrote it, so the renderer cannot raise an abbreviation inside it
    without breaking that check. A code block is excluded: it sits in a fence, which the
    abbreviation scan never reads in the first place.
    """
    return frozenset(
        line.strip()
        for placement in placements_of(candidate)
        if placement.outcome == "placed"
        and not placement.unit_id.endswith(".code_block")
        for line in placement.text.splitlines()
        if line.strip()
    )


def _example_for_unit(facts: FactsDocument, unit_id: str) -> Fact | None:
    marker = f"unit {unit_id}"
    for fact in facts.by_kind("example"):
        if any(marker in (evidence.detail or "") for evidence in fact.evidence):
            return fact
    return None


def unit_failures(candidate: Candidate) -> list[Failure]:
    """BC-04: every unit cites existing SUPPORTED facts, its own per-section rules hold, and every
    identifier in a code span of the authored prose is a fact value or a verified member."""
    failures: list[Failure] = []
    facts = candidate.facts
    name = product_name(candidate.entry)
    by_id = {fact.id: fact for fact in facts.facts}
    by_section: dict[str, list[dict[str, Any]]] = {}
    for unit in candidate.units.get("units", []):
        by_section.setdefault(str(unit.get("section", "")), []).append(unit)
        label = f"{unit.get('section')}/{unit.get('slot')}"
        for fact_id in unit.get("fact_ids", []):
            fact = by_id.get(fact_id)
            section = str(unit.get("section", "")) or None
            if fact is None:
                failures.append(
                    Failure(
                        "COMPOSING", f"{label} cites unknown fact {fact_id}", section
                    )
                )
            elif fact.polarity != "SUPPORTED":
                failures.append(
                    Failure(
                        "COMPOSING",
                        f"{label} cites {fact_id}, which is {fact.polarity}",
                        section,
                    )
                )
    for task in candidate.tasks:
        owned = [
            u
            for u in by_section.get(task.section_id, [])
            if u.get("slot") in task.slots
        ]
        recorded = [
            item
            for item in candidate.units.get("omitted", [])
            if isinstance(item, dict) and item.get("section") == task.section_id
        ]
        partial = {"units": owned, "omitted": recorded}
        failures.extend(
            Failure("COMPOSING", f"{task.section_id}: {error}", task.section_id)
            for error in unit_checks(partial, task, facts, name)
        )
    allowed = allowed_identifiers(facts, name)
    # The same per-unit citation scoping unit_checks applies, restricted to scope_limitations
    # units and unioned across them: a rendered README line is not traced back to the one unit
    # that wrote it. Never wider than what some scope_limitations unit in this candidate cites.
    cited_ids = {
        fact_id
        for unit in candidate.units.get("units", [])
        if unit.get("section") == "scope_limitations"
        for fact_id in unit.get("fact_ids", [])
    }
    allowed = allowed | cited_inherited_identifiers(facts, cited_ids)
    members = verified_members(facts)
    methods = surface_members(facts)
    values = {fact.value for fact in facts.facts if fact.polarity == "SUPPORTED"}
    symbols = {
        fact.value.rsplit(".", 1)[-1]
        for fact in facts.by_kind("public_symbol")
        if fact.polarity == "SUPPORTED"
    }
    placed_lines = {
        line for text in placed_texts(candidate) for line in text.splitlines()
    }
    # A deterministic (renderer-owned) section's spans come from facts and their evidence, so the
    # identifier rule judges authored prose only.
    owners = {section.id: section.owner for section in SEMANTIC_SHELL}
    texts = section_texts(candidate.readme)
    renderer_lines = {
        line
        for section_id, text in texts.items()
        if owners.get(section_id) == "D"
        for line in text.splitlines()
    }
    # The API Reference table rows and member bullets are rendered from the symbol facts.
    renderer_lines.update(
        line
        for line in texts.get("api_reference", "").splitlines()
        if line.startswith(("| ", "- `"))
    )
    seen: set[str] = set()
    # An unverified inherited example is reprinted as the project wrote it, with the renderer's
    # note, like a kept unit: its prose is not authored here.
    renderer_lines.update(
        line
        for block in active_retained(candidate.facts, candidate.dispositions)
        for line in block_lines(block)
    )
    for line in outside_fences(candidate.readme):
        if line in placed_lines or line in renderer_lines:
            continue
        for span in SPAN.findall(line):
            if span in seen:
                continue
            seen.add(span)
            if (
                span not in values
                and span not in symbols
                and not identifier_allowed(span, allowed, members, methods)
            ):
                failures.append(
                    Failure("COMPOSING", f"code span {span!r} is not a fact value")
                )
    return failures


def _dropped_list_failures(
    candidate: Candidate, placement: Placement, texts: Mapping[str, str]
) -> list[Failure]:
    """A list kept as written that placement dropped because its destination "already covers that
    material" must in fact state every one of its items.

    Placement drops a list only for items the destination states, so on a placement the renderer
    made this finds nothing; it is the independent statement of the standard. The drop is
    exclusive on fact IDs, so one shared fact could drop a whole list the section only partly
    states (wave-3 acceptance review, LST-01). An item of Documentation and Resources is judged by
    the link it carries; any other by its subject words.
    """
    destination = placement.destination
    if (
        destination not in LIST_OBLIGED
        or not placement.unit_id.endswith(".list")
        or len(list_items(placement.text)) < 2
    ):
        return []
    by_link = destination == "documentation_resources"
    # What the commercial edition adds is not a limitation of this one: the closing Enterprise
    # paragraph never states a kept list's items.
    section_text = texts.get(destination, "").split(ENTERPRISE_SENTENCE_LEAD, 1)[0]
    # A list about installing is also stated by the renderer's Installation and Dependencies
    # sections, whichever section it was sent to (``Placement.read_with``).
    for other in placement.read_with:
        section_text += "\n" + texts.get(other, "")
    missing = missing_items(
        placement.text,
        section_text,
        by_link=by_link,
        document_text=candidate.readme,
    )
    if not missing:
        return []
    handed = any(
        placement.unit_id in (item.get("unit_ids") or [])
        for item in candidate.plan.get("material_limitations", [])
    )
    unplanned = destination == "documentation_resources" or (
        destination == "scope_limitations" and not handed
    )
    stage: CausalStage = "PLANNING" if unplanned else "COMPOSING"
    shown = "; ".join(
        repr(" ".join(item.replace("**", "").split())[:120]) for item in missing
    )
    return [
        Failure(
            stage,
            f"{placement.unit_id}: kept as written in {destination}, but the section does not "
            f"state {len(missing)} of its {len(list_items(placement.text))} items: {shown}",
            destination,
        )
    ]


def disposition_failures(candidate: Candidate) -> list[Failure]:
    """BC-05: every inherited unit has exactly one disposition, no disposition names an unknown
    unit, no blocking deferral remains, and every placed unit renders in its destination."""
    failures: list[Failure] = []
    inherited = {fact.id: fact for fact in candidate.facts.by_kind("inherited_unit")}
    entries = candidate.dispositions.get("dispositions", [])
    counts = Counter(str(entry.get("unit_id", "")) for entry in entries)
    for unit_id in inherited:
        if counts.get(unit_id, 0) != 1:
            failures.append(
                Failure(
                    "RECONCILING",
                    f"{unit_id} has {counts.get(unit_id, 0)} dispositions; exactly one is required",
                    unit=unit_id,
                )
            )
    for unit_id in counts:
        if unit_id not in inherited:
            failures.append(
                Failure(
                    "RECONCILING", f"{unit_id} is not an inherited unit of this README"
                )
            )
    # A deferred unit is never placed, so it cannot reach the public text; what its cause may do
    # is fail the candidate (validation/deferrals.py). An ADVISORY cause never fails it.
    for finding in review_deferrals(
        candidate.dispositions, candidate.facts, candidate.plan, candidate.readme
    ):
        if finding.decision == "BLOCK":
            failures.append(
                Failure(
                    finding.stage,
                    f"{finding.unit_id} is deferred as {finding.class_id}: {finding.reason}",
                    unit=finding.unit_id,
                )
            )
    headed = {section.id for section in SEMANTIC_SHELL if section.heading}
    texts = section_texts(candidate.readme)
    for placement in placements_of(candidate):
        destination = placement.destination
        if placement.outcome == "excluded":
            failures.append(
                Failure(
                    "PLANNING",
                    f"{placement.unit_id} was placed in {destination}, which the plan omits",
                    unit=placement.unit_id,
                )
            )
            continue
        if placement.outcome == "overlap":
            failures.extend(_dropped_list_failures(candidate, placement, texts))
            continue  # the plan's own content covers it (the list's items are judged above)
        if placement.outcome != "placed":
            continue  # owned by the plan or the renderer
        haystack = (
            texts.get(destination, "") if destination in headed else candidate.readme
        )
        if normalized(placement.text) not in normalized(haystack):
            failures.append(
                Failure(
                    "COMPOSING",
                    f"{placement.unit_id} was placed in {destination} but the candidate does "
                    "not render it there",
                )
            )
    return failures


def protected_fragments(candidate: Candidate) -> list[tuple[str, str, str]]:
    """(category, text, unit_id) for every command, ecosystem example, and verbatim-placed prose
    unit of the existing README: the content whose loss BC-08 judges."""
    fragments: list[tuple[str, str, str]] = []
    placed = {p.unit_id for p in placements_of(candidate) if p.outcome == "placed"}
    for fact in candidate.facts.by_kind("inherited_unit"):
        if unit_type(fact.id) == "code_block":
            language, body = fence_body(fact.value)
            if language == candidate.entry.ecosystem and body.strip():
                # An example enters the facts with its blank-line runs collapsed, so the upstream
                # body is compared in the same normalised spacing.
                fragments.append(("example", collapse_blank_runs(body), fact.id))
            fragments.extend(
                ("command", line.strip(), fact.id)
                for line in body.splitlines()
                if COMMAND.match(line)
            )
        else:
            fragments.extend(
                ("command", span, fact.id)
                for span in SPAN.findall(fact.value)
                if COMMAND.match(span)
            )
            if fact.id in placed:
                fragments.append(("unit", fact.value, fact.id))
    return fragments


def protected_failures(candidate: Candidate) -> list[Failure]:
    """BC-08: every command, example and kept unit a placing disposition keeps is rendered."""
    failures: list[Failure] = []
    by_unit = {
        str(entry.get("unit_id", "")): entry
        for entry in candidate.dispositions.get("dispositions", [])
    }
    normalized_readme = normalized(candidate.readme)
    for category, text, unit_id in protected_fragments(candidate):
        entry = by_unit.get(unit_id, {})
        disposition = entry.get("disposition")
        if disposition not in PLACING or category == "unit":
            continue
        if normalized(text) in normalized_readme:
            continue
        # The disposition names the destination section a dropped command or example belongs to,
        # so a COMPOSING failure routes to the section that may re-author it.
        destination = entry.get("destination_section")
        if category == "example":
            example = _example_for_unit(candidate.facts, unit_id)
            if example is None or example.polarity != "SUPPORTED":
                failures.append(
                    Failure(
                        "RECONCILING",
                        f"{unit_id}: {disposition} keeps an example that was never verified "
                        f"({'no example fact' if example is None else example.polarity}); "
                        "it cannot be rendered",
                    )
                )
            else:
                failures.append(
                    Failure(
                        "COMPOSING",
                        f"{unit_id}: {disposition} keeps {example.id} but the candidate does "
                        "not render it",
                        destination,
                    )
                )
        else:
            failures.append(
                Failure(
                    "COMPOSING",
                    f"{unit_id}: {disposition} keeps the command {text!r} but the candidate "
                    "does not render it",
                    destination,
                )
            )
    return failures
