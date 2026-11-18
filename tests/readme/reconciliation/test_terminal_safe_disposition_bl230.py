"""BL-230: terminal-safe disposition and placement (R46: universal, robust).

The messages and units are the ones in the failure records: Cells .NET ended BC-05 section fit on
three resource links printed under Scope and Limitations
(``[Local documentation landing page](documentation/_site/index.html)``,
``[Samples overview](samples/README.md)``, ``[Contributor and agent instructions](agents.md)``),
none of them a link fact Documentation and Resources could print, so the existing fold
(``link_list_targets``) left the list in Scope. The kept text now moves to the nearest section that
prints a list, recorded, never dropped (R14).
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.destinations import prints_unit
from repo_presenter.readme.reconciliation.dispositions import (
    RESOURCE_KEPT_RATIONALE,
    fit_sealed_sections,
)
from repo_presenter.readme.repair.restore_units import fit_misfiled_units, restore_lost_units

_REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET"
LINKS = (
    "- [Local documentation landing page](documentation/_site/index.html)\n"
    "- [Samples overview](samples/README.md)\n"
    "- [Contributor and agent instructions](agents.md)"
)
UNIT = "inherited_unit:031.list"


_BUILD = Fact("build_test_asset:ci", "build_test_asset", "ci.yml", (Evidence("ci.yml"),))


def _facts(extra: tuple[Fact, ...] = (_BUILD,)) -> FactsDocument:
    return FactsDocument(
        _REPO,
        "0" * 40,
        (
            Fact("identity:repository", "identity", _REPO, (Evidence("x"),)),
            Fact(
                UNIT,
                "inherited_unit",
                LINKS,
                (Evidence("README.md", None),),
                attributes={"section": "Aspose.Cells FOSS for .NET > Documentation"},
            ),
            *extra,
        ),
    )


def _dispositions(destination: str = "scope_limitations") -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": UNIT,
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": destination,
                "fact_ids": [],
                "rationale": "Kept.",
            }
        ]
    }


def test_prints_unit_is_one_source_of_truth() -> None:
    assert not prints_unit("documentation_resources", "list")
    assert prints_unit("api_reference", "table") and not prints_unit("api_reference", "list")
    assert prints_unit("scope_limitations", "list") and not prints_unit("scope_limitations", "code_block")
    assert prints_unit("development_testing", "list")


def test_links_no_link_fact_carries_are_kept_as_written_outside_scope() -> None:
    output = _dispositions()
    fit_sealed_sections(output, _facts())
    entry = output["dispositions"][0]
    assert entry["disposition"] == "VERIFIED_PRESERVE"  # kept, not dropped
    assert entry["destination_section"] == "development_testing"
    assert entry["rationale"].startswith(
        RESOURCE_KEPT_RATIONALE.format(home="development_testing", old="scope_limitations")
    )
    assert len(entry["rationale"]) <= 160


def test_a_mixed_list_with_one_link_led_item_is_also_re_homed() -> None:
    text = "- Does not support macros.\n- [Samples overview](samples/README.md)"
    facts = _facts()
    facts = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(
            Fact(f.id, f.kind, text, f.evidence, attributes=f.attributes)
            if f.id == UNIT
            else f
            for f in facts.facts
        ),
    )
    output = _dispositions()
    fit_sealed_sections(output, facts)
    assert output["dispositions"][0]["destination_section"] == "development_testing"


def test_a_plain_limitations_list_stays_in_scope() -> None:
    facts = _facts()
    text = "- Does not support macros.\n- Does not support charts."
    facts = FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(
            Fact(f.id, f.kind, text, f.evidence, attributes=f.attributes) if f.id == UNIT else f
            for f in facts.facts
        ),
    )
    output = _dispositions()
    fit_sealed_sections(output, facts)
    assert output["dispositions"][0]["destination_section"] == "scope_limitations"


def test_a_list_already_in_a_printable_section_is_untouched() -> None:
    output = _dispositions("development_testing")
    fit_sealed_sections(output, _facts())
    assert output["dispositions"][0]["destination_section"] == "development_testing"


def test_fit_misfiled_units_records_the_move_and_respects_the_plan() -> None:
    moved, changes = fit_misfiled_units(_dispositions(), _facts(), ["development_testing"])
    assert changes == [
        {
            "unit_id": UNIT,
            "was": "VERIFIED_PRESERVE -> scope_limitations",
            "now": "VERIFIED_PRESERVE -> development_testing",
        }
    ]
    assert moved["dispositions"][0]["destination_section"] == "development_testing"
    # A plan that omits the section it would move to leaves the unit exactly where it was.
    same, none = fit_misfiled_units(_dispositions(), _facts(), ["scope_limitations"])
    assert none == []
    assert same["dispositions"][0]["destination_section"] == "scope_limitations"


def test_restore_moves_a_kept_unit_out_of_a_section_that_cannot_print_its_kind() -> None:
    code = "inherited_unit:040.code_block"
    facts = FactsDocument(
        _REPO,
        "0" * 40,
        (
            Fact(
                code,
                "inherited_unit",
                "```bash\nmake build\n```",
                (Evidence("README.md", None),),
                attributes={"section": "Aspose.Cells FOSS for .NET > Build"},
            ),
        ),
    )
    dispositions = {
        "dispositions": [
            {
                "unit_id": code,
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "key_capabilities",
                "fact_ids": [],
            }
        ]
    }
    holdable = ("key_capabilities", "development_testing")
    output, changes = restore_lost_units(dispositions, facts, [code], holdable)
    assert changes and output["dispositions"][0]["destination_section"] == "development_testing"
    assert output["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_with_no_section_that_prints_a_list_the_unit_is_left_for_the_checks() -> None:
    """No build or example fact: Development and Testing is not in the document, so there is no
    placeable section and the fold changes nothing (it never drops the text)."""
    output = _dispositions()
    fit_sealed_sections(output, _facts(()))
    assert output["dispositions"][0]["destination_section"] == "scope_limitations"
