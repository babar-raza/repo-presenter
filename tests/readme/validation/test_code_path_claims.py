"""BC-14 rule (j) extended (BL-062 K02, BL-066 K06): claims beyond the real code path and the
published package are caught deterministically before sealing.

Every positive sentence is a registered false claim, verbatim from ``data/readme_findings.json``
(the sealed README line it was printed on); every rule has a negative control from the same
README that states the truth and must pass.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.claims import claim_findings

REVISION = "b" * 40


def _fact(identifier: str, kind: str, value: str, polarity: str = "SUPPORTED", **attributes: str) -> Fact:
    return Fact(identifier, kind, value, (Evidence("src/x"),), polarity=polarity, attributes=attributes or None)  # type: ignore[arg-type]


def _doc(*extra: Fact) -> FactsDocument:
    return FactsDocument("org/repo", REVISION, (_fact("package:name", "package", "Aspose.X.FOSS"), *extra))


def _findings(text: str, facts: FactsDocument) -> list:
    return [f for f in claim_findings(text + "\n", facts) if "the README" in f.detail]


def _symbol(value: str, kind: str = "method", **attributes: str) -> Fact:
    return _fact(f"public_symbol:{value.lower()}", "public_symbol", value, symbol_kind=kind, **attributes)


def _impl(identifier: str, value: str, **attributes: str) -> Fact:
    return _fact(f"implementation:{identifier}", "implementation", value, **attributes)


# --- (j2) never-thrown exceptions (Cells C++, 3D Python) --------------------------------------

_NEVER = (
    _symbol("Aspose.Cells_FOSS.FormulaException", "class"),
    _symbol("Aspose.Cells_FOSS.StyleException", "class"),
    _impl("never_thrown.aspose.cells_foss.formulaexception", "x", aspect="never_thrown", member="Aspose.Cells_FOSS.FormulaException"),
    _impl("never_thrown.aspose.cells_foss.styleexception", "x", aspect="never_thrown", member="Aspose.Cells_FOSS.StyleException"),
)


def test_a_throw_claim_for_a_never_thrown_exception_is_caught() -> None:
    row = (
        "- **Read and write cell values and formulas.** It writes values of multiple types—including "
        "strings, integers, doubles, and booleans—via `Cell.PutValue`, retrieves them as a "
        "variant-typed `CellValue`, and sets or reads formulas with `Cell.SetFormula` and "
        "`Cell.GetFormula`, throwing `FormulaException` for invalid formulas."
    )
    [finding] = _findings(row, _doc(*_NEVER))
    assert "`FormulaException` is thrown" in finding.detail


def test_an_exception_list_item_saying_when_it_is_raised_is_caught() -> None:
    findings = _findings("  - `FormulaException` / `StyleException` — invalid formula text or style value", _doc(*_NEVER))
    assert {f.detail.split("`")[1] for f in findings} == {"FormulaException", "StyleException"}


def test_a_python_api_row_from_the_commercial_doc_comment_is_caught() -> None:
    facts = _doc(
        _symbol("aspose.threed.TrialException", "class"),
        _impl("never_thrown.aspose.threed.trialexception", "x", aspect="never_thrown", member="aspose.threed.TrialException"),
    )
    [finding] = _findings("| `TrialException` | This is raised in Scene.Open/Scene.Save when no licenses are applied. |", facts)
    assert "TrialException" in finding.detail


def test_a_row_that_says_the_exception_is_not_applicable_passes() -> None:
    facts = _doc(_impl("never_thrown.t", "x", aspect="never_thrown", member="Aspose.ThreeD.TrialException"))
    assert not _findings("| `TrialException` | Trial-related exception (not applicable to this open-source edition). |", facts)
    # No fact, no judgement: a thrown exception named in the same shape is left alone.
    assert not _findings("- throwing `UnsupportedFeatureException` for other formats", _doc(*_NEVER))


# --- (j3) a static instance whose member only throws (3D .NET FileFormat) ---------------------

_STATIC = (
    _impl(
        "throws.aspose.threed.fileformat.wavefrontobj.createsaveoptions.notimplementedexception",
        "x",
        aspect="throws",
        member="Aspose.ThreeD.FileFormat.WavefrontOBJ.CreateSaveOptions",
        field="Aspose.ThreeD.FileFormat.WavefrontOBJ",
        via="Aspose.ThreeD.FileFormat.CreateSaveOptions",
        exception="NotImplementedException",
        condition="always",
        dispatch="static_instance",
    ),
)


def test_static_format_instances_sold_for_save_are_caught() -> None:
    row = (
        "| `FileFormat` | File format registry — `Detect`/`GetFormatByExtension` plus per-format static "
        "members (`WavefrontOBJ`, `STLBinary`, `GLTF2`, `Collada`, `Discreet3DS`, `Microsoft3MF`) used "
        "with `Scene.Save()`/`FromFile()`. |"
    )
    [finding] = _findings(row, _doc(*_STATIC))
    assert "`WavefrontOBJ`" in finding.detail


def test_naming_a_working_instance_or_stating_the_limit_passes() -> None:
    assert not _findings("Save a 3DS file with `Scene.Save()` and `FileFormat.Discreet3DS`.", _doc(*_STATIC))
    assert not _findings("`WavefrontOBJ` is not usable with `Scene.Save()` in this build.", _doc(*_STATIC))


# --- (j4) "throws NotImplementedException" for a body that holds no throw (3D .NET) -------------


def test_a_member_said_to_throw_whose_body_does_not_is_caught() -> None:
    facts = _doc(
        _symbol("Aspose.ThreeD.Entities.NurbsSurface", "class"),
        _symbol("Aspose.ThreeD.Entities.NurbsSurface.ToMesh", body_throws="no"),
        _symbol("Aspose.ThreeD.Entities.NurbsCurve.Evaluate"),
        _impl("throws.nurbscurve.evaluate", "x", aspect="throws", member="Aspose.ThreeD.Entities.NurbsCurve.Evaluate", condition="always", exception="NotImplementedException"),
    )
    row = (
        "- `PolygonModifier`, `TriMesh` helpers, `NurbsCurve.Evaluate`/`EvaluateAt`, and "
        "`NurbsSurface.ToMesh` throw `NotImplementedException`, and `Microsoft3MFFormat` metadata and "
        "`RvmFormat.LoadAttributes` are not implemented."
    )
    [finding] = _findings(row, facts)
    assert "`NurbsSurface.ToMesh`" in finding.detail


def test_a_type_said_to_throw_whose_methods_all_return_is_caught() -> None:
    members = [f"Create{name}" for name in ("RenderTexture", "Pipeline", "VertexBuffer")]
    facts = _doc(
        _symbol("Aspose.ThreeD.Render.RenderFactory", "class"),
        *(_symbol(f"Aspose.ThreeD.Render.RenderFactory.{m}") for m in members),
        *(
            _impl(f"returns.{m.lower()}", f"{m} always returns null", aspect="constant_return", member=f"Aspose.ThreeD.Render.RenderFactory.{m}", returns="null")
            for m in members
        ),
        _symbol("Aspose.ThreeD.Scene.Render"),
        _impl("throws.scene.render", "x", aspect="throws", member="Aspose.ThreeD.Scene.Render", condition="always", exception="NotImplementedException"),
    )
    row = (
        "- Rendering is not implemented in this FOSS build — `Scene.Render`, `RenderFactory`, and the "
        "`IRenderTarget`/`IRenderWindow` rendering pipeline all throw `NotImplementedException`."
    )
    [finding] = _findings(row, facts)
    assert "`RenderFactory`" in finding.detail
    # Negative control: the stub that really throws, alone, passes.
    assert not _findings("- `Scene.Render` throws `NotImplementedException`.", facts)


def test_a_member_named_in_an_earlier_clause_is_not_the_subject() -> None:
    facts = _doc(_symbol("Aspose.ThreeD.Scene.Save", body_throws="no"), _symbol("Aspose.ThreeD.Scene.Open", body_throws="no"))
    row = (
        "- PLY import and export work through `Scene.Open` and `Scene.Save`, but the public "
        "`FileFormat.PLY` field and its Encode/Decode methods throw `NotImplementedException`."
    )
    assert not _findings(row, facts)


# --- (j1) a capability whose member the source states is a stub (3D Python Material) ----------


def test_a_row_offering_a_stub_members_capability_is_caught() -> None:
    facts = _doc(
        _symbol("aspose.threed.shading.Material", "class", signature="class Material(A3DObject)"),
        _symbol("aspose.threed.shading.Material.get_texture"),
        _impl("throws.material.get_texture", "x", aspect="throws", member="aspose.threed.shading.Material.get_texture", condition="always", exception="NotImplementedError"),
    )
    row = (
        "| `Material` | Material class lets you manage texture maps and custom properties, supporting "
        "specular, diffuse, emissive, ambient, and normal maps. |"
    )
    [finding] = _findings(row, facts)
    assert "Material.get_texture" in finding.detail


def test_an_abstract_member_a_subclass_implements_is_not_a_stub() -> None:
    """``Exporter.supports_format`` raises in the base; ``ObjExporter`` implements it."""
    facts = _doc(
        _symbol("aspose.threed.formats.Exporter", "class", signature="class Exporter"),
        _symbol("aspose.threed.formats.Exporter.export"),
        _symbol("aspose.threed.formats.obj.ObjExporter", "class", signature="class ObjExporter(Exporter)"),
        _symbol("aspose.threed.formats.obj.ObjExporter.export"),
        _impl("throws.exporter.export", "x", aspect="throws", member="aspose.threed.formats.Exporter.export", condition="always", exception="NotImplementedError"),
    )
    assert not _findings("| `Exporter` | Exporter objects let you export a scene to a stream. |", facts)


# --- (j5) a format reachable only through a stub (3D Python .dae export) ----------------------

_DAE = (
    _fact("format:output.dae", "format", ".dae", "UNRESOLVED", code_path="stub"),
    _fact("format:input.dae", "format", ".dae"),
    _fact("format:output.obj", "format", ".obj"),
)


def test_exporting_an_unreachable_format_is_caught() -> None:
    row = (
        "- **Export to common 3D formats.** It exports scenes to `.3mf`, `.dae`, `.glb`, `.gltf`, `.obj`, "
        "and `.stl` formats using `Scene.save()` with format-specific `SaveOptions` subclasses."
    )
    [finding] = [f for f in _findings(row, _doc(*_DAE)) if ".dae output" in f.detail]
    assert "format:output.dae" in finding.detail


def test_a_named_format_in_reads_and_writes_is_caught() -> None:
    row = (
        "Aspose.3D FOSS for Python reads and writes OBJ, STL, glTF, and COLLADA files, and provides "
        "classes for mesh, curve, geometry, and shading operations."
    )
    assert any(".dae output" in f.detail for f in _findings(row, _doc(*_DAE)))


def test_reading_the_format_or_disclaiming_its_export_passes() -> None:
    assert not [f for f in _findings("It reads `.dae` files with `Scene.open()`.", _doc(*_DAE)) if ".dae" in f.detail]
    assert not [f for f in _findings("COLLADA files can be read, but export to `.dae` is not supported.", _doc(*_DAE)) if ".dae" in f.detail]


# --- (j6, K06) "no dependencies" while the published package declares some (Words .NET) --------


def test_no_dependencies_against_the_published_package_is_caught() -> None:
    facts = _doc(_fact("dependency:skiasharp", "dependency", "SkiaSharp 3.119.0"), _fact("dependency:development.ilrepack", "dependency", "ILRepack 2.0.46"))
    row = (
        "No required third-party package dependencies; in `Aspose.Words/Aspose.Words.csproj`, no "
        "`PackageReference` a consumer would install is declared."
    )
    [finding] = _findings(row, facts)
    assert "SkiaSharp 3.119.0" in finding.detail


def test_a_feature_without_dependencies_or_a_package_without_them_passes() -> None:
    pillow = _doc(_fact("dependency:pillow-10.1.0", "dependency", "Pillow>=10.1.0"))
    assert not _findings("- `Pillow` >=10.1.0 — used only for PNG rendering; SVG output has no third-party dependency.", pillow)
    only_dev = _doc(_fact("dependency:development.ilrepack", "dependency", "ILRepack 2.0.46"), _fact("dependency:none", "dependency", "none"))
    assert not _findings("No required third-party package dependencies.", only_dev)


# --- (j7, K06) samples said to use the package (Cells .NET) ----------------------------------

_SAMPLES = _fact(
    "project_file:samples.product_reference",
    "project_file",
    "all 15 sample projects reference the product project by ProjectReference; none references the published package",
    aspect="sample_reference",
    samples="15",
    project_reference="15",
    package_reference="0",
    package="Aspose.Cells.FOSS",
)


def test_samples_said_to_use_the_package_version_are_caught() -> None:
    row = (
        "- **[samples/](samples/README.md)** — The samples directory contains example projects "
        "demonstrating how to use `Aspose.Cells.FOSS` version 26.10.0 to work with Excel files."
    )
    [finding] = _findings(row, _doc(_SAMPLES))
    assert "ProjectReference" in finding.detail


def test_a_readme_code_example_is_not_a_sample_project() -> None:
    row = "The first example reads a MSG file and prints its subject line using `Aspose.Cells.FOSS` version 26.10.0 for net8.0."
    assert not _findings(row, _doc(_SAMPLES))
