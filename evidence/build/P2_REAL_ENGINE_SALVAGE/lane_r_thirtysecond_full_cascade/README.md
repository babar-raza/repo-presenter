# The thirty-second complete, real Lane R cascade — the S8 batch-sizing fix closes aspose-pdf-foss/TypeScript

2026-10-23. `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript`. Previously blocked at S8 on a
deterministic `max_output_tokens=8000` truncation (see
`evidence/build/P2_REAL_ENGINE_SALVAGE/lane_r_pdf_foss_typescript_retry_partial/`): a coherence
batch of only a few units still overran the output budget because those units' own rendered text
was large. Fixed in `coherence.py`'s `coherence_batches()` by adding a second, independent
`_COHERENCE_BATCH_CHARS` cap alongside the existing unit-count cap, learned from reading the old
repo's own `coherence.py` docstring (which already called the unit-count-only cap "a safety
fallback, not the normal case") during a thorough salvage/tweak pass this session.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S4 `source_reconciliation` (retry, prior round) | 14 batches, 14 calls | All accepted — the full, uncapped 541-unit set. |
| S5 `presentation_planning` (prior round) | 1 call | Accepted. |
| S6 `section_authoring` (prior round) | 1 per task | All accepted. |
| Render | 0 (deterministic) | 155,143 characters, 1,525 lines. |
| S8 `coherence` (this retry, with the batch-sizing fix) | 3 batches, 3 calls | All accepted on the first attempt — no truncation. `coherence#1` revised `key_capabilities/capability:1`; `coherence#2` revised `api_reference/intro` plus 12 `api_reference/hub:public_symbol:*` sub-slots; `coherence#3` made no revisions. |

Re-rendered: 156,224 characters. This repository's cascade is now complete through S8.

## The known duplicate-opening defect recurs, at its documented mild-overlap severity

`inherited_unit:004.paragraph` was disposed `VERIFIED_PRESERVE` into "opening" at S4. The rendered
opening shows the already-documented pattern: the preserved paragraph and the freshly authored
opening both describe the product as reading/writing/manipulating PDF files, a partial, not
near-total, overlap. The duplicate-opening guard's own documented scope limit (whole-unit,
70%-per-sentence-stem-overlap detection, not partial/first-sentence-only detection) correctly did
not fire here, consistent with the two previously confirmed instances of this exact scope limit
(20th cascade, aspose-slides-foss/.NET; 28th cascade, aspose-cells-foss/Java). Not a new finding,
not a regression — the cascade completing despite this known, documented, out-of-scope-for-this-
fix pattern is itself consistent with every other completed cascade this session.

## Honest scope limits

- This fix is narrowly scoped to the S8 batch-truncation failure mode. It does not touch, and does
  not claim to touch, the duplicate-opening-paragraph defect class, which recurred here exactly as
  documented elsewhere.
- The fix can only ever produce more, smaller coherence batches than before; no already-accepted
  cascade's batch grouping is affected unless its rendered text was itself large enough to be at
  real truncation risk.
