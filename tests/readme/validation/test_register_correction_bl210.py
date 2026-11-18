"""BL-210: the correction BC-18 owes is applied before the seal, deterministically and completely.

Texts are the exact false claims of the 8 failing Lane R seals (``data/readme_findings.json``, read
from a temporary register so the real one is never touched): Cells C++ opening, 3D .NET capability
and Quick Start example, HTML Python capability, Words .NET dependencies line.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation import must_correct
from repo_presenter.readme.validation.must_correct import (
    REGISTER_CORRECTION_RULE,
    corrected_plan_examples,
    flat_squash,
    omission_holds,
    register_corrected,
    withheld_printed_text,
)

REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"
WHOLE = (
    "Aspose.Cells FOSS for Cpp reads and writes Excel files in the .xlsx format. It provides "
    "classes such as Workbook, Worksheet, and Cell. The product supports styling, and includes "
    "features like formula calculation, validation, and page setup. It requires CMake 3.16."
)
FORMULA = "includes features like formula calculation"
CAPABILITY = (
    "It writes values of multiple types via Cell.PutValue and sets formulas with Cell.SetFormula, "
    "throwing FormulaException for invalid formulas."
)
FORMULA_EXC = "throwing `FormulaException` for invalid formulas"
SAVE_LINE = 'scene.Save("output.obj", FileFormat.WavefrontOBJ);'


def _row(quote: str, description: str, repository: str = REPO) -> dict:
    return {
        "repository": repository, "description": description, "evidence": "x.cpp:1@abc",
        "route": "lane_r", "status": "OPEN", "first_seen_at": "2026-11-13", "quote": quote,
        "truth": "what the source says",
    }


@pytest.fixture
def register(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "findings.json"
    rows = [
        _row(FORMULA, "formula calculation"),
        _row(FORMULA_EXC, "FormulaException"),
        _row(SAVE_LINE, "scene.Save obj"),
    ]
    path.write_text(json.dumps({"schema_version": 1, "findings": rows}), encoding="utf-8")
    monkeypatch.setattr(must_correct, "DEFAULT_FINDINGS_PATH", path)
    return path


def _units(*units: dict) -> dict:
    return {"schema_version": 1, "units": list(units), "omitted": []}


def test_a_false_sentence_is_withheld_and_the_rest_kept(register: Path) -> None:
    unit = {"slot": "opening", "section": "opening", "text": WHOLE, "fact_ids": ["a"]}
    plan, units, records = register_corrected({}, _units(unit), REPO, register)
    text = units["units"][0]["text"]
    assert "formula calculation" not in text and "Workbook" in text and "CMake" in text
    assert records[0]["rule"] == REGISTER_CORRECTION_RULE and records[0]["action"] == "sentence_withheld"
    assert records[0]["findings"] and units["register_corrections"] == records


def test_a_capability_that_is_only_false_text_leaves_the_plan_and_later_ones_renumber(
    register: Path,
) -> None:
    plan = {"core_capabilities": [{"title": "One"}, {"title": "Two"}, {"title": "Three"}]}
    units = _units(
        {"slot": "capability:1", "section": "key_capabilities", "text": "True text here.", "fact_ids": []},
        {"slot": "capability:2", "section": "key_capabilities", "text": CAPABILITY.replace(
            "It writes values of multiple types via Cell.PutValue and sets formulas with "
            "Cell.SetFormula, ", ""), "fact_ids": []},
        {"slot": "capability:3", "section": "key_capabilities", "text": "Also true.", "fact_ids": []},
    )
    # capability 2 is exactly the false clause
    units["units"][1]["text"] = "throwing FormulaException for invalid formulas"
    new_plan, new_units, records = register_corrected(plan, units, REPO, register)
    assert [c["title"] for c in new_plan["core_capabilities"]] == ["One", "Three"]
    assert [u["slot"] for u in new_units["units"]] == ["capability:1", "capability:2"]
    assert new_units["units"][1]["text"] == "Also true."
    assert records[0]["action"] == "capability_dropped"


def test_an_api_hub_that_is_only_false_text_falls_back_to_the_fact_true_row(register: Path) -> None:
    unit = {"slot": "hub:public_symbol:x.y", "section": "api_reference",
            "text": "includes features like formula calculation", "fact_ids": []}
    _plan, units, records = register_corrected({}, _units(unit), REPO, register)
    assert units["units"] == [] and records[0]["action"] == "api_row_fallback"
    assert units["omitted"][0]["fact_id"] == "public_symbol:x.y"


def test_nothing_changes_when_no_row_is_printed_or_the_repository_has_none(register: Path) -> None:
    unit = {"slot": "opening", "section": "opening", "text": "A true sentence.", "fact_ids": []}
    plan, units, records = register_corrected({"a": 1}, _units(unit), REPO, register)
    assert records == [] and units == _units(unit) and plan == {"a": 1}
    other = {"slot": "opening", "section": "opening", "text": WHOLE, "fact_ids": []}
    _p, same, none = register_corrected({}, _units(other), "other/repo", register)
    assert none == [] and same["units"][0]["text"] == WHOLE


def test_a_row_quoting_the_whole_unit_is_withheld_through_the_other_rows(register: Path) -> None:
    # Cells C++: one row quotes the whole opening, another its third sentence. Withholding the
    # sentence changes the unit so the whole-paragraph quote is no longer printed either.
    rows = json.loads(register.read_text())
    rows["findings"].append(_row(WHOLE, "the whole opening"))
    register.write_text(json.dumps(rows), encoding="utf-8")
    unit = {"slot": "opening", "section": "opening", "text": WHOLE, "fact_ids": []}
    _p, units, records = register_corrected({}, _units(unit), REPO, register)
    assert units["units"][0]["text"] != WHOLE
    assert "formula calculation" not in units["units"][0]["text"]
    assert records[0]["action"] == "sentence_withheld"


def _example(example_id: str, code: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(example_id, "example", code, (Evidence("README.md", "example"),), polarity)


def test_a_refuted_quick_start_example_is_replaced_by_one_that_is_not(register: Path) -> None:
    facts = FactsDocument(
        REPO, "rev",
        (_example("example:001", f"var scene = new Scene();\n{SAVE_LINE}\n"),
         _example("example:002", "var ok = 1;\n")),
    )
    plan = {"quick_start_example_id": "example:001", "second_quick_start_example_id": None,
            "additional_example_ids": ["example:002"]}
    units = _units(
        {"slot": "lead_in", "section": "quick_start", "text": "Saves a scene.", "fact_ids": ["example:001"]},
        {"slot": "workflow:example:002", "section": "additional_examples",
         "text": "Shows a value.", "fact_ids": ["example:002"]},
    )
    new_plan, new_units = corrected_plan_examples(plan, units, facts)
    assert new_plan["quick_start_example_id"] == "example:002"
    assert new_plan["additional_example_ids"] == []
    assert [u["slot"] for u in new_units["units"]] == ["lead_in"]
    assert new_units["units"][0]["text"] == "Shows a value."
    assert "example:002" in new_units["units"][0]["fact_ids"]
    assert new_units["register_corrections"][0]["action"] == "example_replaced"


def test_the_sentence_matcher_sees_through_links_the_renderer_flattens() -> None:
    text = "It knows far more (see [the story](#the-story) below). Other formats may come."
    assert flat_squash(text).startswith("It knows far more (see the story below)")
    quote = "knows far more (see the story below)"
    assert not omission_holds("inherited_unit:013.paragraph", f"- {quote}", [quote])
    assert omission_holds("inherited_unit:013.paragraph", text, [quote])


def test_withheld_printed_text_drops_a_fact_derived_line_but_never_a_table_row(
    register: Path,
) -> None:
    rows = json.loads(register.read_text())
    rows["findings"].append(_row("No required third-party package dependencies; in `x.csproj`, none is declared.", "deps"))
    rows["findings"].append(_row("| `Util` | Provides methods for signing. |", "row"))
    register.write_text(json.dumps(rows), encoding="utf-8")
    readme = (
        "## Dependencies\n\n### Required Package Dependencies\n\n"
        "No required third-party package dependencies; in `x.csproj`, none is declared.\n\n"
        "## API\n\n| Name | Description |\n|---|---|\n| `Util` | Provides methods for signing. |\n"
    )
    out = withheld_printed_text(readme, REPO, register)
    assert "No required third-party" not in out and "### Required Package Dependencies" not in out
    assert "| `Util` | Provides methods for signing. |" in out  # a table row is a unit's: kept
    assert withheld_printed_text("## A\n\ntrue\n", REPO, register) == "## A\n\ntrue\n"
