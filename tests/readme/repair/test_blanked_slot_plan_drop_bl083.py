"""BL-083 (supervisor decision 2026-11-14, audit O7): a targeted S6 repair that blanks a unit is a
request to drop that slot, which the plan owns; it becomes a deterministic plan-level drop,
recorded in the plan's ``deviations`` and the repair ledger, instead of a changes-ledger refusal.

Real logged shapes (docs/investigations/2026-11-13-lane-r-not-progressing/hosted_lane_r.jsonl):
* 43516323114, Aspose.Cells-FOSS-for-Cpp, F01-F03 in scope_limitations: "change R01 claims
  'units[2].text' changed ('The library does not support conditional formatting, data validation,
  hyperlinks, or page setup operations.' to ''), but the causal stage's own input and this revision
  hold the identical value there";
* 43516330798, Aspose.Cells-FOSS-for-Python, BC-18: "change R01 claims 'units[1].text' changed
  ('Apply bold red font styling to a cell.' to '')" (the workflow name of a register-refuted
  example);
* 43513034263, Aspose.3D-FOSS-for-Python (.dae), the negative shape: the ledger claims
  'units[0].text' changed to a NON-empty rewrite the revision does not hold. That is not a drop
  request and keeps its refusal.
"""

from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.core.errors import JobError
from repo_presenter.readme.composition.authoring import SectionTask
from repo_presenter.readme.repair import loop as loop_module
from repo_presenter.readme.repair.targeted import (
    Defect,
    RepairLedger,
    _uncorroborated_changes,
    blanked_slots,
    plan_without_slots,
)

CPP_SCOPE = {
    "units": [
        {"section": "scope_limitations", "slot": "scope", "text": "Aspose.Cells FOSS for C++ reads and writes .xlsx.", "fact_ids": ["package:name"]},
        {"section": "scope_limitations", "slot": "limitation:1", "text": "Formulas are stored, not calculated.", "fact_ids": ["package:name"]},
        {"section": "scope_limitations", "slot": "limitation:2", "text": "The library does not support conditional formatting, data validation, hyperlinks, or page setup operations.", "fact_ids": ["package:name"]},
        {"section": "scope_limitations", "slot": "limitation:3", "text": "DefinedName supports only GetComment, GetFormula, GetHidden, GetLocalSheetIndex, GetName, SetComment, SetFormula, SetHidden, SetLocalSheetIndex, and SetName methods.", "fact_ids": ["package:name"]},
    ],
    "omitted": [],
}
PY_EXAMPLES = {
    "units": [
        {"section": "additional_examples", "slot": "preview", "text": "Workflows for values and styles.", "fact_ids": ["package:name"]},
        {"section": "additional_examples", "slot": "workflow:example:003", "text": "Apply bold red font styling to a cell.", "fact_ids": ["example:003"]},
        {"section": "additional_examples", "slot": "workflow:example:004", "text": "Add a validation list.", "fact_ids": ["example:004"]},
    ],
    "omitted": [],
}


def _reply(original: dict[str, Any], changes: list[dict[str, Any]]) -> dict[str, Any]:
    return {"revised_output": copy.deepcopy(original), "changes": changes}


def test_a_blanked_unit_is_a_slot_drop_request() -> None:
    reply = _reply(CPP_SCOPE, [
        {"id": "R01", "path": "units[2].text", "before": CPP_SCOPE["units"][2]["text"], "after": ""},
        {"id": "R02", "path": "units[3].text", "before": CPP_SCOPE["units"][3]["text"], "after": ""},
    ])
    # the refusal the hosted run logged ...
    assert len(_uncorroborated_changes(reply["changes"], CPP_SCOPE, reply["revised_output"])) == 2
    # ... is read as a drop of the two limitation slots
    assert blanked_slots(reply, CPP_SCOPE) == ["limitation:2", "limitation:3"]
    reply = _reply(PY_EXAMPLES, [
        {"id": "R01", "path": "units[1].text", "before": "Apply bold red font styling to a cell.", "after": ""},
    ])
    assert blanked_slots(reply, PY_EXAMPLES) == ["workflow:example:003"]


def test_negative_controls_a_rewrite_is_not_a_drop() -> None:
    dae = {"units": [{"section": "opening", "slot": "opening", "text": "Aspose.3D FOSS for Python reads and writes 3D formats including `.3mf`, `.dae`, `.fbx`.", "fact_ids": ["package:name"]}]}
    reply = _reply(dae, [{"id": "R01", "path": "units[0].text", "before": dae["units"][0]["text"],
                          "after": "Aspose.3D FOSS for Python reads and writes 3D formats including .3mf, .fbx."}])
    assert blanked_slots(reply, dae) == []
    # a blank claim whose unit the revision did change is not a drop request either
    reply = _reply(PY_EXAMPLES, [{"id": "R01", "path": "units.1.text", "before": "x", "after": ""}])
    reply["revised_output"]["units"][1]["text"] = "Style a cell."
    assert blanked_slots(reply, PY_EXAMPLES) == []


PLAN = {
    "core_capabilities": [{"title": f"Cap {i}", "fact_ids": [f"public_symbol:c{i}"]} for i in range(1, 4)],
    "additional_example_ids": ["example:003", "example:004"],
    "material_limitations": [
        {"fact_ids": ["public_symbol:formula"], "unit_ids": []},
        {"fact_ids": ["public_symbol:conditionalformatting"], "unit_ids": []},
        {"fact_ids": ["public_symbol:definedname"], "unit_ids": []},
    ],
    "api_hubs": [], "links": [], "deviations": [],
}


def test_the_plan_drops_the_slots_and_records_the_drop() -> None:
    revised, cited, changes = plan_without_slots(
        PLAN, "scope_limitations", ["limitation:2", "limitation:3"], "F01: blanked"
    )
    assert revised["material_limitations"] == [PLAN["material_limitations"][0]]
    assert cited == ["public_symbol:conditionalformatting", "public_symbol:definedname"]
    assert [c["path"] for c in changes] == ["material_limitations[1]", "material_limitations[2]"]
    assert revised["deviations"][-1]["section_id"] == "scope_limitations"
    assert "limitation:2" in revised["deviations"][-1]["text"]
    revised, cited, _ = plan_without_slots(
        PLAN, "additional_examples", ["workflow:example:003"], "BC-18: blanked"
    )
    assert revised["additional_example_ids"] == ["example:004"] and cited == ["example:003"]
    assert PLAN["additional_example_ids"] == ["example:003", "example:004"]  # input untouched


def test_negative_controls_slots_the_plan_does_not_own() -> None:
    assert plan_without_slots(PLAN, "scope_limitations", ["scope"], "x") is None
    assert plan_without_slots(PLAN, "opening", ["opening"], "x") is None
    assert plan_without_slots(PLAN, "scope_limitations", ["limitation:9"], "x") is None
    assert plan_without_slots(PLAN, "additional_examples", ["workflow:example:999"], "x") is None


# --- the wiring: _repair_task routes the refused blank reply to the plan-level drop ------------


class _Store:
    def __init__(self, stored: dict[str, Any]) -> None:
        self.stored = dict(stored)

    def get(self, key: str) -> dict[str, Any] | None:
        return self.stored.get(key)

    def put(self, key: str, job: str, model: Any, output: dict[str, Any]) -> None:
        self.stored[key] = output


def _task() -> SectionTask:
    slots = tuple(u["slot"] for u in CPP_SCOPE["units"])
    return SectionTask("scope_limitations", {}, frozenset({"package:name"}), slots, key="scope")


def _context(dispositions: dict[str, Any]) -> Any:
    manifest = SimpleNamespace(prompt_id="presentation_planning")
    return SimpleNamespace(
        prompts={"presentation_planning": SimpleNamespace(manifest=manifest),
                 "section_authoring": SimpleNamespace(manifest=manifest)},
        entry=SimpleNamespace(ecosystem="cpp"), facts=SimpleNamespace(facts=()), investigation={},
        dispositions=dispositions, plan=copy.deepcopy(PLAN),
        store=_Store({"plan": copy.deepcopy(PLAN)}), context=None,
        name="Aspose.Cells FOSS for C++", units={}, readme="", benchmark="",
    )


@pytest.fixture
def _fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loop_module, "planning_packet", lambda *a, **k: {})
    monkeypatch.setattr(loop_module, "planning_schema", lambda *a, **k: {})
    monkeypatch.setattr(loop_module, "effective_model", lambda *a, **k: "m")
    monkeypatch.setattr(loop_module, "request_hash", lambda *a, **k: "plan")
    monkeypatch.setattr(loop_module, "plan_checks", lambda *a, **k: [])
    monkeypatch.setattr(loop_module, "_store_trimmed_section", lambda *a, **k: None)


DEFECT = Defect("fp", "review", "F01+F02+F03", "scope_limitations", "S6", {})


def test_the_blanked_slots_are_dropped_at_the_plan_with_no_call(_fakes: None, tmp_path: Path) -> None:
    rc = _context({"dispositions": []})
    repairs = RepairLedger(tmp_path / "repairs.json")
    assert loop_module._drop_slots_at_plan(
        rc, DEFECT, _task(), ["limitation:2", "limitation:3"], repairs, "refused"
    )
    assert rc.store.stored["plan"]["material_limitations"] == [PLAN["material_limitations"][0]]
    attempt = repairs.attempts["fp"]
    assert attempt["outcome"] == "repaired" and len(attempt["changes"]) == 2


def test_negative_control_a_slot_carrying_an_inherited_unit_is_not_dropped(_fakes: None, tmp_path: Path) -> None:
    rc = _context({"dispositions": [{"unit_id": "inherited_unit:050.list", "disposition":
                   "SUPERSEDE_REDUNDANT", "destination_section": "scope_limitations"}]})
    rc.store.stored["plan"]["material_limitations"][1]["unit_ids"] = ["inherited_unit:050.list"]
    repairs = RepairLedger(tmp_path / "repairs.json")
    assert not loop_module._drop_slots_at_plan(
        rc, DEFECT, _task(), ["limitation:2"], repairs, "refused"
    )
    assert repairs.attempts["fp"]["outcome"] == "unrepairable"
    assert "inherited_unit:050.list" in repairs.attempts["fp"]["reason"]
    assert rc.store.stored["plan"]["material_limitations"][1]["unit_ids"]  # plan unchanged


def test_repair_task_routes_a_refused_blank_reply_to_the_drop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    seen: list[Any] = []

    def targeted(rc: Any, defect: Any, loaded: Any, original: Any, checks: Any, **kw: Any) -> Any:
        reply = _reply(original, [{"id": "R01", "path": "units[2].text",
                                   "before": original["units"][2]["text"], "after": ""}])
        kw["recover"](reply)
        return JobError("change R01 claims 'units[2].text' changed")

    monkeypatch.setattr(loop_module, "_task_key", lambda *a: "scope")
    monkeypatch.setattr(loop_module, "_targeted_call", targeted)
    monkeypatch.setattr(loop_module, "_drop_slots_at_plan",
                        lambda rc, d, t, slots, r, why: seen.append(slots) or True)
    rc = _context({"dispositions": []})
    rc.store.stored["scope"] = copy.deepcopy(CPP_SCOPE)
    assert loop_module._repair_task(rc, DEFECT, _task(), RepairLedger(tmp_path / "repairs.json"))
    assert seen == [["limitation:2"]]
