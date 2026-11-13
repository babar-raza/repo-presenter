"""scripts/select_scheduled_cohort.plan_cohort (owner ruling R37, 2026-11-13): which cells a
scheduled fire runs, and why every other cell is skipped -- needs-work, terminals, idempotency,
in-flight and bounded retries, against an in-memory ledger (no network, no provider)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.select_scheduled_cohort import (
    load_terminals,
    plan_cohort,
    render_summary,
)

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
CODE = "code-now"
HEAD = "b" * 40


@dataclass
class Entry:
    repository: str
    ecosystem: str = "python"
    active: bool = True


@dataclass
class Cert:
    outcome: str
    certified: bool
    failing_checks: tuple[str, ...] = ()


def _entries(*names: str, inactive: tuple[str, ...] = ()) -> dict[str, Entry]:
    return {name: Entry(name, active=name not in inactive) for name in names}


def _settle(repository, lane, *, sealed=False, code=CODE, revision=HEAD, outcome=None, hours=1, **extra):
    return {
        "kind": "settle", "id": f"s-{repository}-{lane}-{hours}-{code}-{revision[:4]}",
        "repository": repository, "outcomes": {lane: outcome or ("success" if sealed else "failure")},
        "sealed": [lane] if sealed else [], "code": code, "source_revision": revision,
        "at": (NOW - timedelta(hours=hours)).isoformat(), "epoch": 2, **extra,
    }


def _plan(entries, *, certs=None, entries_ledger=(), terminals=(), head=lambda repo: HEAD, **kw):
    return plan_cohort(
        entries=entries,
        authorized_repos=set(entries),
        certifications=certs or {},
        ledger={"entries": list(entries_ledger)},
        terminals=list(terminals),
        code=CODE,
        head=head,
        now=NOW,
        **kw,
    )


def _skip(plan, repository, lane):
    return next(s for s in plan["skipped"] if s["repository"] == repository and s["lane"] == lane)


def test_never_attempted_cells_run_with_both_lanes_in_one_run() -> None:
    plan = _plan(_entries("o/a"))
    assert [(r["repository"], r["lane"], r["lanes"]) for r in plan["runs"]] == [("o/a", "both", ["R", "L"])]


def test_a_certified_lane_is_skipped_and_the_other_lane_runs_alone() -> None:
    plan = _plan(_entries("o/a"), certs={("o/a", "R"): Cert("RECERTIFIED", True)})
    assert [(r["repository"], r["lane"]) for r in plan["runs"]] == [("o/a", "L")]
    assert _skip(plan, "o/a", "R")["category"] == "certified"
    assert plan["certified"] == {"R": 1, "L": 0}


def test_needs_repair_seals_are_picked_first() -> None:
    plan = _plan(
        _entries("o/a", "o/b"),
        certs={("o/b", "R"): Cert("NEEDS_REPAIR", False, ("L-03",)),
               ("o/b", "L"): Cert("RECERTIFIED", True)},
    )
    assert [r["repository"] for r in plan["runs"]] == ["o/b", "o/a"]
    assert "NEEDS_REPAIR (L-03)" in plan["runs"][0]["reasons"]["R"]


def test_at_most_six_cells_per_fire_and_the_rest_are_queued() -> None:
    names = [f"o/r{i}" for i in range(5)]
    plan = _plan(_entries(*names))
    assert sum(len(r["lanes"]) for r in plan["runs"]) == 6
    assert len(plan["runs"]) == 3
    assert len(plan["queued"]) == 4


def test_inactive_and_unauthorized_entries_are_skipped() -> None:
    entries = _entries("o/a", "o/php", inactive=("o/php",))
    plan = plan_cohort(
        entries=entries, authorized_repos={"o/php"}, certifications={}, ledger={"entries": []},
        terminals=[], code=CODE, head=lambda repo: HEAD, now=NOW,
    )
    assert plan["runs"] == []
    assert _skip(plan, "o/php", "R")["category"] == "inactive"
    assert _skip(plan, "o/a", "L")["category"] == "unauthorized"


def test_a_terminal_cell_is_skipped_at_its_pinned_revision_and_lapses_when_upstream_moves() -> None:
    terminal = {"repository": "o/a", "lane": "R", "outcome": "BLOCKED_EXTERNAL", "ruling": "R24",
                "revision": HEAD, "recheck_by": "2026-11-20"}
    plan = _plan(_entries("o/a"), terminals=[terminal])
    assert [(r["repository"], r["lane"]) for r in plan["runs"]] == [("o/a", "L")]
    assert _skip(plan, "o/a", "R")["category"] == "terminal"
    moved = _plan(_entries("o/a"), terminals=[terminal], head=lambda repo: "c" * 40)
    assert moved["runs"][0]["lane"] == "both"
    assert "terminal lapsed" in moved["notes"][0]


def test_an_unreadable_upstream_keeps_the_terminal_and_an_overdue_recheck_is_reported() -> None:
    terminal = {"repository": "o/a", "lane": "L", "outcome": "NOT_APPLICABLE", "ruling": "R20",
                "revision": HEAD, "recheck_by": "2026-11-01"}
    plan = _plan(_entries("o/a"), terminals=[terminal], head=lambda repo: None)
    assert "OVERDUE" in _skip(plan, "o/a", "L")["reason"]


def test_a_failure_on_the_same_code_and_upstream_revision_is_not_repeated() -> None:
    plan = _plan(_entries("o/a"), entries_ledger=[_settle("o/a", "R"), _settle("o/a", "L")])
    assert plan["runs"] == []
    assert _skip(plan, "o/a", "R")["category"] == "idempotent"


def test_a_failure_is_retried_after_a_code_change_or_an_upstream_move() -> None:
    old_code = _plan(_entries("o/a"), entries_ledger=[_settle("o/a", "R", code="code-old")],
                     certs={("o/a", "L"): Cert("RECERTIFIED", True)})
    assert old_code["runs"][0]["lane"] == "R"
    assert "code changed" in old_code["runs"][0]["reasons"]["R"]
    moved = _plan(_entries("o/a"), entries_ledger=[_settle("o/a", "R", revision="a" * 40)],
                  certs={("o/a", "L"): Cert("RECERTIFIED", True)})
    assert "upstream moved" in moved["runs"][0]["reasons"]["R"]


def test_an_unreadable_upstream_head_is_read_as_unchanged() -> None:
    plan = _plan(_entries("o/a"), entries_ledger=[_settle("o/a", "R")],
                 certs={("o/a", "L"): Cert("RECERTIFIED", True)}, head=lambda repo: None)
    assert plan["runs"] == []


def test_three_consecutive_failures_on_unchanged_code_set_the_cell_aside_for_diagnosis() -> None:
    ledger = [
        _settle("o/a", "R", revision="1" * 40, hours=5),
        _settle("o/a", "R", revision="2" * 40, hours=3),
        _settle("o/a", "R", revision="3" * 40, hours=1),
    ]
    plan = _plan(_entries("o/a"), entries_ledger=ledger, certs={("o/a", "L"): Cert("RECERTIFIED", True)})
    assert plan["runs"] == []
    assert plan["diagnose"][0]["consecutive_failures"] == 3
    assert _skip(plan, "o/a", "R")["category"] == "diagnose"


def test_a_code_change_resets_the_retry_bound() -> None:
    ledger = [
        _settle("o/a", "R", revision="1" * 40, hours=5, code="code-old"),
        _settle("o/a", "R", revision="2" * 40, hours=3, code="code-old"),
        _settle("o/a", "R", revision="3" * 40, hours=1, code="code-old"),
    ]
    plan = _plan(_entries("o/a"), entries_ledger=ledger, certs={("o/a", "L"): Cert("RECERTIFIED", True)})
    assert plan["runs"][0]["lane"] == "R" and plan["diagnose"] == []


def test_a_budget_refused_run_is_not_an_attempt() -> None:
    plan = _plan(_entries("o/a"), entries_ledger=[_settle("o/a", "R", budget_refused=True)],
                 certs={("o/a", "L"): Cert("RECERTIFIED", True)})
    assert plan["runs"][0]["lane"] == "R"


def test_a_cell_with_an_unsettled_reservation_is_in_flight_until_the_ttl() -> None:
    reserve = {"kind": "reserve", "id": "cohort-1-1", "repository": "o/a", "lanes": ["R", "L"],
               "batch": "b", "calls": 10, "tokens": 10, "epoch": 2,
               "at": (NOW - timedelta(hours=1)).isoformat()}
    plan = _plan(_entries("o/a"), entries_ledger=[reserve])
    assert plan["runs"] == [] and _skip(plan, "o/a", "L")["category"] == "in_flight"
    stale = dict(reserve, at=(NOW - timedelta(hours=7)).isoformat())
    assert _plan(_entries("o/a"), entries_ledger=[stale])["runs"]
    settled = _settle("o/a", "R", sealed=True)
    settled["id"] = "cohort-1-1"
    assert not any(s["category"] == "in_flight" for s in _plan(_entries("o/a"), entries_ledger=[reserve, settled])["skipped"])


def test_the_summary_leads_with_certified_counts_per_lane() -> None:
    plan = _plan(_entries("o/a"), certs={("o/a", "R"): Cert("RECERTIFIED", True)})
    text = render_summary(plan, ["envelope: 1 / 9 calls"])
    first = next(line for line in text.splitlines() if line.strip() and not line.startswith("#"))
    assert "Lane R 1" in first and "Lane L 0" in first
    assert "| o/a | R | certified |" in text and "| o/a | L |" in text


def test_the_committed_terminal_list_names_the_recorded_terminals() -> None:
    cells = {(c["repository"], c["lane"]): c for c in load_terminals()}
    assert ("aspose-psd-foss/Aspose.PSD-FOSS-for-Java", "R") in cells
    assert ("aspose-gis-foss/Aspose.GIS.FOSS-for-.Net", "L") in cells
    log = (Path(__file__).resolve().parent.parent / "docs" / "DECISION_LOG.md").read_text("utf-8")
    for cell in cells.values():
        assert len(cell["revision"]) == 40 and cell["recheck_by"] and cell["outcome"]
        assert cell["repository"].split("/")[1].split("-for-")[0].split(".")[1].split("-")[0] in log


def test_a_missing_terminal_list_is_an_error_not_an_empty_list(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_terminals(tmp_path / "missing.json")
