"""The two-tier gate (project/state.yaml INDEPENDENT_LLM_REVIEWER.gate_semantics_decision_2026_10_27).

The mission's veto is a PIPELINE property. Tier 1: every class code can decide (a wrong version,
package name or format, a broken install, content loss, an invented name, a repeated paragraph) needs
0.90 recall from the deterministic stage plus the reviewer combined; the reviewer-alone number is
reported beside it. Tier 2: the classes only a model can judge (an unsupported prose claim, a subtle
contradiction, quality) keep the 0.90 target on the reviewer ALONE; a shortfall is declared, not
hidden, and an owner may accept it. Both numbers are always reported.
"""

from __future__ import annotations

import pytest

from repo_presenter.readme.review.calibration.corpus import Base, build_corpus
from repo_presenter.readme.review.calibration.harness import (
    DEFECT_TIERS,
    LLM_ONLY,
    PIPELINE,
    ReviewOutcome,
    compute_metrics,
    defect_label,
    evaluate_tiers,
    run_corpus,
)
from repo_presenter.readme.review.calibration.mutations import OPERATORS
from repo_presenter.readme.review.calibration.outcomes import ACCEPT, REJECT
from repo_presenter.readme.review.calibration.reviewers import (
    always_accept,
    always_reject,
    oracle,
)
from tests.readme.review.calibration.synthetic import make_source


@pytest.fixture
def cases(tmp_path):
    return build_corpus([Base(make_source(tmp_path))])


def report(cases, reviewer, repeats=1):
    return evaluate_tiers(compute_metrics(run_corpus(cases, reviewer, repeats=repeats)))


def names(gates):
    return {g.name for g in gates if g.passed}


def test_every_mutation_operator_is_assigned_a_tier() -> None:
    assert {op for op in OPERATORS} <= set(DEFECT_TIERS)
    assert set(DEFECT_TIERS.values()) == {PIPELINE, LLM_ONLY}
    # the classes code decides are tier 1, the ones only a model judges are tier 2
    for label in (
        "contradict_version",
        "contradict_package_name",
        "contradict_format",
        "break_install_command",
        "drop_section",
        "invent_api_name",
        "duplicate_paragraph",
    ):
        assert DEFECT_TIERS[label] == PIPELINE, label
    for label in (
        "inject_unsupported_claim",
        "add_promotional_filler",
        "real:unsupported_claim",
        "real:contradiction",
    ):
        assert DEFECT_TIERS[label] == LLM_ONLY, label


def test_a_case_is_labelled_by_its_operator_or_as_a_real_defect(cases) -> None:
    labels = {defect_label(c) for c in cases}
    assert labels == {None, *OPERATORS}


def test_a_new_operator_without_a_tier_is_an_error(cases) -> None:
    from dataclasses import replace

    (mutant,) = [c for c in cases if c.operator == "drop_section"]
    with pytest.raises(ValueError, match="no tier"):
        defect_label(replace(mutant, operator="brand_new_operator"))


def test_the_deterministic_stage_carries_tier_one_with_a_reviewer_that_accepts_everything(
    cases,
) -> None:
    tiers = report(cases, always_accept)
    passed = names(tiers.pipeline)
    # what code decides is covered at pipeline level although the model never rejects
    assert {
        "pipeline[contradict_version]",
        "pipeline[contradict_package_name]",
        "pipeline[break_install_command]",
        "pipeline[duplicate_paragraph]",
    } <= passed
    # ... and what only a model judges is not
    assert not names(tiers.llm_only)
    assert tiers.status == "NOT_PASSED"


def test_a_reviewer_that_rejects_everything_fails_the_false_reject_gate(cases) -> None:
    tiers = report(cases, always_reject)
    assert "false_reject_rate" not in names(tiers.shared)
    assert tiers.status == "NOT_PASSED"


def test_the_reviewer_alone_number_is_reported_for_tier_one_but_not_gated(
    cases,
) -> None:
    metrics = compute_metrics(run_corpus(cases, always_accept))
    tiers = evaluate_tiers(metrics)
    gate = next(
        g for g in tiers.pipeline if g.name == "pipeline[break_install_command]"
    )
    assert gate.passed  # the deterministic stage catches it
    assert (
        tiers.reviewer_alone["break_install_command"] == 0.0
    )  # the model alone does not
    assert metrics.per_defect["break_install_command"].llm_target_recall() == 0.0


def test_a_correct_reviewer_passes_both_tiers(cases) -> None:
    tiers = report(cases, oracle, repeats=3)
    assert tiers.status == "PASSED", [
        g.line()
        for g in (*tiers.pipeline, *tiers.llm_only, *tiers.shared)
        if not g.passed
    ]


def test_a_reviewer_that_is_perfect_on_tier_one_but_misses_tier_two_is_limits_only(
    cases,
) -> None:
    def reviewer(case):
        if case.role == "clean" or defect_label(case) is None:
            return oracle(case)
        if DEFECT_TIERS[defect_label(case)] == LLM_ONLY:
            return ReviewOutcome(
                ACCEPT, first_reply_json_valid=True, first_reply_contract_valid=True
            )
        return oracle(case)

    tiers = report(cases, reviewer, repeats=3)
    assert not names(tiers.llm_only)
    assert tiers.status == "LIMITS_ONLY"
    assert (
        REJECT
    )  # (tier two is the owner's to accept; code never records the acceptance)


def test_a_tier_one_miss_is_never_declared_a_limit(cases) -> None:
    def reviewer(case):
        label = defect_label(case)
        if label == "break_install_command":
            return ReviewOutcome(
                ACCEPT, first_reply_json_valid=True, first_reply_contract_valid=True
            )
        return oracle(case)

    # the deterministic stage still catches the install mutant, so tier one holds ...
    assert report(cases, reviewer, repeats=3).status == "PASSED"

    # ... but a class nothing deterministic catches (here: content loss in the synthetic corpus)
    # and the reviewer misses is a tier-one failure, whatever the reviewer does for tier two
    def blind(case):
        if defect_label(case) == "drop_section":
            return ReviewOutcome(
                ACCEPT, first_reply_json_valid=True, first_reply_contract_valid=True
            )
        return oracle(case)

    tiers = report(cases, blind, repeats=3)
    assert tiers.status == "NOT_PASSED" and "pipeline[drop_section]" not in names(
        tiers.pipeline
    )


def test_a_class_nobody_measured_fails_its_gate(tmp_path) -> None:
    only_clean = [
        c for c in build_corpus([Base(make_source(tmp_path))]) if c.role == "clean"
    ]
    tiers = report(only_clean, oracle)
    assert tiers.status == "NOT_PASSED" and not names(tiers.pipeline)
