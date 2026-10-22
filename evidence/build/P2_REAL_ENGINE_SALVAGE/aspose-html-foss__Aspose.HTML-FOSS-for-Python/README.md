# Lane L real-pipeline run: aspose-html-foss/Aspose.HTML-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-html-foss/Aspose.HTML-FOSS-for-Python python <clone-dir>
```

No crash, no manual intervention. Real printed output below.

**Tree / README:** 336 files cloned; live README fetched via `gh api`, 610 lines.

**Facts:** 364 facts built. 7 example receipts: 6 `EXECUTED`, 1 `FAILED`. Two facts
`CONTRADICTED`: `install_command:pip`, `example:006`.

**Correction engine:** 0 edits applied.

**Findings (report-only), verbatim as printed, 4 total:**

- `[failing_example]` line 186: example on lines 186-197 — "example 6: FAILED;
  ImportError; ran against the repository source tree; the package would not
  build; retried after installing declared extra providing 'quickjs'
  (quickjs>=1.19,<2)". Snippet (from `facts.json`, `example:006`):
  ```python
  from aspose_html.dom import Document
  from aspose_html.js import JSContext

  document = Document()
  element = document.create_element("div")
  document.append_child(element)

  with JSContext(document) as ctx:
      result = ctx.evaluate("1 + 1")
      print(result)  # 2
  ```
  The verifier's own evidence shows it tried to recover by installing the
  `quickjs` extra and the example still failed with `ImportError`.
- `install_command:pip` is `CONTRADICTED`: README says `pip install
  aspose-html-foss`; PyPI registry lookup for `aspose-html-foss` returns
  "distribution not found".
- `[format_overclaim]` line 29: 'HTML' marked supported, no confirming SUPPORTED fact.
- `[format_overclaim]` line 30: 'CSS' marked supported, no confirming SUPPORTED fact.
- `[format_overclaim]` line 51: 'HTML' marked supported, no confirming SUPPORTED fact
  (second occurrence, different line).

(Note on counting: the script's `[5/5] findings` section printed exactly 4
lines — 1 `failing_example` + 3 `format_overclaim`. `install_command:pip` is a
separate `CONTRADICTED` fact from step `[3/5]`'s own "CONTRADICTED facts" line,
not a printed Finding; it is included above for completeness since it is a
real contradiction the run surfaced.)

**Full fact record:** `facts.json` in this directory, copied verbatim from
`scripts/_lane_l_output/aspose-html-foss__Aspose.HTML-FOSS-for-Python/facts.json`.

**Scope note:** this is Lane L only (facts + report-only findings). No PR/issue was
filed from this run.
