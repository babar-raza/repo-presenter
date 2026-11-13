"""A maintainers' section the README owes is carried after the zero-call restore (BC-17, R2/R14).

Two real shapes, each held beside a negative control:

* **A dead link inside the kept unit** (Aspose.OMR-FOSS-for-Python, hosted Lane R run 43430687401).
  The README links its own files through ``github.com/omr-python-for-foss/omr-python-for-foss/...``,
  a repository that answers 404, so each such ``link_target`` fact is CONTRADICTED. S4 folded every
  unit carrying one to ``VERIFIED_REWRITE`` (losing 'Developing in VS Code', 'Two ways to author a
  form', 'How recognition works', 'Known limitations / deviations'); the restore kept them verbatim,
  BC-06 refused the dead target, and the rollback lost the sections again ("1 unit(s) restored but
  blocking still fails"). Now the kept unit prints each dead link as its label, S4 keeps it, and the
  reviewer accounts for the dead target on the same fact BC-17 does.
* **A restored unit dropped whole as overlap** (Aspose.Cells-FOSS-for-Go Lane R seal fbe7fa729705).
  ``073.list`` (h2 'Constraints') was restored ``VERIFIED_PRESERVE`` with the rewrite's fact IDs, and
  placement dropped it as overlap with those facts, so BC-17 still reported the section lost.

The unit texts are verbatim from the facts runs of those repositories.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.placement import RESTORED_RATIONALE, placements
from repo_presenter.readme.evidence.facts.links import extract_links
from repo_presenter.readme.parity_gate import LANE_R, SealedCandidate, content_losses
from repo_presenter.readme.reconciliation.dispositions import normalize
from repo_presenter.readme.repair.restore_units import restore_lost_units
from repo_presenter.readme.review.independent_reviewer import live_readme_loss_rule
from repo_presenter.readme.validation.surface_claims import (
    kept_unit_form,
    without_contradicted_links,
)

OMR = "aspose-omr-foss/Aspose.OMR-FOSS-for-Python"
DEAD = "https://github.com/omr-python-for-foss/omr-python-for-foss/blob/main/examples/final-exam.txt"
# inherited_unit:022.paragraph, verbatim (README.md lines 103-107, under 'Two ways to author a form').
TWO_WAYS = (
    "**1. Text markup (the DSL).** Pass a `.txt` file, a `list[str]` of lines, or a binary\n"
    "stream to `Generate`. Markup tokens are byte-identical to Aspose's. See\n"
    f"[`examples/final-exam.txt`]({DEAD}). Attribute lines must begin with\n"
    "a real **TAB**. (Note: `#` begins a **comment** line, matching the reference sample;\n"
    "author choiceboxes with `?choicebox=` + `?option=` or inline `(char) Answer` lines.)"
)
LIVE = (
    "# omr-python-for-foss\n\n"
    "A FOSS Python OMR library.\n\n"
    "## Two ways to author a form\n\n" + TWO_WAYS + "\n"
)
UNIT = "inherited_unit:022.paragraph"


def _omr_facts(polarity: str = "CONTRADICTED") -> FactsDocument:
    return FactsDocument(
        OMR,
        "4228a88533afcbde54d40c5ac6d8253a226f29be",
        (
            Fact("inherited_unit:001.heading", "inherited_unit", "# omr-python-for-foss",
                 (Evidence("README.md", "lines 1-1; heading"),)),
            Fact("inherited_unit:021.heading", "inherited_unit", "## Two ways to author a form",
                 (Evidence("README.md", "lines 101-101; heading"),),
                 attributes={"section": "omr-python-for-foss"}),
            Fact(UNIT, "inherited_unit", TWO_WAYS,
                 (Evidence("README.md", "lines 103-107; paragraph"),),
                 attributes={"section": "omr-python-for-foss > Two ways to author a form"}),
            Fact("link_target:014", "link_target", DEAD,
                 (Evidence("README.md", "HTTP 404"),), polarity=polarity),  # type: ignore[arg-type]
        ),
    )


def _row(disposition: str, fact_ids: list[str], rationale: str = "kept") -> dict:
    return {
        "unit_id": UNIT, "disposition": disposition, "destination_section": "key_capabilities",
        "fact_ids": fact_ids, "rationale": rationale,
    }


def _sealed(readme: str, facts: FactsDocument, row: dict) -> SealedCandidate:
    rows = tuple(
        {"id": f.id, "kind": f.kind, "value": f.value, "polarity": f.polarity,
         "attributes": f.attributes, "evidence": []}
        for f in facts.facts
    )
    return SealedCandidate(LANE_R, readme, rows, (row,))


def test_a_kept_unit_prints_a_dead_link_as_its_label_and_every_other_character_as_written() -> None:
    printed = kept_unit_form(UNIT, TWO_WAYS, _omr_facts())
    assert printed == TWO_WAYS.replace(f"[`examples/final-exam.txt`]({DEAD})", "`examples/final-exam.txt`")
    assert DEAD not in {link.href for link in extract_links(printed)}


def test_negative_control_a_link_not_proven_dead_is_left_as_written() -> None:
    # UNRESOLVED (the check never answered) is not evidence the target is gone: nothing changes.
    assert kept_unit_form(UNIT, TWO_WAYS, _omr_facts("UNRESOLVED")) == TWO_WAYS
    assert without_contradicted_links(TWO_WAYS, _omr_facts("SUPPORTED")) == TWO_WAYS


def test_the_restored_section_with_a_dead_link_is_carried_and_the_dead_target_is_accounted() -> None:
    facts = _omr_facts()
    # The hosted shape: S4 had folded the unit to VERIFIED_REWRITE for its dead link.
    restored, changes = restore_lost_units(
        {"dispositions": [_row("VERIFIED_REWRITE", [UNIT])]}, facts, [UNIT],
        ("key_capabilities",), ("key_capabilities",),
    )
    assert [c["unit_id"] for c in changes] == [UNIT]
    row = restored["dispositions"][0]
    assert row["disposition"] == "VERIFIED_PRESERVE"
    printed = kept_unit_form(UNIT, TWO_WAYS, facts)
    candidate = "# Aspose.OMR FOSS for Python\n\n## Key Capabilities\n\n" + printed + "\n"
    losses = content_losses(_sealed(candidate, facts, row), LIVE)
    assert not [loss for loss in losses if loss.dimension == "section_coverage"]
    assert not [loss for loss in losses if loss.item == DEAD]
    # The reviewer agrees with BC-17 on the dead target (it used to call it a live_readme_loss).
    findings = live_readme_loss_rule(LIVE, candidate, facts=facts, dispositions=restored)
    assert not [f for f in findings if DEAD in f.message]


def test_negative_control_a_live_link_the_candidate_drops_is_still_a_loss() -> None:
    facts = _omr_facts("SUPPORTED")
    candidate = "# Aspose.OMR FOSS for Python\n\n## Two ways to author a form\n\nText only.\n"
    findings = live_readme_loss_rule(
        LIVE, candidate, facts=facts, dispositions={"dispositions": [_row("VERIFIED_PRESERVE", [])]}
    )
    assert [f for f in findings if DEAD in f.message]


def test_s4_keeps_a_unit_whose_only_defect_is_a_dead_link() -> None:
    facts = _omr_facts()
    output = {"dispositions": [
        {"unit_id": "inherited_unit:001.heading", "disposition": "NON_CONTENT",
         "destination_section": None, "fact_ids": [], "rationale": "title"},
        {"unit_id": "inherited_unit:021.heading", "disposition": "NON_CONTENT",
         "destination_section": None, "fact_ids": [], "rationale": "heading"},
        _row("VERIFIED_PRESERVE", ["link_target:014"]),
    ]}
    normalize(output, facts)
    row = next(r for r in output["dispositions"] if r["unit_id"] == UNIT)
    assert row["disposition"] == "VERIFIED_PRESERVE"  # was folded to VERIFIED_REWRITE
    assert "link_target:014" not in row["fact_ids"]  # a dead link is not a fact the unit may cite


GO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
CONSTRAINTS = "inherited_unit:073.list"
# Cells Go inherited_unit:073.list, verbatim (under 'Constraints').
CONSTRAINTS_LIST = (
    "- **A1-style references** (e.g. `\"A1\"`, `\"B2\"`) — tuple/array indices (e.g. `[0, 0]`) are not supported\n"
    "- Modified content regenerates XML; unmodified content reuses original XML\n"
    "- ECMA-376-compatible element ordering\n"
    "- No third-party dependencies — Go standard library only\n"
    "- Do not commit generated `.xlsx` files or contents of `outputfiles/`"
)


def _go_placement(rationale: str) -> str:
    facts = FactsDocument(GO, "99c789e9175f2b12ad82bafeeba148ddcc1367fb", (
        Fact(CONSTRAINTS, "inherited_unit", CONSTRAINTS_LIST, (Evidence("README.md", "list"),),
             attributes={"section": "Aspose.Cells FOSS for Go > Constraints"}),
        Fact("public_symbol:calculateformula", "public_symbol", "CalculateFormula",
             (Evidence("formula.go", "; function; "),)),
    ))
    plan = {
        "sections": [{"section_id": "scope_limitations", "include": True}],
        "material_limitations": [{"fact_ids": ["public_symbol:calculateformula"]}],
    }
    dispositions = {"dispositions": [{
        "unit_id": CONSTRAINTS, "disposition": "VERIFIED_PRESERVE",
        "destination_section": "scope_limitations",
        "fact_ids": ["public_symbol:calculateformula"], "rationale": rationale,
    }]}
    (decision,) = placements(plan, dispositions, facts, "python")
    return decision.outcome


def test_a_restored_unit_is_never_dropped_whole_as_overlap() -> None:
    assert _go_placement(RESTORED_RATIONALE) == "placed"


def test_negative_control_an_ordinary_kept_unit_sharing_the_plans_facts_is_still_overlap() -> None:
    assert _go_placement("The list items are supported by the limitations.") == "overlap"
