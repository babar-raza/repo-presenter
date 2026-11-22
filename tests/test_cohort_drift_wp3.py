"""WP-3 (R50, BL-187/BL-190): a verified upstream change outranks "recertified, skip" in the
scheduled cohort. Relevant / irrelevant / unreadable controls against ``plan_cohort``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_scheduled_cohort_selection import (
    CODE,
    HEAD,
    NOW,
    _entries,
    _settle,
)

from repo_presenter.monitor.run import drifted_cells, report_document
from scripts.select_scheduled_cohort import (
    PRIORITY_DRIFTED,
    PRIORITY_LABELS,
    plan_cohort,
)

SEALED = "a" * 40


@dataclass
class Cert:
    outcome: str = "RECERTIFIED"
    certified: bool = True
    failing_checks: tuple[str, ...] = ()
    revision: str = SEALED


def _plan(entries, certs, drift, ledger=()):
    return plan_cohort(
        entries=entries, authorized_repos=set(entries), certifications=certs,
        ledger={"entries": list(ledger)}, terminals=[], code=CODE, head=lambda r: HEAD, now=NOW,
        drift=drift,
    )


def _cell(klass: str, repo: str = "o/a", lane: str = "R", detail: str = "LICENSE changed") -> dict:
    return {"repository": repo, "lane": lane, "class": klass, "status": "DRIFTED" if klass == "relevant" else "CURRENT",
            "bundle_revision": SEALED, "head_revision": HEAD, "detail": detail, "freshness_due": False, "sealed_at": None}


def _drift(*cells):
    return drifted_cells(report_document(list(cells), observed_at="2026-11-22T00:00:00+00:00"))


def _certs(lane="R"):
    return {("o/a", "R"): Cert(), ("o/a", "L"): Cert()}


def test_a_relevant_drift_outranks_certified_skip_and_ranks_first() -> None:
    plan = _plan(_entries("o/a", "o/b"), {**_certs(), ("o/b", "R"): Cert(), ("o/b", "L"): Cert()},
                 _drift(_cell("relevant", "o/b", "L")))
    assert [(r["repository"], r["lane"]) for r in plan["runs"]] == [("o/b", "L")]
    run = plan["runs"][0]
    assert "verified upstream drift" in run["reasons"]["L"] and "LICENSE changed" in run["reasons"]["L"]
    assert run["priority"]["L"] == PRIORITY_LABELS[PRIORITY_DRIFTED]
    skipped = {(s["repository"], s["lane"]): s["category"] for s in plan["skipped"]}
    assert skipped[("o/b", "R")] == "certified" and skipped[("o/a", "R")] == "certified"
    assert plan["certified"] == {"R": 2, "L": 2}  # the seal still counts; drift only schedules


def test_an_irrelevant_change_and_an_unreadable_report_keep_the_certified_skip() -> None:
    certs = _certs()
    assert _plan(_entries("o/a"), certs, _drift(_cell("irrelevant")))["runs"] == []
    assert _plan(_entries("o/a"), certs, _drift(_cell("unreadable")))["runs"] == []
    assert _plan(_entries("o/a"), certs, {})["runs"] == []
    assert _plan(_entries("o/a"), certs, None)["runs"] == []


def test_a_drift_row_about_an_older_seal_is_ignored() -> None:
    row = _cell("relevant")
    row["bundle_revision"] = "9" * 40  # the cell was resealed since the monitor observed it
    assert _plan(_entries("o/a"), _certs(), _drift(row))["runs"] == []


def test_drift_does_not_repeat_a_run_that_already_ran_on_this_code_and_head() -> None:
    plan = _plan(_entries("o/a"), _certs(), _drift(_cell("relevant")),
                 ledger=[_settle("o/a", "R", sealed=False, revision=HEAD)])
    assert [r["lane"] for r in plan["runs"]] == []
    assert any(s["category"] == "idempotent" for s in plan["skipped"] if s["lane"] == "R")


def test_drift_ranks_ahead_of_a_never_attempted_cell() -> None:
    plan = _plan(_entries("o/a", "o/c"), {("o/a", "R"): Cert(), ("o/a", "L"): Cert()},
                 _drift(_cell("relevant", "o/a", "R")))
    assert plan["runs"][0]["repository"] == "o/a"
