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
    assert finding.report_only_reason == "NO_EVIDENCE_OF_ABSENCE"


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
    assert finding.report_only_reason == "NO_EVIDENCE_OF_ABSENCE"


def test_a_not_published_claim_with_no_fact_is_not_a_blocking_lane_l_defect(
    make_context: Any, make_facts: Any
) -> None:
    """Aspose.BarCode FOSS for Python: the README correctly says the package is not published,
    PyPI genuinely has no release under that name, and there is no fact either way -- this must
    not be an ``unrepaired_defect`` that blocks Lane L (``readme.correction.report.is_defect``)."""
    from repo_presenter.readme.correction.report import is_defect

    ctx = make_context(
        "The package is not published to PyPI.\n",
        make_facts(drop=(PUBLISHED_VERSION_FACT_ID,)),
    )
    (finding,) = stale_package_version(ctx).findings
    assert is_defect(finding) is False


def test_a_fence_is_never_scanned_for_either_shape(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "```\npins version 26.6.0\nis not published to NuGet\n```\n"
    ctx = make_context(readme, make_facts(published(make_fact, "26.9.0")))
    result = stale_package_version(ctx)
    assert result.edits == () and result.findings == ()


def test_a_trailing_yet_is_consumed_with_the_not_published_claim(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """Leaving "yet" behind produced "is published to NuGet yet", which the independent review
    REJECTed as a contradiction (found on Aspose.PSD-FOSS-for-.NET; its full ', but ...' sentence is
    now rewritten whole -- see the next test -- so this pins the plain, non-'but' shape)."""
    readme = "Note that the package is not published to NuGet yet.\n"
    ctx = make_context(readme, make_facts(published(make_fact, "26.9.0")))
    (edit,) = stale_package_version(ctx).edits
    assert edit.original == "is not published to NuGet yet"
    assert edit.replacement == "is published to NuGet"


def test_the_whole_but_not_published_sentence_is_rewritten_not_just_its_verb(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """Real Aspose.PSD-FOSS-for-.NET line: rewriting only 'is not published' left a dangling 'but'
    ('..., but `X` is published to NuGet.'), which the independent review REJECTed."""
    readme = (
        "The package metadata is defined in this repository, but `Aspose.PSD.FOSS` is not "
        "published to NuGet yet.\n"
    )
    # the real repository's identity: the sentence names this package, so the registry reading
    # of it contradicts the denial
    identity = make_fact("package:name", "Aspose.PSD.FOSS")
    ctx = make_context(readme, make_facts(published(make_fact, "26.10.0"), identity))
    (edit,) = stale_package_version(ctx).edits
    assert edit.original == readme.strip()
    assert edit.replacement == "`Aspose.PSD.FOSS` is published to NuGet."
    assert readme[edit.start : edit.end] == edit.original


def test_a_not_published_clause_that_is_not_a_but_sentence_keeps_the_plain_rewrite(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "The package is not published to NuGet yet.\n"
    ctx = make_context(readme, make_facts(published(make_fact, "26.10.0")))
    (edit,) = stale_package_version(ctx).edits
    assert edit.replacement == "is published to NuGet"


# --- a "not published" statement whose subject is another artifact ------------------------------


def test_the_converter_tools_not_published_statement_is_never_rewritten(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """Real Aspose.3D-FOSS-for-.NET Lane L bundle (52b0f00e, 2026-11-10): the live README's
    converter paragraph says the *converter tool* is not published to NuGet -- true -- and the
    detector rewrote it to "it is published to NuGet", a false claim about the converter. The
    registry reading is of the library, so nothing contradicts the sentence."""
    readme = (
        "The repository also contains a separate console conversion tool\n"
        "(`src/converter/Converter.csproj`, package id `Aspose.3D.Converter`) that references the "
        "library\nas a project; it is not published to NuGet.\n"
    )
    result = stale_package_version(make_context(readme, make_facts(published(make_fact))))
    assert result.edits == () and result.findings == ()
    unspelled = (
        "The repository also includes a console conversion tool in src/converter/ that "
        "references the library as a project but is not published to NuGet.\n"
    )
    result = stale_package_version(make_context(unspelled, make_facts(published(make_fact))))
    assert result.edits == ()


def test_the_librarys_own_denial_beside_the_converter_is_still_corrected(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = "The converter tool ships here; the library is not published to NuGet.\n"
    (edit,) = stale_package_version(make_context(readme, make_facts(published(make_fact)))).edits
    assert edit.replacement == "is published to NuGet"


def test_a_denial_naming_only_a_package_id_other_than_this_one_is_not_rewritten(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """The registry reading is of this package's identity; a sentence that names only another
    package id (and none of this package's names) is not a claim that reading contradicts."""
    readme = "The metadata is defined here, but `Aspose.PSD.FOSS` is not published to NuGet yet.\n"
    result = stale_package_version(make_context(readme, make_facts(published(make_fact))))
    assert result.edits == ()
