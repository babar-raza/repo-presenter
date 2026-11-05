"""Owner decision 2026-11-05: a release-gate card whose deliverable is a supervisor-owned artifact
declares ``executor: supervisor`` and may write the GLOBAL_DENY paths its own write_paths name,
never the gate's machinery. Before this, eight cards declared paths the scope check always refused,
so they could never be accepted whatever their checks said, and nothing reported it."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ops"))

import gatectl  # noqa: E402


def card(write_paths, executor=None):
    c = {"id": "TC-900", "write_paths": write_paths}
    if executor:
        c["executor"] = executor
    return c


def test_a_worker_card_declaring_a_denied_path_is_reported():
    problems = gatectl.write_path_problems(card(["data/reviewer_calibration.json"]))
    assert len(problems) == 1 and "executor: supervisor" in problems[0]
    assert gatectl.denied_for(card([]), "docs/DECISION_LOG.md")


def test_a_supervisor_card_may_write_its_supervisor_owned_artifacts():
    sup = card(
        ["data/reviewer_calibration.json", "docs/DECISION_LOG.md", ".github/workflows/x.yml"],
        executor="supervisor",
    )
    assert gatectl.write_path_problems(sup) == []
    for path in ("data/reviewer_calibration.json", "evidence/build/G/TC-900/r.json"):
        assert not gatectl.denied_for(sup, path)


@pytest.mark.parametrize(
    "path",
    ["ops/gatectl.py", "ops/checks/calibration_status.py", "schemas/taskcard.schema.json",
     "project/state.yaml", "project/taskcards/TC-007.yaml", "AGENTS.md", ".claude/settings.json"],
)
def test_no_card_may_touch_the_gate_machinery(path):
    sup = card([path], executor="supervisor")
    assert gatectl.denied_for(sup, path)
    assert gatectl.write_path_problems(sup)


def test_the_exemption_hangs_on_the_executor_field(monkeypatch):
    """Falsifier: with the field ignored, a supervisor card is a worker card again."""
    monkeypatch.setattr(gatectl, "is_supervisor_card", lambda c: False)
    sup = card(["data/reviewer_calibration.json"], executor="supervisor")
    assert gatectl.write_path_problems(sup)
    assert gatectl.denied_for(sup, "data/reviewer_calibration.json")


def test_every_committed_card_declares_only_acceptable_write_paths():
    for path in sorted((REPO / "project" / "taskcards").glob("TC-*.yaml")):
        c = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert gatectl.write_path_problems(c) == [], path.name
