"""BL-870: "`fieldOfViewX`/`Y`" is one member and its sibling's last letter, never a list that starts with a member `Y`.

Real shape: Aspose.3D FOSS for TypeScript at 66cb26d, the maintainers' Camera row (README line 255). Hosted Lane R
refresh run 45006966944 (2026-11-22) kept failing on it: BC-14 "the README names `Y` as a property of `Camera`" refused
to keep the true row (every listed member is a SUPPORTED fact, `fieldOfViewY` among them), so S4's SUPERSEDE_REDUNDANT
stood and the replacement lost moveForward, orthoHeight and fieldOfViewX (BC-05, BC-17: 'no LLM review ... BC-05,
BC-17'). A zero-call replay of the stored seal's facts reproduced all of it and, with 047.table kept, ends clean."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.claims import _lines
from repo_presenter.readme.validation.surface_claims import _kind_lists, surface_findings

ROW = (
    "A viewpoint node entity with `moveForward` and `getBoundingBox` methods, and `nearPlane`, `farPlane`, `aspect`, "
    "`orthoHeight`, `fieldOfView`, `fieldOfViewX`/`Y`, `projectionType`, and `apertureMode` properties."
)
MEMBERS = (
    "moveForward getBoundingBox nearPlane farPlane aspect orthoHeight fieldOfView fieldOfViewX fieldOfViewY "
    "projectionType apertureMode"
).split()


def _facts() -> FactsDocument:
    facts = [
        Fact("identity:ecosystem", "identity", "typescript", (Evidence("x.ts", "line 1"),)),
        Fact("public_symbol:camera", "public_symbol", "Camera", (Evidence("Camera.ts", "line 1; class;"),),
             attributes={"symbol_kind": "class", "declaration": "export class Camera extends Entity"}),
    ]
    for name in MEMBERS:
        kind = "method" if name in ("moveForward", "getBoundingBox") else "property"
        facts.append(
            Fact(f"public_symbol:camera.{name.lower()}", "public_symbol", f"Camera.{name}",
                 (Evidence("Camera.ts", "line 2; property;"),),
                 attributes={"symbol_kind": kind, "member_kind": kind})
        )
    return FactsDocument("a/b", "0" * 40, tuple(facts))


def _table(description: str) -> str:
    return f"| Class | Description |\n|---|---|\n| `Camera` | {description} |\n"


def _details(description: str) -> list[str]:
    return [f.detail for f in surface_findings(_lines(_table(description)), _facts())]


def test_the_shorthand_is_not_a_member_named_y() -> None:
    assert _details(ROW) == []


def test_the_property_list_keeps_its_other_items() -> None:
    lists = {claimed: [name for name, _ in items] for _, _, claimed, items, _ in _kind_lists(ROW)}
    assert lists["property"] == ["projectionType", "apertureMode"]
    assert lists["method"] == ["moveForward", "getBoundingBox"]


def test_negative_control_a_real_missing_member_after_the_shorthand_is_still_flagged() -> None:
    found = _details(ROW.replace("`apertureMode`", "`noSuchThing`"))
    assert any("`noSuchThing`" in d and "no such member" in d for d in found)


def test_negative_control_a_one_letter_member_that_is_not_a_shorthand_is_still_flagged() -> None:
    found = _details("A node entity with `Y` and `aspect` properties.")
    assert any("`Y`" in d and "no such member" in d for d in found)


def test_negative_control_a_longer_name_after_a_slash_is_still_held_to_the_members() -> None:
    found = _details("A node entity with `fieldOfViewX`/`Bogus`, `aspect` and `farPlane` properties.")
    assert any("`Bogus`" in d for d in found)
