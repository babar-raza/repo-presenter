"""R43(1) / BL-101: the stop rule judges a rolling window of the last 12 settled hosted runs against the 12
before them; BL-100: a cell's reservation is the measured p90 of settled lane-cells, bounded by what the batch
has left. Against fixture ledgers and the real settle entries of 2026-11-14 (provider-spend ledger ref), never
the network or the committed budget file."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo_presenter.core.llm.budget import (
    STOP_RULE_WINDOW_RUNS,
    budget_summary_lines,
    effective_document,
    empty_ledger,
    ensure_open_batch,
    ledger_entries,
    measured_cell_cost,
    per_cell_allowance,
    reserve,
    rolling_stop_reason,
    settle,
    settled_runs,
)

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
REAL = Path(__file__).resolve().parents[2] / "fixtures" / "budget" / "ledger_settles_2026-11-14.json"


def _committed(**overrides: Any) -> dict[str, Any]:
    document = {
        "epoch": 2, "batch_size_repositories": 6, "per_batch_cap_multiplier": 1.5,
        "stop_rule_cost_per_sealed_candidate_multiplier": 2.0,
        "total_calls_cap": 9000, "total_tokens_cap": 100_000_000, "spent": {"calls": 0, "tokens": 0},
        "batches": [{"id": "e2-001", "calls_cap": 600, "tokens_cap": 600_000, "calls_spent": 0,
                     "tokens_spent": 0, "repositories": []}],
    }
    document.update(overrides)
    return document


def _run(index: int, calls: float, sealed: bool, *, tokens: float = 1000, lanes=("R",)) -> dict[str, Any]:
    return {"kind": "settle", "epoch": 2, "id": f"r{index:03d}", "batch": "e2-001", "repository": "o/a",
            "at": f"2026-11-14T{index // 60:02d}:{index % 60:02d}:00Z", "calls": calls, "tokens": tokens,
            "outcomes": {lane: "success" if sealed else "failure" for lane in lanes},
            "sealed": list(lanes[:1]) if sealed else [], "lanes": list(lanes)}


def _ledger(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema_version": 1, "entries": runs}


def test_a_single_zero_seal_batch_of_six_never_stops_the_loop() -> None:
    # 18 runs at 100 calls with a seal every third run, then a batch of six at the same spend that sealed
    # nothing: it halves the window's seals, so the cost per seal at most doubles -- never "exceeds 2x".
    runs = [_run(i, 100, i % 3 == 0) for i in range(18)] + [_run(18 + i, 100, False) for i in range(6)]
    assert rolling_stop_reason(runs, 2.0) is None
    # the per-batch rule this replaces stopped on exactly this: the last batch sealed nothing
    assert all(not r["sealed"] for r in runs[-6:])


def test_the_rule_needs_two_full_windows() -> None:
    runs = [_run(i, 100, False) for i in range(2 * STOP_RULE_WINDOW_RUNS - 1)]
    assert rolling_stop_reason(runs, 2.0) is None


def test_an_older_window_with_no_seal_is_no_baseline() -> None:
    runs = [_run(i, 100, False) for i in range(24)]
    assert rolling_stop_reason(runs, 2.0) is None


def test_it_fires_only_above_the_owner_multiplier() -> None:
    # previous 12: 1200 calls / 4 seals = 300; last 12: 1200 calls / 2 seals = 600 (exactly 2x: no stop)
    runs = [_run(i, 100, i % 3 == 0) for i in range(12)] + [_run(12 + i, 100, i % 6 == 0) for i in range(12)]
    assert rolling_stop_reason(runs, 2.0) is None
    # one seal fewer in the last window: 1200 / 1 = 1200 > 2 x 300
    runs = runs[:12] + [_run(12 + i, 100, i == 0) for i in range(12)]
    assert "exceeds 2x" in rolling_stop_reason(runs, 2.0)
    # the multiplier is the committed file's own key, read as the owner set it
    assert rolling_stop_reason(runs, 4.0) is None
    assert ensure_open_batch(_committed(stop_rule_cost_per_sealed_candidate_multiplier=4.0,
                                        batches=[{"id": "e2-001", "calls_cap": 2400, "tokens_cap": 24_000,
                                                  "calls_spent": 0, "tokens_spent": 0}]),
                             _ledger(runs), NOW)[1] is None


def test_a_released_dispatch_and_skipped_lanes_are_not_runs() -> None:
    released = {"kind": "settle", "epoch": 2, "id": "x", "outcomes": {}, "calls": 0, "tokens": 0, "sealed": []}
    skipped = {**_run(1, 10, False), "outcomes": {"R": "skipped", "L": "skipped"}}
    assert settled_runs([released, skipped, _run(2, 10, True)]) == [_run(2, 10, True)]


def test_the_real_ledger_of_2026_11_14_under_the_rolling_rule() -> None:
    """The 53 settled runs up to 08:58Z: the rolling window (R43(1)) does fire on them -- the last 12 runs
    sealed once (408 calls per seal) against 106.3 for the 12 before -- while the first 44 runs, which
    include zero-seal batches, never stop it. Recorded here so the owner rule's effect on real data is
    explicit, not assumed."""
    entries = ledger_entries(json.loads(REAL.read_text(encoding="utf-8")), 2)
    runs = settled_runs(entries)
    assert len(runs) == 53
    fired_at = [len(runs[:i]) for i in range(24, len(runs) + 1) if rolling_stop_reason(runs[:i], 2.0)]
    assert fired_at[0] == 45 and fired_at == list(range(45, 54))
    assert "408.0 calls" in rolling_stop_reason(runs, 2.0)


def test_the_reservation_is_the_measured_p90_of_settled_lane_cells() -> None:
    entries = ledger_entries(json.loads(REAL.read_text(encoding="utf-8")), 2)
    measured = measured_cell_cost(entries)
    assert measured == {"calls": 55.0, "tokens": 2730385.0, "runs": 24, "percentile": 0.9}
    committed = _committed(batches=[{"id": "e2-010", "calls_cap": 270, "tokens_cap": 11_200_000,
                                     "calls_spent": 0, "tokens_spent": 0}])
    ledger = _ledger(list(entries))
    document = effective_document(committed, ledger, NOW)
    assert per_cell_allowance(document, document["batches"][-1]) == (55.0, 2730385.0)
    granted = []
    for index in range(6):
        ledger, entry, _refusal = reserve(committed, ledger, reservation_id=f"c{index}", repository="o/a",
                                         lanes=["R"], now=NOW)
        granted.append(entry)
    funded = [e for e in granted if e]
    # 270 calls fund four whole p90 cells and the remainder is bounded by what the batch has left
    assert [e["calls"] for e in funded[:4]] == [55.0] * 4
    assert sum(e["calls"] for e in funded) <= 270 and sum(e["tokens"] for e in funded) <= 11_200_000
    assert any("per-cell reservation: p90 of 24" in line for line in budget_summary_lines(document))


def test_a_two_lane_run_is_split_over_the_lanes_it_ran() -> None:
    runs = [_run(i, 100, False, lanes=("R", "L"), tokens=2000) for i in range(5)]
    assert measured_cell_cost(runs) == {"calls": 50.0, "tokens": 1000.0, "runs": 5, "percentile": 0.9}


def test_too_few_measured_runs_fall_back_to_the_batch_caps_over_six() -> None:
    committed = _committed()
    ledger = _ledger([_run(i, 30, True) for i in range(4)])
    document = effective_document(committed, ledger, NOW)
    assert "measured_cell" not in document
    assert per_cell_allowance(document, document["batches"][-1]) == (100.0, 100_000.0)


def test_status_lines_show_both_windows_and_no_infinity_in_json() -> None:
    runs = [_run(i, 100, i < 12 and i % 2 == 0) for i in range(24)]
    document = effective_document(_committed(), _ledger(runs), NOW)
    assert document["rolling"] == {"window": 12, "runs": 24, "current": "no seal", "previous": 200.0}
    json.dumps(document, allow_nan=False)
    assert any("previous 12 200.0 calls/seal" in line for line in budget_summary_lines(document))
    assert not math.isinf(per_cell_allowance(document, document["batches"][-1])[0])


def test_settle_then_status_end_to_end() -> None:
    committed = _committed()
    ledger, _entry, _ = reserve(committed, empty_ledger(), reservation_id="x", repository="o/a", lanes=["R"], now=NOW)
    ledger = settle(committed, ledger, {"id": "x", "repository": "o/a", "outcomes": {"R": "failure"},
                                        "sealed": [], "calls": 40, "tokens": 400}, NOW)
    assert effective_document(committed, ledger, NOW)["rolling"]["runs"] == 1
