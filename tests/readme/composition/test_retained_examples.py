"""Unverified inherited examples are retained verbatim and marked; contradicted ones stay omitted.

Mission section 7: NOT_VERIFIED is not FALSE. An UNRESOLVED example (no toolchain, needs input) is
reprinted exactly as the project wrote it, beside a fixed renderer-owned note; a CONTRADICTED one is
omitted with the contradicting fact cited; a SUPPORTED one keeps the verified, unmarked path.
Offline: facts, plan, units and dispositions are built by hand, as in test_pipeline.py.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.lane_l import select_examples
from repo_presenter.readme.composition.planning import plan_checks
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.composition.retained_examples import (
    NOT_VERIFIED_NOTE,
    active_retained,
    retained_examples,
)
from repo_presenter.readme.reconciliation.retained_examples import (
    retain_unverified_examples,
)
from repo_presenter.readme.review.independent_reviewer import review_candidate
from repo_presenter.readme.validation.provenance import example_failures
from tests.readme.composition.synthetic import make_entry

CODE_A = "import widget\n\nw = widget.Widget()\nw.render()\n"
CODE_B = 'import widget\n\nwidget.load("a.png")\n'
CODE_C = "import widget\n\nw = widget.Widget()\nw.render()\nw.render()\n"
CODE_D = "import widget\n\nwidget.removed_call()\n"

README = f"""# Aspose Widget

## Quick Start

Create a widget and render it:

```python
{CODE_A.strip()}
```

## Additional Examples

More ways to render.

```python
{CODE_B.strip()}
```

<details><summary>More</summary>

### Render Twice

Render the widget two times:

```python
{CODE_C.strip()}
```

### Removed Call

```python
{CODE_D.strip()}
```

</details>
"""

UNITS = [
    ("010.heading", "## Quick Start"),
    ("011.paragraph", "Create a widget and render it:"),
    ("012.code_block", f"```python\n{CODE_A.strip()}\n```"),
    ("013.heading", "## Additional Examples"),
    ("014.paragraph", "More ways to render."),
    ("015.code_block", f"```python\n{CODE_B.strip()}\n```"),
    ("016.html_block", "<details><summary>More</summary>"),
    ("017.heading", "### Render Twice"),
    ("018.paragraph", "Render the widget two times:"),
    ("019.code_block", f"```python\n{CODE_C.strip()}\n```"),
    ("020.heading", "### Removed Call"),
    ("021.code_block", f"```python\n{CODE_D.strip()}\n```"),
    ("022.html_block", "</details>"),
]


def _example(number: int, code: str, unit: str, polarity: str) -> Fact:
    return Fact(
        f"example:{number:03d}",
        "example",
        code,
        (
            Evidence(
                "README.md", f"lines 1-2; python fence; unit inherited_unit:{unit}"
            ),
            Evidence("receipts.json", f"example {number}: stub"),
        ),
        polarity=polarity,  # type: ignore[arg-type]
    )


def _facts(
    polarities: tuple[str, str, str, str] = ("UNRESOLVED",) * 3 + ("CONTRADICTED",),
) -> FactsDocument:
    base = (
        Fact(
            "identity:repository",
            "identity",
            "org/Aspose.Widget-FOSS-for-Python",
            (Evidence("r"),),
        ),
        Fact("identity:ecosystem", "identity", "python", (Evidence("r"),)),
        Fact("package:name", "package", "aspose-widget-foss", (Evidence("setup.py"),)),
        Fact("license:spdx", "license", "MIT", (Evidence("LICENSE"),)),
        Fact("license:file", "license", "LICENSE", (Evidence("LICENSE"),)),
    )
    examples = (
        _example(1, CODE_A, "012.code_block", polarities[0]),
        _example(2, CODE_B, "015.code_block", polarities[1]),
        _example(3, CODE_C, "019.code_block", polarities[2]),
        _example(4, CODE_D, "021.code_block", polarities[3]),
    )
    units = tuple(
        Fact(
            f"inherited_unit:{key}",
            "inherited_unit",
            text,
            (Evidence("README.md", key),),
            attributes={"section": "Aspose Widget"},
        )
        for key, text in UNITS
    )
    return FactsDocument(
        "org/Aspose.Widget-FOSS-for-Python", "f" * 40, (*base, *examples, *units)
    )


def _raw_dispositions() -> dict[str, Any]:
    """What the model answers when it is told the example sections are not rendered."""
    entries = []
    for key, _text in UNITS:
        entry: dict[str, Any] = {
            "unit_id": f"inherited_unit:{key}",
            "disposition": "OMIT_UNSUPPORTED",
            "destination_section": None,
            "fact_ids": [],
            "rationale": "The example is unsupported because the section is not rendered.",
        }
        if key == "018.paragraph":
            entry["fact_ids"] = ["package:name"]
            entry["rationale"] = "The lead-in is contradicted by the package fact."
        if key == "021.code_block":
            entry["fact_ids"] = ["example:004"]
            entry["rationale"] = "The example failed: example:004 is CONTRADICTED."
        entries.append(entry)
    return {"dispositions": entries}


def _by_unit(dispositions: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        entry["unit_id"].split(":")[1]: entry for entry in dispositions["dispositions"]
    }


def _plan(facts: FactsDocument, dispositions: dict[str, Any]) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "core_capabilities": [
            {
                "title": "Render widgets",
                "fact_ids": ["package:name"],
                "shared_fact_ids": [],
            },
            {
                "title": "Install with pip",
                "fact_ids": ["package:name"],
                "shared_fact_ids": [],
            },
            {
                "title": "Work with the public API",
                "fact_ids": ["package:name"],
                "shared_fact_ids": [],
            },
        ],
        "quick_start_example_id": None,
        "second_quick_start_example_id": None,
        "additional_example_ids": [],
        "flagship_example_id": None,
        "api_hubs": [],
        "material_limitations": [],
        "links": [],
        "deviations": [],
        "at_a_glance": None,
    }
    plan_checks(plan, facts, dispositions=dispositions, ecosystem="python")
    return plan


def _render(facts: FactsDocument, dispositions: dict[str, Any]) -> str:
    return render_readme(
        make_entry(), facts, _plan(facts, dispositions), {"units": []}, dispositions
    )


def test_unverified_examples_are_retained_by_section_in_readme_order() -> None:
    retained = retained_examples(_facts())
    assert [(r.example_id, r.code_unit.split(":")[1], r.section) for r in retained] == [
        ("example:001", "012.code_block", "quick_start"),
        ("example:002", "015.code_block", "additional_examples"),
        ("example:003", "019.code_block", "additional_examples"),
    ]
    assert retained[0].lead_units == ("inherited_unit:011.paragraph",)
    assert retained[0].section_heading_unit == "inherited_unit:010.heading"
    assert retained[1].lead_units == ("inherited_unit:014.paragraph",)
    assert retained[2].lead_units == (
        "inherited_unit:017.heading",
        "inherited_unit:018.paragraph",
    )
    assert "inherited_unit:016.html_block" in retained[2].wrapper_units


def test_a_supported_example_sends_every_unverified_one_to_additional_examples() -> (
    None
):
    facts = _facts(("SUPPORTED", "UNRESOLVED", "UNRESOLVED", "CONTRADICTED"))
    assert [r.example_id for r in retained_examples(facts)] == [
        "example:002",
        "example:003",
    ]
    assert {r.section for r in retained_examples(facts)} == {"additional_examples"}


def test_an_example_whose_unit_reference_names_the_wrong_block_is_not_retained() -> (
    None
):
    """The example's own code must be the unit's code: a mislinked reference retains nothing."""
    facts = _facts()
    wrong = tuple(
        Fact(
            f.id,
            f.kind,
            f.value,
            (Evidence("README.md", "unit inherited_unit:001.code_block"),),
            polarity=f.polarity,
        )
        if f.kind == "example"
        else f
        for f in facts.facts
    )
    assert (
        retained_examples(FactsDocument(facts.repository, facts.source_revision, wrong))
        == []
    )


def test_the_stage_hands_unverified_examples_and_their_framing_to_their_section() -> (
    None
):
    facts = _facts()
    raw = _raw_dispositions()
    result = _by_unit(retain_unverified_examples(raw, facts))
    for key, section, example in (
        ("012.code_block", "quick_start", "example:001"),
        ("011.paragraph", "quick_start", "example:001"),
        ("010.heading", "quick_start", "example:001"),
        ("015.code_block", "additional_examples", "example:002"),
        ("013.heading", "additional_examples", "example:002"),
        ("017.heading", "additional_examples", "example:003"),
        ("019.code_block", "additional_examples", "example:003"),
        ("016.html_block", "additional_examples", "example:003"),
    ):
        assert result[key]["disposition"] == "SUPERSEDE_REDUNDANT", key
        assert result[key]["destination_section"] == section, key
        assert example in result[key]["fact_ids"], key
        assert result[key]["rationale"].startswith("Reprinted verbatim in "), key
    # The input is untouched.
    assert _by_unit(raw)["012.code_block"]["disposition"] == "OMIT_UNSUPPORTED"


def test_a_contradicted_example_stays_omitted_with_its_contradicting_fact_cited() -> (
    None
):
    result = _by_unit(retain_unverified_examples(_raw_dispositions(), _facts()))
    assert result["021.code_block"]["disposition"] == "OMIT_UNSUPPORTED"
    assert result["021.code_block"]["fact_ids"] == ["example:004"]
    assert result["020.heading"]["disposition"] == "OMIT_UNSUPPORTED"
    rendered = _render(
        _facts(), retain_unverified_examples(_raw_dispositions(), _facts())
    )
    assert "removed_call" not in rendered


def test_an_evidence_backed_omission_of_a_framing_unit_stands() -> None:
    result = _by_unit(retain_unverified_examples(_raw_dispositions(), _facts()))
    assert result["018.paragraph"]["disposition"] == "OMIT_UNSUPPORTED"
    assert result["018.paragraph"]["fact_ids"] == ["package:name"]


def test_a_framing_unit_with_a_contradicted_link_is_left_to_the_model() -> None:
    facts = _facts()
    doc = FactsDocument(
        facts.repository,
        facts.source_revision,
        (
            *(
                Fact(
                    f.id,
                    f.kind,
                    "See [the guide](https://example.invalid/gone) first:",
                    f.evidence,
                    attributes=f.attributes,
                )
                if f.id == "inherited_unit:011.paragraph"
                else f
                for f in facts.facts
            ),
            Fact(
                "link_target:gone",
                "link_target",
                "https://example.invalid/gone",
                (Evidence("README.md"),),
                polarity="CONTRADICTED",
            ),
        ),
    )
    result = _by_unit(retain_unverified_examples(_raw_dispositions(), doc))
    assert result["011.paragraph"]["disposition"] == "OMIT_UNSUPPORTED"
    assert result["012.code_block"]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_the_stage_is_idempotent() -> None:
    once = retain_unverified_examples(_raw_dispositions(), _facts())
    assert retain_unverified_examples(copy.deepcopy(once), _facts()) == once


def test_the_renderer_prints_each_unverified_example_verbatim_beside_the_fixed_note() -> (
    None
):
    facts = _facts()
    dispositions = retain_unverified_examples(_raw_dispositions(), facts)
    readme = _render(facts, dispositions)
    assert (
        "## Quick Start\n\nCreate a widget and render it:\n\n" + NOT_VERIFIED_NOTE
        in readme
    )
    for code in (CODE_A, CODE_B, CODE_C):
        assert f"{NOT_VERIFIED_NOTE}\n\n```python\n{code.strip()}\n```" in readme
    assert readme.count(NOT_VERIFIED_NOTE) == 3
    assert "## Additional Examples\n\nMore ways to render." in readme
    assert (
        "<details>\n<summary>View Additional Examples</summary>\n\n### Render Twice"
        in readme
    )
    assert (
        "Render the widget two times:" not in readme
    )  # its omission is evidence-backed
    assert readme.index("## Quick Start") < readme.index("## Additional Examples")
    assert "[Quick Start](#quick-start)" in readme
    assert "\n\n\n" not in readme
    assert readme == _render(facts, dispositions)


def test_the_note_is_fixed_wording_that_does_not_claim_the_example_works() -> None:
    assert NOT_VERIFIED_NOTE == (
        "> **Not verified:** this example is carried over unchanged from the project's existing "
        "README. It could not be compiled or run here."
    )
    lowered = NOT_VERIFIED_NOTE.lower()
    assert "works" not in lowered and "tested" not in lowered and "verified:" in lowered


def test_the_note_carries_no_banned_narration_phrase() -> None:
    """The qwen3-next/Rust hosted shape: BC-07 ("Structure" -- ``validation/structure.py``'s
    ``_narration_failures``) failed on 'internal narration \\'this revision\\'' every time this
    fixed, renderer-owned note was printed -- a defect of the note's own wording, not of the
    content it accompanies, real in every ecosystem that ever retains an unverified example. The
    falsifier: restoring the old "against this revision" wording must make this fail."""
    from repo_presenter.readme.correction.text_gate import narration

    assert narration(NOT_VERIFIED_NOTE) == []
    assert narration(
        "> **Not verified:** this example is carried over unchanged from the project's "
        "existing README. It could not be compiled or run against this revision."
    ) == ["this revision"]


def test_dispositions_that_never_went_through_the_stage_render_no_example() -> None:
    facts = _facts()
    raw = _raw_dispositions()
    assert active_retained(facts, raw) == []
    readme = _render(facts, raw)
    assert "## Quick Start" not in readme and NOT_VERIFIED_NOTE not in readme


def test_a_supported_example_is_printed_verified_and_unmarked() -> None:
    facts = _facts(("SUPPORTED", "UNRESOLVED", "CONTRADICTED", "CONTRADICTED"))
    dispositions = retain_unverified_examples(_raw_dispositions(), facts)
    plan = _plan(facts, dispositions)
    plan["quick_start_example_id"] = "example:001"
    plan_checks(plan, facts, dispositions=dispositions, ecosystem="python")
    units = {
        "units": [
            {
                "section": "quick_start",
                "slot": "lead_in",
                "text": "Render one:",
                "fact_ids": ["example:001"],
            }
        ]
    }
    readme = render_readme(make_entry(), facts, plan, units, dispositions)
    assert f"Render one:\n\n```python\n{CODE_A.rstrip()}\n```" in readme
    assert f"{NOT_VERIFIED_NOTE}\n\n```python\n{CODE_A.strip()}" not in readme
    assert f"{NOT_VERIFIED_NOTE}\n\n```python\n{CODE_B.strip()}\n```" in readme
    assert readme.count(NOT_VERIFIED_NOTE) == 1


def test_the_independent_reviewer_finds_no_loss_in_the_retained_example_sections() -> (
    None
):
    facts = _facts()
    dispositions = retain_unverified_examples(_raw_dispositions(), facts)
    readme = _render(facts, dispositions)
    before = review_candidate(
        readme_text=_render(facts, _raw_dispositions()),
        units=[],
        facts=facts,
        dispositions=_raw_dispositions(),
        original_readme=README,
    )
    after = review_candidate(
        readme_text=readme,
        units=[],
        facts=facts,
        dispositions=dispositions,
        original_readme=README,
    )
    lost_before = {f.message for f in before.findings if f.rule == "live_readme_loss"}
    lost_after = {f.message for f in after.findings if f.rule == "live_readme_loss"}
    for label in (
        "'Quick Start'",
        "'Additional Examples'",
        "'Render Twice'",
        "code block 'import widget'",
    ):
        assert any(label in m for m in lost_before), label
        assert not any(label in m for m in lost_after), label
    # The one fence still absent is the CONTRADICTED example, accounted for by its omission.
    assert not any("removed_call" in f.quote for f in after.findings)


def _candidate(facts: FactsDocument, dispositions: dict[str, Any], readme: str) -> Any:
    return SimpleNamespace(
        facts=facts,
        dispositions=dispositions,
        readme=readme,
        plan=_plan(facts, dispositions),
        entry=make_entry(),
    )


def test_bc03_accepts_marked_retained_examples_and_rejects_unmarked_ones() -> None:
    facts = _facts()
    dispositions = retain_unverified_examples(_raw_dispositions(), facts)
    readme = _render(facts, dispositions)
    assert example_failures(_candidate(facts, dispositions, readme)) == []
    unmarked = readme.replace(NOT_VERIFIED_NOTE + "\n\n", "", 1)
    failures = example_failures(_candidate(facts, dispositions, unmarked))
    assert [f.detail for f in failures] == [
        "example:001 is not verified but is printed without the not-verified note"
    ]


def test_bc03_still_rejects_an_example_fence_the_stage_did_not_hand_over() -> None:
    facts = _facts()
    dispositions = _raw_dispositions()
    failures = example_failures(_candidate(facts, dispositions, README))
    assert failures and all(
        "not a planned verified example" in f.detail for f in failures
    )


def test_select_examples_names_each_example_by_its_readme_block_not_its_ordinal() -> (
    None
):
    """The unit reference is how reconciliation and the renderer find an example's code block."""
    readme = (
        "# Title\n\nIntro.\n\n```bash\npip install x\n```\n\n## Quick Start\n\n"
        "```python\nimport widget\n```\n\nText.\n\n```python\nimport widget\n```\n\n"
        "```python\nimport widget as w\n```\n"
    )
    candidates = select_examples(readme, "README.md", "python")
    assert [(c.ordinal, c.unit_id) for c in candidates] == [
        (1, "inherited_unit:005.code_block"),
        (2, "inherited_unit:008.code_block"),
    ]
