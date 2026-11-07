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

import json
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


def record_spend(budget_path: Path, calls: int, tokens: int) -> None:
    """Record a ``PRODUCT`` call that actually succeeded: add ``calls``/``tokens`` to the
    program-wide ``spent`` totals and to the currently open batch's own running
    ``calls_spent``/``tokens_spent`` totals (see module docstring for what "open" means), then
    write the file back whole.

    Called only after the call it accounts for has already happened -- it never itself decides
    whether a call may proceed; that is :func:`check_budget`'s job, always called first.
    """
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
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    budget_path.write_text(text, encoding="utf-8")
