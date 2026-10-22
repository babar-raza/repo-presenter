# P2_REAL_ENGINE_SALVAGE run — aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp (cpp)

2026-10-22. Mechanical, read-only run of the existing Lane L pipeline against a fresh
shallow clone. No pipeline code touched. This ecosystem runs a real compiler to verify
README code examples.

Command:

```
git clone --depth 1 https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp.git <clone>
python scripts/run_lane_l.py "aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp" cpp <clone>
```

## Real script output

```
[1/5] cloning aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp (cpp) -> <clone>
      533 files in tree
[2/5] fetching live README
      884 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      2888 facts, 9 example receipts
      example outcomes: {'FAILED': 6, 'NOT_VERIFIED': 1, 'EXECUTED': 2}
      CONTRADICTED facts: ['example:001', 'example:003', 'example:004', 'example:005', 'example:006', 'example:007']
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
      - [failing_example] line 241: the example verifier recorded a failure for the example on lines 241-261: example 1: FAILED; example_001.cpp:14:19: error: invalid use of incomplete t...
      - [failing_example] line 284: the example verifier recorded a failure for the example on lines 284-305: example 3: FAILED; example_003.cpp:15:35: error: invalid use of incomplete t...
      - [failing_example] line 315: the example verifier recorded a failure for the example on lines 315-334: example 4: FAILED; example_004.cpp:15:35: error: invalid use of incomplete t...
      - [failing_example] line 341: the example verifier recorded a failure for the example on lines 341-360: example 5: FAILED; example_005.cpp:13:18: error: invalid use of incomplete t...
      - [failing_example] line 367: the example verifier recorded a failure for the example on lines 367-387: example 6: FAILED; example_006.cpp:13:35: error: invalid use of incomplete t...
      - [failing_example] line 393: the example verifier recorded a failure for the example on lines 393-406: example 7: FAILED; example_007.cpp:12:35: error: invalid use of incomplete t...
      - [report_gaps] line 0: 97 of 234 verified public types are named nowhere in the README; would fill API Reference: public_symbol:aspose.slides.foss.ibaseportionformat, public...
      - [report_gaps] line 0: 7 verified format(s) named nowhere in the README; would fill At a Glance or Key Capabilities: format:output.fodp, format:output.gif, format:output.htm...
```

(Finding reason text is truncated to 150 characters by the script itself; `...` marks that
script-side truncation.)

## Summary

- Facts: 2888
- Example receipts: 9 — `FAILED`: 6, `NOT_VERIFIED`: 1, `EXECUTED`: 2. This is the worst
  example-verification outcome of the 8 repositories in this batch: 6 of 9 README code
  examples failed to compile.
- CONTRADICTED facts: `example:001`, `example:003`, `example:004`, `example:005`,
  `example:006`, `example:007` (6 facts) — matching the 6 compiler-caught `FAILED`
  examples. All six failures share the same compiler diagnostic shape ("invalid use of
  incomplete type") at different lines in `example_001.cpp` through `example_007.cpp`.
- Edits applied by the correction engine: 0.
- Findings: 8 total — 6 `failing_example` (the same six compile failures above) and 2
  `report_gaps` (97 of 234 verified public types named nowhere in the README; 7 verified
  formats named nowhere in the README, e.g. `format:output.fodp`, `format:output.gif`,
  `format:output.htm...`).

`facts.json` copied unmodified from
`scripts/_lane_l_output/aspose-slides-foss__Aspose.Slides-FOSS-for-Cpp/facts.json`.
