"""Fire the real source_reconciliation (S4) LLM call(s) end-to-end, no agent reasoning.

Usage:
    python scripts/run_lane_r_reconciliation.py <owner>/<repo> <ecosystem> <clone_path>

Wires: the same real inherited_unit facts and registry entry run_lane_r_investigation.py
builds, plus that script's own accepted investigation.json output -> readme/reconciliation/
dispositions.py's reconciliation_packet/reconciliation_schema/reconciliation_batches (just
ported) -> core/llm/jobs.py's run_job, once per batch, merged with merge_dispositions.

Requires scripts/run_lane_r_investigation.py to have been run first for the same repository
(reads its accepted investigation.json from scripts/_lane_r_output/<repo>/).
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
from repo_presenter.readme.evidence.facts.inherited import inherited_unit_facts
from repo_presenter.readme.reconciliation.dispositions import (
    merge_dispositions,
    reconciliation_batch_facts,
    reconciliation_batches,
    reconciliation_packet,
    reconciliation_schema,
    summarize,
    write_dispositions,
)


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
    facts_path = Path("evidence/build/P2_REAL_ENGINE_SALVAGE") / repo_dir / "facts.json"
    investigation_path = Path("scripts/_lane_r_output") / repo_dir / "investigation.json"

    print(f"[1/6] reading real facts from {facts_path}")
    base_document = read_facts(facts_path)
    print(f"      {len(base_document.facts)} facts loaded")

    print(f"[2/6] reading the real repository tree, README, and accepted investigation")
    tree_paths = _tree_paths(clone_path)
    readme_bytes = (clone_path / "README.md").read_bytes()
    investigation = json.loads(investigation_path.read_text(encoding="utf-8"))
    print(f"      {len(tree_paths)} files in tree, investigation from {investigation_path}")

    print("[3/6] building real inherited_unit facts from the live README")
    public_symbol_facts = [f for f in base_document.facts if f.kind == "public_symbol"]
    inherited = inherited_unit_facts("README.md", readme_bytes, public_symbol_facts, tree_paths)
    print(f"      {len(inherited)} inherited units (every one, not S3's capped subset)")
    source_revision = run_git(["rev-parse", "HEAD"], cwd=clone_path).stdout.strip()
    # Idempotent re-merge: see run_lane_r_investigation.py's identical comment.
    kept = tuple(f for f in base_document.facts if f.kind != "inherited_unit")
    document = FactsDocument(repository, source_revision, (*kept, *inherited))

    print("[4/6] loading the real prompt manifest and this repository's registry entry")
    prompt_registry = load_manifests(Path("prompts"))
    loaded = prompt_registry["source_reconciliation"]
    manifest = loaded.manifest
    print(f"      source_reconciliation v{manifest.version}, routes to {manifest.model_route}")
    repo_registry = load_registry(Path("data/registry.json"))
    entry = require_listed(repo_registry, repository)

    batches = reconciliation_batches(document, manifest.sampling.max_output_tokens)
    print(f"      {len(batches)} batch(es) of inherited units, {len(inherited)} units total")

    config = load_gateway_config(os.environ)
    workspace = Path("scripts") / "_lane_r_output" / repo_dir / "llm_cache"
    # One invocation per script run (project/state.yaml PORT_BUNDLE_INTEGRITY_LAYER step 1).
    invocation = Invocation.begin()
    ledger_path = workspace / "ledger.jsonl"
    ledger = Ledger(ledger_path, invocation_id=invocation.invocation_id)
    store = CallStore(workspace / "calls")

    outputs = []
    print("[5/6] firing the REAL LLM call(s) through the live gateway")
    for batch_id, batch_units in batches:
        batch_facts = reconciliation_batch_facts(document, batch_units)
        packet = reconciliation_packet(entry, batch_facts, investigation, manifest, batch_units)
        call_schema = reconciliation_schema(loaded, batch_units, batch_facts, investigation)
        context = JobContext(repository=repository, source_revision=source_revision)
        result = run_job(
            loaded,
            packet,
            config=config,
            facts=batch_facts,
            ledger=ledger,
            store=store,
            context=context,
            call_schema=call_schema,
        )
        print(
            f"      {batch_id}: {len(batch_units)} units, {result.provider_calls} call(s), "
            f"model_served={result.model_served}, cache_reused={result.cache_reused}"
        )
        outputs.append(result.output)

    merged = merge_dispositions(outputs)
    print(f"[6/6] merged {len(merged['dispositions'])} dispositions across {len(outputs)} batch(es)")
    print(f"      disposition counts: {dict(summarize(merged))}")
    print()
    print("REAL MODEL OUTPUT (nothing hand-written below this line):")
    print(json.dumps(merged, indent=2))

    out_dir = Path("scripts") / "_lane_r_output" / repo_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = write_dispositions(merged, out_dir / "dispositions.json")
    print(f"\nWrote {out_dir / 'dispositions.json'} (sha256 {digest})")

    invocation.attach_ledger(repository, ledger_path)
    invocation_record_path = workspace / "invocations" / f"{invocation.invocation_id}.json"
    invocation.write(invocation_record_path, Path("."), 0)
    print(f"Wrote {invocation_record_path} (invocation {invocation.invocation_id})")


if __name__ == "__main__":
    main()
