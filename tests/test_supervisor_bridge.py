"""BL-770 / BL-771 (WP-7): the supervisor execution bridge and the liveness dead-man."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from scripts import supervisor_bridge as bridge

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
RUN = {"repository": "o/r", "ecosystem": "python", "lane": "R"}


def _at(minutes_ago: float) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).isoformat()


def _leases(entries: list[dict]) -> dict:
    return bridge.lease_view(entries, NOW)


def _plan(runs: list[dict] | None = None, **extra) -> dict:
    return {"runs": runs if runs is not None else [RUN], "certified": {"R": 3, "L": 4}, **extra}


def test_authorized_due_and_idle_dispatches_with_the_run_request_json() -> None:
    d = bridge.decide(authorized=True, plan=_plan(), leases=_leases([]))
    assert d["action"] == "dispatch"
    assert d["next_run_request"] == {"job": "present", "repository": "o/r", "ecosystem": "python", "lane": "R"}


def test_unauthorized_policy_never_dispatches_but_previews() -> None:
    d = bridge.decide(authorized=False, plan=_plan(), leases=_leases([]))
    assert d["action"] == "none" and "not true" in d["reason"]
    assert d["next_run_request"] is not None  # preview only


def test_dry_run_never_dispatches() -> None:
    d = bridge.decide(authorized=True, plan=_plan(), leases=_leases([]), dry_run=True)
    assert d["action"] == "none" and d["dry_run"] and "would dispatch" in d["reason"]


def test_a_live_cohort_lease_holds_and_nothing_due_does_nothing() -> None:
    live = _leases([{"kind": "reserve", "id": "cohort-1-1-0", "repository": "o/r", "lanes": ["R"], "at": _at(30)}])
    assert bridge.decide(authorized=True, plan=_plan(), leases=live)["action"] == "none"
    assert "held" in bridge.decide(authorized=True, plan=_plan(), leases=live)["reason"]
    assert bridge.decide(authorized=True, plan=_plan([]), leases=_leases([]))["action"] == "none"


def test_a_settled_lease_is_released_and_an_expired_one_is_recovered() -> None:
    entries = [
        {"kind": "reserve", "id": "cohort-1-1-0", "repository": "o/r", "lanes": ["R"], "at": _at(30)},
        {"kind": "settle", "id": "cohort-1-1-0", "at": _at(5)},
        {"kind": "reserve", "id": "cohort-0-1-0", "repository": "o/s", "lanes": ["L"], "at": _at(60 * 7)},
    ]
    view = _leases(entries)
    assert view["live"] == [] and view["expired_total"] == 1  # the 7 h old one passed the 6 h TTL
    assert bridge.decide(authorized=True, plan=_plan(), leases=view)["action"] == "dispatch"


def test_a_planner_block_or_unreadable_inputs_fail_closed() -> None:
    d = bridge.decide(authorized=True, plan={"runs": [RUN], "blocked": "boom"}, leases=_leases([]))
    assert d["action"] == "none"


def test_ready_work_without_a_lease_past_an_hour_is_a_stall() -> None:
    old = _leases([{"kind": "settle", "id": "x", "at": _at(61)}])
    assert bridge.decide(authorized=True, plan=_plan(), leases=old)["stall"]
    assert bridge.decide(authorized=False, plan=_plan(), leases=old)["stall"] is None
    fresh = _leases([{"kind": "settle", "id": "x", "at": _at(10)}])
    assert bridge.decide(authorized=True, plan=_plan(), leases=fresh)["stall"] is None


def test_policy_must_be_the_json_boolean_true(tmp_path: Path) -> None:
    p = tmp_path / "p.json"
    for value, expected in ((True, True), (False, False), ("true", False), (1, False)):
        p.write_text(json.dumps({"scheduled_execution_authorized": value}))
        assert bridge.policy_authorized(p) is expected
    p.write_text("{not json")
    assert bridge.policy_authorized(p) is False
    assert bridge.policy_authorized(tmp_path / "missing.json") is False


def test_the_run_request_is_valid_for_the_executor() -> None:
    import scripts.run_request as rr

    assert bridge.run_request(RUN)["job"] in rr.JOBS and RUN["lane"] in rr.LANES


def test_tick_bridge_jobs_are_gated_and_the_tick_stays_read_only() -> None:
    doc = yaml.safe_load((ROOT / ".github/workflows/supervisor-tick.yml").read_text(encoding="utf-8"))
    assert doc["permissions"] == {"contents": "read", "attestations": "read"}
    assert doc["jobs"]["bridge-plan"]["permissions"] == {"contents": "read", "attestations": "read"} or \
        doc["jobs"]["bridge-plan"].get("permissions", {}).get("contents") == "read"
    dispatch = doc["jobs"]["bridge-dispatch"]
    assert dispatch["needs"] == "bridge-plan"
    assert "action == 'dispatch'" in dispatch["if"]
    assert dispatch["uses"] == "./.github/workflows/present.yml"  # the engine's own authorization gate re-runs
    assert "secrets" not in dispatch


def test_liveness_is_read_only_and_has_the_dead_man() -> None:
    text = (ROOT / ".github/workflows/liveness.yml").read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    assert set(doc["permissions"].values()) <= {"read"}
    assert "secrets." not in text
    on = doc.get(True) or doc["on"]
    assert "schedule" in on and "workflow_run" in on
    assert "DEAD_AFTER_HOURS" in text and "supervisor-tick.yml" in text


def test_bridge_and_metadata_audit_run_requests_validate_and_are_read_only() -> None:
    import pytest

    import scripts.run_request as rr

    registry = ROOT / "data" / "registry.json"
    del registry  # validate() takes the registry for present only; these jobs read nothing from it
    for job in ("bridge", "metadata-audit"):
        assert job in rr.JOBS
    doc = yaml.safe_load((ROOT / ".github/workflows/run-request-execute.yml").read_text(encoding="utf-8"))
    bridge_job = doc["jobs"]["bridge"]
    assert bridge_job["permissions"] == {"contents": "read"}
    assert "--dry-run" in "\n".join(s.get("run", "") for s in bridge_job["steps"])
    audit_job = doc["jobs"]["metadata-audit"]
    assert audit_job["permissions"] == {"contents": "read"} and audit_job["uses"] == "./.github/workflows/metadata-audit.yml"
    audit = yaml.safe_load((ROOT / ".github/workflows/metadata-audit.yml").read_text(encoding="utf-8"))
    assert audit["permissions"] == {"contents": "read"} and audit["jobs"]["audit"]["permissions"] == {"contents": "read"}
    assert "secrets." not in (ROOT / ".github/workflows/metadata-audit.yml").read_text(encoding="utf-8")
    with pytest.raises(rr.RequestError):
        rr.validate({"job": "bridge", "lane": "R"}, {}, ["run-request.json"], True)
