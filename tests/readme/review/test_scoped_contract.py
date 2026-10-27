"""The reply contract for a sectionwise review (reviewer logic 6).

* a citation may only name lines the unit showed: renderer-printed text and another unit's text can
  never be cited, for any claim kind (so a claim about renderer-owned text cannot be made at all);
* an omission, absence or quality finding may cite a whole section, however long (iteration 2: the
  12-line cap rejected 8 of 13 first replies, usually for exactly this); a contradiction or an
  unsupported claim still cites the smallest span, at most 12 lines;
* a finding names a section of its own unit;
* findings of one kind on the same lines are one finding.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.review.clearances import ClearanceContext, apply_clearances
from repo_presenter.readme.review.reply import (
    MAX_CITED_LINES,
    ReviewScope,
    findings_from_reply,
    merge_repeated_findings,
    resolve_cited_lines,
    validate_review_reply,
)
from repo_presenter.readme.review.scope import line_sections
from tests.readme.review.review_support import FACTS, ORIGINAL, raw_finding, raw_reply

CAPABILITIES = "\n".join(
    f"- **Capability {n}.** It exports vector output through `SvgExporter`, number {n}."
    for n in range(1, 21)
)
CANDIDATE = f"""# Aspose.Widget FOSS for Python

Aspose.Widget FOSS renders widgets to PNG and SVG.

## Installation

```bash
pip install aspose-widget-foss
```

## Key Capabilities

{CAPABILITIES}

## Quick Start

Render a widget to a file.

```python
Widget().render("out.png")
```

## License

MIT.
"""
ROWS = CANDIDATE.splitlines()


def at(text: str) -> int:
    (found,) = [i for i, row in enumerate(ROWS, 1) if text in row]
    return found


def scope(*sections: str) -> ReviewScope:
    """The unit made of ``sections``: their reviewable lines, as ``sectionwise.plan_units`` would."""
    by_line = line_sections(CANDIDATE)
    shown = frozenset(n for n, s in enumerate(by_line, 1) if s in sections)
    return ReviewScope(frozenset(sections), shown)


def cited(kind: str, *span: int, **overrides: Any) -> dict[str, Any]:
    finding = raw_finding(kind, **overrides)
    finding.pop("quote")
    finding["lines"] = list(span)
    return finding


def check(*findings: dict[str, Any], unit: ReviewScope) -> list[str]:
    reply = raw_reply("REJECT_FACTUAL", list(findings))
    problems = resolve_cited_lines(reply, CANDIDATE, unit)
    if problems:
        return problems
    return validate_review_reply(
        reply, candidate_readme=CANDIDATE, facts=FACTS, scope=unit
    )


FIRST, LAST = at("Capability 1."), at("Capability 20.")
OPENING = at("renders widgets to PNG")


# --- only shown lines can be cited ---------------------------------------------------------------


def test_a_line_the_unit_did_not_show_cannot_be_cited_for_any_claim_kind() -> None:
    unit = scope("opening", "key_capabilities")
    install = at("pip install aspose-widget-foss")
    other_unit = at("Render a widget to a file.")
    for kind in ("unsupported_claim", "contradiction", "quality"):
        for line in (install, other_unit, 1):
            problems = check(
                cited(kind, line, section_id="key_capabilities"), unit=unit
            )
            assert any("not shown" in p for p in problems), (kind, line, problems)


def test_a_shown_line_is_citable() -> None:
    unit = scope("opening", "key_capabilities")
    assert check(cited("unsupported_claim", OPENING, fact_ids=[]), unit=unit) == []
    assert check(cited("quality", FIRST), unit=unit) == []


def test_a_span_over_renderer_lines_is_refused_for_the_claim_kinds() -> None:
    unit = scope("opening", "key_capabilities", "quick_start")
    problems = check(
        cited("unsupported_claim", at("Render a widget"), at("Widget().render")),
        unit=unit,
    )
    assert any("not shown" in p or "cross" in p for p in problems)


# --- whole-section citations ----------------------------------------------------------------------


def test_the_claim_kinds_keep_the_twelve_line_cap() -> None:
    unit = scope("key_capabilities")
    assert LAST - FIRST + 1 > MAX_CITED_LINES
    for kind in ("unsupported_claim", "contradiction"):
        problems = check(cited(kind, FIRST, LAST), unit=unit)
        assert any(f"cite at most {MAX_CITED_LINES} lines" in p for p in problems), kind


def test_a_quality_finding_may_cite_the_whole_section() -> None:
    unit = scope("key_capabilities")
    reply = raw_reply("REJECT_PRESENTATION", [cited("quality", FIRST, LAST)])
    assert resolve_cited_lines(reply, CANDIDATE, unit) == []
    assert (
        validate_review_reply(
            reply, candidate_readme=CANDIDATE, facts=FACTS, scope=unit
        )
        == []
    )
    (finding,) = reply["findings"]
    assert finding["section_id"] == "key_capabilities"
    assert ROWS[FIRST - 1] in finding["quote"] and ROWS[LAST - 1] in finding["quote"]


def test_an_omission_or_absence_may_cite_the_whole_section_and_the_cited_text_is_not_a_quote() -> (
    None
):
    unit = scope("key_capabilities")
    omission = cited(
        "omission",
        FIRST,
        LAST,
        omission={
            "kind": "omission",
            "section_id": "key_capabilities",
            "missing_ids": ["format:png"],
            "missing_quotes": [],
        },
    )
    absence = cited("absence", FIRST, LAST, absent=["SvgExporter"], id="F02")
    reply = raw_reply("REJECT_FACTUAL", [omission, absence])
    assert resolve_cited_lines(reply, CANDIDATE, unit) == []
    assert (
        validate_review_reply(
            reply, candidate_readme=CANDIDATE, facts=FACTS, scope=unit
        )
        == []
    )
    # a whole section is a locator, not a quote: otherwise the string it names "shown" in its own
    # quote would make absence_present unusable against a false absence claim
    assert [f["quote"] for f in reply["findings"]] == ["", ""]
    context = ClearanceContext(CANDIDATE, ORIGINAL, FACTS)
    (_, cleared) = [apply_clearances(f, context) for f in findings_from_reply(reply)]
    assert cleared.status == "CLEARED" and cleared.clearance.name == "absence_present"


def test_a_whole_section_cannot_cross_into_another_section() -> None:
    unit = scope("key_capabilities", "quick_start")
    problems = check(cited("quality", FIRST, at("Render a widget")), unit=unit)
    assert any("cross more than one section" in p for p in problems)


def test_the_ends_of_a_whole_section_citation_must_be_shown_lines() -> None:
    unit = scope("key_capabilities")
    problems = check(cited("quality", FIRST, at("Render a widget")), unit=unit)
    assert problems
    problems = check(cited("quality", at("pip install"), LAST), unit=unit)
    assert any("not shown" in p for p in problems)


# --- the finding names a section of its own unit ---------------------------------------------------


def test_an_omission_must_name_a_section_of_its_own_unit() -> None:
    unit = scope("key_capabilities")
    omission = {
        "kind": "omission",
        "section_id": "quick_start",
        "missing_ids": ["format:png"],
        "missing_quotes": [],
    }
    problems = check(
        cited("omission", section_id="quick_start", omission=omission), unit=unit
    )
    assert any("not a section of this review unit" in p for p in problems)


# --- repeated findings are one finding -------------------------------------------------------------


def repeated(count: int, **overrides: Any) -> dict[str, Any]:
    findings = [
        cited(
            "unsupported_claim",
            OPENING,
            id=f"F{n:02d}",
            text=f"complaint {n} about the opening",
            fact_ids=[],
            **overrides,
        )
        for n in range(1, count + 1)
    ]
    return raw_reply("REJECT_FACTUAL", findings)


def test_findings_of_one_kind_on_the_same_lines_are_merged_into_the_first() -> None:
    reply = repeated(4)
    merge_repeated_findings(reply)
    (only,) = reply["findings"]
    assert only["id"] == "F01" and only["text"].startswith("complaint 1")
    assert "+3 identical findings merged" in only["text"]


def test_merging_is_idempotent_and_keeps_the_text_inside_the_schema_bound() -> None:
    reply = repeated(3)
    reply["findings"][0]["text"] = "x" * 590
    merge_repeated_findings(reply)
    once = [dict(f) for f in reply["findings"]]
    merge_repeated_findings(reply)
    assert reply["findings"] == once and len(once[0]["text"]) <= 600


def test_findings_that_differ_in_kind_lines_or_typed_field_are_not_merged() -> None:
    reply = raw_reply(
        "REJECT_FACTUAL",
        [
            cited("unsupported_claim", OPENING, id="F01", fact_ids=[]),
            cited("quality", OPENING, id="F02"),
            cited("unsupported_claim", FIRST, id="F03", fact_ids=[]),
            cited("absence", FIRST, id="F04", absent=["alpha"]),
            cited("absence", FIRST, id="F05", absent=["beta"]),
        ],
    )
    merge_repeated_findings(reply)
    assert [f["id"] for f in reply["findings"]] == ["F01", "F02", "F03", "F04", "F05"]


def test_a_merged_reply_is_still_a_blocking_finding_not_an_accept() -> None:
    unit = scope("opening")
    reply = repeated(5)
    assert resolve_cited_lines(reply, CANDIDATE, unit) == []
    merge_repeated_findings(reply)
    assert (
        validate_review_reply(
            reply, candidate_readme=CANDIDATE, facts=FACTS, scope=unit
        )
        == []
    )
    (finding,) = findings_from_reply(reply)
    assert finding.blocking and finding.claim_kind == "unsupported_claim"
