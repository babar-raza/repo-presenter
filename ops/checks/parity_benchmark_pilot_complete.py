#!/usr/bin/env python
"""TC-006 release-gate check (2026-11-04 P0 follow-up directive section 4): a benchmark that
measured one of three named pilot repositories and called itself "complete" was the exact
false-green pattern the directive flagged. This checks the real document names all three pilot
repositories AND carries an explicit PARITY_VERDICT line -- never a bare "COMPLETE" marker that
a placeholder file could satisfy without any real per-repository content.

This check accepts NOT_PASSED as a legitimate, honest verdict (the card's own purpose is to
measure and report, not to force parity into existing) -- it only refuses a document that is
silent about the three named repositories or has no explicit verdict at all.

Usage: python ops/checks/parity_benchmark_pilot_complete.py <doc_path>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_REPOSITORIES = (
    "3D-.NET",
    "Imaging-.NET",
    "Words-.NET",
)
VERDICT_RE = re.compile(r"^PARITY_VERDICT:\s*(PASSED|NOT_PASSED)\s*$", re.MULTILINE)
COMPLETE_RE = re.compile(r"^PARITY_BENCHMARK_COMPLETE:\s*\S", re.MULTILINE)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: parity_benchmark_pilot_complete.py <doc_path>")
        return 2
    path = Path(argv[0])
    if not path.exists():
        print(f"FAIL: {path} does not exist")
        return 1
    text = path.read_text(encoding="utf-8")

    problems = []
    missing_repos = [name for name in REQUIRED_REPOSITORIES if name not in text]
    if missing_repos:
        problems.append(f"missing named pilot repositories: {missing_repos}")
    verdict_match = VERDICT_RE.search(text)
    if verdict_match is None:
        problems.append("no explicit 'PARITY_VERDICT: PASSED|NOT_PASSED' line")
    if not COMPLETE_RE.search(text):
        problems.append("no 'PARITY_BENCHMARK_COMPLETE:' line")

    if problems:
        print("FAIL: " + "; ".join(problems))
        return 1
    print(
        f"OK: {path} addresses all {len(REQUIRED_REPOSITORIES)} named pilot repositories with "
        f"an explicit verdict ({verdict_match.group(1)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
