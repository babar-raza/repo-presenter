"""BL-110: planner priority, against the real failure records of 2026-11-14 (the latest record of every
cell on refs/repository-presenter-state/failures/*, read 16:15Z). Zero calls, no network.

(a) a job error's scope includes readme/composition (where BL-094..BL-097 landed), so PDF Python's
    held ``presentation_planning`` truncation is released and ranks "fix landed";
(b) an OutputRejectedError wrapped in present.py's wording is parsed into its stage and last rejection,
    never ``unknown:model_output_was_rejected``, and is scoped (still transient: never held or capped);
(c) the authored-unit scope is what writes and checks an authored unit, so an unrelated composition
    change is no longer a "fix landed";
(d) while Lane L has reached 25 and Lane R has not, every Lane R cell ranks first, one slot per lane-cell;
(e) re-runs ((a), then (c)) rank ahead of never-attempted cells.

A landed fix is simulated as in tests/test_cohort_order_bl086.py: ``scope_of`` (now) hashes a path set
differently from ``scope_at`` (at the run's commit) when it contains a fixed file."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from repo_presenter import failures
from scripts.select_scheduled_cohort import (
    PRIORITY_FIX_LANDED,
    PRIORITY_LABELS,
    PRIORITY_NEEDS_REPAIR,
    PRIORITY_NEVER_ATTEMPTED,
    lane_ranks,
    plan_cohort,
)

_REAL = json.loads((ROOT / "tests" / "fixtures" / "failures" / "cells_2026-11-14.json").read_text("utf-8"))["documents"]
NOW = datetime(2026, 11, 14, 17, 0, tzinfo=UTC)
RUNS = "https://github.com/babar-raza/repo-presenter/actions/runs/"
AUTHORING = "src/repo_presenter/readme/composition/authoring.py"
PLANNING = "src/repo_presenter/readme/composition/planning.py"
RENDERER = "src/repo_presenter/readme/composition/renderer.py"

PDF_GO = "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go"
PDF_PY = "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python"
PDF_NET = "aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET"
PDF_CPP = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp"
PDF_TS = "aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript"
PAGE_PY = "aspose-page-foss/Aspose.Page-FOSS-for-Python"
D3_NET = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
WORDS_NET = "aspose-words-foss/Aspose.Words-FOSS-for-.NET"
NEW_R = "aspose-slides-foss/Aspose.Slides-FOSS-for-.NET"


def _restamped(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The real documents with every recorded scope hash re-stamped as ``_hash(paths, "before")`` (the
    fake tree at the run's commit), so recorded and re-derived scopes compare on one hash function."""
    documents = copy.deepcopy(documents)
    for doc in documents:
        for item in (doc["latest"].get("classes") or {}).values():
            if item.get("scope_paths"):
                item["scope"] = _hash(item["scope_paths"], "before")
    return documents


def _latest(repository: str, lane: str = "R") -> dict[str, Any]:
    return next(d["latest"] for d in DOCS if d["repository"] == repository and d["lane"] == lane)


def _hash(paths: Any, salt: str) -> str:
    return hashlib.sha256((salt + "\n".join(sorted(paths))).encode()).hexdigest()


def _scopes(fixed: tuple[str, ...]):
    """``scope_at`` at the run's commit, ``scope_of`` now: they differ exactly when a fixed file is in
    the scope (a path that is a directory prefix of a fixed file contains it)."""
    def touched(paths: Any) -> bool:
        return any(f == p or f.startswith(p.rstrip("/") + "/") for p in paths for f in fixed)

    def scope_at(paths: Any, revision: str) -> str:
        return _hash(paths, "before")

    def scope_of(paths: Any) -> str:
        return _hash(paths, "after" if touched(paths) else "before")

    return scope_of, scope_at


DOCS = _restamped(_REAL)


# ------------------------------------------------------------------------------------------------- (b)


def test_a_wrapped_output_rejection_is_parsed_into_its_stage_and_last_rejection() -> None:
    kinds = {repo: failures.job_error_kind(_latest(repo)["failure"]["detail"]) for repo in (PDF_GO, PDF_NET, PDF_TS, PDF_CPP)}
    assert kinds == {
        PDF_GO: ("OutputRejectedError", "section_authoring_text_contains_html_q"),
        PDF_NET: ("OutputRejectedError", "section_authoring_identifiers_that_are_not"),
        PDF_TS: ("OutputRejectedError", "section_authoring_identifiers_that_are_not"),
        PDF_CPP: ("OutputRejectedError", "section_authoring_identifiers_that_are_not"),
    }
    # an unwrapped exception reads as before
    assert failures.job_error_kind(_latest(PDF_PY)["failure"]["detail"]) == (
        "JobError", "presentation_planning_output_truncated_at")
    # a new record carries the parsed signature; a stored pre-BL-110 record is re-keyed on read
    record = failures.build_record(repository=PDF_GO, lane="R", outcome="failure",
                                   failure_detail=_latest(PDF_GO)["failure"]["detail"])
    assert list(record["classes"]) == ["job_error|job_error|OutputRejectedError:section_authoring_text_contains_html_q"]
    assert record["failure"]["transient"] is True
    stored = _latest(PDF_GO)
    assert list(stored["classes"]) == ["job_error|job_error|unknown:model_output_was_rejected"]  # as stored
    assert list(failures.reclassified(stored)["classes"]) == list(record["classes"])
    signatures = [row["signature"] for row in failures.pareto(_REAL)["classes"]]
    assert not any("unknown:model_output_was_rejected" in s for s in signatures)
    assert "job_error|job_error|OutputRejectedError:section_authoring_identifiers_that_are_not" in signatures


def test_an_output_rejection_is_scoped_but_never_held_or_capped() -> None:
    stored = failures.reclassified(_latest(PDF_NET))
    (item,) = stored["classes"].values()
    paths = failures.record_class_paths(stored, item)
    assert paths and "src/repo_presenter/readme/composition" in paths
    scope_of, scope_at = _scopes(())  # no fix: unchanged, but still never held (transient)
    assert failures.class_scope_changed(stored, item, scope_of, scope_at) is False
    assert failures.unchanged_classes(_latest(PDF_NET), scope_of, scope_at) is None
    # any other transient failure stays unscoped
    review = failures.build_record(repository=PDF_NET, lane="R", outcome="failure",
                                   failure_detail="no valid independent review (retryable: a re-run asks the reviewer again)")
    assert failures.record_class_paths(review, next(iter(review["classes"].values()))) is None


# ------------------------------------------------------------------------------------------------- (a)


def test_the_job_error_scope_includes_composition_and_reaches_records_already_written() -> None:
    record = _latest(PDF_PY)
    (item,) = record["classes"].values()
    assert "src/repo_presenter/readme/composition" not in item["scope_paths"]  # as it was recorded
    assert "src/repo_presenter/readme/composition" in failures.record_class_paths(record, item)
    scope_of, scope_at = _scopes((PLANNING,))  # BL-097's planning-bound fix
    assert failures.class_scope_changed(record, item, scope_of, scope_at) is True
    assert failures.known_failures(DOCS, scope_of, scope_at).get((PDF_PY, "R")) is None
    # negative control: without the run's tree (the pre-BL-110 reading) the recorded scope still holds it
    assert failures.known_failures(DOCS, scope_of).get((PDF_PY, "R")) is not None


# ------------------------------------------------------------------------------------------------- (c)


def test_the_authored_unit_scope_is_what_writes_an_authored_unit() -> None:
    record = _latest(PAGE_PY)
    (item,) = record["classes"].values()
    assert item["origin_kind"] == "authored_unit"
    paths = failures.record_class_paths(record, item)
    assert "src/repo_presenter/readme/composition" not in paths and AUTHORING in paths
    for unrelated in (RENDERER, PLANNING):
        scope_of, scope_at = _scopes((unrelated,))
        assert failures.class_scope_changed(record, item, scope_of, scope_at) is False, unrelated
    scope_of, scope_at = _scopes((AUTHORING,))
    assert failures.class_scope_changed(record, item, scope_of, scope_at) is True


# --------------------------------------------------------------------------------------------- (d)(e)


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


def _settle(record: dict[str, Any], lane: str) -> dict[str, Any]:
    return {"kind": "settle", "id": f"cohort-{record['run_id']}-1-1", "repository": record["repository"],
            "outcomes": {lane: "failure"}, "sealed": [], "code": record["code"],
            "source_revision": record["source_revision"], "at": record["at"], "run_url": RUNS + record["run_id"],
            "epoch": 2}


def _plan(fixed: tuple[str, ...], *, lane_l_certified: int = 29) -> dict[str, Any]:
    registry = [D3_NET, PAGE_PY, PDF_GO, PDF_PY, PDF_NET, PDF_CPP, PDF_TS, NEW_R, WORDS_NET]
    fillers = [f"own/filler-{i}" for i in range(lane_l_certified)]
    certs: dict[tuple[str, str], Any] = {(f, lane): Cert("RECERTIFIED", True) for f in fillers for lane in ("L",)}
    certs.update({(D3_NET, "R"): Cert("NEEDS_REPAIR", False, ("BC-18",)),
                  (WORDS_NET, "R"): Cert("NEEDS_REPAIR", False, ("BC-05",))})
    ledger = [_settle(d["latest"], d["lane"]) for d in DOCS]
    # 3D .NET and Words .NET: attempted before failure records existed (rank (c))
    for repo in (D3_NET, WORDS_NET):
        ledger.append({"kind": "settle", "id": f"old-{repo}", "repository": repo, "outcomes": {"R": "failure"},
                       "sealed": [], "code": "old", "source_revision": "s", "at": "2026-11-14T00:00:00Z",
                       "run_url": RUNS + "1", "epoch": 2})
    # Lane L of every registry repository needs work and was never attempted, except where a record says so
    entries = {repo: Entry(repo) for repo in [*registry, *fillers]}
    scope_of, scope_at = _scopes(fixed)
    heads = {d["repository"]: d["latest"]["source_revision"] for d in DOCS}
    return plan_cohort(
        entries=entries, authorized_repos=set(registry), certifications=certs, ledger={"entries": ledger},
        terminals=[], code="code-now", head=lambda r: heads.get(r, "s"), now=NOW,
        known=failures.known_failures(DOCS, scope_of, scope_at), scopes=failures.scope_status(DOCS, scope_of, scope_at),
    )


def _cells(plan: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [(run["repository"], lane, run["priority"][lane]) for run in plan["runs"] for lane in run["lanes"]]


A, C, B = (PRIORITY_LABELS[p] for p in (PRIORITY_FIX_LANDED, PRIORITY_NEEDS_REPAIR, PRIORITY_NEVER_ATTEMPTED))


OUTPUT_BOUNDS = "src/repo_presenter/readme/composition/output_bounds.py"
D = PRIORITY_LABELS[3]


def test_with_the_pdf_fixes_on_main_lane_r_fix_landed_cells_lead_then_repairs_then_first_attempts() -> None:
    # BL-097's planning bound and output bounds: composition modules outside the authored-unit scope
    plan = _plan((PLANNING, OUTPUT_BOUNDS))
    cells = _cells(plan)
    assert len(cells) == 6 and all(lane == "R" for _, lane, _ in cells)
    assert cells[:5] == [(PDF_GO, "R", A), (PDF_PY, "R", A), (PDF_NET, "R", A), (PDF_CPP, "R", A), (PDF_TS, "R", A)]
    assert cells[5] == (D3_NET, "R", C)
    queued = [(q["repository"], q["lane"], q["priority"]) for q in plan["queued"]]
    # (e) the (c) re-run before the never-attempted Lane R cell, every Lane L cell last (d)
    assert queued.index((WORDS_NET, "R", C)) < queued.index((NEW_R, "R", B))
    first_l = next(i for i, q in enumerate(queued) if q[1] == "L")
    assert all(q[1] == "L" for q in queued[first_l:])
    # (c) Page Python's authored-unit class: no authoring module moved, so it stays held (pre-BL-110 any
    # composition change released it as "fix landed")
    # (Page Python and PDF C++ Lane L stay held too: no correction or review code moved)
    assert {(k["repository"], k["lane"]) for k in plan["known_failure"]} == {
        (PAGE_PY, "R"), (PAGE_PY, "L"), (PDF_CPP, "L")}
    assert not any(q[0] == PAGE_PY and q[1] == "R" for q in queued)


def test_without_the_fixes_pdf_python_stays_held_and_the_rejections_rank_retry() -> None:
    plan = _plan(())
    assert (PDF_PY, "R") in {(k["repository"], k["lane"]) for k in plan["known_failure"]}
    ranks = {(run["repository"], lane): run["priority"][lane] for run in plan["runs"] for lane in run["lanes"]}
    ranks.update({(q["repository"], q["lane"]): q["priority"] for q in plan["queued"]})
    assert ranks[(PDF_GO, "R")] == D and ranks[(D3_NET, "R")] == C


def test_lane_ranks_follow_the_per_lane_target() -> None:
    assert lane_ranks({"R": 6, "L": 29}) == {"R": 0, "L": 1}
    assert lane_ranks({"R": 26, "L": 3}) == {"R": 1, "L": 0}
    assert lane_ranks({"R": 6, "L": 20}) == {"R": 0, "L": 0}
    assert lane_ranks({"R": 25, "L": 25}) == {"R": 0, "L": 0}


def test_below_the_target_on_both_lanes_a_lane_l_fix_landed_cell_still_competes() -> None:
    plan = _plan((AUTHORING, PLANNING, "src/repo_presenter/readme/correction/x.py"), lane_l_certified=10)
    cells = _cells(plan)
    # Page Python Lane L's correction classes changed: rank (a), ahead of 3D .NET's (c)
    assert (PAGE_PY, "L", A) in cells and (D3_NET, "R", C) not in cells
    assert sum(1 for _ in cells) == 6


def test_the_hosted_planner_has_the_history_the_scope_reading_needs() -> None:
    """``class_scope_changed`` hashes a class's current scope at its run's ``main_sha``: a one-commit
    checkout cannot read that tree (it would silently fall back to the recorded scope)."""
    import yaml

    present = yaml.safe_load((ROOT / ".github" / "workflows" / "present.yml").read_text(encoding="utf-8"))
    (checkout,) = [s for s in present["jobs"]["cohort"]["steps"] if str(s.get("uses", "")).startswith("actions/checkout")]
    assert checkout["with"]["fetch-depth"] == 0
