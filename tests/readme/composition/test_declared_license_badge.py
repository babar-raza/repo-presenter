"""A manifest-declared license with no license file still fills the badge row's license slot.

Real shape: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript (Lane R run 43413892363) declares MIT in
``package.json`` and has no LICENSE file at its revision (``license:spdx`` SUPPORTED, no
``license:file``). Its live header badge ``[![License: MIT](...License-MIT-blue.svg)](#license)``
(``inherited_unit:002.badge_row``) had no slot to fill because the renderer emitted a license badge
only with a license file, so BC-17 failed on the badge as lost and was the run's only blocker.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
import repo_presenter.extractors.platforms.typescript  # noqa: F401  (registers the "typescript" spec)
from repo_presenter.core.registry.loader import load_registry
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.parity_gate import badge_row_replaced

REGISTRY = load_registry(Path(__file__).resolve().parents[3] / "data" / "registry.json")
REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"
LIVE_ROW = (
    "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#license) "
    "[![Contributors](https://img.shields.io/github/contributors/aspose-3d-foss/"
    "Aspose.3D-FOSS-for-TypeScript.svg)](https://github.com/aspose-3d-foss/"
    "Aspose.3D-FOSS-for-TypeScript/graphs/contributors)"
)


def _entry():
    return next(entry for entry in REGISTRY.entries if entry.repository == REPO)


def _facts(*extra: Fact) -> FactsDocument:
    facts = (
        Fact("identity:repository", "identity", REPO, (Evidence("data/registry.json"),)),
        Fact(
            "license:spdx", "license", "MIT",
            (Evidence("package.json", "license declared by the manifest; no license file at this revision"),),
        ),
        Fact(
            "inherited_unit:002.badge_row", "inherited_unit", LIVE_ROW,
            (Evidence("README.md", "lines 3-3; badge_row; under Aspose.3D FOSS for TypeScript"),),
            attributes={"section": "Aspose.3D FOSS for TypeScript"},
        ),
        *extra,
    )
    return FactsDocument(REPO, "0" * 40, facts)


def _render(*sections: str) -> str:
    plan = {"sections": [{"section_id": s, "include": True} for s in sections]}
    return render_readme(_entry(), _facts(), plan, {"units": []}, {"dispositions": []})


def test_the_declared_license_badge_links_to_the_license_section() -> None:
    readme = _render("identity", "badges", "license")
    assert "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#license)" in readme
    assert "## License" in readme
    assert badge_row_replaced(
        "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#license)", readme
    )


def test_no_license_badge_without_a_license_section_to_link_to() -> None:
    readme = _render("identity", "badges")
    assert "License-MIT" not in readme
