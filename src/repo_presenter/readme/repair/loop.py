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
A defect that names no placed unit but whose quote an authoring task's stored units print is
repaired in that task (the S6 path, ``_authored_routes``); one that names neither is recorded
unrepairable: a whole-batch S4 revision would regenerate unrelated units.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
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
    recover_opening_duplicates_preserved,
    recover_title_verbatim_opening,
    repair_title_verbatim_opening_errors,
    unit_checks,
)
from repo_presenter.readme.composition.authoring_retry import (
    authoring_narrowing,
    recover_authoring_output,
    recover_targeted_repair_dropped_citation,
    recover_targeted_repair_restatements,
)
from repo_presenter.readme.composition.components.identity import product_name
from repo_presenter.readme.composition.output_bounds import bound_authoring_citations
from repo_presenter.readme.composition.placement import PLACED, placements
from repo_presenter.readme.composition.planning import (
    plan_checks,
    planning_packet,
    planning_schema,
    recover_planning_output,
)
from repo_presenter.readme.composition.policy import DEFAULT_POLICY
from repo_presenter.readme.composition.renderer import line_counts, render_readme
from repo_presenter.readme.validation.blocking import JUDGES
from repo_presenter.readme.validation.failures import Candidate
from repo_presenter.readme.validation.rules import effective_visible_lines_budget
from repo_presenter.readme.validation.must_correct import (
    cited_finding_quotes,
    omission_holds,
    open_finding_citations,
    withheld_form,
)
from repo_presenter.readme.reconciliation.dispositions import (
    bound_rationales,
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
    visible_line_budget_hint,
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
    checks: Checks,
    original: Mapping[str, Any],
    quote: str | Sequence[str],
    named_slots: Collection[str] = (),
) -> Checks:
    """Refuse a targeted S6 revision that rewrites a unit the finding does not name.

    The finding's quote identifies the unit it is about (the unit whose text contains it). Any
    other unit of the same section that the revision changes is regeneration of unrelated
    content, which a targeted repair may not do. A quote that matches no unit names none, so the
    guard does not narrow that repair.

    A merged defect carries several equivalent findings, so ``quote`` may be every one of their
    quotes and ``named_slots`` the slots a finding names by its type (``_route_section_defect``):
    each names its own unit, and every named unit may change (Aspose.BarCode-FOSS-for-Python,
    hosted run 43394959529: seventeen merged findings, only the first quote's unit was allowed to
    change, and the reply was refused as a no-op).
    """
    quotes = [quote] if isinstance(quote, str) else list(quote)
    flagged = _flagged_slots(original, quotes)
    flagged.update(named_slots)
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


def _flagged_slots(original: Mapping[str, Any], quotes: Sequence[str]) -> set[Any]:
    """The slots of ``original`` whose text prints one of ``quotes``, matched as printed
    (``_printed``: a README quote carries the code spans the renderer adds to a unit)."""
    keys = [_printed(q) for q in quotes if q and _printed(q)]
    return {
        unit.get("slot")
        for unit in original.get("units", [])
        if isinstance(unit, dict)
        and any(key in _printed(str(unit.get("text", ""))) for key in keys)
    }


#: The deterministic blocking checks every revision is re-judged by before it is accepted
#: (BL-079). A repair used to be accepted on its causing stage's own checks alone, so a reply that
#: still printed the false claim -- reworded, kept, or moved -- was recorded "repaired" and the final
#: check rejected the candidate: hosted Lane R runs 43489984973 (Cells .NET, BC-14 "repaired" with
#: the samples-use-the-package claim), 43489988826 (Cells C++, BC-02 "repaired" by a
#: VERIFIED_PRESERVE of the block printing ``cmake --build build``), 43489976823 / 43489981024
#: (3D .NET / Python, never-thrown exceptions). These three judge claims line by line against the
#: facts, so a render of the revision answers them exactly as the final validation will. The
#: content-loss checks (BC-05/BC-08/BC-17) are not re-run here: a VERIFIED_REWRITE prints only
#: after re-authoring, so a render taken before it would refuse every honest S4 rewrite; they keep
#: their own guards (``patch_checks``' supersession rule, ``reject_uncarried_units``).
REVALIDATED_CHECKS: tuple[str, ...] = ("BC-02", "BC-14", "BC-18")
#: A deterministic reviewer rule and the blocking check that judges the same claims with the same
#: detail text (``claim_contradiction_rule`` reuses ``claim_findings``, as BC-14 does).
_RULE_CHECKS: Mapping[str, str] = {"claim_contradiction": "BC-14"}
#: What a guard composes a revision into: the plan, units document and dispositions to render.
Composed = tuple[dict[str, Any], dict[str, Any], dict[str, Any]]


def owned_failures(defect: Defect) -> Counter[tuple[str, str]]:
    """The ``(check, detail)`` failures of ``REVALIDATED_CHECKS`` the defect is about: a validation
    defect's own failure records, a deterministic review finding's own evidence (its rule mapped to
    the check that judges the same claims). Read from fields, never from prose."""
    owned: Counter[tuple[str, str]] = Counter()
    primary = getattr(defect, "record", None) or {}
    for record in [primary, *primary.get("equivalent_findings", [])]:
        if getattr(defect, "source", None) == "validation":
            check = str(record.get("id") or getattr(defect, "label", ""))
            details = [
                str(failure.get("detail") or "")
                for failure in record.get("failures") or []
                if isinstance(failure, Mapping)
            ]
        else:
            check = _RULE_CHECKS.get(str(record.get("criterion") or ""), "")
            details = [str(record["evidence"])] if record.get("evidence") else []
        if check in REVALIDATED_CHECKS:
            owned.update((check, detail) for detail in details if detail)
    return owned


def revalidation_failures(
    rc: "RepairContext", composed: Composed, checks: Sequence[str] = REVALIDATED_CHECKS
) -> Counter[tuple[str, str]] | None:
    """The ``(check, detail)`` failures of ``checks`` on the README ``composed`` renders, judged by
    the blocking checks' own functions (``validation.blocking.JUDGES``); ``None`` when it cannot be
    rendered or judged (the guard then decides nothing)."""
    plan, units, dispositions = composed
    try:
        readme = render_readme(rc.entry, rc.facts, plan, units, dispositions)
        candidate = Candidate(
            entry=rc.entry,
            facts=rc.facts,
            plan=plan,
            units=units,
            dispositions=dispositions,
            readme=readme,
            original_readme=None,
            source_revision=rc.facts.source_revision,
            readme_sha256=None,
            tree_paths=(),
            tasks=rc.tasks,
            benchmark_readme=rc.benchmark or None,
        )
        found: Counter[tuple[str, str]] = Counter()
        for check in checks:
            found.update((check, failure.detail) for failure in JUDGES[check](candidate))
    except Exception:  # noqa: BLE001 - "cannot judge" is not a verdict on the revision
        return None
    return found


def reject_still_failing(
    checks: Checks,
    rc: "RepairContext",
    defect: Defect,
    original: Mapping[str, Any],
    compose: Callable[[Mapping[str, Any]], Composed | None],
) -> Checks:
    """Refuse a revision whose render still fails the defect's own BC-02/BC-14/BC-18 rule, or fails
    one of them anew, with the rule's own text, so the job's re-ask is told exactly what is still
    false (and, through the packet's ``contradicting_facts``, what is true).

    Judged against the causing stage's own stored output rendered the same way (``original``, the
    baseline), never against the README the defect was found in: both renders share every input but
    the revision, so a failure the baseline already has and the revision does not add is another
    defect's, and nothing about the render inputs (tree paths, a restore) can make the guard
    disagree with itself. "Still failing" is a failure of the defect's own that the revision does
    not print fewer times than the baseline; "anew" is one it prints more times. Runs after
    ``checks``, on the normalised revision, only when they pass."""
    owned = owned_failures(defect)
    baseline_cache: list[Counter[tuple[str, str]] | None] = []

    def baseline() -> Counter[tuple[str, str]] | None:
        if not baseline_cache:
            composed = compose(original)
            baseline_cache.append(None if composed is None else revalidation_failures(rc, composed))
        return baseline_cache[0]

    def guarded(revised: dict[str, Any]) -> list[str]:
        errors = checks(revised)
        if errors:
            return errors
        before = baseline()
        composed = compose(revised)
        after = None if composed is None or before is None else revalidation_failures(rc, composed)
        if before is None or after is None:
            return errors
        for (check, detail), count in sorted(after.items()):
            if (check, detail) in owned and before.get((check, detail), 0) and count >= before[(check, detail)]:
                errors.append(
                    f"revised_output: {check} still fails on this revision, which is the defect: "
                    f"{detail}"
                )
            elif count > before.get((check, detail), 0):
                errors.append(f"revised_output: this revision makes {check} fail: {detail}")
        return errors

    return guarded


def section_composer(
    rc: "RepairContext", task: SectionTask
) -> Callable[[Mapping[str, Any]], Composed | None]:
    """An S6 revision (``task``'s units) put in place of that task's units in the coherent units the
    README is rendered from; ``None`` without them."""
    if not isinstance(rc.units, Mapping) or not rc.units.get("units"):
        return lambda _output: None
    slots = set(task.slots)

    def compose(output: Mapping[str, Any]) -> Composed | None:
        revised = [u for u in output.get("units") or [] if isinstance(u, Mapping)]
        by_slot = {u.get("slot"): u for u in revised}
        units: list[dict[str, Any]] = []
        for unit in rc.units.get("units", []):
            mine = unit.get("section") == task.section_id and unit.get("slot") in slots
            if not mine:
                units.append(unit)
            elif unit.get("slot") in by_slot:
                units.append({**unit, **dict(by_slot.pop(unit.get("slot"))), "section": task.section_id})
        units.extend({**dict(u), "section": task.section_id} for u in by_slot.values())
        return rc.plan, {**rc.units, "units": units}, rc.dispositions

    return compose


def dispositions_composer(rc: "RepairContext") -> Callable[[Mapping[str, Any]], Composed | None]:
    """An S4 revision (one merged batch) put in place of its units' dispositions."""
    if not isinstance(rc.units, Mapping) or not rc.units.get("units"):
        return lambda _output: None

    def compose(output: Mapping[str, Any]) -> Composed | None:
        revised = {
            str(entry.get("unit_id")): entry
            for entry in output.get("dispositions") or []
            if isinstance(entry, Mapping)
        }
        entries = [
            revised.pop(str(entry.get("unit_id")), entry)
            for entry in rc.dispositions.get("dispositions", [])
        ]
        entries.extend(revised.values())
        return rc.plan, rc.units, {**rc.dispositions, "dispositions": entries}

    return compose


def plan_composer(rc: "RepairContext") -> Callable[[Mapping[str, Any]], Composed | None]:
    """An S5 revision (the plan) rendered over the same units and dispositions."""
    if not isinstance(rc.units, Mapping) or not rc.units.get("units"):
        return lambda _output: None
    return lambda output: (dict(output), rc.units, rc.dispositions)


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
    #: The README the defect was found in (for a BC-07 budget repair: its visible-line count).
    readme: str = ""
    #: The coherent units document the README was rendered from; with it a budget repair can
    #: MEASURE what clearing a plan field removes instead of estimating.
    units: dict[str, Any] = field(default_factory=dict)
    #: The published README the candidate is held to (BC-07's line budget is
    #: ``max(policy budget, its visible lines)``); empty when there is none.
    benchmark: str = ""

    @property
    def visible_lines_budget(self) -> int:
        """The budget BC-07 judges this candidate by -- the one shared function, so a repair is
        never judged against a stricter budget than the check that raised the defect."""
        return effective_visible_lines_budget(DEFAULT_POLICY, self.benchmark or None)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


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
    visible_line_budget: Mapping[str, Any] | None = None,
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
                visible_line_budget,
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


def _regenerate_plan(rc: RepairContext, loaded: LoadedManifest) -> dict[str, Any] | None:
    """A fresh ``presentation_planning`` call, the same job initial generation makes
    (``cascade._run_planning``), so a missing call-store entry gets a real original instead of
    stopping the repair cold. ``run_job`` stores its own accepted output under the SAME request
    hash ``request_hash`` already computed (its own docstring: "the store key ``run_job`` would
    compute for this exact packet"), so no further bookkeeping is needed here -- the next round's
    ``rc.store.get(key)`` finds it."""

    def checks(output: dict[str, Any]) -> list[str]:
        return plan_checks(
            output, rc.facts, dispositions=rc.dispositions, ecosystem=rc.entry.ecosystem
        )

    def recover(output: dict[str, Any]) -> dict[str, Any] | None:
        return recover_planning_output(output, rc.facts)

    try:
        result = run_job(
            loaded,
            planning_packet(rc.entry, rc.facts, rc.investigation, rc.dispositions, loaded.manifest),
            config=rc.config, facts=rc.facts, ledger=rc.ledger, store=rc.store,
            context=rc.context,
            call_schema=planning_schema(loaded, rc.facts, rc.investigation, rc.dispositions),
            checks=checks, recover=recover,
        )
    except JobError:
        return None
    return result.output


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
        # ``--restore-sealed-bundle`` (the hosted default) restores a PREVIOUS seal's call store,
        # so a defect the independent reviewer raises against a RESTORED plan has no original
        # call in THIS run's store to revise -- measured live twice on Aspose.Slides-FOSS-for-Cpp,
        # identical both times, "the causing plan is not in the call store" before this fix. A
        # fresh generation gives the next round a real original, never weakening what a repair
        # must satisfy (the regenerated plan is judged by the SAME plan_checks any plan is).
        original = _regenerate_plan(rc, loaded)
        if original is None:
            return _unrepairable(
                defect, repairs,
                "the causing plan is not in the call store, and a fresh "
                "presentation_planning call could not produce one",
            )
        # A plain regenerate alone is not enough: measured on Aspose.Slides-FOSS-for-Cpp (the
        # section_authoring sibling of this same gap), a bare re-ask of the unchanged packet
        # reproduced the identical output and the review re-flagged the identical findings
        # forever. Falling through into the ordinary defect-aware revision below, which DOES
        # carry the finding's own reason, is what section_authoring's fix also does.
        defect = replace(
            defect,
            reason=(
                "the causing plan was not in the call store (restored from a sealed "
                "bundle); regenerated it fresh, then revised in place against this finding"
            ),
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
    hint = _budget_hint(rc, defect, original)
    if hint is not None:
        checks = _fits_the_budget(rc, checks, hint)
    checks = reject_still_failing(checks, rc, defect, original, plan_composer(rc))
    outcome = _targeted_call(
        rc, defect, loaded, original, checks,
        visible_line_budget=hint,
    )
    if isinstance(outcome, JobError):
        return _unrepairable(defect, repairs, str(outcome))
    return _accept(rc, defect, loaded, key, outcome, repairs)


def _budget_hint(
    rc: RepairContext, defect: Defect, plan: Mapping[str, Any]
) -> dict[str, Any] | None:
    """The measured cost of each optional plan lever for a BC-07 visible-line-budget defect, so the
    one repair attempt can clear the right field instead of guessing among small prose trims
    (``targeted.visible_line_budget_hint``; its original caller, rounds.py, was never ported, so the
    packet always carried ``null``). Routed on the defect's label and stage - never its prose - and
    only when the README it was found in is known."""
    if defect.label != "BC-07" or defect.stage != "S5" or not rc.readme:
        return None
    visible, _total = line_counts(rc.readme)
    return visible_line_budget_hint(
        plan,
        rc.facts,
        visible,
        rc.visible_lines_budget,
        measure=_measure_by_render(rc, plan, visible),
    )


def _fits_the_budget(rc: RepairContext, checks: Checks, hint: Mapping[str, Any]) -> Checks:
    """Judge a BC-07 plan revision by what it renders. The plan checks only refuse a no-op, so a
    reply that edited unrelated lists was recorded "repaired" while the README stayed over budget
    (Font, 321 visible lines vs 300): the one attempt a fingerprint gets, spent on nothing. A
    revision whose render still exceeds the budget is rejected with the measured levers named, so
    the job's own bounded re-asks can correct it. A revision that cannot be rendered is left to the
    plan checks: this adds a requirement, it never decides on a render it could not make."""
    budget = rc.visible_lines_budget
    levers = hint.get("optional_plan_fields_and_their_visible_line_cost_if_cleared") or {}

    def judged(revised: dict[str, Any]) -> list[str]:
        errors = checks(revised)
        if errors:
            return errors
        try:
            rendered = render_readme(rc.entry, rc.facts, revised, rc.units, rc.dispositions)
        except Exception:  # noqa: BLE001 - "cannot render" is not a verdict on the budget
            return errors
        visible = line_counts(rendered)[0]
        if visible <= budget:
            return errors
        named = ", ".join(f"{name} (saves {cost})" for name, cost in sorted(levers.items()))
        message = (
            f"the revised plan still renders {visible} visible lines against the budget of "
            f"{budget}; clear (set to null) enough of the optional fields in visible_line_budget "
            f"to remove at least {visible - budget} lines: {named or 'none is selected'}"
        )
        return [message]

    return judged


def _measure_by_render(
    rc: RepairContext, plan: Mapping[str, Any], visible: int
) -> Callable[[str], int | None] | None:
    """A function giving the visible lines that disappear when one plan field is cleared, measured
    by rendering the README again from the same units and dispositions. ``None`` (so the caller
    keeps the formula) without the authored units, and per field when the render cannot be made.
    The plan passed in is never mutated."""
    if not rc.units:
        return None

    def measure(field_name: str) -> int | None:
        try:
            cleared = {**plan, field_name: None}
            rendered = render_readme(rc.entry, rc.facts, cleared, rc.units, rc.dispositions)
            return max(visible - line_counts(rendered)[0], 0)
        except Exception:  # noqa: BLE001 - any render failure means "cannot measure", not a defect
            return None

    return measure


def _withholds_quoted_lines(
    unit: str,
    text: str,
    entry: Mapping[str, Any],
    quotes: Collection[str],
    repository: str | None,
) -> bool:
    """Whether a kept code block or paragraph stops printing every quote it holds because its
    disposition cites the OPEN register rows confirming that text false: the renderer then prints
    it without exactly those lines or sentences (``must_correct.withheld_form``)."""
    held = [quote for quote in quotes if quote and _squash(quote) in _squash(text)]
    cited = cited_finding_quotes(entry.get("fact_ids") or (), repository)
    printed = _squash(withheld_form(unit, text, cited))
    return bool(held) and omission_holds(unit, text, cited) and all(
        _squash(quote) not in printed for quote in held
    )


def reject_printed_quote(
    checks: Checks,
    scope: PatchScope,
    texts: Mapping[str, str],
    quotes: Collection[str],
    repository: str | None = None,
) -> Checks:
    """Refuse an S4 revision that keeps printing the text the finding quotes.

    A kept disposition (``PLACED``) prints its unit as written, so a unit whose text holds the
    quote and is still kept, in this section or another, has not been repaired: moving a wrong
    command is not fixing it. Run after ``checks`` so the disposition judged is the normalised one.
    The one kept form that does stop printing it: a code block or paragraph citing the OPEN
    register rows whose quotes are its false lines or sentences, which prints without exactly
    those (a register-backed correction that would lose true commands is already folded to that
    form by the batch's own checks, ``dispositions._fold_register_corrections``).
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
            entry = by_unit.get(unit, {})
            disposition = entry.get("disposition")
            if disposition in PLACED and not _withholds_quoted_lines(
                unit, texts.get(unit, ""), entry, quotes, repository
            ):
                errors.append(
                    f"{unit}: still {disposition}, which prints the quoted text as written; the "
                    "finding is about that text, so keeping it in any section leaves the defect"
                )
        return errors

    return guarded


#: What ``rewrite_printed_quote`` may fold: prose kept as written (``_fold_dangling_rewrites``'s own
#: set). PRESERVE_ATTRIBUTED is unverified, so it is never re-authored from facts.
_REWRITABLE_KEPT = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
_REWRITABLE_KINDS = frozenset({"paragraph", "list"})
_REWRITE_RATIONALE_LIMIT = 160  # the reconciliation contract's rationale ceiling


def _citations_for(text: str, citations: Mapping[str, str]) -> list[str]:
    """The register citations (``citation_id -> quote``) whose quote ``text`` prints."""
    return [cid for cid, quote in citations.items() if quote and _squash(quote) in _squash(text)]


#: The dispositions that need a citation to stand and get the register row's when they have none.
_CITATION_NEEDED = frozenset({"CORRECT_WITH_EVIDENCE", "OMIT_UNSUPPORTED"})
_REGISTER_RATIONALE = "The findings register confirms the quoted text false. "
#: The kept kinds that print without exactly the register-false text when they cite its row
#: (``must_correct.withheld_form``): lines, sentences, table rows, list items.
_WITHHOLDING_KINDS = (".code_block", ".paragraph", ".table", ".list")


def _cite_register_rows(
    unit: str,
    entry: dict[str, Any],
    ids: Sequence[str],
    text: str,
    citations: Mapping[str, str],
) -> bool:
    """Make ``entry`` answer the register rows its unit prints, citing them as its evidence; False
    when this entry is not one the register rows can settle (it is then left to the other folds
    and to the refusal).

    * CORRECT_WITH_EVIDENCE / OMIT_UNSUPPORTED citing nothing (the PSD .NET shape, hosted run
      43419183454: "CORRECT_WITH_EVIDENCE needs at least one fact ID as evidence") cites the rows.
    * A code block or paragraph kept as written (the Cells Java shape, hosted run 43419171411:
      ``mvn javadoc:javadoc   # generates docs/apidocs/index.html`` among true build commands)
      cites the rows and keeps everything else: it prints without exactly the lines or sentences
      the rows confirm false. Only when something is left to print (``omission_holds``); a unit
      that is nothing but false text is left to the refusal.
    """
    disposition = entry.get("disposition")
    cited = [str(fid) for fid in entry.get("fact_ids") or []]
    holds = omission_holds(unit, text, [citations[cid] for cid in ids])
    if disposition in _CITATION_NEEDED and not cited:
        pass
    elif disposition in PLACED and unit.endswith(_WITHHOLDING_KINDS):
        if all(cid in cited for cid in ids) or not holds:
            return False
    else:
        return False
    entry["fact_ids"] = [*cited, *(cid for cid in ids if cid not in cited)]
    entry["rationale"] = (_REGISTER_RATIONALE + str(entry.get("rationale") or ""))[
        :_REWRITE_RATIONALE_LIMIT
    ]
    return True


def rewrite_printed_quote(
    scope: PatchScope,
    texts: Mapping[str, str],
    quotes: Collection[str],
    original: Mapping[str, Any],
    citations: Mapping[str, str] | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any] | None] | None:
    """The last-resort ``recover`` for a reply ``reject_printed_quote`` refused: each quoted prose
    unit the reply still keeps as written is folded to VERIFIED_REWRITE, in place, keeping its
    destination and citations. No model call; ``run_job`` re-judges the folded reply through the
    same schema, binding and checks before anything is stored.

    Measured (Aspose.3D-FOSS-for-Java, hosted Lane R run 43394954743): the reviewer quoted an
    inherited Enterprise paragraph ("It adds broader format support (including glTF, FBX, USD, ...")
    printed as VERIFIED_MOVE in scope_limitations; both asks of the S4 patch handed back
    VERIFIED_MOVE and the candidate was REJECTed. VERIFIED_REWRITE is the remedy that needs no new
    fact and loses nothing: the section's authoring job re-authors the unit from verified facts
    (``authoring._placed_units`` makes it a citable unit of that section) and BC-05's
    ``obligation_failures`` still requires its must-carry substance under that disposition. The
    same lever as ``reconciliation.dispositions._fold_dangling_rewrites``; a command block, a table
    and an attributed unit are left to the refusal. ``None`` when no quoted unit qualifies."""
    quoted = [
        unit
        for unit in scope.unit_ids
        if unit.rsplit(".", 1)[-1] in _REWRITABLE_KINDS
        and any(quote and quote in texts.get(unit, "") for quote in quotes)
    ]
    cite = {
        unit: ids
        for unit in scope.unit_ids
        if (ids := _citations_for(texts.get(unit, ""), citations or {}))
    }
    if not quoted and not cite:
        return None
    stored = {
        str(entry.get("unit_id")): entry
        for entry in original.get("dispositions", [])
        if isinstance(entry, Mapping)
    }

    def recover(reply: dict[str, Any]) -> dict[str, Any] | None:
        revised = reply.get("revised_output")
        entries = revised.get("dispositions") if isinstance(revised, dict) else None
        if not isinstance(entries, list):
            return None
        by_unit = {
            str(entry.get("unit_id")): entry for entry in entries if isinstance(entry, dict)
        }
        folded = False
        for unit in dict.fromkeys([*cite, *quoted]):
            entry = by_unit.get(unit)
            if entry is None and unit in stored:
                # Left out of the reply: the merge would keep the stored disposition, so the
                # fold is applied to a copy of it, inside the patch's own units.
                entry = json.loads(json.dumps(stored[unit]))
                entries.append(entry)
                by_unit[unit] = entry
            if entry is None:
                continue
            if unit in cite and _cite_register_rows(
                unit, entry, cite[unit], texts.get(unit, ""), citations or {}
            ):
                folded = True
                continue
            if unit not in quoted or entry.get("disposition") not in _REWRITABLE_KEPT:
                continue
            entry["disposition"] = "VERIFIED_REWRITE"
            entry["rationale"] = (
                "Re-authored from the facts: the review found its text unsupported as written. "
                + str(entry.get("rationale") or "")
            )[:_REWRITE_RATIONALE_LIMIT]
            folded = True
        return reply if folded else None

    return recover


def scope_record(defect: Defect, units: Sequence[str]) -> dict[str, Any]:
    """The record a patch scope is cut from: each named unit with the details its failures carry.

    ``patch_scope`` reads the supersession-loss marker from those details (round 4, Email .NET,
    run 42188403878: a bare ``{"unit_id"}`` record hid it, so a reply that left the unit
    superseded was accepted as repaired)."""
    details: dict[str, list[str]] = {}
    for record in [defect.record, *defect.record.get("equivalent_findings", [])]:
        for failure in record.get("failures") or []:
            if isinstance(failure, Mapping) and failure.get("unit_id"):
                details.setdefault(str(failure["unit_id"]), []).append(
                    str(failure.get("detail") or "")
                )
    return {
        "failures": [
            {"unit_id": unit, "detail": " ".join(details.get(unit, []))} for unit in units
        ]
    }

def _register_citations(repository: str, quotes: Collection[str]) -> dict[str, str]:
    """``citation_id -> quote`` for the OPEN register rows of ``repository`` this defect quotes
    (BC-18's own failures carry the row's quote): the evidence the repair may cite for them."""
    wanted = {_squash(quote) for quote in quotes if quote}
    if not wanted:
        return {}
    return {
        cid: row.quote
        for cid, row in open_finding_citations(repository).items()
        if _squash(row.quote) in wanted
    }


def _citable(contract: Mapping[str, Any], citations: Mapping[str, str]) -> dict[str, Any]:
    """The patch contract with the register citations added to what a disposition may cite.

    The contract's ``fact_ids`` enum lists only facts; the defect's own register rows are the
    evidence BC-18 trusts, and binding admits them (OPEN rows of this repository only), so the
    reply -- the model's, or ``rewrite_printed_quote``'s zero-call fold -- may cite them too."""
    widened = json.loads(json.dumps(contract))
    for node in _fact_id_nodes(widened):
        items = node.get("items")
        if isinstance(items, dict) and isinstance(items.get("enum"), list):
            items["enum"] = [*items["enum"], *(c for c in citations if c not in items["enum"])]
            if isinstance(node.get("maxItems"), int):
                node["maxItems"] = max(node["maxItems"], len(citations))
        elif node.get("maxItems") == 0:
            node["items"] = {"type": "string", "enum": list(citations)}
            node["maxItems"] = len(citations)
    return widened


def _fact_id_nodes(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "fact_ids" and isinstance(value, dict):
                found.append(value)
            else:
                found.extend(_fact_id_nodes(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_fact_id_nodes(item))
    return found


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
        quote = _printed(str(record.get("quote") or ""))
        for placement in placed if quote else ():
            if quote in _printed(placement.text) and placement.unit_id not in named:
                named.append(placement.unit_id)
    if named:
        return named
    # A finding about a kept unit the README does NOT print (``disposition_coverage``, whose quote
    # is the unit's own text; ``live_readme_loss``, whose quote is a heading, block or link of it)
    # quotes the source text, which the printed form need not contain: placement unlinks an
    # intra-document link to a section the plan omits, corrects names and counts. Measured on
    # Aspose.Email-FOSS-for-Cpp, hosted Lane R run 43419173061: "030.paragraph is kept
    # (PRESERVE_ATTRIBUTED) but its text is not printed" was unrepairable, "no stored disposition
    # of an inherited unit is named by this defect". The quote is then matched against the units'
    # source text, the same field-to-field test as above; a unit with no stored disposition is
    # never named (the patch scope only revises stored dispositions).
    stored = {str(entry.get("unit_id")) for entry in rc.dispositions.get("dispositions", [])}
    for record in [defect.record, *defect.record.get("equivalent_findings", [])]:
        quote = _squash(str(record.get("quote") or ""))
        for fact in rc.facts.by_kind("inherited_unit") if quote and rc.facts else ():
            if fact.id in stored and quote in _squash(fact.value) and fact.id not in named:
                named.append(fact.id)
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
            # The stored batch as its own contract bounds it. A rationale a deterministic fold
            # wrote after the schema judged the reply (the 228-character unproven-build omission,
            # BC-02) broke that bound, and every merged revision was rejected for a unit the repair
            # never touched: "output rejected twice; last rejection:
            # revised_output.dispositions[19].rationale: '...' is too long" (hosted run
            # 43473807336, Cells C++, both of its S4 BC-18 defects). A rationale is internal --
            # never rendered, withheld from the reviewer -- so bounding it changes no README.
            output = json.loads(json.dumps(output))
            bound_rationales(output)
            keys[batch_id], stored[batch_id] = key, output
    scope = patch_scope(
        scope_record(defect, _named_units(rc, defect)),
        stored,
        batches,
        rc.facts,
        loaded,
        rc.investigation,
        rc.prompts["targeted_repair"].manifest.sampling.max_output_tokens,
    )
    if scope is None:
        # The quote is not in any inherited unit, so no disposition prints it -- but an authored
        # section may (a BC-18 check's earliest stage is RECONCILING when any of its register rows
        # is printed by a unit, and its unit-less failures ride along in one S4 defect).
        authoring = rc.prompts["section_authoring"]
        routes = _authored_routes(rc, defect, authoring)
        # What no authored unit prints but a fact's rendered summary does is a facts defect
        # (hosted run 43473803090: the member bullets "- `Borders`: Gets or sets border
        # settings." and "- `Font`: ..." led this unit-less BC-18 group).
        routed = {
            str(finding.get("quote"))
            for route in routes
            for finding in _quoted_findings(route.defect.record)
        }
        unrouted = [
            f
            for f in _quoted_findings(defect.record)
            if f.get("quote") and str(f["quote"]) not in routed
        ]
        printed = (
            _split_renderer_printed(
                rc, replace(defect, record=_finding_record(unrouted)), rc.tasks, authoring
            )[1]
            if unrouted
            else []
        )
        if routes:
            changed = _repair_routes(rc, defect, routes, repairs)
            _note_facts_defects(defect, repairs, printed)
            return changed
        if printed and len(printed) == len(unrouted):
            return _facts_defect(defect, repairs, printed)
        _unrepairable(
            defect,
            repairs,
            "no stored disposition of an inherited unit is named by this defect; a whole-batch "
            "revision would regenerate unrelated units",
        )
        _note_facts_defects(defect, repairs, printed)
        return False
    batch_facts = reconciliation_batch_facts(rc.facts, batches[scope.batch_id])
    original = stored[scope.batch_id]
    quotes = [
        str(record.get("quote") or "")
        for record in [defect.record, *defect.record.get("equivalent_findings", [])]
    ]
    texts = {fact.id: fact.value for fact in batch_facts.by_kind("inherited_unit")}
    citations = _register_citations(rc.facts.repository, quotes)
    if citations:
        scope = replace(scope, contract=_citable(scope.contract, citations))
    checks = reject_still_failing(
        patch_checks(
            scope,
            reject_printed_quote(
                refuse_noop(original, partial(reconcile_checks, facts=batch_facts)),
                scope,
                texts,
                quotes,
                rc.facts.repository,
            ),
        ),
        rc,
        defect,
        original,
        dispositions_composer(rc),
    )
    outcome = _targeted_call(
        rc,
        defect,
        loaded,
        original,
        checks,
        patch=scope,
        stage_facts=batch_facts,
        recover=bounding_rationales(
            rewrite_printed_quote(scope, texts, quotes, original, citations)
        ),
    )
    if isinstance(outcome, JobError):
        return _unrepairable(defect, repairs, str(outcome))
    return _accept(rc, defect, loaded, keys[scope.batch_id], outcome, repairs)


def bounding_rationales(
    recover: Callable[[dict[str, Any]], dict[str, Any] | None] | None,
) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    """``recover`` (an S4 patch's last-resort fold), then the reply's own over-long rationales
    bounded to the contract. A rationale is the internal record of a disposition, never printed,
    so a reply rejected only for its length is not a defect worth the fingerprint's one attempt;
    the bounded reply is re-judged by the same schema, binding and checks before it is stored."""

    def recovered(reply: dict[str, Any]) -> dict[str, Any] | None:
        folded = recover(reply) if recover is not None else None
        target = folded if folded is not None else reply
        revised = target.get("revised_output") if isinstance(target, dict) else None
        if isinstance(revised, dict) and bound_rationales(revised):
            return target
        return folded

    return recovered


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


def _regenerate_section(
    rc: RepairContext, task: SectionTask, loaded: LoadedManifest
) -> dict[str, Any] | None:
    """A fresh ``section_authoring`` call for ONE task, the same job and checks initial
    generation makes (``cascade._run_authoring``) -- see ``_regenerate_plan`` for why a missing
    call-store entry needs this rather than stopping the repair cold, and why ``run_job`` storing
    its own result is enough."""

    def checks(output: dict[str, Any]) -> list[str]:
        return unit_checks(output, task, rc.facts, rc.name, dispositions=rc.dispositions)

    def recover(output: dict[str, Any]) -> dict[str, Any] | None:
        if task.section_id == "opening":
            return recover_opening_duplicates_preserved(
                output, dispositions=rc.dispositions, facts=rc.facts
            )
        return recover_authoring_output(output, task=task, facts=rc.facts)

    try:
        result = run_job(
            loaded, task.packet, config=rc.config, facts=rc.facts, ledger=rc.ledger,
            store=rc.store, context=rc.context,
            call_schema=bound_authoring_citations(authoring_schema(loaded, task), task),
            checks=checks, recover=recover, narrow=authoring_narrowing(task, loaded),
        )
    except JobError:
        return None
    return result.output


def _task_key(rc: RepairContext, loaded: LoadedManifest, task: SectionTask) -> str:
    return request_hash(
        loaded,
        task.packet,
        bound_authoring_citations(authoring_schema(loaded, task), task),
        model=effective_model(loaded, rc.context),
    )


_OUTCOME_RANK = {"repaired": 0, "escalated": 1, "unrepairable": 2}


@dataclass(frozen=True)
class _Route:
    """One authoring task a (possibly merged) S6 defect is routed to: the task, the defect
    narrowed to the findings that task holds, and the slots those findings name by type."""

    task: SectionTask
    defect: Defect
    named_slots: frozenset[str] = frozenset()


def _named_type_slots(task: SectionTask, quote: str, facts: FactsDocument) -> set[str]:
    """The ``type:`` slots whose type a quote names: the rendered API Reference row prints the
    type's name beside the authored sentence, so a finding's quote usually carries the name and
    not the unit's exact text."""
    if not quote:
        return set()
    by_id = {fact.id: fact for fact in facts.facts}
    named: set[str] = set()
    for slot in task.slots:
        if not slot.startswith("type:"):
            continue
        fact = by_id.get(slot.removeprefix("type:"))
        if fact is None:
            continue
        short = fact.value.rsplit(".", 1)[-1]
        if re.search(rf"(?<!\w){re.escape(short)}(?!\w)", quote):
            named.add(slot)
    return named


def _route_section_defect(
    rc: RepairContext, defect: Defect, loaded: LoadedManifest
) -> list[_Route]:
    """The authoring task(s) an S6 defect's findings are about.

    ``api_reference`` has one task for its intro and hubs and one per batch of undocumented types
    (``authoring._type_batches``), all under the same section id, and a merged defect can hold
    findings about several of them. Each finding goes to the task whose stored units contain its
    quote, else to the type batch whose ``type:`` slot its quote names; a defect none of whose
    findings is located keeps the first task, as before. Measured on
    Aspose.BarCode-FOSS-for-Python (hosted run 43394959529): seventeen findings about type rows
    merged into one defect, the first (hubs) task was revised, the model returned it unchanged
    and the no-op refusal made the whole finding unrepairable.
    """
    candidates = [t for t in rc.tasks if t.section_id == defect.section_id]
    if len(candidates) <= 1:
        return [_Route(task, defect) for task in candidates]
    texts = [_task_texts(rc, loaded, task) for task in candidates]
    findings = _quoted_findings(defect.record)
    owned: dict[int, list[dict[str, Any]]] = {}
    named: dict[int, set[str]] = {}
    for finding in findings:
        quote = str(finding.get("quote") or "")
        key = _printed(quote)
        holders = [i for i, held in enumerate(texts) if key and any(key in t for t in held)]
        if not holders:
            for i, task in enumerate(candidates):
                slots = _named_type_slots(task, quote, rc.facts)
                if slots:
                    holders.append(i)
                    named.setdefault(i, set()).update(slots)
        for i in holders:
            owned.setdefault(i, []).append(finding)
    if not owned:
        return [_Route(candidates[0], defect)]
    routes: list[_Route] = []
    for i in sorted(owned):
        routes.append(
            _Route(
                candidates[i],
                replace(defect, record=_finding_record(owned[i])),
                frozenset(named.get(i, ())),
            )
        )
    return routes


def _squash(text: str) -> str:
    return " ".join(text.split())


def _printed(text: str) -> str:
    """``text`` in the form a README quote is matched against a unit: whitespace squashed and
    code-span backticks dropped on both sides.

    The renderer wraps every known identifier and file extension of an authored unit in a code
    span (``renderer``'s token code-spanning), so the stored unit "LoadFormat and SaveFormat each
    declare a single Xlsx member" prints as "`LoadFormat` and `SaveFormat` each declare ...", and a
    register quote -- README text -- never matched the unit that printed it. Measured on hosted Lane
    R runs 43473807336 (Cells C++, Scope and Limitations) and 43473803090 (Cells .NET, the Style hub
    and the samples link): "no stored disposition of an inherited unit is named by this defect",
    and an S6 repair with no unit flagged answered unchanged (the no-op refusal)."""
    return _squash(text.replace("`", ""))


def _quoted_findings(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every finding a (possibly merged) defect record carries, one per distinct quote.

    A validation defect holds all of a check's failures in one record but copies only the FIRST
    failure's quote to ``record["quote"]`` (``targeted.validation_defects``); BC-18's unit-less S4
    group of hosted run 43473803090 led with a renderer-printed member line, so every authored
    quote behind it went unrouted. Here each failure that carries its own quote is its own finding,
    with exactly its failures, details and instruction; a record whose failures carry no quote
    (a review finding, any other check) is returned as it is."""
    primary = {k: v for k, v in record.items() if k != "equivalent_findings"}
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rec in [primary, *record.get("equivalent_findings", [])]:
        failures = [
            f for f in rec.get("failures") or [] if isinstance(f, Mapping) and f.get("quote")
        ]
        if not failures:
            quote = str(rec.get("quote") or "")
            if quote and quote in seen:
                continue
            seen.add(quote)
            found.append(dict(rec))
            continue
        by_quote: dict[str, list[Mapping[str, Any]]] = {}
        for failure in failures:
            by_quote.setdefault(str(failure["quote"]), []).append(failure)
        for quote, own in by_quote.items():
            if quote in seen:
                continue
            seen.add(quote)
            found.append(
                {
                    **rec,
                    "quote": quote,
                    "instruction": " ".join(
                        dict.fromkeys(str(f.get("instruction") or "") for f in own)
                    ).strip(),
                    "failures": [dict(f) for f in own],
                    "details": list(dict.fromkeys(str(f.get("detail") or "") for f in own)),
                }
            )
    return found


def _finding_record(findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """One defect record for ``findings``: the first, the others as its equivalent findings."""
    record = dict(findings[0])
    record.pop("equivalent_findings", None)
    if len(findings) > 1:
        record["equivalent_findings"] = [dict(f) for f in findings[1:]]
    return record


def _task_texts(rc: RepairContext, loaded: LoadedManifest | None, task: SectionTask) -> list[str]:
    """What ``task``'s units print, in ``_printed`` form: its stored authoring units, and the
    coherent units of its own section and slots (the S8 coherence pass may reword a unit after
    authoring, and the README prints the coherent text)."""
    stored = rc.store.get(_task_key(rc, loaded, task)) or {}
    texts = [
        _printed(str(unit.get("text", "")))
        for unit in stored.get("units", [])
        if isinstance(unit, dict)
    ]
    coherent = getattr(rc, "units", None)
    if isinstance(coherent, Mapping):
        slots = set(task.slots)
        texts.extend(
            _printed(str(unit.get("text", "")))
            for unit in coherent.get("units", [])
            if isinstance(unit, dict)
            and unit.get("section") == task.section_id
            and unit.get("slot") in slots
        )
    return [text for text in texts if text]


#: The shortest documentation summary taken as evidence that the renderer printed a quote from it.
_MIN_PRINTED_SUMMARY = 12


def renderer_printed_facts(facts: FactsDocument | None, quote: str) -> list[str]:
    """The SUPPORTED facts whose own documentation summary the renderer prints in ``quote``.

    The API Reference's Detailed Member Reference bullets (``- `Name`: summary``) and Core API rows
    (``| `Name` | summary |``) are rendered from a ``public_symbol`` fact's ``docstring``
    (``renderer._member_summary`` / ``_symbol_description``), by no authored or inherited unit, so
    no revision of any stage output can change them: only the facts can. Measured on hosted run
    43473803090 (Cells .NET): "- `Borders`: Gets or sets border settings." is
    ``public_symbol:aspose.cells_foss.style.borders``'s docstring, while ``Style.Borders`` has a
    private setter. A fact counts when the quote holds its summary and names its short name, or
    when the quote is a long enough fragment of the summary itself."""
    if facts is None:
        return []
    wanted = _printed(quote)
    if not wanted:
        return []
    found: list[str] = []
    for fact in facts.facts:
        if fact.polarity != "SUPPORTED":
            continue
        docstring = (fact.attributes or {}).get("docstring")
        if not isinstance(docstring, str):
            continue
        summary = _printed(docstring)
        if len(summary) < _MIN_PRINTED_SUMMARY:
            continue
        short = str(fact.value).rsplit(".", 1)[-1]
        names_it = bool(short) and re.search(rf"(?<!\w){re.escape(short)}(?!\w)", wanted)
        if (summary in wanted and names_it) or (
            len(wanted) >= 2 * _MIN_PRINTED_SUMMARY and wanted in summary
        ):
            found.append(fact.id)
    return found


def _split_renderer_printed(
    rc: RepairContext,
    defect: Defect,
    tasks: Sequence[SectionTask],
    loaded: LoadedManifest | None,
) -> tuple[Defect | None, list[dict[str, Any]]]:
    """``defect`` without the findings the renderer printed from facts, and those findings.

    A finding is renderer-printed only on positive evidence: no unit of ``tasks`` prints its quote
    and ``renderer_printed_facts`` names the fact that does. The rest keep the defect's own
    fingerprint; ``None`` when nothing is left for a revision to fix."""
    findings = _quoted_findings(defect.record)
    if not any(f.get("quote") for f in findings):
        return defect, []
    held = [text for task in tasks for text in _task_texts(rc, loaded, task)]
    printed: list[dict[str, Any]] = []
    rest: list[dict[str, Any]] = []
    for finding in findings:
        quote = str(finding.get("quote") or "")
        key = _printed(quote)
        if key and not any(key in text for text in held):
            fact_ids = renderer_printed_facts(rc.facts, quote)
            if fact_ids:
                printed.append({"quote": quote, "fact_ids": fact_ids})
                continue
        rest.append(finding)
    if not printed:
        return defect, []
    if not rest:
        return None, printed
    return replace(defect, record=_finding_record(rest)), printed


def facts_defect_reason(printed: Sequence[Mapping[str, Any]]) -> str:
    """The ledger's reason for findings only the facts can fix: which fact printed which line."""
    return "; ".join(
        f"facts defect: {str(item['quote'])[:120]!r} is printed by the renderer from fact "
        f"{', '.join(item['fact_ids'])}, not by any authored or inherited unit; fix the facts "
        "(a repair cannot change renderer-printed text)"
        for item in printed
    )


def _note_facts_defects(
    defect: Defect, repairs: RepairLedger, printed: Sequence[Mapping[str, Any]]
) -> None:
    """Add the renderer-printed findings to ``defect``'s ledger entry once its routes ran."""
    entry = repairs.attempts.get(defect.fingerprint)
    if entry is None or not printed:
        return
    entry["facts_defects"] = [dict(item) for item in printed]
    note = facts_defect_reason(printed)
    entry["reason"] = f"{entry['reason']}; {note}" if entry.get("reason") else note
    repairs.write()


def _facts_defect(
    defect: Defect, repairs: RepairLedger, printed: Sequence[Mapping[str, Any]]
) -> bool:
    """Record findings only the facts can fix, with no model call: no revision changes them."""
    repairs.record(replace(defect, reason=facts_defect_reason(printed)), "unrepairable")
    repairs.attempts[defect.fingerprint]["facts_defects"] = [dict(item) for item in printed]
    repairs.write()
    return False


def _authored_routes(
    rc: RepairContext, defect: Defect, loaded: LoadedManifest
) -> list[_Route]:
    """The authoring tasks, in any section, whose stored units print one of the defect's quotes.

    For a defect routed to S4 that names no inherited unit: its quote is generated text, and the
    task whose stored units hold it is the one a repair may revise. Measured on
    Aspose.Email-FOSS-for-.Net (hosted Lane R run 43405254498): BC-18's earliest causal stage was
    RECONCILING because two of its register quotes were printed by inherited units, so its
    unit-less failures became one S4 defect naming no unit, recorded "no stored disposition of an
    inherited unit is named by this defect" -- a quote in authored prose had no path to the S6
    repair that owns it. Whitespace is squashed on both sides, as BC-18 matches the README. A quote
    no task's stored units hold (renderer-owned text) routes nowhere.
    """
    findings = [f for f in _quoted_findings(defect.record) if f.get("quote")]
    if not findings:
        return []
    routes: list[_Route] = []
    for task in rc.tasks:
        held = _task_texts(rc, loaded, task)
        mine = [
            f
            for f in findings
            if _printed(str(f["quote"])) and any(_printed(str(f["quote"])) in t for t in held)
        ]
        if not mine:
            continue
        routes.append(
            _Route(
                task,
                replace(
                    defect, stage="S6", section_id=task.section_id, record=_finding_record(mine)
                ),
            )
        )
    return routes


def _repair_section(rc: RepairContext, defect: Defect, repairs: RepairLedger) -> bool:
    if not any(t.section_id == defect.section_id for t in rc.tasks):
        return _unrepairable(defect, repairs, "no authoring task holds this section")
    loaded = rc.prompts["section_authoring"]
    # A finding whose line the renderer printed from a fact (a member bullet, a Core API row) is
    # not in any unit of this section, so a revision cannot reach it: asked anyway, the model
    # answered its section unchanged and the no-op refusal spent the fingerprint (hosted run
    # 43473803090, Cells .NET API Reference). Those findings are recorded as facts defects with no
    # call; the rest of the defect, if any, is repaired as before under the same fingerprint.
    tasks = [t for t in rc.tasks if t.section_id == defect.section_id]
    rest, printed = _split_renderer_printed(rc, defect, tasks, loaded)
    if rest is None:
        return _facts_defect(defect, repairs, printed)
    changed = _repair_routes(rc, rest, _route_section_defect(rc, rest, loaded), repairs)
    _note_facts_defects(rest, repairs, printed)
    return changed


def _repair_routes(
    rc: RepairContext, defect: Defect, routes: Sequence[_Route], repairs: RepairLedger
) -> bool:
    """Repair each routed task against its own findings; one ledger entry per fingerprint."""
    if len(routes) == 1:
        route = routes[0]
        return _repair_task(rc, route.defect, route.task, repairs, route.named_slots)
    # One fingerprint, several tasks: each is repaired against its own findings, and the one
    # ledger entry the fingerprint has says what happened to each.
    changed = False
    entries: list[tuple[SectionTask, dict[str, Any]]] = []
    for route in routes:
        changed = _repair_task(rc, route.defect, route.task, repairs, route.named_slots) or changed
        entries.append((route.task, dict(repairs.attempts.get(defect.fingerprint, {}))))
    best = min(
        (entry for _, entry in entries),
        key=lambda entry: _OUTCOME_RANK.get(str(entry.get("outcome")), len(_OUTCOME_RANK)),
    )
    merged = {
        **best,
        "label": defect.label,
        "changes": [change for _, entry in entries for change in entry.get("changes", [])],
        "reason": "; ".join(
            f"{task.label}: {entry.get('outcome')}"
            + (f" ({entry['reason']})" if entry.get("reason") else "")
            for task, entry in entries
        ),
        "tasks": [task.label for task, _ in entries],
    }
    repairs.attempts[defect.fingerprint] = merged
    repairs.write()
    return changed


def _repair_task(
    rc: RepairContext,
    defect: Defect,
    task: SectionTask,
    repairs: RepairLedger,
    named_slots: Collection[str] = (),
) -> bool:
    loaded = rc.prompts["section_authoring"]
    key = _task_key(rc, loaded, task)
    original = rc.store.get(key)
    if original is None:
        # Same gap and fix as _repair_plan's: --restore-sealed-bundle restores a previous seal's
        # call store, so a review finding against a RESTORED section has no original call in THIS
        # run's store to revise (measured live, Aspose.Slides-FOSS-for-Cpp, two hosted runs,
        # identical both times: F01-F08 all "the causing section is not in the call store",
        # discarding every other already-fixed defect too). A plain re-ask of the SAME packet at
        # this point is not enough on its own: measured on the SAME repository, a bare regenerate
        # reproduced the identical flawed prose (temperature-0 determinism over an unchanged
        # packet) and the review re-flagged the identical findings forever. So the fresh call
        # populates the store and execution falls through into the ordinary defect-aware revision
        # below, which DOES carry the finding's own quote/reason -- the thing a plain re-ask never
        # gets a chance to see.
        original = _regenerate_section(rc, task, loaded)
        if original is None:
            return _unrepairable(
                defect, repairs,
                "the causing section is not in the call store, and a fresh "
                "section_authoring call could not produce one",
            )
        defect = replace(
            defect,
            reason=(
                "the causing section was not in the call store (restored from a sealed "
                "bundle); regenerated it fresh, then revised in place against this finding"
            ),
        )
    checks: Checks = refuse_noop(
        original,
        lambda revised: unit_checks(
            revised, task, rc.facts, rc.name, dispositions=rc.dispositions
        ),
    )
    checks = reject_title_verbatim_opening(checks, task)
    checks = reject_uncarried_units(checks, task)
    quotes = [str(finding.get("quote") or "") for finding in _quoted_findings(defect.record)]
    checks = keep_unflagged_units(checks, original, quotes, named_slots)
    checks = reject_still_failing(checks, rc, defect, original, section_composer(rc, task))
    # Name the units that print the defect's text: a register quote is README text, with the code
    # spans the renderer adds, so the model could not always find it in the stored units and
    # answered its section unchanged (the no-op refusal, hosted run 43473803090).
    printed_by = sorted(str(slot) for slot in _flagged_slots(original, quotes) if slot)
    if printed_by:
        defect = replace(defect, record={**defect.record, "printed_by_slots": printed_by})
    facts = rc.facts.facts
    probe = SlotSetProbe(
        frozenset(task.slots),
        fact_sets=dict(task.slot_facts),
        fact_universe=frozenset(fact.id for fact in facts),
        neutral_facts=frozenset(
            fact.id for fact in facts if fact.kind in {"identity", "package"}
        ),
    )
    def recover(candidate: dict[str, Any]) -> dict[str, Any] | None:
        changed = False
        title_fixed = recover_title_verbatim_opening(candidate, slot_titles=task.slot_titles)
        if title_fixed is not None:
            candidate = title_fixed
            changed = True
        restated_fixed = recover_targeted_repair_restatements(
            candidate, task=task, facts=rc.facts
        )
        if restated_fixed is not None:
            candidate = restated_fixed
            changed = True
        citation_fixed = recover_targeted_repair_dropped_citation(
            candidate, original=original
        )
        if citation_fixed is not None:
            candidate = citation_fixed
            changed = True
        return candidate if changed else None

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
        recover=recover,
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
    benchmark: str = "",
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
        readme=_read_text(out_dir / "README.coherent.md"),
        units=_read_json(out_dir / "content_units.coherent.json"),
        benchmark=benchmark,
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
        "review_repair_rounds": 0,
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
            benchmark=_read_text(clone_path / "README.md"),
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
