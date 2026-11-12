"""R21: Lane L accepts on net improvement; pre-existing residuals are recorded, never blocking.

Real shapes: the count lines are verbatim from aspose-html-foss/Aspose.HTML-FOSS-for-Python's live
README (243 stated, 303 recorded) and the absent-row finding is the HTML seal's own L-03 shape
("the API table lists `CSSDeclarationBlock`, but no public_symbol fact states it"). With the count
edit applied, the absent-row contradiction is one the live README ALREADY carried and no edit can
delete (the edit model is a one-line fragment replace): it is a residual, not a blocker.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from repo_presenter.lane_l_review import (
    RULE_CLAIMS,
    holdout_findings,
    holdouts_document,
    net_improvement,
    split_claim_contradictions,
)
from repo_presenter.readme.correction.engine import correct, is_stable
from repo_presenter.readme.correction.model import Edit

COUNT_LINE = (
    "The library exposes 243 public types in total, listed below by module, with curated "
    "highlights following.\n"
)
TABLE = (
    "| Type | Description |\n"
    "|---|---|\n"
    "| `C0` | zero |\n"
    "| `C1` | one |\n"
    "| `C2` | two |\n"
    "| `C3` | three |\n"
    "| `CSSDeclarationBlock` | a type the public surface does not contain |\n"
)
README = "# Aspose.HTML FOSS for Python\n\n" + COUNT_LINE + "\n" + TABLE


def _symbols(make_fact: Any, classes: int) -> list[Any]:
    return [
        make_fact(
            f"public_symbol:pkg.c{i}", f"C{i}",
            evidence=((f"src/c{i}.py", f"line 1; class; C{i}"),),
            attributes={"symbol_kind": "class"},
        )
        for i in range(classes)
    ]


def _run(make_context: Any, make_facts: Any, make_fact: Any, readme: str = README, classes: int = 303):
    ctx = make_context(readme, make_facts(*_symbols(make_fact, classes)))
    result = correct(ctx)
    deterministic, _idempotent = is_stable(ctx, result)
    return ctx, result, holdout_findings(ctx, result, deterministic=deterministic)


def test_the_absent_row_is_a_residual_when_the_count_edit_made_the_run_a_net_improvement(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx, result, findings = _run(make_context, make_facts, make_fact)
    assert [(e.original, e.replacement) for e in result.edits] == [("243", "303")]
    assert net_improvement(ctx, result)
    assert [f for f in findings if f.rule == RULE_CLAIMS] == []  # L-03 no longer blocks
    assert findings == []
    (row,) = [r for r in findings.residuals if r["kind"] == "claim_contradiction"]
    assert "CSSDeclarationBlock" in row["detail"] and row["rule"] == RULE_CLAIMS
    assert row["line"] is not None


def test_residuals_are_recorded_in_the_holdouts_document_and_never_in_the_readme(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx, result, findings = _run(make_context, make_facts, make_fact)
    document = holdouts_document(findings, idempotent=True, source_revision="0" * 40)
    assert document["summary"]["fail"] == 0
    assert any("CSSDeclarationBlock" in r["detail"] for r in document["residuals"])
    assert "residual" not in result.corrected.lower()  # R9: the README text carries no such wording
    assert result.corrected == README.replace("243", "303")  # only the evidenced edit changed it


def test_without_any_edit_the_same_contradiction_still_blocks(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx, result, findings = _run(make_context, make_facts, make_fact, classes=243)
    assert result.edits == []  # the count is already right: nothing to improve
    assert not net_improvement(ctx, result)
    assert [f.rule for f in findings] == [RULE_CLAIMS]  # unchanged behavior: blocks
    assert findings.residuals == []
    assert "residuals" not in holdouts_document(findings, idempotent=True, source_revision="0")


def test_a_contradiction_an_edit_creates_blocks_and_denies_net_improvement(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx, result, _ = _run(make_context, make_facts, make_fact)
    # An edit that rewrites the count to something the facts still refute is a NEW contradiction.
    bad = dataclasses.replace(
        result,
        edits=[dataclasses.replace(result.edits[0], replacement="999")],
        corrected=README.replace("243", "999"),
    )
    carried, introduced = split_claim_contradictions(ctx, bad)
    assert introduced  # the 999 count contradiction is new
    assert all("CSSDeclarationBlock" not in f.evidence for f in introduced)
    assert any("CSSDeclarationBlock" in f.evidence for f in carried)  # the absent row is not
    assert not net_improvement(ctx, bad)
    deterministic = True
    findings = holdout_findings(ctx, bad, deterministic=deterministic)
    assert any(f.rule == RULE_CLAIMS for f in findings)
    assert findings.residuals == []


def test_a_second_copy_of_a_preexisting_contradiction_counts_as_introduced(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx, result, _ = _run(make_context, make_facts, make_fact)
    doubled_table = TABLE + "| `CSSDeclarationBlock` | listed twice |\n"
    forged = dataclasses.replace(result, corrected=README.replace("243", "303") + "\n" + doubled_table)
    _carried, introduced = split_claim_contradictions(ctx, forged)
    assert introduced, "a second occurrence is a new defect, not the pre-existing one"


def test_the_edit_set_must_be_byte_preserving_outside_its_hunks(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx, result, _ = _run(make_context, make_facts, make_fact)
    tampered = dataclasses.replace(result, corrected=result.corrected + "extra line\n")
    assert not net_improvement(ctx, tampered)


def test_an_unrepaired_defect_is_a_residual_row_when_the_run_improves() -> None:
    from tests.readme.correction.test_lane_l_report import README as REPORT_README
    from tests.readme.correction.test_lane_l_report import broken_link, failing_example
    from tests.readme.correction.test_net_improvement import NOTES_UNIT, corrected

    ctx, result = corrected(REPORT_README, broken_link(), NOTES_UNIT, failing_example())
    findings = holdout_findings(ctx, result, deterministic=True)
    assert findings == []
    (row,) = [r for r in findings.residuals if r["kind"] == "unrepaired_defect"]
    assert row["detail"].startswith("failing_example")
    document = holdouts_document(findings, idempotent=True, source_revision="0" * 40)
    assert document["residuals"] == findings.residuals
