# First real, live-fired Lane R composition call — and the real reason validation matters

2026-10-22. `python scripts/run_lane_r_authoring.py`. This is the first time this repository's
Lane R engine actually called a real LLM, not a mechanism-only unit test.

**What ran:** `prompts/section_authoring.yaml` (ported verbatim from the old repo — real,
governed prompt content, not written by this session) loaded through `core/llm/prompts.py`,
fired through `core/config.py`/`core/llm/transport.py` against the real, confirmed-live
gateway (`https://llm.professionalize.com/v1`, model `qwen3-next` — confirmed present in the
gateway's own model catalog and confirmed answering a schema-valid probe before this run),
via the real `core/llm/jobs.py::run_job` (schema validation, fact-ID binding, caching, and the
re-ask-on-rejection cycle).

The packet was hand-built from the real facts already extracted for
`aspose-3d-foss/Aspose.3D-FOSS-for-Python` (`evidence/build/P2_REAL_ENGINE_SALVAGE/aspose-3d-foss__Aspose.3D-FOSS-for-Python/facts.json`),
since `presentation_planning` (the job that would normally produce this packet) is not wired
yet. Only two facts were offered as citable: `identity:repository` and `package:name` —
deliberately not the format facts, to see honestly what the model does when given almost
nothing to work with.

## What actually happened (real, not simulated)

**Attempt 1** (provider call 1 of 2, `qwen3-next`, real network round trip):

```json
{"units": [{"section": "opening", "slot": "opening",
  "text": "Aspose.3D FOSS for Python reads and writes 3D files in multiple formats including OBJ, STL, U3D, and A3DW.",
  "fact_ids": ["identity:repository", "package:name"]}], "omitted": []}
```

The model **hallucinated four specific format claims** (OBJ, STL, U3D, A3DW) that appear
nowhere in the values of the two facts it was given, and nowhere in the packet at all. The
`fact_ids` array itself was technically correct (both IDs really are accepted facts) — this is
exactly the gap mission section 7 step 5 warns about: *"agent-authored text is checked for
actual entailment, not citation existence."* Citing a real fact ID is not the same as the
prose actually following from that fact's value.

**The check that caught it** (`scripts/run_lane_r_authoring.py::simple_citation_check`,
deliberately labeled in its own docstring as a simplified stand-in for the real
`readme/composition/authoring.py::unit_checks`, which needs a full `SectionTask` this proof
did not build): every capitalized-acronym-shaped token in the unit's prose must appear in the
text of a cited fact's value. `OBJ`, `STL`, `U3D`, `A3DW` all failed this check. `run_job`
correctly treated this as a rejection and fired the manifest's own real `rejection_template`
(the exact text in `prompts/section_authoring.yaml`, not written by this script) as a second
message, asking the model to return one corrected object.

**Attempt 2** (provider call 2 of 2, same real round trip):

```json
{"units": [{"section": "opening", "slot": "opening",
  "text": "Aspose.3D FOSS for Python reads and writes 3D files.",
  "fact_ids": ["identity:repository", "package:name"]}], "omitted": []}
```

The model **self-corrected**: it dropped every invented format claim and produced a sentence
that says less, but says only what the two accepted facts actually support — exactly matching
the prompt's own instruction, *"When a fact does not settle a point, say less."* This final
output passed the citation check and was accepted. `result.provider_calls == 2`,
`result.model_served == "qwen3-next"`.

## Why this is the important proof, not just "a call worked"

A single successful call would only prove the mechanism *can* fire. What this run actually
proves is the thing the mission itself insists matters most (section 11, "no more false
greens"; section 7 step 7, "a returned reviewer REJECT is blocking unless an explicit, proven
deterministic refutation resolves it"): **the raw model is not trustworthy on its own, and the
deterministic validation layer is not optional scaffolding — it is the only thing that turned
a real, fabricated claim into a corrected, honest one.** Removing the `checks` callback (as
the first version of this script did, before this finding) would have silently accepted the
hallucinated formats.

## Honest scope limits

- This is Lane R's authoring stage only, for one hand-built section packet on one repository.
  `presentation_planning` (the job that would normally produce this packet from real content-unit
  inventory) is not wired. `placement.py`/`renderer.py` were not run on this output.
- `simple_citation_check` is explicitly a stand-in, not the real `unit_checks` — it catches
  unsupported acronym-shaped tokens only, not the fuller set of things `unit_checks` checks
  (title restatement, command-line restatement, cross-slot fact leakage, edition-name
  substitution, and more). Wiring the real `unit_checks` needs a real `SectionTask`, which
  needs a real plan — real follow-up work, recorded in `project/state.yaml`.
- Real provider calls cost real tokens against a real budget (2 calls, ~2792+2379 tokens total
  across both attempts in this session's two runs) — not free, and not to be repeated casually
  at portfolio scale without the budget discipline mission section 12 requires.
