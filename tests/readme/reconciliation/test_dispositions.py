"""normalize() and coverage_findings(), ported and tested together per the reuse-manifest's own
instruction ("port coverage_findings() together with normalize(), never separately")."""

from __future__ import annotations

from dataclasses import replace

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    coverage_findings,
    normalize,
    placement_errors,
    rendering_fact_ids,
)

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


# Real hosted defect (run 40571540396, C++; recurs on 40571547837, Go, project/state.yaml
# INDEPENDENT_LLM_REVIEWER.hosted_run_log): an OMIT_UNSUPPORTED with empty fact_ids, claiming "not
# supported by facts", while the unit's own text spells a SUPPORTED package or link_target fact's
# value verbatim. Two distinct ecosystem shapes, proving the fix is general, not a C++ special case.
_CPP_PACKAGE_FACTS = replace(
    FACTS,
    facts=(
        *FACTS.facts,
        Fact(
            "package:distribution.aspose.widget.cpp.foss",
            "package",
            "Aspose.Widget.Cpp.FOSS",
            (Evidence("README.md"),),
        ),
        Fact(
            "build_test_asset:examples",
            "build_test_asset",
            "ctest",
            (Evidence("CMakeLists.txt"),),
        ),
        Fact(
            "inherited_unit:010.code_block",
            "inherited_unit",
            '```xml\n<PackageReference Include="Aspose.Widget.Cpp.FOSS" Version="1.0.0" />\n```',
            (Evidence("README.md", "section 'Widget > Installation'"),),
            attributes={"section": "Widget > Installation"},
        ),
        Fact(
            "inherited_unit:011.code_block",
            "inherited_unit",
            "```\nTotally unsupported legacy content naming nothing real.\n```",
            (Evidence("README.md", "section 'Widget > Installation'"),),
            attributes={"section": "Widget > Installation"},
        ),
    ),
)

_GO_LINK_FACTS = replace(
    FACTS,
    facts=(
        *FACTS.facts,
        Fact("link_target:044", "link_target", "docs/usage.md", (Evidence("README.md"),)),
        Fact(
            "inherited_unit:020.paragraph",
            "inherited_unit",
            "See docs/usage.md for detailed documentation.",
            (Evidence("README.md", "section 'Widget > Detailed Documentation'"),),
            attributes={"section": "Widget > Detailed Documentation"},
        ),
    ),
)


def test_normalize_backfills_an_omit_unsupported_that_spells_a_supported_package() -> None:
    """C++ shape: a NuGet PackageReference block omitted as "not supported by facts" while its
    own text spells the repository's verified distribution package verbatim. normalize() must
    attach that real citation -- never invent a destination, never loosen the disposition -- so
    the disposition is no longer a false claim and live_readme_loss_rule's own accounting (which
    requires fact_ids truthy) stops reporting the block as a live, unaccounted-for loss."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:010.code_block",
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": [],
                "rationale": "The XML snippet is not supported by facts and is not placeable.",
            }
        ]
    }
    normalize(output, _CPP_PACKAGE_FACTS)
    entry = output["dispositions"][0]
    assert entry["disposition"] == "OMIT_UNSUPPORTED"
    assert entry["fact_ids"] == ["package:distribution.aspose.widget.cpp.foss"]
    assert entry["rationale"]  # the false "not supported by facts" claim is gone


def test_normalize_backfills_an_omit_unsupported_that_spells_a_supported_link_target() -> None:
    """Go shape (a different fact kind, a different unit kind -- proving the fix generalises,
    not a C++-only patch): a paragraph naming a verified docs link, omitted uncited."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:020.paragraph",
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": [],
                "rationale": "The usage.md paragraph is not supported by any fact.",
            }
        ]
    }
    normalize(output, _GO_LINK_FACTS)
    entry = output["dispositions"][0]
    assert entry["disposition"] == "OMIT_UNSUPPORTED"
    assert entry["fact_ids"] == ["link_target:044"]


def test_normalize_leaves_a_genuinely_unsupported_omission_uncited() -> None:
    """Negative control: content that spells no SUPPORTED package/link_target fact must stay
    exactly as uncited -- the reviewer rule is never loosened for a real omission."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:011.code_block",
                "disposition": "OMIT_UNSUPPORTED",
                "destination_section": None,
                "fact_ids": [],
                "rationale": "Nothing supports this legacy snippet.",
            }
        ]
    }
    normalize(output, _CPP_PACKAGE_FACTS)
    entry = output["dispositions"][0]
    assert entry["disposition"] == "OMIT_UNSUPPORTED"
    assert entry["fact_ids"] == []
    assert entry["rationale"] == "Nothing supports this legacy snippet."


# Real hosted defect (aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 41095849129): a repository
# with no single SUPPORTED install_command fact (C++'s install story is a choice of NuGet/CMake
# snippets, never one canonical command) still has the installation section render a real
# sentence -- renderer.py's own _installation() falls back to the package's distribution fact
# when no install_command resolved. rendering_fact_ids("installation", ...) did not know this, so
# it reported installation as rendering nothing, and normalize()'s generic "destination renders
# nothing" fold forced every SUPERSEDE_REDUNDANT citing that exact fact back to DEFER_UNRESOLVED
# -- which placement_errors's uncited_redundant_defer then refused outright: an unwinnable loop
# for a model giving the one answer the actual rendered README supports.
def test_rendering_fact_ids_counts_the_distribution_fact_when_no_install_command_exists() -> None:
    assert rendering_fact_ids("installation", _CPP_PACKAGE_FACTS) == [
        "package:distribution.aspose.widget.cpp.foss"
    ]


def test_rendering_fact_ids_prefers_a_real_install_command_when_one_is_supported() -> None:
    """The distribution fallback is only for when nothing else renders; an existing, tested
    install_command path must not be disturbed by it."""
    facts = replace(
        _CPP_PACKAGE_FACTS,
        facts=(
            *_CPP_PACKAGE_FACTS.facts,
            Fact("install_command:001", "install_command", "pip install aspose-widget-foss", (Evidence("x"),)),
        ),
    )
    assert rendering_fact_ids("installation", facts) == ["install_command:001"]


def test_normalize_no_longer_force_defers_a_supersede_citing_the_distribution_fact() -> None:
    """The force-revert this bug caused is gone: a SUPERSEDE_REDUNDANT entry citing the
    distribution fact is no longer silently rewritten to DEFER_UNRESOLVED just because
    rendering_fact_ids used to come back empty."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:010.code_block",
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "installation",
                "fact_ids": ["package:distribution.aspose.widget.cpp.foss"],
                "rationale": "Superseded by the installation section's distribution sentence.",
            }
        ]
    }
    normalize(output, _CPP_PACKAGE_FACTS)
    entry = output["dispositions"][0]
    assert entry["disposition"] != "DEFER_UNRESOLVED"


def test_supersede_redundant_by_installation_is_still_refused_when_the_literal_block_is_not_what_it_renders() -> (
    None
):
    """Fixing the force-revert must not paper over the real gap: the installation section's
    distribution sentence never reproduces a code block's literal text (a PackageReference
    snippet is not the sentence "published on NuGet as Aspose.Widget.Cpp.FOSS"), so
    SUPERSEDE_REDUNDANT by installation for that exact block is still wrong -- now refused for
    the real reason (uncovered_supersession), not the old, misleading uncited_redundant_defer."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:010.code_block",
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "installation",
                "fact_ids": ["package:distribution.aspose.widget.cpp.foss"],
                "rationale": "Superseded by the installation section's distribution sentence.",
            }
        ]
    }
    normalize(output, _CPP_PACKAGE_FACTS)
    errors = placement_errors(output, _CPP_PACKAGE_FACTS)
    assert any("uncovered_supersession" in e for e in errors)
    assert not any("uncited_redundant_defer" in e for e in errors)


def test_verified_preserve_into_development_testing_is_the_clean_answer_for_the_alternative_snippet() -> (
    None
):
    """The disposition prompts/source_reconciliation.yaml now actually recommends for this shape
    passes both normalize() and placement_errors() cleanly, citing the distribution fact as the
    evidence it is a real, supported install path even though no section renders its exact
    text."""
    output = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:010.code_block",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "development_testing",
                "fact_ids": ["package:distribution.aspose.widget.cpp.foss"],
                "rationale": "A real alternative install path for this ecosystem.",
            }
        ]
    }
    norm_errors = normalize(output, _CPP_PACKAGE_FACTS)
    place_errors = placement_errors(output, _CPP_PACKAGE_FACTS)
    assert norm_errors == []
    assert place_errors == []
    entry = output["dispositions"][0]
    assert entry["disposition"] == "VERIFIED_PRESERVE"
