"""Supervisor-run, zero-provider-call measurement of mechanism M1 (freshness/provenance: did the
upstream revision move, has anything relevant to the candidate changed since the last
observation) against ``src/repo_presenter/lane_l_trigger.py``'s real ``trigger_for_repository``/
``compute_trigger`` -- the "stale revision" detector the design calls for M1's recall source.

Every case here reuses fixtures ``tests/test_lane_l_trigger.py`` already proves correct: five
real repositories reproducing this session's own 2026-11-07 census (3D .NET/Words .NET: no
trigger; Cells .NET/Slides Java/PSD .NET: real trigger), plus the two fail-closed cases
(unreachable head, unknown changed paths) that stand in for M1's determinism requirement -- a
case whose input is itself uncertain must deterministically resolve to "treat as changed", never
flip between runs.

Usage: ``python scripts/measure_m1.py [--write]``, same convention as ``measure_m5.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.calibration_harness import (  # noqa: E402
    HARNESS_VERSION,
    SCHEMA_VERSION,
    CaseVerdict,
    score_m1,
)
from repo_presenter.lane_l_trigger import (  # noqa: E402
    Baseline,
    LaneLSeal,
    compute_trigger,
    trigger_for_repository,
)

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"
CURRENT_DETECTORS = {
    "broken_link": "1",
    "enterprise_edition_naming": "2",
    "stale_package_version": "1",
    "versioned_link_target": "1",
}


def measure():
    cases: list[CaseVerdict] = []

    # The real five-repository census: expected=True means a real upstream change exists
    # (a "stale" observation this mechanism must catch); expected=False is a genuinely fresh one.
    census = [
        (
            "aspose-3d-foss/Aspose.3D-FOSS-for-.Net", False,
            {
                "head_revision": "a" * 40,
                "changed_paths_since_baseline": (),
                "last_lane_l_seal": LaneLSeal("a" * 40, CURRENT_DETECTORS),
            },
        ),
        (
            "aspose-cells-foss/Aspose.Cells-FOSS-for-.Net", True,
            {
                "head_revision": "c" * 40,
                "changed_paths_since_baseline": ("Aspose.Cells.FOSS.csproj", "CHANGELOG.md"),
                "last_lane_l_seal": LaneLSeal("b" * 40, CURRENT_DETECTORS),
            },
        ),
        (
            "aspose-slides-foss/Aspose.Slides-FOSS-for-Java", True,
            {
                "head_revision": "d" * 40,
                "changed_paths_since_baseline": None,
                "last_lane_l_seal": None,
                "presenter_last_readme_commit": None,
                "upstream_last_readme_commit": None,
            },
        ),
        (
            "aspose-words-foss/Aspose.Words-FOSS-for-.NET", False,
            {
                "head_revision": "e" * 40,
                "changed_paths_since_baseline": (),
                "last_lane_l_seal": LaneLSeal("e" * 40, CURRENT_DETECTORS),
            },
        ),
        (
            "aspose-psd-foss/Aspose.PSD-FOSS-for-.Net", True,
            {
                "head_revision": "f" * 40,
                "changed_paths_since_baseline": ("Aspose.PSD.FOSS.csproj",),
                "last_lane_l_seal": LaneLSeal("f0" * 20, CURRENT_DETECTORS),
            },
        ),
    ]
    for repository, expected, kwargs in census:
        result = trigger_for_repository(
            repository, current_detector_versions=CURRENT_DETECTORS, **kwargs
        )
        cases.append(
            CaseVerdict(
                case_id=repository, group="overall", expected=expected, flagged=result.triggered
            )
        )

    # Determinism: compute_trigger run twice over the SAME inputs (including the two fail-closed
    # shapes -- unreadable head, unknown changed paths) must agree every time.
    baseline = Baseline("r/x", "a" * 40, "lane_l_seal", "r")
    determinism_inputs = [
        {"head_revision": None, "changed_paths_since_baseline": ()},
        {"head_revision": "b" * 40, "changed_paths_since_baseline": None},
        {"head_revision": "b" * 40, "changed_paths_since_baseline": ("README.md",)},
    ]
    for kwargs in determinism_inputs:
        first = compute_trigger("r/x", baseline=baseline, **kwargs)
        second = compute_trigger("r/x", baseline=baseline, **kwargs)
        cases.append(
            CaseVerdict(
                case_id=f"determinism:{kwargs}", group="overall", expected=False,
                flagged=first.triggered, flagged_rerun=second.triggered,
            )
        )
    return score_m1(cases), len(cases)


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
    certificates = [c for c in doc["certificates"] if c.get("mechanism_class") != "M1"]
    certificates.append(
        {
            "mechanism_class": "M1",
            "status": result.status,
            "measured_at": "2026-11-09T00:00:00Z",
            "corpus": "lane_l_trigger.py real 5-repository census + fail-closed determinism cases",
            "provider_calls": result.provider_calls,
            "provisional": result.provisional,
            "gates": [gate.__dict__ for gate in result.gates],
        }
    )
    doc["certificates"] = certificates
    return doc


def main() -> int:
    result, n_cases = measure()
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print(f"(measured against {n_cases} cases, 0 provider calls)")
    if "--write" in sys.argv[1:]:
        doc = _merge_certificate(result)
        CALIBRATION_PATH.write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
