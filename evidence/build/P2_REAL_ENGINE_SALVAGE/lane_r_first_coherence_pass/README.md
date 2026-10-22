# The first real S8 coherence pass — fires correctly, but does not fix the known duplicate defect

2026-10-22. `aspose-cells-foss/Aspose.Cells-FOSS-for-Go` (the same repository as
`lane_r_second_full_cascade/`). `readme/composition/coherence.py` (stage S8: "revise LLM-owned
units only, once, then re-render") was already fully ported earlier this session but never
fired by any script. This is the first time.

## Why this was fired

Both full cascade runs so far (`lane_r_first_full_cascade/`, `lane_r_second_full_cascade/`)
measured the same defect: a duplicate opening paragraph, caused by a `VERIFIED_PRESERVE`
disposition into the LLM-authored `opening` section sitting beside the freshly-authored content
for that same slot. `dispositions.py`'s own `coordinate_neighbor_promises` docstring names the
real mechanism for this defect class explicitly: "BC-10 coherence-gap... REJECT_PRESENTATION,
moving key factual content out of its original context." Rather than guess a render-time patch,
this fired the real, already-ported S8 coherence stage to find out what it actually does.

## A real bug found and fixed before trusting the result

The first attempt crashed outright:

```
JobError: section_authoring: output rejected twice; last rejection: scope_limitations/scope:
coherence revision drops the previously-cited inherited_unit 'inherited_unit:074.heading' and
none of its own content ('## License') remains in the revised text...
```

This is the real `coherence_content_loss_errors` safety check correctly catching a real
degenerate model revision (the model's rewrite of `scope_limitations/scope` silently dropped
content tied to the License heading) — not a bug in the check. The bug was in this session's own
new script: `run_lane_r_coherence.py` called `run_job` without the `recover=` parameter.
`readme/composition/coherence.py`'s own `recover_coherence_regressions` (the real, already-ported
last-resort correction `repair/rounds.py` passes at this exact call site in the old repository)
composes five deterministic content-loss/title/audience/carry-unit fixes — checked directly
against the old repo's own call site before adding this, not guessed. Fixed by wiring it in.

## The real result, after the fix

```
coherence#1: 3 section(s), 1 call, revised: (none)
coherence#2: 1 section(s), 1 call, revised: (none)
coherence#3: 1 section(s), 1 call, revised: (none)
coherence#4: 1 section(s), 2 calls, revised: ['scope_limitations/limitation:4']
```

4 batches (coherence only revises the non-batched authoring tasks — `opening`,
`key_capabilities`, `quick_start` grouped in batch 1; `additional_examples`, `api_reference`,
`scope_limitations` each their own batch). Batch 4 needed a real reject → `recover` → accept
cycle (the content-loss rejection above, then the deterministic recovery produced an acceptable
revision) — 2 provider calls, not a failure. The other 3 batches each needed exactly 1 call and
made no changes: the coherence pass judged the pre-coherence prose already coherent for those
sections. `README.coherent.md` (22,707 characters, up from the pre-coherence 22,203) is the real,
final re-rendered output.

## The real, falsifiable answer this run gives: S8 does NOT fix the duplicate-opening defect

Checked directly, not assumed: `README.coherent.md`'s own opening section still carries both
paragraphs, byte-for-byte the same duplicate measured in the pre-coherence render. Batch 1
(which includes `opening`) reported `revised: (none)` — the model did not touch it. This
confirms, by firing the real mechanism rather than guessing, that S8 coherence is scoped to a
different defect class than the one measured: it revises the wording of units the LLM already
owns, never removes or reconciles against a *preserved* (not authored) unit sitting beside one —
by its own docstring, "only... prose the LLM already owned." The duplicate's root cause (a
reconciliation disposition choosing `VERIFIED_PRESERVE` instead of `SUPERSEDE_REDUNDANT` for a
unit that duplicates an authored slot) is provably not addressed by either `placement_errors`
(checked and ruled out earlier) or `coherence` (checked and ruled out here) — the real fix, if
one exists in the production system at all, is in a part of the pipeline this session has not
yet found or ported, or this is an accepted, lived-with risk of the real, shipped architecture.

## Honest scope limits

- Fired against one repository's one coherence pass. `recover_coherence_regressions`'s own five
  component fixes are individually well-documented in coherence.py but not individually
  exercised beyond whichever one(s) fired for real here (likely `recover_coherence_content_loss`,
  not confirmed by inspecting which specific sub-fix changed the output).
- `README.coherent.md` has not been diffed field-by-field against the pre-coherence render
  beyond the opening-paragraph check above and the printed `revised` list.
