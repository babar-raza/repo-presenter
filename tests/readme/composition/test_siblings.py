"""Targeted tests for the composition package's smaller, self-contained siblings."""

from __future__ import annotations

from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL, section_ids
from repo_presenter.readme.composition.components.terminology import canonical_forms, to_title_case
from repo_presenter.readme.composition.link_budget import (
    ContentMeasurement,
    resolve_link_budget,
    slot_violations,
)
from repo_presenter.readme.composition.list_coverage import list_items, missing_items
from repo_presenter.readme.composition.coverage import uncovered, Destinations
from repo_presenter.readme.composition.source_topics import path_topic


def test_shell_has_eighteen_sections_in_a_stable_order() -> None:
    assert len(SEMANTIC_SHELL) == 18
    assert section_ids()[0] == "identity"
    assert section_ids()[-1] == "license"


def test_canonical_forms_raises_a_discovered_two_letter_extension() -> None:
    forms = canonical_forms([".ps"])
    assert forms["ps"] == "PS"
    assert forms["pdf"] == "PDF"


def test_to_title_case_leaves_an_identifier_like_token_alone() -> None:
    assert to_title_case("convert a pdf with aspose_widget_foss.Widget") == (
        "Convert a Pdf with aspose_widget_foss.Widget"
    )


def test_link_budget_automatic_total_grows_with_content_size() -> None:
    small = resolve_link_budget(ContentMeasurement(100, 0))
    large = resolve_link_budget(ContentMeasurement(5000, 0))
    assert small.max_total < large.max_total


def test_link_budget_automatic_tiers_have_these_exact_boundaries() -> None:
    def total(units: int, cap: int = 4) -> int:
        return resolve_link_budget(ContentMeasurement(units, 0), None, cap).max_total

    assert [total(u) for u in (0, 300, 301, 500, 501, 1153, 2000, 5000)] == [2, 2, 3, 3, 4, 4, 4, 4]
    # The cap still clamps, and tiers above it are unchanged for a caller that raises the cap.
    assert total(1153, cap=3) == 3
    assert [total(u, cap=6) for u in (2000, 2001, 3000, 3001)] == [4, 5, 5, 6]


def test_the_words_dotnet_measurement_gets_the_portfolios_four_links() -> None:
    """1,153 visible words and no verified example: hosted run 41177743986 was held to a ceiling of 3."""
    assert resolve_link_budget(ContentMeasurement(1153, 0)).max_total == 4


def test_slot_violations_catches_an_over_budget_total() -> None:
    budget = resolve_link_budget(ContentMeasurement(100, 0))
    hrefs = [f"https://docs.aspose.org/widget/{i}/" for i in range(budget.max_total + 2)]
    problems = slot_violations(budget, hrefs)
    assert any("exceed the ceiling" in problem for problem in problems)


def test_list_items_splits_bullets_with_wrapped_lines() -> None:
    text = "- First item\n  continues here\n- Second item\n"
    assert list_items(text) == ["First item continues here", "Second item"]


def test_missing_items_finds_an_item_the_destination_never_states() -> None:
    unit = "- Supports PNG output\n- Supports JPEG output\n"
    destination = "The library writes PNG files."
    missing = missing_items(unit, destination)
    assert any("JPEG" in item for item in missing)
    assert not any("PNG" in item for item in missing)


def test_uncovered_returns_empty_when_the_destination_states_everything() -> None:
    shown = Destinations.of({"scope_limitations": "Only PNG output is supported today."})
    remainder = uncovered(
        "inherited_unit:010.paragraph",
        "Only PNG output is supported today.",
        shown,
        "scope_limitations",
    )
    assert remainder == ""


def test_path_topic_reads_install_from_a_heading_path() -> None:
    assert path_topic("Widget > Installation > Requirements") == "install"
    assert path_topic("Widget > License") == "furniture"
    assert path_topic(None) is None
