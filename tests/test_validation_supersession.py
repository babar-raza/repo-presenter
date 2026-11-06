"""BC-05 supersession: a superseded unit's substance must appear in the README."""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.readme.validation.content_presence import unstated
from repo_presenter.readme.validation.supersession import exempt, superseded_failures

PLATFORM = (
    "The library targets .NET 8.0 or later and runs on Windows, Linux, macOS, Docker containers, "
    "and serverless functions."
)
README_WITHOUT = "## Dependencies\n\nTargets .NET 8.0. No third-party packages.\n"
README_WITH = README_WITHOUT + "\nIt runs on Windows, Linux, macOS, Docker containers and serverless functions.\n"


def _candidate(text: str, readme: str, unit_id: str = "inherited_unit:016.paragraph", rationale: str = ""):
    fact = SimpleNamespace(id=unit_id, value=text)
    facts = SimpleNamespace(by_kind=lambda kind: [fact] if kind == "inherited_unit" else [])
    dispositions = {
        "dispositions": [
            {"unit_id": unit_id, "disposition": "SUPERSEDE_REDUNDANT", "rationale": rationale}
        ]
    }
    return SimpleNamespace(facts=facts, dispositions=dispositions, readme=readme)


def test_lenient_test_misses_an_anchored_sentence_and_strict_catches_it() -> None:
    assert unstated(PLATFORM, README_WITHOUT) == []  # the 2026-11-06 Email .NET leak
    assert unstated(PLATFORM, README_WITHOUT, strict=True)


def test_superseded_unit_whose_substance_is_missing_fails_reconciling() -> None:
    failures = superseded_failures(_candidate(PLATFORM, README_WITHOUT))
    assert len(failures) == 1
    assert failures[0].stage == "RECONCILING"
    assert failures[0].unit == "inherited_unit:016.paragraph"


def test_superseded_unit_whose_substance_is_carried_passes() -> None:
    assert superseded_failures(_candidate(PLATFORM, README_WITH)) == []


def test_renderer_replaced_markup_is_exempt() -> None:
    assert exempt("inherited_unit:002.badge_row", "[![x](y)](z)", "")
    assert exempt("inherited_unit:008.code_block", "```mermaid\nflowchart TD\n```", "")
    assert exempt("inherited_unit:034.paragraph", "x", "Lead-in of the block that follows: carried together with it, never alone.")
    assert not exempt("inherited_unit:016.paragraph", PLATFORM, "covered by the dependencies section")
    assert superseded_failures(
        _candidate("```mermaid\nflowchart TD\n  a-->b\n```", README_WITHOUT, "inherited_unit:008.code_block")
    ) == []


def test_other_dispositions_are_not_judged_here() -> None:
    candidate = _candidate(PLATFORM, README_WITHOUT)
    candidate.dispositions["dispositions"][0]["disposition"] = "OMIT_UNSUPPORTED"
    assert superseded_failures(candidate) == []


def test_a_positional_paragraph_is_exempt() -> None:
    assert exempt(
        "inherited_unit:029.paragraph",
        "A few more real, runnable patterns beyond the Quick Start example above.",
        "",
    )


def _with_symbols(candidate, *symbols: str):
    unit_facts = candidate.facts.by_kind("inherited_unit")
    public = [SimpleNamespace(id=f"public_symbol:{s.lower()}", value=s) for s in symbols]
    candidate.facts = SimpleNamespace(
        by_kind=lambda kind: unit_facts if kind == "inherited_unit" else public if kind == "public_symbol" else []
    )
    return candidate


API_TABLE = (
    "| Struct | Description |\n|---|---|\n"
    "| `AutoFilter` | Represents auto filter. |\n"
    "| `AlignmentValue` | Struct with 1 method. |\n"
    "| `SheetVisibility` | SheetVisibility enum defines three visibility states: Visible, Hidden, and VeryHidden. |\n"
)
API_README = "## API Reference\n\n| Class | Description |\n| --- | --- |\n| `AutoFilter` | Represents auto filter. |\n"


def test_rows_naming_types_outside_the_public_surface_are_not_owed() -> None:
    """Cells-Rust: AlignmentValue and SheetVisibility live in private core_* modules."""
    candidate = _with_symbols(
        _candidate(API_TABLE, API_README, "inherited_unit:052.table"), "AutoFilter", "AutoFilter.clear"
    )
    assert superseded_failures(candidate) == []


def test_a_public_type_missing_from_the_readme_is_still_owed() -> None:
    candidate = _with_symbols(
        _candidate(API_TABLE, API_README, "inherited_unit:052.table"), "AutoFilter", "SheetVisibility"
    )
    failures = superseded_failures(candidate)
    assert len(failures) == 1 and "SheetVisibility" in failures[0].detail


def test_without_an_extracted_surface_every_row_is_owed() -> None:
    assert superseded_failures(_candidate(API_TABLE, API_README, "inherited_unit:052.table"))
