"""Owner ruling R41 (2026-11-13; backlog BL-060): after every merge to main that changes the pipeline, every
candidate of both lanes is re-verified under the fixed code automatically, with evidence, and every cell that
no longer certifies is queued for re-production. Reuses the existing parts only (R27): recertify.yml gains a
push trigger and an evidence summary; cohort-chain.yml runs the cohort planner when it completes; the planner
already selects every cell whose latest seal does not certify under current code. Structural and zero-call,
like tests/test_cohort_chain.py: whether GitHub delivers the push and workflow_run events is what only a
hosted run proves."""

from __future__ import annotations

import inspect
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from repo_presenter import recertify
from repo_presenter.core.candidates import LANE_L, LANE_R
from repo_presenter.core.llm import budget
from repo_presenter.recertify import (
    OUTCOME_NEEDS_REPAIR,
    OUTCOME_RECERTIFIED,
    Recertification,
    reverification_summary,
)
from scripts.select_scheduled_cohort import plan_cohort

WORKFLOWS = ROOT / ".github" / "workflows"
EVIDENCE = re.compile(r"reverified: (\S+), lane R (\d+)/(\d+), lane L (\d+)/(\d+)")


def _load(name: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _on(doc: dict[str, Any]) -> dict[str, Any]:
    return doc["on"] if "on" in doc else doc[True]


def _glob(pattern: str) -> re.Pattern[str]:
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def _triggers(paths: list[str], changed: list[str]) -> bool:
    """GitHub's `paths` rule: a file matches when the LAST pattern that matches it is not a `!` one; the
    workflow runs when at least one changed file matches."""
    def included(path: str) -> bool:
        verdict = False
        for pattern in paths:
            negated = pattern.startswith("!")
            if _glob(pattern.lstrip("!")).match(path):
                verdict = not negated
        return verdict

    return any(included(path) for path in changed)


# --- the trigger: every push to main that changes the code a run executes ---------------------------


def test_a_push_to_main_that_changes_the_pipeline_triggers_it_and_nothing_else_does() -> None:
    on = _on(_load("recertify.yml"))
    assert set(on) == {"push", "workflow_call", "workflow_dispatch"}
    assert on["push"]["branches"] == ["main"]
    paths = on["push"]["paths"]
    for changed in (["src/repo_presenter/recertify.py"], ["prompts/x/manifest.json"], ["pyproject.toml"],
                    ["data/registry.json"], ["data/issue_reproductions/a.json"], ["docs/x.md", "src/a.py"]):
        assert _triggers(paths, changed), changed
    for changed in (["docs/DECISION_LOG.md"], ["project/backlog.yaml"], ["tests/test_x.py"],
                    ["data/provider_budget.json", "data/recertification_baseline.json"], [".github/workflows/x.yml"]):
        assert not _triggers(paths, changed), changed


def test_the_trigger_is_exactly_what_the_code_fingerprint_covers() -> None:
    """The planner re-opens a cell when its code fingerprint changes; the trigger must fire on the same set,
    or a fix could land with no re-verification (or an operational record re-run the portfolio)."""
    paths = _on(_load("recertify.yml"))["push"]["paths"]
    excluded = {p[len("!data/"):] for p in paths if p.startswith("!")}
    assert excluded == set(budget.OPERATIONAL_DATA_FILES)
    assert {p for p in paths if not p.startswith("!")} == {"src/**", "prompts/**", "pyproject.toml", "data/**"}
    source = inspect.getsource(budget.code_fingerprint)
    assert '"src", "prompts", "pyproject.toml", "data"' in source


def test_one_re_certification_at_a_time_whoever_started_it() -> None:
    doc = _load("recertify.yml")
    # job-level, so it binds a run-request call too; no workflow-level group of the same name (deadlock)
    assert "concurrency" not in doc
    job = doc["jobs"]["recertify"]
    assert job["concurrency"] == {"group": "recertify", "cancel-in-progress": False}
    assert doc["permissions"] == {"contents": "write"}
    assert "permissions" not in job or job["permissions"] == {"contents": "write"}


def test_it_writes_every_seal_zero_call_and_reports_the_r41_evidence() -> None:
    steps = _load("recertify.yml")["jobs"]["recertify"]["steps"]
    text = json.dumps(steps)
    assert "secrets." not in text and "GPT_OSS" not in text
    checkout = steps[0]
    assert checkout["with"]["persist-credentials"] is False and checkout["with"]["fetch-depth"] == 0
    run = next(s for s in steps if "--all --write" in str(s.get("run", "")))
    assert "set -o pipefail" in run["run"], "a failed publish must fail the job"
    for flag in ("--base-baseline .recertify/before.json", "--summary .recertify/summary.md",
                 '--run-id "${{ github.run_id }}"'):
        assert flag in run["run"]
    before = next(s for s in steps if "before.json" in str(s.get("run", "")) and s is not run)
    assert before["env"] == {"BEFORE_SHA": "${{ github.event.before }}"}  # never interpolated into the script
    report = steps[-1]
    assert report["if"] == "always()" and "GITHUB_STEP_SUMMARY" in report["run"]
    assert report["run"].index("summary.md") < report["run"].index("log.txt"), "results first (R11)"


def test_its_completion_runs_the_cohort_planner() -> None:
    run = _on(_load("cohort-chain.yml"))["workflow_run"]
    assert _load("recertify.yml")["name"] in run["workflows"]


# --- the summary: per-lane before/after and the evidence line ------------------------------------


def _rec(repository: str, lane: str, outcome: str = OUTCOME_RECERTIFIED, checks: tuple[str, ...] = ()) -> Recertification:
    return Recertification(repository, lane, "rev", outcome, checks, sealed_version_set="v1",
                           current_version_set="v2", seal_commit="c" * 40)


RESULTS = [
    _rec("o/a", LANE_R), _rec("o/b", LANE_R, OUTCOME_NEEDS_REPAIR, ("BC-05",)),
    _rec("o/a", LANE_L), _rec("o/b", LANE_L), _rec("o/c", LANE_L, OUTCOME_NEEDS_REPAIR, ("L-03", "L-05")),
]
BEFORE = {"seals": [
    {"repository": "o/a", "lane": "R", "commit": "1", "outcome": OUTCOME_RECERTIFIED},
    {"repository": "o/b", "lane": "R", "commit": "2", "outcome": OUTCOME_RECERTIFIED},
    {"repository": "o/a", "lane": "L", "commit": "3", "outcome": OUTCOME_NEEDS_REPAIR},
]}


def test_the_summary_leads_with_the_evidence_line_backlog_check_requires() -> None:
    text = reverification_summary(RESULTS, BEFORE, run_id="4242", run_url="https://x/runs/4242",
                                  published=["o/a lane R"])
    match = EVIDENCE.search(text)
    assert match and match.groups() == ("4242", "1", "2", "2", "3")
    assert text.index("reverified:") < text.index("| lane |")
    assert "| R | 2/2 | 1/2 |" in text and "| L | 0/1 | 2/3 |" in text
    assert "Seals re-written under this code: 1; publish failures: 0." in text


def test_every_cell_that_no_longer_certifies_is_listed_as_queued() -> None:
    text = reverification_summary(RESULTS, None, run_id="1")
    assert "2 cells no longer certify" in text
    assert "| o/b | R | cccccccccccc | BC-05 |" in text and "| o/c | L | cccccccccccc | L-03, L-05 |" in text
    assert "| R | 0/0 |" in text  # an unreadable baseline is reported as nothing, never invented
    clean = reverification_summary([_rec("o/a", LANE_R)], BEFORE, run_id="1")
    assert "nothing to re-produce" in clean


def test_the_planner_selects_exactly_the_cells_the_summary_queues() -> None:
    """Verified from the planner's code, not assumed: a cell whose seal no longer certifies is selected
    even though its last attempt ran on the same upstream revision, because the code changed."""
    class Entry:
        def __init__(self, repository: str) -> None:
            self.repository, self.ecosystem, self.active = repository, "python", True

    entries = {name: Entry(name) for name in ("o/a", "o/b", "o/c")}
    now = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
    settle = {"kind": "settle", "id": "cohort-1-1-1", "repository": "o/c", "outcomes": {"L": "failure"},
              "sealed": [], "code": "old-code", "source_revision": "b" * 40, "at": now.isoformat(), "epoch": 2}
    plan = plan_cohort(
        entries=entries, authorized_repos=set(entries),
        certifications={(r.repository, r.lane): r for r in RESULTS}, ledger={"entries": [settle]},
        terminals=[], code="new-code", head=lambda _repo: "b" * 40, now=now,
    )
    selected = {(run["repository"], lane) for run in plan["runs"] for lane in run["lanes"]}
    queued_by_summary = {(r.repository, r.lane) for r in RESULTS if not r.certified}
    # o/c lane R has no seal at all (never a candidate) and is also selected; every failing cell is in
    assert queued_by_summary <= selected
    assert not selected & {(r.repository, r.lane) for r in RESULTS if r.certified}


def test_write_mode_writes_the_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from repo_presenter.core import version_set
    from repo_presenter.core.llm import prompts as prompts_module
    from repo_presenter.core.state import bundle_store

    failing = [r for r in RESULTS if not r.certified]  # nothing to publish: no remote is touched
    monkeypatch.setattr(bundle_store, "seal_history", lambda **_kw: {(r.repository, r.lane): [] for r in failing})
    monkeypatch.setattr(recertify, "recertify_history", lambda *_a, **_kw: failing)
    monkeypatch.setattr(prompts_module, "load_manifests", lambda _p: {})
    monkeypatch.setattr(version_set, "current_fingerprints", lambda _p: {})
    before = tmp_path / "before.json"
    before.write_text(json.dumps(BEFORE), encoding="utf-8")
    summary = tmp_path / "out" / "summary.md"
    code = recertify.main(["--all", "--write", "--remote", str(tmp_path / "none"),
                           "--registry", str(ROOT / "data" / "registry.json"),
                           "--base-baseline", str(before), "--summary", str(summary), "--run-id", "99"])
    assert code == 0
    match = EVIDENCE.search(summary.read_text(encoding="utf-8"))
    assert match and match.groups() == ("99", "0", "1", "0", "1")


def test_summary_needs_write() -> None:
    with pytest.raises(SystemExit):
        recertify.main(["--all", "--summary", "x.md"])
