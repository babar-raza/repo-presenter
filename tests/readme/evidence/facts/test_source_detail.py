"""Source-detail and project-detail facts (2026-11-06 unsupported-claim audit, class B).

Per kind: a positive case (the source states it and the fact says exactly that, with path:line),
a negative case (nothing is emitted where the source does not state it), and the contradicting
reading (a CONTRADICTED trait, or the fact whose content contradicts a false claim).
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import (
    EVIDENCE_ONLY_KINDS,
    FACT_KINDS,
    Evidence,
    Fact,
    FactsDocument,
    fact_id,
)
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.authoring import allowed_identifiers
from repo_presenter.readme.evidence.facts.project_detail import with_project_detail
from repo_presenter.readme.evidence.facts.source_detail import with_source_detail
from repo_presenter.readme.evidence.facts.source_text import clear_cache


def _write(root: Path, files: dict[str, str]) -> list[str]:
    clear_cache()
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return sorted(files)


def _symbol(value: str, path: str, line: int, kind: str, **attributes: str) -> Fact:
    return Fact(
        fact_id("public_symbol", value),
        "public_symbol",
        value,
        (Evidence(path, f"line {line}; {kind}; public by declaration"),),
        attributes={"symbol_kind": kind, **attributes},
    )


def _by_id(facts: list[Fact]) -> dict[str, Fact]:
    return {fact.id: fact for fact in facts}


def _python(root: Path, files: dict[str, str]) -> list[Fact]:
    tree = _write(root, files)
    surface = list(plugin_for("python").surface_facts(root, tree))
    return with_source_detail(root, tree, surface)


def test_the_new_kinds_are_registered_and_evidence_only() -> None:
    assert EVIDENCE_ONLY_KINDS <= set(FACT_KINDS)
    assert {"member_field", "module_export", "internal_symbol", "implementation",
            "standard_reference", "project_file", "package_trait"} == EVIDENCE_ONLY_KINDS  # fmt: skip


# --- enum members -----------------------------------------------------------------------------


def test_typescript_enum_members_and_the_enum_member_list(tmp_path: Path) -> None:
    tree = _write(tmp_path, {"src/Interp.ts": "export enum Interpolation {\n    CONSTANT = 0,\n    LINEAR = 1,\n}\n"})
    facts = with_source_detail(tmp_path, tree, [_symbol("Interpolation", "src/Interp.ts", 1, "enum")])
    by_id = _by_id(facts)
    member = by_id["enum_member:interpolation.linear"]
    assert member.value == "Interpolation.LINEAR"
    assert member.evidence[0].path == "src/Interp.ts" and member.evidence[0].detail.startswith("line 3;")
    enum = by_id["public_symbol:interpolation"]
    assert enum.attributes["members"] == "CONSTANT, LINEAR"
    # Contradicting reading: a README that says the enum has 14 members is held to this count.
    assert enum.attributes["member_count"] == "2"


def test_go_typed_constants_are_enum_members_and_untyped_ones_are_not(tmp_path: Path) -> None:
    source = (
        "package x\n\n// Format is an image format.\ntype Format int\n\nconst (\n"
        "\tFormatPng Format = iota\n\tFormatJpeg\n)\n\nconst (\n\tMaxRows = 10\n)\n"
    )
    tree = _write(tmp_path, {"format.go": source})
    facts = with_source_detail(tmp_path, tree, [_symbol("Format", "format.go", 4, "class")])
    members = sorted(f.value for f in facts if f.kind == "enum_member")
    assert members == ["Format.FormatJpeg", "Format.FormatPng"]


def test_python_enum_and_constant_class_members(tmp_path: Path) -> None:
    facts = _python(
        tmp_path,
        {
            "pkg/__init__.py": "",
            "pkg/kinds.py": (
                "from enum import Enum\n\nclass Mode(Enum):\n    AUTO = 'auto'\n    BYTE = 'byte'\n\n"
                "class TextureMapping:\n    AMBIENT = None\n    SHADOW = None\n\n"
                "class Mixed:\n    LIMIT = 3\n    name = 'x'\n"
            ),
        },
    )
    members = sorted(f.value for f in facts if f.kind == "enum_member")
    assert members == [
        "pkg.kinds.Mode.AUTO",
        "pkg.kinds.Mode.BYTE",
        "pkg.kinds.TextureMapping.AMBIENT",
        "pkg.kinds.TextureMapping.SHADOW",
    ]  # a class mixing constants with ordinary attributes is not an enumeration
    mode = _by_id(facts)["enum_member:pkg.kinds.mode.auto"]
    assert mode.attributes["literal"] == "'auto'" and mode.evidence[0].detail.startswith("line 4;")


def test_rust_struct_fields_are_not_variants(tmp_path: Path) -> None:
    tree = _write(
        tmp_path,
        {"src/shape.rs": "pub enum Shape {\n    /// doc\n    #[default]\n    Rect,\n    Star { points: u8 },\n}\n"},
    )
    facts = with_source_detail(tmp_path, tree, [_symbol("Shape", "src/shape.rs", 1, "enum")])
    assert sorted(f.value for f in facts if f.kind == "enum_member") == ["Shape.Rect", "Shape.Star"]


# --- full docstrings and declarations ---------------------------------------------------------


def test_the_whole_doc_comment_is_kept_beside_the_first_sentence(tmp_path: Path) -> None:
    source = (
        "package x\n\n// Style groups font settings into a record. Multiple cells may share it;\n"
        "// the library automatically deduplicates identical styles during save.\ntype Style struct {\n}\n"
    )
    tree = _write(tmp_path, {"style.go": source})
    fact = _symbol("Style", "style.go", 5, "class", docstring="Style groups font settings into a record.")
    (style,) = [f for f in with_source_detail(tmp_path, tree, [fact]) if f.kind == "public_symbol"]
    assert style.attributes["docstring"] == "Style groups font settings into a record."
    assert "automatically deduplicates identical styles during save" in style.attributes["docstring_full"]
    assert style.attributes["declaration"] == "type Style struct"


def test_csharp_xml_doc_and_a_sealed_declaration(tmp_path: Path) -> None:
    source = (
        "namespace N;\n/// <summary>\n/// Immutable result of a probe.\n/// </summary>\n"
        "/// <remarks>Every number is positive or <see langword=\"null\"/>.</remarks>\n"
        "public sealed class ImageInfo\n{\n}\n"
    )
    tree = _write(tmp_path, {"ImageInfo.cs": source})
    fact = _symbol("N.ImageInfo", "ImageInfo.cs", 6, "class", docstring="Immutable result of a probe.")
    (info,) = [f for f in with_source_detail(tmp_path, tree, [fact]) if f.kind == "public_symbol"]
    assert info.attributes["docstring_full"] == "Immutable result of a probe. Every number is positive or null."
    assert info.attributes["declaration"] == "public sealed class ImageInfo"


def test_a_one_sentence_doc_adds_nothing(tmp_path: Path) -> None:
    facts = _python(tmp_path, {"pkg/__init__.py": "def run():\n    \"\"\"Run it.\"\"\"\n"})
    run = _by_id(facts)["public_symbol:pkg.run"]
    assert "docstring_full" not in (run.attributes or {})


def test_python_docstring_beyond_the_first_line(tmp_path: Path) -> None:
    facts = _python(
        tmp_path,
        {"pkg/__init__.py": "def save(path):\n    \"\"\"Save the document.\n\n    The format is inferred from the suffix.\n    \"\"\"\n"},
    )
    assert _by_id(facts)["public_symbol:pkg.save"].attributes["docstring_full"] == (
        "Save the document. The format is inferred from the suffix."
    )


# --- fields -----------------------------------------------------------------------------------


def test_dataclass_pydantic_slots_and_init_attributes(tmp_path: Path) -> None:
    facts = _python(
        tmp_path,
        {
            "pkg/__init__.py": (
                "from dataclasses import dataclass, field\nfrom pydantic import BaseModel\n\n"
                "@dataclass\nclass Header:\n    major_version: int = 3\n    _hidden: int = 0\n\n"
                "class Model(BaseModel):\n    sections: list = []\n\n"
                "class Table:\n    __slots__ = ('IsBordersVisible', '_x')\n"
                "    def __init__(self):\n        self.Columns = []\n        self._cache = None\n\n"
                "class Plain:\n    note: str\n"
            )
        },
    )
    fields = {f.value: f for f in facts if f.kind == "member_field"}
    assert set(fields) == {
        "pkg.Header.major_version",
        "pkg.Model.sections",
        "pkg.Table.IsBordersVisible",
        "pkg.Table.Columns",
    }  # private names and a plain class's bare annotation are not fields
    assert fields["pkg.Header.major_version"].attributes["type"] == "int"
    assert fields["pkg.Header.major_version"].evidence[0].detail.startswith("line 6;")
    assert _by_id(facts)["public_symbol:pkg.header"].attributes["fields"] == "major_version"


# --- module exports and internal symbols ------------------------------------------------------


def test_a_typescript_export_the_entry_point_does_not_reexport(tmp_path: Path) -> None:
    source = "export interface HtmlSaveOptions {\n    sheet?: number;\n    title: string;\n}\nexport class Book {}\n"
    tree = _write(tmp_path, {"src/html/table.ts": source})
    facts = with_source_detail(tmp_path, tree, [_symbol("Book", "src/html/table.ts", 5, "class")])
    exports = [f for f in facts if f.kind == "module_export"]
    assert [f.value for f in exports] == ["HtmlSaveOptions"]  # Book is public: not repeated here
    # Contradicting reading: the export is NOT public API (reexported "no").
    assert exports[0].attributes["reexported"] == "no"
    assert exports[0].attributes["shape"] == "interface with 2 properties"


def test_csharp_internal_type_with_its_doc_and_where_it_is_constructed(tmp_path: Path) -> None:
    tree = _write(
        tmp_path,
        {
            "src/PlyReader.cs": "/// <summary>Reads PLY files.</summary>\ninternal class PlyReader : IImporter\n{\n}\n",
            "src/IOService.cs": "public class IOService\n{\n    object R() => new PlyReader();\n}\n",
        },
    )
    facts = with_source_detail(tmp_path, tree, [_symbol("IOService", "src/IOService.cs", 1, "class")])
    (reader,) = [f for f in facts if f.kind == "internal_symbol"]
    assert reader.value == "PlyReader"
    assert reader.attributes["visibility"] == "internal"
    assert reader.attributes["docstring_full"] == "Reads PLY files."
    assert reader.attributes["constructed_at"] == "src/IOService.cs:3"


def test_a_private_python_module_docstring_is_internal_and_a_public_class_is_not(tmp_path: Path) -> None:
    facts = _python(
        tmp_path,
        {
            "pkg/__init__.py": "from pkg._cascade import Engine\n",
            "pkg/_cascade.py": "\"\"\"Cascade: !important beats specificity, then source order.\"\"\"\n\nclass Engine:\n    pass\n\nclass _Helper:\n    \"\"\"Internal.\"\"\"\n",
        },
    )
    internal = {f.value: f for f in facts if f.kind == "internal_symbol"}
    assert set(internal) == {"pkg._cascade", "pkg._cascade._Helper"}  # Engine is re-exported: public
    assert "specificity" in internal["pkg._cascade"].attributes["docstring_full"]


# --- implementation ---------------------------------------------------------------------------


def test_csharp_throws_always_and_conditionally_and_a_constant_getter(tmp_path: Path) -> None:
    source = (
        "public class PsdImage\n{\n    public int Version\n    {\n        get => 6;\n        set\n        {\n"
        "            if (value != 6)\n            {\n                throw new ArgumentOutOfRangeException(nameof(value), value, \"Only 6.\");\n"
        "            }\n        }\n    }\n\n    public Layer ActiveLayer\n    {\n        get => Layers.FirstOrDefault();\n"
        "        set => throw new NotSupportedException(\"Not in this build.\");\n    }\n\n"
        "    public void Render() { Draw(); }\n}\n"
    )
    tree = _write(tmp_path, {"PsdImage.cs": source})
    symbols = [
        _symbol("PsdImage", "PsdImage.cs", 1, "class"),
        _symbol("PsdImage.Version", "PsdImage.cs", 3, "method"),
        _symbol("PsdImage.ActiveLayer", "PsdImage.cs", 15, "method"),
        _symbol("PsdImage.Render", "PsdImage.cs", 21, "method"),
    ]
    facts = [f for f in with_source_detail(tmp_path, tree, symbols) if f.kind == "implementation"]
    by_value = {f.value: f for f in facts}
    assert "PsdImage.ActiveLayer setter throws NotSupportedException" in by_value
    assert by_value["PsdImage.ActiveLayer setter throws NotSupportedException"].attributes["condition"] == "always"
    conditional = by_value["PsdImage.Version setter throws ArgumentOutOfRangeException (conditionally)"]
    assert conditional.attributes["message"] == "Only 6." and conditional.evidence[0].detail.startswith("line 10;")
    assert "PsdImage.Version getter always returns 6" in by_value
    assert not any("Render" in value for value in by_value)  # a body that throws nothing


def test_python_stub_raises_always_contradicting_a_works_claim(tmp_path: Path) -> None:
    facts = _python(
        tmp_path,
        {
            "pkg/__init__.py": (
                "class Scene:\n    def render(self):\n        \"\"\"Render.\"\"\"\n        raise NotImplementedError('later')\n\n"
                "    def save(self, path):\n        if not path:\n            raise ValueError('path')\n        return None\n\n"
                "    @property\n    def mask(self):\n        return 1\n\n    @mask.setter\n    def mask(self, value):\n"
                "        raise NotSupportedException('no')\n\nDEFAULT_SMTP_ADDRESS_TYPE = 'SMTP'\n"
            )
        },
    )
    values = {f.value: f for f in facts if f.kind == "implementation"}
    stub = values["pkg.Scene.render raises NotImplementedError"]
    assert stub.attributes["condition"] == "always"  # the fact a "Scene renders" claim meets
    assert "pkg.Scene.save raises ValueError (conditionally)" in values
    assert values["pkg.Scene.mask setter raises NotSupportedException"].attributes["accessor"] == "setter"
    assert "pkg.Scene.mask getter always returns 1" in values
    assert "DEFAULT_SMTP_ADDRESS_TYPE = 'SMTP'" in values


# --- standards --------------------------------------------------------------------------------


def test_named_specifications_with_their_lines_and_tests_ignored(tmp_path: Path) -> None:
    tree = _write(
        tmp_path,
        {
            "src/workbook.go": "package x\n\n// Workbook is an ECMA-376 Office Open XML workbook.\ntype Workbook struct{}\n",
            "src/Mime.cs": "class M { string T = \"message/rfc822\"; }\n",
            "tests/x_test.go": "package x\n// RFC 9999\n",
        },
    )
    facts = [f for f in with_source_detail(tmp_path, tree, []) if f.kind == "standard_reference"]
    assert {f.value: f.evidence[0].detail.split(";")[0] for f in facts} == {
        "ECMA-376": "line 3",
        "RFC 822": "line 1",
    }


# --- project files ----------------------------------------------------------------------------


def test_test_project_dependencies_only_from_test_projects(tmp_path: Path) -> None:
    tree = _write(
        tmp_path,
        {
            "src/Lib/Lib.csproj": '<Project><ItemGroup><PackageReference Include="SkiaSharp" Version="2.88.8" /></ItemGroup></Project>\n',
            "tests/Lib.Tests/Lib.Tests.csproj": (
                "<Project>\n<ItemGroup>\n"
                '<PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />\n'
                '<PackageReference Include="xunit" Version="2.5.3" />\n</ItemGroup>\n</Project>\n'
            ),
        },
    )
    facts = [f for f in with_project_detail(tmp_path, tree, "net", []) if f.kind == "project_file"]
    assert {f.value: f.evidence[0].detail.split(";")[0] for f in facts} == {
        "Microsoft.NET.Test.Sdk 17.8.0": "line 3",
        "xunit 2.5.3": "line 4",
    }  # the library's own SkiaSharp reference is not a test dependency


def test_cmake_settings_presets_and_external_packages(tmp_path: Path) -> None:
    tree = _write(
        tmp_path,
        {
            "CMakeLists.txt": "cmake_minimum_required(VERSION 3.16)\nproject(x)\nset(CMAKE_CXX_STANDARD 17)\nset(CMAKE_CXX_STANDARD_REQUIRED ON)\n",
            "CMakePresets.json": '{"version": 3, "configurePresets": [{"name": "default", "generator": "Ninja", "binaryDir": "build"}]}\n',
        },
    )
    values = {f.value for f in with_project_detail(tmp_path, tree, "cpp", [])}
    assert "CMAKE_CXX_STANDARD 17" in values and "CMAKE_CXX_STANDARD_REQUIRED ON" in values
    assert "configure preset default; generator Ninja; binaryDir build" in values
    assert any(v.startswith("external packages: none") for v in values)


def test_a_find_package_call_is_named_not_reported_as_none(tmp_path: Path) -> None:
    tree = _write(tmp_path, {"CMakeLists.txt": "project(x)\nfind_package(ZLIB REQUIRED)\n"})
    values = {f.value for f in with_project_detail(tmp_path, tree, "cpp", [])}
    assert "external packages: ZLIB" in values


def test_makefile_targets_pytest_config_and_inventory(tmp_path: Path) -> None:
    tree = _write(
        tmp_path,
        {
            "Makefile": ".PHONY: test\ntest:\n\tpython3 -m unittest discover -s tests\n\ncheck: test build\n",
            "pyproject.toml": '[project]\nname = "x"\n\n[tool.pytest.ini_options]\npythonpath = ["src"]\ntestpaths = ["tests"]\n',
            "src/x/data/hyphenation/.gitkeep": "",
            "src/x/__init__.py": "",
        },
    )
    values = {f.value for f in with_project_detail(tmp_path, tree, "python", [])}
    assert "make test: python3 -m unittest discover -s tests" in values
    assert "make check (depends on test build)" in values
    assert 'pytest pythonpath = ["src"]' in values
    assert "src/x/data/hyphenation/ holds no files but .gitkeep" in values
    assert not any(v.startswith("no pyproject.toml") for v in values)  # the manifest exists


def test_test_names_carry_their_documentation(tmp_path: Path) -> None:
    tree = _write(
        tmp_path,
        {
            "tests/T.Tests/DocTests.cs": (
                "public class DocTests\n{\n    /// <summary>\n    /// Saving without mutations preserves the file byte-for-byte.\n"
                "    /// </summary>\n    [Fact]\n    public void Save_IsByteExact()\n    {\n    }\n}\n"
            )
        },
    )
    (test,) = [f for f in with_project_detail(tmp_path, tree, "net", []) if f.kind == "project_file"]
    assert test.value == "test save is byte exact: Saving without mutations preserves the file byte-for-byte."
    assert test.evidence[0].detail.startswith("line 7;")


# --- package traits ---------------------------------------------------------------------------


def test_notices_licence_files_and_requirements_floor(tmp_path: Path) -> None:
    tree = _write(
        tmp_path,
        {
            "THIRD_PARTY_NOTICES.md": "# Third-party notices\n\n## ReportLab\n\nUsed for PDF export.\nLicense: BSD 3-Clause\n",
            "License/SkiaSharp.LICENSE.txt": "MIT License\n",
            "requirements.txt": "# runtime\npython>=3.7\n",
        },
    )
    values = {f.value: f for f in with_project_detail(tmp_path, tree, "python", [])}
    assert values["ReportLab: BSD 3-Clause (third-party notice)"].evidence[0].detail.startswith("line 3;")
    assert "licence notice file for SkiaSharp: License/SkiaSharp.LICENSE.txt (MIT)" in values
    assert values["python>=3.7"].evidence[0].detail.startswith("line 2;")
    assert "no pyproject.toml, setup.py or setup.cfg at the repository root" in values


def test_pure_python_and_stdlib_only_supported(tmp_path: Path) -> None:
    tree = _write(tmp_path, {"pyproject.toml": "[project]\nname='x'\n", "src/x/__init__.py": "import json\nfrom x import y\n", "src/x/y.py": ""})
    traits = {f.id: f for f in with_project_detail(tmp_path, tree, "python", []) if f.kind == "package_trait"}
    assert traits["package_trait:pure_source.python"].polarity == "SUPPORTED"
    assert traits["package_trait:stdlib_only.python"].polarity == "SUPPORTED"


def test_pure_python_and_stdlib_only_contradicted(tmp_path: Path) -> None:
    tree = _write(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname='x'\n",
            "src/x/__init__.py": "import requests\n",
            "src/x/_speed.c": "int f(void) { return 0; }\n",
        },
    )
    traits = {f.id: f for f in with_project_detail(tmp_path, tree, "python", []) if f.kind == "package_trait"}
    pure = traits["package_trait:pure_source.python"]
    assert pure.polarity == "CONTRADICTED" and pure.evidence[0].path == "src/x/_speed.c"
    stdlib = traits["package_trait:stdlib_only.python"]
    assert stdlib.polarity == "CONTRADICTED"
    assert stdlib.evidence[0].path == "src/x/__init__.py" and stdlib.evidence[0].detail.startswith("line 1;")


def test_cgo_contradicts_pure_go(tmp_path: Path) -> None:
    tree = _write(tmp_path, {"lib.go": 'package lib\n\nimport "C"\n', "ok.go": "package lib\n"})
    (trait,) = [f for f in with_project_detail(tmp_path, tree, "go", []) if f.kind == "package_trait"]
    assert trait.value == "pure Go: no cgo" and trait.polarity == "CONTRADICTED"
    assert trait.evidence[0].path == "lib.go"


def test_every_detail_fact_validates_as_a_document(tmp_path: Path) -> None:
    facts = _python(tmp_path, {"pkg/__init__.py": "class A:\n    X = 1\n    Y = 2\n", "Makefile": "t:\n\techo\n"})
    facts = with_project_detail(tmp_path, sorted(["pkg/__init__.py", "Makefile"]), "python", facts)
    document = FactsDocument("o/r", "0" * 40, tuple(facts))
    assert document.to_json()


def test_non_public_names_never_become_allowed_identifiers(tmp_path: Path) -> None:
    """A README naming an internal type or a non-re-exported export as API stays unsupported
    (class A: "non-existent or non-exported type"); a public type's field is a real member."""
    tree = _write(
        tmp_path,
        {
            "src/PlyReader.cs": "internal class PlyReader\n{\n}\n",
            "src/types.ts": "export type QuadrilateralShapeType = 'a' | 'b';\n",
            "pkg/__init__.py": "from dataclasses import dataclass\n\n@dataclass\nclass Header:\n    major_version: int = 3\n",
        },
    )
    surface = list(plugin_for("python").surface_facts(tmp_path, tree))
    facts = with_source_detail(tmp_path, tree, surface)
    assert {f.kind for f in facts} >= {"internal_symbol", "module_export", "member_field"}
    allowed = allowed_identifiers(FactsDocument("o/r", "0" * 40, tuple(facts)), "Aspose.Example")
    assert "PlyReader" not in allowed
    assert "QuadrilateralShapeType" not in allowed
    assert "Header.major_version" in allowed and "major_version" in allowed
