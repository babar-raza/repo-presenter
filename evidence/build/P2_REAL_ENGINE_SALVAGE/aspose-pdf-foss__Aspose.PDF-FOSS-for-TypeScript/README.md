# P2_REAL_ENGINE_SALVAGE run: aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript typescript <clone-dir>
```

No crash, no workaround needed. Ran clean on the first attempt (the clone itself
was by far the largest of the 7: 3275 files).

## Real counts printed by the script

- 3275 files in the cloned tree; live README fetched via `gh api`, 4663 lines.
- **3148 facts** built.
- **118 example receipts**: all 118 `NOT_VERIFIED`.
- Real reason, read from `facts.json`'s `example:001` evidence: `BLOCKED_TOOLCHAIN:
  tsc did not report a version` — the same toolchain-stub reason as the other
  TypeScript repository in this pass, matching `run_lane_l.py`'s own documented
  gap (TypeScript's execution-backed example verifier not yet individually
  proven through this script as of 2026-10-22).
- CONTRADICTED facts: `install_command:npm`.
- **0 edits applied** by the correction engine.

## Findings printed (13 total, verbatim outcomes)

13 `format_overclaim` findings, all for formats the README marks supported with
no SUPPORTED format/capability fact confirming it: line 35 (`PDF`), line 36
(`HTML`), line 37 (`GFM`), line 60 (`PDF`), line 61 (`SVG`), line 61 (`PNG`),
line 61 (`JPEG`), line 61 (`TIFF`), line 61 (`BMP`), line 61 (`GIF`), line 62
(`HTML`), line 62 (`DOCX`), line 62 (`EPUB`).

No `report_gaps` finding fired in this run (the script's findings list ended at
the 13th `format_overclaim` line above — reported as observed, not because a
gap doesn't exist, but because the detector did not report one this run).

## Honest scope note

No example-execution verdict is available for this repository in this run, same
toolchain-stub reason as the other TypeScript repository — an honest gap, not a
false claim. The 13 format-overclaim findings are real and machine-produced.
`facts.json` in this directory is the exact file the script wrote.
