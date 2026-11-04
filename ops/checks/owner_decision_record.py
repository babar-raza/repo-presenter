#!/usr/bin/env python
"""Release-gate-card check: assert a structured, cross-referenced owner-decision record exists
-- not just an arbitrary marker string an agent could write unilaterally (the real defect in
this card's first version, confirmed 2026-11-04: a mutate that merely appended the required
marker could never falsify a legitimate positive state, because appending more of the same text
an agent can already write proves nothing about whether a human actually decided anything).

No purely mechanical check can prove a human actually made a decision -- that is out of scope
for this script. What it CAN enforce is that the record is dated and cross-references a real,
existing entry in docs/DECISION_LOG.md by anchor text, raising the bar from "one string
anywhere" to "a dated record whose reference resolves to real content elsewhere," and giving a
negative control two independent things it can corrupt (the date/ref line itself, or the
decision-log entry it points at) instead of one marker it can only duplicate.

Required record format in the target file: "<PREFIX> <YYYY-MM-DD> ref=<anchor-text-no-spaces>"
The <anchor-text-no-spaces> must appear verbatim somewhere in docs/DECISION_LOG.md.

Usage: python ops/checks/owner_decision_record.py <target_file> <prefix>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DECISION_LOG = Path("docs/DECISION_LOG.md")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: owner_decision_record.py <target_file> <prefix>")
        return 2
    target = Path(argv[0])
    prefix = argv[1]
    text = target.read_text(encoding="utf-8") if target.exists() else ""
    pattern = re.compile(re.escape(prefix) + r"\s+(\d{4}-\d{2}-\d{2})\s+ref=(\S+)")
    m = pattern.search(text)
    if not m:
        print(f"FAIL: {target} has no record matching '{prefix} <YYYY-MM-DD> ref=<anchor>'")
        return 1
    date, anchor = m.group(1), m.group(2)
    log_text = DECISION_LOG.read_text(encoding="utf-8") if DECISION_LOG.exists() else ""
    if anchor not in log_text:
        print(f"FAIL: ref={anchor} (dated {date}) does not match any text in {DECISION_LOG}")
        return 1
    print(f"OK: {target} has a cross-referenced record dated {date}; ref={anchor} found in {DECISION_LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
