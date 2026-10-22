# The twentieth complete, real Lane R cascade — a real limit of the duplicate-opening check's own scope, found

2026-10-22. `aspose-slides-foss/Aspose.Slides-FOSS-for-.NET`. Twentieth full cascade (through
S8), a third .NET repository.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 95 dispositions / 18 units | Accepted. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task | All accepted on the first attempt -- including "opening" (see finding below). |
| Render | 0 (deterministic code) | 29,125 characters, 445 lines. |
| S8 `coherence` | 2 batches, 2 calls total | Both accepted on the first attempt, no revisions anywhere. | Re-rendered: byte-identical, 29,125 characters. |

## A new finding: the duplicate-opening guard's own blind spot, confirmed for real

The pre-coherence render shows the WORST literal duplication yet observed at the sentence level
-- not caught by `CLOSE_DUPLICATE_OPENING_PARAGRAPH_PARTIAL`'s check, and this time precisely
because of a real, previously undocumented limitation in how that check works, not a bug.

The preserved paragraph (line 7-9 of `README.rendered.md`) reads:

> An MIT-licensed .NET library that creates, reads and edits PowerPoint `.pptx` presentations by
> building the Office Open XML package itself — no PowerPoint installation, no COM interop, no
> native dependency and no NuGet dependencies at all.

The authored "opening" unit's FIRST SENTENCE (`content_units.json`) is a near word-for-word
restatement of exactly this -- "Aspose.Slides FOSS for .NET is an MIT-licensed .NET library that
creates, reads and edits PowerPoint .pptx presentations by building the Office Open XML package
itself — no PowerPoint installation, no COM interop, no native dependency and no NuGet
dependencies at all." But the unit's SECOND and THIRD sentences add genuinely new content (the
`net8.0`/`net10.0` targets, the namespaces, the PDF/HTML/image limitation), so `states_all()` --
which requires the WHOLE unit's text to be covered before it fires -- correctly did not flag it:
the unit as a whole is not fully redundant, even though its opening sentence specifically is.

This is a real, previously undocumented limit of the check's scope: it operates at the
whole-unit level (`states_all`), while the recovery path (`uncovered()`) already works at the
per-sentence level. Detection and recovery are asymmetric -- recovery could have trimmed just the
redundant first sentence had detection flagged the unit at all. This is not a regression and not
a false negative in the sense of "the check is broken" -- it is operating exactly as designed and
scoped (whole-unit full-containment, documented from the start as catching "near-total
duplication," not partial sentence-level duplication). It is, however, the clearest real evidence
yet that the check's scope is narrower than the full space of the duplicate-opening defect, and a
concrete, well-specified direction for extending it (per-sentence detection, not just per-unit)
if this work continues beyond this session.

## Honest scope limits

- 20 of 36 repositories now have a FULL real cascade run through S8 (plus one,
  aspose-html-foss/Python, with S3-S6+render only; plus five abandoned attempts for unrelated
  or already-documented reasons this session).
