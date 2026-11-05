"""Executable guard for release-gate card TC-003: pins the governance fact the card
asserts so ordinary CI (not only gatecli) fails when it regresses."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _check(*args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_two_tier_model_and_reinstated_cards_are_recorded():
    _check("ops/checks/marker_check.py", "AGENTS.md", "TWO_TIER_TASKCARD_MODEL_ADOPTED_2026-11-04")
    _check("ops/checks/marker_check.py", "ops/SUPERVISOR.md", "RELEASE_GATE_CARDS_REINSTATED_2026-11-04")
    _check("ops/checks/count_taskcards.py", "13")
