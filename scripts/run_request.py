"""Validate a run request for the privileged, ``workflow_run``-triggered executor (owner ruling,
docs/CONSOLIDATED_GOALS_2026-11-06.md, blocker 2; trust redesign 2026-11-06, docs/DECISION_LOG.md).

This session's GitHub access cannot dispatch workflows (HTTP 403) but can push. A run request is a branch
``run-requests/<id>`` whose ONLY change from the current ``main`` is one file, ``run-request.json``::

    {"job": "present", "repository": "owner/name", "ecosystem": "rust", "lane": "R"}
    {"job": "mint"}

Trust boundary. A push-triggered workflow runs the workflow files of the PUSHED commit, so nothing that holds a
secret may run on the push. ``.github/workflows/run-request.yml`` (push) holds no secret, has a read-only
token, checks nothing out and only exists to produce a ``workflow_run`` event.
``.github/workflows/run-request-execute.yml`` runs on that event; GitHub always executes a ``workflow_run``
workflow from the default branch, so this script, the executor and the workflows it calls are ``main``'s. The
executor checks out ``main`` and runs THIS script, which reads the request from the triggering commit as data
(``git show <head_sha>:run-request.json``, never executed) and refuses unless:

* the triggering run is ``.github/workflows/run-request.yml``, triggered by ``push`` in this repository (not a
  fork), and concluded ``success``;
* its branch is ``run-requests/<id>`` and its ``head_sha`` is still that branch's tip (no replay of an older,
  superseded request);
* the checked-out code is the current ``main``, and the request commit is based on it and changes nothing but
  ``run-request.json`` (so a modified workflow or a modified validator on the branch is refused too);
* the request itself passes ``validate()`` (allowed job, registered repository and ecosystem, lane).

    python scripts/run_request.py --event "$GITHUB_EVENT_PATH"   # prints key=value lines for $GITHUB_OUTPUT
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REQUEST_FILE = "run-request.json"
JOBS = {"present", "mint"}
LANES = {"R", "L", "both"}
TRIGGER_WORKFLOW = ".github/workflows/run-request.yml"
BRANCH_PREFIX = "run-requests/"
_BRANCH = re.compile(r"^run-requests/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
BASE_REF = "refs/run-request/base"
TIP_REF = "refs/run-request/tip"


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


def check_trigger(event: Any) -> tuple[str, str]:
    """``(head_branch, head_sha)`` of a ``workflow_run`` event payload that came from the unprivileged
    run-request workflow, on a push in this repository, and succeeded; ``RequestError`` otherwise."""
    run = event.get("workflow_run") if isinstance(event, dict) else None
    if not isinstance(run, dict):
        raise RequestError("not a workflow_run event")
    path = str(run.get("path") or "").split("@", 1)[0]
    if path != TRIGGER_WORKFLOW:
        raise RequestError(f"unknown triggering workflow {run.get('path')!r}; only {TRIGGER_WORKFLOW} may request a run")
    if run.get("event") != "push":
        raise RequestError(f"the triggering run was a {run.get('event')!r} event, not a push")
    if run.get("conclusion") != "success":
        raise RequestError(f"the triggering run concluded {run.get('conclusion')!r}, not 'success'")
    own = (event.get("repository") or {}).get("full_name")
    head_repo = (run.get("head_repository") or {}).get("full_name")
    if not own or head_repo != own:
        raise RequestError(f"the request comes from {head_repo!r}, not from this repository {own!r}")
    branch, sha = run.get("head_branch"), run.get("head_sha")
    if not isinstance(branch, str) or not branch.startswith(BRANCH_PREFIX) or not _BRANCH.match(branch):
        raise RequestError(f"branch {branch!r} is not a {BRANCH_PREFIX}<id> branch")
    if not isinstance(sha, str) or not _SHA.match(sha):
        raise RequestError(f"head_sha {sha!r} is not a commit id")
    return branch, sha


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def _git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], capture_output=True, text=True).returncode == 0


def resolve(event: Any, remote: str = "origin", base_branch: str = "main") -> dict[str, str]:
    """Every trust check against the real repository; the current directory is the checked-out ``main``.
    The request commit is only ever read as data (``git show``); nothing from it is checked out or run."""
    branch, head_sha = check_trigger(event)
    if not _git_ok("fetch", "--no-tags", "--quiet", remote,
                   f"+refs/heads/{base_branch}:{BASE_REF}", f"+refs/heads/{branch}:{TIP_REF}"):
        raise RequestError(f"could not fetch {base_branch} and {branch} (was the request branch deleted?)")
    base, tip = _git("rev-parse", BASE_REF).strip(), _git("rev-parse", TIP_REF).strip()
    if tip != head_sha:
        raise RequestError(f"{head_sha} is no longer the tip of {branch} ({tip}): a superseded request is not replayed")
    if _git("rev-parse", "HEAD").strip() != base:
        raise RequestError(f"the checked-out code is not the current {base_branch} ({base}); refusing to run stale code")
    based = _git_ok("merge-base", "--is-ancestor", base, head_sha)
    changed = sorted(p for p in _git("diff", "--name-only", "--no-renames", base, head_sha).splitlines() if p)
    if not based or changed != [REQUEST_FILE]:
        validate(None, [], changed, based)  # raises the precise refusal before the request is even read
    try:
        request = json.loads(_git("show", f"{head_sha}:{REQUEST_FILE}"))
        registry = json.loads(_git("show", f"{base}:data/registry.json"))["entries"]
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RequestError(f"unreadable request or registry: {exc}") from exc
    return {**validate(request, registry, changed, based), "head_sha": head_sha}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", type=Path, required=True, help="the workflow_run event payload ($GITHUB_EVENT_PATH)")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--base-branch", default="main")
    args = parser.parse_args(argv)
    try:
        outputs = resolve(json.loads(args.event.read_text(encoding="utf-8")), args.remote, args.base_branch)
    except (RequestError, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    for key, value in outputs.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
