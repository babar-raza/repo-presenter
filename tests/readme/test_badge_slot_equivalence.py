"""R2 is content equivalence: a maintainers' badge/banner whose slot the candidate fills with its own
verified slot badge is REPLACED, not lost -- one judgement (parity_gate.badge_slot_replaced) shared by
BC-17 (technical_content), live_readme_loss and disposition_coverage.

Real text: Aspose.Font-FOSS-for-Python's live header and the candidate the pipeline rendered for it
(2026-11-10 batch run), and Aspose.Page-FOSS-for-Python's three example-result images, which the unit
splitter classed as ``badge_row`` although they are body content."""

from __future__ import annotations

from repo_presenter.readme.parity_gate import (
    badge_row_replaced,
    badge_slot_of_url,
    badge_slot_replaced,
    candidate_badge_slots,
)

LIVE_FONT = (
    "[![Aspose.Font FOSS for Python](https://raw.githubusercontent.com/aspose-font-foss/"
    "Aspose.Font-FOSS-for-Python/main/docs/images/banner.png)](https://github.com/aspose-font-foss/"
    "Aspose.Font-FOSS-for-Python)\n\n# Aspose.Font FOSS for Python\n\n"
    "[![PyPI version](https://img.shields.io/pypi/v/aspose-font-foss.svg)](https://pypi.org/project/aspose-font-foss/)\n"
    "[![Python License](https://img.shields.io/pypi/l/aspose-font-foss.svg)]"
    "(https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/blob/main/LICENSE.txt)\n"
    "[![Contributors](https://img.shields.io/github/contributors/aspose-font-foss/Aspose.Font-FOSS-for-Python.svg)]"
    "(https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/graphs/contributors)\n"
)
CANDIDATE_FONT = (
    "# Aspose.Font FOSS for Python\n\n"
    "[![PyPI](https://img.shields.io/pypi/v/aspose-font-foss.svg)](https://pypi.org/project/aspose-font-foss/) "
    "![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg) "
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.txt) "
    "[![Contributors](https://img.shields.io/github/contributors/aspose-font-foss/Aspose.Font-FOSS-for-Python)]"
    "(https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/graphs/contributors)\n\n"
    "[![Aspose.Font FOSS for Python](https://products.aspose.org/media/font/python/banner-readme.png)]"
    "(https://products.aspose.org/font/python/)\n"
)
PAGE_IMAGE = "![XPS to PDF to PNG result](readme.resources/mb03.png)"


def test_slots_are_read_off_the_image_url() -> None:
    assert badge_slot_of_url("https://raw.githubusercontent.com/x/y/main/docs/images/banner.png") == "banner"
    assert badge_slot_of_url("https://products.aspose.org/media/font/python/banner-readme.png") == "banner"
    assert badge_slot_of_url("https://img.shields.io/pypi/l/aspose-font-foss.svg") == "license"
    assert badge_slot_of_url("https://img.shields.io/badge/License-MIT-blue.svg") == "license"
    assert badge_slot_of_url("https://img.shields.io/github/contributors/o/r.svg") == "contributors"
    assert badge_slot_of_url("https://img.shields.io/pypi/v/aspose-font-foss.svg") == "package"
    assert badge_slot_of_url("https://img.shields.io/badge/python-3.10%2B-blue.svg") == "runtime"
    assert badge_slot_of_url("readme.resources/mb03.png") is None


def test_each_lost_font_badge_is_replaced_by_the_candidates_slot_badge() -> None:
    assert candidate_badge_slots(CANDIDATE_FONT) >= {"banner", "package", "runtime", "license", "contributors"}
    for href in (
        "https://raw.githubusercontent.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/main/docs/images/banner.png",
        "https://img.shields.io/pypi/l/aspose-font-foss.svg",
        "https://img.shields.io/github/contributors/aspose-font-foss/Aspose.Font-FOSS-for-Python.svg",
    ):
        assert badge_slot_replaced(href, LIVE_FONT, CANDIDATE_FONT), href


def test_the_link_target_of_a_replaced_license_badge_is_replaced_too() -> None:
    target = "https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/blob/main/LICENSE.txt"
    assert badge_slot_replaced(target, LIVE_FONT, CANDIDATE_FONT)


def test_a_slot_the_candidate_leaves_empty_is_never_exempt() -> None:
    no_license = CANDIDATE_FONT.replace(
        "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.txt) ", ""
    )
    assert "license" not in candidate_badge_slots(no_license)
    assert badge_slot_replaced("https://img.shields.io/pypi/l/aspose-font-foss.svg", LIVE_FONT, no_license) is None


def test_a_contradicted_href_is_never_exempt() -> None:
    href = "https://img.shields.io/pypi/l/aspose-font-foss.svg"
    assert badge_slot_replaced(href, LIVE_FONT, CANDIDATE_FONT, frozenset({href})) is None


def test_a_body_image_is_content_never_a_badge() -> None:
    assert badge_slot_replaced("readme.resources/mb03.png", PAGE_IMAGE, CANDIDATE_FONT) is None
    assert badge_row_replaced(PAGE_IMAGE, CANDIDATE_FONT) is False


def test_a_badge_row_unit_is_replaced_only_when_every_badge_is_printed_or_replaced() -> None:
    row = (
        "[![PyPI version](https://img.shields.io/pypi/v/aspose-font-foss.svg)](https://pypi.org/project/aspose-font-foss/)\n"
        "[![Python License](https://img.shields.io/pypi/l/aspose-font-foss.svg)](LICENSE.txt)"
    )
    assert badge_row_replaced(row, CANDIDATE_FONT)
    assert not badge_row_replaced(row + "\nSome prose the row also carries.", CANDIDATE_FONT)
    assert not badge_row_replaced(row, "# no badges at all\n")


def _facts_with(units: dict[str, str]):
    from repo_presenter.core.facts import Evidence, Fact, FactsDocument

    return FactsDocument(
        "aspose-font-foss/Aspose.Font-FOSS-for-Python",
        "0" * 40,
        tuple(
            Fact(id=uid, kind="inherited_unit", value=text,  # type: ignore[arg-type]
                 evidence=(Evidence("README.md", None),), polarity="SUPPORTED")
            for uid, text in units.items()
        ),
    )


def test_the_reviewer_and_accounting_read_a_replaced_badge_row_differently_on_purpose() -> None:
    from repo_presenter.readme.review.independent_reviewer import unprinted_kept_units

    banner_row = LIVE_FONT.split("\n\n")[0]
    badge_row = "\n".join(LIVE_FONT.split("\n")[4:7])
    page_row = PAGE_IMAGE
    units = {
        "inherited_unit:001.badge_row": banner_row,
        "inherited_unit:003.badge_row": badge_row,
        "inherited_unit:039.badge_row": page_row,
    }
    dispositions = {
        "dispositions": [
            {"unit_id": uid, "disposition": "VERIFIED_PRESERVE", "destination_section": "opening",
             "fact_ids": [], "rationale": "kept"}
            for uid in units
        ]
    }
    facts = _facts_with(units)
    lenient = unprinted_kept_units(CANDIDATE_FONT, facts=facts, dispositions=dispositions)
    # the reviewer: both header rows are replaced by their slots' verified badges; the example
    # image the splitter mislabelled badge_row is body content and stays unprinted
    assert [u for u, _ in lenient] == ["inherited_unit:039.badge_row"]
    strict = unprinted_kept_units(
        CANDIDATE_FONT, facts=facts, dispositions=dispositions, slot_equivalence=False
    )
    # accounting: still sees every row that is not printed as written, so it can record the
    # supersession explicitly
    assert {u for u, _ in strict} == set(units)
