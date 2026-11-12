"""A stated public-type count the facts refute outright is rewritten to the computed count.

The sentences are verbatim from the live READMEs of aspose-html-foss/Aspose.HTML-FOSS-for-Python
(243 stated, 303 recorded: 302 classes + 1 enum) and aspose-words-foss/Aspose.Words-FOSS-for-Python
(146 stated, 198 recorded: 175 classes + 23 enums) - the two Lane L seals whose re-certification
fails L-03 on exactly these lines (2026-11-09).
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.stale_type_count import stale_type_count

HTML_INTRO = (
    "The library exposes 243 public types in total, listed below by module, with curated "
    "highlights following.\n"
)
HTML_BULLET = (
    "- **[Full API reference](https://reference.aspose.org/html/python/)** - the complete, "
    "browsable reference for all 243 public types.\n"
)
WORDS_INTRO = (
    "The library ships 146 public types across the DOC/DOCX/RTF/Markdown/Text readers, the "
    "DOCX/Markdown/PDF writers, and the shared Light Document Model, summarized in the "
    "module-grouped table below.\n"
)


def _symbols(make_fact: Any, classes: int, enums: int) -> list[Any]:
    facts = []
    for index in range(classes):
        facts.append(
            make_fact(
                f"public_symbol:pkg.c{index}", f"C{index}",
                evidence=((f"src/c{index}.py", f"line 1; class; C{index}"),),
                attributes={"symbol_kind": "class"},
            )
        )
    for index in range(enums):
        facts.append(
            make_fact(
                f"public_symbol:pkg.e{index}", f"E{index}",
                evidence=((f"src/e{index}.py", f"line 1; enum; E{index}"),),
                attributes={"symbol_kind": "enum"},
            )
        )
    return facts


def test_the_real_html_python_count_lines_are_rewritten_to_the_computed_303(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "# Aspose.HTML FOSS for Python\n\n" + HTML_INTRO + "\n" + HTML_BULLET
    ctx = make_context(readme, make_facts(*_symbols(make_fact, 302, 1)))
    edits = stale_type_count(ctx).edits
    assert [(e.original, e.replacement) for e in edits] == [("243", "303"), ("243", "303")]
    for edit in edits:
        assert readme[edit.start : edit.end] == "243"
        assert edit.fact_ids and edit.kind == "FALSE_CLAIM_FIX"


def test_the_real_words_python_count_is_rewritten_to_198(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(WORDS_INTRO, make_facts(*_symbols(make_fact, 175, 23)))
    (edit,) = stale_type_count(ctx).edits
    assert (edit.original, edit.replacement) == ("146", "198")


def test_a_correct_count_is_left_alone(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    ctx = make_context(
        "The library exposes 303 public types in total.\n", make_facts(*_symbols(make_fact, 302, 1))
    )
    assert stale_type_count(ctx).edits == ()


def test_a_count_above_the_facts_is_never_rewritten(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """The maintainers may count kinds the extractor does not record (983 = 969 class/enum facts
    + 14 public delegates in Aspose.PDF FOSS for .NET): deleting that would lose a true statement."""
    ctx = make_context(
        "The library exposes 983 public types in total.\n", make_facts(*_symbols(make_fact, 969, 0))
    )
    assert stale_type_count(ctx).edits == ()


def test_a_count_that_is_not_about_the_public_surface_is_left_alone(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(
        "The test suite defines 12 types and 3 classes of fixture.\n",
        make_facts(*_symbols(make_fact, 50, 0)),
    )
    assert stale_type_count(ctx).edits == ()


def test_no_type_facts_means_no_edit(make_context: Any, make_facts: Any) -> None:
    ctx = make_context(HTML_INTRO, make_facts())
    assert stale_type_count(ctx).edits == ()


def test_each_noun_gets_its_own_count_and_the_thousands_style_is_kept(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(
        "It has 1,200 public classes and 4 public types elsewhere.\n",
        make_facts(*_symbols(make_fact, 1500, 3)),
    )
    edits = stale_type_count(ctx).edits
    # "public classes" -> the class count (thousands style kept); "public types" -> the type count
    assert [(e.original, e.replacement) for e in edits] == [("1,200", "1,500"), ("4", "1503")]


def test_a_line_inside_a_fence_is_never_touched(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(
        "```\nThe library exposes 243 public types in total.\n```\n",
        make_facts(*_symbols(make_fact, 302, 1)),
    )
    assert stale_type_count(ctx).edits == ()


def test_a_count_on_a_line_with_code_spans_is_edited_at_its_real_position(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """The real Aspose.HTML FOSS for Python line 213 is one long line: the count sentence comes
    first and the same line later names `HTMLDocument` in code spans."""
    line = (
        "The library exposes 243 public types in total, listed below by module. The primary entry "
        "point is `HTMLDocument`, which parses HTML into a `Document` tree.\n"
    )
    ctx = make_context(line, make_facts(*_symbols(make_fact, 302, 1)))
    (edit,) = stale_type_count(ctx).edits
    assert line[edit.start : edit.end] == "243" and edit.replacement == "303"
    # and with a code span BEFORE the number the offsets must still land on the digits
    before = "`Foo` has 243 public types in total.\n"
    (edit,) = stale_type_count(make_context(before, make_facts(*_symbols(make_fact, 302, 1)))).edits
    assert before[edit.start : edit.end] == "243"


def test_a_sentence_hard_wrapped_around_the_count_is_edited_on_the_digits_line(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """Verbatim from the sealed Aspose.Words FOSS for Python README (lines 328-330): the number
    ends one line, its noun starts the next."""
    readme = (
        "the target format is otherwise inferred from the output file's extension. The library ships 146\n"
        "public types across the DOC/DOCX/RTF/Markdown/Text readers, the DOCX/Markdown/PDF writers, and\n"
        "the shared Light Document Model, summarized in the module-grouped table below.\n"
    )
    ctx = make_context(readme, make_facts(*_symbols(make_fact, 175, 23)))
    (edit,) = stale_type_count(ctx).edits
    assert readme[edit.start : edit.end] == "146" and edit.replacement == "198"
    assert edit.rationale.startswith("line 1 ")
