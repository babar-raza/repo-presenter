"""BL-600: a planned capability that cites only facts that name the product states nothing the review can check.

Real shape (sealed Aspose.PSD FOSS for Java, plan capabilities 1 and 3 to 5): ``identity:family`` (and the package
name and version) are the only cited facts, although the facts hold ``CompressionMethod`` and ``ColorModes`` enum
members. 3 of 4 fresh independent audit samples faulted capabilities 3 to 5. Over the 30 sealed Lane R plans these
are 4 of 201 capabilities and no other seal has one (report-only run, 2026-11-21).
"""

from __future__ import annotations

from dataclasses import replace

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.composition.planning import (
    naming_only_capability,
    plan_checks,
    recover_naming_only_capabilities,
    recover_planning_output,
)
from tests.readme.composition.synthetic import make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan


def test_only_naming_facts_make_a_capability_naming_only() -> None:
    assert naming_only_capability({"title": "Compression support", "fact_ids": ["identity:family"]})
    assert naming_only_capability(
        {"title": "PSD/PSB file parsing", "fact_ids": ["identity:family", "package:name", "package:version"]}
    )
    assert naming_only_capability({"title": "x", "fact_ids": []})
    # Negative controls: a fact that states something is never naming-only.
    for fact_id in (
        "enum_member:org.aspose.psd.compressionmethod.rle", "public_symbol:org.aspose.psd.colormodes",
        "package:target_framework", "package:python_requires", "format:input.ps", "example:001",
        "dependency:skia-python", "install_command:maven", "build_test_asset:build-command",
    ):
        assert not naming_only_capability({"title": "x", "fact_ids": ["identity:family", fact_id]})


def _case():
    base = make_facts()
    facts = replace(base, facts=(
        *base.facts,
        Fact("enum_member:widget.mode.fast", "enum_member", "widget.Mode.Fast", (Evidence("x"),)),
    ))
    return facts, _dispositions()


def test_plan_checks_refuses_a_naming_only_capability_and_names_the_fix() -> None:
    facts, dispositions = _case()
    plan = _plan()
    plan["core_capabilities"][2] = {
        "title": "Work with the public API", "fact_ids": ["package:name"], "shared_fact_ids": [],
    }
    errors = plan_checks(plan, facts, dispositions=dispositions)
    assert any("core_capabilities 3" in e and "cites only facts that name the product" in e for e in errors)
    plan["core_capabilities"][2]["fact_ids"] = ["package:name", "enum_member:widget.mode.fast"]
    assert not any("cites only facts that name the product" in e for e in plan_checks(plan, facts, dispositions=dispositions))


def test_the_last_resort_drops_it_only_when_the_plan_keeps_its_minimum() -> None:
    def plan_of(weak: set[int], total: int) -> dict:
        titles = [f"Capability {i}" for i in range(1, total + 1)]
        return {
            "core_capabilities": [
                {"title": t, "fact_ids": ["identity:family"] if i in weak else [f"enum_member:e{i}"],
                 "shared_fact_ids": []}
                for i, t in enumerate(titles, 1)
            ],
            "at_a_glance": {"capability_titles": list(titles)},
        }

    kept = recover_naming_only_capabilities(plan_of({2}, 5))
    assert kept is not None
    assert [c["title"] for c in kept["core_capabilities"]] == ["Capability 1", "Capability 3", "Capability 4", "Capability 5"]
    assert "Capability 2" not in kept["at_a_glance"]["capability_titles"]
    assert kept["_recovery_notes"][-1] == {
        "fallback": "naming_only_capability_dropped", "rule": "BL-600", "path": "$.core_capabilities",
        "dropped": ["Capability 2"],
    }
    assert recover_planning_output(plan_of({2}, 5), make_facts())["core_capabilities"].__len__() == 4
    # PSD Java shape: 4 of 6 capabilities are naming-only and 2 < the minimum 3 would remain: nothing is dropped
    # (the plan stays rejected so the planner is asked again), and a plan with none is untouched.
    assert recover_naming_only_capabilities(plan_of({1, 3, 4, 5}, 6)) is None
    assert recover_naming_only_capabilities(plan_of(set(), 6)) is None
