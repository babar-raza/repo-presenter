"""A complete real candidate, re-derived offline from a cascade output directory (plan D9 V4).

``load_cascade_candidate`` reads the artifacts a cascade run leaves (``plan.json``,
``content_units.coherent.json``, the composed dispositions, ``investigation.json``, the merged
``facts.json`` and the cloned ``README.md``), re-renders the README, re-runs the S9 accounting and
the ported blocking checks exactly as ``cascade._compose`` / ``_settle_s9`` do, and returns the
``SourceCandidate`` a reviewer is asked about. No provider call is made.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from repo_presenter.core.facts import FactsDocument, read_facts
from repo_presenter.core.registry.loader import load_registry, require_listed
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.readme.composition.authoring import SectionTask, authoring_tasks
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.evidence.facts.inherited import inherited_unit_facts
from repo_presenter.readme.repair.accounting import account_unprinted_units
from repo_presenter.readme.validation.blocking import validate_candidate
from repo_presenter.readme.validation.failures import Candidate

DEFAULT_REGISTRY_PATH = Path("data/registry.json")
_REMOTE = re.compile(
    r"url\s*=\s*https://github\.com/([^/\s]+/[^\s]+?)(?:\.git)?\s*$", re.MULTILINE
)


@dataclass(frozen=True)
class SourceCandidate:
    """One candidate README with everything a reviewer packet is built from."""

    name: str
    entry: RegistryEntry
    repository: str
    ecosystem: str
    readme: str
    original: str
    facts: FactsDocument
    plan: dict[str, Any]
    units: dict[str, Any]
    dispositions: dict[str, Any]
    validation: dict[str, Any]
    tree_paths: tuple[str, ...]
    tasks: tuple[SectionTask, ...]
    scratch: Path


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clone_repository(clone: Path) -> str:
    """``owner/name`` of the cloned repository, from its ``origin`` URL."""
    match = _REMOTE.search((clone / ".git" / "config").read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"no GitHub origin URL in {clone / '.git' / 'config'}")
    return match.group(1)


def _tree_paths(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    )


def merge_inherited_units(base: FactsDocument, clone: Path) -> FactsDocument:
    """``base`` with the inherited-unit facts of the clone's README, as ``cascade`` merges them."""
    readme_bytes = (clone / "README.md").read_bytes()
    public_symbols = [fact for fact in base.facts if fact.kind == "public_symbol"]
    inherited = inherited_unit_facts(
        "README.md", readme_bytes, public_symbols, _tree_paths(clone)
    )
    kept = tuple(fact for fact in base.facts if fact.kind != "inherited_unit")
    return FactsDocument(base.repository, base.source_revision, (*kept, *inherited))


def blocking_check(source: SourceCandidate, readme: str) -> dict[str, Any]:
    """The ported blocking checks (S9) run over ``readme`` as ``source``'s candidate README."""
    return validate_candidate(
        _candidate(source, readme, source.dispositions), source.scratch, []
    )


def _candidate(
    source: SourceCandidate, readme: str, dispositions: dict[str, Any]
) -> Candidate:
    return Candidate(
        entry=source.entry,
        facts=source.facts,
        plan=source.plan,
        units=source.units,
        dispositions=dispositions,
        readme=readme,
        original_readme=None,
        source_revision=source.facts.source_revision,
        readme_sha256=None,
        tree_paths=source.tree_paths,
        tasks=source.tasks,
    )


def build_source(
    *,
    name: str,
    entry: RegistryEntry,
    facts: FactsDocument,
    plan: dict[str, Any],
    units: dict[str, Any],
    dispositions: dict[str, Any],
    investigation: dict[str, Any],
    original: str,
    tree_paths: list[str],
    scratch: Path,
    recorded_readme: str | None = None,
) -> SourceCandidate:
    """Render ``units`` and account the unprinted kept units exactly as ``cascade._compose`` does,
    then record the S9 validation of the result.

    ``recorded_readme`` is a candidate README kept on record as it was written (an old defect
    that today's renderer no longer reproduces, or an ecosystem it cannot render): it is used
    as it is, with no rendering, no accounting and no S9 validation (``validation`` is empty)."""
    if recorded_readme is not None:
        return SourceCandidate(
            name=name,
            entry=entry,
            repository=entry.repository,
            ecosystem=entry.ecosystem,
            readme=recorded_readme,
            original=original,
            facts=facts,
            plan=plan,
            units=units,
            dispositions=dispositions,
            validation={"summary": {}, "checks": []},
            tree_paths=tuple(tree_paths),
            tasks=(),
            scratch=scratch,
        )
    tasks = authoring_tasks(entry, facts, investigation, dispositions, plan)
    readme = render_readme(entry, facts, plan, units, dispositions)
    bare = SourceCandidate(
        name=name,
        entry=entry,
        repository=entry.repository,
        ecosystem=entry.ecosystem,
        readme=readme,
        original=original,
        facts=facts,
        plan=plan,
        units=units,
        dispositions=dispositions,
        validation={},
        tree_paths=tuple(tree_paths),
        tasks=tuple(tasks),
        scratch=scratch,
    )
    settled, accounted = account_unprinted_units(_candidate(bare, readme, dispositions))
    if accounted and render_readme(entry, facts, plan, units, settled) == readme:
        bare = replace(bare, dispositions=settled)
    return replace(bare, validation=blocking_check(bare, readme))


def load_cascade_candidate(
    work: Path, *, name: str, registry_path: Path = DEFAULT_REGISTRY_PATH
) -> SourceCandidate:
    """The candidate of the cascade run whose ``.present-work`` directory is ``work``."""
    cascade, clone = work / "cascade", work / "clone"
    repository = clone_repository(clone)
    entry = require_listed(load_registry(registry_path), repository)
    composed = cascade / "dispositions.composed.json"
    return build_source(
        name=name,
        entry=entry,
        facts=read_facts(work / "facts.json"),
        plan=_json(cascade / "plan.json"),
        units=_json(cascade / "content_units.coherent.json"),
        dispositions=_json(
            composed if composed.exists() else cascade / "dispositions.json"
        ),
        investigation=_json(cascade / "investigation.json"),
        original=(clone / "README.md").read_bytes().decode("utf-8", errors="replace"),
        tree_paths=_tree_paths(clone),
        scratch=cascade,
    )


def load_lane_r_candidate(
    output: Path,
    *,
    facts_path: Path,
    clone: Path,
    name: str,
    recorded: bool = False,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> SourceCandidate:
    """A candidate from the per-script Lane R outputs (``scripts/_lane_r_output/<repo>``), with
    the Lane L facts of the same repository and a clone supplying the live README and file tree.
    ``recorded`` takes the output's own ``README.coherent.md`` as it was written."""
    repository = clone_repository(clone)
    entry = require_listed(load_registry(registry_path), repository)
    return build_source(
        name=name,
        entry=entry,
        facts=merge_inherited_units(read_facts(facts_path), clone),
        plan=_json(output / "plan.json"),
        units=_json(output / "content_units.coherent.json"),
        dispositions=_json(output / "dispositions.json"),
        investigation=_json(output / "investigation.json"),
        original=(clone / "README.md").read_bytes().decode("utf-8", errors="replace"),
        tree_paths=_tree_paths(clone),
        scratch=output,
        recorded_readme=(
            (output / "README.coherent.md").read_text(encoding="utf-8")
            if recorded
            else None
        ),
    )
