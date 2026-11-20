"""BL-430: the union of two review samples (``llm_review.merge_second_sample``), offline and zero calls.

Hosted audit rounds 44588173276 and 44656899884: every flagged Lane R control had been accepted at seal by
the production packet and flagged by the audit's packet on the same authored lines. A seal needs both
samples. Negative controls: a finding on a line the renderer printed is not counted, a rejected first sample
is never touched, a clean second sample changes no finding and no verdict byte but its own unit records.
"""

from __future__ import annotations

from typing import Any

import pytest

from repo_presenter.readme.review.llm_review import (
    SECOND_SAMPLE,
    SECOND_SAMPLE_KEY,
    m8_blocking_units,
    merge_second_sample,
    second_sample_lines,
)
from repo_presenter.readme.review.verdict import ReviewVerdict
from tests.readme.review.review_support import CANDIDATE, FACTS, llm

EXPORTS = "Exports SVG through the SvgExporter class."
TITLE = "# Aspose.Widget FOSS for Python"


def _unit(label: str) -> dict[str, Any]:
    return {
        "unit": label, "sections": ["key_capabilities"], "lines": [1, 2, 2], "request_sha256": f"req-{label}",
        "reply_sha256": "r", "model_verdict": "ACCEPT", "findings": 0, "status": "reviewed", "reason": "",
        "m8": {"status": "not_run", "shape": None, "verdict": None},
    }


def _sample(*findings: Any, model_verdict: str = "ACCEPT", unit: str = "u1") -> ReviewVerdict:
    return ReviewVerdict.folded(
        list(findings), model_verdict=model_verdict, prompt_version="21", model_served="qwen3-next",
        request_sha256="a" * 8, reply_sha256="b" * 8, calibration_status="NOT_PASSED",
        unit_reviews=[_unit(unit)],
    )


def merged(first: ReviewVerdict, second: ReviewVerdict) -> ReviewVerdict:
    return merge_second_sample(first, second, candidate_readme=CANDIDATE, facts=FACTS)


def test_the_second_sample_reads_only_the_lines_the_production_review_reads() -> None:
    lines = second_sample_lines(CANDIDATE, FACTS)
    rows = CANDIDATE.splitlines()
    assert lines and all(rows[n - 1].strip() for n in lines)
    assert rows.index(f"- {EXPORTS}") + 1 in lines
    assert 1 not in lines  # the title
    assert rows.index("pip install aspose-widget-foss") + 1 not in lines  # renderer-printed installation


def test_a_blocking_finding_on_authored_text_makes_the_union_reject_and_keeps_both_samples_findings() -> None:
    first = _sample(unit="u1")
    flagged = llm("unsupported_claim", quote=EXPORTS, section_id="key_capabilities", finding_id="F01")
    union = merged(first, _sample(flagged, model_verdict="REJECT_FACTUAL"))

    assert union.verdict == "REJECT"
    assert [(f.finding_id, f.quote) for f in union.blocking_findings] == [("S2-F01", EXPORTS)]
    assert union.model_verdict == "REJECT_FACTUAL" and union.prompt_version == "21"
    assert [r["unit"] for r in union.unit_reviews] == ["u1", "s2-u1"]
    assert union.unit_reviews[1][SECOND_SAMPLE_KEY] == SECOND_SAMPLE and SECOND_SAMPLE_KEY not in union.unit_reviews[0]
    assert m8_blocking_units(union.unit_reviews) == ()  # the second sample's records add no M8 objection


def test_a_clean_second_sample_changes_nothing_but_its_unit_records() -> None:
    first = _sample()
    union = merged(first, _sample(unit="u7"))

    assert union.verdict == "ACCEPT" and union.findings == first.findings == ()
    assert union.request_sha256 == first.request_sha256 and union.model_verdict == first.model_verdict
    assert [r["unit"] for r in union.unit_reviews] == ["u1", "s2-u7"]


@pytest.mark.parametrize("quote", [TITLE, "pip install aspose-widget-foss", "MIT."])
def test_a_finding_on_a_line_the_renderer_printed_is_not_counted(quote: str) -> None:
    first = _sample()
    flagged = llm("unsupported_claim", quote=quote, section_id="installation")
    union = merged(first, _sample(flagged, model_verdict="REJECT_FACTUAL"))

    assert union.verdict == "ACCEPT" and union.blocking_findings == ()
    assert len(union.unit_reviews) == 2  # the sample is still recorded


def test_a_finding_that_quotes_nothing_counts_on_an_authored_section_only() -> None:
    first = _sample()
    authored = llm("omission", quote="", section_id="key_capabilities", omission=("key_capabilities", ("capability:svg",), ()))
    rendered = llm("omission", quote="", section_id="installation", omission=("installation", ("package:name",), ()))

    assert merged(first, _sample(authored, model_verdict="REJECT_COHERENCE")).verdict == "REJECT"
    assert merged(first, _sample(rendered, model_verdict="REJECT_COHERENCE")).verdict == "ACCEPT"


def test_a_rejected_first_sample_is_returned_untouched() -> None:
    first = _sample(llm("quality", finding_id="F01"), model_verdict="REJECT_PRESENTATION")
    second = _sample(llm("unsupported_claim", quote=EXPORTS, finding_id="F01"), model_verdict="REJECT_FACTUAL")
    assert merged(first, second) is first
