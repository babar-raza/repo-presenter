"""Zero-call restore of inherited units a sealed Lane R candidate lost (BC-05 / BC-17).

Real data: the two ``Examples`` units and the facts they cite are copied verbatim from
``aspose-cells-foss/Aspose.Cells-FOSS-for-.NET``'s sealed Lane R bundle (inherited_unit:019.paragraph
and :020.list, both left ``DEFER_UNRESOLVED`` with no destination although every fact they cite is
SUPPORTED), and the failure lines are recertify's own output for that seal.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.repair.restore_units import (
    choose_units,
    failing_unit_ids,
    restore_lost_units,
)

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


# --- Cells TypeScript: a rewritten list that lost identifiers, and a maintainers' API class table --------

_TS_SECTION = "Aspose.Cells FOSS for TypeScript"
_TS_LIST = (
    "- Load and save `.xlsx` workbooks - `Workbook.load(filePath)` reads an existing file\n"
    "  (auto-detecting HTML too), and `Workbook.save(filePath, options)` writes it back out.\n"
    "- Read and write cell values, formulas, and shared strings via `Cell.putValue()`/\n"
    "  `Cell.setFormula()`, with `Worksheet.getCell2()`/`getCell()` lookups by reference or\n"
    "  coordinate."
)
_TS_TABLE = (
    "| Class | Description |\n|---|---|\n| `AllConnectorShapeInfo` | Class in the Cells TYPESCRIPT API. |\n"
    "| `AutoFilter` | Class with 5 methods and 2 properties. |"
)


def _ts_facts() -> FactsDocument:
    return FactsDocument(
        "aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript", "0" * 40,
        (
            _fact("inherited_unit:010.list", "inherited_unit", _TS_LIST,
                  section=f"{_TS_SECTION} > Key Capabilities"),
            _fact("inherited_unit:037.table", "inherited_unit", _TS_TABLE,
                  section=f"{_TS_SECTION} > API Reference > Core API"),
            _fact("public_symbol:cell", "public_symbol", "Cell"),
            _fact("public_symbol:workbook", "public_symbol", "Workbook"),
        ),
    )


def _ts_dispositions() -> dict:
    return {
        "dispositions": [
            {"unit_id": "inherited_unit:010.list", "disposition": "VERIFIED_REWRITE",
             "destination_section": "key_capabilities",
             "fact_ids": ["public_symbol:cell", "public_symbol:workbook"], "rationale": "rewritten"},
            {"unit_id": "inherited_unit:037.table", "disposition": "DEFER_UNRESOLVED",
             "destination_section": None, "fact_ids": [],
             "rationale": "The table lists many public symbols not individually verified."},
        ]
    }


TS_HOLDABLE = ("key_capabilities", "api_reference", "quick_start")


def test_a_rewritten_unit_a_validator_still_names_returns_to_verbatim_preserve() -> None:
    new, changes = restore_lost_units(
        _ts_dispositions(), _ts_facts(), ["inherited_unit:010.list"], TS_HOLDABLE, TS_HOLDABLE
    )
    assert [c["unit_id"] for c in changes] == ["inherited_unit:010.list"]
    assert changes[0]["was"] == "VERIFIED_REWRITE -> key_capabilities"
    assert new["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_a_corrected_unit_is_never_reverted_to_its_original_text() -> None:
    corrected = _ts_dispositions()
    corrected["dispositions"][0]["disposition"] = "CORRECT_WITH_EVIDENCE"
    new, changes = restore_lost_units(
        corrected, _ts_facts(), ["inherited_unit:010.list"], TS_HOLDABLE, TS_HOLDABLE
    )
    assert changes == [] and new == corrected


def test_a_maintainers_api_table_is_deferred_until_asked_for() -> None:
    """Printing the maintainers' class table beside the rendered Core API table fails BC-07
    ("lists 139 rows for 31 verified public types", measured on this seal), so it is restored only
    when the caller asks for it after everything else has been tried."""
    ids = ["inherited_unit:037.table"]
    deferred, none = restore_lost_units(_ts_dispositions(), _ts_facts(), ids, TS_HOLDABLE, TS_HOLDABLE)
    assert none == [] and deferred["dispositions"][1]["disposition"] == "DEFER_UNRESOLVED"
    asked, changes = restore_lost_units(
        _ts_dispositions(), _ts_facts(), ids, TS_HOLDABLE, TS_HOLDABLE, include_api_tables=True
    )
    assert [c["now"] for c in changes] == ["PRESERVE_ATTRIBUTED -> api_reference"]
    assert asked["dispositions"][1]["destination_section"] == "api_reference"


def test_failing_unit_ids_reads_bc04_only_when_asked_to() -> None:
    details = [
        "BC-04: development_testing: inherited_unit:010.paragraph: superseded into this section by "
        "reconciliation, so a unit must cite it and state its substance",
        "BC-04: api_reference: unit intro: cites facts outside this section's set: "
        "inherited_unit:034.paragraph",
    ]
    assert failing_unit_ids(details) == []
    assert failing_unit_ids(details, checks=("BC-04",)) == [
        "inherited_unit:010.paragraph", "inherited_unit:034.paragraph",
    ]


def test_failing_unit_ids_reads_a_split_list_unit_id_like_rusts_061_001() -> None:
    """Cells Rust splits a long API list into inherited_unit:061.001.list, :061.002.list, ...; the
    first version of the id pattern read none of them, so the whole BC-05 set was silently skipped."""
    details = [
        "BC-05: inherited_unit:061.001.list is SUPERSEDE_REDUNDANT, but the README does not state 4 "
        "piece(s) of it (span 'get(a1_address) -> result<cell, cellserror>')",
        "BC-05: inherited_unit:063.003.list is SUPERSEDE_REDUNDANT, but the README does not state 1 "
        "piece(s) of it (span 'from_argb(a, r, g, b) -> color')",
    ]
    assert failing_unit_ids(details) == ["inherited_unit:061.001.list", "inherited_unit:063.003.list"]


def _holds(unit: str, category: str, item: str) -> str:
    return (
        f"BC-17: {unit} holds {category} '{item}', which the published README prints and this "
        "candidate loses (technical_content): keep it (VERIFIED_PRESERVE/VERIFIED_MOVE)"
    )


def test_choose_units_takes_one_carrier_per_lost_item_not_every_holder() -> None:
    """Cells TypeScript, verbatim from recertify: 'toCsv()' is held by units 010, 031, 037 and 042;
    'getCell()' only by 010; BC-05 makes 042 mandatory. Restoring all four would print the same
    identifiers four times and push the README over BC-07's visible-line budget."""
    facts = FactsDocument(
        "r/x", "0" * 40,
        (
            _fact("inherited_unit:010.list", "inherited_unit", "x" * 400),
            _fact("inherited_unit:031.table", "inherited_unit", "x" * 900),
            _fact("inherited_unit:037.table", "inherited_unit", "x" * 5000),
            _fact("inherited_unit:042.list", "inherited_unit", "x" * 120),
        ),
    )
    details = [
        "BC-05: inherited_unit:042.list is SUPERSEDE_REDUNDANT, but the README does not state 3 "
        "piece(s) of it (span 'tocsv()')",
        _holds("inherited_unit:010.list", "api_identifiers", "getCell()"),
        _holds("inherited_unit:010.list", "api_identifiers", "toCsv()"),
        _holds("inherited_unit:031.table", "api_identifiers", "toCsv()"),
        _holds("inherited_unit:037.table", "api_identifiers", "toCsv()"),
        _holds("inherited_unit:042.list", "api_identifiers", "toCsv()"),
        _holds("inherited_unit:037.table", "api_identifiers", "load()"),
        _holds("inherited_unit:010.list", "api_identifiers", "load()"),
    ]
    assert choose_units(details, facts) == ["inherited_unit:042.list", "inherited_unit:010.list"]
    # an item a unit already restored carries needs no further carrier
    only_getcell = [_holds("inherited_unit:010.list", "api_identifiers", "getCell()")]
    assert choose_units(only_getcell, facts, already=["inherited_unit:010.list"]) == []


def test_choose_units_reads_the_h2_category_whose_name_contains_a_digit() -> None:
    """Cells Go: 'inherited_unit:073.list holds h2 'Constraints'' - the category pattern first
    rejected the '2', so a whole lost section was never chosen for restore."""
    facts = FactsDocument("r/x", "0" * 40, (_fact("inherited_unit:073.list", "inherited_unit", "- a"),))
    details = [_holds("inherited_unit:073.list", "h2", "Constraints")]
    assert choose_units(details, facts) == ["inherited_unit:073.list"]
