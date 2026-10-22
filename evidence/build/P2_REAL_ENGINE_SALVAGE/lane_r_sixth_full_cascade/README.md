# The sixth complete, real Lane R cascade — a sixth ecosystem

2026-10-22. `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust`. Sixth cascade run, sixth ecosystem
(`rust`, after python, go, net, java, cpp).

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 5 (batched, 91 units across 3 batches) | Batch 1 needed a real reject→accept cycle (2 calls); batch 2 accepted first try; batch 3 needed a real reject→accept cycle (2 calls). Disposition counts: `{'SUPERSEDE_REDUNDANT': 20, 'OMIT_UNSUPPORTED': 33, 'VERIFIED_PRESERVE': 37, 'CORRECT_WITH_EVIDENCE': 1}`. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. `sections 11/18, capabilities 8, hubs 12, examples 1+0, links 0, limitations 6`. |
| S6 `section_authoring` | 5 (one per real authored task: `opening`, `key_capabilities`, `api_reference`, `api_reference#types-1`, `scope_limitations`) | All 5 accepted on the first attempt. 36 content units merged. |
| Render | 0 (deterministic code) | 38,176 characters, 608 lines. |
| S8 `coherence` | 4 (batched, 3 batches) | `coherence#1`: 2 sections, 2 calls, revised `opening/opening` and `key_capabilities/capability:1`. `coherence#2` and `#3`: 1 call each, no revisions. | Re-rendered: 38,290 characters. |

## The same known defect, confirmed a sixth time — and made worse by coherence this time

The rendered README again carries the duplicate-opening-paragraph defect (lines 5 and 7–12 of
`README.rendered.md`): a preserved README paragraph and a freshly authored "opening" unit that
say almost the same thing back to back. Sixth for sixth: every cascade fired this session has
shown this defect class.

This run adds a genuinely new data point. S8 coherence's own revision of the authored `opening`
unit (see `README.coherent.md` lines 1–12) did not differentiate the authored text from the
preserved paragraph beside it — it moved the authored text closer to the preserved paragraph,
nearly paraphrasing it line-for-line ("Aspose.Cells FOSS for Rust is a free, open-source,
pure-Rust library for creating, loading, editing, and saving Excel `.xlsx` ... workbooks" in
both). Coherence's own remit is cross-unit consistency, not duplicate detection, so this is not
a coherence bug — it is confirmation that this mechanism cannot be the fix: asking it to make the
document "sound consistent" can make a duplication read more alike, not less. The real fix
remains precisely located in the unported validation/review/repair subsystem (see
`project/state.yaml`'s `WIRE_PRESENTATION_PLANNING_AND_REAL_UNIT_CHECKS` card) and stays correctly
deferred as its own future, multi-session task. This entry documents the new sub-finding, not a
new decision.

## Honest scope limits

- 6 of 36 repositories now have a full real cascade run (python, go, net, java, cpp, rust).
  TypeScript is the only remaining untried ecosystem for the full cascade; not yet at portfolio
  scale (1 repository per ecosystem, not all 36).
