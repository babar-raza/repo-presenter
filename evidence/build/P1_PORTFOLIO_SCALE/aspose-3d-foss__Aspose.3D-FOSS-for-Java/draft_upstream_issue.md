<!--
NOT FILED. Per mission section 9: "The first live upstream effect for each new
effect capability requires a target named by the owner and exact available
authorization." This repository's Issues effect path has not been exercised or
authorized in this session. This file is the complete, evidence-backed proposal
only -- filing it as a real GitHub issue requires an explicit owner go-ahead.
-->

**Target repository:** `aspose-3d-foss/Aspose.3D-FOSS-for-Java`
**Target revision:** `3d2ed6be91f5abdd1c52ecbcfa192719883cb1b3` (current `main` as of 2026-10-21)

## Proposed title

`Plane.toMesh()` silently returns an empty `Mesh` instead of throwing `UnsupportedOperationException` like its sibling unfinished primitives

## Proposed body

`Plane.java`'s `toMesh()` method is marked `// TODO: Implement mesh conversion` and returns
`new Mesh()`:

```java
public Mesh toMesh() {
    // TODO: Implement mesh conversion
    return new Mesh();
}
```

`Mesh`'s no-arg constructor produces an object with zero control points and zero polygons
(`getPolygonCount() == 0`), so this call succeeds without ever throwing, while silently producing
geometry that is empty and unusable.

This is inconsistent with the other primitive classes in the same state of incompleteness —
`Pyramid`, `Torus`, and `RectangularTorus` all correctly signal "not yet implemented" by throwing:

```java
// Pyramid.java, Torus.java, RectangularTorus.java
@Override
public Mesh toMesh() {
    throw new UnsupportedOperationException();
}
```

### Impact

A caller who builds a scene with a `Plane` node and calls `toMesh()` (or any code path that
triggers it, e.g. mesh-dependent export) gets no exception and no obvious signal that nothing was
produced -- only an empty `Mesh`. This is the same silent-failure hazard class the project's own
`README.md` already documents for unfinished file formats ("Several of the recognized-but-
unfinished formats above fail silently rather than with an error... don't rely on catching an
exception to detect the gap — check the actual output"), but the equivalent risk for primitive
mesh conversion is not currently disclosed anywhere in the README or `FILE_FORMATS.md`.

### Suggested fix shape (not a patch; for triage only)

Either implement real plane mesh generation (the class already exposes `length`/`width`/
`lengthSegments`/`widthSegments`/`up` -- a complete parameter set for generating a real
subdivided-plane mesh), or make `Plane.toMesh()` throw `UnsupportedOperationException()` like its
sibling unfinished primitives, so failures are loud and discoverable rather than silent.

## Dedup check performed

Run 2026-10-21: `gh issue list --repo aspose-3d-foss/Aspose.3D-FOSS-for-Java --state all` returns
**0 issues total** (open or closed) -- the repository currently has no issues at all, so this
cannot be a duplicate. `--search "plane"` and `--search "toMesh"` both independently confirm `[]`.
