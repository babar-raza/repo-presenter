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


# Measured live (aspose-cells-foss/Aspose.Cells-FOSS-for-.NET, run 41298080767): the upstream
# README's own `<PackageReference Include="Aspose.Cells.FOSS" Version="26.10.0.0" />` snippet
# spells the release with .NET's traditional 4-part assembly-version convention (a trailing
# revision, conventionally 0); the registry's own 3-part release ("26.10.0") does not carry it.
# The same release, not a real mismatch -- a bare string comparison called it one.
def test_a_dotnet_four_part_assembly_version_matches_its_three_part_release() -> None:
    sentence = 'Install the published package from NuGet (`Aspose.3D.FOSS`, version 26.1.0.0):'
    assert claim_findings(readme("## Installation", "", sentence), facts()) == []


def test_a_three_part_version_matches_its_four_part_release() -> None:
    """The padding direction is symmetric: the manifest/registry side may be the longer one too."""
    sentence = "Install the published package from NuGet (`Aspose.3D.FOSS`, version 26.1.0):"
    rev_facts = FactsDocument(
        "org/repo",
        REVISION,
        (
            fact("package:name", "package", "Aspose.3D.FOSS"),
            fact("package:version", "package", "26.1.0.0"),
            fact("public_symbol:scene", "public_symbol", "Aspose.ThreeD.Scene"),
            fact("dependency:none", "dependency", "none"),
        ),
    )
    assert claim_findings(readme("## Installation", "", sentence), rev_facts) == []


@pytest.mark.parametrize(
    "shown",
    [
        "26.1.0.1",  # a genuinely different trailing revision, not a trailing zero
        "26.1.0-rc1",  # a prerelease tag must never be silently padded away
    ],
)
def test_a_four_part_version_that_is_not_a_trailing_zero_still_fails(shown: str) -> None:
    sentence = f"Install the published package from NuGet (`Aspose.3D.FOSS`, version {shown}):"
    [finding] = claim_findings(readme("## Installation", "", sentence), facts())
    assert shown in finding.detail and "26.1.0" in finding.detail


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


def test_a_name_quoted_verbatim_from_a_supported_inherited_unit_is_not_a_wrong_name() -> None:
    """Grounded in two real hosted REJECTs, confirmed recurring (aspose-pdf-foss/.NET run
    41121225716; aspose-psd-foss/.NET run 41130142104): each repository's own real README
    genuinely names its own test/sample sub-projects (`Aspose.Pdf.Foss.Tests`,
    `Aspose.PSD.FOSS.Samples.Basic`), confirmed present verbatim in a SUPPORTED inherited_unit
    fact in both repositories' own facts.json -- quoted from the pinned source, not invented --
    yet no fact kind states them as a package identity, so rule (f) flagged them as naming
    "another package" with no fact backing. A name quoted verbatim from a SUPPORTED
    inherited_unit fact is no longer flagged."""
    document = facts(
        fact(
            "inherited_unit:227.code_block",
            "inherited_unit",
            "```bash\ndotnet test tests/Aspose.3D.FOSS.Tests.csproj\n```",
        )
    )
    sentence = "The test project (`Aspose.3D.FOSS.Tests`) is an xUnit suite."
    assert claim_findings(readme(sentence), document) == []


def test_a_name_not_found_in_any_inherited_unit_is_still_a_wrong_name() -> None:
    """The new exemption is narrow: a name that does NOT appear verbatim in any inherited_unit
    fact is still flagged, same as before -- this is not a blanket allowance for anything that
    extends the identity."""
    document = facts(
        fact(
            "inherited_unit:227.code_block",
            "inherited_unit",
            "```bash\ndotnet test tests/Aspose.3D.FOSS.Tests.csproj\n```",
        )
    )
    sentence = "Add the `Aspose.3D.FOSS.Lite` package to your project."
    [finding] = claim_findings(readme(sentence), document)
    assert "Aspose.3D.FOSS.Lite" in finding.detail


def test_a_name_in_a_contradicted_inherited_unit_is_still_a_wrong_name() -> None:
    """Only a SUPPORTED inherited_unit fact grounds a name -- one the extractor itself marked
    CONTRADICTED (the pinned source was checked and this unit's own text does not hold) proves
    nothing, so it must not exempt a name quoted inside it."""
    document = facts(
        fact(
            "inherited_unit:227.code_block",
            "inherited_unit",
            "```bash\ndotnet test tests/Aspose.3D.FOSS.Tests.csproj\n```",
            polarity="CONTRADICTED",
        )
    )
    sentence = "The test project (`Aspose.3D.FOSS.Tests`) is an xUnit suite."
    [finding] = claim_findings(readme(sentence), document)
    assert "Aspose.3D.FOSS.Tests" in finding.detail


def test_the_wrong_name_rule_is_silent_without_an_identity_fact() -> None:
    bare = FactsDocument(
        "org/x", REVISION, (fact("package:version", "package", "1.0.0"),)
    )
    assert claim_findings(readme("`Aspose.3D.FOSS.Core` is great."), bare) == []


# Real hosted false positive (claim_findings/_prose_name_findings, measured against
# aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp's own real build-instructions text): a cross-platform
# build section honestly names the SAME static-library artifact under both its Unix suffix
# (already exempted via `_FILE_LIKE`'s existing ".a") and its MSVC suffix (".lib") -- not a
# second, unverified package, a file extension `_FILE_LIKE` was simply missing.
@pytest.mark.parametrize("extension", ["lib", "dylib", "o", "obj"])
def test_a_native_build_artifact_extending_the_identity_is_not_a_wrong_name(
    extension: str,
) -> None:
    document = facts()
    sentence = f"The build also produces `Aspose.3D.FOSS.{extension}` on that platform."
    assert claim_findings(readme(sentence), document) == []


def test_a_non_file_like_name_extending_the_identity_is_still_a_wrong_name() -> None:
    """Negative control: the widened _FILE_LIKE exemption is scoped to file extensions, not a
    blanket allowance for anything appended to the identity with a separator."""
    document = facts()
    sentence = "Add the `Aspose.3D.FOSS.Lite` package to your project."
    [finding] = claim_findings(readme(sentence), document)
    assert "Aspose.3D.FOSS.Lite" in finding.detail


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


# Words-Python (Lane R, version set 2e1cacfdb7dc): the live README's own sentences. The product
# reads .doc/.docx/.rtf -- executed examples staging tests/data/input/*.doc|.docx|.rtf prove it
# at the same pinned source -- so the flag came from a facts set missing those input facts, not
# from the rule: with the input facts present nothing is flagged; without them a listed format
# no fact states is still unverified, and rule (g) still holds it (it is not weakened).
WORDS_SENTENCES = (
    "- Load documents with the reader chosen automatically from the "
    "`.docx`/`.doc`/`.rtf`/`.md`/`.txt` file extension.",
    "- `Document(filepath=None, *, stream=None, data=None)` — loads a `.doc`, `.docx`, `.rtf`, "
    "`.txt`, or `.md` file.",
)
WORDS_OUTPUTS = tuple(
    fact(f"format:output.{ext}", "format", f".{ext}") for ext in ("docx", "md", "pdf", "txt")
)
WORDS_INPUTS = tuple(
    fact(f"format:input.{ext}", "format", f".{ext}") for ext in ("doc", "docx", "md", "rtf")
)


@pytest.mark.parametrize("sentence", WORDS_SENTENCES)
def test_words_python_format_lists_pass_with_the_executed_input_format_facts(
    sentence: str,
) -> None:
    assert claim_findings(readme(sentence), facts(*WORDS_OUTPUTS, *WORDS_INPUTS)) == []


@pytest.mark.parametrize("sentence", WORDS_SENTENCES)
def test_words_python_format_lists_are_still_held_when_no_fact_states_the_inputs(
    sentence: str,
) -> None:
    [finding] = claim_findings(readme(sentence), facts(*WORDS_OUTPUTS))
    assert ".doc" in finding.detail and ".rtf" in finding.detail


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
