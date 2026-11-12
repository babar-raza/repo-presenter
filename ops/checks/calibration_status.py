#!/usr/bin/env python
"""Release-gate-card check for acceptance calibration status.

Two modes, chosen by whether ``--file``/``--matrix`` are given:

1. **New contract** (TC-007, re-authored 2026-11-07; routine supervisor wiring per TC-013's own
   closeout, "the supervisor ... wires ops/checks/calibration_status.py (--file/--matrix flags)
   ... to call this card's classify() entry point"): reads the mechanism-class responsibility
   matrix (``--matrix``, default ``data/acceptance_responsibility.json``) and the append-only
   PASSED certificates (``--file``, default ``data/acceptance_calibration.json``) via
   ``repo_presenter.acceptance.record.load_certificates``, and reports ``PASSED`` only when
   ``AcceptanceCertificates.complete`` is true -- every mechanism class the matrix lists has a
   PASSED certificate. Fail-closed exactly as that reader is: a missing/malformed matrix or
   calibration file is never read as a vacuous pass.

       python ops/checks/calibration_status.py PASSED --file data/acceptance_calibration.json \\
           --matrix data/acceptance_responsibility.json

2. **Legacy contract** (no ``--file``/``--matrix`` given; preserved for any caller that still
   wants it): the single, frozen ``data/reviewer_calibration.json`` iteration-5 record's own
   ``status`` field, exact string equality -- "NOT_PASSED" contains "PASSED" as a substring, so
   this is real JSON parsing, never a substring check. Owner ruling R10: nothing may ever write
   PASSED into that file again; this mode only ever reads it.

       python ops/checks/calibration_status.py <expected-status>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_PATH = Path("data/reviewer_calibration.json")


def _legacy_main(expected: str) -> int:
    if not LEGACY_PATH.exists():
        print(f"FAIL: {LEGACY_PATH} does not exist")
        return 1
    data = json.loads(LEGACY_PATH.read_text(encoding="utf-8"))
    status = data.get("status")
    if status != expected:
        print(f"FAIL: {LEGACY_PATH} status is {status!r}, need {expected!r}")
        return 1
    print(f"OK: {LEGACY_PATH} status is {status!r}")
    return 0


def _new_main(expected: str, file_path: Path, matrix_path: Path) -> int:
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from repo_presenter.acceptance.record import load_certificates  # noqa: PLC0415

    certificates = load_certificates(
        calibration_path=file_path, responsibility_path=matrix_path
    )
    status = "PASSED" if certificates.complete else "NOT_PASSED"
    if status != expected:
        missing = (
            sorted(certificates.required_mechanisms - certificates.certified_mechanisms)
            if certificates.required_mechanisms is not None
            else None
        )
        print(
            f"FAIL: acceptance calibration status is {status!r}, need {expected!r} "
            f"(problem={certificates.problem!r}, missing={missing})"
        )
        return 1
    print(f"OK: acceptance calibration status is {status!r}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("expected", nargs="?", default="PASSED")
    parser.add_argument("--file", type=Path, default=None)
    parser.add_argument("--matrix", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.file is None and args.matrix is None:
        return _legacy_main(args.expected)
    file_path = args.file or Path("data/acceptance_calibration.json")
    matrix_path = args.matrix or Path("data/acceptance_responsibility.json")
    return _new_main(args.expected, file_path, matrix_path)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
