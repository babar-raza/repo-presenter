"""TC-018: pre-generation obligations, generalizing the R14 drop-inventory rule table.

``docs/investigations/2026-11-06-drop-inventory.md`` and its ``decide.py`` decide every one of
649 historically *dropped* items, after the fact, by inspecting a finished candidate. This module
turns the MECHANICAL and PARTLY-MECHANICAL rules of that table (21 named rule codes; see the
module docstring of ``tests/readme/obligations/test_classify.py`` for the regression fixture that
replays all 649 decisions against this file) into an obligation that can be decided for EVERY
inherited unit a candidate's reconciliation touches -- kept or dropped -- independent of which
candidate eventually gets built:

* ``must_carry`` -- the unit's substance has to appear in the candidate somewhere (a public API
  member with its maintainer description, a resolving link, a pinned version, an install snippet
  or diagram the maintainers wrote, a code example that is not contradicted).
* ``may_drop`` -- the unit is genuinely droppable (private API, a dead link, a contradicted
  example, renderer-owned markup, a decorative badge, a Lane L naming substitution).
* ``undecided`` -- neither is established by the facts this function was given; the model/
  supervisor judgement path other cards own still decides it (never guessed as either of the
  above).

Every input is optional and defaults to ``None`` ("unknown"), because the same ``classify_unit``
is called in two different situations with different amounts of information available:

* **pre-generation** (the obligations inventory, built before a candidate exists): only
  world-level facts are known (is this symbol on the language's own export surface, does a path
  resolve, is a version pinned in a project file, did the maintainers' own example fail against
  the source). Signals that can only be read off a *specific* candidate (did it draw its own
  diagram, did it reprint the pinned version, did it requalify the name) are ``None`` here, so
  the rules that need them (``R-DIAGRAM``, ``R-VERSION-REPLACED``, ``R-API-REQUALIFIED``) fall
  back to their conservative, "still owed" default (``must_carry``) rather than guessing.
* **post-generation / ledger-building** (``readme/obligations/ledger.py``, and the verification
  wiring in ``readme/validation/supersession.py``): the same function is called again once a
  candidate exists, with those extra signals filled in from it, which is when a unit that was
  conservatively ``must_carry`` pre-generation can resolve to ``may_drop`` once its mechanical
  exemption is confirmed.

A ``None`` answer from a TC-017a probe (``src/repo_presenter/acceptance/probes/``) is threaded
through unchanged into ``UnitFacts.public`` -- never coerced to ``True`` or ``False`` here, same
as that package's own contract requires of its callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Obligation = Literal["must_carry", "may_drop", "undecided"]

#: The inherited-unit kinds this module knows how to classify. ``table_item``/``list_item``/
#: ``sentence`` are the drop-inventory's own finer-than-a-whole-unit piece vocabulary (one table
#: row, one list bullet, one sentence); ``enterprise_edition_naming`` is Lane L's naming-rule edit
#: kind (``docs/investigations/2026-11-06-drop-inventory.md``'s R-NAMING). The live pipeline's own
#: whole-unit kinds (``readme/validation/text.py``'s ``unit_type``: ``code_block``, ``heading``,
#: ``badge_row``, ``table``, ``list``, ``paragraph``) map onto these one-for-one except that a
#: whole ``table``/``list``/``paragraph`` unit may hold several pieces, each separately
#: classifiable; ``ledger.py`` does that decomposition.
UNIT_KINDS = frozenset(
    {
        "code_block",
        "table_item",
        "list_item",
        "sentence",
        "heading",
        "html_block",
        "badge_row",
        "enterprise_edition_naming",
    }
)

#: A table-row description that says nothing the maintainer wrote, only the generator's own
#: boilerplate (R-API-FILLER's predicate, decide.py's own ``FILLER`` regex, reproduced here
#: unchanged so the mechanical check this module makes stays identical to the one the drop
#: inventory calibrated against).
FILLER_DESCRIPTION = re.compile(
    r"^(class|struct|enum|interface|trait|type)\b( with [\w ,]+)?( in the .*api)?\.?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Unit:
    """One inherited-README piece, at the drop-inventory's own granularity.

    ``unit_id`` is the whole inherited unit's fact ID (``inherited_unit:031.table``) a piece
    belongs to, when known; it is carried through to the obligations ledger and the verification
    failure a caller raises, never read by ``classify_unit`` itself.
    """

    kind: str
    text: str
    unit_id: str = ""
    subject: str | None = None


@dataclass(frozen=True)
class UnitFacts:
    """Every signal ``classify_unit`` can use, each optional and independently sourced.

    ``None`` always means "not established" and is never treated as ``False``. See the module
    docstring for which fields are available before a candidate exists and which are only known
    once one does.
    """

    # --- table_item (API reference rows) and, for an identifier-naming sentence, prose claims ---
    #: Whether the row's/claim's subject is on the ecosystem's own public export surface
    #: (TC-017a probe and/or ``supersession.py``'s own ``public_names``/``owed`` facts-based
    #: signal; see ``readme/validation/supersession.py``'s ``obligation_public_signal``, which
    #: combines both and returns ``None`` on disagreement rather than silently picking one).
    public: bool | None = None
    #: R-API-FILLER: the original description is generator boilerplate, not maintainer content.
    #: Purely mechanical and world-level (a regex over the row's own text); always computable.
    filler_description: bool | None = None
    #: R-API-REQUALIFIED: a candidate already prints the same name, package-qualified
    #: (``<qualifier>.Name``), so the plain-named row is carried, not missing. Candidate-dependent.
    requalified_printed: bool | None = None
    #: public member(s) named by a prose/list item are confirmed as such by the public surface
    #: (R-API-IDENT). ``True`` is a strict superset of ``public`` for a single-subject row: this
    #: is for prose that *names* a member rather than tabulating one.
    mentions_public_member: bool | None = None

    # --- a link or path cited by a table row, list item or sentence (R-LINK-RESOLVES/-DEAD) ----
    is_link_subject: bool = False
    #: Whether the cited path/link target exists or resolves at the revision. World-level.
    path_exists: bool | None = None

    # --- code_block -------------------------------------------------------------------------
    is_mermaid: bool = False
    #: R-DIAGRAM: the candidate draws its own equivalent diagram. Candidate-dependent.
    own_diagram_drawn: bool | None = None
    #: The block is an install/dependency snippet that pins a version (R-VERSION-REPLACED).
    is_version_pin: bool = False
    #: The candidate reprints the same snippet with the verified current version. Candidate-dep.
    version_replaced: bool | None = None
    #: The unit's original disposition was CORRECT_WITH_EVIDENCE (R-CORRECTION-PRINTED).
    is_correction_required: bool = False
    #: The corrected text is actually printed somewhere in the candidate. Candidate-dependent.
    correction_printed: bool | None = None
    #: The maintainers' own example fails against the source at the revision. World-level
    #: (reproduced/compiled/executed against the pinned revision, never against a candidate).
    contradicted: bool | None = None
    #: A ``contradicted`` failure is only a harness/isolation defect (an undefined helper or a
    #: missing optional dependency the block itself names), not a defect in the example itself
    #: (R-HARNESS vs R-CONTRADICTED). World-level.
    harness_isolation_failure: bool = False
    #: Every path/identifier the block names exists at the revision (R-CODE-EVIDENCE). World-lvl.
    evidence_exists: bool | None = None

    # --- sentence / list_item prose claims --------------------------------------------------
    #: A dependency/tool version pinned in a project file at the revision (R-VERSION). The
    #: obligation to carry it does not depend on whether a candidate happens to print it yet --
    #: that is the separate presence check, not the classification -- so this needs no
    #: candidate-dependent counterpart.
    is_version_claim: bool = False
    #: A purely positional pointer ("collected below"), R-POSITIONAL.
    is_positional_only: bool = False
    #: A claim that counts public types/members, R-COUNT.
    is_count_claim: bool = False
    #: Whether the verified surface contradicts the claimed count. World-level.
    count_contradicted: bool | None = None

    # --- lead-in sentences and section headings (R-LEADIN, and R-HEADING's own exception) ----
    is_leadin: bool = False
    #: The obligation already decided for the block/section this unit introduces. When given,
    #: a lead-in or heading mirrors it exactly (``decide.py``: "a lead-in is kept with its
    #: block"); this is never guessed, only supplied by a caller that has already classified
    #: the associated unit (pre-generation: recursively, by calling ``classify_unit`` on it
    #: first; in the regression fixture: read back from the historical record being replayed).
    associated_block_obligation: Obligation | None = None


def _classify_code_block(facts: UnitFacts) -> Obligation:
    if facts.is_mermaid:
        if facts.own_diagram_drawn is True:
            return "may_drop"
        return "must_carry"
    if facts.is_version_pin:
        if facts.version_replaced is True:
            return "may_drop"
        return "must_carry"
    if facts.is_correction_required:
        if facts.correction_printed is True:
            return "may_drop"
        return "must_carry"
    if facts.contradicted is True:
        return "must_carry" if facts.harness_isolation_failure else "may_drop"
    if facts.contradicted is False:
        if facts.evidence_exists is False:
            return "may_drop"
        return "must_carry"
    return "undecided"


def _classify_table_item(facts: UnitFacts) -> Obligation:
    if facts.is_link_subject:
        if facts.path_exists is None:
            return "undecided"
        return "must_carry" if facts.path_exists else "may_drop"
    if facts.requalified_printed is True:
        return "may_drop"
    if facts.public is None:
        return "undecided"
    if not facts.public:
        return "may_drop"
    if facts.filler_description:
        return "may_drop"
    # A public, non-filler, non-requalified row: whether its current description/row/mention is
    # replaced by filler, missing entirely, or merely paraphrased is a VERIFICATION-time question
    # (does the candidate's rendered text carry the substance) -- R-API-DESC, R-API-ROW-MISSING
    # and R-CARRIED (its paraphrase form) are the same must_carry obligation here; they differ
    # only in whether the obligation ends up satisfied, which classify_unit cannot know yet.
    return "must_carry"


def _classify_prose(facts: UnitFacts) -> Obligation:
    if facts.is_link_subject:
        if facts.path_exists is None:
            return "undecided"
        return "must_carry" if facts.path_exists else "may_drop"
    if facts.is_version_claim:
        return "must_carry"
    if facts.is_positional_only:
        return "may_drop"
    if facts.is_count_claim:
        return "may_drop" if facts.count_contradicted else "must_carry"
    if facts.mentions_public_member is True:
        return "must_carry"
    # A plain prose/list claim with none of the above signals set is exactly the ~147 judgement
    # items this card does not try to decide mechanically (R-PROSE-VALID, and R-API-IDENT when
    # the probe/public-surface answer for the member it names is unknown): undecided, stopping
    # here, per the card's own instruction.
    return "undecided"


def classify_unit(
    unit: Unit,
    facts: UnitFacts | None = None,
    live_readme: str = "",  # noqa: ARG001 -- reserved: a future rule may need the live upstream
    probes: object | None = None,  # noqa: ARG001 -- reserved: callers resolve probes themselves
) -> Obligation:
    """The pre-generation obligation for ``unit``, from ``facts`` alone.

    ``live_readme`` and ``probes`` are accepted (the card's required signature) but this function
    never calls a probe or reads the live README itself -- a caller resolves a probe's three-
    valued answer (``None`` means unknown) into ``facts`` before calling this, exactly as
    ``readme/validation/supersession.py``'s wiring does, so the "never coerce None" contract stays
    in the one place (TC-017a's own probes package) that already enforces it.
    """
    kind = unit.kind
    f = facts if facts is not None else UnitFacts()
    # html_block: raw HTML wrapper markup (a ``<details>``/``<summary>`` shell) the renderer
    # replaces by design, same as ``readme/validation/supersession.py``'s own EXEMPT_KINDS.
    if kind in ("heading", "html_block") or f.is_leadin:
        if f.associated_block_obligation is not None:
            return f.associated_block_obligation
        return "may_drop" if kind in ("heading", "html_block") else "undecided"
    if kind == "badge_row":
        if f.is_link_subject and f.path_exists is not None:
            return "must_carry" if f.path_exists else "may_drop"
        return "may_drop"
    if kind == "enterprise_edition_naming":
        return "may_drop"
    if kind == "code_block":
        return _classify_code_block(f)
    if kind == "table_item":
        return _classify_table_item(f)
    if kind in ("list_item", "sentence"):
        return _classify_prose(f)
    return "undecided"
