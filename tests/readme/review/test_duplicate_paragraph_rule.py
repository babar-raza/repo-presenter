"""A candidate that prints the same prose paragraph twice is provably defective: a deterministic
holdout, so the model is not the only line against it (iteration 2: the model caught 0 of 4
duplicated paragraphs). Fenced code, tables, lists, headings and short lines are not paragraphs."""

from __future__ import annotations

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.review.independent_reviewer import (
    duplicate_paragraph_rule,
    review_candidate,
)

PARAGRAPH = (
    "Aspose.Widget FOSS renders widgets to PNG and SVG through the Widget class, exposes the "
    "SvgExporter for vector output, and needs no native dependency on any supported platform."
)
README = f"""# Aspose.Widget FOSS for Python

{PARAGRAPH}

## Key Capabilities

- **Render.** It renders widgets.

## Scope and Limitations

Rendering to PDF is not implemented.
"""


def test_a_distinct_readme_has_no_duplicate_paragraph() -> None:
    assert duplicate_paragraph_rule(README) == []


def test_the_same_paragraph_printed_twice_is_one_deterministic_blocking_finding() -> (
    None
):
    twice = README.replace(
        "Rendering to PDF is not implemented.",
        PARAGRAPH + "\n\nRendering to PDF is not implemented.",
    )
    (finding,) = duplicate_paragraph_rule(twice)
    assert finding.rule == "duplicate_paragraph" and finding.source == "deterministic"
    assert finding.blocking and finding.quote == PARAGRAPH
    assert "2 times" in finding.evidence


def test_case_spacing_and_markdown_emphasis_do_not_hide_a_repeat() -> None:
    variant = "  ".join(f"**{PARAGRAPH}**".upper().split())
    twice = README + "\n" + variant + "\n"
    assert len(duplicate_paragraph_rule(twice)) == 1


def test_repeated_short_lines_lists_tables_headings_and_fences_are_not_duplicates() -> (
    None
):
    repeated = (
        "## Notes\n\n- **Render.** It renders widgets with the shared pipeline for every format here.\n\n"
        "| Type | Summary |\n|---|---|\n| Widget | The main class that renders every kind of widget here. |\n\n"
        f"```text\n{PARAGRAPH}\n```\n\nSee the guide.\n\nSee the guide.\n"
    )
    assert duplicate_paragraph_rule(README + repeated + repeated) == []


def test_a_paragraph_repeated_inside_a_fence_and_outside_is_not_a_duplicate() -> None:
    fenced = README + f"\n```text\n{PARAGRAPH}\n```\n"
    assert duplicate_paragraph_rule(fenced) == []


def test_review_candidate_runs_the_rule_and_the_verdict_rejects() -> None:
    twice = README + "\n" + PARAGRAPH + "\n"
    verdict = review_candidate(
        readme_text=twice,
        units=[],
        facts=FactsDocument("org/widget", "a" * 40, ()),
        dispositions={},
        original_readme=README,
    )
    assert verdict.verdict == "REJECT"
    assert "duplicate_paragraph" in {f.rule for f in verdict.blocking_findings}
