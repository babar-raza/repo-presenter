"""The refusal/repair half of S4: coordinate_neighbor_promises, dangling_pointers,
uncited_omit_candidates, unprinted_commands, and placement_errors itself.

New, self-contained fixtures (not the old repo's archived wave-6 JSON, which needs
validation/deferrals.py's review_deferrals and recover_uncited_prose_omits -- neither ported),
built the same way the existing test_dispositions.py builds FactsDocument fixtures, covering the
same real defect classes the old repo's docstrings name: a lead-in stranded beside a withheld
block (BC-05), a forward pointer nothing answers (BC-07), a command block printed nowhere (BC-08).
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    RECOVERED_COVERAGE_RATIONALE,
    coordinate_neighbor_promises,
    dangling_pointers,
    placement_errors,
    reconcile_checks,
    uncited_omit_candidates,
    unprinted_commands,
)

REPO = "org/Aspose.Widget-FOSS-for-Python"


def _facts(*extra: Fact) -> FactsDocument:
    base = (
        Fact("identity:repository", "identity", REPO, (Evidence("x"),)),
        Fact("identity:ecosystem", "identity", "python", (Evidence("x"),)),
        Fact("package:name", "package", "aspose-widget-foss", (Evidence("x"),)),
    )
    return FactsDocument(REPO, "f" * 40, (*base, *extra))


def _unit(uid: str, text: str) -> Fact:
    return Fact(uid, "inherited_unit", text, (Evidence("README.md", None),))


def _symbol(value: str) -> Fact:
    return Fact(
        f"public_symbol:{value.lower()}",
        "public_symbol",
        value,
        (Evidence("src/x.py", "; class; "),),
        attributes={"symbol_kind": "class"},
    )


def _entry(unit_id: str, disposition: str, destination: str | None = None, **kw) -> dict:
    return {
        "unit_id": unit_id,
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": kw.get("fact_ids", []),
        "rationale": kw.get("rationale", "because"),
    }


# ---- coordinate_neighbor_promises ----------------------------------------------------------


def test_a_lead_in_beside_an_omitted_block_is_omitted_with_it() -> None:
    facts = _facts(
        _unit("inherited_unit:014.paragraph", "Install it like this:"),
        _unit("inherited_unit:015.code_block", "```bash\nnpm install widget-foss\n```"),
    )
    document = {
        "dispositions": [
            _entry("inherited_unit:014.paragraph", "DEFER_UNRESOLVED"),
            _entry("inherited_unit:015.code_block", "OMIT_UNSUPPORTED", fact_ids=["format:x"]),
        ]
    }
    coordinate_neighbor_promises(document, facts)
    lead = next(e for e in document["dispositions"] if e["unit_id"] == "inherited_unit:014.paragraph")
    assert lead["disposition"] == "OMIT_UNSUPPORTED"
    assert lead["destination_section"] is None


def test_a_lead_in_beside_a_deferred_block_is_deferred_with_it() -> None:
    facts = _facts(
        _unit("inherited_unit:014.paragraph", "Install it like this:"),
        _unit("inherited_unit:015.code_block", "```bash\nnpm install widget-foss\n```"),
    )
    document = {
        "dispositions": [
            _entry("inherited_unit:014.paragraph", "VERIFIED_PRESERVE", "quick_start"),
            _entry("inherited_unit:015.code_block", "DEFER_UNRESOLVED"),
        ]
    }
    coordinate_neighbor_promises(document, facts)
    lead = next(e for e in document["dispositions"] if e["unit_id"] == "inherited_unit:014.paragraph")
    assert lead["disposition"] == "DEFER_UNRESOLVED"


def test_a_lead_in_beside_a_kept_block_in_the_same_section_is_unchanged() -> None:
    """Negative control: nothing here is withheld, so nothing is folded."""
    facts = _facts(
        _unit("inherited_unit:014.paragraph", "Install it like this:"),
        _unit("inherited_unit:015.code_block", "```bash\nnpm install widget-foss\n```"),
    )
    document = {
        "dispositions": [
            _entry("inherited_unit:014.paragraph", "VERIFIED_PRESERVE", "quick_start"),
            _entry("inherited_unit:015.code_block", "VERIFIED_PRESERVE", "quick_start"),
        ]
    }
    import copy

    before = copy.deepcopy(document)
    coordinate_neighbor_promises(document, facts)
    assert document == before


def test_a_lead_in_follows_its_placed_payload_into_the_payloads_section() -> None:
    facts = _facts(
        _unit("inherited_unit:012.paragraph", "Run the tests like this:"),
        _unit("inherited_unit:013.code_block", "```bash\npytest\n```"),
    )
    document = {
        "dispositions": [
            _entry("inherited_unit:012.paragraph", "VERIFIED_PRESERVE", "quick_start"),
            _entry("inherited_unit:013.code_block", "VERIFIED_PRESERVE", "development_testing"),
        ]
    }
    coordinate_neighbor_promises(document, facts)
    lead = next(e for e in document["dispositions"] if e["unit_id"] == "inherited_unit:012.paragraph")
    assert lead["destination_section"] == "development_testing"


def test_a_colonless_unit_beside_an_omitted_block_is_not_a_lead_in() -> None:
    facts = _facts(
        _unit("inherited_unit:014.paragraph", "This is an ordinary sentence."),
        _unit("inherited_unit:015.code_block", "```bash\nnpm install widget-foss\n```"),
    )
    document = {
        "dispositions": [
            _entry("inherited_unit:014.paragraph", "DEFER_UNRESOLVED"),
            _entry("inherited_unit:015.code_block", "OMIT_UNSUPPORTED", fact_ids=["format:x"]),
        ]
    }
    import copy

    before = copy.deepcopy(document)
    coordinate_neighbor_promises(document, facts)
    assert document == before


# ---- uncited_omit_candidates ----------------------------------------------------------------


def test_uncited_omit_candidates_names_a_supported_symbol_the_text_spells() -> None:
    facts = _facts(_symbol("aspose_widget_foss.Widget"))
    candidates = uncited_omit_candidates("See `aspose_widget_foss.Widget` for details.", facts)
    assert "public_symbol:aspose_widget_foss.widget" in candidates


def test_uncited_omit_candidates_is_empty_when_nothing_is_spelled() -> None:
    facts = _facts(_symbol("aspose_widget_foss.Widget"))
    assert uncited_omit_candidates("Nothing relevant here.", facts) == []


# ---- dangling_pointers ----------------------------------------------------------------------


def _padded(*extra: Fact) -> tuple[Fact, ...]:
    """Unrelated inherited units both before AND after the real units under test, so none of
    them ever falls inside dangling_pointers' own "last 3 units of a batch are not judged" tail
    window -- that window is the last 3 of the WHOLE document's inherited units by insertion
    order, not scoped to any one destination."""
    before = tuple(
        _unit(f"inherited_unit:{index:03d}.paragraph", "An unrelated paragraph.")
        for index in range(1, 5)
    )
    after = tuple(
        _unit(f"inherited_unit:{index:03d}.paragraph", "A later unrelated paragraph.")
        for index in range(900, 904)
    )
    return (*before, *extra, *after)


def test_a_kept_unit_whose_pointer_nothing_answers_is_flagged() -> None:
    facts = _facts(*_padded(_unit("inherited_unit:046.paragraph", "The table below lists every method.")))
    document = {
        "dispositions": [_entry("inherited_unit:046.paragraph", "VERIFIED_PRESERVE", "api_reference")]
    }
    found = dangling_pointers(document, facts)
    assert len(found) == 1
    unit, sentence, reason = found[0]
    assert unit == "inherited_unit:046.paragraph"
    assert "table" in reason


def test_a_pointer_the_next_kept_unit_answers_is_not_flagged() -> None:
    facts = _facts(
        *_padded(
            _unit("inherited_unit:046.paragraph", "The table below lists every method."),
            _unit(
                "inherited_unit:047.table",
                "| Class | Description |\n| --- | --- |\n| `Document` | x |",
            ),
        )
    )
    document = {
        "dispositions": [
            _entry("inherited_unit:046.paragraph", "VERIFIED_PRESERVE", "api_reference"),
            _entry("inherited_unit:047.table", "VERIFIED_PRESERVE", "api_reference"),
        ]
    }
    assert dangling_pointers(document, facts) == []


def test_a_pointer_in_a_unit_that_is_not_kept_as_written_is_not_judged() -> None:
    facts = _facts(*_padded(_unit("inherited_unit:046.paragraph", "The table below lists every method.")))
    for disposition in ("VERIFIED_REWRITE", "SUPERSEDE_REDUNDANT", "OMIT_UNSUPPORTED"):
        document = {
            "dispositions": [_entry("inherited_unit:046.paragraph", disposition, "api_reference")]
        }
        assert dangling_pointers(document, facts) == []


# ---- unprinted_commands ---------------------------------------------------------------------


def test_a_command_no_verified_section_prints_is_flagged() -> None:
    facts = _facts()
    unprinted = unprinted_commands("```bash\nnpm install widget-foss-extra\n```", facts)
    assert unprinted == ["npm install widget-foss-extra"]


def test_a_command_the_installation_row_prints_is_not_flagged() -> None:
    facts = _facts(
        Fact(
            "install_command:npm",
            "install_command",
            "npm install aspose-widget-foss",
            (Evidence("README.md", None),),
        )
    )
    unprinted = unprinted_commands("```bash\nnpm install aspose-widget-foss\n```", facts)
    assert unprinted == []


# ---- placement_errors -----------------------------------------------------------------------


def test_an_uncited_omission_of_prose_is_refused() -> None:
    facts = _facts(_unit("inherited_unit:020.paragraph", "Some unsupported claim."))
    document = {"dispositions": [_entry("inherited_unit:020.paragraph", "OMIT_UNSUPPORTED")]}
    errors = placement_errors(document, facts)
    assert any("uncited_prose_omit" in e for e in errors)


def test_an_omission_with_a_cited_fact_is_not_refused_for_that_reason() -> None:
    facts = _facts(_unit("inherited_unit:020.paragraph", "Some unsupported claim."))
    document = {
        "dispositions": [
            _entry("inherited_unit:020.paragraph", "OMIT_UNSUPPORTED", fact_ids=["format:x"])
        ]
    }
    errors = placement_errors(document, facts)
    assert not any("uncited_prose_omit" in e for e in errors)


def test_an_uncited_omission_of_a_code_block_is_refused() -> None:
    """Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 40730367161): a CMake
    add_subdirectory() snippet was OMIT_UNSUPPORTED with empty fact_ids and a "superseded by the
    installation section" rationale -- a real claim, just uncited, on a kind the original rule
    (paragraph/list only) never covered."""
    facts = _facts(_unit("inherited_unit:019.code_block", "```cmake\nadd_subdirectory(x)\n```"))
    document = {"dispositions": [_entry("inherited_unit:019.code_block", "OMIT_UNSUPPORTED")]}
    errors = placement_errors(document, facts)
    assert any("uncited_prose_omit" in e for e in errors)


def test_an_uncited_redundant_diagram_code_block_is_refused() -> None:
    """Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-Java, hosted run 40730382891): a
    live Mermaid diagram superseded by the renderer's own at_a_glance diagram cited no fact and
    was accepted, then reported as live content lost three stages later -- the same class of
    unaccounted loss as an uncited OMIT_UNSUPPORTED, just on a different disposition and kind."""
    facts = _facts(_unit("inherited_unit:008.code_block", "```mermaid\nflowchart TD\n```"))
    document = {
        "dispositions": [
            _entry(
                "inherited_unit:008.code_block",
                "SUPERSEDE_REDUNDANT",
                "at_a_glance",
                rationale="Rendered by at_a_glance.",
            )
        ]
    }
    errors = placement_errors(document, facts)
    assert any("uncited_redundant_diagram" in e for e in errors)


def test_a_redundant_diagram_with_a_cited_fact_is_not_refused_for_that_reason() -> None:
    facts = _facts(_unit("inherited_unit:008.code_block", "```mermaid\nflowchart TD\n```"))
    document = {
        "dispositions": [
            _entry(
                "inherited_unit:008.code_block",
                "SUPERSEDE_REDUNDANT",
                "at_a_glance",
                fact_ids=["package:name"],
                rationale="Rendered by at_a_glance.",
            )
        ]
    }
    errors = placement_errors(document, facts)
    assert not any("uncited_redundant_diagram" in e for e in errors)


def test_a_redundant_paragraph_lead_in_is_not_held_to_the_diagram_citation_rule() -> None:
    """The new rule is scoped to code_block (substantial, independently-checkable content) --
    a lead-in paragraph superseded into the section it introduces still needs no citation."""
    facts = _facts(_unit("inherited_unit:009.paragraph", "See the diagram below."))
    document = {
        "dispositions": [
            _entry(
                "inherited_unit:009.paragraph",
                "SUPERSEDE_REDUNDANT",
                "at_a_glance",
                rationale="Lead-in for the diagram.",
            )
        ]
    }
    errors = placement_errors(document, facts)
    assert not any("uncited_redundant_diagram" in e for e in errors)


def test_an_uncited_deferral_of_a_non_example_code_block_is_refused() -> None:
    """Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 41060017964): three
    alternative install snippets (NuGet PackageReference, CMake find_package path hint,
    add_subdirectory()) each landed DEFER_UNRESOLVED, destination null, uncited, with a
    rationale that actually argued for SUPERSEDE_REDUNDANT -- a code_block the pipeline never
    tried to verify as an example has no structural ambiguity to defer."""
    facts = _facts(_unit("inherited_unit:020.code_block", "```cmake\nadd_subdirectory(x)\n```"))
    document = {"dispositions": [_entry("inherited_unit:020.code_block", "DEFER_UNRESOLVED")]}
    errors = placement_errors(document, facts)
    assert any("uncited_redundant_defer" in e for e in errors)


def test_the_recovered_coverage_sentinel_is_not_held_to_the_defer_citation_rule() -> None:
    """Negative control found by the failing-test discipline itself: widening the rule to catch
    a cited-but-wrong DEFER_UNRESOLVED (test above) first broke a real, documented historical
    fixture (tests/readme/reconciliation/test_patch.py's wave-4 3D-Java case) whose code block is
    genuinely "not provably carried by the section named" -- RECOVERED_COVERAGE_RATIONALE is the
    one deterministic, code-assigned sentinel reserved for exactly that, distinct from anything a
    model writes freely, so it stays exempt even though it is cited."""
    facts = _facts(_unit("inherited_unit:020.code_block", "```cmake\nadd_subdirectory(x)\n```"))
    document = {
        "dispositions": [
            _entry(
                "inherited_unit:020.code_block",
                "DEFER_UNRESOLVED",
                fact_ids=["install_command:maven"],
                rationale=RECOVERED_COVERAGE_RATIONALE,
            )
        ]
    }
    errors = placement_errors(document, facts)
    assert not any("uncited_redundant_defer" in e for e in errors)


def test_a_deferred_tracked_example_is_not_held_to_the_defer_citation_rule() -> None:
    """DEFER_UNRESOLVED is legitimate for a code block the pipeline tried and failed to verify
    as an example -- that is a real, structural ambiguity, not a lazy catch-all."""
    facts = _facts(
        _unit("inherited_unit:020.code_block", "```cmake\nadd_subdirectory(x)\n```"),
        Fact(
            "example:001",
            "example",
            "add_subdirectory(x)",
            (Evidence("README.md", "unit inherited_unit:020.code_block"),),
            polarity="UNRESOLVED",
        ),
    )
    document = {"dispositions": [_entry("inherited_unit:020.code_block", "DEFER_UNRESOLVED")]}
    errors = placement_errors(document, facts)
    assert not any("uncited_redundant_defer" in e for e in errors)


def test_a_deferred_code_block_with_a_citation_is_still_refused() -> None:
    """Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 41068602255): a cited
    DEFER_UNRESOLVED ("fact_ids": ["package:distribution..."], rationale "rendered
    deterministically by the installation section") is just as wrong as an uncited one --
    DEFER_UNRESOLVED means the facts neither support nor contradict the claim, which cannot be
    true of a disposition that cites a fact in support of it. A citation does not excuse this."""
    facts = _facts(_unit("inherited_unit:020.code_block", "```cmake\nadd_subdirectory(x)\n```"))
    document = {
        "dispositions": [
            _entry(
                "inherited_unit:020.code_block",
                "DEFER_UNRESOLVED",
                fact_ids=["package:name"],
            )
        ]
    }
    errors = placement_errors(document, facts)
    assert any("uncited_redundant_defer" in e for e in errors)


def test_a_deferred_paragraph_is_not_held_to_the_defer_citation_rule() -> None:
    """Scoped to code_block only -- normalize() assigns DEFER_UNRESOLVED to many paragraph/list
    units deterministically, and this rule must not relitigate those."""
    facts = _facts(_unit("inherited_unit:021.paragraph", "Some genuinely ambiguous claim."))
    document = {"dispositions": [_entry("inherited_unit:021.paragraph", "DEFER_UNRESOLVED")]}
    errors = placement_errors(document, facts)
    assert not any("uncited_redundant_defer" in e for e in errors)


def test_a_placing_disposition_into_an_unholdable_destination_is_refused() -> None:
    facts = _facts(_unit("inherited_unit:020.paragraph", "Some claim."))
    document = {
        "dispositions": [
            _entry("inherited_unit:020.paragraph", "VERIFIED_PRESERVE", "not_a_real_section")
        ]
    }
    errors = placement_errors(document, facts)
    assert any("needs a destination the shell can hold" in e for e in errors)


def test_a_supersede_with_no_destination_and_no_citation_is_refused() -> None:
    facts = _facts(_unit("inherited_unit:020.paragraph", "Some claim."))
    document = {"dispositions": [_entry("inherited_unit:020.paragraph", "SUPERSEDE_REDUNDANT")]}
    errors = placement_errors(document, facts)
    assert any("names the section" in e for e in errors)


def test_correct_with_evidence_needs_at_least_one_citation() -> None:
    facts = _facts(_unit("inherited_unit:020.paragraph", "Some claim."))
    document = {"dispositions": [_entry("inherited_unit:020.paragraph", "CORRECT_WITH_EVIDENCE")]}
    errors = placement_errors(document, facts)
    assert any("needs at least one fact ID as evidence" in e for e in errors)


def test_a_kept_unit_with_a_dangling_pointer_is_refused_via_placement_errors() -> None:
    facts = _facts(*_padded(_unit("inherited_unit:046.paragraph", "The table below lists every method.")))
    document = {
        "dispositions": [_entry("inherited_unit:046.paragraph", "VERIFIED_PRESERVE", "api_reference")]
    }
    errors = placement_errors(document, facts)
    assert any("dangling_pointer" in e for e in errors)


def test_reconcile_checks_combines_normalize_and_placement_errors() -> None:
    """reconcile_checks = normalize(...) + placement_errors(...), the old repo's own wiring."""
    facts = _facts(*_padded(_unit("inherited_unit:046.paragraph", "The table below lists every method.")))
    document = {
        "dispositions": [_entry("inherited_unit:046.paragraph", "VERIFIED_PRESERVE", "api_reference")]
    }
    errors = reconcile_checks(document, facts)
    assert any("dangling_pointer" in e for e in errors)
