#!/usr/bin/env python
"""Release-gate-card check: assert project/state.yaml's progress.lane_r_accepted /
progress.lane_l_accepted match a FRESH run of scripts/portfolio_status.py, rather than hard-coded
expected numbers (the real defect in this card's first version, confirmed 2026-11-04: hard-coded
10/12 would wrongly FAIL on a legitimate future increase to 11/13, and would wrongly PASS forever
if both numbers simply never changed, which is exactly the "stale dashboard" failure mode this
card exists to prevent).

This needs network access to read the durable state remote's refs -- the card declaring this
check must set `network: true`.

Usage: python ops/checks/dashboard_matches_live.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "ops"))


def main(argv: list[str]) -> int:
    from gatectl import load_yaml

    from repo_presenter.core.portfolio_matrix import backend_reader, build_matrix, stored_bundle_refs, summarize
    from repo_presenter.core.registry.loader import load_registry

    registry_path = REPO_ROOT / "data" / "registry.json"
    entries = load_registry(registry_path).entries
    with backend_reader("origin") as read_state:
        rows = build_matrix(entries, read_state, REPO_ROOT, stored_bundle_refs("origin"))
    live = summarize(rows)
    live_r, live_l = live["lane_r_pipeline_good"], live["lane_l_pipeline_good"]

    state = load_yaml(REPO_ROOT / "project" / "state.yaml")
    progress = state.get("progress", {})
    recorded_r = progress.get("lane_r_accepted")
    recorded_l = progress.get("lane_l_accepted")

    problems = []
    if recorded_r != live_r:
        problems.append(f"lane_r_accepted recorded={recorded_r!r} but live={live_r!r}")
    if recorded_l != live_l:
        problems.append(f"lane_l_accepted recorded={recorded_l!r} but live={live_l!r}")
    if problems:
        print("FAIL: " + "; ".join(problems))
        return 1
    print(f"OK: project/state.yaml matches live portfolio_status.py (R={live_r}, L={live_l})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
