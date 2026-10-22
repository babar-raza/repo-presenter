# P2_REAL_ENGINE_SALVAGE run — aspose-pdf-foss/Aspose.PDF-FOSS-for-Java (java)

2026-10-22. Mechanical, read-only run of the existing Lane L pipeline against a fresh
shallow clone. No pipeline code touched.

Command:

```
git clone --depth 1 https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Java.git <clone>
python scripts/run_lane_l.py "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java" java <clone>
```

## Real script output

```
[1/5] cloning aspose-pdf-foss/Aspose.PDF-FOSS-for-Java (java) -> <clone>
      1281 files in tree
[2/5] fetching live README
      1675 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      24690 facts, 9 example receipts
      example outcomes: {'NOT_VERIFIED': 9}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
      - [format_overclaim] line 32: the README marks 'PDF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 33: the README marks 'HTML' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 34: the README marks 'TIFF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 58: the README marks 'PDF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 59: the README marks 'HTML' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 60: the README marks 'BMP' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 61: the README marks 'GIF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 62: the README marks 'JPEG' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 63: the README marks 'TIFF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [report_gaps] line 0: 137 of 1181 verified public types are named nowhere in the README; would fill API Reference: public_symbol:org.aspose.pdf.loadformat, public_symbol:or...
```

(Finding reason text is truncated to 150 characters by the script itself; `...` marks that
script-side truncation.)

## Summary

- Facts: 24690 — the largest fact count of the 8 repositories in this batch, by a wide
  margin.
- Example receipts: 9, all `NOT_VERIFIED` (java's execution-backed example verifier is not
  yet individually proven through this script, per the script's own docstring).
- CONTRADICTED facts: none.
- Edits applied by the correction engine: 0.
- Findings: 10 total — 9 `format_overclaim` (PDF x2, HTML x2, TIFF x2, BMP, GIF, JPEG) and 1
  `report_gaps` (137 of 1181 verified public types named nowhere in the README — the largest
  absolute under-claim gap in this batch, though against the largest surface by far).

`facts.json` copied unmodified from
`scripts/_lane_l_output/aspose-pdf-foss__Aspose.PDF-FOSS-for-Java/facts.json`.
