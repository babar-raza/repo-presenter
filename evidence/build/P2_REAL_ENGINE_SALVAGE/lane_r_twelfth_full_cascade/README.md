# The twelfth Lane R cascade — S3-S6+render complete, S8 failed for an unrelated reason

2026-10-22. `aspose-html-foss/Aspose.HTML-FOSS-for-Python`. Twelfth cascade attempt, the largest
repository this session has fired a cascade against (332 content units after S6 -- by far the
most of any repository cascaded so far) and a fifth Python repository, different product family
from the other four.

Two repositories were tried and abandoned before this one: `aspose-gis-foss/Aspose.GIS.FOSS-
for-.Net` (no Lane L facts.json exists -- this repository's own default branch genuinely has no
README at all, already documented as a real external failure, not retried) and
`aspose-font-foss/Aspose.Font-FOSS-for-Python` (S6's `api_reference#types-1` task failed closed
on an unrelated, pre-existing rejection -- `identifiers that are not accepted fact values:
TrueType` -- not something this session's duplicate-opening fix touches; left incomplete, not
worked around).

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 103 dispositions / 332 units | Accepted. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task (multiple `api_reference#types-N` sub-batches for this large API surface) | All accepted. |
| Render | 0 (deterministic code) | 68,132 characters, 885 lines -- the largest rendered README this session has produced. |
| S8 `coherence` | 2 batches | `coherence#1`: 1 call, no revisions. `coherence#2`: **failed closed** -- `JobError: output rejected twice; last rejection: unit scope: cites facts outside this section's set: inherited_unit:046.paragraph`. |

## The same known defect, confirmed a twelfth time (at S6/render)

The pre-coherence rendered README again carries the duplicate-opening-paragraph defect in its
mild-to-moderate form (lines 5 and 7 of `README.rendered.md`): the authored `opening` unit names
specific classes/methods (`HTMLDocument.parse`, `CSSStyleSheet`, `URLSearchParams`, `JSContext`)
while the preserved paragraph beside it restates the product's identity and capability summary
in different words covering similar ground. Twelfth for twelfth.

## S8's failure is unrelated to the duplicate-opening fix

`coherence#2`'s rejection ("cites facts outside this section's set") is a different, pre-existing
`unit_checks()` rule (the slot-fact-citation guard, unrelated to `preserved_opening_text`/
`states_all`) tripping on a different section (`scope`, not `opening`). This is the second
unrelated pre-existing rough edge this session's twelfth-cascade attempt has surfaced (after the
font-foss `TrueType` identifier rejection) -- both on real calls against larger, more complex
repositories than the first eleven cascades exercised. Neither is a regression caused by
`CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL`; both are left incomplete and unfixed here, out of
this card's scope, and noted for a future taskcard rather than worked around.

## Honest scope limits

- 12 of 36 repositories now have at least a partial (S3-S6+render) real cascade run; this one's
  S8 stage did not complete. 11 of 36 have a FULL cascade (through S8) completed and committed.
