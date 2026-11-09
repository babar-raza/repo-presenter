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

2026-11-09 (owner ruling R26, rung-(c) fallback, docs/design/2026-11-06-acceptance-redesign.md
section 6): a real, recorded M8 calibration failure now exists --
``data/acceptance_calibration.json``'s M8 certificate, measured for real this session, is
``NOT_PASSED`` on all three of its shapes (classification false-reject 0.0333 > 0.02;
pairwise-benchmark recall 0.3684 < 0.90; M8-S paraphrase recall 0.85 < 0.90 and false-reject
0.10 > 0.02). Rung (b) (an owner-approved second model route for M8 only) is pre-declined as a
standing matter, not something re-asked per candidate: owner ruling R18 already states
qwen3-next is the only model route "including for M8", project-wide, with no second route ever
introduced. Per the design's own fallback-ladder text ("b fails, or the owner declines"), rung
(c) is therefore authorized now, without a further owner round-trip. D9, D14 and D15 are
reassigned below accordingly; M8 itself keeps running (TC-023's contract, still real and still
measured) but becomes advisory, never required for ``provisionally-accepted``.

Three deliberate departures from a literal transcription, all required by this card's own text
(the first two predate rung (c); the third is rung (c) itself), not left to guesswork:

* **D7 is not a mechanism_classes entry at all.** The table's own primary column for D7 reads
  "none may reject it" -- D7 is owned by the facts extractor, not by any acceptance mechanism.
  ``DEFECT_CLASS_OWNERS`` therefore has no ``"D7"`` key, and
  :func:`responsibility_matches_calibration_harness` (and the test suite) assert that absence
  directly, so a future edit cannot silently reinstate it as a fake mechanism requirement.
* **D9 is now "none", like D7, not M8 or M9 -- the rung-(c) reassignment.** Before rung (c), this
  module recorded D9's primary as ``"M8"`` (a correction from the design table's literal, but
  structurally-impossible-to-need, "M9" -- requiring an uncounted mechanism would have made
  ``provisionally-accepted`` permanently unreachable). Rung (c) removes M8 from the gate
  entirely: generated descriptions are already "prevented by construction" (M2 allows a
  generated type description only from ``docstring_full``, never a semantic paraphrase), and the
  one case that can actually occur -- an INHERITED description M8-S would have checked -- is now
  routed as a ``PRESERVE_ATTRIBUTED`` disposition (§6.3's preservation policy: source-consistent
  maintainer material is must-carry unless a probe positively contradicts it) and checked by M9's
  audit rubric downstream, at the ``independently-accepted`` stage, never as a
  ``provisionally-accepted`` gate requirement. This is exactly D7's own shape (a class no
  mechanism in this matrix may reject), so D9 joins it as a second ``"none"`` entry rather than
  inventing a different label for the same structural case.
* **D14 splits by generated vs. inherited text -- the rung-(c) reassignment.** Before rung (c),
  this module recorded D14's primary as ``"M8"`` (the prose judge, uncalibrated). Rung (c)'s own
  text: "Generated prose is limited to renderer templates and bounded lead-ins with a
  deterministic lexicon ban on promotional/superlative wording, which moves D14 for generated
  text to M6" -- ``repo_presenter.readme.validation.wording.promotional_wording_matches``, folded
  into M6's own certificate as a second, independently-gated case group (``wording_ban``,
  alongside the existing ``duplicate_paragraph`` group). This lexicon ban is the backstop half
  only; constraining the generator itself ("bounded lead-ins") is TC-019's own, separately-scoped,
  not-yet-built "generator constraints (S3)" work -- see ``wording.py``'s module docstring for
  that caveat in full. For INHERITED promotional-sounding prose, rung (c)'s text routes it as "a
  disposition decision under the R14 pattern" -- i.e. the existing drop/keep preservation policy
  (``data/drop_decisions.json``, M5, already ``ACCEPTED`` via TC-018) decides whether to carry it,
  the same mechanism D8 (unverifiable maintainer knowledge) already uses for an analogous
  disposition call. ``DEFECT_CLASS_OWNERS["D14"]`` therefore records primary ``"M6"`` (the
  generated-text case, real code, real gate), secondary ``"M5"`` (the inherited-text disposition
  case, no new code needed -- an existing policy, not a new mechanism).
* **D15 moves to M7, M8 dropped -- the rung-(c) reassignment.** Rung (c)'s own text: "M8 becomes
  advisory and is not in the gate; D15 relative to the benchmark is covered by M7's scorecard and
  M9's rubric." ``DEFECT_CLASS_OWNERS["D15"]`` therefore records primary ``"M7"`` (mirroring
  D13's existing "below benchmark" mapping -- D15's "less usable than benchmark" is the same
  benchmark-comparison shape M7 already owns), secondary ``None`` (M9's rubric is a downstream
  audit check at ``independently-accepted``, not a second ``provisionally-accepted`` gate
  requirement -- the same reasoning D9's own departure note gives for never requiring "M9" in
  ``mechanism_classes``).

``REQUIRED_MECHANISM_CLASSES`` is derived, not independently chosen: it is the sorted tuple of
every mechanism that owns at least one defect class as a PRIMARY in ``DEFECT_CLASS_OWNERS``,
after the three departures above. That derivation yields ``M1`` through ``M7`` plus ``M10`` --
**M8 no longer appears** (rung (c): no defect class's primary is M8 any more), M9 never appears
(same structural-impossibility reasoning as before, now applying to D9 and D15 too), and D7
contributes nothing (it is not in the mapping at all).

M8's cross-check, updated for rung (c): ``calibration_harness.MECHANISMS`` deliberately excludes
M8 (it was always TC-023's separate prose-judge contract, not a case this harness's
deterministic/model-free scorers can run) -- this was true before rung (c) and remains true
now, except that ``REQUIRED_MECHANISM_CLASSES`` no longer contains ``"M8"`` at all, so the
subtraction below is a no-op for today's table but is kept so a future re-addition of an M8-owned
defect class (a reversal of rung (c), which this module does not anticipate but does not forbid
either) does not silently break this invariant. The real invariant this module's own correctness
depends on is not ``REQUIRED_MECHANISM_CLASSES <= calibration_harness.MECHANISMS``, but the
weaker, true one stated in this card: ``REQUIRED_MECHANISM_CLASSES - {"M8"}`` IS a subset of
``calibration_harness.MECHANISMS`` (today, equal to it, since M8 is no longer a member to
subtract) -- i.e. this module can never require a mechanism that neither the harness nor TC-023's
M8 contract actually measures. :func:`responsibility_matches_calibration_harness` checks exactly
that, against the real, imported ``calibration_harness.MECHANISMS`` tuple -- not a copy or a
guess.
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

#: Defect-class id -> (primary_mechanism, secondary_mechanism_or_None). D7 and D9 are
#: intentionally absent from any mechanism-owned pairing (both map to primary "none", see module
#: docstring): D7 is owned by the facts extractor, D9 is a PRESERVE_ATTRIBUTED disposition
#: checked by M9's audit downstream -- neither may become a mechanism_classes entry. D14 and D15
#: were reassigned off M8 by the 2026-11-09 rung-(c) fallback (R26); see module docstring for the
#: full reassignment rationale.
DEFECT_CLASS_OWNERS: dict[str, tuple[str, str | None]] = {
    "D1": ("M1", None),
    "D2": ("M4", "M2"),
    "D3": ("M4", None),
    "D4": ("M3", "M2"),
    "D5": ("M2", None),
    "D6": ("M2", None),
    "D8": ("M5", "M2"),
    "D10": ("M5", "M7"),
    "D11": ("M6", None),
    "D12": ("M6", None),
    "D13": ("M7", "M5"),
    "D14": ("M6", "M5"),
    "D15": ("M7", None),
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
