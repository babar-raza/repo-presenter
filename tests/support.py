"""Minimal test-support shim: REPO_ROOT, the npm test double, and disposable git/registry fixtures.

The old repository-presenter project's tests/support.py is a large builder module (synthetic
project roots, cursors, sealed bundles, disposable git repos) with a heavy dependency closure
(openai, httpx, components.issues, core.registry, core.state) none of which this repository has
pulled. Only the self-contained pieces are ported, each alongside the module it actually builds
fixtures for: REPO_ROOT and the npm-stub helpers (fake_npm, npm_calls) for the extractors test
suite (migration/reuse-manifest.yaml's "extractors/platforms" entry); init_git_repository/
commit_all/head_revision for core/git_safety/git.py's own test suite; monitor_registry_entry/
write_registry_file for core/registry/write_gate.py's own test suite (both 2026-10-23). Port the
rest of the old support.py only alongside the modules it actually builds fixtures for.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.state.cas import SaveResult
from repo_presenter.core.state.schema import RepositoryRecord

REPO_ROOT = Path(__file__).resolve().parent.parent


def init_git_repository(path: Path, *, with_commit: bool = True) -> Path:
    """A disposable local repository on branch ``main`` with a local identity.

    ``git init``'s exit status is never the evidence: when git already resolves ``path`` inside
    some repository, ``git init`` there is a no-op re-init that still exits 0, and every fixture
    command after it (identity config, ``add``, ``commit``) lands on that repository instead -
    measured 2026-09-11 (old repo, RESEARCH_AND_GUIDELINES.md section 29, G4-W17 arrival item 55)
    as fixture commits on live lane branches and that checkout's own identity and ``core.bare``
    rewritten. So the target is refused up front if git resolves any repository for it, and the
    repository just created is verified to be the one at ``path`` before anything is written
    into it.
    """
    path.mkdir(parents=True, exist_ok=True)
    enclosing = run_git(["rev-parse", "--absolute-git-dir"], cwd=path)
    if enclosing.returncode == 0:
        raise RuntimeError(
            f"refusing to init a fixture repository at {path}: git already resolves it inside"
            f" {enclosing.stdout.strip()}, where `git init` would be a no-op re-init exiting 0"
            " and every fixture command after it would land on that repository"
        )
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
    ):
        result = run_git(args, cwd=path)
        assert result.returncode == 0, result.stderr
    own = run_git(["rev-parse", "--absolute-git-dir"], cwd=path)
    assert own.returncode == 0, own.stderr
    assert Path(own.stdout.strip()).resolve() == (path / ".git").resolve(), (
        f"fixture at {path} resolved to a different repository: {own.stdout.strip()}"
    )
    if with_commit:
        (path / "README.md").write_text("# test\n", encoding="utf-8")
        commit_all(path, "initial")
    return path


def commit_all(path: Path, message: str) -> str:
    """Stage everything, commit, and return the new HEAD revision."""
    assert run_git(["add", "."], cwd=path).returncode == 0
    result = run_git(["commit", "-q", "-m", message], cwd=path)
    assert result.returncode == 0, result.stderr
    return head_revision(path)


def head_revision(path: Path) -> str:
    result = run_git(["rev-parse", "HEAD"], cwd=path)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def monitor_registry_entry(
    repository: str, *, mode: str = "dry_run", repository_id: int = 1
) -> dict[str, Any]:
    """One registry entry payload for an Aspose FOSS repository (``data/registry.json`` shape).

    Ported 2026-10-23 alongside core/registry/write_gate.py's own test suite.
    """
    owner, name = repository.split("/")
    family = owner.removeprefix("aspose-").removesuffix("-foss")
    platform = name.split("-for-")[1].lower()
    platform = "net" if platform == ".net" else platform
    return {
        "repository": repository,
        "family": family,
        "platform": platform,
        "ecosystem": platform,
        "mode": mode,
        "policy_profile": "fixture",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": repository_id,
            "node_id": f"R_fixture_{repository_id}",
        },
    }


def write_registry_file(root: Path, entries: list[dict[str, Any]]) -> Path:
    """``data/registry.json`` under a synthetic project root."""
    path = root / "data" / "registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "entries": entries}), encoding="utf-8")
    return path


def fake_npm(directory: Path, fail_run: bool = False) -> str:
    """A stand-in `npm` that records its arguments and exits 0 - or 3 on `npm run ...` when asked.

    The real one needs the network and a minute; what the verifier is tested on is what it does
    with an exit code. Written per platform because `execute` runs argv[0] directly: a `.cmd`
    where Windows resolves batch files, a `sh` script with its mode bit where the hosted runner
    (ubuntu) does not.
    """
    directory.mkdir(parents=True, exist_ok=True)
    if fail_run:
        (directory / "fail_run").write_text("", encoding="utf-8")
    if os.name == "nt":
        path = directory / "npm.cmd"
        path.write_text(
            "@echo off\r\n"
            'echo %*>>"%~dp0npm.log"\r\n'
            'if "%1"=="run" if exist "%~dp0fail_run" exit /b 3\r\n'
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        path = directory / "npm"
        path.write_text(
            "#!/bin/sh\n"
            'd=$(dirname "$0")\n'
            'echo "$@" >> "$d/npm.log"\n'
            'if [ "$1" = "run" ] && [ -f "$d/fail_run" ]; then exit 3; fi\n'
            "exit 0\n",
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(path)


def npm_calls(npm: str) -> list[str]:
    log = Path(npm).parent / "npm.log"
    return [line.strip() for line in log.read_text("utf-8").splitlines()] if log.is_file() else []


def merge_to_origin_main(root: Path, message: str = "merge") -> str:
    """Commit everything under ``root`` (initialising a disposable repository on first use) and
    point ``refs/remotes/origin/main`` at the new commit - the state of a control checkout whose
    ``main`` already holds that content. Returns the commit.

    Ported 2026-10-23 alongside core/authorization/record_provenance.py's own test suite.
    """
    if not (root / ".git").exists():
        init_git_repository(root, with_commit=False)
    revision = commit_all(root, message)
    assert run_git(["update-ref", "refs/remotes/origin/main", revision], cwd=root).returncode == 0
    return revision


def make_permit(repository: str, *, mode: str = "full", effect: str = "readme_proposal") -> Any:
    """A ``WritePermit`` for a repository that is not a real Aspose FOSS name (the registry model
    validates the name, ``model_construct`` does not) - the effect modules only read ``.effect``
    and ``.entry.repository`` from it.

    Ported 2026-10-23 alongside propose/effect.py's own test suite.
    """
    from repo_presenter.core.registry.models import RegistryEntry
    from repo_presenter.core.registry.write_gate import WritePermit

    entry = RegistryEntry.model_construct(
        repository=repository,
        family="fixture",
        platform="fixture",
        ecosystem="fixture",
        mode=mode,
        policy_profile="fixture",
        active=True,
        provider_identity=None,
    )
    return WritePermit(effect=effect, entry=entry)  # type: ignore[arg-type]


class InMemoryStateBackend:
    """A :class:`repo_presenter.core.state.cas.StateBackend` test double with the real
    compare-and-swap contract (stale-version rejection, no silent lost update) and no git
    subprocess, for ``tests/core/state/``'s fast suites. The git-ref backend is proven separately
    against a disposable local repository in its own test module."""

    def __init__(self) -> None:
        self._records: dict[str, RepositoryRecord] = {}

    def load(self, repository: str) -> RepositoryRecord | None:
        return self._records.get(repository)

    def save(
        self, repository: str, record: RepositoryRecord, expected_version: int | None
    ) -> SaveResult:
        current = self._records.get(repository)
        current_version = current.state_version if current is not None else None
        if current_version != expected_version:
            return SaveResult(outcome="stale", record=current)
        saved = record.model_copy(update={"state_version": (current_version or 0) + 1})
        self._records[repository] = saved
        return SaveResult(outcome="saved", record=saved)
