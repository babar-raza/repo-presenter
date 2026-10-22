"""Targeted tests for coherence.py's dispositions-aware duplicate-opening guard.

coherence_checks() delegates every section's rules to authoring.unit_checks(), so these tests
cover only the plumbing this module adds on top: that coherence_checks() and
recover_coherence_regressions() both forward ``dispositions`` through to that shared check and
recovery, the same way run_lane_r_coherence.py's real call site does. authoring.py's own tests
cover the check and recovery's actual behaviour in depth.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import SectionTask
from repo_presenter.readme.composition.coherence import coherence_checks, recover_coherence_regressions
from tests.readme.composition.synthetic import make_facts

_PRESERVED = (
    "Aspose Widget FOSS for Python is a free, open-source, pure-Python library for rendering "
    "widgets."
)
_AUTHORED_DUPLICATE = _PRESERVED
_AUTHORED_WITH_NEW_SENTENCE = (
    _PRESERVED + " It also provides a built-in validator via Widget.validate()."
)


def _facts_with_preserved_opening() -> FactsDocument:
    base = make_facts()
    preserved = Fact(
        "inherited_unit:004.paragraph",
        "inherited_unit",
        _PRESERVED,
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


def _opening_task() -> SectionTask:
    return SectionTask(
        section_id="opening", packet={}, accepted_ids=frozenset({"package:name"}), slots=("opening",)
    )


def test_coherence_checks_rejects_a_revised_opening_unit_that_restates_preserved() -> None:
    facts = _facts_with_preserved_opening()
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": _AUTHORED_DUPLICATE,
                "fact_ids": ["package:name"],
            }
        ]
    }
    errors = coherence_checks(
        output,
        [_opening_task()],
        facts,
        "Aspose Widget FOSS for Python",
        dispositions=_dispositions_preserving_opening(),
    )
    assert any("restates the inherited paragraph" in error for error in errors)


def test_coherence_checks_without_dispositions_skips_the_new_check() -> None:
    facts = _facts_with_preserved_opening()
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": _AUTHORED_DUPLICATE,
                "fact_ids": ["package:name"],
            }
        ]
    }
    errors = coherence_checks(output, [_opening_task()], facts, "Aspose Widget FOSS for Python")
    assert not any("restates the inherited paragraph" in error for error in errors)


def test_recover_coherence_regressions_trims_a_duplicated_opening_unit() -> None:
    facts = _facts_with_preserved_opening()
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": _AUTHORED_WITH_NEW_SENTENCE,
                "fact_ids": ["package:name"],
            }
        ]
    }
    result = recover_coherence_regressions(
        output,
        existing_units=output["units"],
        facts=facts,
        tasks=[_opening_task()],
        dispositions=_dispositions_preserving_opening(),
    )
    assert result is not None
    assert result["units"][0]["text"] == "It also provides a built-in validator via Widget.validate()."


def test_recover_coherence_regressions_without_dispositions_is_unaffected() -> None:
    facts = _facts_with_preserved_opening()
    output = {
        "units": [
            {
                "section": "opening",
                "slot": "opening",
                "text": _AUTHORED_WITH_NEW_SENTENCE,
                "fact_ids": ["package:name"],
            }
        ]
    }
    result = recover_coherence_regressions(
        output, existing_units=output["units"], facts=facts, tasks=[_opening_task()]
    )
    assert result is None
