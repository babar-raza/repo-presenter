# Lane L real-pipeline run: aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python python <clone-dir>
```

No crash, no manual intervention. Real printed output below.

**Tree / README:** 136 files cloned; live README fetched via `gh api`, 262 lines.

**Facts:** 85 facts built. 6 example receipts, all outcome `EXECUTED` (no `FAILED`,
no `NEEDS_INPUT`). One fact came back `CONTRADICTED`: `install_command:pip` — the
README's `pip install aspose-barcode-foss` command, contradicted because
`https://pypi.org/pypi/aspose-barcode-foss/json` returns "distribution not found".

**Correction engine:** 0 edits applied.

**Findings (report-only), verbatim as printed (text cut at the script's own
150-char cap), 2 total — both `format_overclaim`:**

- line 43: "the README marks 'SVG' supported, but no SUPPORTED format or
  capability fact confirms it is actually wired up; a human reviewer should
  check whether i[...]"
- line 44: same text, for 'PNG'.

No `failing_example` finding fired for this repository — all 6 README examples
actually ran and passed against the real installed package.

**Full fact record:** `facts.json` in this directory, copied verbatim from
`scripts/_lane_l_output/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python/facts.json`.

**Scope note:** this is Lane L only (facts + report-only findings). No PR/issue was
filed from this run.
