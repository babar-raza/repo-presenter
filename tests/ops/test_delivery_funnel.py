"""The funnel reports the counter's verified acceptance without inventing delivery evidence."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "delivery_funnel", ROOT / "ops" / "checks" / "delivery_funnel.py"
)
funnel = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = funnel
SPEC.loader.exec_module(funnel)
pdc = funnel.pdc


def outcome(repository, lane, *, current=True, no_action=False):
    return pdc.LaneOutcome(
        repository=repository,
        lane=lane,
        record_state="ACCEPTED",
        pipeline_good=True,
        current=current,
        bucket=pdc.UNCALIBRATED,
        revision="rev1",
        certification="RECERTIFIED",
        no_action=no_action,
    )


def verified_outcomes():
    rows = [
        outcome("org/accepted-r", "R"),
        outcome("org/accepted-l", "L"),
        outcome("org/no-edit", "L", no_action=True),
        outcome("org/unreviewed", "L"),
        outcome("org/older", "R", current=False),
    ]
    # Use the same attestation/revision classification the real collector applies.
    pdc.apply_attested(rows, {(row.repository, row.lane): "rev1" for row in rows[:3]}, {})
    return rows


def test_reports_verified_acceptance_per_lane_without_counting_no_action_or_old_seals():
    result = funnel.funnel(verified_outcomes(), SimpleNamespace(complete=True), 5)

    assert result["R"]["independently_accepted"] == 1
    assert result["L"]["independently_accepted"] == 1
    assert result["L"]["mechanism_passing"] == 2
    assert result["L"]["pr_created"] == 0
    assert result["L"]["live_verified"] == 0


def test_header_does_not_call_accepted_candidates_mechanism_only_or_claim_zero_issues(monkeypatch, capsys):
    from repo_presenter.core.registry import loader

    monkeypatch.setattr(funnel.pdc, "collect", lambda remote: (
        verified_outcomes(), None, SimpleNamespace(complete=True)
    ))
    monkeypatch.setattr(loader, "load_registry", lambda path: SimpleNamespace(entries=[None] * 5))

    assert funnel.main([]) == 0
    header = capsys.readouterr().out.splitlines()[0]
    assert "Lane R 1/25 | Lane L 1/25" in header
    assert "mechanism-passing only R 0 L 1" in header
    assert "upstream issues unmeasured" in header
