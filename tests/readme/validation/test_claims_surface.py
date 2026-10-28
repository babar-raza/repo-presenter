"""BC-14, iteration 3: the surface claims a README makes about its own package -- the version the
renderer's own sentence prints, a package name stated in prose, a format list -- are held to the
SUPPORTED facts.

Iteration 2 of the independent-reviewer calibration found that the deterministic stage never saw
the ``contradict_version`` and ``contradict_package_name`` mutants: the version rule did not read
the sentence the renderer itself prints ("(`Aspose.3D.FOSS`, version 27.1.0)": a comma between the
name and the word "version"), the identity rule read install commands in fences only, and nothing
read a format list. Every fixture below is the renderer's or an author's real sentence.
"""

from __future__ import annotations

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.claims import claim_findings

REVISION = "a" * 40


def fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("src/x"),), polarity=polarity)  # type: ignore[arg-type]


def facts(*extra: Fact) -> FactsDocument:
    return FactsDocument(
        "org/repo",
        REVISION,
        (
            fact("package:name", "package", "Aspose.3D.FOSS"),
            fact("package:version", "package", "26.1.0"),
            fact("public_symbol:scene", "public_symbol", "Aspose.ThreeD.Scene"),
            fact("dependency:none", "dependency", "none"),
            *extra,
        ),
    )


FORMATS = tuple(
    fact(f"format:input.{ext}", "format", f".{ext}")
    for ext in ("fbx", "gltf", "obj", "stl", "3ds")
)


def readme(*lines: str) -> str:
    return "\n".join(lines) + "\n"


# --- the version the renderer prints -----------------------------------------------------------


@pytest.mark.parametrize(
    "sentence",
    [
        "Install the published package from NuGet (`Aspose.3D.FOSS`, version 27.1.0):",
        "Aspose.3D FOSS provides the Aspose.3D.FOSS package (version 27.1.0) with `Scene`.",
        "Install the published package from NuGet (`Aspose.3D.FOSS`; version 27.1.0):",
        "The package `Aspose.3D.FOSS` (release 27.1.0) is on NuGet.",
        "Current release of `Aspose.3D.FOSS`: version 27.1.0.",
    ],
)
def test_a_version_after_punctuation_is_still_attached_to_the_package(
    sentence: str,
) -> None:
    [finding] = claim_findings(readme("## Installation", "", sentence), facts())
    assert "27.1.0" in finding.detail and "26.1.0" in finding.detail
    assert finding.line == 2


@pytest.mark.parametrize(
    "sentence",
    [
        "Install the published package from NuGet (`Aspose.3D.FOSS`, version 26.1.0):",
        "Aspose.3D FOSS provides the Aspose.3D.FOSS package (version 26.1.0) with `Scene`.",
        # numbers that are not this package's version stay unjudged
        "`Aspose.3D.FOSS` targets .NET and reads FBX 7.4 files.",
        "See the release notes for 25.12.0 before upgrading.",
        "The `Scene` class needs .NET version 8.0.",
    ],
)
def test_the_right_version_and_unrelated_numbers_pass(sentence: str) -> None:
    assert claim_findings(readme("## Installation", "", sentence), facts()) == []


# --- a package name stated in prose ------------------------------------------------------------


@pytest.mark.parametrize(
    "sentence, wrong",
    [
        (
            "Install the published package from NuGet (`Aspose.3D.FOSS.Core`, version 26.1.0):",
            "Aspose.3D.FOSS.Core",
        ),
        (
            "The package `Aspose.3D.FOSS.Core` could not be confirmed on NuGet.",
            "Aspose.3D.FOSS.Core",
        ),
        (
            "Add the `Aspose.3D.FOSS.Lite` package to your project.",
            "Aspose.3D.FOSS.Lite",
        ),
    ],
)
def test_a_package_name_in_prose_that_extends_the_identity_is_a_wrong_name(
    sentence: str, wrong: str
) -> None:
    [finding] = claim_findings(readme("## Installation", "", sentence), facts())
    assert wrong in finding.detail and "Aspose.3D.FOSS" in finding.detail
    assert finding.stage == "COMPOSING"


def test_python_and_maven_spellings_of_the_identity_are_judged_the_same_way() -> None:
    python = FactsDocument(
        "org/py", REVISION, (fact("package:name", "package", "aspose-3d-foss"),)
    )
    [found] = claim_findings(
        readme("The package `aspose-3d-foss-core` is on PyPI."), python
    )
    assert "aspose-3d-foss-core" in found.detail
    assert (
        claim_findings(readme("The package `aspose-3d-foss` is on PyPI."), python) == []
    )
    maven = FactsDocument(
        "org/j",
        REVISION,
        (fact("package:name", "package", "org.aspose:aspose-cells-foss"),),
    )
    [found] = claim_findings(
        readme("(`org.aspose:aspose-cells-foss-core`, version 26.7.0)"), maven
    )
    assert "aspose-cells-foss-core" in found.detail


@pytest.mark.parametrize(
    "sentence",
    [
        # the identity itself, however it is spelled around it
        "The package `Aspose.3D.FOSS` is on NuGet.",
        # a symbol or namespace that merely starts with the identity is a fact value
        "Load it with `Aspose.3D.FOSS.Loader`.",
        # a dotted prefix of a fact value is a namespace
        "Types live in `Aspose.ThreeD`.",
        # a file, not a package
        "Read `Aspose.3D.FOSS.csproj` and `Aspose.3D.FOSS.md`.",
        # build artefacts named after the package
        "Unpack `Aspose.3D.FOSS.tar.gz`, then open `Aspose.3D.FOSS.egg-info`.",
        # a different, shorter name is not an extension of the identity
        "See the `Aspose` brand site.",
        # a sibling product that only shares the family prefix (3D-.NET's converter tool)
        "The converter, package id `Aspose.3D.Converter`, references the library.",
        # a module path spelled another way than the identity is not the identity plus a suffix
        "Import `Aspose.3D_FOSS.Formats` for the format registry.",
    ],
)
def test_prose_names_that_are_facts_namespaces_files_or_unrelated_are_not_wrong_names(
    sentence: str,
) -> None:
    document = facts(
        fact("public_symbol:loader", "public_symbol", "Aspose.3D.FOSS.Loader")
    )
    assert claim_findings(readme(sentence), document) == []


def test_a_dependency_or_registry_confirmed_distribution_in_prose_is_not_a_wrong_name() -> (
    None
):
    document = facts(
        fact("dependency:core", "dependency", "Aspose.3D.FOSS.Core>=1.0"),
        fact("package:distribution.nuget", "package", "Aspose.3D.FOSS.Native"),
    )
    sentence = "Needs `Aspose.3D.FOSS.Core` and `Aspose.3D.FOSS.Native`."
    assert claim_findings(readme(sentence), document) == []


def test_the_wrong_name_rule_is_silent_without_an_identity_fact() -> None:
    bare = FactsDocument(
        "org/x", REVISION, (fact("package:version", "package", "1.0.0"),)
    )
    assert claim_findings(readme("`Aspose.3D.FOSS.Core` is great."), bare) == []


# --- a format list -----------------------------------------------------------------------------


def test_a_format_list_naming_an_unsupported_format_is_flagged() -> None:
    sentence = (
        "Aspose.3D FOSS reads and writes 3D formats including `.fbx`, `.gltf`, `.obj`, "
        "`.iges`, and `.3ds`."
    )
    [finding] = claim_findings(readme(sentence), facts(*FORMATS))
    assert ".iges" in finding.detail and finding.stage == "COMPOSING"


def test_a_format_list_of_supported_formats_passes_in_any_case_and_spelling() -> None:
    sentence = "It reads and writes `.FBX`, `.gltf` and `.OBJ` files."
    assert claim_findings(readme(sentence), facts(*FORMATS)) == []
    bare_names = tuple(
        fact(f"format:{n}", "format", n.upper()) for n in ("fbx", "gltf", "obj")
    )
    assert claim_findings(readme(sentence), facts(*bare_names)) == []


@pytest.mark.parametrize(
    "sentence",
    [
        # one extension is not a list: another check (BC-04) owns single identifiers
        "It reads `.step` files.",
        # a list with no supported format is not this product's format list
        "Create `.env` and `.cfg` files next to the project.",
        # a list inside a fence is code, not a claim
    ],
)
def test_one_extension_or_a_list_that_is_not_about_the_products_formats_is_not_judged(
    sentence: str,
) -> None:
    assert claim_findings(readme(sentence), facts(*FORMATS)) == []


def test_a_fenced_block_listing_extensions_is_code_not_a_claim() -> None:
    text = readme("```text", "`.fbx` `.gltf` `.iges`", "```")
    assert claim_findings(text, facts(*FORMATS)) == []


def test_a_format_list_is_silent_without_any_supported_format_fact() -> None:
    assert claim_findings(readme("Handles `.fbx`, `.iges` and `.step`."), facts()) == []


@pytest.mark.parametrize(
    "sentence",
    [
        # the real sentence from hosted run 40633293097 (Cells-Rust): an explicit disclaimer,
        # not a claim of support.
        "Reads and writes `.fbx` (OOXML/SpreadsheetML) only — no legacy `.iges` (BIFF).",
        "Does not support `.iges` files, only `.fbx`.",
        "Unlike other tools, `.fbx` is supported but not `.iges`.",
    ],
)
def test_a_disclaimed_format_is_not_a_claim(sentence: str) -> None:
    assert claim_findings(readme(sentence), facts(*FORMATS)) == []


def test_a_claim_right_next_to_a_disclaimed_one_is_still_flagged() -> None:
    # the disclaimer covers only the format it names; an unrelated over-claim beside it must
    # still be caught, so the fix cannot be a blanket "sentence has 'no' in it" exemption.
    sentence = "Reads and writes `.fbx`, `.gltf` and `.step`, but not `.iges`."
    [finding] = claim_findings(readme(sentence), facts(*FORMATS))
    assert ".step" in finding.detail
