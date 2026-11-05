"""The status document is computed from a measurement, and only a complete, fully passing one is
``PASSED`` (``readme.review.calibration.record``)."""

from __future__ import annotations

import json

import pytest

from repo_presenter.readme.review.calibration.corpus import Base, build_corpus
from repo_presenter.readme.review.calibration.harness import (
    ReviewOutcome,
    compute_metrics,
    evaluate_tiers,
    run_corpus,
)
from repo_presenter.readme.review.calibration.outcomes import ACCEPT, REJECT
from repo_presenter.readme.review.calibration.record import (
    merge_repeats,
    status_document,
)
from repo_presenter.readme.review.calibration.reviewers import always_accept, oracle
from repo_presenter.readme.review.calibration_status import parse_calibration
from tests.readme.review.calibration.synthetic import make_source


@pytest.fixture
def cases(tmp_path):
    return build_corpus([Base(make_source(tmp_path))])


def document(run, *, complete=True):
    metrics = compute_metrics(run)
    return status_document(
        evaluate_tiers(metrics),
        metrics,
        complete=complete,
        incomplete_reason="" if complete else "stopped at the cap",
        prompt_version="17",
        model="m",
        measured_on="2026-11-05",
        source="test",
        corpus={"cases": len(run.results)},
    )


def test_a_reviewer_that_passes_every_gate_is_recorded_passed_and_reads_back(cases):
    first = run_corpus(cases, oracle)
    repeats = run_corpus(cases[:2], oracle, repeats=3)
    doc = document(merge_repeats(first, repeats))
    assert doc["status"] == "PASSED" and doc["failed_gates"] == []
    assert (
        doc["measured"]["repeated_cases"] == 2 and doc["measured"]["stable_cases"] == 2
    )
    assert parse_calibration(json.loads(json.dumps(doc))).permits


def test_an_incomplete_run_is_never_passed_even_when_every_gate_passes(cases):
    run = merge_repeats(
        run_corpus(cases, oracle), run_corpus(cases[:2], oracle, repeats=3)
    )
    doc = document(run, complete=False)
    assert doc["status"] == "NOT_PASSED" and "incomplete_run" in doc["failed_gates"]
    assert not parse_calibration(doc).permits


def test_a_failing_reviewer_is_recorded_not_passed_with_its_failed_gates(cases):
    first = run_corpus(cases, always_accept)
    doc = document(
        merge_repeats(first, run_corpus(cases[:2], always_accept, repeats=3))
    )
    assert doc["status"] == "NOT_PASSED"
    assert any(name.startswith("reviewer_alone[") for name in doc["failed_gates"])
    assert doc["owner_acceptance"] == ""


def test_stability_counts_the_first_pass_and_every_fresh_repeat(cases):
    clean = cases[0]
    flips = iter([ACCEPT, ACCEPT, REJECT])
    first = run_corpus([clean], lambda case: ReviewOutcome(ACCEPT))
    repeats = run_corpus([clean], lambda case: ReviewOutcome(next(flips)), repeats=3)
    merged = merge_repeats(first, repeats)
    metrics = compute_metrics(merged)
    assert metrics.repeated_cases == 1 and metrics.stable_cases == 0
    # the first pass still decides the scored verdict
    assert merged.results[0].llm_verdict == ACCEPT


def test_a_repeat_of_a_case_never_asked_is_an_error(cases):
    with pytest.raises(ValueError, match="not in the first pass"):
        merge_repeats(run_corpus(cases[:1], oracle), run_corpus(cases[1:2], oracle))


def test_a_mixed_reviewer_that_fails_one_tier_two_gate_is_not_passed(cases):
    def misses_filler(case):
        if case.operator == "add_promotional_filler":
            return ReviewOutcome(ACCEPT)
        return oracle(case)

    run = merge_repeats(
        run_corpus(cases, misses_filler),
        run_corpus(cases[:2], misses_filler, repeats=3),
    )
    doc = document(run)
    assert doc["status"] == "NOT_PASSED"
    assert "reviewer_alone[add_promotional_filler]" in doc["failed_gates"]
    # every other gate passes: a declared limit, which only the owner may accept
    assert doc["measured"]["two_tier_status"] == "LIMITS_ONLY"
