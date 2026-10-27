"""The hosted workflow runs the chosen lane(s) without loosening the facts/isolation split
(plans/PLAN_lane_l_hosted.md L10). The structure test of ``tests/test_present.py`` still applies
unchanged; this file adds what the lane input must guarantee:

* one ``lane`` input with R, L and both; the facts job knows nothing of lanes;
* a step per lane, each passing its own ``--lane`` flag, each guarded by the input;
* Lane L can run after Lane R failed (a status function), and not without the facts;
* both lanes' call stores are persisted with the sealed bundles (the zero-call rerun needs them);
* the credentialed Lane L step is in the present job, where the secrets are, and never in the facts
  job, which executes repository code.
"""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from tests.test_present import (
    _load_workflow,
    assert_facts_job_is_unprivileged,
    assert_present_job_runs_no_repository_code,
)


def triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    """YAML 1.1 reads the bare key ``on`` as the boolean True."""
    return workflow["on"] if "on" in workflow else workflow[True]


def present_steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return workflow["jobs"]["present"]["steps"]


def lane_steps(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for step in present_steps(workflow):
        run = str(step.get("run", ""))
        if "repo_presenter.present" in run and "--stage cascade" in run:
            lane = run.split("--lane ", 1)[1].split()[0]
            assert lane not in found, f"two steps run Lane {lane}"
            found[lane] = step
    return found


def assert_lanes_are_independent(workflow: dict[str, Any]) -> None:
    """The guarantees the lane input must keep; raises AssertionError naming the broken one."""
    inputs = triggers(workflow)["workflow_dispatch"]["inputs"]
    lane_input = inputs["lane"]
    assert lane_input["type"] == "choice" and set(lane_input["options"]) == {
        "R",
        "L",
        "both",
    }
    assert lane_input["default"] in lane_input["options"]

    steps = lane_steps(workflow)
    assert set(steps) == {"R", "L"}, "each lane needs its own step"
    condition_r = str(steps["R"].get("if", ""))
    condition_l = str(steps["L"].get("if", ""))
    assert "inputs.lane != 'L'" in condition_r, "Lane R must run for R and both"
    assert "inputs.lane != 'R'" in condition_l, "Lane L must run for L and both"
    assert "!cancelled()" in condition_l or "always()" in condition_l, (
        "Lane L must run even when Lane R failed: neither lane is measured by the other's delivery"
    )
    assert "steps.fetch_facts.outcome == 'success'" in condition_l, (
        "Lane L needs the facts: it must not run when the facts could not be fetched"
    )

    persisted = [
        step for step in present_steps(workflow) if "cache" in str(step.get("uses", ""))
    ]
    assert len(persisted) == 2  # one restore, one save
    for step in persisted:
        paths = str(step["with"]["path"])
        assert (
            "candidates/${{ steps.slug.outputs.slug }}" in paths
        )  # both lanes' bundles
        assert ".present-work/cascade/llm_cache" in paths, "Lane R's call store"
        assert ".present-work/lane-l/llm_cache" in paths, "Lane L's call store"
    assert any(step.get("id") == "fetch_facts" for step in present_steps(workflow))

    facts_job = json.dumps(workflow["jobs"]["facts"])
    assert "--lane" not in facts_job and "Lane" not in facts_job, (
        "facts are shared by both lanes"
    )


def test_the_workflow_keeps_both_lanes_independent_and_the_existing_structure() -> None:
    workflow = _load_workflow()
    assert set(workflow["jobs"]) == {"facts", "present"}
    assert_facts_job_is_unprivileged(workflow)
    assert_present_job_runs_no_repository_code(workflow)
    assert_lanes_are_independent(workflow)


def test_each_lane_step_passes_its_own_lane_flag_and_the_same_verified_facts() -> None:
    steps = lane_steps(_load_workflow())
    for lane, step in steps.items():
        run = str(step["run"])
        assert f"--lane {lane}" in run
        assert "--expected-facts-sha256" in run and "--facts-dir .present-facts" in run
        assert "--workdir .present-work" in run
        env = step["env"]
        assert "secrets.GPT_OSS_API_KEY" in json.dumps(env)
        assert "REPOSITORY_PRESENTER_STATE_TOKEN" in env


def test_a_lane_l_step_that_could_be_skipped_by_a_lane_r_failure_fails_the_structure_check() -> (
    None
):
    workflow = copy.deepcopy(_load_workflow())
    workflow_l = lane_steps(workflow)["L"]
    workflow_l["if"] = (
        "${{ inputs.lane != 'R' }}"  # no status function: skipped after R fails
    )
    with pytest.raises(AssertionError, match="even when Lane R failed"):
        assert_lanes_are_independent(workflow)


def test_a_lane_l_step_that_does_not_need_the_facts_fails_the_structure_check() -> None:
    workflow = copy.deepcopy(_load_workflow())
    lane_steps(workflow)["L"]["if"] = "${{ !cancelled() && inputs.lane != 'R' }}"
    with pytest.raises(AssertionError, match="needs the facts"):
        assert_lanes_are_independent(workflow)


def test_a_lane_whose_call_store_is_not_persisted_fails_the_structure_check() -> None:
    workflow = copy.deepcopy(_load_workflow())
    for step in present_steps(workflow):
        if "cache" in str(step.get("uses", "")):
            step["with"]["path"] = step["with"]["path"].replace(
                ".present-work/lane-l/llm_cache\n", ""
            )
    with pytest.raises(AssertionError, match="Lane L's call store"):
        assert_lanes_are_independent(workflow)


def test_a_missing_or_duplicated_lane_step_fails_the_structure_check() -> None:
    workflow = copy.deepcopy(_load_workflow())
    workflow["jobs"]["present"]["steps"] = [
        step
        for step in present_steps(workflow)
        if step.get("name") != "Present (Lane L)"
    ]
    with pytest.raises(AssertionError, match="each lane needs its own step"):
        assert_lanes_are_independent(workflow)

    workflow = copy.deepcopy(_load_workflow())
    workflow["jobs"]["present"]["steps"].append(
        copy.deepcopy(lane_steps(workflow)["R"])
    )
    with pytest.raises(AssertionError, match="two steps run Lane R"):
        assert_lanes_are_independent(workflow)


def test_a_lane_l_step_moved_into_the_facts_job_fails_the_unprivileged_check() -> None:
    """The credentialed Lane L step holds the provider key and the state token; the facts job runs
    repository code. Moving it there is the exact breach the split exists to stop."""
    workflow = copy.deepcopy(_load_workflow())
    step = lane_steps(workflow)["L"]
    workflow["jobs"]["facts"]["steps"].append(step)
    with pytest.raises(AssertionError, match="no secrets"):
        assert_facts_job_is_unprivileged(workflow)


def test_an_unknown_lane_option_fails_the_structure_check() -> None:
    workflow = copy.deepcopy(_load_workflow())
    triggers(workflow)["workflow_dispatch"]["inputs"]["lane"]["options"].append("X")
    with pytest.raises(AssertionError):
        assert_lanes_are_independent(workflow)
