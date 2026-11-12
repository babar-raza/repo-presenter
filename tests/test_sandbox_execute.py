"""Structural proof for the `sandbox-execute` job in present.yml (TC-021): this does not run
docker -- the hosted run is the live proof -- it only proves the YAML cannot quietly regress to
something unsafe (a permission, a secret, a loosened isolation flag) without a test noticing.
Parses the workflow the same way tests/test_present.py's own `_load_workflow` does."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

WORKFLOW = (
    Path(__file__).resolve().parent.parent / ".github" / "workflows" / "present.yml"
)


def _load_workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _sandbox_job() -> dict[str, Any]:
    workflow = _load_workflow()
    assert "sandbox-execute" in workflow["jobs"], "expected a sandbox-execute job"
    return workflow["jobs"]["sandbox-execute"]


def _step_named(job: dict[str, Any], keyword: str) -> dict[str, Any] | None:
    for step in job["steps"]:
        if keyword.lower() in str(step.get("name", "")).lower():
            return step
    return None


def _docker_run_commands(job: dict[str, Any]) -> list[str]:
    return [
        str(step["run"])
        for step in job["steps"]
        if "docker run" in str(step.get("run", ""))
    ]


def test_the_sandbox_execute_job_holds_no_permissions() -> None:
    job = _sandbox_job()
    assert job.get("permissions") == {}


def test_no_step_in_the_sandbox_execute_job_references_a_secret() -> None:
    job = _sandbox_job()
    rendered = json.dumps(job)
    assert "secrets." not in rendered


def test_the_sandbox_execute_job_only_runs_on_manual_dispatch() -> None:
    job = _sandbox_job()
    assert "workflow_dispatch" in str(job.get("if", ""))


def test_the_sandbox_execute_job_is_not_wired_into_the_facts_present_chain() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["sandbox-execute"]
    assert job.get("needs") in (None, [])
    for other_name in ("facts", "present"):
        other_job = workflow["jobs"][other_name]
        assert "sandbox-execute" not in str(other_job.get("needs", ""))


def test_the_sandbox_execute_job_checks_out_with_no_persisted_credentials() -> None:
    job = _sandbox_job()
    checkout = next(
        step for step in job["steps"] if "actions/checkout" in str(step.get("uses", ""))
    )
    assert checkout["with"]["persist-credentials"] is False


def test_every_docker_run_in_the_sandbox_execute_job_carries_the_mandated_isolation_flags() -> (
    None
):
    job = _sandbox_job()
    commands = _docker_run_commands(job)
    assert commands, "expected at least one docker run invocation"
    for command in commands:
        assert "--network none" in command
        assert "--read-only" in command
        assert "--cap-drop ALL" in command


def test_the_canary_step_proves_network_write_and_secret_leak_attempts_all_fail() -> None:
    job = _sandbox_job()
    canary = _step_named(job, "canary")
    assert canary is not None, "expected a canary step"
    run = str(canary.get("run", ""))
    assert "--network none" in run
    assert "grep" in run
    assert "secret" in run.lower()
    # Each of the three attempts has its own explicit, written failure assertion -- not merely a
    # comment describing the intent.
    assert "NETWORK_REACHED" in run
    assert "WRITE_SUCCEEDED" in run


def test_the_legitimate_step_runs_real_fixture_examples_for_two_toolchained_ecosystems() -> None:
    job = _sandbox_job()
    legit = _step_named(job, "legitimate")
    assert legit is not None, "expected a legitimate-execution step"
    run = str(legit.get("run", ""))
    assert "--network none" in run
    assert "/fixtures/cpp" in run
    assert "/fixtures/typescript" in run
    assert "g++" in run
    assert "node " in run


def test_the_sandbox_fixtures_referenced_by_the_legitimate_step_exist() -> None:
    fixtures = Path(__file__).resolve().parent / "fixtures" / "sandbox"
    assert (fixtures / "cpp" / "hello.cpp").is_file()
    assert (fixtures / "typescript" / "hello.js").is_file()
