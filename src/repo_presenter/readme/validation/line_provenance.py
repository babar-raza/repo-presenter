"""TC-017b work item 1: which printed README text is the maintainers' own, and which is this
pipeline's own authored prose.

``readme/validation/surface_claims.py``'s rules (h)-(m) already distinguish the two per sentence
(the module-private ``_Origin`` class), because rule (m) -- the generator guard -- must judge
pipeline-authored prose only, never a sentence quoted verbatim from the maintainers' own README.
That logic lived inside ``surface_claims.py`` alone, with no name another module could import, so
this card's new checks (the closed/open-world rule of work item 2, the probe wiring of work item
3, and the verification-narrative ban of work item 4) would each have had to re-derive the same
notion, or worse, a slightly different one. This module is the one place that notion now lives;
``surface_claims.py`` imports it rather than keeping its own copy.

A line or span is ``"inherited"`` when it is byte-traceable, after whitespace normalization, to a
``SUPPORTED`` ``inherited_unit`` fact's own value -- the pinned source README's own text, chunked
into units by the reconciliation stage (``readme/reconciliation/dispositions.py``'s own
docstring: a unit a disposition keeps, moves, or rewrites still carries the maintainers' original
text in its fact value, regardless of which disposition the candidate gave it). This reuses that
existing record rather than re-deriving provenance by diffing the printed README against a second,
independently-fetched copy of the live one: the information already exists on the facts document
every check in this package already reads, and a second, separately-maintained diff would be a new
place for the same answer to disagree with itself.

Everything else -- every sentence this pipeline composed itself, whether it is true or false --
is ``"generated"``. A ``"generated"`` classification is never, by itself, a finding; it only says
which rule family judges the text (open-world for inherited material, closed-world for generated
material, per work item 2)."""

from __future__ import annotations

from typing import Literal

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.validation.claims import _Line

Provenance = Literal["inherited", "generated"]

#: Below this length a normalized span matches too much unrelated text to mean anything (a bare
#: word, a table pipe) -- the same floor ``surface_claims.py``'s own ``_Origin.unit`` already used.
MIN_TRACEABLE_LENGTH = 12


def _plain(text: str) -> str:
    """Text compared the same way the rest of this package already does: no code ticks, plain
    hyphens, single spaces -- so a unit's own whitespace or backtick styling never breaks a byte
    match that is otherwise exact."""
    return " ".join(text.replace("`", "").replace("‑", "-").replace("–", "-").split())


def _normalized_span(text: str) -> str:
    """``text`` stripped of the markdown framing a printed line or sentence may carry (a list
    marker, a table pipe, surrounding whitespace) before the whitespace-normalized match."""
    return _plain(text.strip().strip("|").strip().lstrip("-*+ ").strip())


def inherited_values(facts: FactsDocument) -> tuple[tuple[str, str], ...]:
    """(fact id, whitespace-normalized value) of every ``SUPPORTED`` ``inherited_unit`` fact --
    the pinned source README's own text, already chunked into units. A ``CONTRADICTED`` or
    ``UNRESOLVED`` ``inherited_unit`` is not a thing the live README actually printed this way (or
    is not confirmed as such), so it is never a source of "inherited" provenance."""
    return tuple(
        (fact.id, _plain(fact.value))
        for fact in facts.by_kind("inherited_unit")
        if fact.polarity == "SUPPORTED"
    )


def unit_for(text: str, facts: FactsDocument) -> str | None:
    """The ``inherited_unit`` fact id that quotes ``text`` verbatim (after whitespace
    normalization), or ``None`` when no such unit exists -- the pipeline authored ``text`` itself.

    The single source of truth for "inherited" vs. "generated" at sentence/span granularity:
    every other function here, and every caller in ``surface_claims.py``, is built on this one
    check so there is exactly one place the byte-traceability rule is stated.
    """
    wanted = _normalized_span(text)
    if len(wanted) < MIN_TRACEABLE_LENGTH:
        return None
    return next(
        (fact_id for fact_id, value in inherited_values(facts) if wanted in value), None
    )


def is_inherited(text: str, facts: FactsDocument) -> bool:
    """Whether ``text`` is the maintainers' own words, byte-traceable to a pinned-source unit."""
    return unit_for(text, facts) is not None


def classify(lines: list[_Line], facts: FactsDocument) -> dict[int, Provenance]:
    """Every non-fenced printed line's origin, at the same physical-line granularity
    ``readme/validation/claims.py``'s own ``_lines`` reader already uses for the rest of this
    package: ``"inherited"`` when the line's own text is byte-traceable (after whitespace
    normalization) to a unit of the pinned source, ``"generated"`` otherwise.

    A fenced line is left out: BC-03/BC-08 (``readme/validation/provenance.py``'s
    ``example_failures``/``protected_failures``) already judge a code fence's own provenance by a
    different, code-aware notion (a planned verified example vs. a retained, unverified one), and
    this module does not duplicate that.
    """
    return {
        line.index: ("inherited" if is_inherited(line.text, facts) else "generated")
        for line in lines
        if not line.in_fence
    }


def classify_span(text: str, facts: FactsDocument) -> Provenance:
    """One statement's origin (a sentence that may wrap several physical lines, as
    ``surface_claims.py``'s own ``_sentences`` yields it): the per-span counterpart to
    ``classify``'s per-line mapping, built on the exact same ``unit_for`` check."""
    return "inherited" if is_inherited(text, facts) else "generated"
