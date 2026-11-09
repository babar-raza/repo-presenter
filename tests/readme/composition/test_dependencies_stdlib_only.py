"""A repository with no dependency manifest still gets a Dependencies section when a SUPPORTED
`package_trait:stdlib_only.*` fact states it (R2 floor: the published aspose.org README prints a
Dependencies section for Aspose.PSD-FOSS-for-Python). Real values: the fact id/value/evidence are
the ones the Python extractor emitted for PSD Python (stored run, 2026-11-10)."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.renderer import RenderContext, _dependencies

REPOSITORY = "aspose-psd-foss/Aspose.PSD-FOSS-for-Python"
REGISTRY = load_registry(Path(__file__).resolve().parents[3] / "data" / "registry.json")

STDLIB = Fact(
    "package_trait:stdlib_only.python", "package_trait",  # type: ignore[arg-type]
    "imports only the Python standard library and the package's own modules",
    (Evidence("src/aspose_psd_foss", None),),
)


def _context(*facts: Fact) -> RenderContext:
    entry = next(e for e in REGISTRY.entries if e.repository == REPOSITORY)
    plugin_for(entry.ecosystem)
    return RenderContext(
        entry, FactsDocument(REPOSITORY, "0" * 40, tuple(facts)),
        {"sections": []}, {"units": []}, {"dispositions": []},
    )


def test_a_stdlib_only_fact_alone_renders_the_required_dependencies_statement() -> None:
    lines = _dependencies(_context(STDLIB))
    assert lines[0] == "### Required Package Dependencies"
    assert (
        "No required third-party package dependencies: the package imports only the Python "
        "standard library and the package's own modules (`src/aspose_psd_foss`)."
    ) in lines


def test_nothing_is_printed_without_that_supported_fact() -> None:
    assert _dependencies(_context()) == []
    unresolved = Fact(STDLIB.id, "package_trait", STDLIB.value, STDLIB.evidence, polarity="UNRESOLVED")  # type: ignore[arg-type]
    assert _dependencies(_context(unresolved)) == []


def test_a_declared_dependency_marker_still_wins_over_the_trait() -> None:
    marker = Fact(
        "dependency:none", "dependency", "none",  # type: ignore[arg-type]
        (Evidence("requirements.txt", "the manifest declares none"),),
    )
    lines = _dependencies(_context(STDLIB, marker))
    assert any("in `requirements.txt`, the manifest declares none" in line for line in lines)
    assert not any("standard library" in line for line in lines)
