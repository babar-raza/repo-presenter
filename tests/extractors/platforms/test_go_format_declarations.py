"""New engineering, not a port (the old repo never built this for Go). Tested against the
exact real shapes measured live in aspose-cells-foss/Aspose.Cells-FOSS-for-Go's own source
(2026-10-22): named ``ExportTo``/``ImportFrom`` methods, and the package's primary bare
``Load``/``Save`` whose only format statement lives in the doc comment above them."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.extractors.platforms.go_format_declarations import format_declarations

_REAL_SHAPE = """
package cells_foss

// Load opens the .xlsx file at path and returns the populated Workbook.
// It is a convenience wrapper around LoadWorkbook that reads all sheets.
func Load(path string) (*Workbook, error) {
	return LoadWorkbook(path)
}

// Save writes the workbook to the given file path in .xlsx format.
func (wb *Workbook) Save(path string) error {
	return SaveWorkbook(wb, path)
}

// LoadWorkbook is the internal implementation Load delegates to.
func LoadWorkbook(path string) (*Workbook, error) {
	return nil, nil
}

// ExportToCSV exports the given sheet to a CSV file at path.
func (wb *Workbook) ExportToCSV(sheetIndex int, path string, delimiter rune) error {
	return nil
}

// ImportFromCSV reads a CSV file at path into a new sheet.
func (wb *Workbook) ImportFromCSV(path string, sheetName string, delimiter rune) error {
	return nil
}
"""


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def test_a_named_method_is_reported_declared_and_registered_in_its_own_direction(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "workbook.go", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["workbook.go"])

    csv = [d for d in decls if d.extension == ".csv"]
    assert any(d.kind == "declaration" for d in csv)
    assert any(d.kind == "registration" and d.direction == "output" for d in csv)
    assert any(d.kind == "registration" and d.direction == "input" for d in csv)


def test_a_bare_load_and_save_reads_the_extension_from_its_doc_comment(tmp_path: Path) -> None:
    _write(tmp_path, "workbook.go", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["workbook.go"])

    xlsx = [d for d in decls if d.extension == ".xlsx"]
    assert any(d.kind == "registration" and d.direction == "input" for d in xlsx)
    assert any(d.kind == "registration" and d.direction == "output" for d in xlsx)


def test_the_internal_loadworkbook_helper_is_not_mistaken_for_the_bare_load_method(
    tmp_path: Path,
) -> None:
    """LoadWorkbook is a prefix match of 'Load' but not an exact identifier -- it must not be
    read as a second bare Load statement (its own doc comment names no extension anyway)."""
    _write(tmp_path, "workbook.go", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["workbook.go"])
    xlsx_input = [d for d in decls if d.extension == ".xlsx" and d.direction == "input"]
    assert len(xlsx_input) == 1  # exactly one bare Load, not one per Load-prefixed identifier


def test_a_method_with_no_doc_comment_produces_no_finding(tmp_path: Path) -> None:
    source = "package p\n\nfunc Load(path string) (*Workbook, error) {\n\treturn nil, nil\n}\n"
    _write(tmp_path, "workbook.go", source)
    decls = format_declarations(tmp_path, ["workbook.go"])
    assert decls == []


def test_a_test_file_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "workbook_test.go", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["workbook_test.go"])
    assert decls == []


def test_files_outside_the_tree_paths_list_are_not_read(tmp_path: Path) -> None:
    _write(tmp_path, "workbook.go", _REAL_SHAPE)
    decls = format_declarations(tmp_path, [])
    assert decls == []
