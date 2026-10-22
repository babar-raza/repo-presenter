# P2_REAL_ENGINE_SALVAGE run — aspose-email-foss/Aspose.Email-FOSS-for-Cpp (cpp)

2026-10-22. Mechanical, read-only run of the existing Lane L pipeline against a fresh
shallow clone. No pipeline code touched. This ecosystem runs a real compiler to verify
README code examples.

Command:

```
git clone --depth 1 https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-Cpp.git <clone>
python scripts/run_lane_l.py "aspose-email-foss/Aspose.Email-FOSS-for-Cpp" cpp <clone>
```

## Real script output

```
[1/5] cloning aspose-email-foss/Aspose.Email-FOSS-for-Cpp (cpp) -> <clone>
      75 files in tree
[2/5] fetching live README
      475 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      237 facts, 4 example receipts
      example outcomes: {'EXECUTED': 2, 'FAILED': 2}
      CONTRADICTED facts: ['example:003', 'example:004']
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
      - [enterprise_edition_naming] line 450: possible Enterprise Edition naming violation ('commercial product'); the product name and its platform are not both spelled out on this line, so the f...
      - [failing_example] line 178: the example verifier recorded a failure for the example on lines 178-233: example 3: FAILED; example_003.cpp:3:27: error: 'read_option' was not declar...
      - [failing_example] line 245: the example verifier recorded a failure for the example on lines 245-273: example 4: FAILED; example_004.cpp:5:14: error: 'cerr' is not a member of 's...
      - [format_overclaim] line 34: the README marks 'MSG' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 35: the README marks 'EML' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 35: the README marks 'RFC' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 35: the README marks 'MIME' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 36: the README marks 'CFB' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 49: the README marks 'MSG' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 50: the README marks 'EML' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 50: the README marks 'RFC' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 50: the README marks 'MIME' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 51: the README marks 'CFB' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
```

(Finding reason text is truncated to 150 characters by the script itself; `...` marks that
script-side truncation. All 13 findings fit before truncation by the script's own print loop
— nothing omitted by this report.)

## Summary

- Facts: 237 — the smallest fact count of the 8 repositories in this batch (also the
  smallest clone, 75 files).
- Example receipts: 4 — `EXECUTED`: 2, `FAILED`: 2.
- CONTRADICTED facts: `example:003`, `example:004` — the same two examples the
  compiler-backed verifier reported as `FAILED` (real compile errors: `'read_option' was not
  declared` at `example_003.cpp:3:27`, and `'cerr' is not a member of 'std'` at
  `example_004.cpp:5:14` — both genuinely broken examples in the live README, caught by
  actually compiling, not guessed).
- Edits applied by the correction engine: 0.
- Findings: 13 total — 1 `enterprise_edition_naming`, 2 `failing_example` (the same two
  compile failures above), 10 `format_overclaim` (MSG x2, EML x2, RFC x2, MIME x2, CFB x2).

`facts.json` copied unmodified from
`scripts/_lane_l_output/aspose-email-foss__Aspose.Email-FOSS-for-Cpp/facts.json`.
