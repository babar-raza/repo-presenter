#!/usr/bin/env python
"""Release-gate-card check: AUTHORIZED != EXECUTED != VERIFIED != DELIVERED (2026-11-04 follow-up
directive, section 6). owner_decision_record.py proves a human wrote an authorization record --
it does not and cannot prove the authorized action actually happened. This is the second,
independent check every live-write card (TC-009a/TC-010a/TC-012a) must also pass: a real,
structured execution-proof record, written only by the actual action (a real token mint, a real
issue lifecycle run, a real cutover), not by the authorization step.

Usage: python ops/checks/execution_proof.py <evidence_file.json> <key>=<expected> [<key>=<expected> ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: execution_proof.py <evidence_file.json> <key>=<expected> [...]")
        return 2
    path = Path(argv[0])
    if not path.exists():
        print(f"FAIL: {path} does not exist -- no execution proof has been recorded")
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: {path} is not valid JSON: {exc}")
        return 1

    problems = []
    for spec in argv[1:]:
        if "=" not in spec:
            print(f"usage error: {spec!r} is not <key>=<expected>")
            return 2
        key, expected = spec.split("=", 1)
        actual = data.get(key)
        if str(actual) != expected:
            problems.append(f"{key}: expected {expected!r}, got {actual!r}")
    if problems:
        print("FAIL: " + "; ".join(problems))
        return 1
    print(f"OK: {path} records a real execution proof matching all {len(argv) - 1} requirement(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
