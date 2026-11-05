# Maintainer-authored content: calibration baseline (2026-11-05)

Requirement 6 of `docs/MAINTAINER_CONTENT_PRESERVATION.md` ("calibrate through portfolio-wide examination ...
rather than assumptions"). This is the measured baseline of what the pipeline did with maintainer-authored
README content **before** the `PRESERVE_ATTRIBUTED` disposition existed, read from the 12 sealed Lane R
bundles on origin (`refs/repository-presenter-state/bundles/*`, each at its product's upstream HEAD).

## Dispositions across 12 sealed candidates (957 inherited units)

| Disposition | Units |
|---|---|
| SUPERSEDE_REDUNDANT | 567 |
| VERIFIED_PRESERVE | 184 |
| VERIFIED_MOVE | 93 |
| OMIT_UNSUPPORTED | 74 |
| VERIFIED_REWRITE | 16 |
| NON_CONTENT | 7 |
| DEFER_UNRESOLVED | 6 |
| CORRECT_WITH_EVIDENCE | 5 |

## The 74 omissions, by the reason their own rationale gives

| Reason | Units | Under the requirement |
|---|---|---|
| Heading, `<details>` wrapper or badge markup | 45 | Mostly structural; acceptable when the content they framed is placed elsewhere, but each must name where |
| Redundant with facts or other text | 9 | Acceptable (nothing lost) |
| Tied to an example recorded CONTRADICTED | 8 | **Only as sound as the contradiction.** At least one is false: Cells Go's "Picture Embedding" section was dropped for example 6, a documented abbreviation (the helper it names exists in `examples/picture/main.go`). The verifier fixes of 2026-11-05 (fixtures never staged under a written name; failures on a substitute input are UNRESOLVED) remove a class of such false contradictions |
| No fact supports it (unverified content) | 7 | **The case the requirement changes**: e.g. Imaging .NET's format table, HTML Python's description of its test directories, Cells C++'s in-memory-stream constructor note. These are `PRESERVE_ATTRIBUTED` (kept verbatim, attributed), not deletions |

Observation: 9.7 % (74 / 957) of maintainer units were dropped, but only 7 for lack of evidence alone. The larger,
quieter loss is **SUPERSEDE_REDUNDANT (567)**: a unit judged covered by generated text is not printed. The
requirement's rule 5 ("avoid ... replacing valuable human-authored information with generic generated
content") bears on that disposition too; it is the next thing to examine against real examples (which
superseded units carried history, intent or unique knowledge the replacement lost).

## Method

Read-only: `dispositions.json` and `facts.json` of each sealed bundle (exported with
`bundle_store.export_bundle`), rationale text classified by keyword (`contradicted`; `redundant`/`duplicat`;
heading/html_block/badge_row unit kinds or `wrapper`/`heading`; `promot`/`marketing`; otherwise "no fact
supports it"). No provider call, no upstream access.
