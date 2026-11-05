"""Executable guard for release-gate card TC-009: pins the governance fact the card
asserts so ordinary CI (not only gatecli) fails when it regresses."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _check(*args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_app_token_reuse_decision_is_logged():
    _check("ops/checks/marker_check.py", "docs/DECISION_LOG.md", "APP_TOKEN_REUSE_DECISION:")
