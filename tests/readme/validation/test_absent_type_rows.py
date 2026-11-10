"""A kept maintainers' API type table prints without the rows naming types the public surface lacks.

BC-14 rule (i) forbids an API-table row naming an absent type; dropping the whole table instead
loses the maintainers' other rows (R2 floor, BC-05/BC-17). The row filter is the one printable form
shared by the renderer's placement, BC-05 and the reviewer's ``disposition_coverage``.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.placement import placements
from repo_presenter.readme.review.independent_reviewer import unprinted_kept_units
from repo_presenter.readme.validation.surface_claims import (
    absent_type_rows,
    without_absent_type_rows,
)

TABLE = "\n".join(
    (
        "| Class | Description |",
        "|---|---|",
        "| `Workbook` | The workbook. |",
        "| `Cell` | A cell. |",
        "| `Range` | A range. |",
        "| `BorderStyle` | Border styles. |",
    )
)
FILTERED = "\n".join(line for line in TABLE.splitlines() if "BorderStyle" not in line)


def _fact(fact_id: str, kind: str, value: str, **attributes: str) -> Fact:
    return Fact(
        id=fact_id,
        kind=kind,  # type: ignore[arg-type]
        value=value,
        evidence=(Evidence("README.md", None),),
        polarity="SUPPORTED",
        attributes=attributes or None,
    )


def _facts(table: str = TABLE) -> FactsDocument:
    return FactsDocument(
        "r/x",
        "0" * 40,
        (
            _fact("inherited_unit:037.table", "inherited_unit", table, section="API Reference"),
            _fact("public_symbol:workbook", "public_symbol", "Workbook", symbol_kind="class"),
            _fact("public_symbol:cell", "public_symbol", "Cell", symbol_kind="class"),
            _fact("public_symbol:range", "public_symbol", "Range", symbol_kind="class"),
        ),
    )


def test_only_the_row_naming_an_absent_type_is_dropped() -> None:
    facts = _facts()
    assert absent_type_rows(TABLE, facts) == ["| `BorderStyle` | Border styles. |"]
    assert without_absent_type_rows(TABLE, facts) == FILTERED


def test_a_table_with_no_absent_row_is_returned_unchanged() -> None:
    assert without_absent_type_rows(FILTERED, _facts(FILTERED)) == FILTERED


def test_a_member_table_is_never_filtered() -> None:
    members = "\n".join(
        (
            "| Method | Description |",
            "|---|---|",
            "| `Detect` | Detects. |",
            "| `GetFormat` | Maps. |",
            "| `Convert` | Converts. |",
        )
    )
    assert without_absent_type_rows(members, _facts(members)) == members


def test_a_delegate_row_is_not_absent() -> None:
    table = TABLE.replace("Border styles.", "A delegate type.")
    assert absent_type_rows(table, _facts(table)) == []


def _dispositions() -> dict:
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:037.table",
                "disposition": "PRESERVE_ATTRIBUTED",
                "destination_section": "api_reference",
                "fact_ids": [],
            }
        ]
    }


def test_placement_prints_the_filtered_table_and_the_reviewer_calls_it_printed() -> None:
    facts = _facts()
    plan = {"sections": [{"section_id": "api_reference", "include": True}]}
    (placed,) = placements(plan, _dispositions(), facts, "python")
    assert placed.text == FILTERED
    readme = "# X\n\n## API Reference\n\n" + placed.text + "\n"
    assert unprinted_kept_units(readme, facts=facts, dispositions=_dispositions()) == []


def test_a_readme_missing_a_present_row_is_still_an_unprinted_kept_unit() -> None:
    facts = _facts()
    readme = "# X\n\n## API Reference\n\n| Class | Description |\n|---|---|\n| `Workbook` | The workbook. |\n"
    assert unprinted_kept_units(readme, facts=facts, dispositions=_dispositions()) == [
        ("inherited_unit:037.table", "PRESERVE_ATTRIBUTED")
    ]


# --- a second, unrelated table in the same text must not dilute the first one's judgement -------
#
# Real case (Aspose.Cells FOSS for Rust, Lane L, 2026-11-10): absent_type_rows pooled every
# _TABLE_ROW line across the WHOLE document (two separate tables, a blank "Traits" one included)
# before judging type share, so a genuinely absent row five of a 30-row "Enumerations" table read
# as zero -- the share was computed over both tables' rows combined, not the one table the row is
# actually in. Lane R only ever calls this on one already-isolated unit's text, so the dilution
# never surfaced there; Lane L's absent_type_row detector is the first caller to pass a whole
# multi-table README.


def test_two_separate_tables_are_judged_independently_not_pooled() -> None:
    first_table_absent_row = "| `BorderStyle` | Border styles. |"
    second_table = "\n".join(
        (
            "| Trait | Description |",
            "|---|---|",
            "| `Debug` | Formatting trait. |",
            "| `Clone` | Cloning trait. |",
        )
    )
    document = f"## API Reference\n\n{TABLE}\n\n## Traits\n\n{second_table}\n"
    facts = _facts()
    assert absent_type_rows(document, facts) == [first_table_absent_row]
    without = without_absent_type_rows(document, facts)
    assert first_table_absent_row not in without
    assert second_table in without  # the unrelated table is untouched, not judged at all
