"""Fire one REAL Lane R section_authoring LLM call end-to-end, no agent reasoning.

Usage:
    python scripts/run_lane_r_authoring.py

Wires: core/llm/prompts.py (loads the real, ported prompts/section_authoring.yaml) ->
core/config.py (reads GPT_OSS_ENDPOINT/GPT_OSS_API_KEY from the process environment) ->
core/llm/transport.py (the real OpenAI-SDK-compatible gateway call) -> core/llm/jobs.py's
run_job (schema validation, fact-ID binding check, caching).

This is the first live-fired Lane R composition call in this repository. The packet
(objective/slots) is hand-built here from the real, already-extracted facts for
aspose-3d-foss/Aspose.3D-FOSS-for-Python (same facts.json RUN_PIPELINE_END_TO_END_ON_REAL_REPO
produced) -- presentation_planning (the job that would normally produce this packet) is not
wired yet, so this script stands in for it with one hand-built, clearly-labeled "opening"
section packet, matching the real live README's actual opening paragraph's scope. The
AUTHORED PROSE ITSELF is 100% the model's real output: nothing about the returned units is
pre-written, hand-edited, or fabricated by this script.
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
from repo_presenter.core.llm.jobs import JobContext, run_job
from repo_presenter.core.llm.ledger import Ledger
from repo_presenter.core.llm.jobs import CallStore
from repo_presenter.core.llm.prompts import load_manifests


def simple_citation_check(
    output: dict, accepted_facts: list[dict], facts: FactsDocument
) -> list[str]:
    """A deliberately simple stand-in for the real ``readme/composition/authoring.py::unit_checks``
    (which needs a full ``SectionTask`` built from a real presentation_planning job output -- not
    yet wired; see this script's own docstring).

    Checks one thing, crudely but honestly: every capitalized-acronym-shaped token in a unit's
    prose (a plausible format/capability name -- OBJ, STL, U3D, API, ...) must appear in the text
    of at least one fact the unit actually cites. This will not catch everything the real
    unit_checks catches, but it is enough to prove the rejection/re-ask path fires for real.
    """
    import re

    cited_text = " ".join(
        fact["value"] for fact in accepted_facts
    ).upper()
    errors: list[str] = []
    acronym = re.compile(r"\b[A-Z][A-Z0-9]{1,6}\b")
    for unit in output.get("units", []):
        text = str(unit.get("text", ""))
        tokens = set(acronym.findall(text))
        unsupported = sorted(t for t in tokens if t not in cited_text)
        if unsupported:
            errors.append(
                f"unit {unit.get('slot')!r} names {', '.join(unsupported)}, which does not "
                "appear in the value of any fact this unit cites -- invented, not supported"
            )
    return errors


def main() -> None:
    facts_path = Path("evidence/build/P2_REAL_ENGINE_SALVAGE/aspose-3d-foss__Aspose.3D-FOSS-for-Python/facts.json")
    print(f"[1/4] reading real facts from {facts_path}")
    document = read_facts(facts_path)
    print(f"      {len(document.facts)} facts loaded")

    print("[2/4] loading the real, ported prompt manifests")
    registry = load_manifests(Path("prompts"))
    manifest = registry.manifests["section_authoring"]
    print(f"      section_authoring v{manifest.manifest.version}, routes to {manifest.manifest.model_route}")

    # Real facts this section may cite: package identity + the two confirmed-working export
    # formats (STL, glTF) + the confirmed-broken one (OBJ), explicitly in do_not_claim.
    by_id = {f.id: f for f in document.facts}
    accepted_ids = [
        "identity:repository",
        "package:name",
    ]
    accepted_facts = [
        {"id": fid, "kind": by_id[fid].kind, "value": by_id[fid].value}
        for fid in accepted_ids
        if fid in by_id
    ]
    contradicted = [
        {"id": f.id, "kind": f.kind, "value": f.value[:80]}
        for f in document.facts
        if f.polarity == "CONTRADICTED"
    ]
    print(f"      accepted_facts: {[f['id'] for f in accepted_facts]}")
    print(f"      do_not_claim (CONTRADICTED): {[f['id'] for f in contradicted]}")

    packet = {
        "repository": document.repository,
        "product_name": "Aspose.3D FOSS for Python",
        "mode": "author",
        "section_id": "opening",
        "objective": (
            "State what the product is and does, as its own actions, from the accepted "
            "facts alone. One unit, the 'opening' slot."
        ),
        "slots": [
            {
                "slot": "opening",
                "title": "Opening",
                "fact_ids": [f["id"] for f in accepted_facts],
                "renders": "",
            }
        ],
        "accepted_facts": accepted_facts,
        "do_not_claim": contradicted,
        "length_budget": "1 unit, 1-2 sentences",
        "rendered_document": "",
        "existing_units": [],
    }

    print("[3/4] firing the REAL LLM call through the live gateway")
    config = load_gateway_config(os.environ)
    workspace = Path(tempfile.mkdtemp(prefix="rp_lane_r_"))
    ledger = Ledger(workspace / "ledger.jsonl")
    store = CallStore(workspace / "calls")
    context = JobContext(repository=document.repository, source_revision=document.source_revision)

    def checks(output: dict) -> list[str]:
        return simple_citation_check(output, accepted_facts, document)

    result = run_job(
        manifest,
        packet,
        config=config,
        facts=document,
        ledger=ledger,
        store=store,
        context=context,
        checks=checks,
    )

    print(f"[4/4] result: {result.provider_calls} provider call(s), model_served={result.model_served}, "
          f"cache_reused={result.cache_reused}, total_tokens={result.total_tokens}")
    print()
    print("REAL MODEL OUTPUT (nothing hand-written below this line):")
    print(json.dumps(result.output, indent=2))

    out_dir = Path("scripts") / "_lane_r_output"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "section_authoring_result.json").write_text(
        json.dumps(result.output, indent=2), encoding="utf-8"
    )
    print(f"\nWrote {out_dir / 'section_authoring_result.json'}")


if __name__ == "__main__":
    main()
