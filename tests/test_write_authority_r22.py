"""Owner ruling R22 (docs/CONSOLIDATED_GOALS_2026-11-06.md Part E): ONE write authority.

The upstream-write allowlist and the registry's ``mode: full`` set must be the same nine
repositories (three R3 pilots plus the six inherited ``full`` entries), draft pull requests only,
and upstream issue filing is off on every repository. A disagreement between the two files would
mean one of them silently authorizes (or silently fails to authorize) a write, so CI fails on it.
Real committed files only -- no fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

from repo_presenter.core.registry.loader import load_registry

DATA = Path(__file__).resolve().parents[1] / "data"


def _allowlist() -> list[dict]:
    return json.loads((DATA / "upstream_write_allowlist.json").read_text(encoding="utf-8"))["repositories"]


def _registry():
    return load_registry(DATA / "registry.json")


def test_the_allowlist_and_the_registry_full_set_are_the_same_repositories() -> None:
    listed = {entry["repository"] for entry in _allowlist()}
    full = {entry.repository for entry in _registry().entries if entry.mode == "full"}
    assert listed == full, (
        f"allowlist-only: {sorted(listed - full)}; registry-full-only: {sorted(full - listed)}"
    )
    assert len(listed) == 9


def test_every_allowlisted_repository_is_a_draft_pull_request_only() -> None:
    for entry in _allowlist():
        assert entry["effects"] == ["pull_request"], entry["repository"]
        assert entry["first_pr_as_draft"] is True, entry["repository"]


def test_upstream_issue_filing_is_off_on_every_repository() -> None:
    armed = [e.repository for e in _registry().entries if e.effective_issues_mode == "file"]
    assert armed == []


def test_the_allowlist_has_no_duplicates() -> None:
    names = [entry["repository"] for entry in _allowlist()]
    assert len(names) == len(set(names))
