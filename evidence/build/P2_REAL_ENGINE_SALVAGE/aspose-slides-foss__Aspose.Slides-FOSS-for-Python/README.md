# P2_REAL_ENGINE_SALVAGE run: aspose-slides-foss/Aspose.Slides-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-slides-foss/Aspose.Slides-FOSS-for-Python python <clone-dir>
```

No crash, no workaround needed. Ran clean on the first attempt.

## Real counts printed by the script

- 654 files in the cloned tree; live README fetched via `gh api`, 1013 lines.
- **3209 facts** built.
- **15 example receipts**: `EXECUTED` 14, `FAILED` 1.
- CONTRADICTED facts: `example:015` only.
- **0 edits applied** by the correction engine.

## Findings printed (2 total, verbatim outcomes)

1 `failing_example` finding: example 15 (lines 413-433), `FAILED`, real captured
`ValueError`.

1 `report_gaps` finding: 245 of 516 verified public types named nowhere in the
README (e.g. `public_symbol:slides_foss.iadjustvalue`, truncated by the script's
own 150-character print slice).

## Mostly clean

14 of 15 README examples execute correctly against the real installed package;
one real failure found. No format-overclaim finding fired for this repository in
this run. `facts.json` in this directory is the exact file the script wrote.
