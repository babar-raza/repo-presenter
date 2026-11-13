"""The self-continuing engine (owner ruling R37, 2026-11-13: the loop runs itself on GitHub Actions
and must not depend on cron punctuality). present.yml's schedule is the heartbeat; cohort-chain.yml
re-runs the planner when a dispatched run or an M9 round completes; run-request `cohort` is the
supervisor's override. Bounded: one planner at a time, one cohort in flight at a time, and an idle
portfolio ends the chain. Structural and zero-call, like tests/test_present_cohort.py: whether
GitHub delivers each workflow_run event is what only a hosted run proves."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import run_request as rr  # noqa: E402
from scripts import scheduled_execution_gate as gate  # noqa: E402
from scripts.select_scheduled_cohort import COHORT_ID_PREFIX, plan_cohort, render_summary  # noqa: E402

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)


def _load(name: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _on(doc: dict[str, Any]) -> dict[str, Any]:
    return doc["on"] if "on" in doc else doc[True]


# --- a tiny evaluator for the job conditions used here (==, !=, &&, ||, parentheses, literals) ---

_PATH = re.compile(r"\b(?:github|inputs)(?:\.[A-Za-z_][A-Za-z0-9_-]*)+")


def _evaluate(expression: str, context: dict[str, Any]) -> bool:
    def lookup(match: re.Match[str]) -> str:
        value: Any = context
        for part in match.group(0).split("."):
            value = value.get(part) if isinstance(value, dict) else None
        return repr("" if value is None else value)

    python = _PATH.sub(lookup, expression).replace("&&", " and ").replace("||", " or ")
    assert "!" not in python.replace("!=", ""), f"unsupported operator in {expression!r}"
    return bool(eval(python, {"__builtins__": {}}, {}))  # noqa: S307 -- literals only, built above


def _ctx(
    event: str, repository: str = "", run: dict[str, str] | None = None, ref_name: str = "main", dispatch_id: str = ""
) -> dict[str, Any]:
    return {
        "github": {"event_name": event, "ref_name": ref_name, "event": {"workflow_run": run or {}}},
        "inputs": {"repository": repository, "dispatch_id": dispatch_id},
    }


# --- present.yml: a no-target call runs only the planner ---------------------------------------


@pytest.mark.parametrize(
    ("context", "cohort", "facts"),
    [
        (_ctx("schedule"), True, False),  # the heartbeat
        (_ctx("workflow_run"), True, False),  # cohort-chain.yml / run-request `cohort` (no target)
        (_ctx("workflow_run", "o/a"), False, True),  # run-request `present` (a target)
        (_ctx("workflow_dispatch", "o/a"), False, True),  # a run the planner dispatched, or by hand
        (_ctx("workflow_dispatch"), True, False),  # cohort-chain.yml requested by a finished worker (BL-077)
    ],
)
def test_present_runs_the_planner_or_the_transaction_never_both(context, cohort, facts) -> None:
    jobs = _load("present.yml")["jobs"]
    assert _evaluate(jobs["cohort"]["if"], context) is cohort
    assert _evaluate(jobs["facts"]["if"], context) is facts


def test_a_no_target_call_cannot_fail_at_startup_and_passes_no_secret() -> None:
    inputs = _on(_load("present.yml"))["workflow_call"]["inputs"]
    assert set(inputs) == {"repository", "ecosystem", "lane"}
    for spec in inputs.values():
        assert spec["required"] is False and spec["default"] == ""
    cohort = _load("present.yml")["jobs"]["cohort"]
    assert "secrets." not in json.dumps(cohort)


def test_one_planner_at_a_time_whoever_started_it() -> None:
    cohort = _load("present.yml")["jobs"]["cohort"]
    # job-level, so it binds the schedule fire and every caller of present.yml alike
    assert cohort["concurrency"] == {"group": "present-cohort-planner", "cancel-in-progress": False}
    dispatch = next(s for s in cohort["steps"] if str(s.get("name", "")).startswith("Dispatch"))
    # under workflow_run (chain, override) github.ref is the default branch, so runs go to main
    assert '--ref "${{ github.ref_name }}"' in dispatch["run"]


# --- cohort-chain.yml ---------------------------------------------------------------------------


def test_the_chain_reacts_to_finished_work_on_main_and_never_to_itself() -> None:
    doc = _load("cohort-chain.yml")
    on = _on(doc)
    assert set(on) == {"workflow_run", "workflow_dispatch"}, (
        "no schedule/push of its own: present.yml's schedule is the heartbeat; workflow_dispatch is the "
        "request a finished planner-dispatched run makes (BL-077: GITHUB_TOKEN runs never fire workflow_run)"
    )
    assert on["workflow_dispatch"] in (None, {}), "a request carries no input"
    run = on["workflow_run"]
    assert run["types"] == ["completed"] and run["branches"] == ["main"]
    assert set(run["workflows"]) == {"present", "audit-seed", "acceptance-write", "recertify"}
    assert doc["name"] not in run["workflows"], "a chain link must never trigger itself"
    assert doc["permissions"] == {"contents": "read"}


def test_the_chain_only_calls_the_planner_with_least_privilege() -> None:
    job = _load("cohort-chain.yml")["jobs"]["cohort"]
    assert job["uses"] == "./.github/workflows/present.yml"
    assert "with" not in job, "a no-target call: only the cohort job runs"
    assert "secrets" not in job, "the planner holds no secret"
    assert job["permissions"] == {"contents": "write", "actions": "write"}


@pytest.mark.parametrize(
    ("run", "fires"),
    [
        ({"name": "present", "event": "workflow_dispatch", "head_branch": "main"}, True),
        ({"name": "present", "event": "schedule", "head_branch": "main"}, False),  # a planner fire
        ({"name": "present", "event": "workflow_dispatch", "head_branch": "feature"}, False),
        ({"name": "audit-seed", "event": "schedule", "head_branch": "main"}, True),
        ({"name": "audit-seed", "event": "workflow_dispatch", "head_branch": "main"}, True),
        ({"name": "acceptance-write", "event": "workflow_dispatch", "head_branch": "main"}, True),
        # R41 (BL-060): a portfolio re-certification after a pipeline change queues what no longer certifies
        ({"name": "recertify", "event": "push", "head_branch": "main"}, True),
        ({"name": "recertify", "event": "workflow_dispatch", "head_branch": "main"}, True),
        ({"name": "recertify", "event": "workflow_dispatch", "head_branch": "feature"}, False),
    ],
)
def test_the_chain_fires_on_worker_and_m9_completions_only(run, fires) -> None:
    job = _load("cohort-chain.yml")["jobs"]["cohort"]
    assert _evaluate(job["if"], _ctx("workflow_run", run=run)) is fires


@pytest.mark.parametrize(("ref_name", "fires"), [("main", True), ("feature", False)])
def test_a_requested_chain_link_runs_only_from_main(ref_name, fires) -> None:
    job = _load("cohort-chain.yml")["jobs"]["cohort"]
    assert _evaluate(job["if"], _ctx("workflow_dispatch", ref_name=ref_name)) is fires


# --- run-request `cohort` -----------------------------------------------------------------------


def test_a_cohort_request_validates_and_takes_no_other_field() -> None:
    assert rr.validate({"job": "cohort"}, [], [rr.REQUEST_FILE], True) == {
        "job": "cohort", "repository": "", "ecosystem": "", "lane": "",
    }
    with pytest.raises(rr.RequestError, match="no other field"):
        rr.validate({"job": "cohort", "repository": "o/a"}, [], [rr.REQUEST_FILE], True)
    with pytest.raises(rr.RequestError, match="not based on the current main"):
        rr.validate({"job": "cohort"}, [], [rr.REQUEST_FILE], False)


def test_the_executor_calls_the_planner_without_a_target_or_a_secret() -> None:
    job = _load("run-request-execute.yml")["jobs"]["cohort"]
    assert job["needs"] == "validate" and job["if"] == "needs.validate.outputs.job == 'cohort'"
    assert job["uses"] == "./.github/workflows/present.yml"
    assert "with" not in job and "secrets" not in job
    assert job["permissions"] == {"contents": "write", "actions": "write"}


# --- one cohort in flight at a time (scripts/select_scheduled_cohort.py) -----------------------


class _Entry:
    def __init__(self, repository: str) -> None:
        self.repository, self.ecosystem, self.active = repository, "python", True


def _reserve(rid: str, repository: str, hours: float = 1) -> dict[str, Any]:
    return {"kind": "reserve", "id": rid, "repository": repository, "lanes": ["R", "L"], "batch": "b",
            "calls": 10, "tokens": 10, "epoch": 2, "at": (NOW - timedelta(hours=hours)).isoformat()}


def _plan(*ledger: dict[str, Any]) -> dict[str, Any]:
    entries = {name: _Entry(name) for name in ("o/a", "o/b", "o/c")}
    return plan_cohort(
        entries=entries, authorized_repos=set(entries), certifications={},
        ledger={"entries": list(ledger)}, terminals=[], code="code", head=lambda repo: "b" * 40, now=NOW,
    )


def test_a_cohort_in_flight_holds_the_planner_and_queues_the_work() -> None:
    plan = _plan(_reserve(f"{COHORT_ID_PREFIX}9-1-1", "o/a"))
    assert plan["runs"] == []
    assert plan["held"] == {"in_flight_cells": 2, "reservations": ["cohort-9-1-1"]}
    assert {(q["repository"], q["lane"]) for q in plan["queued"]} == {
        ("o/b", "R"), ("o/b", "L"), ("o/c", "R"), ("o/c", "L"),
    }
    assert "**Held:**" in render_summary(plan)


def test_a_rerun_of_a_dispatched_run_still_holds() -> None:
    assert _plan(_reserve("cohort-9-1-1-a2", "o/a"))["held"]["in_flight_cells"] == 2


def test_the_last_settle_of_a_cohort_releases_the_hold() -> None:
    settle = {"kind": "settle", "id": "cohort-9-1-1", "repository": "o/a", "outcomes": {"R": "failure"},
              "sealed": [], "code": "old", "source_revision": "b" * 40, "at": NOW.isoformat(), "epoch": 2}
    plan = _plan(_reserve("cohort-9-1-1", "o/a"), settle)
    assert plan["held"] is None and plan["runs"]


def test_a_manual_run_or_an_expired_reservation_never_holds_the_engine() -> None:
    manual = _plan(_reserve("run-77-a1", "o/a"))
    assert manual["held"] is None
    assert [r["repository"] for r in manual["runs"]] == ["o/b", "o/c"]  # its own cell still skipped
    assert _plan(_reserve("cohort-9-1-1", "o/a", hours=7))["held"] is None  # past the TTL


def test_an_idle_portfolio_plans_nothing_so_the_chain_ends(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gate, "evaluate_predicates", lambda **_: [])
    monkeypatch.setattr(gate, "load_policy", lambda _: {"authorized_repositories": ["o/a"]})
    idle = {"runs": [], "skipped": [{"repository": "o/a", "lane": "R", "category": "certified",
                                     "reason": "x"}], "diagnose": [], "queued": [], "certified": {},
            "held": None}
    monkeypatch.setattr(gate, "build_plan", lambda **_: idle)
    assert gate.main([]) == 0
    out = capsys.readouterr().out
    assert "authorized=false" in out and "runs=0" in out and "no authorized cell needs work" in out


def test_a_held_fire_is_an_evidenced_no_op(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gate, "evaluate_predicates", lambda **_: [])
    monkeypatch.setattr(gate, "load_policy", lambda _: {"authorized_repositories": ["o/a"]})
    held = _plan(_reserve("cohort-9-1-1", "o/a"))
    monkeypatch.setattr(gate, "build_plan", lambda **_: held)
    assert gate.main([]) == 0
    out = capsys.readouterr().out
    assert "authorized=false" in out and "runs=0" in out
    assert "reason=held: the previous cohort is still in flight (2 cells, cohort-9-1-1)" in out
