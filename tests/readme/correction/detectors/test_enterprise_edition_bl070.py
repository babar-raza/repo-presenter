"""BL-070: ``enterprise_edition_naming`` v4, from the two Lane L controls of M9 round 43559491132.

Both READMEs are aspose.org's own published readme-refresh candidates (``data/readme_published_state.json``
of aspose.org: Cells C++ PR #2 merged as 9f852d0f, Words Python PR #2 merged as 2d2efee2), so the live
text is the R42 reference. The excerpts below are verbatim from each seal's ``README.original.md``.

* Cells C++ (control 802069, lines 566-567): "[Aspose.Cells for C++ — Enterprise Edition](…), the
  commercial product line …" -- the phrase is an appositive of a link that already names the product.
  v3 rewrote it to "…, the Aspose.Cells for C++ — Enterprise Edition line …" (seal line 561, the
  model flagged the broken sentence). v4 leaves it as aspose.org published it.
* Words Python (control ab8a03, lines 625-626): "the commercial Aspose.Words" hard-wrapped before "API".
  v3 wrote "Aspose.Words — Enterprise Edition", a name the repository never uses; v4 takes the full
  name the README itself gives the Enterprise Edition (line 630), as aspose.org's anchor contract does:
  "Aspose.{Family} for {public_platform} — Enterprise Edition".
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.enterprise_edition import (
    ENTERPRISE_FACT_ID,
    enterprise_edition_naming,
)

CELLS_CPP = (
    "# Aspose.Cells FOSS for C++\n"
    "\n"
    "For the full commercial feature set, see\n"
    "[Aspose.Cells for C++ — Enterprise Edition](https://products.aspose.com/cells/cpp/), the\n"
    "commercial product line this FOSS edition's API is modeled on, with the wider format matrix and\n"
    "the full calculation engine.\n"
)
WORDS_PYTHON = (
    "# Aspose.Words FOSS for Python\n"
    "\n"
    "- Of `PdfSaveOptions`'s 17 fields, 8 — `text_compression`, `embed_full_fonts`, `use_core_fonts`,\n"
    "  `font_embedding_mode`, `page_mode`, `color_mode`, `preserve_form_fields`, and\n"
    "  `memory_optimization` — exist for API forward-compatibility with the commercial Aspose.Words\n"
    "  API and are not yet consumed by the PDF writer.\n"
    "\n"
    "For DOC writing, strict ISO 29500 compliance, and the additional load/save formats and page-layout\n"
    "features beyond this edition's scope, see\n"
    "[Aspose.Words for Python — Enterprise Edition](https://products.aspose.com/words/python-net/),\n"
    "which adds the full commercial feature set on top of the same compatible document model.\n"
)


def _enterprise(make_fact: Any, url: str, level: str = "platform") -> Any:
    return make_fact(ENTERPRISE_FACT_ID, url, evidence=((url, "enterprise target"),),
                     attributes={"level": level, "role": "enterprise"})


def test_no_edit_next_to_a_link_that_already_names_the_product(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    ctx = make_context(CELLS_CPP, make_facts(_enterprise(make_fact, "https://products.aspose.com/cells/cpp/")))
    result = enterprise_edition_naming(ctx)
    assert result.edits == ()
    assert result.findings == ()  # an appositive of a correctly named product is not a naming violation


def test_the_same_phrase_without_the_link_before_it_is_still_fixed(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    """Negative control: the bare phrase with no naming link before it keeps v3's H1-derived fix."""
    readme = CELLS_CPP.replace(
        "[Aspose.Cells for C++ — Enterprise Edition](https://products.aspose.com/cells/cpp/), the\n", "the\n"
    )
    ctx = make_context(readme, make_facts(_enterprise(make_fact, "https://products.aspose.com/cells/cpp/")))
    (edit,) = enterprise_edition_naming(ctx).edits
    assert edit.original == "commercial product"
    assert edit.replacement == "Aspose.Cells for C++ — Enterprise Edition"


def test_a_short_name_takes_the_readmes_own_full_enterprise_name(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    ctx = make_context(WORDS_PYTHON, make_facts(_enterprise(make_fact, "https://products.aspose.com/words/python-net/")))
    (edit,) = enterprise_edition_naming(ctx).edits
    assert edit.original == "the commercial Aspose.Words"
    assert edit.replacement == "Aspose.Words for Python — Enterprise Edition"
    corrected = WORDS_PYTHON[: edit.start] + edit.replacement + WORDS_PYTHON[edit.end :]
    assert "Aspose.Words — Enterprise Edition" not in corrected


def test_a_family_level_target_keeps_the_family_name(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    """Negative control: aspose.org's family anchor names no platform."""
    ctx = make_context(WORDS_PYTHON, make_facts(_enterprise(make_fact, "https://products.aspose.com/words/", "family")))
    (edit,) = enterprise_edition_naming(ctx).edits
    assert edit.replacement == "Aspose.Words — Enterprise Edition"


def test_a_dotted_foss_h1_gives_the_platform_name(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    """PSD .NET live README at b6f778e9 (H1 "Aspose.PSD.FOSS for .NET", line 5): v3 wrote "Aspose.PSD —
    Enterprise Edition" at the platform-level psd/net target; v4 names "Aspose.PSD for .NET"."""
    readme = (
        "# Aspose.PSD.FOSS for .NET\n"
        "\n"
        "This library is for metadata-safe PSD/PSB inspection and limited structural editing. It is not a "
        "rendering engine, a raster editor, or an open-source replacement for the full commercial Aspose.PSD product.\n"
    )
    ctx = make_context(readme, make_facts(_enterprise(make_fact, "https://products.aspose.com/psd/net/")))
    (edit,) = enterprise_edition_naming(ctx).edits
    assert edit.original == "commercial Aspose.PSD product"
    assert edit.replacement == "Aspose.PSD for .NET — Enterprise Edition"


def test_no_platform_qualified_name_anywhere_is_reported_not_guessed(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    readme = "\n".join(WORDS_PYTHON.splitlines()[2:6]) + "\n"  # no H1, no Enterprise Edition link
    ctx = make_context(readme, make_facts(_enterprise(make_fact, "https://products.aspose.com/words/python-net/")))
    result = enterprise_edition_naming(ctx)
    assert result.edits == ()
    assert any("no platform-qualified name" in f.reason for f in result.findings)
