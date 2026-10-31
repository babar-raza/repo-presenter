"""The portfolio matrix, derived from evidence rather than typed into project/state.yaml.

Three independent sources, reported side by side and never merged into one "accepted" number:

* the registry (what is in scope: repository, ecosystem, mode);
* the durable transaction record on the state remote, one per repository per lane (the latest run's
  state, so a later run overwrites an earlier one);
* the sealed bundles committed under ``candidates/`` (what can actually be inspected).

A record in ACCEPTED or READY_FOR_PROPOSAL is a *pipeline-level* observation only. Owner review is
not tracked anywhere in this repository, so the summary says so instead of inventing a number.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Iterator
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
from repo_presenter.core.state.git_backend import GitStateBackend

NO_RECORD = "NO_RECORD"
PIPELINE_GOOD_STATES = frozenset({"ACCEPTED", "READY_FOR_PROPOSAL"})

StateReader = Callable[[str, str], str | None]


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


@contextmanager
def backend_reader(remote: str = "origin") -> Iterator[StateReader]:
    """A ``StateReader`` over the real git-ref backend: ``reader(repository, lane)`` is the
    record's state, or ``None`` when the lane has no record."""
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
    entries: Iterable[_Entry], read_state: StateReader, root: Path
) -> list[MatrixRow]:
    candidates = root / CANDIDATES_DIRNAME
    rows: list[MatrixRow] = []
    for entry in entries:
        slug_dir = candidates / entry.repository.replace("/", "__")
        committed = {
            lane: (lane_status(slug_dir, lane).status if slug_dir.is_dir() else NO_BUNDLE)
            for lane in LANES
        }
        rows.append(
            MatrixRow(
                repository=entry.repository,
                ecosystem=entry.ecosystem,
                mode=entry.mode,
                record_r=read_state(entry.repository, LANE_R) or NO_RECORD,
                record_l=read_state(entry.repository, LANE_L) or NO_RECORD,
                committed_r=committed[LANE_R],
                committed_l=committed[LANE_L],
            )
        )
    return rows


def summarize(rows: Iterable[MatrixRow]) -> dict[str, object]:
    rows = list(rows)
    r_states = Counter(row.record_r for row in rows)
    l_states = Counter(row.record_l for row in rows)
    good_r = {row.repository for row in rows if row.record_r in PIPELINE_GOOD_STATES}
    good_l = {row.repository for row in rows if row.record_l in PIPELINE_GOOD_STATES}
    return {
        "registry_total": len(rows),
        "write_eligible_mode_full": sum(1 for row in rows if row.mode == "full"),
        "lane_r_record_states": dict(sorted(r_states.items())),
        "lane_l_record_states": dict(sorted(l_states.items())),
        "lane_r_attempted": sum(1 for row in rows if row.record_r != NO_RECORD),
        "lane_l_attempted": sum(1 for row in rows if row.record_l != NO_RECORD),
        "lane_r_pipeline_good": len(good_r),
        "lane_l_pipeline_good": len(good_l),
        "both_lanes_pipeline_good": sorted(good_r & good_l),
        "committed_bundles_lane_r": sum(1 for row in rows if row.committed_r != NO_BUNDLE),
        "committed_bundles_lane_l": sum(1 for row in rows if row.committed_l != NO_BUNDLE),
        "owner_reviewed": "not tracked: no owner review record exists in this repository",
    }


def render(rows: Iterable[MatrixRow], summary: dict[str, object]) -> str:
    lines = [
        f"{'repository':<58} {'eco':<10} {'mode':<8} {'R record':<20} {'L record':<20} "
        f"{'R bundle':<10} {'L bundle':<10}"
    ]
    for row in rows:
        lines.append(
            f"{row.repository:<58} {row.ecosystem:<10} {row.mode:<8} {row.record_r:<20} "
            f"{row.record_l:<20} {row.committed_r:<10} {row.committed_l:<10}"
        )
    lines.append("")
    lines.extend(f"{key}: {value}" for key, value in summary.items())
    return "\n".join(lines)
