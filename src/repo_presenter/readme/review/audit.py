"""The mechanical audit of an ``unsupported_claim`` finding: where do the quoted claim's distinctive
terms (identifiers, numbers, quoted phrases) occur in the evidence?

An unsupported claim names no product fact (it is a claim none supports), so the contract cannot
check it against one. What code can do is look the quoted claim's distinctive terms up in the
SUPPORTED fact values and in the original README, and record the result on the finding so a human
reading a blocked candidate sees at once whether the reviewer's claim is plausible (the terms occur
nowhere) or may be wrong (every term is a fact value).

The audit is information and never a clearance. That a quote contains the value of a SUPPORTED fact
is exactly the old repository's measured incident (27 of 30 real REJECTs folded to ACCEPT,
``docs/MISSION_AUTHORITY.md``): the terms of a false claim are often all real ("converts glTF to
STL" names two supported formats and no supported conversion), so term overlap cannot prove a
claim supported. No registered clearance covers ``unsupported_claim``; the finding keeps blocking.
"""

from __future__ import annotations

import re

from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.review.matching import loosely_in

MAX_TERMS = 12
_PATTERNS = (
    re.compile(r"`([^`\n]{2,80})`"),
    re.compile(r'"([^"\n]{3,80})"'),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:(?:\.|::)[A-Za-z_][A-Za-z0-9_]*)+\b"),
    re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b"),
    re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b"),
    re.compile(r"\b\d+(?:\.\d+)*[A-Za-z%]{0,2}"),
)
_NOT_TERMS = frozenset({"e.g", "i.e", "etc"})


def distinctive_terms(quote: str) -> tuple[str, ...]:
    """The identifiers, numbers and quoted phrases of ``quote``, in order of appearance."""
    found: dict[int, str] = {}
    for pattern in _PATTERNS:
        for match in pattern.finditer(quote):
            term = (match.group(1) if pattern.groups else match.group(0)).strip()
            if term.casefold() in _NOT_TERMS or (term.isdigit() and len(term) < 2):
                continue
            found.setdefault(match.start(), term)
    ordered = list(dict.fromkeys(found[start] for start in sorted(found)))
    return tuple(ordered[:MAX_TERMS])


def audit_unsupported_claim(
    quote: str, *, facts: FactsDocument, original_readme: str
) -> str:
    """One sentence on where ``quote``'s distinctive terms occur; it decides nothing."""
    terms = distinctive_terms(quote)
    ending = (
        "no registered clearance proves an unsupported claim false, so it blocks until the "
        "candidate is revised"
    )
    if not terms:
        return (
            "audit: the quoted claim has no distinctive term (identifier, number or quoted "
            f"phrase) to look up; {ending}"
        )
    supported = sorted(
        (fact for fact in facts.facts if fact.polarity == "SUPPORTED"),
        key=lambda fact: fact.id,
    )
    in_facts: dict[str, str] = {}
    in_readme: list[str] = []
    nowhere: list[str] = []
    for term in terms:
        owner = next((f.id for f in supported if loosely_in(term, f.value)), None)
        if owner is not None:
            in_facts[term] = owner
        elif loosely_in(term, original_readme):
            in_readme.append(term)
        else:
            nowhere.append(term)
    parts = []
    if in_facts:
        shown = ", ".join(f"{term} -> {fid}" for term, fid in in_facts.items())
        parts.append(f"found in SUPPORTED fact values: {shown}")
    if in_readme:
        parts.append(f"found only in the original README: {in_readme}")
    if nowhere:
        parts.append(
            f"in no SUPPORTED fact value and not in the original README: {nowhere}"
        )
    return f"audit: distinctive terms {list(terms)}; {'; '.join(parts)}; {ending}"
