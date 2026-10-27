"""Real local git plumbing for the candidates-publish effect (G7-W14), against a disposable local
repository standing in for this control repository's own ``origin`` - no network, but real git
subprocesses, exactly like ``tests/core/state/test_git_backend.py``'s own discipline. This is the
one place this change is proven against *real* git mechanics rather than an injected fake: branch
creation, a fast-forward continuation of a pending branch, idempotent "nothing to commit", and
pushing to a real (local) remote.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from support import init_git_repository

from repo_presenter.candidates_publish.git_ops import (
    checkout_branch,
    overlay_bundle,
    push_branch,
    read_committed_file,
    remote_branch_sha,
    stage_and_commit,
)
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.github.errors import RepositoryMetadataError

SLUG = "aspose-cells-foss__Aspose.Cells-FOSS-for-Go"
BRANCH = f"repository-presenter/candidates-update/{SLUG}"


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    """A disposable local repository standing in for this control repository's own origin, with
    an initial ``candidates/<slug>/CURRENT`` naming an "old" revision already committed."""
    repo = init_git_repository(tmp_path / "remote", with_commit=False)
    bundle = repo / "candidates" / SLUG
    bundle.mkdir(parents=True)
    (bundle / "CURRENT").write_text("a" * 40 + "\n", encoding="utf-8")
    old_revision_dir = bundle / ("a" * 40)
    old_revision_dir.mkdir()
    (old_revision_dir / "README.md").write_text("# old\n", encoding="utf-8")
    assert run_git(["add", "."], cwd=repo).returncode == 0
    assert run_git(["commit", "-q", "-m", "initial"], cwd=repo).returncode == 0
    return repo


@pytest.fixture
def clone(tmp_path: Path, remote: Path) -> Path:
    """A working-tree clone of ``remote`` - what a hosted job's own ``actions/checkout`` gives
    this effect to operate on."""
    target = tmp_path / "clone"
    cloned = run_git(["clone", "-q", str(remote), str(target)])
    assert cloned.returncode == 0, cloned.stderr
    for args in (
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
    ):
        assert run_git(args, cwd=target).returncode == 0
    return target


def _import_dir(tmp_path: Path, revision: str, *extra_files: str) -> Path:
    directory = tmp_path / f"import-{revision}"
    directory.mkdir()
    (directory / "CURRENT").write_text(revision + "\n", encoding="utf-8")
    revision_dir = directory / revision
    revision_dir.mkdir()
    (revision_dir / "README.md").write_text(f"# {revision}\n", encoding="utf-8")
    (revision_dir / "manifest.json").write_text(
        '{"state": "READY_FOR_PROPOSAL"}\n', encoding="utf-8"
    )
    for name in extra_files:
        (revision_dir / name).write_text(f"{name}\n", encoding="utf-8")
    return directory


def test_remote_branch_sha_is_none_for_a_branch_that_does_not_exist_yet(
    clone: Path,
) -> None:
    assert remote_branch_sha(clone, BRANCH, token=None) is None


def test_checkout_branch_fetches_the_base_branch_by_name_for_a_fresh_branch(
    clone: Path,
) -> None:
    checkout_branch(clone, BRANCH, "main", token=None)
    current = read_committed_file(clone, f"candidates/{SLUG}/CURRENT")
    assert current is not None and current.strip() == "a" * 40


def test_a_full_publish_cycle_creates_commits_and_pushes_a_real_branch(
    tmp_path: Path, remote: Path, clone: Path
) -> None:
    new_revision = "b" * 40
    import_dir = _import_dir(tmp_path, new_revision, "manifest.json")

    checkout_branch(clone, BRANCH, "main", token=None)
    previous = read_committed_file(clone, f"candidates/{SLUG}/CURRENT")
    assert (
        previous is not None and previous.strip() == "a" * 40
    )  # the old revision, pre-overlay

    overlay_bundle(clone, SLUG, import_dir)
    new_current = read_committed_file(clone, f"candidates/{SLUG}/CURRENT")
    assert new_current is not None and new_current.strip() == new_revision

    commit_sha = stage_and_commit(
        clone, (f"candidates/{SLUG}",), f"revision: {new_revision}\n"
    )
    assert commit_sha is not None

    push_branch(clone, BRANCH, token=None)

    # Proven against the real remote, not the local clone's own belief about itself.
    pushed_sha = remote_branch_sha(clone, BRANCH, token=None)
    assert pushed_sha == commit_sha

    remote_check = run_git(
        ["show", f"{pushed_sha}:candidates/{SLUG}/CURRENT"], cwd=remote
    )
    assert remote_check.returncode == 0
    assert remote_check.stdout.strip() == new_revision


def test_staging_the_same_content_twice_commits_nothing_the_second_time(
    tmp_path: Path, clone: Path
) -> None:
    new_revision = "b" * 40
    import_dir = _import_dir(tmp_path, new_revision)
    checkout_branch(clone, BRANCH, "main", token=None)
    overlay_bundle(clone, SLUG, import_dir)
    first = stage_and_commit(clone, (f"candidates/{SLUG}",), "first\n")
    assert first is not None

    # Re-overlaying byte-identical content and staging again must find nothing to commit - the
    # real git mechanics behind this effect's own idempotency guarantee.
    overlay_bundle(clone, SLUG, import_dir)
    second = stage_and_commit(clone, (f"candidates/{SLUG}",), "second\n")
    assert second is None


def test_a_pending_branch_is_continued_from_its_own_remote_tip_not_the_base_branch(
    tmp_path: Path, remote: Path, clone: Path
) -> None:
    """Simulates a second, independent job: a fresh clone, after a prior run already pushed the
    candidates-update branch one revision ahead of what this job's own base-branch checkout has
    (this clone was taken before that push - `remote` is a shared, disposable "origin")."""
    first_revision = "b" * 40
    first_import = _import_dir(tmp_path, first_revision)
    checkout_branch(clone, BRANCH, "main", token=None)
    overlay_bundle(clone, SLUG, first_import)
    first_commit = stage_and_commit(
        clone, (f"candidates/{SLUG}",), f"revision: {first_revision}\n"
    )
    assert first_commit is not None
    push_branch(clone, BRANCH, token=None)

    # A second, independent job: a fresh clone of the same remote (never the first job's own
    # clone directory) sees the base branch still at the old revision - but the pending branch
    # already exists, one revision ahead, on the remote.
    second_clone = tmp_path / "clone-2"
    cloned = run_git(["clone", "-q", str(remote), str(second_clone)])
    assert cloned.returncode == 0, cloned.stderr
    for args in (["config", "user.email", "t@e.com"], ["config", "user.name", "T"]):
        assert run_git(args, cwd=second_clone).returncode == 0

    assert remote_branch_sha(second_clone, BRANCH, token=None) is not None
    checkout_branch(
        second_clone, BRANCH, BRANCH, token=None
    )  # continues the pending branch
    previous = read_committed_file(second_clone, f"candidates/{SLUG}/CURRENT")
    assert (
        previous is not None and previous.strip() == first_revision
    )  # never main's old value

    second_revision = "c" * 40
    second_import = _import_dir(tmp_path, second_revision)
    overlay_bundle(second_clone, SLUG, second_import)
    second_commit = stage_and_commit(
        second_clone, (f"candidates/{SLUG}",), f"revision: {second_revision}\n"
    )
    assert second_commit is not None
    push_branch(second_clone, BRANCH, token=None)

    final_sha = remote_branch_sha(clone, BRANCH, token=None)
    assert final_sha == second_commit
    parents = run_git(["log", "--format=%H", final_sha], cwd=remote)
    assert (
        first_commit in parents.stdout
    )  # a fast-forward, never a rebase or a force-reset


def test_push_of_an_unreachable_remote_is_a_typed_failure_not_a_silent_no_op(
    tmp_path: Path, clone: Path
) -> None:
    checkout_branch(clone, BRANCH, "main", token=None)
    run_git(
        ["remote", "set-url", "origin", str(tmp_path / "does-not-exist")], cwd=clone
    )
    with pytest.raises(RepositoryMetadataError):
        push_branch(clone, BRANCH, token=None)


def test_overlay_refuses_a_missing_import_directory(
    clone: Path, tmp_path: Path
) -> None:
    checkout_branch(clone, BRANCH, "main", token=None)
    with pytest.raises(RepositoryMetadataError):
        overlay_bundle(clone, SLUG, tmp_path / "does-not-exist")


def _lane_l_import(tmp_path: Path, revision: str) -> Path:
    """What a job that ran only Lane L carries: a Lane L bundle under ``lane-l/``, no Lane R."""
    directory = tmp_path / f"import-lane-l-{revision}"
    lane = directory / "lane-l"
    (lane / revision).mkdir(parents=True)
    (lane / "CURRENT").write_text(revision + "\n", encoding="utf-8")
    (lane / revision / "README.md").write_text(f"# lane l {revision}\n", encoding="utf-8")
    return directory


def test_publishing_lane_r_keeps_the_committed_lane_l_candidate(
    tmp_path: Path, clone: Path
) -> None:
    """Falsifier for the old wholesale replace: a Lane R import carries no Lane L tree, and
    replacing ``candidates/<slug>`` wholesale would delete Lane L's committed candidate."""
    checkout_branch(clone, BRANCH, "main", token=None)
    lane_l = clone / "candidates" / SLUG / "lane-l"
    (lane_l / ("c" * 40)).mkdir(parents=True)
    (lane_l / "CURRENT").write_text("c" * 40 + "\n", encoding="utf-8")
    (lane_l / ("c" * 40) / "README.md").write_text("# lane l\n", encoding="utf-8")

    overlay_bundle(clone, SLUG, _import_dir(tmp_path, "b" * 40))

    assert read_committed_file(clone, f"candidates/{SLUG}/CURRENT") == "b" * 40 + "\n"
    assert not (clone / "candidates" / SLUG / ("a" * 40)).exists()  # Lane R was replaced
    assert (lane_l / "CURRENT").read_text(encoding="utf-8") == "c" * 40 + "\n"
    assert (lane_l / ("c" * 40) / "README.md").read_text(encoding="utf-8") == "# lane l\n"


def test_publishing_lane_l_replaces_only_the_lane_l_tree(tmp_path: Path, clone: Path) -> None:
    checkout_branch(clone, BRANCH, "main", token=None)
    overlay_bundle(clone, SLUG, _lane_l_import(tmp_path, "d" * 40), "L")
    lane_l = clone / "candidates" / SLUG / "lane-l"
    assert (lane_l / "CURRENT").read_text(encoding="utf-8") == "d" * 40 + "\n"

    overlay_bundle(clone, SLUG, _lane_l_import(tmp_path, "e" * 40), "L")
    assert (lane_l / "CURRENT").read_text(encoding="utf-8") == "e" * 40 + "\n"
    assert not (lane_l / ("d" * 40)).exists()  # the superseded Lane L revision is replaced
    # Lane R is exactly what the remote committed.
    assert read_committed_file(clone, f"candidates/{SLUG}/CURRENT") == "a" * 40 + "\n"
    assert (clone / "candidates" / SLUG / ("a" * 40) / "README.md").read_text(
        encoding="utf-8"
    ) == "# old\n"
