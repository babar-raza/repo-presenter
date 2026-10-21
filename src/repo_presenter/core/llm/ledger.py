"""The call ledger: one record per provider attempt or cache reuse, appended as JSON lines.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``core/llm/ledger.py`` per migration/reuse-manifest.yaml ("readme/composition/" entry).

Provider calls reconcile with this file: every physical attempt is recorded with its job, prompt
manifest hash, model route, the model the gateway actually served, request and response hashes,
token counts, and outcome; a reuse of a stored output is recorded as ``cache_reuse`` with zero
provider calls, which is how a no-op rerun proves it called nothing. Content is never stored here,
only hashes and counts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import MISSING, asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any, Literal

from repo_presenter.core.errors import ProviderCallBudgetError

CallDisposition = Literal["provider_call", "cache_reuse", "cache_stale"]
CallOutcome = Literal[
    "success",
    "http_error",
    "timeout",
    "connection_error",
    "response_invalid",
    "cache_reuse",
    "cache_stale",
]
LEDGER_FILENAME = "calls.jsonl"
# The most provider calls one process may make: one `present` invocation. Ported from the old
# repository's own calibration (its own measured clean full draws ran 10-33 calls); not
# re-calibrated here since this repository has made no provider calls of its own yet.
PROVIDER_CALL_BUDGET = 100


@dataclass(frozen=True)
class CallRecord:
    """One provider attempt or one explicit reuse of a stored output."""

    call_id: str
    logical_call_id: str
    repository: str
    source_revision: str
    stage: str
    job: str
    prompt_sha256: str
    model_route: str
    model_served: str | None
    attempt: int
    disposition: CallDisposition
    started_at: str
    finished_at: str
    latency_ms: int
    outcome: CallOutcome
    http_status: int | None
    request_sha256: str
    response_sha256: str | None
    provider_request_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    error_class: str | None
    # Why the output was rejected, verbatim from the job's own checks.
    rejection: tuple[str, ...] = ()
    # The manifest's own sampling contract for this logical call, carried on every record the same
    # way model_route already is. ``None`` only for a ledger sealed before this field existed.
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: str | None = None
    # Whether this record's own accepted output came from the logical call's second physical
    # attempt (the one automatic model re-ask every job allows) rather than its first.
    derived_via_reask: bool | None = None
    # The model this call's request named (core/llm/fallback.py): the route's primary, or the
    # fallback the run chose for it. Part of the request hash.
    effective_model: str | None = None
    schema_version: int = 1
    # The invocation (one ``present`` process) that appended this record, so a no-op proof counts
    # the provider calls of exactly one invocation out of a ledger several invocations share.
    invocation_id: str | None = None
    # Set only on a line sealed into a bundle's ``calls.jsonl`` for audit: a record of an attempt
    # the sealed composition did not consume, kept with the reason so a rejected or abandoned call
    # never vanishes from the ledger. Never written by a live run.
    retained_reason: str | None = None

    def to_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class LedgerSummary:
    provider_calls: int
    cache_reuses: int
    calls_by_job: dict[str, int]
    total_tokens: int | None


def is_physical_attempt(record: CallRecord) -> bool:
    """Whether ``record`` is a request actually sent to the gateway.

    ``response_invalid`` marks an earlier attempt's reply as rejected and sends nothing, so it is
    never a provider call, even though its disposition says so.
    """
    return record.disposition == "provider_call" and record.outcome != "response_invalid"


def canonical_hash(value: Any) -> str:
    """SHA-256 of a JSON-serialisable value in its canonical form."""
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Ledger:
    """Append-only accounting for one transaction's provider calls."""

    def __init__(
        self,
        path: Path,
        invocation_id: str | None = None,
        call_budget: int = PROVIDER_CALL_BUDGET,
    ) -> None:
        self.path = path
        self.invocation_id = invocation_id
        self.call_budget = call_budget
        self.appended: list[CallRecord] = []

    def append(self, record: CallRecord) -> None:
        if self.invocation_id is not None and record.invocation_id is None:
            record = replace(record, invocation_id=self.invocation_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(record.to_line() + "\n")
        self.appended.append(record)

    @property
    def provider_calls_made(self) -> int:
        """Provider calls this process made, across every job of the transaction."""
        return sum(1 for record in self.appended if record.disposition == "provider_call")

    @property
    def physical_calls_made(self) -> int:
        """Requests actually sent by this process: ``provider_calls_made`` less the
        ``response_invalid`` markers, which record a rejected reply and send nothing."""
        return sum(1 for record in self.appended if is_physical_attempt(record))

    def reserve_provider_call(self) -> None:
        """Refuse a physical provider call once this process has spent its budget.

        Called before the request is sent, so the refused call never reaches the gateway.
        """
        if self.physical_calls_made >= self.call_budget:
            raise ProviderCallBudgetError(
                f"provider-call budget of {self.call_budget} reached in this invocation; "
                "no further calls are made and the run stops"
            )

    @property
    def consumed_calls(self) -> frozenset[str]:
        """The logical calls this run's composition consumed, made or reused."""
        return frozenset(record.logical_call_id for record in self.appended)

    def records(self) -> list[CallRecord]:
        return load_records(self.path)

    def summary(self) -> LedgerSummary:
        return summarize(self.records())


def load_records(path: Path) -> list[CallRecord]:
    """Every record in the ledger, in order; a malformed or duplicated line is a defect."""
    if not path.is_file():
        return []
    return parse_records(path.read_text(encoding="utf-8"), str(path))


def parse_records(text: str, label: str) -> list[CallRecord]:
    """The records in ledger ``text``; ``label`` names the source in a defect message."""
    required = {field.name for field in fields(CallRecord) if field.default is MISSING}
    optional = {field.name for field in fields(CallRecord)} - required
    records: list[CallRecord] = []
    seen: set[str] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not required <= set(payload) or not set(payload) <= required | optional:
            raise ValueError(f"{label}:{number}: ledger record fields do not match CallRecord")
        if isinstance(payload.get("rejection"), list):
            payload["rejection"] = tuple(payload["rejection"])
        record = CallRecord(**payload)
        if record.call_id in seen:
            raise ValueError(f"{label}:{number}: duplicate call ID {record.call_id}")
        seen.add(record.call_id)
        records.append(record)
    return records


def summarize(records: list[CallRecord]) -> LedgerSummary:
    provider = [record for record in records if record.disposition == "provider_call"]
    by_job: dict[str, int] = {}
    for record in provider:
        by_job[record.job] = by_job.get(record.job, 0) + 1
    tokens_known = all(record.total_tokens is not None for record in provider)
    return LedgerSummary(
        provider_calls=len(provider),
        cache_reuses=sum(1 for record in records if record.disposition == "cache_reuse"),
        calls_by_job=dict(sorted(by_job.items())),
        total_tokens=sum(record.total_tokens or 0 for record in provider) if tokens_known else None,
    )
