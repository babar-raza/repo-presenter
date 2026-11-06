"""Reviewers for the calibration harness: two stubs that MUST fail the gate, an oracle that must
pass it, and the live adapter over ``review_with_model``.

The live adapter is the only code here that can reach a provider, and only through
``llm_review.review_with_model`` (hence ``core/llm/jobs.run_job``), so every attempt is a ledger
record. It enforces a hard cap on the physical calls in its ledger file: each review gets a fresh
``Ledger`` whose budget is the cap less what the file already holds, so a call over the cap is
refused before it is sent, and ``BudgetExhausted`` stops the run. Cache replays cost nothing; a
fresh ``store_dir`` per repeat is what bypasses the cache for a repeatability measurement.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import JobError, ProviderCallBudgetError
from repo_presenter.core.llm.fallback import ModelSelection
from repo_presenter.core.llm.jobs import CallStore, JobContext
from repo_presenter.core.llm.ledger import Ledger, is_physical_attempt, load_records
from repo_presenter.core.llm.prompts import PromptRegistry
from repo_presenter.readme.review.calibration.corpus import Case
from repo_presenter.readme.review.calibration.harness import (
    BudgetExhausted,
    ReviewOutcome,
    evidence_text,
)
from repo_presenter.readme.review.calibration.outcomes import (
    ACCEPT,
    REJECT,
    UNAVAILABLE,
)
from repo_presenter.readme.review.llm_review import JOB, review_with_model
from repo_presenter.readme.review.verdict import (
    REVIEWER_LOGIC_VERSION,
    ReviewUnavailable,
)


def always_accept(case: Case) -> ReviewOutcome:
    """The reviewer the mission calls broken: it accepts everything."""
    return ReviewOutcome(ACCEPT)


def always_reject(case: Case) -> ReviewOutcome:
    """The other broken reviewer: it rejects everything."""
    return ReviewOutcome(REJECT)


def oracle(case: Case) -> ReviewOutcome:
    """A reviewer that knows each case's expected verdict. It exists to prove the gate is
    passable by a correct reviewer; it measures nothing about a model."""
    return ReviewOutcome(
        case.expected,
        first_reply_json_valid=True,
        first_reply_contract_valid=True,
        evidence=case.targets,
        quotes=(evidence_text(case.defect_text),) if case.defect_text else (),
    )


def physical_calls(ledger_path: Path) -> int:
    """Requests actually sent, per the ledger file."""
    return sum(1 for record in load_records(ledger_path) if is_physical_attempt(record))


def _unit_flags(appended: list) -> tuple[int, int, int]:
    """``(first replies sent, schema-valid, contract-valid)`` over the review units in ``appended``.

    A sectionwise review makes one logical call per unit (``logical_call_id`` is the hash of the
    unit's first request). The first reply of a unit is valid when the job never recorded a rejection
    for it; it is schema-valid unless the first rejection is a JSON or schema error."""
    by_unit: dict[str, list] = {}
    for record in appended:
        by_unit.setdefault(record.logical_call_id, []).append(record)
    replies = json_valid = contract_valid = 0
    for records in by_unit.values():
        sent = [record for record in records if is_physical_attempt(record)]
        if not sent or sent[0].outcome != "success":
            continue
        replies += 1
        invalid = [record for record in records if record.outcome == "response_invalid"]
        if not invalid:
            json_valid += 1
            contract_valid += 1
            continue
        broken_json = any(
            line.startswith(("output is not a JSON object", "$"))
            for line in invalid[0].rejection
        )
        json_valid += not broken_json
    return replies, json_valid, contract_valid


def _tokens(appended: list) -> int:
    return sum(
        (record.prompt_tokens or 0) + (record.completion_tokens or 0)
        for record in appended
        if is_physical_attempt(record)
    )


def review_key(scope: str, case: Case, prompt_sha256: str, model: str) -> str:
    """The identity of one review in a run's journal: where it was asked (the store, or the fresh
    ``askNNNN`` store of a repeat), the case, the exact README, the prompt, the reviewer logic and the
    model. A change to any of them is a different review, never a journal replay."""
    readme = hashlib.sha256(case.readme.encode("utf-8")).hexdigest()
    return "/".join(
        (
            scope,
            case.case_id,
            readme[:16],
            prompt_sha256[:16],
            f"logic{REVIEWER_LOGIC_VERSION}",
            model,
        )
    )


class ReviewJournal:
    """Every completed review of a run, appended as one JSON line as soon as it is known.

    A resumed run (same ``--out`` and tag) takes a journaled review's outcome as it was recorded,
    first-reply flags and spent calls included, and sends nothing. Without it a resume replays each
    answered unit from the call store but re-asks a unit whose reply broke the contract twice (it was
    never stored), and loses the first-reply flags of everything it replays (iteration 4, section
    2.1). A review the budget interrupted is not journaled: its answered units replay from the store
    and only the units never answered are asked."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: dict[str, dict[str, Any]] = {}
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    self.entries[record["key"]] = record["outcome"]

    def keys(self) -> frozenset[str]:
        return frozenset(self.entries)

    def get(self, key: str) -> ReviewOutcome | None:
        stored = self.entries.get(key)
        if stored is None:
            return None
        fields = dict(stored)
        for name in ("blocking_kinds", "evidence", "quotes"):
            fields[name] = tuple(fields.get(name, ()))
        return ReviewOutcome(**fields)

    def put(self, key: str, outcome: ReviewOutcome) -> None:
        record = dataclasses.asdict(outcome)
        self.entries[key] = record
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"key": key, "outcome": record}, sort_keys=True) + "\n")


class LiveReviewer:
    def __init__(
        self,
        *,
        prompts: PromptRegistry,
        config: GatewayConfig,
        ledger_path: Path,
        store_dir: Path,
        cap: int,
        models: ModelSelection | None = None,
        fresh_store_per_call: bool = False,
        journal: ReviewJournal | None = None,
    ) -> None:
        self.prompts = prompts
        self.config = config
        self.ledger_path = ledger_path
        self.store_dir = store_dir
        self.store = CallStore(store_dir)
        self.fresh_store_per_call = fresh_store_per_call
        self.asked = 0
        self.cap = cap
        self.models = models
        self.journal = journal

    def _key(self, case: Case) -> str:
        loaded = self.prompts[JOB]
        route = loaded.manifest.model_route
        model = route if self.models is None else self.models.model_for(route)
        scope = self.store.directory.relative_to(self.store_dir.parent).as_posix()
        return review_key(scope, case, loaded.sha256, model)

    def __call__(self, case: Case) -> ReviewOutcome:
        if self.fresh_store_per_call:
            self.asked += 1
            self.store = CallStore(self.store_dir / f"ask{self.asked:04d}")
        if self.journal is not None:
            recorded = self.journal.get(self._key(case))
            if recorded is not None:
                return recorded
        outcome = self._review(case)
        if self.journal is not None:
            self.journal.put(self._key(case), outcome)
        return outcome

    def _review(self, case: Case) -> ReviewOutcome:
        spent = physical_calls(self.ledger_path)
        if spent >= self.cap:
            raise BudgetExhausted(f"{spent} provider calls made; the cap is {self.cap}")
        ledger = Ledger(self.ledger_path, call_budget=self.cap - spent)
        source = case.source
        context = JobContext(
            repository=source.repository,
            source_revision=source.facts.source_revision,
            models=self.models,
        )
        verdict = None
        detail = ""
        try:
            verdict = review_with_model(
                prompts=self.prompts,
                config=self.config,
                ledger=ledger,
                store=self.store,
                context=context,
                candidate_readme=case.readme,
                original_readme=source.original,
                facts=source.facts,
                plan=source.plan,
                dispositions=source.dispositions,
                validation=source.validation,
                rendered=source.rendered,
            )
        except ProviderCallBudgetError as error:
            raise BudgetExhausted(str(error)) from error
        except ReviewUnavailable as error:
            detail = f"{error.reason}: {'; '.join(error.errors)}"[:400]
        except JobError as error:
            detail = str(error)[:400]
        replies, json_ok, contract_ok = _unit_flags(ledger.appended)
        json_valid = (json_ok == replies) if replies else None
        contract_valid = (contract_ok == replies) if replies else None
        calls = ledger.physical_calls_made
        flags: dict[str, Any] = {
            "unit_replies": replies,
            "unit_json_valid": json_ok,
            "unit_contract_valid": contract_ok,
            "tokens": _tokens(ledger.appended),
            "units": len(verdict.unit_reviews) if verdict is not None else 0,
        }
        if verdict is None or verdict.retryable:
            return ReviewOutcome(
                UNAVAILABLE,
                calls,
                json_valid,
                contract_valid,
                detail=detail or (verdict.fold.reason if verdict else ""),
                **flags,
            )
        return ReviewOutcome(
            ACCEPT if verdict.verdict == "ACCEPT" else REJECT,
            calls,
            json_valid,
            contract_valid,
            blocking_kinds=tuple(f.claim_kind for f in verdict.blocking_findings),
            evidence=tuple(
                evidence_text(f.quote, f.message) for f in verdict.blocking_findings
            ),
            quotes=tuple(evidence_text(f.quote) for f in verdict.blocking_findings),
            cleared=sum(1 for f in verdict.findings if f.status == "CLEARED"),
            model_served=verdict.model_served or "",
            detail=verdict.fold.reason,
            **flags,
        )
