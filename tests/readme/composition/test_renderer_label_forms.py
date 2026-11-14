"""Lane R's API rows never print a label-only description, and the At a Glance capabilities are
grouped by the verified namespace of the API each cites (BL-005, BL-059).

``capability_categories`` is run on the real plan shape of the sealed Aspose.3D FOSS for .NET
Lane R candidate (03b940a46f7b): "Material assignment" cites ``Aspose.ThreeD.Shading`` types only,
"Scene graph construction" cites ``Aspose.ThreeD``, ``.Entities`` and ``.Profiles`` (no single
namespace, so no category), "Format conversion" cites no type at all."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import _label_only, capability_categories


def _symbol(value: str, kind: str) -> Fact:
    return Fact(
        f"public_symbol:{value}".lower(),
        "public_symbol",
        value,
        (Evidence("src/x.cs", f"line 1; {kind}; public by declaration"),),
        attributes={"symbol_kind": kind},
    )


FACTS = FactsDocument(
    "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
    "a" * 40,
    (
        _symbol("Aspose.ThreeD.Scene", "class"),
        _symbol("Aspose.ThreeD.Node", "class"),
        _symbol("Aspose.ThreeD.Entities.Mesh", "class"),
        _symbol("Aspose.ThreeD.Profiles.Profile", "class"),
        _symbol("Aspose.ThreeD.Shading.PbrMaterial", "class"),
        _symbol("Aspose.ThreeD.Shading.LambertMaterial", "class"),
        _symbol("Aspose.ThreeD.Formats.FbxSaveOptions", "class"),
        _symbol("Aspose.ThreeD.Formats.FbxSaveOptions.EnableCompression", "method"),
    ),
)


def _plan(*cited: tuple[str, ...]) -> dict:
    return {
        "at_a_glance": {"capability_titles": [f"T{i}" for i in range(len(cited))]},
        "core_capabilities": [
            {"title": f"T{i}", "fact_ids": [f"public_symbol:{v}".lower() for v in ids]}
            for i, ids in enumerate(cited)
        ],
    }


def test_a_capability_takes_the_one_namespace_it_cites_below_the_root() -> None:
    plan = _plan(
        ("Aspose.ThreeD.Scene", "Aspose.ThreeD.Entities.Mesh", "Aspose.ThreeD.Profiles.Profile"),
        ("Aspose.ThreeD.Shading.PbrMaterial", "Aspose.ThreeD.Shading.LambertMaterial"),
        (),
        ("Aspose.ThreeD.Formats.FbxSaveOptions.EnableCompression",),
        ("Aspose.ThreeD.Scene", "Aspose.ThreeD.Node"),
    )
    assert capability_categories(plan, FACTS) == ["", "Shading", "", "Formats", ""]


def test_titles_that_do_not_line_up_with_the_plan_get_no_categories() -> None:
    plan = _plan(("Aspose.ThreeD.Shading.PbrMaterial",))
    plan["at_a_glance"]["capability_titles"].append("extra")
    assert capability_categories(plan, FACTS) == []


def test_label_only_descriptions_are_recognised() -> None:
    for label in ("Class with 1 method.", "Interface in the 3D JAVA API.", "Enum with 2 members.",
                  "Created by lexchou on 12/14/2016.", "Public class."):
        assert _label_only(label), label
    for prose in ("Segment of CompositeCurve.", "Enumerates DIRECT, INDEX and INDEX_TO_DIRECT.",
                  "Class that declares a public no-argument constructor."):
        assert not _label_only(prose), prose
