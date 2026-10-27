"""S9 accounting for the example sections and for headings the renderer owns.

The shape is hosted run 7 of aspose-3d-foss/Aspose.3D-FOSS-for-.NET, where ten deterministic
reviewer findings stood after the cascade had finished: a kept example code block the renderer
prints from its verified example fact with supplied usings above it, kept example headings the
renderer replaces with its own titles, the heading of an example S4 omitted because a fact
contradicts it, and headings S4 superseded into the API reference without citing a fact. Each
case has a negative control, the README bytes are proved unchanged by the accounting, and the
whole set is held to the reviewer: before the accounting it REJECTs, after it it ACCEPTs.
"""

from __future__ import annotations

import copy
import dataclasses
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.repair.accounting import account_unprinted_units
from repo_presenter.readme.review.independent_reviewer import (
    heading_printed,
    review_candidate,
    unprinted_kept_units,
)
from repo_presenter.readme.validation.failures import Candidate
from tests.readme.repair.test_accounting import (
    ENTRY,
    REVISION,
    UNITS,
    _by_unit,
    _entry,
    _facts,
    _plan,
    _unit,
)

QUICK = "```python\nscene = Scene()\n```"
CONVERT = "```python\nconvert(scene)\n```"
BROKEN = "```python\nbroken(\n```"


def _example(number: int, code: str, polarity: str, prelude: str = "") -> Fact:
    return Fact(
        f"example:{number:03d}",
        "example",
        code,
        (Evidence("README.md", f"example {number}: {polarity}"),),
        polarity=polarity,  # type: ignore[arg-type]
        attributes={"prelude": prelude} if prelude else None,
    )


def _example_facts() -> FactsDocument:
    base = _facts()
    return FactsDocument(
        base.repository,
        base.source_revision,
        (
            *base.facts,
            _example(1, "scene = Scene()\n", "SUPPORTED", "import threed"),
            _example(2, "convert(scene)\n", "SUPPORTED"),
            _example(3, "broken(\n", "CONTRADICTED"),
            _unit("007.heading", "## Quick Start"),
            _unit("008.code_block", QUICK),
            _unit("009.heading", "### Convert A Scene"),
            _unit("010.code_block", CONVERT),
            _unit("011.heading", "### Broken Sample"),
            _unit("012.code_block", BROKEN),
        ),
    )


def _example_plan() -> dict[str, Any]:
    plan = _plan()
    for section in plan["sections"]:
        if section["section_id"] in {"quick_start", "additional_examples"}:
            section["include"] = True
    plan["quick_start_example_id"] = "example:001"
    plan["additional_example_ids"] = ["example:002"]
    plan["flagship_example_id"] = "example:002"
    return plan


def _example_units() -> dict[str, Any]:
    units = copy.deepcopy(UNITS)
    units["units"] += [
        {
            "section": "quick_start",
            "slot": "lead_in",
            "text": "Create a scene.",
            "fact_ids": ["example:001"],
        },
        {
            "section": "additional_examples",
            "slot": "preview",
            "text": "More examples follow.",
            "fact_ids": ["example:002"],
        },
        {
            "section": "additional_examples",
            "slot": "workflow:example:002",
            "text": "Convert a scene with the converter.",
            "fact_ids": ["example:002"],
        },
    ]
    return units


def _dispositions(**overrides: dict[str, Any] | None) -> dict[str, Any]:
    rows = {
        "007.heading": _entry("007.heading", "VERIFIED_PRESERVE", "quick_start", []),
        "008.code_block": _entry(
            "008.code_block", "VERIFIED_PRESERVE", "quick_start", ["example:001"]
        ),
        "009.heading": _entry(
            "009.heading", "VERIFIED_PRESERVE", "additional_examples", []
        ),
        "010.code_block": _entry(
            "010.code_block",
            "VERIFIED_PRESERVE",
            "additional_examples",
            ["example:002"],
        ),
        "011.heading": _entry(
            "011.heading", "VERIFIED_PRESERVE", "additional_examples", []
        ),
        "012.code_block": _entry(
            "012.code_block", "OMIT_UNSUPPORTED", None, ["example:003"]
        ),
        "001.heading": _entry(
            "001.heading", "SUPERSEDE_REDUNDANT", "identity", ["identity:repository"]
        ),
        "002.heading": _entry("002.heading", "NON_CONTENT", None, []),
        "003.heading": _entry(
            "003.heading", "SUPERSEDE_REDUNDANT", "api_reference", []
        ),
        "004.list": _entry("004.list", "NON_CONTENT", None, []),
        "005.code_block": _entry("005.code_block", "NON_CONTENT", None, []),
        "006.heading": _entry("006.heading", "NON_CONTENT", None, []),
    }
    for unit, row in overrides.items():
        if row is None:
            rows.pop(unit)
        else:
            rows[unit] = row
    return {"dispositions": list(rows.values())}


def _candidate(
    dispositions: dict[str, Any] | None = None,
    *,
    facts: FactsDocument | None = None,
    plan: dict[str, Any] | None = None,
) -> Candidate:
    dispositions = dispositions if dispositions is not None else _dispositions()
    facts = facts if facts is not None else _example_facts()
    plan = plan if plan is not None else _example_plan()
    units = _example_units()
    readme = render_readme(ENTRY, facts, plan, units, dispositions)
    return Candidate(
        ENTRY, facts, plan, units, dispositions, readme, None, REVISION, None, (), []
    )


def _unprinted(candidate: Candidate) -> list[str]:
    return [
        unit.split(":")[1]
        for unit, _ in unprinted_kept_units(
            candidate.readme, facts=candidate.facts, dispositions=candidate.dispositions
        )
    ]


def test_the_fixture_reproduces_the_hosted_shape() -> None:
    candidate = _candidate()
    assert "import threed\nscene = Scene()" in candidate.readme
    assert "### Convert A Scene" not in candidate.readme
    assert "### Convert A Scene" not in candidate.readme.replace(
        "### Convert a Scene With the Converter", ""
    )
    assert {"008.code_block", "009.heading", "011.heading"} <= set(
        _unprinted(candidate)
    )


def test_a_kept_example_block_the_renderer_prints_with_supplied_usings_is_accounted() -> (
    None
):
    candidate = _candidate()
    settled, accounted = account_unprinted_units(candidate)
    row = _by_unit(settled)["008.code_block"]
    assert row["disposition"] == "SUPERSEDE_REDUNDANT"
    assert row["fact_ids"] == ["example:001"]
    assert [a.reason for a in accounted if a.unit_id.endswith("008.code_block")] == [
        "owned_elsewhere"
    ]


def test_an_example_block_the_readme_does_not_contain_is_left_for_repair() -> None:
    """Negative control: the cited example is SUPPORTED, but its code is not in the README."""
    candidate = _candidate()
    candidate = dataclasses.replace(
        candidate, readme=candidate.readme.replace("scene = Scene()", "scene = Other()")
    )
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["008.code_block"]["disposition"] == "VERIFIED_PRESERVE"
    assert not any(a.unit_id.endswith("008.code_block") for a in accounted)


def test_an_example_block_citing_no_supported_example_is_left_for_repair() -> None:
    """Negative control: a block that cites a CONTRADICTED example is not printed by the section,
    so nothing supports calling it redundant."""
    dispositions = _dispositions(
        **{
            "008.code_block": _entry(
                "008.code_block", "VERIFIED_PRESERVE", "quick_start", ["example:003"]
            )
        }
    )
    settled, accounted = account_unprinted_units(_candidate(dispositions))
    assert _by_unit(settled)["008.code_block"]["disposition"] == "VERIFIED_PRESERVE"
    assert not any(a.unit_id.endswith("008.code_block") for a in accounted)


def test_a_kept_heading_over_a_printed_example_is_accounted_by_that_example() -> None:
    settled, accounted = account_unprinted_units(_candidate())
    row = _by_unit(settled)["009.heading"]
    assert row["disposition"] == "SUPERSEDE_REDUNDANT"
    assert row["fact_ids"] == ["example:002"]


def test_a_kept_heading_over_an_example_the_readme_does_not_print_is_left_alone() -> (
    None
):
    """Negative control: the example the heading introduced is not in the README."""
    candidate = _candidate()
    candidate = dataclasses.replace(
        candidate, readme=candidate.readme.replace("convert(scene)", "converted(scene)")
    )
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["009.heading"]["disposition"] == "VERIFIED_PRESERVE"
    assert not any(a.unit_id.endswith("009.heading") for a in accounted)


def test_the_heading_of_an_example_a_fact_contradicts_is_omitted_with_it() -> None:
    settled, accounted = account_unprinted_units(_candidate())
    row = _by_unit(settled)["011.heading"]
    assert row["disposition"] == "OMIT_UNSUPPORTED"
    assert row["fact_ids"] == ["example:003"]
    assert row["destination_section"] is None
    assert [a.now for a in accounted if a.unit_id.endswith("011.heading")] == [
        "OMIT_UNSUPPORTED"
    ]


def test_a_heading_before_an_omission_no_fact_contradicts_is_left_alone() -> None:
    """Negative control: the payload is omitted citing a fact that is not a CONTRADICTED example,
    so the heading is not omitted along with it."""
    dispositions = _dispositions(
        **{
            "012.code_block": _entry(
                "012.code_block", "OMIT_UNSUPPORTED", None, ["identity:repository"]
            )
        }
    )
    settled, _ = account_unprinted_units(_candidate(dispositions))
    assert _by_unit(settled)["011.heading"]["disposition"] == "VERIFIED_PRESERVE"


def test_a_heading_superseded_into_the_api_reference_without_a_fact_is_given_its_facts() -> (
    None
):
    candidate = _candidate()
    assert not heading_printed("### Main", candidate.readme)
    settled, accounted = account_unprinted_units(candidate)
    row = _by_unit(settled)["003.heading"]
    assert row["disposition"] == "SUPERSEDE_REDUNDANT"
    assert row["destination_section"] == "api_reference"
    assert row["fact_ids"] == ["public_symbol:aspose.threed.scene"]
    assert [a.reason for a in accounted if a.unit_id.endswith("003.heading")] == [
        "uncited_heading"
    ]


def test_a_superseded_heading_that_already_cites_a_fact_is_not_touched() -> None:
    dispositions = _dispositions(
        **{
            "003.heading": _entry(
                "003.heading", "SUPERSEDE_REDUNDANT", "api_reference", ["package:name"]
            )
        }
    )
    settled, accounted = account_unprinted_units(_candidate(dispositions))
    assert _by_unit(settled)["003.heading"]["fact_ids"] == ["package:name"]
    assert not any(a.unit_id.endswith("003.heading") for a in accounted)


def test_a_superseded_heading_into_a_section_the_plan_leaves_out_is_not_cited() -> None:
    """Negative control: nothing is built from a section that is not rendered."""
    plan = _example_plan()
    for section in plan["sections"]:
        if section["section_id"] == "api_reference":
            section["include"] = False
    settled, accounted = account_unprinted_units(_candidate(plan=plan))
    assert _by_unit(settled)["003.heading"]["fact_ids"] == []
    assert not any(a.unit_id.endswith("003.heading") for a in accounted)


def test_the_accounting_never_changes_what_renders() -> None:
    candidate = _candidate()
    settled, accounted = account_unprinted_units(candidate)
    assert len(accounted) == 4
    rerendered = render_readme(
        ENTRY, candidate.facts, candidate.plan, candidate.units, settled
    )
    assert rerendered == candidate.readme


def test_the_reviewer_rejects_before_the_accounting_and_accepts_after() -> None:
    """The hosted shape end to end, and the control that the reviewer is not a rubber stamp: the
    same README is rejected for these units until they are accounted. (That accounting never
    covers a unit whose content is not printed is held by the negative controls above.)"""
    candidate = _candidate()
    original = "# Old\n\n## Quick Start\n\n### Main\n"

    def verdict(dispositions: dict[str, Any], readme: str) -> Any:
        return review_candidate(
            readme_text=readme,
            units=candidate.units["units"],
            facts=candidate.facts,
            dispositions=dispositions,
            original_readme=original,
        )

    before = verdict(candidate.dispositions, candidate.readme)
    assert before.verdict == "REJECT"
    assert {f.rule for f in before.findings} >= {"disposition_coverage"}

    settled, _ = account_unprinted_units(candidate)
    after = verdict(settled, candidate.readme)
    assert [f.message for f in after.findings if f.rule == "disposition_coverage"] == []
    assert not any("008.code_block" in f.message for f in after.findings)


@pytest.mark.parametrize(
    ("unit", "readme", "printed"),
    [
        (
            "### Convert a Lambert Material to PBR",
            "### Convert a Lambert Material to PBR\n",
            True,
        ),
        (
            "### Convert a Lambert Material to PBR",
            "### Convert a Lambert Material to PBR Material\n",
            False,
        ),
        ("## Quick Start", "## Quick Start\n", True),
        ("## Quick Start", "Quick Start\n", False),
    ],
)
def test_a_heading_is_printed_only_as_a_heading(
    unit: str, readme: str, printed: bool
) -> None:
    assert heading_printed(unit, readme) is printed
