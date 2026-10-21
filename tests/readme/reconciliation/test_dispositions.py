"""normalize() and coverage_findings(), ported and tested together per the reuse-manifest's own
instruction ("port coverage_findings() together with normalize(), never separately")."""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import coverage_findings, normalize

FACTS = FactsDocument(
    "org/Aspose.Widget-FOSS-for-Python",
    "f" * 40,
    (
        Fact("identity:repository", "identity", "org/Aspose.Widget-FOSS-for-Python", (Evidence("x"),)),
        Fact("identity:ecosystem", "identity", "python", (Evidence("x"),)),
        Fact("package:name", "package", "aspose-widget-foss", (Evidence("x"),)),
        Fact("license:spdx", "license", "MIT", (Evidence("LICENSE"),)),
        Fact("license:file", "license", "LICENSE", (Evidence("LICENSE"),)),
        Fact(
            "public_symbol:aspose_widget_foss.widget",
            "public_symbol",
            "aspose_widget_foss.Widget",
            (Evidence("aspose_widget_foss/widget.py", "; class; "),),
            attributes={"symbol_kind": "class", "docstring": "A widget."},
        ),
        Fact(
            "inherited_unit:001.paragraph",
            "inherited_unit",
            "Licensed under the MIT License.",
            (Evidence("README.md", "section 'Widget > License'"),),
            attributes={"section": "Widget > License"},
        ),
        Fact(
            "inherited_unit:002.paragraph",
            "inherited_unit",
            "The widget class does the rendering.",
            (Evidence("README.md", "section 'Widget > Overview'"),),
            attributes={"section": "Widget > Overview"},
        ),
        Fact(
            "inherited_unit:003.blockquote",
            "inherited_unit",
            "> See `aspose_widget_foss.Widget` for the full API.",
            (Evidence("README.md", "section 'Widget > Overview'"),),
            attributes={"section": "Widget > Overview"},
        ),
    ),
)


def test_normalize_folds_a_license_placement_into_a_supersession() -> None:
    """A placement aimed at the deterministic ``license`` section, whose text the License row
    actually renders, is folded to SUPERSEDE_REDUNDANT citing the facts that section renders --
    never left as a placement into a section the renderer, not any plan, owns."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:001.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "license",
                "fact_ids": ["license:spdx"],
                "rationale": "The license paragraph.",
            }
        ]
    }
    errors = normalize(output, FACTS)
    assert errors == []
    entry = output["dispositions"][0]
    assert entry["disposition"] == "SUPERSEDE_REDUNDANT"
    assert set(entry["fact_ids"]) >= {"license:spdx", "license:file"}


def test_normalize_defers_a_placement_into_a_section_with_no_content_to_render() -> None:
    """``dependencies`` renders only from ``dependency`` facts; this repository has none, so a
    unit placed there cannot be shown to be redundant and is deferred for the owner, never
    silently dropped."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:002.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "dependencies",
                "fact_ids": [],
                "rationale": "A stray dependency mention.",
            }
        ]
    }
    normalize(output, FACTS)
    entry = output["dispositions"][0]
    assert entry["disposition"] == "DEFER_UNRESOLVED"
    assert entry["destination_section"] is None


def test_coverage_findings_flags_an_omission_whose_text_spells_a_supported_symbol() -> None:
    """TC-DSP-01's own self-audit: OMIT_UNSUPPORTED claims no fact supports the unit, but this
    unit's own text spells a SUPPORTED public_symbol verbatim -- that is not a failed support
    lookup, so the claim is unprovable and coverage_findings() must say so."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:003.blockquote",
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": [],
                "rationale": "Nothing supports this.",
            }
        ]
    }
    gaps = coverage_findings(output, FACTS)
    assert len(gaps) == 1
    assert gaps[0].unit_id == "inherited_unit:003.blockquote"
    assert gaps[0].reason == "omit_names_supported"
    assert "public_symbol:aspose_widget_foss.widget" in gaps[0].detail


def test_coverage_findings_is_silent_when_the_omission_is_cited() -> None:
    """The identical omission, cited, is not a gap at all: a cited reason stands."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:003.blockquote",
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": ["package:name"],
                "rationale": "Superseded by the API reference.",
            }
        ]
    }
    assert coverage_findings(output, FACTS) == []


def test_coverage_findings_is_silent_for_an_uncited_plain_paragraph_omission() -> None:
    """An uncited OMIT_UNSUPPORTED of an ordinary paragraph or list is NOT this function's own
    rule (module docstring: "an uncited prose omission is placement_errors' own rule") -- only a
    non-prose kind (table/blockquote/code_block) or an example/version-skew claim is judged here."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:002.paragraph",
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": [],
                "rationale": "",
            }
        ]
    }
    assert coverage_findings(output, FACTS) == []


def test_normalize_is_a_strict_superset_of_what_coverage_findings_would_otherwise_flag() -> None:
    """Run coverage_findings() first (what normalize folds away), confirming the two travel
    together: every gap coverage_findings reports against the license-placement fixture above is
    exactly what normalize's own fold resolves."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:001.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "license",
                "fact_ids": ["license:spdx"],
                "rationale": "",
            }
        ]
    }
    before = coverage_findings(output, FACTS)
    assert before == []  # already provable: the License row does render this fact
    normalize(output, FACTS)
    after = coverage_findings(output, FACTS)
    assert after == []
