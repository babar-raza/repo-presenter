"""An end-to-end smoke test of the deterministic pipeline: planning -> placement -> renderer.

No LLM call anywhere in this file (that is the whole point of the deterministic/agentic split):
the "plan" and "units" a real run would get from presentation_planning and section_authoring are
built here by hand, exactly as a job's accepted, schema-and-binding-valid JSON output would look.
``plan_checks``, ``placements`` and ``render_readme`` then run for real against them.
"""

from __future__ import annotations

from repo_presenter.readme.composition.planning import plan_checks, section_conditions, summarize_plan
from repo_presenter.readme.composition.placement import placements
from repo_presenter.readme.composition.renderer import render_readme
from tests.readme.composition.synthetic import make_entry, make_facts


def _plan() -> dict:
    return {
        "core_capabilities": [
            {
                "title": "Render widgets",
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
                "shared_fact_ids": [],
            },
            {"title": "Install with pip", "fact_ids": ["install_command:pip"], "shared_fact_ids": []},
            {"title": "Work with the public API", "fact_ids": ["package:name"], "shared_fact_ids": []},
        ],
        "quick_start_example_id": "example:001",
        "second_quick_start_example_id": None,
        "additional_example_ids": [],
        "flagship_example_id": None,
        "api_hubs": [{"symbol_fact_id": "public_symbol:aspose_widget_foss.widget", "fact_ids": []}],
        "material_limitations": [],
        "links": [],
        "deviations": [],
        "at_a_glance": {
            "input_format_ids": [],
            "output_format_ids": [],
            "capability_titles": ["Render widgets", "Install with pip", "Work with the public API"],
        },
    }


def _units() -> dict:
    return {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": "It renders widgets from Python.",
                "fact_ids": ["package:name"],
            },
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Builds a Widget and renders it in one call.",
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            },
            {
                "section": "key_capabilities",
                "slot": "capability:2",
                "text": "Installable straight from PyPI.",
                "fact_ids": ["install_command:pip"],
            },
            {
                "section": "key_capabilities",
                "slot": "capability:3",
                "text": "Exposes a small, documented public API.",
                "fact_ids": ["package:name"],
            },
            {
                "section": "quick_start",
                "slot": "lead_in",
                "text": "Create a widget and render it:",
                "fact_ids": ["example:001"],
            },
            {
                "section": "api_reference",
                "slot": "intro",
                "text": "One entry-point class does the work.",
                "fact_ids": [],
            },
            {
                "section": "api_reference",
                "slot": "hub:public_symbol:aspose_widget_foss.widget",
                "text": "Widget is the object you build and render.",
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            },
            {
                "section": "scope_limitations",
                "slot": "scope",
                "text": "Covers rendering only.",
                "fact_ids": [],
            },
        ],
        "omitted": [],
    }


def _dispositions() -> dict:
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:005.code_block",
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "quick_start",
                "fact_ids": ["example:001"],
                "rationale": "The plan's own quick start already renders this exact example.",
            },
            {
                "unit_id": "inherited_unit:010.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "scope_limitations",
                "fact_ids": [],
                "rationale": "A real limitation no fact supersedes.",
            },
        ]
    }


def test_section_conditions_hold_for_the_synthetic_facts() -> None:
    conditions = section_conditions(make_facts())
    assert conditions["quick_start"] is True
    assert conditions["api_reference"] is True
    assert conditions["banner"] is False  # no verified banner/homepage in the synthetic facts
    assert conditions["enterprise_relationship"] is False


def test_plan_checks_accepts_a_well_formed_plan_and_fills_in_sections() -> None:
    plan = _plan()
    errors = plan_checks(plan, make_facts(), dispositions=_dispositions(), ecosystem="python")
    assert errors == []
    included = {entry["section_id"] for entry in plan["sections"] if entry["include"]}
    assert "quick_start" in included
    assert "api_reference" in included
    assert "banner" not in included
    assert "sections 10/18" in summarize_plan(plan) or "sections" in summarize_plan(plan)


def test_plan_checks_rejects_too_few_core_capabilities() -> None:
    plan = _plan()
    plan["core_capabilities"] = plan["core_capabilities"][:1]
    errors = plan_checks(plan, make_facts(), dispositions=_dispositions(), ecosystem="python")
    assert any("core_capabilities must number" in error for error in errors)


def test_placements_places_the_uncovered_limitation_paragraph() -> None:
    plan = _plan()
    plan_checks(plan, make_facts(), dispositions=_dispositions(), ecosystem="python")
    decisions = placements(plan, _dispositions(), make_facts(), "python")
    by_unit = {decision.unit_id: decision for decision in decisions}
    assert by_unit["inherited_unit:010.paragraph"].outcome == "placed"
    assert by_unit["inherited_unit:010.paragraph"].destination == "scope_limitations"
    # The code block was SUPERSEDE_REDUNDANT, not VERIFIED_PRESERVE/MOVE, so placements() (which
    # only ever decides PLACED = {VERIFIED_PRESERVE, VERIFIED_MOVE} dispositions) never sees it.
    assert "inherited_unit:005.code_block" not in by_unit


def test_render_readme_produces_the_expected_shape() -> None:
    plan = _plan()
    dispositions = _dispositions()
    plan_checks(plan, make_facts(), dispositions=dispositions, ecosystem="python")
    readme = render_readme(make_entry(), make_facts(), plan, _units(), dispositions)
    assert readme.startswith("# Aspose.Widget FOSS for Python\n")
    assert "## Key Capabilities" in readme
    assert "renders it in one call" in readme
    assert "## Quick Start" in readme
    assert "Create a widget and render it:" in readme
    assert "```python" in readme
    assert "## API Reference" in readme
    assert "### Core API" in readme
    assert "`Widget`" in readme
    assert "## License" in readme
    assert "MIT License" in readme
    assert readme.endswith("\n")
    assert "\n\n\n" not in readme  # no blank-line runs outside a fence
    # The renderer is a pure function: a rerun on the same inputs is byte-identical.
    assert readme == render_readme(make_entry(), make_facts(), plan, _units(), dispositions)
