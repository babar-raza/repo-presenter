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
counts are printed for visibility and never added in. Amended the same day (owner rule: a version
bump never invalidates a seal, ``repo_presenter.recertify``): the live number per lane is the
count of repositories whose LATEST seal re-certifies under current code (zero provider calls);
the version sets are provenance.

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
    from repo_presenter.recertify import portfolio_recertification
    from repo_presenter.core.version_set import current_fingerprints

    registry_path = REPO_ROOT / "data" / "registry.json"
    entries = load_registry(registry_path).entries
    current = current_fingerprints(REPO_ROOT / "prompts")
    results, seals = portfolio_recertification(
        remote="origin", registry=registry_path, prompts_dir=REPO_ROOT / "prompts"
    )
    certifications = {(r.repository, r.lane): r for r in results}
    with backend_reader("origin") as read_state:
        rows = build_matrix(
            entries, read_state, REPO_ROOT, stored_bundle_refs("origin"), seals, certifications
        )
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
