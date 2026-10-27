"""The drift monitor: is each enabled repository's upstream default branch still the revision its
sealed bundle was built from?

G7-W06 (``docs/EXECUTION_STATE_MACHINE.md`` G7 work item 3): an unattended, read-only observation.
For each enabled registry entry it reads the repository's current default-branch head through
``github/read_client.py`` (one bounded GET pair, the same read the redetection pass uses) and
compares it with the revision the repository's ``CURRENT`` sealed bundle names. Each repository
receives exactly one status:

- ``CURRENT``: the bundle still reflects everything it consumed. Either the head equals the
  bundle's source revision, or the head moved but no path the README consumed changed (the row's
  ``change`` says ``IRRELEVANT_CHANGE``: a release-bump commit is not a reseal).
- ``DRIFTED``: a consumed path changed (``change`` ``RELEVANT_CHANGE``): the README, a manifest, a
  file a fact cites, or, at the 30-day freshness check, a registry reading the facts recorded.
- ``UNKNOWN``: whether a consumed path changed cannot be decided (an unreadable or truncated tree,
  a bundle with neither recorded blob ids nor readable facts). Fail closed: never CURRENT, never
  DRIFTED.
- ``NO_BUNDLE``: no usable sealed bundle (none, a ``CURRENT`` that names none, or one failing
  integrity verification). ``detail`` says which.
- ``UNREACHABLE``: the head could not be read. The failure is recorded and the run continues with
  the remaining repositories; one repository never aborts the others.

Relevance is decided by ``relevance.py`` (``classify_change``): over the files the candidate's own
facts cite (plus README, license and notices), from the git blob ids ``readme/bundle/
seal.py`` recorded in the manifest, or, for a bundle sealed without them, from the sealed facts'
cited paths against the sealed-revision and head trees. An unrelated file change never drifts a
repository. ``freshness.py`` re-reads the package registry for a bundle older than 30 days. The
status is a deterministic fact about upstream and local disk, so no LLM is involved (``AGENTS.md``,
Agentic and Deterministic Boundary). Nothing here writes to any repository, and the only
credential is the read-only token the caller passes in. ``observe_drift`` takes its GitHub readers
as arguments, so tests inject fakes and never reach the network.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from repo_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    LANE_R,
    BundleError,
    lane_directory,
    verify_bundle,
)
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.core.secrets import redact
from repo_presenter.github.read_client import (
    DefaultBranchRead,
    TreeRead,
    fetch_default_branch_sha,
    fetch_tree,
)
from repo_presenter.monitor.freshness import (
    FreshnessResult,
    freshness_check,
    freshness_due,
)
from repo_presenter.monitor.relevance import (
    Classification,
    LiveObservation,
    SealedScope,
    classify_change,
    load_scope,
    needs_head_tree,
    needs_sealed_tree,
    read_sealed_facts,
)

Status = Literal["CURRENT", "DRIFTED", "UNKNOWN", "NO_BUNDLE", "UNREACHABLE"]
STATUSES: tuple[Status, ...] = (
    "CURRENT",
    "DRIFTED",
    "UNKNOWN",
    "NO_BUNDLE",
    "UNREACHABLE",
)
CHANGES: tuple[str, ...] = (
    "NO_CHANGE",
    "IRRELEVANT_CHANGE",
    "RELEVANT_CHANGE",
    "UNKNOWN",
    "UNREACHABLE",
)
SCHEMA_VERSION = 1
_REVISION = re.compile(r"^[0-9a-f]{40}$")

HeadReader = Callable[..., DefaultBranchRead]
TreeReader = Callable[..., TreeRead]
RegistryObserve = Callable[..., Any]


@dataclass(frozen=True)
class RepositoryDrift:
    """One repository's observation. A revision the run never observed is ``None``."""

    repository: str
    mode: str
    status: Status
    head_revision: str | None
    branch: str | None
    bundle_revision: str | None
    detail: str | None = None
    # The relevance class (``relevance.ChangeClass``) behind ``status``; ``None`` where no
    # classification ran (no bundle, unreachable head), and absent from evidence older than this.
    change: str | None = None


def observe_drift(
    root: Path,
    entries: Iterable[RegistryEntry],
    *,
    token: str,
    read_head: HeadReader = fetch_default_branch_sha,
    read_tree: TreeReader = fetch_tree,
    freshness_observe: RegistryObserve | None = None,
    now: datetime | None = None,
    lane: str = LANE_R,
) -> list[RepositoryDrift]:
    """Observe each entry in order. A failure on one entry is recorded, never raised past it.

    ``freshness_observe`` (the registry probe) enables the 30-day freshness check for bundles
    older than ``FRESHNESS_MAX_AGE``; left ``None`` the check does not run and no registry is read.
    ``lane`` selects whose ``CURRENT`` candidate is observed (Lane R by default); a repository is
    observed once per lane, the caller choosing which (a Lane L bundle consumes the same README,
    manifest and cited paths, so the same relevance rules judge it).
    """
    return [
        observe_repository(
            root,
            entry,
            token=token,
            read_head=read_head,
            read_tree=read_tree,
            freshness_observe=freshness_observe,
            now=now,
            lane=lane,
        )
        for entry in entries
    ]


def observe_repository(
    root: Path,
    entry: RegistryEntry,
    *,
    token: str,
    read_head: HeadReader,
    read_tree: TreeReader = fetch_tree,
    freshness_observe: RegistryObserve | None = None,
    now: datetime | None = None,
    lane: str = LANE_R,
) -> RepositoryDrift:
    """Read one repository's head, then classify it against its ``CURRENT`` sealed bundle in
    ``lane``."""
    repository = entry.repository
    try:
        read = read_head(repository, token=token)
    except Exception as exc:  # noqa: BLE001 -- per-repository isolation boundary
        message = redact(f"{type(exc).__name__}: {exc}", [token])
        return RepositoryDrift(
            repository, entry.mode, "UNREACHABLE", None, None, None, message
        )
    if read.sha is None:
        message = redact(read.error or "no default-branch head returned", [token])
        return RepositoryDrift(
            repository, entry.mode, "UNREACHABLE", None, read.branch, None, message
        )
    bundle_revision, manifest, problem = current_bundle(root, repository, lane)
    if bundle_revision is None or manifest is None:
        return RepositoryDrift(
            repository, entry.mode, "NO_BUNDLE", read.sha, read.branch, None, problem
        )
    bundle = bundle_directory(root, repository, lane) / bundle_revision
    scope = load_scope(bundle, bundle_revision, manifest)
    classification = classify_change(
        scope,
        _read_live(repository, read.sha, scope, token=token, read_tree=read_tree),
    )
    if (
        freshness_observe is not None
        and classification.change in ("NO_CHANGE", "IRRELEVANT_CHANGE")
        and freshness_due(manifest.get("sealed_at"), now=now)
    ):
        classification = _with_freshness(
            classification, bundle, entry.ecosystem, scope, freshness_observe
        )
    return RepositoryDrift(
        repository,
        entry.mode,
        _STATUS_OF_CHANGE[classification.change],
        read.sha,
        read.branch,
        bundle_revision,
        None if classification.change == "NO_CHANGE" else classification.detail,
        classification.change,
    )


# A head that moved without touching anything the README consumed leaves the bundle CURRENT: the
# README is still true of the new head, so nothing is due (``change`` keeps the distinction).
_STATUS_OF_CHANGE: dict[str, Status] = {
    "NO_CHANGE": "CURRENT",
    "IRRELEVANT_CHANGE": "CURRENT",
    "RELEVANT_CHANGE": "DRIFTED",
    "UNKNOWN": "UNKNOWN",
    "UNREACHABLE": "UNREACHABLE",
}


def _read_tree(
    repository: str, revision: str, *, token: str, read_tree: TreeReader
) -> TreeRead:
    try:
        return read_tree(repository, revision, token=token)
    except Exception as exc:  # noqa: BLE001 -- per-repository isolation, as for the head read
        message = redact(f"{type(exc).__name__}: {exc}", [token])
        return TreeRead(repository, revision, error=message)


def _read_live(
    repository: str, head: str, scope: SealedScope, *, token: str, read_tree: TreeReader
) -> LiveObservation:
    """Read only the trees the classification needs: the head's when blob ids are recorded or the
    head moved, the sealed revision's only to decide a moved head with no recorded blob ids."""
    head_tree = (
        _read_tree(repository, head, token=token, read_tree=read_tree)
        if needs_head_tree(scope, head)
        else None
    )
    sealed_tree = (
        _read_tree(repository, scope.revision, token=token, read_tree=read_tree)
        if needs_sealed_tree(scope, head)
        else None
    )
    return LiveObservation(head, head_tree, sealed_tree)


def _with_freshness(
    classification: Classification,
    bundle: Path,
    ecosystem: str,
    scope: SealedScope,
    observe: RegistryObserve,
) -> Classification:
    """Fold the 30-day registry re-check into an otherwise unchanged classification.

    Only a RELEVANT reading changes it; an inconclusive or unchanged one leaves it as it was.
    """
    facts = read_sealed_facts(bundle)
    if facts is None:
        return classification
    result: FreshnessResult = freshness_check(
        ecosystem, facts, observe=observe, consumed_fact_ids=scope.consumed_fact_ids
    )
    if result.change != "RELEVANT_CHANGE":
        return classification
    return Classification("RELEVANT_CHANGE", f"freshness: {result.detail}")


def bundle_directory(root: Path, repository: str, lane: str = LANE_R) -> Path:
    """The repository's candidate directory in ``lane`` (``CURRENT`` and one directory per
    revision)."""
    return lane_directory(
        root / CANDIDATES_DIRNAME / repository.replace("/", "__"), lane
    )


def current_bundle(
    root: Path, repository: str, lane: str = LANE_R
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    """The revision ``CURRENT`` names and its verified manifest, when it has a sealed,
    self-consistent bundle.

    Returns ``(revision, manifest, None)`` on success and ``(None, None, reason)`` otherwise. Only
    the ``CURRENT`` pointer is consulted, the same rule ``core/candidates.py`` applies to progress
    counting, so a superseded revision directory left behind can never stand in for the current
    bundle.
    """
    directory = bundle_directory(root, repository, lane)
    pointer = directory / CURRENT_FILENAME
    if not pointer.is_file():
        return None, None, "no CURRENT pointer"
    try:
        revision = pointer.read_text(encoding="utf-8").strip()
    except (OSError, ValueError) as exc:
        return None, None, f"CURRENT pointer is unreadable: {exc}"
    if not _REVISION.fullmatch(revision):
        return None, None, "CURRENT does not name a 40-character revision"
    try:
        manifest = verify_bundle(directory / revision, lane)
    except (BundleError, OSError) as exc:
        return None, None, f"CURRENT bundle fails verification: {exc}"
    if manifest is None:
        return None, None, f"CURRENT names {revision} with no sealed bundle"
    if manifest.get("revision") != revision or manifest.get("repository") != repository:
        return (
            None,
            None,
            f"bundle manifest does not describe {repository} at {revision}",
        )
    return revision, manifest, None


def drift_document(
    observations: Sequence[RepositoryDrift],
    *,
    observed_at: str,
    owner: str | None,
    discovery: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The evidence document: a status summary and one row per repository, sorted by name.

    ``discovery`` (``discovery.DiscoveryReport.to_json()``) is an additive section: present only
    when the run reconciled the registry against its organizations, so a document without it is
    exactly the schema 1 document that existed before and every reader of it is unaffected.
    """
    ordered = sorted(observations, key=lambda observation: observation.repository)
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "observed_at": observed_at,
        "owner": owner,
        "summary": {
            status: sum(1 for observation in ordered if observation.status == status)
            for status in STATUSES
        },
        # Additive (schema_version 1 is unchanged): how many rows each relevance class has.
        "changes": {
            change: sum(1 for observation in ordered if observation.change == change)
            for change in CHANGES
        },
        "repositories": [asdict(observation) for observation in ordered],
    }
    if discovery is not None:
        document["discovery"] = dict(discovery)
    return document


def write_drift_document(document: dict[str, Any], path: Path) -> Path:
    """Write the evidence document as deterministic JSON, creating its directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path
