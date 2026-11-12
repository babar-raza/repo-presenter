"""Coherence length recovery. Real data: aspose-slides-foss/Aspose.Slides-FOSS-for-Python's batch-1
run (2026-11-10) - the `opening` unit was 737 characters before coherence; the revision that kept
every cited fact was 2066 characters, past MAX_UNIT_CHARS (1500), and the run died. Texts below are
verbatim from that run's content_units.json and rejected reply."""

from __future__ import annotations

from repo_presenter.readme.composition.coherence import recover_coherence_overlong_units
from repo_presenter.readme.composition.text_hygiene import MAX_UNIT_CHARS

EXISTING_TEXT = "Aspose.Slides FOSS for Python reads and writes .pptx presentations. It converts presentations to other .pptx files using slides_foss.export.SaveFormat. It supports adding shapes such as rectangles, charts, tables, connectors, and group shapes via slides_foss.ShapeCollection methods like add_auto_shape, add_chart, add_table, add_connector, and add_group_shape. It supports formatting text with BasePortionFormat and ParagraphFormat, applying fill and line formats with FillFormat and LineFormat, and setting slide transition behavior with slides_foss.slideshow.TransitionType. It manages document properties via DocumentProperties, speaker notes via NotesSlideManager, comments via CommentAuthorCollection, and hyperlinks via Hyperlink."
REVISED_TEXT = "Aspose.Slides FOSS for Python reads and writes .pptx presentations. It converts presentations to other .pptx files using slides_foss.export.SaveFormat. It supports adding shapes such as rectangles, charts, tables, connectors, and group shapes via slides_foss.ShapeCollection methods like add_auto_shape, add_chart, add_table, add_connector, and add_group_shape. It supports formatting text at the portion and paragraph level using slides_foss.BasePortionFormat and slides_foss.ParagraphFormat, applying fill and line formats with slides_foss.FillFormat and slides_foss.LineFormat, and setting slide transition behavior with slides_foss.slideshow.TransitionType. It manages presentation metadata through slides_foss.DocumentProperties, adds speaker notes per slide using slides_foss.NotesSlideManager, handles comments via slides_foss.CommentAuthorCollection, and attaches hyperlinks to shapes or text portions via slides_foss.Hyperlink. The package is named aspose-slides-foss and requires Python version 3.10 or later. Input is limited to .pptx files, and SaveFormat declares additional values such as Ppt, Pdf, Xps, Tiff, Odp, Html, Swf, Otp, and more, but only the OOXML presentation family (Pptx, Pptm, Ppsx, Ppsm, Potx, Potm) and SaveFormat.MD produce valid output; every other SaveFormat value raises ValueError at save time. Rendering and conversion to PDF, HTML, XPS, or image formats is not implemented, and the API member is absent rather than present and inert. SmartArt, OLE objects, mathematical text, VBA macros, digital signatures, and action settings other than external hyperlinks are not implemented and raise NotImplementedError. Comment threads are written using only the classic comment-list schema on every save; reply-to-a-reply chains are preserved via each comment's parent_comment, but any features that require a modern PowerPoint-authored thread format are not represented. Unknown XML parts encountered during load are preserved verbatim on save, so opening and re-saving a file never strips content this library does not yet understand."
EXISTING_FACT_IDS = ["identity:ecosystem", "identity:family", "identity:platform", "identity:product-knowledge-refresh", "identity:repository", "identity:revision", "package:license", "package:name", "package:published_version", "package:python_requires", "package:registry_lag", "package:version", "install_command:pip", "example:002", "example:001", "public_symbol:slides_foss", "format:output.pptx", "public_symbol:slides_foss.export.saveformat", "example:003", "example:005", "example:006", "example:014", "public_symbol:slides_foss.shapecollection", "example:004", "public_symbol:slides_foss.baseportionformat", "public_symbol:slides_foss.paragraphformat", "example:012", "public_symbol:slides_foss.charts.charttype", "example:013", "public_symbol:slides_foss.slideshow.transitiontype", "public_symbol:slides_foss.animation", "example:007", "public_symbol:slides_foss.fillformat", "public_symbol:slides_foss.lineformat", "public_symbol:slides_foss.effectformat", "example:011", "example:009", "public_symbol:slides_foss.documentproperties", "public_symbol:slides_foss.notesslidemanager", "example:010", "public_symbol:slides_foss.commentauthorcollection", "public_symbol:slides_foss.hyperlink", "format:input.png", "format:input.pptx"]
REVISED_FACT_IDS = ["example:001", "example:002", "format:input.png", "format:output.pptx", "public_symbol:slides_foss", "public_symbol:slides_foss.export.saveformat", "example:003", "example:005", "example:006", "example:014", "public_symbol:slides_foss.shapecollection", "example:004", "public_symbol:slides_foss.baseportionformat", "public_symbol:slides_foss.paragraphformat", "example:012", "public_symbol:slides_foss.charts.charttype", "example:013", "public_symbol:slides_foss.slideshow.transitiontype", "public_symbol:slides_foss.animation", "example:007", "public_symbol:slides_foss.fillformat", "public_symbol:slides_foss.lineformat", "public_symbol:slides_foss.effectformat", "example:011", "example:009", "public_symbol:slides_foss.documentproperties", "public_symbol:slides_foss.notesslidemanager", "example:010", "public_symbol:slides_foss.commentauthorcollection", "public_symbol:slides_foss.hyperlink", "identity:ecosystem", "identity:family", "identity:platform", "identity:product-knowledge-refresh", "identity:repository", "identity:revision", "package:license", "package:name", "package:published_version", "package:python_requires", "package:registry_lag", "package:version", "format:input.pptx", "public_symbol:slides_foss.export.saveformat"]


def _unit(text: str, fact_ids: list[str], section: str = "opening", slot: str = "opening") -> dict:
    return {"section": section, "slot": slot, "text": text, "fact_ids": list(fact_ids)}


def test_fixture_is_the_real_shape() -> None:
    assert len(EXISTING_TEXT) <= MAX_UNIT_CHARS < len(REVISED_TEXT)


def test_an_overlong_revision_is_reverted_to_the_pre_coherence_unit() -> None:
    output = {"units": [_unit(REVISED_TEXT, REVISED_FACT_IDS)]}
    fixed = recover_coherence_overlong_units(
        output, existing_units=[_unit(EXISTING_TEXT, EXISTING_FACT_IDS)]
    )
    assert fixed is not None
    (unit,) = fixed["units"]
    assert unit["text"] == EXISTING_TEXT and unit["fact_ids"] == EXISTING_FACT_IDS


def test_a_revision_within_the_cap_is_left_alone() -> None:
    short = EXISTING_TEXT + " Added."
    output = {"units": [_unit(short, EXISTING_FACT_IDS)]}
    assert recover_coherence_overlong_units(
        output, existing_units=[_unit(EXISTING_TEXT, EXISTING_FACT_IDS)]
    ) is None
    assert output["units"][0]["text"] == short


def test_when_the_original_is_itself_over_the_cap_nothing_is_reverted() -> None:
    long_original = "x" * (MAX_UNIT_CHARS + 1)
    output = {"units": [_unit(REVISED_TEXT, REVISED_FACT_IDS)]}
    assert recover_coherence_overlong_units(
        output, existing_units=[_unit(long_original, EXISTING_FACT_IDS)]
    ) is None


def test_a_unit_with_no_pre_coherence_counterpart_is_not_touched() -> None:
    output = {"units": [_unit(REVISED_TEXT, REVISED_FACT_IDS, slot="new")]}
    assert recover_coherence_overlong_units(
        output, existing_units=[_unit(EXISTING_TEXT, EXISTING_FACT_IDS)]
    ) is None


def test_the_full_recovery_chain_includes_the_length_revert() -> None:
    from repo_presenter.core.facts import FactsDocument
    from repo_presenter.readme.composition.coherence import recover_coherence_regressions

    output = {"units": [_unit(REVISED_TEXT, REVISED_FACT_IDS)]}
    facts = FactsDocument("o/r", "0" * 40, ())
    fixed = recover_coherence_regressions(
        output, existing_units=[_unit(EXISTING_TEXT, EXISTING_FACT_IDS)], facts=facts, tasks=[]
    )
    assert fixed is not None and fixed["units"][0]["text"] == EXISTING_TEXT
