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
from dataclasses import dataclass, field
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


def _require_contained(ref: str, relative: str, target: Path) -> None:
    """Refuse a stored path that is absolute, drive-qualified, uses a backslash or a ``..`` part,
    or would resolve outside ``target`` on this machine."""
    separators = chr(92)
    if (
        not relative
        or Path(relative).is_absolute()
        or ":" in relative
        or separators in relative
        or ".." in Path(relative).parts
        or not (target / relative).resolve().is_relative_to(target.resolve())
    ):
        raise BundleStoreError(f"{ref}: refusing unsafe path {relative!r}")


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
            entries = []
            for entry in filter(None, listing):
                meta, relative = entry.split("\t", 1)
                entries.append((meta.split()[2], relative))
            # Every path is checked before the first byte is written, so a bad entry can never
            # leave a partial export; the destination must start empty so a stale file from an
            # earlier export can never be mistaken for part of this bundle.
            for _blob, relative in entries:
                _require_contained(ref, relative, target)
            # Lane R's root is the repository directory, which is also the parent of Lane L's own
            # directory, so Lane L's presence there is not a stale Lane R file.
            sibling = LANE_DIRNAMES[LANE_L] if lane == LANE_R else None
            if target.exists() and any(p.name != sibling for p in target.iterdir()):
                raise BundleStoreError(f"{target}: the export destination is not empty")
            for blob, relative in entries:
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


# --- seal history: every sealed bundle a lane ever pushed, never only the latest ----------------

#: Manifest states of a seal that stands as a candidate.
SEALED_GOOD_STATES = frozenset({"ACCEPTED", "READY_FOR_PROPOSAL"})
REVIEW_VERDICT_FILENAME = "review_verdict.json"
DEPENDENCIES_FILENAME = "dependencies.json"
_HISTORY_REF_PREFIX = "refs/repository-presenter-seal-history"


@dataclass(frozen=True)
class SealRecord:
    """One seal: one commit on a lane's bundle ref, read and integrity-verified at that commit.

    The bundle ref is append-only (``publish_bundle`` always commits on top of the previous seal,
    and only a run that sealed publishes at all), so its history is the immutable record of every
    candidate the lane ever sealed. A later run -- failed or not, under any version set -- can add
    commits; it never rewrites or removes this one, so it can never demote it.
    """

    repository: str
    lane: str
    commit: str
    revision: str
    manifest_state: str
    dependencies: dict | None
    review: dict | None
    readme: bytes | None = None
    error: str = ""
    #: The manifest's file inventory (``{name: {sha256, bytes}}``) -- what a regeneration count
    #: compares between seals of one revision.
    files: dict = field(default_factory=dict)
    #: The manifest's ``recertified_from`` (a re-certified seal, ``repo_presenter.recertify``).
    recertified_from: dict | None = None
    #: The materialized ``<revision>`` directory, only while ``seal_history``'s ``scratch`` exists.
    bundle: Path | None = None

    @property
    def pipeline_good(self) -> bool:
        return not self.error and self.manifest_state in SEALED_GOOD_STATES

    @property
    def model_accept(self) -> bool:
        review = self.review or {}
        return review.get("verdict") == "ACCEPT" and review.get("model_verdict") == "ACCEPT"

    @property
    def counted(self) -> bool:
        """A pipeline-good seal carrying a model-reviewed ACCEPT: what a lane count may include."""
        return self.pipeline_good and self.model_accept


def parse_bundle_ref(ref: str) -> tuple[str, str] | None:
    """``refs/.../bundles/<org>__<name>[@lane-l]`` -> ``(org/name, lane)``; None otherwise."""
    from repo_presenter.core.state.git_backend import LANE_L_REF_SUFFIX

    prefix = BUNDLE_REF_PREFIX + "/"
    if not ref.startswith(prefix):
        return None
    key = ref[len(prefix) :]
    lane = LANE_R
    if key.endswith(LANE_L_REF_SUFFIX):
        key, lane = key[: -len(LANE_L_REF_SUFFIX)], LANE_L
    if "__" not in key:
        return None
    return key.replace("__", "/", 1), lane


def _read_seal(git_dir: Path, commit: str, repository: str, lane: str, scratch: Path) -> SealRecord:
    """Materialize ``commit``'s tree into a fresh directory and verify it exactly as a committed
    ``candidates/`` tree is verified. Any failure is a recorded ``error``, never a count."""
    import io
    import json
    import tarfile

    def failed(why: str, revision: str = "") -> SealRecord:
        return SealRecord(repository, lane, commit, revision, "", None, None, None, why)

    archive = subprocess.run(
        ["git", "--git-dir", str(git_dir), "archive", "--format=tar", commit],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    if archive.returncode != 0:
        return failed(f"git archive failed: {archive.stderr.decode(errors='replace').strip()}")
    target = scratch / commit
    target.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        members = [m for m in tar.getmembers() if m.type != tarfile.XGLTYPE]
        for member in members:
            if not (member.isfile() or member.isdir()):
                return failed(f"refusing non-regular tree entry {member.name!r}")
            try:
                _require_contained(commit, member.name.rstrip("/"), target)
            except BundleStoreError as exc:
                return failed(str(exc))
        tar.extractall(target, members=members, filter="data")
    try:
        revision = _current_revision(target)
        bundle = target / revision
        manifest = verify_bundle(bundle, lane)
        if manifest is None:
            return failed(f"CURRENT names {revision} but it has no manifest", revision)
        if manifest.get("repository") not in (None, repository):
            return failed(f"manifest names repository {manifest.get('repository')!r}", revision)
        files = manifest.get("files", {})
        dependencies = review = None
        if DEPENDENCIES_FILENAME in files:  # only manifest-sealed files are evidence
            dependencies = json.loads((bundle / DEPENDENCIES_FILENAME).read_text(encoding="utf-8"))
        if REVIEW_VERDICT_FILENAME in files:
            review = json.loads((bundle / REVIEW_VERDICT_FILENAME).read_text(encoding="utf-8"))
        readme = (bundle / "README.md").read_bytes() if "README.md" in files else None
    except Exception as exc:  # noqa: BLE001 -- corrupt evidence is a reason, never a count
        return failed(f"{type(exc).__name__}: {exc}")
    recertified = manifest.get("recertified_from")
    return SealRecord(
        repository,
        lane,
        commit,
        revision,
        str(manifest.get("state")),
        dependencies if isinstance(dependencies, dict) else None,
        review if isinstance(review, dict) else None,
        readme,
        files=dict(files) if isinstance(files, dict) else {},
        recertified_from=recertified if isinstance(recertified, dict) else None,
        bundle=bundle,
    )


def seal_history(
    *, remote: str = "origin", token: str | None = None, scratch: Path | None = None
) -> dict[tuple[str, str], list[SealRecord]]:
    """Every seal on every bundle ref of ``remote``: ``{(repository, lane): [seal, ...]}``, oldest
    first. One full-history fetch of the bundle namespace into an isolated workspace; read-only
    (nothing is ever pushed). With ``scratch`` the materialized trees are kept there and each
    record's ``bundle`` names its ``<revision>`` directory (re-certification reads it); without
    it they are removed before this returns."""
    import contextlib
    import tempfile

    history: dict[tuple[str, str], list[SealRecord]] = {}
    try:
        with GitStateBackend(remote=remote, token=token) as backend, backend._lock:
            fetched = backend._run_remote_git(
                [
                    "fetch",
                    "--no-write-fetch-head",
                    "--no-tags",
                    backend._remote,
                    f"+{BUNDLE_REF_PREFIX}/*:{_HISTORY_REF_PREFIX}/*",
                ]
            )
            if fetched.returncode != 0:
                raise BundleStoreError(
                    f"fetch of the bundle history failed: {fetched.stderr.strip()}"
                )
            listed = _git(
                backend, ["for-each-ref", "--format=%(refname)", _HISTORY_REF_PREFIX], "for-each-ref"
            )
            keep = contextlib.nullcontext(str(scratch)) if scratch is not None else None
            with keep or tempfile.TemporaryDirectory(prefix="seal-history-") as tmp:
                for local in sorted(filter(None, listed.splitlines())):
                    parsed = parse_bundle_ref(BUNDLE_REF_PREFIX + local[len(_HISTORY_REF_PREFIX) :])
                    if parsed is None:
                        continue
                    repository, lane = parsed
                    commits = _git(backend, ["rev-list", "--reverse", local], "rev-list").split()
                    scratch = Path(tmp) / lane / _slug(repository)
                    history[parsed] = [
                        _read_seal(backend._git_cwd, commit, repository, lane, scratch)
                        for commit in commits
                    ]
    except StateBackendError as exc:
        raise BundleStoreError(str(exc)) from exc
    return history
