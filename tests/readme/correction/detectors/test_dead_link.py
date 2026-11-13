"""A text link to a file the tree holds nothing for is unlinked, its text kept (Cells .NET/Python's
real ``RELEASE_NOTES*.md`` links at their 2026-11-13 revisions, whose trees hold no release-notes
file at all)."""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.dead_link import dead_link
from repo_presenter.readme.correction.detectors.links import broken_link
from repo_presenter.readme.correction.detectors.versioned_link_target import (
    versioned_link_target,
)
from repo_presenter.readme.correction.model import BROKEN_LINK, CorrectionResult
from repo_presenter.readme.correction.report import unrepaired_defects


def missing(make_fact: Any, target: str, line: int, number: str = "001") -> Any:
    return make_fact(
        f"link_target:{number}",
        target,
        polarity="CONTRADICTED",
        evidence=(
            ("README.md", f"line {line}; relative; text 'doc'"),
            ("README.md", f"MISSING: tree does not contain {target}"),
        ),
    )


def test_a_dead_text_link_is_unlinked_and_its_words_kept(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    readme = "# T\n- Read the current [release notes](RELEASE_NOTES.md).\n"
    ctx = make_context(readme, make_facts(missing(make_fact, "RELEASE_NOTES.md", 2)), tree=("README.md", "src/a.py"))
    (edit,) = dead_link(ctx).edits
    assert edit.kind == BROKEN_LINK and edit.fact_ids == ("link_target:001",)
    assert readme[edit.start : edit.end] == "[release notes](RELEASE_NOTES.md)"
    assert edit.replacement == "release notes"
    patched = readme[: edit.start] + edit.replacement + readme[edit.end :]
    assert patched == "# T\n- Read the current release notes.\n"


def test_the_sibling_finding_is_no_longer_an_unrepaired_defect(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    ctx = make_context("[V1 notes](RELEASE_NOTES_V1.md)\n", make_facts(missing(make_fact, "RELEASE_NOTES_V1.md", 1)), tree=("README.md",))
    (finding,) = broken_link(ctx).findings
    result = CorrectionResult(original="", corrected="", edits=list(dead_link(ctx).edits), findings=[finding])
    assert unrepaired_defects(result) == []


def test_an_image_is_never_unlinked(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    ctx = make_context("![logo](logo.png)\n", make_facts(missing(make_fact, "logo.png", 1)), tree=("README.md",))
    assert dead_link(ctx).edits == ()


def test_a_link_another_detector_repairs_is_left_to_it(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    facts = make_facts(missing(make_fact, "RELEASE_NOTES.md", 1))
    versioned = make_context("[n](RELEASE_NOTES.md)\n", facts, tree=("README.md", "RELEASE_NOTES_2023.md", "RELEASE_NOTES_2024.md"))
    assert dead_link(versioned).edits == () and versioned_link_target(versioned).edits
    cased = make_context("[n](docs/Guide.md)\n", make_facts(missing(make_fact, "docs/Guide.md", 1)), tree=("README.md", "docs/guide.md"))
    assert dead_link(cased).edits == () and broken_link(cased).edits


def test_a_link_repeated_on_its_line_is_left_as_written(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    ctx = make_context("[a](X.md) and [b](X.md)\n", make_facts(missing(make_fact, "X.md", 1)), tree=("README.md",))
    assert dead_link(ctx).edits == ()
