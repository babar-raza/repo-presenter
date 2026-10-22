# Real, fresh finding on data the pipeline has never seen

2026-10-22. `python scripts/run_lane_l.py aspose-3d-foss/Aspose.3D-FOSS-for-Java java <clone>`.

**Real manifest/surface extraction**: 5136 facts, including real public-symbol facts from the
vendored tree-sitter Java surface engine. 7 example receipts, all `NOT_VERIFIED` (`java_examples.py`,
the execution-backed verifier, is not ported yet -- see this directory's note in
`migration/reuse-manifest.yaml` and `project/state.yaml`'s `honestly_not_done_yet`).

**The real finding**: the `enterprise_edition_naming` detector (ported this session,
`readme/correction/detectors/enterprise_edition.py`) flagged line 634 of the live README:

> **Acknowledgments.** This project is a clean-room implementation built for API compatibility
> with the commercial Aspose.3D for Java library.

Finding: *"names the aspose.com product with a substitute for its proper name ('the commercial
Aspose.3D for Java'); the fix is not applied because no `link_target:product.enterprise` fact
is on record to cite as evidence — reported, not guessed."* This is a genuinely new finding —
not something any earlier pass in this project (manual or agent-driven) had already found or
fixed for this specific repository. It demonstrates the detector works correctly on fresh real
data, not just its own unit test fixtures.

**Honest gap, same as the .NET sibling**: `format_claims`/`format_declarations` are stubbed
(`return []`) for Java, same as every ecosystem except Python — confirmed this is **the old
repo's own unfinished state**, not something this session's porting broke or skipped (checked
directly against `E:\...\repository-presenter`'s `java.py`: identical stub, identical docstring).
Format/capability over- and under-claim detection is Python-only until this is built fresh for
the other 6 ecosystems — real, valuable future work, not a salvage gap.
