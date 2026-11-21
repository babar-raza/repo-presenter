"""BL-541: a Java README may call a bean accessor a "property".

Hosted Lane R PSD Java (run 44775343067, source d808d1d): the maintainers' bullet reads "the header
properties `getWidth()`, `getHeight()`, `getBitsPerChannel()`, `getColorMode()`, `getCompression()` and
`getChannelsCount()`" (their published README, line 52). The facts record each as a ``method`` (they are
Java methods), so BC-14 / ``claim_contradiction`` called the sentence false ("the README calls
`PsdImage.getWidth` a property ... the facts record it as a method"); the zero-call restore that put the
bullet back was rolled back for that new failure, the BC-17 losses it answered (``getBitsPerChannel()``,
``getCompression()``, ``getChannelsCount()`` ...) stayed for three settle rounds, and the cell ended
"no LLM review was made". In Java a getter IS the bean property, so the sentence is true; a method that is
no accessor, another ecosystem and another kind word keep the finding.
"""

from __future__ import annotations

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.claims import claim_findings

BULLET = (
    "- Loads a PSD document, or an RGB PSB large-format document, from a file path with\n"
    "  `PsdImage.load(String)` or from a stream with `PsdImage.load(InputStream)`, and reads the header\n"
    "  properties `getWidth()`, `getHeight()`, `getBitsPerChannel()`, `getColorMode()`,\n"
    "  `getCompression()` and `getChannelsCount()`."
)
ACCESSORS = ("getWidth", "getHeight", "getBitsPerChannel", "getColorMode", "getCompression", "getChannelsCount")


def _facts(ecosystem: str, owner: str = "org.aspose.psd.PsdImage", extra: tuple[str, ...] = ()) -> FactsDocument:
    path = "main/org/aspose/psd/PsdImage.java"

    def method(name: str) -> Fact:
        return Fact(
            f"public_symbol:{owner.lower()}.{name.lower()}", "public_symbol", f"{owner}.{name}",
            (Evidence(path, "line 58; method; public by declaration"),),
            attributes={"member_kind": "method", "symbol_kind": "method", "signature": f"int {name}()"},
        )

    return FactsDocument(
        "aspose-psd-foss/Aspose.PSD-FOSS-for-Java", "d808d1d",
        (
            Fact("identity:ecosystem", "identity", ecosystem, (Evidence("registry"),)),
            Fact(
                f"public_symbol:{owner.lower()}", "public_symbol", owner,
                (Evidence(path, "line 1; class; public by declaration"),),
                attributes={"symbol_kind": "class", "signature": "class PsdImage", "type_kind": "class"},
            ),
            *[method(name) for name in (*ACCESSORS, *extra)],
        ),
    )


def _kind_findings(text: str, facts: FactsDocument) -> list[str]:
    return [f.detail for f in claim_findings(text, facts) if f.detail.startswith("the README calls")]


def test_the_maintainers_header_properties_bullet_is_not_a_finding_for_java() -> None:
    assert _kind_findings(BULLET, _facts("java")) == []


@pytest.mark.parametrize("ecosystem", ["net", "python", "go"])
def test_the_same_words_stay_a_finding_in_another_ecosystem(ecosystem: str) -> None:
    # C#/Python properties are a language construct; a method of any such ecosystem is no property
    assert _kind_findings(BULLET, _facts(ecosystem))


def test_a_java_method_that_is_no_accessor_is_still_called_out() -> None:
    text = "The `PsdImage` class exposes the properties `getWidth()` and `flatten()`."
    found = _kind_findings(text, _facts("java", extra=("flatten",)))
    assert len(found) == 1 and "`PsdImage.flatten`" in found[0] and "PsdImage.getWidth" not in found[0]


def test_another_kind_word_is_not_relaxed_for_java_accessors() -> None:
    text = "The `PsdImage` class has the fields `getWidth()` and `getHeight()`."
    assert _kind_findings(text, _facts("java"))
