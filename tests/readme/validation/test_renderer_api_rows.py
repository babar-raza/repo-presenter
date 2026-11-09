"""BC-07 judges only the tables the renderer itself emits for the Core API section.

The maintainers' member/class tables the published README prints (R2: the floor) are preserved in
the same section; counting their first cells against the verified public types made BC-07 fail
("lists 139 rows for 31 verified public types").
"""

from __future__ import annotations

from repo_presenter.readme.validation.structure import renderer_api_rows

SECTION = """## API Reference

### Core API

| Class | Description |
|---|---|
| `Workbook` | The workbook. |
| `Cell` | A cell. |

#### Enumerations

| Enumeration | Description |
|---|---|
| `Mode` | A mode. |

<details>
<summary>Detailed Member Reference</summary>

| Method | Description |
|---|---|
| `Detect` | Detects. |
| `GetFormatByExtension` | Maps. |
| `Save` | Saves. |

</details>
"""


def test_only_the_tables_under_the_renderers_headings_are_counted() -> None:
    assert renderer_api_rows(SECTION) == ["Workbook", "Cell", "Mode"]


def test_a_preserved_member_table_adds_no_rows() -> None:
    without = SECTION.split("<details>")[0]
    assert len(renderer_api_rows(SECTION)) == len(renderer_api_rows(without)) == 3


def test_a_section_without_the_renderers_headings_has_no_rows() -> None:
    assert renderer_api_rows("| `A` | x |\n| `B` | y |\n") == []
