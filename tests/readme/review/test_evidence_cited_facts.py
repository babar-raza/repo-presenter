"""The review packet carries every fact a reviewed unit was written from, and the evidence that
makes a limitation checkable.

Aspose.3D-FOSS-for-Java Lane R, hosted run 43413886429 (2026-11-13): six scope_limitations
sentences ("Only `.stl` ... and `.obj` (import only) are implemented ...; other recognized formats
have no working load or save path", "`Scene` rendering is not implemented in this edition", ...)
were filed ``unsupported_claim`` although each is true by the facts: the stub-dispatched formats
are UNRESOLVED with the evidence "dispatched ... only to FbxReader.load, an unimplemented stub",
and ``Scene.render`` throws ``UnsupportedOperationException`` ("Rendering is not implemented in
FOSS version"). The packet never showed the ``scene.render`` throw (the three shortest ``scene.*``
ids won the per-name slots), never carried the plan's own citations for the section, and showed a
format fact as ``.fbx UNRESOLVED`` with no reason. Fact ids, values and evidence below are copied
from a local facts build of the same pinned source (3d2ed6be).
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review import evidence as ev
from repo_presenter.readme.review.sectionwise import plan_cited_fact_ids

SCENE_RENDER = "implementation:throws.com.aspose.threed.scene.render.body.unsupportedoperationexception"
FBX_IN = "format:input.fbx"


def _fact(
    fact_id: str,
    kind: str,
    value: str,
    *,
    polarity: str = "SUPPORTED",
    detail: str | None = None,
    path: str = "src/main/java/com/aspose/threed/Scene.java",
    attributes: dict[str, Any] | None = None,
) -> Fact:
    return Fact(
        id=fact_id, kind=kind, value=value,  # type: ignore[arg-type]
        evidence=(Evidence(path, detail),), polarity=polarity,  # type: ignore[arg-type]
        attributes=attributes,
    )


def _document(*extra: Fact) -> FactsDocument:
    facts = [
        _fact("package:name", "package", "org.aspose:aspose-3d-foss"),
        _fact(
            FBX_IN, "format", ".fbx", polarity="UNRESOLVED",
            path="src/main/java/com/aspose/threed/FileFormat.java",
            detail="line 72; '.fbx' is dispatched for input only to FbxReader.load, an "
            "unimplemented stub; not a registration",
        ),
        _fact(
            "format:input.stl", "format", ".stl",
            path="src/main/java/com/aspose/threed/FileFormat.java",
            detail="line 76; '.stl' matched by a load/createLoadOptions dispatch arm",
        ),
        _fact(
            "implementation:constant.src-main-java-com-aspose-threed-scene.version",
            "implementation", 'VERSION = "26.1.0"',
        ),
        _fact(
            "implementation:throws.com.aspose.threed.scene.save.body.ioexception",
            "implementation", "com.aspose.threed.Scene.save throws IOException (conditionally)",
        ),
        _fact(
            "implementation:returns.com.aspose.threed.scene.getrootnode.body",
            "implementation", "com.aspose.threed.Scene.getRootNode always returns null",
        ),
        _fact(
            SCENE_RENDER, "implementation",
            "com.aspose.threed.Scene.render throws UnsupportedOperationException",
            detail="line 436; throw in the member's own body",
            attributes={
                "aspect": "throws",
                "member": "com.aspose.threed.Scene.render",
                "message": "Rendering is not implemented in FOSS version",
            },
        ),
        *extra,
    ]
    return FactsDocument("aspose-3d-foss/Aspose.3D-FOSS-for-Java", "0" * 40, tuple(facts))


SCENE_LINE = "- `Scene` rendering is not implemented in this edition."
FORMATS_LINE = (
    "- Only `.stl` (import and export) and `.obj` (import only) are implemented in the published "
    "package; other recognized formats have no working load or save path."
)


def _records(text: str, document: FactsDocument | None = None, **kwargs: Any) -> dict[str, dict]:
    records = ev.unit_facts(
        document or _document(), text, sections=["scope_limitations"], **kwargs
    )
    return {record["id"]: record for record in records}


def test_the_member_a_limitation_names_is_shown_by_the_unit_s_own_words() -> None:
    records = _records(SCENE_LINE)
    assert SCENE_RENDER in records
    assert records[SCENE_RENDER]["message"] == "Rendering is not implemented in FOSS version"


def test_an_unresolved_format_carries_the_stub_evidence_that_makes_it_so() -> None:
    record = _records(FORMATS_LINE)[FBX_IN]
    assert record["polarity"] == "UNRESOLVED"
    assert "unimplemented stub" in record["evidence"]


def test_a_symbol_record_still_carries_no_evidence_field() -> None:
    symbol = _fact("public_symbol:com.aspose.threed.scene", "public_symbol", "com.aspose.threed.Scene")
    records = _records(SCENE_LINE, _document(symbol))
    assert "evidence" not in records["public_symbol:com.aspose.threed.scene"]


def test_the_plan_s_citations_for_the_section_are_carried_whatever_the_overlap() -> None:
    unrelated = _fact(
        "implementation:throws.com.aspose.threed.pbrspecularmaterial.diffuse.body."
        "unsupportedoperationexception",
        "implementation",
        "com.aspose.threed.PbrSpecularMaterial.diffuse throws UnsupportedOperationException",
    )
    document = _document(unrelated)
    plan = {
        "material_limitations": [
            {"fact_ids": [unrelated.id, "format:missing"], "unit_ids": ["inherited_unit:061.list"]}
        ],
        "core_capabilities": [{"fact_ids": ["format:input.stl"]}],
    }
    cited = plan_cited_fact_ids(plan, ["scope_limitations"], document)
    assert cited == [unrelated.id]  # an unknown id is dropped; another section's field is not read
    assert unrelated.id not in _records("Nothing here names it.", document)
    assert unrelated.id in _records("Nothing here names it.", document, cited=cited)


def test_cited_facts_never_displace_the_core_facts(monkeypatch) -> None:
    monkeypatch.setattr(ev, "FACTS_CHARS", 400)
    records = _records("Nothing here.", cited=[SCENE_RENDER])
    assert "package:name" in records
