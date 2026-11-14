"""BL-111 / BL-100: supervisor-tick.yml. The 06:31Z and 14:11Z ticks of 2026-11-14 (runs 43566771426,
43603607740) were cancelled by the job's 10-minute ceiling while `portfolio_delivery_count.py` was still
running (it took 9m20s in the last successful tick, 43528417117); no section after it ran. The count is now
bounded on its own inside a job with room, its per-lane headline is shown (a bare `tail -20` showed only the
last per-seal notes), and a "### Budget" section follows it that fails the tick loudly when STOPPED."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "supervisor-tick.yml"


def _tick() -> tuple[dict, str]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = doc["jobs"]["tick"]
    (step,) = [s for s in job["steps"] if "doctor" in s.get("name", "")]
    return job, step["run"]


def test_the_job_has_room_for_the_count_and_the_count_is_bounded() -> None:
    job, run = _tick()
    assert job["timeout-minutes"] >= 30
    assert "timeout 25m python ops/checks/portfolio_delivery_count.py --per-lane 25" in run
    assert 25 < job["timeout-minutes"]
    # the per-lane headline lines are shown, not only the tail of per-seal notes
    assert "lane [RL]:" in run and "| tail -20" not in run.split('echo "### Backlog"')[0]


def test_the_budget_section_follows_the_delivery_numbers_and_stopped_fails_loudly() -> None:
    _, run = _tick()
    assert run.index('echo "### Delivery"') < run.index('echo "### Budget"') < run.index('echo "### Backlog"')
    assert "python -m repo_presenter.core.llm.budget status" in run
    budget = run[run.index('echo "### Budget"'):run.index('echo "### Backlog"')]
    assert "grep -q '^STOPPED:'" in budget
    assert "::error title=Budget STOPPED::" in budget
    assert budget.count("status=1") == 2  # STOPPED, or an unreadable status, fails the tick
    assert run.rstrip().endswith('exit "$status"') or 'exit "$status"' in run


def test_the_tick_stays_read_only() -> None:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert doc["permissions"] == {"contents": "read", "attestations": "read"}
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")


def test_the_stopped_line_the_tick_greps_is_what_status_prints() -> None:
    from repo_presenter.core.llm.budget import budget_summary_lines

    lines = budget_summary_lines({"total_calls_cap": 9000, "total_tokens_cap": 1, "batches": [],
                                  "stop": {"reason": "cost per sealed candidate ..."}})
    assert any(line.startswith("STOPPED:") for line in lines)
