"""BL-087 (supervisor decision 2026-11-14, audit O3 P1): a Core API row never prints the pipeline's analysis wording or a
findings-register quote; it prints the row's substance without the lead, or the fact-true
fallback.

Real data:
* hosted Lane R run 43525324808 (Aspose.HTML-FOSS-for-Python): twelve authored rows such as
  "NodeFilter class is a public symbol in aspose_html.dom." blocked BC-07 and no repair was tried;
* the sealed 3D .NET / Email .NET / Words .NET candidates: 89 rows such as
  "Aspose.ThreeD.Utilities.Matrix4 is a public symbol with members Concatenate, ..." whose member
  list is the substance 3D .NET ``054.table``'s supersession rests on (BC-05/BC-17);
* 3D .NET's ``Chunk`` docstring "Represents a 3DS chunk header.", an OPEN register row
  (``data/readme_findings.json``) the repair loop records as an unreachable "facts defect".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import render_readme, without_symbol_wording
from repo_presenter.readme.validation.public_text import analysis_markers
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _facts, _plan

THREED_NET = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
HTML_ROW = "NodeFilter class is a public symbol in aspose_html.dom."
MATRIX_ROW = (
    "Aspose.ThreeD.Utilities.Matrix4 is a public symbol with members Concatenate, Decompose, "
    "Determinant, Identity, Inverse, Matrix4, Normalize, and Rotate; "
    "Aspose.ThreeD.Utilities.Matrix4.Determinant always returns 1.0."
)
CFB_ROW = (
    "Aspose.Email.Foss.Cfb.CfbReader is a public symbol that exposes the constructors CfbReader, "
    "FromFile, FromStream, and the properties Difat, DirectoryEntries."
)
CHUNK_DOC = "Represents a 3DS chunk header."


@pytest.fixture(autouse=True)
def real_register(monkeypatch: pytest.MonkeyPatch) -> None:
    from repo_presenter.readme.validation import must_correct

    monkeypatch.setattr(
        must_correct,
        "DEFAULT_FINDINGS_PATH",
        Path(__file__).resolve().parents[3] / "data" / "readme_findings.json",
    )


def test_the_lead_goes_and_the_substance_stays() -> None:
    assert without_symbol_wording(HTML_ROW) == ""
    assert without_symbol_wording(MATRIX_ROW).startswith(
        "Has members Concatenate, Decompose, Determinant"
    )
    assert without_symbol_wording(CFB_ROW).startswith("Exposes the constructors CfbReader")
    for text in (MATRIX_ROW, CFB_ROW):
        assert not analysis_markers(without_symbol_wording(text))


def test_negative_control_a_plain_sentence_is_unchanged() -> None:
    text = "Body class gives the paragraphs and tables of a section body."
    assert without_symbol_wording(text) == text


def _type(fact_id: str, value: str, docstring: str = "") -> Fact:
    attributes: dict[str, Any] = {"symbol_kind": "class"}
    if docstring:
        attributes["docstring"] = docstring
    return Fact(
        fact_id, "public_symbol", value, (Evidence("src/Types.cs", "line 1; class"),),
        attributes=attributes,
    )


def _render(repository: str, extra: tuple[Fact, ...], type_units: dict[str, str]) -> str:
    base = _facts()
    facts = FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))
    units = {
        **UNITS,
        "units": [
            *UNITS["units"],
            *(
                {"section": "api_reference", "slot": f"type:{fid}", "text": text,
                 "fact_ids": [fid]}
                for fid, text in type_units.items()
            ),
        ],
    }
    entry = ENTRY.model_copy(update={"repository": repository})
    return render_readme(entry, facts, _plan(), units, _dispositions())


def test_internal_wording_rows_are_never_printed() -> None:
    node = _type("public_symbol:aspose.threed.nodefilter", "aspose.threed.NodeFilter")
    matrix = _type("public_symbol:aspose.threed.matrix4", "aspose.threed.Matrix4")
    body = _type("public_symbol:aspose.threed.body", "aspose.threed.Body")
    readme = _render(
        ENTRY.repository,
        (node, matrix, body),
        {node.id: HTML_ROW, matrix.id: MATRIX_ROW,
         body.id: "Body class gives the paragraphs and tables of a section body."},
    )
    assert not [line for line in analysis_markers(readme) if "public symbol" in line]
    assert "| `NodeFilter` | Public class. |" in readme
    assert "| `Matrix4` | Has members Concatenate, Decompose, Determinant" in readme
    # negative control: an authored sentence with no internal wording prints as written
    assert "| `Body` | Body class gives the paragraphs and tables of a section body. |" in readme


def test_a_register_refuted_docstring_row_prints_the_fallback() -> None:
    chunk = _type("public_symbol:aspose.threed.formats.chunk", "aspose.threed.Chunk", CHUNK_DOC)
    readme = _render(THREED_NET, (chunk,), {})
    assert "`Chunk` | Represents a 3DS chunk header. |" not in readme
    assert "| `Chunk` | Public class. |" in readme


def test_negative_control_another_repository_keeps_the_docstring() -> None:
    chunk = _type("public_symbol:aspose.threed.formats.chunk", "aspose.threed.Chunk", CHUNK_DOC)
    readme = _render(ENTRY.repository, (chunk,), {})
    assert "| `Chunk` | Represents a 3DS chunk header. |" in readme
