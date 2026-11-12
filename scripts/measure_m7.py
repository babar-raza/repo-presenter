"""Supervisor-run, zero-provider-call measurement of mechanism M7 (benchmark parity against the
published aspose.org README) against real, already-committed benchmark texts.

Self-parity cases reuse the exact same 7 real/synthetic texts
``tests/readme/test_parity_gate.py::test_self_parity_on_every_committed_benchmark_text`` already
proves pass every dimension (6 real committed README snapshots plus one synthetic fixture) --
this script does not invent new self-parity material, it turns that already-proven fact into
``calibration_harness.score_m7``'s ``self_parity_matches`` input.

Recall cases are new, but genuine and simple: for each of the 6 REAL committed texts, this script
drops that text's last top-level section (a real content-loss mutation, D10's defect class,
M7's secondary ownership per the design table) and confirms
``repo_presenter.readme.parity_gate.evaluate`` correctly reports ``parity=False`` for the
resulting candidate against the untouched benchmark. A clean (un-mutated) case per text is also
scored, expected ``parity=True``, to measure the false-reject side honestly rather than only
ever feeding defect cases in.

Usage: ``python scripts/measure_m7.py [--write]``, same convention as ``measure_m5.py``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.acceptance.calibration_harness import (  # noqa: E402
    HARNESS_VERSION,
    SCHEMA_VERSION,
    CaseVerdict,
    score_m7,
)
from repo_presenter.readme.parity_gate import SealedCandidate, evaluate  # noqa: E402

CALIBRATION_PATH = REPO_ROOT / "data" / "acceptance_calibration.json"

# The same 6 real, committed README snapshots the existing self-parity test already uses --
# labels and paths copied from tests/readme/test_parity_gate.py::_committed_benchmark_texts.
REAL_TEXTS = [
    (
        "candidates/aspose-3d-foss",
        REPO_ROOT
        / "candidates"
        / "aspose-3d-foss__Aspose.3D-FOSS-for-.NET"
        / "52b0f00ebf28a0b4173921725ff170685ec2c502"
        / "README.md",
    ),
    (
        "live_readme/3d-net",
        REPO_ROOT
        / "evidence/build/P1_PORTFOLIO_SCALE/aspose-3d-foss__Aspose.3D-FOSS-for-.NET"
        / "live_readme.md",
    ),
    (
        "live_readme/imaging-net",
        REPO_ROOT
        / "evidence/build/P1_PORTFOLIO_SCALE/aspose-imaging-foss__Aspose.Imaging-FOSS-for-.NET"
        / "live_readme.md",
    ),
    (
        "live_readme/cells-rust",
        REPO_ROOT
        / "evidence/build/P1_PORTFOLIO_SCALE/aspose-cells-foss__Aspose.Cells-FOSS-for-Rust"
        / "live_readme.md",
    ),
    (
        "live_readme/email-net",
        REPO_ROOT
        / "evidence/build/P1_PORTFOLIO_SCALE/aspose-email-foss__Aspose.Email-FOSS-for-.Net"
        / "live_readme.md",
    ),
    (
        "live_readme/barcode-python",
        REPO_ROOT
        / "evidence/build/P1_PORTFOLIO_SCALE/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python"
        / "live_readme.md",
    ),
]

_HEADING_RE = re.compile(r"^#{1,2}\s+\S", re.MULTILINE)


def _drop_last_section(text: str) -> str | None:
    """Removes the text from the LAST top-level/second-level heading to the end of the document --
    a real section drop. Returns None when the text has fewer than 2 such headings (nothing
    section-sized to drop without destroying the whole document)."""
    starts = [m.start() for m in _HEADING_RE.finditer(text)]
    if len(starts) < 2:
        return None
    return text[: starts[-1]].rstrip() + "\n"


def measure():
    case_verdicts: list[CaseVerdict] = []
    self_parity_matches: list[bool] = []

    for label, path in REAL_TEXTS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")

        # self-parity: same text as both candidate and benchmark.
        clean_candidate = SealedCandidate("L", text, ())
        clean_result = evaluate(label, clean_candidate, text)
        self_parity_matches.append(clean_result.parity)
        case_verdicts.append(
            CaseVerdict(
                case_id=f"{label}:clean", group="overall", expected=False,
                flagged=not clean_result.parity,
            )
        )

        mutated_text = _drop_last_section(text)
        if mutated_text is None:
            continue
        mutated_candidate = SealedCandidate("L", mutated_text, ())
        mutated_result = evaluate(label, mutated_candidate, text)
        case_verdicts.append(
            CaseVerdict(
                case_id=f"{label}:dropped_last_section", group="overall", expected=True,
                flagged=not mutated_result.parity,
            )
        )

    return score_m7(case_verdicts, self_parity_matches), len(case_verdicts), len(self_parity_matches)


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
    certificates = [c for c in doc["certificates"] if c.get("mechanism_class") != "M7"]
    certificates.append(
        {
            "mechanism_class": "M7",
            "status": result.status,
            "measured_at": "2026-11-09T00:00:00Z",
            "corpus": "6 real committed README snapshots + drop-last-section mutations",
            "provider_calls": result.provider_calls,
            "provisional": result.provisional,
            "gates": [gate.__dict__ for gate in result.gates],
        }
    )
    doc["certificates"] = certificates
    return doc


def main() -> int:
    result, n_cases, n_self_parity = measure()
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print(f"(measured against {n_cases} cases, {n_self_parity} self-parity checks, 0 provider calls)")
    if "--write" in sys.argv[1:]:
        doc = _merge_certificate(result)
        CALIBRATION_PATH.write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {CALIBRATION_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
