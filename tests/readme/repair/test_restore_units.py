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


def test_a_maintainers_api_table_is_restored_now_that_bc07_counts_only_the_renderers_tables() -> None:
    """The published README's class/member table is the R2 floor. It used to stay deferred because
    BC-07 counted every first-cell row; BC-07 now judges only the tables the renderer emits under
    "### Core API" / "#### Enumerations", so the table is kept (verbatim) and placed."""
    ids = ["inherited_unit:037.table"]
    new, changes = restore_lost_units(_ts_dispositions(), _ts_facts(), ids, TS_HOLDABLE, TS_HOLDABLE)
    assert [c["unit_id"] for c in changes] == ids
    # No fact backs the maintainers' table, so it is kept attributed, in the API Reference.
    assert new["dispositions"][1]["disposition"] == "PRESERVE_ATTRIBUTED"
    assert new["dispositions"][1]["destination_section"] == "api_reference"


def _type_table_facts() -> FactsDocument:
    table = "\n".join(
        (
            "| Class | Description |",
            "|---|---|",
            "| `Workbook` | The workbook. |",
            "| `Cell` | A cell. |",
            "| `Range` | A range. |",
            "| `BorderStyle` | Border styles. |",
        )
    )
    return FactsDocument(
        "r/x", "0" * 40,
        (
            _fact("inherited_unit:037.table", "inherited_unit", table, section="API Reference > Core API"),
            _fact("public_symbol:workbook", "public_symbol", "Workbook", symbol_kind="class"),
            _fact("public_symbol:cell", "public_symbol", "Cell", symbol_kind="class"),
            _fact("public_symbol:range", "public_symbol", "Range", symbol_kind="class"),
        ),
    )


def test_a_type_table_naming_something_the_public_surface_lacks_is_restored_without_that_row() -> None:
    """Cells Rust: the maintainers' type table lists `BorderStyle`, which lives in an internal
    module. The table is restored (R2 floor); the renderer prints it without the absent row, so
    BC-14 holds and BC-05 / disposition_coverage judge "printed" against the filtered table."""
    from repo_presenter.readme.repair.restore_units import table_contradicts_surface
    from repo_presenter.readme.validation.surface_claims import without_absent_type_rows

    facts = _type_table_facts()
    text = facts.by_kind("inherited_unit")[0].value
    assert table_contradicts_surface(text, facts)
    printed = without_absent_type_rows(text, facts)
    assert "BorderStyle" not in printed
    assert all(row in printed for row in ("`Workbook`", "`Cell`", "`Range`", "| Class | Description |"))
    new, changes = restore_lost_units(
        _ts_dispositions(), facts, ["inherited_unit:037.table"], TS_HOLDABLE, TS_HOLDABLE
    )
    assert [c["unit_id"] for c in changes] == ["inherited_unit:037.table"]
    assert new["dispositions"][1]["destination_section"] == "api_reference"


def test_a_member_table_is_not_a_type_table_and_is_restored() -> None:
    """3D .NET: `Detect`/`GetFormatByExtension`/... are members, not public types."""
    from repo_presenter.readme.repair.restore_units import table_contradicts_surface

    table = "\n".join(
        (
            "| Method | Description |",
            "|---|---|",
            "| `Detect` | Detects. |",
            "| `GetFormatByExtension` | Maps. |",
            "| `WavefrontOBJ` | OBJ. |",
        )
    )
    facts = FactsDocument(
        "r/x", "0" * 40,
        (
            _fact("inherited_unit:050.table", "inherited_unit", table, section="API Reference"),
            _fact("public_symbol:scene", "public_symbol", "Scene", symbol_kind="class"),
        ),
    )
    assert not table_contradicts_surface(table, facts)


def test_a_unit_holding_raw_html_bc06_forbids_is_not_restored() -> None:
    """HTML Python: restoring the maintainers' units put `<base`, `<embed`, `<iframe`, `<meta`
    outside a fence into the README (BC-06) -- a trade of BC-17 for BC-06, so such a unit stays."""
    dispositions = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:041.paragraph", "disposition": "DEFER_UNRESOLVED",
                "destination_section": None, "fact_ids": ["link_target:019"], "rationale": "x",
            },
        ]
    }
    facts = FactsDocument(
        "r/x", "0" * 40,
        (
            _fact(
                "inherited_unit:041.paragraph", "inherited_unit",
                'See the demo <iframe src="https://example.org/embed"></iframe> for details.',
                section="Demo",
            ),
            _fact("link_target:019", "link_target", "x"),
        ),
    )
    new, changes = restore_lost_units(
        dispositions, facts, ["inherited_unit:041.paragraph"], HOLDABLE, INCLUDED
    )
    assert changes == []


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


def test_an_item_still_lost_after_its_carrier_was_restored_escalates_to_every_other_holder() -> None:
    """Cells Rust, verbatim shape from recertify after the first restore pass: the published README
    prints `samples/README.md` in units 028, 046, 072, 077 and 079 (BC-17 counts per holding unit),
    one carrier (028) was restored and the link is STILL named lost, so the carrier did not clear it.
    The first pass takes one carrier; the next pass takes the four remaining holders."""
    texts = {"028": 300, "046": 900, "072": 120, "077": 700, "079": 400}
    facts = FactsDocument(
        "r/x", "0" * 40,
        tuple(_fact(f"inherited_unit:{n}.paragraph", "inherited_unit", "x" * size) for n, size in texts.items()),
    )
    details = [_holds(f"inherited_unit:{n}.paragraph", "links", "samples/README.md") for n in texts]
    first = choose_units(details, facts)
    assert first == ["inherited_unit:072.paragraph"]  # shortest holder, one carrier only
    second = choose_units(details, facts, already=first)
    assert second == [f"inherited_unit:{n}.paragraph" for n in ("028", "046", "077", "079")]
    # once every holder is restored nothing is left to choose
    assert choose_units(details, facts, already=first + second) == []


def test_escalation_leaves_an_item_whose_holders_were_never_restored_to_the_one_carrier_rule() -> None:
    facts = FactsDocument(
        "r/x", "0" * 40,
        (
            _fact("inherited_unit:010.list", "inherited_unit", "x" * 400),
            _fact("inherited_unit:031.table", "inherited_unit", "x" * 900),
            _fact("inherited_unit:042.list", "inherited_unit", "x" * 120),
        ),
    )
    details = [
        _holds("inherited_unit:010.list", "api_identifiers", "toCsv()"),
        _holds("inherited_unit:031.table", "api_identifiers", "toCsv()"),
        _holds("inherited_unit:042.list", "api_identifiers", "load()"),
    ]
    # an unrelated restored unit (not a holder of either item) changes nothing about the rule
    assert choose_units(details, facts, already=["inherited_unit:999.list"]) == [
        "inherited_unit:042.list", "inherited_unit:010.list",
    ]


def test_a_kept_paragraph_is_never_homed_in_api_reference_where_nothing_renders_it() -> None:
    """Cells Cpp: 'BC-05: inherited_unit:041.paragraph was placed in api_reference but the candidate
    does not render it there' -- api_reference prints the verified Core API table, not prose."""
    facts = _facts()
    dispositions = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:019.paragraph", "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "api_reference", "fact_ids": ["link_target:019"],
                "rationale": "x",
            }
        ]
    }
    new, changes = restore_lost_units(
        dispositions, facts, ["inherited_unit:019.paragraph"],
        ("api_reference", "quick_start", "development_testing"),
        ("api_reference", "quick_start", "development_testing"),
    )
    assert changes and new["dispositions"][0]["destination_section"] != "api_reference"


# --- BC-04: a superseded unit the section's authored units must cite -------------------------------

BC04_OWED = (
    "BC-04: scope_limitations: inherited_unit:007.paragraph: superseded into this section by "
    "reconciliation, so a unit must cite it and state its substance, or omitted must list it with a "
    "reason. Substance to carry: Do not use Aspose.PSD.FOSS when you need to:"
)
BC04_OUTSIDE = (
    "BC-04: api_reference: unit intro: cites facts outside this section's set: inherited_unit:034.paragraph"
)


def test_owed_citations_read_the_section_and_unit_and_skip_the_outside_set_shape() -> None:
    from repo_presenter.readme.repair.restore_units import owed_citations

    assert owed_citations([BC04_OWED, BC04_OUTSIDE, *DETAILS]) == [
        ("scope_limitations", "inherited_unit:007.paragraph")
    ]


def test_the_authored_unit_restating_the_substance_cites_the_owed_unit() -> None:
    from repo_presenter.readme.repair.restore_units import cite_owed_units

    facts = _facts(
        _fact(
            "inherited_unit:007.paragraph", "inherited_unit",
            "Do not use Aspose.PSD.FOSS when you need to render text layers or run Photoshop actions:",
            section="Aspose.PSD FOSS > Scope and Limitations",
        )
    )
    units = {
        "units": [
            {"section": "opening", "slot": "opening", "fact_ids": ["package:name"], "text": "A library."},
            {
                "section": "scope_limitations", "slot": "limit:1", "fact_ids": ["format:psd"],
                "text": "Aspose.PSD.FOSS does not render text layers or run Photoshop actions.",
            },
            {
                "section": "scope_limitations", "slot": "limit:2", "fact_ids": [],
                "text": "Nothing else applies.",
            },
        ]
    }
    new, changes = cite_owed_units(units, facts, [("scope_limitations", "inherited_unit:007.paragraph")])
    assert changes == [{"unit_id": "inherited_unit:007.paragraph", "cited_by": "scope_limitations/limit:1"}]
    assert new["units"][1]["fact_ids"] == ["format:psd", "inherited_unit:007.paragraph"]
    assert units["units"][1]["fact_ids"] == ["format:psd"]  # the input is not mutated


def test_no_unit_of_the_section_sharing_a_word_means_nothing_is_cited() -> None:
    from repo_presenter.readme.repair.restore_units import cite_owed_units

    facts = _facts(
        _fact("inherited_unit:007.paragraph", "inherited_unit", "Entirely different words here.")
    )
    units = {"units": [{"section": "scope_limitations", "slot": "a", "fact_ids": [], "text": "zzz qqq"}]}
    assert cite_owed_units(units, facts, [("scope_limitations", "inherited_unit:007.paragraph")])[1] == []


# --- BC-08: a rewritten unit whose kept command the render never printed (hosted PDF Go 025) -----

BC08 = (
    "BC-08: inherited_unit:010.list: VERIFIED_REWRITE keeps the command 'npm install x' but the "
    "candidate does not render it"
)


def test_a_bc08_unit_is_mandatory_only_when_the_caller_names_bc08() -> None:
    facts = _ts_facts()
    assert choose_units([BC08], facts) == []  # recertify's default: BC-08 is not a restore check
    assert choose_units([BC08], facts, mandatory_checks=("BC-05", "BC-08")) == [
        "inherited_unit:010.list"
    ]


def test_restoring_the_bc08_unit_returns_the_rewrite_to_verbatim_preserve() -> None:
    facts = _ts_facts()
    [unit] = choose_units([BC08], facts, mandatory_checks=("BC-05", "BC-08"))
    new, changes = restore_lost_units(_ts_dispositions(), facts, [unit], TS_HOLDABLE, TS_HOLDABLE)
    assert [c["unit_id"] for c in changes] == [unit]
    entry = next(e for e in new["dispositions"] if e["unit_id"] == unit)
    assert entry["disposition"] == "VERIFIED_PRESERVE"
    assert entry["destination_section"] == "key_capabilities"
