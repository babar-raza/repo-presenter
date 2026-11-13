"""The M9 round runs itself on GitHub Actions (owner, 2026-11-13, R37): the scheduled gate (one open seed
batch at a time, an evidenced no-op otherwise), the hosted blind auditor's findings (exactly the shape the
scorer and the acceptance writer read; fail closed; never the manifest), the frozen bot-branch findings
the scorer and writer resolve, and the chain's wiring and attestation signer. No network, no provider
call, no real key: fake seals, a fake reviewer, a local git origin."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE, key_manifest_by_case_id
from repo_presenter.core.state.bundle_store import SealRecord
from repo_presenter.readme.review.findings import Finding
from repo_presenter.readme.review.verdict import ReviewUnavailable

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / ".github" / "workflows"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seeder = _load("run_m9_seeder")
auditor = _load("run_m9_auditor")
scorer = _load("run_m9_scorer")
writer = _load("run_acceptance_writer")
rr = auditor.run_request

SEED = "43300000001"
REVIEWED = {"verdict": "ACCEPT", "model_verdict": "ACCEPT", "unit_reviews": []}


# --- the gate -----------------------------------------------------------------------------------------


def test_no_open_batch_on_dispatch_or_override_seeds_with_this_runs_id():
    out = seeder.gate(["main"], run_id=SEED, require_fresh=False)
    assert out["action"] == "seed" and out["seed_run_id"] == SEED


def test_the_schedule_seeds_only_with_enough_fresh_candidates_else_an_evidenced_noop():
    out = seeder.gate(["main"], run_id=SEED, require_fresh=True, count_fresh=lambda: 9)
    assert out["action"] == "noop" and out["seed_run_id"] == "" and "9 fresh" in out["reason"]
    out = seeder.gate(["main"], run_id=SEED, require_fresh=True, count_fresh=lambda: 10)
    assert out["action"] == "seed" and "10 fresh" in out["reason"]


def test_an_open_batch_is_resumed_never_reseeded_and_its_checkpoints_are_read():
    heads = ["main", "audit-seed/run-5"]
    out = seeder.gate(heads, run_id=SEED, require_fresh=True, count_fresh=lambda: 99)
    assert out == {"action": "resume", "seed_run_id": "5", "has_findings": "false", "has_score": "false",
                   "reason": "seed batch 5 is open; finishing it before any new seed"}
    out = seeder.gate([*heads, "audit-findings/run-5", "audit-score/seed-run-5"], run_id=SEED, require_fresh=False)
    assert (out["action"], out["has_findings"], out["has_score"]) == ("resume", "true", "true")
    # written: the batch is closed, a new one may be seeded
    out = seeder.gate([*heads, "acceptance-record/run-5-6"], run_id=SEED, require_fresh=False)
    assert out["action"] == "seed"


def test_the_audit_is_retried_a_bounded_number_of_times_then_blocked():
    attempts = [f"audit-attempt/run-5-{n}" for n in range(1, seeder.MAX_AUDIT_ATTEMPTS + 1)]
    out = seeder.gate(["audit-seed/run-5", *attempts[:-1]], run_id=SEED, require_fresh=False)
    assert out["action"] == "resume"
    out = seeder.gate(["audit-seed/run-5", *attempts], run_id=SEED, require_fresh=False)
    assert out["action"] == "blocked" and "override" in out["reason"]
    # findings already frozen: scoring/writing is never blocked by audit attempts
    out = seeder.gate(["audit-seed/run-5", "audit-findings/run-5", *attempts], run_id=SEED, require_fresh=False)
    assert out["action"] == "resume"


def test_the_gate_cli_prints_github_outputs_and_fails_visibly_when_blocked(monkeypatch, capsys):
    heads = ["audit-seed/run-5", *[f"audit-attempt/run-5-{n}" for n in range(3)]]
    monkeypatch.setattr(seeder.run_request, "remote_heads", lambda remote: heads)
    monkeypatch.setattr("sys.argv", ["run_m9_seeder.py", "--gate", "--run-id", SEED])
    assert seeder.main() == 1
    assert "action=blocked" in capsys.readouterr().out.splitlines()
    monkeypatch.setattr(seeder.run_request, "remote_heads", lambda remote: ["main"])
    assert seeder.main() == 0
    assert f"seed_run_id={SEED}" in capsys.readouterr().out.splitlines()


def test_the_seed_step_itself_refuses_while_a_batch_is_open(monkeypatch, tmp_path):
    monkeypatch.setattr(seeder.run_request, "remote_heads", lambda remote: ["audit-seed/run-5"])
    monkeypatch.setattr(seeder, "seal_history", lambda **_: pytest.fail("must not even select"))
    monkeypatch.setattr("sys.argv", ["run_m9_seeder.py", "--refuse-if-open", "--out-dir", str(tmp_path)])
    assert seeder.main() == 1


def _seal(repo, lane, revision, *, review=REVIEWED, same=False):
    files = {"README.md": {"sha256": "a"}, "README.original.md": {"sha256": "a" if same else "b"}}
    return SealRecord(repo, lane, "c" * 40, revision, "ACCEPTED", {}, review, b"# x\n", files=files)


def test_fresh_candidates_are_counted_seals_not_yet_judged_as_a_control():
    by_lane = {
        "L": [("o/a", _seal("o/a", "L", "r1")), ("o/noop", _seal("o/noop", "L", "r1", same=True)),
              ("o/unreviewed", _seal("o/unreviewed", "L", "r1", review=None))],
        "R": [("o/b", _seal("o/b", "R", "r2")), ("o/c", _seal("o/c", "R", "r3")), ("o/d", _seal("o/d", "R", "r4"))],
    }
    judged = {("o/b", "R", "r2"): True, ("o/c", "R", "r3"): False, ("o/d", "R", "old"): False}
    assert seeder.fresh_candidates(by_lane, judged) == [("o/a", "L", "r1"), ("o/d", "R", "r4")]


# --- the hosted auditor's findings ----------------------------------------------------------------------

TEXT = "# Widget\n\nInstall:\n\n    pip install widget==9.9\n\nIt renders every format.\n"


def _finding(kind, quote, status="BLOCKING", clearance=None):
    return Finding(rule="llm_review", source="llm", message=f"{kind} here", claim_kind=kind, quote=quote,
                   status=status, clearance=clearance)


def test_findings_map_the_reviewer_verdict_to_the_scorer_shape_at_the_quoted_line():
    findings = [
        _finding("contradiction", "    pip install widget==9.9"),
        _finding("unsupported_claim", "It renders every format."),
        SimpleNamespace(status="CLEARED", claim_kind="contradiction", quote="# Widget", message="cleared",
                        evidence="", rule="r", source="llm"),
        _finding("omission", ""),  # nothing to locate
    ]
    rows = auditor.findings_for("case1", TEXT, findings)
    assert [(r["verdict"], r["line"], r["located"]) for r in rows] == [
        ("false", 5, True), ("unverifiable", 7, True), ("supported", 1, True),
        ("unverifiable", len(TEXT.splitlines()) + 1, False),  # past the end: flags, never matches a seed
    ]
    assert all(r["path"] == "case1.md" and r["candidate_id"] == "case1" for r in rows)
    assert writer.evidence_validity(rows) == (True, "")


def _cases():
    """A real seed plan from fake seals (the seeder's own operators), with the plaintext manifest."""
    readme = (REPO / "tests" / "test_run_m9_seeder.py").read_text(encoding="utf-8")
    template = readme.split('README_TEMPLATE = """', 1)[1].split('"""', 1)[0]
    by_lane = {lane: [(f"own:{lane}{i}", SealRecord(f"own:{lane}{i}", lane, "c" * 40, f"{i:04d}" + "a" * 36,
                                                    "ACCEPTED", {}, None,
                                                    template.format(name=f"{lane}w{i}").encode()))
                      for i in range(12)] for lane in ("L", "R")}
    case_index, manifest = seeder.build_seed_plan(by_lane, salt=7)
    return case_index, key_manifest_by_case_id(manifest)


def test_an_auditor_that_catches_every_seed_passes_the_real_scorer_and_writer_gates():
    case_index, manifest = _cases()
    truth = {m["candidate_id"]: m for m in manifest}
    texts = {e["case_id"]: e["text"] for e in case_index}

    def oracle(source, text):  # test-only: the real auditor never sees the manifest
        record = truth[source]
        if record["shape"] == CLEAN_SHAPE:
            return SimpleNamespace(verdict="ACCEPT", findings=())
        quote = text.splitlines()[record["line"] - 1]
        return SimpleNamespace(verdict="REJECT", findings=(_finding("contradiction", quote),))

    findings = auditor.audit_cases(case_index, texts, lambda e: e["case_id"], oracle)
    result = scorer.score(manifest, [scorer.Finding(f["candidate_id"], f["claim"], f["verdict"], f["path"],
                                                    f["line"]) for f in findings])
    # the oracle's quote is the seeded line's text; a duplicate earlier line would be the only miss
    assert result["seeded_recall"]["rate"] >= 0.9
    assert result["false_flag_rate"]["matched"] == 0
    gates, reasons = writer.evaluate_gates(manifest, findings)
    assert gates["evidence_validity"] is True


def test_an_unavailable_case_fails_the_whole_audit_and_no_partial_findings_are_returned():
    case_index, _ = _cases()
    texts = {e["case_id"]: e["text"] for e in case_index}
    calls = []

    def flaky(source, text):
        calls.append(source)
        if source == case_index[3]["case_id"]:
            raise ReviewUnavailable("gateway 502", [])
        return SimpleNamespace(verdict="ACCEPT", findings=())

    with pytest.raises(auditor.AuditError, match="no valid review"):
        auditor.audit_cases(case_index, texts, lambda e: e["case_id"], flaky)
    assert calls.count(case_index[3]["case_id"]) == 2  # one retry, then fail closed
    with pytest.raises(auditor.AuditError, match="no candidate text"):
        auditor.audit_cases(case_index, {}, lambda e: e["case_id"], flaky)


def test_a_missing_seal_is_an_audit_error_not_a_silent_skip():
    history = {("o/a", "L"): [SimpleNamespace(revision="r1", bundle=None, error="")]}
    with pytest.raises(auditor.AuditError, match="no readable seal"):
        auditor.seal_for(history, "o/a", "L", "r1")
    good = SimpleNamespace(revision="r1", bundle=Path("x"), error="")
    history[("o/a", "L")].append(good)
    assert auditor.seal_for(history, "o/a", "L", "r1") is good


def test_the_auditor_source_never_mentions_the_manifest_or_the_key():
    code = (REPO / "scripts" / "run_m9_auditor.py").read_text(encoding="utf-8")
    body = code.split('"""', 2)[2]  # past the module docstring
    assert "AUDIT_SEED_KEY" not in body and "seed_manifest" not in body and "decrypt" not in body


# --- frozen findings: main or the hosted auditor's bot branch ------------------------------------------

BOT = ["-c", "user.name=github-actions[bot]", "-c", f"user.email={rr.BOT_EMAIL}"]
PATH = rr.findings_path_for(SEED)


def _g(cwd, *args, ident=BOT):
    return subprocess.run(["git", *ident, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def origin(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    _g(origin, "init", "-q", "-b", "main")
    (origin / "README.md").write_text("main\n")
    _g(origin, "add", "-A")
    _g(origin, "commit", "-q", "-m", "base")
    work = tmp_path / "work"
    _g(tmp_path, "clone", "-q", str(origin), str(work))
    return origin, work


def _branch(origin, files, ident=BOT, commits=1, base="main"):
    _g(origin, "checkout", "-q", "-b", rr.findings_ref_for(SEED), base)
    for n in range(commits):
        for rel, content in files.items():
            (origin / rel).parent.mkdir(parents=True, exist_ok=True)
            (origin / rel).write_text(content + str(n) * n)
        _g(origin, "add", "-A")
        _g(origin, "commit", "-q", "-m", "findings", ident=ident)
    _g(origin, "checkout", "-q", "main")


def test_the_hosted_auditors_frozen_branch_resolves(origin):
    origin_dir, work = origin
    _branch(origin_dir, {PATH: "[]"})
    blob = auditor.resolve_findings(SEED, PATH, rr.findings_ref_for(SEED), cwd=work)
    assert blob == b"[]"


@pytest.mark.parametrize(
    "files, ident, commits, fragment",
    [
        ({PATH: "[]", "other.txt": "x"}, BOT, 1, "not only"),
        ({PATH: "[]"}, ["-c", "user.name=someone", "-c", "user.email=someone@example.com"], 1, "github-actions[bot]"),
        ({PATH: "[]"}, BOT, 2, "not one commit on top"),
    ],
)
def test_anything_but_one_bot_commit_adding_only_the_findings_is_refused(origin, files, ident, commits, fragment):
    origin_dir, work = origin
    _branch(origin_dir, files, ident=ident, commits=commits)
    with pytest.raises(auditor.AuditError, match=fragment.replace("[", r"\[").replace("]", r"\]")):
        auditor.resolve_findings(SEED, PATH, rr.findings_ref_for(SEED), cwd=work)


def test_a_wrong_round_path_or_ref_is_refused_and_main_is_read_directly(origin):
    origin_dir, work = origin
    with pytest.raises(auditor.AuditError, match="is not"):
        auditor.resolve_findings(SEED, rr.findings_path_for("1"), "", cwd=work)
    with pytest.raises(auditor.AuditError, match="findings ref"):
        auditor.resolve_findings(SEED, PATH, "audit-findings/run-1", cwd=work)
    with pytest.raises(auditor.AuditError, match="git failed"):
        auditor.resolve_findings(SEED, PATH, "", cwd=work)  # not on main
    (origin_dir / PATH).parent.mkdir(parents=True)
    (origin_dir / PATH).write_text("[1]")
    _g(origin_dir, "add", "-A")
    _g(origin_dir, "commit", "-q", "-m", "findings via PR")
    assert auditor.resolve_findings(SEED, PATH, "", cwd=work) == b"[1]"


# --- the chain's wiring --------------------------------------------------------------------------------


def _wf(name):
    doc = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    return doc, doc["on"] if "on" in doc else doc[True]


def test_the_hosted_audit_job_cannot_see_the_seed_key_or_the_manifest():
    doc, _ = _wf("audit-seed.yml")
    audit = doc["jobs"]["audit"]
    assert "environment" not in audit
    text = json.dumps(audit)
    assert "AUDIT_SEED_KEY" not in text and "m9-seed-manifest" not in text and "seed_manifest" not in text
    assert "secrets.GPT_OSS_ENDPOINT" in text and "secrets.GPT_OSS_API_KEY" in text
    assert audit["permissions"] == {"contents": "write", "actions": "read"}
    downloads = [s for s in audit["steps"] if "download-artifact" in str(s.get("uses"))]
    assert downloads and all("m9-seed-candidates-" in s["with"]["name"] for s in downloads)
    run = "\n".join(s.get("run", "") for s in audit["steps"])
    pushes = [line for line in run.splitlines() if line.strip().startswith("git push")]
    assert 'git push origin "audit-findings/run-${SEED}"' in pushes
    assert not any("--force" in p or " -f" in p or "+" in p for p in pushes)
    assert "refs/heads/main" not in run.split("audit-findings")[-1]  # never pushed to main


def test_the_round_runs_score_and_write_on_main_with_the_frozen_findings_after_the_audit():
    doc, triggers = _wf("audit-seed.yml")
    assert set(triggers) == {"schedule", "workflow_dispatch", "workflow_call"}
    gate_steps = doc["jobs"]["gate"]["steps"]
    assert "refs/heads/main" in gate_steps[0]["run"]
    assert "run_m9_seeder.py --gate" in gate_steps[-1]["run"]
    assert doc["jobs"]["seed"]["environment"] == "acceptance-audit"
    for name, path, permissions in (
        ("score", "./.github/workflows/audit-score.yml", {"contents": "write", "actions": "read"}),
        ("write", "./.github/workflows/acceptance-write.yml",
         {"contents": "write", "id-token": "write", "attestations": "write", "actions": "read"}),
    ):
        job = doc["jobs"][name]
        assert job["uses"] == path and job["secrets"] == "inherit" and job["permissions"] == permissions
        assert job["needs"] == ["gate", "audit"]
        assert job["with"]["findings_ref"] == "audit-findings/run-${{ needs.gate.outputs.seed_run_id }}"
        assert job["with"]["seed_run_id"] == "${{ needs.gate.outputs.seed_run_id }}"
        assert "needs.audit.result == 'success'" in job["if"]


@pytest.mark.parametrize("name", ["audit-score.yml", "acceptance-write.yml"])
def test_the_called_workflows_take_the_same_inputs_by_call_and_dispatch_and_stay_main_only(name):
    doc, triggers = _wf(name)
    assert set(triggers) == {"workflow_dispatch", "workflow_call"}
    assert set(triggers["workflow_call"]["inputs"]) == set(triggers["workflow_dispatch"]["inputs"])
    assert "findings_ref" in triggers["workflow_call"]["inputs"]
    (job,) = doc["jobs"].values()
    assert job["environment"] == "acceptance-audit"
    assert "refs/heads/main" in job["steps"][0]["run"]
    resolve = next(s for s in job["steps"] if "run_m9_auditor.py resolve" in s.get("run", ""))
    assert resolve["env"]["FINDINGS_REF"] == "${{ inputs.findings_ref }}"
    assert "inputs.findings_path" not in json.dumps([s for s in job["steps"] if s is not resolve])


def test_the_attestation_signer_is_still_exactly_acceptance_write_on_main():
    """Sigstore names a reusable workflow's own job_workflow_ref as the Build Signer, which is what
    `gh attestation verify --signer-workflow` matches, so a call from audit-seed.yml or
    run-request-execute.yml keeps the signer `.../acceptance-write.yml@refs/heads/main`. The counter's
    expected signer is unchanged and NOT widened; the callers that can reach it are exactly these two."""
    counter = (REPO / "ops" / "checks" / "portfolio_delivery_count.py").read_text(encoding="utf-8")
    assert 'ACCEPTANCE_WRITER = f"{ATTESTATION_REPO}/.github/workflows/acceptance-write.yml"' in counter
    doc, _ = _wf("acceptance-write.yml")
    attest = [s for s in doc["jobs"]["write"]["steps"] if "attest-build-provenance" in str(s.get("uses"))]
    assert len(attest) == 1
    callers = {
        path.name for path in WORKFLOWS.glob("*.yml")
        if "./.github/workflows/acceptance-write.yml" in path.read_text(encoding="utf-8")
    }
    assert callers == {"audit-seed.yml", "run-request-execute.yml"}
    seed_callers = {
        path.name for path in WORKFLOWS.glob("*.yml")
        if "./.github/workflows/audit-seed.yml" in path.read_text(encoding="utf-8")
    }
    assert seed_callers == {"run-request-execute.yml"}
