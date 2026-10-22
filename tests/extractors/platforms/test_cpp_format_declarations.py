"""New engineering, not a port (the old repo never built this for C++). Tested against the
exact real shapes measured live in aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp's own source
(2026-10-22): an ``enum class LoadFormat``/``enum class SaveFormat`` with no extension literal,
and a qualified reference (``SaveFormat::Xlsx``) as the one real registration signal."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.extractors.platforms.cpp_format_declarations import format_declarations

_ENUMS = """
#pragma once
namespace Aspose { namespace Cells_FOSS {

enum class LoadFormat
{
    Auto = 0,
    Xlsx = 1,
    Csv = 2,
};

enum class SaveFormat
{
    Xlsx = 0,
};

}}
"""

_SERIALIZER = """
#include "aspose/cells_foss/SaveFormat.h"
#include "aspose/cells_foss/LoadFormat.h"

namespace Aspose { namespace Cells_FOSS {

void XlsxWorkbookSerializer::Save(const SaveOptions& options) const
{
    if (options.GetSaveFormat() != SaveFormat::Xlsx) {
        throw InvalidFileFormatException("only Xlsx is supported");
    }
}

LoadOptions::LoadOptions() : _loadFormat(LoadFormat::Auto)
{
}

void Workbook::LoadFromStream(const std::vector<std::uint8_t>& stream)
{
    if (DetectFormat(stream) == LoadFormat::Xlsx) {
        LoadXlsx(stream);
    }
}

}}
"""


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def test_a_declared_and_referenced_member_is_reported_both_declared_and_registered(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "LoadFormat.h", _ENUMS)
    _write(tmp_path, "Serializer.cpp", _SERIALIZER)
    decls = format_declarations(tmp_path, ["LoadFormat.h", "Serializer.cpp"])

    xlsx = [d for d in decls if d.extension == ".xlsx"]
    assert any(d.kind == "declaration" and d.direction is None for d in xlsx)
    assert any(d.kind == "registration" and d.direction == "input" for d in xlsx)
    assert any(d.kind == "registration" and d.direction == "output" for d in xlsx)


def test_a_declared_but_never_referenced_member_is_declared_only(tmp_path: Path) -> None:
    """CSV is declared in the LoadFormat enum but never referenced by a qualified
    ``LoadFormat::Csv`` anywhere else in the tree -- declared without registration, so
    format_facts() will mark it UNRESOLVED, never SUPPORTED."""
    _write(tmp_path, "LoadFormat.h", _ENUMS)
    _write(tmp_path, "Serializer.cpp", _SERIALIZER)
    decls = format_declarations(tmp_path, ["LoadFormat.h", "Serializer.cpp"])

    csv = [d for d in decls if d.extension == ".csv"]
    assert len(csv) == 1
    assert csv[0].kind == "declaration"


def test_the_auto_detection_sentinel_is_not_treated_as_a_format(tmp_path: Path) -> None:
    _write(tmp_path, "LoadFormat.h", _ENUMS)
    decls = format_declarations(tmp_path, ["LoadFormat.h"])
    assert not any(d.extension == ".auto" for d in decls)


def test_a_forward_declaration_does_not_swallow_an_unrelated_later_brace_block(
    tmp_path: Path,
) -> None:
    """Regression: the exact real false positive measured against aspose-cells-foss/
    Aspose.Cells-FOSS-for-Cpp's own live source (2026-10-22) -- ``enum class SaveFormat;`` (a
    forward declaration, no body) followed much later by an unrelated method whose parameter
    list ends in commas was read as the enum's own body, producing five garbage "declarations"
    (fileName, sheetName, stream, name, currentDefinedName) before this fix."""
    header = """
#pragma once
enum class SaveFormat;

class Workbook
{
public:
    void Save(std::string_view fileName, SaveFormat format) const;
    void Save(std::vector<std::uint8_t>& stream, SaveFormat format) const;
};
"""
    (tmp_path / "Workbook.h").write_text(header, encoding="utf-8")
    decls = format_declarations(tmp_path, ["Workbook.h"])
    assert decls == []


def test_files_outside_the_tree_paths_list_are_not_read(tmp_path: Path) -> None:
    _write(tmp_path, "LoadFormat.h", _ENUMS)
    decls = format_declarations(tmp_path, [])  # empty tree -- nothing to scan
    assert decls == []


def test_a_non_source_file_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "LoadFormat.txt", _ENUMS)  # wrong suffix
    decls = format_declarations(tmp_path, ["LoadFormat.txt"])
    assert decls == []
