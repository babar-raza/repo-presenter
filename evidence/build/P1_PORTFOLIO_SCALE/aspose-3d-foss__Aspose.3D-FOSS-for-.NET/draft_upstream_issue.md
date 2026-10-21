<!--
NOT FILED. Per mission section 9: "The first live upstream effect for each new
effect capability requires a target named by the owner and exact available
authorization." This repository's Issues effect path has not been exercised or
authorized in this session. This file is the complete, evidence-backed proposal
only -- filing it as a real GitHub issue requires an explicit owner go-ahead.
-->

**Target repository:** `aspose-3d-foss/Aspose.3D-FOSS-for-.NET`
**Target revision:** `52b0f00ebf28a0b4173921725ff170685ec2c502` (current `main` as of 2026-10-21)

## Proposed title

`FileFormat.RvmText`/`RvmBinary`, `Universal3D`, `AMF`, and `HTML5` are public static fields with
no dispatch entry -- `Scene.Open()`/`Scene.Save()` always throw `ArgumentException` for `.rvm`,
`.u3d`, `.amf`, `.html`, contradicting the README's own documented format support

## Proposed body

`Scene.Save(path)` and `Scene.Open(path)` both resolve a format exclusively through
`FileFormat.GetFormatByExtension()`, which only recognizes extensions present in the private
static `FileFormat._formats` list (populated by `InitializeFormats()`: OBJ, STL, glTF, FBX,
Microsoft 3MF, COLLADA, PLY, Discreet 3DS -- 8 entries). `FileFormat` separately exposes public
static fields `RvmText`, `RvmBinary` (`Formats.RvmFormat`), `Universal3D`, `AMF`, and
`HTML5`/`Aspose3DWeb`, which look like registered, dispatchable formats from the public API
surface, but none of them is added to `_formats`.

### Repro

```csharp
using Aspose.ThreeD;
using Aspose.ThreeD.Entities;
using Aspose.ThreeD.Shading;

var scene = new Scene();
scene.RootNode.CreateChildNode("Box", new Entities.Box(2, 2, 2), new LambertMaterial("m"));

scene.Save("out.rvm");   // ArgumentException: Unsupported file format: .rvm
scene.Save("out.u3d");   // ArgumentException: Unsupported file format: .u3d
scene.Save("out.amf");   // ArgumentException: Unsupported file format: .amf
scene.Save("out.html");  // ArgumentException: Unsupported file format: .html
```

Reproduced live against this exact `main` commit: cloned the repository, referenced
`src/main/Aspose.ThreeD/Aspose.ThreeD.csproj` directly from a throwaway console app (dotnet
10.0.401), and ran the above. All four calls threw `ArgumentException` at the
`GetFormatByExtension` call, before any RVM/U3D/AMF/HTML5-specific code ever ran. By contrast,
`.obj`/`.stl`/`.3mf`/`.dae`/`.ply`/`.3ds` all succeeded in the same session, for the same scene.

### Impact on the published README

This repository's own `README.md` currently documents RVM, U3D, AMF, and HTML5 as supported
formats in three places: the opening paragraph ("...Universal 3D"), the Key Capabilities section
("plus Microsoft 3MF and AVEVA PDMS RVM models, AMF, and an HTML5/Aspose 3D Web viewer export"),
and the At a Glance diagram (inputs/outputs for RVM and U3D). The Scope and Limitations section
additionally states "core RVM geometry import/export works, RVM attribute data does not load" --
which is also incorrect; RVM is not reachable at all through the public `Scene` API, not 90%
functional.

### Suggested fix shape (not a patch; for triage only)

1. Either add `RvmFormat`/`Universal3D`/`AMF`/`HTML5` (with real reader/writer backing, which does
   not currently exist anywhere in the codebase) to `FileFormat._formats` and `IOService`'s
   dispatch switches, or
2. If these four formats are intentionally out of scope for the FOSS edition (consistent with
   how `DracoFormat`/`PdfFormat` are already disclosed as "no reader/writer implementation
   anywhere in the codebase"), update the README to remove the RVM/U3D/AMF/HTML5 claims and
   correct the Scope and Limitations RVM bullet accordingly.

## Dedup check performed

Run 2026-10-21: `gh issue list --repo aspose-3d-foss/Aspose.3D-FOSS-for-.NET --state all` returns
**0 issues total** (open or closed) -- the repository currently has no issues at all, so this
cannot be a duplicate. `--search "rvm"`, `--search "u3d"`, and `--search "unsupported file
format"` all independently confirm `[]`.
