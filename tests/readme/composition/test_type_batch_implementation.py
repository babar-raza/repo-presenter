"""A type batch carries each type's own ``implementation`` facts (authoring._type_batches).

Regression for Aspose.BarCode-FOSS-for-Python, hosted run 43394959529: the batch packet carried
only the symbol fact, so a renderer whose ``render`` raises NotImplementedError was glossed from
its name as rendering barcodes to PDF, and the independent review rejected the row.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    _TYPE_IMPLEMENTATION_RULE,
    _type_batches,
    citable,
    type_implementation_facts,
    unit_checks,
)
from repo_presenter.readme.repair.targeted import Defect, repair_packet
from tests.readme.composition.synthetic import make_entry, make_facts

RENDERER = "public_symbol:aspose_widget_foss.pdfrenderer"
OPTIONS = "public_symbol:aspose_widget_foss.options.code128options"
STUB = "implementation:throws.aspose_widget_foss.pdfrenderer.render.body.notimplementederror"
GUARD = "implementation:throws.aspose_widget_foss.pdfrenderer.save.body.valueerror"
NESTED = "implementation:throws.aspose_widget_foss.pdfrenderer.inner.run.body.notimplementederror"


def _symbol(fact_id: str, value: str) -> Fact:
    return Fact(
        fact_id,
        "public_symbol",
        value,
        (Evidence("aspose_widget_foss/x.py", "; class; "),),
        attributes={"symbol_kind": "class"},
    )


def _throws(fact_id: str, member: str, exception: str, condition: str) -> Fact:
    suffix = "" if condition == "always" else " (conditionally)"
    return Fact(
        fact_id,
        "implementation",
        f"{member} raises {exception}{suffix}",
        (Evidence("aspose_widget_foss/pdfrenderer.py", "line 9; raise statement"),),
        attributes={
            "aspect": "throws",
            "member": member,
            "exception": exception,
            "condition": condition,
        },
    )


def _facts(*, with_stubs: bool = True) -> FactsDocument:
    base = make_facts()
    extra: list[Fact] = [
        _symbol(RENDERER, "aspose_widget_foss.PdfRenderer"),
        _symbol(OPTIONS, "aspose_widget_foss.options.Code128Options"),
    ]
    if with_stubs:
        extra += [
            _throws(GUARD, "aspose_widget_foss.PdfRenderer.save", "ValueError", "conditional"),
            _throws(
                STUB, "aspose_widget_foss.PdfRenderer.render", "NotImplementedError", "always"
            ),
            # A nested type's member is that type's, never PdfRenderer's own.
            _throws(
                NESTED,
                "aspose_widget_foss.PdfRenderer.Inner.run",
                "NotImplementedError",
                "always",
            ),
        ]
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


def test_a_types_own_implementation_facts_are_found_unconditional_raise_first() -> None:
    facts = _facts()
    renderer = next(fact for fact in facts.facts if fact.id == RENDERER)
    options = next(fact for fact in facts.facts if fact.id == OPTIONS)
    assert [fact.id for fact in type_implementation_facts(renderer, facts)] == [STUB, GUARD]
    assert type_implementation_facts(options, facts) == []


def test_the_batch_packet_carries_the_stub_facts_and_the_rule_to_state_them() -> None:
    (task,) = _type_batches(make_entry(), _facts(), [])
    accepted = {record["id"]: record for record in task.packet["accepted_facts"]}
    assert accepted[STUB]["value"] == (
        "aspose_widget_foss.PdfRenderer.render raises NotImplementedError"
    )
    assert GUARD in accepted and NESTED not in accepted
    assert _TYPE_IMPLEMENTATION_RULE in task.packet["objective"]
    assert {STUB, GUARD} <= task.accepted_ids
    slots = {record["slot"]: record for record in task.packet["slots"]}
    assert slots[f"type:{RENDERER}"]["fact_ids"] == sorted({RENDERER, STUB, GUARD})
    assert slots[f"type:{OPTIONS}"]["fact_ids"] == [OPTIONS]
    assert STUB in citable(task, f"type:{RENDERER}")
    assert STUB not in citable(task, f"type:{OPTIONS}")


def test_a_batch_with_no_implementation_facts_is_unchanged() -> None:
    (task,) = _type_batches(make_entry(), _facts(with_stubs=False), [])
    assert _TYPE_IMPLEMENTATION_RULE not in task.packet["objective"]
    assert {record["id"] for record in task.packet["accepted_facts"]} == {RENDERER, OPTIONS}
    assert task.accepted_ids == frozenset({RENDERER, OPTIONS})


def test_a_unit_may_state_the_stub_truthfully_citing_its_implementation_fact() -> None:
    facts = _facts()
    (task,) = _type_batches(make_entry(), facts, [])
    output = {
        "units": [
            {
                "section": "api_reference",
                "slot": f"type:{OPTIONS}",
                "text": "Code128Options holds the settings for Code 128 symbols.",
                "fact_ids": [OPTIONS],
            },
            {
                "section": "api_reference",
                "slot": f"type:{RENDERER}",
                "text": "PdfRenderer is a placeholder: its render method raises "
                "NotImplementedError.",
                "fact_ids": [RENDERER, STUB],
            },
        ],
        "omitted": [],
    }
    errors = unit_checks(output, task, facts, "Aspose.Widget FOSS for Python")
    assert not [error for error in errors if "PdfRenderer" in error or RENDERER in error], errors


def test_the_repair_packet_carries_the_sections_own_implementation_facts_only() -> None:
    facts = _facts()
    (task,) = _type_batches(make_entry(), facts, [])
    defect = Defect("fp", "review", "F01", "api_reference", "S6", {"quote": "PdfRenderer"})
    packet = repair_packet(
        make_entry(), defect, {"units": []}, facts, [], {}, allowed=task.accepted_ids
    )
    ids = {record["id"] for record in packet["facts"]}
    assert {STUB, GUARD} <= ids
    assert NESTED not in ids
