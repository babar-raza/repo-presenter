"""Stage S10: the independent LLM review of one candidate, as one governed ``run_job`` (plan D4-D8).

``review_with_model`` asks the ``independent_review`` job (a separate identity and, per the
manifest's route, a separate model from authoring) for a ``ReviewV1`` reply, judges the reply by the
Phase 1 contract (``reply.validate_review_reply``) as the job's own ``checks``, and folds it into a
``ReviewVerdict`` (``reply.review_from_reply``: clearances, then the one fold). Nothing here decides
a verdict.

Failure is closed. A reply that breaks the contract is re-asked once with the specific errors
(``run_job``'s one re-ask); a reply still invalid, or a provider that stays unreachable through the
bounded transport retries, is ``ReviewUnavailable``: retryable, never ACCEPT, never a silent skip.
The caller records it as a transient failure and seals nothing.

Provider calls per review: one when the first reply is valid, two when it needed the re-ask, none
when the identical request was answered before (the call store replays the accepted reply and the
verdict is rebuilt from it, byte for byte). Every attempt is a ledger record on the caller's
invocation; a transport retry of one attempt is its own counted call.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import OutputRejectedError
from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger, canonical_hash
from repo_presenter.core.llm.prompts import PromptRegistry
from repo_presenter.core.retry import RetryableOperationError
from repo_presenter.readme.review.findings import CLEARANCES_FOR_KIND, Finding
from repo_presenter.readme.review.packet import review_packet, review_schema
from repo_presenter.readme.review.reply import review_from_reply, validate_review_reply
from repo_presenter.readme.review.verdict import ReviewUnavailable, ReviewVerdict

JOB = "independent_review"
#: Re-reviews after a repair: a candidate that still blocks after this many repair rounds is BLOCKED.
MAX_REVIEW_REPAIR_ROUNDS = 2


def review_checks(
    output: dict[str, Any],
    *,
    candidate_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any],
) -> list[str]:
    """The job's ``checks``: the Phase 1 contract, quoted back to the model in the one re-ask."""
    return validate_review_reply(
        output, candidate_readme=candidate_readme, facts=facts, plan=plan
    )


def review_with_model(
    *,
    prompts: PromptRegistry,
    config: GatewayConfig,
    ledger: Ledger,
    store: CallStore,
    context: JobContext,
    candidate_readme: str,
    original_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any],
    dispositions: Mapping[str, Any],
    validation: Mapping[str, Any],
    deterministic_findings: Sequence[Finding] = (),
) -> ReviewVerdict:
    """The model-reviewed verdict for ``candidate_readme``; ``ReviewUnavailable`` when no valid
    review could be obtained."""
    loaded = prompts[JOB]
    packet = review_packet(
        repository=context.repository,
        candidate_readme=candidate_readme,
        original_readme=original_readme,
        facts=facts,
        plan=plan,
        dispositions=dispositions,
        validation=validation,
    )
    try:
        result = run_job(
            loaded,
            packet,
            config=config,
            facts=facts,
            ledger=ledger,
            store=store,
            context=context,
            call_schema=review_schema(loaded, plan),
            checks=partial(
                review_checks,
                candidate_readme=candidate_readme,
                facts=facts,
                plan=plan,
            ),
        )
    except OutputRejectedError as error:
        raise ReviewUnavailable(
            "the reviewer's reply broke the contract after the one re-ask", [str(error)]
        ) from error
    except RetryableOperationError as error:
        raise ReviewUnavailable(
            f"the reviewer could not be reached ({error})", [str(error)]
        ) from error
    model_served = result.model_served or store.record(result.request_sha256).get(
        "model_served"
    )
    if not model_served:
        raise ReviewUnavailable(
            "the provider did not report which model served the review", []
        )
    return review_from_reply(
        result.output,
        candidate_readme=candidate_readme,
        original_readme=original_readme,
        facts=facts,
        plan=plan,
        deterministic_findings=deterministic_findings,
        prompt_version=loaded.manifest.version,
        model_served=str(model_served),
        request_sha256=result.request_sha256,
        reply_sha256=canonical_hash(result.output),
    )


def blocked_predicate(verdict: ReviewVerdict) -> str:
    """What would unblock a candidate the reviewer rejected, exactly (plan D7): per blocking
    finding, the clearance that could disprove it or the fact that only a revision can."""
    if verdict.verdict == "ACCEPT":
        return ""
    parts: list[str] = []
    for finding in verdict.blocking_findings:
        label = finding.finding_id or finding.rule
        where = f" in {finding.section_id}" if finding.section_id else ""
        clearances = CLEARANCES_FOR_KIND.get(finding.claim_kind, ())
        if finding.source == "deterministic":
            needed = f"rule {finding.rule} no longer finds it ({finding.evidence or finding.message})"
        elif clearances:
            needed = (
                f"a revised candidate the reviewer no longer faults, or "
                f"{' / '.join(clearances)} proving its {finding.claim_kind} claim false"
            )
        else:
            needed = (
                f"a revised candidate the reviewer no longer faults (no clearance can disprove "
                f"a {finding.claim_kind} claim)"
            )
        parts.append(f"{label} [{finding.claim_kind}]{where} blocks until {needed}")
    if not parts:
        parts.append(f"{verdict.fold.reason or 'the review did not accept'}")
    return "; ".join(parts)
