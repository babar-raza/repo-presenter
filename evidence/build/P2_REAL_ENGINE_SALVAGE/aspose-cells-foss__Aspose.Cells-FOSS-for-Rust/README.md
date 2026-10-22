# Sixth ecosystem's format-detection reader — structurally close to C++'s, independently verified

2026-10-22. `python scripts/run_lane_l.py aspose-cells-foss/Aspose.Cells-FOSS-for-Rust rust <clone>`.

**Structurally close to the C++ reader, but independently investigated, not assumed**:
`extractors/platforms/rust_format_declarations.py` (new engineering, not a port — the old repo
never built this for Rust either). This product also states formats as a plain `enum
LoadFormat`/`enum SaveFormat` with no extension string literal, and a qualified reference
(`LoadFormat::Xlsx`) as the registration signal — the same two-source shape as C++. Two real
differences confirmed directly against this repository's own source rather than assumed from the
C++ sibling:

1. Rust enums cannot be forward-declared without a body the way C++'s `enum class SaveFormat;`
   can — every `enum ... { ... }` found is a complete definition, so the forward-declaration
   false positive that had to be fixed in the C++ reader has no Rust counterpart to guard
   against.
2. Rust's exhaustiveness checking means a `match` over an enum must name every variant (or use a
   wildcard arm) to compile at all. This repository's real gate functions
   (`ensure_supported_load_format`/`ensure_supported_save_format` in `Workbook.rs`) name every
   declared variant explicitly, including the sentinel `LoadFormat::Auto` — which is why, unlike
   C++'s sibling finding (where `LoadFormat::Xlsx` was never referenced), this reader corroborates
   **both** directions for Xlsx here. The two-source design still matters for the future: a
   revision that widened a match with a wildcard arm (`_ => Ok(())`) rather than naming a new
   variant explicitly would stop referencing that variant by name, and this reader would
   correctly report it as declared-only.

## The real result

```
format:input.xlsx   SUPPORTED  .xlsx
format:output.xlsx  SUPPORTED  .xlsx
```

Both directions corroborated, matching the live README's one real claim — a correct, clean
result. `0 edits applied`, `(none)` findings: this repository's README has no structural or
over-claim defect for any detector to catch in this run.

**Unrelated, already-present finding, untouched by this work**: `install_command:cargo` is
CONTRADICTED (the crate is not published on crates.io under the name `Cargo.toml` declares) —
pre-existing, nothing to do with format detection, left alone.

## Honest scope limits

- Enumerator-name-as-extension is a heuristic, not a literal source read — correct for every
  member measured here, same caveat as the C++ reader.
- Verified against the one Rust registry entry that exists (`dry_run` mode; there is no `full`
  mode Rust candidate yet).
