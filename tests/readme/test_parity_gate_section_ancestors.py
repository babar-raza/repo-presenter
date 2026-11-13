"""BC-17 section_coverage: a benchmark h2 is held by the units of its subsections.

Real failing shape (Font Python, hosted run 43413908303): the published README's
"## Production Workflows" has no content directly under it, only "### 1. Web Font Optimization"
and siblings. The accounting matched only the last segment of a unit's section path, so no unit
held the h2, the loss was routed to PLANNING with no units, and no restore could reach it.
"""

from __future__ import annotations

from repo_presenter.readme import parity_gate as pg

TITLE = "Foo for Python"
BODY = "Subset a web font to the glyphs a page uses, then write it back as WOFF2 for delivery."


def benchmark() -> str:
    return "\n".join(
        [
            f"# {TITLE}",
            "",
            "## Overview",
            "",
            "Foo reads and writes font files from pure Python, with no native dependencies at all.",
            "",
            "## Production Workflows",
            "",
            "### 1. Web Font Optimization",
            "",
            BODY,
            "",
        ]
    )


def without_workflows(text: str) -> str:
    head, _, _ = text.partition("## Production Workflows")
    return head


def fact(fid, value, section=None):
    return {
        "id": fid,
        "kind": "inherited_unit",
        "value": value,
        "polarity": "SUPPORTED",
        "attributes": {"section": section} if section else None,
        "evidence": [],
        "confidence": 1.0,
    }


def facts():
    return (
        fact("inherited_unit:001.heading", f"# {TITLE}"),
        fact("inherited_unit:002.heading", "## Overview", TITLE),
        fact(
            "inherited_unit:003.paragraph",
            "Foo reads and writes font files from pure Python, with no native dependencies at all.",
            f"{TITLE} > Overview",
        ),
        fact("inherited_unit:004.heading", "## Production Workflows", TITLE),
        fact(
            "inherited_unit:005.heading",
            "### 1. Web Font Optimization",
            f"{TITLE} > Production Workflows",
        ),
        fact(
            "inherited_unit:006.paragraph",
            BODY,
            f"{TITLE} > Production Workflows > 1. Web Font Optimization",
        ),
    )


def rows(**overrides):
    default = {
        "inherited_unit:001.heading": "SUPERSEDE_REDUNDANT",
        "inherited_unit:002.heading": "SUPERSEDE_REDUNDANT",
        "inherited_unit:003.paragraph": "VERIFIED_PRESERVE",
        "inherited_unit:004.heading": "SUPERSEDE_REDUNDANT",
        "inherited_unit:005.heading": "SUPERSEDE_REDUNDANT",
        "inherited_unit:006.paragraph": "VERIFIED_PRESERVE",
    }
    merged = {**default, **overrides}
    return tuple(
        {"unit_id": uid, "disposition": d, "fact_ids": [], "rationale": ""}
        for uid, d in merged.items()
        if d is not None
    )


def section(candidate: pg.SealedCandidate) -> pg.Dimension:
    result = pg.evaluate("o/n", candidate, benchmark())
    return next(d for d in result.dimensions if d.name == "section_coverage")


def test_self_parity_still_passes():
    result = pg.evaluate("o/n", pg.SealedCandidate("R", benchmark(), facts(), rows()), benchmark())
    assert result.parity, pg.render([result])


def test_lost_h2_is_routed_to_its_subsection_units_not_planning():
    candidate = pg.SealedCandidate(
        "R",
        without_workflows(benchmark()),
        facts(),
        rows(**{"inherited_unit:006.paragraph": None}),
    )
    d = section(candidate)
    assert not d.passed and d.numbers["missing"] == 1
    (loss,) = d.losses
    assert loss.item == "Production Workflows"
    assert loss.units == ("inherited_unit:006.paragraph",)
    assert loss.stage == "RECONCILING"


def test_h2_whose_subsection_units_are_non_loss_is_justified():
    candidate = pg.SealedCandidate(
        "R",
        without_workflows(benchmark()),
        facts(),
        rows(**{"inherited_unit:006.paragraph": "NON_CONTENT"}),
    )
    d = section(candidate)
    assert d.passed and d.numbers["justified"] == 1


def test_document_title_is_not_an_ancestor_of_every_section():
    # "Foo" topic-matches the title "Foo for Python"; the title must not make every unit of the
    # document a member of a benchmark h2 named "Foo".
    acct = pg.Accounting(pg.SealedCandidate("R", benchmark(), facts(), rows()))
    assert acct._ancestors(f"{TITLE} > Production Workflows > 1. Web Font Optimization", TITLE) == [
        "Production Workflows",
        "1. Web Font Optimization",
    ]
    assert acct._title() == TITLE
    # A unit directly under the title keeps its innermost segment, exactly as before.
    assert acct._ancestors(TITLE, TITLE) == [TITLE]
