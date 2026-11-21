"""BL-622: the maintainers' license sentence that links the license file's web address is superseded by the
License section, which links that very file; it used to rest on a fact "the License section does not render"
and stay in Scope and Limitations, where BC-05 section fit named it on every settle round (hosted Lane R run
44924893253, Aspose.TeX-FOSS-for-Python: "section fit: Scope and Limitations states the project's license,
which the License section states: 'This project is licensed under the [MIT License](https://github.com/...').
Text and facts are the pinned README (07db3203) and its extracted link_target / license facts.
The fold counts the link only at restore time (``license_links=True``): a sealed disposition document that keeps
such a sentence where it is (Aspose.Font-FOSS-for-Python 063.paragraph, RECERTIFIED) is held to the S4 fold as before."""

from __future__ import annotations

from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    fit_sealed_sections,
    license_file_link_ids,
)
from repo_presenter.readme.repair.restore_units import fit_misfiled_units

_REPO = "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"
_BASE = f"https://github.com/{_REPO}/blob/main/"
LICENSE_UNIT = "inherited_unit:081.paragraph"
FONTS_UNIT = "inherited_unit:082.paragraph"
SENTENCE = (
    f"This project is licensed under the [MIT License]({_BASE}LICENSE). The MIT License permits use, copying,\n"
    "modification, distribution, sublicensing, and commercial use, provided its copyright and\n"
    "permission notice are retained. The software is provided without warranty."
)


def _facts(*, license_file: bool = True, link: str = f"{_BASE}LICENSE") -> FactsDocument:
    ev = (Evidence("x"),)
    facts = [
        Fact("identity:repository", "identity", _REPO, ev),
        Fact("license:spdx", "license", "MIT", ev),
        Fact("link_target:002", "link_target", link, ev),
        Fact("link_target:024", "link_target", f"{_BASE}LICENSE-FONTS", ev),
        Fact(LICENSE_UNIT, "inherited_unit", SENTENCE, (Evidence("README.md"),), attributes={"section": "Aspose.TeX FOSS for Python > License"}),
    ]
    if license_file:
        facts.append(Fact("license:file", "license", "LICENSE", ev))
    return FactsDocument(_REPO, "0" * 40, tuple(facts))


def _dispositions(cited: list[str]) -> dict[str, Any]:
    return {
        "dispositions": [
            {"unit_id": LICENSE_UNIT, "disposition": "VERIFIED_PRESERVE", "destination_section": "scope_limitations", "fact_ids": cited, "rationale": "kept"}
        ]
    }


def test_the_web_address_of_the_license_file_is_found() -> None:
    assert license_file_link_ids(_facts()) == {"link_target:002"}  # not LICENSE-FONTS: another file
    assert license_file_link_ids(_facts(license_file=False)) == frozenset()
    assert license_file_link_ids(_facts(link="https://example.com/blob/main/LICENSE.txt")) == frozenset()


def test_the_license_sentence_that_links_the_file_moves_out_of_scope_at_restore_time() -> None:
    output = _dispositions(["link_target:002"])
    fit_sealed_sections(output, _facts(), license_links=True)
    [row] = output["dispositions"]
    assert (row["disposition"], row["destination_section"]) == ("SUPERSEDE_REDUNDANT", "license")
    assert "link_target:024" not in row["fact_ids"] and "link_target:002" in row["fact_ids"]


def test_a_sealed_disposition_document_is_held_to_the_s4_fold_as_before() -> None:
    sealed = _dispositions(["link_target:002"])
    fit_sealed_sections(sealed, _facts())
    assert sealed["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"  # recertification moves no sealed byte


def test_the_zero_call_fit_records_the_move() -> None:
    _output, changes = fit_misfiled_units(_dispositions(["link_target:002"]), _facts(), ["license", "scope_limitations"])
    assert [(c["unit_id"], c["now"]) for c in changes] == [(LICENSE_UNIT, "SUPERSEDE_REDUNDANT -> license")]


def test_negative_controls_a_sentence_resting_on_another_link_or_no_license_file_stays() -> None:
    other = _dispositions(["link_target:024"])
    fit_sealed_sections(other, _facts(), license_links=True)
    assert other["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"  # cites the fonts license: not rendered
    no_file = _dispositions(["link_target:002"])
    fit_sealed_sections(no_file, _facts(license_file=False), license_links=True)
    assert no_file["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_the_superseded_sentence_is_stated_by_the_license_section_that_links_the_file() -> None:
    from repo_presenter.readme.validation.content_presence import unstated

    readme = "## License\n\nThis project is licensed under the [MIT License](LICENSE).\n"
    assert not [p for p in unstated(SENTENCE, readme, kind="paragraph", strict=True) if p.startswith("link ")]
    nothing = "## License\n\nThis project is licensed under the MIT License.\n"
    assert any(p.startswith("link ") for p in unstated(SENTENCE, nothing, kind="paragraph", strict=True))
    other = "## License\n\nSee the [font license](LICENSE-FONTS).\n"
    assert any(p.startswith("link ") for p in unstated(SENTENCE, other, kind="paragraph", strict=True))
    prose = "## License\n\nThe license file is LICENSE and the license is MIT.\n"
    assert any(p.startswith("link ") for p in unstated(SENTENCE, prose, kind="paragraph", strict=True))
