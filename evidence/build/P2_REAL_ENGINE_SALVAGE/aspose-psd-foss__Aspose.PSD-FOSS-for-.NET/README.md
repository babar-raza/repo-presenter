# Lane L run — Aspose.PSD-FOSS-for-.NET

2026-10-22.

```
python scripts/run_lane_l.py aspose-psd-foss/Aspose.PSD-FOSS-for-.NET net <clone>
```

Repository shallow-cloned (`git clone --depth 1`) into a scratch directory, then the
command above run from the repo-presenter root exactly as printed. No source files under
`src/`, `tests/`, `project/state.yaml`, or `migration/reuse-manifest.yaml` were touched.

## Real output

```
[1/5] cloning aspose-psd-foss/Aspose.PSD-FOSS-for-.NET (net) -> <clone>
      117 files in tree
[2/5] fetching live README
      193 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      199 facts, 1 example receipts
      example outcomes: {'NOT_VERIFIED': 1}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
```

**Facts: 199.** **Example receipts: 1, `NOT_VERIFIED`** (only one fenced code example in
`net`'s fence vocabulary was found in the live README; net's execution-backed verifier is
not yet ported in any case). No `CONTRADICTED` facts. 0 correction-engine edits
auto-applied.

**Findings (5, report-only):**

- `enterprise_edition_naming` line 5: names the aspose.com product with a substitute for
  its proper name ("commercial Aspose.PSD product"); fix not applied — no
  `link_target:product...` fact available to anchor it.
- `enterprise_edition_naming` line 21: same pattern ("the commercial Aspose.PSD").
- `enterprise_edition_naming` line 112: same pattern ("Commercial Aspose.PSD").
- `enterprise_edition_naming` line 116: same pattern ("the commercial Aspose.PSD
  product").
- `report_gaps` line 0: 20 of 26 verified public types named nowhere in the README (would
  fill API Reference — e.g. `public_symbol:aspose.psd.imageloader`, and others; the
  script's own printed list is truncated at 150 chars).

No pipeline crash, no clone failure. `facts.json` copied verbatim into this directory.
