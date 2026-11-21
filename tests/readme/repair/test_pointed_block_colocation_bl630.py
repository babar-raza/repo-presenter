"""BL-630: a kept paragraph that points at 'the table below' prints with that table (Slides .NET, hosted run
44924853748, BC-07 on ``080.paragraph`` after restore had kept the edition table elsewhere).

The four units are the real ones of the pinned README (aspose-slides-foss/Aspose.Slides-FOSS-for-.NET @ 86c441b5,
section 'Choosing an edition'): the paragraph whose last sentence says 'The table below was measured ...', the
edition table, the 'short version' paragraph and the list of the three sibling-edition repositories. Every
positive case runs the real renderer and BC-07's own detector; negative controls leave a pair that is already
together, a pair with no shared section, a unit a restore refused, and a paragraph pointing at nothing.
"""

from __future__ import annotations

import copy
from typing import Any

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.references import dangling_references
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.reconciliation.destinations import holdable_sections
from repo_presenter.readme.repair.restore_units import (
    colocate_pointed_blocks,
    pointer_gaps,
    restore_lost_units,
)
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _entry, _facts, _plan, _unit

PARAGRAPH = (
    "There are four editions of this library and they are **not** interchangeable. Three of them —\n"
    ".NET, Java and C++ — are the same design in three languages; Python is a larger and different one.\n"
    "The table below was measured on 2026-08-16 by running each edition and reading the XML in the file\n"
    "it produced."
)
TABLE = "\n".join(
    [
        "| | .NET | Java | C++ | Python |",
        "|---|---|---|---|---|",
        "| Create, open, round-trip, save | yes | yes | yes | yes |",
        "| Save to a stream | yes | yes | **no** | yes |",
        "| Sections | **yes** | no | no | no |",
        "| Charts | no | no | no | **yes** |",
        "| Formats `Save` writes | 3 | 3 | 6 | 7 |",
    ]
)
SHORT = (
    "The short version: **if you need charts, animations, transitions, themes, backgrounds, group shapes\n"
    "or hyperlinks, none of them exist in this edition — use the Python one.**"
)
P, T, S = "inherited_unit:080.paragraph", "inherited_unit:081.table", "inherited_unit:082.paragraph"
DETAIL = (
    f"BC-07: {P} is kept as written but says 'table below' but no table follows it in this section: "
    "'The table below was measured on 2026-08-16 by running each edition and reading the XML in the file it produced.'"
)


def _world() -> FactsDocument:
    base = _facts()
    return FactsDocument(
        base.repository, base.source_revision,
        (
            *base.facts,
            _unit("079.heading", "## Choosing an edition"),
            _unit("080.paragraph", PARAGRAPH),
            _unit("081.table", TABLE),
            _unit("082.paragraph", SHORT),
        ),
    )


def _kept(**where: tuple[str, str | None]) -> dict[str, Any]:
    """The dispositions: ``unit -> (disposition, destination)``."""
    document = _dispositions()
    for unit, (disposition, destination) in where.items():
        document["dispositions"].append(_entry(unit.replace("_", "."), disposition, destination, []))
    return document


def _paragraph_in(destination: str, table: tuple[str, str | None]) -> dict[str, Any]:
    return _kept(
        **{
            "080_paragraph": ("PRESERVE_ATTRIBUTED", destination),
            "081_table": table,
            "082_paragraph": ("PRESERVE_ATTRIBUTED", "scope_limitations"),
        }
    )


def _readme(facts: FactsDocument, dispositions: dict[str, Any], plan: dict[str, Any] | None = None) -> str:
    return render_readme(ENTRY, facts, plan or _plan(hubs=False), copy.deepcopy(UNITS), dispositions)


def _pointer_dangles(readme: str) -> bool:
    return any("table below" in reference.sentence for reference in dangling_references(readme))


def _destination(dispositions: dict[str, Any], unit: str) -> tuple[str, Any]:
    entry = next(e for e in dispositions["dispositions"] if e["unit_id"] == unit)
    return entry["disposition"], entry["destination_section"]


def _holdable(facts: FactsDocument) -> tuple[str, ...]:
    return holdable_sections(facts)


def test_the_detail_is_read_as_a_paragraph_and_the_block_it_points_at() -> None:
    assert pointer_gaps([DETAIL]) == [(P, "table")]
    assert pointer_gaps([DETAIL.replace("BC-07", "BC-06")]) == []
    assert pointer_gaps(["BC-07: inherited_unit:080.paragraph ends with a colon but nothing follows it"]) == []


def test_a_paragraph_kept_away_from_its_table_moves_to_the_table_before_it_prints() -> None:
    facts = _world()
    holdable = _holdable(facts)
    start = _paragraph_in("key_capabilities", ("PRESERVE_ATTRIBUTED", "scope_limitations"))
    assert _pointer_dangles(_readme(facts, start))  # the hosted failure, through the real renderer
    fixed, changes = colocate_pointed_blocks(start, facts, [DETAIL], holdable, holdable)
    assert _destination(fixed, P) == ("PRESERVE_ATTRIBUTED", "scope_limitations")
    assert _destination(fixed, T) == ("PRESERVE_ATTRIBUTED", "scope_limitations")
    assert changes == [
        {"unit_id": P, "was": "PRESERVE_ATTRIBUTED -> key_capabilities", "now": "PRESERVE_ATTRIBUTED -> scope_limitations"}
    ]
    readme = _readme(facts, fixed)
    assert not _pointer_dangles(readme)
    assert "The table below was measured" in readme and "| Sections | **yes** |" in readme
    assert start["dispositions"] != fixed["dispositions"]  # the input is never edited in place


def test_a_table_the_restore_never_kept_is_restored_beside_the_paragraph() -> None:
    facts = _world()
    holdable = _holdable(facts)
    start = _paragraph_in("scope_limitations", ("OMIT_UNSUPPORTED", None))
    assert _pointer_dangles(_readme(facts, start))
    fixed, changes = colocate_pointed_blocks(start, facts, [DETAIL], holdable, holdable)
    assert _destination(fixed, T) == ("PRESERVE_ATTRIBUTED", "scope_limitations")
    assert [c["unit_id"] for c in changes] == [T]
    assert not _pointer_dangles(_readme(facts, fixed))


def test_a_pair_the_table_s_section_cannot_share_keeps_the_paragraphs_section() -> None:
    """api_reference prints a table and no paragraph: the pair meets in the paragraph's own section."""
    facts = _world()
    holdable = _holdable(facts)
    start = _paragraph_in("scope_limitations", ("PRESERVE_ATTRIBUTED", "api_reference"))
    fixed, changes = colocate_pointed_blocks(start, facts, [DETAIL], holdable, holdable)
    assert _destination(fixed, P)[1] == _destination(fixed, T)[1] == "scope_limitations"
    assert [c["unit_id"] for c in changes] == [T]


def test_a_pair_already_together_a_missing_block_and_a_pointer_at_nothing_are_left_alone() -> None:
    facts = _world()
    holdable = _holdable(facts)
    together = _paragraph_in("scope_limitations", ("PRESERVE_ATTRIBUTED", "scope_limitations"))
    same, changes = colocate_pointed_blocks(together, facts, [DETAIL], holdable, holdable)
    assert same == together and changes == []
    no_gap, none = colocate_pointed_blocks(together, facts, [], holdable, holdable)
    assert no_gap == together and none == []
    # a paragraph with no table after it in its own section: nothing to join
    alone = FactsDocument(
        facts.repository, facts.source_revision,
        tuple(f for f in facts.facts if f.id != "inherited_unit:081.table"),
    )
    start = _kept(**{"080_paragraph": ("PRESERVE_ATTRIBUTED", "key_capabilities")})
    left, nothing = colocate_pointed_blocks(start, alone, [DETAIL], holdable, holdable)
    assert left == start and nothing == []
    # a unit a restore already refused or rolled back is never touched again
    away = _paragraph_in("key_capabilities", ("PRESERVE_ATTRIBUTED", "scope_limitations"))
    kept, untouched = colocate_pointed_blocks(away, facts, [DETAIL], holdable, holdable, exclude=[P])
    assert kept == away and untouched == []
    # a paragraph that is not kept (lost) is the restore's, not this lever's
    lost = _paragraph_in("scope_limitations", ("PRESERVE_ATTRIBUTED", "scope_limitations"))
    lost["dispositions"] = [
        {**e, "disposition": "OMIT_UNSUPPORTED", "destination_section": None} if e["unit_id"] == P else e
        for e in lost["dispositions"]
    ]
    unchanged, none = colocate_pointed_blocks(lost, facts, [DETAIL], holdable, holdable)
    assert unchanged == lost and none == []


def test_no_shared_section_records_why_and_changes_nothing() -> None:
    facts = _world()
    start = _paragraph_in("key_capabilities", ("PRESERVE_ATTRIBUTED", "api_reference"))
    skipped: list[dict[str, str]] = []
    # only these two sections are offered: key_capabilities prints no table, api_reference no paragraph
    fixed, changes = colocate_pointed_blocks(
        start, facts, [DETAIL], ("key_capabilities", "api_reference"), None, skipped=skipped
    )
    assert fixed == start and changes == []
    assert skipped == [{"unit_id": P, "reason": "pointer_block_has_no_shared_section"}]


def test_the_two_restore_levers_compose_to_the_hosted_end_state() -> None:
    """restore keeps the omitted table where the nearest section prints one, then the pair is joined."""
    facts = _world()
    holdable = _holdable(facts)
    start = _paragraph_in("key_capabilities", ("OMIT_UNSUPPORTED", None))
    restored, first = restore_lost_units(start, facts, [T], holdable, holdable)
    assert [c["unit_id"] for c in first] == [T]
    assert _pointer_dangles(_readme(facts, restored))  # the failure the hosted run stayed on
    fixed, second = colocate_pointed_blocks(restored, facts, [DETAIL], holdable, holdable)
    assert [c["unit_id"] for c in second] == [P]
    assert not _pointer_dangles(_readme(facts, fixed))
