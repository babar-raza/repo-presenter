"""Zero-call restore of inherited units a Lane R seal lost (TC-019, item-level restore).

R2/BC-17 (``validation/parity.py``) and BC-05 (``reconciliation/dispositions.py``) name, per unit,
content the published README prints and the sealed candidate lost: a unit left ``DEFER_UNRESOLVED``
with no destination, ``OMIT_UNSUPPORTED``, or ``SUPERSEDE_REDUNDANT`` into a section that does not
state it. Their own remedy text is explicit: "keep it (VERIFIED_PRESERVE/VERIFIED_MOVE, or
PRESERVE_ATTRIBUTED when no fact confirms it)". That is a pure re-disposition of a stored output -
no model has to be asked again - so it is computed here, deterministically, from the stored
dispositions and the facts already sealed in the same bundle.

What this module decides and what it does not: it changes only the ``disposition`` and
``destination_section`` of units a validator already named. It never edits unit text, never adds a
claim, and never decides a unit is true: a unit whose own cited facts are not all SUPPORTED is kept
``PRESERVE_ATTRIBUTED`` (printed as written, attribution recorded internally only - ruling R9),
never ``VERIFIED_PRESERVE``. A unit a fact CONTRADICTS is left alone (the validators, not this
module, own that exemption). The caller re-runs the full blocking validation and the independent
reviewer's deterministic rules on the result; a restore that does not make the candidate pass
changes nothing about its verdict.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.placement import ATTRIBUTED, PLACED
from repo_presenter.readme.reconciliation.destinations import nearest_holdable
from repo_presenter.readme.validation.links import unsafe_html_failures
from repo_presenter.readme.validation.surface_claims import absent_type_rows, kept_table_form

__all__ = [
    "choose_units",
    "failing_unit_ids",
    "restore_lost_units",
    "owed_citations",
    "cite_owed_units",
    "vacated_sections",
]

_UNIT = re.compile(r"inherited_unit:\d+(?:\.\d+)*\.[a-z_]+")
#: A unit whose validator-named loss is a kind this module never re-dispositions: headings and
#: badge rows are rendered by the shell, never printed from the inherited unit itself.
_SHELL_RENDERED = frozenset({"heading", "badge_row", "html_block"})
#: ``documentation_resources`` renders only its own per-link generated bullets
#: (``renderer._documentation_resources`` reads ``plan["links"]``, never a placed unit's text), so
#: ANY unit kind dispositioned there -- a kept list, paragraph or table -- is "placed" but never
#: rendered (BC-05, measured on Cells Go: a kept list of the same five documentation links the
#: generated bullets already cover). Unlike ``api_reference`` (which does print a table), no unit
#: kind ever prints here.
_GENERATED_ONLY_DESTINATIONS = frozenset({"documentation_resources"})


def failing_unit_ids(
    details: Sequence[str], checks: Collection[str] = ("BC-05", "BC-17")
) -> list[str]:
    """Unit IDs the given blocking checks name, in first-seen order, from recertify's ``details``
    (``"BC-17: inherited_unit:019.paragraph holds ..."``). BC-04 is deliberately NOT in the default:
    it names a superseded unit an AUTHORED section must state, and restoring such a unit verbatim
    can trade BC-04 for ``REVIEW:disposition_coverage`` (measured on Cells Python: the unit states
    a dependency the renderer already owns, so its restored text is never printed). Pass
    ``checks=("BC-04", ...)`` to read it anyway."""
    seen: list[str] = []
    for detail in details:
        check, _, rest = detail.partition(": ")
        if check not in checks:
            continue
        match = _UNIT.search(rest)
        if match is not None and match.group(0) not in seen:
            seen.append(match.group(0))
    return seen


#: BC-04's "a superseded unit is owed a citation in its destination section" detail
#: (``"BC-04: scope_limitations: inherited_unit:007.paragraph: superseded into this section by
#: reconciliation, so a unit must cite it ..."``). Another BC-04 shape ("cites facts outside this
#: section's set") is a different defect and is not matched.
_SUPERSEDED_INTO_SECTION = "superseded into this section by reconciliation"


def owed_citations(details: Sequence[str]) -> list[tuple[str, str]]:
    """``(section, unit id)`` for every superseded unit BC-04 says that section's authored units must
    cite (``"BC-04: scope_limitations: inherited_unit:007.paragraph: superseded into this section ..."``)."""
    owed: list[tuple[str, str]] = []
    for detail in details:
        check, _, rest = detail.partition(": ")
        if check != "BC-04" or _SUPERSEDED_INTO_SECTION not in rest:
            continue
        section, _, tail = rest.partition(": ")
        match = _UNIT.search(tail)
        if match is not None and (section, match.group(0)) not in owed:
            owed.append((section, match.group(0)))
    return owed


def _words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9_]{4,}", text.lower())}


def cite_owed_units(
    units_document: Mapping[str, Any], facts: FactsDocument, owed: Sequence[tuple[str, str]]
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """``(new units document, changes)``: the citation BC-04 asks for, added where the section
    already STATES the unit's substance. BC-05 independently proves the substance is carried (BC-04
    is the only check naming the unit), so what is missing is the authored unit's reference to the
    inherited unit it restates: the unit of that section whose text shares the most words with the
    inherited unit cites it. Nothing is written when no unit of the section shares a word. The
    caller keeps the result only if the re-judged candidate has no blocking failure."""
    output = copy.deepcopy(dict(units_document))
    inherited = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    changes: list[dict[str, str]] = []
    for section, unit_id in owed:
        fact = inherited.get(unit_id)
        if fact is None:
            continue
        target_words = _words(fact.value)
        best: tuple[int, dict[str, Any]] | None = None
        for unit in output.get("units", []):
            if not isinstance(unit, dict) or unit.get("section") != section:
                continue
            if unit_id in unit.get("fact_ids", []):
                best = None
                break
            shared = len(target_words & _words(str(unit.get("text") or "")))
            if shared and (best is None or shared > best[0]):
                best = (shared, unit)
        if best is None:
            continue
        unit = best[1]
        unit["fact_ids"] = [*unit.get("fact_ids", []), unit_id]
        changes.append({"unit_id": unit_id, "cited_by": f"{section}/{unit.get('slot')}"})
    return output, changes


_HOLDS = re.compile(
    r"^(?P<unit>inherited_unit:\d+(?:\.\d+)*\.[a-z_]+) holds (?P<category>[a-z0-9_ ]+?) "
    r"'(?P<item>.*)', which the published README prints"
)


def choose_units(
    details: Sequence[str],
    facts: FactsDocument,
    already: Collection[str] = (),
    mandatory_checks: Collection[str] = ("BC-05",),
    exclude: Collection[str] = (),
) -> list[str]:
    """The fewest units whose restoration clears what BC-05 / BC-17 name, in first-seen order.

    BC-05 names a unit that must be kept (its replacement does not carry its substance): every one
    is chosen (``mandatory_checks`` may add BC-08: a ``VERIFIED_REWRITE`` unit whose kept command the
    render does not print is returned to ``VERIFIED_PRESERVE``, which prints it as written). BC-17 names, per LOST ITEM, every unit that holds it. On the first pass one carrier
    is enough - an item a chosen unit holds is covered, and each remaining item takes the carrier
    that covers the most uncovered items, shortest text first - because restoring every holder
    prints the same identifiers several times and pushes the README over BC-07's visible-line
    budget (Cells Go 312 of 300 lines, Java 313, measured after restoring every named unit). An
    item that is STILL named after one of its holders was restored (``already``) was not cleared by
    that carrier, so it escalates: every remaining holder of it is chosen.

    ``exclude`` names units restore will not keep (``restore_lost_units(skipped=...)``: a unit whose
    text carries a dangling pointer): they are never chosen, so another holder of the same item
    is."""
    skip = set(exclude)
    mandatory = [u for u in failing_unit_ids(details, checks=tuple(mandatory_checks)) if u not in skip]
    holders: dict[tuple[str, str], list[str]] = {}
    for detail in details:
        check, _, rest = detail.partition(": ")
        match = _HOLDS.match(rest) if check == "BC-17" else None
        if match is None:
            continue
        if match["unit"] not in skip:
            holders.setdefault((match["category"], match["item"]), []).append(match["unit"])
    restored = set(already)
    covered = set(mandatory) | restored
    texts = {fact.id: len(fact.value) for fact in facts.by_kind("inherited_unit")}
    chosen = list(mandatory)
    # An item still named in ``details`` after one of its holders was restored was NOT cleared by
    # that carrier (BC-17 counts per holding unit, and the restored unit's printed text may not
    # carry the very link/identifier the published README prints at every holder: measured on
    # Cells Rust, `samples/` printed four times live, once in the seal). One carrier was enough
    # for the first pass; an item that survives it escalates to every remaining holder.
    for item, units in holders.items():
        if restored.intersection(units):
            chosen.extend(unit for unit in dict.fromkeys(units) if unit not in restored)
    covered = covered | set(chosen)
    pending = {item: units for item, units in holders.items() if not covered.intersection(units)}
    while pending:
        tally: dict[str, int] = {}
        for units in pending.values():
            for unit in set(units):
                tally[unit] = tally.get(unit, 0) + 1
        best = min(tally, key=lambda unit: (-tally[unit], texts.get(unit, 0), unit))
        chosen.append(best)
        covered.add(best)
        pending = {item: units for item, units in pending.items() if best not in units}
    return list(dict.fromkeys(chosen))


def table_contradicts_surface(text: str, facts: FactsDocument) -> bool:
    """Whether this maintainers' table is a type table (BC-14 rule (i): >= 60% of its first cells
    are verified public types, at least 3 rows) with a row naming something the public surface
    does not know. Such a row is not printed (``composition.placement`` filters it out of the
    kept table, BC-14 / ``surface_claims.without_absent_type_rows``), so the table itself is
    still restored: the maintainers' other rows are the published floor (R2). Measured on Cells
    Rust (``BorderStyle``/``CellValueKind`` live in an internal module) and HTML Python
    (``CSSDeclarationBlock``/``BreakHints``). Member tables (``Detect``, ``add(time, value)``) are
    not type tables."""
    return bool(absent_type_rows(text, facts))


def restore_lost_units(
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
    unit_ids: Sequence[str],
    holdable: Collection[str],
    included: Collection[str] | None = None,
    *,
    include_api_tables: bool = True,  # retained for callers; maintainers' API tables are restored
    skipped: list[dict[str, str]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """``(new dispositions, changes)``. ``changes`` records, per re-dispositioned unit, its
    previous and new disposition and destination, so the caller can show exactly what moved.

    A unit already kept verbatim (``VERIFIED_PRESERVE`` / ``VERIFIED_MOVE`` / ``PRESERVE_ATTRIBUTED``)
    is left alone. A ``VERIFIED_REWRITE`` unit a validator still names lost an item in its rewrite
    (BC-17 measured Cells TypeScript's ``getCell()`` / ``Workbook.images`` that way), so it is
    returned to ``VERIFIED_PRESERVE``; ``CORRECT_WITH_EVIDENCE`` is never reverted (its text was
    corrected against a fact and the original is the wrong text).

    A maintainers' TABLE bound for ``api_reference`` is restored like any other unit: BC-07's row
    count judges only the tables the renderer itself emits there (``structure.renderer_api_rows``),
    so the published README's member tables (R2: the floor) are preserved, placed verbatim after the
    renderer's own tables. ``include_api_tables`` is retained only so existing callers keep working.

    A unit whose restored text would carry a dangling in-document pointer (BC-07's "refers to a
    'X below' section this README does not have", the detector ``dangling_pointers`` that
    ``_fold_dangling_rewrites`` also uses) is NOT restored: it was ``VERIFIED_REWRITE`` precisely
    because of that pointer, and restoring it trades BC-17/BC-08 for BC-07 (hosted PDF Go
    ``025.paragraph``). Each such unit is appended to ``skipped`` (when given) and left as it was."""
    from repo_presenter.readme.reconciliation.dispositions import (
        dangling_pointers,
        unproven_source_build_blocks,
    )

    output = copy.deepcopy(dict(dispositions))
    before = {
        entry.get("unit_id"): (
            entry.get("disposition"), entry.get("destination_section"), entry.get("rationale"),
            copy.deepcopy(entry.get("fact_ids")),
        )
        for entry in output.get("dispositions", [])
    }
    units = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    by_id = {fact.id: fact for fact in facts.facts}
    # A block that prints a source-build command no build proved is never restored: BC-02 refuses
    # the README that prints it, so restoring it would trade BC-05/BC-17 for BC-02 (S4 omits it on
    # that evidence, ``dispositions.unproven_source_build_blocks``).
    forbidden = unproven_source_build_blocks(facts)
    changes: list[dict[str, str]] = []
    # A destination the plan omits prints nothing (BC-05: "placed in X, which the plan omits"), so
    # only sections that can hold a unit AND that the sealed plan includes are candidates.
    holdable_set = set(holdable) if included is None else set(holdable) & set(included)
    for entry in output.get("dispositions", []):
        unit_id = entry.get("unit_id")
        if unit_id not in unit_ids or unit_id not in units:
            continue
        if unit_id.rsplit(".", 1)[-1] in _SHELL_RENDERED:
            continue
        if unit_id in forbidden:
            if skipped is not None:
                skipped.append({"unit_id": unit_id, "reason": "forbidden_command"})
            continue
        cited = [by_id[f] for f in entry.get("fact_ids") or [] if f in by_id]
        if any(fact.polarity == "CONTRADICTED" for fact in cited):
            continue
        unit = units[unit_id]
        attributes = unit.attributes or {}
        placed = entry.get("disposition") in PLACED
        if entry.get("disposition") == "CORRECT_WITH_EVIDENCE":
            continue
        current_destination = entry.get("destination_section")
        misrendered = current_destination in _GENERATED_ONLY_DESTINATIONS or (
            current_destination == "api_reference" and unit_id.rsplit(".", 1)[-1] != "table"
        )
        if placed and not misrendered:
            # Already kept verbatim, and its destination is one that does render a placed unit:
            # nothing to change (the common case).
            continue
        destination = current_destination
        if destination not in holdable_set:
            destination = nearest_holdable(unit_id, attributes.get("section"), holdable_set)
        if destination == "api_reference" and unit_id.rsplit(".", 1)[-1] != "table":
            # api_reference prints the Core API table and its hubs from the verified surface; a
            # kept paragraph/list/code block "placed" there is never rendered (BC-05, measured on
            # Cells Cpp: 041.paragraph). This re-homes it whether it was just chosen here or was
            # already kept (PLACED) under that destination from an earlier disposition round.
            destination = nearest_holdable(
                unit_id, attributes.get("section"), holdable_set - {"api_reference"}
            )
        elif destination in _GENERATED_ONLY_DESTINATIONS:
            # Same reasoning for documentation_resources (see _GENERATED_ONLY_DESTINATIONS):
            # measured on Cells Go, a kept list already VERIFIED_MOVE'd there.
            destination = nearest_holdable(
                unit_id, attributes.get("section"), holdable_set - _GENERATED_ONLY_DESTINATIONS
            )
        if destination is None:
            continue
        if placed:
            # Already kept verbatim with a sound disposition; only its destination was wrong.
            # Leave the disposition, fact_ids and rationale exactly as they were.
            if destination == current_destination:
                continue
            changes.append(
                {
                    "unit_id": unit_id,
                    "was": f"{entry.get('disposition')} -> {current_destination}",
                    "now": f"{entry.get('disposition')} -> {destination}",
                }
            )
            entry["destination_section"] = destination
            continue
        printed = kept_table_form(unit.value, facts) if unit_id.endswith(".table") else unit.value
        if unsafe_html_failures(printed):
            # Raw HTML BC-06 forbids outside a fence or a code span (<base>, <meta>, <iframe>, ...)
            # would be printed as written; restoring it trades BC-17 for BC-06. A kept table prints
            # such an element name in a code span (``kept_table_form``), so only text that stays raw
            # in its printed form is refused (measured on HTML Python).
            continue
        supported = bool(cited) and all(fact.polarity == "SUPPORTED" for fact in cited)
        disposition = "VERIFIED_PRESERVE" if supported else ATTRIBUTED
        changes.append(
            {
                "unit_id": unit_id,
                "was": f"{entry.get('disposition')} -> {entry.get('destination_section')}",
                "now": f"{disposition} -> {destination}",
            }
        )
        entry["disposition"] = disposition
        entry["destination_section"] = destination
        if disposition == "VERIFIED_PRESERVE" and not entry.get("fact_ids"):
            entry["fact_ids"] = []
        entry["rationale"] = (
            "Kept as the maintainers wrote it: the published README prints this content and the "
            "candidate would otherwise lose it (BC-17 / BC-05)."
        )
    if changes:
        # Only PLACED units are judged, and none of these was placed before, so none was flagged before.
        flagged = {unit for unit, _, _ in dangling_pointers(output, facts)}
        pointed = {change["unit_id"] for change in changes} & flagged
        if pointed:
            for entry in output.get("dispositions", []):
                unit_id = entry.get("unit_id")
                if unit_id not in pointed:
                    continue
                (entry["disposition"], entry["destination_section"], rationale, fact_ids) = before[unit_id]
                if rationale is None:
                    entry.pop("rationale", None)
                else:
                    entry["rationale"] = rationale
                if fact_ids is None:
                    entry.pop("fact_ids", None)
                else:
                    entry["fact_ids"] = fact_ids
            if skipped is not None:
                skipped.extend(
                    {"unit_id": unit_id, "reason": "dangling_pointer"}
                    for unit_id in dict.fromkeys(c["unit_id"] for c in changes)
                    if unit_id in pointed
                )
            changes = [change for change in changes if change["unit_id"] not in pointed]
    return output, changes


def vacated_sections(changes: Sequence[Mapping[str, str]]) -> dict[str, set[str]]:
    """``{old_section: {unit_id, ...}}`` for every ``restore_lost_units`` change whose destination
    actually moved -- the shape BC-04 needs (``composition.authoring.authoring_tasks``'s
    ``restored_out`` parameter, ``SectionTask.restored_out_ids``) to still accept an authored
    unit's existing citation of a unit THIS restore pass just moved out of the citing unit's own
    section: that citation predates the move, so it is not a new out-of-scope claim. A change whose
    old and new destination are the same (only the disposition changed, e.g. a stale pin) vacates
    nothing and is not included."""
    vacated: dict[str, set[str]] = {}
    for change in changes:
        was, now = str(change.get("was", "")), str(change.get("now", ""))
        if " -> " not in was or " -> " not in now:
            continue
        old_section, new_section = was.rsplit(" -> ", 1)[1], now.rsplit(" -> ", 1)[1]
        if old_section and old_section != new_section:
            vacated.setdefault(old_section, set()).add(str(change["unit_id"]))
    return vacated
