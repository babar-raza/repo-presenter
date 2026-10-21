"""The Node.js platform plugin: identity from `package.json`, surface from the package entry point.

A pure-JavaScript npm package - no `.ts` anywhere - is the TypeScript case without the types. It
has no `public` at module scope either, so the surface is the tree's symbols filtered by what the
entry point the manifest declares exports: `export { A } from './a.js'`, `export * from`, a local
`export { A }`, or the CommonJS forms `module.exports = { A, B }`, `exports.A = ...` and
`module.exports = require('./x')`. Descriptions are the JSDoc blocks the extractor reads before
each declaration.

Nothing here parses JavaScript or reads a registry itself. The `SurfaceExtractor`, manifest and
`RegistryProbe` facades do that for every ecosystem, and `surface/npm_package.py` holds everything
an npm package shares whatever its language - manifest facts, the entry point, the re-export
closure and the name-and-module filter - composed here with the JavaScript `ModuleDialect`
(`.js`/`.mjs`/`.cjs`, CommonJS read). This module never imports the TypeScript plugin, and the
TypeScript plugin never imports this one.

The grammar is TypeScript's: its wheel parses JavaScript as a subset, so no second grammar is
pinned for a language the same tree-sitter package already reads.

Ported (REUSE, near-verbatim) from the old repository-presenter project's ``nodejs.py``.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repo_presenter.extractors.platforms.nodejs_examples import (
    verify_nodejs_build,
    verify_nodejs_examples,
)
from repo_presenter.extractors.surface import npm_package
from repo_presenter.extractors.surface.extractor import surface_symbols
from repo_presenter.extractors.surface.npm_package import (
    JAVASCRIPT_MODULES,
)
from repo_presenter.extractors.surface.registry import (
    observe,
    repository_of,
)
from repo_presenter.core.ecosystems import SPECS, EcosystemSpec, SuiteFileRule
from repo_presenter.core.examples import (
    ExampleCandidate,
    ExampleReceipt,
    FormatClaim,
    FormatDeclaration,
    MeasuredBuild,
)
from repo_presenter.core.facts import Evidence, Fact
from repo_presenter.core.grammars import get_parser
from repo_presenter.core.probes import ProbeRecord

NODEJS = EcosystemSpec(
    ecosystem="nodejs",
    language="JavaScript",
    fence="javascript",
    registry="npm",
    install_fact_id="install_command:npm",
    version_badge=(
        "[![npm](https://img.shields.io/npm/v/{package}.svg)](https://www.npmjs.com/package/"
        "{package})"
    ),
    source_dependencies="npm install",
    verify_command="npm ls {module}",
    example_timeout_seconds=120.0,
    install_timeout_seconds=300.0,
    fence_aliases=frozenset({"javascript", "js", "mjs", "cjs", "node", "nodejs"}),
    floor_fact_id="package:node_engine",
    floor_label="Node.js",
    floor_declaration="engines.node",
    floor_is_minimum=True,
    manifest_globs=("package.json",),
    source_suffixes=frozenset({".js", ".mjs", ".cjs"}),
    suite_files=SuiteFileRule(name=r"(?:[._-](?:test|spec)\.[cm]?jsx?$|^test-.+\.[cm]?jsx?$)"),
)
SPECS.setdefault(NODEJS.ecosystem, NODEJS)

_GRAMMAR = "typescript"
_ENGINE_LANGUAGE = "javascript"


class NodeJsPlugin:
    """What the facts stage asks of a pure-JavaScript npm package."""

    ecosystem = NODEJS.ecosystem
    manifest_globs = NODEJS.manifest_globs
    source_suffixes = NODEJS.source_suffixes

    def detect_manifest(self, root: Path) -> Path | None:
        """The `package.json` that governs the package."""
        return npm_package.detect_manifest(
            root, self.manifest_globs, JAVASCRIPT_MODULES.config_names
        )

    def manifest_facts(self, root: Path, manifest: Path, tree_paths: list[str]) -> list[Fact]:
        """Identity, version, the declared Node engine, and the install command it implies."""
        return npm_package.manifest_facts(self.ecosystem, root, manifest)

    def entry_barrel(self, package: Path) -> Path | None:
        """The source file that is the package's public entry point, or None when it has none."""
        return npm_package.entry_barrel(package, JAVASCRIPT_MODULES)

    def surface_facts(self, root: Path, tree_paths: list[str]) -> list[Fact]:
        """The symbols the package's entry point exports, read from the tree by the extractor."""
        manifest = self.detect_manifest(root)
        package = manifest.parent if manifest is not None else root
        barrel = self.entry_barrel(package)
        if barrel is None:
            return []
        symbols = surface_symbols(
            get_parser(_GRAMMAR), _ENGINE_LANGUAGE, barrel.parent, root, self.ecosystem
        )
        return npm_package.public_symbol_facts(root, barrel, symbols, JAVASCRIPT_MODULES)

    def registry_facts(self, facts: Sequence[Fact]) -> tuple[list[Fact], list[ProbeRecord]]:
        """Resolve the install claim against npm; the fact keeps its ID and gains evidence."""
        by_id = {fact.id: fact for fact in facts}
        install = by_id.get(NODEJS.install_fact_id)
        name = by_id.get("package:name")
        if install is None or name is None:
            return [], []
        reading = observe(self.ecosystem, name.value, repository=repository_of(facts))
        polarity, confidence, detail = reading.install_verdict()
        resolved = Fact(
            install.id,
            install.kind,
            install.value,
            (
                *install.evidence,
                Evidence(reading.evidence_url or reading.registry, detail),
            ),
            polarity=polarity,
            confidence=confidence,
        )
        probe = ProbeRecord(
            kind="registry",
            target=f"{reading.registry}:{name.value}",
            outcome=polarity,
            status=None,
            elapsed_ms=0,
            observation=reading.method or reading.source,
        )
        return [resolved], [probe]

    def verify_examples(
        self,
        root: Path,
        tree_paths: list[str],
        candidates: Sequence[ExampleCandidate],
        workspace: Path,
    ) -> list[ExampleReceipt]:
        """Check each candidate's syntax and its imports of the package, in a disposable copy."""
        manifest = self.detect_manifest(root)
        package = manifest.parent if manifest is not None else root
        return verify_nodejs_examples(
            package,
            self.entry_barrel(package),
            candidates,
            workspace,
            NODEJS.example_timeout_seconds,
            NODEJS.install_timeout_seconds,
        )

    def verify_build(self, root: Path, manifest: Path, workspace: Path) -> MeasuredBuild:
        """The package's own `npm install` (and `npm run build`, if declared), with no example."""
        return verify_nodejs_build(manifest.parent, workspace, NODEJS.install_timeout_seconds)

    def format_claims(self, code: str) -> Sequence[FormatClaim]:
        """Not built; a claim this plugin cannot read is no claim at all."""
        return []

    def format_declarations(self, root: Path, tree_paths: list[str]) -> Sequence[FormatDeclaration]:
        """Not built; a format declaration this plugin cannot read is no declaration at all."""
        return []


PLUGIN: Any = NodeJsPlugin()
