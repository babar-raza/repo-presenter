"""Two authored units carrying the same summary paragraph must not print it twice.

Reproduces hosted Aspose.BarCode-FOSS-for-Python Lane R run 43413875680: the opening and another
section's authored unit carried the same product summary verbatim, the reviewer's
``duplicate_paragraph`` rule blocked the candidate, and the finding (quote rendered with identifiers
in code spans) located no unit, so it routed to no section and the run failed.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.review.defect_bridge import _locate_section
from repo_presenter.readme.review.independent_reviewer import duplicate_paragraph_rule
from tests.readme.composition.synthetic import make_entry

SUMMARY = (
    "Aspose.Widget FOSS for Python renders widgets to PNG and SVG images via the Widget class, "
    "and accepts options to control scale, DPI, module width, and text visibility for output."
)


def _facts() -> FactsDocument:
    entry = make_entry()
    facts = (
        Fact("identity:repository", "identity", entry.repository, (Evidence("data/registry.json"),)),
        Fact("identity:ecosystem", "identity", "python", (Evidence("data/registry.json"),)),
        Fact("package:name", "package", "aspose-widget-foss", (Evidence("setup.py"),)),
        Fact(
            "public_symbol:aspose_widget_foss.widget",
            "public_symbol",
            "aspose_widget_foss.Widget",
            (Evidence("aspose_widget_foss/widget.py", "; class; "),),
            attributes={"symbol_kind": "class", "docstring": "A widget you can render."},
        ),
    )
    return FactsDocument(entry.repository, "f" * 40, facts)


def _plan() -> dict:
    return {
        "sections": [
            {"section_id": "opening", "include": True},
            {"section_id": "scope_limitations", "include": True},
            {"section_id": "development_testing", "include": True},
        ]
    }


def _units(second: str) -> dict:
    return {
        "units": [
            {"section": "opening", "slot": "opening", "text": SUMMARY, "fact_ids": []},
            {"section": "scope_limitations", "slot": "scope", "text": second, "fact_ids": []},
            {
                "section": "development_testing",
                "slot": "summary",
                "text": "Run the test suite with pytest from the repository root.",
                "fact_ids": [],
            },
        ]
    }


def test_a_repeated_authored_summary_prints_once() -> None:
    readme = render_readme(make_entry(), _facts(), _plan(), _units(SUMMARY), {"units": []})
    assert duplicate_paragraph_rule(readme) == []
    assert readme.count("renders widgets to PNG and SVG") == 1
    assert "Run the test suite with pytest" in readme


def test_only_the_repeated_paragraph_of_the_later_unit_is_left_out() -> None:
    second = "The library has some real limits.\n\n" + SUMMARY.replace("Widget class", "`Widget` class")
    readme = render_readme(make_entry(), _facts(), _plan(), _units(second), {"units": []})
    assert duplicate_paragraph_rule(readme) == []
    assert "The library has some real limits." in readme
    assert readme.count("renders widgets to PNG and SVG") == 1


def test_distinct_units_render_unchanged() -> None:
    other = "Only PNG output is fully supported; SVG output omits text and is a preview feature."
    readme = render_readme(make_entry(), _facts(), _plan(), _units(other), {"units": []})
    assert other.split(";")[0] in readme and SUMMARY.split(" via")[0] in readme


def test_a_rendered_quote_locates_the_unit_that_printed_it() -> None:
    units = [{"section": "scope_limitations", "slot": "scope", "text": SUMMARY}]
    quote = SUMMARY.replace("Widget class", "`Widget` class")
    assert _locate_section(quote, units, {}) == "scope_limitations"
