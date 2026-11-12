"""TC-017b work item 1: ``readme/validation/line_provenance.py``'s inherited/generated classifier.

Every fixture is synthetic. The classifier's only job is the byte-traceability rule: a line or
span counts as "inherited" exactly when, after whitespace normalization, it is quoted inside a
SUPPORTED ``inherited_unit`` fact's own value; everything else is "generated" -- including a
false statement, a CONTRADICTED or UNRESOLVED ``inherited_unit``, and a short span too generic to
mean anything (the same 12-character floor ``surface_claims.py``'s own former ``_Origin`` used).
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.validation.claims import _lines
from repo_presenter.readme.validation.line_provenance import (
    classify,
    classify_span,
    inherited_values,
    is_inherited,
    unit_for,
)

REVISION = "a" * 40


def _unit(number: str, text: str, *, polarity: str = "SUPPORTED") -> Fact:
    return Fact(
        f"inherited_unit:{number}",
        "inherited_unit",
        text,
        (Evidence("README.md", "lines 1-9; paragraph; under Acme > Scope"),),
        polarity=polarity,  # type: ignore[arg-type]
    )


def _facts(*facts: Fact) -> FactsDocument:
    return FactsDocument("acme/widgets", REVISION, facts)


MAINTAINER_SENTENCE = "This library does not support streaming decode of multi-gigabyte files."


def test_a_sentence_quoted_verbatim_from_a_supported_unit_is_inherited() -> None:
    facts = _facts(_unit("010", MAINTAINER_SENTENCE))
    assert unit_for(MAINTAINER_SENTENCE, facts) == "inherited_unit:010"
    assert is_inherited(MAINTAINER_SENTENCE, facts) is True


def test_a_pipeline_authored_sentence_with_no_matching_unit_is_generated() -> None:
    facts = _facts(_unit("010", MAINTAINER_SENTENCE))
    invented = "The library provides first-class support for streaming decode."
    assert unit_for(invented, facts) is None
    assert is_inherited(invented, facts) is False


def test_whitespace_and_backtick_styling_never_breaks_an_otherwise_exact_match() -> None:
    sentence = "The `Workbook` class exposes `Save` and `Load` for every supported format."
    facts = _facts(_unit("020", sentence))
    # Re-wrapped onto two lines, with doubled internal spaces and curly dashes: still the same
    # text after whitespace normalization.
    rewrapped = "The  `Workbook`  class exposes\n`Save` and `Load`  for every supported format."
    assert is_inherited(rewrapped, facts) is True


def test_a_contradicted_or_unresolved_unit_never_counts_as_inherited() -> None:
    contradicted = _facts(_unit("030", MAINTAINER_SENTENCE, polarity="CONTRADICTED"))
    unresolved = _facts(_unit("031", MAINTAINER_SENTENCE, polarity="UNRESOLVED"))
    assert is_inherited(MAINTAINER_SENTENCE, contradicted) is False
    assert is_inherited(MAINTAINER_SENTENCE, unresolved) is False


def test_a_short_span_is_never_traceable_however_it_matches() -> None:
    # "the API" is 7 characters: shorter than the floor, even though it is a substring of a real
    # unit's text -- too generic a match to mean the pipeline quoted the maintainers.
    facts = _facts(_unit("040", "Read the API reference below for the full surface."))
    assert unit_for("the API", facts) is None
    assert is_inherited("the API", facts) is False


def test_inherited_values_excludes_non_supported_units() -> None:
    facts = _facts(
        _unit("050", "Alpha statement."),
        _unit("051", "Beta statement.", polarity="CONTRADICTED"),
    )
    ids = {fact_id for fact_id, _ in inherited_values(facts)}
    assert ids == {"inherited_unit:050"}


def test_classify_maps_every_non_fenced_line_and_skips_fences() -> None:
    readme = (
        f"{MAINTAINER_SENTENCE}\n"
        "\n"
        "The library provides first-class support for streaming decode.\n"
        "\n"
        "```python\n"
        f"{MAINTAINER_SENTENCE}\n"
        "```\n"
    )
    facts = _facts(_unit("060", MAINTAINER_SENTENCE))
    lines = _lines(readme)
    mapping = classify(lines, facts)
    assert mapping[0] == "inherited"
    assert mapping[2] == "generated"
    # The fenced copy of the very same sentence is left out of the mapping entirely: a fence's
    # provenance is BC-03/BC-08's concern (readme/validation/provenance.py), not this module's.
    assert 5 not in mapping


def test_classify_span_matches_classify_for_the_same_text() -> None:
    facts = _facts(_unit("070", MAINTAINER_SENTENCE))
    assert classify_span(MAINTAINER_SENTENCE, facts) == "inherited"
    assert classify_span("An entirely different, pipeline-authored sentence here.", facts) == (
        "generated"
    )
