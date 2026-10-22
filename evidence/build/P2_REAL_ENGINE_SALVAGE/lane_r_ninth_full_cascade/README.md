# The ninth complete, real Lane R cascade — coherence's worst instance of the known defect yet

2026-10-22. `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`. Ninth cascade run, second step toward
portfolio-scale coverage (a second TypeScript repository, different product family from
aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript).

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S3 `repository_investigation` | 1 | Accepted on the first attempt. |
| S4 `source_reconciliation` | 83 dispositions / 110 units | Accepted. |
| S5 `presentation_planning` | 1 | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task | All accepted on the first attempt. |
| Render | 0 (deterministic code) | 20,070 characters, 263 lines. |
| S8 `coherence` | 3 batches, 3 calls total | `coherence#1`: 2 sections, 1 call, revised `opening/opening`. `coherence#2`, `coherence#3`: 1 call each, no revisions. | Re-rendered: 20,071 characters (one character different from the pre-coherence render). |

## The same known defect, confirmed a ninth time — this run's coherence pass produced the worst instance yet

The rendered README again carries the duplicate-opening-paragraph defect before coherence (lines
3 and 5–9 of `README.rendered.md`): a preserved README paragraph and the freshly authored
`opening` unit say almost the same thing back to back. Ninth for ninth.

This run's coherence pass revised `opening` — and made it nearly a **verbatim** copy of the
preserved paragraph beside it (see `README.coherent.md` lines 3 and 5–9): the only differences
are backtick code-formatting of "Node" and line-wrap width; every word of substance is identical.
The re-rendered document grew by exactly one character (20,070 → 20,071), consistent with that
near-exact match. This is a direct continuation of the sixth (rust) finding — coherence's
revision of `opening` moved it *toward* the preserved duplicate rather than differentiating it —
but this is the most severe instance observed yet: not a close paraphrase, a near word-for-word
copy. This confirms, more strongly than before, that coherence's revise/no-revise choice and its
revision direction for `opening` are incidental to its actual remit (cross-unit consistency), not
a mechanism that detects or avoids duplication — asking it to make the document "read
consistently" can push two already-similar passages to become nearly identical. The real fix
remains precisely located in the unported validation/review/repair subsystem and stays correctly
deferred as its own future, multi-session task.

## Honest scope limits

- 9 of 36 repositories now have a full real cascade run. All 7 ecosystems have been exercised at
  least once; this is the second of what is intended to be ongoing extension toward full
  portfolio coverage (now 2 TypeScript repositories, 2 Python repositories, 1 each of go, net,
  java, cpp, rust).
