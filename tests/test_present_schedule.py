"""2026-11-04 (TC-012, follow-up directive §10, and the P0 follow-up directive §2): a naive
`schedule:` trigger does not work -- `inputs.*` is only populated for `workflow_dispatch`, so a
scheduled run would otherwise launch with an empty repository/ecosystem. Worse, nothing watches
a schedule fire, so it must fail closed by itself rather than rely on a human noticing a bad
pick. These tests assert the real fix structurally, the same way tests/test_present_lanes.py
already asserts the lane-independence structure, rather than trusting a live hosted run (which
this environment cannot trigger)."""
from __future__ import annotations

import json
from typing import Any

from tests.test_present import WORKFLOW, _load_workflow
from tests.test_present_lanes import present_steps


def facts_steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return workflow["jobs"]["facts"]["steps"]


def test_a_schedule_trigger_exists_with_a_real_cron():
    workflow = _load_workflow()
    triggers = workflow["on"] if "on" in workflow else workflow[True]
    assert "schedule" in triggers, "no schedule: trigger -- TC-012 is not actually done"
    crons = triggers["schedule"]
    assert isinstance(crons, list) and len(crons) >= 1
    assert all("cron" in c and isinstance(c["cron"], str) and c["cron"].strip() for c in crons)


def test_the_facts_job_resolves_a_real_target_for_either_trigger():
    workflow = _load_workflow()
    steps = facts_steps(workflow)
    target_steps = [s for s in steps if s.get("id") == "target"]
    assert len(target_steps) == 1, "exactly one target-resolution step must exist"
    run = str(target_steps[0]["run"])
    assert "github.event_name" in run and "schedule" in run, (
        "the step must actually branch on trigger type, not just exist"
    )
    assert "scheduled_execution_gate.py" in run, (
        "the scheduled branch must call the real authorization-gated selector, not the bare "
        "cohort picker (which enforces no predicate at all) or a placeholder"
    )
    assert "inputs.repository" in run and "inputs.ecosystem" in run, (
        "the manual-dispatch branch must still pass inputs through unchanged"
    )
    assert 'echo "authorized=true"' in run, (
        "a manual dispatch is its own explicit authorization and must set authorized=true "
        "itself, never defer to the gate script"
    )

    outputs = workflow["jobs"]["facts"].get("outputs", {})
    assert "steps.target.outputs.repository" in str(outputs.get("repository", "")), (
        "facts job must expose the resolved repository as its own output for the present job"
    )
    assert "steps.target.outputs.ecosystem" in str(outputs.get("ecosystem", "")), (
        "facts job must expose the resolved ecosystem as its own output for the present job"
    )
    assert "steps.target.outputs.authorized" in str(outputs.get("authorized", "")), (
        "facts job must expose the gate's authorized flag so the present job can enforce it too"
    )


def test_every_provider_consuming_or_repository_code_step_is_gated_on_authorization():
    """The actual P0 enforcement boundary: every step that spends a provider call, runs
    repository code, or could leak a durable-state write must refuse to run when the scheduled
    gate said authorized=false. Checking taskcard status is not enough -- this must be true of
    the workflow file itself."""
    workflow = _load_workflow()

    build_facts = next(s for s in facts_steps(workflow) if s.get("name") == "Build the facts")
    assert "steps.target.outputs.authorized == 'true'" in str(build_facts.get("if", "")), (
        "an unauthorized scheduled run must never execute the upstream repository's own code"
    )

    steps = present_steps(workflow)
    fetch_facts = next(s for s in steps if s.get("id") == "fetch_facts")
    assert "needs.facts.outputs.authorized == 'true'" in str(fetch_facts.get("if", ""))

    for name in ("Present (Lane R)", "Present (Lane L)"):
        step = next(s for s in steps if s.get("name") == name)
        assert "needs.facts.outputs.authorized == 'true'" in str(step.get("if", "")), (
            f"{name} must refuse to spend a provider call or write durable state when "
            "the scheduled run was not authorized"
        )


def test_no_permissive_negative_comparison_remains_anywhere_in_the_workflow():
    """2026-11-04 supervisor-directive correction: `authorized != 'false'` is a PERMISSIVE
    comparison -- an absent, empty, or malformed output (anything other than the literal string
    'false') would satisfy it and run anyway. Every privileged/provider-consuming/repository-
    code step must instead require the explicit POSITIVE match `authorized == 'true'`, so an
    absent, empty, or malformed authorization output fails closed by construction, not by
    coincidence."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "!= 'false'" not in text
    assert text.count("authorized == 'true'") >= 7  # one per gated step, see the test above


def test_a_blocked_schedule_still_produces_a_successful_no_op_not_a_red_job():
    """directive: 'An empty cohort must produce a successful, explicitly evidenced no-op, not an
    unexplained failed run.' The gate script itself must never be the thing that fails the job --
    only the provider-consuming steps are conditionally skipped."""
    workflow = _load_workflow()
    target_step = next(s for s in facts_steps(workflow) if s.get("id") == "target")
    run = str(target_step["run"])
    # the schedule branch's only command is the gate script -- no `exit 1` / `|| exit` escape
    # that would turn "nothing authorized" into a failed step.
    schedule_branch = run.split('"schedule" ]; then', 1)[1].split("else", 1)[0]
    assert "exit 1" not in schedule_branch and "|| exit" not in schedule_branch


def test_target_resolution_runs_before_any_ecosystem_conditional_toolchain_step():
    steps = facts_steps(_load_workflow())
    target_idx = next(i for i, s in enumerate(steps) if s.get("id") == "target")
    for i, s in enumerate(steps):
        if "steps.target.outputs.ecosystem" in str(s.get("if", "")):
            assert i > target_idx, f"{s.get('name')!r} reads steps.target before it is set"


def test_target_resolution_needs_no_secret_and_stays_in_the_unprivileged_facts_job():
    """The selector reads data/registry.json and the public durable-state refs -- contents:
    read is sufficient; it must never need a secret, or it would violate the exact boundary
    assert_facts_job_is_unprivileged already enforces."""
    steps = facts_steps(_load_workflow())
    target_step = next(s for s in steps if s.get("id") == "target")
    assert "secrets." not in json.dumps(target_step)


def test_the_present_job_reads_the_resolved_target_from_the_facts_job_not_raw_inputs():
    """The slug step and both lane steps must read needs.facts.outputs.* so a scheduled run
    (where inputs.repository/ecosystem are empty) actually gets a real target -- this is the
    crux of the fix, not cosmetic."""
    steps = present_steps(_load_workflow())
    slug_step = next(s for s in steps if s.get("id") == "slug")
    assert "needs.facts.outputs.repository" in str(slug_step["env"]["INPUT_REPOSITORY"])

    for name in ("Present (Lane R)", "Present (Lane L)"):
        step = next(s for s in steps if s.get("name") == name)
        env = step["env"]
        assert "needs.facts.outputs.repository" in str(env["INPUT_REPOSITORY"]), name
        assert "needs.facts.outputs.ecosystem" in str(env["INPUT_ECOSYSTEM"]), name
def test_deliberately_failing_proof(): assert False
