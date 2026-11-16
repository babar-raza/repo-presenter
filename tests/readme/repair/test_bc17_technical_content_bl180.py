"""BL-180: the top Lane R failure class ``BC-17|inherited_unit|technical_content``, fixed at its roots.

Three real shapes from the hosted failure records (``refs/repository-presenter-state/failures``),
each beside a negative control; unit texts are verbatim from the facts of those repositories:

* **A stub row withheld on evidence** (Aspose.3D-FOSS-for-Python, hosted Lane R run 43647239376).
  ``060.table``'s FbxExporter row ("FbxExporter.save saves the given Scene ...") is left out of the
  kept table's printable form (``surface_claims.without_stub_rows``: the maintainers' own limitation
  says ``FbxExporter.save()`` raises ``NotImplementedError``). BC-17 judged the RAW unit text, so
  it named ``060.table`` as losing ``FbxExporter.save()`` while the table was already kept: an
  unrepairable demand. The unit that really prints it, the limitation list, is still held to it.
* **A resource-links list restored into Scope** (Aspose.Slides-FOSS-for-Java run 43667477825
  ``084.list``; Slides .NET 43654917831 ``083.list``; Slides C++ 43664912460's docs list). The
  restore re-homed a DEFER_UNRESOLVED links list to the "nearest" printable section, Scope and
  Limitations, BC-05's section fit refused it, the restore was rolled back and the links stayed
  lost. It now keeps such a list in Documentation and Resources, as S4 does (BL-004), and the
  planning backstop owes its links to that section's lines.
* **A kept list that embeds an unverified example** (Aspose.Slides-FOSS-for-Cpp run 43664912460
  ``102.list``). S4 restated it (BC-03 forbids the ``pres.save(... SaveFormat::PDF)`` example)
  and the restatement lost eight API identifiers. Kept as written again, it prints every word but
  that one block.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.planning import missing_kept_list_links
from repo_presenter.readme.parity_gate import LANE_R, Accounting, SealedCandidate, content_losses
from repo_presenter.readme.reconciliation.destinations import holdable_sections
from repo_presenter.readme.reconciliation.dispositions import RECOVERED_FENCE_RATIONALE
from repo_presenter.readme.repair.restore_units import restore_lost_units
from repo_presenter.readme.validation.surface_claims import (
    fence_withheld_form,
    without_example_fences,
)

_EV = (Evidence("README.md", "lines 1-1"),)


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", **attributes: str) -> Fact:
    return Fact(fact_id, kind, value, _EV, polarity, 1.0, attributes or None)


def _rows(document: FactsDocument) -> tuple[dict, ...]:
    return tuple(
        {
            "id": f.id,
            "kind": f.kind,
            "value": f.value,
            "polarity": f.polarity,
            "attributes": f.attributes,
            "evidence": [{"path": e.path, "detail": e.detail} for e in f.evidence],
        }
        for f in document.facts
    )


# --- 1. a stub row withheld on evidence (3D Python 060.table) ---------------------------------

THREED = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
TABLE = (
    "| Class | Description |\n"
    "|---|---|\n"
    "| `BasicLoadOptions` | Simple LoadOptions subclass for basic loading options. |\n"
    "| `FbxExporter` | FbxExporter.save saves the given Scene to a file path using specified "
    "FbxSaveOptions. |\n"
    "| `FbxImporter` | FbxImporter parses ASCII and binary FBX streams. |\n"
    "| `Scene` | The root container of a 3D scene. |"
)
LIMITS = (
    "- FBX support is experimental. `FbxExporter.save()`/`save_to_stream()`\n"
    "  both raise `NotImplementedError` outright, so FBX is import-only at best."
)
BENCHMARK = (
    "# Aspose.3D FOSS for Python\n\n## API Reference\n\n" + TABLE + "\n\n"
    "## Scope and Limitations\n\n" + LIMITS + "\n"
)


def _threed_facts() -> FactsDocument:
    symbols = [
        ("public_symbol:basicloadoptions", "aspose.threed.formats.BasicLoadOptions", "class"),
        ("public_symbol:fbxexporter", "aspose.threed.formats.FbxExporter", "class"),
        ("public_symbol:fbxexporter.save", "aspose.threed.formats.FbxExporter.save", "method"),
        ("public_symbol:fbximporter", "aspose.threed.formats.FbxImporter", "class"),
        ("public_symbol:scene", "aspose.threed.Scene", "class"),
    ]
    return FactsDocument(
        THREED,
        "65b1f577c0f16d0d9112bb6c1153d3024543ac02",
        (
            *(_fact(i, "public_symbol", v, symbol_kind=k) for i, v, k in symbols),
            _fact("inherited_unit:060.table", "inherited_unit", TABLE,
                  section="Aspose.3D FOSS for Python > API Reference"),
            _fact("inherited_unit:067.list", "inherited_unit", LIMITS,
                  section="Aspose.3D FOSS for Python > Scope and Limitations"),
        ),
    )


def _threed_losses(limits_row: dict) -> list:
    document = _threed_facts()
    dispositions = (
        {"unit_id": "inherited_unit:060.table", "disposition": "PRESERVE_ATTRIBUTED",
         "destination_section": "api_reference", "fact_ids": []},
        limits_row,
    )
    # The candidate prints neither the stub row (withheld) nor the limitation list.
    readme = "# Aspose.3D FOSS for Python\n\n## API Reference\n\n| `Scene` | The root. |\n"
    candidate = SealedCandidate(LANE_R, readme, _rows(document), dispositions, document=document)
    return [loss for loss in content_losses(candidate, BENCHMARK) if "FbxExporter" in loss.item]


def test_a_stub_row_withheld_on_evidence_does_not_hold_the_identifier() -> None:
    accounting = Accounting(
        SealedCandidate(LANE_R, "", _rows(_threed_facts()), (), document=_threed_facts())
    )
    printed = accounting.printed_form("inherited_unit:060.table")
    assert printed is not None and "FbxExporter.save saves" not in printed
    assert accounting.withheld_on_evidence("inherited_unit:060.table", "FbxExporter.save()")
    # The limitation list prints it: it is not withheld there.
    assert not accounting.withheld_on_evidence("inherited_unit:067.list", "FbxExporter.save()")


def test_the_hosted_shape_no_longer_blames_the_kept_table() -> None:
    # Hosted run 43647239376: the limitation list's disposition accounts for its absence, and the
    # kept table was named anyway.
    losses = _threed_losses(
        {"unit_id": "inherited_unit:067.list", "disposition": "OMIT_UNSUPPORTED",
         "destination_section": None, "fact_ids": [], "rationale": "contradicted by the source"}
    )
    assert losses == []


def test_negative_control_a_lost_limitation_list_is_still_a_loss_and_names_it() -> None:
    losses = _threed_losses(
        {"unit_id": "inherited_unit:067.list", "disposition": "SUPERSEDE_REDUNDANT",
         "destination_section": "scope_limitations", "fact_ids": []}
    )
    assert losses and {loss.units for loss in losses} == {("inherited_unit:067.list",)}


def test_without_a_facts_document_the_raw_text_judgement_stands() -> None:
    document = _threed_facts()
    candidate = SealedCandidate(LANE_R, "", _rows(document), ())
    assert not Accounting(candidate).withheld_on_evidence(
        "inherited_unit:060.table", "FbxExporter.save()"
    )


# --- 2. a resource-links list is restored into Documentation and Resources ---------------------

JAVA = "aspose-slides-foss/Aspose.Slides-FOSS-for-Java"
# inherited_unit:084.list, verbatim (README.md 'Documentation & Resources > Choosing an Edition').
EDITIONS = (
    "- [Aspose.Slides FOSS for .NET](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET)\n"
    "- [Aspose.Slides FOSS for C++](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp)\n"
    "- [Aspose.Slides FOSS for Python](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python)"
)


def _java_facts(polarity: str = "SUPPORTED") -> FactsDocument:
    return FactsDocument(
        JAVA,
        "620a2614418854b4a18966a361e6907ddc88c7cb",
        (
            _fact("identity:ecosystem", "identity", "java"),
            _fact("identity:repository", "identity", JAVA),
            _fact("link_target:035", "link_target",
                  "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET", polarity),
            _fact("link_target:036", "link_target",
                  "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp", polarity),
            _fact("link_target:037", "link_target",
                  "https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python", polarity),
            _fact("inherited_unit:084.list", "inherited_unit", EDITIONS,
                  section="Aspose.Slides FOSS for Java > Documentation & Resources > Choosing an Edition"),
        ),
    )


def _restore_editions(document: FactsDocument) -> tuple[dict, list]:
    holdable = (
        "key_capabilities", "quick_start", "api_reference", "documentation_resources",
        "scope_limitations", "development_testing",
    )
    dispositions = {
        "dispositions": [
            {"unit_id": "inherited_unit:084.list", "disposition": "DEFER_UNRESOLVED",
             "destination_section": None, "fact_ids": []}
        ]
    }
    return restore_lost_units(dispositions, document, ["inherited_unit:084.list"], holdable)


def test_a_deferred_links_list_is_restored_into_documentation_and_resources() -> None:
    document = _java_facts()
    output, changes = _restore_editions(document)
    assert changes and changes[0]["now"].endswith("-> documentation_resources")
    owed = missing_kept_list_links({"links": []}, document, output)
    assert {link["link_fact_id"] for link in owed} == {
        "link_target:035", "link_target:036", "link_target:037"
    }
    assert {link["section_id"] for link in owed} == {"documentation_resources"}


def test_negative_control_a_list_whose_links_are_not_assignable_is_not_sent_there() -> None:
    # Its links are not SUPPORTED, so Documentation and Resources cannot print it: the old
    # nearest-section rule applies, exactly as before.
    _output, changes = _restore_editions(_java_facts("CONTRADICTED"))
    assert not changes or not changes[0]["now"].endswith("-> documentation_resources")


def test_holdable_sections_offer_documentation_and_resources() -> None:
    # The restore only targets the section when the repository's shell holds it.
    assert "documentation_resources" in holdable_sections(_java_facts())


# --- 3. a kept list that embeds an unverified example prints without it ------------------------

SLIDES_CPP = (
    "- **Save formats**: `save()` writes six Office Open XML presentation formats. Every other\n"
    "  `SaveFormat` value throws `std::invalid_argument` and nothing to indicate why:\n"
    "\n"
    "  ```cpp\n"
    "  pres.save(\"report.pdf\", SaveFormat::PDF);  // throws std::invalid_argument\n"
    "  ```\n"
    "\n"
    "  The format decides the content type.\n"
    "- **Placeholder geometry**: `Shape::x()`/`y()`/`width()`/`height()` resolve placeholder\n"
    "  inheritance. Read inherited geometry with `Shape::get_inherited_frame()`."
)


def _cpp_facts() -> FactsDocument:
    return FactsDocument(
        "aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp",
        "469ce77a07b988c49deb930632b8276c89ec6b66",
        (_fact("identity:ecosystem", "identity", "cpp"),
         _fact("inherited_unit:102.list", "inherited_unit", SLIDES_CPP)),
    )


def test_the_example_fence_is_left_out_and_every_word_around_it_kept() -> None:
    printed = without_example_fences(SLIDES_CPP, {"cpp"})
    assert "```" not in printed and "pres.save" not in printed
    assert "nothing to indicate why.\n\n  The format decides the content type." in printed
    for identifier in ("Shape::x()", "height()", "Shape::get_inherited_frame()", "SaveFormat"):
        assert identifier in printed


def test_only_a_kept_unit_carrying_the_fence_marker_is_printed_without_it() -> None:
    from repo_presenter.extractors.platforms.registry import plugin_for

    plugin_for("cpp")
    facts = _cpp_facts()
    unit = "inherited_unit:102.list"
    marked = {"disposition": "PRESERVE_ATTRIBUTED", "rationale": RECOVERED_FENCE_RATIONALE + "Kept."}
    assert "```cpp" not in fence_withheld_form(unit, SLIDES_CPP, marked, facts)
    # Negative controls: no marker, or a disposition that is not kept as written.
    plain = {"disposition": "PRESERVE_ATTRIBUTED", "rationale": "Kept."}
    rewrite = {"disposition": "VERIFIED_REWRITE", "rationale": RECOVERED_FENCE_RATIONALE}
    assert fence_withheld_form(unit, SLIDES_CPP, plain, facts) == SLIDES_CPP
    assert fence_withheld_form(unit, SLIDES_CPP, rewrite, facts) == SLIDES_CPP
    assert fence_withheld_form(unit, SLIDES_CPP, None, facts) == SLIDES_CPP


def test_ambiguous_multiple_examples_are_preserved_for_downstream_checks() -> None:
    from repo_presenter.extractors.platforms.registry import plugin_for

    plugin_for("cpp")
    text = 'Verified example:\n```cpp\nverified();\n```\nUnverified example:\n```cpp\nunverified();\n```\n'
    marked = {"disposition": "PRESERVE_ATTRIBUTED", "rationale": RECOVERED_FENCE_RATIONALE}
    assert without_example_fences(text, {"cpp"}) == text
    assert fence_withheld_form("inherited_unit:102.list", text, marked, _cpp_facts()) == text


def test_restore_keeps_the_marker_so_the_unit_prints_without_the_example() -> None:
    from repo_presenter.extractors.platforms.registry import plugin_for

    plugin_for("cpp")
    facts = _cpp_facts()
    dispositions = {
        "dispositions": [
            {"unit_id": "inherited_unit:102.list", "disposition": "VERIFIED_REWRITE",
             "destination_section": "scope_limitations", "fact_ids": [],
             "rationale": RECOVERED_FENCE_RATIONALE + "Restated."}
        ]
    }
    output, changes = restore_lost_units(
        dispositions, facts, ["inherited_unit:102.list"], ("scope_limitations",)
    )
    row = output["dispositions"][0]
    assert changes and row["disposition"] == "PRESERVE_ATTRIBUTED"
    printed = fence_withheld_form("inherited_unit:102.list", SLIDES_CPP, row, facts)
    assert "pres.save" not in printed and "Shape::get_inherited_frame()" in printed
