"""Print the portfolio matrix derived from the registry, the state remote's records and candidates/.

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

from repo_presenter.core.portfolio_matrix import backend_reader, build_matrix, render, summarize
from repo_presenter.core.registry.loader import load_registry

REPO_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    entries = load_registry(args.registry).entries
    with backend_reader(args.remote) as read_state:
        rows = build_matrix(entries, read_state, REPO_ROOT)
    summary = summarize(rows)
    if args.json:
        print(json.dumps({"rows": [asdict(row) for row in rows], "summary": summary}, indent=2))
    else:
        print(render(rows, summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
