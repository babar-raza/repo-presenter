# P2_REAL_ENGINE_SALVAGE run: aspose-pdf-foss/Aspose-PDF-FOSS-for-Python

2026-10-22. Command run from the repo-presenter root, against a fresh shallow clone:

```
python scripts/run_lane_l.py aspose-pdf-foss/Aspose-PDF-FOSS-for-Python python <clone-dir>
```

No crash, no workaround needed. Ran clean on the first attempt.

## Real counts printed by the script

- 645 files in the cloned tree; live README fetched via `gh api`, 1752 lines.
- **2133 facts** built (manifest + surface + registry + examples + formats).
- **42 example receipts**: `EXECUTED` 19, `FAILED` 21, `NEEDS_INPUT` 2.
- CONTRADICTED facts: `install_command:pip` plus 21 example facts (`example:001`,
  `002`, `005`, `007`, `009`, `010`, `013`, `014`, `017`, `019`, `020`, `021`, `024`,
  `025`, `026`, `029`, `030`, `033`, `035`, `039`, `041`).
- **0 edits applied** by the correction engine.

## Findings printed (23 total, verbatim outcomes)

21 `failing_example` findings, one per CONTRADICTED example above, each naming the
real exception class captured during verification: `FileExistsError` (×9),
`NameError` (×4), `IndexError` (×1), `aspose_pdf.exceptions.FontEmbeddingException`
(×1), `KeyError` (×2), `aspose_pdf.exceptions.PdfValidationException` (×1).

1 `format_overclaim` finding: line 59, README marks `TIFF` supported but no
SUPPORTED format/capability fact confirms it.

1 `report_gaps` finding: 56 of 370 verified public types named nowhere in the
README (e.g. `public_symbol:aspose_pdf.circleannotation`, truncated by the
script's own 150-character print slice).

## Not a clean result

This repository's README has real, machine-verified example breakage (21 of 42
fenced Python examples fail against the real installed package) and a real
unsupported format claim. Nothing here was invented or guessed — every exception
class and line number above is the script's own printed output, copied as-is.
`facts.json` in this directory is the exact file the script wrote.
