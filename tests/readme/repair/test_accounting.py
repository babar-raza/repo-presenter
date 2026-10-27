"""S9 accounting (readme/repair/accounting.py): a kept inherited unit the render does not print is
accounted as redundant, from the renderer's own placement decisions, and only then.

The shape is the measured aspose-3d-foss/Aspose.3D-FOSS-for-.NET hosted run: a kept list the
destination's planned content already states (``overlap``), kept sub-headings the renderer never
prints (``owned_elsewhere``), and a Mermaid block S4 dropped without citing a fact while the
renderer drew its own At a Glance diagram. Each scenario has a negative control, and the whole
module is held to the reviewer: without the accounting the reviewer REJECTs, with it the same
README is accepted and the README bytes are unchanged.
"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.repair.accounting import (
    account_unprinted_units,
    accounting_document,
)
from repo_presenter.readme.review.independent_reviewer import (
    review_candidate,
    unprinted_kept_units,
)
from repo_presenter.readme.validation.failures import Candidate

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": 1,
            "node_id": "R_1",
        },
    }
)
REVISION = "b" * 40
DOCS_LIST = (
    "- **[Getting started guide](https://docs.example.com/3d)** - installation and walkthroughs.\n"
    "- **[How-to articles](https://kb.example.com/3d)** - task-focused answers."
)
MERMAID = '```mermaid\nflowchart TD\n  a["Old diagram"] --> b["Scene"]\n```'
TITLES = [
    "Build scenes",
    "Save GLB",
    "Read OBJ",
    "Inspect nodes",
    "Convert files",
    "Export meshes",
]


def _fact(fact_id: str, kind: str, value: str, *details: str) -> Fact:
    evidence = tuple(Evidence("README.md", detail) for detail in details) or (
        Evidence("README.md"),
    )
    return Fact(fact_id, kind, value, evidence, polarity="SUPPORTED")


def _unit(unit_id: str, value: str) -> Fact:
    return _fact(f"inherited_unit:{unit_id}", "inherited_unit", value)


def _facts() -> FactsDocument:
    return FactsDocument(
        ENTRY.repository,
        REVISION,
        (
            _fact("identity:repository", "identity", ENTRY.repository),
            _fact("identity:revision", "identity", REVISION),
            _fact("package:name", "package", "aspose-3d-foss"),
            _fact(
                "install_command:pip",
                "install_command",
                "pip install aspose-3d-foss",
                "distribution name declared by the manifest",
                "package registry: found; latest 26.1.0",
            ),
            _fact("license:spdx", "license", "MIT"),
            _fact("license:file", "license", "LICENSE"),
            _fact(
                "public_symbol:aspose.threed.scene",
                "public_symbol",
                "aspose.threed.Scene",
                "line 1; class; public by name",
            ),
            _fact("format:output.glb", "format", ".glb"),
            _fact("format:input.obj", "format", ".obj"),
            _fact(
                "link_target:001",
                "link_target",
                "https://docs.example.com/3d",
                "line 9; external; text 'Docs'",
                "RESOLVED",
            ),
            _fact(
                "link_target:002",
                "link_target",
                "https://kb.example.com/3d",
                "line 10; external; text 'KB'",
                "RESOLVED",
            ),
            _unit("001.heading", "# Old"),
            _unit("002.heading", "## API Reference"),
            _unit("003.heading", "### Main"),
            _unit("004.list", DOCS_LIST),
            _unit("005.code_block", MERMAID),
            _unit("006.heading", "### Orphaned"),
        ),
    )


def _plan(*, glance: bool = True, hubs: bool = True) -> dict[str, Any]:
    included = {
        "identity",
        "badges",
        "opening",
        "navigation",
        "key_capabilities",
        "installation",
        "api_reference",
        "documentation_resources",
        "scope_limitations",
        "license",
    }
    if glance:
        included.add("at_a_glance")
    return {
        "sections": [
            {"section_id": section, "include": section in included, "reason": "r"}
            for section in [
                "identity",
                "badges",
                "opening",
                "navigation",
                "at_a_glance",
                "key_capabilities",
                "installation",
                "dependencies",
                "quick_start",
                "additional_examples",
                "api_reference",
                "documentation_resources",
                "scope_limitations",
                "development_testing",
                "enterprise_relationship",
                "third_party_notices",
                "license",
            ]
        ],
        "core_capabilities": [
            {"title": t, "fact_ids": ["identity:repository"]} for t in TITLES
        ],
        "at_a_glance": {
            "input_format_ids": ["format:input.obj"],
            "output_format_ids": ["format:output.glb"],
            "capability_titles": TITLES,
        },
        "quick_start_example_id": None,
        "additional_example_ids": [],
        "api_hubs": (
            [{"symbol_fact_id": "public_symbol:aspose.threed.scene", "fact_ids": []}]
            if hubs
            else []
        ),
        "material_limitations": [],
        "links": [
            {
                "link_fact_id": "link_target:001",
                "section_id": "documentation_resources",
            },
            {
                "link_fact_id": "link_target:002",
                "section_id": "documentation_resources",
            },
        ],
        "deviations": [],
    }


def _authored(section: str, slot: str, text: str) -> dict[str, Any]:
    return {
        "section": section,
        "slot": slot,
        "text": text,
        "fact_ids": ["identity:repository"],
    }


UNITS: dict[str, Any] = {
    "units": [
        _authored(
            "opening", "opening", "Aspose.3D FOSS for Python builds scenes with Scene."
        ),
        *(
            _authored(
                "key_capabilities", f"capability:{i}", f"Sentence {i} about the API."
            )
            for i in range(1, 7)
        ),
        _authored("api_reference", "intro", "Scene is the entry point."),
        _authored(
            "api_reference",
            "hub:public_symbol:aspose.threed.scene",
            "Scene holds the graph.",
        ),
        _authored(
            "documentation_resources",
            "link:link_target:001",
            "The getting started guide covers installation and walkthroughs.",
        ),
        _authored(
            "documentation_resources",
            "link:link_target:002",
            "The how-to articles give task-focused answers.",
        ),
        _authored("scope_limitations", "scope", "The package writes GLB only."),
    ],
    "omitted": [],
}


def _entry(
    unit: str, disposition: str, destination: str | None, fact_ids: list[str]
) -> dict[str, Any]:
    return {
        "unit_id": f"inherited_unit:{unit}",
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": fact_ids,
        "rationale": "r",
    }


def _dispositions(**overrides: dict[str, Any]) -> dict[str, Any]:
    base = {
        "001.heading": _entry(
            "001.heading", "SUPERSEDE_REDUNDANT", "identity", ["identity:repository"]
        ),
        "002.heading": _entry("002.heading", "VERIFIED_PRESERVE", "api_reference", []),
        "003.heading": _entry("003.heading", "VERIFIED_PRESERVE", "api_reference", []),
        "004.list": _entry(
            "004.list",
            "VERIFIED_PRESERVE",
            "documentation_resources",
            ["link_target:001", "link_target:002"],
        ),
        "005.code_block": _entry("005.code_block", "OMIT_UNSUPPORTED", None, []),
        "006.heading": _entry("006.heading", "NON_CONTENT", None, []),
    }
    base.update(overrides)
    return {"dispositions": list(base.values())}


def _candidate(
    dispositions: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
    facts: FactsDocument | None = None,
) -> Candidate:
    plan = plan if plan is not None else _plan()
    facts = facts if facts is not None else _facts()
    readme = render_readme(ENTRY, facts, plan, UNITS, dispositions)
    return Candidate(
        ENTRY, facts, plan, UNITS, dispositions, readme, None, REVISION, None, (), []
    )


def _by_unit(dispositions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        entry["unit_id"].split(":")[1]: entry for entry in dispositions["dispositions"]
    }


def _unprinted(
    candidate: Candidate, dispositions: dict[str, Any] | None = None
) -> list[str]:
    return [
        unit.split(":")[1]
        for unit, _ in unprinted_kept_units(
            candidate.readme,
            facts=candidate.facts,
            dispositions=dispositions
            if dispositions is not None
            else candidate.dispositions,
        )
    ]


def _verdict(candidate: Candidate, dispositions: dict[str, Any]) -> Any:
    return review_candidate(
        readme_text=candidate.readme,
        units=UNITS["units"],
        facts=candidate.facts,
        dispositions=dispositions,
        original_readme="# Old\n\n## API Reference\n\n### Main\n\n"
        + DOCS_LIST
        + "\n\n"
        + MERMAID
        + "\n",
    )


def test_the_scenario_reproduces_the_measured_defect_before_any_accounting() -> None:
    candidate = _candidate(_dispositions())
    assert _unprinted(candidate) == ["003.heading", "004.list"]
    rules = {
        finding.rule for finding in _verdict(candidate, candidate.dispositions).findings
    }
    assert "disposition_coverage" in rules
    assert (
        "live_readme_loss" in rules
    )  # '### Main' and the Mermaid block are lost unaccounted


def test_a_kept_list_the_destination_already_states_is_accounted_as_redundant() -> None:
    candidate = _candidate(_dispositions())
    settled, accounted = account_unprinted_units(candidate)
    entry = _by_unit(settled)["004.list"]
    assert (entry["disposition"], entry["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "documentation_resources",
    )
    assert set(entry["fact_ids"]) == {"link_target:001", "link_target:002"}
    assert entry["rationale"]
    [list_item] = [a for a in accounted if a.unit_id.endswith("004.list")]
    assert list_item.reason == "overlap"


def test_a_kept_subheading_the_renderer_never_prints_is_accounted_with_the_plans_facts() -> (
    None
):
    candidate = _candidate(_dispositions())
    settled, accounted = account_unprinted_units(candidate)
    entry = _by_unit(settled)["003.heading"]
    assert entry["disposition"] == "SUPERSEDE_REDUNDANT"
    assert entry["destination_section"] == "api_reference"
    assert entry["fact_ids"] == ["public_symbol:aspose.threed.scene"]
    assert next(a for a in accounted if a.unit_id.endswith("003.heading")).reason == (
        "owned_elsewhere"
    )


def test_an_uncited_mermaid_omission_is_superseded_by_the_diagram_the_renderer_drew() -> (
    None
):
    candidate = _candidate(_dispositions())
    settled, accounted = account_unprinted_units(candidate)
    entry = _by_unit(settled)["005.code_block"]
    assert (entry["disposition"], entry["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "at_a_glance",
    )
    # exactly the facts the drawn diagram rests on, none invented
    assert set(entry["fact_ids"]) == {
        "format:input.obj",
        "format:output.glb",
        "identity:repository",
    }
    assert "```mermaid" in candidate.readme
    assert next(
        a for a in accounted if a.unit_id.endswith("005.code_block")
    ).reason == ("uncited_diagram")


def test_accounting_changes_no_byte_of_the_readme_and_turns_the_reviewer_to_accept() -> (
    None
):
    candidate = _candidate(_dispositions())
    settled, accounted = account_unprinted_units(candidate)
    assert len(accounted) == 3
    assert (
        render_readme(ENTRY, candidate.facts, candidate.plan, UNITS, settled)
        == candidate.readme
    )
    assert _verdict(candidate, candidate.dispositions).verdict == "REJECT"
    after = _verdict(candidate, settled)
    assert after.verdict == "ACCEPT", [f.message for f in after.findings]


def test_every_cited_fact_is_a_fact_of_the_document() -> None:
    candidate = _candidate(_dispositions())
    settled, accounted = account_unprinted_units(candidate)
    known = {fact.id for fact in candidate.facts.facts}
    assert accounted
    for item in accounted:
        assert item.fact_ids and set(item.fact_ids) <= known
    assert all(set(e["fact_ids"]) <= known for e in settled["dispositions"])


def test_accounting_is_pure_and_idempotent() -> None:
    candidate = _candidate(_dispositions())
    before = copy.deepcopy(candidate.dispositions)
    settled, first = account_unprinted_units(candidate)
    assert candidate.dispositions == before
    again = _candidate(settled)
    resettled, second = account_unprinted_units(again)
    assert second == []
    assert resettled == settled
    assert accounting_document(first)["accounted"][0]["now"] == "SUPERSEDE_REDUNDANT"


# --- negative controls: nothing is accounted unless the render really did not print it -------


def test_a_heading_the_renderer_prints_is_left_alone() -> None:
    candidate = _candidate(_dispositions())
    settled, accounted = account_unprinted_units(candidate)
    assert "002.heading" not in _unprinted(candidate)
    assert _by_unit(settled)["002.heading"]["disposition"] == "VERIFIED_PRESERVE"
    assert not any(a.unit_id.endswith("002.heading") for a in accounted)


def test_a_list_the_destination_does_not_state_is_left_for_repair() -> None:
    """Overlap is not enough: every item must be stated. The plan links one of the two targets,
    the renderer prints the other item as written, and then the second item's link is taken out of
    the README: the list is no longer stated, so it is left for repair, not accounted."""
    plan = _plan()
    plan["links"] = plan["links"][:1]
    candidate = _candidate(_dispositions(), plan=plan)
    candidate = dataclasses.replace(
        candidate, readme=candidate.readme.replace("https://kb.example.com/3d", "")
    )
    assert "004.list" in _unprinted(candidate)
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["004.list"]["disposition"] == "VERIFIED_PRESERVE"
    assert not any(a.unit_id.endswith("004.list") for a in accounted)



def test_a_kept_list_that_is_printed_is_not_touched() -> None:
    dispositions = _dispositions(
        **{"004.list": _entry("004.list", "VERIFIED_PRESERVE", "scope_limitations", [])}
    )
    candidate = _candidate(dispositions)
    assert "004.list" not in _unprinted(candidate)
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["004.list"]["disposition"] == "VERIFIED_PRESERVE"
    assert not any(a.unit_id.endswith("004.list") for a in accounted)


def test_a_heading_with_no_facts_to_cite_is_left_alone() -> None:
    """No hub, so the plan names no fact for api_reference; the renderer-owned fallback cites
    the class facts only if there are any. A section with nothing to cite is not accounted."""
    facts = FactsDocument(
        ENTRY.repository,
        REVISION,
        tuple(f for f in _facts().facts if f.kind != "public_symbol"),
    )
    candidate = _candidate(_dispositions(), plan=_plan(hubs=False), facts=facts)
    assert "003.heading" in _unprinted(candidate)
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["003.heading"]["disposition"] == "VERIFIED_PRESERVE"
    assert not any(a.unit_id.endswith("003.heading") for a in accounted)


def test_a_mermaid_omission_that_cites_a_fact_stands() -> None:
    cited = _dispositions(
        **{
            "005.code_block": _entry(
                "005.code_block", "OMIT_UNSUPPORTED", None, ["package:name"]
            )
        }
    )
    candidate = _candidate(cited)
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["005.code_block"]["disposition"] == "OMIT_UNSUPPORTED"
    assert not any(a.unit_id.endswith("005.code_block") for a in accounted)


def test_a_mermaid_omission_is_not_superseded_when_no_diagram_was_drawn() -> None:
    candidate = _candidate(_dispositions(), plan=_plan(glance=False))
    assert "```mermaid" not in candidate.readme
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["005.code_block"]["disposition"] == "OMIT_UNSUPPORTED"
    assert not any(a.unit_id.endswith("005.code_block") for a in accounted)


def test_a_non_content_heading_and_other_dispositions_are_never_rewritten() -> None:
    candidate = _candidate(_dispositions())
    settled, _ = account_unprinted_units(candidate)
    originals = _by_unit(candidate.dispositions)
    rewritten = {
        unit for unit, entry in _by_unit(settled).items() if entry != originals[unit]
    }
    assert rewritten == {"003.heading", "004.list", "005.code_block"}


@pytest.mark.parametrize(
    "disposition", ["VERIFIED_REWRITE", "OMIT_UNSUPPORTED", "DEFER_UNRESOLVED"]
)
def test_only_a_kept_as_written_unit_is_accounted_as_overlap(disposition: str) -> None:
    """A rewritten, omitted or deferred list prints nothing as written and claims to; the
    reviewer's kept-unprinted test does not apply, and neither does this stage."""
    dispositions = _dispositions(
        **{
            "004.list": _entry(
                "004.list", disposition, "documentation_resources", ["link_target:001"]
            )
        }
    )
    candidate = _candidate(dispositions)
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["004.list"]["disposition"] == disposition
    assert not any(a.unit_id.endswith("004.list") for a in accounted)
