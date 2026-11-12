"""A code span spelled as a call without arguments is stated by the bare identifier (Cells Go)."""

from repo_presenter.readme.validation.content_presence import unstated


def test_call_spelling_is_stated_by_the_bare_identifier() -> None:
    unit = "Use `Worksheet.Cells()` to reach a cell."
    assert unstated(unit, "The API has Worksheet.Cells for cell access.") == []


def test_call_with_arguments_still_needs_its_arguments() -> None:
    unit = "Use `Worksheet.Cells(1, 2)` to reach a cell."
    assert unstated(unit, "The API has Worksheet.Cells for cell access.") != []


def test_missing_identifier_is_still_reported() -> None:
    unit = "Use `Worksheet.Cells()` to reach a cell."
    assert unstated(unit, "Nothing relevant here at all, only prose.") != []
