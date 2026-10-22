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
