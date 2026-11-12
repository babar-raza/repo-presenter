"""Turn example receipts into ``example`` facts whose polarity states what actually happened.

Ported (REUSE, near-verbatim) from the old repository-presenter project's
``extractors/examples/verify.py`` per migration/reuse-manifest.yaml.
"""

from __future__ import annotations

from collections.abc import Sequence

from repo_presenter.core.examples import (
    PRELUDE_ATTRIBUTE,
    ExampleCandidate,
    ExampleOutcome,
    ExampleReceipt,
)
from repo_presenter.core.facts import Evidence, Fact, Polarity, fact_id

_POLARITY: dict[ExampleOutcome, Polarity] = {
    "EXECUTED": "SUPPORTED",
    "FAILED": "CONTRADICTED",
    "TIMED_OUT": "UNRESOLVED",
    "NEEDS_INPUT": "UNRESOLVED",
    "NOT_VERIFIED": "UNRESOLVED",
}

# Outcomes certain enough to carry full confidence. A timeout proves only that verification
# could not finish in time -- it is never proof the example is wrong -- so it is deliberately
# excluded here and falls to the 0.5 default alongside NEEDS_INPUT/NOT_VERIFIED.
_FULL_CONFIDENCE: frozenset[ExampleOutcome] = frozenset({"EXECUTED", "FAILED"})


def example_facts(
    candidates: Sequence[ExampleCandidate],
    receipts: Sequence[ExampleReceipt],
    receipts_path: str,
) -> list[Fact]:
    """One fact per candidate; a candidate without a receipt is recorded as not verified."""
    by_ordinal = {receipt.ordinal: receipt for receipt in receipts}
    facts: list[Fact] = []
    for candidate in candidates:
        receipt = by_ordinal.get(candidate.ordinal)
        outcome: ExampleOutcome = receipt.outcome if receipt else "NOT_VERIFIED"
        detail = receipt.detail if receipt else "no verification receipt"
        evidence = [
            Evidence(
                candidate.source_path,
                f"lines {candidate.start_line}-{candidate.end_line}; {candidate.language} fence; "
                f"unit {candidate.unit_id}",
            ),
            Evidence(receipts_path, f"example {candidate.ordinal}: {outcome}; {detail}"),
        ]
        if receipt is not None:
            evidence.extend(
                Evidence(binding.source_path, f"staged as {binding.literal}")
                if binding.produced_by is None
                else Evidence(
                    receipts_path,
                    f"staged as {binding.literal} from example {binding.produced_by}'s "
                    f"output {binding.source_path}",
                )
                for binding in receipt.fixtures
            )
        facts.append(
            Fact(
                fact_id("example", f"{candidate.ordinal:03d}"),
                "example",
                candidate.code,
                tuple(evidence),
                polarity=_POLARITY[outcome],
                confidence=1.0 if outcome in _FULL_CONFIDENCE else 0.5,
                attributes=(
                    {PRELUDE_ATTRIBUTE: receipt.prelude}
                    if receipt is not None and receipt.prelude and outcome == "EXECUTED"
                    else None
                ),
            )
        )
    return facts
