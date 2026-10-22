# P2_REAL_ENGINE_SALVAGE run: aspose-tex-foss/Aspose.TeX-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-tex-foss/Aspose.TeX-FOSS-for-Python python <clone-dir>
```

No crash, no workaround needed. Ran clean on the first attempt.

## Real counts printed by the script

- 314 files in the cloned tree; live README fetched via `gh api`, 368 lines.
- **45 facts** built — markedly fewer than the other four Python repositories in
  this pass (564-3209 facts each); reported as observed, not investigated further
  (in scope for this pass: run the pipeline and report what it printed, not
  diagnose why one repository's manifest/surface facts are thin).
- **10 example receipts**: `EXECUTED` 1, `FAILED` 9.
- CONTRADICTED facts: `install_command:pip` plus `example:001` through
  `example:009`.
- **0 edits applied** by the correction engine.

## Findings printed (13 total, verbatim outcomes)

9 `failing_example` findings — examples 1-9 (lines 110-220) — every one `FAILED`
with the real captured exception class `IndentationError`.

1 additional finding at line 0 (as printed, truncated by the script's own slice):
"9 examples fail with a syntax or indentation error: the library source itself may
not parse (an upstream defect for an issue to the maintainers, not a[...]".

3 `format_overclaim` findings: line 44 (`PDF`), line 45 (`DVI`), line 46 (`SVG`) —
README marks each supported but no SUPPORTED format/capability fact confirms it.

## Not a clean result

All 9 of the fenced examples that ran (beyond the one `EXECUTED`) failed with the
same `IndentationError` class — a real, consistent, machine-verified signal,
reported as the script printed it. `facts.json` in this directory is the exact
file the script wrote.
