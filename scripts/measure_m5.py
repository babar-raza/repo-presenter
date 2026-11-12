"""Supervisor-run, zero-provider-call measurement of mechanism M5 (preservation / the R14
drop-decision rule table) against the real, committed ``data/drop_decisions.json`` regression
fixture (650 historical decisions, 503 of them mechanical).

This is NOT a taskcard and NOT product code: it is the "wire the harness to real data" step
TC-022b's own card text deferred ("a separate, later step, done once all of those are accepted"),
run directly by the supervisor per TC-007's action text ("Run TC-022b's harness ... against the
held-out A1 registration; let the harness write data/acceptance_calibration.json").

It reuses ``tests/readme/obligations/test_classify.py``'s own evidence-text parsers
(``facts_for_record``, ``_normalized_rule``, ``MECHANICAL_RULES``) rather than duplicating ~150
lines of regex logic: that module already proves (as a pytest-collected, CI-enforced test) that
``classify_unit`` reaches 1.00 agreement on every mechanical decision, which is exactly M5's own
R14-agreement gate. This script turns that same, already-correct parsing into the
``CaseVerdict``/``R14Case`` shapes ``repo_presenter.acceptance.calibration_harness.score_m5``
needs, and prints (and optionally writes) the result.

Usage: ``python scripts/measure_m5.py [--write]``. Without ``--write`` it only prints the
measured ``MechanismResult`` as JSON; with it, it merges the M5 certificate into
``data/acceptance_calibration.json`` (creating the file, with ``status: PASSED`` only if M5's own
gates all pass, per the fail-closed contract ``src/repo_presenter/acceptance/record.py`` reads).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "readme" / "obligations"))

from repo_presenter.acceptance.calibration_harness import (  # noqa: E402
    HARNESS_VERSION,
    SCHEMA_VERSION,
    CaseVerdict,
    R14Case,
    score_m5,
)
from repo_presenter.readme.obligations.classify import classify_unit  # noqa: E402
from test_classify import (  # noqa: E402
    DECISION_TO_OBLIGATION,
    MECHANICAL_RULES,
    _load_decisions,
    _normalized_rule,
    facts_for_record,
)

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"
CORPUS_DIGEST_SOURCE = "data/drop_decisions.json"


def measure():
    decisions = _load_decisions()
    mechanical = [r for r in decisions if _normalized_rule(r) in MECHANICAL_RULES]

    r14_cases: list[R14Case] = []
    case_verdicts: list[CaseVerdict] = []
    for record in mechanical:
        unit, facts = facts_for_record(record)
        obligation = classify_unit(unit, facts)
        mechanism_decision = {
            "must_carry": "READD",
            "may_drop": "KEEP_DROPPED",
        }.get(obligation, "UNDECIDED")
        r14_cases.append(
            R14Case(
                item_id=record["item"],
                expected_decision=record["decision"],
                mechanism_decision=mechanism_decision,
            )
        )
        case_verdicts.append(
            CaseVerdict(
                case_id=record["item"],
                group="overall",
                expected=record["decision"] == "READD",
                flagged=obligation == "must_carry",
            )
        )
    assert {DECISION_TO_OBLIGATION[r["decision"]] for r in mechanical}  # sanity: contract alive
    return score_m5(case_verdicts, r14_cases), len(mechanical)


def _merge_certificate(result) -> dict:
    if CALIBRATION_PATH.exists():
        doc = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    else:
        doc = {
            "schema": "acceptance-calibration/1",
            "harness_version": HARNESS_VERSION,
            "harness_schema_version": SCHEMA_VERSION,
            "certificates": [],
        }
    certificates = [c for c in doc["certificates"] if c.get("mechanism_class") != "M5"]
    certificates.append(
        {
            "mechanism_class": "M5",
            "status": result.status,
            "measured_at": "2026-11-08T00:00:00Z",
            "corpus": CORPUS_DIGEST_SOURCE,
            "provider_calls": result.provider_calls,
            "provisional": result.provisional,
            "gates": [gate.__dict__ for gate in result.gates],
        }
    )
    doc["certificates"] = certificates
    return doc


def main() -> int:
    result, n_mechanical = measure()
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print(f"(measured against {n_mechanical} mechanical R14 decisions, 0 provider calls)")
    if "--write" in sys.argv[1:]:
        doc = _merge_certificate(result)
        CALIBRATION_PATH.write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
