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
from repo_presenter.readme.composition.coherence import (
    coherence_checks,
    recover_coherence_regressions,
    recover_coherence_stray_identifiers,
    recover_every_section_duplicates_preserved,
)
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


# Real hosted defect (aspose-email-foss/Aspose.Email-FOSS-for-Cpp, run 41142584634): S8
# coherence's own revision of api_reference/intro restated inherited_unit:043.paragraph
# (VERIFIED_PRESERVE into api_reference) nearly verbatim, so the renderer printed it twice --
# a duplicate_paragraph review REJECT, since this fix only reached "opening" before.
# recover_every_section_duplicates_preserved fixes this shape correctly in isolation (tested
# directly below), but is NOT wired into recover_coherence_regressions: live verification
# (aspose-slides-foss/Python, run 41164865868) found that applying it blindly to every section
# produces real false positives on multi-slot, list-heavy sections (see its own docstring).
# Kept as a tested, correct building block for a properly-scoped follow-up.


def _api_reference_task() -> SectionTask:
    return SectionTask(
        section_id="api_reference",
        packet={},
        accepted_ids=frozenset({"package:name"}),
        slots=("intro",),
    )


def _facts_with_preserved_api_reference() -> FactsDocument:
    base = make_facts()
    preserved = Fact(
        "inherited_unit:043.paragraph",
        "inherited_unit",
        _PRESERVED,
        (Evidence("README.md", "section 'API Reference'"),),
    )
    return FactsDocument(base.repository, base.source_revision, (*base.facts, preserved))


def _dispositions_preserving_api_reference() -> dict[str, object]:
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:043.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "api_reference",
                "fact_ids": [],
                "rationale": "test fixture",
            }
        ]
    }


def test_recover_every_section_duplicates_preserved_trims_an_api_reference_unit() -> None:
    facts = _facts_with_preserved_api_reference()
    output = {
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": _AUTHORED_WITH_NEW_SENTENCE,
                "fact_ids": ["package:name"],
            }
        ]
    }
    result = recover_every_section_duplicates_preserved(
        output,
        tasks=[_api_reference_task()],
        dispositions=_dispositions_preserving_api_reference(),
        facts=facts,
    )
    assert result is not None
    assert result["units"][0]["text"] == "It also provides a built-in validator via Widget.validate()."


def test_recover_coherence_regressions_does_not_fix_a_non_opening_section() -> None:
    """Pins the reverted (safe) behavior: recover_coherence_regressions only ever fixes
    "opening" by default now, even when dispositions cover another section too."""
    facts = _facts_with_preserved_api_reference()
    output = {
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": _AUTHORED_WITH_NEW_SENTENCE,
                "fact_ids": ["package:name"],
            }
        ]
    }
    result = recover_coherence_regressions(
        output,
        existing_units=output["units"],
        facts=facts,
        tasks=[_api_reference_task()],
        dispositions=_dispositions_preserving_api_reference(),
    )
    assert result is None


# Real hosted defect (aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 41102257446): a coherence
# revision of api_reference/intro claimed the listing is "grouped exactly as reference.aspose.org
# organizes them" -- a real stray identifier (an external site's domain, not a fact), repeated
# byte for byte on the universal re-ask, since S8's own run_job call carries no narrow= and none
# of the other recover_coherence_* passes are built to re-run unit_checks's own stray-identifier
# rule.
_CLEAN_INTRO = "The library's public types are listed below, with Widget as the entry point."
_STRAY_INTRO = (
    "The library's public types are listed below, grouped exactly as reference.example.org "
    "organizes them."
)


def _api_reference_task() -> SectionTask:
    return SectionTask(
        section_id="api_reference",
        packet={},
        accepted_ids=frozenset({"public_symbol:aspose_widget_foss.widget"}),
        slots=("intro",),
    )


def test_coherence_checks_rejects_a_revision_naming_an_unaccepted_external_site() -> None:
    facts = make_facts()
    output = {
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": _STRAY_INTRO,
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            }
        ]
    }
    errors = coherence_checks(output, [_api_reference_task()], facts, "Aspose Widget FOSS")
    assert any("identifiers that are not accepted fact values" in error for error in errors)


def test_recover_coherence_stray_identifiers_reverts_to_the_clean_pre_coherence_text() -> None:
    facts = make_facts()
    existing = [
        {
            "section": "api_reference",
            "slot": "intro",
            "text": _CLEAN_INTRO,
            "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
        }
    ]
    output = {
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": _STRAY_INTRO,
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            }
        ]
    }
    result = recover_coherence_stray_identifiers(
        output,
        existing_units=existing,
        tasks=[_api_reference_task()],
        facts=facts,
        name="Aspose Widget FOSS",
    )
    assert result is not None
    assert result["units"][0]["text"] == _CLEAN_INTRO


def test_recover_coherence_stray_identifiers_leaves_a_clean_unit_untouched() -> None:
    facts = make_facts()
    existing = [
        {
            "section": "api_reference",
            "slot": "intro",
            "text": _CLEAN_INTRO,
            "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
        }
    ]
    output = {
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": _CLEAN_INTRO,
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            }
        ]
    }
    result = recover_coherence_stray_identifiers(
        output,
        existing_units=existing,
        tasks=[_api_reference_task()],
        facts=facts,
        name="Aspose Widget FOSS",
    )
    assert result is None


def test_recover_coherence_regressions_wires_the_stray_identifier_pass_through_name() -> None:
    facts = make_facts()
    existing = [
        {
            "section": "api_reference",
            "slot": "intro",
            "text": _CLEAN_INTRO,
            "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
        }
    ]
    output = {
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": _STRAY_INTRO,
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            }
        ]
    }
    result = recover_coherence_regressions(
        output,
        existing_units=existing,
        facts=facts,
        tasks=[_api_reference_task()],
        name="Aspose Widget FOSS",
    )
    assert result is not None
    assert result["units"][0]["text"] == _CLEAN_INTRO


def test_recover_coherence_regressions_without_a_name_changes_nothing() -> None:
    """The default empty name keeps every existing caller (none of which pass name=) working
    exactly as before; it simply never recovers this one new defect class without one."""
    facts = make_facts()
    existing = [
        {
            "section": "api_reference",
            "slot": "intro",
            "text": _CLEAN_INTRO,
            "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
        }
    ]
    output = {
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": _STRAY_INTRO,
                "fact_ids": ["public_symbol:aspose_widget_foss.widget"],
            }
        ]
    }
    result = recover_coherence_regressions(
        output, existing_units=existing, facts=facts, tasks=[_api_reference_task()]
    )
    assert result is None
