# Lane R document plan — aspose-3d-foss/Aspose.3D-FOSS-for-Java

## Case classification

Mission §7 case (A): a substantial live README (635 lines) with the full fixed-core section set,
correct badge order (Maven Central / Java version / License / Contributors), correct banner
placement, correct Enterprise Edition naming, and a left-to-right, non-stacked At a Glance
diagram. This README is unusually candid for this product family: it already discloses its own
narrow scope ("STL is the only format that is fully functional in the published 26.5.0 package"),
warns about a self-contradictory FILE_FORMATS.md, warns that the published OBJ import may be
stale relative to GitHub source, and warns generally that unfinished formats can fail silently
rather than throwing. No other README in this batch pre-empts this many of its own likely
findings in its own text.

## Why this plan converges to the live structure rather than inventing a new one

This repository's live README is the strongest evidence yet, within this batch, for
`docs/MISSION_AUTHORITY.md`'s "each live README owns its own tone, prose structure, and heading
skeleton; these are never replaced by a template" rule: it is already doing almost exactly what
the mission asks a good README to do (stating scope honestly, flagging its own documentation's
internal inconsistency, warning the reader about silent-failure risk) in its own voice. Lane R
rebuilding this from a generic shell would discard real, already-correct, already-well-placed
self-disclosure — a clear mission violation, not a stronger proof.

## What this session found, independently

Code-reading `FileFormat.java` confirmed the architecture behind the README's own claim: every
`FileFormat` instance self-registers into an extension-lookup map through the public constructor
(unlike the .NET sibling, where only explicitly-listed formats reach the dispatch list), but
`createLoadOptions()`/`createSaveOptions()`/`load()`/`save()` only have working branches for
STL/OBJ/glTF/FBX import — everything else throws. This matches the README's claim exactly; no
correction needed there. The one genuine, previously-undisclosed gap found this session is
`Plane.toMesh()`: unlike the sibling `Pyramid`/`Torus`/`RectangularTorus` (which all throw
`UnsupportedOperationException`, a loud and discoverable failure), `Plane.toMesh()` is marked
`// TODO: Implement mesh conversion` and silently returns an empty `Mesh` (zero control points,
zero polygons; confirmed from `Mesh.java`'s no-arg constructor). This is the same silent-failure
hazard class the README already discloses for file formats, found in a place (primitive
conversion) the README doesn't yet cover. Nothing else checked this session contradicted the live
text (`facts.json`: 10 of 11 checked facts SUPPORTED, 1 CONTRADICTED, 1 UNVERIFIED-and-left-alone
per the no-invented-claims rule for the OBJ-artifact-staleness claim, which this session's toolchain
could not independently confirm or refute).

## What a different peer-family observation would have changed, and didn't

The sibling `.NET` README (this same batch) required a substantially larger correction (four
format claims entirely unreachable through its public API). No structural or claim borrowing was
applied from that finding to this repository — the Java codebase's dispatch mechanism, while
analogous in spirit, is implemented differently (extension index populated by every constructor
call vs. an explicit allow-list) and happens to not produce the same class of false claim here,
because this README's own Key Capabilities/At a Glance sections already scope themselves to STL
only.

## Resulting candidate

`lane_r_candidate.md` is byte-identical to `lane_l_candidate.md`: one bullet, in the existing
Scope and Limitations section, extended by three sentences to disclose `Plane`'s silent-empty-mesh
behavior alongside the primitives that already throw. No section was added, removed, or
reordered.
