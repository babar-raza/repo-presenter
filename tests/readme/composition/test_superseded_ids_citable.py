"""A unit may cite what reconciliation superseded into its own section.

Aspose.Cells-FOSS-for-Go (hosted Lane R, 2026-11-10): the additional-examples ``preview`` unit cites
the example headings (``inherited_unit:029.heading`` ...) while they were placed. S9 accounting then
supersedes those headings ("owned by the renderer"), and a judge that reads the settled dispositions
-- ``recertify`` -- built a task whose accepted set no longer held them, so BC-04 failed "cites facts
outside this section's set" on a candidate the cascade had passed. Nothing else about the set moves:
a fact belonging to no disposition of the section is still outside it.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    SectionTask,
    _superseded_units,
    unit_checks,
)

SECTION = "additional_examples"
SLOT = "preview"
HEADING = "inherited_unit:029.heading"
STRANGER = "inherited_unit:099.heading"


def _facts() -> FactsDocument:
    def fact(fact_id: str, kind: str, value: str) -> Fact:
        return Fact(fact_id, kind, value, (Evidence("README.md"),))  # type: ignore[arg-type]

    return FactsDocument(
        "org/Aspose.Widget-FOSS-for-Go",
        "f" * 40,
        (
            fact("identity:repository", "identity", "org/Aspose.Widget-FOSS-for-Go"),
            fact("package:name", "package", "aspose-widget-foss"),
            fact(HEADING, "inherited_unit", "### Formulas"),
            fact(STRANGER, "inherited_unit", "### Elsewhere"),
        ),
    )


def _dispositions() -> dict[str, object]:
    return {
        "dispositions": [
            {
                "unit_id": HEADING,
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": SECTION,
                "fact_ids": ["identity:repository"],
                "rationale": "Heading owned by the renderer.",
            },
            {
                "unit_id": STRANGER,
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "quick_start",
                "fact_ids": ["identity:repository"],
                "rationale": "Heading owned by the renderer.",
            },
        ]
    }


def _task(superseded: frozenset[str]) -> SectionTask:
    return SectionTask(
        SECTION,
        {},
        frozenset({"identity:repository", "package:name"}),
        (SLOT,),
        slot_facts={},
        superseded_ids=superseded,
    )


def _output(*fact_ids: str) -> dict[str, object]:
    return {
        "units": [
            {
                "section": SECTION,
                "slot": SLOT,
                "text": "The following examples show common workflows.",
                "fact_ids": list(fact_ids),
            }
        ]
    }


def _outside(errors: list[str]) -> list[str]:
    return [e for e in errors if "outside this section's set" in e]


def test_the_set_of_units_superseded_into_a_section_is_read_from_its_dispositions() -> None:
    assert _superseded_units(_dispositions(), SECTION) == frozenset({HEADING})
    assert _superseded_units(_dispositions(), "quick_start") == frozenset({STRANGER})
    assert _superseded_units(_dispositions(), "api_reference") == frozenset()


def test_a_citation_of_a_unit_superseded_into_the_section_is_not_outside_its_set() -> None:
    errors = unit_checks(
        _output("identity:repository", HEADING),
        _task(_superseded_units(_dispositions(), SECTION)),
        _facts(),
        "Aspose.Widget FOSS for Go",
    )
    assert _outside(errors) == []


def test_without_the_supersession_the_same_citation_is_outside_the_set() -> None:
    errors = unit_checks(
        _output("identity:repository", HEADING),
        _task(frozenset()),
        _facts(),
        "Aspose.Widget FOSS for Go",
    )
    assert _outside(errors) == [
        f"unit {SLOT}: cites facts outside this section's set: {HEADING}"
    ]


def test_a_unit_superseded_into_another_section_is_still_outside() -> None:
    errors = unit_checks(
        _output("identity:repository", STRANGER),
        _task(_superseded_units(_dispositions(), SECTION)),
        _facts(),
        "Aspose.Widget FOSS for Go",
    )
    assert _outside(errors) == [
        f"unit {SLOT}: cites facts outside this section's set: {STRANGER}"
    ]


# --- the mirror case: a unit zero-call restore moved OUT of this section -----------------------
#
# Cells Cpp and Note Python (local Lane R, 2026-11-10): the api_reference "intro" unit cited a
# paragraph that was SUPERSEDE_REDUNDANT into api_reference at authoring time. A zero-call restore
# pass later re-homed that paragraph into scope_limitations, because api_reference never renders a
# placed paragraph's text (readme.repair.restore_units). The intro unit's own text and fact_ids are
# unchanged by restore, so its existing citation now reads as "outside this section's set" even
# though it predates the move -- restore_units.vacated_sections names exactly the ids a restore
# pass moved out of a section, for SectionTask.restored_out_ids to still accept.


def _task_restored_out(restored_out: frozenset[str]) -> SectionTask:
    return SectionTask(
        SECTION,
        {},
        frozenset({"identity:repository", "package:name"}),
        (SLOT,),
        slot_facts={},
        restored_out_ids=restored_out,
    )


def test_vacated_sections_names_only_units_whose_destination_actually_moved() -> None:
    from repo_presenter.readme.repair.restore_units import vacated_sections

    changes = [
        {
            "unit_id": "inherited_unit:041.paragraph",
            "was": "SUPERSEDE_REDUNDANT -> api_reference",
            "now": "VERIFIED_PRESERVE -> scope_limitations",
        },
        {
            # Only the disposition changed (a stale-pin fix); the destination is the same, so
            # nothing is vacated.
            "unit_id": "inherited_unit:013.code_block",
            "was": "SUPERSEDE_REDUNDANT -> installation",
            "now": "VERIFIED_PRESERVE -> installation",
        },
    ]
    assert vacated_sections(changes) == {"api_reference": {"inherited_unit:041.paragraph"}}


def test_a_citation_of_a_unit_restore_moved_out_of_this_section_is_not_outside_its_set() -> None:
    errors = unit_checks(
        _output("identity:repository", HEADING),
        _task_restored_out(frozenset({HEADING})),
        _facts(),
        "Aspose.Widget FOSS for Go",
    )
    assert _outside(errors) == []


def test_without_restored_out_ids_the_same_citation_is_outside_the_set() -> None:
    errors = unit_checks(
        _output("identity:repository", HEADING),
        _task_restored_out(frozenset()),
        _facts(),
        "Aspose.Widget FOSS for Go",
    )
    assert _outside(errors) == [
        f"unit {SLOT}: cites facts outside this section's set: {HEADING}"
    ]


def test_a_unit_restored_out_of_a_different_section_is_still_outside() -> None:
    """Negative control: restored_out_ids from ANOTHER section's restore pass must not exempt a
    citation here -- it is the citing unit's OWN section's vacated ids that count."""
    errors = unit_checks(
        _output("identity:repository", STRANGER),
        _task_restored_out(frozenset({HEADING})),  # names HEADING, not STRANGER
        _facts(),
        "Aspose.Widget FOSS for Go",
    )
    assert _outside(errors) == [
        f"unit {SLOT}: cites facts outside this section's set: {STRANGER}"
    ]
