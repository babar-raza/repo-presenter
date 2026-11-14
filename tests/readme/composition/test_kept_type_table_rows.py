"""P4 (2026-11-14): a kept maintainers' type table in the API Reference prints only the rows the
rendered Core API table does not already print word for word, and the reviewer's "printed" test
agrees.

Rows are verbatim from the sealed Aspose.Cells-FOSS-for-Cpp Lane R candidate (seal revision
9f852d0f, ``inherited_unit:044.table``): 153 of its 157 surface rows were the rendered Core API
rows, printed a second time under "is listed below" (BC-14: "the table rows that follow list
only 157").
"""

from __future__ import annotations

from repo_presenter.readme.composition.placement import is_type_table, rows_not_rendered
from repo_presenter.readme.review.independent_reviewer import _kept_text_printed

TABLE = """| Class | Description |
|---|---|
| `AlignmentValue` | Represents alignment value. |
| `AutoFilter` | Represents auto filter. |
| `CellValue` | Variant-typed scalar cell value wrapper over `monostate`/`int`/`double`/`bool`/`std::string`/`DateTime`. |"""

RENDERED = """### Core API

| Class | Description |
| --- | --- |
| `AlignmentValue` | Represents alignment value. |
| `AutoFilter` | Represents  auto filter. |
| `CellValue` | Public class. |"""


def test_the_shape_is_a_type_table() -> None:
    assert is_type_table(TABLE)
    assert not is_type_table("| Method | Notes |\n|---|---|\n| `Save(fileName)` | saves |")
    assert not is_type_table("| Format | Read |\n|---|---|\n| XLSX | Yes |")


def test_only_rows_the_rendered_table_does_not_print_remain() -> None:
    remainder = rows_not_rendered(TABLE, RENDERED)
    assert remainder.splitlines() == [
        "| Class | Description |",
        "|---|---|",
        "| `CellValue` | Variant-typed scalar cell value wrapper over `monostate`/`int`/`double`/`bool`/`std::string`/`DateTime`. |",
    ]


def test_a_table_the_rendered_table_prints_whole_leaves_nothing_and_one_it_prints_none_of_is_kept() -> None:
    whole = "\n".join(TABLE.splitlines()[:4])
    assert rows_not_rendered(whole, RENDERED) == ""
    assert rows_not_rendered(TABLE, "no table here") == TABLE


def test_the_reviewer_counts_a_table_printed_across_both_tables() -> None:
    readme = RENDERED + "\n\n" + rows_not_rendered(TABLE, RENDERED)
    assert _kept_text_printed(TABLE, "inherited_unit:044.table", readme, "api_reference")
    assert not _kept_text_printed(TABLE, "inherited_unit:044.table", RENDERED, "api_reference")
