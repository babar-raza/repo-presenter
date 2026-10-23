# Twenty-fourth cascade attempt: S3-S6+render complete, S8 failed for an unrelated reason

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

## Honest scope limits

- 23 of 36 repositories have a FULL real cascade run through S8; this twenty-fourth attempt and
  aspose-html-foss/Python both have S3-S6+render only.
