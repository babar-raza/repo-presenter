"""Print the portfolio matrix derived from the registry, the state remote's seal history and
records, and candidates/.

Counts come from the SEAL HISTORY (every commit on every bundle ref), grouped by version-set
fingerprint (``core/version_set.py``): ``lane_*_pipeline_good`` is the CURRENT version set's count,
and every older set's count is listed separately, never summed in. The transaction records are
shown as the latest attempt per lane only.

Read-only: it fetches state refs, never writes one, dispatches nothing and calls no provider.
Usage:
    python scripts/portfolio_status.py [--remote origin] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.portfolio_matrix import (
    backend_reader,
    build_matrix,
    render,
    stored_bundle_refs,
    summarize,
)
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.core.state.bundle_store import seal_history
from repo_presenter.core.version_set import current_fingerprints

REPO_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    parser.add_argument("--prompts", type=Path, default=REPO_ROOT / "prompts")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    entries = load_registry(args.registry).entries
    current = current_fingerprints(args.prompts)
    seals = seal_history(remote=args.remote)
    with backend_reader(args.remote) as read_state:
        rows = build_matrix(
            entries, read_state, REPO_ROOT, stored_bundle_refs(args.remote), seals
        )
    summary = summarize(rows, current)
    if args.json:
        print(
            json.dumps(
                {"current_version_sets": current, "rows": [asdict(row) for row in rows],
                 "summary": summary},
                indent=2,
            )
        )
    else:
        print(render(rows, summary, current))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
