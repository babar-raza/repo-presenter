"""A maintainers' API table row naming a type the public surface no longer has is removed whole.

The table rows are verbatim from the live README of aspose-cells-foss/Aspose.Cells-FOSS-for-Rust's
"Enumerations" table (fetched 2026-11-10): `BorderStyle`, `CellValueKind`, `FillPatternKind`,
`SheetVisibility` and `ValidationMessageSeverity` are the five real rows the independent reviewer's
`claim_contradiction` rule REJECTs the Lane L candidate for -- none of them a type the crate's
current public surface exports.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.absent_type_row import absent_type_row
from repo_presenter.readme.correction.model import TABLE_ROW_REMOVAL
from repo_presenter.readme.correction.apply import apply_edits
from repo_presenter.readme.validation.surface_claims import without_absent_type_rows
from repo_presenter.core.facts import FactsDocument

# The real "Enumerations" table, trimmed to 13 rows (8 real types the facts below record, 5 the
# live README still lists but the crate no longer exports), header and separator exactly as
# printed.
ENUM_TABLE = (
    "#### Enumerations\n"
    "\n"
    "| Enumeration | Description |\n"
    "|---|---|\n"
    "| `AutoShapeType` | Specifies the type of an auto shape (preset geometry). |\n"
    "| `BorderLineStyle` | Represents border. |\n"
    "| `BorderStyle` | Enum with 14 members. |\n"
    "| `CellObjectValue` | Enum with 14 methods and 5 members. |\n"
    "| `CellValue` | Enum with 8 methods and 7 members. |\n"
    "| `CellValueKind` | Enum with 7 members. |\n"
    "| `CellValueType` | Specifies cell value type. |\n"
    "| `DateSystem` | Enum with 2 members. |\n"
    "| `DiagnosticSeverity` | Enum with 4 members. |\n"
    "| `FillPatternKind` | Enum with 18 members. |\n"
    "| `FilterOperatorType` | Represents FilterOperatorType. |\n"
    "| `SheetVisibility` | SheetVisibility enum defines three visibility states. |\n"
    "| `ValidationMessageSeverity` | Enum with 3 members. |\n"
    "\n"
    "#### Traits\n"
)
PRESENT_TYPES = (
    "AutoShapeType",
    "BorderLineStyle",
    "CellObjectValue",
    "CellValue",
    "CellValueType",
    "DateSystem",
    "DiagnosticSeverity",
    "FilterOperatorType",
)
ABSENT_TYPES = (
    "BorderStyle",
    "CellValueKind",
    "FillPatternKind",
    "SheetVisibility",
    "ValidationMessageSeverity",
)


def _type_symbols(make_fact: Any) -> list[Any]:
    return [
        make_fact(
            f"public_symbol:{name.lower()}",
            f"aspose_cells::{name}",
            attributes={"symbol_kind": "enum"},
        )
        for name in PRESENT_TYPES
    ]


def _ctx(make_context: Any, make_facts: Any, make_fact: Any, readme: str = ENUM_TABLE) -> Any:
    return make_context(readme, make_facts(*_type_symbols(make_fact)))


def test_each_absent_row_becomes_one_table_row_removal_edit(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = _ctx(make_context, make_facts, make_fact)
    result = absent_type_row(ctx)
    assert result.findings == ()
    assert len(result.edits) == len(ABSENT_TYPES)
    for edit in result.edits:
        assert edit.kind == TABLE_ROW_REMOVAL
        assert edit.replacement == ""
        assert edit.original.count("\n") == 1 and edit.original.endswith("\n")
        assert edit.fact_ids  # cites the present-surface evidence, never empty
    named = {f"`{name}`" for name in ABSENT_TYPES}
    assert all(any(name in edit.original for name in named) for edit in result.edits)


def test_applying_the_edits_matches_lane_rs_own_kept_table_reading(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """The one printable form of a kept table (Lane R's ``without_absent_type_rows``) and Lane
    L's own patch must never disagree: applying this detector's edits to the live text produces
    exactly what that function already computes."""
    ctx = _ctx(make_context, make_facts, make_fact)
    result = absent_type_row(ctx)
    corrected, _spans = apply_edits(ENUM_TABLE, list(result.edits))
    assert corrected == without_absent_type_rows(ENUM_TABLE, ctx.facts)
    for absent in ABSENT_TYPES:
        assert f"`{absent}`" not in corrected
    for present in PRESENT_TYPES:
        assert f"`{present}`" in corrected
    # header, separator and the following heading are untouched
    assert "| Enumeration | Description |\n|---|---|\n" in corrected
    assert "#### Traits\n" in corrected


def test_a_present_only_table_is_left_alone(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    # A table of present types only, 8 rows (still >= _TABLE_MIN_ROWS): nothing to remove.
    table = (
        "| Enumeration | Description |\n"
        "|---|---|\n"
        + "".join(f"| `{name}` | Present. |\n" for name in PRESENT_TYPES)
    )
    ctx = _ctx(make_context, make_facts, make_fact, table)
    result = absent_type_row(ctx)
    assert result.edits == () and result.findings == ()


def test_a_table_whose_type_share_is_too_low_is_not_judged_at_all(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """Fewer than 60% of the rows are verified types (mostly unrelated prose-shaped rows): not
    read as an API type table at all, matching ``absent_type_rows``'s own threshold -- this
    detector must never edit a table that isn't one."""
    table = (
        "| Name | Note |\n"
        "|---|---|\n"
        "| `SomethingElse` | Not a type. |\n"
        "| `AnotherThing` | Also not a type. |\n"
        "| `AutoShapeType` | Present. |\n"
    )
    ctx = _ctx(make_context, make_facts, make_fact, table)
    result = absent_type_row(ctx)
    assert result.edits == () and result.findings == ()


def test_a_fenced_table_is_never_edited(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    fenced = "```text\n" + ENUM_TABLE + "```\n"
    ctx = _ctx(make_context, make_facts, make_fact, fenced)
    result = absent_type_row(ctx)
    assert result.edits == () and result.findings == ()


def test_no_type_facts_at_all_means_nothing_to_judge(
    make_context: Any, make_facts: Any
) -> None:
    ctx = make_context(ENUM_TABLE, make_facts())
    result = absent_type_row(ctx)
    assert result.edits == () and result.findings == ()
