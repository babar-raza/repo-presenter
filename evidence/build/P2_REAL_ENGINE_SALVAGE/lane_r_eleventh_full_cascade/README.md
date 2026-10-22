# The eleventh complete, real Lane R cascade — first run with the duplicate-opening fix active from the start

2026-10-22. `aspose-email-foss/Aspose.Email-FOSS-for-Python`. Eleventh cascade run, a fourth step
toward portfolio-scale coverage (a fourth Python repository, different product family from
aspose-3d-foss/Python, aspose-barcode-foss/Python, and aspose-cells-foss/Python). The first
cascade fired with CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL's fix already wired in from the
start, rather than retrofitted via a targeted recheck afterward.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 94 dispositions / 25 units | Accepted. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task | All accepted on the first attempt. |
| Render | 0 (deterministic code) | 14,706 characters, 274 lines. |
| S8 `coherence` | 2 batches, 3 calls total | `coherence#1`: 1 call, no revisions. `coherence#2`: 2 calls (one real reject→accept cycle), no revisions in the final accepted output. | Re-rendered: 14,706 characters (byte-identical to the pre-coherence render). |

## The same known defect, confirmed an eleventh time — the duplicate-opening guard did not need to fire here

The rendered README again carries the duplicate-opening-paragraph defect in its mild-to-moderate
form (lines 5 and 7–11 of `README.rendered.md`): the authored `opening` unit and the preserved
README paragraph both describe the product's identity, overlapping in substance (CFB/`.msg`
processing, `MapiMessage`, no COM/Outlook dependency) without being a near-total duplicate of each
other. Eleventh for eleventh: every cascade fired this session has shown this defect class.

`coherence#2`'s one reject→accept cycle is not attributable with certainty to the new
duplicate-opening guard specifically (unlike the two targeted rechecks against the sixth and
ninth cascades' own repositories, where the rejection reason was directly inspected and confirmed)
— `coherence#2` covers two sections, and the retry's final output matches the pre-coherence text
exactly, consistent with either outcome the guard is designed to produce (reject-then-keep-safe,
as seen in both targeted rechecks). The new fix remains honestly scoped as partial: it closes the
near-total-duplication end of the range, not this cascade's milder structural overlap, which
still needs the deferred validation/review/repair subsystem.

## Honest scope limits

- 11 of 36 repositories now have a full real cascade run. All 7 ecosystems have been exercised
  at least once; this is the fourth step of ongoing extension toward full portfolio coverage (now
  4 Python repositories, 2 TypeScript repositories, 1 each of go, net, java, cpp, rust).
