"""The R17 sandbox target (owner decision 2026-11-22: the sandbox is ``babar-raza/repo-presenter`` itself).

One repository variable, ``REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY``, names the sandbox. This module is the
single reader of it for every effect that honours the sandbox: the propose driver (``propose/run.py``), the
sandbox write path (``propose/sandbox.py``) and the issue writes (``issues/*``). Rules, all fail closed:

* the variable must name the exact repository in ``data/sandbox_write_target.json`` (case-insensitive);
* unset, empty, any other repository, or the wildcard ``*`` selects no sandbox (``*`` is the owner's lift of the
  per-target restriction for upstream pull requests and is NEVER a sandbox exemption from R15);
* the data file must be well formed; a missing or malformed file selects no sandbox.

The sandbox entry is deliberately a separate file from ``data/upstream_write_allowlist.json`` (R22: the nine
allowlisted repositories stay the only upstream pull-request targets).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SANDBOX_TARGET_FILE = REPO_ROOT / "data" / "sandbox_write_target.json"
SANDBOX_VARIABLE = "REPO_PRESENTER_PROPOSE_SANDBOX_REPOSITORY"
SANDBOX_LIFTED = "*"
_REPOSITORY = re.compile(r"[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}/[A-Za-z0-9._][A-Za-z0-9._-]{0,99}")


class SandboxConfigError(Exception):
    """The sandbox data file is missing or malformed: no sandbox exists."""


@dataclass(frozen=True)
class SandboxEntry:
    repository: str
    effects: frozenset[str]
    first_pr_as_draft: bool
    branch_prefix: str
    path_template: str

    def readme_path(self, candidate_repository: str) -> str:
        owner, name = candidate_repository.split("/", 1)
        return self.path_template.format(owner=owner, name=name)


def load_sandbox_entry(path: Path = SANDBOX_TARGET_FILE) -> SandboxEntry:
    def bad(why: str) -> SandboxConfigError:
        return SandboxConfigError(f"sandbox target file {path.name} {why}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise bad("is missing") from None
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise bad(f"is unreadable ({type(exc).__name__})") from None
    entry = data.get("sandbox") if isinstance(data, dict) and data.get("schema_version") == 1 else None
    if not isinstance(entry, dict):
        raise bad("has no schema_version 1 'sandbox' object")
    repository = entry.get("repository")
    effects = entry.get("effects")
    prefix = entry.get("sandbox_branch_prefix")
    template = entry.get("sandbox_path_template")
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise bad("has an invalid repository")
    if not isinstance(effects, list) or not effects or not all(e in {"pull_request", "issue", "issue_comment"} for e in effects):
        raise bad("has invalid effects")
    if entry.get("first_pr_as_draft") is not True:
        raise bad("must keep first_pr_as_draft true")
    if not isinstance(prefix, str) or not prefix.startswith("repository-presenter/") or not prefix.endswith("/"):
        raise bad("has an invalid sandbox_branch_prefix")
    if (
        not isinstance(template, str)
        or not template.startswith("sandbox/")
        or ".." in template
        or template.count("{owner}") != 1
        or template.count("{name}") != 1
        or template.lower() == "readme.md"
    ):
        raise bad("has an invalid sandbox_path_template (must stay under sandbox/)")
    return SandboxEntry(repository, frozenset(effects), True, prefix, template)


def sandbox_repository(environment: Mapping[str, str], path: Path = SANDBOX_TARGET_FILE) -> str | None:
    """The sandbox repository the variable selects, or ``None``. Never the wildcard."""
    value = environment.get(SANDBOX_VARIABLE, "").strip()
    if not value or value == SANDBOX_LIFTED or "*" in value:
        return None
    try:
        entry = load_sandbox_entry(path)
    except SandboxConfigError:
        return None
    return entry.repository if value.lower() == entry.repository.lower() else None


def names_sandbox(repository: str, environment: Mapping[str, str], path: Path = SANDBOX_TARGET_FILE) -> bool:
    """``True`` only when the variable selects the sandbox AND ``repository`` is exactly it."""
    chosen = sandbox_repository(environment, path)
    return chosen is not None and repository.strip().lower() == chosen.lower()


def issue_write_refusal(repository: str, environment: Mapping[str, str]) -> str | None:
    """Why an issue write on ``repository`` is refused by the owner's 'sandbox only' authorisation
    (2026-11-22), or ``None`` when ``repository`` is the sandbox the variable names."""
    if names_sandbox(repository, environment):
        return None
    return (
        f"issue writes are authorised for the sandbox only: {SANDBOX_VARIABLE} must name "
        f"{repository} exactly (it is {environment.get(SANDBOX_VARIABLE, '').strip() or 'not set'!r}; "
        "the wildcard never applies, and no upstream repository is cleared)"
    )
