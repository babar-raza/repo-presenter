"""Stale package-version and publication claims, resolved against ``package:published_version``.

Fixtures are drawn from the shapes TC-025's census named: the PDF Java "pins version 26.6.0,
registry lists 26.9.0" case and the PSD .NET "says not published to NuGet, registry lists it"
case (``docs/investigations/2026-11-07-vs0-vertical-slice.md``).
"""

from __future__ import annotations

from typing import Any

from repo_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID
from repo_presenter.readme.correction.detectors.stale_package_version import (
    stale_package_version,
)
from repo_presenter.readme.correction.model import FALSE_CLAIM_FIX


def published(make_fact: Any, version: str = "26.9.0") -> Any:
    return make_fact(
        PUBLISHED_VERSION_FACT_ID,
        version,
        evidence=(("https://repo1.maven.org/x", "package registry: found"),),
    )


# --- the pinned-version shape ----------------------------------------------------------------------


def test_a_stale_pinned_version_is_rewritten_to_the_registrys_current_release(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "This library pins version 26.6.0 of the native runtime for compatibility.\n"
    ctx = make_context(readme, make_facts(published(make_fact, "26.9.0")))
    (edit,) = stale_package_version(ctx).edits
    assert edit.kind == FALSE_CLAIM_FIX
    assert (edit.original, edit.replacement) == ("26.6.0", "26.9.0")
    assert edit.fact_ids == (PUBLISHED_VERSION_FACT_ID,)
    assert readme[edit.start : edit.end] == "26.6.0"


def test_pinned_to_version_and_pinned_at_version_are_also_recognized(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(published(make_fact, "2.0.0"))
    for phrase in ("pinned to version 1.0.0", "pinned at version 1.0.0"):
        ctx = make_context(f"The build is {phrase} of the SDK.\n", facts)
        (edit,) = stale_package_version(ctx).edits
        assert edit.replacement == "2.0.0"


def test_a_pin_that_already_matches_the_registry_is_left_alone(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(
        "This library pins version 26.9.0 of the native runtime.\n",
        make_facts(published(make_fact, "26.9.0")),
    )
    result = stale_package_version(ctx)
    assert result.edits == () and result.findings == ()


def test_a_pinned_version_with_no_published_version_fact_is_reported_not_guessed(
    make_context: Any, make_facts: Any
) -> None:
    ctx = make_context(
        "This library pins version 26.6.0 of the native runtime.\n",
        make_facts(drop=(PUBLISHED_VERSION_FACT_ID,)),
    )
    result = stale_package_version(ctx)
    assert result.edits == ()
    (finding,) = result.findings
    assert "26.6.0" in finding.text and PUBLISHED_VERSION_FACT_ID in finding.reason


# --- the "not published" shape ---------------------------------------------------------------------


def test_a_not_published_claim_contradicted_by_the_registry_is_corrected(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "The package is not published to NuGet, so install it by cloning the repository.\n"
    ctx = make_context(readme, make_facts(published(make_fact, "24.1.0")))
    (edit,) = stale_package_version(ctx).edits
    assert edit.original == "is not published to NuGet"
    assert edit.replacement == "is published to NuGet"
    assert edit.fact_ids == (PUBLISHED_VERSION_FACT_ID,)
    assert readme[edit.start : edit.end] == edit.original


def test_not_yet_published_is_also_recognized(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(
        "This package is not yet published to PyPI.\n",
        make_facts(published(make_fact, "1.0.0")),
    )
    (edit,) = stale_package_version(ctx).edits
    assert edit.replacement == "is published to PyPI"


def test_a_not_published_claim_with_no_published_version_fact_is_reported_not_guessed(
    make_context: Any, make_facts: Any
) -> None:
    ctx = make_context(
        "The package is not published to NuGet yet.\n",
        make_facts(drop=(PUBLISHED_VERSION_FACT_ID,)),
    )
    result = stale_package_version(ctx)
    assert result.edits == ()
    (finding,) = result.findings
    assert "not published" in finding.reason and PUBLISHED_VERSION_FACT_ID in finding.reason


def test_a_fence_is_never_scanned_for_either_shape(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "```\npins version 26.6.0\nis not published to NuGet\n```\n"
    ctx = make_context(readme, make_facts(published(make_fact, "26.9.0")))
    result = stale_package_version(ctx)
    assert result.edits == () and result.findings == ()
