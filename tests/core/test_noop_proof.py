"""The no-op proof is measured: a rerun is a different process, and its own ledger counts its
calls.

Every test here is a negative control for one way the proof could pass softly - a nonzero rerun
count behind a zero exit code, a missing ledger, one process claiming both invocations
(core/noop_proof.py).

Ported (REUSE, scoped) from the old repository-presenter project's own
tests/core/test_noop_proof.py, 2026-10-24, step 1 of
plans/PLAN_bundle_integrity_and_noop_proof.md. The old file's "reconciling totals" section
(ledger_totals/reconcile_ledger/LedgerReconciliationError -- the bundle-manifest-reading half)
and its CLI/hosted-workflow tests are NOT ported here: this repository has no bundle/manifest and
no `verify-noop-proof` CLI command yet. Those belong with core/candidates.py's own port (a later
step), not this one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from repo_presenter.core import noop_proof
from repo_presenter.core.llm.ledger import CallRecord, Ledger
from repo_presenter.core.noop_proof import (
    INVOCATION_RECORD_INVALID,
    INVOCATION_RECORD_MISSING,
    LEDGER_MISSING,
    LEDGER_NO_RECORDS,
    LEDGER_UNREADABLE,
    NONZERO_PROVIDER_CALLS,
    RERUN_FAILED,
    SAME_PROCESS,
    Invocation,
    NoOpProofError,
    ProcessIdentity,
    measure_invocation,
    require_distinct_processes,
    verify_noop_pair,
)

# The real reading, captured at import: this repository has no autouse fixture patching process
# identity yet (the old repo's only existed to let OTHER tests simulate two processes within one
# pytest worker by calling a hosted `main()` twice -- out of scope here, there is no such `main`
# yet), so this is simply the genuine function. Captured by a separate name anyway, matching the
# old test's own discipline, so a future autouse patch added for some other test file cannot
# silently change what these tests exercise.
REAL_IDENTITY = noop_proof.current_process_identity
LEDGER = "runs/transactions/owner__name/rev/calls.jsonl"


def record(
    call_id: str, invocation_id: str | None, disposition: str, tokens: int | None = 15
) -> CallRecord:
    return CallRecord(
        call_id=call_id,
        logical_call_id=f"logical-{call_id}",
        repository="owner/name",
        source_revision="a" * 40,
        stage="INVESTIGATING",
        job="repository_investigation",
        prompt_sha256="p" * 64,
        model_route="qwen3-next",
        model_served="qwen3-next",
        attempt=1 if disposition == "provider_call" else 0,
        disposition=disposition,  # type: ignore[arg-type]
        started_at="2026-10-05T00:00:00.000+00:00",
        finished_at="2026-10-05T00:00:01.000+00:00",
        latency_ms=10,
        outcome="success" if disposition == "provider_call" else "cache_reuse",
        http_status=200,
        request_sha256="r" * 64,
        response_sha256="s" * 64,
        provider_request_id=None,
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=tokens,
        error_class=None,
        invocation_id=invocation_id,
    )


def identity(n: int, *, nonce: str | None = None, pid: int | None = None) -> ProcessIdentity:
    return ProcessIdentity(pid or 100 + n, f"start-{n}", "boot-1", nonce or f"nonce-{n}")


def invocation_document(
    invocation_id: str,
    who: ProcessIdentity,
    ledger: str | None = LEDGER,
    exit_code: int | None = 0,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "invocation_id": invocation_id,
        "identity": who.to_dict(),
        "started_at": "2026-10-05T00:00:00Z",
        "finished_at": "2026-10-05T00:00:09Z",
        "exit_code": exit_code,
        "repository": "owner/name",
        "ledger": ledger,
    }


class Rerun:
    """A project root with a first-run record, a second-run record, and the ledger they share."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.first = root / "first.json"
        self.second = root / "second.json"
        self.ledger = root / LEDGER
        self.ledger.parent.mkdir(parents=True)

    def write(
        self,
        *,
        first: ProcessIdentity | None = None,
        second: ProcessIdentity | None = None,
        second_ledger: str | None = LEDGER,
        second_exit: int | None = 0,
        second_id: str = "second",
    ) -> None:
        (self.first).write_text(
            json.dumps(invocation_document("first", first or identity(1))), encoding="utf-8"
        )
        (self.second).write_text(
            json.dumps(
                invocation_document(second_id, second or identity(2), second_ledger, second_exit)
            ),
            encoding="utf-8",
        )

    def ledger_of(self, *records: CallRecord) -> None:
        self.ledger.write_text(
            "".join(f"{item.to_line()}\n" for item in records), encoding="utf-8", newline="\n"
        )


@pytest.fixture
def rerun(tmp_path: Path) -> Rerun:
    return Rerun(tmp_path)


def reason(call: Any) -> str:
    with pytest.raises(NoOpProofError) as caught:
        call()
    return caught.value.reason


# --- process identity ---------------------------------------------------------------------------


def test_identity_is_read_from_the_operating_system_and_is_stable_within_a_process() -> None:
    first, again = REAL_IDENTITY(), REAL_IDENTITY()
    assert first.pid > 0 and first.started and first.boot_id and first.nonce
    assert first == again and first.key == again.key
    # Never a placeholder: the reading is not a constant a caller could have written down.
    assert first.started not in {"unknown", "0", "n/a"}


def test_two_real_processes_have_distinct_identities_that_share_a_boot() -> None:
    code = (
        "import json;from repo_presenter.core import noop_proof as n;"
        "print(json.dumps(n.current_process_identity().to_dict()))"
    )
    # repo_presenter is not pip-installed in this project's dev setup (tests/conftest.py's own
    # sys.path.insert is what makes it importable under pytest) -- a bare subprocess needs the
    # same src/ directory on PYTHONPATH.
    src_dir = str(Path(__file__).resolve().parents[2] / "src")
    env = {**os.environ, "PYTHONPATH": src_dir}
    outputs = [
        json.loads(
            subprocess.run(
                [sys.executable, "-c", code], check=True, capture_output=True, text=True, env=env
            ).stdout
        )
        for _ in range(2)
    ]
    first, second = (ProcessIdentity.from_dict(item) for item in outputs)
    require_distinct_processes(first, second)  # does not raise
    assert first.key != second.key and first.nonce != second.nonce
    assert first.boot_id == second.boot_id  # one machine, one boot: the marker is boot-unique
    assert first.key != REAL_IDENTITY().key and first.nonce != REAL_IDENTITY().nonce


def test_one_process_claiming_both_invocations_is_refused() -> None:
    mine = REAL_IDENTITY()
    assert reason(lambda: require_distinct_processes(mine, REAL_IDENTITY())) == SAME_PROCESS
    # The same operating-system process under a doctored nonce is still one process.
    doctored = ProcessIdentity(mine.pid, mine.started, mine.boot_id, "another-nonce")
    assert reason(lambda: require_distinct_processes(mine, doctored)) == SAME_PROCESS
    # The same interpreter memory under a doctored pid is still one process.
    cloned = ProcessIdentity(mine.pid + 1, "later", mine.boot_id, mine.nonce)
    assert reason(lambda: require_distinct_processes(mine, cloned)) == SAME_PROCESS


def test_an_unreadable_identity_is_an_error_and_never_a_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> tuple[str, str]:
        raise OSError("no such file")

    monkeypatch.setattr(noop_proof, "_platform_identity", broken)
    assert reason(REAL_IDENTITY) == noop_proof.PROCESS_IDENTITY_UNAVAILABLE


def test_a_malformed_identity_in_a_record_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    document = invocation_document("x", identity(1))
    document["identity"]["pid"] = "7"  # not an integer
    path.write_text(json.dumps(document), encoding="utf-8")
    assert reason(lambda: noop_proof.read_invocation_record(path)) == INVOCATION_RECORD_INVALID


# --- the rerun gate -----------------------------------------------------------------------------


def test_a_rerun_that_reused_everything_in_another_process_verifies(rerun: Rerun) -> None:
    rerun.write()
    rerun.ledger_of(
        record("a", "first", "provider_call"),
        record("b", "first", "provider_call"),
        record("c", "second", "cache_reuse"),
        record("d", "second", "cache_reuse"),
    )
    verified = verify_noop_pair(rerun.first, rerun.second, rerun.root)
    assert verified.measurement.provider_calls == 0
    assert verified.measurement.records == 2 and verified.measurement.cache_reuses == 2


def test_a_nonzero_rerun_count_fails_whatever_the_exit_code_says(rerun: Rerun) -> None:
    """The defect this module exists to close: checking only the second invocation's exit code,
    which is 0 whether the rerun made calls or not."""
    rerun.write(second_exit=0)
    rerun.ledger_of(
        record("a", "first", "provider_call"),
        record("b", "second", "cache_reuse"),
        record("c", "second", "provider_call"),
    )
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        NONZERO_PROVIDER_CALLS
    )


def test_only_the_reruns_own_calls_count_not_the_first_runs(rerun: Rerun) -> None:
    rerun.write()
    rerun.ledger_of(
        *(record(f"first-{n}", "first", "provider_call") for n in range(30)),
        record("reuse", "second", "cache_reuse"),
    )
    assert verify_noop_pair(rerun.first, rerun.second, rerun.root).measurement.provider_calls == 0


def test_a_missing_ledger_fails_with_a_typed_reason(rerun: Rerun) -> None:
    rerun.write()  # the record names a ledger that was never written
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        LEDGER_MISSING
    )


def test_an_invocation_that_never_opened_a_ledger_fails(rerun: Rerun) -> None:
    rerun.write(second_ledger=None)
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        LEDGER_MISSING
    )


def test_an_invocation_with_no_ledger_records_proves_nothing(rerun: Rerun) -> None:
    """Zero calls is also what a process that died before its first job made."""
    rerun.write()
    rerun.ledger_of(record("a", "first", "provider_call"))
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        LEDGER_NO_RECORDS
    )


def test_a_corrupt_ledger_fails_closed(rerun: Rerun) -> None:
    rerun.write()
    rerun.ledger.write_text('{"call_id": "only-this"}\n', encoding="utf-8")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        LEDGER_UNREADABLE
    )


def test_a_missing_invocation_record_fails(rerun: Rerun) -> None:
    rerun.write()
    rerun.second.unlink()
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        INVOCATION_RECORD_MISSING
    )


def test_two_invocations_claiming_one_process_fail(rerun: Rerun) -> None:
    rerun.ledger_of(record("a", "second", "cache_reuse"))
    rerun.write(first=identity(1), second=identity(1))
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == SAME_PROCESS
    # One interpreter under two pids: the shared in-memory nonce gives it away.
    rerun.write(first=identity(1, nonce="shared"), second=identity(2, nonce="shared"))
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == SAME_PROCESS
    # One invocation recorded twice is not a rerun.
    rerun.write(second_id="first")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == SAME_PROCESS


def test_a_rerun_that_itself_failed_is_not_a_proof(rerun: Rerun) -> None:
    rerun.write(second_exit=1)
    rerun.ledger_of(record("a", "second", "cache_reuse"))
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == RERUN_FAILED


def test_a_ledger_path_that_leaves_the_project_is_refused(rerun: Rerun) -> None:
    rerun.write(second_ledger="../outside/calls.jsonl")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        INVOCATION_RECORD_INVALID
    )


# --- stamping and measuring ---------------------------------------------------------------------


def test_the_ledger_stamps_every_record_with_its_invocation(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "calls.jsonl", invocation_id="inv-1")
    ledger.append(record("a", None, "provider_call"))
    ledger.append(record("b", None, "cache_reuse"))
    measured = measure_invocation(tmp_path / "calls.jsonl", "inv-1")
    assert (measured.records, measured.provider_calls, measured.cache_reuses) == (2, 1, 1)
    assert reason(lambda: measure_invocation(tmp_path / "calls.jsonl", "inv-2")) == (
        LEDGER_NO_RECORDS
    )


def test_an_invocation_records_its_own_process_and_ledger(tmp_path: Path) -> None:
    started = Invocation.begin()
    started.attach_ledger("owner/name", tmp_path / "runs" / "t" / "calls.jsonl")
    out = tmp_path / "rec" / "first.json"
    started.write(out, tmp_path, 0)
    loaded = noop_proof.read_invocation_record(out)
    assert loaded.invocation_id == started.invocation_id
    assert loaded.identity == started.identity and loaded.exit_code == 0
    assert loaded.ledger == "runs/t/calls.jsonl"
    # An invocation that never reached its ledger records none.
    bare = Invocation.begin()
    bare.write(out, tmp_path, 1)
    assert noop_proof.read_invocation_record(out).ledger is None


# --- processability exemptions -------------------------------------------------------------------


def test_a_placeholder_repository_has_no_candidate_and_so_nothing_to_prove(rerun: Rerun) -> None:
    """A run that ends in a disposition (no candidate produced) makes no ledger and exits 0."""
    rerun.write(second_ledger=None)
    for path in (rerun.first, rerun.second):
        document = json.loads(path.read_text(encoding="utf-8"))
        document["ledger"], document["disposition"] = None, "insufficient_evidence.json"
        path.write_text(json.dumps(document), encoding="utf-8")
    verified = verify_noop_pair(rerun.first, rerun.second, rerun.root)
    assert verified.measurement is None and verified.second.disposition
    # Still two processes: the exemption is from counting a ledger, not from being a rerun.
    both = json.loads(rerun.second.read_text(encoding="utf-8"))
    both["identity"] = json.loads(rerun.first.read_text(encoding="utf-8"))["identity"]
    rerun.second.write_text(json.dumps(both), encoding="utf-8")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == SAME_PROCESS


def test_a_rerun_whose_outcome_class_differs_from_the_first_runs_fails(rerun: Rerun) -> None:
    rerun.write()
    rerun.ledger_of(record("a", "second", "cache_reuse"))
    document = json.loads(rerun.second.read_text(encoding="utf-8"))
    document["disposition"] = "insufficient_evidence.json"
    rerun.second.write_text(json.dumps(document), encoding="utf-8")
    assert reason(lambda: verify_noop_pair(rerun.first, rerun.second, rerun.root)) == (
        noop_proof.DISPOSITION_MISMATCH
    )
