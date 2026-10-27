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
from collections.abc import Iterator, Mapping, Sequence
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
# The manifest field the drift monitor reads: upstream file -> git blob id at the sealed revision.
# Written by readme/bundle/seal.py when it records upstream blobs; absent on bundles sealed without
# them, which the monitor then judges from the sealed facts' cited paths instead.
UPSTREAM_BLOBS_FIELD = "upstream_blobs"
COUNTED_STATES = frozenset({"READY_FOR_PROPOSAL"})
# The only manifest shape this code knows how to trust. A future, incompatible schema_version
# must fail closed rather than have its (possibly differently-shaped) `files` map trusted as if
# it were this one (TB-06, carried over).
SUPPORTED_SCHEMA_VERSIONS = frozenset({1, 2})
# The manifest versions that predate / carry the lane dimension (module docstring).
LANE_LESS_SCHEMA_VERSION = 1
LANE_SCHEMA_VERSION = 2

LANE_R = "R"
LANE_L = "L"
LANES: tuple[str, ...] = (LANE_R, LANE_L)
# Lane R is layout v1's own root; every other lane lives in a reserved sibling directory. The name
# is not a 40-hex revision, so it can never collide with a revision directory.
LANE_DIRNAMES: dict[str, str] = {LANE_L: "lane-l"}
NO_BUNDLE = "NO_BUNDLE"
CORRUPT_BUNDLE = "CORRUPT_BUNDLE"


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


def lane_directory(repository_dir: Path, lane: str) -> Path:
    """Where ``lane``'s ``CURRENT`` pointer and revision directories live under one repository's
    ``candidates/<slug>/``: the slug directory itself for Lane R (layout v1), a reserved sibling
    directory for any other lane. An unknown lane is a defect in the caller, never a guess."""
    if lane == LANE_R:
        return repository_dir
    dirname = LANE_DIRNAMES.get(lane)
    if dirname is None:
        raise ValueError(f"unknown lane {lane!r}; expected one of {LANES}")
    return repository_dir / dirname


def manifest_lane(manifest: Mapping[str, Any]) -> str:
    """The lane a verified manifest belongs to. The versioned reader: schema 1 predates the lane
    dimension and is Lane R by definition; schema 2 must name a known lane."""
    version = manifest.get("schema_version")
    if version == LANE_LESS_SCHEMA_VERSION:
        return LANE_R
    lane = manifest.get("lane")
    if lane not in LANES:
        raise BundleError(f"bundle manifest (schema {version!r}) names unknown lane {lane!r}")
    return str(lane)


@dataclass(frozen=True)
class SealedBundle:
    """The identity and state of one sealed bundle."""

    repository_dir: str
    revision: str
    state: str
    lane: str = LANE_R


def iter_sealed_bundles(root: Path) -> Iterator[SealedBundle]:
    """Yield every sealed bundle under ``root/candidates`` in path order, Lane R then Lane L.

    Every revision of every repository, sealed or not, current or superseded: a raw inventory,
    not a progress count. ``count_current_candidates`` deliberately does not use this -- see the
    module docstring.
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        for lane in LANES:
            lane_root = lane_directory(repository_dir, lane)
            if not lane_root.is_dir():
                continue
            for revision_dir in sorted(p for p in lane_root.iterdir() if p.is_dir()):
                manifest = revision_dir / BUNDLE_MANIFEST_NAME
                if not manifest.is_file():
                    continue
                yield SealedBundle(
                    repository_dir=repository_dir.name,
                    revision=revision_dir.name,
                    state=_read_state(manifest),
                    lane=lane,
                )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bundle(bundle: Path, lane: str | None = None) -> dict[str, Any] | None:
    """The bundle's manifest, after its inventory and every file it lists check out; a missing,
    empty, corrupt, or unsupported-schema manifest fails closed naming the problem. None when
    there is no bundle at all.

    Checks: the manifest is a readable JSON object naming a non-empty ``state``; it declares a
    ``schema_version`` this code knows how to read; its ``files`` inventory is non-empty (an
    empty inventory is not "nothing to verify", it is a bundle that was never really sealed);
    every listed file is present on disk; every listed file's digest matches what is actually
    there; and, when the manifest records ``ledger_totals``, they equal the sums over its
    ``ledger.jsonl`` (``BundleLedgerError``, reason ``LEDGER_TOTALS_MISMATCH``). When ``lane`` is
    given, the manifest must belong to it (:func:`manifest_lane`): a Lane L manifest found in a
    Lane R directory, or the reverse, is corrupt evidence, not a candidate of either lane.
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
    declared = manifest_lane(manifest)
    if lane is not None and declared != lane:
        raise BundleError(
            f"bundle manifest in the Lane {lane} tree declares Lane {declared}: {manifest_path}"
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


def integrity_valid_candidates(root: Path, lane: str = LANE_R) -> int:
    """How many repositories have a ``CURRENT`` bundle in ``lane`` that passes
    :func:`verify_bundle` cleanly.

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
        lane_root = lane_directory(repository_dir, lane)
        current = lane_root / CURRENT_FILENAME
        if not current.is_file():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        try:
            manifest = verify_bundle(lane_root / revision, lane)
        except BundleError:
            continue
        if manifest is not None:
            valid += 1
    return valid


def count_current_candidates(root: Path, lane: str = LANE_R) -> int:
    """Return how many repositories have their ``CURRENT`` revision in ``lane`` sealed in a
    counted state.

    Reads ``CURRENT``, resolves to that exact revision's manifest, and verifies it -- never scans
    every historical revision directory for any counted state (see the module docstring). A
    repository with no ``CURRENT`` file has never sealed anything and is silently not counted; a
    ``CURRENT`` that names a revision without a valid, self-consistent bundle is corrupt evidence
    and is an error. Each lane is counted on its own: a Lane L candidate never counts toward Lane
    R's progress, or the reverse (mission section 1: neither lane is measured by the other's
    delivery).
    """
    return len(current_counted_repository_dirs(root, lane))


def _verified_current(
    repository_dir: Path, lane: str = LANE_R
) -> tuple[str, dict[str, Any]] | None:
    """``(revision, manifest)`` for the bundle ``CURRENT`` names in ``lane`` under
    ``repository_dir`` (the ``candidates/<slug>/`` directory), verified and self-consistent; None
    when the repository has no ``CURRENT`` in that lane at all. Raises :class:`BundleError` for
    any ``CURRENT`` that does not name a verifiable bundle of its own."""
    lane_root = lane_directory(repository_dir, lane)
    current = lane_root / CURRENT_FILENAME
    if not current.is_file():
        return None
    revision = current.read_text(encoding="utf-8").strip()
    manifest = verify_bundle(lane_root / revision, lane)
    if manifest is None:
        raise BundleError(
            f"{repository_dir.name}: Lane {lane} CURRENT names revision {revision!r} with no "
            "sealed bundle there"
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


def current_counted_repository_dirs(root: Path, lane: str = LANE_R) -> set[str]:
    """The repository directories whose ``CURRENT`` bundle in ``lane`` is sealed in a counted
    state -- the set :func:`count_current_candidates` counts, under that function's own raising
    contract."""
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return set()
    counted: set[str] = set()
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        verified = _verified_current(repository_dir, lane)
        if verified is not None and verified[1].get("state") in COUNTED_STATES:
            counted.add(repository_dir.name)
    return counted


def ready_revision(root: Path, repository: str, lane: str = LANE_R) -> str | None:
    """The ``CURRENT`` revision of ``repository`` in ``lane`` when that bundle verifies and is
    sealed in a counted state; None otherwise. A sealed-but-not-ready, superseded, or absent
    bundle is never returned."""
    repository_dir = root / CANDIDATES_DIRNAME / repository.replace("/", "__")
    if not repository_dir.is_dir():
        return None
    verified = _verified_current(repository_dir, lane)
    if verified is None or verified[1].get("state") not in COUNTED_STATES:
        return None
    return verified[0]


def ready_revision_at(bundle_dir: Path, repository: str, lane: str = LANE_R) -> str | None:
    """Like :func:`ready_revision`, generalized to any directory shaped like one repository's
    own ``candidates/<slug>/`` (a ``CURRENT`` pointer beside sealed revision directories) rather
    than always ``root/candidates/<repository's own slug>``. ``repository`` must equal the
    verified manifest's own recorded ``repository`` field exactly (never merely assumed from the
    directory's name or path)."""
    if not bundle_dir.is_dir():
        return None
    verified = _verified_current(bundle_dir, lane)
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
class LaneStatus:
    """One repository's candidate in one lane, as the one status model reports it. ``status`` is
    the ``CURRENT`` manifest's own state, ``NO_BUNDLE`` when the lane has never sealed anything,
    or ``CORRUPT_BUNDLE`` when its ``CURRENT`` does not name a bundle that verifies (``detail``
    says why: a corrupt bundle is shown, never skipped and never counted)."""

    repository_dir: str
    lane: str
    status: str
    revision: str | None = None
    counted: bool = False
    detail: str | None = None


def lane_status(repository_dir: Path, lane: str) -> LaneStatus:
    """The status of ``lane``'s ``CURRENT`` candidate under ``repository_dir``. Never raises: a
    failure of integrity is the status."""
    try:
        verified = _verified_current(repository_dir, lane)
    except (BundleError, OSError) as exc:
        return LaneStatus(repository_dir.name, lane, CORRUPT_BUNDLE, detail=str(exc))
    if verified is None:
        return LaneStatus(repository_dir.name, lane, NO_BUNDLE)
    revision, manifest = verified
    state = str(manifest["state"])
    return LaneStatus(repository_dir.name, lane, state, revision, state in COUNTED_STATES)


def portfolio_status(root: Path) -> list[LaneStatus]:
    """One row per repository per lane (Lane R, then Lane L), in path order: both lanes' candidates
    in the one model. A repository that has sealed in only one lane still reports the other as
    ``NO_BUNDLE``, so an absent lane is visible rather than missing."""
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return []
    return [
        lane_status(repository_dir, lane)
        for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir())
        for lane in LANES
    ]


def counted_by_lane(rows: Sequence[LaneStatus]) -> dict[str, int]:
    """The progress unit, separately for each lane: repositories whose ``CURRENT`` candidate in
    that lane is in a counted state."""
    return {lane: sum(1 for row in rows if row.lane == lane and row.counted) for lane in LANES}


@dataclass(frozen=True)
class StaleCandidate:
    """One CURRENT candidate whose sealed ``dependencies.json`` names a component older than
    what the running code currently declares."""

    repository_dir: str
    revision: str
    reasons: tuple[str, ...]


def stale_candidates(
    root: Path, current_components: Mapping[str, str], lane: str = LANE_R
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
        lane_root = lane_directory(repository_dir, lane)
        current = lane_root / CURRENT_FILENAME
        if not current.is_file():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        deps_path = lane_root / revision / DEPENDENCIES_FILENAME
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
