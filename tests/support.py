"""Minimal test-support shim: REPO_ROOT, the npm test double, and disposable git fixtures.

The old repository-presenter project's tests/support.py is a large builder module (synthetic
project roots, cursors, sealed bundles, disposable git repos) with a heavy dependency closure
(openai, httpx, components.issues, core.registry, core.state) none of which this repository has
pulled. Only the self-contained pieces are ported, each alongside the module it actually builds
fixtures for: REPO_ROOT and the npm-stub helpers (fake_npm, npm_calls) for the extractors test
suite (migration/reuse-manifest.yaml's "extractors/platforms" entry); init_git_repository/
commit_all/head_revision for core/git_safety/git.py's own test suite (2026-10-23). Port the rest
of the old support.py only alongside the modules it actually builds fixtures for.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from repo_presenter.core.git_safety.git import run_git

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
