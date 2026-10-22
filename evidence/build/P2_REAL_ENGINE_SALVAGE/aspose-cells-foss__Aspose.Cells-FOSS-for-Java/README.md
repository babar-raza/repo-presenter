# P2_REAL_ENGINE_SALVAGE run — aspose-cells-foss/Aspose.Cells-FOSS-for-Java (java)

2026-10-22. Mechanical, read-only run of the existing Lane L pipeline against a fresh
shallow clone. No pipeline code touched.

Command:

```
git clone --depth 1 https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java.git <clone>
python scripts/run_lane_l.py aspose-cells-foss/Aspose.Cells-FOSS-for-Java java <clone>
```

## Real script output

```
[1/5] cloning aspose-cells-foss/Aspose.Cells-FOSS-for-Java (java) -> <clone>
      364 files in tree
[2/5] fetching live README
      537 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      2731 facts, 3 example receipts
      example outcomes: {'NOT_VERIFIED': 3}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
      (none)
```

## Summary

- Facts: 2731
- Example receipts: 3, all `NOT_VERIFIED` (java's execution-backed example verifier is not
  yet individually proven through this script, per the script's own docstring — this is the
  honest gap the script reports, not a crash or a skip).
- CONTRADICTED facts: none.
- Edits applied by the correction engine: 0.
- Findings: **none** — a clean result. The script printed `(none)` for the findings step;
  this is reported as-is, not treated as a failure.

No findings fired for this repository in this run. `facts.json` copied to this directory
unmodified from `scripts/_lane_l_output/aspose-cells-foss__Aspose.Cells-FOSS-for-Java/facts.json`.
