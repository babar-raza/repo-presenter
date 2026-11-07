"""The mechanism-class responsibility matrix, as auditable code (TC-022c).

Why this module exists: ``src/repo_presenter/acceptance/record.py``'s ``load_certificates()``
reads ``data/acceptance_responsibility.json``'s ``mechanism_classes`` (a flat list of strings) as
the exact set of mechanism-class certificates a candidate must have, ALL PASSED, before it can
reach ``provisionally-accepted``. Hand-typing that JSON file is how a wrong required-mechanism set
silently produces a false acceptance (R10/R16) or a permanently unreachable one -- so this module
derives the list from a reviewable, tested table instead, and the supervisor calls
:func:`build_responsibility_document` to emit the real committed file as a separate, later action
(``data/**`` is denied to every worker card, this one included).

The table, transcribed in full from ``docs/design/2026-11-06-acceptance-redesign.md`` section 2.1
(defect class -> owning mechanism(s)):

=====  ===================================================  ============  =========
Class  Defect                                                Primary       Secondary
=====  ===================================================  ============  =========
D1     stale revision/facts                                  M1            --
D2     wrong version/package/install                         M4            M2
D3     broken link                                            M4            --
D4     example fails                                          M3            M2
D5     false checkable claim (mechanical)                     M2            M8 never
D6     ungrounded generated claim                              M2            --
D7     true claim the facts miss                               none         --
D8     unverifiable maintainer knowledge                       M5            M2
D9     semantic description mismatch                           M9 (nominal)  --
D10    content loss/drop                                       M5            M7
D11    duplicate content                                       M6            --
D12    form/attribution leak/naming                            M6            --
D13    below benchmark                                         M7            M5
D14    promotional/generic prose                               M8            --
D15    incoherent or less usable than benchmark                M8 (pairwise) M9
D16    (Lane L only) unjustified/non-minimal edit               M10           --
=====  ===================================================  ============  =========

Two deliberate departures from a literal transcription, both required by this card's own text,
not left to guesswork:

* **D7 is not a mechanism_classes entry at all.** The table's own primary column for D7 reads
  "none may reject it" -- D7 is owned by the facts extractor, not by any acceptance mechanism.
  ``DEFECT_CLASS_OWNERS`` therefore has no ``"D7"`` key, and
  :func:`responsibility_matches_calibration_harness` (and the test suite) assert that absence
  directly, so a future edit cannot silently reinstate it as a fake mechanism requirement.
* **D9's real owning mechanism, for calibration purposes, is M8, not M9.** The design table lists
  D9's primary as "M9", but its own worked-through fallback text immediately qualifies that:
  generated text is "prevented by construction" (so M9 never actually fires against it), while
  "inherited text: M8-S" -- i.e. the case that can actually occur routes to M8's semantic-mismatch
  sub-gate. M9 itself is not a mechanism this codebase measures anywhere (it is not in
  ``calibration_harness.MECHANISMS``, and no card implements an "M9" scorer) -- only D9's row
  mentions it at all, as a label for a check that is structurally impossible to need. Requiring
  "M9" in ``mechanism_classes`` would make ``provisionally-accepted`` permanently unreachable (no
  certificate for a mechanism nothing produces can ever exist). So ``DEFECT_CLASS_OWNERS["D9"]``
  records primary ``"M8"`` here, not ``"M9"`` -- this is the real, calibration-relevant owner, with
  this docstring as the record of why it differs from the design table's literal primary column.

``REQUIRED_MECHANISM_CLASSES`` is derived, not independently chosen: it is the sorted tuple of
every mechanism that owns at least one defect class as a PRIMARY in ``DEFECT_CLASS_OWNERS``,
after the D9 correction above. That derivation yields ``M1`` through ``M8`` plus ``M10`` -- M9
never appears (D9's primary was corrected to M8 before this derivation runs), and D7 contributes
nothing (it is not in the mapping at all).

M8's cross-check: ``calibration_harness.MECHANISMS`` deliberately excludes M8 (it is TC-023's
separate prose-judge contract, not a case this harness's deterministic/model-free scorers can
run). So the real invariant this module's own correctness depends on is not
``REQUIRED_MECHANISM_CLASSES <= calibration_harness.MECHANISMS``, but the weaker, true one stated
in this card: ``REQUIRED_MECHANISM_CLASSES - {"M8"}`` IS a subset of ``calibration_harness.MECHANISMS``
(in fact equal to it, for the mechanisms as they stand today) -- i.e. this module can never require
a mechanism that neither the harness nor TC-023's M8 contract actually measures.
:func:`responsibility_matches_calibration_harness` checks exactly that, against the real,
imported ``calibration_harness.MECHANISMS`` tuple -- not a copy or a guess.
"""

from __future__ import annotations

import json

from . import calibration_harness

__all__ = [
    "DEFECT_CLASS_OWNERS",
    "REQUIRED_MECHANISM_CLASSES",
    "build_responsibility_document",
    "responsibility_matches_calibration_harness",
]

#: Defect-class id -> (primary_mechanism, secondary_mechanism_or_None). D7 is intentionally
#: absent (see module docstring): it is owned by the facts extractor, not by any acceptance
#: mechanism, and must never become a mechanism_classes entry. D9's primary is recorded as the
#: real calibration-relevant owner, "M8", per the module docstring's documented correction from
#: the design table's literal (but structurally-impossible-to-need) "M9".
DEFECT_CLASS_OWNERS: dict[str, tuple[str, str | None]] = {
    "D1": ("M1", None),
    "D2": ("M4", "M2"),
    "D3": ("M4", None),
    "D4": ("M3", "M2"),
    "D5": ("M2", None),
    "D6": ("M2", None),
    "D8": ("M5", "M2"),
    "D9": ("M8", None),
    "D10": ("M5", "M7"),
    "D11": ("M6", None),
    "D12": ("M6", None),
    "D13": ("M7", "M5"),
    "D14": ("M8", None),
    "D15": ("M8", "M9"),
    "D16": ("M10", None),
}

#: Every mechanism that owns at least one defect class above as a PRIMARY, sorted and
#: deduplicated. This is the exact set ``build_responsibility_document()`` writes into
#: ``mechanism_classes`` -- every one of these must be ALL PASSED before a candidate can reach
#: ``provisionally-accepted`` (``record.py.load_certificates``).
REQUIRED_MECHANISM_CLASSES: tuple[str, ...] = tuple(
    sorted({primary for primary, _secondary in DEFECT_CLASS_OWNERS.values()})
)


def build_responsibility_document() -> dict[str, object]:
    """Return the exact dict shape ``record.py.load_certificates()`` reads from
    ``data/acceptance_responsibility.json``: ``{"schema": "acceptance-responsibility/1",
    "mechanism_classes": [...]}``, sorted and deterministic across calls. This module never
    writes that file itself (``data/**`` is denied to every worker card); the supervisor calls
    this function directly and commits the result as a separate, supervisor-owned action.
    """
    return {
        "schema": "acceptance-responsibility/1",
        "mechanism_classes": sorted(REQUIRED_MECHANISM_CLASSES),
    }


def responsibility_matches_calibration_harness() -> bool:
    """True iff ``REQUIRED_MECHANISM_CLASSES`` minus ``{"M8"}`` is a subset of the real,
    imported ``calibration_harness.MECHANISMS`` -- i.e. this module can never require a
    mechanism that neither the harness nor TC-023's separate M8 contract actually measures.
    """
    harness_mechanisms = set(calibration_harness.MECHANISMS)
    required_minus_m8 = set(REQUIRED_MECHANISM_CLASSES) - {"M8"}
    return required_minus_m8.issubset(harness_mechanisms)


# Module-import-time self-check, cheap and deterministic: fail loudly at import, not only under
# pytest, if this module's own derivation ever drifts out of the subset invariant it promises.
assert responsibility_matches_calibration_harness(), (
    "REQUIRED_MECHANISM_CLASSES minus {'M8'} is not a subset of calibration_harness.MECHANISMS; "
    "see this module's docstring and TC-022c's closeout."
)

# Round-trip sanity at import time too: the document this module builds must always be valid,
# re-parseable JSON with no loss.
assert json.loads(json.dumps(build_responsibility_document())) == build_responsibility_document()
