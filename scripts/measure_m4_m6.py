"""Supervisor-run, zero-provider-call measurement of mechanisms M4 (install/package/registry/
links) and M6 (public-text form) against the real, existing mutation operators
(``src/repo_presenter/readme/review/calibration/mutations.py``) and the real deterministic
checkers they are supposed to trip: ``readme.validation.claims.claim_findings`` for M4
(D2's version/package/install-contradiction shapes) and
``readme.review.independent_reviewer.duplicate_paragraph_rule`` for M6 (D11's duplicate-content
shape -- the same rule TC-024's per-candidate canary already reuses).

The synthetic candidate (``tests/readme/review/calibration/synthetic.py::make_source``) is the
same small, already-trusted fixture ``tests/readme/review/calibration/test_calibration_mutations.py``
uses to prove each operator edits exactly the span it claims; this script reuses it rather than
building new fixture material, and reuses the operators themselves rather than hand-writing new
mutations.

Usage: ``python scripts/measure_m4_m6.py [--write]``, same convention as ``measure_m5.py``.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from repo_presenter.acceptance.calibration_harness import (  # noqa: E402
    HARNESS_VERSION,
    SCHEMA_VERSION,
    CaseVerdict,
    score_m4_or_m6,
)
from repo_presenter.readme.review.calibration.mutations import OPERATORS  # noqa: E402
from repo_presenter.readme.review.independent_reviewer import (  # noqa: E402
    duplicate_paragraph_rule,
)
from repo_presenter.readme.validation.claims import claim_findings  # noqa: E402
from tests.readme.review.calibration.synthetic import make_source  # noqa: E402

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"

M4_OPERATORS = ("contradict_version", "contradict_package_name", "break_install_command")
M6_OPERATORS = ("duplicate_paragraph",)


def measure():
    with tempfile.TemporaryDirectory(prefix="m4m6-") as tmp:
        source = make_source(Path(tmp))

        m4_cases: list[CaseVerdict] = [
            CaseVerdict(
                case_id="clean", group="overall", expected=False,
                flagged=bool(claim_findings(source.readme, source.facts)),
            )
        ]
        for name in M4_OPERATORS:
            mutation = OPERATORS[name](source)
            if mutation is None:
                continue
            findings = claim_findings(mutation.readme, source.facts)
            m4_cases.append(
                CaseVerdict(
                    case_id=name, group="overall", expected=True, flagged=bool(findings)
                )
            )

        m6_cases: list[CaseVerdict] = [
            CaseVerdict(
                case_id="clean", group="overall", expected=False,
                flagged=bool(duplicate_paragraph_rule(source.readme)),
            )
        ]
        for name in M6_OPERATORS:
            mutation = OPERATORS[name](source)
            if mutation is None:
                continue
            findings = duplicate_paragraph_rule(mutation.readme)
            m6_cases.append(
                CaseVerdict(
                    case_id=name, group="overall", expected=True, flagged=bool(findings)
                )
            )

    return (
        score_m4_or_m6("M4", m4_cases),
        score_m4_or_m6("M6", m6_cases),
        len(m4_cases),
        len(m6_cases),
    )


def _merge_certificates(m4_result, m6_result) -> dict:
    if CALIBRATION_PATH.exists():
        doc = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    else:
        doc = {
            "schema": "acceptance-calibration/1",
            "harness_version": HARNESS_VERSION,
            "harness_schema_version": SCHEMA_VERSION,
            "certificates": [],
        }
    certificates = [
        c for c in doc["certificates"] if c.get("mechanism_class") not in ("M4", "M6")
    ]
    for result, corpus in (
        (m4_result, "readme.review.calibration.mutations OPERATORS + readme.validation.claims.claim_findings"),
        (m6_result, "readme.review.calibration.mutations OPERATORS + independent_reviewer.duplicate_paragraph_rule"),
    ):
        certificates.append(
            {
                "mechanism_class": result.mechanism,
                "status": result.status,
                "measured_at": "2026-11-09T00:00:00Z",
                "corpus": corpus,
                "provider_calls": result.provider_calls,
                "provisional": result.provisional,
                "gates": [gate.__dict__ for gate in result.gates],
            }
        )
    doc["certificates"] = certificates
    return doc


def main() -> int:
    m4_result, m6_result, n4, n6 = measure()
    print("M4:", json.dumps(m4_result.to_dict(), indent=2, sort_keys=True))
    print(f"(measured against {n4} cases, 0 provider calls)")
    print("M6:", json.dumps(m6_result.to_dict(), indent=2, sort_keys=True))
    print(f"(measured against {n6} cases, 0 provider calls)")
    if "--write" in sys.argv[1:]:
        doc = _merge_certificates(m4_result, m6_result)
        CALIBRATION_PATH.write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
