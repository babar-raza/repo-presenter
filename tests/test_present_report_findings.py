"""A rejected candidate's blocking findings reach the job log (hosted artifacts are not always readable)."""

from __future__ import annotations

import io
from types import SimpleNamespace

from repo_presenter.present import report_findings
from repo_presenter.readme.review.findings import Finding


def test_each_blocking_finding_is_printed_with_its_quote() -> None:
    finding = Finding(
        rule="unsupported_claim",
        source="llm",
        message="no fact supports the claim",
        claim_kind="quality",
        quote="Works on every platform",
        finding_id="F01",
        section_id="scope_limitations",
    )
    out = io.StringIO()
    report_findings(SimpleNamespace(blocking_findings=[finding]), out=out)
    text = out.getvalue()
    assert "F01 [unsupported_claim] section=scope_limitations" in text
    assert "Works on every platform" in text


def test_no_findings_prints_nothing() -> None:
    out = io.StringIO()
    report_findings(SimpleNamespace(blocking_findings=[]), out=out)
    assert out.getvalue() == ""
