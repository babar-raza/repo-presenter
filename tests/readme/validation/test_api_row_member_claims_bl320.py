"""BL-320: an API row's member list is held to the type the sentence is ABOUT, never to a base it names.

Every finding text below is the exact one of the frozen-code hosted pass 1 (2026-11-19) failure
records of the PDF Cpp/Java/.NET/Python/Go cells: the renderer's own fact-true row "Class that
inherits from ExplicitDestination and declares the methods Top and ToString." was refused by BC-14 /
claim_contradiction because the check held the declared list to the BASE the row names. A real
overlap of one listed name with the base (``ToString``) was enough to pick the base as the owner.
Each shape passes after the fix; negative controls show a member the row's own type lacks, a list
whose owner is named after it, and a property called a method are still flagged.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.claims import _lines
from repo_presenter.readme.validation.must_correct import (
    DEGRADE_RECORDS_KEY,
    ClaimFlag,
    degrade_claims,
    duplicate_flags,
)
from repo_presenter.readme.validation.surface_claims import surface_findings
from tests.readme.repair.test_accounting import UNITS, _dispositions, _facts, _plan


def _f(fid: str, kind: str, value: str, **attributes: str) -> Fact:
    return Fact(fid, kind, value, (Evidence("x.h", "line 1"),), attributes=attributes or None)  # type: ignore[arg-type]


def _facts_of(types: list[tuple[str, str]], members: list[tuple[str, str, str]]) -> FactsDocument:
    facts = [_f("identity:ecosystem", "identity", "cpp")]
    for name, bases in types:
        extra = {"bases": bases} if bases else {}
        facts.append(_f(f"public_symbol:{name.lower()}", "public_symbol", f"Ns.{name}", symbol_kind="class", **extra))
    for owner, name, kind in members:
        facts.append(
            _f(f"public_symbol:{owner}.{name}".lower(), "public_symbol", f"Ns.{owner}.{name}",
               symbol_kind="method", member_kind=kind, signature=f"{name}()")
        )
    return FactsDocument("a/b", "0" * 40, tuple(facts))


def _row(name: str, description: str) -> str:
    return f"| Class | Description |\n|---|---|\n| `{name}` | {description} |\n"


def _details(readme: str, facts: FactsDocument) -> list[str]:
    return [f.detail for f in surface_findings(_lines(readme), facts)]


def _pdf() -> FactsDocument:
    return _facts_of(
        [("ExplicitDestination", "PdfObject"), ("FitBHExplicitDestination", "ExplicitDestination"),
         ("MarkupAnnotation", "PdfObject"), ("CaretAnnotation", "MarkupAnnotation")],
        [("ExplicitDestination", "ToString", "method"),
         ("FitBHExplicitDestination", "Top", "method"), ("FitBHExplicitDestination", "ToString", "method"),
         ("MarkupAnnotation", "Accept", "method"),
         ("CaretAnnotation", "Accept", "method"), ("CaretAnnotation", "Frame", "method"),
         ("CaretAnnotation", "Symbol", "method")],
    )


# --- pass-1 finding texts ----------------------------------------------------------------------


def test_fitbh_row_names_the_base_and_declares_its_own_methods() -> None:
    row = _row("FitBHExplicitDestination",
               "Class that inherits from ExplicitDestination and declares the methods Top and ToString.")
    assert _details(row, _pdf()) == []


def test_caret_annotation_row_declares_methods_the_base_also_has() -> None:
    row = _row("CaretAnnotation",
               "Class that inherits from MarkupAnnotation and declares the methods Accept, Frame and Symbol.")
    assert _details(row, _pdf()) == []


def test_every_listed_base_is_a_base_not_an_owner() -> None:
    facts = _facts_of(
        [("Entity", "PdfObject"), ("IOrientable", "PdfObject"), ("Camera", "Entity, IOrientable")],
        [("Entity", "Name", "method"), ("IOrientable", "Aspect", "property"),
         ("Camera", "Name", "method"), ("Camera", "LookAt", "method")],
    )
    row = _row("Camera", "Class that inherits from Entity and IOrientable and declares the methods Name and LookAt.")
    assert _details(row, facts) == []


def test_a_kind_word_that_opens_the_next_list_is_no_member() -> None:
    facts = _facts_of(
        [("Workbook", "PdfObject")],
        [("Workbook", "add_worksheet", "method"), ("Workbook", "properties", "property"),
         ("Workbook", "file_path", "property")],
    )
    row = _row("Workbook", "Class that declares methods including add_worksheet and properties including file_path and properties.")
    assert _details(row, facts) == []


# --- negative controls: the check still finds what is wrong ---------------------------------------


def test_a_member_the_row_type_lacks_is_still_a_finding() -> None:
    row = _row("FitBHExplicitDestination",
               "Class that inherits from ExplicitDestination and declares the methods Top, ToString and Frobnicate.")
    [detail] = _details(row, _pdf())
    assert "`Frobnicate`" in detail and "`FitBHExplicitDestination`" in detail


def test_a_list_whose_owner_is_named_after_it_is_still_held_to_that_owner() -> None:
    row = _row("FitBHExplicitDestination", "Declares the methods Top and ToString of ExplicitDestination.")
    [detail] = _details(row, _pdf())
    assert "`Top`" in detail and "`ExplicitDestination`" in detail


def test_a_sentence_about_the_base_with_a_missing_member_is_still_a_finding() -> None:
    text = "`ExplicitDestination` declares the methods Top and ToString.\n"
    [detail] = _details(text, _pdf())
    assert "`Top`" in detail and "`ExplicitDestination`" in detail


def test_a_property_called_a_method_is_still_a_finding() -> None:
    facts = _facts_of([("Workbook", "PdfObject")], [("Workbook", "properties", "property")])
    [detail] = _details(_row("Workbook", "Class that declares the methods properties."), facts)
    assert "Workbook.properties" in detail and "method" in detail


# --- duplicate_paragraph: the authored copy of a paragraph an inherited unit prints (BL-320) -------

PARAGRAPH = (
    "The library's package entry points are organized into three stable layers, all importable from "
    "the package: the high-level API, the low-level API and the container API, listed below."
)


class _Finding:
    rule = "duplicate_paragraph"
    source = "deterministic"
    message = "the candidate prints the same prose paragraph more than once"
    quote = PARAGRAPH


def _intro_units(text: str, cites: list[str] | None = None) -> dict[str, Any]:
    units = copy.deepcopy(UNITS)
    for unit in units["units"]:
        if unit["slot"] == "intro":
            unit["text"] = text
            if cites is not None:
                unit["fact_ids"] = cites
    return units


def test_the_authored_intro_that_is_the_printed_paragraph_is_dropped_with_a_record() -> None:
    units = _intro_units(PARAGRAPH, ["inherited_unit:041.paragraph"])
    flags = duplicate_flags([_Finding()])
    assert [f.check for f in flags] == ["duplicate_paragraph"]
    _plan_out, new_units, _disp, records = degrade_claims(_plan(), units, _dispositions(), flags, _facts())
    assert "intro" not in [u["slot"] for u in new_units["units"]]
    [record] = records
    assert record["action"] == "duplicate_unit_dropped" and record["slot"] == "intro" and record["rule"] == "BL-240"
    assert new_units[DEGRADE_RECORDS_KEY] == records
    assert len(new_units["units"]) == len(units["units"]) - 1  # nothing else was touched


def test_a_duplicate_with_no_authored_copy_leaves_every_copy_printed() -> None:
    units = _intro_units("Scene is the entry point.")
    plan, new_units, disp, records = degrade_claims(
        _plan(), units, _dispositions(), duplicate_flags([_Finding()]), _facts()
    )
    assert records == [] and new_units == units and disp == _dispositions()  # R14: inherited copy is live content


def test_the_opening_is_never_dropped_as_a_duplicate() -> None:
    units = copy.deepcopy(UNITS)
    units["units"][0]["text"] = PARAGRAPH
    _p, new_units, _d, records = degrade_claims(_plan(), units, _dispositions(), duplicate_flags([_Finding()]), _facts())
    assert records == [] and new_units["units"][0]["slot"] == "opening"


def test_a_model_finding_is_not_a_duplicate_flag() -> None:
    class Other:
        rule = "claim_contradiction"
        quote = PARAGRAPH

    assert duplicate_flags([Other()]) == []
    assert ClaimFlag("x" * 20, "d", "duplicate_paragraph").check == "duplicate_paragraph"
