"""The independent review of a Lane L candidate judges the FINAL README (plans/PLAN_lane_l_hosted.md
L5; mission section 6), not only the edit delta.

The deterministic holdouts here are model-free and each has a falsifier; the LLM review is the
reviewer's own (`review_with_model`), stubbed at its boundary so these tests prove what Lane L hands
it and when it is never asked, not how the reviewer reasons.
"""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter import lane_l_review as review_module
from repo_presenter.core.facts import Fact
from repo_presenter.lane_l_review import (
    LANE_L_REVIEW_VERSION,
    RULE_CLAIMS,
    RULE_CONFINEMENT,
    RULE_LOSS,
    RULE_NONDETERMINISTIC,
    confinement_findings,
    holdout_findings,
    holdouts_document,
    nondeterminism_findings,
    review_correction,
)
from repo_presenter.readme.correction.apply import apply_edits
from repo_presenter.readme.correction.engine import correct
from repo_presenter.readme.correction.model import CorrectionResult, Edit
from repo_presenter.readme.correction.report import RULE_UNREPAIRED_DEFECT
from repo_presenter.readme.review.verdict import ReviewVerdict
from tests.readme.correction.conftest import base_facts, context, fact
from tests.readme.correction.test_lane_l_report import (
    README,
    TREE,
    broken_link,
    failing_example,
    unit,
)

NOTES_UNIT = unit(
    "inherited_unit:004.paragraph",
    "See [the notes](upstream-issues.md) for details.",
    "7-7",
    "paragraph",
)


def corrected(readme: str = README, *extra: Fact):
    ctx = context(readme, base_facts(*extra), tree=TREE)
    return ctx, correct(ctx)


def rules(findings: Any) -> list[str]:
    return [finding.rule for finding in findings]


# --- the holdouts --------------------------------------------------------------------------------------


def test_a_clean_evidenced_correction_clears_every_holdout() -> None:
    ctx, result = corrected(README, broken_link(), NOTES_UNIT)
    assert result.edits
    assert holdout_findings(ctx, result, deterministic=True) == []


def test_confinement_is_reproved_from_the_edit_list_not_trusted_from_the_engine() -> (
    None
):
    ctx, result = corrected(README, broken_link(), NOTES_UNIT)
    assert confinement_findings(ctx.readme, result) == []

    widened = dataclasses.replace(
        result, corrected=result.corrected + "An unlisted sentence.\n"
    )
    findings = confinement_findings(ctx.readme, widened)
    assert rules(findings) and set(rules(findings)) == {RULE_CONFINEMENT}
    assert all(f.source == "deterministic" and f.blocking for f in findings)

    swapped = dataclasses.replace(
        result, corrected=result.corrected.replace("Product", "Produkt")
    )
    assert confinement_findings(ctx.readme, swapped)  # a changed byte no edit names


def test_the_engines_own_output_spans_are_not_consulted() -> None:
    """The proof recomputes the spans from the edit list. A result that moves the replacement and
    reports spans to match passes the span-and-residue check (the text outside the spans is
    still the original's, and the spans hold the replacement), yet is not the original with the
    edits applied; only rebuilding from the edits sees it."""
    edit = Edit(
        kind="BROKEN_LINK",
        detector="broken_link",
        start=0,
        end=3,
        original="foo",
        replacement="qux",
        fact_ids=("link_target:001",),
        rationale="r",
    )
    honest = CorrectionResult("foo bar", "qux bar", [edit], [(0, 3)])
    assert confinement_findings("foo bar", honest) == []

    lying = CorrectionResult("foo bar", " barqux", [edit], [(4, 7)])
    assert apply_edits("foo bar", [edit])[0] == "qux bar" != lying.corrected
    findings = confinement_findings("foo bar", lying)
    assert any("not the original with the edits applied" in f.message for f in findings)


def test_non_determinism_blocks_because_no_rerun_could_ever_be_proven() -> None:
    assert nondeterminism_findings(True) == []
    (finding,) = nondeterminism_findings(False)
    assert finding.rule == RULE_NONDETERMINISTIC and finding.blocking


def test_a_dropped_part_of_the_live_readme_is_loss_unless_an_evidenced_edit_accounts_for_it() -> (
    None
):
    """The retention holdout against the live README. Here the engine's own link repair changes the
    link target; with the inherited unit on record the edit accounts for the change, and without it
    the very same correction is reported as a loss: the accounting is what saves it."""
    ctx, result = corrected(README, broken_link(), NOTES_UNIT)
    assert RULE_LOSS not in rules(holdout_findings(ctx, result, deterministic=True))

    no_units = context(README, base_facts(broken_link()), tree=TREE)
    again = correct(no_units)
    lost = holdout_findings(no_units, again, deterministic=True)
    assert RULE_LOSS in rules(lost)
    assert any("upstream-issues.md" in f.message for f in lost)


def test_a_claim_in_the_final_readme_that_contradicts_a_verified_fact_blocks() -> None:
    wrong = README.replace(
        "```java\nWidget.render();\n```",
        "```bash\nmvn dependency:get -Dartifact=org.aspose:wrong-name:26.7.0\n```",
    )
    facts = (
        fact(
            "install_command:maven",
            "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0",
            attributes={"install_kind": "registry"},
            evidence=(("pom.xml", None),),
        ),
    )
    ctx, result = corrected(wrong, *facts)
    claims = [
        f
        for f in holdout_findings(ctx, result, deterministic=True)
        if f.rule == RULE_CLAIMS
    ]
    # whatever the claim check decides, it is the final text it decides on
    assert all(f.source == "deterministic" and f.blocking for f in claims)


def test_an_unrepaired_defect_is_a_blocking_finding_that_names_lane_r() -> None:
    ctx, result = corrected(README, failing_example())
    findings = holdout_findings(ctx, result, deterministic=True)
    assert RULE_UNREPAIRED_DEFECT in rules(findings)
    (defect,) = [f for f in findings if f.rule == RULE_UNREPAIRED_DEFECT]
    assert "Lane R" in defect.repair and defect.blocking


def test_the_document_records_each_check_and_keeps_idempotence_non_blocking() -> None:
    ctx, result = corrected(README, failing_example())
    findings = holdout_findings(ctx, result, deterministic=True)
    document = holdouts_document(findings, idempotent=False, source_revision="f" * 40)
    by_id = {check["id"]: check for check in document["checks"]}
    assert by_id["L-05"]["verdict"] == "FAIL" and by_id["L-05"]["details"]
    assert by_id["L-01"]["verdict"] == "PASS"
    assert by_id["L-06"]["verdict"] == "FAIL"  # recorded ...
    assert rules(findings) == [RULE_UNREPAIRED_DEFECT]  # ... but it blocks nothing
    assert document["review_logic_version"] == LANE_L_REVIEW_VERSION
    assert document["summary"] == {"pass": 4, "fail": 2}
    assert document["lane"] == "L" and document["source_revision"] == "f" * 40


# --- the review itself ----------------------------------------------------------------------------------


class Recorder:
    """Stands in for ``review_with_model``: records what it was handed and returns a verdict."""

    def __init__(self, verdict: ReviewVerdict) -> None:
        self.verdict = verdict
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> ReviewVerdict:
        self.calls.append(kwargs)
        return self.verdict


ACCEPT = ReviewVerdict.folded(
    (),
    model_verdict="ACCEPT",
    prompt_version="16",
    model_served="qwen3-next",
    request_sha256="a" * 64,
    reply_sha256="b" * 64,
)
PLUMBING = {
    "prompts": SimpleNamespace(),
    "config": SimpleNamespace(),
    "ledger": SimpleNamespace(),
    "store": SimpleNamespace(),
    "context": SimpleNamespace(),
}


def review(
    ctx: Any, result: CorrectionResult, findings: list, holdouts: dict
) -> ReviewVerdict:
    return review_correction(
        ctx=ctx,
        result=result,
        findings=findings,
        holdouts=holdouts,
        facts=ctx.facts,
        **PLUMBING,
    )


def test_the_model_is_handed_the_final_readme_the_live_one_the_edits_and_the_holdouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder(ACCEPT)
    monkeypatch.setattr(review_module, "review_with_model", recorder)
    ctx, result = corrected(README, broken_link(), NOTES_UNIT)
    holdouts = holdouts_document([], idempotent=True, source_revision="f" * 40)

    verdict = review(ctx, result, [], holdouts)

    (call,) = recorder.calls
    assert verdict is ACCEPT  # the reviewer's own verdict, returned unchanged
    assert call["candidate_readme"] == result.corrected  # the FINAL text, whole
    assert call["original_readme"] == README
    assert "docs/upstream-issues.md" in call["candidate_readme"]
    assert call["plan"] == {"sections": []}
    assert call["validation"] is holdouts
    assert call["deterministic_findings"] == ()
    (row,) = call["dispositions"]["dispositions"]
    assert row["unit_id"] == "inherited_unit:004.paragraph"
    assert row["disposition"] == "CORRECT_WITH_EVIDENCE"
    assert call["facts"] is ctx.facts


def test_the_model_is_never_asked_when_a_deterministic_holdout_already_rejects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = Recorder(ACCEPT)
    monkeypatch.setattr(review_module, "review_with_model", recorder)
    ctx, result = corrected(README, failing_example())
    findings = holdout_findings(ctx, result, deterministic=True)
    assert findings

    verdict = review(
        ctx,
        result,
        findings,
        holdouts_document(findings, idempotent=True, source_revision="f" * 40),
    )

    assert recorder.calls == []  # no spend on a candidate a cheaper rule rejects
    assert verdict.verdict == "REJECT" and not verdict.model_reviewed
    assert verdict.blocking_findings == tuple(findings)


def test_a_no_change_candidate_is_still_put_to_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing to correct is not nothing to review: the live README is the candidate, and it is
    judged before it is sealed as NO_CHANGE_WARRANTED."""
    recorder = Recorder(ACCEPT)
    monkeypatch.setattr(review_module, "review_with_model", recorder)
    ctx, result = corrected(README)
    assert result.edits == []
    review(
        ctx,
        result,
        [],
        holdouts_document([], idempotent=True, source_revision="f" * 40),
    )
    (call,) = recorder.calls
    assert call["candidate_readme"] == call["original_readme"] == README


def test_a_reviewers_veto_is_returned_not_overruled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from repo_presenter.readme.review.independent_reviewer import Finding

    rejected = ReviewVerdict.folded(
        (
            Finding(
                rule="llm:x",
                source="llm",
                message="m",
                claim_kind="quality",
                finding_id="F01",
                section_id="opening",
                causal_stage="S6",
                criterion="specificity",
            ),
        ),
        model_verdict="REJECT_PRESENTATION",
        prompt_version="16",
        model_served="qwen3-next",
        request_sha256="a" * 64,
        reply_sha256="b" * 64,
    )
    monkeypatch.setattr(review_module, "review_with_model", Recorder(rejected))
    ctx, result = corrected(README, broken_link(), NOTES_UNIT)
    verdict = review(
        ctx,
        result,
        [],
        holdouts_document([], idempotent=True, source_revision="f" * 40),
    )
    assert verdict is rejected and verdict.verdict == "REJECT"
