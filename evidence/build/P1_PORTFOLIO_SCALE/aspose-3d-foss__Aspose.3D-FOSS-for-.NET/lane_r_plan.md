# Lane R document plan — aspose-3d-foss/Aspose.3D-FOSS-for-.NET

## Case classification

Mission §7 case (A): a substantial live README (631 lines, full fixed-core section set:
Navigation, At a Glance, Key Capabilities, Installation, Dependencies, Quick Start, Additional
Examples, API Reference, Documentation & Resources, Scope and Limitations, Development and
Testing, License), correct badge order, correct banner placement, correct Enterprise Edition
naming, and a left-to-right, non-stacked At a Glance diagram. The document's own voice and
heading skeleton are already sound — the problem found this session is narrowly factual
(specific format-support claims), not structural or tonal.

## Why this plan converges to the live structure rather than inventing a new one

`docs/MISSION_AUTHORITY.md`'s distillation of `idea.md` holds that "each live README owns its own
tone, prose structure, and heading skeleton; these are never replaced by a template," and that
Lane R "can rebuild a coherent, excellent document, but not by treating inherited content as
disposable inputs to a generic shell." This repository's live README already satisfies the
fixed-core contract and is accurate everywhere this session could independently verify it, except
for a specific, reproducible, real-execution-confirmed dispatch-gap around RVM/U3D/AMF/HTML5
(see `facts.json` F-RVM-U3D-AMF-HTML5-UNREACHABLE and F-SCOPE-RVM-CLAIM-CONTRADICTED). Rebuilding
the whole document from scratch for one factual correction would be a generic-shell overfit, not
a stronger proof — exactly the failure mode mission §3 warns against.

## What this session found that the prior owner review (docs/history-reconstruction.md) flagged as a risk for this exact repository

`docs/MISSION_AUTHORITY.md`'s "critical fact" section records the owner's 2026-10-20 finding that
"3D-.NET advertises formats its own `IOService.cs` rejects." This session independently
re-derived a finding in that same family, but through a different and more complete mechanism
than a plain `IOService.cs` read would show: the real gatekeeper is `FileFormat.GetFormatByExtension()`,
which both `Scene.Save(string)` and `Scene.Open(string)` call *before* ever reaching
`IOService` — and it silently omits RVM, U3D, AMF, and HTML5 from its internal `_formats` list
even though `FileFormat` exposes public static fields for all four (`RvmText`/`RvmBinary`,
`Universal3D`, `AMF`, `HTML5`) that look, from the outside, exactly like the eight formats that
actually work. This was confirmed with real execution (dotnet 10.0.401 is available per the
playbook), not code-reading alone: a throwaway console app referencing the library project
directly reproduced `ArgumentException: Unsupported file format` for all four extensions. This is
this repository's own, independently-derived finding — not copied from the Python sibling's
OBJ-export defect (which does not reproduce here; OBJ/COLLADA export both work correctly in this
codebase, per F-OBJ-STL-3MF-DAE-PLY-3DS-EXPORT-WORK) or from the owner's prior note beyond its
one-line pointer.

## What a different peer-family observation would have changed, and didn't

The sibling `aspose-3d-foss/Aspose.3D-FOSS-for-Python` README (P1 vertical-slice worked example)
documents a completely different defect shape (OBJ export broken, COLLADA export unreachable via
a different mechanism — an exporter-ordering bug, not a missing-from-dispatch-list bug). No
cross-platform structural or claim borrowing was applied here; each repository's own facts stand
on their own, per mission §3.

## Resulting candidate

`lane_r_candidate.md` is byte-identical to `lane_l_candidate.md`. Both lanes, applied
independently to the same verified facts and the same live-structure-as-reference rule, correctly
converge on the same document: the live README needed one class of precise correction (removing
four format claims that are not reachable through the public API, and correcting the Scope and
Limitations section's own incorrect self-assessment of the RVM gap), not a rewrite.
