"""A called workflow's permissions may never exceed its caller job's: GitHub refuses the whole calling
file at startup otherwise (run-request-execute.yml startup_failure, 2026-11-13, after present.yml gained
the schedule-only `cohort` job with actions: write). Checked statically for every local `uses:` call,
recursively, against both the called file's top-level and every job's own permissions."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
LEVEL = {"none": 0, "read": 1, "write": 2}


def _perms(block: object) -> dict[str, int]:
    if block in (None, {}):
        return {}
    if isinstance(block, str):  # read-all / write-all
        return {"*": LEVEL["write" if block == "write-all" else "read"]}
    return {k: LEVEL[str(v)] for k, v in dict(block).items()}


def _needed(path: Path, seen: frozenset[str] = frozenset()) -> dict[str, int]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    need = dict(_perms(doc.get("permissions")))
    for job in (doc.get("jobs") or {}).values():
        for key, level in _perms(job.get("permissions")).items():
            need[key] = max(need.get(key, 0), level)
        uses = str(job.get("uses") or "")
        if uses.startswith("./.github/workflows/") and uses not in seen:
            for key, level in _needed(WORKFLOWS / Path(uses).name, seen | {uses}).items():
                need[key] = max(need.get(key, 0), level)
    return need


def _calls() -> list[tuple[str, str, dict[str, int]]]:
    found = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        top = _perms(doc.get("permissions"))
        for name, job in (doc.get("jobs") or {}).items():
            uses = str(job.get("uses") or "")
            if uses.startswith("./.github/workflows/"):
                granted = _perms(job["permissions"]) if "permissions" in job else top
                found.append((f"{path.name}:{name}", uses, granted))
    return found


def test_there_are_local_reusable_calls_to_check() -> None:
    assert any(uses.endswith("present.yml") for _, uses, _ in _calls())


def test_every_caller_job_grants_what_its_called_workflow_needs() -> None:
    problems = []
    for caller, uses, granted in _calls():
        need = _needed(WORKFLOWS / Path(uses).name, frozenset({uses}))
        for key, level in need.items():
            if granted.get(key, granted.get("*", 0)) < level:
                problems.append(f"{caller} -> {uses}: needs {key}={level}, grants {granted.get(key, 0)}")
    assert not problems, problems
