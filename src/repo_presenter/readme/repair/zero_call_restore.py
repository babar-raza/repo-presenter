"""TC-019a: the zero-call-first question TC-019's own design text asks before assuming a seal
repair needs a real generator call (docs/DELIVERY_PLAN_2026-11-07.md section 8.2, "item-level
restore (zero-call share measured first)") -- for a real NEEDS_REPAIR seal, is the fix a MECHANICAL
text substitution a pure function can compute directly from already-committed facts, or does it
genuinely need new generated prose (out of this module's scope, a later, budgeted card)?

Exactly one shape qualifies today: a stated public-type count ("N public types" / "N ... classes
[and enumerations]") that the facts directly contradict, where ``N`` is simply wrong and the
facts' own number is already on record (``public_symbol`` facts -- the same count
``readme/validation/surface_claims.py``'s BC-14 rule (h) holds every such sentence to). The fix is
a pure digit substitution: the sentence's own words, grammar and noun are left untouched, nothing
is invented. Two shapes this module deliberately does NOT fix, because each is a genuine judgement
call with no fact to derive a replacement from:

* An API-table row naming a type the facts' public surface does not hold (BC-14 rule (i)) --
  dropping the row, or finding the real name it should have been, is a decision a human or a real
  generator call makes, never a mechanical substitution.
* A claim with no supporting fact of its own kind on record at all (e.g. a README stating a
  package is unpublished, with no ``package:published_version`` fact to check that against) --
  there is no number or value anywhere in the facts to substitute in its place.

``restore_stated_count`` is the only function this module exports; it returns the corrected text
only when it found a genuine, unambiguous mismatch to fix, and ``None`` in every other case
(nothing to fix, or nothing this module knows how to fix) -- never raising, never guessing.
"""

from __future__ import annotations

import re

from repo_presenter.core.facts import FactsDocument

#: Facts of these ``public_symbol`` ``symbol_kind`` attributes are what a "public types" claim
#: counts -- mirrors ``readme/validation/surface_claims.py``'s own ``TYPE_KINDS``.
_TYPE_KINDS = ("class", "enum")

#: A stated count directly adjacent to a qualifier ("public"/"verified"/"exported"/"documented"/
#: "top-level"/"distinct") and a "types"/"classes[ and enumerations/enums]" noun -- the same shape
#: ``readme/validation/surface_claims.py``'s ``_TYPE_COUNT`` detects (duplicated here, not
#: imported: this module proves a repair against real text and must stay independent of the
#: detector that will later decide whether a seal needs one). Requiring the qualifier immediately
#: before the noun (rather than anywhere in the sentence, as the detector's own wider
#: ``_PUBLIC_CONTEXT`` allows) is this module's own, narrower, deliberately conservative gate: a
#: mechanical substitution must never guess that an unrelated count ("3 return classes") was ever
#: a public-surface claim.
_STATED_COUNT = re.compile(
    r"""(?ix)
    (?<![\w.,])(?P<count>\d{1,3}(?:,\d{3})+|\d+)\s+
    (?P<qualifier>public|verified|exported|documented|top-level|distinct)\s+
    (?:API\s+)?
    (?P<noun>types|classes(?:\s+and\s+(?:enumerations|enums))?)\b
    """
)


def type_counts(facts: FactsDocument) -> tuple[int, int]:
    """(types, classes) exactly as the facts record them: SUPPORTED class/enum ``public_symbol``
    facts, and the classes among them. The same computation
    ``readme/validation/surface_claims.py``'s own ``type_counts`` makes -- duplicated rather than
    imported, per this module's docstring."""
    symbols = [
        fact
        for fact in facts.by_kind("public_symbol")
        if fact.polarity == "SUPPORTED"
    ]
    kinds = [(fact.attributes or {}).get("symbol_kind", "") for fact in symbols]
    types = sum(1 for kind in kinds if kind in _TYPE_KINDS)
    classes = sum(1 for kind in kinds if kind == "class")
    return types, classes


def restore_stated_count(readme_text: str, facts: FactsDocument) -> str | None:
    """``readme_text`` with every "N public types" / "N ... classes[ and enumerations]" statement
    whose stated ``N`` genuinely contradicts the facts corrected to the facts' own number --
    nothing else in the sentence touched, no new clause added -- or ``None`` when every such
    statement already matches the facts (nothing to fix) or the facts carry no type count at all
    (nothing to derive a replacement from).

    A "classes" noun is held to the classes count; a bare "types" noun (covering class and enum
    facts both) is held to the combined types count -- exactly as
    ``readme/validation/surface_claims.py``'s own detector reads the two nouns.
    """
    types, classes = type_counts(facts)
    if types == 0:
        return None

    changed = False

    def _replace(match: re.Match[str]) -> str:
        nonlocal changed
        noun = match.group("noun").lower()
        correct = classes if noun.startswith("classes") else types
        stated = int(match.group("count").replace(",", ""))
        if stated == correct:
            return match.group(0)
        changed = True
        whole = match.group(0)
        start = match.start("count") - match.start(0)
        end = match.end("count") - match.start(0)
        return whole[:start] + str(correct) + whole[end:]

    restored = _STATED_COUNT.sub(_replace, readme_text)
    return restored if changed else None
