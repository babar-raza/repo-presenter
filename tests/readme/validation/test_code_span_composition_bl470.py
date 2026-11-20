"""BL-470: BC-04 accepts a code span that composes fact values (``List<RecognitionResult>``) and
still refuses every span whose identifiers are not facts.

The exact span is the one hosted run 44686944431 (Aspose.OCR-FOSS-for-.NET, 2026-11-20) refused:
``OcrOutput`` is a SUPPORTED symbol whose ``bases`` the extractor read from ``src/OcrOutput.cs`` as
``List<RecognitionResult>``, and ``RecognitionResult`` is a SUPPORTED symbol. The negative controls
are the same shapes with an invented class, an invented method and a real type's wrong member.
"""

from __future__ import annotations

import dataclasses

import pytest
from test_registry_checks import BASE_FACTS, ENTRY, FACTS, _candidate, _fact

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition.authoring import (
    GENERIC_TYPE_NAMES,
    allowed_identifiers,
    composed_identifier_allowed,
    declared_type_texts,
    identifier_allowed,
    surface_members,
    verified_members,
)
from repo_presenter.readme.validation.units import unit_failures


def _symbol(value: str, **attributes: str) -> Fact:
    return Fact(
        f"public_symbol:{value.lower()}",
        "public_symbol",
        value,
        (Evidence("src/X.cs", "line 6; class; public by declaration"),),
        attributes=attributes or None,
    )


OCR = FactsDocument(
    FACTS.repository,
    FACTS.source_revision,
    (
        *BASE_FACTS,
        _symbol("Aspose.OCR.OcrOutput", bases="List<RecognitionResult>", symbol_kind="class"),
        _symbol("Aspose.OCR.RecognitionResult", symbol_kind="class"),
        _symbol(
            "Aspose.OCR.RecognitionResult.RecognitionLinesResult",
            signature="List<LinesResult>",
            member_kind="property",
        ),
        _symbol("Aspose.OCR.OcrInput", symbol_kind="class"),
    ),
)


def _judge(span: str) -> bool:
    allowed = allowed_identifiers(OCR, "Aspose.OCR FOSS for .NET")
    members = verified_members(OCR)
    methods = surface_members(OCR)
    values = {f.value for f in OCR.facts if f.polarity == "SUPPORTED"}

    def plain(name: str) -> bool:
        return name in values or identifier_allowed(name, allowed, members, methods)

    def in_type_position(name: str) -> bool:
        return name in values or name in allowed

    return plain(span) or composed_identifier_allowed(
        span, in_type_position, declared_type_texts(OCR)
    )


@pytest.mark.parametrize(
    "span",
    [
        "List<RecognitionResult>",  # the hosted span
        "List<OcrInput>",
        "Dictionary<string, RecognitionResult>",
        "RecognitionResult[]",
        "Optional[OcrInput]",
        "Task<List<RecognitionResult>>",
        "List<LinesResult>",  # a declared signature, whole
        "RecognitionResult.RecognitionLinesResult",  # unchanged plain rule
    ],
)
def test_composed_fact_values_are_grounded(span: str) -> None:
    assert _judge(span)


@pytest.mark.parametrize(
    "span",
    [
        "List<InventedResult>",  # an invented class inside a generic
        "Dictionary<string, OcrInput2>",
        "List<RecognitionResult, Bogus>",  # one grounded, one invented
        "RecognitionResult.Bogus",  # a real type with a wrong member
        "List<RecognitionResult.Bogus>",  # ... inside a generic
        "OcrInput.InventedMethod()",  # an invented method
        "List<int>",  # no fact value in it at all
        "List",  # a bare wrapper is not a fact
        "Unknown",  # a single ungrounded token is never composed
        "List of RecognitionResult",  # prose, not a type expression
        "List<RecognitionResult> and more",
        "generate(RecognitionResult, data)",  # a call signature is not a type expression
        "OcrInput(InputType type)",
        "v<version>",  # placeholder syntax, not a generic over fact values
        "<html>",
        "object[property]",  # a primitive takes no arguments
        "string<RecognitionResult>",
        "Dictionary<string, ocr.Bogus>",
        "aspose-words",  # an external package name stays refused (Words Python)
        "aspose.words",
    ],
)
def test_ungrounded_spans_stay_refused(span: str) -> None:
    assert not _judge(span)


def test_declared_type_texts_are_source_verbatim_only() -> None:
    assert declared_type_texts(OCR) == {"List<RecognitionResult>", "List<LinesResult>"}
    contradicted = dataclasses.replace(
        OCR.facts[-1], polarity="CONTRADICTED", attributes={"bases": "List<Ghost>"}
    )
    assert declared_type_texts(FactsDocument(OCR.repository, OCR.source_revision, (contradicted,))) == frozenset()


def test_generic_type_names_hold_no_api_names() -> None:
    # The closed list is type constructors and primitives; growing it per candidate is the defect.
    assert len(GENERIC_TYPE_NAMES) < 100
    assert not {"Scene", "Workbook", "Document", "RecognitionResult"} & GENERIC_TYPE_NAMES


def _readme_with(span: str, facts: FactsDocument) -> list[str]:
    base = _candidate(facts=facts)
    line = f"\nOcrOutput inherits `{span}` and holds the results.\n"
    readme = base.readme.replace("\n## ", line + "\n## ", 1)
    assert f"`{span}`" in readme
    candidate = dataclasses.replace(base, readme=readme)
    return [f.detail for f in unit_failures(candidate) if "is not a fact value" in f.detail]


def test_bc04_end_to_end_accepts_the_hosted_span_and_refuses_an_invented_one() -> None:
    assert _readme_with("List<RecognitionResult>", OCR) == []
    assert _readme_with("List<InventedResult>", OCR) == [
        "code span 'List<InventedResult>' is not a fact value"
    ]
    # Without the facts the span is refused exactly as before this fix.
    assert _readme_with("List<RecognitionResult>", FACTS) == [
        "code span 'List<RecognitionResult>' is not a fact value"
    ]
