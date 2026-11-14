"""BL-088: an inherited unit kept as written that prints an OPEN findings-register quote cites the
row deterministically, so it prints without exactly the false item (``must_correct.withheld_form``).

Real data: Aspose.HTML-FOSS-for-Python at bf0f1e7a6d29 (sealed Lane R bundle and hosted run
43525324808). ``inherited_unit:080.list`` was kept VERIFIED_PRESERVE citing nothing; its first item
"`css.parse` — parse selector and declaration text" is an OPEN register row
(``finding:0d79c4711d58``, ``data/readme_findings.json``), so BC-18 failed on maintainer text the
register had already settled, and the targeted repair returned the unit unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import _fold_register_kept_units
from repo_presenter.readme.validation.must_correct import withheld_form

HTML = "aspose-html-foss/Aspose.HTML-FOSS-for-Python"
FINDING = "finding:0d79c4711d58"
QUOTE = "`css.parse` — parse selector and declaration text"
LIST = (
    "- `css.parse` — parse selector and declaration text; selector AST classes (`ClassSelector`, "
    "`TypeSelector`, `AttributeSelector`, `PseudoClassSelector`, `ComplexSelector`, "
    "`CompoundSelector`, and others) model the parsed grammar.\n"
    "- `CSSStyleSheet`, `CSSStyleRule`, `CSSMediaRule`, `CSSFontFaceRule`, `CSSKeyframesRule`, and "
    "the other `CSSRule` subclasses — structural CSSOM stylesheet/rule objects.\n"
    "- `CSSStyleDeclaration`, `ComputedStyleDeclaration` — live inline styles and read-only "
    "resolved (cascade-computed) styles."
)


@pytest.fixture(autouse=True)
def real_register(monkeypatch: pytest.MonkeyPatch) -> None:
    from repo_presenter.readme.validation import must_correct

    monkeypatch.setattr(
        must_correct,
        "DEFAULT_FINDINGS_PATH",
        Path(__file__).resolve().parents[3] / "data" / "readme_findings.json",
    )


def _facts(repository: str, units: dict[str, str]) -> FactsDocument:
    return FactsDocument(
        repository,
        "bf0f1e7a6d29ca9e14de576fe3ff1aa49ddbaf11",
        tuple(
            Fact(uid, "inherited_unit", text, (Evidence("README.md", "lines 1-3; list"),))
            for uid, text in units.items()
        ),
    )


def _entry(unit_id: str, disposition: str = "VERIFIED_PRESERVE") -> dict:
    return {"unit_id": unit_id, "disposition": disposition, "destination_section": "api_reference",
            "fact_ids": [], "rationale": "Kept in api_reference."}


def test_the_kept_list_cites_the_row_and_prints_without_the_false_item() -> None:
    output = {"dispositions": [_entry("inherited_unit:080.list")]}
    _fold_register_kept_units(output, _facts(HTML, {"inherited_unit:080.list": LIST}))
    assert output["dispositions"][0]["fact_ids"] == [FINDING]
    printed = withheld_form("inherited_unit:080.list", LIST, [QUOTE])
    assert "css.parse" not in printed and "CSSStyleDeclaration" in printed


def test_negative_controls() -> None:
    # another repository: the row is not this repository's, nothing is cited
    output = {"dispositions": [_entry("inherited_unit:080.list")]}
    _fold_register_kept_units(output, _facts("other/repo", {"inherited_unit:080.list": LIST}))
    assert output["dispositions"][0]["fact_ids"] == []
    # a superseded unit is not kept as written: the fold leaves it to BC-05/BC-18
    output = {"dispositions": [_entry("inherited_unit:080.list", "SUPERSEDE_REDUNDANT")]}
    _fold_register_kept_units(output, _facts(HTML, {"inherited_unit:080.list": LIST}))
    assert output["dispositions"][0]["fact_ids"] == []
    # a unit that is nothing but the false text: nothing would be left to print, so no citation
    only = f"- {QUOTE}"
    output = {"dispositions": [_entry("inherited_unit:081.list")]}
    _fold_register_kept_units(output, _facts(HTML, {"inherited_unit:081.list": only}))
    assert output["dispositions"][0]["fact_ids"] == []
