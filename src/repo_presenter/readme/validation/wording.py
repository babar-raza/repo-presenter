"""Deterministic promotional/superlative wording ban -- the M6 half of M8's rung-(c) fallback
(owner ruling R26, docs/design/2026-11-06-acceptance-redesign.md section 6): "Generated prose is
limited to renderer templates and bounded lead-ins with a deterministic lexicon ban on
promotional/superlative wording, which moves D14 for generated text to M6."

This module is the lexicon-ban half only. The OTHER half rung (c) requires -- constraining what
the renderer/generator can produce in the first place, so recall against promotional phrasing
reaches 1.00 "by construction" rather than by trying to out-guess arbitrary free text -- is
TC-019's own, separately-scoped "generator constraints (S3)" work, not built here. A lexicon ban
over unconstrained free text cannot have recall 1.00 against phrasing it was never shown; this
module's own measurement (scripts/measure_m6_wording_ban.py) is honest about that: it is scored
against the real dev corpus already used for M8's own classification calibration
(scripts/measure_m8_live.py's clean/promotional spans), not an independent held-out sample -- the
same documented caveat the design states for M8's own dev mutants ("the 18 it5 promotional
mutants are dev"). Recall against genuinely novel promotional phrasing, once the generator itself
is unconstrained, is not something a fixed lexicon can promise.
"""

from __future__ import annotations

#: Terms/phrases a neutral technical document would not carry (superlatives, sales framing,
#: unearned enthusiasm), transcribed from two real sources already in this codebase:
#: prompts/m8/prose_judge.yaml's own "promotional" category definition, and the real promotional
#: corpus this project already measures M8 against
#: (src/repo_presenter/readme/review/calibration/mutations.py::PROMOTIONAL_FILLER,
#: scripts/measure_m8_live.py::SYNTHETIC_PROMOTIONAL, and
#: src/repo_presenter/acceptance/audit/seed.py's own promotional-filler sentences). Matched as
#: case-insensitive substrings; order is stable but not significant.
PROMOTIONAL_TERMS: tuple[str, ...] = (
    "cutting-edge", "cutting edge",
    "best-in-class", "best in class",
    "revolutioniz",  # revolutionize/revolutionizes/revolutionizing/revolutionized
    "revolutionary approach",
    "industry-leading", "industry leading",
    "award-winning", "award winning",
    "world-class", "world class",
    "game-changing", "game changer", "game-changer",
    "next-generation", "next generation",
    "no equal",
    "blazing",
    "lightning-fast", "lightning fast",
    "gold standard",
    "groundbreaking", "ground-breaking",
    "jaw-dropping",
    "masterpiece",
    "supercharge",
    "crush every benchmark", "crushes every benchmark",
    "unlock limitless",
    "ultimate solution",
    "exceed every expectation",
    "single best",
    "simply the best",
    "the best choice",
    "leave the competition behind", "leaves every alternative",
    "complete reinvention",
    "redefine",
    "trusted by fortune 500", "fortune 500 companies",
    "blows every competitor", "blow every competitor",
    "brand new standard", "new gold standard",
    "battle-tested",
    "comes close to the",
    "zero compromises",
    "no rival",
    "outperforms every rival",
    "greatest leap forward",
    "overwhelming",
    "game-changer for",
    "impossibly high",
    "powerful, cutting-edge",
    "award winning choice",
    "setting the bar",
    "obsessed with perfection",
    "deployed in production by more than",
    "faster than every",
    "commercial libraries combined",
    "without question, the most",
    "raving about",
    "never been a better time",
    "most capable library",
    "won't find anywhere else",
    "ever created",
)


def promotional_wording_matches(text: str) -> tuple[str, ...]:
    """Every ``PROMOTIONAL_TERMS`` entry that occurs in ``text`` (case-insensitive substring
    match), in ``PROMOTIONAL_TERMS`` order; empty when none does. A pure function: no network, no
    provider call, no state."""
    lowered = text.lower()
    return tuple(term for term in PROMOTIONAL_TERMS if term in lowered)
