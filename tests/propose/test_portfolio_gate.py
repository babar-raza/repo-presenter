"""Owner ruling R15 (with R16, R20, R24, R33, R39): the portfolio gate at the one write authority.

``github.client.authorize_write`` refuses every upstream ``pull_request`` effect (branch ref,
contents write, pull-request create/update) unless every active registry repository has a terminal
outcome in BOTH lanes. Issues on the R39 pilot and the control repository are never gated.
No network: the predicate runs over injected outcomes, terminals and upstream heads."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repo_presenter.github import client
from repo_presenter.github.client import (
    API_ROOT,
    CONTROL_REPOSITORY,
    PortfolioIncompleteError,
    authorize_request,
    authorize_write,
)
from repo_presenter.propose import portfolio_gate
from repo_presenter.propose.portfolio_gate import (
    ACCEPTED,
    BLOCKED_EXTERNAL,
    NO_ACTION_JUSTIFIED,
    NOT_APPLICABLE,
    PortfolioReadiness,
    evaluate,
    portfolio_readiness,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TODAY = date(2026, 11, 13)
PIN = "a" * 40
ALLOWLISTED = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"
PILOT = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"


def outcome(repo: str, lane: str, **kw: Any) -> SimpleNamespace:
    """A ``portfolio_delivery_count.LaneOutcome``-shaped row; default: re-certified + attested."""
    row = {
        "repository": repo, "lane": lane, "current": True, "certification": "RECERTIFIED",
        "sealed_by_current": False, "failing_checks": [], "pipeline_good": True,
        "independently_accepted": True, "bucket": "independently_accepted", "reason": "",
    }
    row.update(kw)
    return SimpleNamespace(**row)


def not_accepted(repo: str, lane: str) -> SimpleNamespace:
    return outcome(repo, lane, independently_accepted=False, bucket="pipeline_good_uncalibrated",
                   reason="R33: no attested M9 acceptance record at this revision")


def r24(repo: str, lane: str = "R", decided: str = "2026-11-13", recheck_by: str = "2026-11-20",
        **kw: Any) -> dict[str, Any]:
    cell = {"repository": repo, "lane": lane, "outcome": BLOCKED_EXTERNAL, "ruling": "R24",
            "revision": PIN, "decided": decided, "recheck_by": recheck_by}
    cell.update(kw)
    return cell


def still_pinned(_: str) -> str:
    return PIN


def test_a_fully_terminal_synthetic_portfolio_is_ready() -> None:
    outcomes = [
        outcome("o/a", "R"), outcome("o/a", "L"),
        outcome("o/b", "L", independently_accepted=False, bucket="no_action_justified"),
        outcome("o/c", "R"),
    ]
    terminals = [
        r24("o/b", "R"),
        {"repository": "o/c", "lane": "L", "outcome": NOT_APPLICABLE, "ruling": "R20", "revision": PIN},
    ]
    readiness = evaluate(["o/a", "o/b", "o/c"], outcomes, terminals, today=TODAY, head_of=still_pinned)
    assert readiness.ready, readiness.reason()
    assert dict(readiness.terminal) == {
        ("o/a", "R"): ACCEPTED, ("o/a", "L"): ACCEPTED, ("o/b", "R"): BLOCKED_EXTERNAL,
        ("o/b", "L"): NO_ACTION_JUSTIFIED, ("o/c", "R"): ACCEPTED, ("o/c", "L"): NOT_APPLICABLE,
    }


@pytest.mark.parametrize(
    ("decided", "recheck_by"),
    [("2026-11-05", "2026-11-12"),   # checked 8 days ago, recheck_by passed
     ("2026-11-05", "2026-11-30"),   # recheck_by not passed but last check older than 7 days
     ("2026-11-13", "2026-11-12")],  # recheck_by already passed
)
def test_a_stale_r24_recheck_is_not_terminal(decided: str, recheck_by: str) -> None:
    readiness = evaluate(["o/a"], [outcome("o/a", "L")], [r24("o/a", decided=decided, recheck_by=recheck_by)],
                         today=TODAY, head_of=still_pinned)
    assert not readiness.ready
    assert [(r, lane) for r, lane, _ in readiness.missing] == [("o/a", "R")]
    assert "R24 re-check stale" in readiness.missing[0][2]


def test_a_recent_recheck_refreshes_an_old_r24_decision() -> None:
    cell = r24("o/a", decided="2026-10-01", recheck_by="2026-11-19", rechecked="2026-11-12")
    assert evaluate(["o/a"], [outcome("o/a", "L")], [cell], today=TODAY, head_of=still_pinned).ready


@pytest.mark.parametrize("head", ["b" * 40, None])
def test_a_moved_or_unreadable_upstream_lapses_a_terminal(head: str | None) -> None:
    readiness = evaluate(["o/a"], [outcome("o/a", "L")], [r24("o/a")], today=TODAY, head_of=lambda _: head)
    assert not readiness.ready
    assert "upstream" in readiness.missing[0][2]


def test_sealed_but_unattested_needs_repair_and_unsealed_cells_block_with_reasons() -> None:
    outcomes = [
        not_accepted("o/a", "R"),
        outcome("o/a", "L", certification="NEEDS_REPAIR", failing_checks=["BC-14"],
                pipeline_good=False, independently_accepted=False, bucket=""),
        # R16 is Lane L only: a Lane R "no action" bucket is not terminal
        outcome("o/b", "R", independently_accepted=False, bucket="no_action_justified"),
    ]
    readiness = evaluate(["o/a", "o/b"], outcomes, [], today=TODAY, head_of=still_pinned)
    why = {(r, lane): w for r, lane, w in readiness.missing}
    assert not readiness.ready and len(why) == 4
    assert "R33" in why[("o/a", "R")]
    assert "NEEDS_REPAIR (BC-14)" in why[("o/a", "L")]
    assert why[("o/b", "L")] == "no durable seal"
    assert "PORTFOLIO_INCOMPLETE" in readiness.reason() and "4 of 4" in readiness.reason()


def test_an_older_version_set_row_never_counts() -> None:
    rows = [outcome("o/a", "R", current=False), outcome("o/a", "L")]
    assert not evaluate(["o/a"], rows, [], today=TODAY, head_of=still_pinned).ready


def test_today_the_committed_portfolio_is_blocked() -> None:
    """The committed registry and terminal list, with today's acceptance fact: no attested M9
    acceptance record exists for any cell yet (BL-001: independently_accepted 0 / 0), so every
    sealed cell is 'not accepted' and only the recorded terminals close cells."""
    from repo_presenter.core.registry.loader import load_registry

    active = [e.repository for e in load_registry(portfolio_gate.REGISTRY).entries if e.active]
    rows = [not_accepted(r, lane) for r in active for lane in ("R", "L")]
    terminals = portfolio_gate.load_terminal_cells()
    pinned = {c["repository"]: c["revision"] for c in terminals}
    readiness = portfolio_readiness(
        collect=lambda: (rows, None, None),
        head_of=lambda repo: pinned.get(repo),
        now=lambda: datetime(2026, 11, 13, tzinfo=UTC),
    )
    assert not readiness.ready
    assert readiness.active == len(active) >= 40
    assert len(readiness.missing) == 2 * len(active) - len(terminals)
    assert set(readiness.terminal.values()) <= {BLOCKED_EXTERNAL, NOT_APPLICABLE}


def test_any_reading_failure_is_incomplete() -> None:
    def broken() -> Any:
        raise OSError("state remote unreachable")

    readiness = portfolio_readiness(collect=broken)
    assert not readiness.ready and "OSError" in readiness.error
    assert "fail closed" in readiness.reason()
    assert not portfolio_readiness(terminal_cells=Path("/nonexistent/terminal_cells.json"),
                                   collect=lambda: ([], None, None)).ready


# --- the choke point -----------------------------------------------------------------------------

BLOCKED = PortfolioReadiness(ready=False, active=1, missing=(("o/a", "R", "no durable seal"),))


@pytest.fixture
def no_http(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    seen: list[Any] = []
    for verb in ("post", "patch", "put"):
        monkeypatch.setattr(client.httpx, verb, lambda url, **kw: seen.append(url))
    return seen


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [("POST", "git/refs", {"ref": "refs/heads/repository-presenter/readme-update", "sha": PIN}),
     ("PUT", "contents/README.md", {"branch": "repository-presenter/readme-update", "content": ""}),
     ("POST", "pulls", {"head": "repository-presenter/readme-update", "base": "main", "draft": True}),
     ("PATCH", "pulls/7", {"title": "t"})],
)
def test_every_upstream_pr_and_branch_push_request_is_refused_while_incomplete(
    monkeypatch: pytest.MonkeyPatch, no_http: list[Any], method: str, path: str, payload: dict[str, Any]
) -> None:
    monkeypatch.setattr(client, "portfolio_readiness", lambda: BLOCKED)
    url = f"{API_ROOT}/repos/{ALLOWLISTED}/{path}"
    with pytest.raises(PortfolioIncompleteError, match="R15 PORTFOLIO_INCOMPLETE"):
        authorize_request(method, url, payload)
    writer = {"POST": client.default_post, "PUT": client.default_put, "PATCH": client.default_patch}[method]
    with pytest.raises(PortfolioIncompleteError):
        writer(url, "token", payload)
    assert no_http == []


@pytest.mark.parametrize("failure", ["raises", "not-a-readiness"])
def test_an_unreadable_predicate_refuses(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    def reader() -> Any:
        if failure == "raises":
            raise RuntimeError("boom")
        return object()

    monkeypatch.setattr(client, "portfolio_readiness", reader)
    with pytest.raises(PortfolioIncompleteError):
        authorize_write(ALLOWLISTED, "pull_request")


def test_a_complete_portfolio_grants_the_draft_pull_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client, "portfolio_readiness",
                        lambda: PortfolioReadiness(ready=True, active=1, terminal={("o/a", "R"): ACCEPTED}))
    grant = authorize_write(ALLOWLISTED, "pull_request")
    assert grant.upstream and grant.draft_required


def test_issues_and_the_control_repository_never_consult_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    def must_not_run() -> Any:
        raise AssertionError("the R15 gate is for upstream pull requests only")

    monkeypatch.setattr(client, "portfolio_readiness", must_not_run)
    pilot = json.loads((REPO_ROOT / "data" / "issue_pilot.json").read_text("utf-8"))
    assert PILOT in [r["repository"] for r in pilot["repositories"]]
    for effect in ("issue", "issue_comment"):
        assert authorize_write(PILOT, effect).issue_pilot is True  # R39: out of R15's scope
    for effect in ("pull_request", "issue", "internal"):
        assert authorize_write(CONTROL_REPOSITORY, effect).upstream is False
