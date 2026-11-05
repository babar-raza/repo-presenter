"""Enum members are facts (owner decision 2026-11-05), of their own kind.

Calibration iteration 4 found README enum names (`Axis.X_AXIS`, `SaveFormat.Pdf`) cited no fact:
the vendored engine read every enum's members and the surface dropped them. They now become
``enum_member`` facts, which the name checks accept and nothing that counts, lists or caps public
symbols ever sees.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.grammars import get_parser
from repo_presenter.extractors.surface.extractor import (
    SurfaceSymbol,
    enum_member_facts,
    surface_symbols,
    with_enum_members,
)
from repo_presenter.readme.review import clearances, evidence


def _enum(value: str, *members: str) -> SurfaceSymbol:
    return SurfaceSymbol(value, "enum", "src/Axis.cs", 3, enum_members=members)


def _symbol_fact(value: str, kind: str = "enum") -> Fact:
    return Fact(
        f"public_symbol:{value.lower()}",
        "public_symbol",
        value,
        (Evidence("src/Axis.cs"),),
        attributes={"symbol_kind": kind},
    )


def test_each_member_is_one_fact_with_its_enum_and_evidence() -> None:
    facts = enum_member_facts([_enum("W.Axis", "X_AXIS", "Y_AXIS", "X_AXIS")])
    assert [f.value for f in facts] == ["W.Axis.X_AXIS", "W.Axis.Y_AXIS"]
    assert {f.kind for f in facts} == {"enum_member"}
    assert facts[0].id == "enum_member:w.axis.x_axis"
    assert facts[0].attributes == {"enum": "W.Axis"}
    assert "member of enum W.Axis" in facts[0].evidence[0].detail


def test_an_enum_the_plugin_left_out_of_its_surface_contributes_no_member() -> None:
    symbols = [_enum("W.Axis", "X_AXIS"), _enum("W.Hidden", "SECRET")]
    out = with_enum_members([_symbol_fact("W.Axis")], symbols)
    assert [f.value for f in out if f.kind == "enum_member"] == ["W.Axis.X_AXIS"]


def test_the_csharp_engine_hands_its_enum_members_through(tmp_path: Path) -> None:
    package = tmp_path / "src" / "W"
    package.mkdir(parents=True)
    (package / "Axis.cs").write_text(
        "namespace W {\n public enum Axis { XAxis = 0, YAxis = 1 }\n"
        " public class Box { public int Size { get; set; } }\n}\n",
        encoding="utf-8",
    )
    symbols = surface_symbols(get_parser("csharp"), "csharp", package, tmp_path, "w")
    members = {f.value for f in enum_member_facts(symbols)}
    assert members == {"W.Axis.XAxis", "W.Axis.YAxis"}
    # A class's members are not enum members.
    assert not any(value.startswith("W.Box.") for value in members)


def _doc(*facts: Fact) -> FactsDocument:
    return FactsDocument("org/W", "a" * 40, facts)


def test_a_name_denial_of_an_enum_member_is_cleared_by_its_fact() -> None:
    member = enum_member_facts([_enum("W.Axis", "X_AXIS")])[0]
    names = clearances._supported_names(_doc(_symbol_fact("W.Axis"), member))
    assert names["W.Axis.X_AXIS"] == "enum_member:w.axis.x_axis"


def test_a_review_unit_carries_the_members_it_names_and_no_other() -> None:
    members = enum_member_facts([_enum("W.Axis", "X_AXIS", "Y_AXIS", "Z_AXIS")])
    document = _doc(_symbol_fact("W.Axis"), *members)
    carried = {
        record["id"]
        for record in evidence.unit_facts(
            document, "Set the up axis to `Axis.X_AXIS`.", sections=["intro"]
        )
    }
    assert "enum_member:w.axis.x_axis" in carried
    assert not {"enum_member:w.axis.y_axis", "enum_member:w.axis.z_axis"} & carried
