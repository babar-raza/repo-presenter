"""Count current, integrity-verified sealed candidates from bundles on disk.

PARTIAL PORT (the bundle-integrity/counting tier only; see migration/reuse-manifest.yaml). The
old repository-presenter project's ``core/candidates.py`` (647 lines) splits cleanly into this
tier -- pure manifest/CURRENT/ledger integrity, no dependency on anything this repository has not
pulled -- and a second tier (``load_proposable_candidate``, ``_review_refusal``,
``proposal_gate_refusal``, ``ProposableCandidate``, ``AcceptanceGate``) tied to the old repo's own
``review.json`` shape (``verdict_as_returned``/``verdict_basis``/``demoted``) and a 30-point
acceptance scorer this repository does not have. Not ported here, deliberately: building either
on a shape that does not exist would be invention, not adaptation. ``examples_verification_summary``
is also not ported -- this repository's own sealed bundles (``readme/bundle/seal.py`` v1) do not
produce an ``examples.json`` artifact, so the function would always report ``(0, 0)``.

A candidate bundle lives at ``candidates/<owner>__<name>/<revision>/`` and is sealed by its
``manifest.json`` (``readme/bundle/seal.py``). Progress has exactly one unit: repositories whose
*currently pointed-at* revision (``CURRENT``) has a bundle in a counted state -- never a scan of
every historical revision directory for any counted state, which would let a stale, superseded
revision inflate the count even though a reviewer opening the repository would see a different,
current revision entirely (TB-06, carried over from the old repo's own fix for exactly this).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_presenter.core.errors import PresenterError
from repo_presenter.core.noop_proof import (
    LEDGER_TOTALS_MISMATCH,
    LedgerReconciliationError,
    reconcile_ledger,
)

CANDIDATES_DIRNAME = "candidates"
BUNDLE_MANIFEST_NAME = "manifest.json"
CURRENT_FILENAME = "CURRENT"
# Must match readme/bundle/seal.py's own DEPENDENCIES_FILENAME -- duplicated rather than
# imported, since core/ may not import a readme/ module (this file's own docstring; see also
# readme/bundle/seal.py's identical note about core/llm/ledger.py's LEDGER_FILENAME).
DEPENDENCIES_FILENAME = "dependencies.json"
COUNTED_STATES = frozenset({"READY_FOR_PROPOSAL"})
# The only manifest shape this code knows how to trust. A future, incompatible schema_version
# must fail closed rather than have its (possibly differently-shaped) `files` map trusted as if
# it were this one (TB-06, carried over).
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})


class BundleError(PresenterError, ValueError):
    """A sealed bundle on disk cannot be read, or fails integrity or currentness verification.

    Inherits ``ValueError`` too (the old repo's own original base, carried over so nothing
    downstream has to change how it catches this) and ``PresenterError``, so a caller that only
    catches presenter failures still fails closed on it.
    """


class BundleLedgerError(BundleError):
    """A bundle's recorded totals do not equal the sums over the ledger it seals.

    Typed by ``reason`` so a caller routes on the field and never on the prose.
    """

    reason = LEDGER_TOTALS_MISMATCH


@dataclass(frozen=True)
class SealedBundle:
    """The identity and state of one sealed bundle."""

    repository_dir: str
    revision: str
    state: str


def iter_sealed_bundles(root: Path) -> Iterator[SealedBundle]:
    """Yield every sealed bundle under ``root/candidates`` in path order.

    Every revision of every repository, sealed or not, current or superseded: a raw inventory,
    not a progress count. ``count_current_candidates`` deliberately does not use this -- see the
    module docstring.
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        for revision_dir in sorted(p for p in repository_dir.iterdir() if p.is_dir()):
            manifest = revision_dir / BUNDLE_MANIFEST_NAME
            if not manifest.is_file():
                continue
            yield SealedBundle(
                repository_dir=repository_dir.name,
                revision=revision_dir.name,
                state=_read_state(manifest),
            )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bundle(bundle: Path) -> dict[str, Any] | None:
    """The bundle's manifest, after its inventory and every file it lists check out; a missing,
    empty, corrupt, or unsupported-schema manifest fails closed naming the problem. None when
    there is no bundle at all.

    Checks: the manifest is a readable JSON object naming a non-empty ``state``; it declares a
    ``schema_version`` this code knows how to read; its ``files`` inventory is non-empty (an
    empty inventory is not "nothing to verify", it is a bundle that was never really sealed);
    every listed file is present on disk; every listed file's digest matches what is actually
    there; and, when the manifest records ``ledger_totals``, they equal the sums over its
    ``ledger.jsonl`` (``BundleLedgerError``, reason ``LEDGER_TOTALS_MISMATCH``).
    """
    manifest_path = bundle / BUNDLE_MANIFEST_NAME
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise BundleError(f"unreadable bundle manifest: {manifest_path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise BundleError(f"bundle manifest is not an object: {manifest_path}")
    state = manifest.get("state")
    if not isinstance(state, str) or not state:
        raise BundleError(f"bundle manifest has no state: {manifest_path}")
    schema_version = manifest.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise BundleError(
            f"bundle manifest has unsupported schema_version {schema_version!r}: {manifest_path}"
        )
    files = dict(manifest.get("files", {}))
    if not files:
        raise BundleError(f"bundle manifest lists no files: {manifest_path}")
    for name, digest in sorted(files.items()):
        path = bundle / name
        if not path.is_file():
            raise BundleError(f"bundle artifact {name} is missing from {bundle.name}")
        data = path.read_bytes()
        if not isinstance(digest, dict) or (
            _sha256(data) != digest.get("sha256") or len(data) != digest.get("bytes")
        ):
            raise BundleError(f"bundle artifact {name} is corrupt in {bundle.name}")
    if "ledger.jsonl" in files:
        try:
            reconcile_ledger(manifest, bundle / "ledger.jsonl")
        except LedgerReconciliationError as exc:
            raise BundleLedgerError(f"{bundle.name}: {exc}") from exc
    return manifest


def integrity_valid_candidates(root: Path) -> int:
    """How many repositories have a ``CURRENT`` bundle that passes :func:`verify_bundle` cleanly.

    A pass/fail wrapper around the same check ``count_current_candidates`` already applies, but
    reported as a count on its own: a repository whose ``CURRENT`` names no sealed bundle, or
    whose manifest fails integrity verification, simply is not counted here -- a portfolio-health
    signal, not a gate.
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return 0
    valid = 0
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        current = repository_dir / CURRENT_FILENAME
        if not current.is_file():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        try:
            manifest = verify_bundle(repository_dir / revision)
        except BundleError:
            continue
        if manifest is not None:
            valid += 1
    return valid


def count_current_candidates(root: Path) -> int:
    """Return how many repositories have their ``CURRENT`` revision sealed in a counted state.

    Reads ``CURRENT``, resolves to that exact revision's manifest, and verifies it -- never scans
    every historical revision directory for any counted state (see the module docstring). A
    repository with no ``CURRENT`` file has never sealed anything and is silently not counted; a
    ``CURRENT`` that names a revision without a valid, self-consistent bundle is corrupt evidence
    and is an error.
    """
    return len(current_counted_repository_dirs(root))


def _verified_current(repository_dir: Path) -> tuple[str, dict[str, Any]] | None:
    """``(revision, manifest)`` for the bundle ``CURRENT`` names under ``repository_dir``,
    verified and self-consistent; None when the repository has no ``CURRENT`` at all. Raises
    :class:`BundleError` for any ``CURRENT`` that does not name a verifiable bundle of its own."""
    current = repository_dir / CURRENT_FILENAME
    if not current.is_file():
        return None
    revision = current.read_text(encoding="utf-8").strip()
    manifest = verify_bundle(repository_dir / revision)
    if manifest is None:
        raise BundleError(
            f"{repository_dir.name}: CURRENT names revision {revision!r} with no sealed "
            "bundle there"
        )
    if manifest.get("revision") != revision:
        raise BundleError(
            f"{repository_dir.name}: bundle manifest revision {manifest.get('revision')!r} "
            f"does not match CURRENT {revision!r}"
        )
    # The inverse of seal.py's own bundle_directory(): candidates/<owner>__<name>/<revision>,
    # where owner and name are exactly repository.split("/") -- so a manifest's own claimed
    # repository must map back to the directory it was actually found under.
    if str(manifest.get("repository", "")).replace("/", "__") != repository_dir.name:
        raise BundleError(
            f"{repository_dir.name}: bundle manifest repository "
            f"{manifest.get('repository')!r} does not match its directory"
        )
    return revision, manifest


def current_counted_repository_dirs(root: Path) -> set[str]:
    """The repository directories whose ``CURRENT`` bundle is sealed in a counted state -- the
    set :func:`count_current_candidates` counts, under that function's own raising contract."""
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return set()
    counted: set[str] = set()
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        verified = _verified_current(repository_dir)
        if verified is not None and verified[1].get("state") in COUNTED_STATES:
            counted.add(repository_dir.name)
    return counted


def ready_revision(root: Path, repository: str) -> str | None:
    """The ``CURRENT`` revision of ``repository`` when that bundle verifies and is sealed in a
    counted state; None otherwise. A sealed-but-not-ready, superseded, or absent bundle is never
    returned."""
    repository_dir = root / CANDIDATES_DIRNAME / repository.replace("/", "__")
    if not repository_dir.is_dir():
        return None
    verified = _verified_current(repository_dir)
    if verified is None or verified[1].get("state") not in COUNTED_STATES:
        return None
    return verified[0]


def ready_revision_at(bundle_dir: Path, repository: str) -> str | None:
    """Like :func:`ready_revision`, generalized to any directory shaped like one repository's
    own ``candidates/<slug>/`` (a ``CURRENT`` pointer beside sealed revision directories) rather
    than always ``root/candidates/<repository's own slug>``. ``repository`` must equal the
    verified manifest's own recorded ``repository`` field exactly (never merely assumed from the
    directory's name or path)."""
    if not bundle_dir.is_dir():
        return None
    verified = _verified_current(bundle_dir)
    if verified is None or verified[1].get("state") not in COUNTED_STATES:
        return None
    revision, manifest = verified
    if manifest.get("repository") != repository:
        raise BundleError(
            f"{bundle_dir}: bundle manifest repository {manifest.get('repository')!r} does not "
            f"match the expected {repository!r}"
        )
    return revision


@dataclass(frozen=True)
class StaleCandidate:
    """One CURRENT candidate whose sealed ``dependencies.json`` names a component older than
    what the running code currently declares."""

    repository_dir: str
    revision: str
    reasons: tuple[str, ...]


def stale_candidates(
    root: Path, current_components: Mapping[str, str]
) -> list[StaleCandidate]:
    """Every CURRENT candidate whose sealed ``dependencies.json`` is behind the running code's
    own component versions -- a component version change reopens the earliest affected stage of
    every candidate that consumed it (``readme/bundle/invalidation.py``).

    A pure read: no clone, no provider call, no state change, and it cannot itself invalidate a
    candidate -- it only reports what ``invalidation.py``'s own rule already says. Simplified
    from the old repo's own ``stale_candidates`` (which also compared per-check validator
    versions and a separate ``validator_version``): this repository has no consolidated
    validation.json or BLOCKING_CHECKS registry to compare against yet (readme/bundle/seal.py
    v1's own module docstring). A candidate whose ``dependencies.json`` predates a given
    component entirely (an older schema that never recorded it) is silently not flagged for that
    one -- a component this code has never heard of cannot be judged stale by it.
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return []
    stale: list[StaleCandidate] = []
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        current = repository_dir / CURRENT_FILENAME
        if not current.is_file():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        deps_path = repository_dir / revision / DEPENDENCIES_FILENAME
        if not deps_path.is_file():
            continue
        try:
            deps = json.loads(deps_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(deps, dict):
            continue
        reasons: list[str] = []
        recorded_components = deps.get("components") or {}
        for name, current_value in sorted(current_components.items()):
            recorded = recorded_components.get(name)
            if recorded is not None and recorded != current_value:
                reasons.append(f"components.{name} {recorded} -> {current_value}")
        if reasons:
            stale.append(StaleCandidate(repository_dir.name, revision, tuple(reasons)))
    return stale


def _read_state(manifest: Path) -> str:
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError(f"unreadable bundle manifest: {manifest}: {exc}") from exc
    if not isinstance(raw, dict):
        raise BundleError(f"bundle manifest is not an object: {manifest}")
    state = raw.get("state")
    if not isinstance(state, str) or not state:
        raise BundleError(f"bundle manifest has no state: {manifest}")
    return state
