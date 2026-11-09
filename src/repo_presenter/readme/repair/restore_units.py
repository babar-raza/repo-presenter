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
from repo_presenter.readme.composition.placement import ATTRIBUTED, PLACING
from repo_presenter.readme.reconciliation.destinations import nearest_holdable

__all__ = ["failing_unit_ids", "restore_lost_units"]

_UNIT = re.compile(r"inherited_unit:\d+\.[a-z_]+")
#: A unit whose validator-named loss is a kind this module never re-dispositions: headings and
#: badge rows are rendered by the shell, never printed from the inherited unit itself.
_SHELL_RENDERED = frozenset({"heading", "badge_row", "html_block"})


def failing_unit_ids(details: Sequence[str], checks: Collection[str] = ("BC-05", "BC-17")) -> list[str]:
    """Unit IDs the given blocking checks name, in first-seen order, from recertify's ``details``
    (``"BC-17: inherited_unit:019.paragraph holds ..."``)."""
    seen: list[str] = []
    for detail in details:
        check, _, rest = detail.partition(": ")
        if check not in checks:
            continue
        match = _UNIT.search(rest)
        if match is not None and match.group(0) not in seen:
            seen.append(match.group(0))
    return seen


def restore_lost_units(
    dispositions: Mapping[str, Any],
    facts: FactsDocument,
    unit_ids: Sequence[str],
    holdable: Collection[str],
    included: Collection[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """``(new dispositions, changes)``. ``changes`` records, per re-dispositioned unit, its
    previous and new disposition and destination, so the caller can show exactly what moved."""
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
        destination = entry.get("destination_section")
        if destination not in holdable_set:
            destination = nearest_holdable(unit_id, attributes.get("section"), holdable_set)
        if destination is None:
            continue
        supported = bool(cited) and all(fact.polarity == "SUPPORTED" for fact in cited)
        disposition = "VERIFIED_PRESERVE" if supported else ATTRIBUTED
        if entry.get("disposition") in PLACING and entry.get("destination_section") == destination:
            continue
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
