"""R50 / WP-1: the proposal driver (`repo_presenter.propose.run`). Fakes only; nothing here reaches GitHub.
The dry run is proven to write nothing by leaving it every read seam and making every write function of the
GitHub client raise; the write path is proven to refuse, before any network call, unless all five gates hold."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from repo_presenter.github import client as github_client
from repo_presenter.propose import run

TARGET = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"  # on the allowlist and registry mode full
REVISION = "a" * 40
README = "# Cells for Rust\n\nIntro.\n\n## Install\n\n```\ncargo add cells\n```\n"
ENV_ALL = {
    run.AUTHORIZATION_VARIABLE: "true",
    run.SANDBOX_VARIABLE: TARGET,
}


@dataclass
class Ready:
    ready: bool = True
    text: str = "all 80 cells terminal"

    def reason(self) -> str:
        return self.text


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_bundle(root: Path, repository: str = TARGET, lane: str = "R", readme: str = README) -> run.Candidate:
    slug = root / "candidates" / repository.replace("/", "__")
    lane_root = slug if lane == "R" else slug / "lane-l"
    bundle = lane_root / REVISION
    bundle.mkdir(parents=True)
    data = readme.encode()
    (bundle / "README.md").write_bytes(data)
    manifest = {
        "schema_version": 1 if lane == "R" else 2,
        "state": "READY_FOR_PROPOSAL",
        "files": {"README.md": {"sha256": _sha(data), "bytes": len(data)}},
    }
    if lane != "R":
        manifest["lane"] = lane
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (lane_root / "CURRENT").write_text(REVISION + "\n", encoding="utf-8")
    return run.load_candidate(repository, lane, root)


@pytest.fixture
def forbid_writes(monkeypatch):
    """Every GitHub function that can write raises: reaching one fails the test."""

    def boom(*args, **kwargs):
        raise AssertionError("a write function was called")

    for name in ("create_ref", "put_contents", "create_pull_request", "update_pull_request", "default_post", "default_put", "default_patch"):
        monkeypatch.setattr(github_client, name, boom)


@pytest.fixture
def accepted_review(monkeypatch):
    review = SimpleNamespace(verdict="ACCEPT", model_reviewed=True, pr_eligible=True)
    monkeypatch.setattr(run, "load_review_verdict", lambda path: review)
    monkeypatch.setattr(run, "classify", lambda *a, **k: "publication-ready")
    return review


# --- the five gates ---------------------------------------------------------------------------------------


def test_every_gate_holds_for_an_allowlisted_registered_target_with_the_variables_set():
    gates = run.evaluate_gates(TARGET, ENV_ALL, readiness=lambda: Ready())
    assert [g.name for g in gates] == list(run.GATE_NAMES)
    assert all(g.ok for g in gates), [g for g in gates if not g.ok]
    assert run.write_eligible(gates)


def test_the_real_portfolio_gate_is_closed_until_the_official_count_is_complete(monkeypatch):
    from repo_presenter.propose import portfolio_gate

    monkeypatch.setattr(portfolio_gate, "portfolio_readiness", lambda: Ready(False, "17 of 80 cells have no terminal outcome"))
    gates = run.evaluate_gates(TARGET, ENV_ALL)
    closed = {g.name: g for g in gates if not g.ok}
    assert set(closed) == {"portfolio_r15"} and "17 of 80" in closed["portfolio_r15"].detail
    assert not run.write_eligible(gates)


def test_an_unreadable_portfolio_predicate_is_closed_not_open():
    def broken():
        raise RuntimeError("state remote unreachable")

    gate = run.gate_portfolio(broken)
    assert gate.ok is False and "unreadable" in gate.detail


@pytest.mark.parametrize(
    "repository, environment, closed",
    [
        ("aspose-tex-foss/Aspose.TeX-FOSS-for-Python", {**ENV_ALL, run.SANDBOX_VARIABLE: "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"}, {"allowlist", "registry_full"}),
        (TARGET, {**ENV_ALL, run.AUTHORIZATION_VARIABLE: ""}, {"kill_switch"}),
        (TARGET, {**ENV_ALL, run.AUTHORIZATION_VARIABLE: "no"}, {"kill_switch"}),
        (TARGET, {**ENV_ALL, run.SANDBOX_VARIABLE: ""}, {"sandbox_target"}),
        (TARGET, {**ENV_ALL, run.SANDBOX_VARIABLE: "babar-raza/some-sandbox"}, {"sandbox_target"}),
        (TARGET, {}, {"kill_switch", "sandbox_target"}),
    ],
)
def test_each_gate_closes_alone_and_the_report_names_it(repository, environment, closed):
    gates = run.evaluate_gates(repository, environment, readiness=lambda: Ready())
    assert {g.name for g in gates if not g.ok} == closed
    assert not run.write_eligible(gates)


def test_the_owner_lifts_the_sandbox_restriction_only_with_the_star_value():
    other = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
    assert run.gate_sandbox(other, {run.SANDBOX_VARIABLE: TARGET}).ok is False
    assert run.gate_sandbox(other, {run.SANDBOX_VARIABLE: "*"}).ok is True
    assert run.gate_sandbox(other, {}).ok is False
    assert run.gate_sandbox(TARGET, {run.SANDBOX_VARIABLE: TARGET.upper()}).ok is True


def test_a_non_draft_or_pull_request_less_allowlist_entry_is_refused(tmp_path):
    path = tmp_path / "allow.json"
    path.write_text(json.dumps({"schema_version": 1, "repositories": [
        {"repository": TARGET, "effects": ["issue"], "first_pr_as_draft": True}]}))
    assert run.gate_allowlist(TARGET, path).ok is False
    path.write_text(json.dumps({"schema_version": 1, "repositories": [
        {"repository": TARGET, "effects": ["pull_request"], "first_pr_as_draft": False}]}))
    assert "draft" in run.gate_allowlist(TARGET, path).detail
    path.write_text("not json")
    assert run.gate_allowlist(TARGET, path).ok is False  # a malformed allowlist grants nothing


# --- the dry run ------------------------------------------------------------------------------------------


def _head(**kwargs):
    return SimpleNamespace(branch="main", sha=REVISION, error=None, **kwargs)


def test_the_dry_run_builds_the_payload_and_performs_no_write(tmp_path, forbid_writes, accepted_review):
    candidate = make_bundle(tmp_path)
    gates = run.evaluate_gates(TARGET, ENV_ALL, readiness=lambda: Ready())
    seen = []

    def get_contents(owner, name, path, *, ref, token):
        seen.append((owner, name, path, ref))
        return github_client.FileContents(path="README.md", sha="b" * 40, text="# Cells for Rust\n\nOld intro.\n")

    payload = run.build_payload(
        candidate, gates, read_token="ghs_read", root=tmp_path, get_contents=get_contents, fetch_head=lambda r, token=None: _head(),
        verify_token=lambda repo, token: SimpleNamespace(ok=True, reason=""),
    )
    assert seen == [("aspose-cells-foss", "Aspose.Cells-FOSS-for-Rust", "README.md", "main")]
    assert payload["mode"] == "dry_run" and payload["writes_performed"] == 0
    assert payload["draft"] is True and payload["branch"] == "repository-presenter/readme-update"
    assert payload["base_branch"] == "main" and payload["source_revision"] == REVISION
    assert payload["files"] == [{"path": "README.md", "sha256": hashlib.sha256(README.encode()).hexdigest(), "bytes": len(README.encode())}]
    assert payload["candidate_hash"] == candidate.candidate_hash
    assert payload["title"] and "candidate_hash: " + candidate.candidate_hash in payload["body"]
    assert payload["app_token"] == "installation token reaches exactly the target"
    # with no committed authorization record the dry run reports the refusal rather than failing
    assert payload["authorization"]["decision"].startswith("no committed authorization record")
    assert payload["write_eligible"] is False
    assert any("authorization" in r for r in payload["refusals"])


def test_the_dry_run_reports_every_closed_gate_and_a_moved_source_without_failing(tmp_path, forbid_writes, accepted_review):
    candidate = make_bundle(tmp_path)
    gates = run.evaluate_gates(TARGET, {}, readiness=lambda: Ready(False, "incomplete"))
    payload = run.build_payload(
        candidate, gates, read_token=None, root=tmp_path,
        get_contents=lambda *a, **k: None,
        fetch_head=lambda r, token=None: SimpleNamespace(branch="main", sha="c" * 40, error=None),
    )
    text = " | ".join(payload["refusals"])
    for fragment in ("gate portfolio_r15", "gate kill_switch", "gate sandbox_target", "source moved"):
        assert fragment in text
    assert payload["write_eligible"] is False and payload["writes_performed"] == 0
    assert "live_revision" in payload and payload["app_token"].startswith("not checked")
    # no live README: the proposal adds one
    assert "adds one" in payload["body"]


def test_a_rejected_review_is_reported_as_a_refusal(tmp_path, monkeypatch, forbid_writes):
    candidate = make_bundle(tmp_path)
    monkeypatch.setattr(run, "load_review_verdict", lambda p: SimpleNamespace(verdict="REJECT", model_reviewed=True, pr_eligible=False))
    gates = run.evaluate_gates(TARGET, ENV_ALL, readiness=lambda: Ready())
    payload = run.build_payload(candidate, gates, read_token=None, root=tmp_path, get_contents=lambda *a, **k: None, fetch_head=lambda r, token=None: _head())
    assert any("independent review" in r for r in payload["refusals"])
    assert payload["write_eligible"] is False


def test_load_candidate_refuses_a_missing_or_tampered_bundle(tmp_path):
    with pytest.raises(run.CandidateError, match="no sealed candidate"):
        run.load_candidate(TARGET, "R", tmp_path)
    candidate = make_bundle(tmp_path)
    (candidate.bundle / "README.md").write_text("tampered\n")
    with pytest.raises(run.CandidateError, match="does not verify"):
        run.load_candidate(TARGET, "R", tmp_path)


def test_lane_l_bundles_load_from_the_lane_directory(tmp_path):
    candidate = make_bundle(tmp_path, lane="L")
    assert candidate.lane == "L" and candidate.revision == REVISION


# --- the gated write --------------------------------------------------------------------------------------


def _refusing_effect(*args, **kwargs):
    raise AssertionError("the effect must not be reached")


@pytest.mark.parametrize("closed_gate", run.GATE_NAMES)
def test_the_write_refuses_before_any_call_when_any_gate_is_closed(tmp_path, closed_gate, capsys):
    candidate = make_bundle(tmp_path)
    gates = [run.Gate(name, name != closed_gate, "x") for name in run.GATE_NAMES]
    code = run.run_write(
        candidate, gates, environment={run.WRITE_TOKEN_VARIABLE: "ghs_x"}, root=tmp_path, trigger_sha="d" * 40, propose=_refusing_effect
    )
    assert code == run.EXIT_REFUSED
    assert f"refused by gate {closed_gate}" in capsys.readouterr().err


def test_the_write_refuses_without_the_installation_token(tmp_path):
    candidate = make_bundle(tmp_path)
    gates = [run.Gate(name, True, "ok") for name in run.GATE_NAMES]
    assert run.run_write(candidate, gates, environment={}, root=tmp_path, trigger_sha="d" * 40, propose=_refusing_effect) == run.EXIT_REFUSED


def test_the_write_calls_the_effect_once_with_the_app_token_and_a_composed_pull_request(tmp_path, monkeypatch, accepted_review):
    candidate = make_bundle(tmp_path)
    gates = [run.Gate(name, True, "ok") for name in run.GATE_NAMES]
    monkeypatch.setattr(run, "fetch_default_branch_sha", lambda repo, token=None: _head())
    calls = []

    def fake_effect(**kwargs):
        calls.append(kwargs)
        content = kwargs["compose_pull_request"](None)
        assert content.title and "candidate_hash" in content.body
        return SimpleNamespace(
            authorized=True, effected=True, reason="proposed", reason_code=None,
            pr_url="https://github.com/x/y/pull/1", commit_written=True, pr_created=True, pr_updated=False,
        )

    environment = {run.WRITE_TOKEN_VARIABLE: "ghs_write", **ENV_ALL}
    assert run.run_write(candidate, gates, environment=environment, root=tmp_path, trigger_sha="d" * 40, propose=fake_effect) == run.EXIT_OK
    (call,) = calls
    assert call["repository"] == TARGET and call["token"] == "ghs_write"
    assert call["base_branch"] == "main" and call["source_revision"] == REVISION
    assert call["branch"] == "repository-presenter/readme-update"
    assert call["readme_text"] == README and call["permit"].effect == "readme_proposal"
    assert call["review"] is accepted_review


def test_a_refusing_effect_is_a_nonzero_exit(tmp_path, monkeypatch, accepted_review):
    candidate = make_bundle(tmp_path)
    gates = [run.Gate(name, True, "ok") for name in run.GATE_NAMES]
    monkeypatch.setattr(run, "fetch_default_branch_sha", lambda repo, token=None: _head())
    refused = SimpleNamespace(authorized=True, effected=False, reason="no authorization", reason_code="authorization_missing",
                              pr_url=None, commit_written=False, pr_created=False, pr_updated=False)
    code = run.run_write(candidate, gates, environment={run.WRITE_TOKEN_VARIABLE: "ghs_w", **ENV_ALL}, root=tmp_path,
                         trigger_sha="d" * 40, propose=lambda **k: refused)
    assert code == run.EXIT_REFUSED


def test_the_cli_write_refuses_on_closed_gates_before_touching_the_state_remote(monkeypatch, capsys):
    def no_export(*a, **k):
        raise AssertionError("the state remote must not be read for a refused write")

    monkeypatch.setattr(run, "export_candidate", no_export)
    for key in (run.AUTHORIZATION_VARIABLE, run.SANDBOX_VARIABLE):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(run, "gate_portfolio", lambda readiness=None: run.Gate("portfolio_r15", False, "incomplete"))
    code = run.main(["write", "--repository", TARGET, "--lane", "R"])
    assert code == run.EXIT_REFUSED
    err = capsys.readouterr().err
    assert "kill_switch" in err and "portfolio_r15" in err and "sandbox_target" in err


def test_the_cli_rejects_a_malformed_repository():
    with pytest.raises(SystemExit):
        run.main(["gates", "--repository", "not-a-repo"])
    with pytest.raises(SystemExit):
        run.main(["gates", "--repository", "../x/y"])


def test_the_gates_command_writes_the_outputs_and_the_report(tmp_path, monkeypatch):
    out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv(run.AUTHORIZATION_VARIABLE, "true")
    monkeypatch.setenv(run.SANDBOX_VARIABLE, TARGET)
    monkeypatch.setattr(run, "gate_portfolio", lambda readiness=None: run.Gate("portfolio_r15", False, "incomplete"))
    report = tmp_path / "gates.json"
    assert run.main(["gates", "--repository", TARGET, "--out", str(report), "--summary", str(tmp_path / "s.md")]) == run.EXIT_OK
    lines = dict(line.split("=") for line in out.read_text().splitlines())
    assert lines == {"allowlist": "true", "registry_full": "true", "kill_switch": "true", "portfolio_r15": "false",
                     "sandbox_target": "true", "write_eligible": "false"}
    assert [g["name"] for g in json.loads(report.read_text())] == list(run.GATE_NAMES)
