# Second ecosystem, second real catch — the format over-claim this mission started from

2026-10-22 (updated — supersedes this directory's first version, which honestly reported the
gap this entry closes). `python scripts/run_lane_l.py aspose-3d-foss/Aspose.3D-FOSS-for-.NET net <clone>`.

**What changed since the first run**: that run correctly did NOT catch the known U3D/RVM/AMF/
HTML5 over-claim, for two honest reasons recorded at the time — the claim is in the Mermaid At
a Glance diagram, not a table, and .NET had zero format facts at all (`format_claims`/
`format_declarations` were stubbed, same as the old repo). Both gaps are now closed:

1. **`extractors/platforms/net_format_declarations.py`** (new engineering, not a port — the old
   repo never built this for .NET either): reads every `.cs` file for (a) a nested
   `class X : FileFormat` whose constructor calls `base(".ext", ...)` — the declaration — and
   (b) a dispatch switch arm matching `FileFormat.X` inside an Importer/Exporter-named method —
   the registration, with direction inferred from the method name. Verified directly against
   this repository's own real `IOService.cs`: it finds exactly the 8 real registered formats
   (Obj/Stl/Gltf/Fbx/Microsoft3MF/Collada/Ply/Discreet3DS, both directions) and correctly finds
   **no** registration for U3D/RVM/AMF/HTML5 anywhere, because none exists in the real source.
2. **`readme/correction/detectors/format_overclaim.py`** extended with a second claim source:
   Mermaid At a Glance `i\d+`/`o\d+` node labels, scanning for acronym-shaped tokens
   (`[A-Z0-9]{2,6}` with at least one letter) — the exact shape this repository's own claim
   lives in. Bounded, not general prose parsing: only inside those two specific node-ID
   prefixes.

## The real result

```
[format_overclaim] line 34: the README marks 'U3D' supported, but no SUPPORTED format or capability fact confirms it is actually wired up...
[format_overclaim] line 36: the README marks 'RVM' supported, but no SUPPORTED format or capability fact confirms it is actually wired up...
[format_overclaim] line 56: the README marks 'U3D' supported, ...
[format_overclaim] line 58: the README marks 'RVM' supported, ...
[format_overclaim] line 59: the README marks 'AMF' supported, ...
[format_overclaim] line 59: the README marks 'HTML5' supported, ...
[report_gaps] line 0: 2 verified format(s) named nowhere in the README: format:input.dae, format:output.dae
```

Every one of the four known over-claimed formats (U3D, RVM, AMF, HTML5) is caught, at both the
Starting-Points and Outputs node where each appears, automatically — no hand-authored facts, no
repository-specific code. `report_gaps` additionally and correctly found the complementary
under-claim (COLLADA/.dae is genuinely registered and working, per the declaration+registration
cross-reference, but never mentioned in the README) — proof the two detectors cover opposite
directions of the same defect class without stepping on each other.

**One real false positive found and fixed along the way**: the first version of this run also
flagged "AVEVA" and "PDMS" — the node label reads `"...Microsoft 3MF, AVEVA PDMS RVM)"`, and
AVEVA/PDMS are a vendor name and product-suite name clarifying what RVM is, not separate format
claims. Added to a small, evidence-based exclusion list (`_NOT_A_FORMAT`) with a regression test
reproducing the exact false positive, the same discipline applied to every other finding in this
session.

## Honest scope limits

- `net_examples.py` (execution-backed example verification for .NET) is still not ported — all
  7 example receipts are `NOT_VERIFIED`. This proof is entirely static (declaration +
  dispatch-switch reading), not execution-backed, unlike the Python OBJ-export catch.
- The declaration reader only recognizes the "nested class with a `base()` constructor call"
  pattern. A format declared the OTHER way this same file uses (a direct
  `public static readonly FileFormat X = new FileFormat(".ext", ...)` field) is not detected as
  "declared" at all — it doesn't need to be for this specific finding (the over-claim detector
  only needs the ABSENCE of any fact, which holds either way), but a future pass wanting a
  complete declared-format inventory for .NET would need to add this second pattern.
- Verified against one repository, one family. Not yet run against the other 8 .NET repos in
  the registry to see whether the same two patterns generalize or need adjustment.
