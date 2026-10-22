# P2_REAL_ENGINE_SALVAGE run — aspose-slides-foss/Aspose.Slides-FOSS-for-Java (java)

2026-10-22 (updated — supersedes this directory's first version, which honestly reported a
real false-positive class the second run below closes). Mechanical, read-only run of the
existing Lane L pipeline against a fresh shallow clone. No pipeline code touched by this run
itself (the fix that changed the result between the two runs is recorded separately below).

Command:

```
git clone --depth 1 https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java.git <clone>
python scripts/run_lane_l.py "aspose-slides-foss/Aspose.Slides-FOSS-for-Java" java <clone>
```

## Real script output (second run, after the fix)

```
[1/5] cloning aspose-slides-foss/Aspose.Slides-FOSS-for-Java (java) -> <clone>
      447 files in tree
[2/5] fetching live README
      851 lines
[3/5] building facts (manifest + surface + registry + examples + formats)
      5078 facts, 13 example receipts
      example outcomes: {'NOT_VERIFIED': 13}
      CONTRADICTED facts: []
[4/5] running the real Lane L correction engine
      0 edits applied
[5/5] findings (report-only, no auto-edit)
      - [enterprise_edition_naming] line 710: names the aspose.com product with a substitute for its proper name ('the commercial Aspose.Slides for Java product'); the fix is not applied because n...
      - [enterprise_edition_naming] line 754: possible Enterprise Edition naming violation ('commercial product'); the product name and its platform are not both spelled out on this line, so the f...
      - [format_overclaim] line 39: the README marks 'PPTX' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
      - [format_overclaim] line 61: the README marks 'PPTX' supported, but no SUPPORTED format or capability fact confirms it is actually wired up; ...
```

## Summary

- Facts: 5078
- Example receipts: 13, all `NOT_VERIFIED` (java's execution-backed example verifier is not
  yet individually proven through this script, per the script's own docstring).
- CONTRADICTED facts: none.
- Edits applied by the correction engine: 0.
- **Findings: 4 total — down from 14 on the first run.** 2 `enterprise_edition_naming`
  (unchanged), 2 `format_overclaim` on the real PPTX claim (lines 39, 61).

**What changed since the first run**: 10 of the first run's 12 `format_overclaim` hits
(lines 732-741) were a real, measured false-positive class — table-row labels from this
repository's own cross-EDITION feature-comparison table ("Create, open, round-trip, save",
"Charts, animations, transitions, themes, backgrounds, group shapes, hyperlinks", etc.),
flagged only because the table's plain "yes"/"no" cells satisfied the detector's truthy-
marker rule, independent of whether the row's label was actually a format name. Confirmed
to be the same real table as `aspose-slides-foss/Aspose.Slides-FOSS-for-.NET`'s own
README (shared across the family) — fixing the detector once closes both.
`format_overclaim._table_claims()` now requires the row's label to look like a format/
capability name (an all-caps acronym or a dotted extension) before a truthy marker counts
at all; see `src/repo_presenter/readme/correction/detectors/format_overclaim.py`'s own
`_TABLE_LABEL_SHAPE` and migration/reuse-manifest.yaml for the fix's own entry.

`facts.json` copied unmodified from
`scripts/_lane_l_output/aspose-slides-foss__Aspose.Slides-FOSS-for-Java/facts.json`.
