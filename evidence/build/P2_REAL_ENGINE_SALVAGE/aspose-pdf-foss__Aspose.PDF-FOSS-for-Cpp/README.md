# P2_REAL_ENGINE_SALVAGE run — aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp (cpp)

2026-10-22. Mechanical, read-only run of the existing Lane L pipeline against a fresh
shallow clone. No pipeline code touched. This ecosystem runs a real compiler to verify
README code examples.

Command:

```
git clone --depth 1 https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp.git <clone>
python scripts/run_lane_l.py "aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp" cpp <clone>
```

## Real script output

```
[1/5] cloning aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp (cpp) -> <clone>
      1536 files in tree
[2/5] fetching live README
      935 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      1690 facts, 12 example receipts
      example outcomes: {'EXECUTED': 5, 'FAILED': 2, 'NOT_VERIFIED': 5}
      CONTRADICTED facts: ['example:003', 'example:006']
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
      - [enterprise_edition_naming] line 13: names the aspose.com product with a substitute for its proper name ('the commercial Aspose.PDF for .NET'); the fix is not applied because no link_targ...
      - [enterprise_edition_naming] line 882: names the aspose.com product with a substitute for its proper name ('the commercial Aspose.PDF'); the fix is not applied because no link_target:produc...
      - [failing_example] line 252: the example verifier recorded a failure for the example on lines 252-299: example 3: FAILED; example_003.cpp:36:20: error: invalid use of incomplete t...
      - [failing_example] line 359: the example verifier recorded a failure for the example on lines 359-378: example 6: FAILED; example_006.cpp:15:52: error: invalid use of incomplete t...
      - [format_overclaim] line 39: the README marks 'PDF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 64: the README marks 'PDF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 65: the README marks 'PNG' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 65: the README marks 'JPEG' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 65: the README marks 'BMP' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 65: the README marks 'TIFF' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [report_gaps] line 0: 3 of 249 verified public types are named nowhere in the README; would fill API Reference: public_symbol:aspose.pdf.annotations.iappointment, public_sy...
```

(Finding reason text is truncated to 150 characters by the script itself; `...` marks that
script-side truncation.)

## Summary

- Facts: 1690
- Example receipts: 12 — `EXECUTED`: 5, `FAILED`: 2, `NOT_VERIFIED`: 5.
- CONTRADICTED facts: `example:003`, `example:006` — these are the same two examples the
  compiler-backed verifier reported as `FAILED` (compile errors: "invalid use of incomplete
  type" at `example_003.cpp:36:20` and `example_006.cpp:15:52`). Two real, independently
  compiler-caught broken examples in the live README, not static guesses.
- Edits applied by the correction engine: 0.
- Findings: 11 total — 2 `enterprise_edition_naming`, 2 `failing_example` (the same two
  compile failures above), 5 `format_overclaim` (PDF x2, PNG, JPEG, BMP, TIFF), 1
  `report_gaps` (3 of 249 verified public types named nowhere in the README).

`facts.json` copied unmodified from
`scripts/_lane_l_output/aspose-pdf-foss__Aspose.PDF-FOSS-for-Cpp/facts.json`.
