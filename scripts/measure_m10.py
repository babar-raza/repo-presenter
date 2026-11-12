"""Supervisor-run, zero-provider-call measurement of mechanism M10 (Lane L edit justification and
minimality) against ``src/repo_presenter/lane_l_review.py``'s existing L-01 (confinement) and
L-02 (determinism) holdouts -- the real implementation TC-025 landed, per TC-022b's own card
text ("measured against: L-01/L-02 holdouts... TC-025 is the real implementation").

Every case here reuses fixtures and mutation shapes already proven correct by
``tests/test_lane_l_review.py`` (``test_confinement_is_reproved_from_the_edit_list_not_trusted_
from_the_engine``, ``test_non_determinism_blocks_because_no_rerun_could_ever_be_proven``) --
this script does not invent new mutations, it turns those already-proven facts into
``calibration_harness.score_m10``'s ``CaseVerdict`` input.

Usage: ``python scripts/measure_m10.py [--write]``, same convention as ``measure_m5.py``.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from repo_presenter.acceptance.calibration_harness import (  # noqa: E402
    HARNESS_VERSION,
    M10_FALLBACK_IMPLEMENTATION,
    SCHEMA_VERSION,
    CaseVerdict,
)
from repo_presenter.acceptance.calibration_harness import score_m10  # noqa: E402
from repo_presenter.lane_l_review import confinement_findings, nondeterminism_findings  # noqa: E402
from repo_presenter.readme.correction.engine import correct  # noqa: E402
from repo_presenter.readme.correction.model import Fact  # noqa: E402,F401
from tests.readme.correction.conftest import base_facts, context  # noqa: E402
from tests.readme.correction.test_lane_l_report import README, TREE, broken_link, unit  # noqa: E402

NOTES_UNIT = unit(
    "inherited_unit:004.paragraph",
    "See [the notes](upstream-issues.md) for details.",
    "7-7",
    "paragraph",
)

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"


def _corrected():
    ctx = context(README, base_facts(broken_link(), NOTES_UNIT), tree=TREE)
    return ctx, correct(ctx)


def measure():
    ctx, result = _corrected()
    cases: list[CaseVerdict] = []

    # L-01 confinement: clean case.
    cases.append(
        CaseVerdict(
            case_id="confinement:clean", group="overall", expected=False,
            flagged=bool(confinement_findings(ctx.readme, result)),
        )
    )
    # L-01 confinement: text widened outside the listed edits (real mutation, proven caught by
    # test_confinement_is_reproved_from_the_edit_list_not_trusted_from_the_engine).
    widened = dataclasses.replace(result, corrected=result.corrected + "An unlisted sentence.\n")
    cases.append(
        CaseVerdict(
            case_id="confinement:widened", group="overall", expected=True,
            flagged=bool(confinement_findings(ctx.readme, widened)),
        )
    )
    # L-01 confinement: a changed byte no edit names.
    swapped = dataclasses.replace(result, corrected=result.corrected.replace("Product", "Produkt"))
    cases.append(
        CaseVerdict(
            case_id="confinement:swapped_byte", group="overall", expected=True,
            flagged=bool(confinement_findings(ctx.readme, swapped)),
        )
    )
    # L-02 determinism: reproducible rerun (clean) vs. non-reproducible (defect).
    cases.append(
        CaseVerdict(
            case_id="determinism:reproducible", group="overall", expected=False,
            flagged=bool(nondeterminism_findings(True)),
        )
    )
    cases.append(
        CaseVerdict(
            case_id="determinism:non_reproducible", group="overall", expected=True,
            flagged=bool(nondeterminism_findings(False)),
        )
    )
    return score_m10(cases, provisional=True, measured_against=M10_FALLBACK_IMPLEMENTATION), len(cases)


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
    certificates = [c for c in doc["certificates"] if c.get("mechanism_class") != "M10"]
    certificates.append(
        {
            "mechanism_class": "M10",
            "status": result.status,
            "measured_at": "2026-11-09T00:00:00Z",
            "corpus": "lane_l_review.py L-01/L-02 holdouts, reused from test_lane_l_review.py fixtures",
            "provider_calls": result.provider_calls,
            "provisional": result.provisional,
            "measured_against": result.measured_against,
            "gates": [gate.__dict__ for gate in result.gates],
        }
    )
    doc["certificates"] = certificates
    return doc


def main() -> int:
    result, n_cases = measure()
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print(f"(measured against {n_cases} cases, 0 provider calls, provisional={result.provisional})")
    if "--write" in sys.argv[1:]:
        doc = _merge_certificate(result)
        CALIBRATION_PATH.write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
