"""BL-897: a changed API row that is exactly the shared describer's fact-true text is not judged.

Evidence: hosted Lane L PDF Cpp run 45337643264 (2026-11-24) ended 'REJECT with 8 blocking finding(s)':
every one is a row the ``type_description`` correction wrote ("Class that inherits from MarkupAnnotation
and declares the methods Accept and Icon."), faulted for an inheritance or member list the review packet
(member names only, never bases) could not show, a different 8 of 118 each round.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.llm_review import edit_scope
from repo_presenter.readme.review.scope import derived_type_rows


def _fact(fact_id: str, value: str, **attributes: Any) -> Fact:
    return Fact(
        fact_id, "public_symbol", value, (Evidence("include/a.hpp", detail="line 1;"),), "SUPPORTED",
        attributes=attributes,
    )  # type: ignore[arg-type]


FACTS = FactsDocument(
    "org/pdf",
    "a" * 40,
    (
        _fact("public_symbol:n.sound", "N.Sound", symbol_kind="class", bases="MarkupAnnotation"),
        _fact("public_symbol:n.sound.accept", "N.Sound.Accept", symbol_kind="method", member_kind="method"),
        _fact("public_symbol:n.sound.icon", "N.Sound.Icon", symbol_kind="method", member_kind="method"),
        _fact("public_symbol:n.other", "N.Other", symbol_kind="class"),
        _fact("public_symbol:n.other.zap", "N.Other.Zap", symbol_kind="method", member_kind="method"),
    ),
)
LIVE = (
    "# W\n\nIntro.\n\n## API Reference\n\n| Class | Description |\n| --- | --- |\n"
    "| `Sound` | Class with 3 methods. |\n| `Other` | Class with 2 methods. |\n"
)
TRUE_ROW = "Class that inherits from MarkupAnnotation and declares the methods Accept and Icon."
CANDIDATE = LIVE.replace("Class with 3 methods.", TRUE_ROW)
HOLDOUTS = {"lane": "L"}


def test_a_row_equal_to_the_describers_text_is_derived() -> None:
    assert derived_type_rows(CANDIDATE, FACTS, frozenset({9})) == frozenset({9})


def test_a_row_with_other_wording_stays_reviewed() -> None:
    other = LIVE.replace("Class with 3 methods.", "Class that inherits from Foo and declares the method Accept.")
    assert derived_type_rows(other, FACTS, frozenset({9})) == frozenset()
    assert derived_type_rows(LIVE.replace("Class with 3 methods.", TRUE_ROW + " It is fast."), FACTS, frozenset({9})) == frozenset()


def test_an_unchanged_row_is_never_returned() -> None:
    assert derived_type_rows(CANDIDATE, FACTS, frozenset({10})) == frozenset()


def test_edit_scope_drops_derived_rows_only_when_facts_are_given() -> None:
    kwargs = dict(rendered=False, validation=HOLDOUTS, candidate_readme=CANDIDATE, original_readme=LIVE)
    assert edit_scope(**kwargs) == frozenset({9})  # callers without facts keep their scope
    assert edit_scope(facts=FACTS, **kwargs) == frozenset()


def test_a_mixed_edit_keeps_the_non_derived_line_in_scope() -> None:
    candidate = CANDIDATE.replace("Intro.", "Intro changed.")
    got = edit_scope(rendered=False, validation=HOLDOUTS, candidate_readme=candidate, original_readme=LIVE, facts=FACTS)
    assert got == frozenset({3})
