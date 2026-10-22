# Lane L run — Aspose.Slides-FOSS-for-.NET

2026-10-22 (updated — supersedes this directory's first version, which honestly reported a
real false-positive class the second run below closes).

```
python scripts/run_lane_l.py aspose-slides-foss/Aspose.Slides-FOSS-for-.NET net <clone>
```

Repository shallow-cloned (`git clone --depth 1`) into a scratch directory, then the
command above run from the repo-presenter root exactly as printed. No source files under
`src/`, `tests/`, `project/state.yaml`, or `migration/reuse-manifest.yaml` were touched.

## Real output

```
[1/5] cloning aspose-slides-foss/Aspose.Slides-FOSS-for-.NET (net) -> <clone>
      464 files in tree
[2/5] fetching live README
      545 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      2602 facts, 9 example receipts
      example outcomes: {'NOT_VERIFIED': 9}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
```

**Facts: 2602.** **Example receipts: 9, all `NOT_VERIFIED`** (net's execution-backed
example verifier is not yet ported). No `CONTRADICTED` facts. 0 correction-engine edits
auto-applied.

**Findings (8, report-only — down from 22 on the first run):**

- `enterprise_edition_naming` line 511: possible violation ("commercial product").
- `enterprise_edition_naming` line 519: possible violation ("commercial product").
- `format_overclaim` lines 25, 47 (x3): README marks `PPTX`/`PPSX`/`POTX` supported, no
  SUPPORTED format/capability fact confirms wiring.
- `report_gaps` line 0: 219 of 264 verified public types named nowhere in the README
  (would fill API Reference — e.g.
  `public_symbol:aspose.slides.foss.baseportionformat`, and others; script's own printed
  list truncated at 150 chars).

**What changed since the first run**: the first run also flagged 14 lines from this
repository's own cross-EDITION feature-comparison table ("| | .NET | Java | C++ | Python |",
rows like `'Create, open, round-trip, save'`, `'Charts'`, `'Themes'`, `'Hyperlinks'`) — a
real, measured false-positive class, since confirmed independently against
`aspose-slides-foss/Aspose.Slides-FOSS-for-Java`'s own README (the identical table, shared
across the family). `format_overclaim._table_claims()` now requires a table row's label to
look like a format/capability NAME (`_TABLE_LABEL_SHAPE`: an all-caps acronym or a dotted
extension), not merely be non-empty — a cross-edition table's plain "yes"/"no" cells still
satisfy the truthy-marker rule, but its labels (sentences, or Title-Case English words) no
longer pass the shape gate. The 4 correctly-targeted PPTX/PPSX/POTX findings (line 25/47,
from the Mermaid At a Glance diagram, not this table) are unaffected.

No pipeline crash, no clone failure. `facts.json` copied verbatim into this directory.
