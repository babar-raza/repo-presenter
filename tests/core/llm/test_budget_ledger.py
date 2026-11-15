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


def test_the_stop_rule_fires_when_the_rolling_window_cost_per_seal_more_than_doubles() -> None:
    """R43(1): the last 12 settled hosted runs against the 12 before them, never one batch."""
    committed = _committed(batches=[{"id": "e2-001", "calls_cap": 2400, "tokens_cap": 2_400_000,
                                     "calls_spent": 0, "tokens_spent": 0, "repositories": []}])
    ledger = empty_ledger()
    # the previous 12: 1200 calls, 6 seals -> 200/seal
    for index in range(12):
        ledger, _, _ = reserve(committed, ledger, reservation_id=f"a{index}", repository="o/a",
                               lanes=["R"], now=NOW)
        ledger = _settled(ledger, f"a{index}", 100, sealed=("R",) if index % 2 else ())
    # the last 12: 1200 calls, 1 seal -> 1200/seal > 2 x 200
    for index in range(12):
        ledger, entry, _ = reserve(committed, ledger, reservation_id=f"b{index}", repository="o/a",
                                   lanes=["R"], now=NOW)
        assert entry is not None, index
        ledger = _settled(ledger, f"b{index}", 100, sealed=("R",) if index == 0 else ())
    ledger, refusal = ensure_open_batch(committed, ledger, NOW)
    assert refusal is not None and "stop rule" in refusal and "last 12 settled hosted runs" in refusal
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


# --- BL-160: the M9 audit draws from, and settles to, the same durable ledger as production ---------


def _e2_011(**batch: Any) -> dict[str, Any]:
    """The 2026-11-14 shape: one committed batch (420 calls / 17.2M tokens), unspent in the file."""
    return _committed(spent={"calls": 650, "tokens": 1_077_799}, batches=[
        {"id": "e2-011-audit-and-production", "repositories": [], "calls_cap": 420,
         "tokens_cap": 17_200_000, "calls_spent": 0, "tokens_spent": 0, **batch}])


def _audit_settle(ledger: dict, rid: str, calls: float, tokens: float, cases: int, *,
                  batch: str | None = None, at: datetime = NOW) -> dict:
    entry = {"id": rid, "purpose": budget.AUDIT_PURPOSE, "repository": "m9-audit", "outcomes": {},
             "sealed": [], "cases": cases, "calls": calls, "tokens": tokens}
    if batch:
        entry["batch"] = batch
    return settle(_committed(), ledger, entry, at)


def test_production_never_reserves_a_batchs_audit_reserve() -> None:
    committed = _e2_011(audit_reserve_calls=150, audit_reserve_tokens=6_000_000)
    _, planned = reserve_cohort(committed, empty_ledger(),
                                [{"repository": f"o/{i}", "lanes": ["R"]} for i in range(8)],
                                id_prefix="c", now=NOW)
    assert sum(run["reservation"]["calls"] for run in planned if run["reservation"]) <= 420 - 150
    ledger, _ = reserve_cohort(committed, empty_ledger(), [{"repository": "o/a", "lanes": ["R"]}],
                               id_prefix="d", now=NOW)
    document = effective_document(committed, ledger, NOW)
    assert budget.audit_reserve_unspent(document["batches"][-1]) == (150.0, 6_000_000.0)
    # with no audit reserve the same cohort may take the whole batch
    _, planned = reserve_cohort(_e2_011(), empty_ledger(),
                                [{"repository": f"o/{i}", "lanes": ["R"]} for i in range(8)],
                                id_prefix="c", now=NOW)
    assert sum(run["reservation"]["calls"] for run in planned if run["reservation"]) == 420


def test_the_audit_reserves_its_measured_per_case_cost_from_the_reserve_first() -> None:
    committed = _e2_011(audit_reserve_calls=150, audit_reserve_tokens=6_000_000)
    ledger, entry, refusal = budget.reserve_audit(committed, empty_ledger(), reservation_id="audit-1-2-a1",
                                                  cases=12, now=NOW)
    assert refusal is None and entry["purpose"] == "audit" and entry["cases"] == 12
    assert (entry["calls"], entry["tokens"]) == (120.0, 4_800_000.0)  # the defaults, 10 / 400k per case
    document = effective_document(committed, ledger, NOW)
    batch = document["batches"][-1]
    assert batch["hosted"]["audit_calls"] == 120 and budget.audit_reserve_unspent(batch)[0] == 30
    # production's remaining is the batch less what the audit holds and its unspent reserve
    assert budget.production_remaining(document, batch) == (270.0, 11_200_000.0)
    # settling the audit charges its measured spend, and the next round is sized from it
    settled = settle(committed, ledger, {"id": "audit-1-2-a1", "purpose": "audit", "cases": 12,
                                         "calls": 96, "tokens": 3_000_000, "outcomes": {}, "sealed": []}, NOW)
    batch = effective_document(committed, settled, NOW)["batches"][-1]
    assert batch["calls_spent"] == 96 and batch["hosted"]["audit_runs"] == 1
    assert batch["hosted"]["runs"] == 0  # never a production run
    assert budget.measured_audit_case_cost(budget.ledger_entries(settled, 2)) == (8.0, 250_000.0)
    again, same, _ = budget.reserve_audit(committed, settled, reservation_id="audit-1-2-a1", cases=12, now=NOW)
    assert same == entry and len(again["entries"]) == len(settled["entries"])  # idempotent


def test_the_audit_is_refused_when_the_ledger_shows_the_batch_spent_though_the_file_says_unspent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact 2026-11-14 failure: production spent about 408 of e2-011's 420 calls through the
    ledger while the committed file still says 0 spent. The audit of 46 cases is refused before any
    call, and a hosted PRODUCT call against the committed file (the old second purse) is refused too."""
    committed = _e2_011()
    ledger = empty_ledger()
    for index, calls in enumerate([12, 16, 7, 19, 14, 45, 15, 38, 56, 50, 80, 56]):
        ledger, entry, _ = reserve(committed, ledger, reservation_id=f"p{index}", repository="o/a",
                                   lanes=["R"], now=NOW)
        if entry is not None:
            ledger = _settled(ledger, f"p{index}", calls, sealed=())
    assert effective_document(committed, ledger, NOW)["batches"][-1]["calls_spent"] >= 400
    _, entry, refusal = budget.reserve_audit(committed, ledger, reservation_id="audit-x", cases=46, now=NOW)
    assert entry is None and "cannot fund the audit of 46 case(s)" in refusal
    path = tmp_path / "provider_budget.json"
    path.write_text(json.dumps(committed), encoding="utf-8")
    check_budget(path)  # locally (offline use) the committed file still funds a call
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(BudgetExceededError, match="no ledger reservation"):
        check_budget(path)
    # a materialised reservation still funds a hosted call
    granted_ledger, granted, _ = budget.reserve_audit(_e2_011(), empty_ledger(), reservation_id="a",
                                                      cases=4, now=NOW)
    path.write_text(json.dumps(local_budget_document(_e2_011(), granted_ledger, granted, NOW)), encoding="utf-8")
    check_budget(path)


def test_audit_spend_is_charged_to_the_rolling_window_but_never_sizes_a_cell() -> None:
    ledger = empty_ledger()
    for index in range(5):
        ledger = _settled(ledger, f"r{index}", 10, sealed=("R",))
    ledger = _audit_settle(ledger, "audit-a", 400, 4_000_000, 40, batch="e2-001")
    entries = budget.ledger_entries(ledger, 2)
    assert [run["id"] for run in budget.settled_runs(entries)] == [f"r{i}" for i in range(5)]
    assert budget.measured_cell_cost(entries)["calls"] == 10  # the audit is not a lane-cell
    charged = budget.runs_with_audit_spend(entries)
    assert sum(run["calls"] for run in charged) == 450
    assert sum(run.get("audit_calls", 0) for run in charged) == 400 and len(charged) == 5
    document = effective_document(_committed(), ledger, NOW)
    assert document["spent"]["calls"] == 600 + 400  # the programme totals see the audit
    assert any("M9 audit" in line for line in budget.budget_summary_lines(document))


def test_audit_reserve_then_settle_through_the_cli_measures_only_its_own_call_ledger(
    remote: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    budget_path = tmp_path / "provider_budget.json"
    committed = _e2_011(audit_reserve_calls=150, audit_reserve_tokens=6_000_000)
    budget_path.write_text(json.dumps(committed), encoding="utf-8")
    monkeypatch.setattr(budget, "code_fingerprint", lambda *a, **k: "code-1")
    monkeypatch.setattr(budget, "_sealed_lanes", lambda *a: pytest.fail("an audit has no lanes to seal"))
    monkeypatch.setattr(budget, "upstream_revision", lambda *a: pytest.fail("an audit has no upstream"))
    spend, work = tmp_path / "spend", tmp_path / "work"
    common = ["--remote", str(remote), "--budget", str(budget_path), "--repository", "m9-audit",
              "--workdir", str(spend), "--id", "audit-5-6-a1", "--purpose", "audit"]
    assert budget.main(["reserve", *common, "--cases", "3"]) == 0
    local = json.loads(budget_path.read_text(encoding="utf-8"))
    assert local["batches"][0]["calls_cap"] == 30 and local["batches"][0]["reservation"] == "audit-5-6-a1"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    check_budget(budget_path)  # the materialised reservation funds the hosted audit
    record_spend(budget_path, 2, 900)
    (work / "seals" / "R" / "o__a").mkdir(parents=True)
    (work / "seals" / "R" / "o__a" / "ledger.jsonl").write_text(_call("sealed-old", tokens=10**6) + "\n")
    (work / "ledger.jsonl").write_text(_call("a1", tokens=500) + "\n" + _call("a2", tokens=400) + "\n")
    # outside git, settle reads the committed caps from this file: keep its locally recorded spend
    spent = json.loads(budget_path.read_text(encoding="utf-8"))["spent"]
    budget_path.write_text(json.dumps({**committed, "spent": spent}), encoding="utf-8")
    assert budget.main(["settle", *common, "--call-ledger", str(work / "ledger.jsonl")]) == 0
    entries = budget.read_ledger(str(remote))["entries"]
    settled = next(e for e in entries if e["kind"] == "settle")
    assert (settled["calls"], settled["tokens"]) == (2, 900)  # never the sealed bundle's old calls
    assert settled["purpose"] == "audit" and settled["cases"] == 3 and settled["outcomes"] == {}
    assert settled["batch"] == "e2-011-audit-and-production" and settled["budget_refused"] is False


def test_a_refused_audit_reservation_fails_the_step(remote: Path, tmp_path: Path) -> None:
    budget_path = tmp_path / "provider_budget.json"
    budget_path.write_text(json.dumps(_e2_011(calls_cap=5)), encoding="utf-8")
    assert budget.main(["reserve", "--remote", str(remote), "--budget", str(budget_path),
                        "--repository", "m9-audit", "--workdir", str(tmp_path / "s"), "--id", "audit-1",
                        "--purpose", "audit", "--cases", "46"]) == 3
    with pytest.raises(BudgetExceededError):
        check_budget(budget_path)  # the local file holds no allowance


def test_the_backfill_settles_a_past_rounds_artifact_ledger_once(
    remote: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ``audit-settle`` run request: no reservation, the round's artifact ledger, an explicit batch."""
    budget_path = tmp_path / "provider_budget.json"
    budget_path.write_text(json.dumps(_e2_011()), encoding="utf-8")
    monkeypatch.setattr(budget, "code_fingerprint", lambda *a, **k: "code-1")
    artifact = tmp_path / "m9-audit-spend"
    artifact.mkdir()
    (artifact / "ledger.jsonl").write_text("\n".join(_call(f"c{i}", tokens=40_000) for i in range(420)) + "\n")
    args = ["settle", "--purpose", "audit", "--cases", "46", "--remote", str(remote), "--budget",
            str(budget_path), "--id", "audit-43620199171-43641838293", "--repository", "m9-audit",
            "--batch", "e2-011-audit-and-production", "--workdir", str(artifact),
            "--call-ledger", str(artifact / "ledger.jsonl"), "--run-id", "43641838293"]
    assert budget.main(args) == 0
    assert budget.main(args) == 0  # a repeated request is a no-op
    ledger = budget.read_ledger(str(remote))
    settles = [e for e in ledger["entries"] if e["kind"] == "settle"]
    assert len(settles) == 1 and settles[0]["calls"] == 420 and settles[0]["tokens"] == 16_800_000
    batch = effective_document(_e2_011(), ledger, NOW)["batches"][-1]
    assert batch["calls_spent"] == 420 and batch["hosted"]["audit_calls"] == 420
    assert budget.measured_audit_case_cost(budget.ledger_entries(ledger, 2)) == (10.0, 365_218.0)
