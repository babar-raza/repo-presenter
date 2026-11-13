"""BL-080: a Detailed Member Reference bullet the findings register confirms false is not printed.

Hosted Lane R run 43513037866 (Aspose.Cells-FOSS-for-.NET) failed on exactly one blocking check,
BC-18: "- `Save`: Saves the workbook to an XLSX file using default save options." The renderer
prints that bullet from ``public_symbol:aspose.cells_foss.workbook.save``'s doc comment, so the
repair loop recorded it as a facts defect no revision could reach. The register row (OPEN,
``data/readme_findings.json``) is the evidence: the renderer now omits the bullet, keeps every
other bullet, and BC-18 has nothing left to fail.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme_findings import LANE_R, regression_rows
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _facts, _plan

CELLS = "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET"
SAVE_DOC = "Saves the workbook to an XLSX file using default save options."
QUOTE = f"- `Save`: {SAVE_DOC}"


def _method(name: str, docstring: str) -> Fact:
    return Fact(
        f"public_symbol:aspose.threed.scene.{name.lower()}",
        "public_symbol",
        f"aspose.threed.Scene.{name}",
        (Evidence("src/Workbook.cs", "line 207; method; public by declaration"),),
        attributes={"symbol_kind": "method", "signature": f"{name}(string fileName)",
                    "docstring": docstring},
    )


def _with_members() -> FactsDocument:
    base = _facts()
    return FactsDocument(
        base.repository,
        base.source_revision,
        (*base.facts, _method("Save", SAVE_DOC), _method("Open", "Opens a workbook from a file.")),
    )


def _render(repository: str) -> str:
    entry = ENTRY.model_copy(update={"repository": repository})
    units: dict[str, Any] = UNITS
    return render_readme(entry, _with_members(), _plan(), units, _dispositions())


def test_the_real_register_row_is_open_for_cells_net() -> None:
    rows = regression_rows(CELLS, LANE_R)
    assert any(row.quote == QUOTE for row in rows)


def test_the_refuted_bullet_is_omitted_and_the_others_kept() -> None:
    readme = _render(CELLS)
    assert QUOTE not in readme
    assert "- `Open`: Opens a workbook from a file." in readme


def test_negative_control_another_repository_prints_the_bullet() -> None:
    readme = _render(ENTRY.repository)
    assert QUOTE in readme
