# P2_REAL_ENGINE_SALVAGE run — aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET (net)

2026-10-22. Mechanical, read-only run of the existing Lane L pipeline against a fresh
shallow clone. No pipeline code touched.

Command:

```
git clone --depth 1 https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET.git <clone>
python scripts/run_lane_l.py "aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET" net <clone>
```

## Real script output

```
[1/5] cloning aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET (net) -> <clone>
      2619 files in tree
[2/5] fetching live README
      1889 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      13348 facts, 12 example receipts
      example outcomes: {'NOT_VERIFIED': 12}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
      - [report_gaps] line 0: 2 of 969 verified public types are named nowhere in the README; would fill API Reference: public_symbol:aspose.pdf.converters.pstopdf.pstintspace, pub...
```

## Summary

- Facts: 13348 (the largest fact count of the 8 repositories in this batch).
- Example receipts: 12, all `NOT_VERIFIED` (net's execution-backed example verifier is not
  yet individually proven through this script, per the script's own docstring).
- CONTRADICTED facts: none.
- Edits applied by the correction engine: 0.
- Findings: 1 — `report_gaps`: only 2 of 969 verified public types are named nowhere in the
  README (a very low under-claim rate relative to the other repositories in this batch).

`facts.json` copied unmodified from
`scripts/_lane_l_output/aspose-pdf-foss__Aspose.PDF-FOSS-for-.NET/facts.json`.
