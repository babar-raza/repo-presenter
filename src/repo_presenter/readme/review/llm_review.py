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

TC-024 (seal-path switch): every unit record now carries an ``"m8"`` field -- TC-023's narrow prose
judge's (``readme.review.prose_judge``) recorded verdict for that unit, additive and backward
compatible (a record read back from a seal made before this card simply has none, read the same as
``M8_NOT_RUN``). Nothing in this module makes the real M8 provider call yet (that calibration is
separately budgeted, owner ruling R26 -- see ``prose_judge``'s own module docstring): every record
this module writes carries ``M8_NOT_RUN`` until a future card wires a real draw. ``m8_blocking_units``
is the one place a caller (``present.py``, ``recertify.py``, ``core.state.bundle_store``) reads
whether M8 ever recorded an actual objection for a unit; it is never anything other than empty while
no real M8 call has been made, by construction.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
from repo_presenter.readme.review.scope import authored_table_lines, maintainer_lines
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
#: TC-023's narrow prose judge (``readme.review.prose_judge``) has not made a real provider call
#: for this unit (the only status every record this module writes carries today -- see the module
#: docstring). Read as "no M8 objection", exactly like an absent ``"m8"`` key on a record sealed
#: before this card existed.
M8_NOT_RUN = "not_run"
#: A future real M8 call classified this unit "none"/cleared a pairwise or paraphrase check: no
#: objection, same as ``M8_NOT_RUN`` for gating purposes, but recorded as an actual, made call.
M8_OK = "ok"
#: A future real M8 call found an actual defect (a classification other than "none", or a failed
#: pairwise/paraphrase check): blocks exactly like the old reviewer's own REJECT did.
M8_REJECT = "reject"
#: Three independent draws disagreed with no two-of-three majority (``prose_judge.INCONCLUSIVE``):
#: never silently resolved to any one of them -- blocks, the same as ``INSUFFICIENT_EVIDENCE``.
M8_INCONCLUSIVE = "inconclusive"
#: Every status ``m8_blocking_units`` reads as "no objection" -- the only two that may appear on a
#: unit this module reviews until a future card wires a real M8 provider call.
M8_PASSING_STATUSES = frozenset({M8_NOT_RUN, M8_OK})
#: Re-reviews after a repair: a candidate that still blocks after this many repair rounds is BLOCKED.
#: Raised 2 -> 4, 2026-10-30 (measured live, aspose-cells-foss, Rust and Cpp): each round repairs
#: whichever findings its own fingerprint bucket has not already tried, so a REAL, still-
#: unrepaired finding can keep losing its turn to an earlier one already marked unrepairable in
#: the same bucket (Rust's RUST_LANE_R_F01_F02_F03_ROOT_CAUSED: an enterprise-edition sentence
#: went two full hosted runs without ever once reaching a repair attempt), and halving the S4
#: batch size to fix a separate convergence gap means a repository's real defects are now more
#: likely to span multiple reconciliation batches, each needing its own repair call within the
#: same round budget. More rounds never costs a candidate that already passes; it only gives a
#: real, still-queued finding more chances before the candidate gives up on it.
MAX_REVIEW_REPAIR_ROUNDS = 4
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


#: The out-of-scope contract error a Lane L finding earns when every line it cites is live-README text
#: the corrections did not touch (see :func:`edit_scope`).
UNCHANGED_TEXT_ERROR = (
    "lines {lines} are unchanged live-README text, outside what this review judges; a finding must "
    "cite at least one changed line (see review_scope.lane_l.changed_lines) or concern how a "
    "change interacts with its surroundings - cite the changed line"
)
LANE_L_INSTRUCTION = (
    "This is a Lane L review: the candidate is the maintainers' own live README plus minimal "
    "evidenced edits. You are asked to judge THE EDITS: the lines listed in changed_lines, and "
    "whether each edit contradicts, or leaves incoherent, the text around it. Every other line is "
    "unchanged maintainer text shown only as context; defects that already existed in it are "
    "recorded elsewhere (residuals) and are not this review's question. A finding must cite at "
    "least one changed line (a span may extend into neighbouring unchanged lines when the edit "
    "interacts with them); a finding that cites only unchanged lines is a contract error. A "
    "unit with no changed lines has nothing to fault: return ACCEPT unless an edit elsewhere "
    "contradicts it, which you cite on the changed line."
)


def lane_l_changed_lines(candidate_readme: str, original_readme: str) -> frozenset[int]:
    """The 1-based candidate lines a Lane L correction wrote: the candidate rows that are not
    in the original, in order (``difflib`` over whole lines). A pure deletion changes no candidate
    row, so the rows on either side of it count, because the edit's effect is on its surroundings."""
    new = candidate_readme.splitlines()
    old = original_readme.splitlines()
    changed: set[int] = set()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            changed.update(range(j1 + 1, j2 + 1))
        elif tag == "delete":
            changed.update(n for n in (j1, j1 + 1) if 1 <= n <= len(new))
    return frozenset(changed)


def edit_scope(
    *,
    rendered: bool,
    validation: Mapping[str, Any] | None,
    candidate_readme: str,
    original_readme: str,
) -> frozenset[int] | None:
    """The changed candidate lines when this review is edit-scoped, else ``None``.

    Edit-scoped only for a real Lane L correction run (``rendered=False`` and the holdouts document
    that ``lane_l_review.review_correction`` passes as ``validation`` names ``lane == "L"``) whose
    final README differs from the live one. Lane R, the calibration harness and any caller that
    does not pass the Lane L holdouts are unchanged byte for byte."""
    if rendered or not isinstance(validation, Mapping) or validation.get("lane") != "L":
        return None
    if candidate_readme == original_readme:
        return None
    return lane_l_changed_lines(candidate_readme, original_readme)


def _lane_l_scope(
    unit: ReviewUnit, changed: frozenset[int], residuals: Sequence[Any]
) -> dict[str, Any]:
    return {
        "instruction": LANE_L_INSTRUCTION,
        "changed_lines": sorted(n for n in unit.lines if n in changed),
        "residuals_already_recorded": [
            str(row.get("reason") or row.get("summary") or row.get("text") or row)[:300]
            if isinstance(row, Mapping)
            else str(row)[:300]
            for row in residuals
        ][:20],
    }


def unchanged_text_errors(
    output: Mapping[str, Any], *, changed: frozenset[int], unit_lines: frozenset[int]
) -> list[str]:
    """Contract errors for findings that cite specific lines, all of them live-README text the
    corrections did not touch. An omission, an absence, or a finding that cites no line is about
    something absent and is not subject to this rule. Quoted back to the model in the one re-ask,
    exactly like every other contract error; nothing is demoted silently."""
    errors: list[str] = []
    for finding in output.get("findings", []) or []:
        if not isinstance(finding, Mapping):
            continue
        if finding.get("claim_kind") in ("omission", "absence"):
            continue
        lines = [n for n in finding.get("lines") or [] if isinstance(n, int)]
        if not lines:
            continue
        first, last = min(lines), max(lines)
        span = [n for n in range(first, last + 1) if n in unit_lines]
        if span and not any(n in changed for n in span):
            where = f"{first}-{last}" if first != last else str(first)
            errors.append(f"finding {finding.get('id', '?')}: " + UNCHANGED_TEXT_ERROR.format(lines=where))
    return errors


def review_checks(
    output: dict[str, Any],
    *,
    candidate_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any],
    scope: ReviewScope | None = None,
    changed: frozenset[int] | None = None,
) -> list[str]:
    """The job's ``checks``: the cited lines resolved to the candidate's own text, identical findings
    merged, then the Phase 1 contract (scoped to the unit); the errors are quoted back to the model
    in the one re-ask. ``changed`` (Lane L edit scope only, see :func:`edit_scope`) adds the rule
    that a finding must cite at least one changed line."""
    cited = resolve_cited_lines(output, candidate_readme, scope)
    if cited:
        return cited
    if changed is not None and scope is not None:
        unchanged = unchanged_text_errors(output, changed=changed, unit_lines=scope.lines)
        if unchanged:
            return unchanged
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


def _m8_record(
    status: str = M8_NOT_RUN, *, shape: str | None = None, verdict: Any = None
) -> dict[str, Any]:
    """TC-023's per-unit record (TC-024 part a): ``status`` is one of ``M8_NOT_RUN``/``M8_OK``
    (no objection), ``M8_REJECT``/``M8_INCONCLUSIVE`` (blocks -- see ``m8_blocking_units``).
    ``shape`` names which of the three prompt shapes (``readme.review.prose_judge.PROMPT_SHAPES``)
    produced it, and ``verdict`` is that shape's own raw value (a category, or a bool) -- both
    ``None`` while nothing was asked (the only case this module itself ever produces)."""
    return {"status": status, "shape": shape, "verdict": verdict}


def _unit_record(
    unit: ReviewUnit,
    request_sha256: str,
    *,
    reply: Mapping[str, Any] | None = None,
    reply_sha256: str | None = None,
    reason: str = "",
    m8: Mapping[str, Any] | None = None,
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
        "m8": dict(m8) if m8 is not None else _m8_record(),
    }


def m8_blocking_units(unit_reviews: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """TC-013/TC-024's M8 gate (part b): the label of every unit (in order, de-duplicated) whose
    recorded ``m8`` status is an actual objection (``M8_REJECT``/``M8_INCONCLUSIVE``) -- never one
    whose status is absent, ``M8_NOT_RUN`` or ``M8_OK``. ``()`` is the ordinary case until a future
    card wires a real M8 provider call: this module never writes anything else today (see the
    module docstring); a caller treats a non-empty result exactly like the old reviewer's own
    REJECT -- blocking, never silently overruled (non-negotiable 5)."""
    blocked: list[str] = []
    for record in unit_reviews:
        if not isinstance(record, Mapping):
            continue
        m8 = record.get("m8")
        if not isinstance(m8, Mapping):
            continue
        if m8.get("status") not in M8_PASSING_STATUSES:
            label = str(record.get("unit", "?"))
            if label not in blocked:
                blocked.append(label)
    return tuple(blocked)


@dataclass(frozen=True)
class PlannedRequest:
    """One review unit's request, exactly as ``review_with_model`` would send it."""

    unit: ReviewUnit
    packet: dict[str, Any]
    schema: dict[str, Any]
    request_sha256: str


def planned_requests(
    *,
    prompts: PromptRegistry,
    context: JobContext,
    candidate_readme: str,
    original_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any],
    dispositions: Mapping[str, Any],
    rendered: bool = True,
    validation: Mapping[str, Any] | None = None,
) -> tuple[tuple[ReviewUnit, ...], frozenset[int], tuple[PlannedRequest, ...]]:
    """The review units of ``candidate_readme``, its attributed maintainer lines, and each unit's
    packet, call schema and request hash. No call is made: this is the part of
    ``review_with_model`` that decides WHAT is asked, so a dry run counts exactly the requests a
    live review would send (``calibration/estimate.py``)."""
    loaded = prompts[JOB]
    authored = authored_table_lines(candidate_readme, facts) if rendered else frozenset()
    units = plan_units(candidate_readme, rendered=rendered, authored=authored)
    attributed = (
        maintainer_lines(candidate_readme, facts, dispositions) if rendered else frozenset()
    )
    model = effective_model(loaded, context)
    changed = edit_scope(
        rendered=rendered, validation=validation,
        candidate_readme=candidate_readme, original_readme=original_readme,
    )
    residuals = list((validation or {}).get("residuals") or []) if changed is not None else []
    requests = []
    for unit in units:
        packet = unit_packet(
            unit,
            units=units,
            repository=context.repository,
            candidate_readme=candidate_readme,
            original_readme=original_readme,
            facts=facts,
            plan=plan,
            maintainer_lines=attributed,
        )
        if changed is not None:
            packet["review_scope"] = {
                **packet["review_scope"], "lane_l": _lane_l_scope(unit, changed, residuals),
            }
        schema = unit_schema(loaded, unit)
        requests.append(
            PlannedRequest(unit, packet, schema, request_hash(loaded, packet, schema, model=model))
        )
    return units, attributed, tuple(requests)


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
    live README (Lane L) passes ``False``, and none of its text is withheld as renderer-owned.

    The one thing taken from ``dispositions`` is structural: which shown lines are attributed
    maintainer text (``scope.maintainer_lines``, units kept as ``PRESERVE_ATTRIBUTED``). Each unit's
    packet names them and its contract refuses an ``unsupported_claim`` citing only them. A Lane L
    review has no such disposition, so the set is empty and nothing changes there."""
    loaded = prompts[JOB]
    units, attributed, planned = planned_requests(
        prompts=prompts,
        context=context,
        candidate_readme=candidate_readme,
        original_readme=original_readme,
        facts=facts,
        plan=plan,
        dispositions=dispositions,
        rendered=rendered,
        validation=validation,
    )
    changed = edit_scope(
        rendered=rendered, validation=validation,
        candidate_readme=candidate_readme, original_readme=original_readme,
    )
    if not units:
        raise ReviewUnavailable(
            "the candidate has no author-written text to review (every line is renderer-printed)",
            [],
        )
    replies: list[tuple[ReviewUnit, dict[str, Any]]] = []
    records: list[dict[str, Any]] = []
    request_hashes: list[str] = []
    request_of: dict[str, str] = {}
    unavailable: list[tuple[ReviewUnit, ReviewUnavailable]] = []
    model_served: str | None = None
    for request in planned:
        unit, packet, schema = request.unit, request.packet, request.schema
        request_sha256 = request.request_sha256
        request_hashes.append(request_sha256)
        request_of[unit.label] = request_sha256
        _refuse_reroll(store, request_sha256)
        scope = ReviewScope(
            frozenset(unit.sections),
            frozenset(unit.lines),
            attributed & frozenset(unit.lines),
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
                    scope=scope,
                    changed=changed,
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
