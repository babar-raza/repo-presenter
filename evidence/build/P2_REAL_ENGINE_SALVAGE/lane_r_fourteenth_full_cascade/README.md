# The fourteenth complete, real Lane R cascade — coherence successfully differentiates "opening"

2026-10-22. `aspose-slides-foss/Aspose.Slides-FOSS-for-Python`. Fourteenth full cascade (through
S8), a sixth Python repository. Two repositories were tried and abandoned first this round
(aspose-font-foss/Python and aspose-psd-foss/Python both failed closed at S6 on unrelated,
pre-existing rejections — a "TrueType" identifier and a title-restatement rule respectively,
neither related to the duplicate-opening fix; not fixed, not worked around). aspose-page-foss/
Python also failed closed, but on the duplicate-opening guard itself — a second confirmed
instance of the fail-closed pattern already documented for aspose-email-foss/.NET, folded into
that entry.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 155 dispositions / 48 units | Accepted. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task | All accepted on the first attempt. |
| Render | 0 (deterministic code) | 64,419 characters, 1,066 lines. |
| S8 `coherence` | 3 batches, 5 calls total | `coherence#1`: 3 sections, 2 calls (one reject→accept cycle), revised `opening/opening`. `coherence#2`, `#3`: no revisions. | Re-rendered: 64,164 characters. |

## The known defect at render time, then successfully differentiated by coherence

The pre-coherence render carries the duplicate-opening-paragraph defect in a moderate form (lines
5 and 7–10 of `README.rendered.md`): both paragraphs name `Presentation`/`Slide`/`Shape`/
`TextFrame` and both state "no Microsoft Office installation or COM interop required" nearly
verbatim. Fourteenth for fourteenth at the pre-coherence stage.

This time, coherence's revision of `opening` is a genuine success: the duplicate-opening guard
rejected its first attempt, and the accepted retry shortened `opening` to a compact, clearly
distinct sentence ("It reads and writes PowerPoint `.pptx` presentations, creates new
presentations, adds and removes slides, and saves to `.pptx` format.") that states none of the
preserved paragraph's claims. This is the first run where coherence revised `opening` and
produced an unambiguous improvement (as opposed to the sixth/ninth cascades' worsening, or the
seventh/eighth/tenth/thirteenth's harmless no-op).

## Honest scope limits

- 14 of 36 repositories now have a FULL real cascade run through S8 (plus one,
  aspose-html-foss/Python, with S3-S6+render only; plus two abandoned attempts this round for
  unrelated pre-existing reasons, and one more — aspose-page-foss/Python — for the duplicate-
  opening guard's own documented fail-closed pattern).
