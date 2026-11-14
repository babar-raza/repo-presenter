"""Lane R's S4 policy switch: inherit-and-correct for aspose.org-published READMEs (R43(3), BL-103).

Owner ruling R43(3) (2026-11-14): for a repository whose live README is aspose.org's published
readme-refresh candidate, Lane R keeps that text by default, leaves out only what the findings
register proves false, and re-writes only what the facts force. The owner's long-run requirement
is recorded with it: Lane R and Lane L stay separate engines whose differences can be evaluated
live. So this is a *policy inside Lane R*, never a call into Lane L's correction engine:

* ``data/aspose_published_readmes.json`` lists the repositories (mapped from aspose.org's own
  ``data/readme_published_state.json``) and names the policy in force (``inherit_and_correct``
  or ``regenerate``);
* ``REPO_PRESENTER_LANE_R_POLICY`` overrides it for one process (a live A/B run of the two
  engines on the same cell);
* the policy that produced a Lane R seal is recorded in its ``dependencies.components.
  lane_r_policy`` (``lane_r_policy_component``), so a policy switch reopens the seal like any
  other component change and per-policy, per-lane counts stay computable from the seals alone.

``reconciliation.dispositions.fold_inherited_published`` is the one place the policy acts.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

LANE_R_POLICY_VERSION = "1"
INHERIT_AND_CORRECT = "inherit_and_correct"
REGENERATE = "regenerate"
POLICIES = frozenset({INHERIT_AND_CORRECT, REGENERATE})
POLICY_ENV = "REPO_PRESENTER_LANE_R_POLICY"
PUBLISHED_READMES_PATH = Path("data/aspose_published_readmes.json")
_REPO_ROOT = Path(__file__).resolve().parents[4]


def _mapping_path() -> Path:
    if PUBLISHED_READMES_PATH.is_file():
        return PUBLISHED_READMES_PATH
    return _REPO_ROOT / PUBLISHED_READMES_PATH


@lru_cache(maxsize=4)
def _load(path: str) -> tuple[str, frozenset[str]]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return REGENERATE, frozenset()
    policy = str(document.get("policy") or REGENERATE)
    if policy not in POLICIES:
        policy = REGENERATE
    repositories = frozenset(
        str(row.get("repository", "")).casefold()
        for row in document.get("repositories") or ()
        if isinstance(row, dict) and row.get("repository")
    )
    return policy, repositories


def published_repositories() -> frozenset[str]:
    """The repositories (case-folded) whose live README is an aspose.org-published candidate."""
    return _load(str(_mapping_path()))[1]


def configured_policy() -> str:
    """The policy in force for the listed repositories: the environment override, else the file."""
    override = os.environ.get(POLICY_ENV, "").strip()
    if override in POLICIES:
        return override
    return _load(str(_mapping_path()))[0]


def lane_r_policy(repository: str) -> str:
    """``inherit_and_correct`` for a listed repository while that policy is in force, else
    ``regenerate``."""
    if str(repository).casefold() not in published_repositories():
        return REGENERATE
    return configured_policy()


def inherits(repository: str) -> bool:
    return lane_r_policy(repository) == INHERIT_AND_CORRECT


def lane_r_policy_component(repository: str) -> str:
    """The value a Lane R seal records under ``dependencies.components.lane_r_policy``."""
    return f"{lane_r_policy(repository)}.{LANE_R_POLICY_VERSION}"
