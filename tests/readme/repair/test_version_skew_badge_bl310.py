"""BL-310: BC-17 ``technical_content`` and BC-05 ``superseded_unstated`` on a stale pinned version
and on a registry-version badge no template prints.

The texts are the exact finding messages of the Aspose.PDF-FOSS-for-Java Lane R run 44349034180
(and the zero-call re-certification of its seal, registry at 26.9.0, maintainers' README pinned at
26.6.0):

* ``inherited_unit:013.code_block holds code_blocks '<dependency>' ...`` and ``015.code_block holds
  code_blocks 'implementation 'org.aspose:aspose-pdf-foss:26.6.0''``: the candidate prints the same
  Maven and Gradle snippets with the verified 26.9.0 (BC-14 forbids any other), which BC-17 judged a
  loss because the whole block differs by its version;
* ``inherited_unit:013.code_block is SUPERSEDE_REDUNDANT, but the README does not state 1 piece(s)
  of it (<version>26.6.0</version>)`` and the Gradle line: the same two units under BC-05;
* ``inherited_unit:002.badge_row holds links 'https://img.shields.io/maven-central/v/org.aspose/
  aspose-pdf-foss.svg'`` and ``'https://search.maven.org/artifact/org.aspose/aspose-pdf-foss'``:
  Java's ecosystem spec has no version badge, so the README states the version in Installation.

Each shape passes after the fix beside negative controls that still fail.
"""

from __future__ import annotations

from types import SimpleNamespace

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.core.package_registry import verified_package_version, with_verified_version
from repo_presenter.readme.parity_gate import LANE_R, SealedCandidate, content_losses
from repo_presenter.readme.validation.supersession import superseded_failures

REPO = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"
MAVEN = (
    "```xml\n<dependency>\n  <groupId>org.aspose</groupId>\n  <artifactId>aspose-pdf-foss</artifactId>\n"
    "  <version>26.6.0</version>\n</dependency>\n```"
)
GRADLE = "```groovy\nimplementation 'org.aspose:aspose-pdf-foss:26.6.0'\n```"
BADGES = (
    "[![Build Status](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Java/actions/workflows/"
    "build.yml/badge.svg)](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Java/actions/"
    "workflows/build.yml) [![Maven Central](https://img.shields.io/maven-central/v/org.aspose/"
    "aspose-pdf-foss.svg)](https://search.maven.org/artifact/org.aspose/aspose-pdf-foss)"
)
BENCHMARK = (
    f"# Aspose.PDF FOSS for Java\n\n{BADGES}\n\n## Installation\n\n{MAVEN}\n\n{GRADLE}\n"
)
BUILD_BADGE = BADGES.split(" [![Maven")[0]  # the renderer prints this one from its own facts
INSTALLED = (
    f"# Aspose.PDF FOSS for Java\n\n{BUILD_BADGE}\n\n## Installation\n\nInstall the published package from Maven "
    "Central (`org.aspose:aspose-pdf-foss`, version 26.9.0):\n\n"
    + MAVEN.replace("26.6.0", "26.9.0")
    + "\n\n"
    + GRADLE.replace("26.6.0", "26.9.0")
    + "\n"
)
_EV = (Evidence("pom.xml", "declared by the POM"),)


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", **attributes: str) -> Fact:
    return Fact(fact_id, kind, value, _EV, polarity, 1.0, attributes or None)


def _document(*, published: str | None = "26.9.0", name_polarity: str = "SUPPORTED") -> FactsDocument:
    facts = [
        _fact("package:name", "package", "org.aspose:aspose-pdf-foss", name_polarity),
        _fact("inherited_unit:002.badge_row", "inherited_unit", BADGES, section="Aspose.PDF FOSS"),
        _fact("inherited_unit:013.code_block", "inherited_unit", MAVEN, section="Installation"),
        _fact("inherited_unit:015.code_block", "inherited_unit", GRADLE, section="Installation"),
    ]
    if published is not None:
        facts.append(_fact("package:published_version", "package", published))
    return FactsDocument(REPO, "5a4ae879" + "0" * 32, tuple(facts))


def _rows(document: FactsDocument) -> tuple[dict, ...]:
    return tuple(
        {"id": f.id, "kind": f.kind, "value": f.value, "polarity": f.polarity,
         "attributes": f.attributes,
         "evidence": [{"path": e.path, "detail": e.detail} for e in f.evidence]}
        for f in document.facts
    )


_SUPERSEDED = tuple(
    {"unit_id": unit, "disposition": "SUPERSEDE_REDUNDANT", "destination_section": "installation",
     "fact_ids": [], "rationale": "The Installation section states the verified install."}
    for unit in (
        "inherited_unit:002.badge_row", "inherited_unit:013.code_block", "inherited_unit:015.code_block",
    )
)


def _losses(readme: str, document: FactsDocument | None = None, benchmark: str = BENCHMARK) -> list[str]:
    document = document or _document()
    candidate = SealedCandidate(LANE_R, readme, _rows(document), _SUPERSEDED, document=document)
    return [f"{loss.category}: {loss.item}" for loss in content_losses(candidate, benchmark)]


# --- helpers --------------------------------------------------------------------------------------


def test_the_verified_version_is_the_registrys_and_a_stale_one_swaps_by_shape() -> None:
    assert verified_package_version(_document().facts) == "26.9.0"
    assert verified_package_version(_document(published=None).facts) is None
    assert with_verified_version("<version>26.6.0</version>", "26.9.0") == "<version>26.9.0</version>"
    assert with_verified_version("g:a:v26.6.0", "26.9.0") == "g:a:v26.9.0"
    # another shape, the verified version itself and no verified version leave the text alone
    assert with_verified_version('<?xml version="1.0"?> 26.6', "26.9.0") == '<?xml version="1.0"?> 26.6'
    assert with_verified_version("26.9.0", "26.9.0") == "26.9.0"
    assert with_verified_version("<version>26.6.0</version>", None) == "<version>26.6.0</version>"


# --- BC-17 ---------------------------------------------------------------------------------------


def test_the_pinned_snippets_and_the_version_badge_are_not_losses_once_the_verified_version_is_stated() -> None:
    assert _losses(INSTALLED) == []


def test_negative_a_snippet_the_readme_does_not_print_is_still_lost() -> None:
    readme = INSTALLED.split("```xml")[0] + "Version 26.9.0.\n"
    lost = _losses(readme)
    assert any(item.startswith("code_blocks: <dependency>") for item in lost)
    assert any("implementation" in item for item in lost)


def test_negative_a_snippet_that_differs_beyond_its_version_is_still_lost() -> None:
    readme = INSTALLED.replace("<artifactId>aspose-pdf-foss</artifactId>", "<artifactId>other</artifactId>")
    assert any(item.startswith("code_blocks: <dependency>") for item in _losses(readme))


def test_negative_no_verified_version_leaves_the_stale_snippet_a_loss() -> None:
    lost = _losses(INSTALLED, _document(published=None))
    assert any(item.startswith("code_blocks: <dependency>") for item in lost)
    assert any("search.maven.org" in item for item in lost)  # the badge needs the version too


def test_negative_a_badge_of_another_package_stays_lost() -> None:
    other = BENCHMARK.replace("org.aspose/aspose-pdf-foss.svg", "org.other/other-lib.svg").replace(
        "search.maven.org/artifact/org.aspose/aspose-pdf-foss", "search.maven.org/artifact/org.other/other-lib"
    )
    lost = _losses(INSTALLED, benchmark=other)
    assert any("org.other/other-lib" in item for item in lost)


def test_negative_a_readme_that_does_not_state_the_version_loses_the_badge() -> None:
    readme = INSTALLED.replace("26.9.0", "26.10.0")
    assert any("maven-central" in item for item in _losses(readme))


def test_negative_an_unverified_package_name_keeps_the_badge_a_loss() -> None:
    lost = _losses(INSTALLED, _document(name_polarity="UNRESOLVED"))
    assert any("maven-central" in item for item in lost)


# --- BC-05 ---------------------------------------------------------------------------------------


def _superseded_candidate(readme: str, document: FactsDocument) -> SimpleNamespace:
    return SimpleNamespace(
        facts=document,
        dispositions={"dispositions": list(_SUPERSEDED)},
        readme=readme,
    )


def test_a_superseded_snippet_is_stated_when_the_readme_prints_it_at_the_verified_version() -> None:
    assert superseded_failures(_superseded_candidate(INSTALLED, _document())) == []


def test_negative_the_stale_pieces_are_still_owed_without_a_verified_version() -> None:
    failures = superseded_failures(_superseded_candidate(INSTALLED, _document(published=None)))
    text = " ".join(f.detail for f in failures)
    assert "<version>26.6.0</version>" in text and "implementation 'org.aspose:aspose-pdf-foss:26.6.0'" in text


def test_negative_a_piece_that_is_not_a_version_difference_is_still_owed() -> None:
    readme = INSTALLED.replace("  <groupId>org.aspose</groupId>\n", "")
    failures = superseded_failures(_superseded_candidate(readme, _document()))
    assert [f.unit for f in failures] == ["inherited_unit:013.code_block"]
    assert "<groupid>org.aspose</groupid>" in failures[0].detail.lower()
