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

## Re-measured after v14 (2026-11-06 hosted pilot): the prompt rule did not hold

Email .NET and Imaging .NET were regenerated on current `main` (source_reconciliation v14). Supersession did not
fall (Email 48 -> 48, Imaging 38 -> 39 units) and both Email losses the v14 rule names as examples are still
superseded and absent from the new README: "runs on Windows, Linux, macOS, Docker containers, and serverless
functions" (unit 016) and `CfbReader` being "useful when diagnosing a damaged or non-standard file" (unit 036).
`PRESERVE_ATTRIBUTED` is now used (5 units across the two).

Why the existing mechanical test missed them: `content_presence.unstated` judges a sentence that spells an anchor
(`.NET 8.0`, `CfbReader`) by its anchors alone, and the README prints the anchor. `strict=True` also word-tests
such a sentence on its non-anchor words; on the 550 superseded units of the 12 sealed bundles it flags 98
(lenient: 80), and after exempting markup the renderer replaces by design (headings, badge rows, HTML wrappers,
the mermaid diagram, lead-ins carried with their block) units in all 12 bundles: paragraphs ~23, lists ~23
(Rust method lists, dependency-purpose notes), tables ~29 (type descriptions the API Reference lists only by
name). Both Email losses are among them.

Change (owner decision 2026-11-06: blocking, auto-repaired): BC-05 runs `validation/supersession.py`; each such
unit is a RECONCILING failure naming the unit, so the repair loop issues a per-unit reconciliation patch with the
missing pieces quoted, and a candidate that still loses the content is rejected. `RENDERER_VERSION` 35 reopens
every sealed candidate at RECONCILING. Re-measure with this script after the next regeneration.

## Pilot rounds 2 and 3 under the check (2026-11-06)

- **Round 2** (main fcfdc1d): all three Lane R candidates failed BC-05 unrepaired. Cause, found by a clean local
  Email .NET run: the repair loop made one defect per check, patched one batch once and never retried it. Then,
  with one defect per unit: a reply that re-superseded the unit was accepted as repaired, and a keep into the
  opening or the API Reference was re-superseded by the normaliser. Each fixed (PR #26); a paragraph made only
  of positional references is exempt (kept, it dangled).
- **Round 3** (main 7a73f90): **Imaging .NET sealed ACCEPTED** (BC-05 clean, independent review ACCEPT).
  Email .NET still blocked on units 004 (opening: "needs no Microsoft Outlook installation"), 043 (CFB type
  descriptions) and 057 (`SetProperty()`/`GetPropertyValue()` list): the hosted log did not show the repair
  attempts, so `present.py` now prints the repair ledger on a block. Cells-Rust failed earlier, in source
  reconciliation (a retryable `dangling_pointer` rejection after three asks), unrelated to this check.
