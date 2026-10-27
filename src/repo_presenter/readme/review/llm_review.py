"""Stage S10: the independent LLM review of one candidate, one bounded unit per call (plan D4-D8).

``review_with_model`` splits the candidate into review units (``sectionwise.plan_units``: the
author-written text of one section or a small group; nothing the renderer printed), asks the
``independent_review`` job (its own job id, prompt and ledger attribution; the owner chose a single
model for the whole system, so it shares authoring's model) about each unit as one governed
``run_job`` with a packet of at most about 15,000 tokens, judges each reply by the Phase 1 contract
(``reply.validate_review_reply``, scoped to the unit) as the job's own ``checks``, merges the replies
into one (identical findings folded, ids renumbered) and folds that into a ``ReviewVerdict``
(``reply.review_from_reply``: clearances, then the one fold). Nothing here decides a verdict.

Why units: iteration 2 asked one question over a ~70,000-token whole-document packet and the model
accepted 27 of 41 defective candidates, with 87 percent of its findings aimed at text the renderer
printed. A unit holds no such text and a fraction of the evidence.

Failure is closed. A unit reply that breaks the contract is re-asked once with the specific errors
(``run_job``'s one re-ask); one still invalid, or a provider that stays unreachable through the
bounded transport retries, leaves that unit unavailable. A review with an unavailable unit is
``ReviewUnavailable`` (retryable, never ACCEPT, never a silent skip) unless another unit's blocking
finding already rejects the candidate; the unit is then recorded as unavailable in the verdict. The
caller records it as a transient failure and seals nothing.

Provider calls per review: one per unit when every first reply is valid, two for a unit that needed
the re-ask, none when the identical request was answered before (the call store replays the accepted
reply and the verdict is rebuilt from it, byte for byte). Every attempt is a ledger record on the
caller's invocation; a transport retry of one attempt is its own counted call.
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
from repo_presenter.readme.review.calibration_status import load_calibration
from repo_presenter.readme.review.findings import CLEARANCES_FOR_KIND, Finding
from repo_presenter.readme.review.reply import (
    MAX_FINDINGS,
    ReviewScope,
    merge_repeated_findings,
    resolve_cited_lines,
    review_from_reply,
    validate_review_reply,
)
from repo_presenter.readme.review.sectionwise import (
    ReviewUnit,
    plan_units,
    unit_packet,
    unit_schema,
)
from repo_presenter.readme.review.verdict import (
    INSUFFICIENT_EVIDENCE,
    MODEL_ACCEPT,
    REJECT_VERDICTS,
    REVIEWER_LOGIC_VERSION,
    ReviewUnavailable,
    ReviewVerdict,
)

JOB = "independent_review"
#: Re-reviews after a repair: a candidate that still blocks after this many repair rounds is BLOCKED.
MAX_REVIEW_REPAIR_ROUNDS = 2
#: Beside the call store: the requests that got a blocking verdict (the no-re-roll invariant).
BLOCKED_FILENAME = "blocked_requests.json"
#: Finding ids are ``F`` and two digits, so a merged reply holds at most this many findings.
MAX_MERGED_FINDINGS = 99


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


def _record_blocks(
    store: CallStore,
    blocks: Mapping[str, Sequence[str]],
    candidate_readme: str,
    verdict: str,
) -> None:
    """Record each request that got a blocking finding, with the candidate bytes it judged."""
    if not blocks:
        return
    requests = _blocked(store)
    for request_sha256, blocking in blocks.items():
        requests[request_sha256] = {
            "candidate_sha256": hashlib.sha256(
                candidate_readme.encode("utf-8")
            ).hexdigest(),
            "verdict": verdict,
            "blocking": list(blocking),
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
    scope: ReviewScope | None = None,
) -> list[str]:
    """The job's ``checks``: the cited lines resolved to the candidate's own text, identical findings
    merged, then the Phase 1 contract (scoped to the unit); the errors are quoted back to the model
    in the one re-ask."""
    cited = resolve_cited_lines(output, candidate_readme, scope)
    if cited:
        return cited
    merge_repeated_findings(output)
    return validate_review_reply(
        output, candidate_readme=candidate_readme, facts=facts, plan=plan, scope=scope
    )


def _merged_verdict(verdicts: Sequence[str]) -> str:
    """The one model verdict a set of unit verdicts stands for: an insufficient unit blocks the
    whole review (retryably), else the first rejection, else ACCEPT."""
    if INSUFFICIENT_EVIDENCE in verdicts:
        return INSUFFICIENT_EVIDENCE
    for verdict in verdicts:
        if verdict in REJECT_VERDICTS:
            return verdict
    return MODEL_ACCEPT


def _merged_reply(
    replies: Sequence[tuple[ReviewUnit, dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, str]]:
    """The units' replies as one reply with findings renumbered F01..., and which unit each id
    came from. Ids are renumbered before any clearance is issued: a clearance binds the finding id."""
    findings: list[dict[str, Any]] = []
    origin: dict[str, str] = {}
    preserve: list[str] = []
    for unit, reply in replies:
        for raw in reply["findings"]:
            merged = dict(raw)
            merged["id"] = f"F{len(findings) + 1:02d}"
            findings.append(merged)
            origin[merged["id"]] = unit.label
        preserve.extend(
            item for item in reply.get("preserve", []) if item not in preserve
        )
    merged_reply: dict[str, Any] = {
        "verdict": _merged_verdict([reply["verdict"] for _, reply in replies]),
        "findings": findings,
        "preserve": preserve,
    }
    merge_repeated_findings(merged_reply)
    kept = {f["id"] for f in merged_reply["findings"]}
    return merged_reply, {fid: unit for fid, unit in origin.items() if fid in kept}


def _unit_record(
    unit: ReviewUnit,
    request_sha256: str,
    *,
    reply: Mapping[str, Any] | None = None,
    reply_sha256: str | None = None,
    reason: str = "",
) -> dict[str, Any]:
    return {
        "unit": unit.label,
        "sections": list(unit.sections),
        "lines": [unit.lines[0], unit.lines[-1], len(unit.lines)],
        "request_sha256": request_sha256,
        "reply_sha256": reply_sha256,
        "model_verdict": None if reply is None else reply["verdict"],
        "findings": None if reply is None else len(reply["findings"]),
        "status": "reviewed" if reply is not None else "unavailable",
        "reason": reason,
    }


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
    rendered: bool = True,
) -> ReviewVerdict:
    """The model-reviewed verdict for ``candidate_readme``; ``ReviewUnavailable`` when no valid
    review could be obtained. ``dispositions`` and ``validation`` are the deterministic stage's
    evidence: a review unit is not sent them (they decide nothing the reviewer may relitigate).
    ``rendered`` says the candidate was printed by the renderer (Lane R, the default); a corrected
    live README (Lane L) passes ``False``, and none of its text is withheld as renderer-owned."""
    loaded = prompts[JOB]
    units = plan_units(candidate_readme, rendered=rendered)
    if not units:
        raise ReviewUnavailable(
            "the candidate has no author-written text to review (every line is renderer-printed)",
            [],
        )
    model = effective_model(loaded, context)
    replies: list[tuple[ReviewUnit, dict[str, Any]]] = []
    records: list[dict[str, Any]] = []
    request_hashes: list[str] = []
    request_of: dict[str, str] = {}
    unavailable: list[tuple[ReviewUnit, ReviewUnavailable]] = []
    model_served: str | None = None
    for unit in units:
        packet = unit_packet(
            unit,
            units=units,
            repository=context.repository,
            candidate_readme=candidate_readme,
            original_readme=original_readme,
            facts=facts,
            plan=plan,
        )
        schema = unit_schema(loaded, unit)
        request_sha256 = request_hash(loaded, packet, schema, model=model)
        request_hashes.append(request_sha256)
        request_of[unit.label] = request_sha256
        _refuse_reroll(store, request_sha256)
        scope = ReviewScope(frozenset(unit.sections), frozenset(unit.lines))
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
                    scope=scope,
                ),
            )
            served = result.model_served or store.record(result.request_sha256).get(
                "model_served"
            )
            if not served:
                raise ReviewUnavailable(
                    "the provider did not report which model served the review", []
                )
        except OutputRejectedError as error:
            problem = ReviewUnavailable(
                f"unit {unit.label} ({', '.join(unit.sections)}): the reviewer's reply broke the "
                "contract after the one re-ask",
                [str(error)],
            )
        except RetryableOperationError as error:
            problem = ReviewUnavailable(
                f"unit {unit.label} ({', '.join(unit.sections)}): the reviewer could not be "
                f"reached ({error})",
                [str(error)],
            )
        except ReviewUnavailable as error:
            problem = error
        else:
            model_served = model_served or str(served)
            replies.append((unit, result.output))
            records.append(
                _unit_record(
                    unit,
                    result.request_sha256,
                    reply=result.output,
                    reply_sha256=canonical_hash(result.output),
                )
            )
            continue
        unavailable.append((unit, problem))
        records.append(_unit_record(unit, request_sha256, reason=problem.reason))
    if not replies:
        _, first = unavailable[0]
        raise ReviewUnavailable(
            first.reason, [e for _, p in unavailable for e in p.errors]
        )
    merged, origin = _merged_reply(replies)
    verdict = review_from_reply(
        merged,
        candidate_readme=candidate_readme,
        original_readme=original_readme,
        facts=facts,
        plan=plan,
        deterministic_findings=deterministic_findings,
        prompt_version=loaded.manifest.version,
        model_served=model_served or "",
        request_sha256=hashlib.sha256(
            "\n".join(request_hashes).encode("utf-8")
        ).hexdigest(),
        reply_sha256=canonical_hash(merged),
        max_findings=min(MAX_FINDINGS * len(units), MAX_MERGED_FINDINGS),
        calibration_status=load_calibration().status,
        unit_reviews=records,
    )
    if unavailable and verdict.verdict == "ACCEPT":
        raise ReviewUnavailable(
            "; ".join(problem.reason for _, problem in unavailable),
            [error for _, problem in unavailable for error in problem.errors],
        )
    blocks: dict[str, list[str]] = {}
    for finding in verdict.blocking_findings:
        unit_label = origin.get(finding.finding_id)
        if unit_label is not None:
            blocks.setdefault(request_of[unit_label], []).append(finding.finding_id)
    _record_blocks(store, blocks, candidate_readme, verdict.verdict)
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
