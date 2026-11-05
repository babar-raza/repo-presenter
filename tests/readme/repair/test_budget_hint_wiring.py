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


# --- a BC-07 repair is only accepted if it actually fits the budget ----------------------------
# The model was asked to fix a 321-line README, returned a plan that changed unrelated lists, and
# the repair was recorded "repaired" while the defect stood: one attempt spent on nothing. The
# plan checks only refused a no-op. A budget repair is now judged by what it renders.


def _checks_for(monkeypatch, rendered_visible):
    captured = {}
    monkeypatch.setattr(loop, "planning_packet", lambda *a, **k: {})
    monkeypatch.setattr(loop, "planning_schema", lambda *a, **k: {})
    monkeypatch.setattr(loop, "request_hash", lambda *a, **k: "k")
    monkeypatch.setattr(loop, "effective_model", lambda *a, **k: "m")
    monkeypatch.setattr(loop, "refuse_noop", lambda original, checks: checks)
    monkeypatch.setattr(loop, "plan_checks", lambda revised, **k: [])
    monkeypatch.setattr(
        loop,
        "render_readme",
        lambda entry, facts, plan, units, dispositions: "\n".join(["x"] * rendered_visible(plan)),
    )

    def fake_call(rc, d, loaded, original, checks, **kwargs):
        captured["checks"] = checks
        captured["hint"] = kwargs.get("visible_line_budget")
        return "outcome"

    monkeypatch.setattr(loop, "_targeted_call", fake_call)
    monkeypatch.setattr(loop, "_accept", lambda *a, **k: True)
    rc = _rc(BIG_README)
    rc.units = {"units": []}
    loop._repair_plan(rc, _defect("BC-07"), SimpleNamespace(record=lambda *a, **k: None))
    return captured["checks"]


def _lines(plan):
    return 321 if plan.get("flagship_example_id") else 278


def test_a_revision_that_still_exceeds_the_budget_is_rejected_with_the_levers_named(monkeypatch):
    checks = _checks_for(monkeypatch, _lines)
    errors = checks(dict(PLAN, unrelated="edit"))
    assert errors and "321" in errors[0] and "300" in errors[0]
    assert "flagship_example_id" in errors[0]


def test_a_revision_that_fits_the_budget_is_accepted(monkeypatch):
    checks = _checks_for(monkeypatch, _lines)
    assert checks(dict(PLAN, flagship_example_id=None)) == []


def test_a_revision_that_cannot_be_rendered_is_not_judged_by_the_budget(monkeypatch):
    def broken(plan):
        raise KeyError("slot")

    checks = _checks_for(monkeypatch, _lines)
    monkeypatch.setattr(loop, "render_readme", lambda *a, **k: broken(a[2]))
    assert checks(dict(PLAN)) == []


def test_a_non_budget_defect_is_judged_only_by_the_plan_checks(monkeypatch):
    monkeypatch.setattr(loop, "planning_packet", lambda *a, **k: {})
    monkeypatch.setattr(loop, "planning_schema", lambda *a, **k: {})
    monkeypatch.setattr(loop, "request_hash", lambda *a, **k: "k")
    monkeypatch.setattr(loop, "effective_model", lambda *a, **k: "m")
    monkeypatch.setattr(loop, "refuse_noop", lambda original, checks: checks)
    marker = ["plan-check-error"]
    monkeypatch.setattr(loop, "plan_checks", lambda revised, **k: marker)
    seen = {}
    monkeypatch.setattr(
        loop, "_targeted_call", lambda rc, d, l, o, checks, **kw: seen.update(checks=checks) or "o"
    )
    monkeypatch.setattr(loop, "_accept", lambda *a, **k: True)
    rc = _rc(BIG_README)
    rc.units = {"units": []}
    loop._repair_plan(rc, _defect("BC-02"), SimpleNamespace(record=lambda *a, **k: None))
    assert seen["checks"]({}) == marker
