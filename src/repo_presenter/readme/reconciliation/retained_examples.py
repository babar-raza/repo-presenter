"""Hand every unverified inherited example to Quick Start or Additional Examples, after S4.

The stage between ``merge_dispositions`` and the plan. The model's S4 answer for an example it was
told is unsupported is usually an omission ("the section is not rendered"), which loses the
project's own example and the headings around it. Mission section 7: ``NOT_VERIFIED`` is not
``FALSE``, and only redundant or CONTRADICTED content may be removed on code's say-so. So each
UNRESOLVED example's code block, and the heading and paragraph units that frame it, become
SUPERSEDE_REDUNDANT into the section that reprints them (``composition/retained_examples.py``),
citing the example fact. The renderer prints them verbatim beside its fixed not-verified note.

A framing unit is left to the model's disposition when that disposition is an evidence-backed
omission, a rewrite, or a placement elsewhere, or when the unit embeds a CONTRADICTED link or a
forbidden edition label. CONTRADICTED examples are untouched: their omission stands.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.retained_examples import (
    EXAMPLE_SECTIONS,
    SECTION_LABELS,
    RetainedExample,
    retained_examples,
)
from repo_presenter.readme.reconciliation.dispositions import (
    contradicted_embedded_links,
    contradicted_link_hrefs,
    edition_labels,
)

CODE_RATIONALE = (
    "Reprinted verbatim in {section} with a not-verified note: its example is UNRESOLVED, "
    "which is neither supported nor contradicted."
)
FRAMING_RATIONALE = (
    "Reprinted verbatim in {section} beside the unverified example it introduces."
)


def _adoptable(entry: Mapping[str, Any], text: str, hrefs: Mapping[str, str]) -> bool:
    """Whether the model's disposition for a framing unit leaves it free to be reprinted."""
    disposition = entry.get("disposition")
    free = (
        (disposition == "OMIT_UNSUPPORTED" and not entry.get("fact_ids"))
        or disposition == "DEFER_UNRESOLVED"
        or entry.get("destination_section") in EXAMPLE_SECTIONS
    )
    return (
        free
        and not contradicted_embedded_links(text, hrefs)
        and not edition_labels(text)
    )


def _hand_over(
    entry: dict[str, Any], retained: RetainedExample, rationale: str
) -> None:
    entry["disposition"] = "SUPERSEDE_REDUNDANT"
    entry["destination_section"] = retained.section
    entry["fact_ids"] = sorted({*(entry.get("fact_ids") or []), retained.example_id})
    entry["rationale"] = rationale.format(section=SECTION_LABELS[retained.section])


def retain_unverified_examples(
    dispositions: Mapping[str, Any], facts: FactsDocument
) -> dict[str, Any]:
    """``dispositions`` with every unverified example and its framing handed to its section."""
    result = copy.deepcopy(dict(dispositions))
    entries = {
        str(entry.get("unit_id")): entry for entry in result.get("dispositions", [])
    }
    text = {fact.id: fact.value for fact in facts.by_kind("inherited_unit")}
    hrefs = contradicted_link_hrefs(facts)
    for retained in retained_examples(facts):
        code = entries.get(retained.code_unit)
        if code is None:
            continue
        _hand_over(code, retained, CODE_RATIONALE)
        framing = [
            *retained.lead_units,
            *(unit for unit in (retained.section_heading_unit,) if unit),
            *retained.wrapper_units,
        ]
        for unit in framing:
            entry = entries.get(unit)
            if entry is not None and _adoptable(entry, text.get(unit, ""), hrefs):
                _hand_over(entry, retained, FRAMING_RATIONALE)
    return result
