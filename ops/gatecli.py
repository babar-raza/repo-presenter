#!/usr/bin/env python
"""gatecli - the command surface for repo-presenter's supervised execution loop.

Adapted 2026-10-21 from foss-mcp's ops/gatecli.py (reference mechanics only --
see docs/MISSION_AUTHORITY.md). v1 minimal slice: validate, state, commit-guard,
instruct, status-append, verify, review, tick, doctor, resume-brief,
secret-scan. Deferred to a later card (see ops/SUPERVISOR.md "What v1
defers"): dispatch-next/worker-tick/preflight/gate-exit/integrate/
release-record -- not needed until a second taskcard exists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
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
)

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
    state = load_yaml(STATE_FILE) if STATE_FILE.exists() else {}
    print(f"gate: {state.get('current_gate', {}).get('id')} "
          f"[{state.get('current_gate', {}).get('status')}]")
    awi = state.get("active_work_item")
    if awi:
        print(f"active work item: {awi.get('id')} [{awi.get('status')}]")
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
