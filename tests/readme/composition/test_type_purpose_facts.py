"""An undocumented type's batch carries what its purpose sentence may rest on: an enum's verified
values and the doc comments of its documented members -- and the reviewer is shown the same
(``authoring.type_unit_facts``, ``review.sectionwise.type_row_facts``).

Owner review, 2026-11-13: "ReferenceMode enum defines how vertex attributes reference data,
supporting DIRECT, INDEX_TO_DIRECT, and INDEX modes" is a good description, "Enum with 2 members."
and "<qualified name> is a public symbol with members ..." are not. The shapes are the sealed facts'
own: an enum's values are ``enum_member`` facts (``attributes.enum`` naming the enum, Aspose.PDF
FOSS for Python ``aspose_pdf.printing.Duplex``), a member's summary is its ``docstring`` (Aspose.Words
FOSS for Python ``light_document_model.Body.paragraphs`` "Direct ``Paragraph`` children.").
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    _type_batches,
    type_unit_facts,
    type_values,
)
from repo_presenter.readme.composition.renderer import (
    RenderContext,
    _symbol_description,
)
from tests.readme.composition.synthetic import make_entry, make_facts

DUPLEX = "public_symbol:aspose_pdf.printing.duplex"
BODY = "public_symbol:aspose.words_foss.light_document_model.body"
PARAGRAPHS = "public_symbol:aspose.words_foss.light_document_model.body.paragraphs"
TABLES = "public_symbol:aspose.words_foss.light_document_model.body.tables"


def _member(enum: str, name: str) -> Fact:
    return Fact(
        f"enum_member:{enum}.{name}".lower(),
        "enum_member",
        f"{enum}.{name}",
        (Evidence("aspose_pdf/printing.py", f"line 5; member of enum {enum}"),),
        attributes={"enum": enum, "member_kind": "enum"},
    )


def _facts() -> FactsDocument:
    base = make_facts()
    enum = "aspose_pdf.printing.Duplex"
    module = "aspose.words_foss.light_document_model"
    extra = (
        Fact(
            DUPLEX,
            "public_symbol",
            enum,
            (Evidence("aspose_pdf/printing.py", "line 4; enum; public by declaration"),),
            attributes={"symbol_kind": "enum", "signature": "class Duplex(str, Enum)"},
        ),
        *(_member(enum, name) for name in ("NONE", "SIMPLEX", "DUPLEX", "TUMBLE")),
        Fact(
            BODY,
            "public_symbol",
            f"{module}.Body",
            (Evidence("aspose/words_foss/light_document_model.py", "line 40; class; public by declaration"),),
            attributes={"symbol_kind": "class", "signature": "class Body(BaseModel, NodeCastMixin)"},
        ),
        Fact(
            PARAGRAPHS,
            "public_symbol",
            f"{module}.Body.paragraphs",
            (Evidence("aspose/words_foss/light_document_model.py", "line 44; method; public by declaration"),),
            attributes={"symbol_kind": "method", "docstring": "Direct ``Paragraph`` children."},
        ),
        Fact(
            TABLES,
            "public_symbol",
            f"{module}.Body.tables",
            (Evidence("aspose/words_foss/light_document_model.py", "line 48; method; public by declaration"),),
            attributes={"symbol_kind": "method", "docstring": "Direct ``Table`` children."},
        ),
    )
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


def _fact(facts: FactsDocument, fact_id: str) -> Fact:
    return next(fact for fact in facts.facts if fact.id == fact_id)


def test_an_enum_batch_lists_its_verified_values() -> None:
    facts = _facts()
    duplex = _fact(facts, DUPLEX)
    assert type_values(duplex, facts) == ["DUPLEX", "NONE", "SIMPLEX", "TUMBLE"]
    names, _ = type_unit_facts(duplex, facts)
    assert names == ["DUPLEX", "NONE", "SIMPLEX", "TUMBLE"]
    records = {
        record["id"]: record
        for task in _type_batches(make_entry(), facts, [])
        for record in task.packet["accepted_facts"]
    }
    assert records[DUPLEX]["members"] == ["DUPLEX", "NONE", "SIMPLEX", "TUMBLE"]


def test_a_class_batch_carries_its_members_doc_comments_and_binds_them_to_its_slot() -> None:
    facts = _facts()
    body = _fact(facts, BODY)
    _, given = type_unit_facts(body, facts)
    assert [fact.id for fact in given] == [PARAGRAPHS, TABLES]
    (task,) = _type_batches(make_entry(), facts, [])
    records = {record["id"]: record for record in task.packet["accepted_facts"]}
    assert records[PARAGRAPHS]["docstring"] == "Direct ``Paragraph`` children."
    assert {PARAGRAPHS, TABLES} <= task.slot_facts[f"type:{BODY}"]
    # Member doc comments are not implementation facts: no stub rule is added for them.
    assert "Some types carry implementation facts" not in task.packet["objective"]


def test_an_enum_without_an_authored_sentence_renders_its_values_not_a_label() -> None:
    facts = _facts()
    duplex = _fact(facts, DUPLEX)
    context = RenderContext(make_entry(), facts, {}, {}, {})
    assert _symbol_description(context, duplex) == "Enumerates DUPLEX, NONE, SIMPLEX and TUMBLE."
