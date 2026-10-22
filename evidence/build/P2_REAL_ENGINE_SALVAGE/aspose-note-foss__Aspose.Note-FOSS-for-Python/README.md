# Lane L real-pipeline run: aspose-note-foss/Aspose.Note-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-note-foss/Aspose.Note-FOSS-for-Python python <clone-dir>
```

No crash, no manual intervention. Real printed output below.

**Tree / README:** 94 files cloned; live README fetched via `gh api`, 528 lines.

**Facts:** 195 facts built. 12 example receipts (most of the 7 repos) — 11
`EXECUTED`, 1 `FAILED`. One fact `CONTRADICTED`: `example:001`.

**Correction engine:** 0 edits applied.

**Findings (report-only), verbatim as printed, 2 total:**

- `[enterprise_edition_naming]` line 451: "possible Enterprise Edition naming
  violation ('commercial product'); the product name and its platform are not
  both spelled out on this line, so the f[...]" (cut by the script's own
  150-char cap). The actual README line 451 reads: "`License.SetLicense()` and
  `Metered.SetMeteredKey()` are present for API-shape compatibility with the
  commercial product but are no-ops in this edition — no license is required
  to use this library." This is the only run of the 7 where this detector
  fired.
- `[failing_example]` line 104: example on lines 104-111 — "example 1: FAILED;
  AttributeError". Snippet (from `facts.json`, `example:001`):
  ```python
  from aspose.note import Document

  doc = Document("SimpleTable.one")
  print(doc.DisplayName)
  for page in doc:
      print(page.Title.TitleText.Text)
  ```
  Input was staged as `SimpleTable.one` from the repo's own test fixtures.

**Full fact record:** `facts.json` in this directory, copied verbatim from
`scripts/_lane_l_output/aspose-note-foss__Aspose.Note-FOSS-for-Python/facts.json`.

**Scope note:** this is Lane L only (facts + report-only findings). No PR/issue was
filed from this run.
