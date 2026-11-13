"""BC-14 claim_contradiction: a claim is judged against the fact about its own subject.

Class C3 (2026-11-13): Lane R REJECTs that matched a claim to a fact about something else -- a
converter tool's "not published" read against the library's registry reading (3D-.NET), a Python
floor read as the package's release (Slides-Python). Kept apart from ``test_claims.py``, whose
content TC-017b's receipt pins (its check command names that file).
"""

from __future__ import annotations

import pytest

from repo_presenter.readme.validation.claims import claim_findings
from tests.readme.validation.test_claims import NET_3D, _fact, _facts

SLIDES = (
    _fact("package:name", "package", "aspose-slides-foss"),
    _fact("package:published_version", "package", "26.8.0", "current stable release"),
)


def test_a_runtime_named_right_after_the_number_is_not_a_release_claim() -> None:
    """Slides-Python's shape with the runtime after the number: 'needs version 3.10 of Python'."""
    readme = "The `aspose-slides-foss` package needs version 3.10 of Python or later.\n"
    assert claim_findings(readme, _facts(*SLIDES)) == []


@pytest.mark.parametrize(
    "readme",
    [
        "The `aspose-slides-foss` package version 3.10 of the SDK.\n",
        "```bash\npip install aspose-slides-foss==3.10\n```\n",
        "aspose-slides-foss 3.10 is the version you should install.\n",
    ],
)
def test_a_stale_package_release_is_still_caught(readme: str) -> None:
    [finding] = claim_findings(readme, _facts(*SLIDES))
    assert "3.10" in finding.detail and "26.8.0" in finding.detail


# The real hosted Lane R sentence (3D-.NET, version set 2e1cacfdb7dc): the converter, not the
# library, is what "is not published"; no package id is spelled, so the code-span test missed it.
CONVERTER_SENTENCE = (
    "The repository also includes a console conversion tool in src/converter/ that references the "
    "library as a project but is not published to NuGet.\n"
)


@pytest.mark.parametrize(
    "readme",
    [
        CONVERTER_SENTENCE,
        CONVERTER_SENTENCE.replace("src/converter/", "`src/converter/`"),
        "The repository also includes a console conversion tool in src/converter/ that\n"
        "references the library as a project but is not published to NuGet.\n",
        "The converter tool, which wraps the Aspose.3D.FOSS library, is not published to NuGet.\n",
        "The samples under `examples/` are not published to NuGet.\n",
    ],
)
def test_a_denial_whose_subject_is_another_artifact_is_not_the_librarys(readme: str) -> None:
    assert claim_findings(readme, _facts(*NET_3D)) == []


@pytest.mark.parametrize(
    "readme",
    [
        # the subject of the relative clause is the library, not the tool
        "The library that the conversion tool references is not published to NuGet.\n",
        # a coordinated subject still denies the library
        "The converter and the library are not published to NuGet.\n",
        "Unlike the samples, the package is not published to NuGet.\n",
        # a semicolon starts a new clause whose subject is the package
        "The converter tool ships in src/converter/; the package is not published to NuGet.\n",
        "The library is not published to NuGet.\n",
    ],
)
def test_a_denial_about_the_library_still_fails_beside_another_artifact(readme: str) -> None:
    [finding] = claim_findings(readme, _facts(*NET_3D))
    assert "not published" in finding.detail
