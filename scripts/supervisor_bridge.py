"""The supervisor execution bridge (BL-770, WP-7; R8, R37, the Final Directive, plan 8.4).

Until now the hourly supervisor-tick only observed (BL-027: "the execution bridge was never built"). This is
the smallest bridge that makes the tick drive the loop, and nothing more: it reads what the planner
(``scripts/select_scheduled_cohort.py``, zero provider calls) says is due and what the durable provider-spend
ledger says is in flight, and decides whether the tick may dispatch the next cohort. It dispatches nothing
itself: ``supervisor-tick.yml``'s ``bridge-dispatch`` job calls ``present.yml``'s own cohort job (the engine,
R37), which re-runs the authorization gate (``scripts/scheduled_execution_gate.py``), reserves budget and
dispatches the runs. The bridge is therefore double gated and adds no spend path of its own.

Lease semantic (plan 8.4, mapped onto the durable state that already exists): a *lease* is an unsettled,
unexpired ``reserve`` entry on the provider-spend ledger (``core.llm.budget``; TTL
``RESERVATION_TTL_SECONDS``). While any lease is live nothing is in flight to replace, so the bridge holds. A
lease whose TTL passed without a ``settle`` is *expired*: the cell is eligible again (the planner already
treats it so), the bridge reports it as recovered. READY work (the planner has runs) with no live lease for
longer than ``STALL_MINUTES`` is a *stall*: the report says so and the tick diagnoses it (plan 8.4 "stall
response") instead of waiting. Budgets measure, never block (R45): a budget notice is reported, never a hold.

Gating. ``action`` is ``dispatch`` only when ALL hold: ``data/scheduled_execution_policy.json`` has
``scheduled_execution_authorized`` true (read here, independently of the gate), the planner has at least one
run, no cohort lease is live, and the mode is not ``--dry-run``. Everything else is ``none`` with the reason.
``next_run_request`` is the exact ``run-request.json`` content (``scripts/run_request.py``) that would start
the first planned run on the hosted runner; a supervisor pushing it as ``run-requests/<id>`` proves the same
run hosted. The decision is data on stdout, a JSON file and ``key=value`` lines for ``$GITHUB_OUTPUT``.

Usage: python scripts/supervisor_bridge.py [--remote URL] [--out decision.json] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

POLICY = REPO_ROOT / "data" / "scheduled_execution_policy.json"
#: plan 8.4: READY work with no live lease past this is a stall that pre-empts the queue.
STALL_MINUTES = 60


def policy_authorized(path: Path = POLICY) -> bool:
    """Only the JSON boolean ``true``; a missing, corrupt or non-object file is not authorized."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("scheduled_execution_authorized") is True


def lease_view(entries: Iterable[dict[str, Any]], now: datetime) -> dict[str, Any]:
    """Live and expired leases from the ledger's entries (pure). ``last_activity`` is the newest reserve or
    settle timestamp, the stall clock's start."""
    from repo_presenter.core.llm.budget import RESERVATION_TTL_SECONDS, _parse_iso

    entries = [e for e in entries if isinstance(e, dict)]
    settled = {e.get("id") for e in entries if e.get("kind") == "settle"}
    live: list[dict[str, Any]] = []
    expired: list[dict[str, Any]] = []
    last: datetime | None = None
    for entry in entries:
        at = _parse_iso(entry.get("at"))
        if entry.get("kind") in ("reserve", "settle") and at is not None and (last is None or at > last):
            last = at
        if entry.get("kind") != "reserve" or entry.get("id") in settled or at is None:
            continue
        age = (now - at).total_seconds()
        row = {
            "id": str(entry.get("id")),
            "repository": str(entry.get("repository")),
            "lanes": [str(x) for x in entry.get("lanes") or ()],
            "age_minutes": int(age // 60),
            "expires_in_minutes": int((RESERVATION_TTL_SECONDS - age) // 60),
            "cohort": str(entry.get("id")).startswith("cohort-"),
        }
        (live if age < RESERVATION_TTL_SECONDS else expired).append(row)
    return {
        "live": live,
        "expired": expired[-10:],
        "expired_total": len(expired),
        "last_activity": last.isoformat() if last else "",
        "idle_minutes": int((now - last).total_seconds() // 60) if last else None,
    }


def run_request(run: dict[str, Any]) -> dict[str, Any]:
    """The ``run-request.json`` body for one planned run (``scripts/run_request.py`` validates it)."""
    return {
        "job": "present",
        "repository": run["repository"],
        "ecosystem": run["ecosystem"],
        "lane": run["lane"],
    }


def decide(*, authorized: bool, plan: dict[str, Any], leases: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    """The bridge's whole policy (pure)."""
    runs = [r for r in plan.get("runs") or [] if isinstance(r, dict)]
    live_cohort = [lease for lease in leases["live"] if lease["cohort"]]
    due = bool(runs)
    stall = None
    idle = leases.get("idle_minutes")
    if authorized and due and not leases["live"] and (idle is None or idle > STALL_MINUTES):
        stall = {
            "idle_minutes": idle,
            "note": f"READY work and no live lease for over {STALL_MINUTES} minutes (plan 8.4 stall): "
            "diagnose the top failure class, do not wait",
        }
    if plan.get("blocked"):
        action, reason = "none", f"planner blocked: {plan['blocked']}"
    elif live_cohort:
        action, reason = "none", f"held: {len(live_cohort)} cohort lease(s) live ({live_cohort[0]['id']}); the run that settles the last one plans the next"
    elif not due:
        action, reason = "none", "no authorized cell needs work (nothing due)"
    elif not authorized:
        action, reason = "none", "data/scheduled_execution_policy.json: scheduled_execution_authorized is not true (preview only)"
    elif dry_run:
        action, reason = "none", "dry run: would dispatch (no call made)"
    else:
        action, reason = "dispatch", f"{len(runs)} cell(s) due, nothing in flight, policy authorized"
    return {
        "schema_version": 1,
        "action": action,
        "reason": reason,
        "policy_authorized": authorized,
        "dry_run": dry_run,
        "due": due,
        "planned_runs": len(runs),
        "next_run_request": run_request(runs[0]) if runs else None,
        "planned_run_requests": [run_request(r) for r in runs],
        "leases": leases,
        "stall": stall,
        "certified": plan.get("certified", {}),
        "diagnose": len(plan.get("diagnose") or []),
        "queued": len(plan.get("queued") or []),
        "skipped": len(plan.get("skipped") or []),
    }


def render(decision: dict[str, Any]) -> str:
    leases = decision["leases"]
    lines = [
        f"bridge action: {decision['action']} ({decision['reason']})",
        f"policy scheduled_execution_authorized: {decision['policy_authorized']}; dry run: {decision['dry_run']}",
        f"due: {decision['planned_runs']} run(s); queued {decision['queued']}, need diagnosis {decision['diagnose']}, skipped {decision['skipped']}",
        f"leases: {len(leases['live'])} live, {leases['expired_total']} expired and recovered; "
        f"idle {leases['idle_minutes']} min since the ledger's last reserve or settle",
    ]
    for lease in leases["live"][:8]:
        lines.append(f"  live lease {lease['id']} {lease['repository']} {','.join(lease['lanes'])}: "
                     f"age {lease['age_minutes']} min, expires in {lease['expires_in_minutes']} min")
    if decision["stall"]:
        lines.append(f"STALL: {decision['stall']['note']} (idle {decision['stall']['idle_minutes']} min)")
    if decision["next_run_request"]:
        lines.append("next run-request.json: " + json.dumps(decision["next_run_request"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    parser.add_argument("--prompts", type=Path, default=REPO_ROOT / "prompts")
    parser.add_argument("--max", type=int, default=6)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    from repo_presenter.core.llm.budget import _now_utc, ledger_entries, read_ledger, state_token
    from scripts.select_scheduled_cohort import build_plan

    token = state_token()
    authorized = policy_authorized()
    try:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        repos = {str(r) for r in policy.get("authorized_repositories") or [] if isinstance(r, str)}
    except (OSError, ValueError, AttributeError):
        repos = set()
    try:
        plan = build_plan(registry=args.registry, remote=args.remote, authorized_repos=repos,
                          prompts=args.prompts, token=token, max_cells=args.max)
        ledger = read_ledger(args.remote, token)
        leases = lease_view(ledger_entries(ledger, any_epoch=True), _now_utc())
    except Exception as error:  # noqa: BLE001 -- fail closed: an unreadable input never dispatches
        plan = {"runs": [], "blocked": f"inputs unreadable ({type(error).__name__}: {error})"}
        leases = {"live": [], "expired": [], "expired_total": 0, "last_activity": "", "idle_minutes": None}
    decision = decide(authorized=authorized, plan=plan, leases=leases, dry_run=args.dry_run)
    text = json.dumps(decision, indent=1) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(render(decision), file=sys.stderr)
    print(f"action={decision['action']}")
    print(f"due={'true' if decision['due'] else 'false'}")
    print(f"stall={'true' if decision['stall'] else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
