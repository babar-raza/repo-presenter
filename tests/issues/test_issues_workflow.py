"""R39 workflow trust boundary (.github/workflows/issues.yml), the present.yml facts/present model:
the job that runs upstream code holds no secret, no variable, no write scope and no App token; the
job that holds the App token runs no upstream code and installs no toolchain. Triggers: schedule,
manual dispatch, and a validated run request (run-request-execute.yml's ``issues`` job)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _wf(name: str) -> tuple[dict, dict]:
    wf = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    return wf, (wf["on"] if "on" in wf else wf[True])


def test_triggers_and_top_level_permissions() -> None:
    wf, on = _wf("issues.yml")
    assert set(on) == {"schedule", "workflow_dispatch", "workflow_call"}
    assert on["schedule"] and not (on["workflow_call"] or {}).get("inputs")
    assert wf["permissions"] == {"contents": "read"}
    assert set(wf["jobs"]) == {"reproduce", "maintain"}


def test_the_job_that_runs_upstream_code_holds_nothing() -> None:
    wf, _ = _wf("issues.yml")
    job = wf["jobs"]["reproduce"]
    text = json.dumps(job)
    assert job["permissions"] == {"contents": "read"}
    assert "secrets." not in text and "vars." not in text and "github.token" not in text
    assert "create-github-app-token" not in text and "TOKEN" not in text
    for step in job["steps"]:
        if str(step.get("uses", "")).startswith("actions/checkout"):
            assert step["with"]["persist-credentials"] is False
    runs = " ".join(s.get("run", "") for s in job["steps"])
    assert "git clone" in runs and "repo_presenter.issues.reproduce" in runs
    assert "repo_presenter.issues.monitor" not in runs


def test_the_job_holding_the_app_token_runs_no_upstream_code() -> None:
    wf, _ = _wf("issues.yml")
    job = wf["jobs"]["maintain"]
    assert job["needs"] == "reproduce"
    assert job["permissions"] == {"contents": "write"}
    uses = [str(s.get("uses", "")) for s in job["steps"]]
    assert not any(u.startswith(("actions/setup-node", "actions/setup-java", "actions/setup-dotnet",
                                 "actions/setup-go", "dtolnay/")) for u in uses)
    runs = " ".join(s.get("run", "") for s in job["steps"])
    for forbidden in ("git clone", "npm ", "node ", "npx ", ".issue-upstream", "repo_presenter.issues.reproduce"):
        assert forbidden not in runs, forbidden
    (mint,) = [s for s in job["steps"] if "create-github-app-token" in str(s.get("uses", ""))]
    assert mint["with"]["owner"] == "${{ env.PILOT_OWNER }}"
    assert mint["with"]["repositories"] == "${{ env.PILOT_NAME }}"
    assert mint["with"]["permission-issues"] == "write"
    assert set(k for k in mint["with"] if k.startswith("permission-")) == {"permission-issues", "permission-metadata"}
    assert wf["env"] == {"PILOT_OWNER": "aspose-3d-foss", "PILOT_NAME": "Aspose.3D-FOSS-for-TypeScript"}
    for step in job["steps"]:
        if str(step.get("uses", "")).startswith("actions/checkout"):
            assert step["with"]["persist-credentials"] is False


def test_the_run_request_executor_calls_it_with_minimal_permissions() -> None:
    wf, _ = _wf("run-request-execute.yml")
    job = wf["jobs"]["issues"]
    assert job["needs"] == "validate"
    assert job["if"] == "needs.validate.outputs.job == 'issues'"
    assert job["uses"] == "./.github/workflows/issues.yml"
    assert job["permissions"] == {"contents": "write"}
    assert job["secrets"] == "inherit" and "with" not in job
