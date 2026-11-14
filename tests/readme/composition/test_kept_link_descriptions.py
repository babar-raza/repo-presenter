"""P4 (2026-11-14): a resource-links list kept in Documentation and Resources is rendered from the
link facts and the maintainers' own item descriptions; those links get no authored slot. P3: the
Python floor prints as aspose.org prints it."""

from __future__ import annotations

from dataclasses import replace

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.composition.authoring import authoring_tasks
from repo_presenter.readme.composition.planning import plan_checks
from repo_presenter.readme.composition.renderer import render_readme
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan, _units

#: Aspose.3D-FOSS-for-.NET ``059.list`` (seal 52b0f00e), first two items verbatim.
RESOURCES = (
    "- **[Getting started guide](https://docs.aspose.org/3d/net/)** — installation, walkthroughs, "
    "and feature guides for this library.\n"
    "- **[How-to articles and FAQ](https://kb.aspose.org/3d/net/)** — task-focused how-tos and "
    "answers to common questions."
)


def _case():
    base = make_facts()
    facts = replace(base, facts=(
        *base.facts,
        Fact("link_target:020", "link_target", "https://docs.aspose.org/3d/net/", (Evidence("README.md"),)),
        Fact("link_target:021", "link_target", "https://kb.aspose.org/3d/net/", (Evidence("README.md"),)),
        Fact("inherited_unit:059.list", "inherited_unit", RESOURCES,
             (Evidence("README.md", "section 'Aspose Widget > Documentation & Resources'"),),
             attributes={"section": "Aspose Widget > Documentation & Resources"}),
        Fact("package:python_requires", "package", ">=3.10", (Evidence("pyproject.toml", "requires-python declared"),),
             attributes={"floor_declaration": "requires-python"}),
    ))
    dispositions = _dispositions()
    dispositions["dispositions"].append({
        "unit_id": "inherited_unit:059.list",
        "disposition": "VERIFIED_PRESERVE",
        "destination_section": "documentation_resources",
        "fact_ids": ["link_target:020", "link_target:021"],
        "rationale": "Kept in documentation_resources: a list of resource links.",
    })
    plan = _plan()
    assert plan_checks(plan, facts, dispositions=dispositions) == []
    return facts, dispositions, plan


def test_the_kept_list_s_links_are_planned_and_get_no_authored_slot() -> None:
    facts, dispositions, plan = _case()
    assert {link["link_fact_id"] for link in plan["links"] if link["section_id"] == "documentation_resources"} >= {
        "link_target:020", "link_target:021",
    }
    slots = [slot for task in authoring_tasks(make_entry(), facts, {}, dispositions, plan) for slot in task.slots]
    assert not any(slot.startswith("link:") for slot in slots)


def test_the_lines_print_the_maintainers_descriptions_and_the_python_floor() -> None:
    facts, dispositions, plan = _case()
    readme = render_readme(make_entry(), facts, plan, _units(), dispositions)
    lines = [line for line in readme.splitlines() if "(https://docs.aspose.org/3d/net/)" in line]
    assert len(lines) == 1
    assert lines[0].endswith("** — installation, walkthroughs, and feature guides for this library.")
    assert "** — task-focused how-tos and answers to common questions." in readme
    assert "Requires Python 3.10 or later." in readme
    assert "python_requires" not in readme and "declares `requires-python`" not in readme
