"""TC-009a: the one authorized live mint (docs/DECISION_LOG.md, OWNER-AUTH-2026-11-05-TC009A-ONE-MINT).

The proof never carries the token; it is true only when the token is an installation token whose
reach token_provenance verified; it is never overwritten. The workflow can only be dispatched by
hand, targets the one authorized repository read-only, and refuses a second mint.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

from repo_presenter.github.token_provenance import TokenDecision

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "tc-009a-mint-proof.yml"
TOKEN = "ghs_" + "x" * 36
TARGET = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"

spec = importlib.util.spec_from_file_location("mint_proof", REPO / "scripts" / "mint_proof.py")
mint_proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mint_proof)


def ok(repository, token):
    return TokenDecision(True, token)


def refused(repository, token):
    return TokenDecision(False, None, None, "the write token reaches 3 repositories")


def test_a_verified_installation_token_is_proven_and_never_recorded():
    proof = mint_proof.build_proof(TARGET, TOKEN, run_id="1", verify=ok)
    assert proof["minted"] is True and proof["verified_via_token_provenance"] is True
    assert proof["upstream_writes"] == 0 and proof["repository"] == TARGET
    assert TOKEN not in json.dumps(proof) and "ghs_" not in json.dumps(proof)


def test_a_token_that_fails_verification_is_minted_but_not_verified():
    proof = mint_proof.build_proof(TARGET, TOKEN, run_id="1", verify=refused)
    assert proof["minted"] is True and proof["verified_via_token_provenance"] is False
    assert "3 repositories" in proof["verification_detail"]


def test_a_non_installation_token_is_not_a_mint_and_is_never_sent_for_verification():
    def never(repository, token):
        raise AssertionError("a personal token must not reach the verifier")

    proof = mint_proof.build_proof(TARGET, "ghp_" + "y" * 36, run_id="1", verify=never)
    assert proof["minted"] is False and proof["verified_via_token_provenance"] is False


def test_an_existing_proof_is_never_overwritten(tmp_path, monkeypatch):
    out = tmp_path / "mint_proof.json"
    out.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GH_APP_INSTALLATION_TOKEN", TOKEN)
    assert mint_proof.main(["--repository", TARGET, "--out", str(out)]) == 1
    assert out.read_text(encoding="utf-8") == "{}"


def test_an_empty_mint_writes_no_proof(tmp_path, monkeypatch):
    out = tmp_path / "mint_proof.json"
    monkeypatch.delenv("GH_APP_INSTALLATION_TOKEN", raising=False)
    assert mint_proof.main(["--repository", TARGET, "--out", str(out)]) == 1
    assert not out.exists()


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_the_workflow_is_manual_or_run_request_only_with_no_inputs():
    """workflow_dispatch, plus workflow_call from run-request.yml (owner ruling 2026-11-06); never a
    push/schedule trigger of its own, and no inputs on either, so the target cannot be changed."""
    workflow = _workflow()
    triggers = workflow["on"] if "on" in workflow else workflow[True]
    assert set(triggers) == {"workflow_dispatch", "workflow_call"}
    for trigger in triggers.values():
        assert not (trigger or {}).get("inputs")


def test_the_mint_is_the_one_authorized_repository_read_only():
    workflow = _workflow()
    assert f"{workflow['env']['TARGET_OWNER']}/{workflow['env']['TARGET_REPOSITORY']}" == TARGET
    steps = workflow["jobs"]["mint-proof"]["steps"]
    mints = [s for s in steps if str(s.get("uses", "")).startswith("actions/create-github-app-token")]
    assert len(mints) == 1
    permissions = {k: v for k, v in mints[0]["with"].items() if k.startswith("permission-")}
    assert permissions == {"permission-contents": "read", "permission-metadata": "read"}
    assert workflow["permissions"] == {"contents": "write"}  # this repository's proof branch only


def test_the_workflow_refuses_a_second_mint_before_minting():
    steps = _workflow()["jobs"]["mint-proof"]["steps"]
    names = [s.get("name", "") for s in steps]
    guard = names.index("Refuse a second mint")
    mint = next(i for i, s in enumerate(steps) if s.get("id") == "app-token")
    assert guard < mint
    assert "PROOF_BRANCH" in steps[guard]["run"] and "PROOF_PATH" in steps[guard]["run"]


def test_the_token_reaches_only_the_verifier_and_is_never_echoed():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.count("steps.app-token.outputs.token") == 1
    secrets = {part.split("}")[0].strip() for part in text.split("secrets.")[1:]}
    assert secrets == {"GH_APP_ID", "GH_APP_PRIVATE_KEY"}
