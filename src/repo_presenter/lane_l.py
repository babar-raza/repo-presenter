"""Build the Lane L fact document for one pinned clone: the production form of the facts stage
scripts/run_lane_l.py used to carry inline.

Runs the platform plugin's example verification, then hands everything to the extraction
orchestrator (``readme/evidence/facts/extract.py``), which assembles every fact kind the
renderer and the detectors read. No agent reasoning anywhere in this path. The README is read from the clone itself, so
the facts describe the exact revision the run is pinned to.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.examples import ExampleCandidate, collapse_blank_runs
from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.registry.models import RegistryEntry
from repo_presenter.core.snapshot.capture import RepositorySnapshot
from repo_presenter.core.snapshot.inventory import scan
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.evidence.facts.extract import extract_facts

_FENCE = re.compile(r"^```(?P<lang>\S*)\n(?P<body>.*?)\n```", re.MULTILINE | re.DOTALL)


def select_examples(
    readme_text: str, source_path: str, ecosystem: str
) -> list[ExampleCandidate]:
    """Every fenced block in ``ecosystem``'s own fence languages, once each by normalized body.

    Deliberately simpler than the old repo's ``selection.py``: Lane L's ``failing_example`` and
    ``format_overclaim`` detectors read only ``example``/``format`` facts, not content-unit ids.
    """
    aliases = spec_for(ecosystem).example_fences
    candidates: list[ExampleCandidate] = []
    seen: set[str] = set()
    ordinal = 0
    for match in _FENCE.finditer(readme_text):
        lang = match.group("lang").lower()
        if lang not in aliases:
            continue
        body = match.group("body") + "\n"
        normalized = "\n".join(
            line.rstrip() for line in body.splitlines() if line.strip()
        )
        if not normalized.strip() or normalized in seen:
            continue
        seen.add(normalized)
        ordinal += 1
        start_line = readme_text[: match.start()].count("\n") + 1
        end_line = start_line + body.count("\n") + 1
        candidates.append(
            ExampleCandidate(
                ordinal=ordinal,
                language=lang,
                code=collapse_blank_runs(body),
                source_path=source_path,
                start_line=start_line,
                end_line=end_line,
                unit_id=f"inherited_unit:{ordinal:03d}.code_block",
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
