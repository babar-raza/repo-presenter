"""S9 accounting: a sub-heading S4 parked (DEFER_UNRESOLVED) under a heading a deterministic section
prints itself is owned by that section (aspose-psd-foss/Aspose.PSD-FOSS-for-Python: the
maintainers' ``## Dependencies`` held ``### Required``, ``### Native / System``, ``### Development``;
the render printed ``### Required Package Dependencies`` and live_readme_loss refused the three)."""

from __future__ import annotations

import copy
from typing import Any

from repo_presenter.readme.repair.accounting import account_unprinted_units
from repo_presenter.readme.review.independent_reviewer import live_readme_loss_rule
from tests.readme.repair import test_accounting as base

ORIGINAL = (
    "# Old\n\n## Dependencies\n\n### Required\n\n- **Python standard library** only.\n\n"
    "### Native / System\n\n- None.\n\n### Unrelated Notes\n\n- note\n"
)


def _facts() -> Any:
    facts = base._facts()
    extra = (
        base._fact("package_trait:stdlib_only.python", "package_trait", "imports only the stdlib",
                   "no third-party imports"),
        base._unit("007.heading", "## Dependencies"),
        base._unit("008.heading", "### Required"),
        base._unit("009.list", "- **Python standard library** only."),
        base._unit("010.heading", "### Native / System"),
        base._unit("011.list", "- None."),
    )
    return type(facts)(facts.repository, facts.source_revision, (*facts.facts, *extra))


def _plan() -> dict[str, Any]:
    plan = base._plan()
    for section in plan["sections"]:
        if section["section_id"] == "dependencies":
            section["include"] = True
    return plan


def _dispositions(**overrides: dict[str, Any]) -> dict[str, Any]:
    deferred = lambda unit, kind: base._entry(unit, "DEFER_UNRESOLVED", None, [])  # noqa: E731
    rows = base._by_unit(base._dispositions())
    rows.update(
        {
            "007.heading": deferred("007.heading", "heading"),
            "008.heading": deferred("008.heading", "heading"),
            "009.list": deferred("009.list", "list"),
            "010.heading": deferred("010.heading", "heading"),
            "011.list": deferred("011.list", "list"),
        }
    )
    rows.update(overrides)
    return {"dispositions": list(rows.values())}


def _candidate(dispositions: dict[str, Any]) -> Any:
    facts = _facts()
    # the deterministic Dependencies section needs a SUPPORTED dependency fact to render
    facts = type(facts)(
        facts.repository,
        facts.source_revision,
        (*facts.facts, base._fact("dependency:none", "dependency", "none", "the manifest declares none")),
    )
    return base._candidate(dispositions, plan=_plan(), facts=facts)


def test_deferred_subheadings_of_a_rendered_dependencies_section_are_accounted_to_it() -> None:
    candidate = _candidate(_dispositions())
    assert "## Dependencies" in candidate.readme and "### Required Package Dependencies" in candidate.readme
    assert "### Native / System" not in candidate.readme
    before = {f.evidence for f in live_readme_loss_rule(ORIGINAL, candidate.readme, facts=candidate.facts,
                                                        dispositions=candidate.dispositions)}
    assert "heading 'Required'" in before and "heading 'Native / System'" in before
    settled, accounted = account_unprinted_units(candidate)
    rows = base._by_unit(settled)
    for unit in ("008.heading", "010.heading"):
        assert rows[unit]["disposition"] == "SUPERSEDE_REDUNDANT"
        assert rows[unit]["destination_section"] == "dependencies"
        assert set(rows[unit]["fact_ids"]) >= {"dependency:none"}
        assert rows[unit]["rationale"]
    assert {a.reason for a in accounted if a.unit_id.endswith(("008.heading", "010.heading"))} == {
        "deferred_subheading"
    }
    after = {f.evidence for f in live_readme_loss_rule(ORIGINAL, candidate.readme, facts=candidate.facts,
                                                       dispositions=settled)}
    assert "heading 'Required'" not in after and "heading 'Native / System'" not in after


def test_a_deferred_heading_under_a_section_the_llm_writes_is_left_alone() -> None:
    dispositions = _dispositions(
        **{"007.heading": base._entry("007.heading", "DEFER_UNRESOLVED", None, [])}
    )
    candidate = _candidate(dispositions)
    # same shape, but the parent is the maintainers' own "Project Layout": not a D section's title
    facts = candidate.facts
    layout = type(facts)(
        facts.repository,
        facts.source_revision,
        tuple(
            f if f.id != "inherited_unit:007.heading" else base._unit("007.heading", "## Project Layout")
            for f in facts.facts
        ),
    )
    other = base._candidate(copy.deepcopy(dispositions), plan=_plan(), facts=layout)
    settled, _ = account_unprinted_units(other)
    assert base._by_unit(settled)["008.heading"]["disposition"] == "DEFER_UNRESOLVED"


def test_nothing_is_accounted_without_a_fact_the_section_renders_from() -> None:
    facts = base._facts()
    facts = type(facts)(
        facts.repository,
        facts.source_revision,
        (*facts.facts, base._unit("007.heading", "## Dependencies"), base._unit("008.heading", "### Required")),
    )
    dispositions = _dispositions()
    dispositions["dispositions"] = [
        d for d in dispositions["dispositions"]
        if d["unit_id"].split(":")[1] in {"007.heading", "008.heading"}
        or d["unit_id"].split(":")[1] in {"001.heading", "002.heading", "003.heading", "004.list", "005.code_block", "006.heading"}
    ]
    candidate = base._candidate(dispositions, plan=_plan(), facts=facts)
    settled, _ = account_unprinted_units(candidate)
    assert base._by_unit(settled)["008.heading"]["disposition"] == "DEFER_UNRESOLVED"
