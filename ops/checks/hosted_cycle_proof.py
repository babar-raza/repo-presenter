#!/usr/bin/env python
"""Release-gate-card check (TC-012b): an operational, unattended, AUTHORIZED hosted presentation
cycle actually ran -- proven from GitHub's Actions API and the durable state refs, never from an
editable JSON assertion.

TC-012 was accepted on infrastructure evidence (a schedule trigger, a fail-closed authorization
gate, a Docker build). Every scheduled run so far is a deliberate no-op: green, with "Build the
facts" and both "Present (Lane ...)" steps SKIPPED. This check passes only when at least one run
satisfies ALL of:

  1. GitHub's Actions API lists it as a run of the present workflow, for the given event
     (default `schedule`: unattended), on the default branch, conclusion `success`;
  2. the run's own jobs (Actions API) show "Build the facts" concluded `success` -- real facts
     were built, so the authorization gate let the run through -- and at least one
     "Present (Lane R)"/"Present (Lane L)" step concluded `success` (not skipped);
  3. the durable state refs on the remote hold, in some record ref's history, a record of that
     lane whose trigger-dedup ledger maps `run:<run id>:<repository>` to a transaction whose
     last transition reached a sealed outcome (ACCEPTED or READY_FOR_PROPOSAL), and a durable
     bundle ref exists for that repository and lane.

It also requires the current workflow file to still declare a schedule trigger: a cycle proven
once but no longer scheduled is not an operational unattended cycle.

Usage: python ops/checks/hosted_cycle_proof.py [--event schedule] [--workflow present.yml]
       [--slug owner/name] [--remote origin]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RECORDS = "refs/repository-presenter-state/records"
BUNDLES = "refs/repository-presenter-state/bundles"
SEALED = frozenset({"ACCEPTED", "READY_FOR_PROPOSAL"})
LANE_STEPS = {"Present (Lane R)": "R", "Present (Lane L)": "L"}
FACTS_STEP = "Build the facts"


def gh_json(path: str):
    done = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        raise RuntimeError(f"gh api {path} failed: {done.stderr.strip()[:300]}")
    return json.loads(done.stdout)


def run_git(args: list[str], cwd: Path) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=300)
    if done.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {done.stderr.strip()[:300]}")
    return done.stdout


def workflow_still_scheduled(workflow: str) -> bool:
    path = REPO_ROOT / ".github" / "workflows" / workflow
    if not path.is_file():
        return False
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    triggers = doc.get("on", doc.get(True, {})) or {}  # YAML 1.1 reads a bare `on` as True
    return isinstance(triggers, dict) and bool(triggers.get("schedule"))


def executed_runs(slug: str, workflow: str, event: str) -> list[tuple[int, set[str]]]:
    """(run id, lanes whose Present step succeeded) for every qualifying run (criteria 1-2)."""
    repo = gh_json(f"repos/{slug}")
    default_branch = repo.get("default_branch", "main")
    listed = gh_json(
        f"repos/{slug}/actions/workflows/{workflow}/runs?event={event}&status=success&per_page=100"
    )
    found = []
    for run in listed.get("workflow_runs", []):
        if run.get("conclusion") != "success" or run.get("head_branch") != default_branch:
            continue
        jobs = gh_json(f"repos/{slug}/actions/runs/{run['id']}/jobs?per_page=100")
        steps = {
            step.get("name"): step.get("conclusion")
            for job in jobs.get("jobs", [])
            for step in job.get("steps", [])
        }
        if steps.get(FACTS_STEP) != "success":
            continue
        lanes = {lane for name, lane in LANE_STEPS.items() if steps.get(name) == "success"}
        if lanes:
            found.append((int(run["id"]), lanes))
    return found


def sealed_by_run(remote: str, run_ids: set[int]) -> dict[int, list[tuple[str, str, str]]]:
    """run id -> [(repository, lane, sealed state)] from every record ref's full history."""
    result: dict[int, list[tuple[str, str, str]]] = {}
    with tempfile.TemporaryDirectory(prefix="cycle-proof-") as tmp:
        cwd = Path(tmp)
        run_git(["init", "-q", "--bare"], cwd)
        url = run_git(["remote", "get-url", remote], REPO_ROOT).strip()
        run_git(["fetch", "-q", url, f"+{RECORDS}/*:{RECORDS}/*", f"+{BUNDLES}/*:{BUNDLES}/*"], cwd)
        bundles = set(run_git(["for-each-ref", "--format=%(refname)", BUNDLES], cwd).split())
        for ref in run_git(["for-each-ref", "--format=%(refname)", RECORDS], cwd).split():
            key = ref[len(RECORDS) + 1:]
            if f"{BUNDLES}/{key}" not in bundles:
                continue
            for commit in run_git(["rev-list", ref], cwd).split():
                try:
                    record = json.loads(run_git(["show", f"{commit}:record.json"], cwd))
                except (RuntimeError, ValueError):
                    continue
                last = record.get("last_transition") or {}
                if last.get("to") not in SEALED and last.get("to_state") not in SEALED:
                    continue
                tx = last.get("transaction_id")
                for dedup, mapped in (record.get("recent_trigger_dedup_keys") or {}).items():
                    parts = dedup.split(":", 2)
                    if len(parts) == 3 and parts[0] == "run" and parts[1].isdigit():
                        rid = int(parts[1])
                        if rid in run_ids and mapped == tx:
                            state = last.get("to") or last.get("to_state")
                            entry = (record.get("repository", ""), record.get("lane", "R"), state)
                            if entry not in result.setdefault(rid, []):
                                result[rid].append(entry)
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", default="schedule")
    parser.add_argument("--workflow", default="present.yml")
    parser.add_argument("--slug", default="babar-raza/repo-presenter")
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)

    if not workflow_still_scheduled(args.workflow):
        print(f"FAIL: .github/workflows/{args.workflow} declares no schedule trigger")
        return 1
    try:
        runs = executed_runs(args.slug, args.workflow, args.event)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: the Actions API could not be read: {exc}")
        return 1
    if not runs:
        print(f"FAIL: no successful {args.event} run of {args.workflow} built facts and ran a "
              f"Present step (every such run so far skipped them: authorized=false)")
        return 1
    try:
        sealed = sealed_by_run(args.remote, {rid for rid, _ in runs})
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: the state refs could not be read: {exc}")
        return 1
    proven = []
    for rid, lanes in runs:
        for repository, lane, state in sealed.get(rid, []):
            if lane in lanes:
                proven.append(f"run {rid}: {repository} Lane {lane} -> {state}")
    if not proven:
        print(f"FAIL: {len(runs)} executed {args.event} run(s) found, but none left a sealed "
              f"outcome with a durable bundle in the state refs: {[rid for rid, _ in runs]}")
        return 1
    print("OK: operational unattended cycle proven -- " + "; ".join(proven))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
