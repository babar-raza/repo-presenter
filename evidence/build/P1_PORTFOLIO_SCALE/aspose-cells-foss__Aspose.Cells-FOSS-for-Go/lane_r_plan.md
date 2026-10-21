# Lane R plan — aspose-cells-foss/Aspose.Cells-FOSS-for-Go — FLAGGED: GENUINE LANE DIVERGENCE

**This is the case the playbook's "what not to do" section asks a run to find: Lane R
genuinely diverges from Lane L for this repository.** Flagging loudly per step 6/8.

## Also note: a separate, more severe finding, shared by both lanes

Before the completeness gap below, this repository also has one explicit *false* claim, not
merely an absence: the Scope section states "`CalculateFormula` supports only `SUM`,
`AVERAGE`, `MAX`, and `MIN`; any other formula returns an error rather than being evaluated"
(repeated in Key Capabilities and the At a Glance diagram). Reading `formula_engine.go` in
full shows `CalculateFormula` actually dispatches 22 functions across two switch statements --
the 4 named plus `COUNT`, `CONCAT`, `IF`, `COUNTIF`, `VLOOKUP`, `ROUND`, `ABS`, `POWER`,
`SQRT`, `LEN`, `LEFT`, `RIGHT`, `MID`, `UPPER`, `LOWER`, `AND`, `OR`, `NOT` -- each calling a
real, separately-defined implementation, not a stub (F-FORMULA-ENGINE-UNDERSTATED). This is
corrected identically in both lanes (it is a factual claim, not a structural-completeness
question), and is the single most important finding for this repository: a reader who
followed the Scope section's own words would believe formulas like `=IF(...)` or
`=ROUND(...)` fail, when they in fact work.

## Why the type-count/feature gap below is case (B)-adjacent, not case (A)

The live README is otherwise well-written and accurate about what it documents (facts.json's
other facts, aside from the formula-engine one above, are all SUPPORTED where checked). But it
is materially *incomplete*: a `git clone` + source grep at
this source_revision found 28 exported public types, not the 14 the README's own
Documentation & Resources section claims ("the complete, browsable reference for all 14
public types"). The 14 missing types back four real, tested, save-wired features --
**charts** (`Chart`/`ChartSeries`/`ChartAnchor`, `Worksheet.AddChart`, 420 lines of dedicated
tests across 3 files), **pivot tables** (`PivotTable`/`PivotDataField`,
`Worksheet.AddPivotTable`, 207 lines across 2 test files), **conditional formatting**
(`ConditionalFormatting`/`ConditionalFormattingRule`, `Worksheet.AddConditionalFormatting`,
262 lines across 2 test files), and **VBA/macro project storage**
(`VBAProject`, `Workbook.SetVBAProject`, 81 lines of tests) -- none of which appear anywhere
in Key Capabilities, At a Glance, Quick Start, Additional Examples, Project Structure, or the
API Reference table. Notably, the .NET, C++, and TypeScript siblings in this same family DO
document conditional formatting as a core capability -- this is a gap specific to the Go
README, not a family-wide pattern.

## Lane L vs. Lane R, concretely

Lane L (`lane_l_candidate.md`) makes the playbook's "smallest possible precise edit per fact":
it corrects the false "14 public types" sentence to stop overclaiming completeness, completes
the Project Structure tree (which also omitted 7 real source files and 1 example directory),
and adds one Scope and Limitations bullet disclosing that the four feature areas exist and
pointing readers at source/tests -- without authoring new Key-Capabilities prose or an
expanded API table.

Lane R (`lane_r_candidate.md`) is a real, larger, from-facts composition: it adds four new
Key Capabilities bullets (one per feature area, each naming the real types and methods), adds
all 14 missing rows to the API Reference table with descriptions drawn from each type's own
doc comments, corrects the public-type count to 28, and replaces Lane L's single disclosure
bullet with a proper Scope bullet about VBA's round-trip-only nature (the one genuine scope
limitation among the four areas; the other three are simply undocumented, not limited).
**`lane_r_candidate.md` is NOT byte-identical to `lane_l_candidate.md`** -- this is the
divergence case.

## What this does not do

This candidate does not fabricate new Quick Start code examples or claim execution results
for a toolchain that isn't available here (no `go` on this machine); every added sentence
traces to a fact in facts.json, each backed by a direct source read and a real test-file line
count, not inference.
