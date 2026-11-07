"""Per-repository benchmark provenance: is a real aspose.org readme-refresh output actually
known to be live upstream for this product today?

R2 (``docs/CONSOLIDATED_GOALS_2026-11-06.md``) assumes, as a blanket, portfolio-wide premise,
that "the aspose.org readme-refresh output already live upstream" is the minimum quality floor
for every registered repository. That premise has never been checked per repository -- nothing
in this codebase records, for any of the 36 registry entries, whether its *own* live upstream
README is actually known (with a citable source) to be such an output, as opposed to a
maintainer's own README that no one has ever refreshed. ``data/benchmarks.json`` is that record;
this module keeps it honest and in sync with ``data/registry.json``.

``benchmark_status`` is one of three values, never guessed:

* ``live_upstream_readme_refresh`` -- a citable source (a file and section in this repository)
  states, specifically for this repository, that its live upstream README is a known aspose.org
  readme-refresh output. Never set without that citation in ``evidence``.
* ``unknown`` -- this repository's benchmark status has genuinely been raised and discussed
  (named in a parity-benchmark pilot set, a parity-gate CLI pilot set, or similar), but no source
  settles it either way.
* ``no_benchmark_claimed`` -- no parity-benchmark work anywhere in this repository's history has
  even named this repository; there is no claim to evaluate yet.

``check_coverage`` is the one consistency rule: every active registry repository has exactly one
``data/benchmarks.json`` entry, and no ``data/benchmarks.json`` entry names a repository the
registry does not carry. A thin ``ops/checks/benchmarks_registry.py`` CLI wrapper around it is a
direct supervisor follow-up (``ops/**`` is globally denied to every taskcard) once this module is
accepted -- this module is the whole of the checker's actual logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BENCHMARK_STATUSES: tuple[str, ...] = (
    "live_upstream_readme_refresh",
    "unknown",
    "no_benchmark_claimed",
)


def load_registry_repositories(registry_path: Path) -> list[str]:
    """Every repository named in ``data/registry.json``, in file order."""
    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    return [str(entry["repository"]) for entry in raw.get("entries", [])]


def load_benchmarks(benchmarks_path: Path) -> dict[str, Any]:
    """The parsed ``data/benchmarks.json`` document."""
    return json.loads(benchmarks_path.read_text(encoding="utf-8"))


def check_coverage(registry_path: Path, benchmarks_path: Path) -> list[str]:
    """Every way ``data/benchmarks.json`` can disagree with ``data/registry.json``: an empty
    list means the two files are consistent. One problem string per missing, extra, duplicate,
    or malformed entry -- never an exception, so a caller (a pytest test today, a thin CLI
    wrapper tomorrow) can report every problem found in one pass rather than only the first."""
    problems: list[str] = []
    try:
        registry_repos = load_registry_repositories(registry_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read registry at {registry_path}: {exc}"]
    try:
        document = load_benchmarks(benchmarks_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read benchmarks document at {benchmarks_path}: {exc}"]

    entries = document.get("entries")
    if not isinstance(entries, list):
        return [f"benchmarks document's 'entries' must be a list, got {type(entries).__name__}"]

    registry_set = set(registry_repos)
    seen: dict[str, int] = {}
    by_repository: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or "repository" not in entry:
            problems.append(f"entries[{index}] is not a well-formed benchmark record")
            continue
        repository = str(entry["repository"])
        seen[repository] = seen.get(repository, 0) + 1
        by_repository[repository] = entry
        if repository not in registry_set:
            problems.append(
                f"benchmark entry for {repository!r} names a repository data/registry.json does not carry"
            )
        status = entry.get("benchmark_status")
        if status not in BENCHMARK_STATUSES:
            problems.append(
                f"{repository}: benchmark_status {status!r} is not one of {BENCHMARK_STATUSES}"
            )
        if status == "live_upstream_readme_refresh" and not str(entry.get("evidence") or "").strip():
            problems.append(
                f"{repository}: benchmark_status is live_upstream_readme_refresh but evidence is empty"
            )

    for repository, count in seen.items():
        if count > 1:
            problems.append(f"{repository}: {count} benchmark entries, expected exactly one")

    for repository in registry_repos:
        if repository not in by_repository:
            problems.append(f"missing benchmark entry for {repository}")

    return problems
