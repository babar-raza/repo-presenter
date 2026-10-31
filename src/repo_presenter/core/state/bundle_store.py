"""Durable storage for a sealed candidate bundle: one git ref per repository per lane.

A hosted run used to keep its sealed bundle only in an ``actions/cache`` entry and a 14-day
workflow artifact, while the durable transaction record (``git_backend``) holds a state and a
verdict summary but no candidate content. This module is the missing half: the bundle directory
becomes the tree of a commit pushed to ``refs/repository-presenter-state/bundles/<key>`` (the same
key and ``@lane-l`` suffix as the record ref), so a sealed candidate outlives the artifact.

It reuses the state backend's isolated plumbing workspace, fetch and push helpers, and its commit
identity; it needs no working tree, no GitHub App token and no pull request, only the contents
write permission the record refs already use. Only a bundle that verifies is published, and a
republish of identical content pushes nothing.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from repo_presenter.core.candidates import (
    BUNDLE_MANIFEST_NAME,
    CURRENT_FILENAME,
    LANE_DIRNAMES,
    LANE_L,
    LANE_R,
    lane_directory,
    verify_bundle,
)
from repo_presenter.core.errors import PresenterError, StateBackendError
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.state.git_backend import (
    _COMMIT_IDENTITY_ENV,
    GitStateBackend,
    _ref_key,
)

BUNDLE_REF_PREFIX = "refs/repository-presenter-state/bundles"
_FILE_MODE = "100644"


class BundleStoreError(PresenterError):
    """A bundle could not be published or exported; the message says which and why."""


@dataclass(frozen=True)
class BundlePublication:
    ref: str
    commit: str
    files: int
    changed: bool


def bundle_ref(repository: str, lane: str = LANE_R) -> str:
    return f"{BUNDLE_REF_PREFIX}/{_ref_key(repository, lane)}"


def _slug(repository: str) -> str:
    return repository.replace("/", "__")


def _bundle_files(lane_root: Path, lane: str) -> list[tuple[str, Path]]:
    """Every regular file under ``lane_root`` as ``(posix relative path, path)``, sorted. Lane R's
    root is the repository directory, which also holds Lane L's sibling directory; that
    directory belongs to Lane L's own ref and is left out."""
    skip = LANE_DIRNAMES[LANE_L] if lane == LANE_R else None
    files: list[tuple[str, Path]] = []
    for path in sorted(lane_root.rglob("*")):
        if path.is_symlink():
            raise BundleStoreError(f"{path}: a bundle may not contain a symbolic link")
        if not path.is_file():
            continue
        relative = path.relative_to(lane_root).as_posix()
        if skip is not None and relative.split("/", 1)[0] == skip:
            continue
        files.append((relative, path))
    return files


def _git(backend: GitStateBackend, args: list[str], what: str) -> str:
    result = run_git(args, cwd=backend._git_cwd)
    if result.returncode != 0:
        raise BundleStoreError(f"{what} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def publish_bundle(
    repository: str,
    lane: str,
    repository_dir: Path,
    *,
    remote: str = "origin",
    token: str | None = None,
) -> BundlePublication:
    """Push ``repository_dir``'s ``lane`` bundle to its bundle ref.

    ``repository_dir`` is the ``candidates/<slug>`` directory. The bundle must verify (manifest
    inventory and digests) and carry a ``CURRENT`` pointer; otherwise nothing is pushed. When the
    ref already holds an identical tree the call is a no-op and reports ``changed=False``.
    """
    # Absolute, because the git plumbing below runs with the backend's own workspace as its working
    # directory: a relative candidates root (present.py defaults to ".") would not resolve there.
    lane_root = lane_directory(repository_dir, lane).resolve()
    if verify_bundle(lane_root / _current_revision(lane_root), lane) is None:
        raise BundleStoreError(f"{lane_root}: no verifiable sealed bundle to publish")
    files = _bundle_files(lane_root, lane)
    ref = bundle_ref(repository, lane)
    try:
        with GitStateBackend(remote=remote, token=token, lane=lane) as backend, backend._lock:
            parent = backend._fetch_remote_sha(ref)
            for relative, path in files:
                blob = _git(
                    backend,
                    ["hash-object", "-w", "--no-filters", "--", str(path)],
                    f"hash-object {relative}",
                )
                _git(
                    backend,
                    ["update-index", "--add", "--cacheinfo", f"{_FILE_MODE},{blob},{relative}"],
                    f"update-index {relative}",
                )
            tree = _git(backend, ["write-tree"], "write-tree")
            if parent is not None:
                parent_tree = _git(
                    backend, ["rev-parse", "--verify", f"{parent}^{{tree}}"], "rev-parse"
                )
                if parent_tree == tree:
                    return BundlePublication(ref, parent, len(files), changed=False)
            revision = _current_revision(lane_root)
            args = ["commit-tree", tree, "-m", f"bundle: {repository} lane {lane} {revision}"]
            if parent is not None:
                args += ["-p", parent]
            commit = run_git(args, cwd=backend._git_cwd, env=_COMMIT_IDENTITY_ENV)
            if commit.returncode != 0:
                raise BundleStoreError(f"commit-tree failed: {commit.stderr.strip()}")
            commit_sha = commit.stdout.strip()
            push = backend._push_with_retry(
                ["push", backend._remote, f"{commit_sha}:{ref}"], remote_ref=ref
            )
            if push.returncode != 0:
                raise BundleStoreError(f"push of {ref} failed: {push.stderr.strip()}")
            return BundlePublication(ref, commit_sha, len(files), changed=True)
    except StateBackendError as exc:
        raise BundleStoreError(str(exc)) from exc


def _current_revision(lane_root: Path) -> str:
    current = lane_root / CURRENT_FILENAME
    if not current.is_file():
        raise BundleStoreError(f"{lane_root}: no {CURRENT_FILENAME} pointer; nothing is sealed")
    return current.read_text(encoding="utf-8").strip()


def export_bundle(
    repository: str,
    lane: str,
    destination_root: Path,
    *,
    remote: str = "origin",
    token: str | None = None,
) -> Path:
    """Materialize the stored bundle under ``destination_root/<slug>`` (Lane L under its
    ``lane-l`` sibling directory), byte for byte, so ``verify_bundle`` and the status commands read
    it exactly as they read a committed ``candidates/`` tree. Returns the lane root written."""
    ref = bundle_ref(repository, lane)
    target = lane_directory(destination_root / _slug(repository), lane)
    try:
        with GitStateBackend(remote=remote, token=token, lane=lane) as backend, backend._lock:
            sha = backend._fetch_remote_sha(ref)
            if sha is None:
                raise BundleStoreError(f"no stored bundle at {ref}")
            listing = _git(backend, ["ls-tree", "-r", "-z", sha], "ls-tree").split("\0")
            for entry in filter(None, listing):
                meta, relative = entry.split("\t", 1)
                blob = meta.split()[2]
                parts = Path(relative).parts
                if Path(relative).is_absolute() or ".." in parts:
                    raise BundleStoreError(f"{ref}: refusing unsafe path {relative!r}")
                data = subprocess.run(
                    ["git", "--git-dir", str(backend._git_cwd), "cat-file", "blob", blob],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    check=False,
                )
                if data.returncode != 0:
                    raise BundleStoreError(f"cat-file {blob} failed: {data.stderr.decode().strip()}")
                out = target / relative
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data.stdout)
    except StateBackendError as exc:
        raise BundleStoreError(str(exc)) from exc
    revision = _current_revision(target)
    if verify_bundle(target / revision, lane) is None or not (
        target / revision / BUNDLE_MANIFEST_NAME
    ).is_file():
        raise BundleStoreError(f"{target}: the exported bundle does not verify")
    return target
