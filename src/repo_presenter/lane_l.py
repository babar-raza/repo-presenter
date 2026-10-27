"""Build the Lane L fact document for one pinned clone: the production form of the facts stage
scripts/run_lane_l.py used to carry inline.

Runs the platform plugin's example verification, then hands everything to the extraction
orchestrator (``readme/evidence/facts/extract.py``), which assembles every fact kind the
renderer and the detectors read. No agent reasoning anywhere in this path. The README is read from the clone itself, so
the facts describe the exact revision the run is pinned to.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.examples import ExampleCandidate, collapse_blank_runs
from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.core.snapshot.capture import RepositorySnapshot
from repo_presenter.core.snapshot.inventory import scan
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.evidence.facts.extract import extract_facts
from repo_presenter.readme.evidence.facts.inherited import inventory_units

def _fence_parts(source: str) -> tuple[str, str] | None:
    """The info-string language and body of a fenced block, or ``None`` for an indented block."""
    lines = source.splitlines()
    if len(lines) < 2 or not lines[0].startswith(("```", "~~~")):
        return None
    fence = lines[0][:3]
    info = lines[0][3:].strip().split()
    language = info[0].lower() if info else ""
    body = lines[1:-1] if lines[-1].strip().startswith(fence) else lines[1:]
    return language, "\n".join(body) + "\n"


def select_examples(
    readme_text: str, source_path: str, ecosystem: str
) -> list[ExampleCandidate]:
    """Every fenced block in ``ecosystem``'s own fence languages, once each by normalized body.

    Ported (ADAPT) from the old repo's ``extractors/examples/selection.py``: each candidate's
    ``unit_id`` is the README block's own inherited-unit ID (``inventory_units``' block ordinal),
    not the example's ordinal. Reconciliation, planning and the renderer find an example's inherited
    code block through that ID, so an ordinal-numbered ID pointed every example at a different,
    unrelated unit.
    """
    aliases = spec_for(ecosystem).example_fences
    candidates: list[ExampleCandidate] = []
    seen: set[str] = set()
    for unit in inventory_units(readme_text):
        if unit.unit_type != "code_block":
            continue
        parts = _fence_parts(unit.source)
        if parts is None or parts[0] not in aliases or not parts[1].strip():
            continue
        normalized = "\n".join(line.rstrip() for line in parts[1].splitlines() if line.strip())
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(
            ExampleCandidate(
                ordinal=len(candidates) + 1,
                language=parts[0],
                code=collapse_blank_runs(parts[1]),
                source_path=source_path,
                start_line=unit.start_line,
                end_line=unit.end_line,
                unit_id=f"inherited_unit:{unit.ordinal:03d}.code_block",
            )
        )
    return candidates


def tree_paths_of(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    )


def snapshot_of(
    repository: str, root: Path, source_revision: str, tree_paths: list[str]
) -> RepositorySnapshot:
    """The identity of the clone at ``root`` as the extraction orchestrator reads it: the pinned
    revision and where the README, license and notices files are."""
    inventory = scan(root)
    readme = inventory.readme_path
    relative = lambda path: None if path is None else path.relative_to(root).as_posix()
    return RepositorySnapshot(
        repository=repository,
        clone_url=f"https://github.com/{repository}.git",
        source_revision=source_revision,
        tree_sha256=hashlib.sha256("\n".join(tree_paths).encode("utf-8")).hexdigest(),
        tree_entries=len(tree_paths),
        readme_path=relative(readme),
        readme_sha256=hashlib.sha256(readme.read_bytes()).hexdigest()
        if readme
        else None,
        license_path=relative(inventory.license_path),
        notices_path=relative(inventory.notices_path),
    )


def build_lane_l_facts(
    repository: str,
    root: Path,
    ecosystem: str,
    *,
    source_revision: str,
    workspace: Path,
    entry: RegistryEntry,
) -> FactsDocument:
    """Every deterministic fact for the clone at ``root``: ``extract_facts``'s full set (identity,
    manifest and registry reading, surface, examples, formats, license, assets, build and test
    commands, links, product pages, inherited units). ``workspace`` receives example-execution
    scratch files. ``entry`` is the repository's registry entry (family and platform name its
    product pages). Network reads (link checks, registry lookups, product pages) go through
    the seams the extraction modules expose: ``links.fetch_status`` and
    ``published_version._observe``.
    """
    plugin = plugin_for(ecosystem)
    tree_paths = tree_paths_of(root)
    snapshot = snapshot_of(repository, root, source_revision, tree_paths)
    readme_text = (
        (root / snapshot.readme_path).read_bytes().decode("utf-8", errors="replace")
        if snapshot.readme_path is not None
        else ""
    )
    candidates = select_examples(
        readme_text, snapshot.readme_path or "README.md", ecosystem
    )
    workspace.mkdir(parents=True, exist_ok=True)
    receipts = plugin.verify_examples(root, tree_paths, candidates, workspace)
    document, _probes = extract_facts(
        entry,
        snapshot,
        root,
        tree_paths,
        plugin,
        plugin.detect_manifest(root),
        candidates,
        receipts,
        "receipts.json",
    )
    return document
