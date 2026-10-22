# Lane L real-pipeline run: aspose-page-foss/Aspose.Page-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-page-foss/Aspose.Page-FOSS-for-Python python <clone-dir>
```

No crash, no manual intervention. Real printed output below.

**Tree / README:** 2431 files cloned (by far the largest tree of the 7); live
README fetched via `gh api`, 590 lines.

**Facts:** 595 facts built. 8 example receipts: 7 `EXECUTED`, 1 `FAILED`. One fact
`CONTRADICTED`: `example:008`.

**Correction engine:** 0 edits applied.

**Findings (report-only), verbatim as printed, 4 total:**

- `[failing_example]` line 265: example on lines 265-270 — "example 8: FAILED;
  ImportError; ran against the repository source tree; the package would not
  build". Snippet (from `facts.json`, `example:008`):
  ```python
  from aspose.page.mcp import create_server

  server = create_server()
  server.run(host="127.0.0.1", port=8000)
  ```
- `[format_overclaim]` line 56: 'JPEG' marked supported, no confirming SUPPORTED fact.
- `[format_overclaim]` line 56: 'BMP' marked supported, no confirming SUPPORTED fact
  (same line, different format token).
- `[format_overclaim]` line 56: 'TIFF' marked supported, no confirming SUPPORTED fact
  (same line, third format token).

**Full fact record:** `facts.json` in this directory, copied verbatim from
`scripts/_lane_l_output/aspose-page-foss__Aspose.Page-FOSS-for-Python/facts.json`.

**Scope note:** this is Lane L only (facts + report-only findings). No PR/issue was
filed from this run.
