# Maintainer-authored content: calibration baseline (2026-11-05)

Requirement 6 of `docs/MAINTAINER_CONTENT_PRESERVATION.md` ("calibrate through portfolio-wide examination ...
rather than assumptions"). This is the measured baseline of what the pipeline did with maintainer-authored
README content **before** the `PRESERVE_ATTRIBUTED` disposition existed, read from the 12 sealed Lane R
bundles on origin (`refs/repository-presenter-state/bundles/*`, each at its product's upstream HEAD).

## Dispositions across 12 sealed candidates (912 inherited units)

| Disposition | Units |
|---|---|
| SUPERSEDE_REDUNDANT | 549 |
| VERIFIED_PRESERVE | 181 |
| VERIFIED_MOVE | 80 |
| OMIT_UNSUPPORTED | 69 |
| VERIFIED_REWRITE | 15 |
| NON_CONTENT | 7 |
| DEFER_UNRESOLVED | 6 |
| CORRECT_WITH_EVIDENCE | 5 |

## The 69 omissions, by the reason their own rationale gives

| Reason | Units | Under the requirement |
|---|---|---|
| Heading, `<details>` wrapper or badge markup | 45 | Mostly structural; acceptable when the content they framed is placed elsewhere, but each must name where |
| Redundant with facts or other text | 9 | Acceptable (nothing lost) |
| Tied to an example recorded CONTRADICTED | 8 | **Only as sound as the contradiction.** At least one is false: Cells Go's "Picture Embedding" section was dropped for example 6, a documented abbreviation (the helper it names exists in `examples/picture/main.go`). The verifier fixes of 2026-11-05 (fixtures never staged under a written name; failures on a substitute input are UNRESOLVED) remove a class of such false contradictions |
| No fact supports it (unverified content) | 7 | **The case the requirement changes**: e.g. Imaging .NET's format table, HTML Python's description of its test directories, Cells C++'s in-memory-stream constructor note. These are `PRESERVE_ATTRIBUTED` (kept verbatim, attributed), not deletions |

Observation: 7.6 % (69 / 912) of maintainer units were dropped, but only 7 for lack of evidence alone. The larger,
quieter category is **SUPERSEDE_REDUNDANT (549)**: a unit judged covered by generated text is not printed. The
requirement's rule 5 ("avoid ... replacing valuable human-authored information with generic generated
content") bears on that disposition too; it is the next thing to examine against real examples (which
superseded units carried history, intent or unique knowledge the replacement lost).

## SUPERSEDE_REDUNDANT examined (2026-11-06, requirement 5)

`scripts/maintainer_content_audit.py` measures, per superseded unit, the share of its distinctive words that
still occur anywhere in the final README: **467 of 549 carried (>= 0.8), 74 partly (0.5-0.8), 8 mostly gone
(< 0.5)**. Most supersessions are sound (dependency and test-tool lists the renderer prints from facts; class
tables the API reference carries). Reading the lowest-coverage cases found three real loss patterns, each
maintainer knowledge the replacement did not carry:

1. **Enum value lists** superseded "by the API Reference", which lists types, not values (Note Python:
   `HorizontalAlignment: Left, Center, Right`; `FileFormat: Unknown, OneNote2010, OneNoteOnline, OneNote2007`).
2. **Platform and environment statements** superseded by a target-framework fact (Email .NET: "runs on Windows,
   Linux, macOS, Docker containers, and serverless functions").
3. **Usage insight** superseded by an example (Email .NET: `CfbReader` is "useful when diagnosing a damaged or
   non-standard file").

Change: the source_reconciliation prompt (v14) now says a unit is superseded only when the replacement carries all
of its substance (listed values, conditions, when/why insight), naming these three patterns; otherwise it is kept
(`VERIFIED_PRESERVE`/`VERIFIED_MOVE`, or `PRESERVE_ATTRIBUTED` when no fact confirms it). It takes effect when the
candidates are regenerated; re-run the script then to see whether the low and partial buckets shrink.

Note: the earlier counts on this page double-counted one bundle exported twice; corrected above (912 units).

## Method

Read-only: `dispositions.json` and `facts.json` of each sealed bundle (exported with
`bundle_store.export_bundle`), rationale text classified by keyword (`contradicted`; `redundant`/`duplicat`;
heading/html_block/badge_row unit kinds or `wrapper`/`heading`; `promot`/`marketing`; otherwise "no fact
supports it"). No provider call, no upstream access.
