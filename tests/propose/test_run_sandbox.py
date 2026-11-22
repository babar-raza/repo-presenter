"""R17 / owner decision 2026-11-22 in the propose driver: the sandbox exemption from the R15 predicate (gate 4), the
separate sandbox entry for gate 1, the `--sandbox` dry-run payload and write. Fakes only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from repo_presenter.github import client as github_client
from repo_presenter.propose import run
from repo_presenter.propose.acceptance_evidence import AttestedAcceptance

SANDBOX = "babar-raza/repo-presenter"
TARGET = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"
REVISION = "a" * 40
README = "# Cells for Rust\n\nIntro.\n\n## Install\n\n```\ncargo add cells\n```\n"
VERDICTS = {"M1": True, "M2": True, "M3": True, "M4": True, "M5": True, "M6": True, "M7": True, "M10": True}
ENV = {run.AUTHORIZATION_VARIABLE: "true", run.SANDBOX_VARIABLE: SANDBOX}


@dataclass
class Ready:
    ready: bool = True
    text: str = "all terminal"

    def reason(self) -> str:
        return self.text


NOT_READY = lambda: Ready(False, "PORTFOLIO_INCOMPLETE: 80 of 80 cells do not have a terminal outcome")  # noqa: E731


def make_candidate(root: Path) -> run.Candidate:
    slug = root / "candidates" / TARGET.replace("/", "__")
    bundle = slug / REVISION
    bundle.mkdir(parents=True)
    data = README.encode()
    (bundle / "README.md").write_bytes(data)
    manifest = {"schema_version": 1, "state": "READY_FOR_PROPOSAL",
                "files": {"README.md": {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}}}
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (slug / "CURRENT").write_text(REVISION + "\n", encoding="utf-8")
    return run.load_candidate(TARGET, "R", root)


# --- gate 4: the sandbox exemption --------------------------------------------------------------------------------


def test_the_sandbox_passes_the_portfolio_gate_without_the_r15_predicate():
    def must_not_be_read():
        raise AssertionError("the R15 predicate must not be consulted for the sandbox")

    gate = run.gate_portfolio(must_not_be_read, target=SANDBOX, environment=ENV)
    assert gate.ok and "sandbox" in gate.detail


def test_a_non_sandbox_target_is_still_blocked_without_r15():
    gate = run.gate_portfolio(NOT_READY, target=TARGET, environment=ENV)
    assert gate.ok is False and "PORTFOLIO_INCOMPLETE" in gate.detail


def test_every_other_target_fails_closed_when_the_predicate_is_unreadable():
    def broken():
        raise RuntimeError("state remote unreachable")

    gate = run.gate_portfolio(broken, target=TARGET, environment=ENV)
    assert gate.ok is False and "unreadable" in gate.detail


@pytest.mark.parametrize("value", ["*", "", "babar-raza/*", "babar-raza/other", TARGET])
def test_a_wildcard_unset_or_other_value_is_never_a_sandbox_exemption(value):
    environment = {**ENV, run.SANDBOX_VARIABLE: value}
    for target in (SANDBOX, TARGET):
        assert run.gate_portfolio(NOT_READY, target=target, environment=environment).ok is False, (value, target)


def test_the_star_lift_still_leaves_r15_required_for_every_target():
    environment = {**ENV, run.SANDBOX_VARIABLE: "*"}
    gates = run.evaluate_gates(TARGET, environment, readiness=NOT_READY)
    closed = {g.name for g in gates if not g.ok}
    assert "portfolio_r15" in closed and "sandbox_target" not in closed  # '*' lifts gate 5 only, never gate 4
    assert run.evaluate_sandbox_gates(TARGET, environment, readiness=NOT_READY)[3].ok is False


def test_the_sandbox_repository_is_not_writable_through_the_normal_upstream_path():
    gates = run.evaluate_gates(SANDBOX, ENV, readiness=NOT_READY)
    closed = {g.name for g in gates if not g.ok}
    assert "allowlist" in closed and "registry_full" in closed  # it is not on the nine-repository allowlist
    assert not run.write_eligible(gates)


# --- the sandbox gate set ---------------------------------------------------------------------------------------


def test_every_sandbox_gate_holds_with_the_variables_set_and_r15_not_ready():
    gates = run.evaluate_sandbox_gates(TARGET, ENV, readiness=NOT_READY)
    assert [g.name for g in gates] == list(run.GATE_NAMES)
    assert all(g.ok for g in gates), [g for g in gates if not g.ok]
    assert run.write_eligible(gates)


@pytest.mark.parametrize(
    ("environment", "closed"),
    [
        ({run.AUTHORIZATION_VARIABLE: "true"}, {"allowlist", "portfolio_r15", "sandbox_target"}),
        ({**ENV, run.AUTHORIZATION_VARIABLE: ""}, {"kill_switch"}),
        ({**ENV, run.SANDBOX_VARIABLE: "*"}, {"allowlist", "portfolio_r15", "sandbox_target"}),
        ({**ENV, run.SANDBOX_VARIABLE: TARGET}, {"allowlist", "portfolio_r15", "sandbox_target"}),
    ],
)
def test_each_sandbox_gate_closes_alone_and_nothing_is_selected_by_a_wrong_value(environment, closed):
    gates = run.evaluate_sandbox_gates(TARGET, environment, readiness=NOT_READY)
    assert {g.name for g in gates if not g.ok} == closed


def test_the_sandbox_needs_the_candidate_registered_and_active_but_not_mode_full():
    assert run.gate_registry_listed("aspose-tex-foss/Aspose.TeX-FOSS-for-Python").ok  # registered, mode dry_run
    assert run.gate_registry_listed("someone/not-registered").ok is False


# --- the dry-run payload ------------------------------------------------------------------------------------------


@pytest.fixture
def accepted_review(monkeypatch):
    review = SimpleNamespace(verdict="ACCEPT", model_reviewed=True, pr_eligible=False)
    monkeypatch.setattr(run, "load_review_verdict", lambda path: review)
    return review


@pytest.fixture
def forbid_writes(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("a write function was called")

    for name in ("create_ref", "put_contents", "create_pull_request", "update_pull_request", "default_post", "default_put", "default_patch"):
        monkeypatch.setattr(github_client, name, boom)


def test_the_offline_sandbox_dry_run_makes_no_github_call_and_writes_nothing(tmp_path, forbid_writes, accepted_review):
    candidate = make_candidate(tmp_path)

    def no_call(*a, **k):
        raise AssertionError("a GitHub read was attempted offline")

    gates = run.evaluate_sandbox_gates(TARGET, ENV, readiness=NOT_READY)
    payload = run.build_sandbox_payload(candidate, gates, environment=ENV, read_token=None, offline=True,
                                        fetch_head=no_call, get_contents=no_call,
                                        acceptance_records=(AttestedAcceptance(TARGET, "R", REVISION, candidate.bytes_sha256, True, VERDICTS, {}, True, True),))
    assert payload["mode"] == "sandbox_dry_run" and payload["writes_performed"] == 0 and payload["github_calls"].startswith("none")
    assert payload["sandbox_repository"] == SANDBOX and payload["draft"] is True
    assert payload["files"] == [{"path": "sandbox/aspose-cells-foss__Aspose.Cells-FOSS-for-Rust/README.md",
                                 "sha256": hashlib.sha256(README.encode()).hexdigest(), "bytes": len(README.encode())}]
    assert payload["branch"].startswith("repository-presenter/sandbox/") and candidate.bytes_sha256[:12] in payload["branch"]
    assert payload["acceptance"]["state"] == "publication-ready" and payload["acceptance"]["binding"] == "content_bound"
    assert not any("acceptance contract" in r for r in payload["refusals"])
    lowered = (payload["title"] + payload["body"]).lower()
    assert "provenance" not in lowered and "attribution" not in lowered and "proposed by" not in lowered
    assert any("offline" in r for r in payload["refusals"]) and payload["write_eligible"] is False


def test_the_sandbox_dry_run_reports_a_candidate_with_no_attested_record_as_sealed(tmp_path, forbid_writes, accepted_review):
    candidate = make_candidate(tmp_path)
    gates = run.evaluate_sandbox_gates(TARGET, ENV, readiness=NOT_READY)
    payload = run.build_sandbox_payload(candidate, gates, environment=ENV, read_token=None, offline=True)
    assert payload["acceptance"]["state"] == "sealed" and payload["acceptance"]["records_at_revision"] == 0
    assert any("acceptance contract: classified 'sealed'" in r for r in payload["refusals"])


def test_with_no_sandbox_selected_the_dry_run_names_it_and_has_no_target(tmp_path, forbid_writes, accepted_review):
    candidate = make_candidate(tmp_path)
    gates = run.evaluate_sandbox_gates(TARGET, {run.AUTHORIZATION_VARIABLE: "1"}, readiness=NOT_READY)
    payload = run.build_sandbox_payload(candidate, gates, environment={}, read_token=None, offline=True)
    assert payload["sandbox_repository"] is None and payload["files"] == [] and payload["title"] is None
    assert any("no sandbox is selected" in r for r in payload["refusals"])


# --- the write ----------------------------------------------------------------------------------------------------


def test_the_sandbox_write_refuses_before_any_call_when_a_gate_is_closed(tmp_path, capsys):
    candidate = make_candidate(tmp_path)
    gates = run.evaluate_sandbox_gates(TARGET, {}, readiness=NOT_READY)
    assert run.run_sandbox_write(candidate, gates, environment={run.WRITE_TOKEN_VARIABLE: "ghs_w"}) == run.EXIT_REFUSED
    assert "refused by gate" in capsys.readouterr().err


def test_the_sandbox_write_needs_the_app_token(tmp_path):
    candidate = make_candidate(tmp_path)
    gates = run.evaluate_sandbox_gates(TARGET, ENV, readiness=NOT_READY)
    assert run.run_sandbox_write(candidate, gates, environment=ENV) == run.EXIT_REFUSED


def test_the_sandbox_write_calls_the_sandbox_effect_once_with_the_app_token(tmp_path, monkeypatch, accepted_review):
    candidate = make_candidate(tmp_path)
    gates = run.evaluate_sandbox_gates(TARGET, ENV, readiness=NOT_READY)
    monkeypatch.setattr(run, "fetch_default_branch_sha", lambda repo, token=None: SimpleNamespace(branch="main", sha=REVISION, error=None))
    seen = {}

    def fake(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(repository=SANDBOX, effected=True, reason="sandbox draft pull request opened", reason_code=None,
                               pr_url="https://github.com/babar-raza/repo-presenter/pull/9", branch="b", commit_written=True, pr_created=True)

    code = run.run_sandbox_write(candidate, gates, environment={**ENV, run.WRITE_TOKEN_VARIABLE: "ghs_w"}, propose=fake)
    assert code == run.EXIT_OK
    assert seen["token"] == "ghs_w" and seen["candidate_repository"] == TARGET and seen["sandbox_base_branch"] == "main"
    assert seen["readme_bytes_sha256"] == candidate.bytes_sha256
    body = seen["compose"]("# Cells for Rust\n\nOld.\n", "sandbox/x/README.md", candidate.bytes_sha256).body
    assert "provenance" not in body.lower()


def test_the_cli_sandbox_write_refuses_on_closed_gates_before_touching_the_state_remote(monkeypatch, capsys):
    def no_export(*a, **k):
        raise AssertionError("the state remote must not be read for a refused write")

    monkeypatch.setattr(run, "export_candidate", no_export)
    monkeypatch.setattr(run, "gate_portfolio", lambda readiness=None, **k: run.Gate("portfolio_r15", False, "incomplete"))
    for key in (run.AUTHORIZATION_VARIABLE, run.SANDBOX_VARIABLE):
        monkeypatch.delenv(key, raising=False)
    assert run.main(["write", "--sandbox", "--repository", TARGET, "--lane", "R"]) == run.EXIT_REFUSED
    assert "sandbox_target" in capsys.readouterr().err


def test_a_sandbox_pull_request_is_a_draft_even_though_the_sandbox_is_the_control_repository():
    sent = {}

    def write(url, token, payload):
        sent.update(payload)
        return 201, {"number": 1, "html_url": "u", "title": "t", "body": "b"}

    github_client.create_pull_request("babar-raza", "repo-presenter", title="t", body="b", head="h", base="main",
                                      token="x", write=write, draft=True)
    assert sent["draft"] is True
    sent.clear()
    github_client.create_pull_request("babar-raza", "repo-presenter", title="t", body="b", head="h", base="main", token="x", write=write)
    assert "draft" not in sent  # the control repository's other pull requests are unchanged
