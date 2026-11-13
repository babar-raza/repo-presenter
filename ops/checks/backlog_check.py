#!/usr/bin/env python
"""Owner ruling R40 (docs/R40_BACKLOG.md): the backlog's integrity is checked, not trusted.

Every item in project/backlog.yaml has an id, a title, a source (never an invented requirement), a type, a priority, a
status, an implementation path and acceptance criteria; ids are unique; `done` requires non-empty evidence; every
`depends_on` names an existing item. Exit 1 with every problem listed; exit 0 with a status summary.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

BACKLOG = Path(__file__).resolve().parents[2] / "project" / "backlog.yaml"
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
        for dep in item.get("depends_on") or []:
            if dep not in known:
                found.append(f"{iid}: depends_on unknown item {dep}")
    return found


def main() -> int:
    doc = yaml.safe_load(BACKLOG.read_text(encoding="utf-8")) or {}
    found = problems(doc)
    if found:
        print("FAIL:\n  " + "\n  ".join(found))
        return 1
    counts = Counter(i["status"] for i in doc.get("items") or [])
    print("OK: " + ", ".join(f"{k}={counts[k]}" for k in sorted(counts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
