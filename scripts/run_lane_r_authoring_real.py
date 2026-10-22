"""Fire the REAL section_authoring (S6) LLM call(s) end-to-end, no agent reasoning, no hand-built
packet -- unlike scripts/run_lane_r_authoring.py (this session's earlier stand-in proof), every
task here comes from the real authoring_tasks(), every check is the real unit_checks(), and the
plan driving it is the real, accepted plan.json from run_lane_r_planning.py.

Usage:
    python scripts/run_lane_r_authoring_real.py <owner>/<repo> <ecosystem> <clone_path>

Requires run_lane_r_investigation.py, run_lane_r_reconciliation.py, and run_lane_r_planning.py
to have been run first for the same repository.
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
from repo_presenter.readme.composition.authoring import (
    authoring_schema,
    authoring_tasks,
    merge_units,
    unit_checks,
    write_content_units,
)
from repo_presenter.readme.composition.components.identity import product_name
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
    plugin_for(ecosystem)  # see run_lane_r_planning.py's own comment on this exact real bug
    facts_path = Path("evidence/build/P2_REAL_ENGINE_SALVAGE") / repo_dir / "facts.json"
    out_dir = Path("scripts/_lane_r_output") / repo_dir

    print(f"[1/6] reading real facts, investigation, dispositions, and plan from {out_dir}")
    base_document = read_facts(facts_path)
    investigation = json.loads((out_dir / "investigation.json").read_text(encoding="utf-8"))
    dispositions = json.loads((out_dir / "dispositions.json").read_text(encoding="utf-8"))
    plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))

    print("[2/6] rebuilding the real inherited_unit facts so tasks/dispositions agree")
    tree_paths = _tree_paths(clone_path)
    readme_bytes = (clone_path / "README.md").read_bytes()
    public_symbol_facts = [f for f in base_document.facts if f.kind == "public_symbol"]
    inherited = inherited_unit_facts("README.md", readme_bytes, public_symbol_facts, tree_paths)
    source_revision = os.popen(f'git -C "{clone_path}" rev-parse HEAD').read().strip()
    document = FactsDocument(repository, source_revision, (*base_document.facts, *inherited))

    print("[3/6] loading the real prompt manifest and this repository's registry entry")
    prompt_registry = load_manifests(Path("prompts"))
    loaded = prompt_registry["section_authoring"]
    manifest = loaded.manifest
    print(f"      section_authoring v{manifest.version}, routes to {manifest.model_route}")
    repo_registry = load_registry(Path("data/registry.json"))
    entry = require_listed(repo_registry, repository)
    name = product_name(entry)

    tasks = authoring_tasks(entry, document, investigation, dispositions, plan)
    print(f"[4/6] {len(tasks)} real authoring task(s): {[t.label for t in tasks]}")

    config = load_gateway_config(os.environ)
    workspace = Path(tempfile.mkdtemp(prefix="rp_lane_r_s6_"))
    ledger = Ledger(workspace / "ledger.jsonl")
    store = CallStore(workspace / "calls")

    outputs: dict[str, dict] = {}
    print("[5/6] firing the REAL LLM call(s) through the live gateway, with the REAL unit_checks")
    for task in tasks:
        call_schema = authoring_schema(loaded, task)
        context = JobContext(repository=repository, source_revision=source_revision)

        def checks(output: dict, task=task) -> list[str]:
            return unit_checks(output, task, document, name)

        result = run_job(
            loaded,
            task.packet,
            config=config,
            facts=document,
            ledger=ledger,
            store=store,
            context=context,
            call_schema=call_schema,
            checks=checks,
        )
        print(
            f"      {task.label}: {result.provider_calls} call(s), "
            f"model_served={result.model_served}, cache_reused={result.cache_reused}"
        )
        outputs[task.label] = result.output

    merged = merge_units(outputs)
    print(f"[6/6] merged {len(merged['units'])} units across {len(outputs)} task(s)")
    print()
    print("REAL MODEL OUTPUT (nothing hand-written below this line):")
    print(json.dumps(merged, indent=2))

    digest = write_content_units(merged, out_dir / "content_units.json")
    print(f"\nWrote {out_dir / 'content_units.json'} (sha256 {digest})")


if __name__ == "__main__":
    main()
