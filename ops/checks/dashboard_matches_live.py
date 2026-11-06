#!/usr/bin/env python
"""Release-gate-card check: assert project/state.yaml's progress.lane_r_accepted /
progress.lane_l_accepted match a FRESH run of scripts/portfolio_status.py, rather than hard-coded
expected numbers (the real defect in this card's first version, confirmed 2026-11-04: hard-coded
10/12 would wrongly FAIL on a legitimate future increase to 11/13, and would wrongly PASS forever
if both numbers simply never changed, which is exactly the "stale dashboard" failure mode this
card exists to prevent).

2026-11-06 (owner version-set rules, ``core/version_set.py``): the live numbers are the CURRENT
version set's counted seals per lane, read from the seal history -- never the transaction
records' latest state, which a failed re-run under a new version set demotes. Older version sets'
counts are printed for visibility and never added in.

This needs network access to read the durable state remote's refs -- the card declaring this
check must set `network: true`.

Usage: python ops/checks/dashboard_matches_live.py [--no-loss]
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
    from repo_presenter.core.state.bundle_store import seal_history
    from repo_presenter.core.version_set import current_fingerprints

    registry_path = REPO_ROOT / "data" / "registry.json"
    entries = load_registry(registry_path).entries
    current = current_fingerprints(REPO_ROOT / "prompts")
    seals = seal_history(remote="origin")
    with backend_reader("origin") as read_state:
        rows = build_matrix(entries, read_state, REPO_ROOT, stored_bundle_refs("origin"), seals)
    live = summarize(rows, current)
    live_r, live_l = live["lane_r_pipeline_good"], live["lane_l_pipeline_good"]
    for lane in ("r", "l"):
        sets = live[f"lane_{lane}_version_sets"]
        print(
            f"lane {lane.upper()}: current version set {sets['current_version_set']} "
            f"count={sets['current_count']}; older sets (never summed): {sets['older_version_sets']}"
        )

    state = load_yaml(REPO_ROOT / "project" / "state.yaml")
    progress = state.get("progress", {})
    recorded_r = progress.get("lane_r_accepted")
    recorded_l = progress.get("lane_l_accepted")

    problems = []
    # --no-loss (owner ruling R10; the CI mode): fail only when the live count is BELOW the recorded one
    # (a seal lost, or the record overclaims); live above recorded is progress the dashboard has not been
    # resynced to yet -- reported, not a failure, so real seals landing never break CI. The strict
    # equality (no flag) stays TC-005's own point-in-time check.
    no_loss = "--no-loss" in argv
    for lane, recorded, live in (("r", recorded_r, live_r), ("l", recorded_l, live_l)):
        if recorded == live:
            continue
        message = f"lane_{lane}_accepted recorded={recorded!r} but live={live!r}"
        if no_loss and isinstance(recorded, int) and isinstance(live, int) and live > recorded:
            print(f"WARN (unrecorded progress, resync the dashboard): {message}")
            continue
        problems.append(message)
    if problems:
        print("FAIL: " + "; ".join(problems))
        return 1
    print(
        f"OK: no seal lost (recorded R={recorded_r}, L={recorded_l}; live R={live_r}, L={live_l})"
        if no_loss
        else f"OK: project/state.yaml matches live portfolio_status.py (R={live_r}, L={live_l})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
