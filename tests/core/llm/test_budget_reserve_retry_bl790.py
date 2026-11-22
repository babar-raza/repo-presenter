"""BL-790 (hosted Lane L PDF Cpp, run 44993719030): 'no provider budget for this run (provider-spend
ledger unavailable: StateBackendError); zero-call work only', then 'provider budget file holds no
ledger reservation' on the review's one provider call.

Four Lane L runs were dispatched 25 s apart and reserved from the one ledger ref; the run whose
first fetch or push failed gave up at once. The reserve step now re-reads and re-applies after a
backend error (the pure ``mutate`` is re-run on the newer ledger), names the error, and masks any
credential in it; after the last attempt it still fails closed."""

from __future__ import annotations

from typing import Any, Self

import pytest

from repo_presenter.core.errors import StateBackendError
from repo_presenter.core.llm import budget


class _Store:
    def __init__(self, failures: list[Exception], log: list[str]) -> None:
        self._failures, self._log = failures, log

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def update(self, mutate: Any) -> dict[str, Any]:
        self._log.append("update")
        if self._failures:
            raise self._failures.pop(0)
        return mutate({"entries": []})


def _patch(monkeypatch: pytest.MonkeyPatch, failures: list[Exception]) -> list[str]:
    log: list[str] = []
    monkeypatch.setattr(budget, "ledger_store", lambda remote, token=None: _Store(failures, log))
    monkeypatch.setattr(budget, "state_token", lambda: None)
    return log


def _mutate(outcome: dict[str, Any]) -> Any:
    def mutate(current: Any) -> dict[str, Any]:
        outcome.update({"entry": {"id": "r"}, "refusal": None})
        return {"entries": [{"id": "r"}]}

    return mutate


def test_a_transient_backend_error_is_retried_and_the_reservation_is_granted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log = _patch(monkeypatch, [StateBackendError("fetch failed"), StateBackendError("push failed")])
    outcome: dict[str, Any] = {}
    ledger, outcome = budget._update_ledger_with_retry(
        "remote", _mutate(outcome), outcome, sleep=lambda seconds: None
    )
    assert log == ["update"] * 3
    assert outcome["entry"] == {"id": "r"} and ledger == {"entries": [{"id": "r"}]}


def test_a_persistent_outage_still_fails_closed_and_names_the_error_without_a_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = StateBackendError("push of refs/x failed: fatal: unable to access 'https://x-access-token:SECRET@github.com/o/r.git/'")
    log = _patch(monkeypatch, [error] * 10)
    outcome: dict[str, Any] = {}
    ledger, outcome = budget._update_ledger_with_retry(
        "remote", _mutate(outcome), outcome, attempts=3, sleep=lambda seconds: None
    )
    assert log == ["update"] * 3
    assert outcome["entry"] is None and "StateBackendError" in outcome["refusal"]
    assert "SECRET" not in outcome["refusal"] and "***@" in outcome["refusal"]
    assert ledger == budget.empty_ledger()


def test_a_first_try_success_sleeps_never(monkeypatch: pytest.MonkeyPatch) -> None:
    log = _patch(monkeypatch, [])
    outcome: dict[str, Any] = {}

    def forbidden(seconds: float) -> None:
        raise AssertionError("no sleep on success")

    budget._update_ledger_with_retry("remote", _mutate(outcome), outcome, sleep=forbidden)
    assert log == ["update"]
