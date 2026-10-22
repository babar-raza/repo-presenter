# Sixth and final ecosystem's format-detection reader — a real latent product bug, correctly
# NOT a README defect

2026-10-22. `python scripts/run_lane_l.py aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript
typescript <clone>`.

**The idiom, and why scoping the registration signal to the right method matters**:
`extractors/platforms/typescript_format_declarations.py` (new engineering, not a port — the old
repo never built this for TypeScript either). This product declares a single string-valued
`SaveFormat` enum (`XLSX = "xlsx"`, `CSV = "csv"`, `JSON = "json"`, `MARKDOWN = "markdown"`,
`HTML = "html"`) and a `detectFormat()` helper that maps a file extension to one of those
members. A reader that treated any qualified `SaveFormat.X` reference anywhere in the file as
"registered" would read CSV/JSON/MARKDOWN as wired up, because `detectFormat()` references all
three — **but `detectFormat()` only guesses which format a path implies; it is not the method
that actually writes a file.** The real write dispatch, `Workbook.save()`, special-cases only
`SaveFormat.HTML` and falls through to a generic ZIP writer for everything else.

**A real latent bug in the product's own code, found by this investigation**: calling
`workbook.save("report.csv")` in this real repository actually writes XLSX/ZIP bytes to a
`.csv` path, not real CSV content — `save()` never checks for `SaveFormat.CSV`/`JSON`/
`MARKDOWN` at all, only `HTML`. Confirmed directly against the real source
(`workbook.ts`): `detectFormat()` references `SaveFormat.CSV`/`JSON`/`MARKDOWN`, but `save()`'s
own body does not. This reader is deliberately scoped to read qualified `SaveFormat.X`
references only from inside `save()`'s own body, not the whole file, specifically so it reports
CSV/JSON/MARKDOWN as declared-but-unregistered rather than being fooled by `detectFormat()`'s
unrelated reference.

**Correctly, this is not a README defect**: the live README documents CSV/JSON/Markdown export
only through the separate, genuinely-working `toCsv()`/`toJson()`/`toMarkdown()` text-returning
methods ("Export a workbook as text... ready to write to a file or hand to another process
directly") — it never claims `save(path, {saveFormat: SaveFormat.CSV})` writes a real CSV file.
This tool's scope is README correction, not fixing the product's own `save()` implementation, so
that real bug is reported here as a discovery, not patched.

**One real bug caught and fixed in this reader before it could be trusted**: the first version
read method bodies as a fixed-size line window from the declaration line (the same approach the
.NET/Java readers use). This repository's real method signatures span several lines before the
opening brace (`async save(\n  filePath: string,\n  options?: {...},\n) {`), and this reader's
own unit tests caught the window overflowing past `save()`'s real end into the unrelated
`detectFormat()` method on a dense fixture — which would have falsely corroborated exactly the
gap this reader exists to catch. Fixed by replacing the window with real paren/brace-depth
counting (skipping past the parameter list's own brace pairs first, then counting the body's
own braces to its true matching close) before this reader was run against the real repository.

## The real result

```
format:input.html   SUPPORTED  .html
format:output.html  SUPPORTED  .html
```

Only HTML is corroborated — both directions, matching the live README's one direct
file-to-file claim. CSV/JSON/MARKDOWN/XLSX produce no fact at all (no registration signal in
either `save()` or `load()`'s own body), which is the correct, fail-closed outcome given what the
real source shows: XLSX is the implicit fallthrough default in both methods (never an explicit
comparison — the same honestly-stated limitation already recorded for the C++/Go readers), and
CSV/JSON/MARKDOWN genuinely have no file-path save implementation to find. Zero Lane L findings
in this run: the README never makes the claim the product's own code doesn't back, so there is
nothing to flag.

## Honest scope limits

- This reader has no signal at all for the `toCsv()`/`toJson()`/`toMarkdown()` text-export
  methods — a different capability (string-returning) than the `save(path, {saveFormat})`
  file-write path this reader models, deliberately not conflated with it.
- XLSX comes out with no fact (declared, unregistered either direction) despite genuinely
  working — the same stated limitation as the C++/Go readers' implicit-default gap.
- Verified against one repository, the only `mode: full` TypeScript registry entry. The two
  `dry_run` TypeScript repos (3D, PDF) have not been checked against this reader's patterns.

## Portfolio note

This closes `BUILD_FORMAT_DETECTION_FOR_NON_PYTHON_ECOSYSTEMS` — all six non-Python ecosystems
(.NET, Java, C++, Go, Rust, TypeScript) now have a real, independently-investigated
format-declarations reader, each built from that ecosystem's own real source rather than a
shape assumed to generalize from another. The correlation key diverged three separate times
across the six (identifier via dispatch-arm, extension string, identifier via qualified
reference, no second signal at all, and now a signal that must be scoped to the right method) —
the recurring lesson of this whole effort.
