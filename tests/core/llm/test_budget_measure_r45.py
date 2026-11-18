"""R45 (owner, 2026-11-18): ``"enforcement": "measure"`` makes every cap, batch, envelope and stop rule a
measurement -- usage is recorded and reported, never refused. Every document here is built in the test; the
committed ``data/provider_budget.json`` is never read. Without the field the enforcing behaviour is unchanged
(the existing budget tests)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.core.llm.budget import (
    BudgetExceededError,
    budget_summary_lines,
    check_budget,
    effective_document,
    empty_ledger,
    ensure_open_batch,
    local_budget_document,
    record_spend,
    reserve,
    reserve_audit,
    settle,
)

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def _committed(**overrides: Any) -> dict[str, Any]:
    document = {
        "epoch": 2, "enforcement": "measure", "batch_size_repositories": 6, "per_batch_cap_multiplier": 1.5,
        "stop_rule_cost_per_sealed_candidate_multiplier": 2.0,
        "total_calls_cap": 1000, "total_tokens_cap": 1_000_000, "spent": {"calls": 0, "tokens": 0},
        "batches": [{"id": "e2-001", "calls_cap": 60, "tokens_cap": 60_000, "calls_spent": 0,
                     "tokens_spent": 0, "repositories": []}],
    }
    document.update(overrides)
    return document


def _write(tmp_path: Path, document: dict[str, Any]) -> Path:
    path = tmp_path / "budget.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _settled(ledger: dict, rid: str, calls: float, *, sealed: tuple = ("R",)) -> dict:
    return settle(
        _committed(), ledger,
        {"id": rid, "repository": "o/a", "lanes": ["R"], "outcomes": {"R": "success" if sealed else "failure"},
         "sealed": list(sealed), "calls": calls, "tokens": 100.0, "budget_refused": False}, NOW,
    )


def _unproductive_ledger(committed: dict[str, Any]) -> dict[str, Any]:
    """24 settled runs: the previous 12 seal every other run, the last 12 seal once (> 2x cost per seal)."""
    ledger = empty_ledger()
    for index in range(24):
        ledger, entry, refusal = reserve(committed, ledger, reservation_id=f"r{index}", repository="o/a",
                                         lanes=["R"], now=NOW)
        assert entry is not None and refusal is None, index
        sealed = ("R",) if (index % 2 if index < 12 else index == 12) else ()
        ledger = _settled(ledger, f"r{index}", 10, sealed=sealed)
    return ledger


def test_no_cap_refuses_a_product_call_and_spend_is_still_recorded(tmp_path: Path) -> None:
    over = _committed(
        spent={"calls": 5000, "tokens": 9_000_000},
        batches=[{"id": "e2-001", "calls_cap": 60, "tokens_cap": 60_000, "calls_spent": 80,
                  "tokens_spent": 90_000, "repositories": []}],
    )
    path = _write(tmp_path, over)
    check_budget(path, estimated_tokens=10_000_000)
    record_spend(path, 3, 300)
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["spent"] == {"calls": 5003, "tokens": 9_000_300}
    assert document["batches"][-1]["calls_spent"] == 83 and document["batches"][-1]["tokens_spent"] == 90_300


def test_no_open_batch_never_refuses(tmp_path: Path) -> None:
    check_budget(_write(tmp_path, _committed(batches=[])), estimated_tokens=5)


def test_a_missing_or_unparseable_file_still_raises(tmp_path: Path) -> None:
    with pytest.raises(BudgetExceededError):
        check_budget(tmp_path / "absent.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(BudgetExceededError):
        check_budget(bad)


def test_a_hosted_runner_still_needs_its_ledger_reservation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(BudgetExceededError):
        check_budget(_write(tmp_path, _committed()))


def test_other_values_of_the_field_keep_enforcing(tmp_path: Path) -> None:
    path = _write(tmp_path, _committed(enforcement="enforce", spent={"calls": 1000, "tokens": 0}))
    with pytest.raises(BudgetExceededError):
        check_budget(path)


def test_a_fired_rolling_window_notices_once_and_opens_the_next_batch() -> None:
    committed = _committed(batches=[{"id": "e2-001", "calls_cap": 2400, "tokens_cap": 2_400_000,
                                     "calls_spent": 2400, "tokens_spent": 0, "repositories": []}])
    ledger = _unproductive_ledger(committed)
    for entry in ledger["entries"]:  # the last batch is spent down, so the next must be opened
        if entry["kind"] == "open_batch":
            entry["calls_cap"] = 1.0
    ledger, refusal = ensure_open_batch(committed, ledger, NOW)
    assert refusal is None
    kinds = [e["kind"] for e in ledger["entries"]]
    assert "stop" not in kinds and kinds.count("stop_notice") == 1 and kinds[-1] == "open_batch"
    notice = next(e for e in ledger["entries"] if e["kind"] == "stop_notice")
    assert "last 12 settled hosted runs" in notice["reason"] and "previous 12" in notice["reason"]
    # idempotent: a second call neither refuses nor writes a second notice for the same batch
    ledger, refusal = ensure_open_batch(committed, ledger, NOW)
    assert refusal is None and [e["kind"] for e in ledger["entries"]].count("stop_notice") == 1
    document = effective_document(committed, ledger, NOW)
    assert "stop" not in document
    lines = budget_summary_lines(document)
    assert lines[0] == "enforcement: measure"
    assert any(line.startswith("NOTICE: ") and "last 12 settled hosted runs" in line for line in lines)
    assert not any(line.startswith("STOPPED:") for line in lines)


def test_a_committed_stop_entry_is_ignored(tmp_path: Path) -> None:
    committed = _committed()
    ledger, entry, _ = reserve(committed, empty_ledger(), reservation_id="a", repository="o/a",
                               lanes=["R"], now=NOW)
    ledger["entries"].append({"kind": "stop", "epoch": 2, "batch": "e2-001", "reason": "old", "at": "x"})
    document = effective_document(committed, ledger, NOW)
    assert "stop" not in document
    assert not any(line.startswith("STOPPED:") for line in budget_summary_lines(document))
    ledger, refusal = ensure_open_batch(committed, ledger, NOW)
    assert refusal is None
    _, entry, refusal = reserve(committed, ledger, reservation_id="b", repository="o/a", lanes=["R"], now=NOW)
    assert entry is not None and refusal is None


def test_an_overrun_envelope_opens_a_batch_from_the_measured_median_and_notices() -> None:
    committed = _committed(total_calls_cap=100, spent={"calls": 90, "tokens": 0},
                           batches=[{"id": "e2-001", "calls_cap": 60, "tokens_cap": 60_000,
                                     "calls_spent": 0, "tokens_spent": 0, "repositories": []}])
    ledger = empty_ledger()
    ledger, entry, _ = reserve(committed, ledger, reservation_id="a", repository="o/a", lanes=["R"], now=NOW)
    ledger = _settled(ledger, "a", 50)
    for index in range(1, 3):  # drive the batch beyond its cap (a hosted run spent past its allowance)
        ledger, entry, refusal = reserve(committed, ledger, reservation_id=f"x{index}", repository="o/a",
                                         lanes=["R"], now=NOW)
        assert entry is not None and refusal is None
        ledger = _settled(ledger, f"x{index}", 40)
    ledger, refusal = ensure_open_batch(committed, ledger, NOW)
    assert refusal is None
    opened = [e for e in ledger["entries"] if e["kind"] == "open_batch"]
    assert opened and "measured median" in opened[-1]["basis"]
    assert opened[-1]["calls_cap"] > 10  # sized from the median, not reduced by the envelope's remainder
    notices = [e for e in ledger["entries"] if e["kind"] == "stop_notice"]
    assert notices and {n["cause"] for n in notices} == {"envelope"}
    assert len({n["batch"] for n in notices}) == len(notices)  # once per batch
    lines = budget_summary_lines(effective_document(committed, ledger, NOW))
    assert any(line.startswith("NOTICE: programme envelope overrun") for line in lines)
    _, entry, refusal = reserve(committed, ledger, reservation_id="z", repository="o/a", lanes=["R"], now=NOW)
    assert entry is not None and refusal is None and entry["calls"] >= 1


def test_reserve_always_grants_even_when_the_batch_is_spent() -> None:
    committed = _committed(
        total_calls_cap=10, spent={"calls": 500, "tokens": 0},
        batches=[{"id": "e2-001", "calls_cap": 0, "tokens_cap": 0, "calls_spent": 5, "tokens_spent": 5,
                  "repositories": []}],
    )
    ledger, entry, refusal = reserve(committed, empty_ledger(), reservation_id="a", repository="o/a",
                                     lanes=["R", "L"], now=NOW)
    assert refusal is None and entry is not None and entry["calls"] >= 2 and entry["tokens"] >= 2


def test_an_in_flight_run_never_holds_the_next_batch() -> None:
    committed = _committed(batches=[{"id": "e2-001", "calls_cap": 6, "tokens_cap": 6000, "calls_spent": 0,
                                     "tokens_spent": 0, "repositories": []}])
    ledger = empty_ledger()
    for index in range(3):  # unsettled reservations spend the batch down
        ledger, entry, refusal = reserve(committed, ledger, reservation_id=f"u{index}", repository="o/a",
                                         lanes=["R"], now=NOW)
        assert entry is not None and refusal is None, index


def test_the_audit_is_granted_past_the_batch(tmp_path: Path) -> None:
    committed = _committed(batches=[{"id": "e2-001", "calls_cap": 1, "tokens_cap": 1, "calls_spent": 0,
                                     "tokens_spent": 0, "repositories": []}])
    _, entry, refusal = reserve_audit(committed, empty_ledger(), reservation_id="m9", cases=20, now=NOW)
    assert refusal is None and entry is not None


def test_the_local_document_keeps_enforcement_and_check_budget_passes_past_the_allowance(tmp_path: Path) -> None:
    committed = _committed()
    ledger, entry, _ = reserve(committed, empty_ledger(), reservation_id="x", repository="o/a",
                               lanes=["R"], now=NOW)
    document = local_budget_document(committed, ledger, entry, NOW)
    assert document["enforcement"] == "measure"
    path = _write(tmp_path, document)
    for _ in range(int(entry["calls"]) + 5):
        check_budget(path)
        record_spend(path, 1, 10)
    assert json.loads(path.read_text(encoding="utf-8"))["batches"][0]["calls_spent"] == entry["calls"] + 5
