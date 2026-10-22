# Lane L run — Aspose.Cells-FOSS-for-.NET

2026-10-22.

```
python scripts/run_lane_l.py aspose-cells-foss/Aspose.Cells-FOSS-for-.NET net <clone>
```

Repository shallow-cloned (`git clone --depth 1`) into a scratch directory, then the
command above run from the repo-presenter root exactly as printed. No source files under
`src/`, `tests/`, `project/state.yaml`, or `migration/reuse-manifest.yaml` were touched.

## Real output

```
[1/5] cloning aspose-cells-foss/Aspose.Cells-FOSS-for-.NET (net) -> <clone>
      454 files in tree
[2/5] fetching live README
      535 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      657 facts, 9 example receipts
      example outcomes: {'NOT_VERIFIED': 9}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
```

**Facts: 657.** **Example receipts: 9, all `NOT_VERIFIED`** (net's execution-backed example
verifier is not yet ported, so this is the honest stub outcome, not a verified pass). No
`CONTRADICTED` facts. 0 correction-engine edits auto-applied.

**Findings (6, report-only):**

- `enterprise_edition_naming` line 488: possible Enterprise Edition naming violation
  ("commercial product"); not auto-fixed because the product name and platform are not
  both spelled out on that line.
- `format_overclaim` line 28: README marks `XLSX` supported, no SUPPORTED format/capability
  fact confirms it is wired up.
- `format_overclaim` line 49: README marks `XLSX` supported, same gap.
- `format_overclaim` line 50: README marks `PDF` supported, same gap.
- `report_gaps` line 0: 1 of 98 verified public types named nowhere in the README
  (`public_symbol:aspose.cells_foss.fontsetting`).
- `report_gaps` line 7: README says "pure managed", but facts list 1 required dependency
  (`dependency:skiasharp`).

No pipeline crash, no clone failure. `facts.json` copied verbatim into this directory.
