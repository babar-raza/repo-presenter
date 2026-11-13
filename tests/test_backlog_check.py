"""R40: the backlog checker passes on the committed backlog and refuses done-without-evidence, duplicates and gaps."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("backlog_check", Path(__file__).resolve().parent.parent / "ops" / "checks" / "backlog_check.py")
bc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bc)  # type: ignore[union-attr]

GOOD = {"id": "BL-1", "title": "t", "type": "task", "source": "owner", "priority": "P1", "status": "open",
        "implementation_path": "p", "acceptance": "a", "evidence": []}


def test_the_committed_backlog_passes() -> None:
    assert bc.main() == 0


def test_done_without_evidence_is_refused() -> None:
    assert any("done without evidence" in p for p in bc.problems({"items": [dict(GOOD, status="done")]}))


def test_duplicates_unknown_dependencies_and_missing_fields_are_refused() -> None:
    found = bc.problems({"items": [GOOD, dict(GOOD), dict(GOOD, id="BL-2", source="", depends_on=["BL-9"])]})
    assert any("duplicate id BL-1" in p for p in found)
    assert any("BL-2: missing source" in p for p in found)
    assert any("unknown item BL-9" in p for p in found)


def test_an_open_task_card_no_item_names_is_refused() -> None:
    state = {"release_gate_dashboard": {"cards": [{"id": "TC-077", "status": "READY"}, {"id": "TC-001", "status": "ACCEPTED"}]}}
    assert bc.untracked_cards({"items": [GOOD]}, state) == ["task card TC-077 is READY but no backlog item names it"]
    assert bc.untracked_cards({"items": [dict(GOOD, title="fix TC-077")]}, state) == []


def test_a_new_decision_log_entry_without_a_backlog_line_is_refused() -> None:
    log = "## 2026-11-13: old\nno line needed\n## 2026-11-15: new decision\ntext\n## 2026-11-16: tracked\nBacklog: BL-001\n"
    found = bc.untracked_decisions(log)
    assert len(found) == 1 and "2026-11-15" in found[0]


def test_stale_items_are_reported_by_status_age() -> None:
    import datetime as dt
    doc = {"items": [dict(GOOD, status="active", updated="2026-11-01"), dict(GOOD, id="BL-2", status="open", updated="2026-11-10")]}
    old = bc.stale(doc, dt.date(2026, 11, 13))
    assert len(old) == 1 and old[0].startswith("BL-1")


def test_a_done_item_citing_an_unlanded_commit_is_refused() -> None:
    doc = {"items": [dict(GOOD, status="done", evidence=["merged in abc1234"])]}
    assert bc.unlanded_done(doc, lambda sha: False) == ["BL-1: done, but cited commit abc1234 is not in this history (not landed)"]
    assert bc.unlanded_done(doc, lambda sha: True) == []
    assert bc.unlanded_done(doc, lambda sha: None) == []


def test_a_feedback_or_defect_item_is_done_only_after_portfolio_reverification() -> None:
    base = dict(GOOD, status="done", evidence=["fixed in abc1234"])
    for kind in ("feedback", "defect"):
        assert any("R41" in p for p in bc.problems({"items": [dict(base, type=kind)]}))
        ok = dict(base, type=kind, evidence=["reverified: run 123, lane R 5/5, lane L 26/26"])
        assert not any("R41" in p for p in bc.problems({"items": [ok]}))
    assert not any("R41" in p for p in bc.problems({"items": [dict(base, type="task")]}))
