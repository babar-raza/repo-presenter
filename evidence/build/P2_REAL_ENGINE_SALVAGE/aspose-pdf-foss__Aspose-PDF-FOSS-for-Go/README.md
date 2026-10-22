# P2_REAL_ENGINE_SALVAGE run — aspose-pdf-foss/Aspose-PDF-FOSS-for-Go (go)

2026-10-22. Mechanical, read-only run of the existing Lane L pipeline against a fresh
shallow clone. No pipeline code touched.

Command:

```
git clone --depth 1 https://github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Go.git <clone>
python scripts/run_lane_l.py aspose-pdf-foss/Aspose-PDF-FOSS-for-Go go <clone>
```

## Real script output

```
[1/5] cloning aspose-pdf-foss/Aspose-PDF-FOSS-for-Go (go) -> <clone>
      881 files in tree
[2/5] fetching live README
      1046 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      1790 facts, 6 example receipts
      example outcomes: {'EXECUTED': 5, 'NOT_VERIFIED': 1}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
      - [format_overclaim] line 43: the README marks 'PDF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 72: the README marks 'PDF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 73: the README marks 'PNG' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 73: the README marks 'JPEG' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 73: the README marks 'GIF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 73: the README marks 'BMP' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 73: the README marks 'TIFF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 74: the README marks 'HTML' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 75: the README marks 'SVG' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 78: the README marks 'DOCX' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 78: the README marks 'XLSX' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 78: the README marks 'EPUB' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [report_gaps] line 0: 32 of 262 verified public types are named nowhere in the README; would fill API Reference: public_symbol:barcodesymbology, public_symbol:missingglyphp...
```

(Each finding line is printed by the script itself truncated to 150 characters —
`finding.reason[:150]` in `run_lane_l.py` — reproduced here exactly as printed, with `...`
marking that script-side truncation, not mine.)

## Summary

- Facts: 1790
- Example receipts: 6 — `EXECUTED`: 5, `NOT_VERIFIED`: 1.
- CONTRADICTED facts: none.
- Edits applied by the correction engine: 0.
- Findings: 13 total — 12 `format_overclaim` (the README's "At a Glance" table claims PDF,
  PNG, JPEG, GIF, BMP, TIFF, HTML, SVG, DOCX, XLSX, EPUB support that no SUPPORTED fact
  corroborates) and 1 `report_gaps` (32 of 262 verified public types named nowhere in the
  README).

`facts.json` copied unmodified from
`scripts/_lane_l_output/aspose-pdf-foss__Aspose-PDF-FOSS-for-Go/facts.json`.
