"""A kept unit's printable form carries the facts' type count, as the rendered README does.

Aspose.Cells FOSS for C++ (hosted, 2026-11-11): the maintainers' ``041.paragraph`` says "197 public
types"; the renderer prints the facts' 195 (``renderer.correct_stated_type_counts``, over the whole
README). BC-05 compared the uncorrected 197 text with the rendered section and said "placed in
scope_limitations but the candidate does not render it there" for a paragraph that WAS printed, one
number apart, and the restore that had cleared the other losses was discarded for it.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.surface_claims import kept_unit_form

UNIT = "inherited_unit:041.paragraph"
STALE = (
    "The library's public types live in the `Aspose::Cells_FOSS` namespace, with `Workbook` as the\n"
    "root entry point. The full public surface — 197 public types — is listed below, grouped\n"
    "exactly as `reference.aspose.org` organizes them."
)


def _facts(types: int) -> FactsDocument:
    symbols = tuple(
        Fact(
            f"public_symbol:t{i}",
            "public_symbol",
            f"Aspose::Cells_FOSS::T{i}",
            (Evidence("h", f"line {i}; class; declared in a public header"),),
            attributes={"symbol_kind": "class"},
        )
        for i in range(types)
    )
    return FactsDocument("org/x", "d" * 40, symbols)


def test_a_stale_stated_count_is_printed_as_the_facts_number() -> None:
    printed = kept_unit_form(UNIT, STALE, _facts(195))
    assert "195 public types" in printed and "197" not in printed
    assert printed.replace("195", "197") == STALE  # only the digits moved


def test_a_matching_count_and_a_unit_without_one_are_left_exactly_alone() -> None:
    assert kept_unit_form(UNIT, STALE, _facts(197)) == STALE
    plain = "Workbook is the root entry point."
    assert kept_unit_form(UNIT, plain, _facts(195)) == plain


def test_a_number_inside_a_fenced_sample_is_never_edited() -> None:
    fenced = "```cpp\n// 197 public types\n```"
    assert kept_unit_form("inherited_unit:042.code_block", fenced, _facts(195)) == fenced
