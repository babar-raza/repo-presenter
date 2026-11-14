"""Extract every Lane R outcome line from downloaded hosted ``present`` job logs (BL-085).

Input: a directory of ``<run id>.log`` files written by
``gh run view <id> -R babar-raza/repo-presenter --log --job <present job id>``.
Output (stdout): JSON lines, one per run, holding only the Lane R step's ``blocking``, ``finding``,
``repair``, ``restore`` and ``failure`` lines (secrets never appear in these lines; the env blocks
that name them are skipped). Zero provider calls; reads files only.

    python docs/investigations/2026-11-13-lane-r-not-progressing/extract_hosted.py LOGDIR > hosted_lane_r.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KINDS = ("blocking", "finding", "repair", "restore", "failure")


def extract(path: Path) -> dict:
    run = {"run": path.stem, "repository": None, "lanes": None, "main_sha": None,
           **{kind: [] for kind in KINDS}}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split("\t", 2)
        step = parts[1] if len(parts) == 3 else ""
        text = re.sub(r"^﻿?\S+Z ", "", parts[-1]).strip()
        if run["repository"] is None and (m := re.search(r"INPUT_REPOSITORY: (\S+)", text)):
            run["repository"] = m.group(1)
        if run["lanes"] is None and (m := re.search(r'--lanes "([^"]+)"', text)):
            run["lanes"] = m.group(1)
        if run["main_sha"] is None and (m := re.search(r'--main-sha "([0-9a-f]+)"', text)):
            run["main_sha"] = m.group(1)
        if step != "Present (Lane R)":
            continue
        for kind in KINDS:
            if text.startswith(kind + " ") or text.startswith(kind + ":"):
                run[kind].append(text)
                break
    return run


def main(argv: list[str]) -> int:
    for path in sorted(Path(argv[1]).glob("*.log")):
        run = extract(path)
        if run["repository"] and "R" in (run["lanes"] or ""):
            print(json.dumps(run, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
