# The twenty-eighth complete, real Lane R cascade — the heaviest overlap yet, then a clean recovery

2026-10-23. `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`. Twenty-eighth full cascade (through
S8), a third Java repository and the first `aspose-cells-foss`/Java pairing cascaded this
session.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 57 dispositions / 13 units | Accepted. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task | All accepted on the first attempt. |
| Render | 0 (deterministic code) | 22,994 characters, 318 lines. |
| S8 `coherence` | 1 batch, 2 calls | One real reject→accept cycle; revised `opening/opening`, `api_reference/intro`, and `scope_limitations/limitation:2`. | Re-rendered: 23,143 characters. |

## The known defect at render time -- the heaviest word-for-word overlap this session, yet still accepted by S6

The pre-coherence render (lines 5 and 7–11 of `README.rendered.md`) shows the heaviest capability-
list overlap observed this session: both paragraphs enumerate "cell values and formulas, styling,
page setup, data validation, conditional formatting, auto filters, comments, embedded pictures
and charts, drawing shapes, and Excel tables (ListObjects)" in nearly identical wording, and both
end with "Saving is currently limited to .xlsx." This did NOT trigger `states_all()`'s
full-containment test, because the paragraphs' OPENING clauses differ enough (one leads with
"reads and writes... loads, modifies, and saves"; the other leads with "is a free, open-source,
pure-Java spreadsheet library... targets Java 17... Apache POI is used only in test scope") that
neither fully contains the other sentence-by-sentence -- a second concrete instance of the
twentieth cascade's documented scope limit (whole-unit, not per-sentence, detection).

## A clean recovery at S8

Coherence's own first attempt at revising `opening` was rejected (one real reject→accept cycle);
the accepted retry is a genuine success, not a worsening or a no-op: it replaced the capability-
list restatement with a technically specific paragraph naming `Workbook`, `WorksheetCollection`,
`VisibilityType`, `LoadOptions`, and `Workbook.getLoadDiagnostics()` -- content the preserved
paragraph states nothing like. This is the second run this session (after the fourteenth cascade)
where coherence's own revision of `opening` is an unambiguous improvement.

## Honest scope limits

- 27 of 36 repositories now have a FULL real cascade run through S8 (plus two,
  aspose-html-foss/Python and aspose-slides-foss/Cpp, with S3-S6+render only; plus two
  abandoned attempts for unrelated/own-guard reasons this session).
