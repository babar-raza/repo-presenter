# Fifth ecosystem's format-detection reader — a fourth idiom, and real Lane L structure fixes

2026-10-22. `python scripts/run_lane_l.py aspose-cells-foss/Aspose.Cells-FOSS-for-Go go <clone>`.

**A fourth, again-different idiom**: `extractors/platforms/go_format_declarations.py` (new
engineering, not a port — the old repo never built this for Go either). This product has no
format enum, no class hierarchy, no string-literal constructor argument anywhere. Format support
is expressed entirely through exported Go identifiers and their doc comments:

1. A **named-verb method** whose identifier itself states the format: `ExportToCSV`,
   `ImportFromCSV` — the format name is a literal suffix of the Go identifier.
2. The package's **primary `Load`/`Save`**, which carry no format name in their identifier at
   all — the real source states the format only in English prose directly above the function
   (`// Load opens the .xlsx file at path...`), so this reader reads the extension out of that
   doc comment.

**Honestly stated, not worked around**: unlike .NET/Java/C++, Go's idiom gives this reader no
second, independent signal to corroborate a declaration against — an exported Go function's mere
existence already implies the code compiles, and the identifier (or its doc comment) is the only
format statement there is. Both a "declaration" and a "registration" record are emitted from the
same single reading for this reason. This reader genuinely cannot produce the "declared but never
wired up" gap the other three readers can, because Go's language idiom does not physically
separate intent-to-support from a working implementation the way a class hierarchy or
enum-plus-dispatch-table does. Confirmed directly: a search of this repository's real source for
any `TODO`/`not implemented`/`unimplemented` marker near a format-sounding identifier found
exactly one unrelated hit (an OLE compound-file edge case, nothing to do with formats) — there is
no declared-but-stubbed format in this repository to miss.

## The real result

```
format:input.csv   SUPPORTED  .csv
format:input.xlsx  SUPPORTED  .xlsx
format:output.csv  SUPPORTED  .csv
format:output.xlsx SUPPORTED  .xlsx
```

All four come out SUPPORTED by design (a single, self-corroborating source), matching this
repository's live README, which claims exactly these two formats and no others — a correct,
clean result, not a sign the reader missed something.

**Real, independent findings from the same run, unrelated to format detection** — proof the
whole Lane L pipeline, not just this one reader, is live for Go:

- **Two real structure fixes auto-applied** by the correction engine: a second `# H1` heading
  the README's own template forbids, and an unclosed `<details>` block that silently collapses
  every section rendered after it.
- **A real compiler-caught broken example**: `failing_example` reports example 6 failed with
  `.\main.go:16:31: undefined: generateSmallPNG` — a genuinely broken code block in the live
  README, caught by actually compiling it, not by static guessing.
- `report_gaps`: 14 of 28 verified public types named nowhere in the README (an under-claim,
  unrelated to format).

## Honest scope limits

- This reader cannot distinguish a format that is genuinely wired up from one that merely has an
  exported method with a plausible name — Go's idiom gives it nothing stronger to check against.
  Stated above, not silently assumed away.
- Verified against one repository, one family (Cells; the only `mode: full` Go registry entry).
  The other Go registry entry (`aspose-pdf-foss/Aspose-PDF-FOSS-for-Go`, `dry_run`) has not been
  checked against this reader's named-verb/doc-comment patterns.
