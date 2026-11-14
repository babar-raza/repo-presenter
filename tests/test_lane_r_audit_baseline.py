"""The 2026-11-13 Lane R audit (BL-085) is on record and measurable: its baseline is reproducible from its frozen
inputs, so a later measurement compares against exactly what the audit found (owner, 2026-11-14)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

AUDIT = Path(__file__).resolve().parent.parent / "docs" / "investigations" / "2026-11-13-lane-r-not-progressing"


def _measure():
    spec = importlib.util.spec_from_file_location("lane_r_audit_measure", AUDIT / "measure.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_baseline_is_reproducible_from_the_frozen_inputs() -> None:
    baseline = json.loads((AUDIT / "baseline.json").read_text(encoding="utf-8"))
    measure = _measure()
    now = measure.summarise(AUDIT / "hosted_lane_r.jsonl", AUDIT / "recertify_lane_r.json")
    assert {k: v for k, v in baseline.items() if k not in ("as_of", "source")} == now


def test_the_baseline_records_the_audit_headline() -> None:
    baseline = json.loads((AUDIT / "baseline.json").read_text(encoding="utf-8"))
    assert len(baseline["lane_r_certified_cells"]) == 2
    assert baseline["hosted_lane_r_runs"] == 26 and len(baseline["hosted_cells_attempted"]) == 13
    assert baseline["hosted_findings_by_class"]["KIND_WORD_MISREAD_LIST"] == 94


def test_a_later_state_is_compared_class_by_class() -> None:
    measure = _measure()
    base = {"lane_r_certified_cells": ["o/a"], "lane_r_needs_repair_cells": 3, "hosted_lane_r_runs": 2,
            "hosted_cells_attempted": ["o/a"], "repair_attempts": {"repaired": 1, "not_repaired": 1},
            "hosted_findings_by_class": {"A": 5, "B": 1}, "seal_findings_by_class": {}}
    now = dict(base, lane_r_certified_cells=["o/a", "o/b"], hosted_findings_by_class={"A": 2, "C": 1})
    lines = "\n".join(measure.compare(base, now))
    assert "Lane R certified cells: 1 -> 2" in lines
    assert "B" in lines and "GONE" in lines and "NEW" in lines
