"""Push-triggered run requests (owner ruling 2026-11-06): only main plus run-request.json, only an
allowed job, only a registered target."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_request", REPO / "scripts" / "run_request.py")
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)

REGISTRY = [{"repository": "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust", "ecosystem": "rust"}]
OK = ["run-request.json"]
RUST = {"job": "present", "repository": "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust", "ecosystem": "rust", "lane": "R"}


def test_a_registered_present_request_passes():
    assert rr.validate(RUST, REGISTRY, OK, True) == {
        "job": "present", "repository": RUST["repository"], "ecosystem": "rust", "lane": "R"
    }
    assert rr.validate({"job": "mint"}, REGISTRY, OK, True)["job"] == "mint"


@pytest.mark.parametrize(
    "request_, changed, based, fragment",
    [
        (RUST, OK, False, "not based on the current main"),
        (RUST, ["run-request.json", "src/x.py"], True, "must change only"),
        (RUST, [], True, "must change only"),
        ({"job": "deploy"}, OK, True, "unknown job"),
        ({"job": "mint", "repository": "x/y"}, OK, True, "takes no other field"),
        ({**RUST, "repository": "evil/repo"}, OK, True, "not listed"),
        ({**RUST, "ecosystem": "python"}, OK, True, "registered as"),
        ({**RUST, "lane": "X"}, OK, True, "lane"),
        ({**RUST, "token": "x"}, OK, True, "unknown fields"),
    ],
)
def test_everything_else_is_refused(request_, changed, based, fragment):
    with pytest.raises(rr.RequestError, match=fragment):
        rr.validate(request_, REGISTRY, changed, based)


def test_the_workflow_validates_before_it_calls_anything():
    wf = yaml.safe_load((REPO / ".github/workflows/run-request.yml").read_text(encoding="utf-8"))
    triggers = wf["on"] if "on" in wf else wf[True]
    assert set(triggers) == {"push"} and triggers["push"]["branches"] == ["run-requests/**"]
    assert wf["permissions"] == {"contents": "read"}
    for name in ("present", "mint"):
        job = wf["jobs"][name]
        assert job["needs"] == "validate"
        assert job["permissions"] == {"contents": "write"}
    assert wf["jobs"]["present"]["uses"] == "./.github/workflows/present.yml"
    assert wf["jobs"]["mint"]["uses"] == "./.github/workflows/tc-009a-mint-proof.yml"
    called = yaml.safe_load((REPO / ".github/workflows/present.yml").read_text(encoding="utf-8"))
    called_on = called["on"] if "on" in called else called[True]
    assert set(called_on["workflow_call"]["inputs"]) == {"repository", "ecosystem", "lane"}


def _git(cwd, *args):
    import subprocess

    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_the_real_git_check_refuses_a_branch_that_changes_code(tmp_path, monkeypatch, capsys):
    import json as _json

    repo = tmp_path / "r"
    (repo / "data").mkdir(parents=True)
    (repo / "data" / "registry.json").write_text(_json.dumps({"entries": REGISTRY}), encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base")
    _git(repo, "checkout", "-q", "-b", "run-requests/1")
    (repo / "run-request.json").write_text(_json.dumps(RUST), encoding="utf-8")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "request")
    monkeypatch.chdir(repo)
    assert rr.main(["--base", "main"]) == 0
    assert "job=present" in capsys.readouterr().out
    (repo / "evil.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "smuggle")
    assert rr.main(["--base", "main"]) == 1
    assert "must change only" in capsys.readouterr().err
