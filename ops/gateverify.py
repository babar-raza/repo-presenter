"""gateverify - the acceptance engine. Adapted 2026-10-21 from foss-mcp's
ops/gateverify.py (reference mechanics only). Simplified for v1: no container
runner, no pinned-venv-by-lockfile, no holdout directory wiring yet (the
mechanism is a TODO for when a second card exists -- see
ops/SUPERVISOR.md "What v1 defers"). The core safety property is kept
unsimplified: checks run twice clean (flake = fail), then the supervisor's
negative control MUST make them fail, or the card is rejected however green
it looked.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from gatectl import (
    EVIDENCE,
    REPO,
    STATUS_JSONL,
    CANONICAL_ENV,
    all_cards,
    check_scope,
    die,
    drop_worktree,
    fingerprint,
    load_card_at_rev,
    make_worktree,
    now_utc,
    parse_junit,
    read_jsonl,
    resolve_rev,
    run,
    sha256_bytes,
    sha256_file,
)

GATE_STATUS_ORDER = ["BLOCKED_ENV", "FAILED_INTERNAL", "IN_PROGRESS", "VERIFYING", "READY", "ACCEPTED"]


def receipt_dir(gate: str, card_id: str) -> Path:
    return EVIDENCE / "build" / gate / card_id


def load_receipt(gate: str, card_id: str):
    f = receipt_dir(gate, card_id) / "receipt.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def capabilities_missing(requires) -> list[str]:
    """v1 only knows about python (always present, this is python) and git."""
    import shutil
    missing = []
    for cap in requires or []:
        if cap == "git" and not shutil.which("git"):
            missing.append("git")
        # "python" is always present -- gatecli.py is running under it.
    return missing


def _blocked_env(card_id, gate, head, missing, outdir):
    receipt = {
        "schema_version": 1,
        "card": card_id,
        "gate": gate,
        "generated_by": "gatecli",
        "generated_at": now_utc(),
        "base_rev": head,
        "head_rev": head,
        "fingerprint": fingerprint(),
        "scope": {"ok": True, "changed_paths": [], "violations": []},
        "runs": [
            {"run": 1, "checks": [], "all_passed": False},
            {"run": 2, "checks": [], "all_passed": False},
        ],
        "negative_control": {"kind": "mutate", "patch": "n/a", "patch_sha256": "0" * 64,
                              "applied": False, "patch_applied_failed": False},
        "accepted": False,
        "reason": f"BLOCKED_ENV: missing capability: {', '.join(missing)}",
    }
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def run_checks(card, wt: Path, log_lines):
    env = dict(CANONICAL_ENV)
    if not card.get("network", False):
        env["HTTP_PROXY"] = env["HTTPS_PROXY"] = "http://127.0.0.1:9"
        env["GATECTL_OFFLINE"] = "1"

    results, all_passed = [], True
    for idx, chk in enumerate(card["checks"]):
        cmd = chk["command"]
        junit = None
        if chk.get("junitxml"):
            junit = wt / f".junit-{idx}.xml"
            cmd = f'{cmd} "--junitxml={junit}"'
        cwd = wt / chk.get("cwd", ".")
        t0 = time.time()
        rc, out, err = run(cmd, cwd=cwd, env=env, timeout=chk.get("timeout_seconds", 600))
        dur = round(time.time() - t0, 3)
        log_lines.append(f"$ {cmd}\n--- stdout ---\n{out}\n--- stderr ---\n{err}\n")
        entry = {
            "command": chk["command"],
            "exit_code": rc,
            "duration_s": dur,
            "stdout_sha256": sha256_bytes((out + err).encode("utf-8", "replace")),
        }
        if junit:
            entry.update(parse_junit(junit))
        results.append(entry)
        if rc != 0:
            all_passed = False
    return results, all_passed


def structural_gate(card, checks):
    """Exit code 0 is a near-worthless predicate alone -- demand real, unskipped
    tests where a check reports junit counts."""
    problems = []
    min_tests = card.get("min_tests")
    for c in checks:
        if "tests" not in c:
            continue
        if min_tests is not None and c["tests"] < min_tests:
            problems.append(f"{c['command']}: collected {c['tests']} tests, card requires >= {min_tests}")
        if c.get("skipped", 0) > 0:
            problems.append(f"{c['command']}: {c['skipped']} skipped test(s); skips are not evidence")
        if c.get("errors", 0) > 0:
            problems.append(f"{c['command']}: {c['errors']} collection error(s)")
    return problems


def do_verify(card_id: str, base: str, head: str, issue_rev: str | None = None,
              evaluate_scope: bool = True, persist: str = "always"):
    """Run a card's checks for real and write the receipt. Order matters: clean
    run twice (flake detection), structural gate, then the negative control,
    which MUST make the checks fail."""
    if persist not in ("always", "on_fail"):
        raise ValueError(f"persist must be 'always' or 'on_fail', got {persist!r}")
    base = resolve_rev(base)
    head = resolve_rev(head)
    issue_rev = resolve_rev(issue_rev or head)
    card, card_sha = load_card_at_rev(card_id, issue_rev)
    gate = card["gate"]
    outdir = receipt_dir(gate, card_id)
    outdir.mkdir(parents=True, exist_ok=True)

    absent = capabilities_missing(card.get("requires"))
    if absent:
        return _blocked_env(card_id, gate, head, absent, outdir)

    if evaluate_scope:
        ok_scope, changed, violations = check_scope(card, base, head)
    else:
        ok_scope, changed, violations = True, [], []

    log_lines: list[str] = []
    runs: list[dict] = []
    nc_spec = card["negative_control"]
    nc_kind = "patch" if "patch" in nc_spec else "mutate"
    negctl = {
        "kind": nc_kind,
        "patch": nc_spec.get("patch") or nc_spec.get("mutate"),
        "patch_sha256": "0" * 64,
        "applied": False,
        "patch_applied_failed": False,
        "exit_codes": [],
    }
    structural: list[str] = []
    clean_passed = False

    wt = make_worktree(head)
    try:
        for i in (1, 2):
            log_lines.append(f"\n===== CLEAN RUN {i} =====\n")
            checks, passed = run_checks(card, wt, log_lines)
            runs.append({"run": i, "checks": checks, "all_passed": passed})
        structural = structural_gate(card, runs[0]["checks"])

        codes1 = [c["exit_code"] for c in runs[0]["checks"]]
        codes2 = [c["exit_code"] for c in runs[1]["checks"]]
        flaky = codes1 != codes2
        clean_passed = runs[0]["all_passed"] and runs[1]["all_passed"] and not flaky

        if clean_passed:
            if nc_kind == "patch":
                patch = REPO / nc_spec["patch"]
                if patch.exists():
                    negctl["patch_sha256"] = sha256_file(patch)
                    rc, _, err = run(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=wt)
                    applied, why = rc == 0, err
                else:
                    applied, why = False, f"patch missing: {patch}"
            else:
                cmd = nc_spec["mutate"]
                negctl["patch_sha256"] = sha256_bytes(cmd.encode("utf-8"))
                rc, out, err = run(cmd, cwd=wt, timeout=120)
                applied, why = rc == 0, (err or out)

            if applied:
                _, dirty, _ = run(["git", "status", "--porcelain"], cwd=wt)
                if not dirty.strip():
                    applied = False
                    why = ("command exited 0 but left the tree byte-identical - it mutated "
                           "nothing. This is NOT a passing falsifier.")
                else:
                    negctl["tree_changed"] = [ln.strip() for ln in dirty.strip().splitlines()]

            if applied:
                negctl["applied"] = True
                log_lines.append("\n===== NEGATIVE CONTROL (checks MUST now fail) =====\n")
                log_lines.append("mutated: " + ", ".join(negctl.get("tree_changed", [])) + "\n")
                nchecks, npassed = run_checks(card, wt, log_lines)
                negctl["exit_codes"] = [c["exit_code"] for c in nchecks]
                negctl["patch_applied_failed"] = not npassed
            else:
                log_lines.append(f"\n!! falsifier did not apply ({nc_kind}): {why}\n")
        else:
            log_lines.append("\n!! clean runs failed; falsifier skipped (it would prove nothing)\n")
    finally:
        drop_worktree(wt)

    log_text = "".join(log_lines)

    reasons = []
    if not ok_scope:
        reasons.append("scope violation: " + "; ".join(violations[:5]))
    if not clean_passed:
        if runs and runs[0]["all_passed"] != runs[1]["all_passed"]:
            reasons.append("FLAKY: the two clean runs disagreed")
        elif runs and not runs[0]["all_passed"]:
            failed = [c["command"] for c in runs[0]["checks"] if c["exit_code"] != 0]
            reasons.append("checks failed: " + "; ".join(failed))
        else:
            reasons.append("clean checks did not pass identically twice")
    if structural:
        reasons.append("structural gate: " + "; ".join(structural))
    if not negctl["applied"]:
        reasons.append("negative-control patch did not apply")
    elif not negctl["patch_applied_failed"]:
        reasons.append("VACUOUS CHECKS: the suite still passed with the falsifier applied")

    receipt = {
        "schema_version": 1,
        "card": card_id,
        "gate": gate,
        "generated_by": "gatecli",
        "generated_at": now_utc(),
        "base_rev": base,
        "head_rev": head,
        "card_sha256": card_sha,
        "fingerprint": fingerprint(),
        "scope": {"ok": ok_scope, "changed_paths": changed, "violations": violations},
        "runs": runs,
        "negative_control": negctl,
        "accepted": len(reasons) == 0,
        "reason": "; ".join(reasons) if reasons else "all gates passed",
    }
    stored = load_receipt(gate, card_id)
    stored_passed = bool(stored and stored.get("accepted"))
    if persist == "always" or not receipt["accepted"] or not stored_passed:
        (outdir / "stdout.log").write_text(log_text, encoding="utf-8")
        (outdir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


# --------------------------------------------------------------------------
# derived state
# --------------------------------------------------------------------------
def gate_status(statuses: list[str], accepted: bool, exit_verdict) -> str:
    if accepted:
        return "ACCEPTED"
    if not statuses:
        return "READY"
    if any(s == "BLOCKED_ENV" for s in statuses):
        return "BLOCKED_ENV"
    if any(s == "FAILED_INTERNAL" for s in statuses):
        return "FAILED_INTERNAL"
    if all(s in ("ACCEPTED", "SUPERSEDED") for s in statuses):
        return "EXIT_FAILED" if exit_verdict == "NOT_MET" else "EXIT_PENDING"
    if any(s == "IN_PROGRESS" for s in statuses):
        return "IN_PROGRESS"
    return "READY"


def rebuild_state(cards_order: list[str] | None = None):
    """project/state.yaml's CARD-DRIVEN portion is a FUNCTION of primary
    evidence (cards on disk + receipts + instructions log), never a narration.
    This only covers the `cards`/`current_gate`/`accepted_gates`/
    `execution_limits` fields -- the bootstrap-era fields (`authority`,
    `progress`, `active_work_item`, pre-card `current_gate.id` like
    P0_BOOTSTRAP) are supervisor-authored directly until the first taskcard
    exists, exactly as ops/SUPERVISOR.md documents."""
    cards = all_cards()
    instructions = read_jsonl(Path(STATUS_JSONL).parent / "instructions.jsonl")

    attempts: dict[str, int] = {}
    dispatched: set[str] = set()
    for ins in instructions:
        t = ins.get("target_card")
        if t and t != "ALL":
            attempts[t] = max(attempts.get(t, 0), int(ins.get("attempt", 0)))
            if ins.get("kind") in ("dispatch", "rework"):
                dispatched.add(t)

    rows, accepted_ids = [], set()
    for cid in sorted(cards):
        c = cards[cid]
        r = load_receipt(c["gate"], cid)
        row = {"id": cid, "gate": c["gate"], "status": "PENDING",
               "attempt": attempts.get(cid, 0), "blocker": None}
        if r and r.get("accepted"):
            row["status"] = "ACCEPTED"
            row["commit"] = r["head_rev"]
            row["receipt"] = f"{r['gate']}/{cid}/receipt.json"
            accepted_ids.add(cid)
        elif r and not r.get("accepted"):
            if row["attempt"] >= 3:
                row["status"] = "FAILED_INTERNAL"
                row["blocker"] = {
                    "class": "FAILED_INTERNAL",
                    "summary": r.get("reason", "verification failed"),
                    "resume_predicate": f"a new commit for {cid} passes `gatecli.py verify {cid}`",
                    "recorded_at": r.get("generated_at", now_utc()),
                }
            else:
                row["status"] = "IN_PROGRESS"
        elif cid in dispatched:
            row["status"] = "IN_PROGRESS"
        rows.append(row)

    for row in rows:
        if row["status"] == "PENDING":
            deps = cards[row["id"]].get("depends_on", [])
            if all(d in accepted_ids for d in deps):
                row["status"] = "READY"

    return rows, accepted_ids


def ready_cards_from_rows(rows):
    return [r["id"] for r in rows if r["status"] == "READY"]


def next_card_from_rows(rows):
    ready = sorted(ready_cards_from_rows(rows))
    return ready[0] if ready else None
