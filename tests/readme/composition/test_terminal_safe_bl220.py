"""BL-220 (R46 robust, universal): one slot whose authored or planned output keeps failing the job's
own checks after the bounded asks cost the whole Lane R run (``OutputRejectedError``). The exact
rejection lines of the hosted failure records (``repo_presenter.failures.read_cells``, 2026-11-18):

* Cells C++ 44291563956: ``unit context: names the Enterprise Edition; the shell's closing sentence
  names it exactly once. Drop the name ...``;
* Font Python 44297210403: ``unit opening: restates the inherited paragraph the renderer already
  preserves verbatim right beside "opening"'s own unit; ...``;
* PDF Python 43691416767: ``presentation_planning: $.api_hubs[8].fact_ids[9]:
  'public_symbol:aspose_pdf.document.save_as_image' is not one of [...] (cite only an offered ID)``;
* PDF .NET 43683719616 / PDF C++ 43664910650: ``unit capability:N: spells '1', '7'`` after every
  deletion (a unit that is nothing but the value).

Each shape is built from those message texts on the synthetic product; nothing calls a provider.
Every negative control must still fail closed.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import SectionTask, authoring_tasks, unit_checks
from repo_presenter.readme.composition.authoring_retry import (
    RECOVERY_NOTES_KEY,
    recover_authoring_output,
    recover_opening_output,
)
from repo_presenter.readme.composition.planning import (
    citable_from_schema,
    plan_checks,
    recover_planning_output,
)
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan
from tests.readme.composition.test_value_names_bl170 import NAME, _facts, _task

PARAGRAPH = "Aspose.Widget FOSS for Python is a pure-Python library for rendering widgets."


def _facts_with_formats() -> FactsDocument:
    base = _facts()
    formats = (
        Fact("format:input.png", "format", ".png", (Evidence("a.py", "l"),)),
        Fact("format:output.svg", "format", ".svg", (Evidence("a.py", "l"),)),
    )
    inherited = Fact(
        "inherited_unit:090.paragraph", "inherited_unit", PARAGRAPH, (Evidence("README.md", "l"),)
    )
    return replace(base, facts=(*base.facts, *formats, inherited))


def _opening_task(facts: FactsDocument, dispositions: dict[str, Any]) -> SectionTask:
    plan = _plan()
    assert plan_checks(plan, facts, dispositions=dispositions) == []
    return next(
        t for t in authoring_tasks(make_entry(), facts, {}, dispositions, plan)
        if t.section_id == "opening"
    )


def _opening_dispositions() -> dict[str, Any]:
    dispositions = copy.deepcopy(_dispositions())
    dispositions["dispositions"].append(
        {
            "unit_id": "inherited_unit:090.paragraph",
            "disposition": "VERIFIED_PRESERVE",
            "destination_section": "opening",
            "fact_ids": [],
            "rationale": "kept",
        }
    )
    return dispositions


# --- opening: restates the inherited paragraph -------------------------------------------------


def test_a_restating_opening_falls_to_the_format_sentence() -> None:
    facts = _facts_with_formats()
    dispositions = _opening_dispositions()
    task = _opening_task(facts, dispositions)
    output = {
        "units": [{"section": "opening", "slot": "opening", "text": PARAGRAPH,
                   "fact_ids": ["package:name"]}],
        "omitted": [],
    }
    rejected = unit_checks(copy.deepcopy(output), task, facts, NAME, dispositions=dispositions)
    assert any("restates the inherited paragraph" in line for line in rejected)
    recovered = recover_opening_output(
        copy.deepcopy(output), task=task, facts=facts, dispositions=dispositions, name=NAME
    )
    assert recovered is not None
    notes = recovered.pop(RECOVERY_NOTES_KEY)
    assert notes[0]["rule"] == "BL-220" and notes[0]["rejected_text"] == PARAGRAPH
    assert recovered["units"][0]["text"] == f"{NAME} reads PNG files and writes SVG files."
    assert unit_checks(copy.deepcopy(recovered), task, facts, NAME, dispositions=dispositions) == []


def test_a_restating_opening_with_no_format_fact_still_fails_closed() -> None:
    facts = replace(
        _facts_with_formats(),
        facts=tuple(f for f in _facts_with_formats().facts if f.kind != "format"),
    )
    dispositions = _opening_dispositions()
    task = _opening_task(facts, dispositions)
    output = {"units": [{"section": "opening", "slot": "opening", "text": PARAGRAPH,
                         "fact_ids": ["package:name"]}], "omitted": []}
    assert recover_opening_output(
        output, task=task, facts=facts, dispositions=dispositions, name=NAME
    ) is None


def test_a_passing_opening_is_never_touched() -> None:
    facts = _facts_with_formats()
    dispositions = _opening_dispositions()
    task = _opening_task(facts, dispositions)
    output = {"units": [{"section": "opening", "slot": "opening",
                         "text": "It renders widgets to images.", "fact_ids": ["package:name"]}],
              "omitted": []}
    assert recover_opening_output(
        output, task=task, facts=facts, dispositions=dispositions, name=NAME
    ) is None


# --- enterprise relationship: names the Enterprise Edition ---------------------------------------


def _enterprise_task() -> SectionTask:
    return SectionTask("enterprise_relationship", {}, frozenset({"package:name"}), ("context",))


def _context(text: str) -> dict[str, Any]:
    return {"units": [{"section": "enterprise_relationship", "slot": "context", "text": text,
                       "fact_ids": ["package:name"]}], "omitted": []}


def test_the_edition_name_sentence_is_deleted_when_another_is_left() -> None:
    task = _enterprise_task()
    output = _context("It adds PDF signing. See the Enterprise Edition for more.")
    assert any(
        "names the Enterprise Edition" in line
        for line in unit_checks(copy.deepcopy(output), task, make_facts(), NAME)
    )
    recovered = recover_authoring_output(output, task=task, facts=make_facts(), name=NAME)
    assert recovered is not None
    assert recovered["units"][0]["text"] == "It adds PDF signing."
    assert recovered[RECOVERY_NOTES_KEY][0]["rule"] == "BL-220"
    recovered.pop(RECOVERY_NOTES_KEY)
    assert unit_checks(copy.deepcopy(recovered), task, make_facts(), NAME) == []


def test_the_clause_that_names_the_edition_is_cut_back() -> None:
    recovered = recover_authoring_output(
        _context("It adds batch conversion and signing, as described in the Enterprise Edition."),
        task=_enterprise_task(), facts=make_facts(), name=NAME,
    )
    assert recovered is not None
    assert recovered["units"][0]["text"] == "It adds batch conversion and signing."


def test_a_unit_that_is_only_the_edition_name_fails_closed() -> None:
    assert recover_authoring_output(
        _context("The Enterprise Edition adds more."),
        task=_enterprise_task(), facts=make_facts(), name=NAME,
    ) is None


# --- key capabilities: nothing but a value --------------------------------------------------------


def test_a_value_only_capability_falls_to_the_fact_true_type_sentence() -> None:
    facts = _facts()
    task = _task(facts, "key_capabilities")
    symbol = "public_symbol:aspose_widget_foss.widget"
    output = {
        "units": [
            {"section": "key_capabilities", "slot": s,
             "fact_ids": [symbol] if s == "capability:1" else ["package:name"],
             "text": "It supports PKCS#7 and 22 functions." if s == "capability:1"
             else "It renders widgets."}
            for s in task.slots
        ],
        "omitted": [],
    }

    def checks(candidate: dict[str, Any]) -> list[str]:
        return unit_checks(candidate, task, facts, NAME, dispositions=_dispositions())

    assert any(" spells " in line for line in checks(copy.deepcopy(output)))
    recovered = recover_authoring_output(output, task=task, facts=facts, checks=checks, name=NAME)
    assert recovered is not None
    note = recovered.pop(RECOVERY_NOTES_KEY)[0]
    assert note["fallback"] == "capability_fact_true_sentence" and note["rule"] == "BL-220"
    assert recovered["units"][0]["text"] == "Public class."
    assert checks(copy.deepcopy(recovered)) == []


def test_a_value_only_capability_citing_no_type_fails_closed() -> None:
    facts = _facts()
    task = _task(facts, "key_capabilities")
    output = {
        "units": [
            {"section": "key_capabilities", "slot": s, "fact_ids": ["package:name"],
             "text": "It supports 22 functions." if s == "capability:2" else "It renders widgets."}
            for s in task.slots
        ],
        "omitted": [],
    }

    def checks(candidate: dict[str, Any]) -> list[str]:
        return unit_checks(candidate, task, facts, NAME, dispositions=_dispositions())

    assert recover_authoring_output(output, task=task, facts=facts, checks=checks, name=NAME) is None


# --- planning: a fact id outside the offered enum --------------------------------------------------


def test_an_uncitable_hub_fact_id_is_dropped() -> None:
    plan = _plan()
    offered = [
        "public_symbol:aspose_widget_foss.widget", "install_command:pip", "package:name",
        "example:001",
    ]
    bad = "public_symbol:aspose_pdf.document.save_as_image"
    plan["api_hubs"][0]["fact_ids"] = [offered[0], bad]
    recovered = recover_planning_output(plan, make_facts(), offered)
    assert recovered is not None
    assert recovered["api_hubs"][0]["fact_ids"] == [offered[0]]
    note = recovered.pop("_recovery_notes")[0]
    assert note["path"] == "$.api_hubs[0].fact_ids" and note["dropped"] == [bad]
    assert note["rule"] == "BL-220"


def test_a_hub_left_with_no_id_falls_to_its_own_symbol_a_capability_fails_closed() -> None:
    offered = ["public_symbol:aspose_widget_foss.widget", "package:name", "install_command:pip"]
    bad = "public_symbol:aspose_pdf.document.save_as_image"
    plan = _plan()
    plan["api_hubs"][0]["fact_ids"] = [bad]
    recovered = recover_planning_output(plan, make_facts(), offered)
    assert recovered is not None
    assert recovered["api_hubs"][0]["fact_ids"] == [offered[0]]
    plan = _plan()
    plan["core_capabilities"][0]["fact_ids"] = [bad]
    assert recover_planning_output(plan, make_facts(), offered) is None


def test_a_plan_inside_the_enum_is_never_touched_and_no_enum_means_no_op() -> None:
    plan = _plan()
    offered = ["public_symbol:aspose_widget_foss.widget", "install_command:pip", "package:name"]
    assert recover_planning_output(copy.deepcopy(plan), make_facts(), offered) is None
    assert recover_planning_output(copy.deepcopy(plan), make_facts()) is None
    assert citable_from_schema(None) == []
    assert citable_from_schema({"$defs": {"citable_fact_id": {"enum": ["a", "b"]}}}) == ["a", "b"]
