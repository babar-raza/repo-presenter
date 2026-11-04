"""Real tests for core/preflight.py (2026-11-04, P5 follow-up directive §8): warm cache (a
matching prior sealed bundle), cold start (no prior bundle at all), Actions-cache-eviction
equivalent (prior bundle present on disk but no local llm_cache -- irrelevant to this module,
which never touches llm_cache, only the committed bundle manifest), and changed-source negative
controls. Also proves the module never fabricates a skip for the scopes it cannot check."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repo_presenter.core.preflight import (  # noqa: E402
    CHECKED_SCOPES,
    UNCHECKED_SCOPES,
    load_current_bundle_manifest,
    preflight_decision,
)


def _seal_lane_r(candidates_root: Path, repository: str, revision: str) -> None:
    slug = repository.replace("/", "__")
    lane_root = candidates_root / "candidates" / slug
    rev_dir = lane_root / revision
    rev_dir.mkdir(parents=True)
    (rev_dir / "manifest.json").write_text(
        json.dumps({"source_revision": revision}), encoding="utf-8"
    )
    (lane_root / "CURRENT").write_text(revision, encoding="utf-8")


def test_cold_start_no_prior_bundle_never_skips(tmp_path: Path) -> None:
    decision = preflight_decision(
        candidates_root=tmp_path, repository="o/r", lane="R", current_source_revision="abc123",
    )
    assert decision.can_skip_provider_call is False
    assert "no prior sealed bundle" in decision.reason
    assert decision.checked_scopes == ()


def test_warm_matching_revision_still_never_fabricates_a_skip(tmp_path: Path) -> None:
    """The one scope this module CAN check (source) matches, but it must still refuse to skip,
    because the other scopes (prompts/policy/model/...) are not checkable -- this is the core
    honesty property, not a bug to be 'fixed' into a false green."""
    _seal_lane_r(tmp_path, "o/r", "abc123")
    decision = preflight_decision(
        candidates_root=tmp_path, repository="o/r", lane="R", current_source_revision="abc123",
    )
    assert decision.can_skip_provider_call is False
    assert "cannot yet be checked" in decision.reason
    assert decision.checked_scopes == CHECKED_SCOPES
    assert set(decision.unchecked_scopes) == set(UNCHECKED_SCOPES)


def test_changed_source_revision_is_a_real_negative_control(tmp_path: Path) -> None:
    _seal_lane_r(tmp_path, "o/r", "abc123")
    decision = preflight_decision(
        candidates_root=tmp_path, repository="o/r", lane="R", current_source_revision="def456",
    )
    assert decision.can_skip_provider_call is False
    assert "source revision changed" in decision.reason
    assert "abc123" in decision.reason and "def456" in decision.reason


def test_corrupt_manifest_is_never_trusted_as_current(tmp_path: Path) -> None:
    slug = "o__r"
    lane_root = tmp_path / "candidates" / slug
    rev_dir = lane_root / "abc123"
    rev_dir.mkdir(parents=True)
    (rev_dir / "manifest.json").write_text("{not valid json", encoding="utf-8")
    (lane_root / "CURRENT").write_text("abc123", encoding="utf-8")
    manifest = load_current_bundle_manifest(tmp_path, "o/r", "R")
    assert manifest is None


def test_missing_manifest_file_is_treated_as_no_prior_bundle(tmp_path: Path) -> None:
    slug = "o__r"
    lane_root = tmp_path / "candidates" / slug
    lane_root.mkdir(parents=True)
    (lane_root / "CURRENT").write_text("abc123", encoding="utf-8")
    # no manifest.json written under abc123/ at all
    assert load_current_bundle_manifest(tmp_path, "o/r", "R") is None


def test_empty_current_pointer_is_treated_as_no_prior_bundle(tmp_path: Path) -> None:
    slug = "o__r"
    lane_root = tmp_path / "candidates" / slug
    lane_root.mkdir(parents=True)
    (lane_root / "CURRENT").write_text("", encoding="utf-8")
    assert load_current_bundle_manifest(tmp_path, "o/r", "R") is None


def test_lane_l_uses_its_own_sibling_directory_not_lane_r_bundle(tmp_path: Path) -> None:
    """Lane R and Lane L bundles are stored under different sub-paths (core/candidates.py's own
    lane_directory) -- a Lane R seal must not be mistaken for a Lane L one."""
    _seal_lane_r(tmp_path, "o/r", "abc123")  # seals Lane R only
    decision_l = preflight_decision(
        candidates_root=tmp_path, repository="o/r", lane="L", current_source_revision="abc123",
    )
    assert decision_l.can_skip_provider_call is False
    assert "no prior sealed bundle" in decision_l.reason  # Lane L has nothing sealed yet
