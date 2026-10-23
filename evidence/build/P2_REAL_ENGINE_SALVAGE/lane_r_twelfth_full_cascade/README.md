# The twelfth Lane R cascade — S3-S6+render complete 2026-10-22, S8 completed on retry 2026-10-23

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

## Update, 2026-10-23: S8 retried and completed

With `CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL` now wired in and this session's broader cascade
sweep complete, S8 coherence was re-fired against the same saved S3-S6 artifacts (S3-S6 were not
re-run). This time it completed cleanly:

| Stage | Calls | Outcome |
|---|---|---|
| S8 `coherence` | 2 batches, 4 calls total | `coherence#1`: 2 calls (one reject→accept cycle), revised `opening/opening`. `coherence#2`: 2 calls (one reject→accept cycle), revised `api_reference/intro` and 8 `api_reference/hub:*` units plus `scope_limitations/scope`. | Re-rendered: 70,536 characters. |

The rejection that preceded `coherence#2`'s acceptance was the same unrelated, pre-existing
"cites facts outside this section's set" rule noted above -- except this time the model's retry
satisfied it, rather than failing twice. Coherence's revision of `opening` was a surface change
(fully-qualified identifier paths, e.g. `aspose_html.HTMLDocument.parse` instead of
`HTMLDocument.parse`), not a substantive change to the duplication's severity, which remains
mild-to-moderate as originally observed. This repository now has a complete cascade through S8.

## Honest scope limits

- This repository's cascade is now complete through S8 (updated 2026-10-23); see
  project/state.yaml's WIRE_PRESENTATION_PLANNING_AND_REAL_UNIT_CHECKS card for the current
  portfolio-wide count.
