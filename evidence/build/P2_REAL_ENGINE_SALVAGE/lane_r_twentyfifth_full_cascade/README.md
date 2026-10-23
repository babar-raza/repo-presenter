# The twenty-fifth complete, real Lane R cascade — the first clean "opening" this session, and why

2026-10-23. `aspose-psd-foss/Aspose.PSD-FOSS-for-.NET`. Twenty-fifth full cascade (through S8),
a fourth .NET repository, and the first run this session where "opening" shows NO duplicate at
all -- a genuine, informative control case, not a lucky accident.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 49 dispositions / 15 units | Accepted. The README's own lead paragraph (`inherited_unit:002.paragraph`) was disposed `VERIFIED_REWRITE`, not `VERIFIED_PRESERVE`. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task | All accepted on the first attempt. |
| Render | 0 (deterministic code) | 8,016 characters, 134 lines -- the smallest rendered README this session. |
| S8 `coherence` | 1 batch, 1 call | Accepted on the first attempt, revised `opening/opening`. | Re-rendered: 8,049 characters. |

## Why there is no duplicate here: the disposition itself was different

Every prior cascade's duplicate traced back to a `VERIFIED_PRESERVE` (or `VERIFIED_MOVE`)
disposition routing an inherited paragraph into "opening" *verbatim*, which the renderer then
prints as its own separate block beside the freshly authored S6 unit -- two paragraphs, printed
independently, both covering the product's identity.

Here, S4 reconciliation disposed the README's lead paragraph `VERIFIED_REWRITE` instead. Unlike
`VERIFIED_PRESERVE`, a `VERIFIED_REWRITE` disposition does not get its own verbatim render block;
the authored "opening" unit is the only prose this section prints, so there is nothing for it to
duplicate. The `README.rendered.md` for this repository shows exactly one opening paragraph, and
`preserved_opening_text()` (part of `CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL`'s own fix)
correctly found no preserved unit's text to protect against (its own `_placed_units()` lookup
restricts to the rendering-relevant disposition set, and this unit's actual render path differs
from the `VERIFIED_PRESERVE` cases the fix targets).

This is the first real evidence, independent of inspection, that the duplicate-opening defect is
tied to a SPECIFIC disposition choice (`VERIFIED_PRESERVE`/`VERIFIED_MOVE` into "opening"), not an
unavoidable property of every repository's "opening" section -- when S4 reconciliation instead
chooses `VERIFIED_REWRITE` for the inherited lead paragraph, the defect simply does not occur.
This sharpens, rather than contradicts, the root-cause diagnosis already on record (project/
state.yaml's own WIRE_PRESENTATION_PLANNING_AND_REAL_UNIT_CHECKS card): the real general fix
belongs at S4's disposition-choice step, deciding `VERIFIED_REWRITE` over `VERIFIED_PRESERVE`
whenever "opening" will also receive fresh authored content -- exactly the kind of judgment the
deferred validation/review/repair subsystem would make, and precisely what this session's
narrower `states_all()`-based guard does not attempt.

## Honest scope limits

- 24 of 36 repositories now have a FULL real cascade run through S8 (plus two,
  aspose-html-foss/Python and aspose-slides-foss/Cpp, with S3-S6+render only, and
  aspose-pdf-foss/TypeScript failed at S4 before reaching render).
