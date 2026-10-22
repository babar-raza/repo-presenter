# Lane L real-pipeline run: aspose-font-foss/Aspose.Font-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-font-foss/Aspose.Font-FOSS-for-Python python <clone-dir>
```

No crash, no manual intervention. Real printed output below.

**Tree / README:** 512 files cloned (largest clone of the 7); live README fetched
via `gh api`, 559 lines.

**Facts:** 859 facts built. 5 example receipts: 3 `EXECUTED`, 2 `FAILED`. Two facts
`CONTRADICTED`: `example:003`, `example:005`.

**Correction engine:** 0 edits applied.

**Findings (report-only), verbatim as printed, 3 total:**

- `[failing_example]` line 128: example on lines 128-141 — "example 3: FAILED;
  TypeError". Snippet (from `facts.json`, `example:003`):
  ```python
  from aspose_font import FontLoader, VariableInstanceBuilder

  font = FontLoader.open("Roboto-VariableFont_wdth,wght.ttf")
  package = VariableInstanceBuilder.build_package(
      font,
      instance_names=["Bold"],
      naming_strategy="ribbi-safe",
      family_suffix="Beta",
      stat_policy="static",
      preview_text="Review",
      output_dir="var-package-output",
  )
  ```
  Input was staged as `Roboto-VariableFont_wdth,wght.ttf` from the repo's own
  test fixtures.
- `[failing_example]` line 295: example on lines 295-418 — "example 5: FAILED;
  KeyError". Snippet begins (from `facts.json`, `example:005`):
  ```python
  from aspose_font import FontLoader, FontPreviewBuilder, FontQaReporter, WebFontOptimizer
  from aspose_font import FontCleaner
  from aspose_font.subsetter import FontSubsetter

  font = FontLoader.open("Roboto-VariableFont_wdth,wght.ttf")

  subset_result = FontSubsetter.subset_for_web_with_coverage(
      font,
      presets=("latin", "arabic"),
      text="Aspose مرحبا",
  )
  ...
  ```
  (truncated in `facts.json`'s own stored value at ~1500 chars for this report;
  full text is in `facts.json` in this directory). Inputs were staged from three
  repo test fixtures: a PNG template, an SVG, and the variable-font TTF.
- `[report_gaps]` line 0: 166 of 179 verified public types are named nowhere in
  the README (e.g. `public_symbol:aspose_font.activetuplesummary`, among others).

**Full fact record:** `facts.json` in this directory, copied verbatim from
`scripts/_lane_l_output/aspose-font-foss__Aspose.Font-FOSS-for-Python/facts.json`.

**Scope note:** this is Lane L only (facts + report-only findings). No PR/issue was
filed from this run.
