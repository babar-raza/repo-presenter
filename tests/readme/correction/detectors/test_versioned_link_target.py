"""A link to a generic name, repaired to the unique newest of several versioned siblings --
the shape ``links.broken_link`` reports instead of guessing (Cells .NET/Python's real
``RELEASE_NOTES*.md`` case, reconstructed here as a fixture per the census,
``docs/investigations/2026-11-07-vs0-vertical-slice.md``).
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.links import broken_link
from repo_presenter.readme.correction.detectors.versioned_link_target import (
    versioned_link_target,
)
from repo_presenter.readme.correction.model import BROKEN_LINK
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


def test_a_generic_release_notes_link_is_repaired_to_the_strictly_newest_versioned_file(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(missing(make_fact, "Release-Notes/RELEASE_NOTES.md", 1))
    tree = (
        "README.md",
        "Release-Notes/RELEASE_NOTES_24.1.0.md",
        "Release-Notes/RELEASE_NOTES_24.3.0.md",
        "Release-Notes/RELEASE_NOTES_23.9.0.md",
    )
    readme = "[release notes](Release-Notes/RELEASE_NOTES.md)\n"
    ctx = make_context(readme, facts, tree=tree)
    (edit,) = versioned_link_target(ctx).edits
    assert edit.kind == BROKEN_LINK
    assert edit.replacement == "Release-Notes/RELEASE_NOTES_24.3.0.md"
    assert edit.fact_ids == ("link_target:001",)
    assert readme[edit.start : edit.end] == "Release-Notes/RELEASE_NOTES.md"

    # The sibling detector, reading the very same fact, gives up exactly as it does today.
    assert broken_link(ctx).edits == ()
    (finding,) = broken_link(ctx).findings
    assert "no unique file stands in" in finding.reason


def test_a_bare_year_suffix_is_also_a_versioned_match(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(missing(make_fact, "RELEASE_NOTES.md", 1))
    tree = ("README.md", "RELEASE_NOTES_2023.md", "RELEASE_NOTES_2024.md")
    ctx = make_context("[notes](RELEASE_NOTES.md)\n", facts, tree=tree)
    (edit,) = versioned_link_target(ctx).edits
    assert edit.replacement == "RELEASE_NOTES_2024.md"


def test_a_tie_at_the_top_version_has_no_unique_newest(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """``1.0.0`` and ``1.00.0`` parse to the same version tuple: a genuine tie, not a unique
    newest, so neither detector repairs it."""
    facts = make_facts(missing(make_fact, "RELEASE_NOTES.md", 1))
    tree = ("README.md", "RELEASE_NOTES_1.0.0.md", "RELEASE_NOTES_1.00.0.md")
    ctx = make_context("[notes](RELEASE_NOTES.md)\n", facts, tree=tree)
    assert versioned_link_target(ctx).edits == ()
    assert "no unique file stands in" in broken_link(ctx).findings[0].reason


def test_a_trailing_digit_with_no_separator_is_not_treated_as_a_version(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """``LICENSE2.md`` is a different file, not ``LICENSE.md`` version 2: no separator precedes
    the digit, so it is never offered as a stand-in."""
    facts = make_facts(missing(make_fact, "LICENSE.md", 1))
    ctx = make_context("[l](LICENSE.md)\n", facts, tree=("README.md", "LICENSE2.md"))
    assert versioned_link_target(ctx).edits == ()


def test_a_versioned_match_in_a_different_directory_is_not_offered(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(missing(make_fact, "RELEASE_NOTES.md", 1))
    ctx = make_context(
        "[notes](RELEASE_NOTES.md)\n",
        facts,
        tree=("README.md", "archive/RELEASE_NOTES_2024.md"),
    )
    assert versioned_link_target(ctx).edits == ()


def test_the_exact_single_match_case_already_handled_by_broken_link_is_left_to_it(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """A target with exactly one same-basename candidate is ``broken_link``'s own case; this
    detector adds nothing there (it only ever widens coverage, never competes for a case the
    sibling already repairs)."""
    facts = make_facts(missing(make_fact, "gone.md", 1))
    ctx = make_context("[a](gone.md)\n", facts, tree=("README.md", "docs/gone.md"))
    assert versioned_link_target(ctx).edits == ()
    (edit,) = broken_link(ctx).edits
    assert edit.replacement == "docs/gone.md"


# --- the two detectors never disagree about whether a fact's defect remains ------------------------


def test_the_sibling_finding_for_a_fact_this_detector_repairs_is_not_counted_as_unrepaired(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    from repo_presenter.readme.correction.engine import correct

    facts = make_facts(missing(make_fact, "RELEASE_NOTES.md", 1))
    tree = ("README.md", "RELEASE_NOTES_2023.md", "RELEASE_NOTES_2024.md")
    ctx = make_context("[notes](RELEASE_NOTES.md)\n", facts, tree=tree)
    result = correct(ctx)
    assert [edit.detector for edit in result.edits] == ["versioned_link_target"]
    assert unrepaired_defects(result) == []
