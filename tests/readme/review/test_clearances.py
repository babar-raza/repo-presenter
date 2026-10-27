"""V1/V2: the closed clearance catalogue (plan D3). Each clearance has positive and negative cases;
every negative is a way a finding could be wrongly dismissed, so it must stay BLOCKING."""

from __future__ import annotations

from dataclasses import replace

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.clearances import (
    CLEARANCES,
    ClearanceContext,
    absence_present,
    absence_unsourced,
    apply_clearances,
    names_supported,
    omission_present,
)
from repo_presenter.readme.review.findings import (
    CLEARANCE_NAMES,
    Clearance,
    Finding,
    OmissionClaim,
    _seal_clearance,
)
from tests.readme.review.review_support import (
    CANDIDATE,
    FACTS,
    context,
    llm,
    rule_finding,
)


def test_the_catalogue_is_exactly_the_four_clearances_plan_d3_lists() -> None:
    assert set(CLEARANCES) == {
        "absence_present",
        "absence_unsourced",
        "names_supported",
        "omission_present",
    }
    assert tuple(CLEARANCES) == CLEARANCE_NAMES


# ---------------------------------------------------------------------------
# absence_present
# ---------------------------------------------------------------------------


def test_absence_present_clears_when_every_string_is_in_the_named_section() -> None:
    finding = llm("absence", absent=("SvgExporter", "Widget.render"))
    proof = absence_present(finding, context())
    assert proof is not None and proof.name == "absence_present"
    cleared = apply_clearances(finding, context())
    assert cleared.status == "CLEARED" and cleared.clearance == proof


def test_absence_present_searches_only_the_named_section() -> None:
    """`pip install aspose-widget-foss` is in Installation, not in Key Capabilities: text present
    elsewhere does not disprove a gap in the section the finding names."""
    finding = llm("absence", absent=("pip install aspose-widget-foss",))
    assert absence_present(finding, context()) is None
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_partly_disproved_absence_finding_stays_blocking() -> None:
    finding = llm("absence", absent=("SvgExporter", "PluginHost"))
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_an_absent_string_the_finding_quotes_itself_is_not_a_claim_of_absence() -> None:
    """Measured in the old repository: Words-.NET F03..F08 listed in `absent` the very text they
    called wrong and quoted it. Clearing them would dismiss a real wrong-text finding."""
    finding = llm(
        "absence",
        absent=("SvgExporter",),
        quote="Exports SVG through the SvgExporter class.",
    )
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_string_too_short_to_tell_from_coincidence_never_clears() -> None:
    finding = llm("absence", absent=("it",))
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_string_must_match_as_a_whole_token_and_in_case() -> None:
    assert (
        apply_clearances(llm("absence", absent=("Widge",)), context()).status
        == "BLOCKING"
    )
    assert (
        apply_clearances(llm("absence", absent=("svgexporter",)), context()).status
        == "BLOCKING"
    )


def test_an_unlocatable_section_never_clears_by_searching_the_whole_document() -> None:
    finding = llm(
        "absence", section_id="enterprise_relationship", absent=("SvgExporter",)
    )
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_structure_finding_searches_the_whole_document() -> None:
    finding = llm(
        "absence", section_id="structure", absent=("pip install aspose-widget-foss",)
    )
    assert apply_clearances(finding, context()).status == "CLEARED"


def test_an_absence_clearance_needs_the_finding_to_fill_only_the_absent_field() -> None:
    both = llm("absence", absent=("SvgExporter",), unsupported_names=("Widget",))
    assert apply_clearances(both, context()).status == "BLOCKING"


# ---------------------------------------------------------------------------
# absence_unsourced
# ---------------------------------------------------------------------------


def test_absence_unsourced_clears_a_demand_for_text_nobody_wrote() -> None:
    finding = llm("absence", absent=("quantum teleport mode",))
    proof = absence_unsourced(finding, context())
    assert proof is not None and proof.name == "absence_unsourced"
    assert apply_clearances(finding, context()).status == "CLEARED"


def test_absence_unsourced_keeps_a_real_omission_from_the_original_readme() -> None:
    """PluginHost is in the original README and not in the candidate: a true omission."""
    finding = llm("absence", absent=("PluginHost",))
    assert absence_unsourced(finding, context()) is None
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_absence_unsourced_keeps_text_that_only_a_fact_value_carries() -> None:
    finding = llm("absence", absent=("SVG export",))
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_absence_unsourced_keeps_a_bundle_with_one_real_gap() -> None:
    finding = llm("absence", absent=("quantum teleport mode", "widgetctl"))
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_mix_of_present_and_unsourced_strings_is_in_neither_clearance() -> None:
    """The closed catalogue has no combined 'settled' ruling: a mixed bundle keeps blocking."""
    finding = llm("absence", absent=("SvgExporter", "quantum teleport mode"))
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_absence_unsourced_matches_loosely_so_a_case_change_cannot_clear() -> None:
    finding = llm("absence", absent=("pluginhost",))
    assert apply_clearances(finding, context()).status == "BLOCKING"


# ---------------------------------------------------------------------------
# names_supported
# ---------------------------------------------------------------------------


def test_names_supported_clears_when_every_name_equals_a_supported_fact_value() -> None:
    finding = llm(
        "name_denial", unsupported_names=("Widget", "`SvgExporter`", "Widget()")
    )
    proof = names_supported(finding, context())
    assert proof is not None and proof.name == "names_supported"
    assert any("public_symbol:widget" in line for line in proof.evidence)


def test_names_supported_accepts_the_package_name() -> None:
    finding = llm("name_denial", unsupported_names=("aspose-widget-foss",))
    assert apply_clearances(finding, context()).status == "CLEARED"


def test_one_unsupported_name_keeps_the_whole_denial_standing() -> None:
    finding = llm("name_denial", unsupported_names=("Widget", "Gadget"))
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_name_only_a_contradicted_fact_carries_is_not_supported() -> None:
    finding = llm("name_denial", unsupported_names=("LegacyExport",))
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_multi_word_entry_is_a_claim_not_a_name() -> None:
    finding = llm("name_denial", unsupported_names=("Widget class",))
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_denial_that_cites_excluded_evidence_is_not_cleared() -> None:
    finding = llm(
        "name_denial",
        unsupported_names=("Widget",),
        fact_ids=("public_symbol:legacyexport",),
    )
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_only_name_like_facts_support_a_name() -> None:
    finding = llm("name_denial", unsupported_names=("26.9.0",))
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_bare_name_is_not_resolved_by_the_tail_of_a_dotted_symbol() -> None:
    """The old repository resolved `Modified` through `Workbook.Modified`. The closed catalogue
    says 'equals': a member of the wrong type must not clear."""
    facts = FactsDocument(
        "org/widget",
        "a" * 40,
        (
            Fact(
                "public_symbol:pkg.widget",
                "public_symbol",
                "pkg.Widget",
                (Evidence("a"),),
            ),
        ),
    )
    finding = llm("name_denial", unsupported_names=("Widget",))
    assert (
        apply_clearances(finding, ClearanceContext(CANDIDATE, "", facts)).status
        == "BLOCKING"
    )
    exact = llm("name_denial", unsupported_names=("pkg.Widget",))
    assert (
        apply_clearances(exact, ClearanceContext(CANDIDATE, "", facts)).status
        == "CLEARED"
    )


# ---------------------------------------------------------------------------
# omission_present
# ---------------------------------------------------------------------------


def test_omission_present_clears_when_the_section_renders_every_id_and_phrase() -> None:
    finding = llm(
        "omission",
        section_id="quick_start",
        omission=("quick_start", ("example:001",), ()),
    )
    proof = omission_present(finding, context())
    assert proof is not None and proof.name == "omission_present"
    phrase = llm(
        "omission",
        section_id="api_reference",
        omission=("api_reference", (), ("Writes SVG.",)),
    )
    assert apply_clearances(phrase, context()).status == "CLEARED"


def test_a_partly_present_omission_stays_blocking() -> None:
    finding = llm(
        "omission",
        section_id="quick_start",
        omission=("quick_start", ("example:001",), ("PluginHost",)),
    )
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_an_id_rendered_by_a_different_section_does_not_clear() -> None:
    finding = llm(
        "omission",
        section_id="key_capabilities",
        omission=("key_capabilities", ("example:001",), ()),
    )
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_non_supported_id_is_never_cleared_as_present_or_unrestorable() -> None:
    finding = llm(
        "omission",
        section_id="quick_start",
        omission=("quick_start", ("example:002",), ()),
    )
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_non_supported_id_does_not_clear_even_when_its_text_is_in_the_section() -> (
    None
):
    """A CONTRADICTED example may not be stated; if its text is on the page anyway, the finding
    is a reviewer defect for the contract to refuse, never a clearance."""
    candidate = CANDIDATE.replace('Widget().render("out.png")', "Widget().render_pdf()")
    finding = llm(
        "omission",
        section_id="quick_start",
        omission=("quick_start", ("example:002",), ()),
    )
    assert apply_clearances(finding, context(candidate)).status == "BLOCKING"


def test_an_omission_naming_another_section_or_nothing_does_not_clear() -> None:
    mismatch = llm(
        "omission",
        section_id="quick_start",
        omission=("api_reference", ("example:001",), ()),
    )
    empty = llm("omission", section_id="quick_start", omission=("quick_start", (), ()))
    assert apply_clearances(mismatch, context()).status == "BLOCKING"
    assert apply_clearances(empty, context()).status == "BLOCKING"


# ---------------------------------------------------------------------------
# what is deliberately NOT a clearance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "claim_kind", ["contradiction", "unsupported_claim", "quality"]
)
def test_a_quote_containing_a_supported_fact_value_clears_nothing(
    claim_kind: str,
) -> None:
    """The old repository's measured incident (27 of 30 real REJECTs folded to ACCEPT): the quote
    carries the literal value of a SUPPORTED fact the finding cites. That is not a clearance."""
    finding = llm(
        claim_kind,
        quote="Renders a Widget to PNG with Widget.render.",
        fact_ids=("public_symbol:widget", "format:png"),
    )
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_name_denial_whose_quote_carries_a_supported_name_still_needs_every_name() -> (
    None
):
    finding = llm(
        "name_denial",
        quote="Renders a Widget to PNG with Widget.render.",
        unsupported_names=("Widget.render",),
        fact_ids=("public_symbol:widget",),
    )
    assert apply_clearances(finding, context()).status == "BLOCKING"


def test_a_non_typed_finding_that_fills_a_typed_field_is_not_cleared() -> None:
    """A quality complaint dressed as an absence must not be dismissed."""
    mislabelled = llm("quality", absent=("SvgExporter",))
    assert apply_clearances(mislabelled, context()).status == "BLOCKING"
    assert absence_present(mislabelled, context()) is None


def test_a_deterministic_finding_is_never_cleared() -> None:
    finding = rule_finding()
    assert apply_clearances(finding, context()) is finding


def test_an_already_cleared_or_unmatched_finding_is_returned_unchanged() -> None:
    finding = llm("quality")
    assert apply_clearances(finding, context()) is finding


# ---------------------------------------------------------------------------
# the proof object cannot be forged
# ---------------------------------------------------------------------------


def _cleared() -> Finding:
    return apply_clearances(llm("absence", absent=("SvgExporter",)), context())


def test_a_cleared_finding_needs_a_clearance() -> None:
    with pytest.raises(ValueError, match="cleared only by"):
        replace(_cleared(), clearance=None)


def test_a_blocking_finding_cannot_carry_a_clearance() -> None:
    cleared = _cleared()
    with pytest.raises(ValueError, match="BLOCKING but carries a clearance"):
        replace(cleared, status="BLOCKING")


def test_a_clearance_from_the_wrong_catalogue_entry_is_refused() -> None:
    cleared = _cleared()
    assert cleared.clearance is not None
    wrong = replace(cleared.clearance, name="names_supported")
    with pytest.raises(ValueError, match="cleared only by"):
        replace(cleared, clearance=wrong)


def test_a_clearance_with_edited_evidence_or_digest_is_refused() -> None:
    cleared = _cleared()
    assert cleared.clearance is not None
    with pytest.raises(ValueError, match="does not prove this finding"):
        replace(cleared, clearance=replace(cleared.clearance, evidence=("trust me",)))
    with pytest.raises(ValueError, match="does not prove this finding"):
        replace(cleared, clearance=replace(cleared.clearance, digest="0" * 64))


def test_a_valid_clearance_does_not_transfer_to_another_finding() -> None:
    cleared = _cleared()
    other = llm("absence", absent=("PluginHost",))
    with pytest.raises(ValueError, match="does not prove this finding"):
        replace(other, status="CLEARED", clearance=cleared.clearance)


def test_the_strongest_forgery_still_fails_for_a_never_clearable_claim() -> None:
    finding = llm("contradiction", quote="Exports SVG through the SvgExporter class.")
    proof = _seal_clearance("absence_present", finding, ("forged",))
    with pytest.raises(ValueError, match="never clearable"):
        replace(finding, status="CLEARED", clearance=proof)


def test_a_deterministic_finding_cannot_be_constructed_cleared() -> None:
    forged = Clearance("absence_present", ("x",), "0" * 64)
    with pytest.raises(ValueError, match="cannot be CLEARED"):
        Finding(
            rule="claim_contradiction",
            source="deterministic",
            message="m",
            status="CLEARED",
            clearance=forged,
        )


def test_a_tampered_record_does_not_load_as_cleared() -> None:
    record = _cleared().to_record()
    assert Finding.from_record(record) == _cleared()
    record["clearance"]["evidence"] = ["tampered"]
    with pytest.raises(ValueError, match="does not prove this finding"):
        Finding.from_record(record)
    record = llm("quality").to_record()
    record["status"] = "CLEARED"
    with pytest.raises(ValueError):
        Finding.from_record(record)


def test_omission_claims_round_trip_through_a_record() -> None:
    finding = llm(
        "omission", omission=("key_capabilities", ("example:001",), ("x y z",))
    )
    assert Finding.from_record(finding.to_record()) == finding
    assert finding.omission == OmissionClaim(
        "key_capabilities", ("example:001",), ("x y z",)
    )
    assert FACTS.facts  # the shared facts document is non-empty
