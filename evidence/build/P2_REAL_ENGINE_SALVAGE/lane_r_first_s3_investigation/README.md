# The first real, live-fired S3 (repository_investigation) call

2026-10-22. `python scripts/run_lane_r_investigation.py aspose-3d-foss/Aspose.3D-FOSS-for-Python
python <clone>`. The first time this repository has fired `repository_investigation` for real,
rather than the deliberately hand-built/simplified Lane R proofs from earlier this session
(`lane_r_first_live_call/`).

## What this closes

`WIRE_PRESENTATION_PLANNING_AND_REAL_UNIT_CHECKS`'s own packet audit found the real blocker to
firing S3 at all: its prompt packet needs `inherited_units`, and the module that produces them
(`readme/evidence/facts/inherited.py`) was never ported into this repository. Closing that (a
separate commit, same session) also surfaced `readme/evidence/facts/repository_files.py` and
`schemas/facts.schema.json` as missing. With those three in place, this entry ports the one
remaining piece needed to fire S3 itself: `readme/investigation/dossier.py` — the bounded packet
builder and, critically, `investigation_schema()`, which pins every `fact_ids` array in the
per-call schema to an enum of the packet's own dossier IDs, so a hallucinated fact ID is refused
by the decoder itself rather than costing a live provider call before a post-hoc check catches it
(the real defect this mechanism exists for, documented at length in the module's own docstring:
two live Words-Python calls against a byte-identical request produced two different
hallucinations before this schema pinning existed upstream).

## The real result

```
[6/6] result: 1 provider call(s), model_served=qwen3-next, cache_reused=False, total_tokens=13402
```

**One provider call, accepted on the first attempt — no rejection/re-ask cycle needed.** This is
a materially stronger proof than the earlier `section_authoring` stand-in call (which *did* need
a reject/re-ask round after a real hallucination): there, a custom check caught a hallucination
reactively, after it happened; here, the schema's own enum constraint prevents one proactively,
before the model can even express it. Every one of the real output's `fact_ids` arrays
(`product_summary`, `audience`, 4 `problems_solved`, 3 `workflows`, 7 `capabilities`, 6
`limitations`) cites only IDs genuinely present in this repository's real `facts.json` — spot-
checked directly, not asserted: e.g. `format:input.obj`, `public_symbol:aspose.threed.mesh`,
`example:005` are all real fact IDs this repository's own extraction produced for this exact
revision.

**Real inherited units fed the packet, for the first time**: 77 units built from the live
README's actual headings/paragraphs/lists (via the newly-ported `inherited.py`), 51 of which
(headings, paragraphs, lists — `dossier.py`'s own documented filter) entered the bounded packet
alongside 118 dossier facts.

## Honest scope limits

- This is S3 alone. `source_reconciliation` (S4), `presentation_planning` (S5), and a real
  `SectionTask`-driven `section_authoring` (S6) with the full `unit_checks` are not fired here —
  `WIRE_PRESENTATION_PLANNING_AND_REAL_UNIT_CHECKS`'s own cascade is still only one stage deep.
- S3 has no semantic-correctness check of its own (that is S4/S5/S6's job downstream): one
  limitation's citation (`public_symbol:aspose.threed.fmatrix4` for "FBX export is not
  implemented") is a real, dossier-present ID, but a weak pairing — exactly the "citation exists
  vs. citation actually supports the claim" gap the mission names, and exactly why this job's
  output is not meant to be trusted as a finished document on its own.
- Fired against one repository. Not yet run against a second to confirm the schema-pinning
  mechanism generalizes beyond this one dossier's shape.
