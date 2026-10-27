"""The closed catalogue of clearances (plan D3) -- the only way a reviewer finding stops blocking.

A clearance is a pure function of (finding, candidate README, original README, facts) that returns
a ``Clearance`` proof or ``None``. It clears a finding only when it disproves the whole of the
finding's single typed claim; a claim that is partly true, undecidable, mislabelled or made of
strings too short to tell from coincidence returns ``None`` and the finding keeps blocking.

The catalogue is exactly four functions and nothing else:

* ``absence_present``  -- every ``absent`` string occurs in the section the finding names.
* ``absence_unsourced`` -- no ``absent`` string occurs in the candidate, and every one occurs in
  neither the original README nor any fact value: the finding asks for text nobody wrote.
* ``names_supported``  -- every ``unsupported_names`` entry equals a SUPPORTED fact value (or the
  package name).
* ``omission_present`` -- every ``omission`` id and phrase is rendered by the named section.

Deliberately NOT here, each with its evidence (plan D3): "the quote contains the literal value of a
SUPPORTED fact" -- the old repository's measured incident, 27 of 30 real REJECTs folded to ACCEPT
(``docs/MISSION_AUTHORITY.md``); word-overlap "restated" absence; a bare member name resolved by a
dotted symbol's tail; similarity, majority, a second reader, the reviewer retracting itself, or
"the original README says it too". Adding a clearance requires a failing adversarial test first.

Ported (ADAPT) from the old ``review.py``: ``absence_defect`` / ``absence_partition`` (kept: the
section-scoped presence search, the "nowhere in the evidence" test, and the lesson that an
``absent`` string the finding quotes itself is not a claim of absence; dropped: the restated-match
tier and the combined "settled" ruling), ``name_denial_defect`` / ``_denied_names`` (kept: name
normalisation, multi-word entries are claims not names, a cited non-SUPPORTED fact blocks the
clearance; dropped: tail/leading-segment resolution and the not-in-section allowance),
``omission_partition`` / ``_id_rendered`` (kept: the id is rendered when its literal value is in
the section; dropped: the content-unit citation shortcut and the unrestorable tier).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace

from repo_presenter.core.facts import Fact, FactsDocument
from repo_presenter.readme.review.findings import (
    CLEARANCES_FOR_KIND,
    Clearance,
    Finding,
    _seal_clearance,
)
from repo_presenter.readme.review.matching import (
    MIN_CLAIM_CHARS,
    loosely_in,
    present,
    section_scope,
    spaced,
)

#: Fact kinds whose value is a name a reader can write, for ``names_supported``.
NAME_KINDS = frozenset({"public_symbol", "import_path", "identity", "format"})


@dataclass(frozen=True)
class ClearanceContext:
    candidate_readme: str
    original_readme: str
    facts: FactsDocument


def _only(finding: Finding, kind: str) -> bool:
    """The finding is an LLM claim of ``kind`` that fills exactly that kind's typed field."""
    if finding.source != "llm" or finding.claim_kind != kind or not finding.blocking:
        return False
    filled = {
        "absence": bool(finding.absent),
        "name_denial": bool(finding.unsupported_names),
        "omission": finding.omission is not None,
    }
    return filled.pop(kind) and not any(filled.values())


def _claims(finding: Finding) -> tuple[str, ...] | None:
    """The finding's non-blank ``absent`` strings, or ``None`` when one cannot be decided: too
    short to tell from coincidence, or a string the finding quotes itself (the reviewer then
    points at it as present, so its list is not a claim of absence)."""
    stripped = [item.strip() for item in finding.absent]
    if not stripped or not all(stripped):
        return None
    claims = tuple(dict.fromkeys(stripped))
    quote = spaced(finding.quote)
    for claim in claims:
        if len(spaced(claim)) < MIN_CLAIM_CHARS or (quote and spaced(claim) in quote):
            return None
    return claims


def absence_present(finding: Finding, context: ClearanceContext) -> Clearance | None:
    if not _only(finding, "absence") or (claims := _claims(finding)) is None:
        return None
    scope = section_scope(finding.section_id, context.candidate_readme)
    if scope is None or not all(present(claim, scope) for claim in claims):
        return None
    evidence = tuple(
        f"{claim!r} occurs in section {finding.section_id}" for claim in claims
    )
    return _seal_clearance("absence_present", finding, evidence)


def _evidence_text(context: ClearanceContext) -> str:
    values = (fact.value for fact in context.facts.facts)
    return "\n".join([context.original_readme, *values])


def absence_unsourced(finding: Finding, context: ClearanceContext) -> Clearance | None:
    if not _only(finding, "absence") or (claims := _claims(finding)) is None:
        return None
    evidence_text = _evidence_text(context)
    for claim in claims:
        if loosely_in(claim, context.candidate_readme) or loosely_in(
            claim, evidence_text
        ):
            return None
    evidence = tuple(
        f"{claim!r} occurs in no candidate text, no original README text and no fact value"
        for claim in claims
    )
    return _seal_clearance("absence_unsourced", finding, evidence)


def _name(entry: str) -> str | None:
    """One denied identifier as a reader writes it, or ``None`` when the entry is not a name
    (several words are a claim, not an identifier)."""
    name = entry.strip().strip("'\"`").strip().removesuffix("()").replace("::", ".")
    if not name or len(name.split()) > 1:
        return None
    return name


def _supported_names(facts: FactsDocument) -> dict[str, str]:
    names: dict[str, str] = {}
    for fact in facts.facts:
        if fact.polarity != "SUPPORTED":
            continue
        if fact.kind in NAME_KINDS or fact.id == "package:name":
            names.setdefault(fact.value.replace("::", "."), fact.id)
    return names


def names_supported(finding: Finding, context: ClearanceContext) -> Clearance | None:
    if not _only(finding, "name_denial"):
        return None
    by_id: Mapping[str, Fact] = {fact.id: fact for fact in context.facts.facts}
    for fact_id in finding.fact_ids:
        cited = by_id.get(fact_id)
        if (
            cited is not None
            and cited.kind != "inherited_unit"
            and cited.polarity != "SUPPORTED"
        ):
            return None
    supported = _supported_names(context.facts)
    resolved: list[str] = []
    for entry in finding.unsupported_names:
        name = _name(entry)
        if name is None or name not in supported:
            return None
        resolved.append(
            f"{name!r} equals the value of SUPPORTED fact {supported[name]}"
        )
    return _seal_clearance("names_supported", finding, tuple(resolved))


def omission_present(finding: Finding, context: ClearanceContext) -> Clearance | None:
    claim = finding.omission
    if not _only(finding, "omission") or claim is None or claim.is_empty():
        return None
    if claim.section_id != finding.section_id:
        return None
    scope = section_scope(finding.section_id, context.candidate_readme)
    if scope is None:
        return None
    by_id: Mapping[str, Fact] = {fact.id: fact for fact in context.facts.facts}
    proofs: list[str] = []
    for fact_id in claim.missing_ids:
        fact = by_id.get(fact_id)
        if (
            fact is None
            or fact.polarity != "SUPPORTED"
            or not present(fact.value, scope)
        ):
            return None
        proofs.append(f"{fact_id} is rendered by section {finding.section_id}")
    for quote in claim.missing_quotes:
        if not present(quote, scope):
            return None
        proofs.append(f"{quote!r} occurs in section {finding.section_id}")
    return _seal_clearance("omission_present", finding, tuple(proofs))


Clearer = Callable[[Finding, ClearanceContext], Clearance | None]

#: The whole catalogue. A test pins this to exactly the four names plan D3 lists.
CLEARANCES: Mapping[str, Clearer] = {
    "absence_present": absence_present,
    "absence_unsourced": absence_unsourced,
    "names_supported": names_supported,
    "omission_present": omission_present,
}


def apply_clearances(finding: Finding, context: ClearanceContext) -> Finding:
    """The finding, CLEARED by the first registered clearance for its claim kind that proves it,
    else unchanged. The one place in the code base that constructs a CLEARED finding."""
    if finding.source != "llm" or not finding.blocking:
        return finding
    for name in CLEARANCES_FOR_KIND.get(finding.claim_kind, ()):
        proof = CLEARANCES[name](finding, context)
        if proof is not None:
            return replace(finding, status="CLEARED", clearance=proof)
    return finding


__all__ = [
    "CLEARANCES",
    "ClearanceContext",
    "absence_present",
    "absence_unsourced",
    "apply_clearances",
    "names_supported",
    "omission_present",
]
