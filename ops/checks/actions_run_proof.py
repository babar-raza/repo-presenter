#!/usr/bin/env python
"""Release-gate-card check: an execution proof is only as good as the run that wrote it.

``execution_proof.py`` reads a JSON file anyone with write access could edit. This check verifies
the proof against GitHub itself (independent audit 2026-11-06, "live-effect proof can rely on
editable JSON assertions"):

1. the proof names a workflow run, and the GitHub Actions API reports that run ``completed`` /
   ``success``, from one of the expected workflow files;
2. the proof file on the expected branch of the state remote was committed by
   ``github-actions[bot]`` in a commit whose message names that run id;
3. the local proof file is byte-identical to the bot-committed one.

Usage: python ops/checks/actions_run_proof.py <proof.json> <branch> <workflow-file>[,<workflow-file>...]

Needs network and an authenticated ``gh`` CLI (the card declaring it sets ``network: true``).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPOSITORY = "babar-raza/repo-presenter"
BOT = "github-actions[bot]"


def _run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[-3])
        return 2
    path, branch, workflows = Path(argv[0]), argv[1], set(argv[2].split(","))
    if not path.is_file():
        print(f"FAIL: {path} does not exist")
        return 1
    local = path.read_bytes()
    run_id = str(json.loads(local).get("run_id") or "")
    if not run_id.isdigit():
        print(f"FAIL: {path} names no workflow run id")
        return 1
    try:
        run = json.loads(_run("gh", "api", f"repos/{REPOSITORY}/actions/runs/{run_id}"))
    except subprocess.CalledProcessError as exc:
        print(f"FAIL: run {run_id} could not be read from the Actions API: {exc.stderr.strip()}")
        return 1
    workflow = Path(str(run.get("path", ""))).name.split("@", 1)[0]
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        print(f"FAIL: run {run_id} is {run.get('status')}/{run.get('conclusion')}, not completed/success")
        return 1
    if workflow not in workflows:
        print(f"FAIL: run {run_id} came from {workflow!r}, not one of {sorted(workflows)}")
        return 1
    ref = f"refs/check/{branch.replace('/', '_')}"
    try:
        _run("git", "fetch", "-q", "origin", f"+refs/heads/{branch}:{ref}")
        remote = subprocess.run(
            ["git", "show", f"{ref}:{path.as_posix()}"], capture_output=True, check=True
        ).stdout
        author, subject = _run(
            "git", "log", "-1", "--format=%an%x00%s", ref, "--", path.as_posix()
        ).strip().split("\x00", 1)
    except subprocess.CalledProcessError as exc:
        print(f"FAIL: {path} could not be read from origin/{branch}: {exc}")
        return 1
    if author != BOT:
        print(f"FAIL: {path} on origin/{branch} was committed by {author!r}, not {BOT}")
        return 1
    if run_id not in subject:
        print(f"FAIL: the commit of {path} on origin/{branch} does not name run {run_id}: {subject!r}")
        return 1
    if remote != local:
        print(f"FAIL: {path} differs from the {BOT} commit on origin/{branch}")
        return 1
    print(
        f"OK: {path} is the {BOT} commit on origin/{branch} written by run {run_id} "
        f"({workflow}, completed/success)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
