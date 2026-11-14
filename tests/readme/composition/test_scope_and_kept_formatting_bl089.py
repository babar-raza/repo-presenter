"""BL-089 (supervisor decision 2026-11-14, audit O8): the license-in-Scope check stays; the producer
side never states the license there, and kept maintainers' text gets formatting-only corrections.

Real data:
* hosted Lane R run 43516330798 (Aspose.Cells-FOSS-for-Python): BC-05 on the Scope bullet "This
  project is licensed under the MIT License and requires Python version 3.10 or later.", BC-07 on
  ``inherited_unit:023.heading`` "### Export a workbook" (title case) and on
  ``inherited_unit:008.paragraph`` "Install the package from PyPI:" (a colon with nothing after it);
* hosted Lane R run 43520974296 (Aspose.Cells-FOSS-for-TypeScript): BC-05 on "The package version
  is 1.0.0 and is named excel-cells, distributed under the MIT license.";
* the sealed Aspose.3D-FOSS-for-.NET candidate (seal 03b940a46f7b): "This project is licensed
  under the MIT `License`, as stated in the LICENSE file." as a Scope bullet.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import _OBJECTIVES
from repo_presenter.readme.composition.placement import colon_closed_form, placements
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.composition.retained_examples import kept_heading_form
from repo_presenter.readme.composition.source_topics import (
    is_license_statement,
    without_license_statement,
)
from repo_presenter.readme.review.independent_reviewer import unprinted_kept_units
from repo_presenter.readme.validation.text import section_texts
from tests.readme.repair.test_accounting import ENTRY, UNITS, _dispositions, _facts, _plan

CELLS_PYTHON = "This project is licensed under the MIT License and requires Python version 3.10 or later."
CELLS_TS = "The package version is 1.0.0 and is named excel-cells, distributed under the MIT license."
THREED_NET = "This project is licensed under the MIT `License`, as stated in the LICENSE file."


def test_a_license_clause_goes_and_the_rest_of_the_sentence_stays() -> None:
    assert without_license_statement(CELLS_PYTHON) == (
        "This project requires Python version 3.10 or later."
    )
    assert without_license_statement(CELLS_TS) == (
        "The package version is 1.0.0 and is named excel-cells."
    )
    # a sentence that states nothing but the license goes whole
    assert without_license_statement(THREED_NET) == ""
    # code spans the rest of the sentence carries are kept
    assert without_license_statement(
        "It reads the Open XML `.xlsx` format and is licensed under the MIT License."
    ) == "It reads the Open XML `.xlsx` format."


def test_negative_controls_text_without_a_license_statement_is_unchanged() -> None:
    for text in (
        "Formula results are cached, not recalculated.",
        "The `License` class only records a license key and applies nothing.",
        "Text export is one-way; there is no import path back into a `Workbook`.",
    ):
        assert without_license_statement(text) == text


def _scope_units(scope: str, *limitations: str) -> dict[str, Any]:
    units = [u for u in UNITS["units"] if u["section"] != "scope_limitations"]
    units.append(
        {"section": "scope_limitations", "slot": "scope", "text": scope, "fact_ids": ["package:name"]}
    )
    units.extend(
        {"section": "scope_limitations", "slot": f"limitation:{i}", "text": text,
         "fact_ids": ["package:name"]}
        for i, text in enumerate(limitations, start=1)
    )
    return {**UNITS, "units": units}


def test_scope_and_limitations_never_prints_a_license_statement() -> None:
    readme = render_readme(
        ENTRY, _facts(), _plan(),
        _scope_units("The package writes GLB only.", CELLS_PYTHON, THREED_NET, "It has no CLI."),
        _dispositions(),
    )
    scope = section_texts(readme)["scope_limitations"]
    assert not [line for line in scope.splitlines() if is_license_statement(line)]
    assert "- This project requires Python version 3.10 or later." in scope
    assert "- It has no CLI." in scope
    assert "as stated in the LICENSE file" not in scope


def test_negative_control_a_scope_without_a_license_renders_as_before() -> None:
    units = _scope_units("The package writes GLB only.", "It has no CLI.")
    readme = render_readme(ENTRY, _facts(), _plan(), units, _dispositions())
    assert "The package writes GLB only.\n\n- It has no CLI." in readme


def test_the_authoring_packet_forbids_the_license_in_scope() -> None:
    objective = _OBJECTIVES["scope_limitations"][0]
    assert "Never state the project's license" in objective


def test_a_kept_heading_prints_in_title_case() -> None:
    assert kept_heading_form("inherited_unit:023.heading", "### Export a workbook") == (
        "### Export a Workbook"
    )
    # negative controls: a title-case heading and a paragraph are unchanged
    assert kept_heading_form("inherited_unit:023.heading", "### Export a Workbook") == (
        "### Export a Workbook"
    )
    assert kept_heading_form("inherited_unit:024.paragraph", "### Export a workbook") == (
        "### Export a workbook"
    )


def test_a_dangling_colon_is_closed_and_only_that() -> None:
    assert colon_closed_form("Install the package from PyPI:") == "Install the package from PyPI."
    assert colon_closed_form("Install the package from PyPI.") == "Install the package from PyPI."
    assert colon_closed_form("Use `std::string`::") == "Use `std::string`::"


def _python_facts(*units: tuple[str, str]) -> FactsDocument:
    base = _facts()
    extra = tuple(
        Fact(uid, "inherited_unit", text, (Evidence("README.md", "lines 1-2; unit"),),
             attributes={"section": "Aspose.3D FOSS for Python > Installation"})
        for uid, text in units
    )
    return FactsDocument(base.repository, base.source_revision, (*base.facts, *extra))


def _kept(unit: str) -> dict[str, Any]:
    return {"unit_id": unit, "disposition": "VERIFIED_PRESERVE",
            "destination_section": "scope_limitations", "fact_ids": [], "rationale": "r"}


def test_a_kept_lead_in_with_nothing_after_it_is_printed_with_a_full_stop() -> None:
    lead = "inherited_unit:008.paragraph"
    facts = _python_facts((lead, "Install the package from PyPI:"))
    dispositions = _dispositions()
    dispositions["dispositions"].append(_kept(lead))
    decided = {p.unit_id: p for p in placements(_plan(), dispositions, facts, "python")}
    assert decided[lead].outcome == "placed"
    assert decided[lead].text == "Install the package from PyPI."
    readme = render_readme(ENTRY, facts, _plan(), UNITS, dispositions)
    assert "Install the package from PyPI." in readme
    assert "Install the package from PyPI:" not in readme
    # the reviewer reads the same form: the kept unit is printed, not lost
    assert lead not in {u for u, _ in unprinted_kept_units(readme, facts=facts, dispositions=dispositions)}


def test_negative_control_a_lead_in_followed_by_its_kept_block_keeps_its_colon() -> None:
    lead, block = "inherited_unit:008.paragraph", "inherited_unit:009.list"
    facts = _python_facts(
        (lead, "The package needs:"), (block, "- Python 3.10 or later\n- no native code")
    )
    dispositions = _dispositions()
    dispositions["dispositions"].extend([_kept(lead), _kept(block)])
    decided = {p.unit_id: p for p in placements(_plan(), dispositions, facts, "python")}
    assert decided[lead].text == "The package needs:"
