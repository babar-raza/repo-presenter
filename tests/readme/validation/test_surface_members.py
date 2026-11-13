"""BC-14 rules (n)/(o) and the listed-count part of (h): BL-063 (K03), BL-064 (K04), BL-065 (K05).

Every README line below is verbatim from a sealed Lane R candidate the 2026-11-13 false-claim review
registered in ``data/readme_findings.json`` (``docs/investigations/2026-11-13-lane-r-false-claim-
review.md``), and every fact shape is the sealed facts' own (``symbol_kind`` "method" for every member,
``declaration`` on types) or the extractor-7 shape (``member_kind``/``settable``/``type_kind``). A
statement the facts cannot decide is never a finding: the controls at the end are true sentences and
sentences about members the facts do not classify.
"""

from __future__ import annotations

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import (
    _member_summary,  # noqa: F401 (import check)
)
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.surface_claims import caller_true_summary

REVISION = "b" * 40


def _type(value: str, kind: str = "class", **attributes: str) -> Fact:
    return Fact(
        f"public_symbol:{value.lower()}",
        "public_symbol",
        value,
        (Evidence("src/x.cs", f"line 1; {kind}; public by declaration"),),
        attributes={"symbol_kind": kind, **attributes},
    )


def _member(value: str, **attributes: str) -> Fact:
    return Fact(
        f"public_symbol:{value.lower()}",
        "public_symbol",
        value,
        (Evidence("src/x.cs", "line 2; method; public by declaration"),),
        attributes={"symbol_kind": "method", **attributes},
    )


def _facts(ecosystem: str, *symbols: Fact) -> FactsDocument:
    return FactsDocument(
        "org/repo",
        REVISION,
        (Fact("identity:ecosystem", "identity", ecosystem, (Evidence("registry"),)), *symbols),
    )


def _details(readme: str, facts: FactsDocument) -> list[str]:
    return [finding.detail for finding in claim_findings(readme, facts)]


# --- Cells .NET (269b6ae5d8f7): Style, Font, Color, FillPattern ---------------------------------

CELLS = (
    _type("Aspose.Cells_FOSS.Style", declaration="public class Style"),
    _type("Aspose.Cells_FOSS.Font", declaration="public class Font"),
    _type("Aspose.Cells_FOSS.Borders", declaration="public class Borders"),
    _type("Aspose.Cells_FOSS.Color", declaration="public struct Color : IEquatable<Color>"),
    _type("Aspose.Cells_FOSS.FillPattern", "enum", declaration="public enum FillPattern"),
    _type("Aspose.Cells_FOSS.Workbook", declaration="public class Workbook"),
    _member("Aspose.Cells_FOSS.Style.Font", signature="Font",
            docstring="Gets or sets the font settings."),
    _member("Aspose.Cells_FOSS.Style.Borders", signature="Borders",
            docstring="Gets or sets border settings."),
    _member("Aspose.Cells_FOSS.Style.Pattern", signature="FillPattern"),
    _member("Aspose.Cells_FOSS.Style.ForegroundColor", signature="Color"),
)
CELLS_7 = tuple(
    Fact(f.id, f.kind, f.value, f.evidence, attributes={
        **(f.attributes or {}),
        **({"member_kind": "property", "settable": "false"}
           if f.value.endswith((".Style.Font", ".Style.Borders")) else {}),
        **({"member_kind": "property", "settable": "true"}
           if f.value.endswith((".Style.Pattern", ".Style.ForegroundColor")) else {}),
    })
    for f in CELLS
)


def test_k04_properties_such_as_names_members_style_lacks() -> None:
    line = (
        "The `Style` class enables formatting of cells through properties such as `Font`, "
        "`Color`, `FillPattern`, and `Border`, allowing consistent styling across spreadsheet "
        "content."
    )
    details = _details(f"## API Reference\n\n{line}\n", _facts("net", *CELLS))
    assert sum("as a property of `Style`" in d for d in details) == 3  # Color, FillPattern, Border
    assert not any("`Font` as a property" in d for d in details)


def test_k03_a_struct_and_an_enum_are_not_classes_in_dotnet() -> None:
    line = (
        "- **Apply rich cell styling.** It applies rich cell styling through the "
        "`Aspose.Cells_FOSS.Style`, `Font`, `Color`, `FillPattern`, and `Border` classes."
    )
    details = _details(f"## Key Capabilities\n\n{line}\n", _facts("net", *CELLS))
    assert any("`Color` a class" in d and "struct" in d for d in details)
    assert any("`FillPattern` a class" in d and "enum" in d for d in details)
    assert not any("`Font` a class" in d for d in details)


def test_k03_gets_or_sets_on_a_private_setter_is_a_finding_and_the_renderer_says_gets() -> None:
    readme = (
        "## API Reference\n\n### Style\n\nStyle formats cells.\n\n"
        "- `Borders`: Gets or sets border settings.\n"
        "- `Font`: Gets or sets the font settings.\n"
        "- `Pattern`: Gets or sets the fill pattern.\n"
    )
    details = _details(readme, _facts("net", *CELLS_7))
    assert sorted(d.split("`")[1] for d in details if "'Gets or sets'" in d) == [
        "Style.Borders",
        "Style.Font",
    ]
    # Facts sealed before settable existed decide nothing.
    assert not any("'Gets or sets'" in d for d in _details(readme, _facts("net", *CELLS)))
    borders = next(f for f in CELLS_7 if f.value.endswith(".Style.Borders"))
    pattern = next(f for f in CELLS_7 if f.value.endswith(".Style.Pattern"))
    assert caller_true_summary("Gets or sets border settings.", borders) == "Gets border settings."
    assert caller_true_summary("Gets or sets the fill.", pattern) == "Gets or sets the fill."


# --- Email .NET (e8cc8cca4d3a) --------------------------------------------------------------------

EMAIL_SEALED = (
    _type("Aspose.Email.Foss.Msg.MapiMessage"),
    _member("Aspose.Email.Foss.Msg.MapiMessage.Attachments", signature="IList<MapiAttachment>"),
    _member("Aspose.Email.Foss.Msg.MapiMessage.Body", signature="string"),
    _member("Aspose.Email.Foss.Msg.MapiMessage.AddAttachment", signature="AddAttachment(string name)"),
    _member("Aspose.Email.Foss.Msg.MapiMessage.AttachMethodByValue", signature="int"),
    _member("Aspose.Email.Foss.Msg.MapiMessage.AttachMethodStorage", signature="int"),
    _type("Aspose.Email.Foss.Cfb.CfbStorage"),
    _member("Aspose.Email.Foss.Cfb.CfbStorage.AddStorage", signature="AddStorage(string name)"),
    _member("Aspose.Email.Foss.Cfb.CfbStorage.Children", signature="IList<CfbNode>"),
    _type("Aspose.Email.Foss.Cfb.CfbDocument"),
    _member("Aspose.Email.Foss.Cfb.CfbDocument.CfbDocument", signature="CfbDocument()"),
    _member("Aspose.Email.Foss.Cfb.CfbDocument.FromFile", signature="FromFile(string path)"),
    _type("Aspose.Email.Foss.Cfb.DirectoryEntry"),
    _member("Aspose.Email.Foss.Cfb.DirectoryEntry.IsRoot", signature="IsRoot()"),
)
EMAIL_7 = tuple(
    Fact(f.id, f.kind, f.value, f.evidence, attributes={
        **(f.attributes or {}),
        **({"member_kind": kind} if (kind := {
            "AttachMethodByValue": "constant", "AttachMethodStorage": "constant",
            "Children": "property", "Attachments": "property", "Body": "property",
            "CfbDocument": "constructor", "FromFile": "method", "IsRoot": "method",
            "AddAttachment": "method", "AddStorage": "method",
        }.get(f.value.rsplit(".", 1)[-1])) and (f.attributes or {}).get("symbol_kind") == "method"
           else {}),
    })
    for f in EMAIL_SEALED
)
EMAIL_ROWS = (
    "| Class | Description |\n| --- | --- |\n"
    "| `CfbDocument` | Aspose.Email.Foss.Cfb.CfbDocument is a public symbol that exposes the "
    "constructors CfbDocument, FromFile. |\n"
    "| `CfbStorage` | Aspose.Email.Foss.Cfb.CfbStorage is a public symbol that exposes the methods "
    "AddStorage, and Children. |\n"
    "| `DirectoryEntry` | Aspose.Email.Foss.Cfb.DirectoryEntry is a public symbol that exposes the "
    "properties IsRoot. |\n"
    "| `MapiMessage` | Aspose.Email.Foss.Msg.MapiMessage is a public symbol that exposes the "
    "properties Attachments and Body, and the methods AddAttachment, AttachMethodByValue, and "
    "AttachMethodStorage. |\n"
)


def test_k03_a_constant_and_a_get_only_property_are_not_methods_even_in_sealed_facts() -> None:
    details = _details(f"## API Reference\n\n{EMAIL_ROWS}", _facts("net", *EMAIL_SEALED))
    named = sorted(d.split("`")[1] for d in details if " a method " in d)
    assert named == [
        "CfbStorage.Children",
        "MapiMessage.AttachMethodByValue",
        "MapiMessage.AttachMethodStorage",
    ]
    # A signature with a parameter list does not say "method" in sealed facts (a Python property
    # reads that way too): IsRoot and FromFile are decided only by extractor-7 facts.
    assert not any("IsRoot" in d or "FromFile" in d for d in details)


def test_k03_a_static_factory_is_not_a_constructor_and_a_method_not_a_property() -> None:
    details = _details(f"## API Reference\n\n{EMAIL_ROWS}", _facts("net", *EMAIL_7))
    assert any("`CfbDocument.FromFile` a constructor" in d for d in details)
    assert any("`DirectoryEntry.IsRoot` a property" in d for d in details)
    assert not any("`CfbDocument.CfbDocument`" in d for d in details)
    assert not any(d.split("`")[1] in ("MapiMessage.Attachments", "MapiMessage.Body") for d in details)
    assert len(details) == 5


# --- 3D .NET (03b940a46f7b): cross-bound namesakes and a member no type has ----------------------

THREED_NET = (
    _type("Aspose.ThreeD.Property", declaration="public abstract class Property"),
    _member("Aspose.ThreeD.Property.GetExtra", signature="GetExtra(string name)"),
    _member("Aspose.ThreeD.Property.SetExtra", signature="SetExtra(string name, object value)"),
    _member("Aspose.ThreeD.Property.GetBindPoint", signature="GetBindPoint(AnimationNode anim)"),
    _type("Aspose.ThreeD.Formats.GLTF.Property", declaration="public class Property"),
    _member("Aspose.ThreeD.Formats.GLTF.Property.Name", signature="string"),
    _member("Aspose.ThreeD.Formats.GLTF.Property.Description", signature="string"),
    _type("Aspose.ThreeD.Entities.VertexElementTangent",
          declaration="public class VertexElementTangent : VertexElementFVector"),
    _type("Aspose.ThreeD.Entities.VertexElementFVector",
          declaration="public class VertexElementFVector : VertexElement"),
    _member("Aspose.ThreeD.Entities.VertexElementFVector.Data", signature="IList<FVector4>"),
    _member("Aspose.ThreeD.Entities.VertexElementFVector.SetData", signature="SetData(FVector4[] data)"),
    _type("Aspose.ThreeD.Scene", declaration="public class Scene"),
)
THREED_TABLE = (
    "| Class | Description |\n|---|---|\n"
    "| `Scene` | The root of a 3D document. |\n"
    "| `Property-GLTF` | Exposes `GetExtra`/`SetExtra` for arbitrary user data and `GetBindPoint` "
    "for animation bind points. |\n"
    "| `VertexElementTangent` | Per-vertex tangent data, exposed via `Tangents`. |\n"
    "| `VertexElementFVector` | Vertex data read through `Data` and written by `SetData()`. |\n"
)


def test_k04_members_of_a_namesake_and_an_unknown_member_are_findings() -> None:
    details = _details(f"## API Reference\n\n{THREED_TABLE}", _facts("net", *THREED_NET))
    cross = [d for d in details if "not of `Aspose.ThreeD.Formats.GLTF.Property`" in d]
    # "Exposes `GetExtra`/`SetExtra`" claims membership; "... and `GetBindPoint` for ..." follows a
    # phrase, not a joiner, so it is a mention the rule leaves alone (the row is caught either way).
    assert sorted(d.split("`")[3] for d in cross) == ["GetExtra", "SetExtra"]
    assert any("`Tangents`, which no fact states" in d for d in details)
    # Inherited members are the type's own (VertexElementTangent : VertexElementFVector).
    assert not any("VertexElementFVector`" in d and "`Data`" in d for d in details)
    assert len(details) == 3


def test_k04_spans_a_row_only_mentions_are_not_held_to_its_members() -> None:
    """Aspose.PDF .NET Lane L seal 847bbde01f5f (R10 gate, 2026-11-13): tag names, an exception the
    row says is thrown, a nested type and an extension method are mentions, not members."""
    facts = _facts(
        "net",
        _type("Aspose.Pdf.LogicalStructure.TableTRElement", declaration="public class TableTRElement"),
        _member("Aspose.Pdf.LogicalStructure.TableTRElement.AppendChild", signature="AppendChild(Element e)"),
        _type("Aspose.Pdf.LogicalStructure.StructureTypeStandard",
              declaration="public static class StructureTypeStandard"),
        _member("Aspose.Pdf.LogicalStructure.StructureTypeStandard.TR", signature="StructureType"),
        _member("Aspose.Pdf.LogicalStructure.StructureTypeStandard.TD", signature="StructureType"),
        _type("Aspose.Pdf.Annotations.Measure", declaration="public class Measure"),
        _member("Aspose.Pdf.Annotations.Measure.Scale", signature="string"),
        _type("Aspose.Pdf.Annotations.Measure.NumberFormatList", declaration="public class NumberFormatList"),
        _member("Aspose.Pdf.Annotations.Measure.NumberFormatList.Add", signature="Add(NumberFormat f)"),
        _type("Aspose.Pdf.DocumentCollection", declaration="public class DocumentCollection"),
        _member("Aspose.Pdf.DocumentCollection.Count", signature="int"),
    )
    table = (
        "| Class | Description |\n|---|---|\n"
        "| `TableTRElement` | A table row (`TR`) element holding `TD` and `TH` cells. |\n"
        "| `NumberFormatList` | The `Measure.NumberFormatList` of a measure. |\n"
        "| `DocumentCollection` | Its `Add` throws `NotImplementedException`. |\n"
    )
    details = _details(f"## API Reference\n\n{table}", facts)
    # Only the span the row says the type has ("Its `Add`") is judged: Add belongs to another type.
    assert len(details) == 1 and "names `Add`, a member of `Aspose.Pdf.Annotations" in details[0]


# --- 3D Python (4812255e83c2): read-only properties, a wrong base ---------------------------------

THREED_PY = (
    _type("aspose.threed.GlobalTransform", signature="class GlobalTransform"),
    *(
        _member(f"aspose.threed.GlobalTransform.{name}", signature=f"def {name}(self) -> Vector3",
                member_kind="property", settable="false")
        for name in ("translation", "scale", "euler_angles", "rotation", "transform_matrix")
    ),
    _type("aspose.threed.Entity", signature="class Entity(SceneObject)"),
    _type("aspose.threed.SceneObject", signature="class SceneObject(A3DObject)"),
    _type("aspose.threed.A3DObject", signature="class A3DObject"),
    _type("aspose.threed.entities.Geometry", signature="class Geometry(Entity)"),
    _type("aspose.threed.entities.Mesh", signature="class Mesh(Geometry)"),
)


def test_k03_read_only_properties_offered_for_direct_manipulation() -> None:
    row = (
        "| Class | Description |\n|---|---|\n| `GlobalTransform` | The GlobalTransform class exposes "
        "translation, scale, euler_angles, rotation, and transform_matrix properties for direct "
        "manipulation of an entity's world transform. |\n"
    )
    details = _details(f"## API Reference\n\n{row}", _facts("python", *THREED_PY))
    assert any("read-only members of `GlobalTransform`" in d for d in details)
    # Saying what they are, without offering them for assignment, is true.
    honest = row.replace(" for direct manipulation of", " that read")
    assert _details(f"## API Reference\n\n{honest}", _facts("python", *THREED_PY)) == []


@pytest.mark.parametrize(
    "sentence",
    [
        (
            "The `Scene` class serves as the root container, where each `Node` holds a "
            "`Transform`, optional `Mesh`-derived `Entity`, and materials."
        ),
        (
            "`Scene` instances contain a hierarchy of `Node` objects, each with a `Transform`, "
            "optional `Mesh`-derived entities, and materials."
        ),
    ],
)
def test_k04_a_base_the_type_does_not_derive_from(sentence: str) -> None:
    details = _details(f"## API Reference\n\n{sentence}\n", _facts("python", *THREED_PY))
    assert any("`Entity` derives from `Mesh`" in d for d in details)


def test_k04_a_true_base_is_not_a_finding() -> None:
    sentence = "Every `Entity`-derived `Mesh` is attached to a node."
    assert _details(f"## API Reference\n\n{sentence}\n", _facts("python", *THREED_PY)) == []


# --- Cells C++ (e6583bda4b1c): a count said to be listed over fewer rows (K05) --------------------


def _cpp_types(count: int) -> tuple[Fact, ...]:
    return tuple(_type(f"Aspose.Cells_FOSS.T{i}") for i in range(count))


def test_k05_a_count_said_to_be_listed_must_match_the_rows_listed() -> None:
    rows = "".join(f"| `T{i}` | Represents t{i}. |\n" for i in range(4))
    readme = (
        "## API Reference\n\nThe library's public types live in the `Aspose::Cells_FOSS` namespace. "
        "The\nfull public surface — 6 public types — is listed below, grouped exactly as\n"
        "`reference.aspose.org` organizes them.\n\n| Class | Description |\n|---|---|\n"
        f"{rows}\n## Documentation & Resources\n\n| `T5` | outside the section |\n"
    )
    details = _details(readme, _facts("cpp", *_cpp_types(6)))
    assert any("the table rows that follow list only 4" in d for d in details)
    full = readme.replace(rows, rows + "| `T4` | t4 |\n| `T5` | t5 |\n")
    assert not any("rows that follow" in d for d in _details(full, _facts("cpp", *_cpp_types(6))))


# --- controls: nothing the facts cannot decide is a finding ---------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        # The methods/properties named are what the facts say.
        (
            "| Class | Description |\n|---|---|\n| `MapiMessage` | Exposes the properties "
            "Attachments and Body and the method AddAttachment. |\n| `CfbStorage` | x |\n"
            "| `CfbDocument` | y |\n"
        ),
        # Types named by a domain word, not as members.
        "The `MapiMessage` class handles the CfbStorage and CfbDocument fields of a message.",
        # Plain English after a kind word.
        "The methods and properties of `MapiMessage` are listed in the reference.",
    ],
)
def test_controls_true_or_undecidable_statements_pass(line: str) -> None:
    assert _details(f"## API Reference\n\n{line}\n", _facts("net", *EMAIL_7)) == []


def test_python_attributes_the_surface_does_not_record_are_not_missing_members() -> None:
    line = "The `GlobalTransform` class keeps the properties `owner_node` and `scale`."
    assert _details(f"## API Reference\n\n{line}\n", _facts("python", *THREED_PY)) == []


def test_acronyms_and_python_attributes_are_not_missing_members() -> None:
    """R10 gate, 2026-11-13: Aspose.Email C++ Lane R ("... attachments, and MAPI properties",
    "keyed by (property ID, property type)") and Aspose.Note Python Lane R ("it provides
    DisplayName, FileFormat, GetPageHistory(), and Save() methods": DisplayName is an instance
    attribute the Python surface does not record) printed no missing member."""
    email = _facts(
        "cpp",
        _type("aspose.email.foss.msg.mapi_message", declaration="class mapi_message"),
        _member("aspose.email.foss.msg.mapi_message.subject", signature="subject()"),
    )
    row = (
        "| Class | Description |\n|---|---|\n| `mapi_message` | Mutable high-level MSG object, "
        "with subject/body, recipients, attachments, and MAPI properties; keyed by (property ID, "
        "property type). |\n"
    )
    assert _details(f"## API Reference\n\n{row}", email) == []
    note = _facts(
        "python",
        _type("aspose.note.Document", signature="class Document(CompositeNode)"),
        _member("aspose.note.Document.Save", signature="def Save(self, target)",
                member_kind="method"),
    )
    sentence = (
        "The aspose.note.Document class loads a .one file; it provides DisplayName, FileFormat, "
        "GetPageHistory(), and Save() methods."
    )
    assert _details(f"## API Reference\n\n{sentence}\n", note) == []
