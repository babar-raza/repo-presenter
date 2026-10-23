# Twenty-fourth cascade: S3-S6+render complete 2026-10-23, S8 completed on retry 2026-10-23 -- with a new finding

2026-10-23. `aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp`. S3-S6 and the pre-coherence render
all accepted and confirm the known duplicate-opening defect a twenty-fourth time at the render.
S8 coherence's first batch was accepted (revising `opening/opening`, `api_reference/intro`, and
`api_reference/hub:public_symbol:aspose.slides.foss`), but the second batch failed closed on an
unrelated, pre-existing rejection: `scope_limitations`'s `limitation:6` unit used `sections()` as
an identifier that is not an accepted fact value, and the recover's own correction was rejected
for the same reason. Because the overall `run_lane_r_coherence.py` script only persists
`content_units.coherent.json`/`README.coherent.md` after every batch succeeds, the first batch's
accepted "opening" revision was never written to disk and could not be recovered for this
evidence record -- a real limitation of that script's own all-or-nothing persistence, not
examined further here.

This is the sixth distinct unrelated, pre-existing rough edge this session's broader cascade
sweep has surfaced (after the "TrueType" identifier rejection, two title-restatement rejections,
the "cites facts outside this section's set" rejection, and a missing-disposition rejection on
aspose-pdf-foss/TypeScript earlier this same round) -- none of them related to
`CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL`'s own check. This repository's cascade is left
incomplete, not forced through with a workaround.

## Update, 2026-10-23: S8 retried and completed -- coherence introduced a new sentence-level duplicate

S8 was re-fired against the same saved S3-S6 artifacts (not re-run). This time both batches
completed cleanly: `coherence#1` (1 call, no rejection) revised `opening/opening`,
`api_reference/intro`, and `api_reference/hub:public_symbol:aspose.slides.foss`;
`coherence#2` (2 calls, one reject→accept cycle) made no revisions. Re-rendered: 39,334
characters.

A new, precise finding, not previously observed: the ORIGINAL pre-coherence `opening` unit
(`content_units.json`) was "It reads and writes PowerPoint presentations in formats including
... It supports creating, reading, and editing presentations, including comment authors,
comments, replies, and document properties." -- it did NOT open with a product-identity
sentence at all. Coherence's accepted revision PREPENDED a new leading sentence: "Aspose.Slides
FOSS for Cpp is a free, open-source, MIT-licensed C++ library for creating, reading, and editing
PowerPoint presentations." -- which is now a near word-for-word match of the preserved
paragraph's own first sentence ("Aspose.Slides FOSS for C++ is a free, open-source, MIT-licensed
C++ library for creating, reading, and editing PowerPoint `.pptx` presentations.").

This is not the same pattern as the sixth/ninth cascades (coherence worsening an EXISTING
overlap) or the twentieth/twenty-eighth cascades (a unit's own first sentence already
duplicating before coherence touches it) -- here coherence CREATED a brand-new sentence-level
duplicate in a unit that had none before, by prepending an identity clause the model apparently
judged the "opening" section needed. The duplicate-opening guard correctly did not fire (the
revised unit's OTHER sentences differ enough that `states_all()`'s whole-unit test does not
trigger), consistent with its already-documented scope limit -- but this is the first evidence
that coherence's own editing behavior, not just S6's original authoring, can independently
introduce the kind of sentence-level duplication the guard cannot see.

## Honest scope limits

- This repository's cascade is now complete through S8 (updated 2026-10-23); see
  project/state.yaml's CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL card for this new finding and
  WIRE_PRESENTATION_PLANNING_AND_REAL_UNIT_CHECKS for the current portfolio-wide count.
