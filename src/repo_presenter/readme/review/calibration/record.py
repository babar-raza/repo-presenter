"""From a measured run to the calibration status document, by code only.

``data/reviewer_calibration.json`` is read by ``review/calibration_status.py`` and must be the honest
output of the harness, never a hand edit. This module turns one complete measurement (a first pass
plus fresh repeats of a pre-registered stability subset) into that document:

* ``merge_repeats`` folds the fresh repeats of each stability case onto its first-pass result, so the
  first pass still decides every scored verdict and stability means *every* review of the case
  (first pass and each fresh repeat) returned the same verdict.
* ``status_document`` writes ``PASSED`` only when the two-tier report is ``PASSED`` **and** the run is
  complete (every pre-registered case asked, no budget stop). Anything else is ``NOT_PASSED`` with the
  failed gates listed. ``LIMITS_ONLY`` is recorded as ``NOT_PASSED`` too: only the owner can turn it
  into ``PASSED_WITH_DECLARED_LIMITS`` (``owner_acceptance``), and code never writes that field.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from repo_presenter.readme.review.calibration.harness import (
    CaseResult,
    GateResult,
    Metrics,
    Run,
    TierReport,
)
from repo_presenter.readme.review.calibration_names import NOT_PASSED, PASSED
from repo_presenter.readme.review.verdict import REVIEWER_LOGIC_VERSION


def merge_repeats(first: Run, repeats: Run) -> Run:
    """``first`` with each case of ``repeats`` carrying its fresh outcomes after its first-pass one.
    A repeated case missing from ``first`` is an error: stability is measured on asked cases only."""
    extra: dict[str, CaseResult] = {r.case.case_id: r for r in repeats.results}
    known = {r.case.case_id for r in first.results}
    missing = sorted(set(extra) - known)
    if missing:
        raise ValueError(f"repeated cases not in the first pass: {', '.join(missing)}")
    merged = tuple(
        replace(r, outcomes=(r.outcomes[0], *extra[r.case.case_id].outcomes))
        if r.case.case_id in extra
        else r
        for r in first.results
    )
    stopped = "; ".join(s for s in (first.stopped, repeats.stopped) if s)
    return Run(merged, stopped=stopped)


def _gate_record(gate: GateResult) -> dict[str, Any]:
    return {
        "name": gate.name,
        "value": None if gate.value is None else round(gate.value, 4),
        "threshold": gate.threshold,
        "direction": gate.direction,
        "passed": gate.passed,
        "n": gate.n,
    }


def status_document(
    tiers: TierReport,
    metrics: Metrics,
    *,
    complete: bool,
    incomplete_reason: str,
    prompt_version: str,
    model: str,
    measured_on: str,
    source: str,
    corpus: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The calibration status document for one measurement."""
    gates: Sequence[GateResult] = (*tiers.pipeline, *tiers.llm_only, *tiers.shared)
    failed = [gate.name for gate in gates if not gate.passed]
    if not complete:
        failed.append("incomplete_run")
    status = PASSED if tiers.status == PASSED and complete else NOT_PASSED
    measured: dict[str, Any] = {
        "source": source,
        "measured_on": measured_on,
        "corpus": dict(corpus),
        "two_tier_status": tiers.status,
        "complete": complete,
        "incomplete_reason": incomplete_reason,
        "gates": [_gate_record(gate) for gate in gates],
        "reviewer_alone_tier1_not_gated": {
            label: None if value is None else round(value, 4)
            for label, value in tiers.reviewer_alone.items()
        },
        "clean_n": metrics.clean_n,
        "clean_llm_rejected": metrics.clean_llm_rejected,
        "clean_unavailable": metrics.clean_unavailable,
        "unscored_twins_asked": metrics.unscored_n,
        "unscored_twins_llm_rejected": metrics.unscored_llm_rejected,
        "first_replies": metrics.first_replies,
        "first_reply_json_valid": metrics.first_reply_json_valid,
        "first_reply_contract_valid": metrics.first_reply_contract_valid,
        "repeated_cases": metrics.repeated_cases,
        "stable_cases": metrics.stable_cases,
        "provider_calls": metrics.calls,
        "cases_asked": metrics.cases_asked,
        "tokens": metrics.tokens,
    }
    if extra:
        measured.update(extra)
    return {
        "schema_version": 1,
        "status": status,
        "reviewer_logic_version": REVIEWER_LOGIC_VERSION,
        "prompt_version": prompt_version,
        "model": model,
        "owner_acceptance": "",
        "failed_gates": failed,
        "measured": measured,
    }
