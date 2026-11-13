"""present.yml as the autonomous engine (owner ruling R37, 2026-11-13): the schedule-only cohort
job plans, funds and dispatches each fire; every present run reserves its budget before its lanes
and records its measured spend after them, success or failure. Structural, like
tests/test_present_lanes.py: a hosted run is what proves it live."""

from __future__ import annotations

import json
from typing import Any

from tests.test_present import TOOLCHAIN_ACTIONS, _load_workflow
from tests.test_present_lanes import present_steps


def _cohort(workflow: dict[str, Any]) -> dict[str, Any]:
    return workflow["jobs"]["cohort"]


def _step(steps: list[dict[str, Any]], prefix: str) -> tuple[int, dict[str, Any]]:
    return next((i, s) for i, s in enumerate(steps) if str(s.get("name", "")).startswith(prefix))


def test_the_schedule_is_hourly() -> None:
    workflow = _load_workflow()
    triggers = workflow["on"] if "on" in workflow else workflow[True]
    assert [c["cron"] for c in triggers["schedule"]] == ["17 * * * *"]


def test_the_cohort_job_runs_only_as_the_planner_with_least_privilege_and_no_secret() -> None:
    """The planner runs on the schedule (heartbeat) or on a no-target call from main
    (cohort-chain.yml, run-request `cohort`); never on a dispatch or a targeted call."""
    workflow = _load_workflow()
    cohort = _cohort(workflow)
    assert cohort["if"] == (
        "github.event_name == 'schedule' || "
        "(github.event_name == 'workflow_run' && inputs.repository == '')"
    )
    assert cohort["concurrency"] == {"group": "present-cohort-planner", "cancel-in-progress": False}
    assert cohort["permissions"] == {"contents": "write", "actions": "write"}
    rendered = json.dumps(cohort)
    assert "secrets." not in rendered and "GPT_OSS" not in rendered
    assert "--stage" not in rendered, "the cohort job presents nothing itself"
    assert not any(
        name in str(step.get("uses", "")) for step in cohort["steps"] for name in TOOLCHAIN_ACTIONS
    ), "the cohort job runs no repository code"
    assert all(
        step["with"].get("persist-credentials") is False
        for step in cohort["steps"] if "actions/checkout" in str(step.get("uses", ""))
    )
    # the facts job (and so the present job) never runs on a schedule event or a no-target call
    assert workflow["jobs"]["facts"]["if"] == "github.event_name != 'schedule' && inputs.repository != ''"


def test_the_cohort_plans_through_the_gate_then_funds_then_dispatches_then_reports() -> None:
    steps = _cohort(_load_workflow())["steps"]
    plan_i, plan = _step(steps, "Plan")
    reserve_i, reserve = _step(steps, "Reserve")
    dispatch_i, dispatch = _step(steps, "Dispatch")
    report_i, report = _step(steps, "Report")
    assert plan_i < reserve_i < dispatch_i < report_i
    assert "scheduled_execution_gate.py --max 6" in plan["run"] and "--plan" in plan["run"]
    assert "budget reserve-cohort" in reserve["run"]
    for step in (reserve, dispatch):
        assert step["if"] == "steps.plan.outputs.authorized == 'true'"
    assert "gh workflow run present.yml" in dispatch["run"]
    for flag in ("repository=", "ecosystem=", "lane=", "dispatch_id="):
        assert f"-f {flag}" in dispatch["run"]
    assert 'if run.get("reservation")' in dispatch["run"], "an unfunded run is never dispatched"
    assert "budget release" in dispatch["run"], "a failed dispatch releases its reservation"
    assert report["if"] == "always()" and "GITHUB_STEP_SUMMARY" in report["run"]
    assert "render_summary" in report["run"]


def test_dispatched_runs_carry_a_dispatch_id_and_skip_the_sandbox_proof() -> None:
    workflow = _load_workflow()
    triggers = workflow["on"] if "on" in workflow else workflow[True]
    dispatch_id = triggers["workflow_dispatch"]["inputs"]["dispatch_id"]
    assert dispatch_id["required"] is False and dispatch_id["default"] == ""
    assert "dispatch_id" not in triggers["workflow_call"]["inputs"]
    assert "inputs.dispatch_id == ''" in workflow["jobs"]["sandbox-execute"]["if"]


def test_every_present_run_reserves_before_its_lanes_and_settles_after_them() -> None:
    workflow = _load_workflow()
    present = workflow["jobs"]["present"]
    assert "needs.facts.result != 'skipped'" in present["if"] and "!cancelled()" in present["if"]
    steps = present_steps(workflow)
    names = [s.get("name") for s in steps]
    reserve_i, reserve = _step(steps, "Reserve this run's provider budget")
    settle_i, settle = _step(steps, "Record this run's measured spend")
    lane_r = names.index("Present (Lane R)")
    lane_l = names.index("Present (Lane L)")
    restore = next(i for i, s in enumerate(steps) if "cache/restore" in str(s.get("uses", "")))
    save = next(i for i, s in enumerate(steps) if "cache/save" in str(s.get("uses", "")))
    assert restore < reserve_i < lane_r < lane_l < settle_i < save, (
        "the baseline must include the restored call ledgers, and the spend must be recorded "
        "before anything else can fail"
    )
    assert "budget reserve" in reserve["run"] and "steps.budget.outputs.id" in reserve["run"]
    assert "steps.fetch_facts.outcome == 'success'" in reserve["if"]
    assert settle["if"] == "always()"
    for needle in ("budget settle", "steps.lane_r.outcome", "steps.lane_l.outcome",
                   "needs.facts.result", "needs.facts.outputs.source_revision"):
        assert needle in settle["run"], needle
    for step in (reserve, settle):
        assert "REPOSITORY_PRESENTER_STATE_TOKEN" in step["env"]
        assert "secrets." not in json.dumps(step)
    budget_id = next(s for s in steps if s.get("id") == "budget")
    assert "inputs.dispatch_id" in budget_id["run"] and "github.run_attempt" in budget_id["run"]


def test_the_facts_job_publishes_the_pinned_revision_for_the_ledger() -> None:
    facts = _load_workflow()["jobs"]["facts"]
    assert "steps.digest.outputs.source_revision" in facts["outputs"]["source_revision"]
    digest = next(s for s in facts["steps"] if s.get("id") == "digest")
    assert "facts-manifest.json" in digest["run"]
