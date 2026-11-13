"""Fail-closed authorization gate for present.yml's `schedule:` trigger ONLY (2026-11-04 P0,
follow-up directive section 2: "Make scheduled provider-consuming execution fail closed until
its explicit authorization and safety predicates are satisfied... Enforce the gate at the actual
workflow execution boundary [not] only by changing taskcard status").

A manual `workflow_dispatch` never calls this script -- an explicit, named, human-triggered run
IS its own authorization (directive: "preserve safe manual read-only tests, isolated engineering
runs and explicitly authorized pilots"). Only a `schedule:`-triggered run, which nobody watched
when it started, needs this gate.

A scheduled run spends real provider calls and commits real durable-state git refs even when
every registry entry stays `mode: dry_run` (that mode only gates the final upstream PR/issue
effect -- see core/registry/write_gate.py -- not the internal pipeline's cost or its own state
writes). This gate is therefore the correct place to stop an unauthorized scheduled run before
either happens, and it independently re-derives every predicate from its own primary source --
it never trusts a single hand-set flag as a complete authorization:

  1. data/scheduled_execution_policy.json: scheduled_execution_authorized == true AND the
     candidate repository is explicitly named in authorized_repositories.
  2. docs/DECISION_LOG.md: the most recent OWNER_RULING_SWEEP_PAUSE: entry reads LIFTED (TC-004 --
     the 2026-10-31 portfolio-sweep pause has never otherwise been lifted on the record).
  3. data/acceptance_calibration.json: a PASSED certificate for every required mechanism class
     (owner ruling R33, 2026-11-13; replaces the frozen data/reviewer_calibration.json).

All three together are necessary; any one of them failing makes the whole gate fail closed.
Absent that, the run selects nothing, spends nothing, and writes nothing -- a clean, evidenced
no-op (exit 0, authorized=false, reason= naming exactly what is missing), never a crashed job and
never a silent partial authorization.

Owner ruling R37 (2026-11-13): once the predicates hold, the gate plans the whole fire -- up to six
(repository, lane) cells, R25 -- through scripts/select_scheduled_cohort.plan_cohort (needs-work,
terminal, idempotency and bounded-retry rules live there) and writes it with --plan for
present.yml's cohort job, which reserves budget and dispatches one present run per repository.

Usage: python scripts/scheduled_execution_gate.py [--max 6] [--remote origin]
           [--plan plan.json] [--summary summary.md]
Always prints `authorized=`, `reason=`, `repository=`, `ecosystem=`, `lane=` (the first run) and
`runs=` as GITHUB_OUTPUT-style lines (empty / 0 when authorized=false). Always exits 0.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from scripts.select_scheduled_cohort import (  # noqa: E402
    MAX_CELLS,
    build_plan,
    render_summary,
)

from repo_presenter.readme.review.calibration_status import (  # noqa: E402
    PASSED,
    load_calibration,
)

DECISION_LOG = REPO_ROOT / "docs" / "DECISION_LOG.md"
CALIBRATION = REPO_ROOT / "data" / "reviewer_calibration.json"
POLICY = REPO_ROOT / "data" / "scheduled_execution_policy.json"

SWEEP_PAUSE_RE = re.compile(r"OWNER_RULING_SWEEP_PAUSE:\s*(\S+)")


def sweep_pause_lifted(decision_log_text: str) -> bool:
    """Only the MOST RECENT ruling counts -- an owner can re-pause after lifting. Anything other
    than the literal token LIFTED (no ruling at all, UPHELD, a typo) is "still paused," never
    inferred as permissive."""
    matches = SWEEP_PAUSE_RE.findall(decision_log_text)
    if not matches:
        return False
    return matches[-1].rstrip(".,:;") == "LIFTED"


def calibration_passed(path: Path) -> bool:
    """True only when the project's own fail-closed parser reads the file as exactly PASSED.

    Delegates to ``calibration_status.load_calibration`` so this gate can never be more permissive
    than the code that guards the reviewer itself: a bare ``"status": "PASSED"`` beside failed
    gates, a missing ``measured`` object, an unknown status or a reviewer-logic version other than
    the current one all read as not passed. PASSED_WITH_DECLARED_LIMITS (a limited, owner-accepted
    pass) deliberately does NOT open scheduled spend."""
    return load_calibration(path).status == PASSED


def load_policy(path: Path) -> dict:
    if not path.exists():
        return {"scheduled_execution_authorized": False, "authorized_repositories": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"scheduled_execution_authorized": False, "authorized_repositories": []}
    if not isinstance(data, dict):
        return {"scheduled_execution_authorized": False, "authorized_repositories": []}
    return data


def evaluate_predicates(
    *, decision_log_text: str, calibration: Path, policy: dict
) -> list[str]:
    """Every unmet predicate, named plainly; an empty list means every predicate is satisfied."""
    reasons = []
    if not policy.get("scheduled_execution_authorized"):
        reasons.append(
            "data/scheduled_execution_policy.json: scheduled_execution_authorized is not true"
        )
    if not sweep_pause_lifted(decision_log_text):
        reasons.append(
            "TC-004: the 2026-10-31 portfolio-sweep pause has not been explicitly lifted "
            "(docs/DECISION_LOG.md has no OWNER_RULING_SWEEP_PAUSE: LIFTED entry)"
        )
    # Owner ruling R33 (2026-11-13): "accepted" is defined by the acceptance contract, so the third
    # predicate is the acceptance calibration's PASSED certificates (data/acceptance_calibration.json
    # against data/acceptance_responsibility.json), not the frozen data/reviewer_calibration.json.
    if not acceptance_calibration_complete():
        reasons.append(
            "R33: data/acceptance_calibration.json does not hold a PASSED certificate for every "
            "required mechanism class (data/acceptance_responsibility.json)"
        )
    return reasons


def acceptance_calibration_complete() -> bool:
    """Fail-closed: every required mechanism class has a PASSED certificate."""
    from repo_presenter.acceptance.record import load_certificates

    return load_certificates().complete


def _print_blocked(reasons: list[str]) -> None:
    print("authorized=false")
    print("repository=")
    print("ecosystem=")
    print("lane=")
    print("runs=0")
    print("reason=" + " | ".join(reasons))


def _write(path: Path | None, text: str) -> None:
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Owner ruling R37 (2026-11-13): a scheduled fire plans a whole cohort -- up to six cells
    (R25), each with its own lane -- through ``scripts/select_scheduled_cohort.plan_cohort``,
    and only after every predicate above holds. ``--plan`` writes the plan for the fire's
    dispatcher; the printed lines name the first run (the ``--max 1`` contract this gate always
    had) and the number of runs."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max", type=int, default=MAX_CELLS, help="cells per fire (R25: six)")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--registry", type=Path, default=REPO_ROOT / "data" / "registry.json")
    parser.add_argument("--prompts", type=Path, default=REPO_ROOT / "prompts")
    parser.add_argument("--plan", type=Path, default=None, help="write the cohort plan (JSON) here")
    parser.add_argument("--summary", type=Path, default=None, help="write the fire's markdown summary here")
    args = parser.parse_args(argv)

    decision_log_text = (
        DECISION_LOG.read_text(encoding="utf-8") if DECISION_LOG.exists() else ""
    )
    policy = load_policy(POLICY)
    reasons = evaluate_predicates(
        decision_log_text=decision_log_text, calibration=CALIBRATION, policy=policy
    )
    if reasons:
        blocked = {"runs": [], "skipped": [], "diagnose": [], "queued": [], "certified": {},
                   "blocked": " | ".join(reasons)}
        _write(args.plan, json.dumps(blocked, indent=1) + "\n")
        _write(args.summary, render_summary(blocked))
        _print_blocked(reasons)
        return 0

    authorized_repos = {
        str(r) for r in (policy.get("authorized_repositories") or []) if isinstance(r, str)
    }
    from repo_presenter.core.llm.budget import state_token

    try:
        plan = build_plan(
            registry=args.registry, remote=args.remote, authorized_repos=authorized_repos,
            prompts=args.prompts, token=state_token(), max_cells=args.max,
        )
    except Exception as error:  # noqa: BLE001 -- fail closed: an unreadable input selects nothing
        reason = f"the cohort inputs could not be read ({type(error).__name__}: {error})"
        blocked = {"runs": [], "skipped": [], "diagnose": [], "queued": [], "certified": {},
                   "blocked": reason}
        _write(args.plan, json.dumps(blocked, indent=1) + "\n")
        _write(args.summary, render_summary(blocked))
        _print_blocked([reason])
        return 0
    _write(args.plan, json.dumps(plan, indent=1) + "\n")
    _write(args.summary, render_summary(plan))
    if not plan["runs"]:
        _print_blocked(
            [
                (
                    "every predicate cleared, but no authorized cell needs work this fire "
                    f"({len(plan['skipped'])} skipped, {len(plan['diagnose'])} need diagnosis)"
                )
            ]
        )
        return 0

    first = plan["runs"][0]
    print("authorized=true")
    print(f"repository={first['repository']}")
    print(f"ecosystem={first['ecosystem']}")
    print(f"lane={first['lane']}")
    print(f"runs={len(plan['runs'])}")
    print("reason=all predicates satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
