"""WP-3 (R50): .github/workflows/monitor.yml is read-only against upstream: it references no secret, no
variable and no App token, runs no upstream code, calls no provider, writes only this repository's
state ref (contents: write on the one job), and is callable from the validated run request."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _load(name: str) -> tuple[dict, dict]:
    wf = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    return wf, (wf["on"] if "on" in wf else wf[True])


def test_monitor_runs_on_a_schedule_dispatch_and_call_and_holds_one_job() -> None:
    wf, on = _load("monitor.yml")
    assert set(on) == {"schedule", "workflow_dispatch", "workflow_call"}
    assert "*/6" in on["schedule"][0]["cron"]
    assert wf["permissions"] == {"contents": "read"}
    assert set(wf["jobs"]) == {"monitor"}
    assert wf["jobs"]["monitor"]["permissions"] == {"contents": "write"}


def test_monitor_holds_no_secret_no_app_token_and_runs_no_upstream_code() -> None:
    wf, _ = _load("monitor.yml")
    text = json.dumps(wf)
    for forbidden in ("secrets.", "vars.", "create-github-app-token", "git clone", "npm ", "setup-node",
                      "setup-java", "setup-dotnet", "OPENAI", "GPT_OSS", "REPO_PRESENTER_ISSUES_WRITE"):
        assert forbidden not in text, forbidden
    runs = " ".join(s.get("run", "") for s in wf["jobs"]["monitor"]["steps"])
    assert "repo_presenter.monitor" in runs and "--no-write" not in runs


def test_the_run_request_executor_calls_monitor_with_main_s_copy_and_no_secrets() -> None:
    wf, _ = _load("run-request-execute.yml")
    job = wf["jobs"]["monitor"]
    assert job["uses"] == "./.github/workflows/monitor.yml"
    assert job["if"] == "needs.validate.outputs.job == 'monitor'"
    assert job["permissions"] == {"contents": "write"}
    assert "secrets" not in job
