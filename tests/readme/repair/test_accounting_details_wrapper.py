"""S9 accounting for a kept ``<details>`` wrapper and for a heading kept outside an example
section over an example the README prints.

The shape is hosted run 42705822491 of Aspose.3D-FOSS-for-TypeScript: the inherited
``<details><summary>View Additional Examples</summary>`` opener was kept ``VERIFIED_PRESERVE`` into
``development_testing`` but never printed (the examples section prints its own wrapper), and the
first sub-example's heading was kept ``VERIFIED_PRESERVE`` into ``opening`` while its body moved to
``additional_examples`` as an UNRESOLVED example reprinted with a note. Each case has a negative
control, and the README bytes are proved unchanged by the accounting.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.repair.accounting import account_unprinted_units
from repo_presenter.readme.review.independent_reviewer import unprinted_kept_units
from repo_presenter.readme.validation.failures import Candidate
from tests.readme.repair.test_accounting import (
    ENTRY,
    REVISION,
    _by_unit,
    _entry,
    _unit,
)
from tests.readme.repair.test_accounting_examples import (
    _dispositions as _base_dispositions,
    _example,
    _example_facts,
    _example_plan,
    _example_units,
)

OPENER = "<details><summary>View Additional Examples</summary>"
CLOSER = "</details>"
UNRESOLVED_CODE = "```python\nunresolved_call(scene)\n```"


def _facts(opener: str = OPENER) -> FactsDocument:
    base = _example_facts()
    extra = (
        _example(4, "unresolved_call(scene)\n", "UNRESOLVED"),
        _unit("013.html_block", opener),
        _unit("014.heading", "### Load With Custom Options"),
        _unit("015.paragraph", "Lead-in of the custom options example."),
        _unit("016.code_block", UNRESOLVED_CODE),
        _unit("017.html_block", CLOSER),
    )
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


def _dispositions(**overrides: dict[str, Any] | None) -> dict[str, Any]:
    document = _base_dispositions()
    rows = {row["unit_id"]: row for row in document["dispositions"]}
    rows["inherited_unit:013.html_block"] = _entry(
        "013.html_block", "VERIFIED_PRESERVE", "development_testing", []
    )
    rows["inherited_unit:014.heading"] = _entry(
        "014.heading", "VERIFIED_PRESERVE", "opening", []
    )
    rows["inherited_unit:015.paragraph"] = _entry(
        "015.paragraph", "SUPERSEDE_REDUNDANT", "additional_examples", []
    )
    rows["inherited_unit:016.code_block"] = _entry(
        "016.code_block", "SUPERSEDE_REDUNDANT", "additional_examples", ["example:004"]
    )
    rows["inherited_unit:017.html_block"] = _entry(
        "017.html_block", "VERIFIED_PRESERVE", "development_testing", []
    )
    for unit, row in overrides.items():
        key = f"inherited_unit:{unit}"
        if row is None:
            rows.pop(key)
        else:
            rows[key] = row
    return {"dispositions": list(rows.values())}


def _plan() -> dict[str, Any]:
    plan = _example_plan()
    plan["additional_example_ids"] = ["example:002", "example:004"]
    return plan


def _candidate(
    dispositions: dict[str, Any] | None = None, *, opener: str = OPENER
) -> Candidate:
    facts = _facts(opener)
    plan = _plan()
    units = _example_units()
    dispositions = dispositions if dispositions is not None else _dispositions()
    readme = render_readme(ENTRY, facts, plan, units, dispositions)
    return Candidate(
        ENTRY, facts, plan, units, dispositions, readme, None, REVISION, None, (), []
    )


def _unprinted(candidate: Candidate) -> set[str]:
    return {
        unit.split(":")[1]
        for unit, _ in unprinted_kept_units(
            candidate.readme, facts=candidate.facts, dispositions=candidate.dispositions
        )
    }


def test_the_fixture_reproduces_the_hosted_shape() -> None:
    candidate = _candidate()
    assert "unresolved_call(scene)" in candidate.readme
    assert "### Load With Custom Options" not in candidate.readme
    assert {"013.html_block", "014.heading"} <= _unprinted(candidate)


def test_a_kept_details_wrapper_the_render_does_not_print_is_accounted() -> None:
    candidate = _candidate()
    settled, accounted = account_unprinted_units(candidate)
    row = _by_unit(settled)["013.html_block"]
    assert row["disposition"] == "SUPERSEDE_REDUNDANT"
    assert row["fact_ids"] == ["identity:repository"]
    # development_testing is not in the plan, so the renderer-owned collapsible section takes it.
    assert row["destination_section"] == "additional_examples"
    # The closing tag the renderer prints itself is printed, so it is not touched.
    assert _by_unit(settled)["017.html_block"]["disposition"] == "VERIFIED_PRESERVE"
    assert [a.reason for a in accounted if a.unit_id.endswith("013.html_block")] == [
        "owned_elsewhere"
    ]


def test_a_details_opener_with_another_summary_is_accounted_too() -> None:
    candidate = _candidate(opener="<details>\n<summary>Show more</summary>")
    settled, _ = account_unprinted_units(candidate)
    assert _by_unit(settled)["013.html_block"]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_an_html_block_that_is_not_a_details_wrapper_is_left_alone() -> None:
    """Negative control: only the wrapper tags the renderer owns are accounted."""
    candidate = _candidate(opener='<p align="center"><img src="logo.png"></p>')
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["013.html_block"]["disposition"] == "VERIFIED_PRESERVE"
    assert not any(a.unit_id.endswith("013.html_block") for a in accounted)


def test_a_details_opener_with_extra_content_is_left_alone() -> None:
    """Negative control: a wrapper that carries text of its own is content, not a bare wrapper."""
    candidate = _candidate(opener="<details>\n<summary>Notes</summary>\nSee below.")
    settled, _ = account_unprinted_units(candidate)
    assert _by_unit(settled)["013.html_block"]["disposition"] == "VERIFIED_PRESERVE"


def test_a_kept_heading_over_a_printed_unresolved_example_is_accounted() -> None:
    candidate = _candidate()
    settled, accounted = account_unprinted_units(candidate)
    row = _by_unit(settled)["014.heading"]
    assert row["disposition"] == "SUPERSEDE_REDUNDANT"
    assert row["destination_section"] == "additional_examples"
    assert row["fact_ids"] == ["example:004"]
    assert [a.reason for a in accounted if a.unit_id.endswith("014.heading")] == [
        "owned_elsewhere"
    ]


def test_a_heading_over_an_unresolved_example_whose_code_is_not_printed_is_left_alone() -> (
    None
):
    """Negative control: the example is UNRESOLVED and its code is not in the README."""
    candidate = _candidate()
    candidate = dataclasses.replace(
        candidate, readme=candidate.readme.replace("unresolved_call", "other_call")
    )
    settled, accounted = account_unprinted_units(candidate)
    assert _by_unit(settled)["014.heading"]["disposition"] == "VERIFIED_PRESERVE"
    assert not any(a.unit_id.endswith("014.heading") for a in accounted)


def test_a_heading_over_an_example_destined_outside_an_example_section_is_left_alone() -> (
    None
):
    """Negative control: the code block's own destination is not an example section."""
    dispositions = _dispositions(
        **{
            "016.code_block": _entry(
                "016.code_block",
                "SUPERSEDE_REDUNDANT",
                "key_capabilities",
                ["example:004"],
            )
        }
    )
    settled, _ = account_unprinted_units(_candidate(dispositions))
    assert _by_unit(settled)["014.heading"]["disposition"] == "VERIFIED_PRESERVE"


def test_the_accounting_never_changes_what_renders() -> None:
    candidate = _candidate()
    settled, _ = account_unprinted_units(candidate)
    assert (
        render_readme(ENTRY, candidate.facts, candidate.plan, candidate.units, settled)
        == candidate.readme
    )
