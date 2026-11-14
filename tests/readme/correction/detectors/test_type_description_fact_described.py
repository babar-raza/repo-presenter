"""Version 4 of ``type_description`` (BL-005, owner feedback 536baa63f4): a cell that is only a
count, a label or bookkeeping, of a type with no usable doc comment, is replaced by what the facts
state about the type -- its bases, its members' names by kind, its enum values -- never by invented
purpose text, and the row stays (R14).

The shapes are the real ones of the sealed Aspose.3D FOSS for Java Lane L bundle (revision
3d2ed6be91f5): ``VertexElementPolygonGroup`` (whose inherited members' evidence points at
``VertexElement.java`` and ``VertexElementIntsTemplate.java``), ``RenderParameters`` (one
constructor, ``RenderParameters()``), ``PresetShaders`` (``DEFAULT``, ``CUSTOMIZED``,
``PresetShaders.java:3-6``, read from the pinned source as ``enum_values``), ``Stream`` (Javadoc
"Created by lexchou on 12/14/2016.") and ``IRenderTarget`` (``public interface IRenderTarget {}``).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.correction.apply import apply_edits
from repo_presenter.readme.correction.detectors.type_description import (
    NON_DESCRIPTIVE,
    TypeDescriber,
    cell_shape,
    fact_true_label_cells,
    type_description,
)

PACKAGE = "com.aspose.threed"


def _path(name: str) -> str:
    return f"src/main/java/com/aspose/threed/{name}.java"


def _type(name: str, kind: str = "class", docstring: str = "", **extra: str) -> Fact:
    attributes = {"symbol_kind": kind, **extra}
    if docstring:
        attributes["docstring"] = docstring
    return Fact(
        f"public_symbol:{PACKAGE}.{name}".lower(),
        "public_symbol",
        f"{PACKAGE}.{name}",
        (Evidence(_path(name), f"line 3; {kind}; public by declaration"),),
        attributes=attributes,
    )


def _member(owner: str, name: str, signature: str, declared_in: str | None = None) -> Fact:
    return Fact(
        f"public_symbol:{PACKAGE}.{owner}.{name}".lower(),
        "public_symbol",
        f"{PACKAGE}.{owner}.{name}",
        (Evidence(_path(declared_in or owner), "line 9; method; public by declaration"),),
        attributes={"symbol_kind": "method", "signature": signature},
    )


FACTS = (
    _type("VertexElement"),
    _member("VertexElement", "getReferenceMode", "ReferenceMode getReferenceMode()"),
    _type("VertexElementIntsTemplate"),
    _member("VertexElementIntsTemplate", "getReferenceMode", "ReferenceMode getReferenceMode()", "VertexElement"),
    _member("VertexElementIntsTemplate", "getData", "List<Integer> getData()"),
    _type("VertexElementPolygonGroup"),
    _member("VertexElementPolygonGroup", "getReferenceMode", "ReferenceMode getReferenceMode()", "VertexElement"),
    _member("VertexElementPolygonGroup", "getData", "List<Integer> getData()", "VertexElementIntsTemplate"),
    _member("VertexElementPolygonGroup", "VertexElementPolygonGroup", "VertexElementPolygonGroup()"),
    _member("VertexElementPolygonGroup", "clear", "void clear()"),
    _member("VertexElementPolygonGroup", "getVertexElementType", "VertexElementType getVertexElementType()"),
    _type("RenderParameters"),
    _member("RenderParameters", "RenderParameters", "RenderParameters()"),
    _type("Stream", docstring="Created by lexchou on 12/14/2016."),
    _member("Stream", "close", "void close()"),
    _member("Stream", "flush", "void flush()"),
    _type("IRenderTarget"),
    _type("PresetShaders", "enum", enum_values="DEFAULT,CUSTOMIZED"),
)

TABLE = (
    "| Class | Description |\n"
    "|---|---|\n"
    "| `RenderParameters` | Class with 1 method. |\n"
    "| `Stream` | Created by lexchou on 12/14/2016. |\n"
    "| `VertexElementPolygonGroup` | Class with 18 methods and 6 properties. |\n"
    "| `IRenderTarget` | Interface in the 3D JAVA API. |\n"
    "| `PresetShaders` | Enum with 2 members. |\n"
)


def test_the_owner_flagged_rows_become_fact_true_and_keep_their_rows(make_context: Any) -> None:
    ctx = make_context(TABLE, list(FACTS))
    result = type_description(ctx)
    corrected = apply_edits(TABLE, list(result.edits))[0]
    assert corrected.splitlines() == [
        "| Class | Description |",
        "|---|---|",
        "| `RenderParameters` | Class that declares a public no-argument constructor. |",
        "| `Stream` | Declares the methods close and flush. |",
        "| `VertexElementPolygonGroup` | Class that inherits from VertexElementIntsTemplate and "
        "declares the methods clear and getVertexElementType. |",
        "| `IRenderTarget` | Interface in the 3D JAVA API. |",
        "| `PresetShaders` | Enumerates CUSTOMIZED and DEFAULT. |",
    ]
    # Nothing to say about an empty interface beyond its name and kind: reported, never guessed.
    (finding,) = result.findings
    assert finding.text == "Interface in the 3D JAVA API." and finding.report_only_reason == "NO_DOC_COMMENT"
    for line in corrected.splitlines()[2:-2]:
        assert cell_shape(line.split("|")[2].strip()) not in NON_DESCRIPTIVE


def test_every_edit_cites_the_type_and_the_members_it_names(make_context: Any) -> None:
    ctx = make_context(TABLE, list(FACTS))
    by_original = {edit.original: edit for edit in type_description(ctx).edits}
    group = by_original["Class with 18 methods and 6 properties."]
    assert group.fact_ids[0] == f"public_symbol:{PACKAGE}.vertexelementpolygongroup"
    assert f"public_symbol:{PACKAGE}.vertexelementpolygongroup.clear" in group.fact_ids


def test_a_described_type_never_claims_a_kind_the_facts_contradict() -> None:
    document = FactsDocument("o/r", "a" * 40, (_type("IRenderTarget", type_kind="interface"),
                                                _member("IRenderTarget", "render", "void render()")))
    text, _ = TypeDescriber(document).describe(document.facts[0], "Class")
    assert text == "Interface that declares the method render."


def test_a_kept_lane_r_table_prints_the_same_fact_true_cells() -> None:
    document = FactsDocument("o/r", "a" * 40, FACTS)
    printed = fact_true_label_cells(TABLE, document)
    assert "| `RenderParameters` | Class that declares a public no-argument constructor. |" in printed
    assert "| `IRenderTarget` | Interface in the 3D JAVA API. |" in printed  # nothing true to say
    assert fact_true_label_cells(printed, document) == printed  # idempotent


def test_more_names_than_the_cap_read_including(make_context: Any) -> None:
    many = [_type("Vector3")] + [_member("Vector3", f"m{i}", f"void m{i}()") for i in range(9)]
    ctx = make_context("| `Vector3` | Class with 9 methods. |\n", many)
    (edit,) = type_description(replace(ctx)).edits
    assert edit.replacement == "Class that declares methods including m0, m1, m2, m3, m4 and m5."


def test_a_python_class_is_described_by_its_recorded_fields(make_context: Any) -> None:
    """Page Python ``AxialShading`` (``fields: color_space, coords, domain, function, extend``):
    its annotated fields are on the type fact, with no member fact of their own."""
    shading = Fact(
        "public_symbol:aspose.page.common.color_resources.axialshading",
        "public_symbol",
        "aspose.page.common.color_resources.AxialShading",
        (Evidence("src/aspose/page/common/color_resources.py", "line 171; class; public"),),
        attributes={
            "symbol_kind": "class",
            "signature": "class AxialShading",
            "fields": "color_space, coords, domain, function, extend",
        },
    )
    ctx = make_context("| `AxialShading` | Class with 5 properties. |\n", [shading])
    (edit,) = type_description(ctx).edits
    assert edit.replacement == (
        "Class that declares the fields color_space, coords, domain, function and extend."
    )
