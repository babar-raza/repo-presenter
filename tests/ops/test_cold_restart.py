"""Cold-restart test, required directly by the 2026-11-04 directive: prove the supervisor
resumes correctly without session memory. ops/SUPERVISOR.md states this as the whole design's
own property ("A cold restart reads this file and `python ops/gatecli.py resume-brief` and loses
nothing -- no state has ever lived in a session's context"); this test actually exercises it
rather than taking the claim on faith.

Runs the real CLI as independently-launched subprocesses (not repeated calls into one long-lived
interpreter) and cross-checks against a freshly re-imported in-process rebuild, proving the
derived state is a pure function of on-disk evidence (taskcards + receipts + instructions.jsonl),
never of anything a running process could have cached or accumulated.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_tick() -> str:
    result = subprocess.run(
        [sys.executable, "ops/gatecli.py", "tick"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_two_independently_launched_cold_processes_agree():
    first = _run_tick()
    second = _run_tick()
    assert first == second


def test_cold_subprocess_agrees_with_a_freshly_reimported_in_process_rebuild():
    cold_output = _run_tick()

    sys.path.insert(0, str(REPO_ROOT / "ops"))
    import importlib

    import gateverify

    importlib.reload(gateverify)  # genuinely fresh module state, not anything a prior test left
    rows, _ = gateverify.rebuild_state()
    ready = gateverify.ready_cards_from_rows(rows)
    assert f"ready cards: {ready or 'none'}" in cold_output


def test_resume_brief_also_runs_cold_without_error():
    result = subprocess.run(
        [sys.executable, "ops/gatecli.py", "resume-brief"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "=== ops/SUPERVISOR.md ===" in result.stdout
