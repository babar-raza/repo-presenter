"""The provider-call budget gate (TC-015, owner ruling R25): unit tests of ``check_budget`` and
``record_spend`` against a fixture budget file under ``tmp_path`` -- never the real, committed
``data/provider_budget.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.core.llm.budget import (
    BudgetExceededError,
    InferenceClass,
    check_budget,
    record_spend,
)


def _write(tmp_path: Path, document: dict[str, Any], name: str = "budget.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _document(
    *,
    total_calls_cap: float = 1000,
    total_tokens_cap: float = 1_000_000,
    spent_calls: float = 0,
    spent_tokens: float = 0,
    batches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "total_calls_cap": total_calls_cap,
        "total_tokens_cap": total_tokens_cap,
        "spent": {"calls": spent_calls, "tokens": spent_tokens},
        "batches": [] if batches is None else batches,
    }


def _open_batch(
    *, calls_cap: float = 100, tokens_cap: float = 100_000, calls_spent: float = 0,
    tokens_spent: float = 0, batch_id: str = "b1",
) -> dict[str, Any]:
    return {
        "id": batch_id,
        "repositories": ["org/repo"],
        "calls_cap": calls_cap,
        "tokens_cap": tokens_cap,
        "calls_spent": calls_spent,
        "tokens_spent": tokens_spent,
    }


def test_a_missing_budget_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(BudgetExceededError):
        check_budget(missing)


def test_an_unparseable_budget_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_text("not json at all {{{", encoding="utf-8")
    with pytest.raises(BudgetExceededError):
        check_budget(path)


def test_a_budget_file_that_is_not_a_json_object_raises(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(BudgetExceededError):
        check_budget(path)


def test_no_batches_at_all_means_no_open_batch_and_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, _document(batches=[]))
    with pytest.raises(BudgetExceededError):
        check_budget(path)


def test_a_batch_whose_calls_spent_already_reached_its_cap_is_not_open_and_raises(
    tmp_path: Path,
) -> None:
    exhausted = _open_batch(calls_cap=10, calls_spent=10)
    path = _write(tmp_path, _document(batches=[exhausted]))
    with pytest.raises(BudgetExceededError):
        check_budget(path)


def test_a_call_within_an_open_batchs_cap_succeeds_and_does_not_raise(tmp_path: Path) -> None:
    batch = _open_batch(calls_cap=10, calls_spent=5)
    path = _write(tmp_path, _document(batches=[batch]))
    check_budget(path)  # must not raise


def test_a_call_that_would_exceed_the_open_batchs_calls_cap_raises(tmp_path: Path) -> None:
    # calls_spent (9) < calls_cap (10), so the batch is open, but calls_spent + 1 (10) is not
    # strictly less than calls_cap (10) -- it would exactly reach it, not exceed it, so widen the
    # gap by one: calls_spent (10) is itself not < cap (10.5), i.e. use a cap just above spent so
    # the "+1 exceeds" branch is the one actually exercised (open, but no further headroom).
    batch = _open_batch(calls_cap=9.5, calls_spent=9)
    path = _write(tmp_path, _document(batches=[batch]))
    with pytest.raises(BudgetExceededError):
        check_budget(path)


def test_a_call_within_the_open_batchs_token_cap_with_estimated_tokens_succeeds(
    tmp_path: Path,
) -> None:
    batch = _open_batch(calls_cap=10, calls_spent=0, tokens_cap=1000, tokens_spent=100)
    path = _write(tmp_path, _document(total_tokens_cap=1_000_000, batches=[batch]))
    check_budget(path, estimated_tokens=500)  # 100 + 500 = 600 <= 1000: must not raise


def test_a_call_that_would_exceed_the_open_batchs_tokens_cap_raises(tmp_path: Path) -> None:
    batch = _open_batch(calls_cap=10, calls_spent=0, tokens_cap=1000, tokens_spent=800)
    path = _write(tmp_path, _document(total_tokens_cap=1_000_000, batches=[batch]))
    with pytest.raises(BudgetExceededError):
        check_budget(path, estimated_tokens=500)  # 800 + 500 = 1300 > 1000


def test_total_tokens_cap_is_independently_enforced_even_with_batch_headroom(
    tmp_path: Path,
) -> None:
    # The open batch itself has plenty of room (tokens_spent=0, tokens_cap=1_000_000), but the
    # program-wide spent.tokens is already near total_tokens_cap -- the global cap must still
    # refuse the call even though the batch alone would allow it.
    batch = _open_batch(calls_cap=10, calls_spent=0, tokens_cap=1_000_000, tokens_spent=0)
    path = _write(
        tmp_path,
        _document(total_tokens_cap=1000, spent_tokens=900, batches=[batch]),
    )
    with pytest.raises(BudgetExceededError):
        check_budget(path, estimated_tokens=200)  # 900 + 200 = 1100 > total_tokens_cap (1000)


def test_check_budget_does_nothing_for_every_class_other_than_product(tmp_path: Path) -> None:
    # A path that does not exist: if any of these classes actually consulted the file, this
    # would raise. None of them may.
    missing = tmp_path / "does_not_exist.json"
    check_budget(missing, inference_class=InferenceClass.NO_INFERENCE)
    check_budget(missing, inference_class=InferenceClass.REPLAY)
    check_budget(missing, inference_class=InferenceClass.SUPERVISORY)


def test_check_budget_still_gates_when_inference_class_is_explicitly_product(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(BudgetExceededError):
        check_budget(missing, inference_class=InferenceClass.PRODUCT)


def test_record_spend_updates_global_spent_and_the_open_batchs_own_running_totals(
    tmp_path: Path,
) -> None:
    batch = _open_batch(calls_cap=10, calls_spent=2, tokens_cap=1000, tokens_spent=200)
    path = _write(tmp_path, _document(spent_calls=2, spent_tokens=200, batches=[batch]))

    record_spend(path, 1, 50)

    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["spent"]["calls"] == 3
    assert document["spent"]["tokens"] == 250
    updated_batch = document["batches"][-1]
    assert updated_batch["calls_spent"] == 3
    assert updated_batch["tokens_spent"] == 250
    # Every other field of the batch and the document is left exactly as it was.
    assert updated_batch["id"] == "b1"
    assert updated_batch["calls_cap"] == 10
    assert updated_batch["tokens_cap"] == 1000
    assert document["total_calls_cap"] == 1000


def test_record_spend_writes_utf8_with_a_trailing_newline(tmp_path: Path) -> None:
    batch = _open_batch(calls_cap=10, calls_spent=0)
    path = _write(tmp_path, _document(batches=[batch]))

    record_spend(path, 1, 10)

    raw = path.read_bytes().decode("utf-8")
    assert raw.endswith("\n")
    assert not raw.endswith("\n\n")


def test_record_spend_then_check_budget_reflects_the_new_spend(tmp_path: Path) -> None:
    """A full gate/record cycle: spend against a nearly-exhausted batch, then confirm the next
    ``check_budget`` call sees the batch as no longer open."""
    batch = _open_batch(calls_cap=3, calls_spent=2)
    path = _write(tmp_path, _document(batches=[batch]))

    check_budget(path)  # calls_spent (2) + 1 = 3, not > calls_cap (3): allowed
    record_spend(path, 1, 10)

    with pytest.raises(BudgetExceededError):
        check_budget(path)  # calls_spent is now 3, which has reached calls_cap: no longer open


# --- concurrency (2026-11-09: two scripts calling record_spend at the same time raced its
# read-modify-write and briefly produced invalid JSON) ------------------------------------------


def test_many_concurrent_record_spend_calls_never_corrupt_the_file_and_lose_no_update(
    tmp_path: Path,
) -> None:
    import threading

    batch = _open_batch(calls_cap=10_000, calls_spent=0)
    path = _write(tmp_path, _document(total_calls_cap=10_000, batches=[batch]))

    n_threads = 20
    calls_per_thread = 5
    errors: list[BaseException] = []

    def _spend() -> None:
        try:
            for _ in range(calls_per_thread):
                record_spend(path, 1, 10)
        except BaseException as error:  # noqa: BLE001 -- recorded, re-raised by the main thread
            errors.append(error)

    threads = [threading.Thread(target=_spend) for _ in range(n_threads)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, errors
    # The file must still be valid JSON (never truncated/interleaved mid-write) with every
    # thread's spend accounted for -- no lost update from the race.
    document = json.loads(path.read_text(encoding="utf-8"))
    expected_calls = n_threads * calls_per_thread
    assert document["spent"]["calls"] == expected_calls
    assert document["spent"]["tokens"] == expected_calls * 10
    assert document["batches"][0]["calls_spent"] == expected_calls
    assert document["batches"][0]["tokens_spent"] == expected_calls * 10


def test_record_spend_lock_times_out_instead_of_hanging_forever(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from repo_presenter.core.llm import budget as budget_module

    monkeypatch.setattr(budget_module, "_LOCK_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(budget_module, "_LOCK_POLL_SECONDS", 0.01)
    batch = _open_batch(calls_cap=10, calls_spent=0)
    path = _write(tmp_path, _document(batches=[batch]))
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.write_text("", encoding="utf-8")  # simulate another process already holding it

    with pytest.raises(TimeoutError):
        record_spend(path, 1, 10)

    lock_path.unlink()
