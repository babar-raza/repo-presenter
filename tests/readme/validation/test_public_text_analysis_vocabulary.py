"""BL-002 (owner feedback 2026-11-13, P0): no README prints the pipeline's evidence/analysis wording.

Real data: the two sealed Lane R lines that printed an install fact's evidence detail verbatim
(3D Python @ 65b1f577c0f1, Email C++), copied from their bundle READMEs; and the preserved maintainer
lines from sealed Lane L READMEs that use the English words "fact" / "evidence" / "unreachable"
legitimately and must keep passing. The check is BC-07 (``validation/public_text.py``, next to the
R9 attribution check); the renderer no longer produces the sentence (``composition/renderer.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.extractors.platforms.registry import plugin_for
from repo_presenter.readme.composition.renderer import RenderContext, _installation
from repo_presenter.readme.validation.public_text import analysis_markers

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = load_registry(ROOT / "data" / "registry.json")

SEALED_LEAKS = (
    # aspose-3d-foss/Aspose.3D-FOSS-for-Python Lane R, README.md line 64.
    (
        "The package `aspose-3d-foss` could not be confirmed on PyPI (package registry: a "
        "distribution of this name exists, but ownership not confirmed: the registry's project "
        "URLs point at another repository)."
    ),
    # aspose-email-foss/Aspose.Email-FOSS-for-Cpp Lane R, README.md line 66.
    (
        "The package `AsposeEmailFoss` could not be confirmed on any package registry (package "
        "registry: none could not be read)."
    ),
)
MAINTAINER_PROSE = (
    # Font Python Lane L, Aspose-PDF Go/Python Lane L, PDF Java Lane R, PDF Python Lane L.
    "├── stat-evidence.json                           (STAT policy decisions & diagnostics)",
    "# QA evidence report generation",
    "  `ValidationOptions`) and embedding that evidence as a `/DSS` with `AddValidationInfo`, so the",
    "  itself, not marked content), `Document.AutoTag()` tags a PDF made elsewhere after the fact",
    "| `WidgetFieldInfo` | Resolves the interactive-field facts of a Widget annotation dictionary. |",
    "- `Document.optimize()` (aliased `optimize_resources()`) removes unreachable objects,",
    "Formats marked unsupported are listed below.",
)


@pytest.mark.parametrize("line", SEALED_LEAKS)
def test_the_sealed_leaks_fail(line: str) -> None:
    assert analysis_markers(f"## Installation\n\n{line}\n") != []


@pytest.mark.parametrize(
    "line",
    [
        "Install it (fact id install_command:pip).",
        "The install is SUPPORTED by the registry.",
        "This claim is UNRESOLVED.",
        "See facts.json for details.",
        "package registry unreachable: ConnectError",
        "The registry's project URLs point at another repository.",
        "The registry answered ambiguously.",
    ],
)
def test_internal_vocabulary_fails(line: str) -> None:
    assert analysis_markers(line) != []


@pytest.mark.parametrize("line", MAINTAINER_PROSE)
def test_maintainer_prose_with_plain_english_words_passes(line: str) -> None:
    assert analysis_markers(line) == []


def test_code_fences_are_not_prose() -> None:
    readme = "## Usage\n\n```python\nstatus = Result.SUPPORTED  # package registry: x\n```\n"
    assert analysis_markers(readme) == []


def _context(repository: str, *facts: Fact) -> RenderContext:
    entry = next(e for e in REGISTRY.entries if e.repository == repository)
    plugin_for(entry.ecosystem)
    return RenderContext(
        entry,
        FactsDocument(repository, "0" * 40, tuple(facts)),
        {"sections": []},
        {"units": []},
        {"dispositions": []},
    )


PYTHON = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
PACKAGE = Fact(
    "package:name", "package", "aspose-3d-foss",
    (Evidence("setup.py", "distribution name declared by the manifest"),),
)


def _install(detail: str, polarity: str) -> Fact:
    return Fact(
        "install_command:pip", "install_command", "pip install aspose-3d-foss",
        (
            Evidence("setup.py", "distribution name declared by the manifest"),
            Evidence("https://pypi.org/pypi/aspose-3d-foss/json", detail),
        ),
        polarity=polarity,  # type: ignore[arg-type]
        confidence=0.5 if polarity == "UNRESOLVED" else 1.0,
    )


@pytest.mark.parametrize(
    "detail",
    [
        (
            "package registry: a distribution of this name exists, but ownership not confirmed: "
            "the registry's project URLs point at another repository"
        ),
        "package registry unreachable: ConnectError",
        "package registry: pypi answered ambiguously",
    ],
)
def test_an_unconfirmed_install_renders_no_analysis_wording(detail: str) -> None:
    rendered = "\n".join(_installation(_context(PYTHON, _install(detail, "UNRESOLVED"), PACKAGE)))
    assert analysis_markers(rendered) == []
    assert "could not be confirmed" not in rendered and detail not in rendered


def test_an_unpublished_package_is_stated_plainly() -> None:
    rendered = _installation(
        _context(PYTHON, _install("package registry: distribution not found", "CONTRADICTED"), PACKAGE)
    )
    assert rendered[0] == "`aspose-3d-foss` is not yet published on PyPI."
    assert analysis_markers("\n".join(rendered)) == []


# --- BL-003 class K11, owned by BL-002: the pipeline's perspective printed as prose -------------

K11_SEALED = (
    # aspose-3d-foss/Aspose.3D-FOSS-for-.NET Lane R (one of 53 Core API rows).
    (
        "| `AnimationChannel` | Aspose.ThreeD.Animation.AnimationChannel is a public symbol with "
        "members Add, BindPoint, ComponentType. |"
    ),
    # aspose-psd-foss/Aspose.PSD-FOSS-for-.NET Lane R.
    "The verified public surface includes `Aspose.PSD.Image` for loading, manipulating, and saving.",
    # Every sealed Lane R README with an API Reference (renderer text before this change).
    "The verified public surface has 293 types.",
    (
        "It covers all 293 verified public types; the [API Reference](#api-reference) section "
        "above covers the essentials."
    ),
)


@pytest.mark.parametrize("line", K11_SEALED)
def test_k11_pipeline_perspective_fails(line: str) -> None:
    assert analysis_markers(line) != []


def test_maintainer_this_checkout_is_not_refused() -> None:
    """Cells .NET's maintainers wrote it in their own README (Lane L README.original.md:154)."""
    line = (
        "This checkout does not contain a `tests/` directory. These builds check compilation; they "
        "do not provide automated behavioral test coverage."
    )
    assert analysis_markers(line) == []


def test_the_renderer_and_the_review_scope_use_the_reader_facing_count() -> None:
    from repo_presenter.readme.composition.components.terminology import canonical_forms
    from repo_presenter.readme.review import scope

    assert scope._SURFACE_SUMMARY.match("The public API has 293 types.")
    assert scope._SURFACE_SUMMARY.match("The verified public surface has 293 types.")  # sealed
    assert any(p.search("It covers all 5 public types; the [API Reference](#api-reference) section "
                        "above covers the essentials.") for p in scope._RENDERER_SENTENCES)
    # `text`, `excel` and `markdown` are format facts and ordinary words: never upper-cased.
    forms = canonical_forms([".text", ".excel", ".markdown", ".docx"])
    assert "text" not in forms and "excel" not in forms and "markdown" not in forms
    assert forms["docx"] == "DOCX"
