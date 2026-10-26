"""Minimal test-support shim: REPO_ROOT, the npm test double, and disposable git/registry fixtures.

The old repository-presenter project's tests/support.py is a large builder module (synthetic
project roots, cursors, sealed bundles, disposable git repos) with a heavy dependency closure
(openai, httpx, components.issues, core.registry, core.state) none of which this repository has
pulled. Only the self-contained pieces are ported, each alongside the module it actually builds
fixtures for: REPO_ROOT and the npm-stub helpers (fake_npm, npm_calls) for the extractors test
suite (migration/reuse-manifest.yaml's "extractors/platforms" entry); init_git_repository/
commit_all/head_revision for core/git_safety/git.py's own test suite; monitor_registry_entry/
write_registry_file for core/registry/write_gate.py's own test suite (both 2026-10-23);
write_bundle and the fake readers/listers for monitor/'s own test suite (2026-10-26). Port the
rest of the old support.py only alongside the modules it actually builds fixtures for.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.core.registry.models import Registry, RegistryEntry
from repo_presenter.core.state.cas import SaveResult
from repo_presenter.core.state.schema import RepositoryRecord
from repo_presenter.github.read_client import DefaultBranchRead
from repo_presenter.monitor.org_listing import OrganizationListing, UpstreamRepository

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


# --- Portfolio monitoring fakes (ported with components/monitor's tests) -----------------

def write_bundle(
    root: Path,
    repository_dir: str,
    revision: str,
    state: str | None,
    *,
    raw: str | None = None,
    current: bool = True,
    upstream_blobs: dict[str, str] | None = None,
    facts: list[dict[str, Any]] | None = None,
    manifest_extra: dict[str, Any] | None = None,
) -> Path:
    """Create a bundle directory; seal it with a manifest when ``state`` or ``raw`` is given.

    Writes ``CURRENT`` pointing at ``revision`` too (unless ``current=False``), matching what a
    real seal always does - ``count_current_candidates`` (TB-06) only ever resolves a repository
    through its own ``CURRENT`` file, never by scanning revision directories directly.
    ``upstream_blobs`` is recorded on the manifest when given, as a seal records it; omitted, the
    manifest carries no upstream blob ids (a bundle sealed before they were recorded).
    ``facts`` writes a sealed ``facts.json`` listed in the manifest's inventory (digest-checked, as
    in a real seal); ``manifest_extra`` adds fields to the manifest (``sealed_at``,
    ``consumed_fact_ids``).
    """
    bundle = root / "candidates" / repository_dir / revision
    bundle.mkdir(parents=True, exist_ok=True)
    manifest = bundle / "manifest.json"
    if raw is not None:
        manifest.write_text(raw, encoding="utf-8")
    elif state is not None:
        readme = bundle / "README.md"
        readme.write_bytes(b"")
        digest = {"README.md": {"sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0}}
        recorded = {} if upstream_blobs is None else {"upstream_blobs": upstream_blobs}
        if facts is not None:
            facts_bytes = json.dumps({"facts": facts}).encode("utf-8")
            (bundle / "facts.json").write_bytes(facts_bytes)
            digest["facts.json"] = {
                "sha256": hashlib.sha256(facts_bytes).hexdigest(),
                "bytes": len(facts_bytes),
            }
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repository": repository_dir.replace("__", "/", 1),
                    "revision": revision,
                    "state": state,
                    "files": digest,
                    **recorded,
                    **(manifest_extra or {}),
                }
            ),
            encoding="utf-8",
        )
    if current and (raw is not None or state is not None):
        (bundle.parent / "CURRENT").write_text(f"{revision}\n", encoding="utf-8")
    return bundle


class FakeDefaultBranchReader:
    """Injected stand-in for ``github/read_client.py::fetch_default_branch_sha``.

    Each repository maps to a head sha, a ready ``DefaultBranchRead``, or an exception to raise.
    Every call and the token it was given are recorded, so a test can prove what was read.
    """

    def __init__(self, outcomes: dict[str, str | DefaultBranchRead | Exception]) -> None:
        self.outcomes = outcomes
        self.calls: list[str] = []
        self.tokens: list[str | None] = []

    def __call__(self, repository: str, *, token: str | None = None) -> DefaultBranchRead:
        self.calls.append(repository)
        self.tokens.append(token)
        outcome = self.outcomes[repository]
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, DefaultBranchRead):
            return outcome
        return DefaultBranchRead(repository, sha=outcome, branch="main")


# --- Registry discovery (components/monitor/discovery.py): an organization lister that reaches no
# network. ``FakeOrganizationLister`` stands in for ``org_listing.list_organization_repositories``,
# records every organization it is asked for and the token it was given, and is the only seam, so a
# test can prove what was listed and that nothing else was read.

# The ten repositories GitHub held on 2026-10-11 in the registry's organizations that the registry
# did not list. Ids and flags are the ones GitHub reported.
#
# - JMAP_FAMILY: eight public repositories (last pushed 2026-09-26). The owner has since admitted
#   them, so the live registry lists them; the tests that need "an unadmitted family" build it by
#   REMOVING these entries from a registry fixture (``registry_without``), never by relying on what
#   the live registry happens to hold.
# - GO_MCP: the PDF library's MCP server (its name fails the registry naming contract, so it stays
#   unregistered), and ORG_PROFILE: an organization profile repository (excluded by policy).
JMAP_FAMILY: tuple[UpstreamRepository, ...] = tuple(
    UpstreamRepository(
        f"aspose-email-foss/Aspose.JMAP-FOSS-for-{platform}",
        identity,
        default_branch="main",
        pushed_at="2026-09-26T20:04:00Z",
        language=language,
    )
    for platform, identity, language in (
        ("Python", 1389232730, "Python"),
        ("Node.js", 1389232832, "JavaScript"),
        ("TypeScript", 1389232963, "TypeScript"),
        ("Go", 1389233108, "Go"),
        ("Rust", 1389233264, "Rust"),
        (".NET", 1389233379, "C#"),
        ("Cpp", 1389233504, "C++"),
        ("Java", 1389233642, "Java"),
    )
)
GO_MCP = UpstreamRepository(
    "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP",
    1287149459,
    default_branch="main",
    pushed_at="2026-07-03T09:59:27Z",
    language="Go",
)
ORG_PROFILE = UpstreamRepository(
    "aspose-slides-foss/.github",
    1335892192,
    default_branch="main",
    pushed_at="2026-09-20T12:44:55Z",
)
# Beyond the admitted entries, now: the MCP server (UNREGISTERED) and the profile repository
# (EXCLUDED_BY_POLICY).
BEYOND_THE_REGISTRY: tuple[UpstreamRepository, ...] = (GO_MCP, ORG_PROFILE)
# Before the JMAP family was admitted: the ten, nine of them candidates.
BEFORE_ADMISSION: tuple[UpstreamRepository, ...] = (*JMAP_FAMILY, *BEYOND_THE_REGISTRY)
UNREGISTERED_BEFORE_ADMISSION = tuple(
    repository.full_name for repository in BEFORE_ADMISSION if repository.name != ".github"
)


class FakeOrganizationLister:
    """``organization -> OrganizationListing``, recording every call."""

    def __init__(
        self,
        repositories: Mapping[str, Iterable[UpstreamRepository]],
        *,
        errors: Mapping[str, str | Exception] | None = None,
        truncated: Iterable[str] = (),
    ) -> None:
        self.repositories = {org: tuple(items) for org, items in repositories.items()}
        self.errors = dict(errors or {})
        self.truncated = frozenset(truncated)
        self.calls: list[str] = []
        self.tokens: list[str | None] = []

    def __call__(self, organization: str, *, token: str | None = None) -> OrganizationListing:
        self.calls.append(organization)
        self.tokens.append(token)
        failure = self.errors.get(organization)
        if isinstance(failure, Exception):
            raise failure
        if failure is not None:
            return OrganizationListing(organization, error=failure)
        return OrganizationListing(
            organization,
            self.repositories.get(organization, ()),
            truncated=organization in self.truncated,
        )


def mirror(entries: Iterable[RegistryEntry]) -> dict[str, list[UpstreamRepository]]:
    """What GitHub would list if it held exactly the admitted entries, under their admitted ids."""
    listing: dict[str, list[UpstreamRepository]] = {}
    for entry in entries:
        listing.setdefault(entry.owner, []).append(
            UpstreamRepository(
                entry.repository,
                entry.provider_identity.repository_id,
                default_branch="main",
                pushed_at="2026-09-01T00:00:00Z",
            )
        )
    return listing


def with_extra(
    listing: Mapping[str, Sequence[UpstreamRepository]], extra: Iterable[UpstreamRepository]
) -> dict[str, list[UpstreamRepository]]:
    merged = {org: list(items) for org, items in listing.items()}
    for repository in extra:
        merged.setdefault(repository.owner, []).append(repository)
    return merged


def registry_without(path: Path, repositories: Iterable[UpstreamRepository]) -> Registry:
    """The registry at ``path`` minus any entry that admits one of ``repositories`` (by id).

    Builds the "these are not admitted" scenario from the registry fixture itself, so a test about
    unregistered repositories holds whatever the owner has admitted since.
    """
    removed = {repository.repository_id for repository in repositories}
    return Registry(
        entries=tuple(
            entry
            for entry in load_registry(path).entries
            if entry.provider_identity.repository_id not in removed
        )
    )
