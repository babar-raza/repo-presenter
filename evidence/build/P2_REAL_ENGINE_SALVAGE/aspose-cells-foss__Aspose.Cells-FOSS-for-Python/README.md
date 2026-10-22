# Lane L real-pipeline run: aspose-cells-foss/Aspose.Cells-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-cells-foss/Aspose.Cells-FOSS-for-Python python <clone-dir>
```

No crash, no manual intervention. Real printed output below.

**Tree / README:** 113 files cloned; live README fetched via `gh api`, 183 lines.

**Facts:** 1129 facts built (by far the largest of the 7 — this ecosystem's surface is
large: 160 verified public types). 6 example receipts: 5 `EXECUTED`, 1 `FAILED`.
One fact `CONTRADICTED`: `example:005`.

**Correction engine:** 0 edits applied.

**Findings (report-only), verbatim as printed, 7 total:**

- `[failing_example]` line 112: example on lines 112-120 — "example 5: FAILED;
  RuntimeError". The failing snippet (from `facts.json`, `example:005`):
  ```python
  from aspose.cells_foss import Workbook

  workbook = Workbook("report.xlsx")
  workbook.save("report.csv")
  workbook.save("report.json")
  workbook.save("report.md")
  workbook.save("report.pdf")  # Requires skia-python
  ```
  Receipt evidence notes the input was staged as `report.xlsx` from example 1's
  own output, and the failure is a real `RuntimeError` (the script's own output
  does not print the full traceback past the outcome tag; see `receipts.json`
  reference inside `facts.json` for the exact evidence trail captured).
- `[format_overclaim]` line 141: 'CSV' marked supported, no confirming SUPPORTED fact.
- `[format_overclaim]` line 142: 'TSV' marked supported, no confirming SUPPORTED fact.
- `[format_overclaim]` line 143: 'JSON' marked supported, no confirming SUPPORTED fact.
- `[format_overclaim]` line 144: 'Markdown' marked supported, no confirming SUPPORTED fact.
- `[format_overclaim]` line 145: 'PDF' marked supported, no confirming SUPPORTED fact.
- `[report_gaps]` line 0: 157 of 160 verified public types are named nowhere in the
  README (e.g. `public_symbol:aspose.cells_foss.agileencryptionparameters`, among others).

**Full fact record:** `facts.json` in this directory, copied verbatim from
`scripts/_lane_l_output/aspose-cells-foss__Aspose.Cells-FOSS-for-Python/facts.json`.

**Scope note:** this is Lane L only (facts + report-only findings). No PR/issue was
filed from this run.
