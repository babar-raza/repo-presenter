# P2_REAL_ENGINE_SALVAGE run: aspose-psd-foss/Aspose.PSD-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-psd-foss/Aspose.PSD-FOSS-for-Python python <clone-dir>
```

No crash, no workaround needed. Ran clean on the first attempt.

## Real counts printed by the script

- 105 files in the cloned tree; live README fetched via `gh api`, 252 lines.
- **564 facts** built.
- **5 example receipts**: `EXECUTED` 1, `FAILED` 4.
- CONTRADICTED facts: `example:001`, `example:003`, `example:004`, `example:005`.
- **1 edit applied** by the correction engine: `STRUCTURE_FIX` at character offsets
  9217-9222, rationale (as printed, truncated by the script's own slice): "line 219
  is a closing code fence that closes nothing; it turns the lines after it into a
  code block".

## Findings printed (5 total, verbatim outcomes)

4 `failing_example` findings — examples 1, 3, 4, 5 (lines 89-103, 119-126, 130-138,
142-162) — each `FAILED`, with real exception classes `IndexError` (×2),
`AttributeError`, `NameError`. Each finding's evidence notes the example "ran against
the repository source tree" (per `facts.json`'s `example:001` evidence: "the
pa[ckage would not build]" — the verifier fell back to running against the cloned
source tree rather than an installed package). Two PSD test fixtures were staged for
verification: `src/aspose_psd_foss_test/testdata/basic-indexed.psd`, staged once as
`example.psd` and once as `modified.psd`.

1 `report_gaps` finding: 33 of 77 verified public types named nowhere in the README
(e.g. `public_symbol:aspose_psd_foss.colormodes`, truncated by the script's own
150-character print slice).

## Not a clean result

A real structural defect (dangling closing fence) was found and fixed by the
correction engine — this is the only one of the 7 runs in this pass where the
engine applied an edit. 4 of 5 README examples fail against the real package.
`facts.json` in this directory is the exact file the script wrote.
