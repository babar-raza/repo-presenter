"""BL-640: a maintainers' status badge no fact verifies is never printed (BL-620), its value is carried by the
candidate stating it in words. When BC-17 still names the badge, restore keeps the unit that states the value
(TeX Python: ``072.list`` 'This is a Pre-Alpha release'); the badge row itself has no restore lever.

Real data: aspose-tex-foss/Aspose.TeX-FOSS-for-Python at 07db3203 (README header and Scope list); the BC-17
detail is the exact line of hosted run 44943500229."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.repair.restore_units import choose_units

STATUS = "https://img.shields.io/badge/status-pre--alpha-orange.svg"
DETAIL = (
    f"BC-17: inherited_unit:002.badge_row holds links '{STATUS}', which the published README prints and this "
    "candidate loses (technical_content): keep it (VERIFIED_PRESERVE/VERIFIED_MOVE, or PRESERVE_ATTRIBUTED when "
    "no fact confirms it), or omit it citing the fact that contradicts it"
)
BADGES = (
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/o/r/blob/main/LICENSE) "
    f"[![Status: Pre--Alpha]({STATUS})](https://github.com/o/r#scope-and-limitations)"
)
SCOPE = (
    "- This is a Pre-Alpha release: the core engine and public API are under active development.\n"
    "- Plain TeX is the supported format."
)


def _fact(fact_id: str, value: str) -> Fact:
    return Fact(
        id=fact_id, kind="inherited_unit", value=value, evidence=(Evidence("README.md", None),),  # type: ignore[arg-type]
        polarity="SUPPORTED", attributes={"section": "X"},  # type: ignore[arg-type]
    )


def _facts(scope: str = SCOPE) -> FactsDocument:
    return FactsDocument(
        "aspose-tex-foss/Aspose.TeX-FOSS-for-Python", "0" * 40,
        (
            _fact("inherited_unit:002.badge_row", BADGES),
            _fact("inherited_unit:072.list", scope),
            _fact("inherited_unit:073.paragraph", "Unrelated text."),
        ),
    )


def test_the_unit_that_states_the_badge_value_is_chosen_not_the_badge_row() -> None:
    assert choose_units([DETAIL], _facts()) == ["inherited_unit:072.list"]


def test_negative_control_a_value_no_unit_states_leaves_the_badge_row_chosen_as_before() -> None:
    silent = "- The core engine is under active development.\n- Plain TeX is the supported format."
    assert choose_units([DETAIL], _facts(silent)) == ["inherited_unit:002.badge_row"]


def test_negative_control_an_excluded_carrier_is_never_chosen() -> None:
    assert choose_units([DETAIL], _facts(), exclude=["inherited_unit:072.list"]) == ["inherited_unit:002.badge_row"]


def test_negative_control_a_verified_slot_badge_is_not_a_status_badge() -> None:
    detail = DETAIL.replace(STATUS, "https://img.shields.io/badge/python-3.10%2B-blue.svg")
    facts = _facts("- Needs python 3.10+ here.")
    assert choose_units([detail], facts) == ["inherited_unit:002.badge_row"]
