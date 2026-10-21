"""Targeted tests for authoring.py's identifier-handling and unit_checks guard."""

from __future__ import annotations

from repo_presenter.readme.composition.authoring import (
    SectionTask,
    allowed_identifiers,
    identifier_tokens,
    unit_checks,
)
from tests.readme.composition.synthetic import make_facts


def test_identifier_tokens_finds_dotted_and_coordinate_shapes() -> None:
    text = "Use `aspose_widget_foss.Widget` or the Maven coordinate org.aspose:aspose-widget-foss."
    tokens = identifier_tokens(text)
    assert "aspose_widget_foss.Widget" in tokens
    assert "org.aspose:aspose-widget-foss" in tokens


def test_allowed_identifiers_admits_every_supported_fact_value() -> None:
    allowed = allowed_identifiers(make_facts(), "Aspose Widget FOSS for Python")
    assert "aspose-widget-foss" in allowed
    assert "aspose_widget_foss.Widget" in allowed
    assert "Widget" in allowed  # the dotted suffix is admitted too


def test_unit_checks_rejects_a_stray_identifier_no_fact_carries() -> None:
    facts = make_facts()
    task = SectionTask(
        section_id="key_capabilities",
        packet={},
        accepted_ids=frozenset({"public_symbol:aspose_widget_foss.widget"}),
        slots=("capability:1",),
        slot_facts={"capability:1": frozenset({"public_symbol:aspose_widget_foss.widget"})},
    )
    output = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Also integrates with TotallyMadeUpFramework.",
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            }
        ]
    }
    errors = unit_checks(output, task, facts, "Aspose Widget FOSS for Python")
    assert any("TotallyMadeUpFramework" in error for error in errors)


def test_unit_checks_accepts_a_unit_that_only_spells_accepted_identifiers() -> None:
    facts = make_facts()
    task = SectionTask(
        section_id="key_capabilities",
        packet={},
        accepted_ids=frozenset({"public_symbol:aspose_widget_foss.widget"}),
        slots=("capability:1",),
        slot_facts={"capability:1": frozenset({"public_symbol:aspose_widget_foss.widget"})},
    )
    output = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Builds an aspose_widget_foss.Widget and renders it.",
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            }
        ]
    }
    assert unit_checks(output, task, facts, "Aspose Widget FOSS for Python") == []


def test_unit_checks_rejects_a_forbidden_markdown_link() -> None:
    facts = make_facts()
    task = SectionTask(
        section_id="opening",
        packet={},
        accepted_ids=frozenset({"package:name"}),
        slots=("opening",),
    )
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": "See [the docs](https://example.com) for more.",
                "fact_ids": ["package:name"],
            }
        ]
    }
    errors = unit_checks(output, task, facts, "Aspose Widget FOSS for Python")
    assert any("Markdown link" in error for error in errors)
