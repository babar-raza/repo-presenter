"""The durable hosted provider-spend ledger (owner ruling R37, 2026-11-13; core/llm/budget.py):
caps from the committed file, spend from the ledger on the state remote; reservations, R25 batch
opening, the stop rule, measured settlement and the CLI a hosted job runs -- against fixture
documents and a disposable local state remote, never the real committed budget or the network."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from support import init_git_repository

from repo_presenter.core.llm import budget
from repo_presenter.core.llm.budget import (
    LEDGER_REF,
    BudgetExceededError,
    check_budget,
    effective_document,
    empty_ledger,
    ensure_open_batch,
    local_budget_document,
    measure_new_calls,
    record_spend,
    reserve,
    reserve_cohort,
    settle,
)
from repo_presenter.core.state.git_backend import GitJsonRef

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)


def _committed(**overrides: Any) -> dict[str, Any]:
    document = {
        "epoch": 2,
        "batch_size_repositories": 6,
        "per_batch_cap_multiplier": 1.5,
        "stop_rule_cost_per_sealed_candidate_multiplier": 2.0,
        "total_calls_cap": 9000,
        "total_tokens_cap": 100_000_000,
        "spent": {"calls": 600, "tokens": 1000},
        "batches": [
            {"id": "e2-001", "calls_cap": 600, "tokens_cap": 600_000, "calls_spent": 0,
             "tokens_spent": 0, "repositories": []}
        ],
    }
    document.update(overrides)
    return document


def _settled(ledger: dict, rid: str, calls: float, *, sealed=("R",), tokens: float = 100) -> dict:
    return settle(_committed(), ledger, {"id": rid, "repository": "o/a", "outcomes": {"R": "success"},
                                         "sealed": list(sealed), "calls": calls, "tokens": tokens}, NOW)


def test_a_reservation_is_one_cell_share_per_lane_and_is_charged_until_settled() -> None:
    committed = _committed()
    ledger, entry, refusal = reserve(committed, empty_ledger(), reservation_id="x", repository="o/a",
                                     lanes=["R", "L"], now=NOW)
    assert refusal is None and entry["calls"] == 200 and entry["batch"] == "e2-001"
    document = effective_document(committed, ledger, NOW)
    assert document["batches"][-1]["calls_spent"] == 200
    assert document["spent"]["calls"] == 800
    settled = _settled(ledger, "x", 37)
    document = effective_document(committed, settled, NOW)
    assert document["batches"][-1]["calls_spent"] == 37
    assert document["batches"][-1]["hosted"] == {"calls": 37, "tokens": 100, "runs": 1,
                                                 "sealed": 1, "in_flight": 0}


def test_reserving_the_same_id_twice_is_idempotent() -> None:
    committed = _committed()
    ledger, first, _ = reserve(committed, empty_ledger(), reservation_id="x", repository="o/a",
                               lanes=["R"], now=NOW)
    again, second, _ = reserve(committed, ledger, reservation_id="x", repository="o/a", lanes=["R"], now=NOW)
    assert second == first and len(again["entries"]) == 1


def test_concurrent_reservations_never_exceed_the_batch() -> None:
    committed = _committed()
    _, planned = reserve_cohort(
        committed, empty_ledger(), [{"repository": f"o/{i}", "lanes": ["R"]} for i in range(8)],
        id_prefix="c", now=NOW,
    )
    funded = [run for run in planned if run["reservation"]]
    assert sum(run["reservation"]["calls"] for run in funded) <= 600
    # Six cells drain the batch; the seventh is refused, not over-granted (runs still in flight).
    assert len(funded) == 6 and "waiting for 6 in-flight" in planned[6]["refusal"]


def test_an_exhausted_batch_opens_the_next_at_r25s_measured_median() -> None:
    committed = _committed()
    ledger = empty_ledger()
    # 520 of 600 spent: the last 80 cannot fund another 100-call cell, so the next batch opens.
    for index, calls in enumerate([100, 100, 120, 100, 100]):
        ledger, _, _ = reserve(committed, ledger, reservation_id=f"r{index}", repository="o/a",
                               lanes=["R"], now=NOW)
        ledger = _settled(ledger, f"r{index}", calls, tokens=1000)
    ledger, refusal = ensure_open_batch(committed, ledger, NOW)
    assert refusal is None
    opened = ledger["entries"][-1]
    assert opened["kind"] == "open_batch" and opened["after"] == "e2-001"
    assert opened["calls_cap"] == 900  # 1.5 x median 100 x 6
    assert opened["tokens_cap"] == 9000
    assert effective_document(committed, ledger, NOW)["batches"][-1]["id"] == opened["id"]


def test_a_committed_batch_takes_precedence_over_hosted_ones() -> None:
    committed = _committed()
    ledger = {"entries": [{"kind": "open_batch", "epoch": 2, "id": "e2-002-hosted", "after": "e2-001",
                           "calls_cap": 10, "tokens_cap": 10}]}
    newer = _committed(batches=committed["batches"] + [
        {"id": "e2-002-owner", "calls_cap": 50, "tokens_cap": 50, "calls_spent": 0, "tokens_spent": 0}])
    assert effective_document(newer, ledger, NOW)["batches"][-1]["id"] == "e2-002-owner"


def test_the_stop_rule_fires_when_cost_per_sealed_candidate_more_than_doubles() -> None:
    committed = _committed()
    ledger = empty_ledger()
    # batch 1: 600 calls, 6 seals -> 100/seal
    for index in range(6):
        ledger, _, _ = reserve(committed, ledger, reservation_id=f"a{index}", repository="o/a",
                               lanes=["R"], now=NOW)
        ledger = _settled(ledger, f"a{index}", 100)
    ledger, refusal = ensure_open_batch(committed, ledger, NOW)
    assert refusal is None
    # batch 2 (900 calls): 900 calls, 1 seal -> 900/seal > 2 x 100
    for index in range(6):
        ledger, entry, _ = reserve(committed, ledger, reservation_id=f"b{index}", repository="o/a",
                                   lanes=["R"], now=NOW)
        ledger = _settled(ledger, f"b{index}", 150, sealed=("R",) if index == 0 else ())
    ledger, refusal = ensure_open_batch(committed, ledger, NOW)
    assert refusal is not None and "stop rule" in refusal
    assert ledger["entries"][-1]["kind"] == "stop"
    # and it stays stopped: no further batch, no reservation
    _, entry, refusal = reserve(committed, ledger, reservation_id="c", repository="o/a", lanes=["R"], now=NOW)
    assert entry is None and "stop rule" in refusal


def test_an_unsettled_reservation_past_its_ttl_stays_charged_but_is_not_in_flight() -> None:
    committed = _committed()
    ledger, _, _ = reserve(committed, empty_ledger(), reservation_id="x", repository="o/a",
                           lanes=["R"], now=NOW - timedelta(hours=7))
    document = effective_document(committed, ledger, NOW)
    assert document["batches"][-1]["calls_spent"] == 100
    assert document["batches"][-1]["hosted"]["in_flight"] == 0


def test_the_envelope_bounds_every_reservation() -> None:
    committed = _committed(spent={"calls": 8990, "tokens": 0})
    _, entry, _ = reserve(committed, empty_ledger(), reservation_id="x", repository="o/a", lanes=["R"], now=NOW)
    # the last batch holds only what the envelope has left (10), shared over six cells
    assert entry is not None and entry["calls"] == 2
    spent = _committed(spent={"calls": 9000, "tokens": 0})
    _, entry, refusal = reserve(spent, empty_ledger(), reservation_id="x", repository="o/a", lanes=["R"], now=NOW)
    assert entry is None and "envelope" in refusal


def test_the_local_document_holds_only_this_runs_allowance(tmp_path: Path) -> None:
    committed = _committed()
    ledger, entry, _ = reserve(committed, empty_ledger(), reservation_id="x", repository="o/a",
                               lanes=["R"], now=NOW)
    ledger, _, _ = reserve(committed, ledger, reservation_id="y", repository="o/b", lanes=["R"], now=NOW)
    document = local_budget_document(committed, ledger, entry, NOW)
    assert document["batches"] == [
        {"id": "e2-001", "reservation": "x", "repositories": ["o/a"], "calls_cap": 100.0,
         "tokens_cap": 100000.0, "calls_spent": 0.0, "tokens_spent": 0.0}
    ]
    assert document["spent"]["calls"] == 700  # committed 600 + y's 100, never x's own
    path = tmp_path / "budget.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    for _ in range(100):
        check_budget(path)
        record_spend(path, 1, 10)
    with pytest.raises(BudgetExceededError):
        check_budget(path)


def test_no_reservation_refuses_every_product_call(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_text(json.dumps(local_budget_document(_committed(), empty_ledger(), None, NOW)), encoding="utf-8")
    with pytest.raises(BudgetExceededError):
        check_budget(path)


def test_check_budget_refuses_past_the_total_calls_cap(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_text(json.dumps(_committed(spent={"calls": 9000, "tokens": 0})), encoding="utf-8")
    with pytest.raises(BudgetExceededError):
        check_budget(path)


def _call(call_id: str, disposition: str = "provider_call", outcome: str = "success", tokens: int = 7) -> str:
    return json.dumps({"call_id": call_id, "disposition": disposition, "outcome": outcome,
                       "total_tokens": tokens})


def test_measured_spend_counts_only_this_runs_physical_attempts(tmp_path: Path) -> None:
    ledger = tmp_path / "cascade" / "llm_cache" / "ledger.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(_call("old") + "\n", encoding="utf-8")
    baseline = budget.ledger_call_ids(tmp_path)
    with ledger.open("a", encoding="utf-8") as stream:
        stream.write(_call("new1") + "\n" + _call("new2", outcome="http_error", tokens=0) + "\n")
        stream.write(_call("new3", outcome="response_invalid") + "\n")
        stream.write(_call("reuse", disposition="cache_reuse") + "\nnot json\n")
    assert measure_new_calls(tmp_path, baseline) == (2, 7)


# --- the state-remote ledger and the CLI a hosted job runs ------------------------------------


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    return init_git_repository(tmp_path / "state-remote")


def test_the_ledger_ref_is_compare_and_swap_updated(remote: Path) -> None:
    with GitJsonRef(LEDGER_REF, remote=str(remote)) as store:
        assert store.read() == (None, None)
        store.update(lambda current: {"entries": [1]})
        store.update(lambda current: {"entries": [*current["entries"], 2]})
        assert store.read()[1] == {"entries": [1, 2]}


def test_a_lost_race_is_reapplied_on_the_newer_document(remote: Path) -> None:
    with GitJsonRef(LEDGER_REF, remote=str(remote)) as store, \
            GitJsonRef(LEDGER_REF, remote=str(remote)) as rival:
        store.update(lambda current: {"entries": ["first"]})
        raced = {"done": False}

        def mutate(current: Any) -> dict:
            if not raced["done"]:
                raced["done"] = True
                rival.update(lambda doc: {"entries": [*doc["entries"], "rival"]})
            return {"entries": [*current["entries"], "mine"]}

        store.update(mutate, sleep=lambda seconds: None)
        assert store.read()[1] == {"entries": ["first", "rival", "mine"]}


def test_ledger_refs_stay_in_the_state_namespace(remote: Path) -> None:
    from repo_presenter.core.errors import StateBackendError

    with pytest.raises(StateBackendError):
        GitJsonRef("refs/heads/main", remote=str(remote))


def test_reserve_then_settle_through_the_cli_records_measured_spend(
    remote: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    budget_path = tmp_path / "provider_budget.json"
    budget_path.write_text(json.dumps(_committed()), encoding="utf-8")
    workdir = tmp_path / "work"
    monkeypatch.setattr(budget, "code_fingerprint", lambda *a, **k: "code-1")
    monkeypatch.setattr(budget, "_sealed_lanes", lambda remote, repo, outcomes: ["R"])
    common = ["--remote", str(remote), "--budget", str(budget_path), "--repository", "o/a",
              "--workdir", str(workdir), "--id", "run-1-a1"]
    assert budget.main(["reserve", *common, "--lanes", "R"]) == 0
    local = json.loads(budget_path.read_text(encoding="utf-8"))
    assert local["batches"][0]["calls_cap"] == 100 and local["batches"][0]["reservation"] == "run-1-a1"
    record_spend(budget_path, 1, 50)
    ledger = workdir / "cascade" / "llm_cache" / "ledger.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(_call("c1", tokens=50) + "\n" + _call("c2", tokens=5) + "\n", encoding="utf-8")
    # the reserve step rewrote the local file; settle reads the committed caps from it outside git
    budget_path.write_text(json.dumps({**_committed(), "spent": local["spent"]}), encoding="utf-8")
    assert budget.main(["settle", *common, "--outcome", "R=success", "--outcome", "L=",
                        "--source-revision", "f" * 40, "--run-url", "u"]) == 0
    document = budget.read_ledger(str(remote))
    settled = next(e for e in document["entries"] if e["kind"] == "settle")
    assert settled["calls"] == 2 and settled["tokens"] == 55
    assert settled["outcomes"] == {"R": "success"} and settled["sealed"] == ["R"]
    assert settled["code"] == "code-1" and settled["batch"] == "e2-001"
    assert settled["source_revision"] == "f" * 40 and settled["budget_refused"] is False


def test_a_facts_failure_settles_as_a_failed_attempt_without_a_reservation(
    remote: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    budget_path = tmp_path / "provider_budget.json"
    budget_path.write_text(json.dumps(_committed()), encoding="utf-8")
    monkeypatch.setattr(budget, "code_fingerprint", lambda *a, **k: "code-1")
    assert budget.main(["settle", "--remote", str(remote), "--budget", str(budget_path),
                        "--repository", "o/a", "--workdir", str(tmp_path / "none"), "--id", "d-1",
                        "--lanes", "R,L", "--outcome", "R=skipped", "--outcome", "L=skipped",
                        "--facts-result", "failure", "--source-revision", "e" * 40]) == 0
    settled = budget.read_ledger(str(remote))["entries"][0]
    assert settled["outcomes"] == {"R": "failure", "L": "failure"}
    assert settled["budget_refused"] is False and settled["calls"] == 0


def test_reserve_cohort_and_release_through_the_cli(remote: Path, tmp_path: Path) -> None:
    budget_path = tmp_path / "provider_budget.json"
    budget_path.write_text(json.dumps(_committed()), encoding="utf-8")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"runs": [{"repository": "o/a", "ecosystem": "python", "lane": "both",
                                          "lanes": ["L", "R"]}]}), encoding="utf-8")
    out = tmp_path / "dispatch.json"
    assert budget.main(["reserve-cohort", "--remote", str(remote), "--budget", str(budget_path),
                        "--plan", str(plan), "--out", str(out), "--id-prefix", "cohort-9-1"]) == 0
    run = json.loads(out.read_text(encoding="utf-8"))["runs"][0]
    assert run["dispatch_id"] == "cohort-9-1-1" and run["reservation"]["calls"] == 200
    assert budget.main(["release", "--remote", str(remote), "--budget", str(budget_path),
                        "--id", "cohort-9-1-1", "--repository", "o/a", "--reason", "dispatch failed"]) == 0
    document = effective_document(_committed(), budget.read_ledger(str(remote)))
    assert document["batches"][-1]["calls_spent"] == 0  # released: charged nothing


def test_an_unreachable_ledger_fails_closed_to_zero_call_work(tmp_path: Path) -> None:
    budget_path = tmp_path / "provider_budget.json"
    budget_path.write_text(json.dumps(_committed()), encoding="utf-8")
    assert budget.main(["reserve", "--remote", str(tmp_path / "no-such-remote"), "--budget",
                        str(budget_path), "--repository", "o/a", "--workdir", str(tmp_path / "w"),
                        "--id", "x"]) == 0
    with pytest.raises(BudgetExceededError):
        check_budget(budget_path)
