"""Stage S10: the independent LLM review of one candidate, as one governed ``run_job`` (plan D4-D8).

``review_with_model`` asks the ``independent_review`` job (its own job id, prompt and ledger
attribution; the owner chose a single model for the whole system, so it shares authoring's model) for a ``ReviewV1`` reply, judges the reply by the
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

import hashlib
import json
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import OutputRejectedError
from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.llm.jobs import (
    CallStore,
    JobContext,
    effective_model,
    request_hash,
    run_job,
)
from repo_presenter.core.llm.ledger import Ledger, canonical_hash
from repo_presenter.core.llm.prompts import PromptRegistry
from repo_presenter.core.retry import RetryableOperationError
from repo_presenter.readme.review.findings import CLEARANCES_FOR_KIND, Finding
from repo_presenter.readme.review.packet import review_packet, review_schema
from repo_presenter.readme.review.reply import (
    resolve_cited_lines,
    review_from_reply,
    validate_review_reply,
)
from repo_presenter.readme.review.verdict import (
    REVIEWER_LOGIC_VERSION,
    ReviewUnavailable,
    ReviewVerdict,
)

JOB = "independent_review"
#: Re-reviews after a repair: a candidate that still blocks after this many repair rounds is BLOCKED.
MAX_REVIEW_REPAIR_ROUNDS = 2
#: Beside the call store: the requests that got a blocking verdict (the no-re-roll invariant).
BLOCKED_FILENAME = "blocked_requests.json"


class RerollRefused(RuntimeError):
    """A fresh review of a request that already has a blocking verdict was asked for. The only
    second look at identical bytes is the call store's replay; measured stability of a fresh review
    is low, so resampling until ACCEPT would be a quiet demotion of the blocking verdict."""


def _blocked(store: CallStore) -> dict[str, Any]:
    path = store.directory / BLOCKED_FILENAME
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("reviewer_logic_version") != REVIEWER_LOGIC_VERSION:
        return {}  # another reviewer's blocks are not this one's
    requests = document.get("requests")
    return requests if isinstance(requests, dict) else {}


def _refuse_reroll(store: CallStore, request_sha256: str) -> None:
    """Raise when ``request_sha256`` has a blocking verdict and the store would not replay it."""
    if request_sha256 in _blocked(store) and store.get(request_sha256) is None:
        raise RerollRefused(
            f"request {request_sha256[:12]} already has a blocking verdict and its stored reply "
            "is gone: a fresh review of the same bytes is refused, never resampled; replay the "
            "stored reply or revise the candidate"
        )


def _record_block(
    store: CallStore, request_sha256: str, candidate_readme: str, verdict: ReviewVerdict
) -> None:
    if verdict.verdict != "REJECT" or verdict.retryable:
        return
    requests = _blocked(store)
    requests[request_sha256] = {
        "candidate_sha256": hashlib.sha256(
            candidate_readme.encode("utf-8")
        ).hexdigest(),
        "verdict": verdict.verdict,
        "blocking": [f.finding_id or f.rule for f in verdict.blocking_findings],
    }
    document = {"reviewer_logic_version": REVIEWER_LOGIC_VERSION, "requests": requests}
    store.directory.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (store.directory / BLOCKED_FILENAME).write_bytes(text.encode("utf-8"))


def review_checks(
    output: dict[str, Any],
    *,
    candidate_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any],
) -> list[str]:
    """The job's ``checks``: the cited lines resolved to the candidate's own text, then the Phase 1
    contract; the errors are quoted back to the model in the one re-ask."""
    cited = resolve_cited_lines(output, candidate_readme)
    if cited:
        return cited
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
    schema = review_schema(loaded, plan)
    _refuse_reroll(
        store,
        request_hash(loaded, packet, schema, model=effective_model(loaded, context)),
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
            call_schema=schema,
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
    verdict = review_from_reply(
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
    _record_block(store, result.request_sha256, candidate_readme, verdict)
    return verdict


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
