"""Manual exploration tool: shows what the next scheduled-run target(s) WOULD be, from the
authorized registry and the durable state backend's existing records (2026-11-04, follow-up
directive §10: "Simply adding `schedule:` will not supply [repository/ecosystem/lane] values and
will not create a valid portfolio schedule").

Read-only: reads data/registry.json and the durable state backend's existing records; never
writes a state ref, dispatches nothing, calls no provider. Prefers repositories with no record
yet, then ones whose most recent record is FAILED_INTERNAL, skipping anything already both-lane
pipeline-good -- a simple, bounded, auditable policy, not a scoring framework.

2026-11-04 (P0 follow-up directive, section 2/9): ``present.yml``'s own ``schedule:`` trigger no
longer calls this script directly -- it calls ``scripts/scheduled_execution_gate.py``, which
reuses ``select_eligible`` below but ALSO enforces the sweep-pause, calibration and explicit
per-repository authorization predicates before ever returning a target. This script stays as a
read-only "what would be picked" exploration tool for an owner inspecting the unauthorized
candidate pool; it is not, itself, an authorization boundary and must never be wired back into
the workflow without going through the gate.

Usage:
    python scripts/select_scheduled_cohort.py [--max N] [--remote origin]

Prints GITHUB_OUTPUT-style `key=value` lines. With --max 1 (the default): `repository=<owner/name>`
and `ecosystem=<ecosystem>` for the single selected target. Exits 1 with no output if nothing is
eligible.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.core.portfolio_matrix import (  # noqa: E402
    PIPELINE_GOOD_STATES,
    backend_reader,
    build_matrix,
    stored_bundle_refs,
)
from repo_presenter.core.registry.loader import load_registry  # noqa: E402
from repo_presenter.core.registry.models import RegistryEntry  # noqa: E402


def select_eligible(
    entries: dict[str, RegistryEntry],
    rows: list[Any],
    *,
    authorized_repos: set[str] | None = None,
    max_n: int = 1,
) -> list[Any]:
    """Never-attempted-first, both-lane-pipeline-good excluded, inactive excluded. When
    ``authorized_repos`` is given, only those repositories are even considered -- the gate
    script's own, stricter call; ``None`` (this script's own default) means "every active,
    registered repository," which is why this function alone must never be treated as an
    authorization decision."""
    eligible = [
        row
        for row in rows
        if not (row.record_r in PIPELINE_GOOD_STATES and row.record_l in PIPELINE_GOOD_STATES)
        and entries[row.repository].active
        and (authorized_repos is None or row.repository in authorized_repos)
    ]
    eligible.sort(
        key=lambda row: (0 if row.record_r == "NO_RECORD" else 1)
        + (0 if row.record_l == "NO_RECORD" else 1)
    )
    return eligible[: max(0, max_n)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max", type=int, default=1)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    args = parser.parse_args(argv)

    entries = {e.repository: e for e in load_registry(args.registry).entries}
    with backend_reader(args.remote) as read_state:
        rows = build_matrix(
            list(entries.values()), read_state, REPO_ROOT, stored_bundle_refs(args.remote)
        )

    chosen = select_eligible(entries, rows, max_n=args.max)
    if not chosen:
        print("# nothing eligible this run", file=sys.stderr)
        return 1

    row = chosen[0]
    print(f"repository={row.repository}")
    print(f"ecosystem={entries[row.repository].ecosystem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
