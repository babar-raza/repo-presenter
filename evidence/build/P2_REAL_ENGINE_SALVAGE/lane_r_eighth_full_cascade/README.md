# The eighth complete, real Lane R cascade — first beyond one-per-ecosystem

2026-10-22. `aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python`. Eighth cascade run, and the
first fired for portfolio-scale coverage rather than ecosystem-first coverage (every ecosystem
already had one real cascade run after the seventh; this is a second Python repository, a
different product family from aspose-3d-foss/Aspose.Cells-FOSS-for-Python).

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 59 dispositions / 77 units | Accepted. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task | All accepted on the first attempt. |
| Render | 0 (deterministic code) | 16,622 characters, 295 lines. |
| S8 `coherence` | 2 batches, 4 calls total | `coherence#1`: 4 sections, 2 calls, revised `key_capabilities/capability:1` and `quick_start/lead_in`. `coherence#2`: 2 sections, 2 calls, revised 7 units across `api_reference` and `scope_limitations`. | Re-rendered: 16,781 characters. |

## The same known defect, confirmed an eighth time

The rendered README again carries the duplicate-opening-paragraph defect (lines 5 and 7–11 of
`README.rendered.md`): a preserved README paragraph and the freshly authored `opening` unit say
almost the same thing back to back. Eighth for eighth: every cascade fired this session has shown
this defect class. Coherence revised units in `key_capabilities`, `quick_start`, `api_reference`,
and `scope_limitations` this run — its heaviest revision load yet — but again left `opening`
itself untouched, consistent with the seventh (typescript) run and in contrast with the sixth
(rust) run where it worsened the same unit. This is additional evidence, not a new decision — the
real fix remains precisely located in the unported validation/review/repair subsystem and stays
correctly deferred as its own future, multi-session task.

## Honest scope limits

- 8 of 36 repositories now have a full real cascade run. All 7 ecosystems have been exercised at
  least once (as of the seventh cascade); this eighth run is the first step toward broader
  portfolio coverage within an already-proven ecosystem (a second Python repository).
