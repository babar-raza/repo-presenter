"""An undocumented type's sentence is built from its facts only, and an alias reads the facts of
the class it re-exports (authoring._type_batches).

Regressions: Aspose.3D-FOSS-for-Java hosted run 43405236397 (19 factuality findings, every one a
name-derived "X represents ..." gloss the objective asked for) and Aspose.BarCode-FOSS-for-Python
run 43405225313 (``aspose_barcode_foss.PdfRenderer``, a re-export of
``aspose_barcode_foss.renderers.PdfRenderer``, got none of its stub facts and was glossed as
rendering barcodes to PDF).
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    _type_batches,
    type_implementation_facts,
    type_members,
    type_paths,
)
from tests.readme.composition.synthetic import make_entry, make_facts

ALIAS = "public_symbol:aspose_widget_foss.pdfrenderer"
CLASS = "public_symbol:aspose_widget_foss.renderers.pdfrenderer"
METHOD = "public_symbol:aspose_widget_foss.renderers.pdfrenderer.render"
STUB = "implementation:throws.aspose_widget_foss.renderers.pdfrenderer.render.body.notimplementederror"
MATRIX = "public_symbol:aspose_widget_foss.matrix4"
DECOMPOSE = "public_symbol:aspose_widget_foss.matrix4.decompose"


def _facts() -> FactsDocument:
    base = make_facts()
    extra = (
        # The real shape (python_surface.public_symbol_facts' loose alias, measured on the
        # BarCode checkout): its own fact, no defined_at, the target named only by evidence.
        Fact(
            ALIAS,
            "public_symbol",
            "aspose_widget_foss.PdfRenderer",
            (
                Evidence(
                    "aspose_widget_foss/__init__.py",
                    "line 29; class; public by reexport; re-export of "
                    "aspose_widget_foss.renderers.PdfRenderer",
                ),
            ),
            attributes={"symbol_kind": "class"},
        ),
        Fact(
            CLASS,
            "public_symbol",
            "aspose_widget_foss.renderers.PdfRenderer",
            (
                Evidence(
                    "aspose_widget_foss/renderers.py",
                    "line 3; class; public by reexport; re-export of "
                    "aspose_widget_foss._internal.renderers.pdf.PdfRenderer",
                ),
            ),
            attributes={"symbol_kind": "class"},
        ),
        Fact(
            METHOD,
            "public_symbol",
            "aspose_widget_foss.renderers.PdfRenderer.render",
            (Evidence("aspose_widget_foss/_internal/renderers/pdf.py", "line 20; method; "),),
            attributes={"symbol_kind": "method"},
        ),
        Fact(
            STUB,
            "implementation",
            "aspose_widget_foss.renderers.PdfRenderer.render raises NotImplementedError",
            (Evidence("aspose_widget_foss/_internal/renderers/pdf.py", "line 23; raise"),),
            attributes={
                "aspect": "throws",
                "member": "aspose_widget_foss.renderers.PdfRenderer.render",
                "exception": "NotImplementedError",
                "condition": "always",
            },
        ),
        Fact(
            MATRIX,
            "public_symbol",
            "aspose_widget_foss.Matrix4",
            (Evidence("aspose_widget_foss/matrix4.py", "line 1; class; public by declaration"),),
            attributes={"symbol_kind": "class", "signature": "class Matrix4"},
        ),
        Fact(
            DECOMPOSE,
            "public_symbol",
            "aspose_widget_foss.Matrix4.decompose",
            (Evidence("aspose_widget_foss/matrix4.py", "line 9; method; public by declaration"),),
            attributes={"symbol_kind": "method"},
        ),
    )
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


def _fact(facts: FactsDocument, fact_id: str) -> Fact:
    return next(fact for fact in facts.facts if fact.id == fact_id)


def test_an_alias_reads_the_implementation_facts_of_the_class_it_re_exports() -> None:
    facts = _facts()
    alias = _fact(facts, ALIAS)
    assert "aspose_widget_foss.renderers.PdfRenderer" in type_paths(alias, facts)
    assert [fact.id for fact in type_implementation_facts(alias, facts)] == [STUB]
    assert type_members(alias, facts) == ["render"]
    (task,) = _type_batches(make_entry(), facts, [])
    assert STUB in task.slot_facts[f"type:{ALIAS}"]
    assert STUB in task.slot_facts[f"type:{CLASS}"]


def test_a_type_without_a_re_export_keeps_only_its_own_path() -> None:
    facts = _facts()
    matrix = _fact(facts, MATRIX)
    assert type_paths(matrix, facts) == {"aspose_widget_foss.Matrix4"}
    assert type_implementation_facts(matrix, facts) == []


def test_the_objective_asks_for_facts_only_never_a_name_derived_purpose() -> None:
    (task,) = _type_batches(make_entry(), _facts(), [])
    objective = task.packet["objective"]
    assert "what it represents" not in objective
    assert "its name:" not in objective
    assert "Never a purpose" in objective and "inferred from the" in objective
    records = {record["id"]: record for record in task.packet["accepted_facts"]}
    assert records[MATRIX]["members"] == ["decompose"]
    assert records[MATRIX]["signature"] == "class Matrix4"
