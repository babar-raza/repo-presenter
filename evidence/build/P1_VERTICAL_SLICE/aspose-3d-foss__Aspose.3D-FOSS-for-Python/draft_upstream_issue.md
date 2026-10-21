<!--
NOT FILED. Per mission section 9: "The first live upstream effect for each new
effect capability requires a target named by the owner and exact available
authorization." This repository's Issues effect path has not been exercised or
authorized in this session. This file is the complete, evidence-backed proposal
only -- filing it as a real GitHub issue requires an explicit owner go-ahead.
-->

**Target repository:** `aspose-3d-foss/Aspose.3D-FOSS-for-Python`
**Target revision:** `65b1f577c0f16d0d9112bb6c1153d3024543ac02` (current `master` as of 2026-10-21)

## Proposed title

OBJ export via `Scene.save()` always raises `TypeError`; direct `ObjExporter.export()` silently writes nothing for any scene built the documented way

## Proposed body

`Scene.save(path_ending_in_.obj)` fails on every call with:

```
TypeError: a bytes-like object is required, not 'str'
```

Reproduced on the published PyPI package `aspose-3d-foss==26.1.0` and against the
current `master` blob of `aspose/threed/formats/obj/ObjExporter.py` (byte-identical
to the installed wheel, so this is not a stale-package issue).

### Repro

```python
import aspose.threed as a3d
from aspose.threed.entities import Box

scene = a3d.Scene()
box = Box(length=2.0, width=1.0, height=1.0)
scene.root_node.create_child_node("box", entity=box.to_mesh())
scene.save("box.obj")
```

```
Traceback (most recent call last):
  ...
  File ".../aspose/threed/Scene.py", line 181, in save
    exporter.export(self, stream, options)
  File ".../aspose/threed/formats/obj/ObjExporter.py", line 25, in export
    self._write_obj(scene, stream, options)
  File ".../aspose/threed/formats/obj/ObjExporter.py", line 50, in _write_obj
    stream.write(content)
TypeError: a bytes-like object is required, not 'str'
```

### Root cause 1 — str written to a binary stream

`ObjExporter._write_obj()` (line 50) builds `content = '\n'.join(lines)`, a `str`,
and calls `stream.write(content)` directly. `Scene.save()` always opens a
filename-based target with `open(file_name, 'wb')` (binary mode), so this always
fails for a plain filename.

### Root cause 2 — independent of root cause 1, and still broken if "fixed" naively

Even calling `ObjExporter().export(scene, io.StringIO(), options)` directly,
bypassing `Scene.save()` with a correctly-typed text stream, writes **zero bytes**
for a scene built the way every example in this project's own README builds one
(entities attached to a named child node via `create_child_node()`), because:

```python
def _collect_nodes(self, node, node_map, material_map, node_id=0):
    if node.entity is not None and node not in node_map.values():
        node_map[node_id] = node
        ...
        for child in node.child_nodes:
            node_id = self._collect_nodes(child, node_map, material_map, node_id + 1)
    return node_id
```

The recursive descent into `node.child_nodes` only happens **inside** the
`if node.entity is not None` branch. When called with `scene.root_node` (which
itself carries no entity in every documented usage pattern), the function returns
immediately without visiting any child node, so `node_map` stays empty regardless
of what the scene actually contains.

### Impact

OBJ export is completely non-functional through any usage pattern this project's
own README documents, and has no test coverage (`tests/test_obj_importer.py`
exists; no OBJ export test exists in the repository).

### Suggested fix shape (not a patch; for triage only)

1. Encode `content` to bytes (`content.encode('utf-8')`) before writing, or detect
   the stream's mode and encode conditionally, matching the pattern other
   exporters already use successfully (STL/glTF/3MF export all work correctly
   against the same `Scene.save()` binary-stream contract).
2. Fix `_collect_nodes()` to recurse into `node.child_nodes` unconditionally,
   independent of whether the current node itself carries an entity (mirroring
   how `Scene.save()`'s own working exporters traverse the scene graph).

## Dedup check performed

Run 2026-10-21: `gh issue list --repo aspose-3d-foss/Aspose.3D-FOSS-for-Python --state all` returns
**0 issues total** (open or closed) — the repository currently has no issues at
all, so this cannot be a duplicate. `--search "obj export"` and `--search "ObjExporter"`
both independently confirm `[]`.
