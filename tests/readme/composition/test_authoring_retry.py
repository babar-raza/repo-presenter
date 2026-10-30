"""Self-contained tests for authoring_retry.py's pure logic (ported 2026-10-23 from the old
repository-presenter project, see that module's own docstring for provenance).

The old repo's own test_authoring_retry.py exercises the full narrow=/run_job integration against
a live-shaped mock gateway (httpx) and nine real wave-3 fixture replies, via tests/support.py's
mock_gateway and composition/type_fallback.py -- neither of which this repository has ported
(mock_gateway was explicitly left out of this repo's own tests/support.py as too heavy a
dependency closure to pull whole; type_fallback.py is a separate, not-yet-evaluated old-repo
module). Rather than port that whole closure to run one test file, these tests cover the same
defect classes directly against authoring_retry.py's own pure functions -- the live falsifier-
equivalent proof is a real S6 cascade retry against aspose-words-foss/.NET (the repository whose
title-restatement rejection, confirmed independently twice this session, motivated this port),
not a mocked unit test.
"""

from __future__ import annotations

import json

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import SectionTask
from repo_presenter.readme.composition.authoring_retry import (
    failing_slots,
    recover_restating_sentences,
    recover_targeted_repair_restatements,
    repeated_slots,
)


def _facts() -> FactsDocument:
    return FactsDocument(
        "org/Aspose.Example-FOSS-for-Python",
        "a" * 40,
        (Fact("identity:repository", "identity", "org/Aspose.Example-FOSS-for-Python", (Evidence("x"),)),),
    )


def _task(section_id: str, slots: tuple[str, ...], **fields: object) -> SectionTask:
    return SectionTask(section_id, {}, frozenset(), slots, **fields)


# ---------------------------------------------------------------------------------------------
# recover_restating_sentences: the deterministic last resort for the title-restatement class
# that failed closed, independently, twice this session on aspose-words-foss/.NET's S6.
# ---------------------------------------------------------------------------------------------


def test_a_sentence_that_only_restates_the_slots_title_is_dropped_when_others_remain() -> None:
    task = _task(
        "key_capabilities", ("capability:1",), slot_titles={"capability:1": "Inspect embedded charts"}
    )
    output = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Inspect embedded charts. Each chart's series and axis labels are "
                "readable through the public API.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    repaired = recover_restating_sentences(output, task=task, facts=_facts())
    assert repaired is not None
    assert repaired["units"][0]["text"] == (
        "Each chart's series and axis labels are readable through the public API."
    )


def test_a_sentence_restating_a_printed_command_is_dropped_when_others_remain() -> None:
    task = _task(
        "development_testing", ("summary",), slot_render_lines={"summary": ("pytest",)}
    )
    output = {
        "units": [
            {
                "section": "development_testing",
                "slot": "summary",
                "text": "Tests live in tests/. Contributors run pytest before each change. "
                "Python 3.10 or later is required.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    repaired = recover_restating_sentences(output, task=task, facts=_facts())
    assert repaired is not None
    assert repaired["units"][0]["text"] == (
        "Tests live in tests/. Python 3.10 or later is required."
    )


def test_a_unit_that_is_nothing_but_the_restatement_is_left_alone() -> None:
    task = _task("key_capabilities", ("capability:1",), slot_titles={"capability:1": "Render pages"})
    only = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Render pages.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    assert recover_restating_sentences(only, task=task, facts=_facts()) is None


def test_a_unit_that_restates_nothing_is_not_touched() -> None:
    task = _task("key_capabilities", ("capability:1",), slot_titles={"capability:1": "Render pages"})
    fine = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Pages come out one at a time.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    assert recover_restating_sentences(fine, task=task, facts=_facts()) is None


# ---------------------------------------------------------------------------------------------
# recover_targeted_repair_restatements: the same recovery, wrapped for targeted_repair's own
# {"revised_output": {...}} shape. Real hosted defect (aspose-cells-foss/Aspose.Cells-FOSS-for-
# Rust, run 41112836454): a targeted repair correctly fixed a factuality finding by rewriting a
# unit, but the fix itself restated a command the renderer prints verbatim right after it --
# rejected for a different, real reason the job's two asks were already spent on the original
# finding, and loop.py's own _repair_section passed only the narrower, title-only
# recover_title_verbatim_opening as its recover=, never this restatement recovery.
# ---------------------------------------------------------------------------------------------


def test_recover_targeted_repair_restatements_fixes_the_wrapped_revised_output() -> None:
    task = _task(
        "development_testing", ("summary",), slot_render_lines={"summary": ("cargo test --all-targets",)}
    )
    output = {
        "revised_output": {
            "units": [
                {
                    "section": "development_testing",
                    "slot": "summary",
                    "text": "cargo test --all-targets reports 0 tests. CI runs the samples as "
                    "smoke tests instead.",
                    "fact_ids": ["identity:repository"],
                }
            ],
            "omitted": [],
        },
        "changes": [],
    }
    repaired = recover_targeted_repair_restatements(output, task=task, facts=_facts())
    assert repaired is not None
    assert repaired["revised_output"]["units"][0]["text"] == (
        "CI runs the samples as smoke tests instead."
    )
    assert repaired["changes"] == []


def test_recover_targeted_repair_restatements_is_none_when_revised_output_is_not_a_dict() -> None:
    task = _task("development_testing", ("summary",))
    assert recover_targeted_repair_restatements({}, task=task, facts=_facts()) is None
    assert (
        recover_targeted_repair_restatements(
            {"revised_output": "not a dict"}, task=task, facts=_facts()
        )
        is None
    )


def test_recover_targeted_repair_restatements_is_none_when_nothing_restates() -> None:
    task = _task(
        "development_testing", ("summary",), slot_render_lines={"summary": ("cargo test --all-targets",)}
    )
    output = {
        "revised_output": {
            "units": [
                {
                    "section": "development_testing",
                    "slot": "summary",
                    "text": "CI runs the samples as smoke tests.",
                    "fact_ids": ["identity:repository"],
                }
            ],
            "omitted": [],
        }
    }
    assert recover_targeted_repair_restatements(output, task=task, facts=_facts()) is None


# ---------------------------------------------------------------------------------------------
# failing_slots / repeated_slots: the narrowing decision authoring_narrowing() builds on.
# ---------------------------------------------------------------------------------------------


def test_a_rejection_naming_one_slot_narrows_to_that_slot_alone() -> None:
    task = _task("key_capabilities", ("capability:1", "capability:2"))
    content = json.dumps(
        {
            "units": [
                {"slot": "capability:1", "text": "a", "fact_ids": []},
                {"slot": "capability:2", "text": "b", "fact_ids": []},
            ]
        }
    )
    rejection = ["unit capability:1: restates its own title 'X'"]
    assert failing_slots(task, content, rejection) == ["capability:1"]


def test_a_rejection_no_unit_owns_narrows_to_nothing() -> None:
    task = _task("key_capabilities", ("capability:1",))
    content = json.dumps({"units": [{"slot": "capability:1", "text": "a", "fact_ids": []}]})
    rejection = ["inherited_unit:003.paragraph: superseded with no citing unit"]
    assert failing_slots(task, content, rejection) == []


def test_repeated_slots_are_the_ones_the_second_reply_gave_exactly_as_the_first_did() -> None:
    first = json.dumps({"units": [{"slot": "a", "text": "same", "fact_ids": ["x"]}]})
    second = json.dumps({"units": [{"slot": "a", "text": "same", "fact_ids": ["x"]}]})
    assert repeated_slots(first, second, ["a"]) == ["a"]
    changed = json.dumps({"units": [{"slot": "a", "text": "different", "fact_ids": ["x"]}]})
    assert repeated_slots(first, changed, ["a"]) == []
