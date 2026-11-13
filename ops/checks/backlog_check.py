#!/usr/bin/env python
"""Owner ruling R40 (docs/R40_BACKLOG.md): the backlog's integrity is checked, not trusted.

Every item in project/backlog.yaml has an id, a title, a source (never an invented requirement), a type, a priority, a
status, an implementation path and acceptance criteria; ids are unique; `done` requires non-empty evidence; every
`depends_on` names an existing item.

Silently dropped work is the failure this guards against (owner, 2026-11-13: "how to best track it"), so it also checks:
  * every task card the release-gate dashboard does not show ACCEPTED/SUPERSEDED is named by a backlog item;
  * every docs/DECISION_LOG.md entry dated on or after DECISION_LOG_RULE_FROM carries a "Backlog:" line (BL ids, or
    "none") — a follow-up written only in prose is how work was dropped;
  * staleness (report, never a CI failure): items whose `updated` date is older than their status allows
    (active 3 days, blocked 7 days — R24 re-check, open 14 days) are listed; `--strict` fails on them (the hosted
    tick prints the report).
Exit 1 with every problem listed; exit 0 with a status summary.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BACKLOG = ROOT / "project" / "backlog.yaml"
STATE = ROOT / "project" / "state.yaml"
DECISION_LOG = ROOT / "docs" / "DECISION_LOG.md"
DECISION_LOG_RULE_FROM = dt.date(2026, 11, 14)
STALE_AFTER_DAYS = {"active": 3, "blocked": 7, "open": 14}
SEED_DATE = dt.date(2026, 11, 13)  # items without `updated` were last verified by the 2026-11-13 reconciliation
STATUSES = {"open", "active", "blocked", "deferred", "done"}
TYPES = {"requirement", "task", "defect", "feedback", "gap", "debt", "blocked"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
REQUIRED = ("id", "title", "type", "source", "priority", "status", "implementation_path", "acceptance")


def problems(doc: dict) -> list[str]:
    found: list[str] = []
    items = doc.get("items") or []
    ids = [str(i.get("id")) for i in items]
    for dup, n in Counter(ids).items():
        if n > 1:
            found.append(f"duplicate id {dup}")
    known = set(ids)
    for item in items:
        iid = item.get("id", "?")
        for key in REQUIRED:
            if not str(item.get(key) or "").strip():
                found.append(f"{iid}: missing {key}")
        if item.get("status") not in STATUSES:
            found.append(f"{iid}: status {item.get('status')!r} not in {sorted(STATUSES)}")
        if item.get("type") not in TYPES:
            found.append(f"{iid}: type {item.get('type')!r} not in {sorted(TYPES)}")
        if item.get("priority") not in PRIORITIES:
            found.append(f"{iid}: priority {item.get('priority')!r} not in {sorted(PRIORITIES)}")
        if item.get("status") == "done" and not item.get("evidence"):
            found.append(f"{iid}: done without evidence (R40 req 7)")
        if (item.get("status") == "done" and item.get("type") in ("feedback", "defect")
                and not any("reverified" in str(e).lower() for e in item.get("evidence") or [])):
            found.append(f"{iid}: a {item.get('type')} item is done only with portfolio-wide re-verification evidence "
                         "('reverified: <run id>, lane R x/y, lane L x/y') (R41)")
        for dep in item.get("depends_on") or []:
            if dep not in known:
                found.append(f"{iid}: depends_on unknown item {dep}")
    return found


def _text(item: dict) -> str:
    return " ".join(str(v) for v in item.values())


def untracked_cards(doc: dict, state: dict) -> list[str]:
    """Task cards not ACCEPTED/SUPERSEDED on the dashboard that no backlog item names."""
    cards = ((state or {}).get("release_gate_dashboard") or {}).get("cards") or []
    open_cards = [c["id"] for c in cards if c.get("status") not in ("ACCEPTED", "SUPERSEDED")]
    corpus = " ".join(_text(i) for i in doc.get("items") or [])
    return [f"task card {cid} is {next(c['status'] for c in cards if c['id'] == cid)} but no backlog item names it"
            for cid in open_cards if not re.search(rf"\b{re.escape(cid)}\b", corpus)]


_ENTRY = re.compile(r"^## (\d{4}-\d{2}-\d{2})\b.*$", re.M)


def untracked_decisions(log: str) -> list[str]:
    """Decision-log entries on/after the rule date without a "Backlog:" line."""
    found = []
    heads = list(_ENTRY.finditer(log))
    for n, head in enumerate(heads):
        day = dt.date.fromisoformat(head.group(1))
        if day < DECISION_LOG_RULE_FROM:
            continue
        body = log[head.end(): heads[n + 1].start() if n + 1 < len(heads) else len(log)]
        if not re.search(r"^\s*\**Backlog:?\**:?\s*\S", body, re.M):
            found.append(f"decision-log entry '{head.group(0)[3:80]}' has no 'Backlog:' line (BL ids or 'none')")
    return found


def stale(doc: dict, today: dt.date) -> list[str]:
    found = []
    for item in doc.get("items") or []:
        limit = STALE_AFTER_DAYS.get(item.get("status"))
        if limit is None:
            continue
        raw = item.get("updated")
        try:
            day = dt.date.fromisoformat(str(raw)) if raw else SEED_DATE
        except ValueError:
            found.append(f"{item.get('id')}: updated {raw!r} is not a date")
            continue
        if (today - day).days > limit:
            found.append(f"{item.get('id')} [{item.get('priority')}] {item.get('status')} since {day} (> {limit} days): {str(item.get('title'))[:80]}")
    return found


_SHA = re.compile(r"\b[0-9a-f]{7,40}\b")


def unlanded_done(doc: dict, is_ancestor) -> list[str]:
    """A `done` item that cites a commit not in this history claims work that never landed (the 2026-11-13
    reconciliation found four "done" branches that existed only locally)."""
    found = []
    for item in doc.get("items") or []:
        if item.get("status") != "done":
            continue
        for sha in _SHA.findall(" ".join(str(e) for e in item.get("evidence") or [])):
            if not any(ch.isalpha() for ch in sha) or not any(ch.isdigit() for ch in sha):
                continue  # a plain number or word, not a commit id
            verdict = is_ancestor(sha)
            if verdict is False:
                found.append(f"{item.get('id')}: done, but cited commit {sha} is not in this history (not landed)")
    return found


def _git_is_ancestor(sha: str):
    import subprocess  # noqa: PLC0415

    known = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=ROOT, capture_output=True)
    if known.returncode != 0:
        return None  # unknown object here (e.g. another repository's commit): not judged
    return subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=ROOT, capture_output=True).returncode == 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    strict, report = "--strict" in argv, "--report" in argv
    doc = yaml.safe_load(BACKLOG.read_text(encoding="utf-8")) or {}
    state = yaml.safe_load(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    found = problems(doc) + untracked_cards(doc, state) + unlanded_done(doc, _git_is_ancestor)
    if DECISION_LOG.exists():
        found += untracked_decisions(DECISION_LOG.read_text(encoding="utf-8"))
    old = stale(doc, dt.date.today())
    if strict:
        found += [f"stale: {s}" for s in old]
    if found:
        print("FAIL:\n  " + "\n  ".join(found))
        return 1
    counts = Counter(i["status"] for i in doc.get("items") or [])
    print("OK: " + ", ".join(f"{k}={counts[k]}" for k in sorted(counts)))
    if report or old:
        print(f"stale ({len(old)}):" + ("".join(f"\n  {s}" for s in old) if old else " none"))
    if report:
        nxt = [i for i in doc.get("items") or [] if i.get("status") in ("open", "active")]
        nxt.sort(key=lambda i: (i.get("priority", "P9"), i.get("status") != "active", i.get("id")))
        print("next eligible:" + "".join(f"\n  {i['id']} [{i['priority']}] {i['status']}: {str(i['title'])[:90]}" for i in nxt[:8]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
