#!/usr/bin/env python
"""Release-gate-card check: assert data/reviewer_calibration.json's status field equals exactly
the given value. Real JSON parsing, not substring matching -- "NOT_PASSED" contains "PASSED" as
a substring, so a naive marker check would be fooled by the exact string this check must
currently correctly reject. Usage:

    python ops/checks/calibration_status.py <expected-status>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PATH = Path("data/reviewer_calibration.json")


def main(argv: list[str]) -> int:
    expected = argv[0] if argv else "PASSED"
    if not PATH.exists():
        print(f"FAIL: {PATH} does not exist")
        return 1
    data = json.loads(PATH.read_text(encoding="utf-8"))
    status = data.get("status")
    if status != expected:
        print(f"FAIL: {PATH} status is {status!r}, need {expected!r}")
        return 1
    print(f"OK: {PATH} status is {status!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
