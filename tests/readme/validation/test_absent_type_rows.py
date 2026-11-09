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
