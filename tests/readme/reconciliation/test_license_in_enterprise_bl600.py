"""BL-600: a license paragraph the model filed under the Enterprise Edition section is the License section's.

Real shape (sealed Aspose.OCR FOSS for .NET, unit 076.paragraph; 13 of 30 sealed Lane R dispositions file the
license paragraph there): the model superseded the maintainers' license paragraph into ``enterprise_relationship``,
the Enterprise clause was authored from it and printed "See [... Enterprise Edition](...). This project is licensed
under the MIT License. The MIT License permits ... commercial use ...", which 4 of 4 fresh independent audit samples
faulted as promotional text (``quality``). Re-filing happens at generation only (S4's ``normalize``): the sealed
document re-certification folds (``fit_sealed_sections``) is untouched (R10).
"""

from __future__ import annotations

import copy
from typing import Any

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import fit_sealed_sections, normalize

_REPO = "aspose-ocr-foss/Aspose.OCR-FOSS-for-.NET"
LICENSE_076 = (
    "This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying,\n"
    "modification, distribution, sublicensing, and commercial use, provided its copyright and\n"
    "permission notice are retained. The software is provided without warranty."
)
ENTERPRISE_075 = (
    "Aspose.OCR for .NET Enterprise Edition adds recognition of more scripts and handwriting; "
    "see the commercial product page."
)


def _facts() -> FactsDocument:
    def unit(uid: str, text: str, heading: str) -> Fact:
        return Fact(
            uid, "inherited_unit", text, (Evidence("README.md", None),),
            attributes={"section": f"Aspose.OCR FOSS for .NET > {heading}"},
        )

    return FactsDocument(
        _REPO,
        "032181110c3d6d3689404021d7473ccfd9050a80",
        (
            Fact("identity:repository", "identity", _REPO, (Evidence("x"),)),
            Fact("license:file", "license", "LICENSE", (Evidence("LICENSE"),)),
            Fact("license:spdx", "license", "MIT", (Evidence("LICENSE"),)),
            Fact(
                "link_target:product.enterprise", "link_target", "https://products.aspose.com/ocr/net/",
                (Evidence("https://products.aspose.com/ocr/net/"),),
            ),
            unit("inherited_unit:075.paragraph", ENTERPRISE_075, "License"),
            unit("inherited_unit:076.paragraph", LICENSE_076, "License"),
        ),
    )


def _dispositions(disposition: str) -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": "inherited_unit:075.paragraph",
                "disposition": disposition,
                "destination_section": "enterprise_relationship",
                "fact_ids": ["link_target:product.enterprise"],
                "rationale": "Describes the commercial product.",
            },
            {
                "unit_id": "inherited_unit:076.paragraph",
                "disposition": disposition,
                "destination_section": "enterprise_relationship",
                "fact_ids": ["license:spdx", "link_target:product.enterprise"],
                "rationale": "Provides license details, placed here to avoid duplicating license prose.",
            },
        ]
    }


def _by_unit(output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["unit_id"]: entry for entry in output["dispositions"]}


def test_a_license_paragraph_filed_under_enterprise_goes_to_the_license_section() -> None:
    for disposition in ("SUPERSEDE_REDUNDANT", "VERIFIED_PRESERVE"):
        output = _dispositions(disposition)
        normalize(output, _facts())
        entry = _by_unit(output)["inherited_unit:076.paragraph"]
        assert entry["disposition"] == "SUPERSEDE_REDUNDANT"
        assert entry["destination_section"] == "license"
        assert set(entry["fact_ids"]) == {"license:file", "license:spdx"}
        assert len(entry["rationale"]) <= 160


def test_a_paragraph_that_speaks_of_the_commercial_product_stays_in_the_enterprise_section() -> None:
    """Negative control: the real Enterprise paragraph is never moved, and a license paragraph that also
    names the Enterprise Edition (a statement about the other product) stays where the model filed it."""
    output = _dispositions("VERIFIED_PRESERVE")
    normalize(output, _facts())
    entry = _by_unit(output)["inherited_unit:075.paragraph"]
    assert entry["destination_section"] == "enterprise_relationship"
    mixed = _facts()
    swapped = FactsDocument(
        mixed.repository,
        mixed.source_revision,
        tuple(
            Fact(
                f.id, f.kind,
                LICENSE_076 + " The Enterprise Edition is licensed commercially." if f.id == "inherited_unit:076.paragraph" else f.value,
                f.evidence, attributes=f.attributes,
            )
            for f in mixed.facts
        ),
    )
    output = _dispositions("VERIFIED_PRESERVE")
    normalize(output, swapped)
    assert _by_unit(output)["inherited_unit:076.paragraph"]["destination_section"] == "enterprise_relationship"


def test_a_sealed_document_is_not_re_filed_by_re_certification() -> None:
    """R10: ``fit_sealed_sections`` (re-certification) never moves it; only generation does."""
    sealed = _dispositions("SUPERSEDE_REDUNDANT")
    before = copy.deepcopy(sealed)
    fit_sealed_sections(sealed, _facts())
    assert sealed == before
