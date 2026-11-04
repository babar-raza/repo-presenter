#!/usr/bin/env python
"""Release-gate-card check: assert project/taskcards/ holds at least N real
TC-NNN.yaml cards. Usage:

    python ops/checks/count_taskcards.py <minimum>
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    minimum = int(argv[0]) if argv else 1
    cards = sorted(Path("project/taskcards").glob("TC-*.yaml"))
    if len(cards) < minimum:
        print(f"FAIL: found {len(cards)} taskcard(s) under project/taskcards/, need >= {minimum}")
        return 1
    print(f"OK: found {len(cards)} taskcard(s) (>= {minimum}): " + ", ".join(c.stem for c in cards))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
