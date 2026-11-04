#!/usr/bin/env python
"""Generic release-gate-card check: assert every given marker substring is
present in the given file. A governance taskcard's check must fail honestly
when the fact it asserts is not yet true -- this script exists so that
honesty, not a bespoke script per card. Usage:

    python ops/checks/marker_check.py <file> <marker> [<marker> ...]

Exits 0 only if the file exists and every marker is found verbatim inside it.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: marker_check.py <file> <marker> [<marker> ...]")
        return 2
    path = Path(argv[0])
    markers = argv[1:]
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = [m for m in markers if m not in text]
    if missing:
        print(f"FAIL: {path} missing marker(s): {missing}")
        return 1
    print(f"OK: {path} contains all {len(markers)} required marker(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
