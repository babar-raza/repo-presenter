"""The scheduled cohort: which (repository, lane) cells the next autonomous fire runs, and why every
other cell is skipped (owner ruling R37, 2026-11-13: the execution loop runs itself on GitHub
Actions; R25: batches of six).

``plan_cohort`` is pure and is the whole policy. A cell needs work when its latest seal does not
certify under current code -- no seal at all, or a seal that re-certifies ``NEEDS_REPAIR``
(``repo_presenter.recertify``, zero provider calls) -- and it is skipped, with the reason recorded,
when it is:

* an inactive registry entry, or not named in ``data/scheduled_execution_policy.json``;
* terminal (``data/terminal_cells.json``: R24 ``BLOCKED_EXTERNAL``, R20 ``NOT_APPLICABLE``) at the
  upstream revision the decision was verified at -- a moved upstream lapses the terminal (R24);
* sealed and certified under current code;
* in flight (a hosted run holds an unsettled, unexpired budget reservation for it);
* idempotent: its last hosted attempt ran on the same code fingerprint
  (``core.llm.budget.code_fingerprint``) and the same upstream revision and did not seal it, so a
  re-run would repeat the same run on unchanged inputs;
* marked for diagnosis: it failed ``max_failures`` consecutive times on the current code (a
  changed upstream revision does not reset this; only a code change does). R36(b): the class is
  diagnosed and fixed once, locally, before another hosted run is spent on it.

Attempts are the ``settle`` entries of the durable provider-spend ledger
(``core.llm.budget.LEDGER_REF``), which every hosted ``present`` job writes on success or failure;
a run refused any budget is not an attempt. Cells are ordered NEEDS_REPAIR first (a seal one
repair away), then never-attempted, then retries after a code or upstream change; a repository
whose two lanes both need work runs as one ``both`` run (two cells).

Read-only as a CLI: it prints the plan (``--json``) without writing a ref, dispatching or calling
a provider. ``scripts/scheduled_execution_gate.py`` is the authorization boundary that calls it.

Usage:
    python scripts/select_scheduled_cohort.py [--max-cells 6] [--remote origin] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from repo_presenter.core.llm.budget import (  # noqa: E402
    RESERVATION_TTL_SECONDS,
    _now_utc,
    _parse_iso,
    ledger_entries,
)
from repo_presenter.core.portfolio_matrix import PIPELINE_GOOD_STATES  # noqa: E402
from repo_presenter.core.registry.models import RegistryEntry  # noqa: E402

LANES = ("R", "L")
TERMINAL_CELLS = REPO_ROOT / "data" / "terminal_cells.json"
#: R25: a batch is six repositories; a fire runs at most six cells.
MAX_CELLS = 6
#: Consecutive failures on unchanged code before a cell is set aside for diagnosis.
MAX_CONSECUTIVE_FAILURES = 3

PRIORITY_NEEDS_REPAIR = 0
PRIORITY_NEVER_ATTEMPTED = 1
PRIORITY_RETRY = 2


def select_eligible(
    entries: dict[str, RegistryEntry],
    rows: list[Any],
    *,
    authorized_repos: set[str] | None = None,
    max_n: int = 1,
) -> list[Any]:
    """The pre-R37 record-state picker (never-attempted first, both-lane pipeline-good excluded,
    inactive excluded), kept for callers that only hold transaction-record rows. The scheduled
    path uses :func:`plan_cohort`."""
    eligible = [
        row
        for row in rows
        if not (row.record_r in PIPELINE_GOOD_STATES and row.record_l in PIPELINE_GOOD_STATES)
        and entries[row.repository].active
        and (authorized_repos is None or row.repository in authorized_repos)
    ]
    eligible.sort(
        key=lambda row: (0 if row.record_r == "NO_RECORD" else 1)
        + (0 if row.record_l == "NO_RECORD" else 1)
    )
    return eligible[: max(0, max_n)]


def load_terminals(path: Path = TERMINAL_CELLS) -> list[dict[str, Any]]:
    """The recorded terminal cells; a missing or corrupt file is an error, never "no terminals"
    (that would silently spend runs on cells the owner closed)."""
    document = json.loads(path.read_text(encoding="utf-8"))
    cells = document.get("cells") if isinstance(document, dict) else None
    if not isinstance(cells, list):
        raise TypeError(f"{path}: 'cells' must be a list")
    return [cell for cell in cells if isinstance(cell, dict)]


def upstream_head(repository: str) -> str | None:
    """The upstream default branch's revision, or ``None`` when it cannot be read."""
    from repo_presenter.core.llm.budget import upstream_revision

    return upstream_revision(repository)


def attempts_by_cell(entries: Iterable[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Per cell, its hosted attempts oldest first: every ``settle`` whose lane outcome is a real
    attempt (success or failure) and that was granted a budget."""
    found: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in entries:
        if entry.get("kind") != "settle" or entry.get("budget_refused"):
            continue
        outcomes = entry.get("outcomes") or {}
        for lane in LANES:
            if outcomes.get(lane) not in ("success", "failure"):
                continue
            found.setdefault((str(entry.get("repository")), lane), []).append(
                {
                    "sealed": lane in (entry.get("sealed") or []),
                    "outcome": outcomes.get(lane),
                    "code": entry.get("code", ""),
                    "source_revision": entry.get("source_revision", ""),
                    "at": entry.get("at", ""),
                    "run_url": entry.get("run_url", ""),
                }
            )
    return found


def in_flight_cells(entries: Iterable[dict[str, Any]], now: datetime) -> dict[tuple[str, str], str]:
    """Cells a hosted run is still working on: an unsettled reservation younger than the TTL."""
    entries = list(entries)
    settled = {e.get("id") for e in entries if e.get("kind") == "settle"}
    flying: dict[tuple[str, str], str] = {}
    for entry in entries:
        if entry.get("kind") != "reserve" or entry.get("id") in settled:
            continue
        at = _parse_iso(entry.get("at"))
        if at is None or (now - at).total_seconds() >= RESERVATION_TTL_SECONDS:
            continue
        for lane in entry.get("lanes") or ():
            flying[(str(entry.get("repository")), str(lane))] = str(entry.get("id"))
    return flying


def consecutive_failures(attempts: list[dict[str, Any]], code: str) -> int:
    """Trailing unsealed attempts that all ran on ``code`` (a seal or older code ends the run)."""
    count = 0
    for attempt in reversed(attempts):
        if attempt["sealed"] or attempt["code"] != code:
            break
        count += 1
    return count


def _terminal_for(
    terminals: list[dict[str, Any]], repository: str, lane: str
) -> dict[str, Any] | None:
    for cell in terminals:
        if cell.get("repository") == repository and cell.get("lane") == lane:
            return cell
    return None


def plan_cohort(
    *,
    entries: Mapping[str, RegistryEntry],
    authorized_repos: set[str],
    certifications: Mapping[tuple[str, str], Any],
    ledger: Any,
    terminals: list[dict[str, Any]],
    code: str,
    head: Callable[[str], str | None] = upstream_head,
    now: datetime | None = None,
    max_cells: int = MAX_CELLS,
    max_failures: int = MAX_CONSECUTIVE_FAILURES,
    epoch: Any = None,
) -> dict[str, Any]:
    """The fire's plan (pure but for ``head``, which is only asked when a decision needs it):
    ``runs`` to dispatch, every ``skipped`` cell with its category and reason, the ``diagnose``
    list, the cells ``queued`` behind a full batch, and the certified count per lane (R11)."""
    now = now or _now_utc()
    all_entries = ledger_entries(ledger, any_epoch=True)
    attempts = attempts_by_cell(all_entries)
    flying = in_flight_cells(ledger_entries(ledger, epoch, any_epoch=epoch is None), now)
    heads: dict[str, str | None] = {}

    def head_of(repository: str) -> str | None:
        if repository not in heads:
            heads[repository] = head(repository)
        return heads[repository]

    certified = {lane: 0 for lane in LANES}
    skipped: list[dict[str, Any]] = []
    diagnose: list[dict[str, Any]] = []
    needs: dict[str, dict[str, tuple[int, str]]] = {}
    notes: list[str] = []

    def skip(repository: str, lane: str, category: str, reason: str) -> None:
        skipped.append({"repository": repository, "lane": lane, "category": category, "reason": reason})

    for repository, entry in entries.items():
        for lane in LANES:
            cert = certifications.get((repository, lane))
            if cert is not None and getattr(cert, "certified", False):
                certified[lane] += 1
            if not entry.active:
                skip(repository, lane, "inactive", "inactive registry entry")
                continue
            if repository not in authorized_repos:
                skip(repository, lane, "unauthorized", "not in authorized_repositories")
                continue
            terminal = _terminal_for(terminals, repository, lane)
            if terminal is not None:
                pinned = str(terminal.get("revision") or "")
                current = head_of(repository) if pinned else None
                if not pinned or current is None or current.startswith(pinned) or pinned.startswith(current):
                    overdue = str(terminal.get("recheck_by") or "") < now.date().isoformat()
                    skip(
                        repository, lane, "terminal",
                        f"{terminal.get('outcome')} ({terminal.get('ruling')}) at "
                        f"{pinned[:12] or 'any revision'}"
                        + ("; R24 re-check OVERDUE" if overdue and terminal.get("recheck_by") else ""),
                    )
                    continue
                notes.append(
                    f"{repository} Lane {lane}: terminal lapsed, upstream moved "
                    f"{pinned[:12]} -> {current[:12]}"
                )
            if cert is not None and getattr(cert, "certified", False):
                skip(repository, lane, "certified", "sealed and certified under current code")
                continue
            if (repository, lane) in flying:
                skip(repository, lane, "in_flight", f"in flight ({flying[(repository, lane)]})")
                continue
            history = attempts.get((repository, lane), [])
            failures = consecutive_failures(history, code)
            if failures >= max_failures:
                item = {
                    "repository": repository, "lane": lane, "consecutive_failures": failures,
                    "last_run": history[-1]["run_url"] if history else "",
                }
                diagnose.append(item)
                skip(
                    repository, lane, "diagnose",
                    f"failed {failures} consecutive times on the current code: diagnose and fix "
                    "the failure class locally before another hosted run (R36b)",
                )
                continue
            needs_repair = cert is not None and getattr(cert, "outcome", "") == "NEEDS_REPAIR"
            if history:
                last = history[-1]
                if last["code"] == code and code:
                    # An unreadable upstream head or an unrecorded revision reads as "unchanged":
                    # the cheaper error is one skipped fire, not a repeated hosted run.
                    current = head_of(repository)
                    recorded = str(last["source_revision"] or "")
                    if current is None or not recorded or current == recorded:
                        skip(
                            repository, lane, "idempotent",
                            f"last attempt ({last['outcome']}, {last['at']}) ran this code on "
                            f"upstream {str(last['source_revision'])[:12] or 'unknown'} and did "
                            "not seal; nothing has changed since",
                        )
                        continue
                    reason = "upstream moved since the last attempt"
                else:
                    reason = "code changed since the last attempt"
                priority = PRIORITY_NEEDS_REPAIR if needs_repair else PRIORITY_RETRY
            elif needs_repair:
                priority, reason = PRIORITY_NEEDS_REPAIR, ""
            else:
                priority, reason = PRIORITY_NEVER_ATTEMPTED, "no seal, never attempted by the hosted loop"
            if needs_repair:
                checks = ", ".join(getattr(cert, "failing_checks", ()) or ()) or "?"
                reason = f"latest seal NEEDS_REPAIR ({checks})" + (f"; {reason}" if reason else "")
            elif cert is None and reason != "no seal, never attempted by the hosted loop":
                reason = f"no seal; {reason}"
            needs.setdefault(repository, {})[lane] = (priority, reason)

    order = {repository: index for index, repository in enumerate(entries)}
    ranked = sorted(needs, key=lambda repo: (min(p for p, _ in needs[repo].values()), order[repo]))
    runs: list[dict[str, Any]] = []
    queued: list[dict[str, Any]] = []
    room = max(0, max_cells)
    for repository in ranked:
        lanes = sorted(needs[repository], key=lambda lane: (needs[repository][lane][0], LANES.index(lane)))
        take = lanes[: min(len(lanes), room)]
        for lane in lanes[len(take):]:
            queued.append({"repository": repository, "lane": lane, "reason": needs[repository][lane][1]})
        if not take:
            continue
        room -= len(take)
        take = sorted(take, key=LANES.index)
        runs.append(
            {
                "repository": repository,
                "ecosystem": entries[repository].ecosystem,
                "lanes": take,
                "lane": "both" if len(take) == 2 else take[0],
                "reasons": {lane: needs[repository][lane][1] for lane in take},
            }
        )
    return {
        "runs": runs,
        "skipped": skipped,
        "diagnose": diagnose,
        "queued": queued,
        "certified": certified,
        "notes": notes,
        "code": code,
        "planned_at": now.isoformat(timespec="seconds"),
    }


def render_summary(plan: dict[str, Any], budget_lines: list[str] | None = None,
                   dispatched: list[dict[str, Any]] | None = None,
                   recent: list[dict[str, Any]] | None = None) -> str:
    """The fire's job summary, results first (R11): certified counts per lane, then what ran and
    what was skipped, and why."""
    certified = plan.get("certified") or {}
    lines = [
        "## Scheduled fire",
        "",
        (
            f"**Certified under current code: Lane R {certified.get('R', 0)}, "
            f"Lane L {certified.get('L', 0)}** (goal: 25 each)"
        ),
        "",
    ]
    if plan.get("blocked"):
        lines += [f"**Not authorized:** {plan['blocked']}", ""]
    if budget_lines:
        lines += ["### Budget", "", *[f"- {line}" for line in budget_lines], ""]
    if recent:
        lines += ["### Settled since the previous fire", "", "| repository | outcomes | sealed | calls | run |", "|---|---|---|---|---|"]
        for item in recent:
            lines.append(
                f"| {item.get('repository')} | {item.get('outcomes')} | "
                f"{', '.join(item.get('sealed') or []) or '-'} | {item.get('calls', 0):g} | "
                f"{item.get('run_url') or item.get('run_id') or '-'} |"
            )
        lines.append("")
    runs = dispatched if dispatched is not None else plan.get("runs") or []
    lines += [f"### Ran ({len(runs)})", ""]
    if runs:
        lines += ["| repository | lane | why | budget |", "|---|---|---|---|"]
        for run in runs:
            why = "; ".join(f"{lane}: {text}" for lane, text in (run.get("reasons") or {}).items())
            granted = run.get("reservation") or {}
            budget = (f"{granted.get('calls', 0):g} calls" if granted else run.get("refusal", "-"))
            lines.append(f"| {run['repository']} | {run['lane']} | {why} | {budget} |")
    else:
        lines.append("nothing")
    lines.append("")
    for title, key in (("Needs diagnosis (R36b)", "diagnose"), ("Queued behind the batch of six", "queued")):
        items = plan.get(key) or []
        if items:
            lines += [f"### {title} ({len(items)})", ""]
            lines += [f"- {i['repository']} Lane {i['lane']}: {i.get('reason') or i.get('consecutive_failures')}" for i in items]
            lines.append("")
    skipped = plan.get("skipped") or []
    if skipped:
        lines += [f"### Skipped ({len(skipped)})", "", "| repository | lane | category | reason |", "|---|---|---|---|"]
        for item in skipped:
            lines.append(f"| {item['repository']} | {item['lane']} | {item['category']} | {item['reason']} |")
        lines.append("")
    for note in plan.get("notes") or []:
        lines.append(f"- note: {note}")
    return "\n".join(lines) + "\n"


def build_plan(
    *, registry: Path, remote: str, authorized_repos: set[str] | None, prompts: Path,
    token: str | None = None, max_cells: int = MAX_CELLS,
) -> dict[str, Any]:
    """Gather the plan's inputs from the real sources (zero provider calls) and plan the fire."""
    from repo_presenter.core.llm.budget import code_fingerprint, read_ledger
    from repo_presenter.core.registry.loader import load_registry
    from repo_presenter.recertify import portfolio_recertification

    entries = {e.repository: e for e in load_registry(registry).entries}
    results, _ = portfolio_recertification(
        remote=remote, token=token, registry=registry, prompts_dir=prompts
    )
    certifications = {(r.repository, r.lane): r for r in results}
    ledger = read_ledger(remote, token)
    epoch = None
    try:
        epoch = json.loads((REPO_ROOT / "data" / "provider_budget.json").read_text("utf-8")).get("epoch")
    except (OSError, ValueError):
        pass
    return plan_cohort(
        entries=entries,
        authorized_repos=set(entries) if authorized_repos is None else authorized_repos,
        certifications=certifications,
        ledger=ledger,
        terminals=load_terminals(),
        code=code_fingerprint(REPO_ROOT),
        max_cells=max_cells,
        epoch=epoch,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-cells", type=int, default=MAX_CELLS)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    parser.add_argument("--prompts", type=Path, default=REPO_ROOT / "prompts")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    plan = build_plan(
        registry=args.registry, remote=args.remote, authorized_repos=None, prompts=args.prompts,
        max_cells=args.max_cells,
    )
    print(json.dumps(plan, indent=1) if args.json else render_summary(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
