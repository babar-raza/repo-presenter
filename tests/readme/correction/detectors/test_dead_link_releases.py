"""``dead_link`` version 2 (BL-010, owner feedback a922e11316): a dead release-notes link of a
repository that publishes release tags points at its Releases page instead of being unlinked.

Real shapes: Cells Python's "- Read the current [release notes](RELEASE_NOTES.md)." (tags V26.3.0
.. V26.10.0, ``git ls-remote --tags`` 2026-11-14) and Cells .NET's "- [V26.10.0 release
notes](RELEASE_NOTES_V26.10.0.md)" (tags V26.4.0 .. V26.10.0); neither tree ever held the file."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from repo_presenter.readme.correction.apply import apply_edits
from repo_presenter.readme.correction.detectors.dead_link import dead_link
from repo_presenter.readme.correction.model import BROKEN_LINK

PYTHON_TAGS = ("V26.10.0", "V26.3.0", "V26.3.1", "V26.7.0")


def _missing(make_fact: Any, target: str, line: int) -> Any:
    return make_fact(
        "link_target:001",
        target,
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", f"line {line}; relative; text 'doc'"),
            ("README.md", f"MISSING: tree does not contain {target}"),
        ),
    )


def test_a_release_notes_link_points_at_the_releases_page(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    readme = "# T\n- Read the current [release notes](RELEASE_NOTES.md).\n"
    ctx = make_context(
        readme, make_facts(_missing(make_fact, "RELEASE_NOTES.md", 2)), tree=("README.md",),
        repository="aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
    )
    (edit,) = dead_link(replace(ctx, release_tags=PYTHON_TAGS)).edits
    assert edit.kind == BROKEN_LINK and edit.original == "RELEASE_NOTES.md"
    assert edit.locators == ("tag:V26.10.0", "tag:V26.3.0", "tag:V26.3.1")
    corrected = apply_edits(readme, [edit])[0]
    assert corrected == (
        "# T\n- Read the current [release notes]"
        "(https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python/releases).\n"
    )


def test_a_versioned_link_points_at_that_tag(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    readme = "- [V26.10.0 release notes](RELEASE_NOTES_V26.10.0.md)\n"
    ctx = make_context(
        readme, make_facts(_missing(make_fact, "RELEASE_NOTES_V26.10.0.md", 1)), tree=("README.md",),
        repository="aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
    )
    (edit,) = dead_link(replace(ctx, release_tags=("V26.10.0", "V26.4.0", "V26.9.0"))).edits
    assert edit.replacement == (
        "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET/releases/tag/V26.10.0"
    )


def test_without_tags_the_link_is_unlinked_as_before(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    readme = "- Read the current [release notes](RELEASE_NOTES.md).\n"
    ctx = make_context(readme, make_facts(_missing(make_fact, "RELEASE_NOTES.md", 1)), tree=("README.md",))
    (edit,) = dead_link(ctx).edits
    assert edit.replacement == "release notes"


def test_a_link_that_is_not_release_notes_is_never_pointed_at_releases(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    readme = "- See the [guide](docs/GUIDE.md).\n"
    ctx = make_context(readme, make_facts(_missing(make_fact, "docs/GUIDE.md", 1)), tree=("README.md",))
    (edit,) = dead_link(replace(ctx, release_tags=PYTHON_TAGS)).edits
    assert edit.replacement == "guide"
