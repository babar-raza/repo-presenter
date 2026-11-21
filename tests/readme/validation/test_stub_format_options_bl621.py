"""BL-621: a type description whose first word is a verb ("Load options for FBX format.") is a noun phrase
naming a configuration class, not a claim that the format is loaded. The rows are the maintainers' own
docstrings, verbatim from the live README of aspose-3d-foss/Aspose.3D-FOSS-for-Java (README.md lines 291-292,
pinned source 3d2ed6be), where hosted Lane R run 44931307380 ended REJECT on exactly these two lines.
Negative controls: a real claim of the same format in the same table, with the same fact, still blocks."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.claims import claim_findings

REVISION = "b" * 40


def _fact(identifier: str, kind: str, value: str, polarity: str = "SUPPORTED", **attributes: str) -> Fact:
    return Fact(identifier, kind, value, (Evidence("src/x"),), polarity=polarity, attributes=attributes or None)  # type: ignore[arg-type]


FACTS = FactsDocument(
    "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
    REVISION,
    (
        _fact("package:name", "package", "Aspose.3D.FOSS"),
        _fact("format:input.fbx", "format", ".fbx", "UNRESOLVED", code_path="stub"),
        _fact("format:output.fbx", "format", ".fbx", "UNRESOLVED", code_path="stub"),
        _fact("format:input.obj", "format", ".obj"),
    ),
)


def _stub_findings(text: str) -> list:
    return [f for f in claim_findings(text + "\n", FACTS) if "reachable only through a stub" in f.detail]


def test_the_options_class_rows_of_the_maintainers_table_are_not_format_claims() -> None:
    assert not _stub_findings("| `FbxLoadOptions` | Load options for FBX format. |")
    assert not _stub_findings("| `FbxSaveOptions` | Save options for FBX format. |")
    assert not _stub_findings("| `ImportSettings` | Import settings for FBX files. |")


def test_a_real_claim_of_the_stub_format_still_blocks() -> None:
    assert _stub_findings("| `Scene` | Load FBX files into a scene. |")
    assert _stub_findings("The library can load options and open FBX files.")
    assert [f for f in _stub_findings("It saves scenes to `.fbx`.") if ".fbx output" in f.detail]
    assert _stub_findings("| `FbxLoader` | Loads FBX format scenes. |")
