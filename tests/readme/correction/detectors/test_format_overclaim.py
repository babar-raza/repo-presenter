"""Format/capability OVER-claiming: a table row marks a format supported with nothing (or a
CONTRADICTED fact) confirming it -- the direction ``report_gaps`` does not cover (see
``migration/reuse-manifest.yaml``'s readme_correction/ entry, "known_gap"). Positive case, a
CONTRADICTED-fact case, and two negative controls (correctly-caveated and correctly-supported)."""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.format_overclaim import format_overclaim

TABLE_README = (
    "# P\n\n## Supported Formats\n\n"
    "| Format | Read |\n"
    "|---|---|\n"
    "| STL | ✅ |\n"
    "| OBJ | ✅ |\n"
    "| AMF | ❌ |\n"
)


def test_a_format_marked_supported_with_no_backing_fact_is_flagged(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(make_fact("format:stl", ".stl", evidence=(("io.py", None),)))
    result = format_overclaim(make_context(TABLE_README, facts))
    assert result.edits == ()  # this detector never edits
    (finding,) = result.findings
    assert finding.line == 8 and "'OBJ'" in finding.reason
    assert "no SUPPORTED format or capability fact confirms it" in finding.reason


def test_a_format_marked_supported_but_on_record_as_contradicted_cites_the_fact(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact("format:stl", ".stl", evidence=(("io.py", None),)),
        make_fact(
            "format:obj",
            ".obj",
            polarity="CONTRADICTED",
            evidence=(("io.py", "IOService.cs rejects .obj: no writer registered"),),
        ),
    )
    result = format_overclaim(make_context(TABLE_README, facts))
    (finding,) = result.findings
    assert finding.line == 8 and finding.fact_ids == ("format:obj",)
    assert "CONTRADICTED" in finding.reason


def test_a_format_backed_by_a_supported_fact_is_not_flagged(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "# P\n\n| Format | Read |\n|---|---|\n| STL | ✅ |\n"
    facts = make_facts(make_fact("format:stl", ".stl", evidence=(("io.py", None),)))
    assert format_overclaim(make_context(readme, facts)).findings == ()


def test_a_correctly_caveated_row_marked_unsupported_is_not_flagged(
    make_context: Any, make_facts: Any
) -> None:
    """The ❌ cell in ``TABLE_README``'s AMF row is a correctly-undocumented claim: no claim of
    support is made at all, so nothing is flagged for it."""
    facts = make_facts()  # no format:amf fact of any polarity
    result = format_overclaim(make_context(TABLE_README, facts))
    assert all("AMF" not in finding.text for finding in result.findings)


MERMAID_README = (
    "# P\n\n```mermaid\n"
    "flowchart TD\n"
    '  i1["An existing 3MF or RVM file"]\n'
    '  o1["3MF or RVM file"]\n'
    "```\n"
)


def test_a_mermaid_output_node_naming_an_unsupported_format_is_flagged(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """The real shape of the aspose-3d-foss/Aspose.3D-FOSS-for-.NET U3D/RVM/AMF/HTML5
    over-claim (2026-10-22): the claim lives in the Mermaid At a Glance diagram's Outputs node,
    never a table."""
    facts = make_facts(make_fact("format:output.3mf", ".3mf", evidence=(("io.cs", None),)))
    result = format_overclaim(make_context(MERMAID_README, facts))
    # RVM has no backing fact at all: flagged, once per node it appears in (both the Starting
    # Points and the Outputs node here). 3MF is backed by a SUPPORTED fact: never flagged, on
    # either node.
    reasons = [f.reason for f in result.findings]
    assert len(result.findings) == 2
    assert all("RVM" in reason for reason in reasons)
    assert not any("3MF" in reason for reason in reasons)


def test_a_vendor_and_product_suite_name_clarifying_a_real_format_is_not_flagged(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """Regression: the exact real false positive measured against aspose-3d-foss/
    Aspose.3D-FOSS-for-.NET's own live README (2026-10-22) -- 'AVEVA PDMS RVM' names a vendor
    and product suite clarifying what RVM is, not two more format claims."""
    readme = (
        '# P\n\n```mermaid\nflowchart TD\n'
        '  o3["3MF or RVM file (Microsoft 3MF, AVEVA PDMS RVM)"]\n```\n'
    )
    facts = make_facts()  # no backing facts for RVM, 3MF, AVEVA, or PDMS
    result = format_overclaim(make_context(readme, facts))
    reasons = [f.reason for f in result.findings]
    assert any("RVM" in reason for reason in reasons)  # the real format claim is still flagged
    assert not any("AVEVA" in reason or "PDMS" in reason for reason in reasons)


def test_a_content_encoding_qualifier_clarifying_a_real_format_is_not_flagged(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """Regression: the exact real false positive measured against aspose-3d-foss/
    Aspose.3D-FOSS-for-Java's own live README (2026-10-22) -- 'binary or ASCII' qualifies the
    STL claim right next to it (its content encoding), not a second format claim."""
    readme = (
        '# P\n\n```mermaid\nflowchart TD\n'
        '  i1["An existing STL file (binary or ASCII)"]\n```\n'
    )
    facts = make_facts(make_fact("format:input.stl", ".stl", evidence=(("io.java", None),)))
    result = format_overclaim(make_context(readme, facts))
    assert all("ASCII" not in finding.reason for finding in result.findings)


def test_an_ordinary_word_in_a_mermaid_node_is_not_mistaken_for_a_format(
    make_context: Any, make_facts: Any
) -> None:
    readme = '# P\n\n```mermaid\nflowchart TD\n  i1["An existing input file"]\n```\n'
    facts = make_facts()
    result = format_overclaim(make_context(readme, facts))
    assert result.findings == ()


def test_a_cross_edition_feature_comparison_table_is_not_mistaken_for_a_format_table(
    make_context: Any, make_facts: Any
) -> None:
    """Regression: the exact real false positive measured against aspose-slides-foss's own
    live .NET and Java READMEs (2026-10-22) -- a table comparing what each EDITION of the
    library supports ("| | .NET | Java | C++ | Python |"), with plain "yes"/"no" cells, is not
    a format-support table. Its row labels are feature sentences or Title-Case English words
    ("Create, open, round-trip, save", "Charts", "Themes", "Hyperlinks"), never the all-caps-
    acronym or dotted-extension shape a real format name has."""
    readme = (
        "# P\n\n## Choosing an edition\n\n"
        "| | .NET | Java | C++ | Python |\n"
        "|---|---|---|---|---|\n"
        "| Create, open, round-trip, save | yes | yes | yes | yes |\n"
        "| Charts | no | no | no | yes |\n"
        "| Themes | no | no | no | yes |\n"
        "| Hyperlinks | no | no | no | yes |\n"
    )
    facts = make_facts()  # no backing facts for any of these feature labels
    result = format_overclaim(make_context(readme, facts))
    assert result.findings == ()


def test_a_real_format_table_row_is_still_flagged_alongside_the_feature_table_fix(
    make_context: Any, make_facts: Any
) -> None:
    """Positive control, same pass: a genuine all-caps format label in an ordinary table row is
    unaffected by the cross-edition-table fix above."""
    readme = (
        "# P\n\n## Supported Formats\n\n"
        "| Format | Read |\n"
        "|---|---|\n"
        "| PPTX | yes |\n"
    )
    facts = make_facts()
    result = format_overclaim(make_context(readme, facts))
    (finding,) = result.findings
    assert "'PPTX'" in finding.reason


def test_an_api_reference_row_whose_prose_merely_contains_the_word_supported_is_not_flagged(
    make_context: Any, make_facts: Any
) -> None:
    """Regression: measured live against aspose-3d-foss/Aspose.3D-FOSS-for-Python's real README
    (2026-10-22) -- an API Reference table row whose DESCRIPTION cell happens to contain the word
    "supported" in prose (e.g. "...returns true if the specified file format is supported by this
    importer.") is not a format/capability support-marker row, and must not be flagged. The
    marker check requires the cell's entire (markup-stripped) content to be a truthy token, not a
    substring match anywhere in an arbitrary-length prose cell."""
    readme = (
        "# P\n\n### Core API\n\n| Class | Description |\n|---|---|\n"
        "| `ColladaImporter` | ColladaImporter.supports_format returns true if the specified "
        "file format is supported by this importer. |\n"
    )
    facts = make_facts()  # no format/capability facts at all
    result = format_overclaim(make_context(readme, facts))
    assert result.findings == ()


# --- evidence of absence ------------------------------------------------------------------------
#
# 53 of the 65 format over-claim findings behind the hosted Lane L refusals came from repositories
# whose extracted facts hold no format or capability at all (Barcode, Email-.Net, Imaging, PDF-Cpp,
# PDF-TypeScript, Slides-Java, TeX): an extractor gap read as a defect, which refuses the whole
# candidate as `lane_l_unrepaired_defect`. A claim is a defect when a CONTRADICTED fact says so, or
# when the facts hold a real picture of the formats and this one is not in it (3D-.NET: sixteen
# SUPPORTED formats and not U3D / RVM / AMF / HTML5, the owner's 2026-10-20 ruling).

from repo_presenter.readme.correction.report import is_defect


def test_a_claim_in_a_repository_with_no_format_facts_is_reported_but_is_not_a_defect(
    make_context: Any, make_facts: Any
) -> None:
    result = format_overclaim(make_context(TABLE_README, make_facts()))
    assert result.findings, "the claim is still reported for review"
    assert all(f.report_only_reason == "NO_EVIDENCE_OF_ABSENCE" for f in result.findings)
    assert not any(is_defect(f) for f in result.findings)


def test_a_claim_matching_only_an_unresolved_fact_is_not_a_defect(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact("format:stl", ".stl", evidence=(("io.py", None),)),
        make_fact("format:obj", ".obj", polarity="UNRESOLVED", evidence=(("io.py", None),)),
    )
    result = format_overclaim(make_context(TABLE_README, facts))
    obj = next(f for f in result.findings if f.line == 8)
    assert obj.fact_ids == ("format:obj",) and not is_defect(obj)


def test_a_claim_absent_from_a_real_picture_of_the_formats_is_still_a_defect(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """The negative control: the repository has SUPPORTED formats and OBJ is not among them."""
    facts = make_facts(make_fact("format:stl", ".stl", evidence=(("io.py", None),)))
    (finding,) = format_overclaim(make_context(TABLE_README, facts)).findings
    assert finding.line == 8 and is_defect(finding) and not finding.report_only_reason


def test_a_contradicted_claim_is_a_defect_even_with_no_other_format_facts(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact("format:obj", ".obj", polarity="CONTRADICTED", evidence=(("io.py", "rejected"),))
    )
    findings = format_overclaim(make_context(TABLE_README, facts)).findings
    contradicted = next(f for f in findings if f.fact_ids == ("format:obj",))
    assert is_defect(contradicted)
