"""Run requests (owner ruling 2026-11-06; trust redesign 2026-11-06): the push-triggered workflow is an
unprivileged trigger only; the privileged executor runs from main via workflow_run and accepts only current
main plus run-request.json, an allowed job, a registered target, from the tip of a run-requests/ branch."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
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


# --- the workflow_run trigger payload -------------------------------------------------------------------

OWN = "babar-raza/repo-presenter"


def _event(branch="run-requests/1", sha="0" * 40, **overrides):
    run = {
        "path": ".github/workflows/run-request.yml",
        "event": "push",
        "conclusion": "success",
        "head_branch": branch,
        "head_sha": sha,
        "head_repository": {"full_name": OWN},
    }
    run.update(overrides)
    return {"workflow_run": run, "repository": {"full_name": OWN}}


def test_a_successful_push_run_of_the_trigger_workflow_is_accepted():
    assert rr.check_trigger(_event()) == ("run-requests/1", "0" * 40)
    # GitHub may suffix the path with @ref; the file itself must still be the trigger workflow.
    assert rr.check_trigger(_event(path=".github/workflows/run-request.yml@refs/heads/run-requests/1"))


@pytest.mark.parametrize(
    "event, fragment",
    [
        ({}, "not a workflow_run event"),
        (_event(path=".github/workflows/evil.yml"), "unknown triggering workflow"),
        (_event(path=".github/workflows/evil.yml@x/.github/workflows/run-request.yml"), "unknown triggering workflow"),
        (_event(path=None), "unknown triggering workflow"),
        (_event(event="workflow_dispatch"), "not a push"),
        (_event(conclusion="failure"), "not 'success'"),
        (_event(conclusion=None), "not 'success'"),
        (_event(head_repository={"full_name": "attacker/fork"}), "not from this repository"),
        (_event(branch="main"), "not a run-requests/<id> branch"),
        (_event(branch="feature/run-requests/1"), "not a run-requests/<id> branch"),
        (_event(branch="run-requests/$(curl evil)"), "not a run-requests/<id> branch"),
        (_event(sha="HEAD"), "not a commit id"),
    ],
)
def test_every_other_trigger_is_refused(event, fragment):
    with pytest.raises(rr.RequestError, match=re.escape(fragment)):
        rr.check_trigger(event)


# --- real git: main plus run-request.json, read from the triggering commit as data ----------------------

GIT_ID = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _git(cwd, *args):
    return subprocess.run(["git", *GIT_ID, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Remote:
    """A stand-in for the GitHub repository (``origin``) plus the executor's checkout of ``main``."""

    def __init__(self, tmp_path):
        self.origin = tmp_path / "origin"
        for rel in ("scripts/run_request.py", ".github/workflows/run-request.yml",
                    ".github/workflows/run-request-execute.yml"):
            (self.origin / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, self.origin / rel)
        (self.origin / "data").mkdir()
        (self.origin / "data" / "registry.json").write_text(json.dumps({"entries": REGISTRY}), encoding="utf-8")
        _git(self.origin, "init", "-q", "-b", "main")
        self.commit_on("main", {}, "base")
        self.work = tmp_path / "work"
        _git(tmp_path, "clone", "-q", str(self.origin), str(self.work))
        self.event_path = tmp_path / "event.json"

    def commit_on(self, branch, files, message):
        if branch != "main":
            exists = subprocess.run(["git", "rev-parse", "--verify", "-q", f"refs/heads/{branch}"],
                                    cwd=self.origin, capture_output=True).returncode == 0
            _git(self.origin, "checkout", "-q", *([branch] if exists else ["-b", branch, "main"]))
        for rel, content in files.items():
            (self.origin / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.origin / rel).write_text(content, encoding="utf-8")
        _git(self.origin, "add", "-A")
        _git(self.origin, "commit", "-q", "--allow-empty", "-m", message)
        sha = _git(self.origin, "rev-parse", "HEAD")
        _git(self.origin, "checkout", "-q", "main")
        return sha

    def request(self, payload, branch="run-requests/1", extra=None):
        files = {"run-request.json": payload if isinstance(payload, str) else json.dumps(payload)}
        files.update(extra or {})
        return self.commit_on(branch, files, "request")

    def run(self, sha, branch="run-requests/1", monkeypatch=None, **overrides):
        self.event_path.write_text(json.dumps(_event(branch=branch, sha=sha, **overrides)), encoding="utf-8")
        monkeypatch.chdir(self.work)
        return rr.main(["--event", str(self.event_path)])


@pytest.fixture
def remote(tmp_path):
    return Remote(tmp_path)


def _refused(remote, monkeypatch, capsys, sha, fragment, **kw):
    assert remote.run(sha, monkeypatch=monkeypatch, **kw) == 1
    captured = capsys.readouterr()
    assert captured.out == ""  # nothing reaches $GITHUB_OUTPUT, so no privileged job runs
    assert fragment in captured.err


def test_main_plus_a_registered_present_request_passes(remote, monkeypatch, capsys):
    sha = remote.request(RUST)
    assert remote.run(sha, monkeypatch=monkeypatch) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["job=present", f"repository={RUST['repository']}", "ecosystem=rust", "lane=R", f"head_sha={sha}"]


def test_main_plus_a_mint_request_passes(remote, monkeypatch, capsys):
    sha = remote.request({"job": "mint"}, branch="run-requests/mint-2")
    assert remote.run(sha, branch="run-requests/mint-2", monkeypatch=monkeypatch) == 0
    assert "job=mint" in capsys.readouterr().out


@pytest.mark.parametrize(
    "extra",
    [
        # the push-triggered workflow rewritten on the branch (e.g. to call present.yml with secrets itself)
        {".github/workflows/run-request.yml": "name: run-request\non: push\njobs: {}\n"},
        # the privileged workflow rewritten on the branch (GitHub ignores it for workflow_run; so does this check)
        {".github/workflows/run-request-execute.yml": "name: run-request-execute\n"},
        # the validator rewritten on the branch to accept anything
        {"scripts/run_request.py": "def validate(*a):\n    return {'job': 'present'}\n"},
        # any other extra file
        {"evil.py": "x = 1\n"},
        # the registry widened on the branch to register an attacker repository
        {"data/registry.json": json.dumps({"entries": [{"repository": "evil/repo", "ecosystem": "rust"}]})},
    ],
)
def test_a_branch_that_changes_anything_besides_the_request_is_refused(remote, monkeypatch, capsys, extra):
    sha = remote.request(RUST, extra=extra)
    _refused(remote, monkeypatch, capsys, sha, "must change only")


def test_the_validator_that_runs_is_mains_not_the_branchs(remote, monkeypatch, capsys):
    """The branch's permissive validator is never executed: main's refuses the branch that carries it, and
    the executor's checkout still holds main's validator."""
    permissive = "import sys\nprint('job=present')\nsys.exit(0)\n"
    sha = remote.request({"job": "deploy"}, extra={"scripts/run_request.py": permissive})
    _refused(remote, monkeypatch, capsys, sha, "must change only")
    assert (remote.work / "scripts" / "run_request.py").read_text(encoding="utf-8") == (
        REPO / "scripts" / "run_request.py").read_text(encoding="utf-8")


def test_a_superseded_request_is_not_replayed(remote, monkeypatch, capsys):
    old = remote.request({"job": "mint"})
    new = remote.request(RUST)  # a newer commit on the same branch
    assert old != new
    _refused(remote, monkeypatch, capsys, old, "no longer the tip")
    assert remote.run(new, monkeypatch=monkeypatch) == 0


def test_a_deleted_request_branch_is_refused(remote, monkeypatch, capsys):
    sha = remote.request(RUST)
    _git(remote.origin, "branch", "-q", "-D", "run-requests/1")
    _refused(remote, monkeypatch, capsys, sha, "could not fetch")


def test_a_request_not_based_on_current_main_is_refused(remote, monkeypatch, capsys):
    sha = remote.request(RUST)
    remote.commit_on("main", {"README.md": "newer main\n"}, "main advances")
    _git(remote.work, "pull", "-q", "--ff-only")
    _refused(remote, monkeypatch, capsys, sha, "not based on the current main")


def test_stale_checked_out_code_is_refused(remote, monkeypatch, capsys):
    """main advanced after the executor checked out: refuse rather than run code not validated as current."""
    remote.commit_on("main", {"README.md": "newer main\n"}, "main advances")
    sha = remote.request(RUST, branch="run-requests/2")
    _refused(remote, monkeypatch, capsys, sha, "not the current main", branch="run-requests/2")


@pytest.mark.parametrize(
    "payload, fragment",
    [
        ({**RUST, "repository": "evil/repo"}, "not listed"),
        ({**RUST, "ecosystem": "python"}, "registered as"),
        ({"job": "deploy"}, "unknown job"),
        ({"job": "mint", "repository": "x/y"}, "takes no other field"),
        ({"job": "mint", "ref": "attacker-branch"}, "takes no other field"),
        ({**RUST, "lane": "X"}, "lane"),
        ("not json", "unreadable request"),
        ("[]", "not a JSON object"),
    ],
)
def test_a_bad_request_on_an_otherwise_clean_branch_is_refused(remote, monkeypatch, capsys, payload, fragment):
    sha = remote.request(payload)
    _refused(remote, monkeypatch, capsys, sha, fragment)


def test_a_bad_trigger_is_refused_for_a_clean_request(remote, monkeypatch, capsys):
    sha = remote.request(RUST)
    _refused(remote, monkeypatch, capsys, sha, "not 'success'", conclusion="failure")
    _refused(remote, monkeypatch, capsys, sha, "unknown triggering workflow", path=".github/workflows/other.yml")


# --- static: the workflow files themselves --------------------------------------------------------------


def _wf(name):
    wf = yaml.safe_load((REPO / ".github" / "workflows" / name).read_text(encoding="utf-8"))
    return wf, (wf["on"] if "on" in wf else wf[True])


def _write_scopes(permissions):
    if isinstance(permissions, str):
        return [] if permissions == "read-all" else [permissions]
    return [k for k, v in (permissions or {}).items() if v == "write"]


def test_the_push_triggered_workflow_holds_no_secret_and_no_write_scope():
    text = (REPO / ".github/workflows/run-request.yml").read_text(encoding="utf-8")
    wf, triggers = _wf("run-request.yml")
    assert wf["name"] == rr.TRIGGER_WORKFLOW.rsplit("/", 1)[1].removesuffix(".yml")
    assert set(triggers) == {"push"} and triggers["push"]["branches"] == ["run-requests/**"]
    assert wf["permissions"] == {"contents": "read"}
    assert "secrets" not in text
    for job in wf["jobs"].values():
        assert "uses" not in job, "the push-triggered workflow must not call a reusable workflow"
        assert not _write_scopes(job.get("permissions", {}))
        for step in job.get("steps", []):
            assert "actions/checkout" not in str(step.get("uses", "")), "it must not even check out the pushed code"


def test_the_privileged_workflow_runs_from_main_on_workflow_run_and_validates_first():
    wf, triggers = _wf("run-request-execute.yml")
    assert set(triggers) == {"workflow_run"}
    trig = triggers["workflow_run"]
    assert trig["workflows"] == ["run-request"] and trig["types"] == ["completed"]
    assert trig["branches"] == ["run-requests/**"]
    assert wf["permissions"] == {"contents": "read"}

    validate = wf["jobs"]["validate"]
    assert "secrets" not in validate and not _write_scopes(validate.get("permissions", {}))
    checkouts = [s for s in validate["steps"] if str(s.get("uses", "")).startswith("actions/checkout")]
    assert len(checkouts) == 1
    ref = str((checkouts[0].get("with") or {}).get("ref", ""))
    assert ref == "main"
    assert "head_sha" not in ref and "head_branch" not in ref and "github.sha" not in ref
    for step in validate["steps"]:
        assert "head_sha" not in json.dumps(step.get("with") or {})
    runs = [s["run"] for s in validate["steps"] if "run" in s]
    assert runs == ['python scripts/run_request.py --event "$GITHUB_EVENT_PATH" >> "$GITHUB_OUTPUT"']

    for name, path in (("present", "./.github/workflows/present.yml"),
                       ("mint", "./.github/workflows/tc-009a-mint-proof.yml")):
        job = wf["jobs"][name]
        assert job["needs"] == "validate"
        assert job["if"] == f"needs.validate.outputs.job == '{name}'"
        assert job["uses"] == path  # local path: resolves to the default-branch commit this run executes
        # present.yml's schedule-only cohort job holds actions: write; a caller must grant at least
        # its callee's permissions or GitHub refuses the file at startup (2026-11-13).
        expected = {"contents": "write", "actions": "write"} if name == "present" else {"contents": "write"}
        assert job["permissions"] == expected
    assert set(wf["jobs"]["present"]["with"]) == {"repository", "ecosystem", "lane"}
    assert "with" not in wf["jobs"]["mint"]


def test_the_called_workflow_interfaces_are_unchanged():
    _, present_on = _wf("present.yml")
    assert set(present_on["workflow_call"]["inputs"]) == {"repository", "ecosystem", "lane"}
    _, mint_on = _wf("tc-009a-mint-proof.yml")
    assert not (mint_on["workflow_call"] or {}).get("inputs")




def test_a_recertify_request_validates_and_takes_no_other_field():
    assert rr.validate({"job": "recertify"}, REGISTRY, OK, True)["job"] == "recertify"
    with pytest.raises(rr.RequestError, match="takes no other field"):
        rr.validate({"job": "recertify", "repository": "x/y"}, REGISTRY, OK, True)


def test_the_recertify_workflow_carries_no_llm_secret():
    """R10 re-certification makes zero provider calls; the workflow must not even hold the key."""
    text = (Path(__file__).resolve().parent.parent / ".github/workflows/recertify.yml").read_text()
    assert "GPT_OSS" not in text and "secrets." not in text
    assert "--all --write" in text


# --- the M9 audit jobs (owner R37, 2026-11-13): strict fields, a verified seed run, one open batch ----------

SEED = "43217648963"
FINDINGS = f"evidence/build/GATE5_DELIVERY_PROGRAM/M9_AUDIT/findings-{SEED}.json"
ADJ = f"evidence/build/GATE5_DELIVERY_PROGRAM/M9_AUDIT/adjudications-{SEED}.json"
CLOSED_HEADS = [
    "main",
    "audit-seed/run-43208002268", "acceptance-record/run-43208002268",  # the legacy, suffix-less record
    f"audit-seed/run-{SEED}", f"acceptance-record/run-{SEED}-43221294654",
    f"audit-findings/run-{SEED}",
]
ALL_FILES = (("main", FINDINGS), ("main", ADJ), (f"audit-findings/run-{SEED}", FINDINGS))


def _ctx(heads=CLOSED_HEADS, files=ALL_FILES, verify=None):
    calls = []

    def verify_seed_run(run_id):
        calls.append(run_id)
        if verify is not None:
            verify(run_id)

    ctx = rr.AuditContext(heads=heads, exists=lambda ref, path: (ref, path) in set(files),
                          verify_seed_run=verify_seed_run)
    ctx.calls = calls
    return ctx


def test_open_seed_batches_reads_the_real_branch_conventions():
    assert rr.open_seed_batches(CLOSED_HEADS) == []
    assert rr.open_seed_batches([*CLOSED_HEADS, "audit-seed/run-9", "audit-seed/run-10"]) == ["9", "10"]
    # a record of ANOTHER seed, or a malformed record branch, closes nothing
    assert rr.open_seed_batches(["audit-seed/run-5", "acceptance-record/run-55-1", "acceptance-record/run-5x"]) == ["5"]


def test_an_audit_seed_request_passes_only_while_no_batch_is_open():
    assert rr.validate({"job": "audit-seed"}, REGISTRY, OK, True, _ctx())["job"] == "audit-seed"
    with pytest.raises(rr.RequestError, match="seed batch run 77 is still open"):
        rr.validate({"job": "audit-seed"}, REGISTRY, OK, True, _ctx(heads=[*CLOSED_HEADS, "audit-seed/run-77"]))
    with pytest.raises(rr.RequestError, match="takes no other field"):
        rr.validate({"job": "audit-seed", "salt": "1"}, REGISTRY, OK, True, _ctx())
    with pytest.raises(rr.RequestError, match="cannot be verified"):
        rr.validate({"job": "audit-seed"}, REGISTRY, OK, True)


def test_audit_score_and_acceptance_write_pass_with_exact_fields_and_a_verified_seed_run():
    ctx = _ctx()
    out = rr.validate({"job": "audit-score", "seed_run_id": SEED, "findings_path": FINDINGS}, REGISTRY, OK, True, ctx)
    assert out == {"job": "audit-score", "repository": "", "ecosystem": "", "lane": "", "seed_run_id": SEED,
                   "findings_path": FINDINGS, "findings_ref": "", "adjudications_path": ""}
    assert ctx.calls == [SEED]
    out = rr.validate({"job": "acceptance-write", "seed_run_id": SEED, "findings_path": FINDINGS,
                       "findings_ref": f"audit-findings/run-{SEED}", "adjudications_path": ADJ},
                      REGISTRY, OK, True, _ctx())
    assert out["findings_ref"] == f"audit-findings/run-{SEED}" and out["adjudications_path"] == ADJ


@pytest.mark.parametrize(
    "job, fields, fragment",
    [
        ("audit-score", {"seed_run_id": 43217648963, "findings_path": FINDINGS}, "not a run id"),
        ("audit-score", {"seed_run_id": "4321x", "findings_path": FINDINGS}, "not a run id"),
        ("audit-score", {"seed_run_id": "0123", "findings_path": FINDINGS}, "not a run id"),
        ("audit-score", {"seed_run_id": f"{SEED};rm", "findings_path": FINDINGS}, "not a run id"),
        ("audit-score", {"seed_run_id": SEED}, "findings_path None"),
        ("audit-score", {"seed_run_id": SEED, "findings_path": FINDINGS.replace("M9_AUDIT/", "M9_AUDIT/../")},
         "is not"),
        ("audit-score", {"seed_run_id": SEED, "findings_path": "evidence/build/GATE5_DELIVERY_PROGRAM/M9_AUDIT/"
                         "findings-43213595013.json"}, "is not"),  # another round's findings
        ("audit-score", {"seed_run_id": SEED, "findings_path": "data/registry.json"}, "is not"),
        ("audit-score", {"seed_run_id": SEED, "findings_path": FINDINGS, "findings_ref": "main"}, "findings_ref"),
        ("audit-score", {"seed_run_id": SEED, "findings_path": FINDINGS, "findings_ref": "audit-findings/run-1"},
         "findings_ref"),
        ("audit-score", {"seed_run_id": SEED, "findings_path": FINDINGS, "adjudications_path": ADJ},
         "unknown fields"),  # adjudications are acceptance-write's alone
        ("audit-score", {"seed_run_id": SEED, "findings_path": FINDINGS, "token": "x"}, "unknown fields"),
        ("acceptance-write", {"seed_run_id": SEED, "findings_path": FINDINGS, "adjudications_path": "x.json"},
         "adjudications_path"),
    ],
)
def test_every_other_audit_field_is_refused(job, fields, fragment):
    with pytest.raises(rr.RequestError, match=re.escape(fragment)):
        rr.validate({"job": job, **fields}, REGISTRY, OK, True, _ctx())


def test_the_files_branches_and_seed_run_must_really_exist():
    request = {"job": "audit-score", "seed_run_id": SEED, "findings_path": FINDINGS}
    with pytest.raises(rr.RequestError, match="does not exist on main"):
        rr.validate(request, REGISTRY, OK, True, _ctx(files=()))
    with pytest.raises(rr.RequestError, match="is not a seed batch"):
        rr.validate(request, REGISTRY, OK, True, _ctx(heads=["main"]))
    with pytest.raises(rr.RequestError, match="there is no audit-findings"):
        rr.validate({**request, "findings_ref": f"audit-findings/run-{SEED}"}, REGISTRY, OK, True,
                    _ctx(heads=[h for h in CLOSED_HEADS if not h.startswith("audit-findings/")]))
    with pytest.raises(rr.RequestError, match="does not exist on main"):
        rr.validate({**request, "job": "acceptance-write", "adjudications_path": ADJ}, REGISTRY, OK, True,
                    _ctx(files=(("main", FINDINGS),)))

    def refuse(run_id):
        raise rr.RequestError(f"run {run_id} has no successful seed job")

    with pytest.raises(rr.RequestError, match="no successful seed job"):
        rr.validate(request, REGISTRY, OK, True, _ctx(verify=refuse))


# --- the seed run, verified through the GitHub API (faked: no network) -------------------------------------


def _api(run=None, jobs=None, artifacts=None, fail=False):
    base_run = {"id": int(SEED), "repository": {"full_name": OWN}, "path": ".github/workflows/audit-seed.yml",
                "event": "schedule", "head_branch": "main", "status": "completed", "conclusion": "success"}
    base_run.update(run or {})
    if jobs is None:
        jobs = [{"name": "gate", "conclusion": "success"}, {"name": "seed", "conclusion": "success"},
                {"name": "audit", "conclusion": "failure"}]
    if artifacts is None:
        artifacts = [{"name": f"m9-seed-manifest-{SEED}", "expired": False}]
    responses = {
        f"/actions/runs/{SEED}": base_run,
        f"/actions/runs/{SEED}/jobs?per_page=100": {"jobs": jobs},
        f"/actions/runs/{SEED}/artifacts?name=m9-seed-manifest-{SEED}": {"artifacts": artifacts},
    }

    def get(path):
        if fail:
            raise OSError("HTTP Error 404")
        return responses[path]
    return get


def test_a_completed_seed_run_with_a_successful_seed_job_and_its_manifest_artifact_is_verified():
    rr.verify_seed_run(SEED, OWN, _api())  # a later chain job failing does not unmake the seed
    rr.verify_seed_run(SEED, OWN, _api(run={"event": "workflow_dispatch"}))
    # the run-request override path: run-request-execute.yml calling audit-seed.yml (nested job name)
    rr.verify_seed_run(SEED, OWN, _api(
        run={"path": ".github/workflows/run-request-execute.yml", "event": "workflow_run", "head_branch": "main"},
        jobs=[{"name": "validate", "conclusion": "success"}, {"name": "audit-seed / seed", "conclusion": "success"}]))


@pytest.mark.parametrize(
    "api, fragment",
    [
        (_api(fail=True), "could not read run"),
        (_api(run={"id": 1}), "was not found"),
        (_api(run={"repository": {"full_name": "attacker/fork"}}), "belongs to"),
        (_api(run={"path": ".github/workflows/present.yml"}), "not of a seeding workflow"),
        (_api(run={"path": ".github/workflows/evil.yml@x/.github/workflows/audit-seed.yml"}), "not of a seeding"),
        (_api(run={"event": "push"}), "was started by"),
        (_api(run={"path": ".github/workflows/run-request-execute.yml", "event": "schedule"}), "was started by"),
        (_api(run={"event": "workflow_dispatch", "head_branch": "feature"}), "not main"),
        (_api(run={"status": "in_progress"}), "has not completed"),
        (_api(jobs=[{"name": "seed", "conclusion": "failure"}]), "no successful seed job"),
        (_api(jobs=[{"name": "present", "conclusion": "success"}]), "no successful seed job"),
        (_api(artifacts=[]), "no unexpired"),
        (_api(artifacts=[{"name": f"m9-seed-manifest-{SEED}", "expired": True}]), "no unexpired"),
        (_api(artifacts=[{"name": "m9-seed-manifest-1", "expired": False}]), "no unexpired"),
    ],
)
def test_every_other_seed_run_is_refused(api, fragment):
    with pytest.raises(rr.RequestError, match=re.escape(fragment)):
        rr.verify_seed_run(SEED, OWN, api)


def test_an_audit_score_request_end_to_end_through_real_git(remote, monkeypatch, capsys):
    """main holds the findings; the seed branch exists on origin; the API (faked) vouches for the run."""
    remote.commit_on("main", {FINDINGS: "[]\n"}, "findings via PR")
    remote.commit_on(f"audit-seed/run-{SEED}", {"x": "y"}, "seed")
    _git(remote.work, "pull", "-q", "--ff-only")
    monkeypatch.setattr(rr, "github_get_json", lambda repository, token: _api())
    sha = remote.request({"job": "audit-score", "seed_run_id": SEED, "findings_path": FINDINGS})
    assert remote.run(sha, monkeypatch=monkeypatch) == 0
    out = capsys.readouterr().out.splitlines()
    assert "job=audit-score" in out and f"seed_run_id={SEED}" in out and f"findings_path={FINDINGS}" in out

    sha = remote.request({"job": "audit-seed"}, branch="run-requests/2")
    _refused(remote, monkeypatch, capsys, sha, f"seed batch run {SEED} is still open", branch="run-requests/2")


def test_a_findings_file_that_exists_only_on_the_request_branch_is_refused(remote, monkeypatch, capsys):
    remote.commit_on(f"audit-seed/run-{SEED}", {"x": "y"}, "seed")
    monkeypatch.setattr(rr, "github_get_json", lambda repository, token: _api())
    sha = remote.request({"job": "audit-score", "seed_run_id": SEED, "findings_path": FINDINGS},
                         extra={FINDINGS: "[]\n"})
    _refused(remote, monkeypatch, capsys, sha, "must change only")


def test_the_executor_calls_the_m9_workflows_with_validated_inputs_and_minimal_permissions():
    wf, _ = _wf("run-request-execute.yml")
    validate = wf["jobs"]["validate"]
    assert validate["permissions"] == {"contents": "read", "actions": "read"}
    for key in ("seed_run_id", "findings_path", "findings_ref", "adjudications_path"):
        assert validate["outputs"][key] == f"${{{{ steps.check.outputs.{key} }}}}"
    expected = {
        "audit-seed": ("./.github/workflows/audit-seed.yml", set(),
                       {"contents": "write", "actions": "read", "id-token": "write", "attestations": "write"}),
        "audit-score": ("./.github/workflows/audit-score.yml", {"seed_run_id", "findings_path", "findings_ref"},
                        {"contents": "write", "actions": "read"}),
        "acceptance-write": ("./.github/workflows/acceptance-write.yml",
                             {"seed_run_id", "findings_path", "findings_ref", "adjudications_path"},
                             {"contents": "write", "actions": "read", "id-token": "write", "attestations": "write"}),
    }
    for name, (path, inputs, permissions) in expected.items():
        job = wf["jobs"][name]
        assert job["needs"] == "validate"
        assert job["if"] == f"needs.validate.outputs.job == '{name}'"
        assert job["uses"] == path
        assert job["secrets"] == "inherit"
        assert job["permissions"] == permissions
        assert set(job.get("with") or {}) == inputs
        for key, value in (job.get("with") or {}).items():
            assert value == f"${{{{ needs.validate.outputs.{key} }}}}"
