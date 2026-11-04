"""Executable guard for release-gate card TC-006: pins the governance fact the card
asserts so ordinary CI (not only gatecli) fails when it regresses."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _check(*args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pilot_parity_benchmark_covers_all_three_repositories_with_a_verdict():
    _check("ops/checks/parity_benchmark_pilot_complete.py", "docs/PARITY_BENCHMARK_PILOT.md")
