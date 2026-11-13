"""A kept maintainers' unit prints the product named as BC-12 requires.

The maintainers' own wording uses the short family name ("Aspose.Cells FOSS") or the platform as
"C++" where the registry spells it "Cpp". Zero-call restore keeps such a unit verbatim, so BC-12
failed on it and the whole restore result was discarded (measured 2026-11-11: PDF Cpp, Slides Cpp,
Cells Cpp, Cells Go). ``kept_unit_form`` is the one printable form the renderer, BC-05 and the
independent reviewer share, so the correction lives where "printed" is defined; the texts below are
the maintainers' real ones.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.placement import placements
from repo_presenter.readme.review.independent_reviewer import unprinted_kept_units
from repo_presenter.readme.validation.structure import canonical_name_failures
from repo_presenter.readme.validation.surface_claims import canonical_name_form, kept_unit_form

from tests.readme.validation.test_registry_checks import REPO_ROOT

GO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
SLIDES_CPP = "aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp"
PDF_CPP = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp"

# Cells Go inherited_unit:055.list, verbatim: the short name, once broken across a line wrap.
GO_LIST = (
    "- **[Getting started guide](https://docs.aspose.org/cells/go/)** — Go documentation for\n"
    "  Aspose.Cells FOSS: loading, editing, styling, and saving spreadsheets.\n"
    "- **[How-to guides & FAQ](https://kb.aspose.org/cells/go/)** — Go knowledge base for "
    "Aspose.Cells\n  FOSS: how-to articles, FAQ, and troubleshooting guides.\n"
)
# Slides Cpp inherited_unit:004.paragraph, verbatim: the platform written "C++".
SLIDES_PARAGRAPH = (
    "Aspose.Slides FOSS for C++ is a free, open-source, MIT-licensed C++ library for creating, "
    "reading, and editing PowerPoint `.pptx` presentations. It integrates into CMake-based build "
    "systems via `FetchContent` and requires no Microsoft PowerPoint installation."
)


def _facts(repository: str, *units: tuple[str, str]) -> FactsDocument:
    return FactsDocument(
        repository,
        "0" * 40,
        tuple(
            Fact(uid, "inherited_unit", text, (Evidence("README.md", None),), polarity="SUPPORTED")
            for uid, text in units
        ),
    )


def _bc12(repository: str, readme: str) -> list[str]:
    registry = json.loads((REPO_ROOT / "data" / "registry.json").read_text(encoding="utf-8"))
    entry = RegistryEntry.model_validate(
        next(e for e in registry["entries"] if e["repository"] == repository)
    )
    return [f.detail for f in canonical_name_failures(SimpleNamespace(entry=entry, readme=readme))]


def test_the_real_go_list_fails_bc12_as_written_and_passes_once_printed_in_its_kept_form() -> None:
    assert _bc12(GO, GO_LIST)  # the failure that discarded the restore
    printed = canonical_name_form(GO_LIST, _facts(GO))
    assert _bc12(GO, printed) == []
    assert "Aspose.Cells FOSS for Go: loading" in printed
    assert "Aspose.Cells FOSS for Go: how-to" in printed  # the wrapped one, rejoined


def test_a_platform_written_cplusplus_is_rewritten_to_the_registrys_spelling() -> None:
    assert _bc12(SLIDES_CPP, SLIDES_PARAGRAPH)
    # Another edition named in prose, or a link whose text is not the name of the repository it
    # targets, proves nothing about which product it names: still BC-12's to flag.
    assert _bc12(SLIDES_NET, "Aspose.Slides FOSS for Java provides charts.")
    assert _bc12(
        SLIDES_NET,
        "- [Aspose.Slides FOSS](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java)",
    )
    printed = canonical_name_form(SLIDES_PARAGRAPH, _facts(SLIDES_CPP))
    assert printed.startswith("Aspose.Slides FOSS for Cpp is a free")
    assert "MIT-licensed C++ library" in printed  # the language name elsewhere is untouched
    assert _bc12(SLIDES_CPP, printed) == []


def test_link_destinations_urls_code_spans_and_fences_are_left_byte_for_byte() -> None:
    text = (
        "See [Aspose.PDF FOSS](https://github.com/aspose-pdf-foss/Aspose.PDF.FOSS/blob/main/x)\n"
        "and `Aspose.PDF FOSS` and https://example.com/Aspose.PDF.FOSS/docs here.\n\n"
        "```bash\necho Aspose.PDF FOSS\n```\n"
    )
    printed = canonical_name_form(text, _facts(PDF_CPP))
    assert "[Aspose.PDF FOSS for Cpp](https://github.com/aspose-pdf-foss/Aspose.PDF.FOSS/blob/main/x)" in printed
    assert "`Aspose.PDF FOSS`" in printed
    assert "https://example.com/Aspose.PDF.FOSS/docs" in printed
    assert "```bash\necho Aspose.PDF FOSS\n```" in printed


def test_text_that_already_uses_the_canonical_name_or_none_is_unchanged() -> None:
    facts = _facts(PDF_CPP)
    for text in ("Aspose.PDF FOSS for Cpp reads PDFs.", "A library with no product name."):
        assert canonical_name_form(text, facts) is text or canonical_name_form(text, facts) == text


def test_a_name_split_by_a_blank_line_is_two_paragraphs_not_a_name() -> None:
    text = "Aspose.PDF\n\nFOSS stands alone here."
    assert canonical_name_form(text, _facts(PDF_CPP)) == text


def test_a_heading_unit_is_not_rewritten_because_a_loss_check_matches_headings_by_text() -> None:
    facts = _facts(PDF_CPP)
    assert kept_unit_form("inherited_unit:001.heading", "# Aspose.PDF FOSS", facts) == "# Aspose.PDF FOSS"
    assert kept_unit_form("inherited_unit:002.paragraph", "Aspose.PDF FOSS reads.", facts) == (
        "Aspose.PDF FOSS for Cpp reads."
    )


def test_placement_and_the_reviewer_agree_on_the_corrected_printed_form() -> None:
    unit = "inherited_unit:004.paragraph"
    facts = _facts(SLIDES_CPP, (unit, SLIDES_PARAGRAPH))
    dispositions = {
        "dispositions": [
            {
                "unit_id": unit,
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "scope_limitations",
                "fact_ids": [],
                "rationale": "kept",
            }
        ]
    }
    plan = {"sections": [{"section_id": "scope_limitations", "include": True}]}
    (placed,) = placements(plan, dispositions, facts, "cpp")
    assert placed.text.startswith("Aspose.Slides FOSS for Cpp is a free")
    readme = "# X\n\n## Scope\n\n" + placed.text + "\n"
    assert unprinted_kept_units(readme, facts=facts, dispositions=dispositions) == []
    # The reviewer is lenient about a name-only difference, so the verbatim wording also reads as
    # printed there; what matters is that the corrected form -- the one the renderer now prints --
    # is never reported as a kept unit the README fails to print.
    assert kept_unit_form(unit, SLIDES_PARAGRAPH, facts) == placed.text


SLIDES_NET = "aspose-slides-foss/Aspose.Slides-FOSS-for-.NET"
# Slides .NET inherited_unit:083.list, verbatim (README lines 493-495 at 86c441b5): the maintainers'
# links to the sibling editions, each named in full.
SLIDES_NET_SIBLINGS = (
    "- [Aspose.Slides FOSS for Java](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java)\n"
    "- [Aspose.Slides FOSS for C++](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp)\n"
    "- [Aspose.Slides FOSS for Python](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python)"
)


def test_a_sibling_edition_named_in_full_is_another_product_not_a_misspelling() -> None:
    """Run 43413917875: BC-12 read "Aspose.Slides FOSS for Java" as this product's short name, so the
    zero-call restore rolled 083.list back as a new BC-12 failure and the reviewer then refused the
    three sibling links as lost. The printable form already leaves the list untouched (another
    product), and BC-12 now agrees with it."""
    assert kept_unit_form("inherited_unit:083.list", SLIDES_NET_SIBLINGS, _facts(SLIDES_NET)) == (
        SLIDES_NET_SIBLINGS
    )
    assert _bc12(SLIDES_NET, SLIDES_NET_SIBLINGS) == []


def test_the_products_own_short_name_and_its_cplusplus_tail_still_fail() -> None:
    """The sibling rule exempts only "for <another platform>": the bare short name, a variant of
    this product's own tail, and the C++ spelling of the Cpp tail are still this product."""
    assert _bc12(SLIDES_NET, "Aspose.Slides FOSS reads decks.")
    assert _bc12(SLIDES_NET, "Aspose.Slides FOSS for .Net reads decks.")
    assert _bc12(SLIDES_CPP, SLIDES_PARAGRAPH)
    # Another edition named in prose, or a link whose text is not the name of the repository it
    # targets, proves nothing about which product it names: still BC-12's to flag.
    assert _bc12(SLIDES_NET, "Aspose.Slides FOSS for Java provides charts.")
    assert _bc12(
        SLIDES_NET,
        "- [Aspose.Slides FOSS](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java)",
    )
