"""2026-11-04 (TC-009, dev/mock scope): structural tests for .github/workflows/mint-app-token.yml
-- a reusable `workflow_call`-only workflow adapting the legacy repo's own proven
actions/create-github-app-token@v2 pattern. Confirms it cannot fire on its own (no trigger but
workflow_call) and that nothing calls it yet (TC-009a's job, not this one), following the same
_load_workflow-style structural-parsing pattern tests/test_present.py already established."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

WORKFLOWS_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"
MINT_TOKEN_PATH = WORKFLOWS_DIR / "mint-app-token.yml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    return workflow["on"] if "on" in workflow else workflow[True]


def test_the_workflow_has_no_trigger_but_workflow_call():
    workflow = _load(MINT_TOKEN_PATH)
    triggers = _triggers(workflow)
    assert set(triggers) == {"workflow_call"}, (
        "this workflow must never be independently triggerable -- only a future, "
        "explicitly-authorized caller (TC-009a) may invoke it"
    )


def test_nothing_in_this_repository_calls_it_yet():
    """TC-009a is the separate, owner-gated card that adds the one real caller. Until that card
    lands, no other workflow file may reference this one."""
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        if path == MINT_TOKEN_PATH:
            continue
        text = path.read_text(encoding="utf-8")
        assert "mint-app-token.yml" not in text, f"{path.name} already calls mint-app-token.yml"


def test_the_mint_step_uses_the_official_action_scoped_to_one_repository():
    workflow = _load(MINT_TOKEN_PATH)
    steps = workflow["jobs"]["mint"]["steps"]
    mint_steps = [s for s in steps if s.get("uses", "").startswith("actions/create-github-app-token")]
    assert len(mint_steps) == 1, "exactly one token-minting step, using the official action"
    step = mint_steps[0]
    with_block = step["with"]
    assert with_block["owner"] == "${{ inputs.owner }}"
    assert with_block["repositories"] == "${{ inputs.repository_name }}"
    # Never the whole App installation: owner+repositories together scope to one repo. No
    # issues/administration permission at all -- only what a caller explicitly requests.
    assert "permission-issues" not in with_block
    assert "permission-administration" not in with_block


def test_the_workflow_references_no_secret_outside_the_two_app_credential_names():
    workflow = _load(MINT_TOKEN_PATH)
    rendered = json.dumps(workflow)
    assert "secrets.GH_APP_ID" in rendered
    assert "secrets.GH_APP_PRIVATE_KEY" in rendered
    # No state/provider secret belongs anywhere near token minting.
    assert "GPT_OSS" not in rendered
    assert "REPOSITORY_PRESENTER_STATE_TOKEN" not in rendered


def test_the_token_output_is_wired_through_without_a_second_echo():
    """The minted token must flow only through the one blessed path (job output -> workflow
    output), never printed or re-assigned to a second variable that could leak into a log."""
    workflow = _load(MINT_TOKEN_PATH)
    job = workflow["jobs"]["mint"]
    assert job["outputs"]["token"] == "${{ steps.app-token.outputs.token }}"
    for step in job["steps"]:
        run = str(step.get("run", ""))
        assert "steps.app-token.outputs.token" not in run, (
            "the token must never be referenced from a run: step -- only as a job/workflow output"
        )


def test_any_future_caller_may_only_target_this_repository():
    """2026-11-04 owner directive: every repository except babar-raza/repo-presenter is read-only,
    and this workflow takes `owner`/`repository_name` from its caller -- so a caller could mint an
    installation token for an upstream repository. Until that rule is lifted by a reviewed change,
    every `uses:` of this workflow must pass literal owner/repository_name values naming this
    repository (an expression is refused: it could resolve to anything)."""
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        if path == MINT_TOKEN_PATH:
            continue
        for job in (_load(path).get("jobs") or {}).values():
            if "mint-app-token" not in str(job.get("uses", "")):
                continue
            with_ = job.get("with") or {}
            assert with_.get("owner") == "babar-raza", (path.name, with_)
            assert with_.get("repository_name") == "repo-presenter", (path.name, with_)


def test_minted_token_requests_only_the_least_privilege_permission_set():
    """Least privilege (TC-009, 2026-11-04 directive): the minted installation token may carry
    only contents, metadata and pull-requests. Any other `permission-*` input (issues,
    administration, workflows, actions, ...) widens what a leaked or misused token can do and
    must be a reviewed change to this test, not a drive-by edit to the workflow."""
    workflow = _load(MINT_TOKEN_PATH)
    steps = workflow["jobs"]["mint"]["steps"]
    granted = {
        key
        for step in steps
        if "create-github-app-token" in str(step.get("uses", ""))
        for key in (step.get("with") or {})
        if key.startswith("permission-")
    }
    assert granted == {"permission-contents", "permission-metadata", "permission-pull-requests"}
