"""The hosted portfolio monitor: one read-only pass of drift, discovery and freshness, reported to a
state ref (WP-3, owner ruling R50 (2026-11-22): the change-detection component of the previous
project works here; R5/R20/BL-187/BL-190).

For every active registry entry and each lane the monitor materializes the CURRENT sealed bundle
from its bundle ref (read-only), reads the upstream default-branch head with the workflow token and
classifies the change against the files the sealed README consumed (``drift.observe_repository``):

* ``relevant``    a consumed path changed (or the 30-day registry re-check changed): the cell is DRIFTED
                  and the cohort selector (``scripts/select_scheduled_cohort.py``) puts it in the
                  next cohort even though its seal still re-certifies;
* ``irrelevant``  the head moved but nothing the README consumed did: the seal stays, no work;
* ``unchanged``   head equals the sealed revision;
* ``unreadable``  the change cannot be decided (unreadable tree or head): fail closed, never
                  reported as current;
* ``no_bundle``   no sealed bundle in that lane yet.

It also reconciles the registry against each authorized organization's listing (new repositories
that are not admitted) and lists every sealed bundle that is due its 30-day freshness re-check.

Nothing here writes to an upstream repository, calls a provider or mutates a bundle. The report
goes to ``refs/repository-presenter-state/monitor/report`` (this repository's own state namespace,
the same compare-and-swap writer the provider-spend ledger uses) and to the job summary.

Usage:
    python -m repo_presenter.monitor.run --remote <url> [--out report.json] [--summary path]
        [--no-write] [--bundle-root DIR] [--repository owner/name] [--lanes R,L]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo_presenter.core.candidates import CANDIDATES_DIRNAME, LANE_L, LANE_R, LANES
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.core.secrets import redact
from repo_presenter.github.read_client import fetch_default_branch_sha
from repo_presenter.monitor import drift as drift_module
from repo_presenter.monitor.drift import (
    HeadReader,
    RepositoryDrift,
    current_bundle,
    observe_repository,
)
from repo_presenter.monitor.freshness import freshness_due

MONITOR_REF = "refs/repository-presenter-state/monitor/report"
SCHEMA_VERSION = 1
REPO_ROOT = Path(__file__).resolve().parents[3]

#: The report's per-cell change class, from drift's relevance ``change`` (the three the owner named
#: -- relevant, irrelevant, unreadable -- plus the two that are not a change at all).
CHANGE_CLASS = {
    "RELEVANT_CHANGE": "relevant",
    "IRRELEVANT_CHANGE": "irrelevant",
    "NO_CHANGE": "unchanged",
    "UNKNOWN": "unreadable",
    "UNREACHABLE": "unreadable",
}
CLASSES: tuple[str, ...] = ("relevant", "irrelevant", "unchanged", "unreadable", "no_bundle")

BundleExporter = Callable[[str, str, Path], None]


def change_class(row: RepositoryDrift) -> str:
    """The report class of one drift row; a row with no classification is ``no_bundle`` (or
    ``unreadable`` when its head could not be read)."""
    if row.change in CHANGE_CLASS:
        return CHANGE_CLASS[row.change]
    return "unreadable" if row.status == "UNREACHABLE" else "no_bundle"


def _cell(row: RepositoryDrift, lane: str, *, sealed_at: str | None, due: bool) -> dict[str, Any]:
    return {
        "repository": row.repository,
        "lane": lane,
        "status": row.status,
        "class": change_class(row),
        "change": row.change,
        "head_revision": row.head_revision,
        "bundle_revision": row.bundle_revision,
        "sealed_at": sealed_at,
        "freshness_due": due,
        "detail": row.detail,
    }


def _state_exporter(remote: str, token: str | None) -> BundleExporter:
    from repo_presenter.core.state.bundle_store import export_bundle

    def export(repository: str, lane: str, destination: Path) -> None:
        export_bundle(repository, lane, destination / CANDIDATES_DIRNAME, remote=remote, token=token)

    return export


def observe_cells(
    entries: Iterable[RegistryEntry],
    *,
    token: str,
    export: BundleExporter | None,
    bundle_root: Path | None,
    read_head: HeadReader | None = None,
    freshness_observe: Callable[..., Any] | None = None,
    lanes: Sequence[str] = LANES,
    now: datetime | None = None,
    read_tree: Callable[..., Any] | None = None,
    scratch_parent: Path | None = None,
) -> list[dict[str, Any]]:
    """One report cell per (entry, lane). A failure on one cell is a recorded row, never an
    exception past it. With ``bundle_root`` the sealed bundles are read from that ``candidates/``
    parent; otherwise ``export`` materializes each into a scratch directory removed straight away
    (disk stays flat across 40 cells)."""
    heads: dict[str, Any] = {}
    # Resolved at call time (not as default arguments) so a caller or test can swap the readers.
    head_reader = read_head or fetch_default_branch_sha
    tree_reader = read_tree or drift_module.fetch_tree

    def cached_head(repository: str, *, token: str) -> Any:
        if repository not in heads:
            try:
                heads[repository] = head_reader(repository, token=token)
            except Exception as exc:  # noqa: BLE001 -- cached so both lanes record the same failure
                heads[repository] = exc
        if isinstance(heads[repository], Exception):
            raise heads[repository]
        return heads[repository]

    cells: list[dict[str, Any]] = []
    extra: dict[str, Any] = {"read_tree": tree_reader}
    for entry in entries:
        for lane in lanes:
            scratch: Path | None = None
            root = bundle_root
            problem: str | None = None
            if root is None:
                scratch = Path(tempfile.mkdtemp(prefix="monitor-", dir=scratch_parent))
                root = scratch
                try:
                    assert export is not None
                    export(entry.repository, lane, scratch)
                except Exception as exc:  # noqa: BLE001 -- per-cell isolation boundary
                    problem = redact(f"{type(exc).__name__}: {exc}", [token])
            try:
                if problem is not None:
                    # No stored bundle (or an unreadable one): still read the head so the report
                    # says whether upstream is reachable, but there is nothing to compare.
                    row = _no_bundle(entry, lane, problem, token, cached_head)
                    cells.append(_cell(row, lane, sealed_at=None, due=False))
                    continue
                _, manifest, _ = current_bundle(root, entry.repository, lane)
                sealed_at = None if manifest is None else str(manifest.get("sealed_at") or "") or None
                row = observe_repository(
                    root, entry, token=token, read_head=cached_head,
                    freshness_observe=freshness_observe, now=now, lane=lane, **extra,
                )
                due = manifest is not None and freshness_due(sealed_at, now=now)
                cells.append(_cell(row, lane, sealed_at=sealed_at, due=due))
            except Exception as exc:  # noqa: BLE001 -- one cell never aborts the portfolio
                message = redact(f"{type(exc).__name__}: {exc}", [token])
                cells.append(
                    {"repository": entry.repository, "lane": lane, "status": "UNKNOWN",
                     "class": "unreadable", "change": "UNKNOWN", "head_revision": None,
                     "bundle_revision": None, "sealed_at": None, "freshness_due": False,
                     "detail": message}
                )
            finally:
                if scratch is not None:
                    shutil.rmtree(scratch, ignore_errors=True)
    return cells


def _no_bundle(
    entry: RegistryEntry, lane: str, problem: str, token: str, read_head: HeadReader
) -> RepositoryDrift:
    try:
        read = read_head(entry.repository, token=token)
    except Exception as exc:  # noqa: BLE001
        return RepositoryDrift(
            entry.repository, entry.mode, "UNREACHABLE", None, None, None,
            redact(f"{type(exc).__name__}: {exc}", [token]),
        )
    if read.sha is None:
        return RepositoryDrift(
            entry.repository, entry.mode, "UNREACHABLE", None, read.branch, None,
            redact(read.error or "no default-branch head returned", [token]),
        )
    return RepositoryDrift(
        entry.repository, entry.mode, "NO_BUNDLE", read.sha, read.branch, None, problem
    )


def report_document(
    cells: Sequence[Mapping[str, Any]],
    *,
    observed_at: str,
    run_id: str = "",
    discovery: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The state-ref document: per-cell rows, counts per class, the drifted and due lists, and the
    discovery section when it ran."""
    ordered = sorted(cells, key=lambda cell: (cell["repository"], cell["lane"]))
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "monitor_report",
        "observed_at": observed_at,
        "run_id": run_id,
        "summary": {name: sum(1 for c in ordered if c["class"] == name) for name in CLASSES},
        "drifted": [
            {"repository": c["repository"], "lane": c["lane"],
             "bundle_revision": c["bundle_revision"], "head_revision": c["head_revision"],
             "detail": c["detail"]}
            for c in ordered if c["class"] == "relevant"
        ],
        "freshness_due": [
            {"repository": c["repository"], "lane": c["lane"], "sealed_at": c["sealed_at"]}
            for c in ordered if c["freshness_due"]
        ],
        "cells": ordered,
    }
    if discovery is not None:
        document["discovery"] = dict(discovery)
    return document


def drifted_cells(document: Mapping[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    """``{(repository, lane): row}`` of the cells a report names as relevantly changed. A missing,
    malformed or foreign document names none (the cohort selector then behaves exactly as before)."""
    if not isinstance(document, Mapping) or document.get("kind") != "monitor_report":
        return {}
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for row in document.get("drifted") or []:
        if isinstance(row, Mapping) and row.get("repository") and row.get("lane") in LANES:
            found[(str(row["repository"]), str(row["lane"]))] = dict(row)
    return found


def read_report(*, remote: str, token: str | None) -> tuple[dict[str, Any] | None, str]:
    """``(document, note)`` from the monitor state ref; ``(None, why)`` when absent or unreadable
    (read-only; never raises)."""
    from repo_presenter.core.state.git_backend import GitJsonRef

    try:
        _, document = GitJsonRef(MONITOR_REF, remote=remote, token=token).read()
    except Exception as exc:  # noqa: BLE001
        return None, f"monitor report not readable ({type(exc).__name__}: {str(exc)[:160]})"
    if document is None:
        return None, "no monitor report on the state ref yet"
    return dict(document), ""


def write_report(document: dict[str, Any], *, remote: str, token: str | None) -> None:
    from repo_presenter.core.state.git_backend import GitJsonRef

    GitJsonRef(MONITOR_REF, remote=remote, token=token).update(lambda _current: document)


def summary_markdown(document: Mapping[str, Any]) -> str:
    counts = document["summary"]
    lines = [
        "### Portfolio monitor (read-only)",
        "",
        f"observed {document['observed_at']} - " + ", ".join(f"{counts[name]} {name}" for name in CLASSES),
        "",
    ]
    if document["drifted"]:
        lines += ["| Drifted cell | Sealed | Head | Why |", "|---|---|---|---|"]
        for row in document["drifted"]:
            lines.append(
                f"| {row['repository']} Lane {row['lane']} | {(row['bundle_revision'] or '')[:12]} "
                f"| {(row['head_revision'] or '')[:12]} | {(row['detail'] or '').replace('|', '/')[:160]} |"
            )
    else:
        lines.append("No cell has a relevant upstream change.")
    unreadable = [c for c in document["cells"] if c["class"] == "unreadable"]
    if unreadable:
        lines += ["", f"**{len(unreadable)} unreadable (fail closed, not current):** "
                  + ", ".join(f"{c['repository']}/{c['lane']}" for c in unreadable)]
    if document["freshness_due"]:
        lines += ["", f"{len(document['freshness_due'])} sealed bundle(s) are due the 30-day registry re-check."]
    section = document.get("discovery")
    if isinstance(section, Mapping):
        counts_d = section.get("counts") or {}
        lines += ["", "discovery: " + ", ".join(f"{k} {v}" for k, v in sorted(counts_d.items()))]
    return "\n".join(lines) + "\n"


def _discovery(registry_path: Path, token: str, now: datetime) -> dict[str, Any] | None:
    from repo_presenter.monitor.discovery import observe_registry_gaps
    from repo_presenter.monitor.org_listing import list_organization_repositories

    registry = load_registry(registry_path)
    report = observe_registry_gaps(
        REPO_ROOT, registry, lister=list_organization_repositories, token=token, now=now
    )
    return report.to_json()


def _freshness_observer() -> Callable[..., Any]:
    from repo_presenter.extractors.surface.registry import observe

    return observe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    parser.add_argument("--remote", default="origin", help="the state remote (bundle refs, report ref)")
    parser.add_argument("--repository", help="limit to one owner/name")
    parser.add_argument("--lanes", default="R,L")
    parser.add_argument("--bundle-root", type=Path,
                        help="read sealed bundles from this candidates/ parent instead of the state refs")
    parser.add_argument("--no-write", action="store_true", help="do not write the state ref")
    parser.add_argument("--no-discovery", action="store_true")
    parser.add_argument("--no-freshness", action="store_true")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    state_token = os.environ.get("REPOSITORY_PRESENTER_STATE_TOKEN") or token or None
    lanes = [lane for lane in args.lanes.split(",") if lane in (LANE_R, LANE_L)]
    now = datetime.now(UTC)
    entries = [
        entry for entry in load_registry(args.registry).entries
        if entry.active and (args.repository is None or entry.repository == args.repository)
    ]
    cells = observe_cells(
        entries,
        token=token,
        export=None if args.bundle_root else _state_exporter(args.remote, state_token),
        bundle_root=args.bundle_root,
        freshness_observe=None if args.no_freshness else _freshness_observer(),
        lanes=lanes,
        now=now,
    )
    discovery = None
    if not args.no_discovery and args.repository is None:
        try:
            discovery = _discovery(args.registry, token, now)
        except Exception as exc:  # noqa: BLE001 -- discovery never blocks the drift report
            discovery = {"error": redact(f"{type(exc).__name__}: {exc}", [token])}
    document = report_document(
        cells, observed_at=now.isoformat(timespec="seconds"), run_id=args.run_id, discovery=discovery
    )
    text = summary_markdown(document)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(text)
    if not args.no_write:
        write_report(document, remote=args.remote, token=state_token)
        print(f"report written to {MONITOR_REF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
