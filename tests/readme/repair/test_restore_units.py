"""Zero-call restore of inherited units a sealed Lane R candidate lost (BC-05 / BC-17).

Real data: the two ``Examples`` units and the facts they cite are copied verbatim from
``aspose-cells-foss/Aspose.Cells-FOSS-for-.NET``'s sealed Lane R bundle (inherited_unit:019.paragraph
and :020.list, both left ``DEFER_UNRESOLVED`` with no destination although every fact they cite is
SUPPORTED), and the failure lines are recertify's own output for that seal.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.repair.restore_units import failing_unit_ids, restore_lost_units

DETAILS = [
    "BC-05: inherited_unit:035.paragraph is SUPERSEDE_REDUNDANT, but the README does not state 1 "
    "piece(s) of it (link 'license/license.txt'): a superseded unit's replacement must carry all of "
    "its substance",
    "BC-17: inherited_unit:019.paragraph holds h2 'Examples', which the published README prints and "
    "this candidate loses (section_coverage): keep it (VERIFIED_PRESERVE/VERIFIED_MOVE)",
    "BC-17: inherited_unit:020.list holds h2 'Examples', which the published README prints and this "
    "candidate loses (section_coverage): keep it (VERIFIED_PRESERVE/VERIFIED_MOVE)",
    "BC-17: inherited_unit:019.paragraph holds links 'samples/README.md', which the published README "
    "prints",
    "BC-14: the README states '14 public types'",
]


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", **attrs: str) -> Fact:
    return Fact(
        id=fact_id, kind=kind, value=value,  # type: ignore[arg-type]
        evidence=(Evidence("README.md", None),), polarity=polarity,  # type: ignore[arg-type]
        attributes=attrs or None,
    )


def _facts(*extra: Fact) -> FactsDocument:
    base = [
        _fact(
            "inherited_unit:019.paragraph", "inherited_unit",
            "Runnable samples live under [`samples/`](samples/README.md). Feature areas currently "
            "covered include:",
            section="Aspose.Cells FOSS for .NET > Examples",
        ),
        _fact(
            "inherited_unit:020.list", "inherited_unit",
            "- basic workbook and cell operations\n- load and repair behavior\n- styles",
            section="Aspose.Cells FOSS for .NET > Examples",
        ),
        _fact("link_target:019", "link_target", "samples/README.md"),
        _fact("build_test_asset:examples", "build_test_asset", "samples/"),
    ]
    return FactsDocument("aspose-cells-foss/Aspose.Cells-FOSS-for-.NET", "0" * 40, tuple(base + list(extra)))


def _dispositions(disposition: str = "DEFER_UNRESOLVED", facts: tuple[str, ...] = ("link_target:019", "build_test_asset:examples")):
    return {
        "dispositions": [
            {
                "unit_id": unit, "disposition": disposition, "destination_section": None,
                "fact_ids": list(facts), "rationale": "the paragraph about runnable samples",
            }
            for unit in ("inherited_unit:019.paragraph", "inherited_unit:020.list")
        ]
    }


HOLDABLE = ("opening", "key_capabilities", "quick_start", "additional_examples", "development_testing")
INCLUDED = ("opening", "key_capabilities", "quick_start", "development_testing")


def test_failing_unit_ids_reads_only_the_named_checks_in_first_seen_order() -> None:
    assert failing_unit_ids(DETAILS) == [
        "inherited_unit:035.paragraph", "inherited_unit:019.paragraph", "inherited_unit:020.list",
    ]
    assert failing_unit_ids(DETAILS, checks=("BC-14",)) == []  # BC-14 names no unit


def test_a_deferred_unit_with_only_supported_facts_is_kept_verbatim_in_a_section_the_plan_includes() -> None:
    new, changes = restore_lost_units(
        _dispositions(), _facts(), ["inherited_unit:019.paragraph", "inherited_unit:020.list"],
        HOLDABLE, INCLUDED,
    )
    assert [c["unit_id"] for c in changes] == ["inherited_unit:019.paragraph", "inherited_unit:020.list"]
    for entry in new["dispositions"]:
        assert entry["disposition"] == "VERIFIED_PRESERVE"
        assert entry["destination_section"] in INCLUDED  # never a section the plan omits


def test_a_unit_citing_an_unconfirmed_fact_is_kept_attributed_not_verified() -> None:
    facts = _facts(_fact("link_target:099", "link_target", "x", polarity="UNRESOLVED"))
    new, _ = restore_lost_units(
        _dispositions(facts=("link_target:099",)), facts, ["inherited_unit:019.paragraph"],
        HOLDABLE, INCLUDED,
    )
    entry = new["dispositions"][0]
    assert entry["disposition"] == "PRESERVE_ATTRIBUTED"


def test_a_unit_citing_a_contradicted_fact_is_left_alone() -> None:
    facts = _facts(_fact("link_target:099", "link_target", "x", polarity="CONTRADICTED"))
    original = _dispositions(facts=("link_target:099",))
    new, changes = restore_lost_units(original, facts, ["inherited_unit:019.paragraph"], HOLDABLE, INCLUDED)
    assert changes == [] and new == original


def test_a_unit_no_validator_named_is_never_touched_and_the_input_is_not_mutated() -> None:
    original = _dispositions()
    snapshot = repr(original)
    new, changes = restore_lost_units(original, _facts(), ["inherited_unit:020.list"], HOLDABLE, INCLUDED)
    assert [c["unit_id"] for c in changes] == ["inherited_unit:020.list"]
    assert new["dispositions"][0]["disposition"] == "DEFER_UNRESOLVED"  # 019 untouched
    assert repr(original) == snapshot


def test_no_holdable_included_section_means_no_change() -> None:
    new, changes = restore_lost_units(
        _dispositions(), _facts(), ["inherited_unit:019.paragraph"], HOLDABLE, ()
    )
    assert changes == []
    assert new["dispositions"][0]["disposition"] == "DEFER_UNRESOLVED"
