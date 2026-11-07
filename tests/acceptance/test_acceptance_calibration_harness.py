"""Tests for the pure calibration-scoring harness (TC-022b).

These tests never require the real A1 registration (TC-022a) or any live mechanism
implementation: every fixture here is small and worker-constructed, with a KNOWN correct answer,
so the scoring math itself -- not any real pipeline -- is what is proved. In particular, several
fixtures are built to sit exactly at or just below the card's own 0.90 recall threshold, so a
mutation that lowers that threshold (TC-022b's own negative control) is guaranteed to flip at
least one assertion here from correct to wrong.
"""

from __future__ import annotations

import json

import pytest

from repo_presenter.acceptance.calibration_harness import (
    HARNESS_VERSION,
    M10_FALLBACK_IMPLEMENTATION,
    SCHEMA_VERSION,
    CaseVerdict,
    EndToEndResult,
    Gate,
    MechanismResult,
    R14Case,
    build_mechanism_result,
    determinism_gate,
    false_reject_gate,
    gates_all_pass,
    group_recall_gates,
    joint_false_reject_gate,
    make_rate_gate,
    r14_agreement_gate,
    result_to_json_bytes,
    score_calibration,
    score_end_to_end,
    score_m1,
    score_m2,
    score_m3,
    score_m4_or_m6,
    score_m5,
    score_m7,
    score_m10,
    self_parity_gate,
)


# --------------------------------------------------------------------------------------------
# Helpers to build fixtures with known, exact rates.
# --------------------------------------------------------------------------------------------


def _defect_cases(group: str, n_total: int, n_caught: int) -> list[CaseVerdict]:
    """``n_total`` real-defect cases in ``group``, the first ``n_caught`` of them flagged."""
    return [
        CaseVerdict(
            case_id=f"{group}:defect:{index}",
            group=group,
            expected=True,
            flagged=index < n_caught,
        )
        for index in range(n_total)
    ]


def _clean_cases(group: str, n_total: int, n_false_rejected: int) -> list[CaseVerdict]:
    """``n_total`` clean-twin cases in ``group``, the first ``n_false_rejected`` incorrectly
    flagged as defective."""
    return [
        CaseVerdict(
            case_id=f"{group}:clean:{index}",
            group=group,
            expected=False,
            flagged=index < n_false_rejected,
        )
        for index in range(n_total)
    ]


# --------------------------------------------------------------------------------------------
# Core primitive: make_rate_gate / gates_all_pass.
# --------------------------------------------------------------------------------------------


def test_make_rate_gate_exact_boundary_passes() -> None:
    gate = make_rate_gate("x", 90, 100, threshold=0.90, direction=">=")
    assert gate.value == 0.90
    assert gate.passed is True
    assert gate.n == 100


def test_make_rate_gate_just_below_boundary_fails() -> None:
    gate = make_rate_gate("x", 89, 100, threshold=0.90, direction=">=")
    assert gate.value == 0.89
    assert gate.passed is False


def test_make_rate_gate_le_direction_boundary() -> None:
    at_threshold = make_rate_gate("y", 4, 100, threshold=0.04, direction="<=")
    over_threshold = make_rate_gate("y", 5, 100, threshold=0.04, direction="<=")
    assert at_threshold.passed is True
    assert over_threshold.passed is False


def test_make_rate_gate_empty_denominator_never_silently_passes() -> None:
    gate = make_rate_gate("z", 0, 0, threshold=0.90, direction=">=")
    assert gate.value is None
    assert gate.passed is False
    assert gate.n == 0


def test_make_rate_gate_rejects_bad_direction() -> None:
    with pytest.raises(ValueError):
        make_rate_gate("x", 1, 1, threshold=0.90, direction="==")


def test_make_rate_gate_rejects_numerator_over_denominator() -> None:
    with pytest.raises(ValueError):
        make_rate_gate("x", 2, 1, threshold=0.90, direction=">=")


def test_gates_all_pass_empty_list_is_not_a_pass() -> None:
    assert gates_all_pass([]) is False


def test_gates_all_pass_requires_every_gate() -> None:
    passing = make_rate_gate("a", 1, 1, threshold=0.90, direction=">=")
    failing = make_rate_gate("b", 0, 1, threshold=0.90, direction=">=")
    assert gates_all_pass([passing]) is True
    assert gates_all_pass([passing, failing]) is False


# --------------------------------------------------------------------------------------------
# group_recall_gates: the real boundary fixtures the negative control must break.
# --------------------------------------------------------------------------------------------


def test_group_recall_at_exactly_0_90_passes() -> None:
    cases = _defect_cases("A", n_total=100, n_caught=90)
    gates = group_recall_gates(cases, prefix="M.recall", threshold=0.90)
    assert len(gates) == 1
    assert gates[0].name == "M.recall[A]"
    assert gates[0].value == 0.90
    assert gates[0].passed is True


def test_group_recall_at_0_89_fails() -> None:
    """This is the fixture the card's negative control is built to flip: 0.89 sits strictly
    between 0.50 and 0.90, so lowering the harness's 0.90 threshold to 0.50 (the mutation) must
    flip this gate's ``passed`` from False to True."""
    cases = _defect_cases("A", n_total=100, n_caught=89)
    gates = group_recall_gates(cases, prefix="M.recall", threshold=0.90)
    assert gates[0].value == 0.89
    assert gates[0].passed is False


def test_group_recall_gates_are_per_group_and_sorted() -> None:
    cases = _defect_cases("zeta", 10, 10) + _defect_cases("alpha", 10, 5)
    gates = group_recall_gates(cases, prefix="M.recall", threshold=0.90)
    assert [gate.name for gate in gates] == ["M.recall[alpha]", "M.recall[zeta]"]
    assert gates[0].passed is False  # alpha: 5/10 = 0.50
    assert gates[1].passed is True  # zeta: 10/10 = 1.00


def test_group_recall_gates_ignore_clean_cases() -> None:
    cases = _defect_cases("A", 10, 9) + _clean_cases("A", 50, 50)
    gates = group_recall_gates(cases, prefix="M.recall", threshold=0.90)
    assert len(gates) == 1
    assert gates[0].n == 10  # only the defect cases count toward recall's denominator


# --------------------------------------------------------------------------------------------
# false_reject_gate / joint_false_reject_gate.
# --------------------------------------------------------------------------------------------


def test_false_reject_rate_at_threshold_passes_and_over_fails() -> None:
    at = false_reject_gate(_clean_cases("c", 100, 4), name="fr", threshold=0.04)
    over = false_reject_gate(_clean_cases("c", 100, 5), name="fr", threshold=0.04)
    assert at.value == 0.04 and at.passed is True
    assert over.value == 0.05 and over.passed is False


def test_false_reject_gate_ignores_defect_cases() -> None:
    cases = _clean_cases("c", 50, 1) + _defect_cases("c", 50, 0)
    gate = false_reject_gate(cases, name="fr", threshold=0.04)
    assert gate.n == 50


def test_joint_false_reject_gate_pools_both_mechanisms() -> None:
    m5_pool = _clean_cases("m5", 50, 1)
    m7_pool = _clean_cases("m7", 50, 0)
    gate = joint_false_reject_gate(m5_pool, m7_pool, name="joint", threshold=0.02)
    assert gate.n == 100
    assert gate.value == 0.01
    assert gate.passed is True


def test_joint_false_reject_gate_over_budget_fails() -> None:
    m5_pool = _clean_cases("m5", 50, 2)
    m7_pool = _clean_cases("m7", 50, 1)
    gate = joint_false_reject_gate(m5_pool, m7_pool, name="joint", threshold=0.02)
    assert gate.value == 0.03
    assert gate.passed is False


def test_joint_false_reject_gate_exactly_at_budget_passes() -> None:
    m5_pool = _clean_cases("m5", 50, 1)
    m7_pool = _clean_cases("m7", 50, 1)
    gate = joint_false_reject_gate(m5_pool, m7_pool, name="joint", threshold=0.02)
    assert gate.value == 0.02
    assert gate.passed is True


# --------------------------------------------------------------------------------------------
# determinism_gate (M1) / self_parity_gate (M7).
# --------------------------------------------------------------------------------------------


def test_determinism_gate_requires_full_agreement() -> None:
    agreeing = [
        CaseVerdict("a", "g", True, flagged=True, flagged_rerun=True),
        CaseVerdict("b", "g", False, flagged=False, flagged_rerun=False),
    ]
    gate = determinism_gate(agreeing, name="det")
    assert gate.value == 1.00
    assert gate.passed is True


def test_determinism_gate_one_mismatch_fails() -> None:
    cases = [
        CaseVerdict("a", "g", True, flagged=True, flagged_rerun=True),
        CaseVerdict("b", "g", False, flagged=False, flagged_rerun=True),
    ]
    gate = determinism_gate(cases, name="det")
    assert gate.value == 0.5
    assert gate.passed is False


def test_determinism_gate_ignores_cases_without_a_rerun() -> None:
    cases = [
        CaseVerdict("a", "g", True, flagged=True, flagged_rerun=None),
        CaseVerdict("b", "g", True, flagged=True, flagged_rerun=True),
    ]
    gate = determinism_gate(cases, name="det")
    assert gate.n == 1


def test_self_parity_gate_all_correct_passes() -> None:
    gate = self_parity_gate([True, True, True])
    assert gate.value == 1.00
    assert gate.passed is True


def test_self_parity_gate_one_wrong_fails() -> None:
    gate = self_parity_gate([True, False, True])
    assert gate.passed is False


# --------------------------------------------------------------------------------------------
# M5's R14 agreement: a frozen regression fixture, mirroring data/drop_decisions.json's shape.
# --------------------------------------------------------------------------------------------


def _r14_fixture(mismatch: bool) -> list[R14Case]:
    """Mirrors data/drop_decisions.json's ``decisions`` shape: each entry's recorded ``decision``
    is one of READD/KEEP_DROPPED; here as (expected, mechanism) pairs."""
    cases = [
        R14Case(item_id="repo-a:item-1", expected_decision="READD", mechanism_decision="READD"),
        R14Case(
            item_id="repo-a:item-2",
            expected_decision="KEEP_DROPPED",
            mechanism_decision="KEEP_DROPPED",
        ),
        R14Case(item_id="repo-b:item-3", expected_decision="READD", mechanism_decision="READD"),
    ]
    if mismatch:
        cases.append(
            R14Case(
                item_id="repo-c:item-4",
                expected_decision="READD",
                mechanism_decision="KEEP_DROPPED",
            )
        )
    else:
        cases.append(
            R14Case(
                item_id="repo-c:item-4",
                expected_decision="KEEP_DROPPED",
                mechanism_decision="KEEP_DROPPED",
            )
        )
    return cases


def test_r14_agreement_full_match_passes() -> None:
    gate = r14_agreement_gate(_r14_fixture(mismatch=False))
    assert gate.value == 1.00
    assert gate.passed is True
    assert gate.n == 4


def test_r14_agreement_single_mismatch_fails_even_though_recall_would_be_high() -> None:
    """Agreement must be exactly 1.00, not merely >= 0.90: three of four still correct is 0.75,
    and even if it were higher it must not be treated as a passing recall-style gate."""
    gate = r14_agreement_gate(_r14_fixture(mismatch=True))
    assert gate.value == 0.75
    assert gate.passed is False


# --------------------------------------------------------------------------------------------
# Per-mechanism scorers, wired against the card's own exact thresholds.
# --------------------------------------------------------------------------------------------


def test_score_m1_passes_at_recall_and_determinism_boundary() -> None:
    cases = _defect_cases("A", 100, 90)
    cases = [
        CaseVerdict(case.case_id, case.group, case.expected, case.flagged, flagged_rerun=case.flagged)
        for case in cases
    ] + _clean_cases("A", 10, 0)
    result = score_m1(cases)
    assert result.status == "PASSED"
    assert result.mechanism == "M1"


def test_score_m1_fails_below_recall_boundary() -> None:
    cases = _defect_cases("A", 100, 89)
    result = score_m1(cases)
    assert result.status == "NOT_PASSED"
    recall_gate = next(g for g in result.gates if g.name == "M1.recall[A]")
    assert recall_gate.value == 0.89


def test_score_m2_recall_per_owned_class_and_clean_false_reject() -> None:
    cases = _defect_cases("A", 50, 45) + _defect_cases("D", 50, 45) + _clean_cases("A", 100, 4)
    result = score_m2(cases)
    assert result.status == "PASSED"
    names = {gate.name for gate in result.gates}
    assert "M2.recall[A]" in names and "M2.recall[D]" in names
    assert "M2.false_reject_rate" in names


def test_score_m2_fails_when_one_owned_class_below_recall() -> None:
    cases = _defect_cases("A", 50, 45) + _defect_cases("D", 50, 30) + _clean_cases("A", 100, 0)
    result = score_m2(cases)
    assert result.status == "NOT_PASSED"


def test_score_m3_false_contradicted_budget() -> None:
    cases = _defect_cases("python", 30, 27) + _clean_cases("python", 100, 2)
    result = score_m3(cases)
    assert result.status == "PASSED"
    contradicted = next(g for g in result.gates if g.name == "M3.false_contradicted_rate")
    assert contradicted.value == 0.02


def test_score_m4_or_m6_rejects_unknown_mechanism() -> None:
    with pytest.raises(ValueError):
        score_m4_or_m6("M9", [])


def test_score_m4_and_m6_recall_only() -> None:
    cases = _defect_cases("install", 40, 36)
    for mechanism in ("M4", "M6"):
        result = score_m4_or_m6(mechanism, cases)
        assert result.mechanism == mechanism
        assert result.status == "PASSED"
        assert len(result.gates) == 1  # recall only, no false-reject gate for M4/M6


def test_score_m5_requires_recall_and_r14_full_agreement() -> None:
    cases = _defect_cases("preservation", 30, 30)
    passing_r14 = _r14_fixture(mismatch=False)
    result = score_m5(cases, passing_r14)
    assert result.status == "PASSED"

    result_bad_r14 = score_m5(cases, _r14_fixture(mismatch=True))
    assert result_bad_r14.status == "NOT_PASSED"


def test_score_m7_requires_recall_and_self_parity() -> None:
    cases = _defect_cases("benchmark", 30, 30)
    result = score_m7(cases, [True, True, True])
    assert result.status == "PASSED"

    result_broken_parity = score_m7(cases, [True, False])
    assert result_broken_parity.status == "NOT_PASSED"


def test_score_m10_is_provisional_by_default_and_names_the_fallback() -> None:
    cases = _defect_cases("lane_l", 30, 30)
    result = score_m10(cases)
    assert result.mechanism == "M10"
    assert result.provisional is True
    assert result.measured_against == M10_FALLBACK_IMPLEMENTATION
    assert result.status == "PASSED"


def test_score_m10_can_be_marked_non_provisional_once_tc_025_lands() -> None:
    cases = _defect_cases("lane_l", 30, 30)
    result = score_m10(cases, provisional=False, measured_against="TC-025 real implementation")
    assert result.provisional is False
    assert result.measured_against == "TC-025 real implementation"


# --------------------------------------------------------------------------------------------
# End-to-end aggregate: on-target recall, per-operator recall, clean false-reject, joint budget.
# --------------------------------------------------------------------------------------------


def _passing_end_to_end_inputs() -> dict:
    return dict(
        on_target_cases=_defect_cases("real_A_D", 100, 90),
        mutation_cases=(
            _defect_cases("duplicate_paragraph", 20, 18) + _defect_cases("drop_section", 20, 20)
        ),
        clean_cases=_clean_cases("clean", 100, 10),
        m5_clean_pool=_clean_cases("m5", 50, 0),
        m7_clean_pool=_clean_cases("m7", 50, 1),
        n_minimums={"per_class_target": 30, "clean_twin_target": 50, "met": True},
    )


def test_score_end_to_end_all_gates_passing() -> None:
    result = score_end_to_end(**_passing_end_to_end_inputs())
    assert result.status == "PASSED"
    names = {gate.name for gate in result.gates}
    assert "end_to_end.on_target_recall[real_A_D]" in names
    assert "end_to_end.operator_recall[duplicate_paragraph]" in names
    assert "end_to_end.operator_recall[drop_section]" in names
    assert "end_to_end.clean_false_reject_rate" in names
    assert "end_to_end.m5_m7_joint_false_reject_rate" in names
    assert result.n_minimums == {"per_class_target": 30, "clean_twin_target": 50, "met": True}


def test_score_end_to_end_fails_when_one_operator_below_recall() -> None:
    inputs = _passing_end_to_end_inputs()
    inputs["mutation_cases"] = _defect_cases("duplicate_paragraph", 20, 10)  # 0.50 recall
    result = score_end_to_end(**inputs)
    assert result.status == "NOT_PASSED"
    operator_gate = next(
        g for g in result.gates if g.name == "end_to_end.operator_recall[duplicate_paragraph]"
    )
    assert operator_gate.passed is False


def test_score_end_to_end_fails_when_clean_false_reject_over_budget() -> None:
    inputs = _passing_end_to_end_inputs()
    inputs["clean_cases"] = _clean_cases("clean", 100, 11)  # 0.11 > 0.10 budget
    result = score_end_to_end(**inputs)
    assert result.status == "NOT_PASSED"


def test_score_end_to_end_n_minimums_is_passed_through_verbatim_even_when_short() -> None:
    inputs = _passing_end_to_end_inputs()
    shortfall_report = {
        "per_class_target": 30,
        "per_class_achieved": {"A": 12, "D": 30},
        "per_class_shortfall": {"A": 18, "D": 0},
        "met": False,
    }
    inputs["n_minimums"] = shortfall_report
    result = score_end_to_end(**inputs)
    # The end-to-end status is about the gates, not about n_minimums; a short registration is
    # still reported honestly rather than silently hidden or used to fail the gates themselves.
    assert result.n_minimums == shortfall_report


# --------------------------------------------------------------------------------------------
# Top-level assembly: overall status, provisional mechanisms never block it, provider_calls.
# --------------------------------------------------------------------------------------------


def _passing_mechanism(mechanism: str, *, provisional: bool = False) -> MechanismResult:
    gate = make_rate_gate(f"{mechanism}.recall[x]", 90, 100, threshold=0.90, direction=">=")
    return build_mechanism_result(mechanism, [gate], provisional=provisional)


def _failing_mechanism(mechanism: str) -> MechanismResult:
    gate = make_rate_gate(f"{mechanism}.recall[x]", 10, 100, threshold=0.90, direction=">=")
    return build_mechanism_result(mechanism, [gate])


def test_score_calibration_overall_passed_when_everything_passes() -> None:
    mechanisms = {m: _passing_mechanism(m) for m in ("M1", "M2", "M3", "M4", "M5", "M6", "M7")}
    mechanisms["M10"] = _passing_mechanism("M10", provisional=True)
    end_to_end = score_end_to_end(**_passing_end_to_end_inputs())
    result = score_calibration(
        corpus_digest="deadbeef", mechanisms=mechanisms, end_to_end=end_to_end
    )
    assert result.status == "PASSED"
    assert result.provider_calls == 0


def test_score_calibration_one_failing_mechanism_fails_overall() -> None:
    mechanisms = {m: _passing_mechanism(m) for m in ("M1", "M2", "M3", "M4", "M6", "M7")}
    mechanisms["M5"] = _failing_mechanism("M5")
    mechanisms["M10"] = _passing_mechanism("M10", provisional=True)
    end_to_end = score_end_to_end(**_passing_end_to_end_inputs())
    result = score_calibration(
        corpus_digest="deadbeef", mechanisms=mechanisms, end_to_end=end_to_end
    )
    assert result.status == "NOT_PASSED"


def test_score_calibration_provisional_m10_failure_does_not_block_overall_status() -> None:
    """M10 is provisional (today, measured only against the L-01/L-02 fallback); a provisional
    mechanism's own failure is still reported, but it must not be what makes the overall,
    non-provisional status NOT_PASSED, since the card never asks this card to fail a release on a
    stand-in measurement it explicitly marked as such."""
    mechanisms = {m: _passing_mechanism(m) for m in ("M1", "M2", "M3", "M4", "M5", "M6", "M7")}
    mechanisms["M10"] = _failing_mechanism("M10")
    # Explicitly re-mark provisional (build_mechanism_result does not default True).
    failing_m10 = mechanisms["M10"]
    mechanisms["M10"] = MechanismResult(
        mechanism=failing_m10.mechanism,
        status=failing_m10.status,
        gates=failing_m10.gates,
        provider_calls=failing_m10.provider_calls,
        provisional=True,
        measured_against=M10_FALLBACK_IMPLEMENTATION,
    )
    end_to_end = score_end_to_end(**_passing_end_to_end_inputs())
    result = score_calibration(
        corpus_digest="deadbeef", mechanisms=mechanisms, end_to_end=end_to_end
    )
    assert mechanisms["M10"].status == "NOT_PASSED"  # still visible, not hidden
    assert result.status == "PASSED"  # but does not block the overall, non-provisional status


def test_score_calibration_provider_calls_always_zero_for_these_mechanisms() -> None:
    mechanisms = {m: _passing_mechanism(m) for m in ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M10")}
    end_to_end = score_end_to_end(**_passing_end_to_end_inputs())
    result = score_calibration(
        corpus_digest="deadbeef", mechanisms=mechanisms, end_to_end=end_to_end
    )
    assert result.provider_calls == 0
    assert result.schema_version == SCHEMA_VERSION
    assert result.harness_version == HARNESS_VERSION


# --------------------------------------------------------------------------------------------
# R10 for the harness itself: two runs over an unchanged input set are byte-identical.
# --------------------------------------------------------------------------------------------


def test_harness_is_byte_identical_across_two_runs_over_unchanged_inputs() -> None:
    def _build():
        mechanisms = {
            "M1": score_m1(_defect_cases("A", 50, 45) + _clean_cases("A", 10, 0)),
            "M2": score_m2(_defect_cases("A", 50, 45) + _clean_cases("A", 50, 1)),
            "M3": score_m3(_defect_cases("python", 30, 28) + _clean_cases("python", 50, 1)),
            "M4": score_m4_or_m6("M4", _defect_cases("install", 40, 37)),
            "M5": score_m5(_defect_cases("preservation", 30, 30), _r14_fixture(mismatch=False)),
            "M6": score_m4_or_m6("M6", _defect_cases("links", 40, 37)),
            "M7": score_m7(_defect_cases("benchmark", 30, 28), [True, True, True]),
            "M10": score_m10(_defect_cases("lane_l", 30, 28)),
        }
        end_to_end = score_end_to_end(**_passing_end_to_end_inputs())
        return score_calibration(
            corpus_digest="abc123deadbeef", mechanisms=mechanisms, end_to_end=end_to_end
        )

    first_bytes = result_to_json_bytes(_build())
    second_bytes = result_to_json_bytes(_build())
    assert first_bytes == second_bytes
    # Also robust to dict-insertion order in `mechanisms` (sort_keys handles this independently
    # of the order the caller happened to build the mapping in).
    result = _build()
    reordered = score_calibration(
        corpus_digest=result.corpus_digest,
        mechanisms=dict(reversed(list(result.mechanisms.items()))),
        end_to_end=result.end_to_end,
    )
    assert result_to_json_bytes(result) == result_to_json_bytes(reordered)

    # And the bytes really are valid, round-trippable JSON with the expected top-level shape.
    decoded = json.loads(first_bytes.decode("utf-8"))
    assert decoded["schema_version"] == SCHEMA_VERSION
    assert decoded["harness_version"] == HARNESS_VERSION
    assert set(decoded["mechanisms"]) == {"M1", "M2", "M3", "M4", "M5", "M6", "M7", "M10"}
    assert "end_to_end" in decoded
    assert decoded["provider_calls"] == 0
