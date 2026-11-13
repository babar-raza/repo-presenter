"""R39 maintenance cycle: recording/dedup, the close/keep/reopen decisions, idempotency, the
dry-run default and the live gates -- against a fake GitHub, a local state file and the real
committed pilot data (whose write guard the fake transports still pass through)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.github.token_provenance import TokenDecision
from repo_presenter.issues.monitor import (
    FileStore,
    Issue,
    decide,
    record_issues,
    run_cycle,
)
from repo_presenter.issues.pilot import load_reproductions

PILOT = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"
BOT = "repository-presenter[bot]"
REV0 = "66cb26df3b031f0bf6976d4e88dc89721983afa4"
REV1 = "1" * 40
SPEC = load_reproductions(PILOT)
BY_ISSUE = {r.issue_number: r for r in SPEC.reproductions}
T0 = datetime(2026, 11, 13, 12, tzinfo=UTC)
LIVE_ENV = {"REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED": "1", "GH_APP_INSTALLATION_TOKEN": "ghs_test"}
ACTUAL = {4: "control points: 0 polygons: 0", 5: "eulerAngles is not a function",
          6: "Unsupported format: FbxFormat", 7: "Cannot find module 'adm-zip'", 8: "binary STL size: 50 bytes"}
FIXED = {4: "Tri control points: 3 polygons: 1", 5: "", 6: "Mesh control points: 3", 7: "",
         8: "vertex 10 20 30\nbinary STL size: 134 bytes"}


def _marker(n: int, legacy: bool = True) -> str:
    prefix = "repository-presenter-defect" if legacy else "repo-presenter-defect"
    return f"<!-- {prefix}: {BY_ISSUE[n].defect_fingerprint} -->"


class FakeGitHub:
    def __init__(self) -> None:
        self.issues: dict[int, dict[str, Any]] = {}
        self.comments: dict[int, list[dict[str, Any]]] = {}
        self.writes: list[tuple[str, str, dict[str, Any]]] = []
        self.now = T0

    def add(self, n: int, *, author: str = BOT, state: str = "open", body: str | None = None,
            reason: str | None = None, closed_by: str | None = None) -> None:
        self.issues[n] = {
            "number": n, "html_url": f"https://github.com/{PILOT}/issues/{n}", "title": f"issue {n}",
            "body": body if body is not None else f"Revision `{REV0}`\n\n{_marker(n)}\n",
            "user": {"login": author}, "state": state, "state_reason": reason,
            "created_at": "2026-10-20T08:53:22Z",
            "closed_by": {"login": closed_by} if closed_by else None,
        }
        self.comments.setdefault(n, [])

    def fetch(self, url: str, token: Any) -> tuple[int, Any]:
        path = url.split(f"/repos/{PILOT}/", 1)[1]
        if path.startswith("issues?state=all"):
            return 200, [{k: v for k, v in i.items() if k != "closed_by"} for i in self.issues.values()] if "page=1" in path else []
        n = int(path.split("/")[1].split("?")[0])
        if "/comments" in path:
            return 200, list(self.comments[n]) if "page=1" in path else []
        return 200, dict(self.issues[n])

    def post(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.writes.append(("POST", url, payload))
        n = int(url.rsplit("/", 2)[-2])
        self.comments[n].append({"body": payload["body"], "user": {"login": BOT},
                                 "created_at": self.now.strftime("%Y-%m-%dT%H:%M:%SZ")})
        return 201, {}

    def patch(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.writes.append(("PATCH", url, payload))
        n = int(url.rsplit("/", 1)[-1])
        self.issues[n]["state"] = payload["state"]
        self.issues[n]["state_reason"] = payload["state_reason"]
        self.issues[n]["closed_by"] = {"login": BOT} if payload["state"] == "closed" else None
        return 200, {}


def _checks(revision: str, outputs: dict[int, str]) -> dict[str, Any]:
    return {
        "schema_version": 1, "repository": PILOT, "revision": revision, "ran_at": "x",
        "toolchain": {"node": "v22.23.4", "npm": "10.9.9"}, "prepared": True, "prepare": [],
        "results": [
            {"issue_number": r.issue_number, "defect_fingerprint": r.defect_fingerprint, "check_id": r.check_id,
             "ran": True, "exit_code": 0, "output": outputs.get(r.issue_number, ACTUAL[r.issue_number]),
             "truncated": False, "setup": []}
            for r in SPEC.reproductions
        ],
    }


def _pilot(tmp_path: Path, mode: str) -> Path:
    doc = json.loads((Path(__file__).resolve().parents[2] / "data" / "issue_pilot.json").read_text("utf-8"))
    doc["repositories"][0]["mode"] = mode
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps(doc), "utf-8")
    return path


def _cycle(gh: FakeGitHub, tmp_path: Path, *, run: str, now: datetime, revision: str = REV0,
           outputs: dict[int, str] | None = None, mode: str = "live", env: dict[str, str] | None = None,
           checks: Any = "default", token_ok: bool = True) -> tuple[str, dict[str, Any]]:
    gh.now = now
    payload = _checks(revision, outputs or {}) if checks == "default" else checks
    return run_cycle(
        PILOT, store=FileStore(tmp_path / "state.json"), checks_payload=payload,
        environment=LIVE_ENV if env is None else env, run_key=run, now=now, head=revision,
        fetch=gh.fetch, post=gh.post, patch=gh.patch, pilot_path=_pilot(tmp_path, mode),
        verify_token=lambda repo, tok: TokenDecision(token_ok, tok if token_ok else None, None,
                                                     "ok" if token_ok else "wrong scope"),
    )


def _five(gh: FakeGitHub) -> None:
    for n in (4, 5, 6, 7, 8):
        gh.add(n)


# ----------------------------------------------------------------------------- recording / dedup


def _issue(n: int, **kw: Any) -> Issue:
    base = dict(number=n, url=f"u{n}", title=f"t{n}", author=BOT,
                state="open", state_reason=None, created_at="2026-10-20T00:00:00Z")
    base.update(kw)
    if "body" not in base:
        base["body"] = f"Revision `{REV0}` {_marker(n)}"
    return Issue(**base)


def test_only_the_apps_own_marked_issues_are_recorded_and_the_legacy_marker_is_read() -> None:
    issues = [_issue(4), _issue(5, body=f"x {_marker(5, legacy=False)}"), _issue(9, author="a-person", body=_marker(6)),
              _issue(10, body="no marker")]
    views, notes = record_issues(PILOT, issues, SPEC, bot_login=BOT)
    assert [v.issue.number for v in views] == [4, 5]
    assert all(v.verifiable for v in views)
    assert views[0].handoff.status == "FILED" and views[0].handoff.issue_ref.number == 4
    assert views[0].handoff.triggering_check.id == BY_ISSUE[4].check_id
    assert any("#10" in n for n in notes)
    assert sum("has no presenter issue upstream" in n for n in notes) == 3  # 6, 7, 8 absent here


def test_duplicates_collapse_to_the_lowest_number_and_are_never_touched() -> None:
    views, _ = record_issues(PILOT, [_issue(12, body=_marker(4)), _issue(4)], SPEC, bot_login=BOT)
    assert len(views) == 1
    # #4 is canonical; a reproduction that names #4 stays verifiable.
    assert views[0].issue.number == 4 and views[0].duplicates == (12,) and views[0].verifiable


def test_an_issue_with_no_reproduction_is_recorded_unverifiable() -> None:
    fp = "sha256:" + "e" * 64
    views, _ = record_issues(PILOT, [_issue(20, body=f"<!-- repository-presenter-defect: {fp} -->")], SPEC, bot_login=BOT)
    (view,) = views
    assert not view.verifiable and "never auto-closed" in view.reason
    assert view.handoff.triggering_check.id == "unverifiable:issue-20"
    # A reproduction recorded for a different issue number does not make it verifiable either.
    views, _ = record_issues(PILOT, [_issue(30, body=_marker(4))], SPEC, bot_login=BOT)
    assert not views[0].verifiable and "names issue #4" in views[0].reason


# ----------------------------------------------------------------------------- decisions


def _d(**kw: Any):
    base = dict(verifiable=True, outcome="STILL_REPRODUCES", issue_state="open", state_reason=None,
                closed_by_bot=False, reopened_revisions=(), revision=REV1,
                last_statement_at=T0 - timedelta(days=1), last_statement_revision=REV0, now=T0,
                interval_days=7, unchanged_interval_days=30)
    base.update(kw)
    return decide(**base).action


def test_decision_table() -> None:
    assert _d(outcome="VERIFIED_RESOLVED") == "CLOSE"
    assert _d(outcome="NOT_VERIFIABLE") == "NONE"
    assert _d(verifiable=False, outcome=None) == "NONE"
    assert _d(verifiable=False, outcome=None, issue_state="open") == "NONE"
    # dated re-check: at most once per interval, more rarely while the revision is unchanged
    assert _d() == "NONE"
    assert _d(last_statement_at=T0 - timedelta(days=7)) == "COMMENT_STILL_REPRODUCES"
    assert _d(revision=REV0, last_statement_at=T0 - timedelta(days=29)) == "NONE"
    assert _d(revision=REV0, last_statement_at=T0 - timedelta(days=30)) == "COMMENT_STILL_REPRODUCES"
    assert _d(last_statement_at=None) == "COMMENT_STILL_REPRODUCES"
    # closed
    assert _d(issue_state="closed", outcome="VERIFIED_RESOLVED") == "NONE"
    assert _d(issue_state="closed", state_reason="completed", closed_by_bot=True) == "REOPEN"
    assert _d(issue_state="closed", state_reason="completed", closed_by_bot=False) == "REOPEN"
    assert _d(issue_state="closed", state_reason="not_planned") == "NONE"
    assert _d(issue_state="closed", reopened_revisions=(REV0,), closed_by_bot=False) == "NONE"
    assert _d(issue_state="closed", reopened_revisions=(REV1,), closed_by_bot=True) == "NONE"
    assert _d(issue_state="closed", reopened_revisions=(REV0,), closed_by_bot=True) == "REOPEN"
    assert _d(issue_state="closed", outcome="NOT_VERIFIABLE") == "NONE"


# ----------------------------------------------------------------------------- cycles


def test_the_first_cycle_is_a_dry_run_even_with_every_live_gate_open(tmp_path: Path) -> None:
    gh = FakeGitHub()
    _five(gh)
    summary, doc = _cycle(gh, tmp_path, run="1", now=T0, outputs={4: FIXED[4]}, mode="live")
    assert gh.writes == []
    assert "DRY RUN" in summary and "first hosted cycle is always a dry run" in summary
    assert "would CLOSE #4" in summary
    assert doc["dry_run_cycles"] == 1 and doc["live_cycles"] == 0
    assert set(r["issue_number"] for r in doc["records"].values()) == {4, 5, 6, 7, 8}
    assert [e["event"] for e in doc["ledger"]] == ["IMPORTED"] * 5
    assert doc["cycles"][-1]["mode"] == "dry_run"


@pytest.mark.parametrize(
    "mode, env, token_ok, blocker",
    [
        ("dry_run", LIVE_ENV, True, "pilot mode is 'dry_run'"),
        ("live", {"GH_APP_INSTALLATION_TOKEN": "ghs_test"}, True, "kill switch"),
        ("live", {"REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED": "1"}, True, "no App installation token"),
        ("live", LIVE_ENV, False, "token refused"),
    ],
)
def test_every_live_gate_keeps_the_cycle_a_dry_run(tmp_path: Path, mode, env, token_ok, blocker) -> None:
    gh = FakeGitHub()
    _five(gh)
    _cycle(gh, tmp_path, run="1", now=T0)  # the mandatory first dry run
    summary, doc = _cycle(gh, tmp_path, run="2", now=T0, outputs={4: FIXED[4]}, mode=mode, env=env,
                          token_ok=token_ok)
    assert gh.writes == [] and blocker in summary and doc["cycles"][-1]["mode"] == "dry_run"


def test_live_close_keep_and_reopen_with_evidence_and_full_idempotency(tmp_path: Path) -> None:
    gh = FakeGitHub()
    _five(gh)
    _cycle(gh, tmp_path, run="1", now=T0)
    # A new upstream revision fixes #4; the others still reproduce there.
    t1 = T0 + timedelta(days=8)
    summary, doc = _cycle(gh, tmp_path, run="2", now=t1, revision=REV1, outputs={4: FIXED[4]})
    assert doc["cycles"][-1]["mode"] == "live"
    assert gh.issues[4]["state"] == "closed" and gh.issues[4]["state_reason"] == "completed"
    close_comment = gh.comments[4][0]["body"]
    assert REV1 in close_comment and "no longer reproduces" in close_comment and "sha256:" in close_comment
    for n in (5, 6, 7, 8):  # new revision, more than 7 days: one dated re-check each
        assert gh.issues[n]["state"] == "open"
        (comment,) = gh.comments[n]
        assert "still reproduces" in comment["body"] and REV1 in comment["body"] and t1.date().isoformat() in comment["body"]
    record4 = next(r for r in doc["records"].values() if r["issue_number"] == 4)
    assert record4["handoff"]["status"] == "RESOLVED_UPSTREAM" and record4["handoff"]["close_reason"] == "completed"
    assert record4["closed_by_us"]["revision"] == REV1
    events = [e["event"] for e in doc["ledger"]]
    assert events.count("CLOSED") == 1 and events.count("RECHECK_COMMENTED") == 4
    writes_after_cycle_2 = len(gh.writes)

    # A rerun of the same cycle and a new cycle the next day change nothing upstream.
    _, same = _cycle(gh, tmp_path, run="2", now=t1, revision=REV1, outputs={4: FIXED[4]})
    _, next_day = _cycle(gh, tmp_path, run="3", now=t1 + timedelta(days=1), revision=REV1, outputs={4: FIXED[4]})
    assert len(gh.writes) == writes_after_cycle_2
    assert len(same["cycles"]) == len(doc["cycles"])  # same run key: recorded once
    assert len(next_day["ledger"]) == len(doc["ledger"])

    # #4 regresses at a later revision: reopened once, with evidence; never twice at that revision.
    rev2 = "2" * 40
    _cycle(gh, tmp_path, run="4", now=t1 + timedelta(days=2), revision=rev2)
    assert gh.issues[4]["state"] == "open" and "reproduces again" in gh.comments[4][-1]["body"]
    gh.issues[4].update(state="closed", state_reason="completed", closed_by={"login": "a-maintainer"})
    _, final = _cycle(gh, tmp_path, run="5", now=t1 + timedelta(days=3), revision=rev2)
    assert gh.issues[4]["state"] == "closed"  # a maintainer re-closed after our reopen: left alone
    row = next(r for r in final["cycles"][-1]["rows"] if r["issue"] == 4)
    assert row["decision"] == "NONE" and "re-closed" in row["reason"]


def test_a_lost_state_write_does_not_cause_a_second_comment(tmp_path: Path) -> None:
    gh = FakeGitHub()
    _five(gh)
    _cycle(gh, tmp_path, run="1", now=T0)
    t1 = T0 + timedelta(days=8)
    _cycle(gh, tmp_path, run="2", now=t1, revision=REV1)
    posted = len(gh.writes)
    # Throw the state away (as if the state write had failed) but keep the first dry run on record.
    state = json.loads((tmp_path / "state.json").read_text("utf-8"))
    for record in state["records"].values():
        record.pop("last_statement", None)
    (tmp_path / "state.json").write_text(json.dumps(state), "utf-8")
    _cycle(gh, tmp_path, run="3", now=t1 + timedelta(days=1), revision=REV1)
    assert len(gh.writes) == posted  # the re-check comments were read back from upstream


def test_unverifiable_and_not_verifiable_records_are_never_written(tmp_path: Path) -> None:
    gh = FakeGitHub()
    _five(gh)
    gh.add(21, body="<!-- repository-presenter-defect: sha256:" + "d" * 64 + " -->")
    _cycle(gh, tmp_path, run="1", now=T0)
    summary, doc = _cycle(gh, tmp_path, run="2", now=T0 + timedelta(days=40), checks=None)
    assert gh.writes == []
    assert "every re-check is NOT_VERIFIABLE" in summary
    rows = {r["issue"]: r for r in doc["cycles"][-1]["rows"]}
    assert rows[21]["verifiable"] is False and rows[21]["decision"] == "NONE"
    assert all(rows[n]["decision"] == "NONE" for n in (4, 5, 6, 7, 8))


def test_checks_for_another_revision_are_refused(tmp_path: Path) -> None:
    gh = FakeGitHub()
    _five(gh)
    _cycle(gh, tmp_path, run="1", now=T0)
    gh.now = T0
    summary, _ = run_cycle(
        PILOT, store=FileStore(tmp_path / "state.json"), checks_payload=_checks(REV1, {4: FIXED[4]}),
        environment=LIVE_ENV, run_key="2", now=T0, head=REV0, fetch=gh.fetch, post=gh.post, patch=gh.patch,
        pilot_path=_pilot(tmp_path, "live"), verify_token=lambda r, t: TokenDecision(True, t),
    )
    assert gh.writes == [] and "not the upstream head" in summary


def test_a_human_authored_issue_is_never_touched(tmp_path: Path) -> None:
    gh = FakeGitHub()
    gh.add(4, author="a-person")
    _cycle(gh, tmp_path, run="1", now=T0)
    _, doc = _cycle(gh, tmp_path, run="2", now=T0, outputs={4: FIXED[4]})
    assert gh.writes == [] and doc["records"] == {}
