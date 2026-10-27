"""The metrics harness and its gate, run offline with stub and scripted reviewers."""

from __future__ import annotations

import itertools

import pytest

from repo_presenter.readme.review.calibration.corpus import Base, build_corpus
from repo_presenter.readme.review.calibration.harness import (
    ACCEPT,
    REJECT,
    UNAVAILABLE,
    BudgetExhausted,
    ReviewOutcome,
    compute_metrics,
    corpus_gate_passes,
    evaluate_gates,
    run_corpus,
)
from repo_presenter.readme.review.calibration.reviewers import (
    always_accept,
    always_reject,
    oracle,
)
from tests.readme.review.calibration.synthetic import make_source


@pytest.fixture
def cases(tmp_path):
    return build_corpus([Base(make_source(tmp_path))])


def failed(metrics, scope="llm"):
    return {g.name for g in evaluate_gates(metrics, scope=scope) if not g.passed}


RECALL = {
    "recall[contradiction]",
    "recall[content_loss]",
    "recall[unsupported_claim]",
    "recall[broken_install]",
}


def test_a_reviewer_that_accepts_everything_fails_the_corpus_gate_on_every_recall(
    cases,
):
    metrics = compute_metrics(run_corpus(cases, always_accept, repeats=2))
    assert not corpus_gate_passes(metrics)
    assert RECALL <= failed(metrics)
    assert metrics.false_reject_rate == 0.0 and metrics.approved_yield == 1.0
    assert all(stats.llm_recall() == 0.0 for stats in metrics.per_class.values())


def test_a_reviewer_that_rejects_everything_fails_the_corpus_gate_on_false_rejects(
    cases,
):
    metrics = compute_metrics(run_corpus(cases, always_reject, repeats=2))
    assert not corpus_gate_passes(metrics)
    assert "false_reject_rate" in failed(metrics)
    assert metrics.false_reject_rate == 1.0 and metrics.approved_yield == 0.0
    # Rejecting everything catches every defect by verdict alone ...
    verdict_gates = evaluate_gates(metrics, basis="verdict")
    assert not any(g.name in RECALL and not g.passed for g in verdict_gates)
    # ... and none of them on target: it never says what is wrong.
    assert RECALL <= failed(metrics)


def test_the_pipeline_scope_also_fails_both_stubs(cases):
    accept = compute_metrics(run_corpus(cases, always_accept, repeats=2))
    reject = compute_metrics(run_corpus(cases, always_reject, repeats=2))
    assert not corpus_gate_passes(accept, scope="pipeline")
    assert "recall[unsupported_claim]" in failed(accept, "pipeline")
    assert "false_reject_rate" in failed(reject, "pipeline")


def test_a_correct_reviewer_passes_every_gate(cases):
    metrics = compute_metrics(run_corpus(cases, oracle, repeats=3))
    assert corpus_gate_passes(metrics) and corpus_gate_passes(metrics, scope="pipeline")
    assert metrics.false_reject_rate == 0.0 and metrics.approved_yield == 1.0
    assert metrics.stability == 1.0 and metrics.json_valid_first_reply_rate == 1.0


def test_the_pipeline_catches_what_the_deterministic_stage_catches_even_if_the_model_accepts(
    cases,
):
    metrics = compute_metrics(run_corpus(cases, always_accept))
    broken = metrics.per_class["broken_install"]
    assert broken.llm_recall() == 0.0 and broken.pipeline_recall() == 1.0
    assert metrics.per_class["unsupported_claim"].pipeline_recall() == 0.0
    assert (
        metrics.content_loss_rate == 1.0
    )  # nothing deterministic sees a dropped section here


def test_an_unavailable_review_is_in_the_denominator_and_never_a_catch(cases):
    metrics = compute_metrics(
        run_corpus(cases, lambda case: ReviewOutcome(UNAVAILABLE))
    )
    for stats in metrics.per_class.values():
        assert stats.llm_rejected == 0 and stats.unavailable == stats.n
    assert metrics.clean_unavailable == metrics.clean_n == 1
    assert metrics.false_reject_rate == 0.0 and metrics.clean_accepted == 0


def test_per_class_recall_is_computed_per_class(cases):
    caught = {"inject_unsupported_claim", "contradict_version"}

    def reviewer(case):
        return ReviewOutcome(REJECT if case.operator in caught else ACCEPT)

    metrics = compute_metrics(run_corpus(cases, reviewer))
    assert metrics.per_class["unsupported_claim"].llm_recall() == 1.0
    assert metrics.per_class["contradiction"].llm_recall() == pytest.approx(1 / 3)
    assert metrics.per_class["invented_api"].llm_recall() == 0.0


def test_stability_is_the_share_of_repeated_cases_with_one_verdict(cases):
    flip = itertools.count()

    def reviewer(case):
        if case.operator == "contradict_version":
            return ReviewOutcome(REJECT if next(flip) % 2 == 0 else ACCEPT)
        return ReviewOutcome(ACCEPT)

    metrics = compute_metrics(run_corpus(cases, reviewer, repeats=2))
    assert metrics.repeated_cases == len(cases)
    assert metrics.stable_cases == len(cases) - 1
    assert metrics.stability == pytest.approx((len(cases) - 1) / len(cases))


def test_first_reply_validity_is_measured_only_over_replies_that_were_sent(cases):
    def reviewer(case):
        if case.role == "clean":
            return ReviewOutcome(
                ACCEPT, 2, first_reply_json_valid=True, first_reply_contract_valid=False
            )
        return ReviewOutcome(ACCEPT, 0)

    metrics = compute_metrics(run_corpus(cases, reviewer))
    assert metrics.first_replies == 1 and metrics.json_valid_first_reply_rate == 1.0
    assert metrics.contract_valid_first_reply_rate == 0.0
    assert metrics.calls == 2 and metrics.cases_asked == len(cases)


def test_a_gate_with_no_measurement_fails(cases):
    metrics = compute_metrics(run_corpus(cases, oracle, repeats=1))
    assert "stability" in failed(metrics)
    empty = compute_metrics(run_corpus([], oracle))
    assert failed(empty) == RECALL | {
        "false_reject_rate",
        "json_valid_first_reply",
        "stability",
    }


def test_a_budget_stop_keeps_the_answered_cases_and_says_why(cases):
    asked = []

    def reviewer(case):
        if len(asked) == 3:
            raise BudgetExhausted("200 provider calls made; the cap is 200")
        asked.append(case.case_id)
        return ReviewOutcome(ACCEPT)

    run = run_corpus(cases, reviewer)
    assert [r.case.case_id for r in run.results] == asked and len(asked) == 3
    assert "cap is 200" in run.stopped


def test_content_loss_rate_is_the_share_of_dropped_sections_the_pipeline_approves(
    tmp_path,
):
    from repo_presenter.readme.review.calibration.harness import CaseResult, PreLLM, Run

    cases = build_corpus([Base(make_source(tmp_path))])
    loss = next(c for c in cases if c.klass == "content_loss")
    results = (
        CaseResult(loss, PreLLM((), ()), (ReviewOutcome(ACCEPT),)),
        CaseResult(loss, PreLLM(("live_readme_loss",), ()), (ReviewOutcome(ACCEPT),)),
    )
    assert compute_metrics(Run(results)).content_loss_rate == 0.5


def test_a_rejection_for_another_reason_is_not_a_catch(cases):
    def reviewer(case):
        if case.role == "clean":
            return ReviewOutcome(ACCEPT)
        return ReviewOutcome(
            REJECT, evidence=("something unrelated about the license",)
        )

    metrics = compute_metrics(run_corpus(cases, reviewer))
    stats = metrics.per_class["contradiction"]
    assert stats.llm_recall() == 1.0 and stats.llm_target_recall() == 0.0
    assert stats.pipeline_target_recall() <= stats.pipeline_recall()


def test_a_rejection_that_names_the_defect_is_a_catch(cases):
    def reviewer(case):
        if case.role == "clean":
            return ReviewOutcome(ACCEPT)
        return ReviewOutcome(
            REJECT, evidence=("the text says " + case.targets[0] + " here",)
        )

    metrics = compute_metrics(run_corpus(cases, reviewer))
    assert all(s.llm_target_recall() == 1.0 for s in metrics.per_class.values())
    assert corpus_gate_passes(replace_stability(metrics))


def replace_stability(metrics):
    from dataclasses import replace

    return replace(
        metrics,
        first_replies=1,
        first_reply_json_valid=1,
        repeated_cases=1,
        stable_cases=1,
    )
