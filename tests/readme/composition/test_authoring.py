"""Targeted tests for authoring.py's identifier-handling and unit_checks guard."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    SectionTask,
    allowed_identifiers,
    identifier_tokens,
    preserved_opening_text,
    recover_opening_duplicates_preserved,
    unit_checks,
)
from tests.readme.composition.synthetic import make_facts


def test_identifier_tokens_finds_dotted_and_coordinate_shapes() -> None:
    text = "Use `aspose_widget_foss.Widget` or the Maven coordinate org.aspose:aspose-widget-foss."
    tokens = identifier_tokens(text)
    assert "aspose_widget_foss.Widget" in tokens
    assert "org.aspose:aspose-widget-foss" in tokens


def test_allowed_identifiers_admits_every_supported_fact_value() -> None:
    allowed = allowed_identifiers(make_facts(), "Aspose Widget FOSS for Python")
    assert "aspose-widget-foss" in allowed
    assert "aspose_widget_foss.Widget" in allowed
    assert "Widget" in allowed  # the dotted suffix is admitted too


def test_unit_checks_rejects_a_stray_identifier_no_fact_carries() -> None:
    facts = make_facts()
    task = SectionTask(
        section_id="key_capabilities",
        packet={},
        accepted_ids=frozenset({"public_symbol:aspose_widget_foss.widget"}),
        slots=("capability:1",),
        slot_facts={"capability:1": frozenset({"public_symbol:aspose_widget_foss.widget"})},
    )
    output = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Also integrates with TotallyMadeUpFramework.",
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            }
        ]
    }
    errors = unit_checks(output, task, facts, "Aspose Widget FOSS for Python")
    assert any("TotallyMadeUpFramework" in error for error in errors)


def test_unit_checks_accepts_a_unit_that_only_spells_accepted_identifiers() -> None:
    facts = make_facts()
    task = SectionTask(
        section_id="key_capabilities",
        packet={},
        accepted_ids=frozenset({"public_symbol:aspose_widget_foss.widget"}),
        slots=("capability:1",),
        slot_facts={"capability:1": frozenset({"public_symbol:aspose_widget_foss.widget"})},
    )
    output = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Builds an aspose_widget_foss.Widget and renders it.",
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            }
        ]
    }
    assert unit_checks(output, task, facts, "Aspose Widget FOSS for Python") == []


def test_unit_checks_rejects_a_forbidden_markdown_link() -> None:
    facts = make_facts()
    task = SectionTask(
        section_id="opening",
        packet={},
        accepted_ids=frozenset({"package:name"}),
        slots=("opening",),
    )
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": "See [the docs](https://example.com) for more.",
                "fact_ids": ["package:name"],
            }
        ]
    }
    errors = unit_checks(output, task, facts, "Aspose Widget FOSS for Python")
    assert any("Markdown link" in error for error in errors)


# The "opening" fixtures below are the real, committed text of two independent Lane R cascade
# runs this session (evidence/build/P2_REAL_ENGINE_SALVAGE/lane_r_{sixth,ninth}_full_cascade/),
# not synthetic prose -- grounding the duplicate-opening-paragraph check and its recovery in the
# actual defect the ten real cascades this session observed, not a guessed shape of it.

_PRESERVED_NINTH_CASCADE = (
    "Aspose.3D FOSS for TypeScript is a free, open-source, MIT-licensed TypeScript/JavaScript "
    "library for building and converting 3D scenes in Node.js. It exposes an "
    "Aspose.3D-compatible scene-graph API — Scene, Node, Mesh, Material — for "
    "constructing scenes from meshes and vertex attribute data, assigning shading materials, "
    "animating node hierarchies with keyframes, and reading and writing widely used interchange "
    "formats such as glTF, OBJ, STL, FBX, and COLLADA, as pure TypeScript with no native "
    "bindings."
)
_AUTHORED_NINTH_CASCADE_POST_COHERENCE = (
    "Aspose.3D FOSS for TypeScript is a free, open-source, MIT-licensed TypeScript/JavaScript "
    "library for building and converting 3D scenes in `Node`.js. It exposes an "
    "Aspose.3D-compatible scene-graph API — `Scene`, `Node`, `Mesh`, `Material` — for "
    "constructing scenes from meshes and vertex attribute data, assigning shading materials, "
    "animating node hierarchies with keyframes, and reading and writing widely used interchange "
    "formats such as glTF, OBJ, STL, FBX, and COLLADA, as pure TypeScript with no native "
    "bindings."
)
_PRESERVED_SIXTH_CASCADE = (
    "Aspose.Cells FOSS for Rust is a free, open-source, pure-Rust library for creating, "
    "loading, editing, and saving Excel `.xlsx` (Office Open XML / SpreadsheetML) workbooks. "
    "It exposes an API modeled after Aspose.Cells, so the familiar `Workbook` / `Worksheet` / "
    "`Cells` object model is available to Rust programs with no proprietary runtime, no "
    "Microsoft Office installation, and no external Aspose dependency. The OOXML packaging "
    "— ZIP container, relationships, shared strings, styles, worksheet XML, and charts "
    "— is implemented from scratch on top of a small set of general-purpose crates: `zip` "
    "(package container), `roxmltree` (XML parsing), `chrono` (date/time), `sha2` / `base64` / "
    "`getrandom` (protection hashing), and `serde_json`."
)
_AUTHORED_SIXTH_CASCADE_DISTINCT = (
    "Aspose.Cells FOSS for Rust reads and writes Excel `.xlsx` workbooks. It loads workbooks "
    "from files, byte arrays, or streams using `Workbook.load_xlsx`, "
    "`Workbook.load_xlsx_from_bytes`, or `Workbook.load_xlsx_from_stream`, and saves them using "
    "`Workbook.save_xlsx`, `Workbook.save_xlsx_to_bytes`, or `Workbook.save_xlsx_to_stream`. It "
    "provides methods to inspect and repair damaged packages via "
    "`LoadOptions.try_repair_package` and `LoadOptions.try_repair_xml`, and exposes diagnostics "
    "through `Workbook.get_load_diagnostics`. The library implements the OOXML packaging format "
    "from scratch on top of general-purpose crates, with no proprietary runtime, no Microsoft "
    "Office installation, and no external Aspose dependency."
)


def _opening_task(accepted_ids: frozenset[str]) -> SectionTask:
    return SectionTask(
        section_id="opening", packet={}, accepted_ids=accepted_ids, slots=("opening",)
    )


def _facts_with_preserved_opening(text: str) -> FactsDocument:
    base = make_facts()
    preserved = Fact(
        "inherited_unit:004.paragraph",
        "inherited_unit",
        text,
        (Evidence("README.md", "section 'Aspose Widget'"),),
    )
    return FactsDocument(base.repository, base.source_revision, (*base.facts, preserved))


def _dispositions_preserving_opening() -> dict[str, object]:
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:004.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "opening",
                "fact_ids": [],
                "rationale": "test fixture",
            }
        ]
    }


def test_preserved_opening_text_reads_the_preserved_unit_verbatim() -> None:
    facts = _facts_with_preserved_opening(_PRESERVED_NINTH_CASCADE)
    assert preserved_opening_text(_dispositions_preserving_opening(), facts) == (
        _PRESERVED_NINTH_CASCADE
    )


def test_preserved_opening_text_empty_without_a_preserved_opening_unit() -> None:
    assert preserved_opening_text({"dispositions": []}, make_facts()) == ""


def test_unit_checks_rejects_an_opening_unit_that_restates_the_preserved_paragraph() -> None:
    """Grounded in the real ninth cascade (aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript): S8
    coherence's own revision of "opening" there became a near word-for-word copy of the
    paragraph reconciliation had already preserved beside it. This is exactly the shape this
    check exists to catch."""
    facts = _facts_with_preserved_opening(_PRESERVED_NINTH_CASCADE)
    task = _opening_task(frozenset({"package:name"}))
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": _AUTHORED_NINTH_CASCADE_POST_COHERENCE,
                "fact_ids": ["package:name"],
            }
        ]
    }
    errors = unit_checks(
        output,
        task,
        facts,
        "Aspose 3D FOSS for TypeScript",
        dispositions=_dispositions_preserving_opening(),
    )
    assert any("restates the inherited paragraph" in error for error in errors)


def test_unit_checks_allows_an_opening_unit_that_genuinely_differs() -> None:
    """Grounded in the real sixth cascade (aspose-cells-foss/Aspose.Cells-FOSS-for-Rust) before
    S8 coherence touched it: the freshly authored unit names its own distinct methods and the
    preserved paragraph names its own distinct crates. Neither states the other, so the check
    must not fire here -- the common, non-defective case."""
    facts = _facts_with_preserved_opening(_PRESERVED_SIXTH_CASCADE)
    task = _opening_task(frozenset({"package:name"}))
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": _AUTHORED_SIXTH_CASCADE_DISTINCT,
                "fact_ids": ["package:name"],
            }
        ]
    }
    errors = unit_checks(
        output,
        task,
        facts,
        "Aspose Cells FOSS for Rust",
        dispositions=_dispositions_preserving_opening(),
    )
    assert not any("restates the inherited paragraph" in error for error in errors)


def test_unit_checks_without_dispositions_does_not_run_the_new_check() -> None:
    """Back-compatible default: every existing caller that never passes ``dispositions`` (every
    non-"opening" unit_checks call site, and any pre-fix test) keeps its exact prior behaviour."""
    facts = _facts_with_preserved_opening(_PRESERVED_NINTH_CASCADE)
    task = _opening_task(frozenset({"package:name"}))
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": _AUTHORED_NINTH_CASCADE_POST_COHERENCE,
                "fact_ids": ["package:name"],
            }
        ]
    }
    errors = unit_checks(output, task, facts, "Aspose 3D FOSS for TypeScript")
    assert not any("restates the inherited paragraph" in error for error in errors)


def test_recover_opening_duplicates_preserved_returns_none_when_fully_redundant() -> None:
    """Grounded in the real ninth cascade's near-total duplicate: nothing deterministic is left
    to keep, so recovery must not fabricate replacement text -- it returns None and the job
    fails closed, exactly as it would with no ``recover`` at all."""
    facts = _facts_with_preserved_opening(_PRESERVED_NINTH_CASCADE)
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": _AUTHORED_NINTH_CASCADE_POST_COHERENCE,
            }
        ]
    }
    result = recover_opening_duplicates_preserved(
        output, dispositions=_dispositions_preserving_opening(), facts=facts
    )
    assert result is None


def test_recover_opening_duplicates_preserved_trims_to_the_genuinely_new_sentence() -> None:
    preserved = "Aspose Widget FOSS for Python is a free, open-source, pure-Python library for rendering widgets."
    authored = preserved + " It also provides a built-in validator via Widget.validate()."
    facts = _facts_with_preserved_opening(preserved)
    output = {"units": [{"section": "opening", "slot": "opening", "text": authored}]}
    result = recover_opening_duplicates_preserved(
        output, dispositions=_dispositions_preserving_opening(), facts=facts
    )
    assert result is not None
    assert result["units"][0]["text"] == "It also provides a built-in validator via Widget.validate()."


def test_recover_opening_duplicates_preserved_returns_none_without_a_preserved_unit() -> None:
    output = {
        "units": [{"section": "opening", "slot": "opening", "text": "Anything at all."}]
    }
    result = recover_opening_duplicates_preserved(
        output, dispositions={"dispositions": []}, facts=make_facts()
    )
    assert result is None
