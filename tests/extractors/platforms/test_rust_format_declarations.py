"""New engineering, not a port (the old repo never built this for Rust). Tested against the
exact real shapes measured live in aspose-cells-foss/Aspose.Cells-FOSS-for-Rust's own source
(2026-10-22): a ``#[derive(...)]``-decorated ``pub enum LoadFormat``/``SaveFormat`` with a
``#[default]`` sentinel variant, and an exhaustive ``match`` as the real registration signal."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.extractors.platforms.rust_format_declarations import format_declarations

_ENUMS = """
#[derive(Debug, Default, Clone, PartialEq)]
/// Specifies load format.
pub enum LoadFormat {
    #[default]
    Auto,
    Xlsx,
    Csv,
}

#[derive(Debug, Default, Clone, PartialEq)]
/// Specifies save format.
pub enum SaveFormat {
    #[default]
    Xlsx,
}
"""

_WORKBOOK = """
use super::*;

impl Workbook {
    fn ensure_supported_load_format(options: &LoadOptions) -> Result<(), CellsError> {
        match options.load_format {
            LoadFormat::Auto | LoadFormat::Xlsx => Ok(()),
        }
    }

    fn ensure_supported_save_format(options: &SaveOptions) -> Result<(), CellsError> {
        match options.save_format {
            SaveFormat::Xlsx => Ok(()),
        }
    }
}
"""


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def test_a_declared_and_referenced_member_is_reported_both_declared_and_registered(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "LoadFormat.rs", _ENUMS)
    _write(tmp_path, "Workbook.rs", _WORKBOOK)
    decls = format_declarations(tmp_path, ["LoadFormat.rs", "Workbook.rs"])

    xlsx = [d for d in decls if d.extension == ".xlsx"]
    assert any(d.kind == "declaration" for d in xlsx)
    assert any(d.kind == "registration" and d.direction == "input" for d in xlsx)
    assert any(d.kind == "registration" and d.direction == "output" for d in xlsx)


def test_a_declared_but_never_referenced_member_is_declared_only(tmp_path: Path) -> None:
    """Csv is declared in the LoadFormat enum but the real gate's match arm only names
    Auto/Xlsx explicitly -- declared without registration, so format_facts() will mark it
    UNRESOLVED, never SUPPORTED."""
    _write(tmp_path, "LoadFormat.rs", _ENUMS)
    _write(tmp_path, "Workbook.rs", _WORKBOOK)
    decls = format_declarations(tmp_path, ["LoadFormat.rs", "Workbook.rs"])

    csv = [d for d in decls if d.extension == ".csv"]
    assert len(csv) == 1
    assert csv[0].kind == "declaration"


def test_the_default_attribute_sentinel_is_not_treated_as_a_format(tmp_path: Path) -> None:
    """`#[default]` decorates the Auto variant; 'default' itself must never be read as a
    second declared format, and Auto is excluded as a sentinel."""
    _write(tmp_path, "LoadFormat.rs", _ENUMS)
    decls = format_declarations(tmp_path, ["LoadFormat.rs"])
    assert not any(d.extension in (".auto", ".default") for d in decls)


def test_files_outside_the_tree_paths_list_are_not_read(tmp_path: Path) -> None:
    _write(tmp_path, "LoadFormat.rs", _ENUMS)
    decls = format_declarations(tmp_path, [])
    assert decls == []


def test_a_non_rust_file_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "LoadFormat.txt", _ENUMS)
    decls = format_declarations(tmp_path, ["LoadFormat.txt"])
    assert decls == []
