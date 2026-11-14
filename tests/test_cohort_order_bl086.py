"""BL-086 (audit O2, supervisor decision 2026-11-14): the planner's order within the batch of six
and the two-failure cap, against real-shaped inputs -- the provider-spend ledger's ``settle``
entries and the failure records BL-084 backfilled from the logs of the hosted runs since
2026-11-12 (``evidence/build/BL-084/backfill_records.json``). Zero calls, no network.

A "fix landing" is simulated by changing the hash of one path set: every recorded class scope is
re-stamped as a deterministic hash of its paths, and the current-code scope function returns a
different hash for any scope that contains the fixed file -- exactly what ``scope_fingerprint``
does when a commit touches that file."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from repo_presenter import failures  # noqa: E402
from scripts.select_scheduled_cohort import (  # noqa: E402
    MAX_CELLS,
    PRIORITY_LABELS,
    plan_cohort,
    render_summary,
)

RECORDS = json.loads((ROOT / "evidence" / "build" / "BL-084" / "backfill_records.json").read_text("utf-8"))
NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
CODE_NOW = "code-after-the-fix"
RUNS = "https://github.com/babar-raza/repo-presenter/actions/runs/"
CLAIMS = "src/repo_presenter/readme/validation/claims.py"

D3_NET = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
D3_PY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
CELLS_RUST = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"
CELLS_TS = "aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript"
EMAIL_NET = "aspose-email-foss/Aspose.Email-FOSS-for-.Net"
IMAGING_NET = "aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET"
NOTE_PY = "aspose-note-foss/Aspose.Note-FOSS-for-Python"
PDF_JAVA = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"
PSD_NET = "aspose-psd-foss/Aspose.PSD-FOSS-for-.NET"
REGISTRY = [D3_NET, D3_PY, CELLS_RUST, CELLS_TS, EMAIL_NET, IMAGING_NET, NOTE_PY, PDF_JAVA, PSD_NET]


@dataclass
class Entry:
    repository: str
    ecosystem: str = "net"
    active: bool = True


@dataclass
class Cert:
    outcome: str
    certified: bool
    failing_checks: tuple[str, ...] = ()


def _hash(paths: Any) -> str:
    return hashlib.sha256("\n".join(sorted(paths)).encode()).hexdigest()


def _records(repositories: set[str]) -> list[dict[str, Any]]:
    """The real Lane R records of ``repositories``, each class re-stamped with ``_hash``."""
    chosen = []
    for record in RECORDS:
        if record["repository"] not in repositories or record["lane"] != "R":
            continue
        record = copy.deepcopy(record)
        for item in record["classes"].values():
            if item.get("scope_paths"):
                item["scope"] = _hash(item["scope_paths"])
        chosen.append(record)
    return chosen


def _settle(record: dict[str, Any]) -> dict[str, Any]:
    sealed = record["outcome"] == "success"
    return {
        "kind": "settle", "id": f"cohort-{record['run_id']}-1-1", "repository": record["repository"],
        "outcomes": {"R": "success" if sealed else "failure"}, "sealed": ["R"] if sealed else [],
        "code": record["code"], "source_revision": record["source_revision"], "at": record["at"],
        "run_url": RUNS + record["run_id"], "epoch": 2,
    }


def _scope_of(fixed: tuple[str, ...]):
    def scope_of(paths: Any) -> str:
        return "after-fix" if any(path in paths for path in fixed) else _hash(paths)
    return scope_of


def _plan(*, fixed: tuple[str, ...] = (CLAIMS,), records=None, extra_ledger=(), heads=None,
          certs=None, registry=REGISTRY, hold: bool = True) -> dict[str, Any]:
    records = _records(set(registry)) if records is None else records
    documents = failures.documents_from_records(records)
    scope_of = _scope_of(fixed)
    latest = {doc["repository"]: doc["latest"]["source_revision"] for doc in documents}
    heads = {**latest, **(heads or {})}
    # Lane L is not under test: every Lane L cell certified.
    certifications = {(repo, "L"): Cert("RECERTIFIED", True) for repo in registry}
    certifications.update(certs or {})
    return plan_cohort(
        entries={repo: Entry(repo) for repo in registry},
        authorized_repos=set(registry),
        certifications=certifications,
        ledger={"entries": [_settle(r) for r in records] + list(extra_ledger)},
        terminals=[],
        code=CODE_NOW,
        head=lambda repo: heads.get(repo, "head-" + repo),
        now=NOW,
        known=failures.known_failures(documents, scope_of) if hold else None,
        scopes=failures.scope_status(documents, scope_of),
    )


def _imaging_attempt() -> dict[str, Any]:
    """Imaging .NET: one hosted Lane R attempt before failure records existed (no record)."""
    return {
        "kind": "settle", "id": "cohort-43400000001-1-1", "repository": IMAGING_NET,
        "outcomes": {"R": "failure"}, "sealed": [], "code": "aafe239c-older", "source_revision": "im1",
        "at": "2026-11-11T10:00:00+00:00", "run_url": RUNS + "43400000001", "epoch": 2,
    }


def _order(plan: dict[str, Any]) -> list[tuple[int, str, str]]:
    return [(run["order"], run["repository"], run["priority"]["R"]) for run in plan["runs"]]


def _skip(plan: dict[str, Any], repository: str) -> dict[str, Any]:
    return next(s for s in plan["skipped"] if s["repository"] == repository and s["lane"] == "R")


def test_the_real_records_have_the_shapes_the_planner_reads() -> None:
    documents = failures.documents_from_records(_records(set(REGISTRY)))
    status = failures.scope_status(documents, _scope_of((CLAIMS,)))
    assert status[(D3_PY, "R")] == {
        "run_id": "43529879702", "source_revision": status[(D3_PY, "R")]["source_revision"], "transient": False,
        "changed": ["claim_contradiction|unresolved|stub_format"], "unchanged": [], "unscoped": [],
    }
    assert status[(D3_NET, "R")]["changed"] == []  # disposition_coverage / live_readme_loss: not claims.py
    assert status[(EMAIL_NET, "R")]["changed"] == ["claim_contradiction|unresolved|member_kind"]


def test_the_batch_is_ordered_fix_landed_then_never_attempted_then_unrecorded_repair_then_retry() -> None:
    plan = _plan(
        extra_ledger=[_imaging_attempt()],
        heads={CELLS_RUST: "rust-moved"},  # releases BL-084's hold: a plain retry, rank (d)
        certs={(IMAGING_NET, "R"): Cert("NEEDS_REPAIR", False, ("BC-18",)),
               (PSD_NET, "R"): Cert("NEEDS_REPAIR", False, ("BC-07",))},
    )
    assert _order(plan) == [
        (1, D3_PY, PRIORITY_LABELS[0]),       # (a) 5 failures in a row, but the fix reached stub_format
        (2, EMAIL_NET, PRIORITY_LABELS[0]),   # (a) member_kind is in claims.py's scope
        (3, PSD_NET, PRIORITY_LABELS[1]),     # (b) never attempted, NEEDS_REPAIR seal first in the tie
        (4, NOTE_PY, PRIORITY_LABELS[1]),     # (b) never attempted, no seal
        (5, PDF_JAVA, PRIORITY_LABELS[1]),    # (b)
        (6, IMAGING_NET, PRIORITY_LABELS[2]),  # (c) NEEDS_REPAIR, attempted before records existed
    ]
    assert sum(len(run["lanes"]) for run in plan["runs"]) == MAX_CELLS
    assert [(q["order"], q["repository"], q["priority"]) for q in plan["queued"]] == [
        (1, CELLS_RUST, PRIORITY_LABELS[3])  # (d) upstream moved, scope unchanged
    ]
    assert plan["runs"][0]["reasons"]["R"] == (
        "no seal; fix landed: code scope changed for claim_contradiction|unresolved|stub_format"
    )
    assert "no failure record of the last attempt" in plan["runs"][5]["reasons"]["R"]
    # BL-084's hold stays: Cells TypeScript (BC-05, unchanged) and 3D .NET (five failures, unchanged).
    assert _skip(plan, CELLS_TS)["category"] == "known_failure"
    assert _skip(plan, D3_NET)["category"] == "known_failure"

    summary = render_summary(plan)
    assert "| # | repository | lane | priority | why | budget |" in summary
    assert f"| 1 | {D3_PY} | R | R: (a) fix landed | R: no seal; fix landed:" in summary
    assert f"- 1. {CELLS_RUST} Lane R: (d) retry; no seal; upstream moved" not in summary  # code changed
    assert f"- 1. {CELLS_RUST} Lane R: (d) retry; no seal; code changed since the last attempt" in summary


def test_without_a_fix_the_retried_cells_are_held_or_capped_and_first_attempts_lead() -> None:
    plan = _plan(fixed=(), heads={D3_NET: "moved", D3_PY: "moved", CELLS_RUST: "moved"})
    ranks = {run["repository"]: run["priority"]["R"] for run in plan["runs"]}
    assert ranks == {IMAGING_NET: PRIORITY_LABELS[1], NOTE_PY: PRIORITY_LABELS[1],
                     PDF_JAVA: PRIORITY_LABELS[1], PSD_NET: PRIORITY_LABELS[1], CELLS_RUST: PRIORITY_LABELS[3]}
    # The four-cells-take-17-runs pattern: an upstream move releases BL-084's hold, the cap still applies.
    for repository in (D3_NET, D3_PY):
        skipped = _skip(plan, repository)
        assert skipped["category"] == "capped"
        assert "no class of the last failure has a changed code scope" in skipped["reason"]
    assert {c["repository"] for c in plan["capped"]} == {D3_NET, D3_PY}
    assert "### Capped: two hosted failures, no scope change (2)" in render_summary(plan)
    # Same upstream: the hold is the stronger statement and keeps its category.
    same = _plan(fixed=())
    assert _skip(same, D3_NET)["category"] == "known_failure"
    assert _skip(same, CELLS_TS)["category"] == "known_failure"


def test_the_cap_applies_after_two_failures_not_one() -> None:
    rust = _records({CELLS_RUST})  # one real failure (43516334907)
    assert _plan(records=rust, registry=[CELLS_RUST], heads={CELLS_RUST: "moved"}, fixed=())["runs"]
    second = copy.deepcopy(rust[0])
    second.update(run_id="43600000000", at="2026-11-14T08:00:00Z", source_revision="moved")
    plan = _plan(records=rust + [second], registry=[CELLS_RUST], heads={CELLS_RUST: "moved-again"}, fixed=())
    assert plan["runs"] == []
    assert _skip(plan, CELLS_RUST)["category"] == "capped"
    assert plan["capped"][0]["consecutive_failures"] == 2


def test_the_cap_without_any_record_and_its_release_by_a_seal_or_a_transient_failure() -> None:
    def attempt(run_id: str, *, sealed: bool = False, hours: int) -> dict[str, Any]:
        return {"kind": "settle", "id": f"cohort-{run_id}-1-1", "repository": NOTE_PY,
                "outcomes": {"R": "success" if sealed else "failure"}, "sealed": ["R"] if sealed else [],
                "code": f"old-{hours}", "source_revision": "n1",
                "at": f"2026-11-13T{10 + hours:02d}:00:00+00:00", "run_url": RUNS + run_id, "epoch": 2}

    two = [attempt("1", hours=1), attempt("2", hours=2)]
    plan = _plan(records=[], registry=[NOTE_PY], extra_ledger=two)
    assert _skip(plan, NOTE_PY)["category"] == "capped"
    assert "no failure record of the last attempt" in _skip(plan, NOTE_PY)["reason"]
    # A seal in between ends the streak.
    sealed_between = [attempt("1", hours=1), attempt("2", sealed=True, hours=2), attempt("3", hours=3)]
    assert _plan(records=[], registry=[NOTE_PY], extra_ledger=sealed_between)["runs"]
    # A transient last failure (an infrastructure retry) does not cap.
    transient = failures.finalize(
        failures.build_record(repository=NOTE_PY, lane="R", outcome="failure",
                              failure_detail="no valid independent review (retryable: a re-run asks the reviewer again)"),
        run_id="2", source_revision="n1", at="2026-11-13T12:00:00Z", code="old-2", root=ROOT,
    )
    assert transient["failure"]["transient"]
    plan = _plan(records=[], registry=[NOTE_PY], extra_ledger=two, hold=False)
    assert plan["runs"] == []
    documents = failures.documents_from_records([transient])
    released = plan_cohort(
        entries={NOTE_PY: Entry(NOTE_PY)}, authorized_repos={NOTE_PY},
        certifications={(NOTE_PY, "L"): Cert("RECERTIFIED", True)}, ledger={"entries": two}, terminals=[],
        code=CODE_NOW, head=lambda _r: "n1", now=NOW,
        known=failures.known_failures(documents, _scope_of(())),
        scopes=failures.scope_status(documents, _scope_of(())),
    )
    assert [run["repository"] for run in released["runs"]] == [NOTE_PY]


@pytest.mark.parametrize("fixed", [(CLAIMS,), ("src/repo_presenter/readme/review/independent_reviewer.py",)])
def test_a_fix_in_the_scope_of_a_held_cell_releases_it_at_rank_a(fixed: tuple[str, ...]) -> None:
    plan = _plan(fixed=fixed, registry=[D3_PY, EMAIL_NET])
    assert {run["repository"] for run in plan["runs"]} == {D3_PY, EMAIL_NET}
    assert all(run["priority"]["R"] == PRIORITY_LABELS[0] for run in plan["runs"])
    assert plan["known_failure"] == [] and plan["capped"] == []


def test_a_record_of_an_older_attempt_does_not_count_as_a_landed_fix() -> None:
    records = _records({EMAIL_NET})
    later = {"kind": "settle", "id": "cohort-43700000000-1-1", "repository": EMAIL_NET,
             "outcomes": {"R": "failure"}, "sealed": [], "code": "newer", "source_revision": "e2",
             "at": "2026-11-14T09:00:00+00:00", "run_url": RUNS + "43700000000", "epoch": 2}
    plan = _plan(records=records, registry=[EMAIL_NET], extra_ledger=[later], heads={EMAIL_NET: "e2"})
    assert plan["runs"] == []
    assert "no failure record of the last attempt" in _skip(plan, EMAIL_NET)["reason"]


def test_the_existing_bounds_still_hold() -> None:
    plan = _plan(extra_ledger=[_imaging_attempt()])
    assert sum(len(run["lanes"]) for run in plan["runs"]) <= MAX_CELLS
    in_flight = {"kind": "reserve", "id": "cohort-9-1-1", "repository": NOTE_PY, "lanes": ["R"],
                 "at": NOW.isoformat(), "epoch": 2}
    held = _plan(extra_ledger=[in_flight])
    assert held["runs"] == [] and held["held"]["in_flight_cells"] == 1
    assert {q["repository"] for q in held["queued"]} >= {D3_PY, EMAIL_NET}
