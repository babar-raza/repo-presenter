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

Independent review (``readme.review.independent_reviewer``) runs at the end of the same process,
writing ``review_verdict.json`` beside the other final artifacts -- not a separate pass any more.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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
    recover_restating_sentences,
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
    merge_dispositions,
    reconciliation_batch_facts,
    reconciliation_batches,
    reconciliation_packet,
    reconciliation_schema,
    write_dispositions,
)
from repo_presenter.readme.reconciliation.retained_examples import retain_unverified_examples
from repo_presenter.readme.review.independent_reviewer import (
    REVIEW_VERDICT_FILENAME,
    ReviewVerdict,
    review_candidate,
    write_review_verdict,
)

DEFAULT_PROMPTS_PATH = Path("prompts")
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
        result = run_job(
            loaded, packet, config=config, facts=batch_facts, ledger=ledger, store=store,
            context=context, call_schema=call_schema,
        )
        outputs.append(result.output)
    return retain_unverified_examples(merge_dispositions(outputs), document)


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
            return recover_restating_sentences(output, task=task, facts=document)

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
) -> CascadeResult:
    """Run S3 (investigation) through S8 (coherence) plus the independent review, for one
    repository, as one process under one invocation. Writes the same artifact files the six
    separate scripts wrote (``investigation.json``, ``dispositions.json``, ``plan.json``,
    ``content_units.json``, ``content_units.coherent.json``, ``README.rendered.md``,
    ``README.coherent.md``, ``README.patch.diff``, ``review_verdict.json``) under ``out_dir``,
    and ``facts.json`` (with the real inherited-unit facts merged in) at ``facts_path``.
    """
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

    dispositions = _run_reconciliation(
        entry=entry, document=document, investigation=investigation, prompts=prompts,
        config=config, ledger=ledger, store=store, context=context,
    )
    write_dispositions(dispositions, out_dir / "dispositions.json")

    plan = _run_planning(
        entry=entry, document=document, investigation=investigation, dispositions=dispositions,
        ecosystem=ecosystem, prompts=prompts, config=config, ledger=ledger, store=store,
        context=context,
    )
    write_plan(plan, out_dir / "plan.json")

    units_document = _run_authoring(
        entry=entry, document=document, investigation=investigation, dispositions=dispositions,
        plan=plan, prompts=prompts, config=config, ledger=ledger, store=store, context=context,
    )
    write_content_units(units_document, out_dir / "content_units.json")

    pre_coherence_readme = render_readme(entry, document, plan, units_document, dispositions)
    original = (clone_path / "README.md").read_bytes().decode("utf-8", errors="replace")
    (out_dir / "README.rendered.md").write_text(pre_coherence_readme, encoding="utf-8", newline="\n")
    (out_dir / "README.patch.diff").write_text(
        render_patch(original, pre_coherence_readme), encoding="utf-8", newline="\n"
    )

    coherent_units = _run_coherence(
        entry=entry, document=document, investigation=investigation, dispositions=dispositions,
        plan=plan, units_document=units_document, pre_coherence_readme=pre_coherence_readme,
        prompts=prompts, config=config, ledger=ledger, store=store, context=context,
    )
    final_readme = render_readme(entry, document, plan, coherent_units, dispositions)
    (out_dir / "content_units.coherent.json").write_text(
        json.dumps(coherent_units, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    readme_path = out_dir / "README.coherent.md"
    readme_path.write_text(final_readme, encoding="utf-8", newline="\n")

    facts_hash = write_facts(document, facts_path)
    del facts_hash  # returned for callers that want it; not needed further here

    verdict = review_candidate(
        readme_text=final_readme, units=coherent_units.get("units", []), facts=document,
        dispositions=dispositions, original_readme=original,
    )
    write_review_verdict(verdict, out_dir / REVIEW_VERDICT_FILENAME)

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
        readme_path=readme_path,
        review_verdict=verdict,
        entry=entry,
        document=document,
    )
