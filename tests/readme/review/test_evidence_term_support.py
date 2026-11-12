"""The review packet carries the facts that bear on a claim's distinctive terms (Words-FOSS-for-
Python's Lane R candidate, 2026-11-10: the reviewer filed 11 unsupported_claim findings although the
LoadFormat/SaveFormat members that prove 'reads DOCX, DOC, RTF, Markdown, text' and the source fact
about ``Document.light_document_model`` existed -- the packet never carried them, because a bullet
that names no identifier matched no symbol and enum members are not ranked by word overlap).

Real text and real fact ids/values, copied from that run's stored bundle."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review import evidence as ev

READS = (
    "- **Read multiple input formats.** It reads DOCX, DOC, RTF, Markdown, and plain text files "
    "automatically based on file extension using dedicated readers."
)
MODEL = (
    "- Inspect the parsed document model directly — sections, paragraphs, runs, tables, styles, "
    "and numbered/bulleted lists are all typed Pydantic models reachable from "
    "`Document.light_document_model`."
)


def _fact(fact_id: str, kind: str, value: str) -> Fact:
    return Fact(
        id=fact_id, kind=kind, value=value,  # type: ignore[arg-type]
        evidence=(Evidence("src/aspose/words_foss", None),), polarity="SUPPORTED",
    )


def _document() -> FactsDocument:
    facts = [
        _fact("identity:repository", "identity", "aspose-words-foss/Aspose.Words-FOSS-for-Python"),
        _fact("enum_member:aspose.words_foss.loadformat.auto", "enum_member", "aspose.words_foss.LoadFormat.AUTO"),
        _fact("enum_member:aspose.words_foss.loadformat.docx", "enum_member", "aspose.words_foss.LoadFormat.DOCX"),
        _fact("enum_member:aspose.words_foss.loadformat.markdown", "enum_member", "aspose.words_foss.LoadFormat.MARKDOWN"),
        _fact("enum_member:aspose.words_foss.loadformat.rtf", "enum_member", "aspose.words_foss.LoadFormat.RTF"),
        _fact("enum_member:aspose.words_foss.saveformat.pdf", "enum_member", "aspose.words_foss.SaveFormat.PDF"),
        _fact("enum_member:aspose.words_foss.nodetype.document", "enum_member", "aspose.words_foss.NodeType.DOCUMENT"),
        _fact(
            "implementation:throws.aspose.words_foss.document.light_document_model.getter.valueerror",
            "implementation",
            "aspose.words_foss.Document.light_document_model getter raises ValueError",
        ),
        _fact("implementation:constant.aspose.words_foss.doc_reader.constants.sprm_pilvl", "implementation", "SPRM_PILVL = 97"),
    ]
    return FactsDocument("aspose-words-foss/Aspose.Words-FOSS-for-Python", "0" * 40, tuple(facts))


def _ids(text: str) -> set[str]:
    return {r["id"] for r in ev.unit_facts(_document(), text, sections=["key_capabilities"])}


def test_a_bullet_naming_formats_carries_the_enumeration_members_that_prove_them() -> None:
    ids = _ids(READS)
    assert "enum_member:aspose.words_foss.loadformat.docx" in ids
    assert "enum_member:aspose.words_foss.loadformat.rtf" in ids
    assert "enum_member:aspose.words_foss.loadformat.markdown" in ids


def test_format_members_are_limited_to_the_formats_the_text_names() -> None:
    ids = _ids(READS)
    assert "enum_member:aspose.words_foss.loadformat.auto" not in ids  # 'auto' is not a named format
    assert "enum_member:aspose.words_foss.saveformat.pdf" not in ids  # PDF is not in this bullet
    assert "enum_member:aspose.words_foss.nodetype.document" not in ids  # not a format enumeration


def test_a_claim_about_an_attribute_is_shown_what_the_source_says_it_does() -> None:
    ids = _ids(MODEL)
    assert (
        "implementation:throws.aspose.words_foss.document.light_document_model.getter.valueerror"
        in ids
    )
    assert "implementation:constant.aspose.words_foss.doc_reader.constants.sprm_pilvl" not in ids


def test_term_support_never_displaces_a_fact_that_was_already_carried(monkeypatch) -> None:
    for budget in (300, 700, 36_000):
        monkeypatch.setattr(ev, "FACTS_CHARS", budget)
        with_support = _ids(MODEL) | _ids(READS)
        monkeypatch.setattr(ev, "_term_support", lambda *a, **k: [])
        monkeypatch.setattr(ev, "_format_members", lambda *a, **k: [])
        without_support = _ids(MODEL) | _ids(READS)
        monkeypatch.undo()
        assert without_support <= with_support, budget
