"""Select the next scheduled-run target(s) from the authorized registry, for present.yml's
`schedule:` trigger (2026-11-04, follow-up directive §10: "Simply adding `schedule:` will not
supply [repository/ecosystem/lane] values and will not create a valid portfolio schedule").

Read-only: reads data/registry.json and the durable state backend's existing records; never
writes a state ref, dispatches nothing, calls no provider. Prefers repositories with no record
yet, then ones whose most recent record is FAILED_INTERNAL, skipping anything already both-lane
pipeline-good -- a simple, bounded, auditable policy, not a scoring framework.

Usage:
    python scripts/select_scheduled_cohort.py [--max N] [--remote origin]

Prints GITHUB_OUTPUT-style `key=value` lines. With --max 1 (the default and the only mode
present.yml actually uses today): `repository=<owner/name>` and `ecosystem=<ecosystem>` for the
single selected target. Exits 1 with no output if nothing is eligible (the caller must treat
that as "skip this scheduled run," never as a crash).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.core.portfolio_matrix import (  # noqa: E402
    PIPELINE_GOOD_STATES,
    backend_reader,
    build_matrix,
    stored_bundle_refs,
)
from repo_presenter.core.registry.loader import load_registry  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max", type=int, default=1)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    args = parser.parse_args(argv)

    entries = {e.repository: e for e in load_registry(args.registry).entries}
    with backend_reader(args.remote) as read_state:
        rows = build_matrix(list(entries.values()), read_state, REPO_ROOT, stored_bundle_refs(args.remote))

    def need_score(row) -> tuple[int, int]:
        # Lower sorts first: never-attempted beats failed; a repo already both-lane
        # pipeline-good is excluded entirely before this ever runs (see the filter below).
        r_new = 0 if row.record_r == "NO_RECORD" else 1
        l_new = 0 if row.record_l == "NO_RECORD" else 1
        return (r_new + l_new, row.repository)  # type: ignore[return-value]

    eligible = [
        row for row in rows
        if not (row.record_r in PIPELINE_GOOD_STATES and row.record_l in PIPELINE_GOOD_STATES)
        and entries[row.repository].active
    ]
    eligible.sort(key=lambda row: (0 if row.record_r == "NO_RECORD" else 1)
                                  + (0 if row.record_l == "NO_RECORD" else 1))

    chosen = eligible[: max(0, args.max)]
    if not chosen:
        print("# nothing eligible this run", file=sys.stderr)
        return 1

    # present.yml only wires a single repository/ecosystem pair per run today (one `facts` +
    # `present` job pair, not a matrix) -- --max > 1 is accepted for future use but only the
    # first selection is ever actually emitted as GITHUB_OUTPUT, by design, not by oversight.
    row = chosen[0]
    print(f"repository={row.repository}")
    print(f"ecosystem={entries[row.repository].ecosystem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
