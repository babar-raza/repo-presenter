"""P3 / P5 (2026-11-14): sealed facts re-derived, with zero calls, the way current extraction
derives them (``recertify.corrected_facts`` and the .NET ``current_type_facts`` hook).

Fixtures are the real fact shapes of the sealed candidates: 3D Python ``format:output.obj``
(seal 65b1f577, example 8 "FAILED; TypeError" beside a declaration and a registered exporter),
HTML Python ``package:python_requires`` (seal bf0f1e7a, "python_requires declared" against
``pyproject.toml``) and Words .NET ``DocumentPositionMovement.cs`` at 0d3f1add (public only under
``#if CPLUSPLUS``; 618 public types instead of 615, BL-065).
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.extractors.platforms.net import current_public_types
from repo_presenter.extractors.platforms.python import corrected_floor_declaration
from repo_presenter.readme.composition.renderer import python_floor_sentence
from repo_presenter.readme.evidence.facts.formats import demote_failed_receipt_formats
from repo_presenter.recertify import SourceSnapshot, corrected_facts, current_surface

OBJ_OUTPUT = Fact(
    "format:output.obj",
    "format",
    ".obj",
    (
        Evidence("README.md", "line 285; example 8: output .obj"),
        Evidence("receipts.json", "example 8: FAILED; TypeError"),
        Evidence("aspose/threed/FileFormat.py", "line 33; FileFormat imports ObjFormat, which states .obj"),
        Evidence(
            "aspose/threed/formats/__init__.py",
            "line 71; ObjPlugin (aspose/threed/formats/obj/ObjPlugin.py) registered with ObjExporter "
            "for ObjFormat, which states .obj",
        ),
    ),
)
GLTF_OUTPUT = Fact(
    "format:output.gltf",
    "format",
    ".gltf",
    (
        Evidence("README.md", "line 157; example 2: output .gltf"),
        Evidence("receipts.json", "example 2: EXECUTED; exit 0"),
        Evidence("README.md", "line 231; example 5: output .gltf"),
        Evidence("receipts.json", "example 5: FAILED; TypeError"),
    ),
)
OBJ_INPUT = Fact(
    "format:input.obj",
    "format",
    ".obj",
    (
        Evidence("README.md", "line 135; example 1: input .obj"),
        Evidence(
            "receipts.json",
            "example 1: NEEDS_INPUT; FileNotFoundError: the example opens an input the repository "
            "does not provide",
        ),
        Evidence("aspose/threed/FileFormat.py", "line 33; FileFormat imports ObjFormat, which states .obj"),
    ),
)


def test_a_format_its_own_receipt_refutes_is_not_supported() -> None:
    demoted = {fact.id: fact for fact in demote_failed_receipt_formats([OBJ_OUTPUT, GLTF_OUTPUT, OBJ_INPUT])}
    assert demoted["format:output.obj"].polarity == "UNRESOLVED"
    # An executed example of the same direction wins over a failed one; a missing input is not a
    # refutation.
    assert demoted["format:output.gltf"].polarity == "SUPPORTED"
    assert demoted["format:input.obj"].polarity == "SUPPORTED"


def test_a_not_implemented_receipt_refutes_too() -> None:
    dae = Fact(
        "format:output.dae",
        "format",
        ".dae",
        (Evidence("receipts.json", "example 4: NOT_VERIFIED; NotImplementedError: supports_format"),),
    )
    assert demote_failed_receipt_formats([dae])[0].polarity == "UNRESOLVED"


HTML_FLOOR = Fact(
    "package:python_requires",
    "package",
    ">=3.10",
    (Evidence("pyproject.toml", "python_requires declared"),),
)


def test_the_python_floor_names_the_key_its_manifest_declares() -> None:
    document = FactsDocument("aspose-html-foss/Aspose.HTML-FOSS-for-Python", "b" * 40, (HTML_FLOOR,))
    corrected, changed = corrected_floor_declaration(document)
    assert changed
    fact = corrected.facts[0]
    assert fact.evidence[0].detail == "requires-python declared"
    assert fact.attributes == {"floor_declaration": "requires-python"}
    again, changed_again = corrected_floor_declaration(corrected)
    assert not changed_again and again is corrected
    setup = FactsDocument("o/r", "c" * 40, (Fact(
        "package:python_requires", "package", ">=3.7", (Evidence("setup.py", "python_requires declared"),),
        attributes={"floor_declaration": "python_requires"},
    ),))
    assert corrected_floor_declaration(setup) == (setup, False)


def test_corrected_facts_applies_both_and_says_what_changed() -> None:
    document = FactsDocument("o/r", "d" * 40, (OBJ_OUTPUT, HTML_FLOOR))
    corrected, note = corrected_facts(document)
    assert "format:output.obj" in note and "python_requires" in note
    assert {f.id: f.polarity for f in corrected.facts}["format:output.obj"] == "UNRESOLVED"


def test_the_python_floor_reads_as_aspose_org_writes_it() -> None:
    assert python_floor_sentence("3.10") == "Requires Python 3.10 or later."


#: Words .NET Aspose.Words/Model/Nodes/Navigation/DocumentPositionMovement.cs@0d3f1add, verbatim
#: apart from the trimmed member list.
DOCUMENT_POSITION_MOVEMENT = """// Copyright (c) 2001-2026 Aspose Pty Ltd. All Rights Reserved.
// 16/10/2010 by Dmitry Vorobyev

namespace Aspose.Words
{
    /// <summary>
    /// Specifies one of possible movements of <see cref="DocumentPosition"/>.
    /// </summary>
#if CPLUSPLUS
    public
#else
    internal
#endif
    enum DocumentPositionMovement
    {
        /// <summary>
        /// No movement done.
        /// </summary>
        None,
        /// <summary>
        /// Moved inside a node.
        /// </summary>
        Inside
    }
}
"""
SECTION = """namespace Aspose.Words
{
    /// <summary>Represents a document section.</summary>
    public class Section
    {
        /// <summary>The body.</summary>
        public void Clear() { }
    }
}
"""
MOVEMENT_PATH = "Aspose.Words/Model/Nodes/Navigation/DocumentPositionMovement.cs"
SECTION_PATH = "Aspose.Words/Model/Section.cs"


def _sealed_words() -> FactsDocument:
    def symbol(slug: str, value: str, path: str, kind: str) -> Fact:
        return Fact(
            f"public_symbol:{slug}", "public_symbol", value,
            (Evidence(path, f"line 10; {kind}; public by declaration"),),
            attributes={"symbol_kind": kind, "declaration": "public"},
        )

    return FactsDocument(
        "aspose-words-foss/Aspose.Words-FOSS-for-.NET",
        "0d3f1add920f5294d726b4f286c2d6ba7c3ae22c",
        (
            symbol("aspose.words.documentpositionmovement", "Aspose.Words.DocumentPositionMovement", MOVEMENT_PATH, "enum"),
            symbol("aspose.words.section", "Aspose.Words.Section", SECTION_PATH, "class"),
            symbol("aspose.words.section.clear", "Aspose.Words.Section.Clear", SECTION_PATH, "method"),
            symbol("aspose.words.unreadable", "Aspose.Words.Unreadable", "Aspose.Words/Missing.cs", "class"),
        ),
    )


def test_a_type_public_only_under_if_cplusplus_leaves_the_sealed_surface() -> None:
    sources = {MOVEMENT_PATH: DOCUMENT_POSITION_MOVEMENT, SECTION_PATH: SECTION}
    narrowed, gone = current_public_types(_sealed_words(), sources)
    assert gone == ["Aspose.Words.DocumentPositionMovement"]
    # Only removes, and only a type whose own file was read: the unreadable one stays.
    assert [fact.value for fact in narrowed.facts] == [
        "Aspose.Words.Section",
        "Aspose.Words.Section.Clear",
        "Aspose.Words.Unreadable",
    ]
    assert current_public_types(narrowed, sources) == (narrowed, [])


def test_recertify_counts_the_types_today_s_extractor_counts() -> None:
    source = SourceSnapshot(
        tree_paths=(MOVEMENT_PATH, SECTION_PATH, "Aspose.Words/Aspose.Words.csproj"),
        readme=b"",
        sources={MOVEMENT_PATH: DOCUMENT_POSITION_MOVEMENT, SECTION_PATH: SECTION},
    )
    narrowed, clause = current_surface(_sealed_words(), "net", source)
    assert clause is not None and "Aspose.Words.DocumentPositionMovement" in clause
    assert sum(
        1 for f in narrowed.facts if (f.attributes or {}).get("symbol_kind") in ("class", "enum")
    ) == 2


def test_units_of_types_the_current_facts_dropped_leave_with_them() -> None:
    from repo_presenter.recertify import current_units

    narrowed, _ = current_public_types(
        _sealed_words(), {MOVEMENT_PATH: DOCUMENT_POSITION_MOVEMENT, SECTION_PATH: SECTION}
    )
    sealed = {
        "units": [
            {"slot": "type:public_symbol:aspose.words.documentpositionmovement", "text": "x"},
            {"slot": "hub:public_symbol:aspose.words.section", "text": "y"},
            {"slot": "intro", "text": "z"},
        ],
        "omitted": [],
    }
    assert [u["slot"] for u in current_units(sealed, narrowed)["units"]] == [
        "hub:public_symbol:aspose.words.section",
        "intro",
    ]
    assert current_units(sealed, _sealed_words()) == sealed
