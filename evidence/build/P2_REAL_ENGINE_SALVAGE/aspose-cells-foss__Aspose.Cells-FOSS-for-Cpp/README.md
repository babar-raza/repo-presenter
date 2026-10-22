# Fourth ecosystem's format-detection reader — a third, different idiom, and a different repo
# family (Cells, not 3D)

2026-10-22. `python scripts/run_lane_l.py aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp cpp <clone>`.

**A third correlation key, confirming the design generalizes but the idiom never does**:
`extractors/platforms/cpp_format_declarations.py` (new engineering, not a port — the old repo
never built this for C++ either). This product states formats as a plain `enum class
LoadFormat`/`enum class SaveFormat` with no extension string literal anywhere in source — unlike
.NET (`base(".ext", ...)`) and Java (`"ext"` constructor argument), there is nothing to read as
"the extension" except the enumerator's own name, so this reader normalizes the enumerator name
itself (`Xlsx` → `.xlsx`) — a heuristic, stated plainly, not a literal read. Registration is a
fully-qualified reference (`LoadFormat::Xlsx` / `SaveFormat::Xlsx`) anywhere outside the enum's
own declaration, correlated by enumerator name (like .NET's identifier correlation, not Java's
extension-string correlation).

**One real bug found and fixed before any real result could be trusted**: this repository's own
`Workbook.h` forward-declares the enum (`enum class SaveFormat;`, no body) before using it in two
`Save()` overload signatures. The first version of the enum-block regex's `[^{]*` gap skipped
right past that semicolon and greedily matched the *next* unrelated `{...}` block in the file,
reading ordinary method parameter names (`fileName`, `sheetName`, `stream`, `name`,
`currentDefinedName`) as five garbage "declared formats." Fixed by excluding `;` from the gap
(`[^{;]*`), with a regression test reproducing the exact real shape.

## The real result

This repository's declared and registered surfaces turn out to be genuinely small and already
consistent — no over-claim, no under-claim, for format at all:

```
format:output.xlsx  SUPPORTED  .xlsx   (SaveFormat::Xlsx declared in SaveFormat.h AND referenced
                                         by the real gate in XlsxWorkbookSerializer.cpp)
```

The live README only claims `.xlsx` support, which really is registered — a correct, clean
no-finding result, not a sign the reader missed something. The value of building it here is
having the signal in place at all, so a *future* revision that grows either enum without wiring
the new member into the real save path is caught the same way the .NET/Java gaps were.

**Honest limitation surfaced, not hidden**: `format:input.xlsx` comes out UNRESOLVED
(declared-only), not SUPPORTED, even though loading XLSX obviously works in this repository (it
is exercised by the test suite and is the only real format). The reason: the real source never
writes a qualified `LoadFormat::Xlsx` reference anywhere — only `LoadFormat::Auto` (the
auto-detection default) is referenced; actual format detection happens without ever comparing
against the `Xlsx` member by name. This reader's registration signal (a qualified reference) is
real but narrower than "the capability actually works," the mirror image of Java's
"dispatched-but-stub" limitation — there, a signal fired for something that doesn't really work;
here, something that really works produces no signal. Both are stated, not silently resolved.

**Unrelated, independently real finding from the same run** (not format-detection, proof the
whole Lane L pipeline is live): the real C++ toolchain actually compiled and ran this
repository's README examples — one `EXECUTED`, and one genuinely `FAILED` with a real compiler
error (`example_002.cpp:10:48: error: no match for 'operator[]'`), caught by
`failing_example`.

## Honest scope limits

- Enumerator-name-as-extension is a heuristic (`Xlsx` → `.xlsx`), not a literal source read —
  it happens to be correct for every member measured in this repository, but a product that named
  an enumerator differently from its extension (e.g. `Workbook` for `.xlsx`) would be read wrong.
  Stated, not silently assumed correct.
- Verified against one repository, one family (Cells; the only `mode: full` C++ registry entry).
  Not yet run against the other `dry_run` C++ repos (Email, PDF, Slides), which may have larger
  declared surfaces where the input/output asymmetry above, or a real over-claim, actually shows.
