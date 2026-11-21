"""BL-561: an authored paragraph the document already prints as a kept maintainers' unit prints once, and the
degrade's drop of a duplicate unit leaves its slot owed nothing.

Real data: hosted Cells C++ refresh run 44900529375 (``duplicate_paragraph``, "the paragraph occurs 2 times",
quote "The library's public types live in the `Aspose::Cells_FOSS` namespace, with `Workbook` as the root entry
point and `Worksheet`/`Cells`/`Cell` forming the primary object graph beneath it."): the paragraph is the
maintainers' ``inherited_unit:041.paragraph``; an authored api_reference unit carried it verbatim while the
placement printed it too. The BL-320 degrade lever (drop the authored copy with an R14 record) was tried twice
and discarded each time, "adds failing check(s) ['BC-04']": the dropped slot was still owed a unit.
"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any

from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.review.independent_reviewer import duplicate_paragraph_rule
from repo_presenter.readme.composition.authoring import (
    DUPLICATE_UNIT_OMISSION_REASON,
    product_name,
    unit_checks,
)
from repo_presenter.readme.validation.must_correct import degrade_claims, duplicate_flags
from tests.readme.composition.synthetic import make_entry
from tests.readme.composition.test_api_row_fallback import _facts as _api_facts
from tests.readme.composition.test_api_row_fallback import _tasks as _api_tasks
from tests.readme.composition.test_pipeline import _dispositions as _pipeline_dispositions
from tests.readme.composition.test_pipeline import _plan as _pipeline_plan
from tests.readme.repair.test_accounting import (
    ENTRY,
    UNITS,
    _dispositions,
    _entry,
    _facts,
    _plan,
    _unit,
)

PARAGRAPH = (
    "The library's public types live in the Aspose::Cells_FOSS namespace, with Workbook as the root entry "
    "point and Worksheet/Cells/Cell forming the primary object graph beneath it."
)
UNIT_ID = "007.paragraph"
CITED = f"inherited_unit:{UNIT_ID}"


def _facts_with_paragraph() -> Any:
    base = _facts()
    return dataclasses.replace(base, facts=(*base.facts, _unit(UNIT_ID, PARAGRAPH)))


def _disp() -> dict[str, Any]:
    return _dispositions(**{UNIT_ID: _entry(UNIT_ID, "VERIFIED_PRESERVE", "api_reference", [])})


def _units(intro: str, cites: list[str]) -> dict[str, Any]:
    units = copy.deepcopy(UNITS)
    for unit in units["units"]:
        if unit["slot"] == "intro":
            unit["text"], unit["fact_ids"] = intro, cites
    return units


def _render(intro: str, cites: list[str] | None = None) -> str:
    return render_readme(ENTRY, _facts_with_paragraph(), _plan(), _units(intro, cites or [CITED]), _disp())


def test_a_paragraph_the_placement_prints_is_not_printed_again_by_an_authored_unit() -> None:
    readme = _render(PARAGRAPH)
    assert readme.count("public types live in the") == 1
    assert duplicate_paragraph_rule(readme) == []


def test_the_kept_maintainers_copy_is_the_one_that_prints() -> None:
    readme = _render(PARAGRAPH.replace("Workbook", "`Workbook`"))
    assert PARAGRAPH in readme
    assert readme.count("forming the primary object graph") == 1


def test_only_the_repeated_paragraph_of_the_unit_is_left_out() -> None:
    readme = _render("Scene is the entry point of the graph.\n\n" + PARAGRAPH)
    assert "is the entry point of the graph." in readme
    assert readme.count("public types live in the") == 1


def test_negative_control_a_different_authored_paragraph_prints_as_written() -> None:
    other = "Scene is the entry point, and every export starts from a Scene built from nodes and meshes in memory."
    readme = _render(other)
    assert "every export starts from a" in readme and PARAGRAPH in readme


def test_negative_control_the_reviewer_rule_still_sees_a_real_duplicate() -> None:
    assert duplicate_paragraph_rule(PARAGRAPH + "\n\n" + PARAGRAPH) != [] or len(PARAGRAPH) < 120
    long = PARAGRAPH + " " + PARAGRAPH
    assert duplicate_paragraph_rule("# T\n\n## Scope and Limitations\n\n" + long + "\n\n" + long + "\n") != []


def _intro_task() -> tuple[Any, Any]:
    facts = _api_facts()
    return next(t for t in _api_tasks(facts) if "intro" in t.slots), facts


def _reply(task: Any) -> dict[str, Any]:
    return {
        "units": [
            {"section": task.section_id, "slot": slot, "text": f"Text for {slot} of the library.", "fact_ids": []}
            for slot in task.slots
        ],
        "omitted": [],
    }


def _owed(output: dict[str, Any], task: Any, facts: Any) -> list[str]:
    errors = unit_checks(output, task, facts, product_name(make_entry()), register=False, values=False)
    return [e for e in errors if "must fill exactly these slots" in e]


class _Dup:
    rule = "duplicate_paragraph"
    source = "deterministic"
    message = "the candidate prints the same prose paragraph more than once"
    quote = PARAGRAPH


def test_a_dropped_duplicate_unit_leaves_its_slot_owed_nothing() -> None:
    task, facts = _intro_task()
    reply = _reply(task)
    for unit in reply["units"]:
        if unit["slot"] == "intro":
            unit["text"] = PARAGRAPH
    _plan_out, dropped, _disp_out, records = degrade_claims(
        _pipeline_plan(), reply, _pipeline_dispositions(), duplicate_flags([_Dup()]), facts
    )
    assert [r["action"] for r in records] == ["duplicate_unit_dropped"] and records[0]["slot"] == "intro"
    assert "intro" not in [u["slot"] for u in dropped["units"]]
    assert _owed(dropped, task, facts) == []


def test_negative_control_a_unit_dropped_without_the_record_is_still_owed() -> None:
    task, facts = _intro_task()
    reply = _reply(task)
    reply["units"] = [u for u in reply["units"] if u["slot"] != "intro"]
    assert _owed(reply, task, facts)


def test_negative_control_the_record_releases_only_its_own_section_and_slot() -> None:
    task, facts = _intro_task()
    reply = _reply(task)
    reply["units"] = [u for u in reply["units"] if u["slot"] != "intro"]
    reply["omitted"] = [{"fact_id": "slot:other:intro", "slot": "intro", "reason": DUPLICATE_UNIT_OMISSION_REASON, "section": "other"}]
    assert _owed(reply, task, facts)
