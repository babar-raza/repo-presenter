"""An API-member listing is API Reference content: kept in the collapsed API Reference and printed
there, never superseded, never kept in a visible section.

Measured (2026-11-06, Cells-Rust Lane R, hosted run 42213705268): the maintainer's member lists
(``put_value_*``, ``get_font_mut()``, ``try_repair_*``) were superseded (BC-05 failed: the README
did not state every signature) or kept in visible sections (BC-07 failed: 314 visible lines of 964
exceed the budget 300); kept in the API Reference they were dropped as overlap (the reviewer's
disposition_coverage failed). The three gates are all right; the destination and the placement
were not.
"""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.placement import api_listing_units, placements
from repo_presenter.readme.composition.planning import plan_checks
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.reconciliation.dispositions import (
    API_LISTING_RATIONALE,
    normalize,
)
from repo_presenter.readme.validation.structure import line_counts
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan, _units

LISTING = "inherited_unit:020.list"
CAPABILITY = "inherited_unit:021.list"
LISTING_TEXT = (
    "- `Widget`\n"
    "  - `render(scale) -> Image`, `set_color(value)`\n"
    "  - `save_png(path)`"
)


def _facts(*, heading: str = "Aspose Widget > API Reference > Rendering") -> FactsDocument:
    base = make_facts()
    extra = (
        Fact(
            "public_symbol:aspose_widget_foss.widget.render",
            "public_symbol",
            "aspose_widget_foss.Widget.render",
            (Evidence("aspose_widget_foss/widget.py", "; method; "),),
            attributes={"symbol_kind": "method", "docstring": "Renders the widget."},
        ),
        Fact(
            LISTING,
            "inherited_unit",
            LISTING_TEXT,
            (Evidence("README.md", f"section '{heading}'"),),
            attributes={"section": heading},
        ),
        Fact(
            CAPABILITY,
            "inherited_unit",
            "- `Widget` renders crisp output at any scale.",
            (Evidence("README.md", "section 'Aspose Widget > Features'"),),
            attributes={"section": "Aspose Widget > Features"},
        ),
    )
    return replace(base, facts=(*base.facts, *extra))


def _with(disposition: str, destination: str | None) -> dict:
    output = copy.deepcopy(_dispositions())
    output["dispositions"].append(
        {
            "unit_id": LISTING,
            "disposition": disposition,
            "destination_section": destination,
            "fact_ids": ["public_symbol:aspose_widget_foss.widget.render"],
            "rationale": "The member list.",
        }
    )
    return output


def test_a_member_listing_is_recognised_by_heading_or_by_content() -> None:
    assert LISTING in api_listing_units(_facts())
    # Outside an API heading it still lists members beyond the names it leads with.
    assert LISTING in api_listing_units(_facts(heading="Aspose Widget > Features > Rendering"))
    # A capability bullet that merely opens with a type name is not a member listing.
    assert CAPABILITY not in api_listing_units(_facts())


@pytest.mark.parametrize(
    ("disposition", "destination"),
    [
        ("SUPERSEDE_REDUNDANT", "scope_limitations"),
        ("SUPERSEDE_REDUNDANT", "api_reference"),
        ("VERIFIED_PRESERVE", "documentation_resources"),
        ("VERIFIED_MOVE", "key_capabilities"),
        ("PRESERVE_ATTRIBUTED", "scope_limitations"),
    ],
)
def test_normalize_keeps_a_member_listing_in_the_api_reference(disposition: str, destination: str) -> None:
    output = _with(disposition, destination)
    normalize(output, _facts())
    entry = next(e for e in output["dispositions"] if e["unit_id"] == LISTING)
    assert entry["destination_section"] == "api_reference"
    assert entry["disposition"] == (
        "VERIFIED_PRESERVE" if disposition == "SUPERSEDE_REDUNDANT" else disposition
    )
    assert entry["rationale"].startswith(API_LISTING_RATIONALE)


def test_a_kept_member_listing_prints_inside_the_collapsed_api_reference() -> None:
    facts = _facts()
    output = _with("VERIFIED_PRESERVE", "api_reference")
    plan = _plan()
    plan_checks(plan, facts, dispositions=output, ecosystem="python")
    decision = next(d for d in placements(plan, output, facts, "python") if d.unit_id == LISTING)
    # It cites a member the Core API surface covers, yet it prints as written.
    assert decision.outcome == "placed"
    readme = render_readme(make_entry(), facts, plan, _units(), output)
    api = readme[readme.index("## API Reference") :]
    api = api[: api.index("\n## ", 1)] if "\n## " in api[1:] else api
    assert "`save_png(path)`" in api
    assert api.index("`save_png(path)`") < api.index("</details>")
    without = _with("VERIFIED_PRESERVE", "api_reference")
    without["dispositions"].pop()
    baseline = render_readme(make_entry(), facts, plan, _units(), without)
    # Collapsed: the listing adds no visible line.
    assert line_counts(readme)[0] == line_counts(baseline)[0]
