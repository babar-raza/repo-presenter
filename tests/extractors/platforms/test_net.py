"""The .NET plugin supplies what is .NET's own and leaves the rest to the shared facades.

Ported (REUSE for manifest/registry coverage) from the old repository-presenter project's
``tests/components/readme/extractors/platforms/test_net.py`` per migration/reuse-manifest.yaml.

Three tests from the old file are deliberately NOT ported, matching the trims documented in
``extractors/platforms/net.py``'s own docstring:
- ``test_surface_facts_come_from_the_shared_extractor_with_slug_safe_values`` (needs the
  unported tree-sitter surface engine; this plugin's ``surface_facts`` always returns ``[]``).
- ``test_the_manifests_own_build_is_driven_once_and_measured_with_no_example`` (needs the
  unported ``net_examples``/``core.execution`` toolchain runner; this plugin defines no
  ``verify_build`` at all, so ``extractors.platforms.registry.verify_build`` answers
  "not attempted" for it, which is covered by that module's own test).
- ``test_the_plugin_imports_no_sibling_ecosystem`` is replaced by a version matching this
  plugin's real (smaller) import set, since the old assertion encoded the old repo's import
  list verbatim.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repo_presenter.extractors.platforms import net
from repo_presenter.extractors.platforms.registry import known_ecosystems, plugin_for
from repo_presenter.core.examples import ExampleCandidate
from repo_presenter.core.facts import Fact

CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <PackageId>Aspose.Widget</PackageId>
    <Version>1.2.3</Version>
    <TargetFrameworks>net8.0;net6.0</TargetFrameworks>
  </PropertyGroup>
</Project>
"""
WIDGET = """
namespace Aspose.Widget
{
    /// <summary>A widget.</summary>
    public class Widget
    {
        public string Name { get; set; }
        public void Save(string path) { }
    }
}
"""


def _repository(root: Path) -> list[str]:
    source = root / "src" / "Aspose.Widget"
    source.mkdir(parents=True)
    (source / "Aspose.Widget.csproj").write_text(CSPROJ, encoding="utf-8")
    (source / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    sample = root / "samples" / "Demo"
    sample.mkdir(parents=True)
    (sample / "Demo.csproj").write_text(CSPROJ, encoding="utf-8")
    return ["src/Aspose.Widget/Aspose.Widget.csproj", "src/Aspose.Widget/Widget.cs"]


def test_the_plugin_is_discovered_by_module_name() -> None:
    assert plugin_for("net") is net.PLUGIN
    assert "net" in known_ecosystems()


def test_the_governing_manifest_is_the_product_project_not_a_sample(tmp_path: Path) -> None:
    """Depth cannot separate two project files at the same level; sources beside them can."""
    _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "src/Aspose.Widget/Aspose.Widget.csproj"


CONSOLE = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <PackageId>Aspose.Widget.Converter</PackageId>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\\main\\Aspose.Widget\\Aspose.Widget.csproj" />
  </ItemGroup>
</Project>
"""
UNDECLARED_TESTS = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="NUnit" version="4.2.2" />
  </ItemGroup>
</Project>
"""
BUILD_PROPS = """<Project>
  <PropertyGroup>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>
</Project>
"""


def test_a_console_tool_one_level_up_does_not_outrank_the_library(tmp_path: Path) -> None:
    """Measured on Aspose.3D for .NET: depth chose the converter, not the product.

    `src/converter/Converter.csproj` is one directory above `src/main/Aspose.ThreeD/`, and its
    only source declares no public type, so the repository produced zero public symbols and the
    API Reference row had no evidence at all. `OutputType` says which one is an application.
    """
    library = tmp_path / "src" / "main" / "Aspose.Widget"
    library.mkdir(parents=True)
    (library / "Aspose.Widget.csproj").write_text(CSPROJ, encoding="utf-8")
    (library / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    console = tmp_path / "src" / "converter"
    console.mkdir(parents=True)
    (console / "Converter.csproj").write_text(CONSOLE, encoding="utf-8")
    (console / "Program.cs").write_text("internal class Program { }\n", encoding="utf-8")

    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    where = manifest.relative_to(tmp_path).as_posix()
    assert where == "src/main/Aspose.Widget/Aspose.Widget.csproj"


def test_a_shared_property_file_at_the_root_never_governs(tmp_path: Path) -> None:
    """`Directory.Build.props` only lends properties to the projects beside it, and sits where
    depth always prefers it - so the surface was read from the whole tree, tests and samples
    included, before this ranking."""
    library = tmp_path / "src" / "Aspose.Widget"
    library.mkdir(parents=True)
    (library / "Aspose.Widget.csproj").write_text(CSPROJ, encoding="utf-8")
    (library / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    (tmp_path / "Directory.Build.props").write_text(BUILD_PROPS, encoding="utf-8")

    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "src/Aspose.Widget/Aspose.Widget.csproj"


def test_a_test_project_that_declares_nothing_is_still_a_test_project(tmp_path: Path) -> None:
    """A test project declaring no `IsTestProject`/`IsPackable`/`OutputType`, sitting at the
    same depth as the product and sorting before it, is still caught by a reference to a test
    runner."""
    library = tmp_path / "Aspose.Widget"
    library.mkdir(parents=True)
    (library / "Aspose.Widget.csproj").write_text(CSPROJ, encoding="utf-8")
    (library / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    suite = tmp_path / "Aspose.JavaMs.Tests"
    suite.mkdir(parents=True)
    (suite / "Aspose.JavaMs.Tests.csproj").write_text(UNDECLARED_TESTS, encoding="utf-8")
    (suite / "WidgetTests.cs").write_text(WIDGET, encoding="utf-8")

    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    assert manifest.relative_to(tmp_path).as_posix() == "Aspose.Widget/Aspose.Widget.csproj"


DEPENDENT = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <PackageId>Aspose.Widget</PackageId>
    <TargetFrameworks>net10.0;net6.0;netcoreapp3.1</TargetFrameworks>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="SkiaSharp" Version="2.88.8" />
    <PackageReference Include="SonarAnalyzer.CSharp" Version="10.33.0" PrivateAssets="all" />
    <PackageReference Include="ILRepack" Version="2.0.46" ExcludeAssets="all" />
    <ProjectReference Include="..\\Other\\Other.csproj" />
  </ItemGroup>
</Project>
"""


def test_a_package_reference_becomes_a_dependency_and_a_private_one_is_development(
    tmp_path: Path,
) -> None:
    """A reference a consumer never installs is a development dependency. A `ProjectReference`
    is not a package a reader installs at all."""
    source = tmp_path / "src" / "Aspose.Widget"
    source.mkdir(parents=True)
    (source / "Aspose.Widget.csproj").write_text(DEPENDENT, encoding="utf-8")
    (source / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in net.PLUGIN.manifest_facts(tmp_path, manifest, [])}

    assert facts["dependency:skiasharp"].value == "SkiaSharp 2.88.8"
    assert (
        facts["dependency:development.sonaranalyzer.csharp"].value == "SonarAnalyzer.CSharp 10.33.0"
    )
    assert facts["dependency:development.ilrepack"].value == "ILRepack 2.0.46"
    assert "dependency:none" not in facts
    assert not any("other" in fact_id for fact_id in facts)
    floor = facts["package:target_framework"]
    assert floor.value == "netcoreapp3.1;net6.0;net10.0"
    assert (floor.attributes or {}).get("floor_declaration") == "TargetFrameworks"


def test_a_project_with_no_package_reference_proves_a_verified_zero(tmp_path: Path) -> None:
    """3D, Email and Slides for .NET declare none, which the contract renders as a sentence."""
    _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in net.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    marker = facts["dependency:none"]
    assert marker.value == "none" and marker.polarity == "SUPPORTED"
    assert marker.evidence[0].path == "src/Aspose.Widget/Aspose.Widget.csproj"
    assert "PackageReference" in (marker.evidence[0].detail or "")


def test_the_broadest_target_framework_orders_first() -> None:
    """netstandard runs everywhere; netcoreapp and net5+ are one lineage; net48 is another."""
    targets = ["net48", "net10.0", "netcoreapp3.1", "netstandard2.0", "net6.0"]
    assert sorted(targets, key=net._framework_order) == [
        "netstandard2.0",
        "netcoreapp3.1",
        "net6.0",
        "net10.0",
        "net48",
    ]
    assert net._framework_order("uap10.0")[0] == 3


def test_a_project_file_that_will_not_parse_still_ranks(tmp_path: Path) -> None:
    """A malformed project claims nothing rather than raising: the remaining keys rank it."""
    broken = tmp_path / "Aspose.Broken"
    broken.mkdir(parents=True)
    (broken / "Aspose.Broken.csproj").write_text("<Project", encoding="utf-8")
    assert net._declares(broken / "Aspose.Broken.csproj") == (False, False)
    assert net.PLUGIN.detect_manifest(tmp_path) == broken / "Aspose.Broken.csproj"


def test_manifest_facts_carry_identity_version_framework_and_the_install_command(
    tmp_path: Path,
) -> None:
    tree = _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {fact.id: fact for fact in net.PLUGIN.manifest_facts(tmp_path, manifest, tree)}
    assert facts["package:name"].value == "Aspose.Widget"
    assert facts["package:version"].value == "1.2.3"
    assert facts["package:target_framework"].value == "net6.0;net8.0"
    install = facts["install_command:dotnet"]
    assert install.value == "dotnet add package Aspose.Widget"
    assert install.polarity == "UNRESOLVED" and install.confidence == 0.5


def test_an_unreadable_registry_leaves_the_install_claim_unresolved(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Silence is not absence: a probe that cannot read must not contradict the claim."""
    tree = _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = net.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        from repo_presenter.extractors.surface.registry import RegistryObservation

        return RegistryObservation("nuget", "Aspose.Widget", None, True, None, None, "offline")

    monkeypatch.setattr(net, "observe", unreadable)
    resolved, probes = net.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["UNRESOLVED"]
    assert probes and probes[0].outcome == "UNRESOLVED"


def test_a_package_the_registry_does_not_carry_contradicts_the_install_claim(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """A registry that answers conclusively "not published" contradicts the install claim."""
    tree = _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = net.PLUGIN.manifest_facts(tmp_path, manifest, tree)

    def absent(*args: Any, **kwargs: Any) -> Any:
        from repo_presenter.extractors.surface.registry import RegistryObservation

        return RegistryObservation(
            "nuget",
            "Aspose.Widget",
            False,
            False,
            "https://api.nuget.org/v3-flatcontainer/aspose.widget/index.json",
            "nuget-api",
            "live_probe",
        )

    monkeypatch.setattr(net, "observe", absent)
    resolved, probes = net.PLUGIN.registry_facts(facts)
    assert [fact.polarity for fact in resolved] == ["CONTRADICTED"]
    assert resolved[0].confidence == 1.0
    assert "distribution not found" in (resolved[0].evidence[-1].detail or "")
    assert probes and probes[0].outcome == "CONTRADICTED"


def test_a_missing_verifier_reports_not_verified_rather_than_failure(tmp_path: Path) -> None:
    """A check this plugin cannot run is UNRESOLVED (NOT_VERIFIED), never CONTRADICTED - true
    both for the old repo's "no toolchain on this machine" case and this pull's deliberate
    non-port of the dotnet-build-backed verifier."""
    candidates = [
        ExampleCandidate(1, "csharp", "var w = new Widget();", "README.md", 1, 3, "unit:001")
    ]
    receipts = net.PLUGIN.verify_examples(tmp_path, [], candidates, tmp_path / "run")
    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]


def test_a_project_with_no_package_id_takes_the_msbuild_default_name(tmp_path: Path) -> None:
    """A project declaring no PackageId still gets an install claim: MSBuild's own default is
    PackageId = AssemblyName = the project file's name, so the claim exists under that name and
    goes through the registry like any other."""
    project = tmp_path / "src" / "Aspose.Gis.Foss" / "Aspose.Gis.Foss.csproj"
    project.parent.mkdir(parents=True)
    project.write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n'
        "    <TargetFramework>net10.0</TargetFramework>\n  </PropertyGroup>\n</Project>\n",
        encoding="utf-8",
    )
    facts = {f.id: f for f in net.PLUGIN.manifest_facts(tmp_path, project, [])}
    assert facts["package:name"].value == "Aspose.Gis.Foss"
    install = facts["install_command:dotnet"]
    assert install.value == "dotnet add package Aspose.Gis.Foss"
    assert install.polarity == "UNRESOLVED"
    assert "manifest" in install.evidence[0].detail
    assert "default" in facts["package:name"].evidence[0].detail


def test_the_plugin_imports_only_core_and_the_shared_surface_facades(tmp_path: Path) -> None:
    """This pull's net.py imports only core/, the shared surface facades, and stdlib - no
    sibling platform module, and (unlike the old repo) no tree-sitter grammars or execution
    toolchain, since surface_facts/verify_examples were deliberately not ported this pass."""
    import ast

    source = Path(net.__file__).read_text("utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(".platforms." in name and not name.endswith(".net") for name in imported)
    assert all(
        name.startswith(
            (
                "repo_presenter.core",
                "repo_presenter.extractors.surface",
                "collections",
                "pathlib",
                "typing",
                "__future__",
                "xml.etree",
            )
        )
        for name in imported
    ), sorted(imported)


def test_every_fact_the_plugin_emits_is_typed_as_a_fact(tmp_path: Path) -> None:
    tree = _repository(tmp_path)
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    for fact in [
        *net.PLUGIN.manifest_facts(tmp_path, manifest, tree),
        *net.PLUGIN.surface_facts(tmp_path, tree),
    ]:
        assert isinstance(fact, Fact)


def test_a_single_target_framework_stays_a_single_value_without_an_override(
    tmp_path: Path,
) -> None:
    """One `TargetFramework` is its own floor: the value and the citation are unchanged."""
    source = tmp_path / "src" / "Aspose.Widget"
    source.mkdir(parents=True)
    (source / "Aspose.Widget.csproj").write_text(
        CSPROJ.replace(
            "<TargetFrameworks>net8.0;net6.0</TargetFrameworks>",
            "<TargetFramework>net8.0</TargetFramework>",
        ),
        encoding="utf-8",
    )
    (source / "Widget.cs").write_text(WIDGET, encoding="utf-8")
    manifest = net.PLUGIN.detect_manifest(tmp_path)
    assert manifest is not None
    facts = {f.id: f for f in net.PLUGIN.manifest_facts(tmp_path, manifest, [])}
    assert facts["package:target_framework"].value == "net8.0"
    assert not (facts["package:target_framework"].attributes or {})
