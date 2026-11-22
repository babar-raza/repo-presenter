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

import re
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, replace

from repo_presenter.core.facts import Fact, FactsDocument
from repo_presenter.readme.review.derivation import Derivation, flag_is_about_count, flag_within_sentences
from repo_presenter.readme.review.findings import (
    CLEARANCES_FOR_KIND,
    PROVENANCE_CLEARANCES_FOR_KIND,
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
NAME_KINDS = frozenset({"public_symbol", "enum_member", "import_path", "identity", "format"})


#: Which of a candidate's lines (1-based) a deterministic stage printed from SUPPORTED facts, asked lazily
#: for the lines a finding cites (``review.derivation.lane_r_derivation``); ``None`` when it cannot say.
Deriver = Callable[[Collection[int]], Derivation | None]


@dataclass(frozen=True)
class ClearanceContext:
    candidate_readme: str
    original_readme: str
    facts: FactsDocument
    #: Lane R only, and only where the caller holds the plan, units and dispositions the candidate was
    #: rendered from (the cascade). Absent: ``derived_from_supported_facts`` clears nothing.
    derive: Deriver | None = None


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


def _api_symbol_rendered(fact: Fact, facts: FactsDocument, scope: str) -> str:
    """How the API Reference prints SUPPORTED public symbol ``fact``, or ``""`` when it does not (BL-551).

    The renderer never prints a symbol's qualified value ("Aspose.Cells_FOSS.Workbook.Save"): a type is a
    ``| `Workbook` |`` row or a ``### Workbook`` heading, a member a ``- `Save`:`` bullet under its owner's
    ``### Workbook`` heading (``renderer._api_reference``, ``api_reference_names``). An omission claim naming
    such a fact as absent from ``api_reference`` therefore could never be cleared by the literal-value test,
    although the section prints it (hosted Cells C++ refresh run 44787653565, S2-F03/S2-F04 on the Workbook and
    Worksheet rows). It is cleared only for a symbol printed exactly where the renderer prints it: a member's
    bullet counts only inside its own owner's block, and a bare common word elsewhere in the section counts for
    nothing."""
    if fact.kind != "public_symbol":
        return ""
    from repo_presenter.readme.composition.renderer import api_reference_names

    names = api_reference_names(facts)
    kind = (fact.attributes or {}).get("symbol_kind", "")
    if kind in ("class", "enum"):
        name = re.escape(names.get(fact.value, fact.value.rsplit(".", 1)[-1]))
        found = re.search(rf"(?m)^(?:\|\s*`{name}`\s*\||###\s+{name}\s*$)", scope)
        return f"`{names.get(fact.value, '')}`" if found else ""
    owner_value, _, member = fact.value.rpartition(".")
    owner = next((f for f in facts.by_kind("public_symbol") if f.value == owner_value), None)
    if owner is None or owner.polarity != "SUPPORTED" or not member:
        return ""
    owner_name = re.escape(names.get(owner_value, owner_value.rsplit(".", 1)[-1]))
    block = re.search(rf"(?ms)^###\s+{owner_name}\s*$(.*?)(?=^###\s|^</details>|\Z)", scope)
    if block is None:
        return ""
    found = re.search(rf"(?m)^-\s+`{re.escape(member)}`\s*:", block.group(1))
    return f"`{member}` under {owner_name}" if found else ""


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
        if fact is None or fact.polarity != "SUPPORTED":
            return None
        if present(fact.value, scope):
            proofs.append(f"{fact_id} is rendered by section {finding.section_id}")
        elif finding.section_id == "api_reference" and (
            shown := _api_symbol_rendered(fact, context.facts, scope)
        ):
            proofs.append(f"{fact_id} is rendered by section {finding.section_id} as {shown}")
        else:
            return None
    for quote in claim.missing_quotes:
        if not present(quote, scope):
            return None
        proofs.append(f"{quote!r} occurs in section {finding.section_id}")
    return _seal_clearance("omission_present", finding, tuple(proofs))


def _quoted_lines(quote: str, rows: list[str]) -> frozenset[int] | None:
    """The 1-based candidate lines ``quote`` is, whole line for whole line; ``None`` when any non-blank quoted
    line is not exactly a candidate line (a fragment of a line is never located: an authored clause joined to a
    printed lead-in is one line, and it is not the renderer's)."""
    found: set[int] = set()
    wanted = [row.strip() for row in quote.splitlines() if row.strip()]
    if not wanted:
        return None
    for text in wanted:
        hits = [number for number, row in enumerate(rows, 1) if row.strip() == text]
        if not hits:
            return None
        found.update(hits)
    return frozenset(found)


def derived_from_supported_facts(finding: Finding, context: ClearanceContext) -> Clearance | None:
    """BL-400: every line the finding quotes is printed by a deterministic stage from SUPPORTED facts.

    The production review was shown lines the renderer prints from facts alone (the opening's format
    sentence is an authored unit slot holding the sentence ``renderer._scope_statement`` prints), and a model
    flag on one blocked the seal although the M9 audit clears the same line (``scripts/run_m9_auditor.py``,
    ``review.derivation``: the same predicate, one implementation). A line qualifies only when the renderer's
    own re-derivation reproduces it with every authored unit replaced by a sentinel (an authored sentence is
    never cleared), every fact it states is SUPPORTED, no claim detector or open findings-register row
    refutes it, and it is in no known-false class (counts, Enterprise Edition naming, accessor wording,
    behaviour claims) unless its provenance verifies. Anything undecidable returns ``None``."""
    if (
        finding.source != "llm"
        or not finding.blocking
        or finding.claim_kind not in PROVENANCE_CLEARANCES_FOR_KIND
        or context.derive is None
    ):
        return None
    lines = _quoted_lines(finding.quote, context.candidate_readme.splitlines())
    if not lines:
        return None
    derived = context.derive(lines)
    rows = context.candidate_readme.splitlines()
    if derived is None:
        return None
    # BL-801/BL-802: a verified member-list row, or a flag that is only the renderer-appended count sentence
    verified = {
        number: derived.statements[number] if number in derived.statements else derived.sentences[number][1]
        for number in lines
        if number in derived.statements
        or (number in derived.sentences and flag_within_sentences(finding.message, derived.sentences[number][0]))
    }
    if not lines <= (derived.clearable | frozenset(verified)):
        return None
    if any(
        number in derived.corrected and not flag_is_about_count(finding.message, rows[number - 1])
        for number in lines
    ):
        return None  # BL-543: a flag on another statement of a count-corrected paragraph stays
    evidence = tuple(
        f"line {number} is printed from SUPPORTED facts by a deterministic stage (zero-call re-derivation); "
        "no register row or claim detector refutes it; "
        + (
            f"verified by its provenance ({derived.provenance[number]})"
            if number in derived.provenance
            else f"verified against SUPPORTED facts ({verified[number]})"
            if number in verified
            else "in no known-false class"
        )
        + (f"; cites {', '.join(derived.cited[number])}" if number in derived.cited else "")
        for number in sorted(lines)
    )
    return _seal_clearance("derived_from_supported_facts", finding, evidence)


Clearer = Callable[[Finding, ClearanceContext], Clearance | None]

#: The whole catalogue. A test pins this to exactly the four names plan D3 lists.
CLEARANCES: Mapping[str, Clearer] = {
    "absence_present": absence_present,
    "absence_unsourced": absence_unsourced,
    "names_supported": names_supported,
    "omission_present": omission_present,
}


#: The provenance clearances (BL-400), kept apart from the four typed ones above: a test pins ``CLEARANCES`` to
#: exactly plan D3's four names, and this catalogue to exactly the one name ``PROVENANCE_CLEARANCES_FOR_KIND``
#: lists.
PROVENANCE_CLEARANCES: Mapping[str, Clearer] = {
    "derived_from_supported_facts": derived_from_supported_facts,
}


def apply_clearances(finding: Finding, context: ClearanceContext) -> Finding:
    """The finding, CLEARED by the first registered clearance for its claim kind that proves it,
    else unchanged. The one place in the code base that constructs a CLEARED finding."""
    if finding.source != "llm" or not finding.blocking:
        return finding
    catalogue = {**CLEARANCES, **PROVENANCE_CLEARANCES}
    for name in (
        *CLEARANCES_FOR_KIND.get(finding.claim_kind, ()),
        *PROVENANCE_CLEARANCES_FOR_KIND.get(finding.claim_kind, ()),
    ):
        proof = catalogue[name](finding, context)
        if proof is not None:
            return replace(finding, status="CLEARED", clearance=proof)
    return finding


__all__ = [
    "CLEARANCES",
    "PROVENANCE_CLEARANCES",
    "ClearanceContext",
    "Deriver",
    "absence_present",
    "absence_unsourced",
    "apply_clearances",
    "derived_from_supported_facts",
    "names_supported",
    "omission_present",
]
