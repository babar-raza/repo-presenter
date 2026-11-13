"""New engineering, not a port (the old repo never built this for Java). Tested against the
exact real shapes measured live in aspose-3d-foss/Aspose.3D-FOSS-for-Java's own source
(2026-10-22): a direct ``new FileFormat(...)`` constructor call, a subclass ``super(...)`` call,
and an ``ext.equals("...")`` dispatch chain inside ``load``/``save`` methods."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.extractors.platforms.java_format_declarations import format_declarations

_REAL_SHAPE = """
package com.aspose.threed;

public class FileFormat {
    public static final FileFormat STL_BINARY;
    public static final FileFormat WAVEFRONTOBJ;
    public static final FileFormat UNIVERSAL3D;

    static {
        STL_BINARY = new FileFormat(FileFormatType.STL, new Version(1, 0, 0),
            FileContentType.BINARY, "stl", new String[]{"stl"}, true, true);
        WAVEFRONTOBJ = new FileFormat(FileFormatType.WAVEFRONTOBJ, new Version(1, 0, 0),
            FileContentType.ASCII, "obj", new String[]{"obj"}, true, true);
        UNIVERSAL3D = new FileFormat(FileFormatType.UNIVERSAL3D, new Version(1, 0, 0),
            FileContentType.BINARY, "u3d", new String[]{"u3d"}, true, true);
    }

    Scene load(Stream stream, LoadOptions options) throws IOException, ImportException {
        String ext = extension.toLowerCase();
        if (ext.equals("stl")) {
            return new StlReader().load(stream, options);
        }
        else if (ext.equals("obj")) {
            return new ObjReader().load(stream, options);
        }
        throw new IOException("No importer available for format: " + extension);
    }

    void save(Scene scene, Stream stream, SaveOptions options) throws IOException {
        String ext = extension.toLowerCase();
        if (ext.equals("stl")) {
            new StlWriter().save(scene, stream, options, contentType);
        }
        else {
            throw new IOException("No exporter available for format: " + extension);
        }
    }
}

class RvmFormat extends FileFormat {
    public RvmFormat(FileContentType contentType) {
        super(FileFormatType.RVM, new Version(1, 0, 0), contentType,
              ".rvm", new String[]{".rvm"}, true, true);
    }
}
"""


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def test_a_declared_and_dispatched_format_is_reported_both_declared_and_registered(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "FileFormat.java", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["FileFormat.java"])

    stl = [d for d in decls if d.extension == ".stl"]
    assert any(d.kind == "declaration" for d in stl)
    assert any(d.kind == "registration" and d.direction == "input" for d in stl)
    assert any(d.kind == "registration" and d.direction == "output" for d in stl)


def test_a_declared_but_never_dispatched_format_is_declared_only(tmp_path: Path) -> None:
    """The exact real bug this reader exists to surface: OBJ is declared and dispatched for
    input only (the save() chain's real shape in this fixture has no 'obj' arm), and
    UNIVERSAL3D/RVM are declared with canImport/canExport hardcoded true but never dispatched
    anywhere -- declared without any registration, so format_facts() will mark them UNRESOLVED,
    never SUPPORTED, exactly mirroring this repository's real U3D/RVM over-claim."""
    _write(tmp_path, "FileFormat.java", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["FileFormat.java"])

    obj = [d for d in decls if d.extension == ".obj"]
    assert any(d.kind == "declaration" for d in obj)
    assert any(d.kind == "registration" and d.direction == "input" for d in obj)
    assert not any(d.kind == "registration" and d.direction == "output" for d in obj)

    for extension in (".u3d", ".rvm"):
        matching = [d for d in decls if d.extension == extension]
        assert len(matching) == 1
        assert matching[0].kind == "declaration"


def test_a_subclass_super_call_extension_is_read_with_its_leading_dot_normalized(
    tmp_path: Path,
) -> None:
    """RvmFormat's super() call states its extension as ".rvm" (with a leading dot), unlike the
    direct-constructor formats' bare "rvm" style -- both must normalize to the same key so a
    declaration recorded one way is still found by a dispatch arm written the other way."""
    _write(tmp_path, "FileFormat.java", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["FileFormat.java"])
    assert any(d.extension == ".rvm" and d.kind == "declaration" for d in decls)


def test_files_outside_the_tree_paths_list_are_not_read(tmp_path: Path) -> None:
    _write(tmp_path, "FileFormat.java", _REAL_SHAPE)
    decls = format_declarations(tmp_path, [])  # empty tree -- nothing to scan
    assert decls == []


def test_a_non_java_file_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "FileFormat.txt", _REAL_SHAPE)  # wrong suffix
    decls = format_declarations(tmp_path, ["FileFormat.txt"])
    assert decls == []


_STUBBED_HANDLERS = """
package com.aspose.threed;

public class FileFormat {
    static {
        OBJ = new FileFormat(FileFormatType.WAVEFRONTOBJ, new Version(1, 0, 0),
            FileContentType.ASCII, "obj", new String[]{"obj"}, true, true);
        GLTF = new FileFormat(FileFormatType.GLTF2, new Version(2, 0, 0),
            FileContentType.ASCII, "gltf", new String[]{"gltf"}, true, true);
        GLB = new FileFormat(FileFormatType.GLTF2, new Version(2, 0, 0),
            FileContentType.BINARY, "glb", new String[]{"glb"}, true, true);
        FBX = new FileFormat(FileFormatType.FBX, new Version(7, 4, 0),
            FileContentType.BINARY, "fbx", new String[]{"fbx"}, true, true);
    }

    public LoadOptions createLoadOptions() throws ImportException {
        if (extension.equals("gltf") || extension.equals("glb")) {
            return new GltfLoadOptions();
        }
        throw new ImportException("Load options not implemented for " + extension);
    }

    Scene load(Stream stream, LoadOptions options) throws IOException, ImportException {
        String ext = extension.toLowerCase();
        if (ext.equals("obj")) {
            ObjReader loader = new ObjReader();
            return loader.load(stream, options);
        }
        else if (ext.equals("gltf") || ext.equals("glb")) {
            GltfReader loader = new GltfReader();
            return loader.load(stream, options);
        }
        else if (ext.equals("fbx")) {
            return new FbxReader().load(stream, options);
        }
        throw new IOException("No importer available for format: " + extension);
    }

    void save(Scene scene, Stream stream, SaveOptions options) throws IOException {
        String ext = extension.toLowerCase();
        if (ext.equals("obj")) {
            ObjWriter saver = new ObjWriter();
            saver.save(scene, stream, options);
        }
    }

    private static class ObjReader {
        public Scene load(Stream stream, LoadOptions options) throws IOException, ImportException {
            Scene scene = new Scene();
            java.io.BufferedReader reader = open(stream); // "}" in a comment is not a brace
            String line = reader.readLine();
            return scene;
        }
    }

    private static class GltfReader {
        public Scene load(Stream stream, LoadOptions options) throws IOException, ImportException {
            // TODO: implement GLTF loading
            return new Scene();
        }
    }

    private static class FbxReader {
        public Scene load(Stream stream, LoadOptions options) throws IOException, ImportException {
            throw new UnsupportedOperationException("FBX import is not implemented");
        }
    }

    private static class ObjWriter {
        public void save(Scene scene, Stream stream, SaveOptions options) throws IOException {
            // TODO: implement OBJ saving
        }
    }
}
"""


def _registered(decls, direction):
    return {d.extension for d in decls if d.kind == "registration" and d.direction == direction}


def test_a_format_dispatched_only_to_a_stub_handler_is_not_registered(tmp_path: Path) -> None:
    """Hosted Lane R run 43394954743 (Aspose.3D-FOSS-for-Java): ``GltfReader.load`` is a ``// TODO``
    returning an empty ``Scene``, yet the dispatch arm made ``format:input.gltf`` SUPPORTED and the
    README claimed the product reads glTF. A stub handler is not a registration; a real one is."""
    _write(tmp_path, "FileFormat.java", _STUBBED_HANDLERS)
    decls = format_declarations(tmp_path, ["FileFormat.java"])

    assert _registered(decls, "input") == {".obj"}  # ObjReader.load really reads
    assert _registered(decls, "output") == set()  # ObjWriter.save is an empty TODO
    stubbed = {
        (d.extension, d.direction): d.detail
        for d in decls
        if d.kind == "declaration" and d.direction is not None
    }
    assert set(stubbed) == {
        (".gltf", "input"),
        (".glb", "input"),
        (".fbx", "input"),
        (".obj", "output"),
    }
    assert "GltfReader.load" in stubbed[(".gltf", "input")]
    assert "FbxReader.load" in stubbed[(".fbx", "input")]  # a not-implemented throw is a stub


def test_stubbed_formats_become_unresolved_facts_and_implemented_ones_stay_supported(
    tmp_path: Path,
) -> None:
    from repo_presenter.readme.evidence.facts.formats import format_facts

    _write(tmp_path, "FileFormat.java", _STUBBED_HANDLERS)
    decls = format_declarations(tmp_path, ["FileFormat.java"])
    polarity = {
        fact.id: fact.polarity
        for fact in format_facts([], [], lambda _code: [], "examples.json", decls)
    }
    assert polarity["format:input.obj"] == "SUPPORTED"
    for unresolved in (
        "format:input.gltf",
        "format:input.glb",
        "format:input.fbx",
        "format:output.obj",
    ):
        assert polarity[unresolved] == "UNRESOLVED"


def test_an_unresolvable_handler_keeps_the_dispatch_registration(tmp_path: Path) -> None:
    """``_REAL_SHAPE`` dispatches to handler classes it never declares: nothing is known about
    them, so the arm stays a registration (no format is demoted on a guess)."""
    _write(tmp_path, "FileFormat.java", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["FileFormat.java"])
    assert _registered(decls, "input") == {".stl", ".obj"}
    assert _registered(decls, "output") == {".stl"}
