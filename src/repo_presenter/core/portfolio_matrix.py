"""The portfolio matrix, derived from evidence rather than typed into project/state.yaml.

Independent sources, reported side by side and never merged into one "accepted" number:

* the registry (what is in scope: repository, ecosystem, mode);
* the SEAL HISTORY on the state remote (every commit on every bundle ref,
  ``core/state/bundle_store.seal_history``) -- the only source a count is taken from;
* the durable transaction record, one per repository per lane: the latest ATTEMPT's routing state
  (a later run overwrites an earlier one, and a failed re-run under a new version set moves it
  ACCEPTED -> INVALIDATED). Reported as attempt status only; nothing counted reads it;
* the sealed bundles committed under ``candidates/`` (what can actually be inspected).

Owner rules (2026-11-06, ``core/version_set.py``): a lane count is the number of repositories with
a counted seal (pipeline-good manifest state, model-reviewed ACCEPT) under ONE version-set
fingerprint. ``lane_*_pipeline_good`` is the CURRENT fingerprint's count -- the only set that can
form a release set; every older fingerprint's count is reported separately and never summed in.
A seal is immutable: a later failed run never removes it from the count of its own version set.

Owner review is not tracked anywhere in this repository, so the summary says so instead of
inventing a number.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from repo_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    LANE_L,
    LANE_R,
    LANES,
    NO_BUNDLE,
    lane_status,
)
from repo_presenter.core.state.bundle_store import BUNDLE_REF_PREFIX, SealRecord, bundle_ref
from repo_presenter.core.state.git_backend import GitStateBackend
from repo_presenter.core.version_set import fingerprint, group_by_fingerprint, version_set_report

NO_RECORD = "NO_RECORD"
#: Transaction-record states a scheduler treats as "done for now". Routing only: no count reads the
#: record (see the module docstring).
PIPELINE_GOOD_STATES = frozenset({"ACCEPTED", "READY_FOR_PROPOSAL"})

StateReader = Callable[[str, str], str | None]
SealHistory = Mapping[tuple[str, str], Sequence[SealRecord]]


class _Entry(Protocol):
    repository: str
    ecosystem: str
    mode: str


@dataclass(frozen=True)
class MatrixRow:
    repository: str
    ecosystem: str
    mode: str
    record_r: str
    record_l: str
    committed_r: str
    committed_l: str
    stored_r: bool = False
    stored_l: bool = False
    # Full version-set fingerprints under which this repository has a counted seal, per lane.
    seal_sets_r: tuple[str, ...] = ()
    seal_sets_l: tuple[str, ...] = ()
    # Every seal commit on the lane's bundle ref (counted or not).
    seals_r: int = 0
    seals_l: int = 0


def counted_fingerprints(seals: Iterable[SealRecord], lane: str) -> tuple[str, ...]:
    """The sorted, distinct version-set fingerprints of the ``seals`` that count (pipeline-good
    manifest state, model ACCEPT, a readable dependencies record)."""
    found = set()
    for seal in seals:
        if seal.counted and seal.dependencies is not None:
            found.add(fingerprint(seal.dependencies, lane))
    return tuple(sorted(found))


def stored_bundle_refs(remote: str = "origin") -> frozenset[str]:
    """The ref names under the durable bundle prefix on ``remote`` (one ``git ls-remote``)."""
    listed = subprocess.run(
        ["git", "ls-remote", remote, f"{BUNDLE_REF_PREFIX}/*"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return frozenset(line.split("\t")[1] for line in listed.splitlines() if "\t" in line)


@contextmanager
def backend_reader(remote: str = "origin") -> Iterator[StateReader]:
    """A ``StateReader`` over the real git-ref backend: ``reader(repository, lane)`` is the
    record's (latest attempt's) state, or ``None`` when the lane has no record."""
    backends = {lane: GitStateBackend(remote=remote, lane=lane) for lane in LANES}
    try:

        def read(repository: str, lane: str) -> str | None:
            record = backends[lane].load(repository)
            return None if record is None else str(record.state)

        yield read
    finally:
        for backend in backends.values():
            backend.close()


def build_matrix(
    entries: Iterable[_Entry],
    read_state: StateReader,
    root: Path,
    stored_refs: Iterable[str] = (),
    seals: SealHistory | None = None,
) -> list[MatrixRow]:
    candidates = root / CANDIDATES_DIRNAME
    stored = frozenset(stored_refs)
    seals = seals or {}
    rows: list[MatrixRow] = []
    for entry in entries:
        slug_dir = candidates / entry.repository.replace("/", "__")
        committed = {
            lane: (lane_status(slug_dir, lane).status if slug_dir.is_dir() else NO_BUNDLE)
            for lane in LANES
        }
        lane_seals = {lane: list(seals.get((entry.repository, lane), ())) for lane in LANES}
        rows.append(
            MatrixRow(
                repository=entry.repository,
                ecosystem=entry.ecosystem,
                mode=entry.mode,
                record_r=read_state(entry.repository, LANE_R) or NO_RECORD,
                record_l=read_state(entry.repository, LANE_L) or NO_RECORD,
                committed_r=committed[LANE_R],
                committed_l=committed[LANE_L],
                stored_r=bundle_ref(entry.repository, LANE_R) in stored,
                stored_l=bundle_ref(entry.repository, LANE_L) in stored,
                seal_sets_r=counted_fingerprints(lane_seals[LANE_R], LANE_R),
                seal_sets_l=counted_fingerprints(lane_seals[LANE_L], LANE_L),
                seals_r=len(lane_seals[LANE_R]),
                seals_l=len(lane_seals[LANE_L]),
            )
        )
    return rows


def lane_version_sets(
    rows: Iterable[MatrixRow], lane: str, current: str | None
) -> dict[str, object]:
    """One lane's counted seals grouped by version-set fingerprint, never summed across sets."""
    pairs = [
        (row.repository, value)
        for row in rows
        for value in (row.seal_sets_r if lane == LANE_R else row.seal_sets_l)
    ]
    return version_set_report(group_by_fingerprint(pairs), current)


def summarize(
    rows: Iterable[MatrixRow], current: Mapping[str, str] | None = None
) -> dict[str, object]:
    """``current`` is ``{lane: current version-set fingerprint}``
    (``version_set.current_fingerprints``); without it no set is current and both counts are 0."""
    rows = list(rows)
    current = current or {}
    r_states = Counter(row.record_r for row in rows)
    l_states = Counter(row.record_l for row in rows)
    sets_r = lane_version_sets(rows, LANE_R, current.get(LANE_R))
    sets_l = lane_version_sets(rows, LANE_L, current.get(LANE_L))
    good_r = set(sets_r["current_repositories"])  # type: ignore[call-overload]
    good_l = set(sets_l["current_repositories"])  # type: ignore[call-overload]
    return {
        "registry_total": len(rows),
        "write_eligible_mode_full": sum(1 for row in rows if row.mode == "full"),
        # the latest ATTEMPT per lane (the transaction record's routing state; never a count)
        "lane_r_record_states": dict(sorted(r_states.items())),
        "lane_l_record_states": dict(sorted(l_states.items())),
        "lane_r_attempted": sum(1 for row in rows if row.record_r != NO_RECORD),
        "lane_l_attempted": sum(1 for row in rows if row.record_l != NO_RECORD),
        # counted seals under the CURRENT version set only: the release-forming count
        "lane_r_pipeline_good": len(good_r),
        "lane_l_pipeline_good": len(good_l),
        "both_lanes_pipeline_good": sorted(good_r & good_l),
        "lane_r_version_sets": sets_r,
        "lane_l_version_sets": sets_l,
        "lane_r_seals_total": sum(row.seals_r for row in rows),
        "lane_l_seals_total": sum(row.seals_l for row in rows),
        "committed_bundles_lane_r": sum(1 for row in rows if row.committed_r != NO_BUNDLE),
        "committed_bundles_lane_l": sum(1 for row in rows if row.committed_l != NO_BUNDLE),
        "durable_bundles_lane_r": sum(1 for row in rows if row.stored_r),
        "durable_bundles_lane_l": sum(1 for row in rows if row.stored_l),
        "owner_reviewed": "not tracked: no owner review record exists in this repository",
    }


def _sets_cell(sets: tuple[str, ...], current: str | None) -> str:
    if not sets:
        return "-"
    has_current = current is not None and current in sets
    return ("cur+" if has_current else "") + f"{len(sets) - int(has_current)}old"


def render(
    rows: Iterable[MatrixRow],
    summary: dict[str, object],
    current: Mapping[str, str] | None = None,
) -> str:
    current = current or {}
    lines = [
        f"{'repository':<58} {'eco':<10} {'mode':<8} {'R attempt':<20} {'L attempt':<20} "
        f"{'R bundle':<10} {'L bundle':<10} {'R stored':<9} {'L stored':<9} "
        f"{'R seal sets':<12} {'L seal sets':<12}"
    ]
    for row in rows:
        lines.append(
            f"{row.repository:<58} {row.ecosystem:<10} {row.mode:<8} {row.record_r:<20} "
            f"{row.record_l:<20} {row.committed_r:<10} {row.committed_l:<10} "
            f"{'yes' if row.stored_r else '-':<9} {'yes' if row.stored_l else '-':<9} "
            f"{_sets_cell(row.seal_sets_r, current.get(LANE_R)):<12} "
            f"{_sets_cell(row.seal_sets_l, current.get(LANE_L)):<12}"
        )
    lines.append("")
    lines.extend(f"{key}: {value}" for key, value in summary.items())
    return "\n".join(lines)
