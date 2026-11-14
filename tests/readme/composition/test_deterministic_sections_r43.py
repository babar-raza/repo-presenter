"""R43(2) (owner, 2026-11-14; BL-102): Development and Testing, Documentation and Resources and Scope
and Limitations are produced from facts plus kept maintainer text, never model prose; the model
writes only the opening and the key-capability sentences, which carry no number, count, file or key
name."""

from __future__ import annotations

from dataclasses import replace

from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.readme.composition.authoring import (
    AUTHORED_SECTIONS,
    SectionTask,
    authoring_tasks,
    unit_checks,
    value_tokens,
)
from repo_presenter.readme.composition.components.shell import DETERMINISTIC_SECTIONS
from repo_presenter.readme.composition.planning import plan_checks
from repo_presenter.readme.composition.renderer import (
    RenderContext,
    link_target_description,
    render_readme,
    scope_fact_bullets,
)
from tests.readme.composition.synthetic import make_entry, make_facts
from tests.readme.composition.test_pipeline import _dispositions, _plan, _units

NAME = "Aspose.Widget FOSS for Python"


def _section(readme: str, heading: str) -> str:
    body = readme.split(f"## {heading}\n", 1)[1]
    return body.split("\n## ", 1)[0]


def _symbol(value: str, kind: str) -> Fact:
    return Fact(
        f"public_symbol:{value.lower()}", "public_symbol", value,
        (Evidence("aspose_widget_foss/widget.py", f"line 1; {kind}; public"),),
        attributes={"symbol_kind": kind},
    )


def _stub(member: str, exception: str = "NotImplementedError") -> Fact:
    return Fact(
        f"implementation:throws.{member.lower()}",
        "implementation",
        f"{member} raises {exception}",
        (Evidence("aspose_widget_foss/widget.py", "line 9; raise statement in the member's own body"),),
        attributes={"aspect": "throws", "condition": "always", "exception": exception, "member": member},
    )


def test_the_three_sections_are_never_authored() -> None:
    assert DETERMINISTIC_SECTIONS == {"development_testing", "documentation_resources", "scope_limitations"}
    assert not DETERMINISTIC_SECTIONS & set(AUTHORED_SECTIONS)
    assert {"opening", "key_capabilities"} <= set(AUTHORED_SECTIONS)
    tasks = authoring_tasks(make_entry(), make_facts(), {}, _dispositions(), _plan())
    assert not {task.section_id for task in tasks} & DETERMINISTIC_SECTIONS


def test_a_sealed_authored_scope_unit_is_not_printed_and_the_kept_limitation_is() -> None:
    plan = _plan()
    plan_checks(plan, make_facts(), dispositions=_dispositions())
    assert plan["material_limitations"] == []
    readme = render_readme(make_entry(), make_facts(), plan, _units(), _dispositions())
    scope = _section(readme, "Scope and Limitations")
    assert "Covers rendering only." not in readme  # the sealed authored "scope" unit
    assert "Only PNG output is currently supported." in scope  # the maintainers' kept text


def test_scope_prints_stub_facts_the_kept_text_does_not_name() -> None:
    base = make_facts()
    facts = replace(base, facts=(
        *base.facts,
        _symbol("aspose_widget_foss.Widget.render_pdf", "method"),
        _symbol("aspose_widget_foss.Widget.render_svg", "method"),
        _symbol("aspose_widget_foss.WidgetError", "class"),
        _stub("aspose_widget_foss.Widget.render_pdf"),
        _stub("aspose_widget_foss.Widget.render_svg"),
        _stub("aspose_widget_foss.Renderer.run"),
        Fact(
            "implementation:never_thrown.aspose_widget_foss.widgeterror", "implementation",
            "aspose_widget_foss.WidgetError is never thrown or constructed by the library's own code",
            (Evidence("aspose_widget_foss/errors.py", "line 3"),),
            attributes={"aspect": "never_thrown", "member": "aspose_widget_foss.WidgetError", "type": "WidgetError"},
        ),
    ))
    context = RenderContext(make_entry(), facts, _plan(), _units(), _dispositions())
    bullets = scope_fact_bullets(context, "The Renderer class is experimental.")
    assert bullets == [
        "`Widget`: `render_pdf` and `render_svg` raise NotImplementedError.",
        "`WidgetError` is declared but unused by the library's own code.",
    ]  # Renderer is named by the kept text, so it is not repeated
    plan = _plan()
    plan_checks(plan, facts, dispositions=_dispositions())
    readme = render_readme(make_entry(), facts, plan, _units(), _dispositions())
    assert "`Widget`: `render_pdf` and `render_svg` raise NotImplementedError." in _section(
        readme, "Scope and Limitations"
    )


def test_a_conditional_or_non_public_throw_is_not_a_stub() -> None:
    base = make_facts()
    guarded = replace(_stub("aspose_widget_foss.Widget.save"), attributes={
        "aspect": "throws", "condition": "conditional", "exception": "NotImplementedError",
        "member": "aspose_widget_foss.Widget.save",
    })
    hidden = replace(_stub("Internal.read"), attributes={
        "aspect": "throws", "exception": "NotImplementedError", "member": "Internal.read",
        "visibility": "internal",
    })
    facts = replace(base, facts=(*base.facts, guarded, hidden))
    context = RenderContext(make_entry(), facts, _plan(), _units(), _dispositions())
    assert scope_fact_bullets(context, "") == []


def test_link_descriptions_come_from_the_link_fact_when_no_maintainer_text_describes_it() -> None:
    def link(value: str) -> Fact:
        return Fact("link_target:009", "link_target", value, (Evidence("README.md"),))

    assert link_target_description(link("https://docs.aspose.org/widget/python/")).startswith(
        "Installation, walkthroughs, and feature guides"
    )
    assert link_target_description(link("https://kb.aspose.org/widget/python/")).startswith("Task-focused")
    assert link_target_description(link("examples/")) == "The `examples` directory in this repository."
    assert link_target_description(link("docs/releasing.md")) == "`docs/releasing.md` in this repository."
    assert link_target_description(link("https://pypi.org/project/x/")) == "On pypi.org."
    assert link_target_description(link("#additional-examples")) == "A section of this README."


def test_a_sealed_authored_link_sentence_is_replaced_by_the_fact_description() -> None:
    base = make_facts()
    facts = replace(base, facts=(
        *base.facts,
        Fact("link_target:009", "link_target", "https://kb.aspose.org/widget/python/", (Evidence("README.md"),)),
    ))
    plan = {**_plan(), "links": [{"link_fact_id": "link_target:009", "section_id": "documentation_resources"}]}
    units = _units()
    units["units"].append({
        "section": "documentation_resources", "slot": "link:link_target:009",
        "text": "Over 40 how-to articles cover the library.", "fact_ids": ["link_target:009"],
    })
    plan_checks(plan, facts, dispositions=_dispositions())
    readme = render_readme(make_entry(), facts, plan, units, _dispositions())
    docs = _section(readme, "Documentation & Resources")
    assert "Over 40 how-to articles" not in readme
    assert "— Task-focused how-to articles and answers to common questions." in docs


def test_development_and_testing_prints_no_authored_summary() -> None:
    base = make_facts()
    facts = replace(base, facts=(
        *base.facts,
        Fact("build_test_asset:examples", "build_test_asset", "examples/",
             (Evidence("examples/", "3 files; example programs"),)),
    ))
    units = _units()
    units["units"].append({
        "section": "development_testing", "slot": "summary",
        "text": "Run the 12 examples with python 3.10.", "fact_ids": [],
    })
    plan = _plan()
    plan_checks(plan, facts, dispositions=_dispositions())
    readme = render_readme(make_entry(), facts, plan, units, _dispositions())
    assert "Run the 12 examples" not in readme
    if "## Development and Testing" in readme:
        assert "Example programs live under `examples/`." in _section(readme, "Development and Testing")


def test_value_tokens_finds_numbers_counts_files_and_keys_but_not_the_product_name() -> None:
    assert value_tokens(f"{NAME} reads and writes workbooks.", NAME) == []
    assert value_tokens("Aspose.3D FOSS for .NET loads scenes.", "Aspose.3D FOSS for .NET") == []
    assert value_tokens("It supports 17 formats and Python 3.10.", NAME) == ["17", "3.10"]
    assert value_tokens("It covers three formats.", NAME) == ["three"]
    assert value_tokens("Settings live in pyproject.toml under examples/.", NAME) == [
        "pyproject.toml", "examples/",
    ]
    assert value_tokens("The python_requires floor applies.", NAME) == ["python_requires"]
    # format extensions, identifiers with digits and encodings are not values
    assert value_tokens("It reads `.xlsx` and UTF-8 text through `Vector3` and Base64.", NAME) == []


def test_unit_checks_reject_a_value_in_an_opening_or_capability_unit_only() -> None:
    facts = make_facts()
    for section, slot in (("opening", "opening"), ("key_capabilities", "capability:1")):
        task = SectionTask(section, {}, frozenset({"package:name"}), (slot,))
        output = {"units": [{"section": section, "slot": slot, "text": "It renders 12 widget kinds.",
                             "fact_ids": ["package:name"]}]}
        errors = unit_checks(output, task, facts, NAME)
        assert any("spells '12'" in error for error in errors), errors
        clean = {"units": [{"section": section, "slot": slot, "text": "It renders widgets.",
                            "fact_ids": ["package:name"]}]}
        assert not any("spells" in error for error in unit_checks(clean, task, facts, NAME))
    task = SectionTask("quick_start", {}, frozenset({"example:001"}), ("lead_in",))
    output = {"units": [{"section": "quick_start", "slot": "lead_in", "text": "It renders 12 widgets.",
                         "fact_ids": ["example:001"]}]}
    assert not any("spells" in error for error in unit_checks(output, task, facts, NAME))
