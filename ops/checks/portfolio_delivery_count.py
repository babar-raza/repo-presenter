#!/usr/bin/env python
"""Release-gate-card check: derive the P1 live-delivery count from real, cross-validated
evidence -- never accept a manually typed "LIVE_DELIVERY_CONFIRMED_COUNT: N" marker (the real
defect in TC-011's first version, confirmed 2026-11-04: an agent could simply type any number).

A repository counts toward P1 only if ALL of the following are true, each independently
checked, not inferred from a single summary field:
  1. Both lanes' durable state records are in {ACCEPTED, READY_FOR_PROPOSAL} (pipeline-good).
  2. The reviewer calibration record currently reports status == "PASSED" (checked globally --
     if calibration has never passed, nothing anywhere counts, full stop).
  3. A real, dated live-delivery ledger entry exists for that repository in
     evidence/delivery_ledger.json, recording an upstream-verified outcome -- this file and its
     schema do not exist yet, so today's correct, honest answer is zero. Writing the ledger
     format is real future work, not a shortcut taken here.

Usage: python ops/checks/portfolio_delivery_count.py <minimum>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

CALIBRATION = REPO_ROOT / "data" / "reviewer_calibration.json"
LEDGER = REPO_ROOT / "evidence" / "delivery_ledger.json"


def main(argv: list[str]) -> int:
    minimum = int(argv[0]) if argv else 25

    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8")) if CALIBRATION.exists() else {}
    if calibration.get("status") != "PASSED":
        print(f"FAIL: reviewer calibration status is {calibration.get('status')!r}, not PASSED -- "
              f"nothing can count toward P1 while this holds")
        return 1

    from repo_presenter.core.portfolio_matrix import (
        backend_reader,
        build_matrix,
        stored_bundle_refs,
    )
    from repo_presenter.core.registry.loader import load_registry

    entries = load_registry(REPO_ROOT / "data" / "registry.json").entries
    with backend_reader("origin") as read_state:
        rows = build_matrix(entries, read_state, REPO_ROOT, stored_bundle_refs("origin"))
    pipeline_good = {
        row.repository for row in rows
        if row.record_r in ("ACCEPTED", "READY_FOR_PROPOSAL") and row.record_l in ("ACCEPTED", "READY_FOR_PROPOSAL")
    }

    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
    live_verified = {
        entry["repo"] for entry in ledger
        if entry.get("live_verified") is True and entry.get("repo") in pipeline_good
    }

    count = len(live_verified)
    if count < minimum:
        print(f"FAIL: real cross-validated live-delivery count is {count}, need >= {minimum} "
              f"(pipeline-good-both-lanes: {len(pipeline_good)}, calibration PASSED: yes, "
              f"ledger entries recognized: {count})")
        return 1
    print(f"OK: {count} repositories cross-validated as both-lane pipeline-good, calibrated, "
          f"and live-verified (>= {minimum})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
