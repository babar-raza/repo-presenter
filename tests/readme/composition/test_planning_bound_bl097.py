"""BL-097: a presentation_planning reply is bounded to fit the job's max_output_tokens.

Hosted Lane R run 43572739220 (Aspose-PDF-FOSS-for-Python at 6493dfc2) failed with
"presentation_planning: output truncated at the manifest's max_output_tokens (6000); raise the budget
or bound the output, never retry". Every planning schema on record lets a reply with every array full
reach 21,000-34,500 characters (6000 tokens hold about 18,000); the free-text strings had no
maxLength at all. The bound gives every string a maxLength and bounds ``deviations`` -- internal
accounting nothing downstream reads -- so the reply at measured p95 sizes fits; a schema whose
deviations already fit keeps its deviations bound byte for byte.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.composition.output_bounds import (
    CHARS_PER_TOKEN,
    DEVIATION_ENTRY_OVERHEAD_CHARS,
    DEVIATION_TEXT_MAX_LENGTH,
    DEVIATION_TEXT_P95_CHARS,
    PLAN_PRINTED_P95_CHARS,
    PLAN_TEXT_MAX_LENGTH,
    PLANNED_SHARE,
    _citable_width,
    bound_planning_reply,
    deviations_bound,
)
from repo_presenter.readme.composition.planning import planning_schema
from tests.readme.composition.synthetic import make_facts

BUDGET = 6000
#: Real citable fact ids of the failing PDF Python schema's kind and length (mean width about 45).
PDF_PYTHON_IDS = [
    f"public_symbol:aspose_pdf.annotations.lineannotation.member_{i:03d}" for i in range(400)
] + [f"inherited_unit:{i:03d}.paragraph" for i in range(300)]
#: Short ids of the PDF Java schema's width (about 27), whose ten full deviations already fit.
PDF_JAVA_IDS = [f"public_symbol:m{i:04d}" for i in range(200)]


def _schema(ids: list[str]) -> dict:
    return {
        "type": "object",
        "$defs": {"citable_fact_id": {"type": "string", "enum": ids}},
        "properties": {
            "sections": {
                "type": "array",
                "items": {"type": "object", "properties": {"reason": {"type": "string"}}},
            },
            "core_capabilities": {
                "type": "array",
                "items": {"type": "object", "properties": {"title": {"type": "string"}}},
            },
            "at_a_glance": {
                "oneOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "properties": {
                            "capability_titles": {"type": "array", "items": {"type": "string"}}
                        },
                    },
                ]
            },
            "deviations": {
                "type": "array",
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "minLength": 1},
                        "fact_ids": {"type": "array", "maxItems": 12},
                    },
                },
            },
        },
    }


def _reply_chars(schema: dict) -> float:
    deviations = schema["properties"]["deviations"]
    items = deviations["maxItems"]
    ids = deviations["items"]["properties"]["fact_ids"]["maxItems"]
    entry = DEVIATION_ENTRY_OVERHEAD_CHARS + DEVIATION_TEXT_P95_CHARS + ids * _citable_width(schema)
    return PLAN_PRINTED_P95_CHARS + items * entry


def test_the_pdf_python_shape_is_bounded_to_fit() -> None:
    schema = _schema(PDF_PYTHON_IDS)
    room = BUDGET * CHARS_PER_TOKEN * PLANNED_SHARE
    assert _reply_chars(schema) > room  # the unbounded schema does not fit
    bounded = bound_planning_reply(schema, BUDGET)
    assert _reply_chars(bounded) <= room
    deviations = bounded["properties"]["deviations"]
    assert deviations["items"]["properties"]["fact_ids"]["maxItems"] >= 1
    assert deviations["maxItems"] >= 1
    assert schema["properties"]["deviations"]["maxItems"] == 10  # the input is not mutated


def test_every_free_text_string_gets_a_terminating_bound() -> None:
    bounded = bound_planning_reply(_schema(PDF_JAVA_IDS), BUDGET)
    properties = bounded["properties"]
    assert properties["core_capabilities"]["items"]["properties"]["title"]["maxLength"] == PLAN_TEXT_MAX_LENGTH
    glance = properties["at_a_glance"]["oneOf"][1]["properties"]["capability_titles"]["items"]
    assert glance["maxLength"] == PLAN_TEXT_MAX_LENGTH
    text = properties["deviations"]["items"]["properties"]["text"]
    assert text["maxLength"] == DEVIATION_TEXT_MAX_LENGTH and text["minLength"] == 1
    assert properties["sections"]["maxItems"] > 0
    assert "maxLength" in properties["sections"]["items"]["properties"]["reason"]


def test_negative_control_a_schema_that_fits_keeps_its_deviations_bound() -> None:
    schema = _schema(PDF_JAVA_IDS)
    assert deviations_bound(schema, BUDGET) is None
    bounded = bound_planning_reply(schema, BUDGET)
    assert bounded["properties"]["deviations"]["maxItems"] == 10
    assert bounded["properties"]["deviations"]["items"]["properties"]["fact_ids"]["maxItems"] == 12
    # Without a budget only the string bounds apply.
    assert bound_planning_reply(_schema(PDF_PYTHON_IDS), None)["properties"]["deviations"]["maxItems"] == 10


def test_the_real_planning_schema_is_bounded() -> None:
    loaded = load_manifests(Path("prompts"))["presentation_planning"]
    schema = planning_schema(loaded, make_facts(), {}, {"dispositions": []})
    title = schema["properties"]["core_capabilities"]["items"]["properties"]["title"]
    assert title["maxLength"] == PLAN_TEXT_MAX_LENGTH
    assert schema["properties"]["deviations"]["items"]["properties"]["text"]["maxLength"] == DEVIATION_TEXT_MAX_LENGTH
