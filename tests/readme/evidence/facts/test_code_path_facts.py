"""K02/K06 fact fixes (BL-062, BL-066): facts record what the code path really does.

Every fixture is the real shape behind a registered false claim
(``docs/investigations/2026-11-13-lane-r-false-claim-review.md``, ``data/readme_findings.json``),
cut to the lines that decide it; each has a negative control the rule must leave alone.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.examples import FormatDeclaration
from repo_presenter.core.facts import Evidence, Fact, fact_id
from repo_presenter.extractors.platforms import net
from repo_presenter.extractors.platforms.python_format_declarations import (
    format_declarations,
)
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.evidence.facts.formats import format_facts
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


def _never(facts: list[Fact]) -> set[str]:
    return {
        f.value.split(" ", 1)[0]
        for f in facts
        if f.kind == "implementation" and (f.attributes or {}).get("aspect") == "never_thrown"
    }


# --- never-thrown exception types (Cells C++ FormulaException/StyleException) ----------------

_CELLS_CPP = {
    "include/cells/CellsException.h": "class CellsException : public std::runtime_error {\npublic:\n    explicit CellsException(std::string_view message);\n};\n",
    "include/cells/FormulaException.h": '#include "cells/CellsException.h"\nclass FormulaException : public CellsException {\npublic:\n    /// Initializes a new instance of the FormulaException class.\n    explicit FormulaException(std::string_view message);\n};\n',
    "include/cells/StyleException.h": "class StyleException : public CellsException {\npublic:\n    explicit StyleException(std::string_view message);\n};\n",
    "include/cells/UnsupportedFeatureException.h": "class UnsupportedFeatureException : public CellsException {\npublic:\n    explicit UnsupportedFeatureException(std::string_view message);\n};\n",
    "src/cells/FormulaException.cpp": '#include "cells/FormulaException.h"\nFormulaException::FormulaException(std::string_view message)\n    : CellsException(message) {}\n',
    "src/cells/StyleException.cpp": '#include "cells/StyleException.h"\nStyleException::StyleException(std::string_view message)\n    : CellsException(message) {}\n',
    # Cell::SetFormula only stores the text (Cell.cpp:153); saving throws UnsupportedFeatureException.
    "src/cells/Cell.cpp": 'void Cell::SetFormula(std::string_view formula) {\n    // FormulaException is documented, never thrown\n    formula_ = std::string(formula);\n}\nvoid Workbook::Save(int f) {\n    if (f != 1) throw UnsupportedFeatureException("FormulaException");\n}\n',
}


def _cpp_symbols() -> list[Fact]:
    return [
        _symbol("Cells.CellsException", "include/cells/CellsException.h", 1, "class"),
        _symbol("Cells.FormulaException", "include/cells/FormulaException.h", 2, "class"),
        _symbol("Cells.StyleException", "include/cells/StyleException.h", 1, "class"),
        _symbol("Cells.UnsupportedFeatureException", "include/cells/UnsupportedFeatureException.h", 1, "class"),
    ]


def test_an_exception_only_constructed_in_its_own_files_is_never_thrown(tmp_path: Path) -> None:
    tree = _write(tmp_path, _CELLS_CPP)
    facts = with_source_detail(tmp_path, tree, _cpp_symbols())
    # Comments and string literals naming it are not uses; its own constructor is not a use.
    assert _never(facts) == {"Cells.FormulaException", "Cells.StyleException"}
    fact = next(f for f in facts if f.id == "implementation:never_thrown.cells.formulaexception")
    assert fact.evidence[0].path == "include/cells/FormulaException.h"
    assert fact.evidence[0].detail.startswith("line 2;")


def test_a_base_exception_thrown_through_a_subclass_is_thrown(tmp_path: Path) -> None:
    """Negative control: ``CellsException`` itself is never named in a throw, but its subclass
    ``UnsupportedFeatureException`` is thrown, so ``catch (CellsException&)`` really catches."""
    tree = _write(tmp_path, _CELLS_CPP)
    facts = with_source_detail(tmp_path, tree, _cpp_symbols())
    assert "Cells.CellsException" not in _never(facts)
    assert "Cells.UnsupportedFeatureException" not in _never(facts)


def test_a_python_exception_defined_and_exported_only_is_never_thrown(tmp_path: Path) -> None:
    """3D Python ``TrialException``: "raised in Scene.Open/Scene.Save when no licenses are
    applied" is the commercial product's doc comment; the FOSS package only defines and exports
    it. ``ImportException`` is raised, so it is not reported."""
    tree = _write(
        tmp_path,
        {
            "aspose/threed/__init__.py": "from .TrialException import TrialException\nfrom .ImportException import ImportException\n__all__ = ['TrialException', 'ImportException']\n",
            "aspose/threed/TrialException.py": 'class TrialException(Exception):\n    """This is raised in Scene.Open/Scene.Save when no licenses are applied."""\n\n    _suppress = False\n\n    @staticmethod\n    def set_suppress_trial_exception(value):\n        TrialException._suppress = bool(value)\n',
            "aspose/threed/ImportException.py": "class ImportException(Exception):\n    pass\n",
            "aspose/threed/Scene.py": "from .ImportException import ImportException\n\n\nclass Scene:\n    def open(self, path):\n        if not path:\n            raise ImportException('no path')\n",
        },
    )
    surface = list(plugin_for("python").surface_facts(tmp_path, tree))
    facts = with_source_detail(tmp_path, tree, surface)
    assert {name.rsplit(".", 1)[-1] for name in _never(facts)} == {"TrialException"}


# --- a static instance built as a type whose virtual only throws (3D .NET FileFormat) ----------

_FILE_FORMAT = """namespace Aspose.ThreeD
{
    public class FileFormat
    {
        public static readonly FileFormat WavefrontOBJ = new FileFormat(".obj", new[] { ".obj" });
        public static FileFormat Discreet3DS;
        public static readonly FileFormat Fbx = new FbxFormat();

        public virtual SaveOptions CreateSaveOptions()
        {
            throw new NotImplementedException($"Save options not implemented for {Extension}");
        }
    }

    public class FbxFormat : FileFormat
    {
        public override SaveOptions CreateSaveOptions()
        {
            return new FbxSaveOptions();
        }
    }
}
"""


def _net_symbols() -> list[Fact]:
    path = "src/Aspose/ThreeD/FileFormat.cs"
    return [
        _symbol("Aspose.ThreeD.FileFormat", path, 3, "class"),
        # The surface extractor lists static fields with kind "method" (K03, owned elsewhere).
        _symbol("Aspose.ThreeD.FileFormat.WavefrontOBJ", path, 5, "method"),
        _symbol("Aspose.ThreeD.FileFormat.Discreet3DS", path, 6, "method"),
        _symbol("Aspose.ThreeD.FileFormat.Fbx", path, 7, "method"),
        _symbol("Aspose.ThreeD.FileFormat.CreateSaveOptions", path, 9, "method"),
        _symbol("Aspose.ThreeD.FbxFormat", path, 15, "class"),
        _symbol("Aspose.ThreeD.FbxFormat.CreateSaveOptions", path, 17, "method"),
    ]


def test_a_static_instance_of_the_base_type_carries_its_throwing_virtual(tmp_path: Path) -> None:
    tree = _write(tmp_path, {"src/Aspose/ThreeD/FileFormat.cs": _FILE_FORMAT})
    facts = with_source_detail(tmp_path, tree, _net_symbols())
    stubs = {
        (f.attributes or {}).get("member"): f
        for f in facts
        if (f.attributes or {}).get("dispatch") == "static_instance"
    }
    assert set(stubs) == {"Aspose.ThreeD.FileFormat.WavefrontOBJ.CreateSaveOptions"}
    fact = stubs["Aspose.ThreeD.FileFormat.WavefrontOBJ.CreateSaveOptions"]
    assert fact.attributes["exception"] == "NotImplementedException"
    assert fact.attributes["via"] == "Aspose.ThreeD.FileFormat.CreateSaveOptions"
    # Negative controls: an instance of the overriding subtype (Fbx) and an unassigned field.
    assert not any("FileFormat.Fbx." in member or "Discreet3DS" in member for member in stubs)


def test_a_method_whose_body_was_read_without_a_throw_is_marked(tmp_path: Path) -> None:
    """3D .NET ``NurbsSurface.ToMesh`` returns a placeholder grid; the README said it throws."""
    source = (
        "namespace Aspose.ThreeD.Entities\n{\n    public class NurbsSurface\n    {\n"
        "        public Mesh ToMesh()\n        {\n            var mesh = new Mesh();\n"
        "            // Simple linear interpolation for now\n            return mesh;\n        }\n\n"
        "        public void Evaluate()\n        {\n            throw new NotImplementedException();\n        }\n    }\n}\n"
    )
    path = "src/Entities/NurbsSurface.cs"
    tree = _write(tmp_path, {path: source})
    facts = with_source_detail(
        tmp_path,
        tree,
        [
            _symbol("Aspose.ThreeD.Entities.NurbsSurface", path, 3, "class"),
            _symbol("Aspose.ThreeD.Entities.NurbsSurface.ToMesh", path, 5, "method"),
            _symbol("Aspose.ThreeD.Entities.NurbsSurface.Evaluate", path, 12, "method"),
        ],
    )
    by_value = {f.value: f for f in facts if f.kind == "public_symbol"}
    assert by_value["Aspose.ThreeD.Entities.NurbsSurface.ToMesh"].attributes["body_throws"] == "no"
    assert "body_throws" not in by_value["Aspose.ThreeD.Entities.NurbsSurface.Evaluate"].attributes


# --- dispatch order: a format behind a raising probe is not supported (3D Python .dae) ----------

_DISPATCH = {
    "pkg/__init__.py": "",
    "pkg/FileFormat.py": "from .formats.obj.ObjFormat import ObjFormat\nfrom .formats.fbx.FbxFormat import FbxFormat\nfrom .formats.dae.DaeFormat import DaeFormat\n",
    "pkg/formats/__init__.py": (
        "from .IOService import IOService\nfrom .obj.ObjPlugin import ObjPlugin\n"
        "from .fbx.FbxPlugin import FbxPlugin\nfrom .dae.DaePlugin import DaePlugin\n\n\n"
        "def _register_plugins():\n    io = IOService()\n    io.register_plugin(ObjPlugin())\n"
        "    io.register_plugin(FbxPlugin())\n    io.register_plugin(DaePlugin())\n"
    ),
    "pkg/formats/IOService.py": (
        "class IOService:\n    _exporters = []\n\n    def register_plugin(self, plugin):\n        pass\n\n"
        "    def create_exporter(self, fmt):\n        for exporter in self._exporters:\n"
        "            if exporter.supports_format(fmt):\n                return exporter\n"
        "        raise RuntimeError('No exporter')\n"
    ),
    "pkg/formats/Exporter.py": (
        "class Exporter:\n    def supports_format(self, file_format):\n"
        "        raise NotImplementedError('supports_format is not implemented')\n"
    ),
}
for _name, _ext, _supports, _body in (
    ("Obj", "obj", True, "stream.write('o')"),
    ("Fbx", "fbx", False, "raise NotImplementedError('FBX export is not implemented')"),
    ("Dae", "dae", True, "stream.write('<COLLADA/>')"),
):
    _low = _name.lower()
    _DISPATCH[f"pkg/formats/{_low}/__init__.py"] = ""
    _DISPATCH[f"pkg/formats/{_low}/{_name}Format.py"] = (
        f"class {_name}Format:\n    @property\n    def extensions(self):\n        return ['{_ext}']\n"
    )
    _DISPATCH[f"pkg/formats/{_low}/{_name}Importer.py"] = (
        f"class {_name}Importer:\n    def supports_format(self, f):\n        return True\n\n"
        "    def import_scene(self, scene, stream, options):\n        scene.add(stream.read())\n"
    )
    _supports_text = "    def supports_format(self, f):\n        return True\n\n" if _supports else ""
    _DISPATCH[f"pkg/formats/{_low}/{_name}Exporter.py"] = (
        f"from ..Exporter import Exporter\n\n\nclass {_name}Exporter(Exporter):\n{_supports_text}"
        f"    def export(self, scene, stream, options):\n        {_body}\n"
    )
    _DISPATCH[f"pkg/formats/{_low}/{_name}Plugin.py"] = (
        f"class {_name}Plugin:\n    def __init__(self):\n"
        f"        from .{_name}Importer import {_name}Importer\n"
        f"        from .{_name}Exporter import {_name}Exporter\n"
        f"        self._importer = {_name}Importer()\n        self._exporter = {_name}Exporter()\n\n"
        f"    def get_file_format(self):\n        from .{_name}Format import {_name}Format\n"
        f"        return {_name}Format()\n"
    )


def test_a_format_registered_after_a_raising_probe_is_unreachable(tmp_path: Path) -> None:
    tree = _write(tmp_path, _DISPATCH)
    declarations = format_declarations(tmp_path, tree)
    registered = {(d.direction, d.extension) for d in declarations if d.kind == "registration"}
    # Obj (before the stub) and every importer (FbxImporter answers supports_format) stay.
    assert {("output", ".obj"), ("input", ".obj"), ("input", ".fbx"), ("input", ".dae")} <= registered
    assert ("output", ".dae") not in registered and ("output", ".fbx") not in registered
    [unreachable] = [d for d in declarations if d.kind == "declaration" and d.direction == "output"]
    assert unreachable.extension == ".dae"
    assert "FbxExporter.supports_format (defined by Exporter)" in unreachable.detail

    facts = {f.id: f for f in format_facts([], [], lambda code: [], "receipts.json", declarations)}
    dae = facts["format:output.dae"]
    assert dae.polarity == "UNRESOLVED" and dae.attributes == {"code_path": "stub"}
    assert facts["format:output.obj"].polarity == "SUPPORTED"
    assert facts["format:output.obj"].attributes is None


def test_without_a_raising_probe_dispatch_order_changes_nothing(tmp_path: Path) -> None:
    """Negative control: the same tree with ``FbxExporter.supports_format`` implemented."""
    files = dict(_DISPATCH)
    files["pkg/formats/fbx/FbxExporter.py"] = (
        "from ..Exporter import Exporter\n\n\nclass FbxExporter(Exporter):\n"
        "    def supports_format(self, f):\n        return False\n\n"
        "    def export(self, scene, stream, options):\n        raise NotImplementedError('x')\n"
    )
    tree = _write(tmp_path, files)
    declarations = format_declarations(tmp_path, tree)
    assert ("output", ".dae") in {(d.direction, d.extension) for d in declarations if d.kind == "registration"}
    assert not any(d.kind == "declaration" and d.direction for d in declarations)


def test_a_stub_declaration_never_downgrades_an_executed_example() -> None:
    declaration = FormatDeclaration(".dae", "output", "declaration", "pkg/x.py", 3, "unreachable")
    facts = format_facts([], [], lambda code: [], "r.json", [declaration])
    assert facts[0].attributes == {"code_path": "stub"}


# --- K06: dependencies a consumer of the published package gets (Words .NET) -------------------

_WORDS_CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFrameworks>net462;netstandard2.0;net8.0</TargetFrameworks><AssemblyName>Aspose.Words.FOSS</AssemblyName></PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\\Aspose.Foundation\\Aspose.Foundation\\Aspose.Foundation.csproj" />
    <PackageReference Include="ILRepack" Version="2.0.46" PrivateAssets="all" ExcludeAssets="all" />
  </ItemGroup>
</Project>
"""
_FOUNDATION_CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="SkiaSharp" Version="3.119.0" />
    <PackageReference Include="System.Text.Encoding.CodePages" Version="7.0.0" />
    <PackageReference Include="BitMiracle.LibTiff.NET" Version="2.4.649" />
    <PackageReference Include="Microsoft.Win32.Registry" Version="5.0.0" />
  </ItemGroup>
</Project>
"""
_WORDS_NUSPEC = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2012/06/nuspec.xsd">
	<metadata>
		<id>Aspose.Words.FOSS</id>
		<version>26.3.0</version>
		<dependencies>
			<group targetFramework="net462" />
			<group targetFramework=".NETStandard2.0">
				<dependency id="SkiaSharp" version="3.119.0" exclude="Build,Analyzers" />
				<dependency id="BitMiracle.LibTiff.NET" version="2.4.649" exclude="Build,Analyzers" />
				<dependency id="Microsoft.Win32.Registry" version="5.0.0" exclude="Build,Analyzers" />
			</group>
			<group targetFramework="net8.0">
				<dependency id="SkiaSharp" version="3.119.0" exclude="Build,Analyzers" />
				<dependency id="BitMiracle.LibTiff.NET" version="2.4.649" exclude="Build,Analyzers" />
			</group>
		</dependencies>
	</metadata>
</package>
"""


def _words(root: Path, nuspec: bool = True) -> Path:
    files = {
        "Aspose.Words/Aspose.Words.csproj": _WORDS_CSPROJ,
        "Aspose.Words/Document.cs": "namespace Aspose.Words { public class Document {} }\n",
        "Aspose.Foundation/Aspose.Foundation/Aspose.Foundation.csproj": _FOUNDATION_CSPROJ,
    }
    if nuspec:
        files["Package/Aspose.Words.FOSS.nuspec"] = _WORDS_NUSPEC
    _write(root, files)
    manifest = net.PLUGIN.detect_manifest(root)
    assert manifest is not None and manifest.name == "Aspose.Words.csproj"
    return manifest


def test_the_published_nuspec_is_the_dependency_snapshot(tmp_path: Path) -> None:
    """BL-066 acceptance: SkiaSharp 3.119.0, BitMiracle.LibTiff.NET 2.4.649 and
    Microsoft.Win32.Registry 5.0.0 (netstandard2.0), no ``dependency:none``."""
    manifest = _words(tmp_path)
    facts = {f.id: f for f in net.PLUGIN.manifest_facts(tmp_path, manifest, []) if f.kind == "dependency"}
    assert facts["dependency:skiasharp"].value == "SkiaSharp 3.119.0"
    assert facts["dependency:bitmiracle.libtiff.net"].value == "BitMiracle.LibTiff.NET 2.4.649"
    registry = facts["dependency:microsoft.win32.registry"]
    assert registry.value == "Microsoft.Win32.Registry 5.0.0"
    assert registry.evidence[0].path == "Package/Aspose.Words.FOSS.nuspec"
    assert "(target frameworks .NETStandard2.0)" in registry.evidence[0].detail
    assert facts["dependency:development.ilrepack"].value == "ILRepack 2.0.46"
    # The source-only CodePages reference is not in the published package (dropped Words #9).
    assert "dependency:none" not in facts and "dependency:system.text.encoding.codepages" not in facts


def test_without_a_nuspec_the_referenced_projects_dependencies_count(tmp_path: Path) -> None:
    manifest = _words(tmp_path, nuspec=False)
    facts = {f.id: f for f in net.PLUGIN.manifest_facts(tmp_path, manifest, []) if f.kind == "dependency"}
    assert "dependency:none" not in facts
    skia = facts["dependency:skiasharp"]
    assert skia.evidence[0].path == "Aspose.Foundation/Aspose.Foundation/Aspose.Foundation.csproj"
    assert "ProjectReference" in skia.evidence[0].detail


def test_samples_that_reference_the_project_are_recorded(tmp_path: Path) -> None:
    """Cells .NET: 15 samples, each ``<ProjectReference Include="..\\..\\src\\...csproj" />``."""
    product = '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><PackageId>Aspose.Cells.FOSS</PackageId></PropertyGroup><ItemGroup><PackageReference Include="SkiaSharp" Version="2.88.8" /></ItemGroup></Project>'
    sample = '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include="..\\..\\src\\Aspose.Cells_FOSS\\Aspose.Cells_FOSS.csproj" /></ItemGroup></Project>'
    files = {"src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj": product, "src/Aspose.Cells_FOSS/Workbook.cs": "class Workbook {}\n"}
    for name in ("Basic", "Charts", "Styles"):
        files[f"samples/Samples.{name}/Samples.{name}.csproj"] = sample
    _write(tmp_path, files)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    facts = {f.id: f for f in net.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    record = facts["project_file:samples.product_reference"]
    assert record.attributes["project_reference"] == "3" and record.attributes["package_reference"] == "0"
    assert record.value.startswith("all 3 sample projects reference the product project")


def test_a_repository_without_samples_records_nothing(tmp_path: Path) -> None:
    manifest = _words(tmp_path)
    assert not any(f.kind == "project_file" for f in net.PLUGIN.manifest_facts(tmp_path, manifest, []))
