"""A bare colon lead-in kept while the block it introduces is superseded goes with its block.

Aspose.Cells-FOSS-for-Java, hosted Lane R run 43419171411: BC-07 "inherited_unit:014.paragraph is
kept as written but ends with a colon but nothing follows it before the next heading: 'Gradle
(Groovy DSL):'". The S4 repair of the lead-in alone kept it VERIFIED_PRESERVE (a patch of a lead-in
cannot move the block after it), and the C2 restore fix (a *restored* lead-in brings its block)
does not reach a lead-in S4 itself kept. ``coordinate_neighbor_promises`` -- run on every cascade
pass after the batches merge -- settled a kept lead-in against an omitted, deferred, kept or
verified-example block, but not against a block superseded by a section's own content.
"""

from __future__ import annotations

from repo_presenter.readme.reconciliation.dispositions import (
    coordinate_neighbor_promises,
)
from repo_presenter.readme.validation.supersession import exempt
from tests.readme.reconciliation.test_placement_errors import _entry, _facts, _unit

LEAD = "inherited_unit:014.paragraph"
BLOCK = "inherited_unit:015.code_block"
GRADLE = "```groovy\nimplementation 'org.aspose:aspose-widget-foss:26.7.0'\n```"


def _settle(lead_text: str) -> dict[str, object]:
    facts = _facts(_unit(LEAD, lead_text), _unit(BLOCK, GRADLE))
    document = {
        "dispositions": [
            _entry(LEAD, "VERIFIED_PRESERVE", "quick_start", rationale="a label for the snippet"),
            _entry(
                BLOCK,
                "SUPERSEDE_REDUNDANT",
                "installation",
                fact_ids=["package:name"],
                rationale="the Installation section renders the dependency",
            ),
        ]
    }
    coordinate_neighbor_promises(document, facts)
    return next(e for e in document["dispositions"] if e["unit_id"] == LEAD)


def test_a_kept_label_whose_block_is_superseded_is_superseded_with_it() -> None:
    lead = _settle("Gradle (Groovy DSL):")
    assert lead["disposition"] == "SUPERSEDE_REDUNDANT"
    assert lead["destination_section"] == "installation"
    # BC-05 does not hold a superseded lead-in to stating its own words elsewhere.
    assert exempt(LEAD, "Gradle (Groovy DSL):", str(lead["rationale"]))


def test_a_lead_in_that_makes_a_claim_is_left_for_its_own_disposition() -> None:
    lead = _settle("Requires Gradle 8 and is published to Maven Central:")
    assert lead["disposition"] == "VERIFIED_PRESERVE"
    assert lead["destination_section"] == "quick_start"
