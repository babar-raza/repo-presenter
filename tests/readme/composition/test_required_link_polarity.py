"""A link a VERIFIED_REWRITE cites as evidence is printed only when it is SUPPORTED.

Aspose.Words-FOSS-for-.NET (Lane R, hosted run 43394971759, deterministic on re-run): a
``VERIFIED_REWRITE`` disposition cited the CONTRADICTED ``link_target:020``. ``plan_checks``'s
links backstop (``_required_link_sections``) took every ``link_target:`` it cited without checking
polarity and appended it to ``plan.links`` after the plan's binding was checked; authoring then
built slot ``link:link_target:020`` whose fact_ids enum offered only that CONTRADICTED ID, and
section_authoring was rejected twice with "fact link_target:020 is CONTRADICTED, not SUPPORTED".
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import authoring_tasks, citable
from repo_presenter.readme.composition.planning import (
    _missing_links,
    _required_link_sections,
    plan_checks,
)
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan

GOOD = "link_target:019"
BAD = "link_target:020"


def _facts() -> FactsDocument:
    base = make_facts()
    extra = (
        Fact(
            GOOD,
            "link_target",
            "https://docs.aspose.org/widget/python/",
            (Evidence("README.md"),),
        ),
        Fact(
            BAD,
            "link_target",
            "https://example.invalid/stale",
            (Evidence("README.md"),),
            polarity="CONTRADICTED",
        ),
        Fact(
            "inherited_unit:030.paragraph",
            "inherited_unit",
            "See the [docs](https://docs.aspose.org/widget/python/).",
            (Evidence("README.md", "section 'Aspose Widget > Resources'"),),
            attributes={"section": "Aspose Widget > Resources"},
        ),
    )
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


def _rewrite_dispositions() -> dict:
    dispositions = _dispositions()
    dispositions["dispositions"].append(
        {
            "unit_id": "inherited_unit:030.paragraph",
            "disposition": "VERIFIED_REWRITE",
            "destination_section": "documentation_resources",
            "fact_ids": [GOOD, BAD],
            "rationale": "Rewritten against the verified docs link; the stale one is contradicted.",
        }
    )
    return dispositions


def test_the_backstop_requires_only_supported_link_targets() -> None:
    required = _required_link_sections(_facts(), _rewrite_dispositions())
    assert required == {GOOD: "documentation_resources"}
    missing = _missing_links({"links": []}, _facts(), _rewrite_dispositions())
    assert [m["link_fact_id"] for m in missing] == [GOOD]


def test_a_contradicted_link_a_rewrite_cites_never_reaches_plan_links() -> None:
    plan = _plan()
    errors = plan_checks(
        plan, _facts(), dispositions=_rewrite_dispositions(), ecosystem="python"
    )
    assert errors == []
    linked = {link["link_fact_id"] for link in plan["links"]}
    assert BAD not in linked
    assert GOOD in linked


def test_authoring_never_offers_a_non_supported_link_even_if_the_plan_carries_one() -> (
    None
):
    """Defence in depth: a plan that does carry the CONTRADICTED link gives it no slot and no
    slot's fact_ids enum offers it."""
    facts = _facts()
    plan = _plan()
    plan_checks(plan, facts, dispositions=_rewrite_dispositions(), ecosystem="python")
    plan["links"].append({"link_fact_id": BAD, "section_id": "documentation_resources"})
    tasks = authoring_tasks(make_entry(), facts, {}, _rewrite_dispositions(), plan)
    docs = [task for task in tasks if task.section_id == "documentation_resources"]
    assert docs, "documentation_resources is authored for the SUPPORTED link"
    for task in tasks:
        assert f"link:{BAD}" not in task.slots
        assert f"link:{BAD}" not in task.slot_facts
        assert BAD not in task.accepted_ids
        for slot in task.slots:
            assert BAD not in citable(task, slot)
    assert f"link:{GOOD}" in docs[0].slots
    assert GOOD in citable(docs[0], f"link:{GOOD}")
