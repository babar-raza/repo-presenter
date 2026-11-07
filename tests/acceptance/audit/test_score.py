"""TC-014: pure, offline tests for `repo_presenter.acceptance.audit.score`. Pure arithmetic over
in-memory findings/seed-record fixtures - no provider call, no network, no filesystem access."""

from __future__ import annotations

import pytest

from repo_presenter.acceptance.audit.score import (
    AuditMetric,
    Finding,
    ScoringError,
    defective_accepted_rate,
    false_flag_rate,
    score_audit_batch,
    seeded_recall,
)
from repo_presenter.acceptance.audit.seed import CLEAN_SHAPE

SEED_RECORDS = [
    {"candidate_id": "cand-1", "shape": "A", "operator": "count_mismatch", "line": 10},
    {"candidate_id": "cand-2", "shape": "D", "operator": "inject_unsupported_claim", "line": 20},
    {"candidate_id": "cand-3", "shape": "D9", "operator": "misdescribe_type", "line": 30},
]

CLEAN_IDS = ["cand-4", "cand-5"]
UNSEEDED_ACCEPTED_IDS = ["cand-6", "cand-7"]


# ---------------------------------------------------------------------------
# AuditMetric
# ---------------------------------------------------------------------------


def test_audit_metric_computes_the_rate() -> None:
    metric = AuditMetric(matched=3, total=10)
    assert metric.rate == pytest.approx(0.3)


def test_audit_metric_rejects_an_empty_population() -> None:
    with pytest.raises(ScoringError):
        AuditMetric(matched=0, total=0)


def test_audit_metric_rejects_matched_greater_than_total() -> None:
    with pytest.raises(ScoringError):
        AuditMetric(matched=5, total=3)


# ---------------------------------------------------------------------------
# seeded_recall
# ---------------------------------------------------------------------------


def test_seeded_recall_counts_a_finding_at_the_right_candidate_and_line_as_caught() -> None:
    findings = [
        Finding(candidate_id="cand-1", claim="39 public types", verdict="false", path="README.md", line=10),
        Finding(candidate_id="cand-2", claim="exercised and verified", verdict="unverifiable", path="README.md", line=20),
    ]
    metric = seeded_recall(findings, SEED_RECORDS)
    assert metric.matched == 2
    assert metric.total == 3


def test_seeded_recall_does_not_count_a_finding_at_the_wrong_line() -> None:
    findings = [
        Finding(candidate_id="cand-1", claim="x", verdict="false", path="README.md", line=11),
    ]
    metric = seeded_recall(findings, SEED_RECORDS)
    assert metric.matched == 0
    assert metric.total == 3


def test_seeded_recall_does_not_count_a_supported_verdict_as_caught() -> None:
    findings = [
        Finding(candidate_id="cand-1", claim="x", verdict="supported", path="README.md", line=10),
    ]
    metric = seeded_recall(findings, SEED_RECORDS)
    assert metric.matched == 0


def test_seeded_recall_accepts_plain_mapping_findings_too() -> None:
    findings = [
        {"candidate_id": "cand-1", "claim": "x", "verdict": "false", "path": "README.md", "line": 10},
    ]
    metric = seeded_recall(findings, SEED_RECORDS)
    assert metric.matched == 1


def test_seeded_recall_ignores_clean_control_records_in_the_manifest() -> None:
    records = SEED_RECORDS + [
        {"candidate_id": "cand-8", "shape": CLEAN_SHAPE, "operator": "clean_control", "line": None}
    ]
    metric = seeded_recall([], records)
    assert metric.total == 3


def test_seeded_recall_raises_when_every_record_is_a_clean_control() -> None:
    records = [{"candidate_id": "cand-8", "shape": CLEAN_SHAPE, "operator": "clean_control", "line": None}]
    with pytest.raises(ScoringError):
        seeded_recall([], records)


def test_seeded_recall_raises_on_an_empty_manifest() -> None:
    with pytest.raises(ScoringError):
        seeded_recall([], [])


def test_seeded_recall_raises_on_a_seeded_record_with_no_line() -> None:
    bad_records = [{"candidate_id": "cand-1", "shape": "A", "operator": "count_mismatch", "line": None}]
    with pytest.raises(ScoringError):
        seeded_recall([], bad_records)


def test_seeded_recall_raises_on_a_finding_missing_a_required_key() -> None:
    with pytest.raises(ScoringError):
        seeded_recall([{"candidate_id": "cand-1", "verdict": "false"}], SEED_RECORDS)


# ---------------------------------------------------------------------------
# false_flag_rate
# ---------------------------------------------------------------------------


def test_false_flag_rate_counts_any_flag_on_a_clean_candidate() -> None:
    findings = [
        Finding(candidate_id="cand-4", claim="x", verdict="false", path="README.md", line=1),
    ]
    metric = false_flag_rate(findings, CLEAN_IDS)
    assert metric.matched == 1
    assert metric.total == 2


def test_false_flag_rate_is_zero_when_every_clean_candidate_is_untouched() -> None:
    findings = [
        Finding(candidate_id="cand-4", claim="x", verdict="supported", path="README.md", line=1),
    ]
    metric = false_flag_rate(findings, CLEAN_IDS)
    assert metric.matched == 0
    assert metric.total == 2


def test_false_flag_rate_raises_on_empty_clean_control_ids() -> None:
    with pytest.raises(ScoringError):
        false_flag_rate([], [])


def test_false_flag_rate_unverifiable_verdict_also_counts_as_a_flag() -> None:
    findings = [
        Finding(candidate_id="cand-5", claim="x", verdict="unverifiable", path="README.md", line=1),
    ]
    metric = false_flag_rate(findings, CLEAN_IDS)
    assert metric.matched == 1


# ---------------------------------------------------------------------------
# defective_accepted_rate
# ---------------------------------------------------------------------------


def test_defective_accepted_rate_counts_a_false_finding() -> None:
    findings = [
        Finding(candidate_id="cand-6", claim="x", verdict="false", path="README.md", line=5),
    ]
    metric = defective_accepted_rate(findings, UNSEEDED_ACCEPTED_IDS)
    assert metric.matched == 1
    assert metric.total == 2


def test_defective_accepted_rate_ignores_other_candidates_findings() -> None:
    findings = [
        Finding(candidate_id="cand-999", claim="x", verdict="false", path="README.md", line=5),
    ]
    metric = defective_accepted_rate(findings, UNSEEDED_ACCEPTED_IDS)
    assert metric.matched == 0


def test_defective_accepted_rate_raises_on_empty_ids() -> None:
    with pytest.raises(ScoringError):
        defective_accepted_rate([], [])


# ---------------------------------------------------------------------------
# score_audit_batch
# ---------------------------------------------------------------------------


def test_score_audit_batch_computes_all_three_metrics_from_one_findings_list() -> None:
    findings = [
        Finding(candidate_id="cand-1", claim="x", verdict="false", path="README.md", line=10),
        Finding(candidate_id="cand-4", claim="x", verdict="false", path="README.md", line=1),
        Finding(candidate_id="cand-6", claim="x", verdict="unverifiable", path="README.md", line=2),
    ]
    scorecard = score_audit_batch(findings, SEED_RECORDS, CLEAN_IDS, UNSEEDED_ACCEPTED_IDS)
    assert scorecard.seeded_recall.matched == 1
    assert scorecard.seeded_recall.total == 3
    assert scorecard.false_flag_rate.matched == 1
    assert scorecard.false_flag_rate.total == 2
    assert scorecard.defective_accepted_rate.matched == 1
    assert scorecard.defective_accepted_rate.total == 2


def test_score_audit_batch_accepts_a_generator_of_findings() -> None:
    def generate():
        yield Finding(candidate_id="cand-1", claim="x", verdict="false", path="README.md", line=10)

    scorecard = score_audit_batch(generate(), SEED_RECORDS, CLEAN_IDS, UNSEEDED_ACCEPTED_IDS)
    assert scorecard.seeded_recall.matched == 1
