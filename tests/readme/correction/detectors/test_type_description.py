"""An API table cell that does not describe its type is replaced by the type's own doc comment
summary, and reported when the source has none (``detectors.type_description``).

Every row and fact below is verbatim from a sealed bundle on the state remote:

* the owner's review of the Aspose.3D FOSS for Java Lane L candidate (revision 3d2ed6be,
  2026-11-13) named five rows "all wrong description" (``RenderParameters``,
  ``VertexElementPolygonGroup``, ``Stream``, ``IRenderTarget``, ``PresetShaders``) and four "good
  descriptions" (``RenderStage``, ``RvmLoadOptions``, "Segment of CompositeCurve.",
  ``ReferenceMode``). None of the five has a usable doc comment in the pinned
  source (``Stream``'s only Javadoc is "Created by lexchou on 12/14/2016."), so Lane L reports
  them and edits nothing; the four good ones are left exactly as written.
* Aspose.PDF FOSS for Python Lane L (revision 02b0c0e4): ``MarkdownSaveOptions`` reads "Class with
  1 method and 4 properties." while its docstring says "Options for saving PDF documents as
  Markdown." -- the one shape Lane L can verifiably correct.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.correction.apply import apply_edits
from repo_presenter.readme.correction.detectors.type_description import (
    NON_DESCRIPTIVE,
    SHAPE_BOOKKEEPING,
    SHAPE_COUNT,
    SHAPE_DOC,
    SHAPE_LABEL,
    SHAPE_OTHER,
    cell_shape,
    type_description,
)
from repo_presenter.readme.correction.model import FALSE_CLAIM_FIX
from repo_presenter.readme.correction.report import is_defect

JAVA_TABLE = (
    "### Core API\n"
    "\n"
    "| Class | Description |\n"
    "|---|---|\n"
    "| `RenderParameters` | Class with 1 method. |\n"
    "| `RenderStage` | RenderStage provides a default constructor to create a new rendering stage"
    " for custom rendering pipelines. |\n"
    "| `RvmLoadOptions` | Load options for AVEVA Plant Design Management System's RVM file. |\n"
    "| `Stream` | Created by lexchou on 12/14/2016. |\n"
    "| `VertexElementPolygonGroup` | Class with 18 methods and 6 properties. |\n"
    "\n"
    "#### Interfaces\n"
    "\n"
    "| Interface | Description |\n"
    "|---|---|\n"
    "| `IRenderTarget` | Interface in the 3D JAVA API. |\n"
    "\n"
    "#### Enumerations\n"
    "\n"
    "| Enumeration | Description |\n"
    "|---|---|\n"
    "| `PresetShaders` | Enum with 2 members. |\n"
    "| `ReferenceMode` | ReferenceMode enum defines how vertex attributes reference data,"
    " supporting DIRECT, INDEX_TO_DIRECT, and INDEX modes. |\n"
)


def _type(name: str, kind: str, line: int, docstring: str = "", package: str = "com.aspose.threed") -> Fact:
    attributes = {"symbol_kind": kind}
    if docstring:
        attributes["docstring"] = docstring
    path = "src/main/java/" + package.replace(".", "/") + f"/{name}.java"
    return Fact(
        f"public_symbol:{package}.{name}".lower(),
        "public_symbol",
        f"{package}.{name}",
        (Evidence(path, f"line {line}; {kind}; public by declaration"),),
        attributes=attributes,
    )


JAVA_TYPES = (
    _type("RenderParameters", "class", 3),
    _type("RenderStage", "class", 3),
    _type("RvmLoadOptions", "class", 9, "Load options for AVEVA Plant Design Management System's RVM file."),
    _type("Stream", "class", 8, "Created by lexchou on 12/14/2016."),
    _type("VertexElementPolygonGroup", "class", 3),
    # The extractor records IRenderTarget (``public interface IRenderTarget {}``) as a class.
    _type("IRenderTarget", "class", 3),
    _type("PresetShaders", "enum", 3),
    _type("ReferenceMode", "enum", 3),
)


def test_the_owner_flagged_java_rows_are_reported_and_the_good_rows_untouched(
    make_context: Any, make_facts: Any
) -> None:
    ctx = make_context(JAVA_TABLE, make_facts(*JAVA_TYPES))
    result = type_description(ctx)
    assert result.edits == ()  # no doc comment describes any of them: Lane L does not guess
    reported = {finding.text: finding for finding in result.findings}
    assert set(reported) == {
        "Class with 1 method.",
        "Created by lexchou on 12/14/2016.",
        "Class with 18 methods and 6 properties.",
        "Interface in the 3D JAVA API.",
        "Enum with 2 members.",
    }
    for finding in result.findings:
        assert finding.report_only_reason == "NO_DOC_COMMENT"
        assert not is_defect(finding)  # Lane R's to author; never blocks a Lane L seal


PDF_ROW = (
    "| Class | Description |\n"
    "|---|---|\n"
    "| `MarkdownSaveOptions` | Class with 1 method and 4 properties. |\n"
    "| `PdfConsts` | Class with 2 methods. |\n"
)
MARKDOWN_OPTIONS = Fact(
    "public_symbol:aspose_pdf.markdown.markdownsaveoptions",
    "public_symbol",
    "aspose_pdf.markdown.MarkdownSaveOptions",
    (Evidence("aspose_pdf/markdown/__init__.py", "line 12; class; public by declaration"),),
    attributes={
        "symbol_kind": "class",
        "signature": "class MarkdownSaveOptions",
        "docstring": "Options for saving PDF documents as Markdown.",
    },
)
PDF_CONSTS = Fact(
    "public_symbol:aspose_pdf.pdfconsts",
    "public_symbol",
    "aspose_pdf.PdfConsts",
    (Evidence("aspose_pdf/consts.py", "line 3; class; public by declaration"),),
    attributes={"symbol_kind": "class", "signature": "class PdfConsts"},
)


def test_a_count_cell_of_a_documented_type_becomes_its_doc_comment_summary(
    make_context: Any, make_facts: Any
) -> None:
    ctx = make_context(PDF_ROW, make_facts(MARKDOWN_OPTIONS, PDF_CONSTS))
    result = type_description(ctx)
    (edit,) = result.edits
    assert edit.kind == FALSE_CLAIM_FIX
    assert edit.original == "Class with 1 method and 4 properties."
    assert edit.replacement == "Options for saving PDF documents as Markdown."
    assert edit.fact_ids == (MARKDOWN_OPTIONS.id,)
    corrected, _ = apply_edits(PDF_ROW, list(result.edits))
    assert corrected == PDF_ROW.replace(
        "Class with 1 method and 4 properties.", "Options for saving PDF documents as Markdown."
    )
    (finding,) = result.findings  # PdfConsts has no doc comment
    assert finding.text == "Class with 2 methods."
    # Idempotent: the corrected cell is the doc comment, which is never edited again.
    again = type_description(make_context(corrected, make_facts(MARKDOWN_OPTIONS, PDF_CONSTS)))
    assert again.edits == ()


def test_shapes_of_the_real_rows() -> None:
    assert cell_shape("Class with 1 method.") == SHAPE_COUNT
    assert cell_shape("Class with 18 methods and 6 properties.") == SHAPE_COUNT
    assert cell_shape("Enum with 14 methods and 5 members.") == SHAPE_COUNT
    assert cell_shape("Interface in the 3D JAVA API.") == SHAPE_LABEL
    assert cell_shape("Class in the Cells TYPESCRIPT API.") == SHAPE_LABEL
    assert (
        cell_shape(
            "Aspose.ThreeD.Animation.KeyFrame is a public symbol with members Bias, Continuity."
        )
        == SHAPE_LABEL
    )
    assert cell_shape("Created by lexchou on 12/14/2016.") == SHAPE_BOOKKEEPING
    assert {SHAPE_COUNT, SHAPE_LABEL, SHAPE_BOOKKEEPING} == NON_DESCRIPTIVE
    # The owner's four good descriptions are never non-descriptive.
    for good in (
        (
            "RenderStage provides a default constructor to create a new rendering stage for "
            "custom rendering pipelines."
        ),
        "Segment of CompositeCurve.",
        (
            "ReferenceMode enum defines how vertex attributes reference data, supporting DIRECT, "
            "INDEX_TO_DIRECT, and INDEX modes."
        ),
    ):
        assert cell_shape(good) == SHAPE_OTHER
    rvm = "Load options for AVEVA Plant Design Management System's RVM file."
    assert cell_shape(rvm, rvm) == SHAPE_DOC


def test_a_name_two_documented_types_share_is_left_alone(make_context: Any, make_facts: Any) -> None:
    twin = Fact(
        "public_symbol:aspose_pdf.other.markdownsaveoptions",
        "public_symbol",
        "aspose_pdf.other.MarkdownSaveOptions",
        (Evidence("aspose_pdf/other.py", "line 3; class; public by declaration"),),
        attributes={"symbol_kind": "class", "docstring": "Something else entirely."},
    )
    ctx = make_context(PDF_ROW, make_facts(MARKDOWN_OPTIONS, twin, PDF_CONSTS))
    result = type_description(ctx)
    assert result.edits == ()
    assert [finding.text for finding in result.findings] == ["Class with 2 methods."]
