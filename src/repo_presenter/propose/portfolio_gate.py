"""Owner ruling R15: no upstream push or pull request before every candidate of BOTH lanes is
sealed, validated and passed -- as amended by R16, R20, R24 and R33.

Enforced at the one write authority (R22): ``repo_presenter.github.client.authorize_write`` calls
:func:`require_portfolio_complete` for every upstream ``pull_request`` effect (branch ref, contents
write, pull-request create/update), before any request is made. Issues (R39 pilot) are a separate
effect and are never gated here; the control repository is never gated.

The portfolio predicate holds when EVERY active ``data/registry.json`` repository has, in Lane R
AND in Lane L, one terminal outcome:

* ``ACCEPTED`` -- its latest seal re-certifies under current code (``recertify``) and holds an
  attested M9 acceptance record at that revision (R33), exactly as
  ``ops/checks/portfolio_delivery_count.py`` counts ``independently_accepted``;
* ``NO_ACTION_JUSTIFIED`` (Lane L only, R16) -- the certified seal equals the live README;
* ``BLOCKED_EXTERNAL`` (R24) in ``data/terminal_cells.json`` with a FRESH re-check (the last
  verification at most :data:`R24_RECHECK_DAYS` days ago and ``recheck_by`` not passed) and the
  upstream still at the pinned revision; a stale check or a moved upstream is not terminal;
* ``NOT_APPLICABLE`` (R20) in ``data/terminal_cells.json``, upstream still at the pinned revision.

Computed every time from the state remote's seal history, the attested record branches and the
committed terminal list -- never from an editable "ready" marker, never cached. Any failure to read
any of it makes the portfolio INCOMPLETE (fail closed).
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
LANES = ("R", "L")
TERMINAL_CELLS = REPO_ROOT / "data" / "terminal_cells.json"
REGISTRY = REPO_ROOT / "data" / "registry.json"
DELIVERY_COUNT = REPO_ROOT / "ops" / "checks" / "portfolio_delivery_count.py"
#: R24: a terminal external blocker is re-checked every 7 days; an older check is not terminal.
R24_RECHECK_DAYS = 7

ACCEPTED = "ACCEPTED"
NO_ACTION_JUSTIFIED = "NO_ACTION_JUSTIFIED"
BLOCKED_EXTERNAL = "BLOCKED_EXTERNAL"
NOT_APPLICABLE = "NOT_APPLICABLE"

#: Upstream default-branch revision for a repository, or ``None`` when unreadable.
HeadFn = Callable[[str], "str | None"]


@dataclass(frozen=True)
class PortfolioReadiness:
    ready: bool
    active: int
    #: (repository, lane) -> the terminal outcome that closes it
    terminal: Mapping[tuple[str, str], str] = field(default_factory=dict)
    #: (repository, lane, why) for every cell without a terminal outcome
    missing: tuple[tuple[str, str, str], ...] = ()
    #: a reading failure: the predicate could not be computed at all (always not ready)
    error: str = ""

    def reason(self, limit: int = 8) -> str:
        if self.error:
            return f"owner ruling R15: portfolio readiness could not be computed ({self.error}); fail closed"
        if self.ready:
            return f"all {self.active} active repositories have a terminal outcome in both lanes"
        shown = "; ".join(f"{repo} lane {lane}: {why}" for repo, lane, why in self.missing[:limit])
        more = f" (and {len(self.missing) - limit} more)" if len(self.missing) > limit else ""
        return (
            "owner ruling R15 PORTFOLIO_INCOMPLETE: no upstream push or pull request before every "
            f"candidate of both lanes has a terminal outcome; {len(self.missing)} of "
            f"{2 * self.active} (repository, lane) cells do not: {shown}{more}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "active": self.active,
            "cells": 2 * self.active,
            "terminal": len(self.terminal),
            "terminal_by_outcome": _count(self.terminal.values()),
            "missing": [{"repository": r, "lane": lane, "why": why} for r, lane, why in self.missing],
            "error": self.error,
        }


def _count(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def load_terminal_cells(path: Path = TERMINAL_CELLS) -> list[dict[str, Any]]:
    """The committed terminal list; missing or malformed raises (never read as "no terminals")."""
    document = json.loads(path.read_text(encoding="utf-8"))
    cells = document.get("cells") if isinstance(document, dict) else None
    if not isinstance(cells, list):
        raise TypeError(f"{path}: 'cells' must be a list")
    return [cell for cell in cells if isinstance(cell, dict)]


def _iso(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def recorded_terminal(
    cell: Mapping[str, Any], today: date, head_of: HeadFn
) -> tuple[str | None, str]:
    """``(outcome, why)`` for one ``terminal_cells.json`` entry: ``outcome`` is ``None`` when it does
    not count as terminal today (R24 stale, upstream moved or unreadable, unknown outcome)."""
    outcome = str(cell.get("outcome") or "")
    if outcome not in {BLOCKED_EXTERNAL, NOT_APPLICABLE}:
        return None, f"terminal_cells.json outcome {outcome!r} is not a recognised terminal"
    if outcome == BLOCKED_EXTERNAL:
        checked = max(
            (d for d in (_iso(cell.get("decided")), _iso(cell.get("rechecked"))) if d), default=None
        )
        recheck_by = _iso(cell.get("recheck_by"))
        if checked is None or recheck_by is None:
            return None, "R24 terminal without a dated check/recheck_by: not terminal"
        if today - checked > timedelta(days=R24_RECHECK_DAYS) or today > recheck_by:
            return None, (
                f"R24 re-check stale (last checked {checked.isoformat()}, recheck_by "
                f"{recheck_by.isoformat()}): not terminal until re-verified"
            )
    pinned = str(cell.get("revision") or "")
    if pinned:
        head = head_of(str(cell.get("repository")))
        if head is None:
            return None, f"{outcome} pinned at {pinned[:12]}, upstream head unreadable: fail closed"
        if not (head.startswith(pinned) or pinned.startswith(head)):
            return None, f"{outcome} lapsed: upstream moved {pinned[:12]} -> {head[:12]}"
    return outcome, f"{outcome} ({cell.get('ruling')})"


def _outcome_terminal(outcome: Any) -> tuple[str | None, str]:
    """From one ``portfolio_delivery_count.LaneOutcome`` (current version set)."""
    if outcome is None:
        return None, "no durable seal"
    certified = getattr(outcome, "certification", "") == "RECERTIFIED" or (
        getattr(outcome, "sealed_by_current", False) and not getattr(outcome, "failing_checks", [])
    )
    if certified and getattr(outcome, "independently_accepted", False):
        return ACCEPTED, "re-certified and attested independently accepted (R33)"
    if certified and outcome.lane == "L" and getattr(outcome, "bucket", "") == "no_action_justified":
        return NO_ACTION_JUSTIFIED, "R16 NO_ACTION_JUSTIFIED"
    if getattr(outcome, "certification", "") == "NEEDS_REPAIR":
        checks = ", ".join(getattr(outcome, "failing_checks", []) or []) or "unreadable"
        return None, f"latest seal NEEDS_REPAIR ({checks})"
    if not getattr(outcome, "pipeline_good", False):
        return None, "no certified seal" + (f" ({outcome.reason})" if getattr(outcome, "reason", "") else "")
    return None, f"sealed and re-certified, not accepted: {getattr(outcome, 'reason', '') or 'no attested M9 record'}"


def evaluate(
    active: Iterable[str],
    outcomes: Iterable[Any],
    terminals: Iterable[Mapping[str, Any]],
    *,
    today: date,
    head_of: HeadFn,
) -> PortfolioReadiness:
    """Pure apart from ``head_of``. ``outcomes`` are ``LaneOutcome``-shaped objects (only the
    CURRENT version set's are used); ``terminals`` are ``terminal_cells.json`` entries."""
    repos = sorted(set(active))
    current = {(o.repository, o.lane): o for o in outcomes if getattr(o, "current", True)}
    recorded = {(str(c.get("repository")), str(c.get("lane"))): c for c in terminals}
    closed: dict[tuple[str, str], str] = {}
    missing: list[tuple[str, str, str]] = []
    for repo in repos:
        for lane in LANES:
            outcome, why = _outcome_terminal(current.get((repo, lane)))
            if outcome is None and (repo, lane) in recorded:
                outcome, recorded_why = recorded_terminal(recorded[(repo, lane)], today, head_of)
                why = recorded_why if outcome is not None else f"{why}; {recorded_why}"
            if outcome is None:
                missing.append((repo, lane, why))
            else:
                closed[(repo, lane)] = outcome
    return PortfolioReadiness(
        ready=bool(repos) and not missing, active=len(repos), terminal=closed, missing=tuple(missing)
    )


def _delivery_count() -> Any:
    """``ops/checks/portfolio_delivery_count.py`` as a module: the one counter of accepted and
    R16 outcomes (re-certification + attested records), reused rather than duplicated."""
    spec = importlib.util.spec_from_file_location("_r15_portfolio_delivery_count", DELIVERY_COUNT)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {DELIVERY_COUNT}")
    import sys

    name = spec.name
    if name in sys.modules:
        return sys.modules[name]
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve their module through sys.modules
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def portfolio_readiness(
    *,
    remote: str = "origin",
    registry: Path = REGISTRY,
    terminal_cells: Path = TERMINAL_CELLS,
    head_of: HeadFn | None = None,
    collect: Callable[[], Any] | None = None,
    now: Callable[[], datetime] | None = None,
) -> PortfolioReadiness:
    """Read-only, zero provider calls. Any reading failure is an incomplete portfolio."""
    try:
        from repo_presenter.core.llm.budget import upstream_revision
        from repo_presenter.core.registry.loader import load_registry

        active = [e.repository for e in load_registry(registry).entries if e.active]
        terminals = load_terminal_cells(terminal_cells)
        outcomes, _, _ = (collect or (lambda: _delivery_count().collect(remote=remote)))()
        today = (now or (lambda: datetime.now(UTC)))().date()
        return evaluate(active, outcomes, terminals, today=today, head_of=head_of or upstream_revision)
    except Exception as exc:  # noqa: BLE001 -- fail closed on every reading failure
        return PortfolioReadiness(ready=False, active=0, error=f"{type(exc).__name__}: {exc}")


ReadinessFn = Callable[[], PortfolioReadiness]


def main(argv: list[str] | None = None) -> int:
    """``python -m repo_presenter.propose.portfolio_gate [--json]``: report the predicate; exit 0
    only when every cell is terminal."""
    import sys

    args = sys.argv[1:] if argv is None else argv
    readiness = portfolio_readiness()
    if "--json" in args:
        print(json.dumps(readiness.as_dict(), indent=2))
    else:
        print(readiness.reason(limit=len(readiness.missing) or 1))
    return 0 if readiness.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
