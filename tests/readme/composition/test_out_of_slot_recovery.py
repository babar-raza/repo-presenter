"""Recovery for a unit that cites a fact outside its own slot's planned set.

Found on hosted run 40474666141 (aspose-3d-foss/Aspose.3D-FOSS-for-.NET): S8 coherence returned
capability:4 with the text S6 had accepted, plus format:output.3mf in its fact_ids. That fact sat
only in the opening and At a Glance (the plan's capability slot held eleven of the sixteen format
facts), so the unit was refused twice and one refused task made the repository unpresentable.
The recoveries here only delete or revert; none adds a citation or rewords a sentence, and every
result is judged again by the same checks.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from repo_presenter.core.errors import JobError, OutputRejectedError
from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    SectionTask,
    citable,
    unit_checks,
)
from repo_presenter.readme.composition.authoring_retry import (
    recover_authoring_output,
    withdraw_out_of_slot_citations,
)
from repo_presenter.readme.composition.coherence import (
    coherence_checks,
    recover_coherence_out_of_slot_citations,
    recover_coherence_regressions,
)

NAME = "Aspose Widget FOSS for Python"
SLOT = "capability:1"
IN_SLOT = ("format:input.fbx", "format:output.fbx", "format:input.3mf")
OUTSIDE = "format:output.3mf"


def _facts() -> FactsDocument:
    def fact(fact_id: str, kind: str, value: str) -> Fact:
        return Fact(fact_id, kind, value, (Evidence("README.md"),))  # type: ignore[arg-type]

    return FactsDocument(
        "org/Aspose.Widget-FOSS-for-Python",
        "f" * 40,
        (
            fact(
                "identity:repository", "identity", "org/Aspose.Widget-FOSS-for-Python"
            ),
            fact("package:name", "package", "aspose-widget-foss"),
            fact("format:input.fbx", "format", ".fbx"),
            fact("format:output.fbx", "format", ".fbx"),
            fact("format:input.3mf", "format", ".3mf"),
            fact("format:output.3mf", "format", ".3mf"),
        ),
    )


def _task() -> SectionTask:
    accepted = frozenset({"identity:repository", "package:name", *IN_SLOT, OUTSIDE})
    return SectionTask(
        "key_capabilities",
        {},
        accepted,
        (SLOT,),
        slot_facts={SLOT: frozenset(IN_SLOT)},
        slot_titles={SLOT: "Format conversion"},
    )


def _unit(text: str, fact_ids: list[str]) -> dict[str, Any]:
    return {
        "section": "key_capabilities",
        "slot": SLOT,
        "text": text,
        "fact_ids": fact_ids,
    }


ACCEPTED = _unit("It reads and writes .fbx and .3mf models.", list(IN_SLOT))
REVISED = _unit("It reads and writes .fbx and .3mf models.", [*IN_SLOT, OUTSIDE])


def test_the_hosted_shape_is_refused_by_the_checks_as_recorded() -> None:
    errors = coherence_checks(
        {"units": [copy.deepcopy(REVISED)]},
        [_task()],
        _facts(),
        NAME,
        existing_units=[ACCEPTED],
    )
    assert any(
        "cites facts outside its slot's planned set (format:output.3mf)" in e
        for e in errors
    )
    assert not any("outside this section's set" in e for e in errors)


def test_the_accepted_unit_passes_the_same_checks() -> None:
    assert (
        coherence_checks(
            {"units": [copy.deepcopy(ACCEPTED)]}, [_task()], _facts(), NAME
        )
        == []
    )


def test_coherence_reverts_a_unit_with_nothing_to_withdraw_but_its_whole_text() -> None:
    output = {"units": [copy.deepcopy(REVISED)]}
    recovered = recover_coherence_regressions(
        output, existing_units=[ACCEPTED], facts=_facts(), tasks=[_task()]
    )
    assert recovered is not None
    assert recovered["units"] == [ACCEPTED]
    assert (
        coherence_checks(
            recovered, [_task()], _facts(), NAME, existing_units=[ACCEPTED]
        )
        == []
    )


def test_coherence_withdraws_the_citation_with_its_sentence_when_other_sentences_remain() -> (
    None
):
    revised = _unit(
        "It reads and writes .fbx models. It also reads and writes .3mf models.",
        [*IN_SLOT, OUTSIDE],
    )
    output = {"units": [revised]}
    recovered = recover_coherence_out_of_slot_citations(
        output, existing_units=[ACCEPTED], tasks=[_task()], facts=_facts()
    )
    assert recovered is not None
    unit = recovered["units"][0]
    assert unit["text"] == "It reads and writes .fbx models."
    assert unit["fact_ids"] == list(IN_SLOT)
    assert OUTSIDE not in unit["fact_ids"]


def test_nothing_is_reverted_when_the_earlier_unit_cites_outside_the_slot_too() -> None:
    earlier = _unit("It reads and writes .fbx and .3mf models.", [*IN_SLOT, OUTSIDE])
    output = {"units": [copy.deepcopy(REVISED)]}
    assert (
        recover_coherence_out_of_slot_citations(
            output, existing_units=[earlier], tasks=[_task()], facts=_facts()
        )
        is None
    )
    assert output["units"] == [REVISED]


def test_a_unit_citing_only_its_own_slot_is_not_touched() -> None:
    output = {"units": [copy.deepcopy(ACCEPTED)]}
    assert (
        recover_coherence_out_of_slot_citations(
            output, existing_units=[ACCEPTED], tasks=[_task()], facts=_facts()
        )
        is None
    )


def test_a_revert_that_the_checks_would_still_refuse_stays_refused() -> None:
    bad_text = "It reads and writes .fbx, .3mf and <Widget> models."
    earlier = _unit(bad_text, list(IN_SLOT))
    output = {"units": [_unit(bad_text, [*IN_SLOT, OUTSIDE])]}
    recovered = recover_coherence_out_of_slot_citations(
        output, existing_units=[earlier], tasks=[_task()], facts=_facts()
    )
    assert recovered is not None
    assert coherence_checks(recovered, [_task()], _facts(), NAME) != []


def test_withdrawal_removes_the_sentence_and_adds_nothing() -> None:
    unit = _unit(
        "It reads .fbx models. It writes .3mf models. Nothing else is promised.",
        [*IN_SLOT, OUTSIDE],
    )
    before = list(unit["fact_ids"])
    assert withdraw_out_of_slot_citations(unit, citable(_task(), SLOT), _facts())
    assert unit["text"] == "It reads .fbx models. Nothing else is promised."
    assert set(unit["fact_ids"]) < set(before)
    assert unit["fact_ids"] == [i for i in before if i != OUTSIDE]


def test_withdrawal_leaves_a_unit_that_would_have_no_sentence_left() -> None:
    unit = _unit("It writes .3mf models.", [*IN_SLOT, OUTSIDE])
    snapshot = copy.deepcopy(unit)
    assert not withdraw_out_of_slot_citations(unit, citable(_task(), SLOT), _facts())
    assert unit == snapshot


def test_withdrawal_leaves_a_unit_when_no_sentence_spells_the_outside_fact() -> None:
    unit = _unit(
        "It reads .fbx models. It converts between formats.", [*IN_SLOT, OUTSIDE]
    )
    snapshot = copy.deepcopy(unit)
    assert not withdraw_out_of_slot_citations(unit, citable(_task(), SLOT), _facts())
    assert unit == snapshot


def test_withdrawal_leaves_a_unit_citing_an_unknown_fact() -> None:
    unit = _unit(
        "It reads .fbx models. It writes .3mf models.", [*IN_SLOT, "format:output.zzz"]
    )
    snapshot = copy.deepcopy(unit)
    assert not withdraw_out_of_slot_citations(unit, citable(_task(), SLOT), _facts())
    assert unit == snapshot


def test_authoring_recovery_withdraws_and_the_result_passes_the_authoring_checks() -> (
    None
):
    revised = _unit(
        "It reads and writes .fbx models. It also writes .3mf models.",
        [*IN_SLOT, OUTSIDE],
    )
    output: dict[str, Any] = {"units": [revised], "omitted": []}
    refused = unit_checks(copy.deepcopy(output), _task(), _facts(), NAME)
    assert any("outside its slot's planned set" in error for error in refused)
    recovered = recover_authoring_output(output, task=_task(), facts=_facts())
    assert recovered is not None
    assert unit_checks(recovered, _task(), _facts(), NAME) == []
    assert recovered["units"][0]["fact_ids"] == list(IN_SLOT)


def test_authoring_recovery_does_nothing_for_a_unit_that_stays_in_its_slot() -> None:
    output: dict[str, Any] = {"units": [copy.deepcopy(ACCEPTED)], "omitted": []}
    assert recover_authoring_output(output, task=_task(), facts=_facts()) is None


def test_authoring_recovery_fails_closed_when_one_sentence_carries_the_citation() -> (
    None
):
    output: dict[str, Any] = {"units": [copy.deepcopy(REVISED)], "omitted": []}
    assert recover_authoring_output(output, task=_task(), facts=_facts()) is None
    assert output["units"] == [REVISED]


def test_an_output_rejection_is_a_job_error_so_existing_handlers_still_catch_it() -> (
    None
):
    assert issubclass(OutputRejectedError, JobError)
    with pytest.raises(JobError):
        raise OutputRejectedError("section_authoring: output rejected twice")
