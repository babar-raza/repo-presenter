"""Owner ruling R39: the issue-management pilot allowlist and the recorded reproductions.

The committed allowlist names exactly one repository (widening is the owner's call), it is
enforced by the monitor before any read, and the write guard grants a pilot repository only
comments and state changes on existing issues -- never a new issue, never a title/body edit --
while the R3/R22 allowlist and the registry stay exactly as they were."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.github import client
from repo_presenter.github.client import (
    API_ROOT,
    UpstreamWriteForbiddenError,
    authorize_request,
    authorize_write,
)
from repo_presenter.issues.monitor import run_cycle
from repo_presenter.issues.pilot import (
    NotInPilotError,
    PilotError,
    load_pilot,
    load_reproductions,
    require_pilot,
)

PILOT = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"
ISSUES = f"{API_ROOT}/repos/{PILOT}/issues"
DATA = Path(__file__).resolve().parents[2] / "data"


def test_the_committed_pilot_is_exactly_the_typescript_3d_repository() -> None:
    pilot = load_pilot()
    assert [e.repository for e in pilot.values()] == [PILOT]
    entry = pilot[PILOT.lower()]
    assert entry.effects == {"issue", "issue_comment"}
    assert entry.bot_login == "repository-presenter[bot]"
    assert entry.mode in ("dry_run", "live")


def test_the_pilot_does_not_touch_the_r22_write_authority() -> None:
    allow = json.loads((DATA / "upstream_write_allowlist.json").read_text(encoding="utf-8"))
    assert PILOT not in {e["repository"] for e in allow["repositories"]}
    registry = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
    entries = registry if isinstance(registry, list) else registry.get("entries") or registry.get("repositories")
    entry = next(e for e in entries if e["repository"] == PILOT)
    assert entry["mode"] == "dry_run" and entry["issues_mode"] is None  # no README PR, no filing


def test_require_pilot_refuses_every_other_repository() -> None:
    assert require_pilot(PILOT).repository == PILOT
    with pytest.raises(NotInPilotError, match="owner's call"):
        require_pilot("aspose-3d-foss/Aspose.3D-FOSS-for-Python")


def test_the_monitor_refuses_an_unlisted_repository_before_any_read(tmp_path: Path) -> None:
    def fetch(url: str, token: Any) -> Any:
        raise AssertionError("no read may happen for an unlisted repository")

    with pytest.raises(NotInPilotError):
        run_cycle("aspose-cells-foss/Aspose.Cells-FOSS-for-Rust", store=None, checks_payload=None,  # type: ignore[arg-type]
                  environment={}, run_key="r", fetch=fetch)


@pytest.mark.parametrize(
    "content",
    [
        None,
        "{not json",
        {"schema_version": 2, "bot_login": "x[bot]", "repositories": []},
        {"schema_version": 1, "bot_login": "a-person", "repositories": []},
        {"schema_version": 1, "bot_login": "x[bot]", "repositories": [
            {"repository": PILOT, "effects": ["pull_request"], "mode": "dry_run",
             "recheck_comment_interval_days": 7, "unchanged_revision_comment_interval_days": 30}]},
        {"schema_version": 1, "bot_login": "x[bot]", "repositories": [
            {"repository": PILOT, "effects": ["issue"], "mode": "armed",
             "recheck_comment_interval_days": 7, "unchanged_revision_comment_interval_days": 30}]},
        {"schema_version": 1, "bot_login": "x[bot]", "repositories": [
            {"repository": PILOT, "effects": ["issue"], "mode": "live",
             "recheck_comment_interval_days": 0, "unchanged_revision_comment_interval_days": 30}]},
    ],
)
def test_a_malformed_pilot_file_grants_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: Any) -> None:
    path = tmp_path / "issue_pilot.json"
    if content is not None:
        path.write_text(content if isinstance(content, str) else json.dumps(content), "utf-8")
    with pytest.raises(PilotError):
        load_pilot(path)
    monkeypatch.setattr(client, "ISSUE_PILOT_ALLOWLIST", path)
    with pytest.raises(UpstreamWriteForbiddenError):
        authorize_write(PILOT, "issue_comment")


def test_the_write_guard_grants_the_pilot_comments_and_state_changes_only() -> None:
    assert authorize_request("POST", f"{ISSUES}/4/comments", {"body": "x"}).issue_pilot
    assert authorize_request("PATCH", f"{ISSUES}/4", {"state": "closed", "state_reason": "completed"}).issue_pilot
    assert authorize_request("PATCH", f"{ISSUES}/4", {"state": "open", "state_reason": "reopened"}).issue_pilot
    with pytest.raises(UpstreamWriteForbiddenError, match="never creates"):
        authorize_request("POST", ISSUES, {"title": "t", "body": "b"})
    with pytest.raises(UpstreamWriteForbiddenError, match="only state"):
        authorize_request("PATCH", f"{ISSUES}/4", {"state": "closed", "title": "renamed"})
    with pytest.raises(UpstreamWriteForbiddenError):
        authorize_write(PILOT, "pull_request")
    with pytest.raises(UpstreamWriteForbiddenError):
        authorize_request("POST", f"{API_ROOT}/repos/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues/1/comments", {"body": "x"})


def test_the_recorded_reproductions_cover_the_five_open_issues() -> None:
    spec = load_reproductions(PILOT)
    assert [r.issue_number for r in spec.reproductions] == [4, 5, 6, 7, 8]
    assert {r.recorded_revision for r in spec.reproductions} == {"66cb26df3b031f0bf6976d4e88dc89721983afa4"}
    assert {r.environment for r in spec.reproductions} == {"checkout", "consumer_omit_dev"}
    for r in spec.reproductions:
        assert r.reproduces_if_any and (r.resolved_if_all or r.resolved_if_output_empty)
        assert r.evidence and "require('./dist/aspose/threed')" in r.script


def test_a_reproduction_file_with_a_bad_entry_is_refused(tmp_path: Path) -> None:
    good = json.loads((DATA / "issue_reproductions" / "aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript.json").read_text("utf-8"))
    for mutate in (
        lambda d: d["reproductions"][0].update(resolved_if_all=[], resolved_if_output_empty=False),
        lambda d: d["reproductions"][1].update(defect_fingerprint=d["reproductions"][0]["defect_fingerprint"]),
        lambda d: d["reproductions"][0].update(reproduces_if_any=["("]),
        lambda d: d["reproductions"][0].update(recorded_revision="main"),
        lambda d: d.update(repository="someone/else"),
    ):
        doc = json.loads(json.dumps(good))
        mutate(doc)
        path = tmp_path / "r.json"
        path.write_text(json.dumps(doc), "utf-8")
        with pytest.raises(PilotError):
            load_reproductions(PILOT, path)
