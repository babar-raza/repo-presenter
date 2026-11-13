"""A section_authoring task with no slot to fill offers no citation at all.

Aspose.Words-FOSS-for-.NET (Lane R, hosted run 43405227517, after the plan-side fix for run
43394971759): ``documentation_resources`` was still included, because reconciliation placed an
inherited unit there, but none of its planned links was SUPPORTED, so its authoring task had no
slots. ``authoring_schema`` then returned the manifest's own schema, whose ``fact_ids`` are
unpinned strings, and the model cited the CONTRADICTED ``link_target:020`` (the ``../../issues``
link a VERIFIED_REWRITE cited). ``unit_checks`` discards every unit of a slotless task, but binding
judges them first, so the job was rejected twice with "fact link_target:020 is CONTRADICTED, not
SUPPORTED". The rejection carried no schema error, so that reply was schema-valid: only a slotless
schema could have let it through.
"""

from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.llm.prompts import load_manifests
from repo_presenter.readme.composition.authoring import (
    authoring_schema,
    authoring_tasks,
)
from repo_presenter.readme.composition.output_bounds import bound_authoring_citations
from repo_presenter.readme.composition.planning import plan_checks
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan

REPO_ROOT = Path(__file__).resolve().parents[3]
SECTION_AUTHORING = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
BAD = "link_target:020"


def _facts() -> FactsDocument:
    base = make_facts()
    extra = (
        Fact(
            BAD,
            "link_target",
            "../../issues",
            (Evidence("README.md"),),
            polarity="CONTRADICTED",
        ),
        Fact(
            "inherited_unit:030.paragraph",
            "inherited_unit",
            "Docs live on the product site.",
            (Evidence("README.md", "section 'Aspose Widget > Resources'"),),
            attributes={"section": "Aspose Widget > Resources"},
        ),
        Fact(
            "inherited_unit:031.paragraph",
            "inherited_unit",
            "Please [open an issue](../../issues).",
            (Evidence("README.md", "section 'Aspose Widget > Contributing'"),),
            attributes={"section": "Aspose Widget > Contributing"},
        ),
    )
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


def _dispositions_placing_docs() -> dict:
    dispositions = _dispositions()
    dispositions["dispositions"] += [
        {
            "unit_id": "inherited_unit:030.paragraph",
            "disposition": "VERIFIED_PRESERVE",
            "destination_section": "documentation_resources",
            "fact_ids": [],
            "rationale": "Kept as written.",
        },
        {
            "unit_id": "inherited_unit:031.paragraph",
            "disposition": "VERIFIED_REWRITE",
            "destination_section": "documentation_resources",
            "fact_ids": [BAD],
            "rationale": "The relative issues link does not resolve; rewritten.",
        },
    ]
    return dispositions


def _docs_task():
    facts, dispositions, plan = _facts(), _dispositions_placing_docs(), _plan()
    assert plan_checks(plan, facts, dispositions=dispositions, ecosystem="python") == []
    tasks = authoring_tasks(make_entry(), facts, {}, dispositions, plan)
    docs = [task for task in tasks if task.section_id == "documentation_resources"]
    assert len(docs) == 1
    return docs[0]


def _unit(fact_ids: list[str]) -> dict:
    return {
        "units": [
            {
                "section": "documentation_resources",
                "slot": "resources",
                "text": "Report problems on the issue tracker.",
                "fact_ids": fact_ids,
            }
        ],
        "omitted": [],
    }


def test_the_words_net_shape_gives_documentation_resources_a_slotless_task() -> None:
    task = _docs_task()
    assert task.slots == ()
    assert BAD not in task.accepted_ids


def test_a_slotless_task_schema_rejects_a_unit_citing_a_contradicted_fact() -> None:
    task = _docs_task()
    schema = bound_authoring_citations(authoring_schema(SECTION_AUTHORING, task), task)
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(_unit([BAD])))
    # Not only the contradicted one: a slotless task's units are all discarded, so none is asked.
    assert list(validator.iter_errors(_unit(["package:name"])))
    assert not list(validator.iter_errors({"units": [], "omitted": []}))


def test_a_slotted_task_schema_is_unchanged_in_shape() -> None:
    facts, dispositions, plan = _facts(), _dispositions_placing_docs(), _plan()
    plan_checks(plan, facts, dispositions=dispositions, ecosystem="python")
    for task in authoring_tasks(make_entry(), facts, {}, dispositions, plan):
        if not task.slots:
            continue
        units = authoring_schema(SECTION_AUTHORING, task)["properties"]["units"]
        assert units["minItems"] == units["maxItems"] == len(task.slots)
        for item in units["prefixItems"]:
            enum = item["properties"]["fact_ids"]["items"].get("enum", [])
            assert BAD not in enum
