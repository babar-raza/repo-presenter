"""BL-080: member-kind lists in Core API rows, from the real 3D Python hosted run 43513034263.

That Lane R run was REJECTed with 42 blocking findings; 41 were ``claim_contradiction`` "the README
calls `X.y` a method ..., but the facts record it as a property". Every row below is verbatim from
the run's log and every fact is the shape the extractor records at 65b1f577 (``member_kind`` /
``settable`` on members, a ``class X`` signature on types). Two classes:

* 16 findings were the rule misreading the row: the kind word belonged to a verb ("holds control
  points, deformers, and provides methods to add ...") or started a new conjunct ("read-only
  properties for key and compound, and methods to add tokens"), or the list was the infinitives
  after "methods to" ("methods to find, get, and remove properties"). Those are no longer findings.
* 25 were true (an authored row called ``x``/``y`` properties "methods"). The renderer now spells
  that kind word "members" (``surface_claims.kind_true_text``), which the same rule accepts.
"""

from __future__ import annotations

from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.surface_claims import MemberIndex, kind_true_text
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _facts, _plan

KIND = "call it by its kind"


def _type(value: str) -> Fact:
    return Fact(
        f"public_symbol:{value.lower()}",
        "public_symbol",
        value,
        (Evidence("aspose/threed/x.py", "line 1; class; public by name"),),
        attributes={"symbol_kind": "class", "signature": f"class {value.rsplit('.', 1)[-1]}"},
    )


def _member(value: str, kind: str, settable: str | None = None) -> Fact:
    attributes = {
        "symbol_kind": "method",
        "member_kind": kind,
        "signature": f"def {value.rsplit('.', 1)[-1]}(self)",
    }
    if settable is not None:
        attributes["settable"] = settable
    return Fact(
        f"public_symbol:{value.lower()}",
        "public_symbol",
        value,
        (Evidence("aspose/threed/x.py", "line 2; method; public by name"),),
        attributes=attributes,
    )


def _members(owner: str, kinds: dict[str, str]) -> list[Fact]:
    return [
        _member(f"{owner}.{name}", kind, "true" if kind == "property" else None)
        for name, kind in kinds.items()
    ]


TYPES: dict[str, dict[str, str]] = {
    "aspose.threed.entities.Geometry": {
        "control_points": "property", "deformers": "property", "add_element": "method",
        "create_element": "method", "find_property": "method", "get_bounding_box": "method",
        "remove_property": "method", "get_entity_renderer_key": "method",
    },
    "aspose.threed.PropertyCollection": {
        "count": "property", "find_property": "method", "get": "method",
        "remove_property": "method",
    },
    "aspose.threed.formats.ColladaFormat": {
        "can_export": "property", "can_import": "property", "content_type": "property",
        "extension": "property", "version": "property", "create_load_options": "method",
        "create_save_options": "method",
    },
    "aspose.threed.formats.fbx.FbxElement": {
        "key": "property", "compound": "property", "add_token": "method",
        "set_compound": "method",
    },
    "aspose.threed.utilities.FVector2": {
        "x": "property", "y": "property", "dot": "method", "length": "method",
        "normalize": "method", "parse": "method",
    },
    "aspose.threed.utilities.Vector4": {
        "x": "property", "y": "property", "z": "property", "w": "property", "set": "method",
    },
}


def _threed() -> FactsDocument:
    base = _facts()
    symbols: list[Fact] = []
    for owner, kinds in TYPES.items():
        symbols += [_type(owner), *_members(owner, kinds)]
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *symbols))


#: Verbatim rows of run 43513034263 the rule misread (the kind word qualifies none of the names).
MISREAD = [
    ("Geometry", "Geometry class holds control points, deformers, and provides methods to add and "
     "create elements, find properties, get its bounding box, and remove properties, and its "
     "get_entity_renderer_key method is not implemented."),
    ("PropertyCollection", "PropertyCollection class holds a count and provides methods to find, "
     "get, and remove properties."),
    ("ColladaFormat", "ColladaFormat class represents the Collada file format with read-only "
     "properties for export and import support, content type, file extension, and version, and "
     "provides methods to create load and save options."),
    ("FbxElement", "FbxElement class represents an FBX parser element with read-only properties "
     "for key and compound, and methods to add tokens and set the compound."),
]
#: Verbatim rows of the same run that really call properties methods.
MISNAMED = [
    ("FVector2", "FVector2 class provides two-dimensional floating-point vector functionality with "
     "x, y, dot, length, normalize, and parse methods, where parse raises ValueError conditionally.",
     {"x", "y"}),
    ("Vector4", "Vector4 class provides four-dimensional vector functionality with x, y, z, w, and "
     "set methods.", {"x", "y", "z", "w"}),
]


def _row(name: str, text: str) -> str:
    return f"## API Reference\n\n| Class | Description |\n| --- | --- |\n| `{name}` | {text} |\n"


def _kind_findings(readme: str, facts: FactsDocument) -> list[str]:
    return [f.detail for f in claim_findings(readme, facts) if KIND in f.detail]


@pytest.mark.parametrize(("name", "text"), MISREAD)
def test_a_kind_word_that_qualifies_no_listed_name_is_not_a_finding(name: str, text: str) -> None:
    assert _kind_findings(_row(name, text), _threed()) == []


@pytest.mark.parametrize(("name", "text", "wrong"), MISNAMED)
def test_a_list_that_calls_properties_methods_is_still_a_finding(
    name: str, text: str, wrong: set[str]
) -> None:
    details = _kind_findings(_row(name, text), _threed())
    assert {d.split("`")[1].split(".")[1] for d in details} == wrong


@pytest.mark.parametrize(("name", "text", "wrong"), MISNAMED)
def test_the_kind_true_text_names_them_members_and_passes_the_rule(
    name: str, text: str, wrong: set[str]
) -> None:
    facts = _threed()
    index = MemberIndex(facts)
    owner = index.resolve(name)[0]
    fixed = kind_true_text(text, owner, facts, index)
    assert fixed == text.replace(" methods", " members", 1)
    assert _kind_findings(_row(name, fixed), facts) == []


@pytest.mark.parametrize(("name", "text"), MISREAD)
def test_a_row_the_rule_does_not_refute_is_left_as_written(name: str, text: str) -> None:
    facts = _threed()
    index = MemberIndex(facts)
    assert kind_true_text(text, index.resolve(name)[0], facts, index) == text


def test_a_correctly_named_list_is_left_as_written() -> None:
    facts = _threed()
    index = MemberIndex(facts)
    text = "FVector2 has the x and y properties and the dot, length and normalize methods."
    assert kind_true_text(text, index.resolve("FVector2")[0], facts, index) == text
    assert _kind_findings(_row("FVector2", text), facts) == []


def _units_with(rows: list[tuple[str, str]]) -> dict[str, Any]:
    facts = _threed()
    index = MemberIndex(facts)
    extra = [
        {
            "section": "api_reference",
            "slot": f"type:{index.resolve(name)[0].id}",
            "text": text,
            "fact_ids": [index.resolve(name)[0].id],
        }
        for name, text in rows
    ]
    return {**UNITS, "units": [*UNITS["units"], *extra]}


def test_the_renderer_prints_the_authored_rows_kind_true() -> None:
    """End to end: the authored type units of the run, rendered, pass the rule; the misnamed rows
    print "members", the misread rows print exactly as authored."""
    facts = _threed()
    rows = [(name, text) for name, text, _ in MISNAMED] + MISREAD
    readme = render_readme(ENTRY, facts, _plan(), _units_with(rows), _dispositions())
    assert _kind_findings(readme, facts) == []
    for name, text, _ in MISNAMED:
        assert f"| `{name}` | {text.replace(' methods', ' members', 1)} |" in readme
    for name, text in MISREAD:
        assert f"| `{name}` | {text} |" in readme


def test_negative_control_the_authored_rows_as_written_are_refused() -> None:
    facts = _threed()
    readme = "\n".join(_row(name, text) for name, text, _ in MISNAMED)
    assert len(_kind_findings(readme, facts)) == 6
