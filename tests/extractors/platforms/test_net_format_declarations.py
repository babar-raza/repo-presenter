"""New engineering, not a port (the old repo never built this for .NET). Tested against the
exact real shapes measured live in aspose-3d-foss/Aspose.3D-FOSS-for-.NET's own source
(2026-10-22): a nested ``class X : FileFormat`` with a ``base(".ext", ...)`` constructor call,
and a dispatch switch expression over ``FileFormat.X`` inside an Importer/Exporter method."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.extractors.platforms.net_format_declarations import format_declarations

_REAL_SHAPE = """
namespace Aspose.ThreeD;

public partial class FileFormat
{
    internal class ObjFormat : FileFormat
    {
        public ObjFormat() : base(".obj", new[] { ".obj" }, new Version(1, 0), true, true,
            FileContentType.ASCII, new FileFormatType(".obj"))
        {
        }
    }

    internal class UnreachableFormat : FileFormat
    {
        public UnreachableFormat() : base(".xyz", new[] { ".xyz" }, new Version(1, 0), true, true,
            FileContentType.ASCII, new FileFormatType(".xyz"))
        {
        }
    }
}
"""

_DISPATCH_SHAPE = """
namespace Aspose.ThreeD.Formats;

internal class IOService
{
    internal IImporter CreateImporter(FileFormat format)
    {
        return format switch
        {
            FileFormat f when f == FileFormat.ObjFormat => new ObjReader(),
            _ => throw new NotSupportedException($"Import not supported for {format.Extension}")
        };
    }

    internal IExporter CreateExporter(FileFormat format)
    {
        return format switch
        {
            FileFormat f when f == FileFormat.ObjFormat => new ObjWriter(),
            _ => throw new NotSupportedException($"Export not supported for {format.Extension}")
        };
    }
}
"""


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def test_a_declared_and_dispatched_format_is_reported_both_declared_and_registered(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "FileFormat.cs", _REAL_SHAPE)
    _write(tmp_path, "IOService.cs", _DISPATCH_SHAPE)
    decls = format_declarations(tmp_path, ["FileFormat.cs", "IOService.cs"])

    obj = [d for d in decls if d.extension == ".obj"]
    assert any(d.kind == "declaration" for d in obj)
    assert any(d.kind == "registration" and d.direction == "input" for d in obj)
    assert any(d.kind == "registration" and d.direction == "output" for d in obj)


def test_a_declared_but_never_dispatched_format_is_declared_only(tmp_path: Path) -> None:
    """The exact real bug this reader exists to surface: a class declares a format, but no
    dispatch method's switch ever matches it -- declared without any registration in either
    direction, so format_facts() will mark it UNRESOLVED, never SUPPORTED."""
    _write(tmp_path, "FileFormat.cs", _REAL_SHAPE)
    _write(tmp_path, "IOService.cs", _DISPATCH_SHAPE)
    decls = format_declarations(tmp_path, ["FileFormat.cs", "IOService.cs"])

    unreachable = [d for d in decls if d.extension == ".xyz"]
    assert len(unreachable) == 1
    assert unreachable[0].kind == "declaration"


def test_files_outside_the_tree_paths_list_are_not_read(tmp_path: Path) -> None:
    _write(tmp_path, "FileFormat.cs", _REAL_SHAPE)
    decls = format_declarations(tmp_path, [])  # empty tree -- nothing to scan
    assert decls == []


def test_a_non_cs_file_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "FileFormat.txt", _REAL_SHAPE)  # wrong suffix
    decls = format_declarations(tmp_path, ["FileFormat.txt"])
    assert decls == []
