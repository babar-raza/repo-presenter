"""BL-803: the author of an undocumented-looking type's sentence is shown the doc comment the reviewer is shown.

``authoring.undocumented_types`` lists every type with no first-sentence ``docstring``, though the extractors keep
the whole doc comment of such a type as ``docstring_full`` (a type re-exported from a private module, every
TypeScript type), and ``review.evidence._record`` shows the reviewer that text as the type's ``docstring``. The
author's packet carried neither, so the sentence was written from the name ("EncodingError represents errors that
occur during barcode encoding.", doc comment "Raised when encoding fails.") and the audit's judge, who reads the doc
comment, faulted it: BarCode Python 13 and HTML Python 13 of the round-7 false flags (seed run 44988613948) are such
rows. A type with no doc comment is unchanged: its packet record has no ``docstring``.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import TYPE_DOC_CHARS, _type_batches, type_doc_comment
from repo_presenter.readme.review.evidence import DOC_CHARS
from tests.readme.composition.synthetic import make_entry, make_facts


def _class(name: str, detail: str = "line 1; class; public by declaration", **attributes: str) -> Fact:
    return Fact(
        f"public_symbol:{name.lower()}", "public_symbol", name, (Evidence("pkg/m.py", detail),),
        attributes={"symbol_kind": "class", **attributes},
    )


def _facts(*extra: Fact) -> FactsDocument:
    base = make_facts()
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


DOC = "Raised when encoding fails."


def test_the_author_is_shown_the_doc_comment_the_reviewer_is_shown() -> None:
    assert TYPE_DOC_CHARS == DOC_CHARS
    facts = _facts(_class("pkg.exceptions.EncodingError", docstring_full=DOC), _class("pkg.Plain"))
    (task,) = _type_batches(make_entry(), facts, [])
    records = {record["id"]: record for record in task.packet["accepted_facts"]}
    assert records["public_symbol:pkg.exceptions.encodingerror"]["docstring"] == DOC
    assert "docstring" not in records["public_symbol:pkg.plain"]


def test_a_re_exported_alias_reads_the_doc_comment_of_the_class_it_names() -> None:
    alias = _class("pkg.PngRenderer", "line 29; class; public by reexport; re-export of pkg.renderers.PngRenderer")
    target = _class("pkg.renderers.PngRenderer", docstring_full="Render a barcode into PNG output.")
    facts = _facts(alias, target)
    assert type_doc_comment(alias, facts) == "Render a barcode into PNG output."
    assert type_doc_comment(alias) == ""  # without the document an alias knows nothing


def test_a_long_doc_comment_is_cut_where_the_reviewers_is() -> None:
    long = "word " * 100
    cut = type_doc_comment(_class("pkg.Long", docstring_full=long))
    assert len(cut) == TYPE_DOC_CHARS + 4 and cut.endswith(" ...")


def test_negative_control_a_first_sentence_docstring_or_no_doc_comment_adds_nothing() -> None:
    assert type_doc_comment(_class("pkg.A", docstring="Does a thing.", docstring_full="Does a thing. More.")) == ""
    assert type_doc_comment(_class("pkg.B")) == ""
