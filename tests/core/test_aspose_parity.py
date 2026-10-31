"""Parity of our README with the aspose.org candidate (core/aspose_parity.py): numbers, not text.

The tests use synthetic Markdown only; the reference text is never stored or asserted on.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.aspose_parity import compare, measure, reference_path, render

OURS = """# Aspose.Widget FOSS for .NET

[![NuGet](https://img.shields.io/x.svg)](https://www.nuget.org/packages/Aspose.Widget/)

## Navigation

## Key Capabilities

## Quick Start

```csharp
var w = new Widget();
```

## API Reference

<details>
<summary>Types</summary>

| a | b |
</details>

[docs](https://docs.aspose.org/widget/) and [product](https://products.aspose.org/widget/net/).
"""

REFERENCE = """# Aspose.Widget FOSS for .NET

## Navigation

## At a Glance

```mermaid
graph TD
```

## Key Capabilities

## Quick Start

```csharp
var w = new Widget();
```

```csharp
var x = 1;
```

## Additional Examples

## API Reference
"""


def test_measure_counts_fences_headings_links_and_ignores_headings_inside_fences() -> None:
    text = "# T\n\n```md\n## not a heading\n```\n\n## Real\n[a](https://aspose.org/x) [b](https://e.com)\n"
    shape = measure(text)
    assert shape.code_fences == 1
    assert [name for _, name in shape.headings] == ["t", "real"]
    assert shape.links == 2 and shape.aspose_links == 1


def test_mermaid_and_details_are_counted() -> None:
    shape = measure(REFERENCE + "\n<details>\n</details>\n")
    assert shape.mermaid_diagrams == 1 and shape.code_fences == 3
    assert shape.details_blocks == 1


def test_compare_names_missing_and_extra_headings_and_the_h2_ones_separately() -> None:
    parity = compare(OURS, REFERENCE)
    assert parity.missing_headings == ("at a glance", "additional examples")
    assert parity.missing_h2 == ("at a glance", "additional examples")
    assert parity.extra_headings == ()
    assert parity.shared_order_agrees


def test_a_reordered_shared_heading_is_reported() -> None:
    swapped = REFERENCE.replace("## Key Capabilities\n\n## Quick Start", "## Quick Start\n\n## Key Capabilities")
    assert not compare(swapped, REFERENCE).shared_order_agrees


def test_an_identical_readme_is_full_parity() -> None:
    parity = compare(REFERENCE, REFERENCE)
    assert parity.missing_headings == () and parity.extra_headings == ()
    assert parity.line_ratio == 1.0 and parity.shared_order_agrees


def test_the_reference_path_is_the_canonical_store_layout(tmp_path: Path) -> None:
    path = reference_path(tmp_path, "imaging", "net")
    assert path == tmp_path / "reports" / "repo-presenter-regen-full" / "imaging" / "net" / "readme.md"


def test_render_prints_numbers_and_heading_names_only() -> None:
    out = render("x/y (Lane R)", compare(OURS, REFERENCE))
    assert "missing H2 sections" in out and "at a glance" in out
    assert "var w = new Widget()" not in out
