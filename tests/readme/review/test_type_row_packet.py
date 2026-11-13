"""The review packet for an authored API reference row carries exactly the facts its type unit was
given (``authoring.type_unit_facts``): the type fact, the member names listed with it, and its own
implementation facts.

Aspose.3D-FOSS-for-TypeScript Lane R, hosted run 43430680427 (2026-11-13): sixteen rows written by
the facts-only type objective were filed ``unsupported_claim`` although each is true by the facts,
e.g. "ReferenceMode is a public symbol with members DIRECT, INDEX, and INDEX_TO_DIRECT." and "Scene
is a public symbol with members VERSION, animationClips, ...; ... Scene.render throws Error". The
packet found facts by identifiers and word overlap only: a member written as a plain word
(``DIRECT``, ``clear``) was never an identifier, so no member list reached the reviewer, and a
replay on a local facts build of the same pinned source (66cb26df) left 22 of the rows'
implementation facts out too (``Vertex.readDouble throws Error``...).

Aspose.BarCode-FOSS-for-Python Lane R, run 43430657331: "PngRenderer ... provide PNG rendering
capabilities" rests on the class's own doc comment, which the extractor keeps as
``docstring_full`` ("Render a barcode into PNG output ...") and the packet never showed; the alias
``aspose_barcode_foss.PngRenderer`` is that class only by its evidence ("re-export of ..."); and
``generate``'s signature was cut before ``-> Barcode``.

The facts are copied verbatim from local facts builds of the pinned sources
(``fixtures/type_row_facts.json``: Aspose.3D TypeScript 66cb26df, Aspose.BarCode Python 06eca5c0).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import _type_batches, type_unit_facts
from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL
from repo_presenter.readme.composition.renderer import api_reference_names
from repo_presenter.readme.review.evidence import unit_facts
from repo_presenter.readme.review.scope import authored_table_lines, authored_type_rows
from repo_presenter.readme.review.sectionwise import plan_units, type_row_facts, unit_packet
from tests.readme.composition.synthetic import make_entry

FIXTURE = Path(__file__).parent / "fixtures" / "type_row_facts.json"
HEADING = next(section.heading for section in SEMANTIC_SHELL if section.id == "api_reference")


def _document(lane: str) -> FactsDocument:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))[lane]
    return FactsDocument(
        repository=payload["repository"],
        source_revision=payload["source_revision"],
        facts=tuple(
            Fact(
                id=record["id"],
                kind=record["kind"],
                value=record["value"],
                evidence=tuple(Evidence(e["path"], e.get("detail")) for e in record["evidence"]),
                polarity=record.get("polarity", "SUPPORTED"),
                confidence=record.get("confidence", 1.0),
                attributes=record.get("attributes"),
            )
            for record in payload["facts"]
        ),
    )


#: Rows exactly as the hosted candidate printed them (the findings' own quotes).
TS_ROWS = (
    "| `ReferenceMode` | ReferenceMode is a public symbol with members DIRECT, INDEX, and "
    "INDEX_TO_DIRECT. |",
    "| `RelativeRectangle` | RelativeRectangle is a public symbol with members constructor, "
    "fromScale, offsetHeight, offsetWidth, offsetX, offsetY, scaleHeight, and scaleWidth. |",
    "| `RotationMode` | RotationMode is a public symbol with members FIXED and ORBIT. |",
    "| `Scene` | Scene is a public symbol with members VERSION, animationClips, assetInfo, clear, "
    "constructor, createAnimationClip, currentAnimationClip, and findProperty; Scene.open throws "
    "TypeError (conditionally), Scene.render throws Error, and Scene.save throws Error "
    "(conditionally) and TypeError (conditionally). |",
    "| `TextureMapping` | TextureMapping is a public symbol with members AMBIENT, BUMP, DIFFUSE, "
    "DISPLACEMENT, EMISSIVE, GLOW, NORMAL, and OPACITY. |",
    "| `Vector2` | Vector2 is a public symbol with members constructor, equals, getItem, length, "
    "length2, parse, set, and setItem; Vector2.getItem throws Error (conditionally), Vector2.parse "
    "throws Error (conditionally), and Vector2.setItem throws Error (conditionally). |",
    "| `Vertex` | Vertex is a public symbol with members compare, compareTo, constructor, "
    "readDouble, readFVector2, readFVector3, readFVector4, and readFloat; Vertex.readDouble throws "
    "Error (conditionally), Vertex.readFloat throws Error (conditionally), Vertex.readFVector2 "
    "throws Error (conditionally), Vertex.readFVector3 throws Error (conditionally), "
    "Vertex.readFVector4 throws Error (conditionally), and Vertex.readVector2 throws Error "
    "(conditionally). |",
    "| `VertexDeclaration` | VertexDeclaration is a public symbol with members addField, clear, "
    "compareTo, constructor, count, fromGeometry, getField, and sealed; VertexDeclaration.addField "
    "throws Error (conditionally), VertexDeclaration.clear throws Error (conditionally), and "
    "VertexDeclaration.fromGeometry throws Error. |",
)


def _readme(rows: tuple[str, ...]) -> str:
    return "\n".join(
        [
            f"## {HEADING}",
            "",
            "The `Scene` class is where a document starts.",
            "",
            "| Class | Description |",
            "| --- | --- |",
            *rows,
            "",
        ]
    )


def _packets(facts: FactsDocument, readme: str) -> list[dict]:
    units = plan_units(readme, rendered=True, authored=authored_table_lines(readme, facts))
    return [
        unit_packet(
            unit,
            units=units,
            repository=facts.repository,
            candidate_readme=readme,
            original_readme="",
            facts=facts,
            plan={},
        )
        for unit in units
    ]


def _shown(packets: list[dict]) -> dict[str, dict]:
    return {record["id"]: record for packet in packets for record in packet["facts"]}


def test_every_ts_row_is_shown_the_members_and_implementation_facts_it_states() -> None:
    facts = _document("typescript")
    readme = _readme(TS_ROWS)
    rows = authored_type_rows(readme, facts)
    assert len(rows) == len(TS_ROWS)
    shown = _shown(_packets(facts, readme))
    for type_fact in rows.values():
        members, implementation = type_unit_facts(type_fact, facts)
        record = shown[type_fact.id]
        assert record["members"] == ", ".join(members)
        for fact in implementation:
            assert fact.id in shown, (type_fact.value, fact.id)
    assert shown["public_symbol:referencemode"]["members"] == "DIRECT, INDEX, INDEX_TO_DIRECT"
    assert shown["public_symbol:scene"]["members"] == (
        "VERSION, animationClips, assetInfo, clear, constructor, createAnimationClip, "
        "currentAnimationClip, findProperty"
    )
    render = shown["implementation:throws.scene.render.body.error"]
    assert render["value"] == "Scene.render throws Error"
    assert render["message"] == "render is not implemented"
    assert "implementation:throws.vertex.readdouble.body.error" in shown


def test_the_reviewer_is_shown_exactly_what_the_type_batch_gave_the_author() -> None:
    facts = _document("typescript")
    readme = _readme(TS_ROWS)
    (unit,) = plan_units(readme, rendered=True, authored=authored_table_lines(readme, facts))
    given, members = type_row_facts(unit, readme, facts)
    accepted: dict[str, dict] = {}
    bound: set[str] = set()
    for task in _type_batches(make_entry(), facts, []):
        accepted.update({record["id"]: record for record in task.packet["accepted_facts"]})
        for slot_ids in task.slot_facts.values():
            bound.update(slot_ids)
    row_types = {fact.id for fact in authored_type_rows(readme, facts).values()}
    # Each row's facts are its slot's bound facts, and the member list is the author's own.
    documented = {
        fact.id
        for row in authored_type_rows(readme, facts).values()
        for fact in type_unit_facts(row, facts)[1]
    }
    assert set(given) == {
        i for i in bound if i in row_types or i in documented or not i.startswith("public_symbol:")
    }
    for type_id, names in members.items():
        assert accepted[type_id]["members"] == names


def test_a_row_outside_the_unit_and_a_live_readme_carry_no_type_facts() -> None:
    facts = _document("typescript")
    readme = _readme(TS_ROWS)
    (unit,) = plan_units(readme, rendered=True, authored=authored_table_lines(readme, facts))
    lane_l = type(unit)(unit.index, unit.sections, unit.lines, rendered=False)
    assert type_row_facts(lane_l, readme, facts) == ([], {})
    intro_only = type(unit)(unit.index, unit.sections, (3,), rendered=True)
    assert type_row_facts(intro_only, readme, facts) == ([], {})


def test_given_facts_come_before_ranked_and_symbol_groups_and_are_not_capped() -> None:
    facts = _document("typescript")
    ids = [fact.id for fact in facts.facts if fact.kind in {"implementation", "public_symbol"}]
    assert len(ids) > 60  # more than MAX_RANKED and MAX_CITED: neither cap applies to them
    records = unit_facts(facts, "unrelated words only", sections=("api_reference",), given=ids)
    assert set(ids) <= {record["id"] for record in records}


@pytest.mark.parametrize(
    ("fact_id", "field", "expected"),
    [
        (
            "public_symbol:aspose_barcode_foss.renderers.pngrenderer",
            "docstring",
            "Render a barcode into PNG output.",
        ),
        (
            "public_symbol:aspose_barcode_foss.renderers.svgrenderer",
            "docstring",
            "Render a barcode into SVG output.",
        ),
        (
            "public_symbol:aspose_barcode_foss.pngrenderer",
            "reexport_of",
            "aspose_barcode_foss.renderers.PngRenderer",
        ),
        ("public_symbol:aspose_barcode_foss.generate", "signature", "-> Barcode"),
    ],
)
def test_barcode_capability_sentences_are_shown_the_source_they_rest_on(
    fact_id: str, field: str, expected: str
) -> None:
    facts = _document("python")
    text = (
        "The `aspose_barcode_foss.renderers.PngRenderer` and `aspose_barcode_foss.PngRenderer` "
        "classes provide PNG rendering capabilities for barcodes. The "
        "`aspose_barcode_foss.renderers.SvgRenderer` class renders SVG. The "
        "`aspose_barcode_foss.generate` function creates a `Barcode` instance."
    )
    shown = {
        record["id"]: record for record in unit_facts(facts, text, sections=("api_reference",))
    }
    assert expected in shown[fact_id][field]


def test_a_documented_symbol_keeps_its_own_docstring() -> None:
    facts = _document("python")
    shown = {
        record["id"]: record
        for record in unit_facts(facts, "`aspose_barcode_foss.generate`", sections=("x",))
    }
    assert shown["public_symbol:aspose_barcode_foss.generate"]["docstring"] == (
        "Create a barcode for the requested symbology."
    )


def test_barcode_stub_row_is_shown_its_not_implemented_fact() -> None:
    facts = _document("python")
    names = api_reference_names(facts)
    renderer = "public_symbol:aspose_barcode_foss.renderers.renderer"
    value = next(fact.value for fact in facts.facts if fact.id == renderer)
    row = (
        f"| `{names[value]}` | aspose_barcode_foss.renderers.Renderer is a public symbol and its "
        "render method raises NotImplementedError. |"
    )
    shown = _shown(_packets(facts, _readme((row,))))
    assert (
        "implementation:throws.aspose_barcode_foss.renderers.renderer.render.body."
        "notimplementederror" in shown
    )
