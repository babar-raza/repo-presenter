"""Fire the real coherence (S8) LLM call(s) end-to-end, no agent reasoning.

Usage:
    python scripts/run_lane_r_coherence.py <owner>/<repo> <ecosystem> <clone_path>

Wires: the real, already-rendered README (render_readme, from the accepted content_units.json)
-> readme/composition/coherence.py's coherence_packet/coherence_schema/coherence_checks (all
already fully ported, but never fired by any script before now) -> core/llm/jobs.py's run_job,
once per batch of LLM-owned sections, merged with apply_coherence -> re-rendered.

This is the real mechanism named explicitly in dispositions.py's own docstring
(coordinate_neighbor_promises: "BC-10 coherence-gap... REJECT_PRESENTATION, moving key factual
content out of its original context") for catching exactly the duplicate-opening-paragraph
defect both full cascade runs (lane_r_first_full_cascade/, lane_r_second_full_cascade/) measured
-- not a render-time patch invented without the real system's own review stage.

Requires run_lane_r_investigation.py, run_lane_r_reconciliation.py, run_lane_r_planning.py, and
run_lane_r_authoring_real.py to have been run first for the same repository.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.config import load_gateway_config
from repo_presenter.core.facts import FactsDocument, read_facts
from repo_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.authoring import authoring_tasks
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
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.evidence.facts.inherited import inherited_unit_facts


def _tree_paths(root: Path) -> list[str]:
    paths = []
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def main() -> None:
    repository, ecosystem, clone_path_arg = sys.argv[1], sys.argv[2], sys.argv[3]
    clone_path = Path(clone_path_arg)
    repo_dir = repository.replace("/", "__")
    plugin_for(ecosystem)
    facts_path = Path("evidence/build/P2_REAL_ENGINE_SALVAGE") / repo_dir / "facts.json"
    out_dir = Path("scripts/_lane_r_output") / repo_dir

    print(f"[1/6] reading the real S3-S6 artifacts from {out_dir}")
    base_document = read_facts(facts_path)
    investigation = json.loads((out_dir / "investigation.json").read_text(encoding="utf-8"))
    dispositions = json.loads((out_dir / "dispositions.json").read_text(encoding="utf-8"))
    plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
    units_document = json.loads((out_dir / "content_units.json").read_text(encoding="utf-8"))

    tree_paths = _tree_paths(clone_path)
    readme_bytes = (clone_path / "README.md").read_bytes()
    public_symbol_facts = [f for f in base_document.facts if f.kind == "public_symbol"]
    inherited = inherited_unit_facts("README.md", readme_bytes, public_symbol_facts, tree_paths)
    document = FactsDocument(repository, base_document.source_revision, (*base_document.facts, *inherited))

    repo_registry = load_registry(Path("data/registry.json"))
    entry = require_listed(repo_registry, repository)
    name = product_name(entry)

    print("[2/6] rendering the pre-coherence README (deterministic code, no LLM call)")
    pre_coherence_readme = render_readme(entry, document, plan, units_document, dispositions)
    print(f"      {len(pre_coherence_readme)} characters")

    tasks = authoring_tasks(entry, document, investigation, dispositions, plan)
    print(f"[3/6] {len(tasks)} authoring tasks total; coherence only revises non-batch ones")

    print("[4/6] loading the real prompt manifest")
    prompt_registry = load_manifests(Path("prompts"))
    loaded = prompt_registry["section_authoring"]
    manifest = loaded.manifest
    print(f"      section_authoring v{manifest.version} (coherence mode), routes to {manifest.model_route}")

    batches = coherence_batches(tasks)
    print(f"      {len(batches)} coherence batch(es)")

    config = load_gateway_config(os.environ)
    workspace = Path(tempfile.mkdtemp(prefix="rp_lane_r_s8_"))
    ledger = Ledger(workspace / "ledger.jsonl")
    store = CallStore(workspace / "calls")

    current = units_document
    print("[5/6] firing the REAL LLM call(s) through the live gateway, with the REAL coherence_checks")
    for batch_id, batch_tasks in batches:
        existing = coherence_batch_units(current.get("units", []), batch_tasks)
        packet = coherence_packet(entry, pre_coherence_readme, current, batch_tasks, document)
        call_schema = coherence_schema(loaded, existing, batch_tasks)
        context = JobContext(repository=repository, source_revision=document.source_revision)

        def checks(output: dict, batch_tasks=batch_tasks, existing=existing) -> list[str]:
            return coherence_checks(
                output,
                batch_tasks,
                document,
                name,
                existing_units=existing,
                prior_omitted=current.get("omitted", []),
            )

        def recover(output: dict, batch_tasks=batch_tasks, existing=existing) -> dict | None:
            return recover_coherence_regressions(
                output, existing_units=existing, facts=document, tasks=batch_tasks
            )

        result = run_job(
            loaded,
            packet,
            config=config,
            facts=document,
            ledger=ledger,
            store=store,
            context=context,
            call_schema=call_schema,
            checks=checks,
            recover=recover,
        )
        print(
            f"      {batch_id}: {len(batch_tasks)} section(s), {result.provider_calls} call(s), "
            f"model_served={result.model_served}, cache_reused={result.cache_reused}"
        )
        current, revised = apply_coherence(current, result.output)
        print(f"            revised: {revised or '(none)'}")

    print(f"[6/6] re-rendering with the coherence pass's own revisions applied")
    final_readme = render_readme(entry, document, plan, current, dispositions)
    print(f"      {len(final_readme)} characters")

    (out_dir / "content_units.coherent.json").write_text(
        json.dumps(current, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "README.coherent.md").write_text(final_readme, encoding="utf-8", newline="\n")
    print(f"\nWrote {out_dir / 'content_units.coherent.json'} and {out_dir / 'README.coherent.md'}")


if __name__ == "__main__":
    main()
