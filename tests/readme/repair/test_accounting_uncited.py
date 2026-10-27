"""S9 accounting for example units whose S4 row cites no fact (hosted run 9, Python).

Four deterministic reviewer findings stood after the cascade: two example headings S4 superseded
into Additional Examples and the heading and code block of an example S4 omitted. In every case the
extractor had already linked the example fact to the very code block (the fact's own evidence names
``unit inherited_unit:NNN.code_block``), but S4's row cited nothing, and the reviewer counts an
accounting disposition only when it cites a fact. Each case has a negative control; nothing the
accounting does changes what renders, and the reviewer is held to it before and after.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.repair.accounting import account_unprinted_units
from repo_presenter.readme.review.independent_reviewer import review_candidate
from repo_presenter.readme.validation.failures import Candidate
from tests.readme.repair.test_accounting import _by_unit, _entry
from tests.readme.repair.test_accounting_examples import (
    ENTRY,
    REVISION,
    _dispositions,
    _example_facts,
    _example_plan,
    _example_units,
)


def _linked(
    facts: FactsDocument, number: int, unit: str | None, polarity: str
) -> FactsDocument:
    """``facts`` with example ``number`` re-written so its evidence names ``unit`` as the fence it
    verified (exactly what the extractor writes when it lifts a fence), at ``polarity``."""
    rebuilt: list[Fact] = []
    for fact in facts.facts:
        if fact.id == f"example:{number:03d}":
            detail = (
                f"lines 1-3; python fence; unit inherited_unit:{unit}"
                if unit
                else "lines 1-3"
            )
            fact = dataclasses.replace(
                fact,
                polarity=polarity,
                evidence=(
                    Evidence("README.md", detail),
                    Evidence("receipts.json", f"example {number}: {polarity}"),
                ),
            )
        rebuilt.append(fact)
    return FactsDocument(facts.repository, facts.source_revision, tuple(rebuilt))


def _candidate(dispositions: dict[str, Any], facts: FactsDocument) -> Candidate:
    plan, units = _example_plan(), _example_units()
    readme = render_readme(ENTRY, facts, plan, units, dispositions)
    return Candidate(
        ENTRY, facts, plan, units, dispositions, readme, None, REVISION, None, (), []
    )


def _facts_linked() -> FactsDocument:
    facts = _linked(_example_facts(), 1, "008.code_block", "SUPPORTED")
    facts = _linked(facts, 2, "010.code_block", "SUPPORTED")
    return _linked(facts, 3, "012.code_block", "CONTRADICTED")


def _superseded_headings() -> dict[str, Any]:
    """Run 9's shape: the headings and code blocks under Additional Examples are SUPERSEDE_
    REDUNDANT and cite nothing."""
    return _dispositions(
        **{
            "009.heading": _entry(
                "009.heading", "SUPERSEDE_REDUNDANT", "additional_examples", []
            ),
            "010.code_block": _entry(
                "010.code_block", "SUPERSEDE_REDUNDANT", "additional_examples", []
            ),
        }
    )


def _omitted_uncited() -> dict[str, Any]:
    return _dispositions(
        **{
            "011.heading": _entry("011.heading", "OMIT_UNSUPPORTED", None, []),
            "012.code_block": _entry("012.code_block", "OMIT_UNSUPPORTED", None, []),
        }
    )


def test_a_superseded_example_heading_is_accounted_by_the_supported_example_it_introduced() -> (
    None
):
    candidate = _candidate(_superseded_headings(), _facts_linked())
    settled, accounted = account_unprinted_units(candidate)
    row = _by_unit(settled)["009.heading"]
    assert row["disposition"] == "SUPERSEDE_REDUNDANT"
    assert row["fact_ids"] == ["example:002"]
    assert [a.reason for a in accounted if a.unit_id.endswith("009.heading")] == [
        "uncited_heading"
    ]


def test_a_superseded_example_heading_is_left_alone_when_the_example_is_not_supported() -> (
    None
):
    """Negative control: the heading's example only failed to verify (UNRESOLVED), so no
    SUPPORTED example is printed under the section's title and there is nothing to cite."""
    facts = _linked(_facts_linked(), 2, "010.code_block", "UNRESOLVED")
    settled, accounted = account_unprinted_units(
        _candidate(_superseded_headings(), facts)
    )
    assert _by_unit(settled)["009.heading"]["fact_ids"] == []
    assert not any(a.unit_id.endswith("009.heading") for a in accounted)


def test_a_superseded_example_heading_is_left_alone_when_the_extractor_linked_another_block() -> (
    None
):
    """Negative control: the example fact's evidence names a different code block, so it says
    nothing about the block under this heading."""
    facts = _linked(_facts_linked(), 2, "008.code_block", "SUPPORTED")
    settled, _ = account_unprinted_units(_candidate(_superseded_headings(), facts))
    assert _by_unit(settled)["009.heading"]["fact_ids"] == []


def test_a_superseded_example_heading_is_left_alone_when_the_block_is_not_printed() -> (
    None
):
    """Negative control: the SUPPORTED example is linked but its code is not in the README."""
    candidate = _candidate(_superseded_headings(), _facts_linked())
    candidate = dataclasses.replace(
        candidate, readme=candidate.readme.replace("convert(scene)", "convert(other)")
    )
    settled, _ = account_unprinted_units(candidate)
    assert _by_unit(settled)["009.heading"]["fact_ids"] == []


def test_an_omitted_contradicted_example_cites_the_fact_the_extractor_linked_to_it() -> (
    None
):
    candidate = _candidate(_omitted_uncited(), _facts_linked())
    settled, accounted = account_unprinted_units(candidate)
    block = _by_unit(settled)["012.code_block"]
    assert block["disposition"] == "OMIT_UNSUPPORTED"
    assert block["fact_ids"] == ["example:003"]
    assert block["destination_section"] is None
    heading = _by_unit(settled)["011.heading"]
    assert heading["disposition"] == "OMIT_UNSUPPORTED"
    assert heading["fact_ids"] == ["example:003"]
    assert {a.unit_id.rsplit(":", 1)[1] for a in accounted} >= {
        "011.heading",
        "012.code_block",
    }


def test_an_omission_is_not_cited_when_the_linked_example_is_supported() -> None:
    """Negative control: omitting a block whose example VERIFIED is not a contradiction, and no
    fact may be cited that does not say so."""
    facts = _linked(_facts_linked(), 3, "012.code_block", "SUPPORTED")
    settled, accounted = account_unprinted_units(_candidate(_omitted_uncited(), facts))
    assert _by_unit(settled)["012.code_block"]["fact_ids"] == []
    assert not any(a.reason == "uncited_contradicted_omission" for a in accounted)


def test_an_omission_is_not_cited_when_no_example_is_linked_to_the_block() -> None:
    """Negative control: a contradicted example exists, but its evidence names no code block."""
    facts = _linked(_facts_linked(), 3, None, "CONTRADICTED")
    settled, accounted = account_unprinted_units(_candidate(_omitted_uncited(), facts))
    assert _by_unit(settled)["012.code_block"]["fact_ids"] == []
    assert _by_unit(settled)["011.heading"]["fact_ids"] == []
    assert not any(a.reason == "uncited_contradicted_omission" for a in accounted)


def test_an_omission_that_already_cites_a_fact_is_not_rewritten() -> None:
    dispositions = _dispositions(
        **{
            "012.code_block": _entry(
                "012.code_block", "OMIT_UNSUPPORTED", None, ["example:003"]
            ),
        }
    )
    settled, accounted = account_unprinted_units(
        _candidate(dispositions, _facts_linked())
    )
    assert _by_unit(settled)["012.code_block"]["fact_ids"] == ["example:003"]
    assert not any(a.unit_id.endswith("012.code_block") for a in accounted)


def test_a_non_example_omission_is_never_given_an_example_fact() -> None:
    """Negative control: an omitted paragraph is not an example block, so even with a CONTRADICTED
    example in the document there is nothing deterministic to cite."""
    dispositions = _dispositions(
        **{"004.list": _entry("004.list", "OMIT_UNSUPPORTED", None, [])}
    )
    settled, _ = account_unprinted_units(_candidate(dispositions, _facts_linked()))
    assert _by_unit(settled)["004.list"]["fact_ids"] == []


def test_the_accounting_never_changes_what_renders_and_the_reviewer_agrees() -> None:
    dispositions = _superseded_headings()
    for unit, row in _by_unit(_omitted_uncited()).items():
        if unit in {"011.heading", "012.code_block"}:
            dispositions["dispositions"] = [
                row if r["unit_id"].endswith(unit) else r
                for r in dispositions["dispositions"]
            ]
    candidate = _candidate(dispositions, _facts_linked())
    settled, accounted = account_unprinted_units(candidate)
    assert accounted
    assert render_readme(
        ENTRY, candidate.facts, candidate.plan, candidate.units, settled
    ) == (candidate.readme)
    original = "# Old\n\n## Quick Start\n\n### Convert A Scene\n\n### Broken Sample\n"

    def verdict(dispositions: dict[str, Any]) -> Any:
        return review_candidate(
            readme_text=candidate.readme,
            units=candidate.units["units"],
            facts=candidate.facts,
            dispositions=dispositions,
            original_readme=original,
        )

    before, after = verdict(candidate.dispositions), verdict(settled)
    assert len(after.findings) < len(before.findings)
