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

__all__ = ["choose_units", "failing_unit_ids", "restore_lost_units"]

_UNIT = re.compile(r"inherited_unit:\d+(?:\.\d+)*\.[a-z_]+")
#: A unit whose validator-named loss is a kind this module never re-dispositions: headings and
#: badge rows are rendered by the shell, never printed from the inherited unit itself.
_SHELL_RENDERED = frozenset({"heading", "badge_row", "html_block"})


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


_HOLDS = re.compile(
    r"^(?P<unit>inherited_unit:\d+(?:\.\d+)*\.[a-z_]+) holds (?P<category>[a-z0-9_ ]+?) "
    r"'(?P<item>.*)', which the published README prints"
)


def choose_units(
    details: Sequence[str], facts: FactsDocument, already: Collection[str] = ()
) -> list[str]:
    """The fewest units whose restoration clears what BC-05 / BC-17 name, in first-seen order.

    BC-05 names a unit that must be kept (its replacement does not carry its substance): every one
    is chosen. BC-17 names, per LOST ITEM, every unit that holds it, and one carrier is enough -
    so an item a chosen (or already restored) unit holds is covered, and each remaining item takes
    the carrier that covers the most uncovered items, shortest text first. Restoring every holder
    prints the same identifiers several times and pushes the README over BC-07's visible-line
    budget (Cells Go 312 of 300 lines, Java 313, measured after restoring every named unit)."""
    mandatory = failing_unit_ids(details, checks=("BC-05",))
    holders: dict[tuple[str, str], list[str]] = {}
    for detail in details:
        check, _, rest = detail.partition(": ")
        match = _HOLDS.match(rest) if check == "BC-17" else None
        if match is None:
            continue
        holders.setdefault((match["category"], match["item"]), []).append(match["unit"])
    covered = set(mandatory) | set(already)
    texts = {fact.id: len(fact.value) for fact in facts.by_kind("inherited_unit")}
    chosen = list(mandatory)
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


def restore_lost_units(
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
    unit_ids: Sequence[str],
    holdable: Collection[str],
    included: Collection[str] | None = None,
    *,
    include_api_tables: bool = False,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """``(new dispositions, changes)``. ``changes`` records, per re-dispositioned unit, its
    previous and new disposition and destination, so the caller can show exactly what moved.

    A unit already kept verbatim (``VERIFIED_PRESERVE`` / ``VERIFIED_MOVE`` / ``PRESERVE_ATTRIBUTED``)
    is left alone. A ``VERIFIED_REWRITE`` unit a validator still names lost an item in its rewrite
    (BC-17 measured Cells TypeScript's ``getCell()`` / ``Workbook.images`` that way), so it is
    returned to ``VERIFIED_PRESERVE``; ``CORRECT_WITH_EVIDENCE`` is never reverted (its text was
    corrected against a fact and the original is the wrong text).

    A maintainers' TABLE bound for ``api_reference`` is deferred (``include_api_tables`` False):
    the Core API table is rendered from the verified public surface, and printing the maintainers'
    class table beside it fails BC-07 ("lists N rows for M verified public types", measured on
    Cells TypeScript/Go/Cpp/Java after the first restore pass). Other units usually carry the same
    identifiers, so the caller restores those first and asks for the deferred tables only when the
    items are still lost."""
    output = copy.deepcopy(dict(dispositions))
    units = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    by_id = {fact.id: fact for fact in facts.facts}
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
        cited = [by_id[f] for f in entry.get("fact_ids") or [] if f in by_id]
        if any(fact.polarity == "CONTRADICTED" for fact in cited):
            continue
        unit = units[unit_id]
        attributes = unit.attributes or {}
        if entry.get("disposition") in PLACED or entry.get("disposition") == "CORRECT_WITH_EVIDENCE":
            continue
        destination = entry.get("destination_section")
        if destination not in holdable_set:
            destination = nearest_holdable(unit_id, attributes.get("section"), holdable_set)
        if destination is None:
            continue
        if (
            destination == "api_reference"
            and unit_id.rsplit(".", 1)[-1] == "table"
            and not include_api_tables
        ):
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
    return output, changes
