"""The version set: one fingerprint of every *mechanism* a sealed candidate was produced under.

Owner rules (2026-11-06, binding; the two predecessor projects were abandoned over violating them):

1. ONE version set for every candidate that counts. A release set never mixes candidates produced
   under different version sets: prompts (name, version, sha256, model route), reviewer logic,
   renderer / shell / normalisation, correction engine, detectors, and any future contract or
   acceptance-profile version a seal records.
2. A version bump must NEVER invalidate a sealed candidate. A seal is an immutable record of what
   was produced under its version set; a later failed run under a NEW set never demotes it.

The fingerprint is computed from a sealed bundle's own ``dependencies.json`` (what that seal
consumed) and, by the very same function, from the dependencies record a seal made NOW would write
(``readme.bundle.seal.current_dependencies_document``) -- so "the current version set" can never
drift from what current code actually seals.

What is IN the mechanism scope: every top-level key of the dependencies record except the
per-repository inputs, plus the lane. Default-include on purpose: a mechanism key a future seal
adds (``validators``, ``acceptance_profile_version``, ``policy`` ...) joins the fingerprint without
anyone remembering to list it here.

What is OUT: ``source`` (the pinned revision and, for Lane L, the live README's bytes) and
``facts`` (the extracted fact records) -- per-repository inputs, not mechanisms -- and the
machine half of ``environment`` (Python version, OS, resolved toolchains), which describes the
host a run happened on, not the code that produced the candidate. ``environment``'s one code
version, ``inherited_units_version`` (this codebase's inherited-unit inventory), IS a mechanism
and stays in.

Each lane has its own consumed scope (Lane R never ran a detector; Lane L never ran the renderer),
so each lane has its own fingerprint, and a lane's fingerprint always carries the lane itself: the
two lanes' sets can never collide.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

#: Top-level dependencies-record keys that are per-repository inputs, never mechanisms.
INPUT_KEYS = frozenset({"source", "facts"})
#: The one ``environment`` field that is a code version rather than a fact about the machine.
ENVIRONMENT_MECHANISM_KEYS = frozenset({"inherited_units_version"})
#: Short display length of a fingerprint (the full sha256 is what is compared).
SHORT = 12


def mechanism_scope(dependencies: Mapping[str, Any], lane: str) -> dict[str, Any]:
    """The mechanism half of one dependencies record, plus the lane. Pure."""
    if not isinstance(dependencies, Mapping):
        raise ValueError("a dependencies record must be a JSON object")
    scope: dict[str, Any] = {"lane": lane}
    for key, value in dependencies.items():
        if key in INPUT_KEYS or key == "lane":
            continue
        if key == "environment":
            if isinstance(value, Mapping):
                kept = {k: value[k] for k in sorted(value) if k in ENVIRONMENT_MECHANISM_KEYS}
                if kept:
                    scope["environment"] = kept
            continue
        scope[key] = value
    return scope


def fingerprint_scope(scope: Mapping[str, Any]) -> str:
    """sha256 over the canonical JSON of a mechanism scope."""
    canonical = json.dumps(scope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def fingerprint(dependencies: Mapping[str, Any], lane: str) -> str:
    """The version-set fingerprint of a sealed bundle's ``dependencies.json``."""
    return fingerprint_scope(mechanism_scope(dependencies, lane))


def short(value: str | None) -> str:
    return "-" if not value else value[:SHORT]


def current_dependencies(lane: str, prompts: Any) -> dict[str, Any]:
    """The dependencies record a seal made NOW, in ``lane``, would write, with neutral placeholder
    per-repository inputs (an empty fact set, a placeholder revision and live README). The
    placeholders only fill keys :func:`mechanism_scope` drops, so they never reach the
    fingerprint. Built through ``seal.current_dependencies_document`` itself, never a copy of it."""
    from repo_presenter.core.facts import FactsDocument
    from repo_presenter.readme.bundle.seal import current_dependencies_document

    revision = "0" * 40
    return current_dependencies_document(
        lane=lane,
        source_revision=revision,
        facts=FactsDocument(repository="version-set/placeholder", source_revision=revision, facts=()),
        prompts=prompts,
        original_readme=b"",
    )


def current_fingerprint(lane: str, prompts: Any) -> str:
    """The fingerprint a seal made by current code, in ``lane``, would carry. ``prompts`` is a
    ``PromptRegistry`` (``core.llm.prompts.load_manifests``)."""
    return fingerprint(current_dependencies(lane, prompts), lane)


def current_fingerprints(prompts_dir: Path, lanes: Iterable[str] = ("R", "L")) -> dict[str, str]:
    """``{lane: current fingerprint}`` from the committed prompt manifests in ``prompts_dir``."""
    from repo_presenter.core.llm.prompts import load_manifests

    prompts = load_manifests(prompts_dir)
    return {lane: current_fingerprint(lane, prompts) for lane in lanes}


def group_by_fingerprint(
    counted: Iterable[tuple[str, str | None]],
) -> dict[str | None, list[str]]:
    """``(repository, fingerprint)`` pairs -> ``{fingerprint: sorted distinct repositories}``.
    A repository appears once per fingerprint it has a counted seal under, and the groups are
    NEVER summed: each is its own version set."""
    groups: dict[str | None, set[str]] = {}
    for repository, value in counted:
        groups.setdefault(value, set()).add(repository)
    return {key: sorted(repos) for key, repos in groups.items()}


def version_set_report(
    groups: Mapping[str | None, Iterable[str]], current: str | None
) -> dict[str, Any]:
    """The per-lane version-set report: the CURRENT fingerprint's count (the only set that can
    form a release set) and every older fingerprint's count, separately. No cross-set total."""
    current_repos = sorted(groups.get(current, ())) if current else []
    older = {
        short(key) if key else "unreadable": len(list(repos))
        for key, repos in sorted(groups.items(), key=lambda item: item[0] or "")
        if key != current
    }
    return {
        "current_version_set": short(current),
        "current_count": len(current_repos),
        "current_repositories": current_repos,
        "older_version_sets": older,
    }
