"""``presentation_planning``'s own last-resort ``recover=`` corrections.

Measured live (aspose-words-foss/Aspose.Words-FOSS-for-.NET, hosted run 41180018042, branch
``fix/link-budget-tiers``): once an earlier blocker cleared, the run reached ``presentation_planning``
and failed there because the model assigned the same ``link_target:NNN`` fact to more than one
``links`` entry. ``recover_duplicate_link_assignments``/``recover_planning_output`` already existed
in this module for exactly this case, but ``cascade.py``'s own ``_run_planning`` never passed
``recover=`` into its ``run_job`` call -- the correction was dead code, never reachable on a real
run. These tests cover the recovery functions directly; ``tests/test_cascade_s9.py`` proves the
wiring itself against the real cascade.
"""

from __future__ import annotations

from repo_presenter.readme.composition.planning import (
    recover_duplicate_link_assignments,
    recover_planning_output,
)
from tests.readme.composition.synthetic import make_facts


def _plan_with_duplicate_link() -> dict:
    return {
        "core_capabilities": [
            {"title": "x", "fact_ids": ["package:name"], "shared_fact_ids": []},
        ],
        "links": [
            {"link_fact_id": "link_target:001", "section_id": "scope_limitations"},
            {"link_fact_id": "link_target:002", "section_id": "api_reference"},
            {"link_fact_id": "link_target:001", "section_id": "quick_start"},
        ],
    }


def test_recover_duplicate_link_assignments_keeps_the_first_and_drops_later_repeats() -> None:
    output = _plan_with_duplicate_link()
    recovered = recover_duplicate_link_assignments(output)
    assert recovered is not None
    assert recovered["links"] == [
        {"link_fact_id": "link_target:001", "section_id": "scope_limitations"},
        {"link_fact_id": "link_target:002", "section_id": "api_reference"},
    ]
    # the input is never mutated -- recover= always hands run_job a new dict to re-validate
    assert output["links"] == _plan_with_duplicate_link()["links"]


def test_recover_duplicate_link_assignments_is_a_noop_when_every_target_is_unique() -> None:
    output = {
        "links": [
            {"link_fact_id": "link_target:001", "section_id": "scope_limitations"},
            {"link_fact_id": "link_target:002", "section_id": "api_reference"},
        ]
    }
    assert recover_duplicate_link_assignments(output) is None


def test_recover_duplicate_link_assignments_is_a_noop_with_no_links_field() -> None:
    assert recover_duplicate_link_assignments({"core_capabilities": []}) is None


def test_recover_planning_output_applies_the_link_dedupe() -> None:
    facts = make_facts()
    output = _plan_with_duplicate_link()
    recovered = recover_planning_output(output, facts)
    assert recovered is not None
    assert recovered["links"] == [
        {"link_fact_id": "link_target:001", "section_id": "scope_limitations"},
        {"link_fact_id": "link_target:002", "section_id": "api_reference"},
    ]


def test_recover_planning_output_is_a_noop_when_neither_last_resort_applies() -> None:
    facts = make_facts()
    output = {
        # Confirmed non-triggering: the exact core_capabilities entry tests/test_cascade.py's own
        # _PLANNING_REPLY carries, which that fixture's cascade test accepts on the first attempt
        # (zero retries, so recover_uncited_capability_titles never has anything to fix for it).
        "core_capabilities": [
            {"title": "Install with pip", "fact_ids": ["install_command:pip"], "shared_fact_ids": []},
        ],
        "links": [],
    }
    assert recover_planning_output(output, facts) is None
