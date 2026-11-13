"""Validate a run request for the privileged, ``workflow_run``-triggered executor (owner ruling,
docs/CONSOLIDATED_GOALS_2026-11-06.md, blocker 2; trust redesign 2026-11-06, docs/DECISION_LOG.md).

This session's GitHub access cannot dispatch workflows (HTTP 403) but can push. A run request is a branch
``run-requests/<id>`` whose ONLY change from the current ``main`` is one file, ``run-request.json``::

    {"job": "present", "repository": "owner/name", "ecosystem": "rust", "lane": "R"}
    {"job": "mint"}
    {"job": "recertify"}
    {"job": "cohort"}
    {"job": "audit-seed"}
    {"job": "audit-score", "seed_run_id": "43217648963",
     "findings_path": "evidence/build/GATE5_DELIVERY_PROGRAM/M9_AUDIT/findings-43217648963.json"}
    {"job": "acceptance-write", "seed_run_id": "...", "findings_path": "...",
     "findings_ref": "audit-findings/run-...", "adjudications_path": ""}

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

The M9 audit jobs (owner, 2026-11-13, R37: "this should be wired to the system so everything is autonomous";
the system runs itself on GitHub Actions) add these checks:

* ``seed_run_id`` is digits only and names, in THIS repository, a completed run whose ``seed`` job succeeded
  and that holds an unexpired ``m9-seed-manifest-<id>`` artifact: a run of ``audit-seed.yml`` on ``main``
  (schedule or dispatch) or of ``run-request-execute.yml`` (workflow_run, always main's files) calling it.
  Checked through the GitHub API with the executor's read-only token (``verify_seed_run``): the event
  payload vouches only for the trigger run, never for a run it does not describe;
* ``findings_path`` is exactly ``evidence/build/GATE5_DELIVERY_PROGRAM/M9_AUDIT/findings-<seed_run_id>.json``
  (so no ``..``, no other directory, no other round's file) and exists on ``main``, or, with
  ``findings_ref: audit-findings/run-<seed_run_id>``, on the hosted auditor's frozen bot branch;
  ``adjudications_path`` is empty or exactly ``.../adjudications-<seed_run_id>.json`` on ``main``;
* ONE OPEN SEED BATCH AT A TIME (owner trust boundary): ``audit-seed`` is refused while any
  ``audit-seed/run-<id>`` branch has no ``acceptance-record/run-<id>[-<writer run>]`` branch, so a round is
  scored and written before another seed is spent. Seeds stay burned per run id (the seeder's salt); the
  key stays in the ``acceptance-audit`` environment; nothing here, and no session, reads the manifest.

Supervisor runbook -- the autonomous M9 round. The PRIMARY path needs no session step: ``audit-seed.yml``
runs on its schedule; its ``gate`` job (``run_m9_seeder.py --gate``) seeds only when no batch is open and
enough sealed candidates are not yet judged, or resumes the open batch; its hosted ``audit`` job
(``run_m9_auditor.py audit``: the existing independent reviewer over each case's text and its seal's pinned
facts, never the manifest) commits the findings FROZEN to ``audit-findings/run-<id>``; ``audit-score.yml``
and ``acceptance-write.yml`` then run as reusable calls in the same run, on main, in ``acceptance-audit``.
The supervisor only watches. The OVERRIDE path (a batch the gate reports ``blocked``, findings or
adjudications committed to main by blind reviewers) is one run request per step, each a branch
``run-requests/<id>`` holding one commit on current main that adds only ``run-request.json``:

1. push ``{"job": "audit-seed"}`` (refused while a batch is open); wait for the run -- its run id is the
   seed id, and its own chain may already finish the round;
2. blind auditors who never see the manifest freeze findings: the hosted ``audit-findings/run-<id>``
   branch, or a PR merged to main adding ``M9_AUDIT/findings-<id>.json``;
3. push ``{"job": "audit-score", "seed_run_id": "<id>", "findings_path": ".../findings-<id>.json"}`` (add
   ``"findings_ref": "audit-findings/run-<id>"`` for the hosted branch);
4. push ``{"job": "acceptance-write", <the same fields>, "adjudications_path": ""}``: it writes and attests
   ``acceptance-record/run-<id>-<writer run>``, which also closes the batch.

    python scripts/run_request.py --event "$GITHUB_EVENT_PATH"   # prints key=value lines for $GITHUB_OUTPUT
"""

from __future__ import annotations

import argparse
import json
import re
import os
import subprocess
import sys
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

REQUEST_FILE = "run-request.json"
AUDIT_JOBS = ("audit-seed", "audit-score", "acceptance-write")
JOBS = {"present", "mint", "recertify", "cohort", *AUDIT_JOBS}
LANES = {"R", "L", "both"}
TRIGGER_WORKFLOW = ".github/workflows/run-request.yml"
BRANCH_PREFIX = "run-requests/"
_BRANCH = re.compile(r"^run-requests/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
BASE_REF = "refs/run-request/base"
TIP_REF = "refs/run-request/tip"

# --- the M9 audit round's pieces (audit-seed.yml, run_m9_auditor.py, acceptance-write.yml) ---------------
M9_DIR = "evidence/build/GATE5_DELIVERY_PROGRAM/M9_AUDIT"
SEED_BRANCH_PREFIX = "audit-seed/run-"
FINDINGS_BRANCH_PREFIX = "audit-findings/run-"
SCORE_BRANCH_PREFIX = "audit-score/seed-run-"
ATTEMPT_BRANCH_PREFIX = "audit-attempt/run-"
BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
_RUN_ID = re.compile(r"^[1-9][0-9]{0,19}$")
_SEED_BRANCH = re.compile(r"^audit-seed/run-([1-9][0-9]{0,19})$")
_RECORD_BRANCH = re.compile(r"^acceptance-record/run-([1-9][0-9]{0,19})(?:-[1-9][0-9]{0,19})?$")
#: The workflows a seed run may be a run of, and the events that may start it. A ``workflow_run`` run
#: always executes the default branch's files; ``audit-seed.yml`` must also have run on main.
SEED_WORKFLOWS = {
    ".github/workflows/audit-seed.yml": frozenset({"schedule", "workflow_dispatch"}),
    ".github/workflows/run-request-execute.yml": frozenset({"workflow_run"}),
}
SEED_MANIFEST_ARTIFACT = "m9-seed-manifest-{}"


class RequestError(ValueError):
    pass


def findings_path_for(seed_run_id: str) -> str:
    return f"{M9_DIR}/findings-{seed_run_id}.json"


def adjudications_path_for(seed_run_id: str) -> str:
    return f"{M9_DIR}/adjudications-{seed_run_id}.json"


def findings_ref_for(seed_run_id: str) -> str:
    return f"{FINDINGS_BRANCH_PREFIX}{seed_run_id}"


def is_run_id(value: Any) -> bool:
    return isinstance(value, str) and _RUN_ID.match(value) is not None


def open_seed_batches(heads: Iterable[str]) -> list[str]:
    """Seed run ids (oldest first) that have an ``audit-seed/run-<id>`` branch and no acceptance-record
    branch ``acceptance-record/run-<id>`` or ``acceptance-record/run-<id>-<writer run id>``: the rounds
    seeded and not yet written. ``heads`` are branch names without ``refs/heads/``."""
    seeded, written = set(), set()
    for head in heads:
        if (match := _SEED_BRANCH.match(head)) is not None:
            seeded.add(match.group(1))
        elif (match := _RECORD_BRANCH.match(head)) is not None:
            written.add(match.group(1))
    return sorted(seeded - written, key=int)


class AuditContext:
    """What the M9 job checks need from the real repository, injected so tests use fakes: the remote's
    branch names, whether a path exists at a ref (``"main"`` or a findings branch) and the seed-run
    verifier (raises ``RequestError``). A plain class: this script is also loaded by file path, where
    a dataclass cannot resolve its own module."""

    def __init__(
        self,
        heads: Iterable[str] = (),
        exists: Callable[[str, str], bool] = lambda ref, path: False,
        verify_seed_run: Callable[[str], None] = lambda run_id: None,
    ) -> None:
        self.heads = list(heads)
        self.exists = exists
        self.verify_seed_run = verify_seed_run


def _validate_audit(job: str, request: dict[str, Any], context: AuditContext | None) -> dict[str, str]:
    if context is None:
        raise RequestError(f"an {job} request cannot be verified without the repository context")
    blank = {"job": job, "repository": "", "ecosystem": "", "lane": ""}
    if job == "audit-seed":
        if set(request) != {"job"}:
            raise RequestError("an audit-seed request takes no other field (its salt is its own run id)")
        still_open = open_seed_batches(context.heads)
        if still_open:
            first = still_open[0]
            raise RequestError(
                f"seed batch run {first} is still open ({SEED_BRANCH_PREFIX}{first} has no "
                f"acceptance-record/run-{first}-* branch): one open seed batch at a time; score and write it first"
            )
        return blank
    allowed = {"job", "seed_run_id", "findings_path", "findings_ref"}
    if job == "acceptance-write":
        allowed.add("adjudications_path")
    if set(request) - allowed:
        raise RequestError(f"unknown fields {sorted(set(request) - allowed)}")
    seed = request.get("seed_run_id")
    if not is_run_id(seed):
        raise RequestError(f"seed_run_id {seed!r} is not a run id (a string of digits)")
    findings = request.get("findings_path")
    if findings != findings_path_for(seed):
        raise RequestError(f"findings_path {findings!r} is not {findings_path_for(seed)!r}")
    ref = request.get("findings_ref", "")
    if ref not in ("", findings_ref_for(seed)):
        raise RequestError(f"findings_ref {ref!r} is neither empty (main) nor {findings_ref_for(seed)!r}")
    adjudications = request.get("adjudications_path", "")
    if adjudications not in ("", adjudications_path_for(seed)):
        raise RequestError(
            f"adjudications_path {adjudications!r} is neither empty nor {adjudications_path_for(seed)!r}"
        )
    if f"{SEED_BRANCH_PREFIX}{seed}" not in context.heads:
        raise RequestError(f"there is no {SEED_BRANCH_PREFIX}{seed} branch: {seed} is not a seed batch")
    if ref and ref not in context.heads:
        raise RequestError(f"there is no {ref} branch")
    if not context.exists(ref or "main", findings):
        raise RequestError(f"{findings} does not exist on {ref or 'main'}")
    if adjudications and not context.exists("main", adjudications):
        raise RequestError(f"{adjudications} does not exist on main")
    context.verify_seed_run(seed)
    return {**blank, "seed_run_id": seed, "findings_path": findings, "findings_ref": ref,
            "adjudications_path": adjudications}


def verify_seed_run(run_id: str, repository: str, get_json: Callable[[str], Any]) -> None:
    """Refuse unless ``run_id`` is, in ``repository``, a COMPLETED run of ``audit-seed.yml`` on main
    (schedule/dispatch) or of ``run-request-execute.yml`` (workflow_run) whose ``seed`` job concluded
    ``success`` and that holds an unexpired ``m9-seed-manifest-<run_id>`` artifact (an artifact is only
    ever uploaded by its own run, so a hand-pushed seed branch has none). ``get_json(path)`` is a GitHub
    REST GET relative to ``/repos/<repository>``."""
    if not is_run_id(run_id):
        raise RequestError(f"seed_run_id {run_id!r} is not a run id")
    artifact = SEED_MANIFEST_ARTIFACT.format(run_id)
    try:
        run = get_json(f"/actions/runs/{run_id}")
        jobs = get_json(f"/actions/runs/{run_id}/jobs?per_page=100")
        artifacts = get_json(f"/actions/runs/{run_id}/artifacts?name={artifact}")
    except Exception as exc:  # noqa: BLE001 -- an unverifiable run is refused, never assumed
        raise RequestError(f"could not read run {run_id} from the GitHub API: {exc}") from exc
    if not isinstance(run, dict) or str(run.get("id")) != run_id:
        raise RequestError(f"run {run_id} was not found")
    owner = (run.get("repository") or {}).get("full_name")
    if not repository or owner != repository:
        raise RequestError(f"run {run_id} belongs to {owner!r}, not {repository!r}")
    path = str(run.get("path") or "").split("@", 1)[0]
    if path not in SEED_WORKFLOWS:
        raise RequestError(f"run {run_id} is a run of {run.get('path')!r}, not of a seeding workflow")
    if run.get("event") not in SEED_WORKFLOWS[path]:
        raise RequestError(f"run {run_id} of {path} was started by {run.get('event')!r}")
    if path.endswith("/audit-seed.yml") and run.get("head_branch") != "main":
        raise RequestError(f"run {run_id} ran on {run.get('head_branch')!r}, not main")
    if run.get("status") != "completed":
        raise RequestError(f"run {run_id} has not completed (status {run.get('status')!r})")
    seed_jobs = [
        job for job in (jobs or {}).get("jobs", []) or []
        if isinstance(job, dict) and (job.get("name") == "seed" or str(job.get("name", "")).endswith("/ seed"))
    ]
    if not any(job.get("conclusion") == "success" for job in seed_jobs):
        raise RequestError(f"run {run_id} has no successful seed job")
    if not any(
        isinstance(a, dict) and a.get("name") == artifact and not a.get("expired")
        for a in (artifacts or {}).get("artifacts", []) or []
    ):
        raise RequestError(f"run {run_id} holds no unexpired {artifact} artifact")


def github_get_json(repository: str, token: str | None, api: str = "https://api.github.com") -> Callable[[str], Any]:
    """A GitHub REST GET relative to ``/repos/<repository>``; the token is sent, never printed."""
    def get(path: str) -> Any:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "run-request-validator"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(f"{api}/repos/{repository}{path}", headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    return get


def validate(
    request: Any,
    registry: list[dict[str, Any]],
    changed: list[str],
    based_on_base: bool,
    context: AuditContext | None = None,
) -> dict[str, str]:
    """The workflow outputs for a valid request; ``RequestError`` naming the first problem otherwise.
    ``context`` is used only by the M9 audit jobs (remote branches, files on main, the seed run)."""
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
    if job == "recertify":
        # Owner ruling R10: re-certify every bundle ref's latest seal under main's code (zero provider
        # calls) and write the passing ones as new seal commits. No target field: it is all seals.
        if set(request) != {"job"}:
            raise RequestError("a recertify request takes no other field (it re-certifies every seal)")
        return {"job": "recertify", "repository": "", "ecosystem": "", "lane": ""}
    if job == "cohort":
        # Owner ruling R37: the override that kicks the autonomous engine once when the cron is late.
        # It runs present.yml's cohort job exactly as the schedule does (authorization gate, one
        # cohort at a time, budget reservation, dispatch); no target field, the planner picks.
        if set(request) != {"job"}:
            raise RequestError("a cohort request takes no other field (the planner picks the cells)")
        return {"job": "cohort", "repository": "", "ecosystem": "", "lane": ""}
    if job in AUDIT_JOBS:
        return _validate_audit(job, request, context)
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
    context = None
    if isinstance(request, dict) and request.get("job") in AUDIT_JOBS:
        context = audit_context(event, remote, base)
    return {**validate(request, registry, changed, based, context), "head_sha": head_sha}


def remote_heads(remote: str = "origin") -> list[str]:
    """Every branch name on ``remote`` (``git ls-remote --heads``), without ``refs/heads/``."""
    listing = _git("ls-remote", "--heads", remote)
    return [line.split("refs/heads/", 1)[1] for line in listing.splitlines() if "refs/heads/" in line]


def audit_context(event: Any, remote: str, base: str) -> AuditContext:
    """The real repository behind ``AuditContext``: branch names from ``git ls-remote``, paths checked
    with ``git cat-file -e`` at ``base`` (main) or at a freshly fetched findings branch (data only,
    nothing checked out), and the seed run through the GitHub API with the executor's read-only token."""
    def exists(ref: str, path: str) -> bool:
        if ".." in path.split("/"):
            return False
        if ref == "main":
            return _git_ok("cat-file", "-e", f"{base}:{path}")
        local = "refs/run-request/findings"
        if not _git_ok("fetch", "--no-tags", "--quiet", remote, f"+refs/heads/{ref}:{local}"):
            return False
        return _git_ok("cat-file", "-e", f"{local}:{path}")

    repository = str((event.get("repository") or {}).get("full_name") or "")
    getter = github_get_json(repository, os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    return AuditContext(
        heads=remote_heads(remote),
        exists=exists,
        verify_seed_run=lambda run_id: verify_seed_run(run_id, repository, getter),
    )


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
