"""R50 / WP-1: structural proof that `.github/workflows/propose.yml` (and its run-request wiring) cannot write
upstream without every gate, keeps the App secrets out of everything but the two mint steps, is least-privilege,
and that its dry-run job writes nothing. Parses the YAML; nothing here calls GitHub."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
PROPOSE = WORKFLOWS / "propose.yml"
EXECUTOR = WORKFLOWS / "run-request-execute.yml"
KILL = "REPO_PRESENTER_PROPOSAL_WRITE_AUTHORIZED"
SANDBOX = "REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(doc: dict) -> dict:
    return doc["on"] if "on" in doc else doc[True]


WF = _load(PROPOSE)
JOBS = WF["jobs"]


def _steps(job: str) -> list[dict]:
    return JOBS[job]["steps"]


def _mints(job: str) -> list[dict]:
    return [s for s in _steps(job) if str(s.get("uses", "")).startswith("actions/create-github-app-token")]


def test_triggers_are_workflow_call_and_dispatch_and_dry_run_is_the_default():
    triggers = _triggers(WF)
    assert set(triggers) == {"workflow_call", "workflow_dispatch"}
    for name in triggers:
        assert triggers[name]["inputs"]["dry_run"]["default"] is True
        assert set(triggers[name]["inputs"]) == {"repository", "lane", "dry_run", "sandbox"}
        assert triggers[name]["inputs"]["sandbox"]["default"] is False  # the R17 sandbox path is opt-in


def test_the_jobs_are_validate_gate_dry_run_write_in_that_order():
    assert list(JOBS) == ["validate", "gate", "dry-run", "write"]
    assert JOBS["gate"]["needs"] == "validate"
    assert JOBS["dry-run"]["needs"] == ["validate", "gate"]
    assert JOBS["write"]["needs"] == ["validate", "gate", "dry-run"]


def test_permissions_are_least_privilege_and_no_job_holds_a_write_scope():
    assert WF["permissions"] == {"contents": "read"}
    for name, job in JOBS.items():
        assert "permissions" in job, f"{name} must declare its own permissions"
        assert set(job["permissions"].values()) == {"read"}, (name, job["permissions"])
        assert set(job["permissions"]) <= {"contents", "attestations"}, (name, job["permissions"])
    assert JOBS["validate"]["permissions"] == {"contents": "read"}
    # attestations: read lets gate 3b verify the acceptance record's Sigstore attestation (read-only)
    assert JOBS["dry-run"]["permissions"] == {"contents": "read", "attestations": "read"}
    for name, job in JOBS.items():
        for step in job["steps"]:
            if str(step.get("uses", "")).startswith("actions/checkout"):
                assert step["with"]["persist-credentials"] is False, name


def test_the_app_secrets_appear_only_in_the_two_mint_steps_and_never_in_validate_or_gate():
    for name in ("validate", "gate"):
        assert "secrets." not in json.dumps(JOBS[name]), f"{name} must hold no secret"
    for name in ("dry-run", "write"):
        for step in _steps(name):
            text = json.dumps(step)
            if "secrets." in text:
                assert str(step["uses"]).startswith("actions/create-github-app-token"), (name, step.get("name"))
                assert set(re.findall(r"secrets\.(\w+)", text)) == {"GH_APP_ID", "GH_APP_PRIVATE_KEY"}
                assert "run" not in step and "env" not in step
    assert len(_mints("dry-run")) == 1 and len(_mints("write")) == 1
    assert "secrets." not in json.dumps(WF["on"] if "on" in WF else WF[True])
    # no LLM / gateway secret and no PAT anywhere in the file
    assert set(re.findall(r"secrets\.(\w+)", PROPOSE.read_text(encoding="utf-8"))) == {"GH_APP_ID", "GH_APP_PRIVATE_KEY"}


def test_the_dry_run_mint_is_read_only_and_only_the_write_job_mints_a_write_token():
    (dry,) = _mints("dry-run")
    permissions = {k: v for k, v in dry["with"].items() if k.startswith("permission-")}
    assert permissions and set(permissions.values()) == {"read"}
    assert dry["continue-on-error"] is True
    (write,) = _mints("write")
    scoped = {k: v for k, v in write["with"].items() if k.startswith("permission-")}
    assert scoped == {"permission-contents": "write", "permission-metadata": "read", "permission-pull-requests": "write"}
    for step in (dry, write):  # one repository, never the whole installation
        assert step["with"]["owner"] == "${{ needs.validate.outputs.owner }}"
        assert step["with"]["repositories"] == "${{ needs.validate.outputs.name }}"


def test_the_write_token_reaches_exactly_one_step_and_nothing_else_names_it():
    holders = [
        (job, s.get("name"))
        for job in JOBS
        for s in _steps(job)
        if "GH_PROPOSAL_WRITE_TOKEN" in json.dumps(s.get("env", {}))
    ]
    assert len(holders) == 1 and holders[0][0] == "write"
    (step,) = [s for s in _steps("write") if "GH_PROPOSAL_WRITE_TOKEN" in json.dumps(s.get("env", {}))]
    assert step["env"]["GH_PROPOSAL_WRITE_TOKEN"] == "${{ steps.app-token.outputs.token }}"
    assert "steps.app-token" not in json.dumps([s for s in _steps("write") if s is not step])
    for job in ("validate", "gate", "dry-run"):
        assert "steps.app-token" not in json.dumps(JOBS[job]) and "GH_PROPOSAL_WRITE_TOKEN" not in json.dumps(JOBS[job])
    # the token is minted after every dependency is installed, then used by the final step
    names = [s.get("name", s.get("uses", "")) for s in _steps("write")]
    install = next(i for i, n in enumerate(names) if n == "Install")
    mint = next(i for i, s in enumerate(_steps("write")) if s.get("id") == "app-token")
    assert install < mint < len(names) - 1 and _steps("write")[-1] is step


def test_inputs_never_reach_a_shell_script_directly():
    for name, job in JOBS.items():
        for step in job["steps"]:
            run = step.get("run", "")
            assert "${{ inputs." not in run and "${{ github.event" not in run, (name, step.get("name"))
            assert "${{ needs." not in run, (name, step.get("name"))
    # validate: every input passes through env and is pattern-checked
    (check,) = _steps("validate")
    assert set(check["env"]) == {
        "INPUT_REPOSITORY", "INPUT_LANE", "INPUT_DRY_RUN", "INPUT_SANDBOX", "SANDBOX_REPOSITORY", "REF",
    }
    assert '[ "$REF" = "refs/heads/main" ]' in check["run"]


# --- the write job is unreachable without every gate -------------------------------------------------------


def _expression(text: str, context: dict) -> bool:
    """Evaluate the (restricted) `if:` expression grammar used here: dotted lookups, string literals,
    ==, &&, ||, parentheses."""
    expr = " ".join(str(text).split())
    expr = re.sub(r"needs\.([\w-]+)\.(outputs\.(\w+)|result)", lambda m: f"ctx['needs']['{m.group(1)}']['{m.group(3) or 'result'}']", expr)
    expr = re.sub(r"vars\.(\w+)", lambda m: f"ctx['vars'].get('{m.group(1)}', '')", expr)
    expr = expr.replace("&&", " and ").replace("||", " or ")
    assert re.fullmatch(r"[\w\s\[\]'\".(),=\-]*", expr), expr
    return bool(eval(expr, {"__builtins__": {}}, {"ctx": context}))


def _context() -> dict:
    return {
        "needs": {
            "validate": {"dry_run": "false"},
            "gate": {
                "allowlist": "true",
                "registry_full": "true",
                "portfolio_r15": "true",
                "sandbox_target": "true",
                "write_eligible": "true",
            },
            "dry-run": {"result": "success", "write_eligible": "true"},
        },
        "vars": {KILL: "true", SANDBOX: "owner/sandbox"},
    }


def test_the_write_job_runs_only_when_every_gate_is_open():
    condition = JOBS["write"]["if"]
    assert _expression(condition, _context()) is True
    assert _expression(condition, {**_context(), "vars": {**_context()["vars"], KILL: "1"}}) is True


@pytest.mark.parametrize(
    "path, value",
    [
        (("needs", "validate", "dry_run"), "true"),  # a dry run never reaches the write job
        (("needs", "gate", "allowlist"), "false"),
        (("needs", "gate", "registry_full"), "false"),
        (("needs", "gate", "portfolio_r15"), "false"),  # R15: not every candidate of both lanes passes
        (("needs", "gate", "sandbox_target"), "false"),
        (("needs", "gate", "write_eligible"), "false"),
        (("needs", "gate", "allowlist"), ""),  # a gate that produced no output is closed
        (("needs", "dry-run", "result"), "failure"),
        (("needs", "dry-run", "result"), "skipped"),
        (("needs", "dry-run", "write_eligible"), "false"),
        (("vars", KILL), ""),
        (("vars", KILL), "false"),
        (("vars", KILL), "yes"),
    ],
)
def test_closing_any_single_gate_keeps_the_write_job_from_running(path, value):
    context = _context()
    target = context
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert _expression(JOBS["write"]["if"], context) is False


def test_the_write_if_names_every_gate_and_no_write_step_exists_outside_the_gated_job():
    condition = JOBS["write"]["if"]
    for token in (
        "needs.validate.outputs.dry_run == 'false'",
        f"vars.{KILL}",
        "needs.gate.outputs.allowlist == 'true'",
        "needs.gate.outputs.registry_full == 'true'",
        "needs.gate.outputs.portfolio_r15 == 'true'",
        "needs.gate.outputs.sandbox_target == 'true'",
        "needs.gate.outputs.write_eligible == 'true'",
        "needs.dry-run.result == 'success'",
    ):
        assert token in " ".join(condition.split()), token
    for name in ("validate", "gate", "dry-run"):
        assert "if" not in JOBS[name] or "write" not in str(JOBS[name]["if"])
        text = json.dumps(JOBS[name])
        assert "propose.run write" not in text and "permission-contents\": \"write" not in text
        assert "pull_request" not in text or name == "gate"
    run_write = [s for s in _steps("write") if "propose.run write" in s.get("run", "")]
    assert len(run_write) == 1
    # the write step passes the live variables so the driver re-evaluates all five gates before any call
    assert set(run_write[0]["env"]) >= {
        "GH_PROPOSAL_WRITE_TOKEN",
        KILL,
        SANDBOX,
        "REPOSITORY_PRESENTER_STATE_TOKEN",
    }
    assert run_write[0]["env"][KILL] == f"${{{{ vars.{KILL} }}}}"
    assert run_write[0]["env"][SANDBOX] == f"${{{{ vars.{SANDBOX} }}}}"


def test_the_dry_run_job_writes_nothing():
    text = json.dumps(JOBS["dry-run"])
    assert "propose.run payload" in text and "propose.run write" not in text
    assert "GH_PROPOSAL_WRITE_TOKEN" not in text
    assert "git push" not in text and "gh pr" not in text and "gh api -X" not in text and "--method" not in text
    # attestations: read lets gate 3b verify the acceptance record's Sigstore attestation (read-only)
    assert JOBS["dry-run"]["permissions"] == {"contents": "read", "attestations": "read"}
    (payload,) = [s for s in _steps("dry-run") if "propose.run payload" in s.get("run", "")]
    # the payload step holds the read token and the state-read token only
    assert set(payload["env"]) == {
        "GITHUB_TOKEN",
        "GH_TOKEN",  # the read-only default token `gh attestation verify` uses (gate 3b)
        "REPOSITORY_PRESENTER_STATE_TOKEN",
        "READ_TOKEN",
        "REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY",
        "REPOSITORY",
        "LANE",
        "SANDBOX",
        "TRIGGER_SHA",
    }
    uploads = [s for s in _steps("dry-run") if str(s.get("uses", "")).startswith("actions/upload-artifact")]
    assert [u["with"]["name"].split("-")[1] for u in uploads] == ["payload"] and uploads[0]["if"] == "always()"


def test_the_gate_job_is_read_only_and_reports_all_five_gates():
    (step,) = [s for s in _steps("gate") if s.get("id") == "gates"]
    assert "propose.run gates" in step["run"]
    assert set(JOBS["gate"]["outputs"]) == {
        "allowlist", "registry_full", "kill_switch", "portfolio_r15", "sandbox_target", "write_eligible"}
    assert JOBS["gate"]["permissions"] == {"contents": "read", "attestations": "read"}
    from repo_presenter.propose.run import GATE_NAMES

    assert set(GATE_NAMES) == set(JOBS["gate"]["outputs"]) - {"write_eligible"}


def test_the_run_request_executor_calls_propose_dry_run_by_default_with_read_only_permissions():
    doc = _load(EXECUTOR)
    job = doc["jobs"]["propose"]
    assert job["needs"] == "validate" and job["if"] == "needs.validate.outputs.job == 'propose'"
    assert job["uses"] == "./.github/workflows/propose.yml"
    assert job["permissions"] == {"contents": "read", "attestations": "read"}
    assert job["secrets"] == "inherit"
    assert job["with"] == {
        "repository": "${{ needs.validate.outputs.repository }}",
        "lane": "${{ needs.validate.outputs.lane }}",
        # fail closed: anything other than the exact string 'false' is a dry run
        "dry_run": "${{ needs.validate.outputs.dry_run != 'false' }}",
        # R17 sandbox mode only for the exact string 'true'
        "sandbox": "${{ needs.validate.outputs.sandbox == 'true' }}",
    }
    assert doc["jobs"]["validate"]["outputs"]["dry_run"] == "${{ steps.check.outputs.dry_run }}"


# --- naming drift of the kill-switch variables ----------------------------------------------------------------


def test_the_kill_switch_names_agree_between_code_and_workflows():
    from repo_presenter.candidates_publish.effect import (
        AUTHORIZATION_VARIABLE as candidates,
    )
    from repo_presenter.issues.file import (
        AUTHORIZATION_VARIABLE as issues,
    )
    from repo_presenter.propose.effect import AUTHORIZATION_VARIABLE as proposal

    assert (proposal, candidates, issues) == (
        "REPO_PRESENTER_PROPOSAL_WRITE_AUTHORIZED",
        "REPO_PRESENTER_CANDIDATES_WRITE_AUTHORIZED",
        "REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED",
    )
    used = set()
    for path in sorted(WORKFLOWS.glob("*.yml")):
        used |= set(re.findall(r"vars\.(\w*WRITE_AUTHORIZED)", path.read_text(encoding="utf-8")))
    assert used <= {proposal, candidates, issues}, used
    assert {proposal, issues} <= used  # both wired workflows read a name the code reads


def test_no_workflow_code_or_test_still_uses_the_old_project_variable_prefix():
    offenders = []
    # BL-742: the issues switch's canonical family name legitimately lives in the issues code and issues.yml.
    issues_files = {"src/repo_presenter/issues/file.py", "src/repo_presenter/issues/monitor.py", ".github/workflows/issues.yml"}
    for base in (ROOT / "src", ROOT / ".github", ROOT / "scripts", ROOT / "data", ROOT / "ops"):
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".yml", ".yaml", ".json", ".sh", ".md"} and re.search(
                r"REPOSITORY_PRESENTER_\w*WRITE_AUTHORIZED", path.read_text(encoding="utf-8", errors="ignore")
            ):
                offenders.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    assert not set(offenders) - issues_files, offenders


# --- the R17 sandbox mode (owner decision 2026-11-22) -------------------------------------------------------------


def test_sandbox_mode_scopes_both_mints_to_the_sandbox_and_never_accepts_the_wildcard():
    (check,) = _steps("validate")
    run = check["run"]
    # the write target (owner/name outputs, which both mint steps use) is the sandbox in sandbox mode
    assert 'target="$SANDBOX_REPOSITORY"' in run and 'owner="${target%%/*}"' in run
    assert '[ "$SANDBOX_REPOSITORY" != "*" ]' in run
    assert check["env"]["SANDBOX_REPOSITORY"] == "${{ vars.REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY }}"
    assert check["env"]["INPUT_SANDBOX"] == "${{ inputs.sandbox }}"
    assert JOBS["validate"]["outputs"]["sandbox"] == "${{ steps.check.outputs.sandbox }}"
    for step in (*_mints("dry-run"), *_mints("write")):
        assert step["with"]["owner"] == "${{ needs.validate.outputs.owner }}"
        assert step["with"]["repositories"] == "${{ needs.validate.outputs.name }}"


def test_the_sandbox_flag_reaches_the_gate_payload_and_write_steps_through_env_only():
    for job, command in (("gate", "gates"), ("dry-run", "payload"), ("write", "write")):
        (step,) = [s for s in _steps(job) if f"propose.run {command}" in s.get("run", "")]
        assert step["env"]["SANDBOX"] == "${{ needs.validate.outputs.sandbox }}"
        assert "--sandbox" in step["run"] and "${{ needs." not in step["run"] and "${{ inputs." not in step["run"]
    # the write job's `if` is unchanged: every gate still has to be open, in sandbox mode too
    assert "needs.gate.outputs.portfolio_r15 == 'true'" in JOBS["write"]["if"]
