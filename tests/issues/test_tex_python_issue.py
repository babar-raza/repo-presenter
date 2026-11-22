"""R50 (owner, 2026-11-22), WP-4/WP-5: the TeX Python defect ('N of 119 .py files fail ast.parse at
181015d', approved 2026-10-16, never filed, fixed upstream 2026-11-06) as the issue system's
end-to-end test, in dry run.

Fixtures are real directories: a CLEAN tree (every file parses; the shape of upstream 07db3203,
0 of 248 failing) and a BROKEN tree (indentation collapsed to one space per level; the shape of
181015d, 102 of 119 failing). The recorded reproduction really runs (``python -I`` over the tree,
the production runner), is validated as hostile input, classified, and decided by the monitor.
Nothing here touches the network: the monitor runs ``offline`` or against an empty fake GitHub."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from repo_presenter.github.client import (
    UpstreamWriteForbiddenError,
    authorize_request,
    authorize_write,
)
from repo_presenter.issues.approval import evidence_digest, handoff_id
from repo_presenter.issues.dedup import fingerprint_marker
from repo_presenter.issues.file import (
    AUTHORIZATION_VARIABLE,
    write_authorized,
)
from repo_presenter.issues.filing_report import build_report
from repo_presenter.issues.model import load_handoff
from repo_presenter.issues.monitor import FileStore, run_cycle
from repo_presenter.issues.pilot import (
    SIMULATED_ISSUE_NUMBER,
    PilotError,
    load_pilot,
    load_reproductions,
    require_pilot,
)
from repo_presenter.issues.reproduce import run_reproductions

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
TEX = "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"
FP = "sha256:c00f9615a81bb9f3c77f45df5ded5036d8da0cce6d6dee01634a27b3f3659188"
HANDOFF = DATA / "issue_handoffs" / f"aspose-tex-foss__Aspose.TeX-FOSS-for-Python__{FP.removeprefix('sha256:')}.json"
OLD_REV = "181015d2eee3e19f8af3d84e4a932ac84ad47c7c"
NEW_REV = "07db320334a0a58e11107b6ca8092b2e5047c1f8"
BOT = "repository-presenter[bot]"
NOW = datetime(2026, 11, 22, 12, tzinfo=UTC)
GOOD = "def f(x):\n    for i in x:\n        print(i)\n    return x\n"
COLLAPSED = "def f(x):\n for i in x:\n print(i)\n return x\n"


def _tree(root: Path, good: int, bad: int) -> Path:
    root.mkdir(parents=True)
    for i in range(good):
        (root / f"ok_{i}.py").write_text(GOOD, encoding="utf-8")
    for i in range(bad):
        (root / f"bad_{i}.py").write_text(COLLAPSED, encoding="utf-8")
    return root


def _checks(checkout: Path, revision: str) -> dict[str, Any]:
    """The production reproduce step (real ``python -I`` over the fixture tree)."""
    return run_reproductions(TEX, checkout, revision=revision, now=lambda: NOW)


def _cycle(tmp_path: Path, checks: dict[str, Any], revision: str, *, run: str = "r1",
           pilot_path: Path | None = None, environment: dict[str, str] | None = None,
           fetch: Any = None, post: Any = None, patch: Any = None, offline: bool = True,
           ) -> tuple[str, dict[str, Any]]:
    kwargs: dict[str, Any] = {}
    if fetch is not None:
        kwargs.update(fetch=fetch, post=post, patch=patch)
    return run_cycle(
        TEX, store=FileStore(tmp_path / "state.json"), checks_payload=checks,
        environment=environment or {}, run_key=run, now=NOW, head=revision, offline=offline,
        pilot_path=pilot_path, **kwargs,
    )


# --------------------------------------------------------------------------- the monitor decision


def test_clean_tree_is_verified_resolved_and_the_close_is_planned_not_posted(tmp_path: Path) -> None:
    clean = _tree(tmp_path / "clean", good=6, bad=0)
    checks = _checks(clean, NEW_REV)
    (row,) = checks["results"]
    assert row["ran"] and row["exit_code"] == 0 and "FAILED/TOTAL 0/6" in row["output"]
    assert checks["toolchain"].get("python")  # the python runtime recorded its interpreter

    summary, doc = _cycle(tmp_path, checks, NEW_REV)
    (out,) = doc["cycles"][-1]["rows"]
    assert out["outcome"] == "VERIFIED_RESOLVED" and out["decision"] == "CLOSE"
    assert out["simulated"] is True and out["performed"] is False and out["issue"] == SIMULATED_ISSUE_NUMBER
    assert out["planned"]["state_change"] == "closed (completed)"
    comment = out["planned"]["comment"]
    assert NEW_REV in comment and "no longer reproduces" in comment and "FAILED/TOTAL 0/6" in comment
    assert "sha256:" in comment and "ast.parse" in comment and "npm" not in comment
    assert "DRY RUN" in summary and "NOT posted" in summary and "SIMULATED" in summary
    assert doc["dry_run_cycles"] == 1 and doc["live_cycles"] == 0
    assert doc["records"][FP]["handoff"]["source_revision"] == OLD_REV  # the OLD finding is the tracked one


def test_broken_tree_still_reproduces_and_a_dated_comment_is_planned(tmp_path: Path) -> None:
    broken = _tree(tmp_path / "broken", good=17, bad=102)
    checks = _checks(broken, OLD_REV)
    assert "FAILED/TOTAL 102/119" in checks["results"][0]["output"]  # the original finding's shape
    _, doc = _cycle(tmp_path, checks, OLD_REV)
    (out,) = doc["cycles"][-1]["rows"]
    assert out["outcome"] == "STILL_REPRODUCES" and out["decision"] == "COMMENT_STILL_REPRODUCES"
    assert out["performed"] is False and out["planned"]["state_change"] is None
    assert "still reproduces" in out["planned"]["comment"] and "FAILED/TOTAL 102/119" in out["planned"]["comment"]


def test_no_close_on_an_unparseable_or_empty_observation(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()  # 0 of 0 files fail: not a positive observation of a fix
    _, doc = _cycle(tmp_path, _checks(empty, NEW_REV), NEW_REV)
    (out,) = doc["cycles"][-1]["rows"]
    assert out["outcome"] == "NOT_VERIFIABLE" and out["decision"] == "NONE"


def test_the_script_does_not_count_itself_or_run_upstream_code(tmp_path: Path) -> None:
    tree = _tree(tmp_path / "tree", good=2, bad=0)
    (tree / "evil.py").write_text("raise SystemExit('executed upstream code')\n", encoding="utf-8")
    (tree / "sitecustomize.py").write_text("raise SystemExit('imported from cwd')\n", encoding="utf-8")
    out = _checks(tree, NEW_REV)["results"][0]
    assert out["exit_code"] == 0 and "FAILED/TOTAL 0/4" in out["output"]  # parsed, never executed/imported
    assert not list(tree.glob("repo-presenter-repro-*"))  # the script lives outside the checkout


# --------------------------------------------------------------------------- never a write


def _live_pilot(tmp_path: Path) -> Path:
    doc = json.loads((DATA / "issue_pilot.json").read_text("utf-8"))
    for entry in doc["repositories"]:
        entry["mode"] = "live"
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps(doc), "utf-8")
    return path


def test_a_simulated_record_is_never_written_for_even_with_every_live_gate_open(tmp_path: Path) -> None:
    from repo_presenter.github.token_provenance import TokenDecision

    writes: list[Any] = []

    def fetch(url: str, token: Any) -> tuple[int, Any]:
        return 200, []  # no upstream issue at all

    def write(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        writes.append((url, payload))
        return 201, {}

    clean = _tree(tmp_path / "clean", good=3, bad=0)
    checks = _checks(clean, NEW_REV)
    env = {AUTHORIZATION_VARIABLE: "1", "GH_APP_INSTALLATION_TOKEN": "ghs_test"}
    pilot = _live_pilot(tmp_path)
    # first cycle is always dry; the second has every gate open
    from repo_presenter.issues import monitor

    monitor_verify = lambda repo, tok: TokenDecision(True, tok, None, "ok")
    first = monitor.run_cycle(TEX, store=FileStore(tmp_path / "s.json"), checks_payload=checks, environment=env,
                              run_key="1", now=NOW, head=NEW_REV, fetch=fetch, post=write, patch=write,
                              pilot_path=pilot, verify_token=monitor_verify)
    second = monitor.run_cycle(TEX, store=FileStore(tmp_path / "s.json"), checks_payload=checks, environment=env,
                               run_key="2", now=NOW, head=NEW_REV, fetch=fetch, post=write, patch=write,
                               pilot_path=pilot, verify_token=monitor_verify)
    assert first[1]["cycles"][-1]["mode"] == "dry_run" and second[1]["cycles"][-1]["mode"] == "live"
    (row,) = second[1]["cycles"][-1]["rows"]
    assert row["performed"] is False and "simulated record" in row["error"]
    assert writes == []


def test_a_real_issue_with_the_fingerprint_replaces_the_simulated_record(tmp_path: Path) -> None:
    real = {
        "number": 12, "html_url": f"https://github.com/{TEX}/issues/12", "title": "t",
        "body": f"x\n\n{fingerprint_marker(FP)}\n", "user": {"login": BOT}, "state": "open",
        "state_reason": None, "created_at": "2026-10-20T08:53:22Z",
    }

    def fetch(url: str, token: Any) -> tuple[int, Any]:
        if "issues?state=all" in url:
            return 200, [real] if "page=1" in url else []
        return 200, []  # comments

    clean = _tree(tmp_path / "clean", good=3, bad=0)
    _, doc = _cycle(tmp_path, _checks(clean, NEW_REV), NEW_REV, fetch=fetch, offline=False,
                    post=lambda *a: (_ for _ in ()).throw(AssertionError("no write")),
                    patch=lambda *a: (_ for _ in ()).throw(AssertionError("no write")))
    (row,) = doc["cycles"][-1]["rows"]
    assert row["issue"] == 12 and row["simulated"] is False and row["decision"] == "CLOSE"


# --------------------------------------------------------------------------- pilot data


def test_tex_is_in_the_pilot_dry_run_only_and_not_in_the_write_allowlist() -> None:
    entry = require_pilot(TEX)
    assert entry.mode == "dry_run" and entry.effects == {"issue", "issue_comment"}
    allow = json.loads((DATA / "upstream_write_allowlist.json").read_text("utf-8"))
    assert TEX not in {e["repository"] for e in allow["repositories"]}
    registry = json.loads((DATA / "registry.json").read_text("utf-8"))
    rows = registry if isinstance(registry, list) else registry.get("entries") or registry.get("repositories")
    reg = next(e for e in rows if e["repository"] == TEX)
    assert reg["mode"] == "dry_run" and reg["issues_mode"] is None  # no README PR, no filing
    # the pilot grant never creates an issue, and a README pull request stays refused
    with pytest.raises(UpstreamWriteForbiddenError, match="never creates one"):
        authorize_request("POST", f"https://api.github.com/repos/{TEX}/issues", {"title": "t", "body": "b"})
    with pytest.raises(UpstreamWriteForbiddenError):
        authorize_write(TEX, "pull_request")


def test_the_committed_reproduction_is_the_original_defect() -> None:
    spec = load_reproductions(TEX)
    (repro,) = spec.reproductions
    assert spec.runtime == "python" and spec.prepare == ()
    assert repro.defect_fingerprint == FP and repro.recorded_revision == OLD_REV
    assert repro.issue_number == SIMULATED_ISSUE_NUMBER and FP in spec.simulated_by_fingerprint()
    assert repro.defect_class == "SOURCE_UNPARSEABLE"


def test_a_zero_issue_number_without_a_simulated_record_is_refused(tmp_path: Path) -> None:
    doc = json.loads((DATA / "issue_reproductions" / "aspose-tex-foss__Aspose.TeX-FOSS-for-Python.json").read_text("utf-8"))
    del doc["simulated_issues"]
    path = tmp_path / "r.json"
    path.write_text(json.dumps(doc), "utf-8")
    with pytest.raises(PilotError, match="simulated_issues"):
        load_reproductions(TEX, path)


def test_the_pilot_lists_both_repositories_with_typescript_first() -> None:
    assert list(load_pilot()) == [
        "aspose-3d-foss/aspose.3d-foss-for-typescript", TEX.lower(),
    ]


# --------------------------------------------------------------------------- the filing path (dry run)


def test_the_handoff_is_the_old_finding_and_matches_the_owner_approval_digest() -> None:
    handoff = load_handoff(HANDOFF)
    assert handoff.source_revision == OLD_REV and handoff.status == "HANDOFF_PENDING"
    assert handoff_id(handoff).endswith(FP.removeprefix("sha256:"))
    # the digest the owner approved on 2026-10-16 (old project ops/issue_approvals record)
    assert evidence_digest(handoff) == "sha256:085fcb7e351f42e50d9d6b04fe002cef46eda71f0451af87172745ba5dda2a27"


class _Approvals:
    def __init__(self, record: dict[str, Any] | None) -> None:
        self.record = record

    def read(self, identifier: str) -> str | None:
        return None if self.record is None else json.dumps(self.record)


def _approval(expires: str = "2026-11-15T11:28:29Z") -> dict[str, Any]:
    handoff = load_handoff(HANDOFF)
    return {
        "handoff_id": handoff_id(handoff), "repository": TEX, "evidence_digest": evidence_digest(handoff),
        "approver": "babar-raza", "approved_at": "2026-10-16T11:28:29Z", "expires_at": expires,
    }


def test_filing_dry_run_reports_every_closed_gate_and_the_issue_it_would_file() -> None:
    handoff = load_handoff(HANDOFF)
    report = build_report(handoff, approvals=_Approvals(_approval()), environment={},
                          now=datetime(2026, 10, 17, tzinfo=UTC))
    assert report["action"] == "REFUSED"
    gates = {g["gate"].split(" (")[0].split(" $")[0]: g for g in report["gates"]}
    assert gates["registry write gate"]["open"] is False and "issues_mode 'dry_run'" in gates["registry write gate"]["reason"]
    pilot_gate = next(g for g in report["gates"] if g["gate"].startswith("upstream write allowlist"))
    assert pilot_gate["open"] is False and "never creates one" in pilot_gate["reason"]
    kill = next(g for g in report["gates"] if g["gate"].startswith("kill switch"))
    assert kill["open"] is False and AUTHORIZATION_VARIABLE in kill["gate"]
    approval = next(g for g in report["gates"] if g["gate"].startswith("owner approval"))
    assert approval["open"] is True  # valid on 2026-10-17, inside its window
    assert report["issue"]["labels"] == ["repo-presenter", "defect:source_unparseable"]
    assert report["issue"]["body"].rstrip().endswith(fingerprint_marker(FP))
    assert report["issue"]["title"].startswith("Aspose.TeX FOSS for Python: 102 of 119")
    assert report["dedup"]["existing_records"] == [] and "SIMULATED" in report["dedup"]["simulated_tracking"]


def test_filing_dry_run_today_is_refused_on_an_expired_approval_and_a_stale_finding(tmp_path: Path) -> None:
    handoff = load_handoff(HANDOFF)
    clean = _tree(tmp_path / "clean", good=4, bad=0)
    checks = _checks(clean, NEW_REV)
    report = build_report(handoff, approvals=_Approvals(_approval()), environment={}, now=NOW,
                          checks_payload=checks, head=NEW_REV)
    approval = next(g for g in report["gates"] if g["gate"].startswith("owner approval"))
    assert approval["open"] is False and "expired" in approval["reason"]
    assert report["recheck"].endswith("the defect no longer reproduces")
    assert report["action"] == "REFUSED" and report["plan_filing"]["action"] == "REFUSED"


def test_filing_dry_run_with_a_fresh_approval_refuses_a_stale_finding() -> None:
    handoff = load_handoff(HANDOFF)
    record = _approval(expires="2026-12-20T00:00:00Z")
    record["approved_at"] = "2026-11-21T00:00:00Z"
    spec = load_reproductions(TEX).reproductions[0]
    payload = {
        "schema_version": 1, "repository": TEX, "revision": NEW_REV, "ran_at": "x", "toolchain": {"python": "3.13"},
        "prepared": True, "prepare": [],
        "results": [{"issue_number": 0, "defect_fingerprint": FP, "check_id": spec.check_id, "ran": True,
                     "exit_code": 0, "output": "FAILED/TOTAL 0/248\n", "truncated": False, "setup": []}],
    }
    report = build_report(handoff, approvals=_Approvals(record), environment={}, now=NOW,
                          checks_payload=payload, head=NEW_REV)
    assert next(g for g in report["gates"] if g["gate"].startswith("owner approval"))["open"] is True
    assert "stale finding" in report["plan_filing"]["refusal"]


def test_an_existing_upstream_issue_is_a_dedup_not_a_filing() -> None:
    handoff = load_handoff(HANDOFF)
    issue = {"number": 3, "html_url": f"https://github.com/{TEX}/issues/3", "body": fingerprint_marker(FP)}
    report = build_report(handoff, approvals=_Approvals(_approval(expires="2026-12-20T00:00:00Z")),
                          environment={}, now=NOW, issues=[issue])
    assert report["dedup"]["existing_records"] == ["upstream issue #3"]
    assert report["plan_filing"]["already_filed"] == {"number": 3} or report["plan_filing"]["action"] == "REFUSED"


# --------------------------------------------------------------------------- kill switch naming


@pytest.mark.parametrize(
    "env, expected",
    [
        ({}, False),
        ({AUTHORIZATION_VARIABLE: "1"}, True),
        ({AUTHORIZATION_VARIABLE: ""}, False),
        ({AUTHORIZATION_VARIABLE: "maybe"}, False),
    ],
)
def test_the_kill_switch_fails_closed(env: dict[str, str], expected: bool) -> None:
    assert write_authorized(env) is expected


def test_the_kill_switch_name_is_the_family_name() -> None:
    assert AUTHORIZATION_VARIABLE == "REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED"


# --------------------------------------------------------------------------- hosted wiring


def _wf(name: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def test_the_issues_workflow_matrix_equals_the_pilot_and_mints_only_for_live_repositories() -> None:
    wf = _wf("issues.yml")
    pilot = load_pilot()
    for job in ("reproduce", "maintain"):
        include = wf["jobs"][job]["strategy"]["matrix"]["include"]
        assert {f"{m['owner']}/{m['name']}".lower() for m in include} == set(pilot), job
        for m in include:
            slug = f"{m['owner']}/{m['name']}".lower()
            # a dry-run repository never holds a write-capable token; TypeScript keeps minting as before
            assert m["mint"] is (slug.startswith("aspose-3d-foss/")), slug
            assert m["runtime"] == ("python" if "Python" in m["name"] else "node")
    # the kill switch is wired under its one name and only in the maintain job
    maintain = json.dumps(wf["jobs"]["maintain"])
    assert "vars.REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED" in maintain
    assert "vars." not in json.dumps(wf["jobs"]["reproduce"])
    # the node toolchain is only set up for the node legs
    node_step = next(s for s in wf["jobs"]["reproduce"]["steps"] if str(s.get("uses", "")).startswith("actions/setup-node"))
    assert node_step["if"] == "${{ matrix.runtime == 'node' }}"


def test_the_run_request_issues_job_covers_every_pilot_repository_with_no_input() -> None:
    job = _wf("run-request-execute.yml")["jobs"]["issues"]
    assert job["uses"] == "./.github/workflows/issues.yml" and "with" not in job
