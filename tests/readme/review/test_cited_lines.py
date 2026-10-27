"""Phase 3b contract changes (investigation 2026-10-27, iteration 1 causes):

* the model cites candidate LINES and code derives the quote and the section, so a paraphrased or
  wrongly-sectioned quote is no longer something a model can produce;
* an ``unsupported_claim`` (and a ``quality`` finding) has no product fact to cite by definition, so
  the contract no longer demands one -- a ``contradiction`` still does;
* an ``unsupported_claim`` carries a mechanical audit of its distinctive terms, which never clears it;
* a ``quality`` finding against text the renderer owns is a scope error, not a finding.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any

import pytest

from repo_presenter.readme.review.clearances import ClearanceContext, apply_clearances
from repo_presenter.readme.review.reply import (
    findings_from_reply,
    resolve_cited_lines,
    review_from_reply,
    validate_review_reply,
)
from tests.readme.review.review_support import (
    CANDIDATE,
    FACTS,
    ORIGINAL,
    raw_finding,
    raw_reply,
)

LINES = CANDIDATE.splitlines()


def at(text: str) -> int:
    """The 1-based line of ``CANDIDATE`` that holds ``text``."""
    (found,) = [i for i, line in enumerate(LINES, 1) if text in line]
    return found


def cited(kind: str = "quality", *span: int, **overrides: Any) -> dict[str, Any]:
    """A finding as the call schema shapes it: ``lines`` and no ``quote``."""
    finding = raw_finding(kind, **overrides)
    finding.pop("quote")
    finding["lines"] = list(span)
    return finding


def resolved(*findings: dict[str, Any], candidate: str = CANDIDATE):
    reply = raw_reply("REJECT_FACTUAL", list(findings))
    return reply, resolve_cited_lines(reply, candidate)


def errors(reply: Any) -> list[str]:
    return validate_review_reply(reply, candidate_readme=CANDIDATE, facts=FACTS)


# ---------------------------------------------------------------------------
# lines -> quote and section
# ---------------------------------------------------------------------------


def test_code_derives_the_exact_quote_from_the_cited_line() -> None:
    n = at("SvgExporter class")
    reply, problems = resolved(cited("quality", n, n))
    assert problems == []
    assert (
        reply["findings"][0]["quote"] == "- Exports SVG through the SvgExporter class."
    )
    assert errors(reply) == []


def test_a_single_number_cites_one_line_and_a_span_cites_several() -> None:
    n = at("Renders a Widget")
    one, _ = resolved(cited("quality", n))
    assert one["findings"][0]["quote"] == LINES[n - 1]
    two, _ = resolved(cited("quality", n, n + 1))
    assert two["findings"][0]["quote"] == "\n".join(LINES[n - 1 : n + 1])


def test_code_derives_the_section_and_overrides_the_models_label() -> None:
    n = at("pip install aspose-widget-foss")
    reply, problems = resolved(
        cited(
            "contradiction",
            n,
            section_id="key_capabilities",
            criterion="factuality",
            fact_ids=["package:name"],
        )
    )
    assert problems == []
    assert reply["findings"][0]["section_id"] == "installation"
    assert errors(reply) == []


def test_lines_before_the_first_heading_are_the_opening_and_a_heading_is_structure() -> (
    None
):
    reply, _ = resolved(
        cited("quality", at("renders widgets to PNG"), section_id="license")
    )
    assert reply["findings"][0]["section_id"] == "opening"
    reply, _ = resolved(cited("quality", at("## Installation"), section_id="license"))
    assert reply["findings"][0]["section_id"] == "structure"


def test_a_typed_finding_keeps_the_section_it_names() -> None:
    n = at("SvgExporter class")
    reply, problems = resolved(
        cited("absence", n, absent=["PluginHost"], section_id="quick_start")
    )
    assert problems == []
    assert reply["findings"][0]["section_id"] == "quick_start"
    assert reply["findings"][0]["quote"] == LINES[n - 1]


@pytest.mark.parametrize(
    ("span", "fragment"),
    [
        ((0, 1), "line numbers start at 1"),
        ((1, 9999), "the candidate has"),
        ((5, 4), "first line after the last"),
        ((1, 20), "at most"),
        (("a", 2), "whole numbers"),
        ((True, 2), "whole numbers"),
        ((1, 2, 3), "one or two"),
    ],
)
def test_an_impossible_citation_is_refused_with_the_reason(
    span: tuple[Any, ...], fragment: str
) -> None:
    _, problems = resolved(cited("quality", *span))
    assert any(fragment in problem for problem in problems), problems


def test_a_citation_of_only_blank_lines_is_refused() -> None:
    blank = next(i for i, line in enumerate(LINES, 1) if not line.strip())
    _, problems = resolved(cited("quality", blank))
    assert any("blank" in problem for problem in problems), problems


def test_a_span_across_two_sections_is_refused() -> None:
    _, problems = resolved(cited("quality", at("SvgExporter class"), at("from aspose")))
    assert any("more than one section" in problem for problem in problems), problems


def test_resolving_twice_changes_nothing_so_a_stored_reply_replays_identically() -> (
    None
):
    reply, _ = resolved(cited("quality", at("SvgExporter class")))
    again = copy.deepcopy(reply)
    assert resolve_cited_lines(again, CANDIDATE) == []
    assert again == reply


def test_a_model_supplied_quote_beside_lines_is_replaced_never_trusted() -> None:
    n = at("SvgExporter class")
    finding = cited("quality", n)
    finding["quote"] = "a paraphrase the candidate never contains"
    reply, problems = resolved(finding)
    assert problems == [] and errors(reply) == []
    assert reply["findings"][0]["quote"] == LINES[n - 1]


def test_a_model_supplied_quote_without_lines_is_still_checked_verbatim() -> None:
    finding = raw_finding("quality", quote="a paraphrase the candidate never contains")
    assert any(
        "quote is not" in e for e in errors(raw_reply("REJECT_FACTUAL", [finding]))
    )


@pytest.mark.parametrize("kind", ["contradiction", "unsupported_claim"])
def test_a_quoted_kind_must_cite_lines(kind: str) -> None:
    reply, _ = resolved(cited(kind, criterion="factuality", fact_ids=["format:png"]))
    assert any("must quote the candidate text" in e for e in errors(reply)), errors(
        reply
    )


# ---------------------------------------------------------------------------
# the fact rule (iteration 1 cause 5.2)
# ---------------------------------------------------------------------------


def test_an_unsupported_claim_needs_a_quote_and_no_product_fact() -> None:
    n = at("SvgExporter class")
    for criterion in ("factuality", "specificity"):
        reply, _ = resolved(
            cited("unsupported_claim", n, criterion=criterion, fact_ids=[])
        )
        assert errors(reply) == [], criterion


def test_a_quality_finding_needs_no_product_fact_even_under_factuality() -> None:
    reply, _ = resolved(
        cited("quality", at("SvgExporter class"), criterion="factuality", fact_ids=[])
    )
    assert errors(reply) == []


@pytest.mark.parametrize("criterion", ["factuality", "completeness", "coherence"])
def test_a_contradiction_still_cites_a_product_fact(criterion: str) -> None:
    n = at("SvgExporter class")
    reply, _ = resolved(cited("contradiction", n, criterion=criterion, fact_ids=[]))
    assert any("at least one product fact" in e for e in errors(reply)), errors(reply)
    inherited = ["inherited_unit:001.paragraph"]
    reply, _ = resolved(
        cited("contradiction", n, criterion=criterion, fact_ids=inherited)
    )
    assert any("at least one product fact" in e for e in errors(reply))
    reply, _ = resolved(
        cited("contradiction", n, criterion=criterion, fact_ids=["format:png"])
    )
    assert errors(reply) == []


def test_the_other_factuality_kinds_still_cite_a_product_fact() -> None:
    n = at("SvgExporter class")
    reply, _ = resolved(
        cited(
            "name_denial",
            n,
            criterion="factuality",
            fact_ids=[],
            unsupported_names=["Widget"],
        )
    )
    assert any("at least one product fact" in e for e in errors(reply))


# ---------------------------------------------------------------------------
# the audit of an unsupported claim, and why it clears nothing
# ---------------------------------------------------------------------------


def audit_of(quote_line: str, candidate: str, original: str = ORIGINAL) -> str:
    lines = candidate.splitlines()
    n = next(i for i, line in enumerate(lines, 1) if quote_line in line)
    finding = cited("unsupported_claim", n, criterion="factuality", fact_ids=[])
    reply = raw_reply("REJECT_FACTUAL", [finding])
    assert resolve_cited_lines(reply, candidate) == []
    verdict = review_from_reply(
        reply,
        candidate_readme=candidate,
        original_readme=original,
        facts=FACTS,
        plan=None,
        deterministic_findings=(),
        prompt_version="16",
        model_served="qwen3-next",
        request_sha256="r" * 64,
        reply_sha256="p" * 64,
    )
    (only,) = verdict.findings
    assert only.status == "BLOCKING" and verdict.verdict == "REJECT"
    return only.evidence


def test_the_audit_lists_the_distinctive_terms_found_in_no_supported_fact_or_readme() -> (
    None
):
    candidate = CANDIDATE.replace(
        "- Exports SVG through the SvgExporter class.",
        "- Delivers 10x speed through the FooBarEngine class.",
    )
    text = audit_of("10x speed", candidate)
    assert "FooBarEngine" in text and "10x" in text
    assert "no SUPPORTED fact value" in text and "original README" in text


def test_the_audit_names_the_supported_fact_a_term_occurs_in_and_still_blocks() -> None:
    """The 27-of-30 negative control: every distinctive term of the quote is a SUPPORTED fact
    value, and the finding still blocks, because the audit is information and not a clearance."""
    text = audit_of("SvgExporter class", CANDIDATE)
    assert "SvgExporter" in text and "public_symbol:svgexporter" in text
    assert "no registered clearance" in text


def test_a_claim_with_no_distinctive_term_says_so() -> None:
    candidate = CANDIDATE.replace(
        "- Exports SVG through the SvgExporter class.",
        "- Has full round-trip fidelity.",
    )
    assert "no distinctive term" in audit_of("round-trip", candidate)


def test_an_unsupported_claim_is_never_cleared_whatever_its_terms() -> None:
    n = at("SvgExporter class")
    finding = cited(
        "unsupported_claim",
        n,
        criterion="factuality",
        fact_ids=["public_symbol:svgexporter"],
    )
    reply = raw_reply("REJECT_FACTUAL", [finding])
    resolve_cited_lines(reply, CANDIDATE)
    (found,) = findings_from_reply(reply)
    assert (
        apply_clearances(found, ClearanceContext(CANDIDATE, ORIGINAL, FACTS)) == found
    )
    assert replace(found).blocking


# ---------------------------------------------------------------------------
# renderer-owned text
# ---------------------------------------------------------------------------


def test_a_quality_finding_against_renderer_owned_text_is_a_scope_error() -> None:
    n = at("pip install aspose-widget-foss")
    reply, _ = resolved(cited("quality", n, criterion="presentation"))
    found = errors(reply)
    assert any("renderer owns" in e and "installation" in e for e in found), found


def test_a_factual_finding_against_renderer_owned_text_is_still_valid() -> None:
    n = at("pip install aspose-widget-foss")
    reply, _ = resolved(
        cited("contradiction", n, criterion="factuality", fact_ids=["package:name"])
    )
    assert errors(reply) == []


def test_a_quality_finding_against_authored_text_is_still_valid() -> None:
    reply, _ = resolved(
        cited("quality", at("SvgExporter class"), criterion="specificity")
    )
    assert errors(reply) == []
