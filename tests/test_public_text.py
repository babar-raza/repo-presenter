"""Owner ruling 2026-11-06: the maintainer attribution never reaches the public README."""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.readme.composition.placement import (
    ATTRIBUTION_LINE,
    with_attribution,
)
from repo_presenter.readme.validation.public_text import (
    internal_markers,
    public_text_failures,
)


def test_attributed_content_prints_as_written_with_no_attribution() -> None:
    shown = with_attribution(["Kept maintainer paragraph.", "Other."], [True, False])
    assert shown == ["Kept maintainer paragraph.", "Other."]
    assert all(ATTRIBUTION_LINE not in text for text in shown)


def test_any_attribution_wording_in_the_readme_fails() -> None:
    for line in (
        ATTRIBUTION_LINE,
        "*From the maintainers' README:*",
        "This section is not independently verified.",
        "Source: inherited_unit:012.paragraph",
    ):
        failures = public_text_failures(SimpleNamespace(readme=f"# Title\n\n{line}\n\nBody.\n"))
        assert failures and failures[0].stage == "COMPOSING", line


def test_an_ordinary_readme_passes() -> None:
    readme = "# Aspose.Cells FOSS for Rust\n\nRead and write XLSX files.\n\n## Installation\n"
    assert internal_markers(readme) == []
