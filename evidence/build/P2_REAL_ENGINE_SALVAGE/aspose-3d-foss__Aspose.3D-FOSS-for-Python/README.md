# First real, fully-automated end-to-end catch

2026-10-22. `python scripts/run_lane_l.py aspose-3d-foss/Aspose.3D-FOSS-for-Python <clone>`,
run by the supervisor session, independently re-verified (not trusted from any agent's
self-report).

**What ran, with zero agent reasoning or hand-authored facts anywhere in the path:**

1. A fresh `git clone --depth 1` of the real repository.
2. `extractors/platforms/python.py` (the ported Python extractor): real manifest facts,
   real surface facts (337 public symbols via the vendored tree-sitter engine), real PyPI
   registry resolution, and — as of this run — the real, execution-backed
   `verify_python_examples()` (ported this session from the old repo's `python_examples.py`,
   using the already-ported `core/execution.py`/`core/toolchains.py` primitives): a real
   `pip install`, then each of the 12 Python code fences in the live README actually run
   against the real installed package.
3. `readme/evidence/facts/{examples,formats}.py` (ported this session): raw receipts turned
   into typed `example`/`format` facts with real polarity.
4. `readme/correction/engine.py` (ported, confinement-proof architecture): the real
   `failing_example` detector reading those facts.

**Result:** `example:008` — the README's own "Position a Node With Transform" snippet
(`scene.save("post.obj")`) — comes back `CONTRADICTED`, outcome `FAILED`, with the real
captured `TypeError: a bytes-like object is required, not 'str'` from `ObjExporter.py:50`.
The `failing_example` detector correctly surfaces this as a Finding. See `facts.json` in
this directory for the full fact record.

**Why this matters:** this is the exact same defect independently found by hand during
`P1_VERTICAL_SLICE` (2026-10-21, see `evidence/build/P1_VERTICAL_SLICE/aspose-3d-foss__Aspose.3D-FOSS-for-Python/facts.json`'s
`F-OBJ-EXPORT-BROKEN`). The hand-found version required a human/agent to design and run a
bespoke reproduction script. This version requires only `python scripts/run_lane_l.py
<repository>` — the salvaged, real pipeline rediscovers the same real bug on its own, with
no repository-specific code anywhere in the path.

**Full example outcome breakdown this run** (12 candidates): 7 `EXECUTED` (real passes,
including the correct STL/glTF/3MF export examples), 4 `NEEDS_INPUT` (examples that need a
fixture file — e.g. an existing `.obj` to open — not supplied by this run; honestly marked,
not fabricated as EXECUTED), 1 `FAILED` (the OBJ-export bug above).

**Honest scope note:** `report_gaps` also fired (22 of 337 verified public types never named
in the README) — a real, legitimate finding, not investigated further in this pass since it
is not the bug this specific proof was built to find.

**What this does NOT yet prove:** Lane R (composition) was not exercised in this run — this
proof is Lane L only. No correction was auto-applied (the `failing_example` detector is
report-only by design, per its own docstring: a broken example needs a maintainer's or a
model's fix, not a deterministic edit). No PR or issue was filed from this run (the issue
for this exact defect, `aspose-3d-foss/Aspose.3D-FOSS-for-Python#4`, was already filed
2026-10-21 from the hand-found version).
