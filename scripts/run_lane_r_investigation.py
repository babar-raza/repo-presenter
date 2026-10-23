"""Fire one REAL repository_investigation (S3) LLM call end-to-end, no agent reasoning.

Usage:
    python scripts/run_lane_r_investigation.py <owner>/<repo> <ecosystem> <clone_path>

Wires: readme/evidence/facts/inherited.py (the real inherited_unit facts, just ported --
the one genuine blocker to firing this job for real) -> readme/investigation/dossier.py
(the real, bounded packet and the per-call schema that pins every fact_ids array to this
repository's own dossier) -> core/llm/jobs.py's run_job (the same real gateway call, schema
validation, fact-ID binding check, caching every other real job in this repository uses).

This is the first live-fired S3 call in this repository. Everything in the model's output is
its own: nothing here pre-writes or hand-edits a single field of product_summary, audience,
problems_solved, workflows, capabilities, limitations, or uncertainties.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from repo_presenter.core.config import load_gateway_config
from repo_presenter.core.facts import FactsDocument, read_facts
from repo_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.readme.evidence.facts.inherited import inherited_unit_facts
from repo_presenter.readme.investigation.dossier import (
    investigation_packet,
    investigation_schema,
    write_investigation,
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
    facts_path = Path("evidence/build/P2_REAL_ENGINE_SALVAGE") / (
        repository.replace("/", "__")
    ) / "facts.json"

    print(f"[1/6] reading real facts from {facts_path}")
    base_document = read_facts(facts_path)
    print(f"      {len(base_document.facts)} facts loaded")

    print(f"[2/6] reading the real repository tree and README at {clone_path}")
    tree_paths = _tree_paths(clone_path)
    readme_bytes = (clone_path / "README.md").read_bytes()
    print(f"      {len(tree_paths)} files in tree, {len(readme_bytes)} bytes of README")

    print("[3/6] building real inherited_unit facts from the live README")
    public_symbol_facts = [f for f in base_document.facts if f.kind == "public_symbol"]
    inherited = inherited_unit_facts("README.md", readme_bytes, public_symbol_facts, tree_paths)
    print(f"      {len(inherited)} inherited units")
    source_revision = os.popen(
        f'git -C "{clone_path}" rev-parse HEAD'
    ).read().strip()
    document = FactsDocument(repository, source_revision, (*base_document.facts, *inherited))

    print("[4/6] loading the real, ported prompt manifests and this repository's registry entry")
    prompt_registry = load_manifests(Path("prompts"))
    loaded = prompt_registry["repository_investigation"]
    manifest = loaded.manifest
    print(
        f"      repository_investigation v{manifest.version}, routes to {manifest.model_route}"
    )
    repo_registry = load_registry(Path("data/registry.json"))
    entry = require_listed(repo_registry, repository)

    packet = investigation_packet(entry, document, manifest)
    call_schema = investigation_schema(loaded, document)
    print(
        f"      packet: {len(packet['fact_dossier'])} dossier facts, "
        f"{len(packet['inherited_units'])} inherited units"
    )

    print("[5/6] firing the REAL LLM call through the live gateway")
    config = load_gateway_config(os.environ)
    workspace = Path("scripts/_lane_r_output") / repository.replace("/", "__") / "llm_cache"
    ledger = Ledger(workspace / "ledger.jsonl")
    store = CallStore(workspace / "calls")
    context = JobContext(repository=repository, source_revision=source_revision)

    result = run_job(
        loaded,
        packet,
        config=config,
        facts=document,
        ledger=ledger,
        store=store,
        context=context,
        call_schema=call_schema,
    )

    print(
        f"[6/6] result: {result.provider_calls} provider call(s), "
        f"model_served={result.model_served}, cache_reused={result.cache_reused}, "
        f"total_tokens={result.total_tokens}"
    )
    print()
    print("REAL MODEL OUTPUT (nothing hand-written below this line):")
    print(json.dumps(result.output, indent=2))

    out_dir = Path("scripts") / "_lane_r_output" / repository.replace("/", "__")
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = write_investigation(result.output, out_dir / "investigation.json")
    print(f"\nWrote {out_dir / 'investigation.json'} (sha256 {digest})")


if __name__ == "__main__":
    main()
