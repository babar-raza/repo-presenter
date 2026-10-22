"""New engineering, not a port (the old repo never built this for TypeScript). Tested against
the exact real shapes measured live in aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript's own
source (2026-10-22): a string-valued ``SaveFormat`` enum, a ``detectFormat()`` helper that
references every member but performs no I/O, and the real ``save()``/``load()`` dispatch that
only wires up a subset of what's declared."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.extractors.platforms.typescript_format_declarations import (
    format_declarations,
)

_REAL_SHAPE = """
export enum SaveFormat {
  XLSX = "xlsx",
  CSV = "csv",
  JSON = "json",
  MARKDOWN = "markdown",
  HTML = "html",
}

export class Workbook {
  static async load(filePath: string, password?: string): Promise<Workbook> {
    const workbook = new Workbook(false);
    const ext = filePath.toLowerCase().split(".").pop();
    if (ext === "html" || ext === "htm") {
      const htmlDoc = await HtmlDocument.load(filePath);
      return workbook;
    }
    await workbook.loadFile(filePath);
    return workbook;
  }

  async save(
    filePath: string,
    options?: { password?: string; saveFormat?: SaveFormat },
  ) {
    const format = options?.saveFormat || this.detectFormat(filePath);
    if (format === SaveFormat.HTML) {
      const exporter = new HtmlExporter(this);
      return;
    }
    const zip = await createZipWriter();
    await this.writeToZip(zip, options);
  }

  private detectFormat(filePath: string): SaveFormat {
    const ext = filePath.toLowerCase().split(".").pop();
    if (ext === "html" || ext === "htm") return SaveFormat.HTML;
    if (ext === "csv") return SaveFormat.CSV;
    if (ext === "json") return SaveFormat.JSON;
    if (ext === "md" || ext === "markdown") return SaveFormat.MARKDOWN;
    return SaveFormat.XLSX;
  }

  toCsv(): string {
    return "";
  }
}
"""


def _write(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")


def test_html_is_declared_and_registered_both_directions(tmp_path: Path) -> None:
    _write(tmp_path, "workbook.ts", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["workbook.ts"])

    html = [d for d in decls if d.extension == ".html"]
    assert any(d.kind == "declaration" for d in html)
    assert any(d.kind == "registration" and d.direction == "output" for d in html)
    assert any(d.kind == "registration" and d.direction == "input" for d in html)


def test_detectformat_referencing_csv_does_not_count_as_registration(tmp_path: Path) -> None:
    """The exact real bug this reader exists to surface: detectFormat() references
    SaveFormat.CSV/JSON/MARKDOWN, but save()'s own body never checks for them -- they must come
    out declared-only, not falsely corroborated by the unrelated detectFormat() reference."""
    _write(tmp_path, "workbook.ts", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["workbook.ts"])

    for extension in (".csv", ".json", ".markdown"):
        matching = [d for d in decls if d.extension == extension]
        assert len(matching) == 1, (extension, matching)
        assert matching[0].kind == "declaration"


def test_xlsx_the_implicit_fallthrough_default_is_declared_only(tmp_path: Path) -> None:
    """XLSX is the generic ZIP-writer fallthrough in both save() and load() -- never an
    explicit SaveFormat.XLSX or "xlsx" comparison -- so this reader honestly reports it as
    declared-only, the same limitation already stated for the C++/Go readers."""
    _write(tmp_path, "workbook.ts", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["workbook.ts"])

    xlsx = [d for d in decls if d.extension == ".xlsx"]
    assert len(xlsx) == 1
    assert xlsx[0].kind == "declaration"


def test_files_outside_the_tree_paths_list_are_not_read(tmp_path: Path) -> None:
    _write(tmp_path, "workbook.ts", _REAL_SHAPE)
    decls = format_declarations(tmp_path, [])
    assert decls == []


def test_a_non_typescript_file_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "workbook.txt", _REAL_SHAPE)
    decls = format_declarations(tmp_path, ["workbook.txt"])
    assert decls == []
