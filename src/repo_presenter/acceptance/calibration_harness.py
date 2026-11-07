"""Pure, offline scoring harness for the deterministic acceptance mechanisms (TC-022b).

Scope, exactly: this module scores mechanisms M1 through M7 and M10 -- the model-free pipeline
stages -- plus a deterministic end-to-end aggregate over the same cases. M8 (the prose judge) is
explicitly OUT of scope here; it is a separate card, TC-023, and nothing in this module touches it.

What this module is, and is not:

* It is a set of PURE scoring functions. Given already-computed per-case verdicts (a case id, a
  stratification group, whether the case is actually defective, and whether the mechanism under
  test flagged it), it computes recall / false-reject-rate / determinism / agreement / self-parity
  exactly per the thresholds in TC-022b's own card text, and assembles a result object shaped like
  the real, committed ``data/acceptance_calibration.json`` (per-mechanism status, a harness/schema
  version, a corpus digest, a flat list of named gates per mechanism, and ``provider_calls`` --
  always ``0`` here, since scoring already-computed verdicts calls no model and no provider).
* It does NOT call any mechanism (M1-M7/M10) itself, does not read the real A1 registration from
  disk, and does not write ``data/acceptance_calibration.json`` (that path is in
  ``ops/gatectl.py``'s ``GLOBAL_DENY`` and is supervisor/attested-writer-owned only -- see TC-022b's
  own card text and closeout). This card's own tests construct small, in-memory fixtures with
  KNOWN correct answers (e.g. a fixture engineered so recall computes to exactly 0.90, and a sibling
  engineered to compute to exactly 0.89) and assert the scoring math against those known values.
  Wiring this harness to the real A1 registration (TC-022a) and the real mechanism implementations
  (TC-016, TC-017a, TC-017b, TC-018, TC-020, TC-021, and for M10 ideally TC-025) is a separate, later
  step, done once all of those are accepted -- not performed by this module or its tests.

Determinism (R10, for the harness itself -- distinct from M1's own "determinism == 1.00" gate,
which is about the MECHANISM under test, not this harness): every function here is a pure function
of its arguments. There is no clock read, no random choice, and no unordered-dict-dependent
serialization -- :func:`result_to_json_bytes` sorts keys and uses a fixed, whitespace-free
separator, so two calls over an unchanged input set produce byte-identical output, with zero
provider calls, every time. :func:`test_calibration_harness.py`'s own determinism test proves this
directly.

M10 provisional note: this module never silently drops the fact that a mechanism was measured
against a stand-in. :func:`score_m10` always names, in its own result (``measured_against``), which
real implementation (if any) or fallback (today's Lane L ``L-01``/``L-02`` holdouts,
``src/repo_presenter/lane_l_review.py``) the recall figure was computed against, and sets
``provisional=True`` whenever that fallback is what was actually used.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

#: This harness's own schema for the result object it produces. Bump whenever a field's meaning
#: changes; a mere new optional field does not require a bump.
SCHEMA_VERSION = 1

#: Bump whenever a scoring rule (a threshold, a direction, a grouping rule, the joint-pool rule
#: for M5/M7) changes meaning.
HARNESS_VERSION = "1"

#: The mechanisms this harness measures. M8 (the prose judge) is deliberately absent.
MECHANISMS: tuple[str, ...] = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M10")

#: The fallback M10 is measured against when TC-025's real Lane L minimality/justification
#: mechanism has not yet landed in this worktree.
M10_FALLBACK_IMPLEMENTATION = "src/repo_presenter/lane_l_review.py (L-01/L-02 holdouts)"

_DIRECTIONS = (">=", "<=")


def _passes(value: float, threshold: float, direction: str) -> bool:
    if direction == ">=":
        return value >= threshold
    if direction == "<=":
        return value <= threshold
    raise ValueError(f"unknown gate direction {direction!r} (expected one of {_DIRECTIONS})")


# --------------------------------------------------------------------------------------------
# Core primitive: one named gate, built from a numerator/denominator rate.
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Gate:
    """One named, thresholded measurement. ``value`` is the observed rate, rounded to 4 decimal
    places before the pass/fail comparison is made (so floating-point noise from division never
    flips a result that is exactly on a boundary) -- or ``None`` when ``n`` is 0, in which case the
    gate is always ``passed=False`` (an empty sample proves nothing; it is never silently a pass)."""

    name: str
    value: float | None
    threshold: float
    direction: str
    passed: bool
    n: int


def make_rate_gate(
    name: str, numerator: int, denominator: int, *, threshold: float, direction: str
) -> Gate:
    """A :class:`Gate` scoring ``numerator / denominator`` against ``threshold`` in ``direction``
    (``">="`` or ``"<="``). ``denominator == 0`` always yields ``value=None, passed=False``."""
    if denominator <= 0:
        return Gate(
            name=name, value=None, threshold=threshold, direction=direction, passed=False, n=0
        )
    if numerator < 0 or numerator > denominator:
        raise ValueError(f"gate {name!r}: numerator {numerator} out of range for n={denominator}")
    value = round(numerator / denominator, 4)
    return Gate(
        name=name,
        value=value,
        threshold=threshold,
        direction=direction,
        passed=_passes(value, threshold, direction),
        n=denominator,
    )


def gates_all_pass(gates: Sequence[Gate]) -> bool:
    """A mechanism/stage is ``PASSED`` only when it produced at least one gate and every gate it
    produced passed. An empty gate list is never treated as a pass by omission."""
    return bool(gates) and all(gate.passed for gate in gates)


# --------------------------------------------------------------------------------------------
# Per-case verdict input shape (what a mechanism's own run over a case already decided).
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseVerdict:
    """One case's already-computed outcome for one mechanism.

    ``group`` is the stratification key the card's threshold is counted per (an owned defect
    class for M2, an ecosystem for M3, a mutation-operator name for the end-to-end aggregate, or a
    constant such as ``"overall"`` for a mechanism the card does not ask to stratify). ``expected``
    is ``True`` when the case is a real defect/mutant this mechanism is supposed to catch, ``False``
    when it is a clean twin expected to be accepted. ``flagged`` is what the mechanism under test
    actually decided (rejected/flagged ``True``, accepted ``False``). ``flagged_rerun`` is a second,
    independent run's ``flagged`` value, used only by :func:`determinism_gate`; it is ``None`` when
    no rerun was performed for this case.
    """

    case_id: str
    group: str
    expected: bool
    flagged: bool
    flagged_rerun: bool | None = None


def group_recall_gates(
    cases: Sequence[CaseVerdict], *, prefix: str, threshold: float = 0.90
) -> list[Gate]:
    """One recall :class:`Gate` per distinct ``group`` among the ``expected=True`` cases: recall is
    the fraction of that group's real-defect cases the mechanism actually flagged. Groups are
    reported in sorted order (so output order never depends on input order, per R10)."""
    by_group: dict[str, list[CaseVerdict]] = {}
    for case in cases:
        if case.expected:
            by_group.setdefault(case.group, []).append(case)
    gates: list[Gate] = []
    for group in sorted(by_group):
        members = by_group[group]
        caught = sum(1 for member in members if member.flagged)
        gates.append(
            make_rate_gate(
                f"{prefix}[{group}]",
                caught,
                len(members),
                threshold=threshold,
                direction=">=",
            )
        )
    return gates


def false_reject_gate(cases: Sequence[CaseVerdict], *, name: str, threshold: float) -> Gate:
    """A :class:`Gate` for the false-reject rate over the ``expected=False`` (clean-twin) cases:
    the fraction of clean twins the mechanism incorrectly flagged as defective."""
    clean = [case for case in cases if not case.expected]
    false_rejects = sum(1 for case in clean if case.flagged)
    return make_rate_gate(name, false_rejects, len(clean), threshold=threshold, direction="<=")


def joint_false_reject_gate(
    pool_a: Sequence[CaseVerdict], pool_b: Sequence[CaseVerdict], *, name: str, threshold: float
) -> Gate:
    """M5's and M7's false-reject rates, counted JOINTLY on their shared clean-twin pool: the sum
    of both mechanisms' false rejects over the combined pool must not exceed ``threshold`` --
    exactly TC-022b's card text ("counted JOINTLY with M7"), not two independent 0.02 budgets."""
    combined = [case for case in pool_a if not case.expected] + [
        case for case in pool_b if not case.expected
    ]
    false_rejects = sum(1 for case in combined if case.flagged)
    return make_rate_gate(name, false_rejects, len(combined), threshold=threshold, direction="<=")


def determinism_gate(
    cases: Sequence[CaseVerdict], *, name: str, threshold: float = 1.00
) -> Gate:
    """M1's own determinism gate: the fraction of cases (restricted to those a rerun was actually
    performed for, i.e. ``flagged_rerun is not None``) whose rerun agreed with the first run."""
    with_rerun = [case for case in cases if case.flagged_rerun is not None]
    matches = sum(1 for case in with_rerun if case.flagged == case.flagged_rerun)
    return make_rate_gate(name, matches, len(with_rerun), threshold=threshold, direction=">=")


def self_parity_gate(
    correct_self_matches: Sequence[bool], *, name: str = "M7.self_parity", threshold: float = 1.00
) -> Gate:
    """M7's self-parity gate: a benchmark README scored against itself must report no difference,
    for every self-comparison performed. ``correct_self_matches[i]`` is ``True`` exactly when the
    i-th self-comparison correctly found zero loss/difference."""
    matches = sum(1 for correct in correct_self_matches if correct)
    return make_rate_gate(
        name, matches, len(correct_self_matches), threshold=threshold, direction=">="
    )


# --------------------------------------------------------------------------------------------
# M5's R14 drop-decision agreement (a frozen regression fixture, not a sample: == 1.00 required).
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class R14Case:
    """One already-decided entry from ``data/drop_decisions.json``'s ``decisions`` array, plus
    what M5's own rule table decided for it. ``expected_decision``/``mechanism_decision`` are one
    of ``"READD"``/``"KEEP_DROPPED"`` (the only two values that schema's ``decision`` field uses)."""

    item_id: str
    expected_decision: str
    mechanism_decision: str


def r14_agreement_gate(
    cases: Sequence[R14Case], *, name: str = "M5.r14_agreement", threshold: float = 1.00
) -> Gate:
    """Every one of the frozen ``data/drop_decisions.json`` entries must be reproduced exactly:
    agreement must be ``1.00``, never merely a high recall, since those decisions are a regression
    fixture, not a sample to estimate a rate from."""
    matches = sum(1 for case in cases if case.mechanism_decision == case.expected_decision)
    return make_rate_gate(name, matches, len(cases), threshold=threshold, direction=">=")


# --------------------------------------------------------------------------------------------
# Per-mechanism result: a status, its gates, and (only ever for M10 today) a provisional note.
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MechanismResult:
    mechanism: str
    status: str
    gates: tuple[Gate, ...]
    provider_calls: int = 0
    provisional: bool = False
    measured_against: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mechanism": self.mechanism,
            "status": self.status,
            "provider_calls": self.provider_calls,
            "provisional": self.provisional,
            "measured_against": self.measured_against,
            "gates": [gate.__dict__ for gate in self.gates],
        }


def build_mechanism_result(
    mechanism: str,
    gates: Sequence[Gate],
    *,
    provider_calls: int = 0,
    provisional: bool = False,
    measured_against: str | None = None,
) -> MechanismResult:
    status = "PASSED" if gates_all_pass(gates) else "NOT_PASSED"
    return MechanismResult(
        mechanism=mechanism,
        status=status,
        gates=tuple(gates),
        provider_calls=provider_calls,
        provisional=provisional,
        measured_against=measured_against,
    )


# --------------------------------------------------------------------------------------------
# Per-mechanism convenience scorers, each wired to TC-022b's own, exact thresholds.
# --------------------------------------------------------------------------------------------


def score_m1(cases: Sequence[CaseVerdict]) -> MechanismResult:
    """M1 (freshness/provenance): recall >= 0.90; determinism == 1.00."""
    gates = [
        *group_recall_gates(cases, prefix="M1.recall", threshold=0.90),
        determinism_gate(cases, name="M1.determinism", threshold=1.00),
    ]
    return build_mechanism_result("M1", gates)


def score_m2(cases: Sequence[CaseVerdict]) -> MechanismResult:
    """M2 (claim proof): recall >= 0.90 per owned defect class (``case.group``); clean-twin
    false-reject rate <= 0.04."""
    gates = [
        *group_recall_gates(cases, prefix="M2.recall", threshold=0.90),
        false_reject_gate(cases, name="M2.false_reject_rate", threshold=0.04),
    ]
    return build_mechanism_result("M2", gates)


def score_m3(cases: Sequence[CaseVerdict]) -> MechanismResult:
    """M3 (example execution): recall >= 0.90 per ecosystem (``case.group``); false-CONTRADICTED
    rate <= 0.02 (a clean, runnable example incorrectly reported CONTRADICTED)."""
    gates = [
        *group_recall_gates(cases, prefix="M3.recall", threshold=0.90),
        false_reject_gate(cases, name="M3.false_contradicted_rate", threshold=0.02),
    ]
    return build_mechanism_result("M3", gates)


def score_m4_or_m6(mechanism: str, cases: Sequence[CaseVerdict]) -> MechanismResult:
    """M4 or M6 (install/package/registry/links; public-text form): recall >= 0.90. No
    false-reject budget is stated for these in TC-022b's card text, so none is scored here."""
    if mechanism not in ("M4", "M6"):
        raise ValueError(f"score_m4_or_m6 is only for M4/M6, got {mechanism!r}")
    gates = group_recall_gates(cases, prefix=f"{mechanism}.recall", threshold=0.90)
    return build_mechanism_result(mechanism, gates)


def score_m5(cases: Sequence[CaseVerdict], r14_cases: Sequence[R14Case]) -> MechanismResult:
    """M5 (preservation / R14 drop-decision rule table): recall >= 0.90; R14 agreement == 1.00.
    M5's false-reject budget (<= 0.02) is counted JOINTLY with M7 on their shared clean-twin pool
    -- see :func:`joint_false_reject_gate` and :func:`score_end_to_end`'s ``m5_m7_joint_false_reject``
    gate, not a standalone gate here, so it is never double-counted as two separate 0.02 budgets."""
    gates = [
        *group_recall_gates(cases, prefix="M5.recall", threshold=0.90),
        r14_agreement_gate(r14_cases, name="M5.r14_agreement", threshold=1.00),
    ]
    return build_mechanism_result("M5", gates)


def score_m7(cases: Sequence[CaseVerdict], self_parity_matches: Sequence[bool]) -> MechanismResult:
    """M7 (benchmark parity against the live upstream README): recall >= 0.90; self-parity == 1.00.
    M7's false-reject budget is the joint M5/M7 budget -- see :func:`score_m5`'s docstring."""
    gates = [
        *group_recall_gates(cases, prefix="M7.recall", threshold=0.90),
        self_parity_gate(self_parity_matches, name="M7.self_parity", threshold=1.00),
    ]
    return build_mechanism_result("M7", gates)


def score_m10(
    cases: Sequence[CaseVerdict],
    *,
    provisional: bool = True,
    measured_against: str = M10_FALLBACK_IMPLEMENTATION,
) -> MechanismResult:
    """M10 (Lane L edit justification and minimality): recall >= 0.90. TC-025 is the real
    implementation; when it has not landed, ``provisional=True`` and ``measured_against`` must name
    the fallback actually used (today: ``lane_l_review.py``'s L-01/L-02 holdouts) -- this is always
    visible in the result, never a silent substitution."""
    gates = group_recall_gates(cases, prefix="M10.recall", threshold=0.90)
    return build_mechanism_result(
        "M10", gates, provisional=provisional, measured_against=measured_against
    )


# --------------------------------------------------------------------------------------------
# Deterministic end-to-end aggregate (M8 excluded).
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EndToEndResult:
    status: str
    gates: tuple[Gate, ...]
    n_minimums: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "gates": [gate.__dict__ for gate in self.gates],
            "n_minimums": dict(self.n_minimums),
        }


def score_end_to_end(
    *,
    on_target_cases: Sequence[CaseVerdict],
    mutation_cases: Sequence[CaseVerdict],
    clean_cases: Sequence[CaseVerdict],
    m5_clean_pool: Sequence[CaseVerdict],
    m7_clean_pool: Sequence[CaseVerdict],
    n_minimums: Mapping[str, Any],
) -> EndToEndResult:
    """The deterministic-mechanisms-only end-to-end aggregate (M8 excluded):

    * ``on_target_cases`` (real A+D cases, ``case.group`` typically a single value such as
      ``"real_A_D"``): recall >= 0.90.
    * ``mutation_cases`` (synthetic mutant cases, ``case.group`` the mutation-operator name):
      every operator's own recall >= 0.90.
    * ``clean_cases``: false-reject rate <= 0.10.
    * ``m5_clean_pool``/``m7_clean_pool``: the same joint M5/M7 false-reject budget (<= 0.02) also
      reported at the aggregate level, since it spans two mechanisms rather than belonging to
      either one alone.

    ``n_minimums`` is passed through verbatim (never recomputed or silently reinterpreted here):
    it is TC-022a's own honest report of whether its n>=30-per-class / n>=50-clean-twin minimums
    were met, or how far short the registration fell -- this harness only carries that report
    forward into its own result object, exactly as the card requires.
    """
    gates = [
        *group_recall_gates(on_target_cases, prefix="end_to_end.on_target_recall", threshold=0.90),
        *group_recall_gates(mutation_cases, prefix="end_to_end.operator_recall", threshold=0.90),
        false_reject_gate(clean_cases, name="end_to_end.clean_false_reject_rate", threshold=0.10),
        joint_false_reject_gate(
            m5_clean_pool,
            m7_clean_pool,
            name="end_to_end.m5_m7_joint_false_reject_rate",
            threshold=0.02,
        ),
    ]
    status = "PASSED" if gates_all_pass(gates) else "NOT_PASSED"
    return EndToEndResult(status=status, gates=tuple(gates), n_minimums=dict(n_minimums))


# --------------------------------------------------------------------------------------------
# Top-level result object: the shape the real data/acceptance_calibration.json must have.
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CalibrationResult:
    schema_version: int
    harness_version: str
    status: str
    corpus_digest: str
    provider_calls: int
    mechanisms: Mapping[str, MechanismResult]
    end_to_end: EndToEndResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "harness_version": self.harness_version,
            "status": self.status,
            "corpus_digest": self.corpus_digest,
            "provider_calls": self.provider_calls,
            "mechanisms": {
                mechanism: result.to_dict() for mechanism, result in self.mechanisms.items()
            },
            "end_to_end": self.end_to_end.to_dict(),
        }


def score_calibration(
    *,
    corpus_digest: str,
    mechanisms: Mapping[str, MechanismResult],
    end_to_end: EndToEndResult,
) -> CalibrationResult:
    """Assemble the final result object. Overall ``status`` is ``PASSED`` only when every
    non-provisional mechanism and the end-to-end aggregate are ``PASSED``; a mechanism still
    measured only provisionally (today: M10, pending TC-025) is reported in full but never silently
    allowed to block -- or silently allowed to pass -- the overall status: it is reported in its own
    right, exactly as the card requires, but does not count toward ``status`` while provisional."""
    provider_calls = sum(result.provider_calls for result in mechanisms.values())
    non_provisional_passed = all(
        result.status == "PASSED" for result in mechanisms.values() if not result.provisional
    )
    status = "PASSED" if non_provisional_passed and end_to_end.status == "PASSED" else "NOT_PASSED"
    return CalibrationResult(
        schema_version=SCHEMA_VERSION,
        harness_version=HARNESS_VERSION,
        status=status,
        corpus_digest=corpus_digest,
        provider_calls=provider_calls,
        mechanisms=dict(mechanisms),
        end_to_end=end_to_end,
    )


def result_to_json_bytes(result: CalibrationResult) -> bytes:
    """A canonical, deterministic serialization of ``result``: sorted keys, no incidental
    whitespace. Two calls over an unchanged ``CalibrationResult`` (built from an unchanged input
    set) produce byte-identical output -- this is R10 for the harness itself, proved directly by
    ``test_calibration_harness.py``'s own two-run determinism test."""
    return json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
