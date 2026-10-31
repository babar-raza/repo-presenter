"""The durable bundle store (core/state/bundle_store.py): a sealed bundle survives as a git ref.

Grounded in the 2026-10-31 status review: a hosted run kept its sealed bundle only in an
actions/cache entry and a 14-day artifact, so every hosted ACCEPT was non-durable. Tested against
real git on a disposable local remote, as tests/core/state/test_lane_state.py does.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from support import REPO_ROOT, init_git_repository

from repo_presenter.core.candidates import BundleError, lane_directory, lane_status
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.state.bundle_store import (
    BUNDLE_REF_PREFIX,
    BundleStoreError,
    bundle_ref,
    export_bundle,
    publish_bundle,
)

REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
SLUG = "aspose-3d-foss__Aspose.3D-FOSS-for-.NET"


def _seal(repository_dir: Path, lane: str, revision: str, readme: bytes) -> Path:
    """A minimal sealed bundle (manifest inventory with real digests) for ``lane``."""
    lane_root = lane_directory(repository_dir, lane)
    bundle = lane_root / revision
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "README.md").write_bytes(readme)
    manifest = {
        "schema_version": 2,
        "lane": lane,
        "state": "READY_FOR_PROPOSAL",
        "repository": REPO,
        "revision": revision,
        "files": {
            "README.md": {"sha256": hashlib.sha256(readme).hexdigest(), "bytes": len(readme)}
        },
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (lane_root / "CURRENT").write_text(revision + "\n", encoding="utf-8")
    return bundle


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    return init_git_repository(tmp_path / "remote")


def _ref_sha(remote: Path, ref: str) -> str | None:
    shown = run_git(["rev-parse", "--verify", "--quiet", ref], cwd=remote)
    return shown.stdout.strip() if shown.returncode == 0 else None


def _tree_files(remote: Path, ref: str) -> list[str]:
    listed = run_git(["ls-tree", "-r", "--name-only", ref], cwd=remote)
    assert listed.returncode == 0, listed.stderr
    return sorted(listed.stdout.split())


def test_the_bundle_ref_uses_the_record_ref_key_and_lane_suffix() -> None:
    assert bundle_ref(REPO) == f"{BUNDLE_REF_PREFIX}/{SLUG}"
    assert bundle_ref(REPO, "L") == f"{BUNDLE_REF_PREFIX}/{SLUG}@lane-l"


def test_a_published_bundle_exports_byte_for_byte_and_still_verifies(
    tmp_path: Path, remote: Path
) -> None:
    source = tmp_path / "candidates" / SLUG
    readme = b"line one\r\nline two\n\xc3\xa9\n"  # CRLF and non-ASCII: bytes must survive
    _seal(source, "R", "a" * 40, readme)
    published = publish_bundle(REPO, "R", source, remote=str(remote))
    assert published.changed and published.files == 3  # CURRENT, manifest.json, README.md
    assert _ref_sha(remote, published.ref) == published.commit

    exported = export_bundle(REPO, "R", tmp_path / "out", remote=str(remote))
    assert (exported / ("a" * 40) / "README.md").read_bytes() == readme
    assert lane_status(tmp_path / "out" / SLUG, "R").status == "READY_FOR_PROPOSAL"


def test_republishing_identical_content_pushes_nothing(tmp_path: Path, remote: Path) -> None:
    source = tmp_path / "candidates" / SLUG
    _seal(source, "R", "b" * 40, b"same\n")
    first = publish_bundle(REPO, "R", source, remote=str(remote))
    second = publish_bundle(REPO, "R", source, remote=str(remote))
    assert first.changed and not second.changed
    assert second.commit == first.commit == _ref_sha(remote, first.ref)


def test_a_new_revision_is_a_new_commit_on_top_of_the_previous_one(
    tmp_path: Path, remote: Path
) -> None:
    source = tmp_path / "candidates" / SLUG
    _seal(source, "R", "c" * 40, b"first\n")
    first = publish_bundle(REPO, "R", source, remote=str(remote))
    _seal(source, "R", "d" * 40, b"second\n")
    second = publish_bundle(REPO, "R", source, remote=str(remote))
    assert second.changed and second.commit != first.commit
    parent = run_git(["rev-parse", f"{second.commit}^"], cwd=remote).stdout.strip()
    assert parent == first.commit
    assert "d" * 40 + "/README.md" in _tree_files(remote, second.ref)


def test_each_lane_keeps_its_own_bundle_ref_and_lane_r_leaves_lane_l_out(
    tmp_path: Path, remote: Path
) -> None:
    source = tmp_path / "candidates" / SLUG
    _seal(source, "R", "e" * 40, b"lane r\n")
    _seal(source, "L", "f" * 40, b"lane l\n")
    r = publish_bundle(REPO, "R", source, remote=str(remote))
    l_ = publish_bundle(REPO, "L", source, remote=str(remote))
    assert r.ref != l_.ref and l_.ref.endswith("@lane-l")
    assert not any(name.startswith("lane-l/") for name in _tree_files(remote, r.ref))
    assert _tree_files(remote, l_.ref) == [
        "CURRENT",
        "f" * 40 + "/README.md",
        "f" * 40 + "/manifest.json",
    ]
    out = tmp_path / "out"
    export_bundle(REPO, "L", out, remote=str(remote))
    assert lane_status(out / SLUG, "L").status == "READY_FOR_PROPOSAL"
    assert lane_status(out / SLUG, "R").status == "NO_BUNDLE"


def test_a_tampered_bundle_is_refused_and_nothing_is_pushed(tmp_path: Path, remote: Path) -> None:
    source = tmp_path / "candidates" / SLUG
    bundle = _seal(source, "R", "9" * 40, b"honest\n")
    (bundle / "README.md").write_bytes(b"tampered\n")
    with pytest.raises(BundleError):
        publish_bundle(REPO, "R", source, remote=str(remote))
    assert _ref_sha(remote, bundle_ref(REPO, "R")) is None


def test_a_directory_with_no_current_pointer_is_not_published(
    tmp_path: Path, remote: Path
) -> None:
    source = tmp_path / "candidates" / SLUG
    source.mkdir(parents=True)
    with pytest.raises(BundleStoreError, match="CURRENT"):
        publish_bundle(REPO, "R", source, remote=str(remote))


def test_exporting_a_bundle_that_was_never_stored_fails_clearly(
    tmp_path: Path, remote: Path
) -> None:
    with pytest.raises(BundleStoreError, match="no stored bundle"):
        export_bundle(REPO, "R", tmp_path / "out", remote=str(remote))


def test_an_unreachable_remote_is_a_visible_store_error(tmp_path: Path) -> None:
    source = tmp_path / "candidates" / SLUG
    _seal(source, "R", "8" * 40, b"x\n")
    with pytest.raises(BundleStoreError):
        publish_bundle(REPO, "R", source, remote=str(tmp_path / "does-not-exist"))


def test_the_real_committed_bundle_round_trips_unchanged(tmp_path: Path, remote: Path) -> None:
    """The one real sealed bundle in the repository (3D-.NET, commit 6f8f9cb) goes through the
    store and comes back byte-identical, verified by the same code the status commands use."""
    source = REPO_ROOT / "candidates" / SLUG
    published = publish_bundle(REPO, "R", source, remote=str(remote))
    exported = export_bundle(REPO, "R", tmp_path / "out", remote=str(remote))
    original_files = sorted(
        p.relative_to(source).as_posix()
        for p in source.rglob("*")
        if p.is_file() and "lane-l" not in p.parts
    )
    assert _tree_files(remote, published.ref) == original_files
    for relative in original_files:
        assert (exported / relative).read_bytes() == (source / relative).read_bytes()
    assert lane_status(tmp_path / "out" / SLUG, "R").status == lane_status(source, "R").status


def test_a_relative_candidates_path_publishes(
    tmp_path: Path, remote: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first live run of the publish step failed with 'could not open candidates/<slug>/...':
    present.py defaults the candidates root to "." so the path it passes is relative, while every
    other test here used an absolute tmp_path, and the git plumbing runs in another directory."""
    _seal(tmp_path / "candidates" / SLUG, "R", "7" * 40, b"relative\n")
    monkeypatch.chdir(tmp_path)
    published = publish_bundle(REPO, "R", Path("candidates") / SLUG, remote=str(remote))
    assert published.changed and published.files == 3
    assert _tree_files(remote, published.ref)[0] == "7" * 40 + "/README.md"
