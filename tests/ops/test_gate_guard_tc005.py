"""Executable guard for release-gate card TC-005: pins the governance fact the card
asserts so ordinary CI (not only gatecli) fails when it regresses."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _check(*args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_release_contract_adopted_and_dashboard_matches_live():
    _check("ops/checks/marker_check.py", "docs/RELEASE_CONTRACT_P1-P5.md", "RELEASE_CONTRACT_ADOPTED_2026-11-04")
    _check("ops/checks/dashboard_matches_live.py")
