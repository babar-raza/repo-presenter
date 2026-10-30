"""The present-equivalent orchestrator: one process runs the whole S3-S8 Lane R cascade for one
repository, under ONE :class:`~repo_presenter.core.noop_proof.Invocation`/``Ledger``.

BUILD_PRESENT_EQUIVALENT_ORCHESTRATOR (``project/state.yaml``), owner-decided 2026-10-25: three
cards (``GITHUB_ACTIONS_HOSTING_GAP_2026_10_24``, ``PORT_BUNDLE_INTEGRITY_LAYER``,
``WIRE_GATEVERIFY_TO_PORTFOLIO``) converged on the same blocker -- the old repo's own ``present``
CLI command runs facts-to-seal in one process with one ledger, which is exactly what a sealed
bundle's no-op proof needs, and this repository instead had six separate scripts
(``scripts/run_lane_r_{investigation,reconciliation,planning,authoring_real,coherence}.py`` +
``run_lane_r_render.py``), each its own process with its own ``Invocation``. The owner chose to
build the orchestrator rather than redesign the no-op proof for multiple ledgers.

This module does not replace those six scripts' own logic -- it inlines the exact same calls into
every already-ported, already-tested stage function
(``readme.investigation.dossier``/``readme.reconciliation.dispositions``/
``readme.composition.{planning,authoring,authoring_retry,coherence,renderer}``), reusing one
``FactsDocument`` (computed once, not re-derived six times in six separate processes the way the
scripts had to), one ``Invocation``/``Ledger``/``CallStore``, and writing the exact same artifact
files to ``out_dir`` the six scripts wrote, so every existing downstream reader
(``scripts/run_independent_review.py``, a future ``seal.py`` adaptation) needs no change.

Independent review runs at the end of the same process, writing ``review_verdict.json`` beside the
other final artifacts. Stage S10 is the model's review (``readme.review.llm_review``,
``plans/PLAN_independent_llm_reviewer.md`` D7): it runs once per candidate version, only when no
deterministic rule and no blocking check rejects the candidate; its blocking findings are routed by
causal stage into the same repair (``review_repair_rounds`` rounds at most, each re-review a counted
call on the one ledger), and a candidate that still blocks is BLOCKED with the verdict's exact
findings. A review that cannot be obtained raises ``ReviewUnavailable``.

S4 runs ``dispositions.reconcile_checks`` (normalize, then placement_errors) as the reconciliation
job's own checks, and S9 follows the render:
the kept units the renderer did not print are accounted (``readme.repair.accounting``), the ported
blocking checks run (``validation.json``), and a failure whose causal stage any of S4/S5/S6 names is
repaired by that stage's own revision (a per-unit reconciliation patch, a plan revision, or a section
revision -- ``readme.repair.loop.repair_defect``'s own dispatch) and the cascade runs again from the
call store, at most ``max_rounds`` passes, all under the one invocation. Measured on
aspose-3d-foss/Aspose.3D-FOSS-for-.NET (hosted run 40464255814): the reviewer's twelve findings on
kept-but-unprinted units stood because neither step existed. A second measurement, aspose-cells-foss/
Aspose.Cells-FOSS-for-Cpp (hosted runs 40571540396, 40679621466): a structural check (BC-12, causal
stage COMPOSING/S6) failed identically both runs and was never attempted here at all, because this
loop used to repair S4 defects only -- widened to every stage ``repair_defect`` supports, the same
``defect.repairable`` test S10's own repair routing already applies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_presenter.core.config import GatewayConfig
from repo_presenter.core.facts import FactsDocument, read_facts, write_facts
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import PromptRegistry, load_manifests
from repo_presenter.core.noop_proof import Invocation, measure_invocation
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.authoring import (
    authoring_schema,
    authoring_tasks,
    merge_units,
    recover_opening_duplicates_preserved,
    unit_checks,
    write_content_units,
)
from repo_presenter.readme.composition.authoring_retry import (
    authoring_narrowing,
    recover_authoring_output,
)
from repo_presenter.readme.composition.coherence import (
    apply_coherence,
    coherence_batch_units,
    coherence_batches,
    coherence_checks,
    coherence_packet,
    coherence_schema,
    recover_coherence_regressions,
)
from repo_presenter.readme.composition.components.identity import product_name
from repo_presenter.readme.composition.planning import (
    plan_checks,
    planning_packet,
    planning_schema,
    write_plan,
)
from repo_presenter.readme.composition.renderer import render_patch, render_readme
from repo_presenter.readme.evidence.facts.inherited import inherited_unit_facts
from repo_presenter.readme.investigation.dossier import (
    investigation_packet,
    investigation_schema,
    write_investigation,
)
from repo_presenter.readme.reconciliation.dispositions import (
    coordinate_neighbor_promises,
    merge_dispositions,
    reconcile_checks,
    reconciliation_batch_facts,
    reconciliation_batches,
    reconciliation_narrowing,
    reconciliation_packet,
    reconciliation_schema,
    write_dispositions,
)
from repo_presenter.readme.reconciliation.retained_examples import (
    retain_unverified_examples,
)
from repo_presenter.readme.repair.accounting import (
    ACCOUNTING_FILENAME,
    Accounted,
    account_unprinted_units,
    accounting_document,
)
from repo_presenter.readme.repair.targeted import (
    MAX_ROUNDS,
    REPAIRS_FILENAME,
    Defect,
    RepairLedger,
    merge_equivalent,
    validation_defects,
)
from repo_presenter.readme.review.defect_bridge import build_defects
from repo_presenter.readme.review.independent_reviewer import (
    REVIEW_VERDICT_FILENAME,
    ReviewVerdict,
    review_candidate,
    write_review_verdict,
)
from repo_presenter.readme.review.llm_review import (
    MAX_REVIEW_REPAIR_ROUNDS,
    review_with_model,
)
from repo_presenter.readme.validation.blocking import (
    blocking_failures,
    validate_candidate,
)
from repo_presenter.readme.validation.failures import Candidate

DEFAULT_PROMPTS_PATH = Path("prompts")
COMPOSED_DISPOSITIONS_FILENAME = "dispositions.composed.json"
DEFAULT_REGISTRY_PATH = Path("data/registry.json")


@dataclass(frozen=True)
class CascadeResult:
    """Everything a caller (a thin CLI, a future hosted workflow step) needs after one full
    S3-S8 run: the one invocation that made every provider call, where every artifact landed,
    the independent reviewer's own verdict on the result, and -- for a caller that wants to seal
    this result (readme.bundle.seal.seal_candidate) -- the registry entry and the final
    FactsDocument this run actually consumed, so sealing never has to re-derive them."""

    repository: str
    source_revision: str
    invocation: Invocation
    provider_calls: int
    out_dir: Path
    facts_path: Path
    readme_path: Path
    review_verdict: ReviewVerdict
    entry: RegistryEntry
    document: FactsDocument
    validation: dict[str, Any]
    accounted: tuple[Accounted, ...]
    rounds: int


def _tree_paths(root: Path) -> list[str]:
    paths = []
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def _document_with_inherited_units(
    repository: str, base: FactsDocument, source_revision: str, clone_path: Path
) -> FactsDocument:
    """The one real inherited-unit merge this process needs -- computed once, not re-derived by
    every stage the way six separate processes each had to."""
    tree_paths = _tree_paths(clone_path)
    readme_bytes = (clone_path / "README.md").read_bytes()
    public_symbol_facts = [f for f in base.facts if f.kind == "public_symbol"]
    inherited = inherited_unit_facts("README.md", readme_bytes, public_symbol_facts, tree_paths)
    kept = tuple(f for f in base.facts if f.kind != "inherited_unit")
    return FactsDocument(repository, source_revision, (*kept, *inherited))


def _run_investigation(
    *, entry: RegistryEntry, document: FactsDocument, prompts: PromptRegistry,
    config: GatewayConfig, ledger: Ledger, store: CallStore, context: JobContext,
) -> dict:
    loaded = prompts["repository_investigation"]
    packet = investigation_packet(entry, document, loaded.manifest)
    call_schema = investigation_schema(loaded, document)
    result = run_job(
        loaded, packet, config=config, facts=document, ledger=ledger, store=store,
        context=context, call_schema=call_schema,
    )
    return result.output


def _run_reconciliation(
    *, entry: RegistryEntry, document: FactsDocument, investigation: dict,
    prompts: PromptRegistry, config: GatewayConfig, ledger: Ledger, store: CallStore,
    context: JobContext,
) -> dict:
    loaded = prompts["source_reconciliation"]
    batches = reconciliation_batches(document, loaded.manifest.sampling.max_output_tokens)
    outputs = []
    for _batch_id, batch_units in batches:
        batch_facts = reconciliation_batch_facts(document, batch_units)
        packet = reconciliation_packet(entry, batch_facts, investigation, loaded.manifest, batch_units)
        call_schema = reconciliation_schema(loaded, batch_units, batch_facts, investigation)

        def checks(output: dict, batch_facts=batch_facts) -> list[str]:
            # reconcile_checks, not normalize alone: this job's own docstring at the top of this
            # file already says "S4 runs dispositions.normalize as the reconciliation job's own
            # checks" -- true of this orchestrator but not of placement_errors(), which
            # normalize() alone never runs. Measured live (aspose-cells-foss/Aspose.Cells-FOSS-
            # for-Java, hosted run 40723588078): an OMIT_UNSUPPORTED on a real paragraph and code
            # block, both citing no fact at all, was accepted here unchecked -- placement_errors()
            # run directly against the same facts and dispositions catches it immediately (and 7
            # more like it) as uncited_prose_omit. The content then surfaced three stages later as
            # a deterministic "live content lost" block (S10's own preservation holdout), the
            # defect having already slipped past the one stage built to catch it at its source.
            return reconcile_checks(output, batch_facts)

        # reconciliation_narrowing, not the plain silence-only callable this replaced: a
        # rejection-aware third ask for exactly the units a rejection names, whether their
        # disposition was missing entirely or simply wrong, leaving every other unit's own
        # already-correct entry untouched. Measured live why the plain, silence-only form is not
        # enough on its own (aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 41090058316): a
        # prompt fix that correctly resolved three named units' wrong dispositions also flipped a
        # fourth, previously-correct sibling's answer, because the universal re-ask regenerates
        # the WHOLE batch rather than touching only what was named.
        narrow = reconciliation_narrowing(entry, batch_units, batch_facts, investigation, loaded)

        result = run_job(
            loaded, packet, config=config, facts=batch_facts, ledger=ledger, store=store,
            context=context, call_schema=call_schema, checks=checks, narrow=narrow,
        )
        outputs.append(result.output)
    # coordinate_neighbor_promises is documented (dispositions.py's own module docstring, and its
    # own docstring: "Runs once, after merge_dispositions() folds every batch into one flat
    # document -- the one point a neighbor's own final disposition is visible regardless of
    # which batch produced it") to run exactly here -- it never had, in this orchestrator.
    # Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-Java, run 41068618078): a lead-in
    # paragraph ("Gradle (Groovy DSL):") was VERIFIED_MOVE into quick_start while the code block
    # it introduces was independently OMIT_UNSUPPORTED with no destination -- a lead-in moved
    # without its payload, BC-07's own dangling-colon check catching what this function exists to
    # prevent at the source.
    merged = retain_unverified_examples(merge_dispositions(outputs), document)
    return coordinate_neighbor_promises(merged, document)


def _run_planning(
    *, entry: RegistryEntry, document: FactsDocument, investigation: dict, dispositions: dict,
    ecosystem: str, prompts: PromptRegistry, config: GatewayConfig, ledger: Ledger,
    store: CallStore, context: JobContext,
) -> dict:
    loaded = prompts["presentation_planning"]
    packet = planning_packet(entry, document, investigation, dispositions, loaded.manifest)
    call_schema = planning_schema(loaded, document, investigation, dispositions)

    def checks(output: dict) -> list[str]:
        return plan_checks(output, document, dispositions=dispositions, ecosystem=ecosystem)

    result = run_job(
        loaded, packet, config=config, facts=document, ledger=ledger, store=store,
        context=context, call_schema=call_schema, checks=checks,
    )
    return result.output


def _run_authoring(
    *, entry: RegistryEntry, document: FactsDocument, investigation: dict, dispositions: dict,
    plan: dict, prompts: PromptRegistry, config: GatewayConfig, ledger: Ledger, store: CallStore,
    context: JobContext,
) -> dict:
    loaded = prompts["section_authoring"]
    name = product_name(entry)
    tasks = authoring_tasks(entry, document, investigation, dispositions, plan)
    outputs: dict[str, dict] = {}
    for task in tasks:
        call_schema = authoring_schema(loaded, task)

        def checks(output: dict, task=task) -> list[str]:
            return unit_checks(output, task, document, name, dispositions=dispositions)

        def recover(output: dict, task=task) -> dict | None:
            if task.section_id == "opening":
                return recover_opening_duplicates_preserved(
                    output, dispositions=dispositions, facts=document
                )
            return recover_authoring_output(output, task=task, facts=document)

        result = run_job(
            loaded, task.packet, config=config, facts=document, ledger=ledger, store=store,
            context=context, call_schema=call_schema, checks=checks, recover=recover,
            narrow=authoring_narrowing(task, loaded),
        )
        outputs[task.label] = result.output
    return merge_units(outputs)


def _run_coherence(
    *, entry: RegistryEntry, document: FactsDocument, investigation: dict, dispositions: dict,
    plan: dict, units_document: dict, pre_coherence_readme: str, prompts: PromptRegistry,
    config: GatewayConfig, ledger: Ledger, store: CallStore, context: JobContext,
) -> dict:
    loaded = prompts["section_authoring"]
    name = product_name(entry)
    tasks = authoring_tasks(entry, document, investigation, dispositions, plan)
    batches = coherence_batches(tasks)
    current = units_document
    for _batch_id, batch_tasks in batches:
        existing = coherence_batch_units(current.get("units", []), batch_tasks)
        packet = coherence_packet(entry, pre_coherence_readme, current, batch_tasks, document)
        call_schema = coherence_schema(loaded, existing, batch_tasks)

        def checks(output: dict, batch_tasks=batch_tasks, existing=existing) -> list[str]:
            return coherence_checks(
                output, batch_tasks, document, name, existing_units=existing,
                prior_omitted=current.get("omitted", []), dispositions=dispositions,
            )

        def recover(output: dict, batch_tasks=batch_tasks, existing=existing) -> dict | None:
            return recover_coherence_regressions(
                output, existing_units=existing, facts=document, tasks=batch_tasks,
                dispositions=dispositions,
            )

        result = run_job(
            loaded, packet, config=config, facts=document, ledger=ledger, store=store,
            context=context, call_schema=call_schema, checks=checks, recover=recover,
        )
        current, _revised = apply_coherence(current, result.output)
    return current


@dataclass(frozen=True)
class _Composition:
    """One pass over S4-S8 and the S9 accounting: the dispositions the README was finally rendered
    with, and everything the validation and the reviewer read."""

    dispositions: dict[str, Any]
    plan: dict[str, Any]
    units_document: dict[str, Any]
    coherent_units: dict[str, Any]
    readme: str
    tasks: list[Any]
    accounted: list[Accounted]


def _candidate(
    entry: RegistryEntry, document: FactsDocument, plan: dict, units: dict, dispositions: dict,
    readme: str, tree_paths: list[str], tasks: list[Any],
) -> Candidate:
    """What the blocking checks read. ``original_readme`` is left unset: BC-01 compares it with the
    snapshot's README digest, which Lane L holds and the cascade is not handed, and a digest taken
    here from the same bytes would pass by construction."""
    return Candidate(
        entry=entry,
        facts=document,
        plan=plan,
        units=units,
        dispositions=dispositions,
        readme=readme,
        original_readme=None,
        source_revision=document.source_revision,
        readme_sha256=None,
        tree_paths=tree_paths,
        tasks=tasks,
    )


def _compose(
    *, entry: RegistryEntry, document: FactsDocument, investigation: dict, ecosystem: str,
    tree_paths: list[str], original_bytes: bytes, out_dir: Path, prompts: PromptRegistry,
    config: GatewayConfig, ledger: Ledger, store: CallStore, context: JobContext,
) -> _Composition:
    """S4 through S8, then account for the kept units the render does not print (S9).

    Every artifact lands in ``out_dir``; a repaired S4 batch is read back from the call store, so
    a second pass asks the provider only for what the repair changed."""
    common = {"config": config, "ledger": ledger, "store": store, "context": context}
    dispositions = _run_reconciliation(
        entry=entry, document=document, investigation=investigation, prompts=prompts, **common
    )
    write_dispositions(dispositions, out_dir / "dispositions.json")
    # What the planning, authoring and coherence calls are made from. dispositions.json is
    # rewritten below with the S9 accounting, so a repair that rebuilds those calls' request
    # hashes from disk reads this one, or every rebuilt hash would miss the call store.
    write_dispositions(dispositions, out_dir / COMPOSED_DISPOSITIONS_FILENAME)

    plan = _run_planning(
        entry=entry, document=document, investigation=investigation, dispositions=dispositions,
        ecosystem=ecosystem, prompts=prompts, **common,
    )
    write_plan(plan, out_dir / "plan.json")

    units_document = _run_authoring(
        entry=entry, document=document, investigation=investigation, dispositions=dispositions,
        plan=plan, prompts=prompts, **common,
    )
    write_content_units(units_document, out_dir / "content_units.json")

    pre_coherence_readme = render_readme(entry, document, plan, units_document, dispositions)
    original = original_bytes.decode("utf-8", errors="replace")
    (out_dir / "README.rendered.md").write_text(pre_coherence_readme, encoding="utf-8", newline="\n")
    (out_dir / "README.patch.diff").write_text(
        render_patch(original, pre_coherence_readme), encoding="utf-8", newline="\n"
    )

    coherent_units = _run_coherence(
        entry=entry, document=document, investigation=investigation, dispositions=dispositions,
        plan=plan, units_document=units_document, pre_coherence_readme=pre_coherence_readme,
        prompts=prompts, **common,
    )
    final_readme = render_readme(entry, document, plan, coherent_units, dispositions)
    tasks = authoring_tasks(entry, document, investigation, dispositions, plan)
    candidate = _candidate(
        entry, document, plan, coherent_units, dispositions, final_readme, tree_paths, tasks
    )
    settled, accounted = account_unprinted_units(candidate)
    if accounted:
        if render_readme(entry, document, plan, coherent_units, settled) == final_readme:
            dispositions = settled
        else:
            accounted = []  # accounting must not change what renders; a change is not applied
    write_dispositions(dispositions, out_dir / "dispositions.json")
    (out_dir / ACCOUNTING_FILENAME).write_text(
        json.dumps(accounting_document(accounted), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (out_dir / "content_units.coherent.json").write_text(
        json.dumps(coherent_units, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (out_dir / "README.coherent.md").write_text(final_readme, encoding="utf-8", newline="\n")
    return _Composition(
        dispositions, plan, units_document, coherent_units, final_readme, tasks, accounted
    )


def _settle_defects(
    *, composed: _Composition, validation: dict[str, Any], verdict: ReviewVerdict,
    entry: RegistryEntry, document: FactsDocument, prompts: PromptRegistry,
) -> list[Defect]:
    """The defects of this pass that ``repair_defect`` (``readme.repair.loop``) may act on: every
    failing blocking check, routed to whichever causal stage it names -- S4 reconciliation, S5
    planning, or S6 authoring, exactly the three ``repair_defect`` dispatches on -- and the
    (deterministic) reviewer's own findings on a kept unit (``review.defect_bridge``).

    Not S4 alone: a structural check (e.g. BC-12, causal stage COMPOSING/S6) that names an
    LLM-owned section is exactly as repairable as an S4 disposition defect, and the two hosted
    aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp runs (40571540396, 40679621466) proved what
    withholding that chance costs: BC-12 failed identically on 'development_testing' every round
    of both runs (confirmed from each run's own downloaded validation.json), yet was computed by
    ``validation_defects`` and then silently discarded here before a repair was ever attempted --
    the only reason one run's failure message named a different (also real, now-fixed) defect
    instead of BC-12 is that ``present.py`` raises on the first blocking condition it finds, not
    that BC-12 ever had a repair chance in either run. The outer S10 loop cannot make up the
    difference either: ``run_cascade`` never even calls the model while a blocking check fails, so
    a non-S4 blocking check had no path to a bounded repair at all. A non-repairable stage (S3, or
    none) still falls out exactly as before -- this only widens which *repairable* stages reach
    the loop, the same ``defect.repairable`` test ``_review_defects`` already applies to the
    reviewer's own findings."""
    repairer = prompts["targeted_repair"].sha256
    units = composed.coherent_units.get("units", [])
    llm_sections = {str(unit["section"]) for unit in units if unit.get("section")}
    found = [
        *validation_defects(validation, llm_sections, repairer),
        *build_defects(
            verdict,
            units=units,
            plan=composed.plan,
            dispositions=composed.dispositions,
            facts=document,
            ecosystem=entry.ecosystem,
            repairer=repairer,
        ),
    ]
    return [defect for defect in found if defect.repairable]


def _repair_defects(
    *, defects: list[Defect], composed: _Composition, investigation: dict, entry: RegistryEntry,
    document: FactsDocument, prompts: PromptRegistry, config: GatewayConfig, ledger: Ledger,
    store: CallStore, context: JobContext, repairs: RepairLedger,
) -> bool:
    """One targeted repair per fresh defect, each a ``run_job`` call routed by its own causal
    stage (``repair.loop.repair_defect``: S4's per-unit patch, S5's plan revision, or S6's section
    revision). True when a stored stage output changed, which is what makes another pass worth
    making. Already stage-agnostic before this fix -- ``run_cascade``'s own S10 loop already calls
    this with S4/S5/S6 defects from ``_review_defects``; only its *caller inside the S9 settle
    loop* (``_settle_defects``, née ``_s4_defects``) used to withhold everything but S4."""
    from repo_presenter.readme.repair.loop import RepairContext, repair_defect

    rc = RepairContext(
        entry=entry, facts=document, prompts=prompts, config=config, ledger=ledger, store=store,
        context=context, investigation=investigation, dispositions=composed.dispositions,
        plan=composed.plan, tasks=composed.tasks, name=product_name(entry),
    )
    fresh = merge_equivalent([d for d in defects if not repairs.attempted(d.fingerprint)])
    for defect in defects:
        if repairs.attempted(defect.fingerprint):
            repairs.note_re_raised(defect)
    changed = [repair_defect(rc, defect, repairs) for defect in fresh]  # every one is attempted
    return any(changed)


@dataclass(frozen=True)
class _Settled:
    """The result of the S4-S9 passes: the last composition, the validation and the deterministic
    verdict that judged it, and how many passes it took."""

    composed: _Composition
    validation: dict[str, Any]
    verdict: ReviewVerdict
    rounds: int


def _settle_s9(
    *, entry: RegistryEntry, document: FactsDocument, investigation: dict, ecosystem: str,
    tree_paths: list[str], original_bytes: bytes, original: str, out_dir: Path,
    prompts: PromptRegistry, config: GatewayConfig, ledger: Ledger, store: CallStore,
    context: JobContext, repairs: RepairLedger, max_rounds: int,
) -> _Settled:
    """Compose, validate and review deterministically, repairing S4 defects, until nothing fresh
    is repairable or ``max_rounds`` passes have been made. No model reviews here (S10 follows)."""
    rounds = 0
    while True:
        rounds += 1
        composed = _compose(
            entry=entry, document=document, investigation=investigation, ecosystem=ecosystem,
            tree_paths=tree_paths, original_bytes=original_bytes, out_dir=out_dir,
            prompts=prompts, config=config, ledger=ledger, store=store, context=context,
        )
        candidate = _candidate(
            entry, document, composed.plan, composed.coherent_units, composed.dispositions,
            composed.readme, tree_paths, composed.tasks,
        )
        validation = validate_candidate(candidate, out_dir, [])
        verdict = review_candidate(
            readme_text=composed.readme, units=composed.coherent_units.get("units", []),
            facts=document, dispositions=composed.dispositions, original_readme=original,
        )
        write_review_verdict(verdict, out_dir / REVIEW_VERDICT_FILENAME)
        if rounds >= max_rounds:
            break
        defects = _settle_defects(
            composed=composed, validation=validation, verdict=verdict, entry=entry,
            document=document, prompts=prompts,
        )
        if not defects or not _repair_defects(
            defects=defects, composed=composed, investigation=investigation, entry=entry,
            document=document, prompts=prompts, config=config, ledger=ledger, store=store,
            context=context, repairs=repairs,
        ):
            break
    return _Settled(composed, validation, verdict, rounds)


def _review_defects(
    *, settled: _Settled, verdict: ReviewVerdict, entry: RegistryEntry, document: FactsDocument,
    prompts: PromptRegistry, repairs: RepairLedger,
) -> list[Defect]:
    """The repairable defects of the model's blocking findings, routed by their causal stage
    (``review.defect_bridge``). A finding no stage may revise is recorded unrepairable."""
    composed = settled.composed
    defects = build_defects(
        verdict,
        units=composed.coherent_units.get("units", []),
        plan=composed.plan,
        dispositions=composed.dispositions,
        facts=document,
        ecosystem=entry.ecosystem,
        repairer=prompts["targeted_repair"].sha256,
    )
    for defect in defects:
        if not defect.repairable and not repairs.attempted(defect.fingerprint):
            repairs.record(defect, "unrepairable")
    return [defect for defect in defects if defect.repairable]


def run_cascade(
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
    review_repair_rounds: int = MAX_REVIEW_REPAIR_ROUNDS,
) -> CascadeResult:
    """Run S3 (investigation) through S8 (coherence), the S9 validation and the independent
    review, for one repository, as one process under one invocation. Writes the same artifact
    files the six separate scripts wrote (``investigation.json``, ``dispositions.json``,
    ``plan.json``, ``content_units.json``, ``content_units.coherent.json``, ``README.rendered.md``,
    ``README.coherent.md``, ``README.patch.diff``, ``review_verdict.json``) under ``out_dir``,
    plus ``validation.json``, ``accounting.json`` and ``repairs.json``, and ``facts.json`` (with
    the real inherited-unit facts merged in) at ``facts_path``.

    S9, after every pass: the kept inherited units the renderer did not print are accounted
    (``readme.repair.accounting``, deterministic and render-preserving); the ported blocking checks
    (``readme.validation.blocking``) and the reviewer then judge the README. A failure whose cause
    is S4 is repaired as a per-unit patch of the stored S4 batch (``readme.repair.loop``), and the
    cascade runs again from the call store, until nothing fresh is repairable or ``max_rounds``
    passes have been made. Every repair is a ``run_job`` call on this same ledger, so the
    invocation stays the one that made every provider call.

    S10: when S9 leaves no deterministic blocking finding, the independent reviewer (its own job, prompt and ledger attribution) reviews the
    candidate (one provider call, two when it needed the one re-ask). Its blocking findings are
    repaired by their causal stage and the candidate re-composed and re-reviewed, at most
    ``review_repair_rounds`` times; ``0`` leaves the repair to the caller (``repair.loop``).
    """
    from repo_presenter.readme.repair.loop import composition_hash

    plugin_for(ecosystem)
    base_document = read_facts(facts_path)
    source_revision = run_git(["rev-parse", "HEAD"], cwd=clone_path).stdout.strip()
    document = _document_with_inherited_units(repository, base_document, source_revision, clone_path)

    prompts = load_manifests(prompts_path)
    repo_registry = load_registry(registry_path)
    entry = require_listed(repo_registry, repository)

    workspace = out_dir / "llm_cache"
    invocation = Invocation.begin()
    ledger_path = workspace / "ledger.jsonl"
    ledger = Ledger(ledger_path, invocation_id=invocation.invocation_id)
    store = CallStore(workspace / "calls")
    context = JobContext(repository=repository, source_revision=source_revision)

    investigation = _run_investigation(
        entry=entry, document=document, prompts=prompts, config=config, ledger=ledger,
        store=store, context=context,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    write_investigation(investigation, out_dir / "investigation.json")

    original_bytes = (clone_path / "README.md").read_bytes()
    original = original_bytes.decode("utf-8", errors="replace")
    tree_paths = _tree_paths(clone_path)
    repairs = RepairLedger(
        out_dir / REPAIRS_FILENAME, composition=composition_hash(source_revision, document, prompts)
    )
    write_facts(document, facts_path)

    settle = {
        "entry": entry, "document": document, "investigation": investigation,
        "ecosystem": ecosystem, "tree_paths": tree_paths, "original_bytes": original_bytes,
        "original": original, "out_dir": out_dir, "prompts": prompts, "config": config,
        "ledger": ledger, "store": store, "context": context, "repairs": repairs,
        "max_rounds": max_rounds,
    }
    settled = _settle_s9(**settle)
    rounds = settled.rounds
    verdict = settled.verdict
    review_rounds = 0
    while not verdict.blocking_findings and not blocking_failures(settled.validation):
        # S10 (plan D7): the model reviews only a candidate no deterministic rule or blocking
        # check rejects, once per candidate version. ReviewUnavailable propagates: no valid
        # review, no verdict that could be sealed.
        verdict = review_with_model(
            prompts=prompts, config=config, ledger=ledger, store=store, context=context,
            candidate_readme=settled.composed.readme, original_readme=original, facts=document,
            plan=settled.composed.plan, dispositions=settled.composed.dispositions,
            validation=settled.validation, deterministic_findings=verdict.findings,
        )
        write_review_verdict(verdict, out_dir / REVIEW_VERDICT_FILENAME)
        if verdict.verdict == "ACCEPT" or review_rounds >= review_repair_rounds:
            break
        defects = _review_defects(
            settled=settled, verdict=verdict, entry=entry, document=document, prompts=prompts,
            repairs=repairs,
        )
        if not defects or not _repair_defects(
            defects=defects, composed=settled.composed, investigation=investigation, entry=entry,
            document=document, prompts=prompts, config=config, ledger=ledger, store=store,
            context=context, repairs=repairs,
        ):
            break
        review_rounds += 1
        settled = _settle_s9(**settle)
        rounds += settled.rounds
        verdict = settled.verdict
    composed, validation = settled.composed, settled.validation
    (out_dir / "validation.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    invocation.attach_ledger(repository, ledger_path)
    invocation_record_path = workspace / "invocations" / f"{invocation.invocation_id}.json"
    invocation.write(invocation_record_path, Path("."), 0)

    measured = measure_invocation(ledger_path, invocation.invocation_id)
    return CascadeResult(
        repository=repository,
        source_revision=source_revision,
        invocation=invocation,
        provider_calls=measured.provider_calls,
        out_dir=out_dir,
        facts_path=facts_path,
        readme_path=out_dir / "README.coherent.md",
        review_verdict=verdict,
        entry=entry,
        document=document,
        validation=validation,
        accounted=tuple(composed.accounted),
        rounds=rounds,
    )
