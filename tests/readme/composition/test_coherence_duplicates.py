"""Coherence duplicate recovery. Real shape: Aspose.Email-FOSS-for-Cpp Lane R (2026-11-10) - S8
rewrote the api_reference intro into a verbatim copy of an inherited mapi_message paragraph."""

from __future__ import annotations

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.coherence import (
    recover_coherence_duplicated_units,
    recover_coherence_regressions,
)

MAPI = (
    "MapiMessage represents a message in the MAPI object model and exposes its subject, body, "
    "recipients and attachments as typed properties that can be read, edited and saved back."
)
INTRO = "The API reference lists the public classes of the library and how they fit together."
OTHER = "This section is unrelated prose about installation that is not repeated anywhere else at all."


def _unit(text: str, section: str = "api_reference", slot: str = "intro", fact_ids=("a",)) -> dict:
    return {"section": section, "slot": slot, "text": text, "fact_ids": list(fact_ids)}


def _existing() -> list[dict]:
    return [
        _unit(INTRO),
        _unit(MAPI, section="detailed_member_reference", slot="mapi_message", fact_ids=("m",)),
    ]


def test_a_revision_that_copies_another_paragraph_reverts() -> None:
    copy = MAPI.replace(" ", "  ").upper()  # whitespace and case differ, content is the same
    output = {"units": [_unit(copy, fact_ids=("a", "b"))]}
    fixed = recover_coherence_duplicated_units(output, existing_units=_existing())
    assert fixed is not None
    (unit,) = fixed["units"]
    assert unit["text"] == INTRO and unit["fact_ids"] == ["a"]


def test_a_non_duplicating_revision_is_kept() -> None:
    revised = INTRO + " It is generated from the public headers."
    output = {"units": [_unit(revised)]}
    assert recover_coherence_duplicated_units(output, existing_units=_existing()) is None
    assert output["units"][0]["text"] == revised


def test_a_paragraph_inside_a_multi_paragraph_revision_counts() -> None:
    output = {"units": [_unit(INTRO + "\n\n" + MAPI)]}
    fixed = recover_coherence_duplicated_units(output, existing_units=_existing())
    assert fixed is not None and fixed["units"][0]["text"] == INTRO


def test_a_short_repeated_sentence_is_not_a_duplicate() -> None:
    short = "See the member reference below."
    existing = [_unit(INTRO), _unit(short, section="x", slot="y")]
    output = {"units": [_unit(short)]}
    assert recover_coherence_duplicated_units(output, existing_units=existing) is None


def test_the_full_recovery_chain_includes_the_duplicate_revert() -> None:
    output = {"units": [_unit(MAPI)]}
    facts = FactsDocument("o/r", "0" * 40, ())
    fixed = recover_coherence_regressions(
        output, existing_units=_existing(), facts=facts, tasks=[]
    )
    assert fixed is not None and fixed["units"][0]["text"] == INTRO
