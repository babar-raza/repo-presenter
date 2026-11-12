#!/usr/bin/env python
"""gatecli - the command surface for repo-presenter's supervised execution loop.

Adapted 2026-10-21 from foss-mcp's ops/gatecli.py (reference mechanics only --
see docs/MISSION_AUTHORITY.md). v1 minimal slice: validate, state, commit-guard,
instruct, status-append, verify, review, tick, doctor, resume-brief,
secret-scan, plus dispatch-next/worker-tick (owner ruling R8, 2026-11-06:
lease-based autonomous continuation over the same state machine). Still
deferred (see ops/SUPERVISOR.md "What v1 defers"): preflight/gate-exit/
integrate/release-record.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cardlint
import gateverify
import secretscan
from gatectl import (
    EVIDENCE,
    GLOBAL_DENY,
    INSTRUCTIONS_JSONL,
    OPS,
    REPO,
    SCHEMAS,
    STATE_FILE,
    STATUS_JSONL,
    TASKCARDS,
    all_cards,
    append_jsonl,
    die,
    dump_yaml,
    git,
    git_porcelain_status,
    load_schema,
    load_yaml,
    matches_any,
    now_utc,
    read_jsonl,
    schema_errors,
    write_path_problems,
)
from gatectl import sha256_bytes as gatectl_sha256

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


# --------------------------------------------------------------------------
# validate
# --------------------------------------------------------------------------
def cmd_validate(args) -> int:
    problems = []

    if not STATE_FILE.exists():
        die(f"missing {STATE_FILE}")
    try:
        state = load_yaml(STATE_FILE)
    except Exception as exc:  # noqa: BLE001
        die(f"project/state.yaml does not parse: {exc}")

    for key in ("schema_version", "project", "updated_at"):
        if key not in state:
            problems.append(f"project/state.yaml missing required bootstrap key: {key}")
    if state.get("project") != "repo-presenter":
        problems.append(f"project/state.yaml 'project' is {state.get('project')!r}, expected 'repo-presenter'")

    problems.extend(gateverify.find_duplicate_card_ids())

    cards = all_cards()
    if not cards:
        print("validate: bootstrap mode -- no taskcards under project/taskcards/ yet. "
              "project/state.yaml is supervisor-authored directly (ops/SUPERVISOR.md).")
    else:
        schema = load_schema("taskcard.schema.json")
        for cid, card in sorted(cards.items()):
            errs = schema_errors(schema, card)
            if errs:
                problems.append(f"{cid}: schema violations: " + "; ".join(errs))
        problems.extend(gateverify.find_dependency_graph_problems(cards))
        rows, accepted_ids = gateverify.rebuild_state()
        print("validate: derived card rows from evidence (receipts + instructions.jsonl):")
        for r in rows:
            print(f"  {r['id']}: {r['status']}" + (f" (blocker: {r['blocker']['summary']})" if r.get("blocker") else ""))

        # 2026-11-04: the real execution cursor is `release_gate_dashboard.cards` (tool-generated
        # by `regenerate-dashboard`), not the unused top-level `cards` key the schema names --
        # confirmed real defect: the old comparison here only checked rows ALREADY present in
        # state.yaml, so a card entirely missing from the persisted dashboard was silently never
        # flagged. Now explicitly required once any real taskcard exists.
        dash = state.get("release_gate_dashboard")
        if not isinstance(dash, dict) or not isinstance(dash.get("cards"), list):
            problems.append(
                "project/state.yaml has no release_gate_dashboard.cards -- run "
                "`python ops/gatecli.py regenerate-dashboard` before validating."
            )
        else:
            dash_cards = dash["cards"]
            seen_ids: dict[str, int] = {}
            for i, dc in enumerate(dash_cards):
                seen_ids[dc.get("id")] = seen_ids.get(dc.get("id"), 0) + 1
            for cid, n in seen_ids.items():
                if n > 1:
                    problems.append(f"release_gate_dashboard.cards has {n} entries for {cid!r} -- duplicate")
            dash_by_id = {dc["id"]: dc for dc in dash_cards if "id" in dc}
            for r in rows:
                sc = dash_by_id.get(r["id"])
                if sc is None:
                    problems.append(
                        f"{r['id']}: present under project/taskcards/ but MISSING from "
                        f"release_gate_dashboard.cards -- run `regenerate-dashboard`."
                    )
                elif sc.get("status") != r["status"]:
                    problems.append(
                        f"{r['id']}: release_gate_dashboard says status={sc.get('status')!r} but "
                        f"the rebuild from receipts/instructions says {r['status']!r} -- "
                        f"regenerate-dashboard, never hand-edit this block."
                    )
            extra = set(dash_by_id) - set(cards)
            if extra:
                problems.append(f"release_gate_dashboard.cards names card(s) with no matching file: {sorted(extra)}")

        for cid, card in sorted(cards.items()):
            # 2026-11-04 (supervisor directive correction): this used to pass the receipt's own
            # raw `accepted` field straight through, bypassing cardlint's checks for any card
            # whose receipt forged or stale-claimed `accepted: true` even when
            # rebuild_state()'s own coherence/dependency computation says otherwise (e.g.
            # INCOHERENT_RECEIPT). cardlint must grandfather a card only when it is EFFECTIVELY
            # accepted -- the same set this validate run already derived and printed above --
            # never from the receipt's own say-so.
            accepted = cid in accepted_ids
            problems.extend(cardlint.lint_card(card, REPO, accepted=accepted))

    if problems:
        print("\nvalidate: FAIL", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return EXIT_FAIL
    print("\nvalidate: OK")
    return EXIT_OK


# --------------------------------------------------------------------------
# regenerate-dashboard: the real execution cursor, 2026-11-04
# --------------------------------------------------------------------------
# project/state.yaml's narrative sections (authority/progress/current_gate/active_work_item/
# next_ready_items) carry rich hand-authored comments and are never auto-reformatted -- a full
# YAML load-modify-dump round trip would silently delete every one of them (PyYAML has no
# comment model). This surgically replaces or inserts ONLY the release_gate_dashboard block as
# raw text, exactly like every other edit this file's own history has made to state.yaml by
# hand -- the difference is this one is tool-generated from gateverify.rebuild_state(), never
# narrated, per ops/SUPERVISOR.md's "never hand-write project/state.yaml's card-driven fields."
TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:", re.MULTILINE)


def _splice_top_level_block(text: str, key: str, new_block: str, insert_before_key: str) -> str:
    start_re = re.compile(rf"^{re.escape(key)}:.*?(?=\n[A-Za-z_][A-Za-z0-9_]*:|\Z)", re.MULTILINE | re.DOTALL)
    m = start_re.search(text)
    if m:
        return text[:m.start()] + new_block.rstrip("\n") + "\n" + text[m.end():].lstrip("\n")
    anchor = re.compile(rf"^{re.escape(insert_before_key)}:", re.MULTILINE)
    am = anchor.search(text)
    if not am:
        return text.rstrip("\n") + "\n\n" + new_block
    return text[:am.start()] + new_block.rstrip("\n") + "\n\n" + text[am.start():]


def cmd_regenerate_dashboard(args) -> int:
    rows, _ = gateverify.rebuild_state()
    ready = gateverify.ready_cards_from_rows(rows)
    dashboard = {
        "release_gate_dashboard": {
            "generated_by": "gatecli",
            "generated_at": now_utc(),
            "note": "Tool-generated from gateverify.rebuild_state() -- never hand-edit this "
                    "block. Historical current_gate/active_work_item below are preserved "
                    "bootstrap-era narrative, not this cursor; this block is the real, "
                    "evidence-derived release-gate status as of generated_at.",
            "cards": rows,
            "ready": ready,
        }
    }
    block_text = dump_yaml(dashboard)
    text = STATE_FILE.read_text(encoding="utf-8")
    new_text = _splice_top_level_block(text, "release_gate_dashboard", block_text, "current_gate")
    STATE_FILE.write_text(new_text, encoding="utf-8")
    print(f"regenerate-dashboard: wrote {len(rows)} card rows, ready={ready or 'none'}")
    return EXIT_OK


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------
def cmd_state(args) -> int:
    if not STATE_FILE.exists():
        die(f"missing {STATE_FILE}")
    print(STATE_FILE.read_text(encoding="utf-8"))
    return EXIT_OK


# --------------------------------------------------------------------------
# commit-guard
# --------------------------------------------------------------------------
SUPERVISOR_OWNED = [
    "plans/**", "project/**", "ops/**", "schemas/**", "docs/**", "migration/**", "evidence/**",
    "data/**", ".github/**", ".claude/**", ".gitattributes", ".gitignore", "AGENTS.md", "README.md",
]


def cmd_commit_guard(args) -> int:
    """Refuses when there is uncommitted work OUTSIDE the paths the supervisor
    is about to stage -- the mechanical fix for a `git add -A` sweeping a
    worker's product files into an unrelated supervisor commit (foss-mcp
    TC-018 incident, ops/SUPERVISOR.md)."""
    intended = args.paths if args.paths else SUPERVISOR_OWNED
    rc, out, err = git_porcelain_status()
    if rc != 0:
        die(f"git status failed: {err}")
    offenders = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if not matches_any(path, intended):
            offenders.append(path)
    if offenders:
        print("commit-guard: REFUSED -- uncommitted changes outside the intended supervisor "
              "paths would be swept in by a broad `git add`:", file=sys.stderr)
        for o in offenders:
            print(f"  - {o}", file=sys.stderr)
        print("Stage explicit supervisor paths, never `git add -A`.", file=sys.stderr)
        return EXIT_FAIL
    print("commit-guard: OK -- no uncommitted work outside the intended paths.")
    return EXIT_OK


# --------------------------------------------------------------------------
# instruct / status-append  (the two append-only JSONL channels)
# --------------------------------------------------------------------------
def cmd_instruct(args) -> int:
    rc, head, _ = git("rev-parse", "HEAD")
    issue_rev = args.issue_rev or (head if rc == 0 else "NONE")
    if issue_rev != "NONE":
        # A supervisor typing an abbreviated SHA must not reach the schema as
        # one -- resolve to the full 40-hex form, same discipline as verify's
        # resolve_rev (foss-mcp lesson: an abbreviated SHA in a receipt failed
        # validation after the work was already verified).
        rrc, full, rerr = git("rev-parse", "--verify", f"{issue_rev}^{{commit}}")
        if rrc != 0:
            die(f"instruct: cannot resolve --issue-rev {issue_rev!r}: {rerr}")
        issue_rev = full
    line = {
        "ts": now_utc(),
        "target_card": args.target_card,
        "kind": args.kind,
        "instruction": args.instruction,
        "card_sha256": args.card_sha256 or "NONE",
        "issue_rev": issue_rev,
        "attempt": args.attempt,
    }
    if args.successor:
        line["successor"] = args.successor
    schema = load_schema("instruction-line.schema.json")
    errs = schema_errors(schema, line)
    if errs:
        die("instruct: generated line fails its own schema: " + "; ".join(errs))
    append_jsonl(INSTRUCTIONS_JSONL, line)
    print(f"instruct: appended {line['kind']} for {line['target_card']} (attempt {line['attempt']})")
    return EXIT_OK


def cmd_status_append(args) -> int:
    rc, head, err = git("rev-parse", "HEAD")
    if rc != 0 or not head:
        die(f"status-append: cannot resolve HEAD: {err}")
    line = {
        "ts": now_utc(),
        "card": args.card,
        "phase": args.phase,
        "verdict": args.verdict,
        "summary": args.summary,
        "commit": head,
        "attempt": args.attempt,
    }
    if args.evidence:
        line["evidence"] = args.evidence
    schema = load_schema("status-line.schema.json")
    errs = schema_errors(schema, line)
    if errs:
        die("status-append: generated line fails its own schema: " + "; ".join(errs))
    append_jsonl(STATUS_JSONL, line)
    print(f"status-append: appended {line['phase']}/{line['verdict']} for {line['card']} @ {head[:12]}")
    return EXIT_OK


# --------------------------------------------------------------------------
# verify / review
# --------------------------------------------------------------------------
def cmd_verify(args) -> int:
    receipt = gateverify.do_verify(
        args.card, args.base, args.head,
        issue_rev=args.issue_rev, evaluate_scope=not args.no_scope,
    )
    print(json.dumps(receipt, indent=2))
    return EXIT_OK if receipt["accepted"] else EXIT_FAIL


def cmd_review(args) -> int:
    rc = cmd_verify(args)
    if rc == EXIT_OK:
        print(f"\nreview: ACCEPTED -- {args.card}")
    else:
        print(f"\nreview: REWORK REQUIRED -- {args.card}", file=sys.stderr)
    return rc


# --------------------------------------------------------------------------
# tick / doctor / resume-brief
# --------------------------------------------------------------------------
def cmd_tick(args) -> int:
    # 2026-11-07 (docs/DELIVERY_PLAN_2026-11-07.md Step 0 routine fix): state.yaml's
    # current_gate/active_work_item are bootstrap-era narrative (state.yaml's own dashboard
    # note), superseded by the derived card rows below. Printing them here misled a reader
    # into treating a 2026-11-03 snapshot as live status; tick now reports only what the
    # evidence-derived rebuild actually computes.
    cards = all_cards()
    if cards:
        rows, _ = gateverify.rebuild_state()
        ready = gateverify.ready_cards_from_rows(rows)
        print(f"ready cards: {ready or 'none'}")
    else:
        print("no taskcards yet under project/taskcards/")
    return EXIT_OK


def cmd_doctor(args) -> int:
    problems = []
    if not STATE_FILE.exists():
        problems.append("project/state.yaml is missing")
    if not (OPS / "SUPERVISOR.md").exists():
        problems.append("ops/SUPERVISOR.md is missing")
    rc, out, _ = git_porcelain_status("--", *SUPERVISOR_OWNED)
    if rc == 0 and out.strip():
        problems.append("uncommitted supervisor-owned paths:\n    " + out.strip().replace("\n", "\n    "))
    cards = all_cards()
    schema = load_schema("taskcard.schema.json")
    for cid, card in sorted(cards.items()):
        errs = schema_errors(schema, card)
        if errs:
            problems.append(f"{cid} fails its own schema: " + "; ".join(errs))
        for problem in write_path_problems(card):
            problems.append(f"{cid}: {problem}")
    if problems:
        print("doctor: ISSUES FOUND", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return EXIT_FAIL
    print("doctor: clean")
    return EXIT_OK


def cmd_resume_brief(args) -> int:
    print("=== ops/SUPERVISOR.md ===")
    sup = OPS / "SUPERVISOR.md"
    print("present" if sup.exists() else "MISSING")
    print("\n=== last status lines ===")
    lines = read_jsonl(STATUS_JSONL)
    for line in lines[-10:]:
        print(f"  {line['ts']} {line['card']} {line['phase']}/{line['verdict']}: {line['summary'][:80]}")
    if not lines:
        print("  (none yet)")
    print("\n=== current cursor ===")
    state = load_yaml(STATE_FILE) if STATE_FILE.exists() else {}
    print(dump_yaml({
        "current_gate": state.get("current_gate"),
        "active_work_item": {k: v for k, v in (state.get("active_work_item") or {}).items()
                              if k in ("id", "status", "purpose")},
    }))
    return EXIT_OK


def cmd_secret_scan(args) -> int:
    findings = secretscan.scan_tree(REPO)
    if findings:
        print("secret-scan: POSSIBLE SECRETS FOUND", file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        return EXIT_FAIL
    print("secret-scan: clean")
    return EXIT_OK


# --------------------------------------------------------------------------
# dispatch-next / worker-tick: autonomous continuation (owner ruling R8, 2026-11-06)
# --------------------------------------------------------------------------
# These extend the EXISTING state machine; they are not a second one. The lease lives in the
# same append-only channel the machine already persists dispatches in (ops/instructions.jsonl):
# a `dispatch` line carrying a `lease` object acquires it, a `rework` line renews it after a
# failed independent verify, `lease_release` ends it on a verdict and `lease_expired` ends it
# when the holder went silent past expires_at. gateverify.rebuild_state() derives every card
# status from those same lines (a lease_expired line un-dispatches the card, so it is READY
# again). There is exactly one lease slot: one worker at a time, never two writers racing.
# Acceptance is never decided here -- only by gateverify.do_verify (the same independent,
# worktree-isolated, twice-clean + negative-control path `gatecli.py verify/review` run).
DEFAULT_LEASE_TTL_MINUTES = 240
DEFAULT_HOLDER = "supervisor"
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"
LEASE_FIELDS = ("holder", "base_sha", "acquired_at", "expires_at")


def _parse_ts(ts: str) -> datetime:
    return datetime.strptime(ts, TS_FMT).replace(tzinfo=UTC)


def _plus_minutes(ts: str, minutes: int) -> str:
    return (_parse_ts(ts) + timedelta(minutes=minutes)).strftime(TS_FMT)


def active_lease(instructions: list[dict] | None = None, now: str | None = None) -> dict | None:
    """The single live (or expired-but-not-yet-marked) lease, derived from the instructions
    log alone, or None. ``expired`` is computed against ``now`` (default: now_utc())."""
    if instructions is None:
        instructions = read_jsonl(INSTRUCTIONS_JSONL)
    lease = None
    for ins in instructions:
        kind, card, info = ins.get("kind"), ins.get("target_card"), ins.get("lease")
        if kind == "dispatch" and isinstance(info, dict):
            lease = {"card": card, "attempt": int(ins.get("attempt", 1)),
                     "card_sha256": ins.get("card_sha256", "NONE"), **info}
        elif lease and card == lease["card"]:
            if kind == "rework" and isinstance(info, dict):
                lease.update(info)
                lease["attempt"] = int(ins.get("attempt", lease["attempt"]))
            elif kind in ("lease_release", "lease_expired", "supersede", "stop"):
                lease = None
    if lease is not None:
        lease["expired"] = _parse_ts(now or now_utc()) >= _parse_ts(lease["expires_at"])
    return lease


def _card_sha_at(card_id: str, rev: str) -> str:
    rc, out, _ = git("show", f"{rev}:project/taskcards/{card_id}.yaml")
    if rc != 0:
        return "NONE"
    return gatectl_sha256(out.encode("utf-8"))


def _head_sha(rev: str = "HEAD") -> str:
    rc, out, err = git("rev-parse", "--verify", f"{rev}^{{commit}}")
    if rc != 0 or len(out) != 40:
        die(f"cannot resolve {rev!r}: {err or out}")
    return out


def commit_tag(card: dict) -> str:
    return f"({card['gate']}/{card['id']})"


def tagged_commits(base: str, head: str, card: dict) -> list[str]:
    """Card-tagged commits in base..head, oldest first -- the worker's progress signal (the
    same `(GATE/TC-NNN)` subject tag check_scope attributes a commit to a card by)."""
    rc, out, _ = git("log", "--reverse", "--format=%H%x00%s", f"{base}..{head}")
    if rc != 0:
        return []
    tag = commit_tag(card)
    revs = []
    for line in out.splitlines():
        sha, _, subject = line.partition("\x00")
        if tag in subject:
            revs.append(sha)
    return revs


def assignment(lease: dict, card: dict) -> dict:
    """The machine-readable instruction a worker (or the supervisor dispatching one) acts on."""
    cid, base = card["id"], lease["base_sha"]
    return {
        "card": cid,
        "gate": card["gate"],
        "executor": card.get("executor", "worker"),
        "attempt": lease["attempt"],
        "card_file": f"project/taskcards/{cid}.yaml",
        "card_sha256": lease.get("card_sha256", "NONE"),
        "purpose": " ".join(str(card.get("purpose", "")).split()),
        "write_paths": card.get("write_paths", []),
        "depends_on": card.get("depends_on", []),
        "checks": [c["command"].strip() for c in card.get("checks", [])],
        "commit_subject_tag": commit_tag(card),
        "lease": {k: lease[k] for k in LEASE_FIELDS},
        "report_progress": (f"python ops/gatecli.py status-append --card {cid} --phase committed "
                            f"--verdict n/a --summary \"...\" --attempt {lease['attempt']}"),
        "judged_by": [
            f"python ops/gatecli.py review {cid} --base {base} --head <worker-commit> --issue-rev {base}",
            f"python ops/gatecli.py verify {cid} --base {base} --head <worker-commit> --issue-rev {base}",
        ],
        "never": "the worker never runs verify/review on its own work and never edits "
                 "project/state.yaml, ops/, schemas/ or its own card",
    }


def _append_instruction(line: dict):
    errs = schema_errors(load_schema("instruction-line.schema.json"), line)
    if errs:
        die("generated instruction line fails its own schema: " + "; ".join(errs))
    append_jsonl(INSTRUCTIONS_JSONL, line)


def _lease_line(kind: str, lease: dict, instruction: str, attempt: int, **extra) -> dict:
    info = {k: lease[k] for k in LEASE_FIELDS}
    info.update({k: v for k, v in extra.items() if v is not None})
    return {
        "ts": now_utc(), "target_card": lease["card"], "kind": kind,
        "instruction": instruction, "card_sha256": lease.get("card_sha256", "NONE"),
        "issue_rev": lease["base_sha"], "attempt": attempt, "lease": info,
    }


def _expire(lease: dict):
    _append_instruction(_lease_line(
        "lease_expired", lease,
        f"lease held by {lease['holder']} expired at {lease['expires_at']} with no accepted "
        f"verification -- {lease['card']} returns to READY",
        lease["attempt"], outcome="expired"))


def _acquire(holder: str, ttl: int, base: str | None, dry_run: bool) -> dict:
    """Pick the first READY card in tick's own order and lease it. Returns a result dict."""
    rows, _ = gateverify.rebuild_state()
    ready = gateverify.ready_cards_from_rows(rows)
    cid = gateverify.next_card_from_rows(rows)
    if cid is None:
        return {"status": "IDLE", "ready": [], "reason": "no READY card (blocked cards are "
                "awaiting a prerequisite or an owner decision, never dispatched)"}
    card = all_cards()[cid]
    row = next(r for r in rows if r["id"] == cid)
    prior = [i for i in read_jsonl(INSTRUCTIONS_JSONL) if i.get("target_card") == cid]
    crashed = bool(prior) and prior[-1].get("kind") == "lease_expired"
    # A crashed worker's expired lease did not consume an attempt; a judged failure did.
    attempt = max(1, row.get("attempt", 0)) if crashed else row.get("attempt", 0) + 1
    attempt = min(attempt, 3)
    base_sha = _head_sha(base or "HEAD")
    acquired = now_utc()
    lease = {"card": cid, "attempt": attempt, "holder": holder, "base_sha": base_sha,
             "acquired_at": acquired, "expires_at": _plus_minutes(acquired, ttl),
             "card_sha256": _card_sha_at(cid, base_sha)}
    if not dry_run:
        _append_instruction(_lease_line(
            "dispatch", lease,
            f"lease-dispatched by gatecli dispatch-next to {holder}: implement {cid} exactly as "
            f"project/taskcards/{cid}.yaml states; every commit subject ends with {commit_tag(card)}",
            attempt))
    return {"status": "DRY_RUN_WOULD_DISPATCH" if dry_run else "DISPATCHED",
            "ready": ready, "assignment": assignment(lease, card)}


def _refresh_dashboard(args):
    # Keep release_gate_dashboard in step with the lease line just written (validate compares
    # them); its one-line note goes to stderr so stdout stays a single JSON document.
    if not getattr(args, "no_dashboard", False):
        with contextlib.redirect_stdout(sys.stderr):
            cmd_regenerate_dashboard(args)


def cmd_dispatch_next(args) -> int:
    lease = active_lease()
    if lease and not lease["expired"]:
        if lease["holder"] != args.holder:
            print(json.dumps({"status": "REFUSED", "reason": f"lease held by {lease['holder']!r} "
                              f"on {lease['card']} until {lease['expires_at']}",
                              "lease": lease}, indent=2))
            return EXIT_FAIL
        card = all_cards()[lease["card"]]
        print(json.dumps({"status": "LEASE_HELD", "assignment": assignment(lease, card)}, indent=2))
        return EXIT_OK
    expired_card = None
    if lease and lease["expired"]:
        expired_card = lease["card"]
        if not args.dry_run:
            _expire(lease)
    result = _acquire(args.holder, args.ttl_minutes, args.base, args.dry_run)
    if expired_card:
        result["expired_lease"] = expired_card
    if not args.dry_run and (result["status"] == "DISPATCHED" or expired_card):
        _refresh_dashboard(args)
    print(json.dumps(result, indent=2))
    return EXIT_OK


def _independent_verify(card_id: str, base: str, head: str) -> dict:
    """The ONLY acceptance path: the existing gateverify.do_verify (what `gatecli.py verify`
    runs). Isolated in one function so tests can mock it; worker-tick never grades itself."""
    return gateverify.do_verify(card_id, base, head, issue_rev=base, evaluate_scope=True)


def cmd_worker_tick(args) -> int:
    dry = args.dry_run
    report: dict = {"dry_run": dry, "now": now_utc(), "actions": []}
    act = report["actions"].append
    mutated = False
    lease = active_lease()
    if lease is None:
        act({"action": "no_lease"})
    else:
        card = all_cards().get(lease["card"])
        report["lease"] = {k: v for k, v in lease.items() if k != "card_sha256"}
        head = _head_sha(args.head)
        commits = tagged_commits(lease["base_sha"], head, card) if card else []
        candidate = commits[-1] if commits else None
        if candidate and candidate != lease.get("verified_head"):
            if dry:
                act({"action": "would_verify", "card": lease["card"], "head": candidate,
                     "tagged_commits": len(commits),
                     "command": f"python ops/gatecli.py verify {lease['card']} --base "
                                f"{lease['base_sha']} --head {candidate} --issue-rev {lease['base_sha']}"})
            else:
                receipt = _independent_verify(lease["card"], lease["base_sha"], candidate)
                reason = str(receipt.get("reason", ""))
                if receipt.get("accepted"):
                    _append_instruction(_lease_line(
                        "lease_release", lease, f"independent verify ACCEPTED {candidate}",
                        lease["attempt"], verified_head=candidate, outcome="accepted"))
                    act({"action": "verified_accepted", "card": lease["card"], "head": candidate})
                    lease = None
                elif lease["attempt"] >= 3:
                    _append_instruction(_lease_line(
                        "lease_release", lease, f"attempt 3 failed independent verify: {reason}"[:2000],
                        lease["attempt"], verified_head=candidate, outcome="failed_internal"))
                    act({"action": "failed_internal", "card": lease["card"], "head": candidate,
                         "reason": reason})
                    lease = None
                else:
                    renewed = dict(lease, expires_at=_plus_minutes(now_utc(), args.ttl_minutes))
                    _append_instruction(_lease_line(
                        "rework", renewed,
                        f"REWORK REQUIRED (independent verify of {candidate[:12]}): {reason}"[:2000],
                        lease["attempt"] + 1, verified_head=candidate, outcome="rework"))
                    act({"action": "rework_lease_renewed", "card": lease["card"], "head": candidate,
                         "attempt": lease["attempt"] + 1, "expires_at": renewed["expires_at"],
                         "reason": reason})
                mutated = True
        elif lease["expired"]:
            act({"action": "would_expire" if dry else "expired", "card": lease["card"],
                 "expires_at": lease["expires_at"], "tagged_commits": len(commits)})
            if not dry:
                _expire(lease)
                mutated = True
            lease = None
        else:
            act({"action": "no_progress", "card": lease["card"], "tagged_commits": len(commits),
                 "already_verified_head": lease.get("verified_head"),
                 "lease_live_until": lease["expires_at"]})
    if lease is None and not args.no_advance:
        result = _acquire(args.holder, args.ttl_minutes, None, dry)
        act({"action": "advance", **result})
        mutated = mutated or result["status"] == "DISPATCHED"
    if mutated and not dry:
        _refresh_dashboard(args)
    print(json.dumps(report, indent=2))
    return EXIT_OK


# --------------------------------------------------------------------------
# argument parser
# --------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(prog="gatecli.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate").set_defaults(func=cmd_validate)
    sub.add_parser("regenerate-dashboard").set_defaults(func=cmd_regenerate_dashboard)
    sub.add_parser("state").set_defaults(func=cmd_state)

    cg = sub.add_parser("commit-guard")
    cg.add_argument("--paths", nargs="*", default=None)
    cg.set_defaults(func=cmd_commit_guard)

    ins = sub.add_parser("instruct")
    ins.add_argument("--target-card", required=True)
    ins.add_argument("--kind", required=True,
                      choices=["dispatch", "rework", "root_cause", "stop", "channel_init", "supersede"])
    ins.add_argument("--instruction", required=True)
    ins.add_argument("--card-sha256", default=None)
    ins.add_argument("--issue-rev", default=None)
    ins.add_argument("--attempt", type=int, default=1)
    ins.add_argument("--successor", default=None)
    ins.set_defaults(func=cmd_instruct)

    sa = sub.add_parser("status-append")
    sa.add_argument("--card", required=True)
    sa.add_argument("--phase", required=True,
                     choices=["started", "committed", "blocked", "new_defect", "provisional", "ended"])
    sa.add_argument("--verdict", required=True, choices=["pass", "fail", "n/a"])
    sa.add_argument("--summary", required=True)
    sa.add_argument("--attempt", type=int, default=1)
    sa.add_argument("--evidence", nargs="*", default=None)
    sa.set_defaults(func=cmd_status_append)

    for name, fn in (("verify", cmd_verify), ("review", cmd_review)):
        v = sub.add_parser(name)
        v.add_argument("card")
        v.add_argument("--base", required=True)
        v.add_argument("--head", required=True)
        v.add_argument("--issue-rev", default=None)
        v.add_argument("--no-scope", action="store_true")
        v.set_defaults(func=fn)

    for name, fn in (("dispatch-next", cmd_dispatch_next), ("worker-tick", cmd_worker_tick)):
        d = sub.add_parser(name)
        d.add_argument("--holder", default=DEFAULT_HOLDER,
                       help="who holds the lease (a session id, a subagent name)")
        d.add_argument("--ttl-minutes", type=int, default=DEFAULT_LEASE_TTL_MINUTES)
        d.add_argument("--dry-run", action="store_true",
                       help="report what would happen; write nothing")
        d.add_argument("--no-dashboard", action="store_true",
                       help="do not regenerate release_gate_dashboard after a state change")
        if name == "dispatch-next":
            d.add_argument("--base", default=None, help="base revision for the lease (default HEAD)")
        else:
            d.add_argument("--head", default="HEAD",
                           help="revision to look for the worker's card-tagged commits in")
            d.add_argument("--no-advance", action="store_true",
                           help="do not dispatch the next READY card after a release/expiry")
        d.set_defaults(func=fn)

    sub.add_parser("tick").set_defaults(func=cmd_tick)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("resume-brief").set_defaults(func=cmd_resume_brief)
    sub.add_parser("secret-scan").set_defaults(func=cmd_secret_scan)

    return p


def main(argv=None) -> int:
    # This machine defaults to cp1252; gatecli's own stdout must not mangle an
    # em-dash or curly quote from a YAML/Markdown file it is only printing,
    # not writing (the written files are already read/written as UTF-8).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
