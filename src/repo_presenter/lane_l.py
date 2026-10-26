"""Build the Lane L fact document for one pinned clone: the production form of the facts stage
scripts/run_lane_l.py used to carry inline.

Wires only what Lane L's detectors read -- manifest, surface, registry, example, and format facts --
from the ported platform extractor, the shared fact model, and the example/format evidence
converters. No agent reasoning anywhere in this path. The README is read from the clone itself, so
the facts describe the exact revision the run is pinned to.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_presenter.core.ecosystems import spec_for
from repo_presenter.core.examples import ExampleCandidate, collapse_blank_runs
from repo_presenter.core.facts import Evidence, Fact, FactsDocument, fact_id
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.evidence.facts.examples import example_facts
from repo_presenter.readme.evidence.facts.formats import format_facts

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


def build_lane_l_facts(
    repository: str,
    root: Path,
    ecosystem: str,
    *,
    source_revision: str,
    workspace: Path,
) -> FactsDocument:
    """Facts for the clone at ``root``. ``workspace`` receives example-execution scratch files."""
    plugin = plugin_for(ecosystem)
    tree_paths = tree_paths_of(root)
    readme_text = (root / "README.md").read_bytes().decode("utf-8", errors="replace")
    manifest = plugin.detect_manifest(root)
    identity = Fact(
        fact_id("identity", "repository"),
        "identity",
        repository,
        (Evidence("data/registry.json", "admitted registry entry"),),
    )
    facts: list[Fact] = [identity]
    if manifest is not None:
        manifest_facts = plugin.manifest_facts(root, manifest, tree_paths)
        registry_resolved, _probes = plugin.registry_facts([identity, *manifest_facts])
        resolved_by_id = {f.id: f for f in registry_resolved}
        facts.extend(resolved_by_id.get(f.id, f) for f in manifest_facts)
    facts.extend(plugin.surface_facts(root, tree_paths))
    candidates = select_examples(readme_text, "README.md", ecosystem)
    workspace.mkdir(parents=True, exist_ok=True)
    receipts = plugin.verify_examples(root, tree_paths, candidates, workspace)
    facts.extend(example_facts(candidates, receipts, "receipts.json"))
    facts.extend(
        format_facts(
            candidates,
            receipts,
            plugin.format_claims,
            "receipts.json",
            plugin.format_declarations(root, tree_paths),
        )
    )
    return FactsDocument(
        repository=repository, source_revision=source_revision, facts=tuple(facts)
    )
