# P2_REAL_ENGINE_SALVAGE run: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript typescript <clone-dir>
```

No crash, no workaround needed. Ran clean on the first attempt.

## Real counts printed by the script

- 190 files in the cloned tree; live README fetched via `gh api`, 444 lines.
- **1045 facts** built.
- **4 example receipts**: all 4 `NOT_VERIFIED`.
- Real reason, read from `facts.json`'s `example:001` evidence: `BLOCKED_TOOLCHAIN:
  tsc did not report a version`. This matches `run_lane_l.py`'s own stated gap
  (header docstring): TypeScript's execution-backed example verifier has not been
  individually ported/proven through this script as of 2026-10-22 — an honest
  stub result, not fabricated as EXECUTED.
- CONTRADICTED facts: `install_command:npm`.
- **0 edits applied** by the correction engine.

## Findings printed (8 total, verbatim outcomes)

7 `format_overclaim` findings: line 34 (`OBJ`), line 34 (`STL`), line 35 (`FBX`),
line 36 (`3MF`), line 56 (`STL`), line 57 (`FBX`), line 58 (`3MF`) — README marks
each supported but no SUPPORTED format/capability fact confirms it.

1 `report_gaps` finding: 28 of 81 verified public types named nowhere in the
README (e.g. `public_symbol:inamedobject`, `public_symbol:bindpoint`, truncated
by the script's own 150-character print slice).

## Honest scope note

No example-execution verdict is available for this repository in this run — the
TypeScript verifier is still a toolchain-blocked stub, per the script's own
documented gap, not a claim this proof makes false. `facts.json` in this
directory is the exact file the script wrote.
