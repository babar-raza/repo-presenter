"""Fire the real presentation_planning (S5) LLM call end-to-end, no agent reasoning.

Usage:
    python scripts/run_lane_r_planning.py <owner>/<repo> <ecosystem> <clone_path>

Wires: the real facts + inherited units + accepted investigation.json (S3) + accepted
dispositions.json (S4) -> readme/composition/planning.py's planning_packet/planning_schema/
plan_checks (all already fully ported -- this is the first time this repository has fired
them for real) -> core/llm/jobs.py's run_job.

Requires run_lane_r_investigation.py and run_lane_r_reconciliation.py to have been run first
for the same repository.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.config import load_gateway_config
from repo_presenter.core.facts import FactsDocument, read_facts
from repo_presenter.core.git_safety.git import run_git
from repo_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.core.noop_proof import Invocation
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.planning import (
    plan_checks,
    planning_packet,
    planning_schema,
    summarize_plan,
    write_plan,
)
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
    # Every ecosystem's EcosystemSpec self-registers into core.ecosystems.SPECS only when its
    # own platforms/<ecosystem>.py module is imported (core/ may not import an extractor
    # itself, so it cannot do this for us). The real production pipeline already triggers this
    # via plugin_for() before any stage asks spec_for() for the same ecosystem; this script
    # reads only pre-built facts.json and never touches the extractor layer otherwise, so it
    # must trigger the same import itself -- real bug hit live (2026-10-22, ecosystem="go"):
    # planning.plan_checks() -> placement.placements() -> renders_verbatim() -> spec_for("go")
    # raised ConfigError because nothing had imported platforms/go.py yet in this process.
    plugin_for(ecosystem)
    facts_path = Path("evidence/build/P2_REAL_ENGINE_SALVAGE") / repo_dir / "facts.json"
    out_dir = Path("scripts/_lane_r_output") / repo_dir

    print(f"[1/5] reading real facts, investigation, and dispositions from {out_dir}")
    base_document = read_facts(facts_path)
    investigation = json.loads((out_dir / "investigation.json").read_text(encoding="utf-8"))
    dispositions = json.loads((out_dir / "dispositions.json").read_text(encoding="utf-8"))
    print(f"      {len(base_document.facts)} facts, {len(dispositions['dispositions'])} dispositions")

    print("[2/5] rebuilding the real inherited_unit facts so the packet's shell/dispositions agree")
    tree_paths = _tree_paths(clone_path)
    readme_bytes = (clone_path / "README.md").read_bytes()
    public_symbol_facts = [f for f in base_document.facts if f.kind == "public_symbol"]
    inherited = inherited_unit_facts("README.md", readme_bytes, public_symbol_facts, tree_paths)
    source_revision = run_git(["rev-parse", "HEAD"], cwd=clone_path).stdout.strip()
    document = FactsDocument(repository, source_revision, (*base_document.facts, *inherited))

    print("[3/5] loading the real prompt manifest and this repository's registry entry")
    prompt_registry = load_manifests(Path("prompts"))
    loaded = prompt_registry["presentation_planning"]
    manifest = loaded.manifest
    print(f"      presentation_planning v{manifest.version}, routes to {manifest.model_route}")
    repo_registry = load_registry(Path("data/registry.json"))
    entry = require_listed(repo_registry, repository)

    packet = planning_packet(entry, document, investigation, dispositions, manifest)
    call_schema = planning_schema(loaded, document, investigation, dispositions)

    print("[4/5] firing the REAL LLM call through the live gateway, with the REAL plan_checks")
    config = load_gateway_config(os.environ)
    workspace = out_dir / "llm_cache"
    invocation = Invocation.begin()
    ledger_path = workspace / "ledger.jsonl"
    ledger = Ledger(ledger_path, invocation_id=invocation.invocation_id)
    store = CallStore(workspace / "calls")
    context = JobContext(repository=repository, source_revision=source_revision)

    def checks(output: dict) -> list[str]:
        return plan_checks(output, document, dispositions=dispositions, ecosystem=ecosystem)

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
    )

    print(
        f"[5/5] result: {result.provider_calls} provider call(s), "
        f"model_served={result.model_served}, cache_reused={result.cache_reused}, "
        f"total_tokens={result.total_tokens}"
    )
    print(f"      {summarize_plan(result.output)}")
    print()
    print("REAL MODEL OUTPUT (nothing hand-written below this line):")
    print(json.dumps(result.output, indent=2))

    digest = write_plan(result.output, out_dir / "plan.json")
    print(f"\nWrote {out_dir / 'plan.json'} (sha256 {digest})")

    invocation.attach_ledger(repository, ledger_path)
    invocation_record_path = workspace / "invocations" / f"{invocation.invocation_id}.json"
    invocation.write(invocation_record_path, Path("."), 0)
    print(f"Wrote {invocation_record_path} (invocation {invocation.invocation_id})")


if __name__ == "__main__":
    main()
