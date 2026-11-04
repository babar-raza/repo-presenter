"""A BC-07 visible-line-budget defect at S5 must reach the repair model WITH the measured lever
costs (targeted.visible_line_budget_hint). The hint existed but nothing called it (its caller,
rounds.py, was never ported), so the repair packet always carried ``visible_line_budget: null`` and
the model re-emitted an unchanged plan (aspose-font-foss Aspose.Font-FOSS-for-Python, 321 visible
lines vs 300, flagship example:006): the defect recurred and the candidate failed closed."""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.readme.repair import loop
from tests.readme.composition.synthetic import make_entry, make_facts

PLAN = {"flagship_example_id": "example:001", "additional_example_ids": ["example:001"]}
BIG_README = "\n".join(f"line {i}" for i in range(321))


def _rc(readme):
    return SimpleNamespace(
        prompts={"presentation_planning": SimpleNamespace(manifest=None)},
        entry=make_entry(),
        facts=make_facts(),
        investigation={},
        dispositions={},
        context=None,
        store=SimpleNamespace(get=lambda key: PLAN),
        readme=readme,
        units={},
    )


def _drive(monkeypatch, defect, readme):
    seen = {}
    monkeypatch.setattr(loop, "planning_packet", lambda *a, **k: {})
    monkeypatch.setattr(loop, "planning_schema", lambda *a, **k: {})
    monkeypatch.setattr(loop, "request_hash", lambda *a, **k: "k")
    monkeypatch.setattr(loop, "effective_model", lambda *a, **k: "m")
    monkeypatch.setattr(loop, "refuse_noop", lambda original, checks: checks)

    def fake_call(rc, d, loaded, original, checks, **kwargs):
        seen.update(kwargs)
        return "outcome"

    monkeypatch.setattr(loop, "_targeted_call", fake_call)
    monkeypatch.setattr(loop, "_accept", lambda *a, **k: True)
    repairs = SimpleNamespace(record=lambda *a, **k: None)
    loop._repair_plan(_rc(readme), defect, repairs)
    return seen


def _defect(label):
    return SimpleNamespace(label=label, stage="S5", fingerprint="f", reason=None)


def test_a_bc07_defect_carries_the_measured_lever_costs(monkeypatch):
    seen = _drive(monkeypatch, _defect("BC-07"), BIG_README)
    hint = seen["visible_line_budget"]
    assert hint["visible_lines_over_budget"] == 21
    assert set(hint["optional_plan_fields_and_their_visible_line_cost_if_cleared"]) == {
        "flagship_example_id"
    }


def test_another_defect_gets_no_budget_hint(monkeypatch):
    assert _drive(monkeypatch, _defect("BC-02"), BIG_README).get("visible_line_budget") is None


def test_a_bc07_defect_without_a_rendered_readme_gets_no_hint(monkeypatch):
    assert _drive(monkeypatch, _defect("BC-07"), "").get("visible_line_budget") is None


# --- measured lever cost -----------------------------------------------------------------------
# The formula said 17 visible lines for Font's flagship example; re-rendering with the field
# cleared saves 43. A hint that understates every lever tells the model no single field can close
# the overage, so the cost is MEASURED by a re-render when one is possible.


def test_a_measured_cost_replaces_the_formula_cost():
    from repo_presenter.readme.repair.targeted import visible_line_budget_hint

    hint = visible_line_budget_hint(
        PLAN, make_facts(), 321, 300, measure=lambda field: {"flagship_example_id": 43}.get(field)
    )
    assert hint["optional_plan_fields_and_their_visible_line_cost_if_cleared"] == {
        "flagship_example_id": 43
    }


def test_an_unmeasurable_field_falls_back_to_the_formula_cost():
    from repo_presenter.readme.repair.targeted import visible_line_budget_hint

    formula = visible_line_budget_hint(PLAN, make_facts(), 321, 300)
    unmeasured = visible_line_budget_hint(PLAN, make_facts(), 321, 300, measure=lambda f: None)
    assert unmeasured == formula


def test_the_loop_measures_by_rerendering_with_the_field_cleared(monkeypatch):
    rendered = []

    def fake_render(entry, facts, plan, units, dispositions):
        rendered.append(dict(plan))
        return "\n".join("x" for _ in range(321 if plan.get("flagship_example_id") else 278))

    monkeypatch.setattr(loop, "render_readme", fake_render)
    rc = _rc(BIG_README)
    rc.units = {"units": []}
    measure = loop._measure_by_render(rc, PLAN, 321)
    assert measure("flagship_example_id") == 43
    assert rendered[-1]["flagship_example_id"] is None
    # the original plan is never mutated
    assert PLAN["flagship_example_id"] == "example:001"


def test_the_measure_is_none_when_rendering_is_impossible(monkeypatch):
    def broken(*a, **k):
        raise KeyError("a unit for the cleared slot")

    monkeypatch.setattr(loop, "render_readme", broken)
    rc = _rc(BIG_README)
    rc.units = {"units": []}
    assert loop._measure_by_render(rc, PLAN, 321)("flagship_example_id") is None


def test_the_measure_is_unavailable_without_the_authored_units():
    rc = _rc(BIG_README)
    rc.units = {}
    assert loop._measure_by_render(rc, PLAN, 321) is None
