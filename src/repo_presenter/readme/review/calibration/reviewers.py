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

from pathlib import Path

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
from repo_presenter.readme.review.llm_review import review_with_model
from repo_presenter.readme.review.verdict import ReviewUnavailable


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
    )


def physical_calls(ledger_path: Path) -> int:
    """Requests actually sent, per the ledger file."""
    return sum(1 for record in load_records(ledger_path) if is_physical_attempt(record))


def _first_reply_flags(appended: list) -> tuple[bool | None, bool | None]:
    sent = [record for record in appended if is_physical_attempt(record)]
    if not sent or sent[0].outcome != "success":
        return None, None
    invalid = [record for record in appended if record.outcome == "response_invalid"]
    if not invalid:
        return True, True
    lines = invalid[0].rejection
    broken_json = any(
        line.startswith(("output is not a JSON object", "$")) for line in lines
    )
    return not broken_json, False


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

    def __call__(self, case: Case) -> ReviewOutcome:
        spent = physical_calls(self.ledger_path)
        if spent >= self.cap:
            raise BudgetExhausted(f"{spent} provider calls made; the cap is {self.cap}")
        ledger = Ledger(self.ledger_path, call_budget=self.cap - spent)
        if self.fresh_store_per_call:
            self.asked += 1
            self.store = CallStore(self.store_dir / f"ask{self.asked:04d}")
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
            )
        except ProviderCallBudgetError as error:
            raise BudgetExhausted(str(error)) from error
        except ReviewUnavailable as error:
            detail = f"{error.reason}: {'; '.join(error.errors)}"[:400]
        except JobError as error:
            detail = str(error)[:400]
        json_valid, contract_valid = _first_reply_flags(ledger.appended)
        calls = ledger.physical_calls_made
        if verdict is None or verdict.retryable:
            return ReviewOutcome(
                UNAVAILABLE,
                calls,
                json_valid,
                contract_valid,
                detail=detail or (verdict.fold.reason if verdict else ""),
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
            cleared=sum(1 for f in verdict.findings if f.status == "CLEARED"),
            model_served=verdict.model_served or "",
            detail=verdict.fold.reason,
        )
