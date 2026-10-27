"""The Lane L correction report and the outcomes a run can have (plans/PLAN_lane_l_hosted.md L2, L3).

Three outcomes: ``CORRECTED``, ``NO_CHANGE_WARRANTED`` (a legitimate result, never a fabricated
improvement) and ``REFUSED_LANE_R_RECOMMENDED`` (a defect no deterministic edit may repair is
neither dropped nor masked). The report is a pure function of its inputs, so a rerun writes the same
bytes.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.correction.engine import correct, is_stable
from repo_presenter.readme.correction.model import Finding
from repo_presenter.readme.correction.report import (
    CANDIDATE_OUTCOMES,
    INFORMATIONAL_DETECTORS,
    OUTCOME_CORRECTED,
    OUTCOME_NO_CHANGE,
    OUTCOME_REFUSED,
    canonical_json,
    correction_dispositions,
    corrections_document,
    defect_findings,
    is_defect,
    lane_r_recommendation,
    outcome_of,
    unrepaired_defects,
)
from tests.readme.correction.conftest import base_facts, context, fact

README = """# Product

The maintainers wrote this opening and every sentence below it.

## Documentation

See [the notes](upstream-issues.md) for details.

## Usage

```java
Widget.render();
```
"""
TREE = ("README.md", "LICENSE", "pom.xml", "docs/upstream-issues.md")


def broken_link() -> Fact:
    return fact(
        "link_target:001",
        "upstream-issues.md",
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", "line 7; relative; text 'the notes'"),
            ("README.md", "MISSING: tree does not contain upstream-issues.md"),
        ),
    )


def unit(unit_id: str, value: str, lines: str, kind: str) -> Fact:
    return Fact(
        unit_id,
        "inherited_unit",
        value,
        (Evidence("README.md", f"lines {lines}; {kind}"),),
    )


def failing_example() -> Fact:
    return fact(
        "example:001",
        "Widget.render();",
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", "lines 11-11; unit"),
            ("receipts.json", "FAILED: cannot find symbol render"),
        ),
    )


def run(readme: str = README, *extra: Fact):
    ctx = context(readme, base_facts(*extra), tree=TREE)
    return ctx, correct(ctx)


# --- outcomes ---------------------------------------------------------------------------------


def test_a_repairable_defect_is_a_corrected_outcome() -> None:
    _ctx, result = run(README, broken_link())
    assert [edit.kind for edit in result.edits] == ["BROKEN_LINK"]
    assert outcome_of(result) == OUTCOME_CORRECTED in CANDIDATE_OUTCOMES


def test_a_readme_with_nothing_to_correct_is_no_change_warranted_and_the_candidate_is_the_live_readme() -> (
    None
):
    _ctx, result = run(README)
    assert result.edits == []
    assert (
        result.corrected == README
    )  # not a rewritten, "improved" README: the live one
    assert outcome_of(result) == OUTCOME_NO_CHANGE
    assert OUTCOME_NO_CHANGE in CANDIDATE_OUTCOMES


def test_a_failing_example_is_a_defect_that_refuses_the_run_and_recommends_lane_r() -> (
    None
):
    _ctx, result = run(README, failing_example())
    assert result.edits == []
    assert outcome_of(result) == OUTCOME_REFUSED
    assert OUTCOME_REFUSED not in CANDIDATE_OUTCOMES
    (defect,) = unrepaired_defects(result)
    assert defect.detector == "failing_example"
    assert "Lane R is the recommended lane" in lane_r_recommendation(result)
    assert "failing_example line 11" in lane_r_recommendation(result)
    (finding,) = defect_findings(result)
    assert (finding.rule, finding.source, finding.claim_kind) == (
        "lane_l_unrepaired_defect",
        "deterministic",
        "contradiction",
    )
    assert finding.blocking and finding.fact_ids == ("example:001",)


def test_a_repaired_defect_beside_an_unrepaired_one_still_refuses_the_run() -> None:
    """Falsifier for 'edits made, so ship': one fixed link does not excuse a README that still
    carries a failing example. The candidate is refused whole; the report keeps both facts."""
    _ctx, result = run(README, broken_link(), failing_example())
    assert [edit.kind for edit in result.edits] == ["BROKEN_LINK"]
    assert outcome_of(result) == OUTCOME_REFUSED


# --- which findings are defects ----------------------------------------------------------------------


def make(detector: str, reason: str = "") -> Finding:
    return Finding(detector, 3, "text", "because", report_only_reason=reason)


@pytest.mark.parametrize(
    ("detector", "reason", "defect"),
    [
        ("failing_example", "", True),
        ("format_overclaim", "", True),
        ("broken_link", "", True),
        ("enterprise_edition_naming", "", True),
        (
            "second_h1",
            "OVERLAPS_ANOTHER_CORRECTION",
            True,
        ),  # a skipped FIX stays a defect
        ("second_h1", "INTERNAL_NARRATION", True),
        ("report_gaps", "", False),  # an opportunity, not a falsehood
        (
            "add_install_forms",
            "ALREADY_SHOWN",
            False,
        ),  # an addition legitimately not made
        ("add_build_test", "NO_BUILD_RECEIPT", False),
        ("a_detector_added_next_year", "", True),  # unknown detectors fail closed
    ],
)
def test_the_closed_table_of_what_is_a_defect(
    detector: str, reason: str, defect: bool
) -> None:
    assert is_defect(make(detector, reason)) is defect


def test_only_report_gaps_is_informational_today() -> None:
    assert INFORMATIONAL_DETECTORS == {"report_gaps"}


# --- the report ---------------------------------------------------------------------------------------


def report_for(ctx, result) -> dict:
    deterministic, idempotent = is_stable(ctx, result)
    original = ctx.readme.encode("utf-8")
    corrected = result.corrected.encode("utf-8")
    return corrections_document(
        ctx,
        result,
        original_sha256=hashlib.sha256(original).hexdigest(),
        corrected_sha256=hashlib.sha256(corrected).hexdigest(),
        deterministic=deterministic,
        idempotent=idempotent,
    )


def test_the_report_states_each_edit_with_its_evidence_and_what_it_left_alone() -> None:
    ctx, result = run(README, broken_link())
    document = report_for(ctx, result)
    assert document["lane"] == "L" and document["outcome"] == OUTCOME_CORRECTED
    assert document["summary"] == {"BROKEN_LINK": 1}
    (edit,) = document["edits"]
    assert edit["line"] == 7 and edit["original"] == "upstream-issues.md"
    assert edit["replacement"] == "docs/upstream-issues.md"
    assert edit["evidence"][0]["status"] == "CONTRADICTED"
    assert document["confinement"]["verified"] is True
    assert document["stability"] == {
        "deterministic": True,
        "idempotent": True,
        "provider_calls": 0,
    }
    assert all("defect" in item for item in document["unapplied"])


def test_the_report_is_a_pure_function_of_its_inputs_and_names_no_machine() -> None:
    ctx, result = run(README, broken_link())
    first = canonical_json(report_for(ctx, result))
    ctx2, result2 = run(README, broken_link())
    assert canonical_json(report_for(ctx2, result2)) == first
    text = first.decode("utf-8")
    assert "\r" not in text and text.endswith("\n")
    for forbidden in ("C:\\", "/home/", "/tmp/", "AppData", "pytest-of"):
        assert forbidden not in text
    assert json.loads(text)["source_revision"] == ctx.facts.source_revision


def test_the_canonical_json_is_the_same_bytes_whatever_the_platform_newline() -> None:
    document = {"b": "é\nline", "a": [1, 2]}
    data = canonical_json(document)
    assert data == '{\n  "a": [\n    1,\n    2\n  ],\n  "b": "é\\nline"\n}\n'.encode()


# --- the edits as the reviewer's dispositions -----------------------------------------------------------


def test_a_replacement_edit_accounts_for_the_inherited_unit_it_changes() -> None:
    notes = unit(
        "inherited_unit:004.paragraph",
        "See [the notes](upstream-issues.md) for details.",
        "7-7",
        "paragraph",
    )
    ctx, result = run(README, broken_link(), notes)
    rows = correction_dispositions(ctx, result.edits)["dispositions"]
    assert rows == [
        {
            "unit_id": "inherited_unit:004.paragraph",
            "disposition": "CORRECT_WITH_EVIDENCE",
            "destination_section": None,
            "fact_ids": ["link_target:001"],
            "rationale": result.edits[0].rationale,
        }
    ]


def test_an_edit_in_no_inherited_unit_and_a_pure_insertion_account_for_nothing() -> (
    None
):
    ctx, result = run(README, broken_link())  # no inherited_unit facts at all
    assert correction_dispositions(ctx, result.edits) == {"dispositions": []}
    insertion = result.edits[0].__class__(
        kind="MISSING_INFO",
        detector="add_x",
        start=10,
        end=10,
        original="",
        replacement="- a verified fact\n",
        fact_ids=("package:name",),
        rationale="r",
    )
    notes = unit("inherited_unit:001.paragraph", "x", "1-20", "paragraph")
    ctx2, _ = run(README, notes)
    assert correction_dispositions(ctx2, [insertion]) == {"dispositions": []}
