"""BC-05 (supersession): a unit judged SUPERSEDE_REDUNDANT is not printed because its replacement
carries all of its substance -- so the README must state that substance.

Why a check and not only a prompt rule (owner decision 2026-11-06, docs/DECISION_LOG.md): the
source_reconciliation v14 rule ("superseded only when the replacement carries all of its substance:
listed values, conditions, when/why insight") was in force for the 2026-11-06 hosted pilot, and the
new Email .NET candidate still superseded "runs on Windows, Linux, macOS, Docker containers, and
serverless functions" and the ``CfbReader`` note "useful when diagnosing a damaged or non-standard
file"; neither appears in its README. A model's claim that content is carried is tested here the
way an advisory deferral's "nothing lost" is (``validation/deferrals.py``), with
``content_presence.unstated(strict=True)``: a sentence that spells an anchor the README prints
(``.NET 8.0``) must still have its other words carried.

A failure is RECONCILING and names its unit, so the repair loop re-reconciles that one unit with
the missing pieces quoted (keep it, move it, or attribute it), and a candidate that still loses the
content is rejected. Exempt, because the renderer replaces them by design and the reader loses
nothing a maintainer wrote: headings, badge rows, raw HTML wrappers, the mermaid diagram (the
renderer draws At a Glance from verified facts), and a lead-in carried with its block.

TC-018: ``superseded_failures`` above only ever looked at units given the one disposition
SUPERSEDE_REDUNDANT. The drop inventory (``docs/investigations/2026-11-06-drop-inventory.md``)
found that a must-carry obligation is violated the same way under VERIFIED_REWRITE, OMIT_UNSUPPORTED
and DEFER_UNRESOLVED (a public API member's maintainer description replaced by generic filler is
just as real a loss as the member being dropped outright, whatever disposition the row carries).
``obligation_failures`` below covers every inherited unit's every disposition: it classifies each
decomposed piece with ``readme/obligations/classify.py``'s ``classify_unit`` (the same mechanical
rule table ``superseded_failures``'s own exemptions already approximate, now applied uniformly)
and fails only a ``must_carry`` piece whose substance ``content_presence.unstated(strict=True)``
cannot find in the candidate -- never a ``may_drop`` or ``undecided`` one, so an over-flag
(a re-qualified name, a badge, a diagram the candidate draws itself) is never raised twice.
"""

from __future__ import annotations

import re

from repo_presenter.core.package_registry import (
    is_unconfirmed_registry_install,
    unconfirmed_registry_packages,
)
from repo_presenter.readme.composition.references import positional_only
from repo_presenter.readme.validation.content_presence import unstated
from repo_presenter.readme.validation.failures import Candidate, Failure

SUPERSEDED = "SUPERSEDE_REDUNDANT"
# The phrase every failure of this check carries; reconciliation/patch.py reads it to require that a
# repair of such a unit stops superseding it.
LOSS_MARKER = "is SUPERSEDE_REDUNDANT, but the README does not state"
EXEMPT_KINDS = frozenset({"heading", "badge_row", "html_block"})
_LEAD_IN = "lead-in of the block that follows"
_SHOWN = 4


def _kind(unit_id: str) -> str:
    return unit_id.rsplit(".", 1)[-1]


def _diagram(text: str) -> bool:
    return text.lstrip().lstrip("`~").lstrip().lower().startswith("mermaid")


def exempt(unit_id: str, text: str, rationale: str) -> bool:
    """Whether a superseded unit is markup the renderer replaces by design."""
    kind = _kind(unit_id)
    if kind in EXEMPT_KINDS:
        return True
    if kind == "code_block" and _diagram(text):
        return True
    if kind == "paragraph" and positional_only(text):
        # "A few more patterns beyond the Quick Start example above." (Email .NET, 2026-11-06 local
        # pilot): kept by a repair, it became a BC-07 dangling reference.
        return True
    return _LEAD_IN in rationale.lower()


_SPAN_PIECE = re.compile(r"^span '(.+)'$")
_IDENTIFIER = re.compile(r"^[a-z_][\w:.<>&-]*(?:\(.*\))?(?:\s*->.*)?$")


def _core(name: str) -> str:
    """An identifier's last path segment, arguments and return type removed, lower case."""
    head = re.split(r"[(\s]", name.strip(), maxsplit=1)[0]
    return re.split(r"::|\.", head)[-1].lower()


def public_names(candidate: Candidate) -> frozenset[str]:
    """The last segment of every public symbol the facts verify (empty when none are extracted)."""
    return frozenset(
        _core(str(fact.value)) for fact in candidate.facts.by_kind("public_symbol")
    )


def owed(piece: str, public: frozenset[str]) -> bool:
    """Whether a missing piece is content the README owes.

    A code span naming an identifier outside the verified public surface is not: Cells-Rust's
    maintainer table (inherited_unit:052, local pilot 2026-11-06) lists ``AlignmentValue``, the
    ``*Model`` structs and ``CellValueKind``, which live in private ``mod core_*`` modules ``lib.rs``
    never re-exports; the README's API Reference prints the verified surface instead, and that
    supersession is correct. Without an extracted surface every piece is owed."""
    match = _SPAN_PIECE.match(piece)
    if not public or match is None:
        return True
    name = match.group(1)
    if not _IDENTIFIER.match(name):
        return True
    return _core(name) in public


_LEADING_SPAN = re.compile(r"^\s*(?:\|\s*|[-*+]\s+)(?:\*\*)?`([^`\n]+)`")


def owed_text(text: str, kind: str, public: frozenset[str]) -> str:
    """A table or list without the rows whose subject is an identifier outside the verified public
    surface (Cells-Rust: ``SheetVisibility`` / ``RelationshipResolutionException`` rows describe
    private ``core_*`` types). Other units, and every unit without an extracted surface, unchanged."""
    if not public or kind not in {"table", "list"}:
        return text
    kept: list[str] = []
    for line in text.splitlines():
        match = _LEADING_SPAN.match(line)
        name = match.group(1) if match else ""
        if name and _IDENTIFIER.match(name.lower()) and _core(name) not in public:
            continue
        kept.append(line)
    return "\n".join(kept)


def superseded_failures(candidate: Candidate) -> list[Failure]:
    """One RECONCILING failure per superseded unit whose substance the README does not state."""
    texts = {
        fact.id: str(fact.value or "")
        for fact in candidate.facts.by_kind("inherited_unit")
    }
    failures: list[Failure] = []
    public = public_names(candidate)
    # BC-02 refuses to print the registry install of a package whose ownership the registry does not
    # confirm, so a superseded unit's copy of that command is not owed by its replacement.
    unconfirmed = unconfirmed_registry_packages(candidate.facts.by_kind("install_command"))
    for entry in candidate.dispositions.get("dispositions", []):
        if entry.get("disposition") != SUPERSEDED:
            continue
        unit_id = str(entry.get("unit_id", ""))
        text = texts.get(unit_id, "")
        if not text.strip() or exempt(unit_id, text, str(entry.get("rationale") or "")):
            continue
        missing = [
            piece
            for piece in unstated(
                owed_text(text, _kind(unit_id), public),
                candidate.readme,
                kind=_kind(unit_id),
                strict=True,
            )
            if owed(piece, public) and not is_unconfirmed_registry_install(piece, unconfirmed)
        ]
        if not missing:
            continue
        shown = "; ".join(missing[:_SHOWN])
        failures.append(
            Failure(
                "RECONCILING",
                f"{unit_id} {LOSS_MARKER} "
                f"{len(missing)} piece(s) of it ({shown}): a superseded unit's replacement must "
                "carry all of its substance; keep it (VERIFIED_PRESERVE/VERIFIED_MOVE), or "
                "PRESERVE_ATTRIBUTED when no fact confirms it",
                unit=unit_id,
            )
        )
    return failures


# --- TC-018: every disposition, not only SUPERSEDE_REDUNDANT -----------------------------------

#: The phrase every failure of ``obligation_failures`` carries, so a repair loop can recognize it
#: the same way it already recognizes :data:`LOSS_MARKER`.
OBLIGATION_LOSS_MARKER = "is must_carry, but the README does not state"
_ALREADY_CHECKED = frozenset({SUPERSEDED})


def obligation_failures(candidate: Candidate) -> list[Failure]:
    """One RECONCILING failure per decomposed piece that :mod:`readme.obligations.classify` rates
    ``must_carry`` and :func:`content_presence.unstated` (strict) cannot find in the candidate,
    for EVERY inherited unit regardless of its disposition.

    SUPERSEDE_REDUNDANT units are left to :func:`superseded_failures` above (unchanged, so its own
    existing exemptions and failure wording keep working); this only adds coverage for the
    dispositions the drop inventory found losing content the same way: VERIFIED_REWRITE,
    OMIT_UNSUPPORTED, DEFER_UNRESOLVED, CORRECT_WITH_EVIDENCE and any other non-SUPERSEDE
    disposition. A ``may_drop`` or ``undecided`` piece is never flagged, so an obligation this
    module cannot yet decide is left to the model/supervisor judgement path, never guessed.
    """
    from repo_presenter.readme.obligations.ledger import ledger_from_candidate

    by_unit: dict[str, str] = {
        str(entry.get("unit_id", "")): str(entry.get("disposition", ""))
        for entry in candidate.dispositions.get("dispositions", [])
    }
    failures: list[Failure] = []
    for record in ledger_from_candidate(candidate):
        if record.obligation != "must_carry" or record.carried is not False:
            continue
        if by_unit.get(record.unit_id) in _ALREADY_CHECKED:
            continue  # superseded_failures already judges this unit, with its own exemptions
        failures.append(
            Failure(
                "RECONCILING",
                f"{record.unit_id} {OBLIGATION_LOSS_MARKER} its {record.piece_kind} "
                f"{record.text[:160]!r} ({record.evidence})",
                unit=record.unit_id,
            )
        )
    return failures
