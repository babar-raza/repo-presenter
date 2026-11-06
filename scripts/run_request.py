"""Validate a push-triggered run request (owner ruling, docs/CONSOLIDATED_GOALS_2026-11-06.md, blocker 2).

This session's GitHub access cannot dispatch workflows (HTTP 403) but can push. A run request is a branch
``run-requests/<id>`` whose ONLY change from the current ``main`` is one file, ``run-request.json``::

    {"job": "present", "repository": "owner/name", "ecosystem": "rust", "lane": "R"}
    {"job": "mint"}

``.github/workflows/run-request.yml`` runs this script first and calls the named workflow only when it
passes. Because a push-triggered workflow runs the workflow files of the pushed commit, the branch must be
exactly ``main`` plus the request: anything else is refused, so the code that runs is always ``main``'s.

    python scripts/run_request.py --request run-request.json --base origin/main   # prints key=value lines
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REQUEST_FILE = "run-request.json"
JOBS = {"present", "mint"}
LANES = {"R", "L", "both"}


class RequestError(ValueError):
    pass


def validate(request: Any, registry: list[dict[str, Any]], changed: list[str], based_on_base: bool) -> dict[str, str]:
    """The workflow outputs for a valid request; ``RequestError`` naming the first problem otherwise."""
    if not based_on_base:
        raise RequestError("the request branch is not based on the current main")
    if changed != [REQUEST_FILE]:
        raise RequestError(f"the request branch must change only {REQUEST_FILE}, it changes {changed}")
    if not isinstance(request, dict):
        raise RequestError("the request is not a JSON object")
    job = request.get("job")
    if job not in JOBS:
        raise RequestError(f"unknown job {job!r}; allowed: {sorted(JOBS)}")
    if job == "mint":
        if set(request) != {"job"}:
            raise RequestError("a mint request takes no other field (its target is fixed in the workflow)")
        return {"job": "mint", "repository": "", "ecosystem": "", "lane": ""}
    allowed_keys = {"job", "repository", "ecosystem", "lane"}
    if set(request) - allowed_keys:
        raise RequestError(f"unknown fields {sorted(set(request) - allowed_keys)}")
    repository, ecosystem, lane = request.get("repository"), request.get("ecosystem"), request.get("lane", "both")
    entry = next((e for e in registry if e.get("repository") == repository), None)
    if entry is None:
        raise RequestError(f"{repository!r} is not listed in data/registry.json")
    if ecosystem != entry.get("ecosystem"):
        raise RequestError(f"{repository} is registered as {entry.get('ecosystem')!r}, not {ecosystem!r}")
    if lane not in LANES:
        raise RequestError(f"lane {lane!r} is not one of {sorted(LANES)}")
    return {"job": "present", "repository": repository, "ecosystem": ecosystem, "lane": lane}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--request", type=Path, default=Path(REQUEST_FILE))
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--registry", type=Path, default=Path("data/registry.json"))
    args = parser.parse_args(argv)
    base = _git("rev-parse", args.base).strip()
    based = _git("merge-base", base, "HEAD").strip() == base
    changed = sorted(p for p in _git("diff", "--name-only", base, "HEAD").splitlines() if p)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        outputs = validate(request, json.loads(args.registry.read_text(encoding="utf-8"))["entries"], changed, based)
    except (RequestError, OSError, json.JSONDecodeError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    for key, value in outputs.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
