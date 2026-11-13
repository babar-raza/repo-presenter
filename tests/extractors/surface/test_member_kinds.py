"""BL-063 (K03) and BL-065 (K05): the surface facts say what a member is and whether a type is public.

Every source shape below is the real one from the 2026-11-13 Lane R false-claim review
(``docs/investigations/2026-11-13-lane-r-false-claim-review.md``, register rows in
``data/readme_findings.json``):

* Cells .NET ``Style.Font``/``Borders`` are ``{ get; private set; }`` (Style.cs:68,73@f71fe559) and
  were printed "Gets or sets"; ``Color`` is a struct and ``FillPattern`` an enum (Color.cs:11,
  FillPattern.cs:9), called "classes".
* Email .NET ``MapiMessage.AttachMethodByValue`` is a ``public const int`` (MapiMessage.cs:52),
  ``CfbDocument.FromFile`` a static factory (CfbDocument.cs:37), ``DirectoryEntry.IsRoot()`` a method,
  ``CfbStorage.Children`` a get-only property -- all emitted as "method" with no further kind.
* Words .NET ``DocumentPositionMovement``/``INodeCollection``/``NodeEnumerator`` are ``public`` only
  under ``#if CPLUSPLUS`` (DocumentPositionMovement.cs:9-14@0d3f1add): 618 public types instead of 615.
* 3D .NET ``public struct Chunk`` is nested in ``internal static class ChunkHelper``
  (Formats/3DSHelper.cs:52,108@52b0f00e).
* 3D Python ``GlobalTransform``'s five ``@property`` getters have no setter (GlobalTransform.py:16-20).
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.extractors.platforms.net import NetPlugin
from repo_presenter.extractors.platforms.python_surface import (
    inspect_public_surface,
    public_symbol_facts,
)


def _net_facts(tmp_path: Path, files: dict[str, str]) -> dict[str, dict[str, str]]:
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    facts = NetPlugin().surface_facts(tmp_path, [])
    return {f.value: dict(f.attributes or {}) for f in facts if f.kind == "public_symbol"}


STYLE = """namespace Aspose.Cells_FOSS
{
    public class Style
    {
        /// <summary>Gets or sets the font settings.</summary>
        public Font Font { get; private set; }
        /// <summary>Gets or sets border settings.</summary>
        public Borders Borders { get; private set; }
        public FillPattern Pattern { get; set; }
        public Color ForegroundColor { get; init; }
        public int Index { get; protected set; }
        public string Name => "style";
    }
    public class Font { }
    public class Borders { }
    public struct Color : System.IEquatable<Color> { public bool Equals(Color other) => true; }
    public enum FillPattern { None, Solid }
}
"""

EMAIL = """namespace Aspose.Email.Foss
{
    public sealed class MapiMessage
    {
        public const int AttachMethodByValue = 1;
        public static readonly int Limit = 5;
        public void AddAttachment(string name) { }
    }
    public sealed class CfbDocument
    {
        public CfbDocument() { }
        public static CfbDocument FromFile(string path) { return new CfbDocument(); }
    }
    public sealed record DirectoryEntry(int StreamId)
    {
        public bool IsRoot() { return StreamId == 0; }
    }
    public sealed class CfbStorage
    {
        public System.Collections.Generic.IList<object> Children { get; } = new System.Collections.Generic.List<object>();
    }
}
"""


def test_property_accessors_are_recorded_from_the_real_cells_style(tmp_path: Path) -> None:
    facts = _net_facts(tmp_path, {"src/Style.cs": STYLE})
    assert facts["Aspose.Cells_FOSS.Style.Font"]["member_kind"] == "property"
    assert facts["Aspose.Cells_FOSS.Style.Font"]["settable"] == "false"
    assert facts["Aspose.Cells_FOSS.Style.Borders"]["settable"] == "false"
    assert facts["Aspose.Cells_FOSS.Style.Pattern"]["settable"] == "true"
    assert facts["Aspose.Cells_FOSS.Style.ForegroundColor"]["settable"] == "true"  # init
    assert facts["Aspose.Cells_FOSS.Style.Index"]["settable"] == "false"  # protected set
    assert facts["Aspose.Cells_FOSS.Style.Name"]["settable"] == "false"  # expression-bodied
    # symbol_kind stays "method" for every member: counts, caps and placement are unchanged.
    assert facts["Aspose.Cells_FOSS.Style.Font"]["symbol_kind"] == "method"


def test_type_kinds_and_bases_are_recorded(tmp_path: Path) -> None:
    facts = _net_facts(tmp_path, {"src/Style.cs": STYLE})
    assert facts["Aspose.Cells_FOSS.Color"]["type_kind"] == "struct"
    assert facts["Aspose.Cells_FOSS.Color"]["bases"] == "System.IEquatable<Color>"
    assert facts["Aspose.Cells_FOSS.FillPattern"]["type_kind"] == "enum"
    assert facts["Aspose.Cells_FOSS.Style"]["type_kind"] == "class"


def test_constants_factories_methods_and_get_only_properties_are_told_apart(tmp_path: Path) -> None:
    facts = _net_facts(tmp_path, {"src/Email.cs": EMAIL})
    kinds = {value.rsplit(".", 2)[-2] + "." + value.rsplit(".", 1)[-1]: a.get("member_kind")
             for value, a in facts.items() if "member_kind" in a}
    assert kinds["MapiMessage.AttachMethodByValue"] == "constant"
    assert kinds["MapiMessage.Limit"] == "field"
    assert kinds["MapiMessage.AddAttachment"] == "method"
    assert kinds["CfbDocument.CfbDocument"] == "constructor"
    assert kinds["CfbDocument.FromFile"] == "method"
    assert kinds["DirectoryEntry.IsRoot"] == "method"
    assert kinds["CfbStorage.Children"] == "property"
    assert facts["Aspose.Email.Foss.CfbStorage.Children"]["settable"] == "false"
    assert facts["Aspose.Email.Foss.MapiMessage.AttachMethodByValue"]["settable"] == "false"


WORDS_SPLIT = """namespace Aspose.Words
{
    /// <summary>Specifies one of possible movements.</summary>
#if CPLUSPLUS
    public
#else
    internal
#endif
    enum DocumentPositionMovement
    {
        None,
        Inside,
    }

#if CPLUSPLUS
    public
#else
    internal
#endif
    class NodeEnumerator
    {
        public bool MoveNext() { return false; }
    }

#if JAVA
    internal
#else
    public
#endif
    class PortedEverywhere
    {
        public void Run() { }
    }

#if DEBUG
    public class DebugOnly { }
#endif

    public class Document
    {
        public void Save(string path) { }
    }
}
"""


def test_an_access_modifier_chosen_by_if_cplusplus_is_read_from_the_release_branch(
    tmp_path: Path,
) -> None:
    facts = _net_facts(tmp_path, {"Aspose.Words/Model/Nodes/Split.cs": WORDS_SPLIT})
    assert "Aspose.Words.DocumentPositionMovement" not in facts
    assert "Aspose.Words.NodeEnumerator" not in facts
    assert "Aspose.Words.NodeEnumerator.MoveNext" not in facts
    assert "Aspose.Words.DebugOnly" not in facts
    # The other direction: public in the .NET branch, internal only in the Java port.
    assert "Aspose.Words.PortedEverywhere" in facts
    assert "Aspose.Words.PortedEverywhere.Run" in facts
    assert "Aspose.Words.Document.Save" in facts


CHUNK = """namespace Aspose.ThreeD.Formats
{
    public static class ChunkIds
    {
        public const ushort CHUNK_MTL_MAP = 0xA200;
    }

    /// <summary>Helper methods for 3DS file parsing.</summary>
    internal static class ChunkHelper
    {
        /// <summary>Represents a 3DS chunk header.</summary>
        public struct Chunk
        {
            public ushort Id { get; }
        }
    }

    public class Outer
    {
        public class Inner { }
        private class Hidden { public class Deeper { } }
    }
}
"""


def test_a_public_type_nested_in_an_internal_type_is_not_public(tmp_path: Path) -> None:
    facts = _net_facts(tmp_path, {"src/Formats/3DSHelper.cs": CHUNK})
    assert not any(value.endswith(".Chunk") or ".Chunk." in value for value in facts)
    assert not any(value.endswith(".Deeper") for value in facts)
    assert "Aspose.ThreeD.Formats.ChunkIds" in facts
    assert any(value.endswith("Inner") for value in facts)


def test_python_properties_record_whether_a_setter_exists(tmp_path: Path) -> None:
    package = tmp_path / "aspose" / "threed"
    package.mkdir(parents=True)
    (tmp_path / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text(
        "from .GlobalTransform import GlobalTransform\n", encoding="utf-8"
    )
    (package / "GlobalTransform.py").write_text(
        "class GlobalTransform:\n"
        "    def __init__(self):\n        self._t = None\n\n"
        "    @property\n    def translation(self):\n        return self._t\n\n"
        "    @property\n    def scale(self):\n        return self._t\n\n"
        "    @scale.setter\n    def scale(self, value):\n        self._t = value\n\n"
        "    def to_matrix(self):\n        return None\n",
        encoding="utf-8",
    )
    facts = {
        f.value: dict(f.attributes or {})
        for f in public_symbol_facts(inspect_public_surface(tmp_path, ["aspose"]))
    }
    translation = next(a for v, a in facts.items() if v.endswith("GlobalTransform.translation"))
    scale = next(a for v, a in facts.items() if v.endswith("GlobalTransform.scale"))
    to_matrix = next(a for v, a in facts.items() if v.endswith("GlobalTransform.to_matrix"))
    assert (translation["member_kind"], translation["settable"]) == ("property", "false")
    assert (scale["member_kind"], scale["settable"]) == ("property", "true")
    assert to_matrix["member_kind"] == "method" and "settable" not in to_matrix
