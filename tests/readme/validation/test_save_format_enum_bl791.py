"""BL-791 (hosted Lane L Slides Python, run 44414886517 and 44993661753's sibling cells).

The real shape, from the pinned source (aspose-slides-foss/Aspose.Slides-FOSS-for-Python @ 4e63447):
the README says "Save to ``.pptx`` (the default) or the related ``.pptm``, ``.ppsx``, ``.ppsm``,
``.potx``, and ``.potm`` Office Open XML variants through ``SaveFormat``", hard-wrapped so the verb
is on the line before the list. The facts hold ``.pptx`` as the one executed format and
``SaveFormat.PPTM`` / ``PPSX`` / ``PPSM`` / ``POTX`` / ``POTM`` as SUPPORTED enum members, so rule (g)
refused the live README's own sentence (and Lane L refused the candidate on that residual).
BL-651's load-format declaration is extended to the save direction, for a sentence about writing.
"""

from __future__ import annotations

from test_registry_checks import FACTS

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.claims import claim_findings

SENTENCE = (
    "- Open, create, and save presentations through `Presentation`. Save\n"
    "  to `.pptx` (the default) or the related `.pptm`, `.ppsx`, `.ppsm`, `.potx`, and `.potm` Office\n"
    "  Open XML variants through `SaveFormat`.\n"
)


def _fact(fact_id: str, kind: str, value: str, **attributes: object) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md", "x"),), attributes=attributes or None)


def _enum(enum: str, names: tuple[str, ...], polarity: str = "SUPPORTED") -> tuple[Fact, ...]:
    return tuple(
        Fact(
            f"enum_member:{enum.lower()}.{name.lower()}", "enum_member", f"{enum}.{name}",
            (Evidence("SaveFormat.py", "x"),), polarity=polarity,  # type: ignore[arg-type]
            attributes={"enum": enum, "member_kind": "enum"},
        )
        for name in names
    )


def _findings(readme: str, *facts: Fact) -> list[str]:
    document = FactsDocument(
        FACTS.repository, FACTS.source_revision,
        (*FACTS.facts, _fact("format:output.pptx", "format", ".pptx"), *facts),
    )
    return [f.detail for f in claim_findings(readme, document) if "lists the format" in f.detail]


SAVE = _enum("slides_foss.export.SaveFormat", ("PPTX", "PPTM", "PPSX", "PPSM", "POTX", "POTM"))


def test_the_wrapped_save_sentence_is_stated_by_the_save_format_enum() -> None:
    assert _findings(SENTENCE, *SAVE) == []


def test_without_the_enum_the_sentence_is_still_refused() -> None:
    (detail,) = _findings(SENTENCE)
    assert ".pptm" in detail and ".potm" in detail


def test_an_extension_the_enum_does_not_declare_stays_refused() -> None:
    (detail,) = _findings(SENTENCE.replace("`.potm`", "`.xlsx`"), *SAVE)
    assert ".xlsx" in detail and ".pptm" not in detail


def test_a_contradicted_member_does_not_count() -> None:
    both = _enum("slides_foss.export.SaveFormat", ("PPTX", "PPSX", "PPSM", "POTX", "POTM")) + _enum(
        "slides_foss.export.SaveFormat", ("PPTM",), polarity="CONTRADICTED"
    )
    (detail,) = _findings(SENTENCE, *both)
    assert ".pptm" in detail


def test_a_save_enum_does_not_state_a_load_sentence_and_a_load_enum_does_not_state_a_save_sentence() -> None:
    load_sentence = "- Reads `.pptx`, `.pptm` and `.ppsx` presentations.\n"
    assert _findings(load_sentence, *SAVE) != []
    load = _enum("slides_foss.LoadFormat", ("PPTM", "PPSX"))
    assert _findings(load_sentence, *load) == []
    assert _findings(SENTENCE, *load) != []
