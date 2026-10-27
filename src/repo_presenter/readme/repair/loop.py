"""Reviewer-driven targeted repair and the bounded settle loop over the S3-S8 cascade.

Ported from the S5/S6 halves of the old repository's ``components/readme/repair/rounds.py``
(``repair_defect``, ``escalate_to_plan``, ``_stage_target``, ``_refuse_noop``,
``_reject_title_verbatim_opening``, ``_reject_uncarried_units``, ``composition_id``,
``run_transaction``), rebuilt over ``repo_presenter.cascade.run_cascade`` and the independent
reviewer's ``ReviewVerdict`` (via ``readme.review.defect_bridge``), not over the old S9/S10 stack.

A REJECT verdict's deterministic findings become ``Defect`` records routed to the stage that may
revise them. One targeted ``targeted_repair`` call is made per fresh fingerprint, through
``core.llm.jobs.run_job`` with ``repair_checks`` as its validation. A revised output is written to
the call store under the causing call's own request hash, and the cascade is run again over the
same output directory: every unchanged call is served from the store with zero provider calls, so
only the repaired stage and whatever it changed downstream are asked again. A defect whose
fingerprint was already attempted is reported, never retried. The loop ends on ACCEPT, when no
fresh repairable defect remains, or at ``MAX_ROUNDS``.

Routing: S6 (one authored section), S5 (the plan, reached by an S6 slot-set escalation) and S4
(a disposition of inherited content). An S4 defect is repaired as a per-unit patch
(``reconciliation/patch.py``): the units at fault are the inherited units whose placed text holds
the finding's quote, the reply contract is cut down to those units, the reply is merged into the
stored batch and judged by the batch's own checks, and its ledger is derived from the difference.
A defect that names no placed unit is recorded unrepairable: a whole-batch S4 revision would
regenerate unrelated units.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path
from typing import Any

from repo_presenter.cascade import (
    COMPOSED_DISPOSITIONS_FILENAME,
    DEFAULT_PROMPTS_PATH,
    DEFAULT_REGISTRY_PATH,
    CascadeResult,
    run_cascade,
)
from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.errors import JobError
from repo_presenter.core.facts import FactsDocument, read_facts
from repo_presenter.core.llm.jobs import (
    CallStore,
    JobContext,
    JobResult,
    effective_model,
    request_hash,
    run_job,
)
from repo_presenter.core.llm.ledger import Ledger, canonical_hash
from repo_presenter.core.llm.prompts import (
    LoadedManifest,
    PromptRegistry,
    load_manifests,
)
from repo_presenter.core.noop_proof import Invocation
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.authoring import (
    SectionTask,
    authoring_schema,
    authoring_tasks,
    carried_unit_errors,
    recover_title_verbatim_opening,
    repair_title_verbatim_opening_errors,
    unit_checks,
)
from repo_presenter.readme.composition.components.identity import product_name
from repo_presenter.readme.composition.placement import PLACED, placements
from repo_presenter.readme.composition.planning import (
    plan_checks,
    planning_packet,
    planning_schema,
)
from repo_presenter.readme.reconciliation.dispositions import (
    reconcile_checks,
    reconciliation_batch_facts,
    reconciliation_batches,
    reconciliation_packet,
    reconciliation_schema,
)
from repo_presenter.readme.reconciliation.patch import (
    PatchScope,
    condensed,
    failing_units,
    patch_checks,
    patch_scope,
    unit_changes,
)
from repo_presenter.readme.repair.targeted import (
    MAX_ROUNDS,
    REPAIRS_FILENAME,
    Defect,
    RepairLedger,
    SlotSetProbe,
    defect_fingerprint,
    merge_equivalent,
    repair_checks,
    repair_packet,
    repair_schema,
)
from repo_presenter.readme.review.defect_bridge import build_defects

Checks = Callable[[dict[str, Any]], list[str]]


def refuse_noop(original: Mapping[str, Any], checks: Checks) -> Checks:
    """Refuse a revision identical to the causing stage's own stored output before ``checks``.

    Measured live (aspose-font-foss/Aspose.Font-FOSS-for-Python, the old repository's S5 BC-07
    blocker): a reply that returns its input unchanged clears every check and is recorded as
    repaired, and the next round finds nothing changed. The refusal sits here, not in
    ``repair_checks``, so it covers every causing stage the same way.
    """

    def guarded(revised: dict[str, Any]) -> list[str]:
        if revised == original:
            return [
                (
                    "matches the causal stage's own output unchanged; a no-op cannot repair a "
                    "defect this stage's content did not change"
                )
            ]
        return checks(revised)

    return guarded


def reject_title_verbatim_opening(checks: Checks, task: SectionTask) -> Checks:
    """Layer review's stricter title-restatement standard onto an S6 repair, never onto
    ``unit_checks`` itself, so a fresh draft keeps the item-106 carve-out it always had."""

    def guarded(revised: dict[str, Any]) -> list[str]:
        return [*checks(revised), *repair_title_verbatim_opening_errors(revised, task)]

    return guarded


def reject_uncarried_units(checks: Checks, task: SectionTask) -> Checks:
    """Layer the must-carry rule onto an S6 repair, the same rule a fresh draft is judged by."""
    if not task.must_carry:
        return checks

    def guarded(revised: dict[str, Any]) -> list[str]:
        return [*checks(revised), *carried_unit_errors(revised, task)]

    return guarded


def keep_unflagged_units(
    checks: Checks, original: Mapping[str, Any], quote: str
) -> Checks:
    """Refuse a targeted S6 revision that rewrites a unit the finding does not name.

    The finding's quote identifies the unit it is about (the unit whose text contains it). Any
    other unit of the same section that the revision changes is regeneration of unrelated
    content, which a targeted repair may not do. A quote that matches no unit names none, so the
    guard does not narrow that repair.
    """
    flagged = {
        unit.get("slot")
        for unit in original.get("units", [])
        if isinstance(unit, dict) and quote and quote in str(unit.get("text", ""))
    }
    if not flagged:
        return checks
    stored = {
        unit.get("slot"): unit
        for unit in original.get("units", [])
        if isinstance(unit, dict)
    }

    def guarded(revised: dict[str, Any]) -> list[str]:
        errors = checks(revised)
        for unit in revised.get("units", []):
            if not isinstance(unit, dict):
                continue
            slot = unit.get("slot")
            if slot in stored and slot not in flagged and unit != stored[slot]:
                errors.append(
                    f"revised_output: unit {slot} is not the finding's own unit; a targeted "
                    "repair may not rewrite unrelated units"
                )
        return errors

    return guarded


@dataclass(frozen=True)
class RepairContext:
    """The inputs one repair round reads: the same stage inputs the cascade was called with,
    read back from its own output directory."""

    entry: RegistryEntry
    facts: FactsDocument
    prompts: PromptRegistry
    config: GatewayConfig
    ledger: Ledger
    store: CallStore
    context: JobContext
    investigation: dict[str, Any]
    dispositions: dict[str, Any]
    plan: dict[str, Any]
    tasks: list[SectionTask]
    name: str


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _unrepairable(defect: Defect, repairs: RepairLedger, reason: str) -> bool:
    repairs.record(replace(defect, reason=reason), "unrepairable")
    return False


def _targeted_call(
    rc: RepairContext,
    defect: Defect,
    loaded: LoadedManifest,
    original: dict[str, Any],
    checks: Checks,
    *,
    slots: SlotSetProbe | None = None,
    allowed: Collection[str] | None = None,
    slot_facts: Mapping[str, Collection[str]] | None = None,
    carried: Sequence[str] = (),
    recover: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    patch: PatchScope | None = None,
    stage_facts: FactsDocument | None = None,
) -> JobResult | JobError:
    """One ``targeted_repair`` call, judged by ``repair_checks`` around the causing stage's own
    ``checks``; a rejection after the job's own re-asks comes back as the ``JobError``.

    ``patch`` is an S4 disposition patch: the reply is asked for and judged by its bounded contract,
    merged into ``original``, and its ledger derived from the difference. ``stage_facts`` is the
    fact set the causing call's own binding was judged against (one batch's, for S4)."""
    contract = loaded.manifest.output.schema_
    repairer = rc.prompts["targeted_repair"]
    reply_contract = patch.contract if patch is not None else contract
    try:
        return run_job(
            repairer,
            repair_packet(
                rc.entry,
                defect,
                patch.shown if patch is not None else original,
                rc.facts,
                (),
                condensed(reply_contract) if patch is not None else contract,
                allowed,
                slot_facts,
                None,
                carried=carried,
            ),
            config=rc.config,
            facts=rc.facts,
            ledger=rc.ledger,
            store=rc.store,
            context=rc.context,
            call_schema=repair_schema(
                repairer, reply_contract, bound_changes=patch is not None
            ),
            checks=partial(
                repair_checks,
                defect=defect,
                output_contract=contract,
                patch_contract=reply_contract if patch is not None else None,
                derive_changes=unit_changes if patch is not None else None,
                binding=loaded.manifest.output.binding,
                facts=stage_facts if stage_facts is not None else rc.facts,
                stage_checks=checks,
                slots=slots,
                original=original,
            ),
            recover=recover,
        )
    except JobError as error:
        return error


def _accept(
    rc: RepairContext,
    defect: Defect,
    loaded: LoadedManifest,
    key: str,
    result: JobResult,
    repairs: RepairLedger,
) -> bool:
    rc.store.put(
        key,
        loaded.manifest.prompt_id,
        result.model_served,
        result.output["revised_output"],
    )
    repairs.record(
        defect, "repaired", result.request_sha256, result.output.get("changes", [])
    )
    return True


def _repair_plan(rc: RepairContext, defect: Defect, repairs: RepairLedger) -> bool:
    loaded = rc.prompts["presentation_planning"]
    packet = planning_packet(
        rc.entry, rc.facts, rc.investigation, rc.dispositions, loaded.manifest
    )
    schema = planning_schema(loaded, rc.facts, rc.investigation, rc.dispositions)
    key = request_hash(
        loaded, packet, schema, model=effective_model(loaded, rc.context)
    )
    original = rc.store.get(key)
    if original is None:
        return _unrepairable(
            defect, repairs, "the causing plan is not in the call store"
        )
    checks = refuse_noop(
        original,
        partial(
            plan_checks,
            facts=rc.facts,
            dispositions=rc.dispositions,
            ecosystem=rc.entry.ecosystem,
        ),
    )
    outcome = _targeted_call(rc, defect, loaded, original, checks)
    if isinstance(outcome, JobError):
        return _unrepairable(defect, repairs, str(outcome))
    return _accept(rc, defect, loaded, key, outcome, repairs)


def reject_printed_quote(
    checks: Checks, scope: PatchScope, texts: Mapping[str, str], quotes: Collection[str]
) -> Checks:
    """Refuse an S4 revision that keeps printing the text the finding quotes.

    A kept disposition (``PLACED``) prints its unit as written, so a unit whose text holds the
    quote and is still kept, in this section or another, has not been repaired: moving a wrong
    command is not fixing it. Run after ``checks`` so the disposition judged is the normalised one.
    """
    quoted = [
        unit
        for unit in scope.unit_ids
        if any(quote and quote in texts.get(unit, "") for quote in quotes)
    ]
    if not quoted:
        return checks

    def guarded(revised: dict[str, Any]) -> list[str]:
        errors = checks(revised)
        by_unit = {
            str(entry.get("unit_id")): entry
            for entry in revised.get("dispositions", [])
            if isinstance(entry, Mapping)
        }
        for unit in quoted:
            disposition = by_unit.get(unit, {}).get("disposition")
            if disposition in PLACED:
                errors.append(
                    f"{unit}: still {disposition}, which prints the quoted text as written; the "
                    "finding is about that text, so keeping it in any section leaves the defect"
                )
        return errors

    return guarded


def _named_units(rc: RepairContext, defect: Defect) -> list[str]:
    """The inherited units a defect is about: those its failure records name in their ``unit_id``
    field, else (a review finding, which carries a quote and no unit) those whose placed text holds
    the quote. The quote is a field of the finding and the placed text is what the renderer
    prints, so no prose is read."""
    named = failing_units(defect.record)
    if named:
        return named
    placed = placements(rc.plan, rc.dispositions, rc.facts, rc.entry.ecosystem)
    for record in [defect.record, *defect.record.get("equivalent_findings", [])]:
        quote = str(record.get("quote") or "")
        for placement in placed if quote else ():
            if quote in placement.text and placement.unit_id not in named:
                named.append(placement.unit_id)
    return named


def _repair_reconciliation(
    rc: RepairContext, defect: Defect, repairs: RepairLedger
) -> bool:
    """An S4 defect repaired as a patch of the units at fault: one ``targeted_repair`` call whose
    reply is bounded to those units, merged into the stored batch and judged by the batch's own
    checks. The repaired batch replaces the stored one under the causing call's request hash."""
    loaded = rc.prompts["source_reconciliation"]
    batches = dict(
        reconciliation_batches(rc.facts, loaded.manifest.sampling.max_output_tokens)
    )
    keys: dict[str, str] = {}
    stored: dict[str, dict[str, Any]] = {}
    for batch_id, units in batches.items():
        batch_facts = reconciliation_batch_facts(rc.facts, units)
        key = request_hash(
            loaded,
            reconciliation_packet(
                rc.entry, batch_facts, rc.investigation, loaded.manifest, units
            ),
            reconciliation_schema(loaded, units, batch_facts, rc.investigation),
            model=effective_model(loaded, rc.context),
        )
        output = rc.store.get(key)
        if output is not None:
            keys[batch_id], stored[batch_id] = key, output
    scope = patch_scope(
        {"failures": [{"unit_id": unit} for unit in _named_units(rc, defect)]},
        stored,
        batches,
        rc.facts,
        loaded,
        rc.investigation,
        rc.prompts["targeted_repair"].manifest.sampling.max_output_tokens,
    )
    if scope is None:
        return _unrepairable(
            defect,
            repairs,
            "no stored disposition of an inherited unit is named by this defect; a whole-batch "
            "revision would regenerate unrelated units",
        )
    batch_facts = reconciliation_batch_facts(rc.facts, batches[scope.batch_id])
    original = stored[scope.batch_id]
    quotes = [
        str(record.get("quote") or "")
        for record in [defect.record, *defect.record.get("equivalent_findings", [])]
    ]
    checks = patch_checks(
        scope,
        reject_printed_quote(
            refuse_noop(original, partial(reconcile_checks, facts=batch_facts)),
            scope,
            {fact.id: fact.value for fact in batch_facts.by_kind("inherited_unit")},
            quotes,
        ),
    )
    outcome = _targeted_call(
        rc, defect, loaded, original, checks, patch=scope, stage_facts=batch_facts
    )
    if isinstance(outcome, JobError):
        return _unrepairable(defect, repairs, str(outcome))
    return _accept(rc, defect, loaded, keys[scope.batch_id], outcome, repairs)


def _escalate_to_plan(
    rc: RepairContext, defect: Defect, repairs: RepairLedger, probe: SlotSetProbe
) -> bool:
    """A slot-set or fact-selection change belongs to the plan: record the escalation once and run
    one plan-level repair. The escalated defect takes its own fingerprint, so it is attempted once."""
    parts: list[str] = []
    if probe.returned is not None and probe.returned != probe.required:
        returned = ", ".join(sorted(probe.returned)) or "no slot"
        parts.append(
            f"the revision would leave {returned} where the plan assigned "
            f"{', '.join(sorted(probe.required))}"
        )
    if probe.fact_conflicts:
        parts.append(
            "the revision cites "
            f"{', '.join(sorted(probe.fact_conflicts))} outside the slot's planned facts"
        )
    reason = "; ".join(parts) + "; escalated once to a plan-level repair at S5"
    repairs.record(replace(defect, reason=reason), "escalated")
    escalated = replace(
        defect,
        fingerprint=defect_fingerprint(
            defect.source, None, "S5", defect.label, defect.fingerprint
        ),
        section_id=None,
        stage="S5",
        reason=None,
    )
    return _repair_plan(rc, escalated, repairs)


def _repair_section(rc: RepairContext, defect: Defect, repairs: RepairLedger) -> bool:
    task = next((t for t in rc.tasks if t.section_id == defect.section_id), None)
    if task is None:
        return _unrepairable(defect, repairs, "no authoring task holds this section")
    loaded = rc.prompts["section_authoring"]
    key = request_hash(
        loaded,
        task.packet,
        authoring_schema(loaded, task),
        model=effective_model(loaded, rc.context),
    )
    original = rc.store.get(key)
    if original is None:
        return _unrepairable(
            defect, repairs, "the causing section is not in the call store"
        )
    checks: Checks = refuse_noop(
        original,
        lambda revised: unit_checks(
            revised, task, rc.facts, rc.name, dispositions=rc.dispositions
        ),
    )
    checks = reject_title_verbatim_opening(checks, task)
    checks = reject_uncarried_units(checks, task)
    checks = keep_unflagged_units(checks, original, str(defect.record.get("quote", "")))
    facts = rc.facts.facts
    probe = SlotSetProbe(
        frozenset(task.slots),
        fact_sets=dict(task.slot_facts),
        fact_universe=frozenset(fact.id for fact in facts),
        neutral_facts=frozenset(
            fact.id for fact in facts if fact.kind in {"identity", "package"}
        ),
    )
    outcome = _targeted_call(
        rc,
        defect,
        loaded,
        original,
        checks,
        slots=probe,
        allowed=task.accepted_ids,
        slot_facts=task.slot_facts,
        carried=task.must_carry,
        recover=partial(recover_title_verbatim_opening, slot_titles=task.slot_titles),
    )
    if isinstance(outcome, JobError):
        if probe.conflicts:
            return _escalate_to_plan(rc, defect, repairs, probe)
        return _unrepairable(defect, repairs, str(outcome))
    return _accept(rc, defect, loaded, key, outcome, repairs)


def repair_defect(rc: RepairContext, defect: Defect, repairs: RepairLedger) -> bool:
    """One targeted repair for one repairable defect. Every outcome is recorded in the ledger;
    the return says whether a stored output changed, which is what makes a re-run worth making."""
    if defect.stage == "S6":
        return _repair_section(rc, defect, repairs)
    if defect.stage == "S5":
        return _repair_plan(rc, defect, repairs)
    if defect.stage == "S4":
        return _repair_reconciliation(rc, defect, repairs)
    return _unrepairable(
        defect,
        repairs,
        defect.reason or f"{defect.stage} repair is not ported",
    )


def composition_hash(
    source_revision: str, document: FactsDocument, prompts: PromptRegistry
) -> str:
    """What the repair ledger is scoped to: the revision, the facts, and the prompt set. A rebuilt
    composition on changed evidence starts with no attempts spent."""
    return canonical_hash(
        {
            "revision": source_revision,
            "facts": document.to_json(),
            "prompts": dict(sorted(prompts.hashes().items())),
        }
    )


def composition_id(result: CascadeResult, prompts: PromptRegistry) -> str:
    return composition_hash(result.source_revision, result.document, prompts)


@dataclass(frozen=True)
class SettleResult:
    """The last cascade run, the repair ledger over the whole settle, and how many runs it took."""

    result: CascadeResult
    repairs: RepairLedger
    rounds: int


def _load_context(
    result: CascadeResult,
    *,
    out_dir: Path,
    registry_path: Path,
    prompts: PromptRegistry,
    config: GatewayConfig,
    ledger: Ledger,
) -> RepairContext:
    entry = require_listed(load_registry(registry_path), result.repository)
    # facts.json stores the inherited units in sorted position, but the cascade builds its document
    # with them appended after every other fact (cascade._document_with_inherited_units). Packets
    # serialise in that order, so the same order is rebuilt here, or every cache key recomputed
    # from disk would differ from the one the cascade stored.
    stored = read_facts(result.facts_path)
    facts = FactsDocument(
        stored.repository,
        stored.source_revision,
        (
            *(fact for fact in stored.facts if fact.kind != "inherited_unit"),
            *(fact for fact in stored.facts if fact.kind == "inherited_unit"),
        ),
    )
    investigation = _read_json(out_dir / "investigation.json")
    # The dispositions the S5/S6/S8 calls were made from, not the accounted ones the README and
    # the reviewer saw: the request hashes rebuilt here must match the call store's.
    composed = out_dir / COMPOSED_DISPOSITIONS_FILENAME
    dispositions = _read_json(
        composed if composed.is_file() else out_dir / "dispositions.json"
    )
    plan = _read_json(out_dir / "plan.json")
    tasks = authoring_tasks(entry, facts, investigation, dispositions, plan)
    return RepairContext(
        entry=entry,
        facts=facts,
        prompts=prompts,
        config=config,
        ledger=ledger,
        store=CallStore(out_dir / "llm_cache" / "calls"),
        context=JobContext(
            repository=result.repository, source_revision=result.source_revision
        ),
        investigation=investigation,
        dispositions=dispositions,
        plan=plan,
        tasks=tasks,
        name=product_name(entry),
    )


def settle_candidate(
    repository: str,
    ecosystem: str,
    clone_path: Path,
    *,
    facts_path: Path,
    out_dir: Path,
    config: GatewayConfig,
    prompts_path: Path = DEFAULT_PROMPTS_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    max_rounds: int = MAX_ROUNDS,
) -> SettleResult:
    """Run the cascade, then repair and re-run until the candidate is accepted, no fresh repair
    remains, or ``max_rounds`` cascade runs have been made. Every repair is one ``run_job`` call."""
    prompts = load_manifests(prompts_path)
    cascade_args = {
        "facts_path": facts_path,
        "out_dir": out_dir,
        "config": config,
        "prompts_path": prompts_path,
        "registry_path": registry_path,
        # this loop owns the rounds; the cascade's own S9 repair would double-spend the calls
        "max_rounds": 1,
    }
    result = run_cascade(repository, ecosystem, clone_path, **cascade_args)
    repairs = RepairLedger(
        out_dir / REPAIRS_FILENAME, composition=composition_id(result, prompts)
    )
    rounds = 1
    while result.review_verdict.verdict != "ACCEPT" and rounds < max_rounds:
        invocation = Invocation.begin()
        ledger_path = out_dir / "llm_cache" / "ledger.jsonl"
        ledger = Ledger(ledger_path, invocation_id=invocation.invocation_id)
        rc = _load_context(
            result,
            out_dir=out_dir,
            registry_path=registry_path,
            prompts=prompts,
            config=config,
            ledger=ledger,
        )
        units = _read_json(out_dir / "content_units.coherent.json").get("units", [])
        defects = build_defects(
            result.review_verdict,
            units=units,
            plan=rc.plan,
            dispositions=rc.dispositions,
            facts=rc.facts,
            ecosystem=ecosystem,
            repairer=prompts["targeted_repair"].sha256,
        )
        for defect in defects:
            if not defect.repairable and not repairs.attempted(defect.fingerprint):
                repairs.record(defect, "unrepairable")
        repeated = [
            d for d in defects if d.repairable and repairs.attempted(d.fingerprint)
        ]
        if repeated:
            for defect in repeated:
                repairs.note_re_raised(defect)
            break
        fresh = merge_equivalent(
            [
                d
                for d in defects
                if d.repairable and not repairs.attempted(d.fingerprint)
            ]
        )
        if not fresh:
            break
        changed = [repair_defect(rc, defect, repairs) for defect in fresh]
        invocation.attach_ledger(repository, ledger_path)
        invocation.write(
            out_dir / "llm_cache" / "invocations" / f"{invocation.invocation_id}.json",
            Path("."),
            0,
        )
        if not any(changed):
            break
        result = run_cascade(repository, ecosystem, clone_path, **cascade_args)
        rounds += 1
    return SettleResult(result=result, repairs=repairs, rounds=rounds)
