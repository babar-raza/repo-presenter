"""BL-772 (WP-9): the read-only metadata audit. No network: ``fetch`` is injected."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import httpx

from repo_presenter.monitor import metadata_audit as ma

REPO = "aspose-words-foss/Aspose.Words-FOSS-for-Python"
GOOD_TREE = ["README.md", "LICENSE", "SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
             ".github/ISSUE_TEMPLATE/bug.md", ".github/PULL_REQUEST_TEMPLATE.md", "docs/images/banner.png"]


def _fetch(repo: dict | None, profile: dict | None, tree: list[str] | None, calls: list[str] | None = None):
    def fetch(url: str, token: str | None) -> httpx.Response:
        if calls is not None:
            calls.append(url)
        if url.endswith("/community/profile"):
            body = profile
        elif "/git/trees/" in url:
            body = None if tree is None else {"tree": [{"path": p, "type": "blob", "sha": "a" * 40} for p in tree], "truncated": False}
        else:
            body = repo
        if body is None:
            return httpx.Response(404, json={})
        return httpx.Response(200, json=body)

    return fetch


GOOD_REPO = {"description": "A library.", "topics": ["aspose", "foss", "python"], "license": {"spdx_id": "MIT"},
             "default_branch": "main", "archived": False, "has_issues": True}
GOOD_PROFILE = {"health_percentage": 100, "files": {"readme": {}, "contributing": {}, "code_of_conduct": {},
                                                    "issue_template": {}, "pull_request_template": {}}}


def test_a_complete_repository_has_no_findings() -> None:
    row = ma.observe_repository(REPO, fetch=_fetch(GOOD_REPO, GOOD_PROFILE, GOOD_TREE))
    assert row["findings"] == [] and row["observed"]
    assert row["social_preview"].startswith("not observable")


def test_missing_metadata_is_reported_per_check() -> None:
    repo = {**GOOD_REPO, "description": None, "topics": ["python"], "license": None}
    row = ma.observe_repository(REPO, fetch=_fetch(repo, {"files": {}}, ["README.md"]))
    for check in ("description", "topics", "expected_topics", "license", "security_policy", "contributing",
                  "code_of_conduct", "issue_template", "pr_template", "visual_asset"):
        assert check in row["findings"], check
    assert "readme" not in row["findings"]


def test_an_unreadable_input_is_unknown_never_a_pass() -> None:
    row = ma.observe_repository(REPO, fetch=_fetch(GOOD_REPO, None, None))
    assert "unknown:security_policy" in row["findings"] and "unknown:visual_asset" in row["findings"]
    gone = ma.observe_repository(REPO, fetch=_fetch(None, None, None))
    assert not gone["observed"] and gone["findings"] == ["unknown:all"]


def test_the_audit_totals_and_markdown() -> None:
    rows = [{"repository": REPO, "family": "words", "platform": "python"}]
    report = ma.audit(rows, fetch=_fetch({**GOOD_REPO, "archived": True}, GOOD_PROFILE, GOOD_TREE))
    assert report["failing_by_check"]["not_archived"] == 1 and report["read_only"] is True
    text = ma.render_markdown(report)
    assert REPO in text and "not_archived" in text
    json.dumps(report)


def test_only_get_requests_are_made_and_the_module_has_no_write_call() -> None:
    calls: list[str] = []
    ma.observe_repository(REPO, fetch=_fetch(GOOD_REPO, GOOD_PROFILE, GOOD_TREE, calls))
    assert len(calls) == 3 and all(c.startswith("https://api.github.com/repos/") for c in calls)
    source = Path(ma.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not attrs & {"post", "put", "patch", "delete"}
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "repo_presenter.github.client" not in imported  # the write-capable client is never imported
