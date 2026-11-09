"""A link the model assigned to a section the same plan excludes is settled, not rejected.

Measured live (Aspose.3D-FOSS-for-TypeScript, hosted run 42694304290): ``presentation_planning`` was
rejected twice with "link 'link_target:011' is assigned to a section that is not included:
'quick_start'; link 'link_target:012' ... 'additional_examples'". A link renders only in
``documentation_resources``, so the assignment named a home the plan does not have.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.composition.planning import plan_checks
from tests.readme.composition.synthetic import make_facts
from tests.readme.composition.test_pipeline import _plan


def _facts() -> Any:
    base = make_facts()
    links = (
        Fact("link_target:011", "link_target", "https://reference.example.com/3d/", (Evidence("README.md"),)),
        Fact("link_target:012", "link_target", "https://docs.example.com/3d/examples", (Evidence("README.md"),)),
        Fact("link_target:013", "link_target", "https://docs.example.com/3d/examples", (Evidence("README.md"),)),
    )
    return replace(base, facts=(*base.facts, *links))


def _links(plan: dict) -> list[tuple[str, str]]:
    return [(link["link_fact_id"], link["section_id"]) for link in plan["links"]]


def _included(plan: dict) -> set[str]:
    return {entry["section_id"] for entry in plan["sections"] if entry["include"]}


def test_links_assigned_to_excluded_sections_move_to_documentation_resources() -> None:
    plan = _plan()
    plan["links"] = [
        {"link_fact_id": "link_target:011", "section_id": "additional_examples"},
        {"link_fact_id": "link_target:012", "section_id": "additional_examples"},
    ]
    errors = plan_checks(plan, _facts(), ecosystem="python")
    assert not [e for e in errors if "not included" in e], errors
    assert _links(plan) == [
        ("link_target:011", "documentation_resources"),
        ("link_target:012", "documentation_resources"),
    ]
    assert "documentation_resources" in _included(plan)
    assert "additional_examples" not in _included(plan)


def test_a_link_whose_url_an_included_section_already_carries_is_dropped() -> None:
    plan = _plan()
    plan["links"] = [
        {"link_fact_id": "link_target:012", "section_id": "api_reference"},
        {"link_fact_id": "link_target:013", "section_id": "additional_examples"},
    ]
    plan_checks(plan, _facts(), ecosystem="python")
    assert _links(plan) == [("link_target:012", "api_reference")]


def test_a_link_in_an_included_section_is_left_exactly_as_planned() -> None:
    plan = _plan()
    plan["links"] = [{"link_fact_id": "link_target:011", "section_id": "api_reference"}]
    plan_checks(plan, _facts(), ecosystem="python")
    assert _links(plan) == [("link_target:011", "api_reference")]


def test_an_unverified_link_in_an_excluded_section_still_rejects() -> None:
    plan = _plan()
    plan["links"] = [{"link_fact_id": "link_target:999", "section_id": "additional_examples"}]
    errors = plan_checks(plan, _facts(), ecosystem="python")
    assert any("link_target:999" in e and "not a verified link target" in e for e in errors)
    assert any("not included" in e for e in errors)


def _anchor_only_facts() -> Any:
    base = make_facts()
    kept = tuple(fact for fact in base.facts if fact.kind != "link_target")
    anchor = Fact("link_target:021", "link_target", "#usage", (Evidence("README.md"),))
    return replace(base, facts=(*kept, anchor))


def test_a_link_no_included_section_can_hold_is_dropped_not_rejected() -> None:
    plan = _plan()
    plan["links"] = [{"link_fact_id": "link_target:021", "section_id": "additional_examples"}]
    errors = plan_checks(plan, _anchor_only_facts(), ecosystem="python")
    assert not [e for e in errors if "not included" in e], errors
    assert _links(plan) == []


def test_an_unknown_id_in_an_excluded_section_is_not_dropped() -> None:
    plan = _plan()
    plan["links"] = [{"link_fact_id": "link_target:999", "section_id": "additional_examples"}]
    plan_checks(plan, _facts(), ecosystem="python")
    assert _links(plan) == [("link_target:999", "additional_examples")]


def test_a_duplicate_assignment_is_still_rejected() -> None:
    plan = _plan()
    plan["links"] = [
        {"link_fact_id": "link_target:011", "section_id": "api_reference"},
        {"link_fact_id": "link_target:011", "section_id": "api_reference"},
    ]
    errors = plan_checks(plan, _facts(), ecosystem="python")
    assert any("assigned more than once" in e for e in errors)
