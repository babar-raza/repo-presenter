"""The provider-call budget gate (owner ruling R25): the whole 2026-11-07 delivery program's
provider-call envelope, spent in capped batches, with every genuine fresh model call refused
outright unless an open, un-exhausted batch exists to charge it to.

``data/provider_budget.json`` (read verbatim, never assumed) holds the program-wide envelope:
``total_calls_cap`` / ``total_tokens_cap`` (the whole program's hard ceiling), ``spent`` (the
running ``calls``/``tokens`` totals across every batch ever opened), and ``batches`` -- a list of
dicts this module gives the shape ``{"id", "repositories", "calls_cap", "tokens_cap",
"calls_spent", "tokens_spent"}``. Opening, sizing, and closing a batch is the supervisor's own
ongoing job (owner ruling R25); this module only reads and spends against whatever batch is
already there.

**The four inference classes** (docs/DELIVERY_PLAN_2026-11-07.md section 7; restated here so this
module is self-contained):

* ``NO_INFERENCE`` -- no model call of any kind (recertification, rule-based checks, deterministic
  decisions). Never gated: there is nothing to gate.
* ``REPLAY`` -- :func:`repo_presenter.core.llm.jobs.run_job`'s own cache-hit path: the accepted
  output for this exact request is already on disk, so the request is answered from the store with
  zero network calls. Never gated: a replay never reaches this module at all (``run_job`` never
  calls :func:`check_budget` or :func:`record_spend` on that path).
* ``SUPERVISORY`` -- a Claude/Codex session doing manual review or prompt-tuning work. Never a
  qwen3-next product call, so never gated by this module either.
* ``PRODUCT`` -- a genuine fresh qwen3-next inference call (``run_job``'s retry loop, the one real
  provider-call boundary in this codebase). This is the only class :func:`check_budget` ever
  blocks; it is a deliberate no-op for every other class.

**What "open" means.** A batch in ``batches[]`` is open when it is the *last* entry in the list and
its own ``calls_spent`` has not yet reached its own ``calls_cap``. There is at most one open batch
at a time: once the last batch's ``calls_spent`` reaches its ``calls_cap`` it is exhausted and
nothing is open until the supervisor appends a new one. An empty ``batches[]`` means nothing is
open (no batch has ever been opened yet).
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import math
import os
import subprocess
import time
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

#: ``src/repo_presenter/core/llm/budget.py`` -> ``core/llm`` -> ``core`` -> ``repo_presenter`` ->
#: ``src`` -> the repository root (same depth, and the same convention, as
#: ``repo_presenter.readme.review.calibration_status.DEFAULT_CALIBRATION_PATH``).
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BUDGET_PATH = REPO_ROOT / "data" / "provider_budget.json"


class InferenceClass(Enum):
    """The four classes of activity this delivery program distinguishes (see module docstring)."""

    NO_INFERENCE = "no_inference"
    REPLAY = "replay"
    SUPERVISORY = "supervisory"
    PRODUCT = "product"


class BudgetExceededError(Exception):
    """A ``PRODUCT`` call was refused before any network request was made: the budget file at
    ``budget_path`` is missing or unparseable, no batch in ``batches[]`` is open, or spending the
    call (and, when known in advance, its estimated tokens) would exceed the open batch's own cap
    or the program's total cap."""


def _load_document(budget_path: Path) -> dict[str, Any]:
    """The budget file's decoded JSON object. Raises :class:`BudgetExceededError`, never a bare
    ``OSError``/``ValueError``, so every caller of :func:`check_budget` fails the same way on a
    missing or corrupt file."""
    try:
        raw = budget_path.read_text(encoding="utf-8")
    except OSError as error:
        raise BudgetExceededError(f"provider budget file {budget_path} cannot be read: {error}") from error
    try:
        document = json.loads(raw)
    except ValueError as error:
        raise BudgetExceededError(f"provider budget file {budget_path} is not valid JSON: {error}") from error
    if not isinstance(document, dict):
        raise BudgetExceededError(f"provider budget file {budget_path} is not a JSON object")
    return document


def _number(value: Any) -> float | None:
    """``value`` as a plain number, excluding ``bool`` (a JSON boolean is never a cap or a spend
    count even though ``isinstance(True, int)`` is true in Python)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _spent(document: dict[str, Any]) -> tuple[float, float]:
    """The program-wide ``spent.calls``/``spent.tokens`` totals; missing or malformed reads as
    zero spent so far (there is nothing to protect against double-counting on a fresh file)."""
    spent = document.get("spent")
    if not isinstance(spent, dict):
        return 0.0, 0.0
    calls = _number(spent.get("calls"))
    tokens = _number(spent.get("tokens"))
    return (calls or 0.0), (tokens or 0.0)


def _open_batch(document: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
    """The ``(index, batch)`` of the currently open batch (see module docstring), or ``None`` when
    nothing is open: an empty ``batches[]``, a malformed last entry, or one whose own
    ``calls_spent`` has already reached its ``calls_cap``."""
    batches = document.get("batches")
    if not isinstance(batches, list) or not batches:
        return None
    index = len(batches) - 1
    batch = batches[index]
    if not isinstance(batch, dict):
        return None
    calls_cap = _number(batch.get("calls_cap"))
    calls_spent = _number(batch.get("calls_spent"))
    if calls_cap is None or calls_spent is None:
        return None
    if calls_spent >= calls_cap:
        return None
    return index, batch


def check_budget(
    budget_path: Path,
    estimated_tokens: int | None = None,
    *,
    inference_class: InferenceClass = InferenceClass.PRODUCT,
) -> None:
    """Refuse a ``PRODUCT`` call the program's budget cannot afford, before it is ever sent.

    Raises :class:`BudgetExceededError` when ``inference_class`` is ``PRODUCT`` and: the budget
    file does not exist or does not parse as a JSON object; there is no open batch (see module
    docstring); the open batch's ``calls_spent + 1`` would exceed its own ``calls_cap``; or, when
    ``estimated_tokens`` is given, ``spent.tokens + estimated_tokens`` would exceed
    ``total_tokens_cap`` or the open batch's ``tokens_spent + estimated_tokens`` would exceed its
    own ``tokens_cap``.

    Does nothing -- not even reading ``budget_path`` -- for every other :class:`InferenceClass`:
    ``NO_INFERENCE``, ``REPLAY`` and ``SUPERVISORY`` are never gated by this function.
    """
    if inference_class is not InferenceClass.PRODUCT:
        return
    document = _load_document(budget_path)
    located = _open_batch(document)
    if located is None:
        raise BudgetExceededError(
            f"provider budget file {budget_path} has no open batch; a PRODUCT call is refused "
            "until the supervisor opens one"
        )
    _, batch = located
    calls_cap = _number(batch.get("calls_cap"))
    calls_spent = _number(batch.get("calls_spent")) or 0.0
    if calls_cap is None or calls_spent + 1 > calls_cap:
        raise BudgetExceededError(
            f"provider budget file {budget_path}: the open batch's calls_spent "
            f"({calls_spent}) + 1 would exceed its own calls_cap ({calls_cap})"
        )
    total_calls_cap = _number(document.get("total_calls_cap"))
    if total_calls_cap is not None and _spent(document)[0] + 1 > total_calls_cap:
        raise BudgetExceededError(
            f"provider budget file {budget_path}: spent.calls ({_spent(document)[0]}) + 1 would "
            f"exceed total_calls_cap ({total_calls_cap})"
        )
    if estimated_tokens is None:
        return
    spent_calls, spent_tokens = _spent(document)
    total_tokens_cap = _number(document.get("total_tokens_cap"))
    if total_tokens_cap is None or spent_tokens + estimated_tokens > total_tokens_cap:
        raise BudgetExceededError(
            f"provider budget file {budget_path}: spent.tokens ({spent_tokens}) + "
            f"estimated_tokens ({estimated_tokens}) would exceed total_tokens_cap "
            f"({total_tokens_cap})"
        )
    tokens_cap = _number(batch.get("tokens_cap"))
    tokens_spent = _number(batch.get("tokens_spent")) or 0.0
    if tokens_cap is None or tokens_spent + estimated_tokens > tokens_cap:
        raise BudgetExceededError(
            f"provider budget file {budget_path}: the open batch's tokens_spent "
            f"({tokens_spent}) + estimated_tokens ({estimated_tokens}) would exceed its own "
            f"tokens_cap ({tokens_cap})"
        )


_LOCK_TIMEOUT_SECONDS = 10.0
_LOCK_POLL_SECONDS = 0.05


@contextlib.contextmanager
def _locked(budget_path: Path):
    """A simple, portable (POSIX and Windows) mutex over ``budget_path``'s own read-modify-write
    cycle: exclusive-create a sibling ``.lock`` file (``os.O_CREAT | os.O_EXCL`` -- atomic on both
    platforms, unlike a lock-free read-check-write), retrying with a short poll until
    ``_LOCK_TIMEOUT_SECONDS`` elapses, then raise. Found necessary 2026-11-09: two scripts
    calling :func:`record_spend` at the same time raced this exact read-modify-write and briefly
    produced invalid JSON (see docs/DECISION_LOG.md, the same date) -- this lock, plus the atomic
    rename in :func:`_write_document_atomically`, closes that gap for any two CALLERS OF THIS
    MODULE; it does not make ``check_budget`` + the provider call + ``record_spend`` atomic as
    one unit across a call site (a separate, larger gap, not fixed here)."""
    lock_path = budget_path.with_suffix(budget_path.suffix + ".lock")
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    fd = None
    while fd is None:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"could not acquire {lock_path} within {_LOCK_TIMEOUT_SECONDS}s "
                    "(another process is updating the provider budget file)"
                ) from None
            time.sleep(_LOCK_POLL_SECONDS)
    try:
        os.close(fd)
        yield
    finally:
        with contextlib.suppress(OSError):
            lock_path.unlink()


def _write_document_atomically(budget_path: Path, document: dict[str, Any]) -> None:
    """Write ``document`` to ``budget_path`` via a same-directory temp file plus
    ``os.replace`` -- atomic on both POSIX and Windows, so a reader never observes a partially
    written (truncated or interleaved) file, which a direct ``write_text`` cannot promise."""
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp_path = budget_path.with_suffix(budget_path.suffix + f".tmp{os.getpid()}")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, budget_path)


def record_spend(budget_path: Path, calls: int, tokens: int) -> None:
    """Record a ``PRODUCT`` call that actually succeeded: add ``calls``/``tokens`` to the
    program-wide ``spent`` totals and to the currently open batch's own running
    ``calls_spent``/``tokens_spent`` totals (see module docstring for what "open" means), then
    write the file back whole -- the read-modify-write is locked (:func:`_locked`) and the write
    itself is atomic (:func:`_write_document_atomically`), so two concurrent callers can never
    corrupt the file or silently lose one another's update.

    Called only after the call it accounts for has already happened -- it never itself decides
    whether a call may proceed; that is :func:`check_budget`'s job, always called first.
    """
    with _locked(budget_path):
        document = _load_document(budget_path)
        spent = document.get("spent")
        if not isinstance(spent, dict):
            spent = {}
            document["spent"] = spent
        spent["calls"] = (_number(spent.get("calls")) or 0.0) + calls
        spent["tokens"] = (_number(spent.get("tokens")) or 0.0) + tokens
        located = _open_batch(document)
        if located is not None:
            index, batch = located
            batch["calls_spent"] = (_number(batch.get("calls_spent")) or 0.0) + calls
            batch["tokens_spent"] = (_number(batch.get("tokens_spent")) or 0.0) + tokens
            document["batches"][index] = batch
        _write_document_atomically(budget_path, document)


# --- The durable hosted spend ledger (owner ruling R37, 2026-11-13) ------------------------------
#
# A hosted runner starts from the committed ``data/provider_budget.json`` and throws its own
# ``record_spend`` writes away when it ends, and ``main`` is a protected branch (required status
# check ``test``), so no hosted job can commit its spend there. The durable record of hosted spend
# is therefore one JSON ledger on the state remote, ``LEDGER_REF`` -- the namespace the bot token
# already writes for transaction records and sealed bundles -- appended by compare-and-swap
# (``core/state/git_backend.GitJsonRef``).
#
# Split of authority:
#
# * the committed file stays the owner's: ``total_calls_cap``/``total_tokens_cap``,
#   ``batch_size_repositories``, ``per_batch_cap_multiplier``,
#   ``stop_rule_cost_per_sealed_candidate_multiplier`` and ``epoch`` are read from it and never
#   written by a hosted job; a batch the supervisor commits there still takes precedence over
#   every batch a hosted job opened after the previous committed one;
# * the ledger holds what hosted jobs did: ``open_batch`` (the next batch, opened when the last
#   one cannot fund another cell, sized by R25 from the previous batch's measured median), ``stop``
#   (the stop rule fired), ``reserve`` (an allowance granted to one run before it spends) and
#   ``settle`` (that run's measured provider calls and tokens from its own call ledgers, its lane
#   outcomes, seals, code fingerprint and upstream revision -- written on success or failure).
#
# ``effective_document`` folds the two into a document of the committed file's own shape, so
# ``check_budget`` keeps its semantics exactly: a hosted job's local budget file is rewritten to
# hold only its own reservation as the open batch, so concurrent jobs can never together spend
# more than the batch holds. An unsettled reservation is charged in full (a job killed before it
# settled spent an unknown amount up to its allowance); it is never released by assumption.

LEDGER_REF = "refs/repository-presenter-state/ledger/provider-spend"
LEDGER_SCHEMA_VERSION = 1
#: A reservation not settled within this long is no longer "in flight" (the facts job's 60 and the
#: present job's 90 minute timeouts, plus queueing); it stays charged in full.
RESERVATION_TTL_SECONDS = 6 * 3600
#: Files under ``data/`` that are operational records, not code: changing them never re-opens a
#: cell that failed on otherwise unchanged code.
OPERATIONAL_DATA_FILES = frozenset(
    {
        "provider_budget.json",
        "scheduled_execution_policy.json",
        "terminal_cells.json",
        "recertification_baseline.json",
        "registry_observations.json",
        "issue_pilot.json",
    }
)
#: The local file a hosted job keeps its reservation and its call ledgers' baseline in.
RESERVATION_FILENAME = "budget-reservation.json"
STATE_TOKEN_VARIABLE = "REPOSITORY_PRESENTER_STATE_TOKEN"


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)  # noqa: FURB162


def empty_ledger() -> dict[str, Any]:
    return {"schema_version": LEDGER_SCHEMA_VERSION, "entries": []}


def ledger_entries(ledger: Any, epoch: Any = None, *, any_epoch: bool = False) -> list[dict[str, Any]]:
    """The ledger's entries of one budget ``epoch`` (or of every epoch)."""
    if not isinstance(ledger, dict) or not isinstance(ledger.get("entries"), list):
        return []
    return [
        entry
        for entry in ledger["entries"]
        if isinstance(entry, dict) and (any_epoch or entry.get("epoch") == epoch)
    ]


def _num(value: Any) -> float:
    return _number(value) or 0.0


def batch_usage(entries: list[dict[str, Any]], now: datetime | None = None) -> dict[str, dict[str, Any]]:
    """Per batch id: the calls/tokens charged by hosted runs (a settled run at its measured cost,
    an unsettled reservation at its full allowance), the settled runs, the seals they produced and
    the reservations still in flight."""
    now = now or _now_utc()
    settles = {e.get("id"): e for e in entries if e.get("kind") == "settle"}
    usage: dict[str, dict[str, Any]] = {}

    def slot(batch_id: Any) -> dict[str, Any]:
        return usage.setdefault(
            str(batch_id),
            {"calls": 0.0, "tokens": 0.0, "settled": [], "sealed": 0, "in_flight": []},
        )

    def charge_settled(bucket: dict[str, Any], settled: dict[str, Any]) -> None:
        bucket["calls"] += _num(settled.get("calls"))
        bucket["tokens"] += _num(settled.get("tokens"))
        bucket["settled"].append(settled)
        bucket["sealed"] += len(settled.get("sealed") or [])

    reserved_ids = set()
    for entry in entries:
        if entry.get("kind") != "reserve":
            continue
        reserved_ids.add(entry.get("id"))
        bucket = slot(entry.get("batch"))
        settled = settles.get(entry.get("id"))
        if settled is not None:
            charge_settled(bucket, settled)
            continue
        bucket["calls"] += _num(entry.get("calls"))
        bucket["tokens"] += _num(entry.get("tokens"))
        at = _parse_iso(entry.get("at"))
        if at is not None and (now - at).total_seconds() < RESERVATION_TTL_SECONDS:
            bucket["in_flight"].append(entry)
    for settle_id, settled in settles.items():
        if settle_id in reserved_ids or not settled.get("batch"):
            continue
        charge_settled(slot(settled.get("batch")), settled)
    return usage


def effective_document(
    committed: dict[str, Any], ledger: Any, now: datetime | None = None
) -> dict[str, Any]:
    """The committed budget document with the hosted ledger folded in (pure): batches opened by
    hosted jobs appended after the committed last batch, every batch's ``calls_spent``/
    ``tokens_spent`` and the programme ``spent`` raised by what hosted runs were charged, and
    ``stop`` set when the stop rule fired on the current last batch."""
    document = copy.deepcopy(committed)
    entries = ledger_entries(ledger, committed.get("epoch"))
    batches = [b for b in (document.get("batches") or []) if isinstance(b, dict)]
    last_id = batches[-1].get("id") if batches else None
    for entry in entries:
        if entry.get("kind") == "open_batch" and entry.get("after") == last_id:
            batches.append(
                {
                    "id": entry.get("id"),
                    "repositories": [],
                    "calls_cap": _num(entry.get("calls_cap")),
                    "tokens_cap": _num(entry.get("tokens_cap")),
                    "calls_spent": 0.0,
                    "tokens_spent": 0.0,
                    "basis": entry.get("basis", ""),
                    "opened_by": "hosted",
                }
            )
            last_id = entry.get("id")
    usage = batch_usage(entries, now)
    for batch in batches:
        used = usage.get(str(batch.get("id")))
        if used is None:
            continue
        batch["calls_spent"] = _num(batch.get("calls_spent")) + used["calls"]
        batch["tokens_spent"] = _num(batch.get("tokens_spent")) + used["tokens"]
        batch["hosted"] = {
            "calls": used["calls"],
            "tokens": used["tokens"],
            "runs": len(used["settled"]),
            "sealed": used["sealed"],
            "in_flight": len(used["in_flight"]),
        }
    calls, tokens = _spent(document)
    document["spent"] = {
        "calls": calls + sum(u["calls"] for u in usage.values()),
        "tokens": tokens + sum(u["tokens"] for u in usage.values()),
    }
    document["batches"] = batches
    stops = [e for e in entries if e.get("kind") == "stop" and e.get("batch") == last_id]
    if stops:
        document["stop"] = stops[-1]
    return document


def per_cell_allowance(document: dict[str, Any], batch: dict[str, Any]) -> tuple[float, float]:
    """One cell's share of a batch: its caps over ``batch_size_repositories`` (R25's six)."""
    size = max(1, int(_num(document.get("batch_size_repositories")) or 6))
    return (
        float(math.ceil(_num(batch.get("calls_cap")) / size)),
        float(math.ceil(_num(batch.get("tokens_cap")) / size)),
    )


def _median(values: list[float]) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def cost_per_sealed(batch: dict[str, Any]) -> float | None:
    """Hosted calls per sealed candidate in ``batch``: ``inf`` when it spent and sealed nothing,
    ``None`` when no hosted run measured it (a batch spent outside the ledger is not judged)."""
    hosted = batch.get("hosted")
    if not isinstance(hosted, dict) or not hosted.get("runs"):
        return None
    if hosted.get("sealed"):
        return _num(hosted.get("calls")) / _num(hosted.get("sealed"))
    return math.inf if _num(hosted.get("calls")) > 0 else None


def batch_remaining(document: dict[str, Any], batch: dict[str, Any]) -> tuple[float, float]:
    """What ``batch`` can still fund, never more than the programme envelope has left."""
    calls, tokens = _spent(document)
    total_calls = _number(document.get("total_calls_cap")) or 0.0
    total_tokens = _number(document.get("total_tokens_cap")) or 0.0
    return (
        min(_num(batch.get("calls_cap")) - _num(batch.get("calls_spent")), total_calls - calls),
        min(_num(batch.get("tokens_cap")) - _num(batch.get("tokens_spent")), total_tokens - tokens),
    )


def ensure_open_batch(
    committed: dict[str, Any], ledger: Any, now: datetime | None = None
) -> tuple[dict[str, Any], str | None]:
    """Make sure the last batch can fund at least one cell, opening the next one under R25 when it
    cannot (pure). Returns ``(ledger, None)`` when a batch can fund a cell (possibly with a new
    ``open_batch`` entry), or ``(ledger, reason)`` naming why nothing can be spent -- with a new
    ``stop`` entry when the stop rule fired."""
    now = now or _now_utc()
    ledger = copy.deepcopy(ledger) if isinstance(ledger, dict) else empty_ledger()
    ledger.setdefault("entries", [])
    document = effective_document(committed, ledger, now)
    batches = document.get("batches") or []
    if not batches:
        return ledger, "no batch has ever been opened in data/provider_budget.json"
    last = batches[-1]
    cell_calls, _ = per_cell_allowance(document, last)
    remaining_calls, remaining_tokens = batch_remaining(document, last)
    if remaining_calls >= max(1.0, cell_calls) and remaining_tokens >= 1:
        return ledger, None
    if "stop" in document:
        return ledger, (
            f"stop rule fired on batch {last.get('id')} ({document['stop'].get('reason')}); "
            "a batch committed to data/provider_budget.json resumes spending"
        )
    hosted = last.get("hosted") or {}
    if hosted.get("in_flight"):
        return ledger, (
            f"batch {last.get('id')} is spent down; waiting for {hosted['in_flight']} in-flight "
            "run(s) to settle before measuring it and opening the next"
        )
    current_cost = cost_per_sealed(last)
    previous_cost = next(
        (
            cost
            for cost in (cost_per_sealed(b) for b in reversed(batches[:-1]))
            if cost is not None and cost != math.inf
        ),
        None,
    )
    multiplier = _number(committed.get("stop_rule_cost_per_sealed_candidate_multiplier")) or 2.0
    if (
        current_cost is not None
        and previous_cost is not None
        and current_cost > multiplier * previous_cost
    ):
        reason = (
            f"cost per sealed candidate {current_cost:.1f} calls exceeds {multiplier:g}x the "
            f"previous measured batch's {previous_cost:.1f}"
        )
        ledger["entries"].append(
            {"kind": "stop", "epoch": committed.get("epoch"), "batch": last.get("id"),
             "reason": reason, "at": _iso(now)}
        )
        return ledger, f"stop rule fired on batch {last.get('id')}: {reason}"
    size = max(1, int(_num(committed.get("batch_size_repositories")) or 6))
    cap_multiplier = _number(committed.get("per_batch_cap_multiplier")) or 1.5
    usage = batch_usage(ledger_entries(ledger, committed.get("epoch")), now)
    measured = [
        s for s in usage.get(str(last.get("id")), {}).get("settled", []) if _num(s.get("calls")) > 0
    ]
    median_calls = _median([_num(s.get("calls")) for s in measured])
    median_tokens = _median([_num(s.get("tokens")) for s in measured])
    if median_calls is None:
        calls_cap, tokens_cap = _num(last.get("calls_cap")), _num(last.get("tokens_cap"))
        basis = f"no hosted run measured {last.get('id')}: its caps carried forward"
    else:
        calls_cap = float(math.ceil(cap_multiplier * median_calls * size))
        tokens_cap = float(math.ceil(cap_multiplier * (median_tokens or 0.0) * size))
        basis = (
            f"R25: {cap_multiplier:g}x the measured median of {len(measured)} run(s) in "
            f"{last.get('id')} ({median_calls:g} calls, {median_tokens or 0:g} tokens) x {size}"
        )
    spent_calls, spent_tokens = _spent(document)
    calls_cap = min(calls_cap, (_number(committed.get("total_calls_cap")) or 0.0) - spent_calls)
    tokens_cap = min(tokens_cap, (_number(committed.get("total_tokens_cap")) or 0.0) - spent_tokens)
    if calls_cap < 1 or tokens_cap < 1:
        return ledger, "the programme envelope (total_calls_cap/total_tokens_cap) is spent"
    batch_id = f"e{committed.get('epoch')}-{len(batches) + 1:03d}-hosted"
    ledger["entries"].append(
        {"kind": "open_batch", "epoch": committed.get("epoch"), "id": batch_id,
         "after": last.get("id"), "calls_cap": calls_cap, "tokens_cap": tokens_cap,
         "basis": basis, "at": _iso(now)}
    )
    return ledger, None


def find_entry(ledger: Any, kind: str, entry_id: str) -> dict[str, Any] | None:
    for entry in ledger_entries(ledger, any_epoch=True):
        if entry.get("kind") == kind and entry.get("id") == entry_id:
            return entry
    return None


def reserve(
    committed: dict[str, Any],
    ledger: Any,
    *,
    reservation_id: str,
    repository: str,
    lanes: list[str],
    now: datetime | None = None,
    meta: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    """Grant ``reservation_id`` an allowance (pure): one cell's share of the open batch per lane,
    never more than the batch or the envelope has left. Returns ``(ledger, entry, refusal)``; an
    existing reservation of that id is returned unchanged (idempotent)."""
    now = now or _now_utc()
    existing = find_entry(ledger, "reserve", reservation_id)
    if existing is not None:
        return copy.deepcopy(ledger), existing, None
    ledger, refusal = ensure_open_batch(committed, ledger, now)
    if refusal is not None:
        return ledger, None, refusal
    document = effective_document(committed, ledger, now)
    batch = document["batches"][-1]
    cell_calls, cell_tokens = per_cell_allowance(document, batch)
    remaining_calls, remaining_tokens = batch_remaining(document, batch)
    calls = float(min(cell_calls * max(1, len(lanes)), remaining_calls))
    tokens = float(min(cell_tokens * max(1, len(lanes)), remaining_tokens))
    if calls < 1 or tokens < 1:
        return ledger, None, f"batch {batch.get('id')} cannot fund another cell"
    entry = {
        "kind": "reserve", "epoch": committed.get("epoch"), "id": reservation_id,
        "batch": batch.get("id"), "repository": repository, "lanes": list(lanes),
        "calls": calls, "tokens": tokens, "at": _iso(now), **(meta or {}),
    }
    ledger["entries"].append(entry)
    return ledger, entry, None


def settle(
    committed: dict[str, Any], ledger: Any, entry: dict[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    """Append one run's ``settle`` entry (pure); a second settle of the same id is a no-op."""
    ledger = copy.deepcopy(ledger) if isinstance(ledger, dict) else empty_ledger()
    ledger.setdefault("entries", [])
    if find_entry(ledger, "settle", str(entry.get("id"))) is not None:
        return ledger
    reservation = find_entry(ledger, "reserve", str(entry.get("id")))
    ledger["entries"].append(
        {
            "kind": "settle",
            "epoch": committed.get("epoch"),
            "batch": (reservation or {}).get("batch", entry.get("batch")),
            "at": _iso(now or _now_utc()),
            **entry,
        }
    )
    return ledger


def local_budget_document(
    committed: dict[str, Any],
    ledger: Any,
    reservation: dict[str, Any] | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """The budget file a hosted job runs against: the committed caps, the programme ``spent``
    from the durable ledger (less this run's own reservation), and exactly one batch -- this
    run's reservation, or an exhausted placeholder when none was granted, so ``check_budget``
    refuses every ``PRODUCT`` call while zero-call work (replay, recertification) still runs."""
    others = copy.deepcopy(ledger) if isinstance(ledger, dict) else empty_ledger()
    if reservation is not None:
        others["entries"] = [
            e for e in others.get("entries", [])
            if not (e.get("kind") == "reserve" and e.get("id") == reservation.get("id"))
        ]
    document = effective_document(committed, others, now)
    document.pop("stop", None)
    if reservation is None:
        document["batches"] = [
            {"id": "no-reservation", "repositories": [], "calls_cap": 0, "tokens_cap": 0,
             "calls_spent": 0, "tokens_spent": 0}
        ]
    else:
        document["batches"] = [
            {"id": reservation.get("batch"), "reservation": reservation.get("id"),
             "repositories": [reservation.get("repository")],
             "calls_cap": _num(reservation.get("calls")),
             "tokens_cap": _num(reservation.get("tokens")),
             "calls_spent": 0.0, "tokens_spent": 0.0}
        ]
    document["note"] = (
        "Materialised by a hosted job from data/provider_budget.json (caps) and "
        f"{LEDGER_REF} (spend); never committed."
    )
    return document


def _call_ledger_records(workdir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not workdir.is_dir():
        return records
    for path in sorted(workdir.rglob("*.jsonl")):
        if path.name not in ("ledger.jsonl", "calls.jsonl"):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and "call_id" in record:
                records.append(record)
    return records


def ledger_call_ids(workdir: Path) -> set[str]:
    """Every call id already in a call ledger under ``workdir`` (e.g. restored by the cache)."""
    return {str(record.get("call_id")) for record in _call_ledger_records(workdir)}


def measure_new_calls(workdir: Path, baseline: set[str]) -> tuple[int, int]:
    """The physical provider calls, and their tokens, appended to ``workdir``'s call ledgers since
    ``baseline`` was taken: the run's own measured cost (a ``response_invalid`` marker sends
    nothing, ``core/llm/ledger.is_physical_attempt``)."""
    seen: set[str] = set()
    calls = tokens = 0
    for record in _call_ledger_records(workdir):
        call_id = str(record.get("call_id"))
        if call_id in baseline or call_id in seen:
            continue
        seen.add(call_id)
        if record.get("disposition") != "provider_call" or record.get("outcome") == "response_invalid":
            continue
        calls += 1
        tokens += int(_num(record.get("total_tokens")))
    return calls, tokens


def code_fingerprint(root: Path = REPO_ROOT, revision: str = "HEAD") -> str:
    """One hash of the code a run executes at ``revision`` (``src``, ``prompts``,
    ``pyproject.toml`` and every non-operational ``data/`` file): two attempts with the same
    fingerprint ran the same code, whatever else (a decision-log line, a budget batch) changed on
    ``main`` between them. Empty when git cannot read the tree."""
    listed = subprocess.run(
        ["git", "ls-tree", "-r", revision, "--", "src", "prompts", "pyproject.toml", "data"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    if listed.returncode != 0 or not listed.stdout.strip():
        return ""
    kept = []
    for line in listed.stdout.splitlines():
        path = line.split("\t", 1)[-1]
        if path.startswith("data/") and path[len("data/"):] in OPERATIONAL_DATA_FILES:
            continue
        kept.append(line)
    return hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()


def upstream_revision(repository: str, timeout: float = 30) -> str | None:
    """The upstream default branch's current revision (``git ls-remote``), or ``None``."""
    try:
        listed = subprocess.run(
            ["git", "ls-remote", f"https://github.com/{repository}.git", "HEAD"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if listed.returncode != 0 or not listed.stdout.strip():
        return None
    return listed.stdout.split()[0]


def state_token() -> str | None:
    return os.environ.get(STATE_TOKEN_VARIABLE) or None


def ledger_store(remote: str, token: str | None = None) -> Any:
    from repo_presenter.core.state.git_backend import GitJsonRef

    return GitJsonRef(LEDGER_REF, remote=remote, token=token)


def read_ledger(remote: str, token: str | None = None) -> dict[str, Any]:
    with ledger_store(remote, token) as store:
        _, document = store.read()
    return document if isinstance(document, dict) else empty_ledger()


def committed_document(budget_path: Path) -> dict[str, Any]:
    """The budget file as committed at ``HEAD`` (a hosted job's reserve step rewrites the local
    copy), falling back to the file on disk outside a git checkout."""
    try:
        relative = budget_path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        relative = None
    if relative is not None:
        shown = subprocess.run(
            ["git", "show", f"HEAD:{relative.as_posix()}"], cwd=REPO_ROOT,
            capture_output=True, text=True, check=False,
        )
        if shown.returncode == 0:
            try:
                document = json.loads(shown.stdout)
            except ValueError:
                document = None
            if isinstance(document, dict):
                return document
    return _load_document(budget_path)


def _cmd_reserve(args: Any) -> int:
    """Claim (or grant) this run's reservation, then materialise the local budget file."""
    committed = committed_document(args.budget)
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    meta = {"run_id": args.run_id, "main_sha": args.main_sha}
    outcome: dict[str, Any] = {}

    def mutate(current: Any) -> dict[str, Any]:
        ledger, entry, refusal = reserve(
            committed, current, reservation_id=args.id, repository=args.repository,
            lanes=[lane for lane in args.lanes.split(",") if lane], meta=meta,
        )
        outcome.update({"entry": entry, "refusal": refusal})
        return ledger

    try:
        with ledger_store(args.remote, state_token()) as store:
            ledger = store.update(mutate)
    except Exception as error:  # noqa: BLE001 -- a ledger outage fails closed: no spend at all
        ledger = empty_ledger()
        outcome = {"entry": None, "refusal": f"provider-spend ledger unavailable: {type(error).__name__}"}
    entry, refusal = outcome.get("entry"), outcome.get("refusal")
    if entry is not None and find_entry(ledger, "settle", args.id) is not None:
        entry, refusal = None, f"reservation {args.id} is already settled; a re-run needs a new id"
    document = local_budget_document(committed, ledger, entry)
    _write_document_atomically(args.budget, document)
    (workdir / RESERVATION_FILENAME).write_text(
        json.dumps(
            {"id": args.id, "reservation": entry, "refusal": refusal,
             "baseline_call_ids": sorted(ledger_call_ids(workdir)),
             "baseline_spent": document.get("spent")},
            indent=1, sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    if entry is None:
        print(f"::warning::no provider budget for this run ({refusal}); zero-call work only")
    else:
        print(
            f"reserved {entry['calls']:g} calls / {entry['tokens']:g} tokens in batch "
            f"{entry['batch']} for {args.repository} ({args.id})"
        )
    return 0


def _sealed_lanes(remote: str, repository: str, outcomes: dict[str, str]) -> list[str]:
    from repo_presenter.core.portfolio_matrix import PIPELINE_GOOD_STATES
    from repo_presenter.core.state.git_backend import GitStateBackend

    sealed = []
    for lane, outcome in sorted(outcomes.items()):
        if outcome != "success":
            continue
        try:
            with GitStateBackend(remote=remote, token=state_token(), lane=lane) as backend:
                record = backend.load(repository)
        except Exception as error:  # noqa: BLE001 -- unreadable reads as not sealed, never sealed
            print(f"::warning::Lane {lane} record unreadable ({type(error).__name__}); not counted sealed")
            continue
        if record is not None and str(record.state) in PIPELINE_GOOD_STATES:
            sealed.append(lane)
    return sealed


def _cmd_settle(args: Any) -> int:
    """Record this run's measured spend and outcomes in the durable ledger (success or failure)."""
    committed = committed_document(args.budget)
    workdir = Path(args.workdir)
    reserved = True
    try:
        state = json.loads((workdir / RESERVATION_FILENAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # The reserve step never ran (the facts job failed first): nothing was spendable, and the
        # failure is still a real attempt of the cell.
        reserved = False
        state = {"id": args.id, "reservation": None, "refusal": "the reserve step did not run",
                 "baseline_call_ids": [], "baseline_spent": None}
    measured_calls, measured_tokens = measure_new_calls(
        workdir, set(state.get("baseline_call_ids") or [])
    )
    # record_spend's own count in the local file is a second measure; the larger one is charged.
    try:
        local_calls, local_tokens = _spent(_load_document(args.budget))
    except BudgetExceededError:
        local_calls = local_tokens = 0.0
    baseline = state.get("baseline_spent")
    if isinstance(baseline, dict):
        base_calls, base_tokens = _num(baseline.get("calls")), _num(baseline.get("tokens"))
    else:
        base_calls, base_tokens = local_calls, local_tokens
    calls = max(float(measured_calls), local_calls - base_calls)
    tokens = max(float(measured_tokens), local_tokens - base_tokens)
    outcomes = {
        lane: value
        for lane, value in (item.split("=", 1) for item in args.outcome if "=" in item)
        if lane in ("R", "L") and value
    }
    if args.facts_result == "failure":
        # The facts job failed (an upstream that does not build, a toolchain error): every lane
        # this run was asked for failed with it, and that is an attempt like any other.
        for lane in [lane for lane in args.lanes.split(",") if lane in ("R", "L")]:
            if outcomes.get(lane) in (None, "", "skipped"):
                outcomes[lane] = "failure"
    source_revision = args.source_revision or upstream_revision(args.repository) or ""
    entry = {
        "id": state.get("id") or args.id,
        "repository": args.repository,
        "lanes": sorted(outcomes),
        "outcomes": outcomes,
        "sealed": _sealed_lanes(args.remote, args.repository, outcomes),
        "calls": calls,
        "tokens": tokens,
        "budget_refused": reserved and state.get("reservation") is None,
        "refusal": state.get("refusal"),
        "source_revision": source_revision,
        "code": code_fingerprint(),
        "main_sha": args.main_sha,
        "run_id": args.run_id,
        "run_url": args.run_url,
    }
    try:
        with ledger_store(args.remote, state_token()) as store:
            store.update(lambda current: settle(committed, current, entry))
    except Exception as error:  # noqa: BLE001
        print(f"::error::this run's spend could not be recorded durably: {type(error).__name__}: {error}")
        return 1
    print(
        f"settled {entry['id']}: {calls:g} provider calls, {tokens:g} tokens; outcomes "
        f"{outcomes}; sealed {entry['sealed'] or 'none'}"
    )
    return 0


def budget_summary_lines(document: dict[str, Any]) -> list[str]:
    calls, tokens = _spent(document)
    lines = [
        (
            f"envelope: {calls:g} / {_num(document.get('total_calls_cap')):g} calls, "
            f"{tokens:g} / {_num(document.get('total_tokens_cap')):g} tokens"
        )
    ]
    batches = document.get("batches") or []
    if batches:
        last = batches[-1]
        hosted = last.get("hosted") or {}
        lines.append(
            f"last batch {last.get('id')}: {_num(last.get('calls_spent')):g} / "
            f"{_num(last.get('calls_cap')):g} calls; hosted runs {hosted.get('runs', 0)}, sealed "
            f"{hosted.get('sealed', 0)}, in flight {hosted.get('in_flight', 0)}"
        )
    if "stop" in document:
        lines.append(f"STOPPED: {document['stop'].get('reason')}")
    return lines


def _cmd_status(args: Any) -> int:
    committed = committed_document(args.budget)
    document = effective_document(committed, read_ledger(args.remote, state_token()))
    if args.json:
        print(json.dumps(document, indent=1, sort_keys=True))
    else:
        print("\n".join(budget_summary_lines(document)))
    return 0


def reserve_cohort(
    committed: dict[str, Any], ledger: Any, runs: list[dict[str, Any]], *, id_prefix: str,
    now: datetime | None = None, meta: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Reserve every planned run of one scheduled fire, in plan order (pure). Returns the ledger
    and the runs, each with ``dispatch_id`` and either ``reservation`` or ``refusal``: a run the
    budget cannot fund is never dispatched (it would spend nothing and record nothing useful)."""
    ledger = copy.deepcopy(ledger) if isinstance(ledger, dict) else empty_ledger()
    planned = []
    for index, run in enumerate(runs, start=1):
        dispatch_id = f"{id_prefix}-{index}"
        ledger, entry, refusal = reserve(
            committed, ledger, reservation_id=dispatch_id, repository=run["repository"],
            lanes=list(run.get("lanes") or []), now=now, meta=meta,
        )
        planned.append({**run, "dispatch_id": dispatch_id, "reservation": entry, "refusal": refusal})
    return ledger, planned


def _cmd_reserve_cohort(args: Any) -> int:
    committed = committed_document(args.budget)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    runs = list(plan.get("runs") or [])
    result: dict[str, Any] = {"runs": []}

    def mutate(current: Any) -> dict[str, Any]:
        ledger, planned = reserve_cohort(
            committed, current, runs, id_prefix=args.id_prefix,
            meta={"run_id": args.run_id, "main_sha": args.main_sha, "via": "scheduled cohort"},
        )
        result["runs"] = planned
        return ledger

    try:
        with ledger_store(args.remote, state_token()) as store:
            ledger = store.update(mutate) if runs else store.read()[1] or empty_ledger()
    except Exception as error:  # noqa: BLE001 -- fail closed: nothing is dispatched unfunded
        ledger = empty_ledger()
        result["runs"] = [
            {**run, "dispatch_id": "", "reservation": None,
             "refusal": f"provider-spend ledger unavailable: {type(error).__name__}"}
            for run in runs
        ]
    document = effective_document(committed, ledger)
    result["budget"] = budget_summary_lines(document)
    result["recent"] = [
        e for e in ledger_entries(ledger, any_epoch=True)
        if e.get("kind") == "settle" and e.get("outcomes")
        and (_parse_iso(e.get("at")) or _now_utc()) > _now_utc() - timedelta(hours=args.recent_hours)
    ]
    Path(args.out).write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    funded = sum(1 for run in result["runs"] if run.get("reservation"))
    print(f"funded {funded} of {len(runs)} planned run(s)")
    return 0


def _cmd_release(args: Any) -> int:
    """Close a reservation whose run never started (a failed dispatch): charged zero."""
    committed = committed_document(args.budget)
    entry = {"id": args.id, "repository": args.repository, "lanes": [], "outcomes": {},
             "sealed": [], "calls": 0.0, "tokens": 0.0, "budget_refused": False,
             "refusal": args.reason, "run_id": args.run_id}
    with ledger_store(args.remote, state_token()) as store:
        store.update(lambda current: settle(committed, current, entry))
    print(f"released {args.id}: {args.reason}")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m repo_presenter.core.llm.budget")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("reserve", "settle", "status"):
        command = sub.add_parser(name)
        command.add_argument("--remote", default="origin")
        command.add_argument("--budget", type=Path, default=DEFAULT_BUDGET_PATH)
        if name == "status":
            command.add_argument("--json", action="store_true")
            continue
        command.add_argument("--id", required=True)
        command.add_argument("--repository", required=True)
        command.add_argument("--workdir", default=".present-work")
        command.add_argument("--run-id", default="")
        command.add_argument("--main-sha", default="")
        if name == "reserve":
            command.add_argument("--lanes", default="R,L")
        else:
            command.add_argument("--outcome", action="append", default=[])
            command.add_argument("--facts-result", default="")
            command.add_argument("--lanes", default="R,L")
            command.add_argument("--source-revision", default="")
            command.add_argument("--run-url", default="")
    cohort = sub.add_parser("reserve-cohort")
    cohort.add_argument("--remote", default="origin")
    cohort.add_argument("--budget", type=Path, default=DEFAULT_BUDGET_PATH)
    cohort.add_argument("--plan", required=True)
    cohort.add_argument("--out", required=True)
    cohort.add_argument("--id-prefix", required=True)
    cohort.add_argument("--run-id", default="")
    cohort.add_argument("--main-sha", default="")
    cohort.add_argument("--recent-hours", type=float, default=2.0)
    release = sub.add_parser("release")
    release.add_argument("--remote", default="origin")
    release.add_argument("--budget", type=Path, default=DEFAULT_BUDGET_PATH)
    release.add_argument("--id", required=True)
    release.add_argument("--repository", required=True)
    release.add_argument("--reason", required=True)
    release.add_argument("--run-id", default="")
    args = parser.parse_args(argv)
    handler = {"reserve": _cmd_reserve, "settle": _cmd_settle, "status": _cmd_status,
               "reserve-cohort": _cmd_reserve_cohort, "release": _cmd_release}
    return handler[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
