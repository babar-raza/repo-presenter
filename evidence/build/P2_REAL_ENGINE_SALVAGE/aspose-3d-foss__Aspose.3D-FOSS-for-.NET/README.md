# Real extraction works; the known format over-claim is not yet catchable

2026-10-22. `python scripts/run_lane_l.py aspose-3d-foss/Aspose.3D-FOSS-for-.NET net <clone>`.

**Real manifest/surface extraction**: 3590 facts, 293 real public-symbol facts from the
vendored tree-sitter C# surface engine. 7 example receipts, all `NOT_VERIFIED`
(`net_examples.py` is not ported).

**Did not catch the known U3D/RVM/AMF/HTML5 over-claim** (independently found by hand earlier
this session, 2026-10-21: the README's Mermaid diagram and prose claim these formats work;
`FileFormat.GetFormatByExtension()` never resolves them). Two independent, honest reasons, both
checked directly rather than assumed:

1. **The claim isn't in a markdown table.** `format_overclaim.py` (ported this session) is
   explicitly, documented-ly table-only (its own docstring: *"a prose sentence... makes the same
   over-claim in a shape this detector does not parse; broadening to prose is future work, not
   attempted here"*). Checked the live README directly: the claim lives in the Mermaid `At a
   Glance` diagram and in prose/bullets (`grep -n "U3D\|RVM\|AMF\|HTML5"` — lines 34/36/56/58/59/83/84/88),
   never a table row. This is the detector working exactly as documented, not a bug.
2. **No `format` facts exist for .NET at all.** `format_claims`/`format_declarations` are
   stubbed (`return []`) for every ecosystem except Python — confirmed this is the OLD repo's
   own unfinished state (identical stub + identical docstring in
   `E:\...\repository-presenter`'s `net.py`), not something this session's porting broke.

**What this means for "make the lanes work equally for all candidates"**: format/capability
over- and under-claim detection — the exact defect class this whole mission started from
(the original aspose-3d-foss/Python OBJ-export bug) — only works for Python today. Closing
this for the other 6 ecosystems needs new engineering (an ecosystem-specific format-declaration
reader per platform, mirroring `python_format_declarations.py`), not a salvage/port task — the
old repo never built this either. Recorded as real, valuable future work in
`project/state.yaml`.
