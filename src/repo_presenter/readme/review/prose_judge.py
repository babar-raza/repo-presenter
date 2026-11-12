"""M8: a NEW, narrow prose-only judge (TC-023), replacing the old monolithic reviewer's role in
the acceptance critical path for ONE job only -- prose-quality judgement.

Why a new, narrow judge. ``readme.review.independent_reviewer`` / ``prompts/independent_review.yaml``
ask one model call to prove twelve different kinds of correctness at once: factual accuracy,
claim support, preservation, structure, AND prose quality together. ``data/reviewer_calibration.json``
(frozen, iteration 5: status ``NOT_PASSED``) records that this has failed five calibration
iterations, and ``docs/investigations/2026-11-06-reviewer-rootcause.md`` measures qwen3-next's own
repeat-draw stability at roughly 0.70-0.90 -- it does not reliably return the same verdict on a
repeated, byte-identical request even at temperature 0 / seed 1. M8 takes away ONLY the one job a
model is plausibly suited for -- prose quality -- leaving facts, claims and structure to separate
deterministic mechanisms (other cards, not this one) that do not depend on model judgement at all.

M8's exact scope, three independent question shapes (``prompts/prose_judge.yaml``), never combined
into one call -- that combination is exactly the needle-in-a-haystack, one-weak-skill-sinks-the-
verdict mistake the rootcause document already demonstrates:

- **classification**: given ONLY one prose line/span (no facts packet, no source code), name
  exactly one of ``promotional`` / ``generic_template`` / ``incoherent`` / ``misleading_framing``,
  or ``none``.
- **pairwise_benchmark_comparison**: given one whole section and the benchmark's section of the
  same purpose, answer yes/no: is the candidate's section at least as clear and usable?
- **m8s_paraphrase_check**: given an inherited type description not backed by a full docstring
  fact, and the type's real signature beside it, answer yes/no: is the description a fair
  paraphrase of the signature?

Model route (owner ruling, binding, project-wide): qwen3-next only. ``prompts/prose_judge.yaml``
records this (``model_route: qwen3-next``); this module never introduces a second model route, and
never references any other model id.

Sequential majority voting (``sequential_majority_vote``) is the reliability mechanism, because
qwen3-next is not deterministic: draw twice; if the two agree, stop; if they disagree, draw a
third time and accept whichever verdict two of the three agree on; if all three disagree with
each other, the call is ``INCONCLUSIVE`` -- never silently resolved to any one of the three. It is
implemented here as a PURE, deterministic state machine parameterized by an injectable draw
source (any zero-argument callable), so this module's own tests exercise the full state machine
with fake, scripted draw sequences (``ScriptedDraws``) at ZERO real provider calls. Nothing in this
module makes a provider call, opens a network connection, or imports the gateway/job-running machinery
(``core.llm.jobs``, ``core.llm.ledger``, …) -- a real call is future, separately budgeted work
(see ``core.llm.jobs`` for how one would eventually be wired); this module only proves the
contract and the voting logic correct against fakes.

Scope boundary, explicit and binding (owner ruling R26). This module builds the judge's CONTRACT
and VOTING LOGIC only. It does NOT run the real ~500-call calibration measurement against A1 (a
separate, future, explicitly budgeted step once a provider budget exists) and it does NOT
pre-build, stub, or wire any fallback path for what happens if M8 fails that future calibration
(sometimes called "rung (c)": removing the judge from the critical path in favor of a
deterministic wording ban plus a separate audit mechanism). That fallback is authorized only
after a real, recorded M8 calibration failure actually occurs -- which has not happened, because
the real calibration has not been run yet. Nothing in this module anticipates it; if you are
reading this because you were about to add a "what if M8 fails calibration" switch here, don't --
that decision is out of scope for this module until the real failure it would respond to exists.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

import yaml

__all__ = [
    "PROSE_CATEGORIES",
    "PROMPT_SHAPES",
    "ProseCategory",
    "INCONCLUSIVE",
    "ProseJudgeError",
    "VoteResult",
    "ScriptedDraws",
    "sequential_majority_vote",
    "ClassificationRequest",
    "classify_prose_span",
    "PairwiseComparisonRequest",
    "compare_section_to_benchmark",
    "ParaphraseCheckRequest",
    "check_type_paraphrase",
    "ProseJudgePrompts",
    "load_prose_judge_prompts",
]

#: The four defect categories M8's classification call may name, plus "none" (no category
#: applies). Must stay exactly in sync with ``prompts/prose_judge.yaml``'s
#: ``classification.categories`` keys and output schema enum -- ``load_prose_judge_prompts``
#: fails closed if the prompt file and this constant ever drift apart.
ProseCategory = Literal["promotional", "generic_template", "incoherent", "misleading_framing", "none"]

PROSE_CATEGORIES: frozenset[str] = frozenset(
    {"promotional", "generic_template", "incoherent", "misleading_framing", "none"}
)

#: The three independent prompt shapes ``prompts/prose_judge.yaml`` must declare, by name, one
#: top-level mapping key each -- never combined into one call (see the module docstring).
PROMPT_SHAPES: tuple[str, ...] = (
    "classification",
    "pairwise_benchmark_comparison",
    "m8s_paraphrase_check",
)

#: The sentinel verdict a classification / pairwise / paraphrase call resolves to when three
#: independent draws disagree with each other with no two-of-three majority
#: (``sequential_majority_vote``). Never folded to any one of the draws' own values: a caller
#: that receives this must treat the call as having answered nothing, the same way
#: ``readme.review.verdict.INSUFFICIENT_EVIDENCE`` blocks retryably rather than resolving
#: quietly. (Follows that module's own convention of naming a sentinel outcome as a plain,
#: exported string constant rather than a bespoke enum class.)
INCONCLUSIVE = "INCONCLUSIVE"


class ProseJudgeError(ValueError):
    """Raised when a draw returns a value outside its call's declared domain (e.g. a
    classification draw that is not one of ``PROSE_CATEGORIES``, or a pairwise/paraphrase draw
    that is not a ``bool``), or when a typed request or the prompt file itself is malformed.
    Never silently coerced or defaulted."""


T = TypeVar("T")


@dataclass(frozen=True)
class VoteResult(Generic[T]):
    """One call's resolved outcome. ``verdict`` is one of the draws' own values when two or more
    of up to three draws agreed, or the ``INCONCLUSIVE`` sentinel when all three disagreed with
    each other. ``draws`` is every value actually drawn, in order (length 2 or 3 -- never more,
    never fewer than the algorithm needed). ``agreement`` is how many of ``draws`` equal
    ``verdict``: 2 when a verdict was reached, 0 when inconclusive (never claimed as agreeing
    when it did not)."""

    verdict: T | str
    draws: tuple[T, ...]
    agreement: int

    @property
    def is_inconclusive(self) -> bool:
        return self.verdict == INCONCLUSIVE


@dataclass
class ScriptedDraws(Generic[T]):
    """A fake, call-counting draw source for tests -- and nothing else. It makes no provider
    call, no network call, no subprocess call; it only replays ``sequence`` in order and counts
    how many times it was called, so a test can assert the voting state machine drew exactly as
    many times as the algorithm requires (2 when the first two draws agree, 3 when they do not),
    never more. Calling it past the end of ``sequence`` raises ``StopIteration`` -- a test that
    scripts exactly 2 or 3 values and sees the state machine ask for one more has caught a real
    defect, not a fixture gap."""

    sequence: Sequence[T]
    calls: int = field(default=0, init=False)

    def __call__(self) -> T:
        if self.calls >= len(self.sequence):
            raise StopIteration(
                f"ScriptedDraws exhausted after {self.calls} call(s); the voting state machine "
                "asked for a draw this fake was not scripted to provide"
            )
        value = self.sequence[self.calls]
        self.calls += 1
        return value


def sequential_majority_vote(draw: Callable[[], T]) -> VoteResult[T]:
    """The reliability mechanism for one model call that is not deterministic (owner ruling:
    qwen3-next, this project's one model route, is not reliably self-consistent -- see the module
    docstring). ``draw`` is called at least twice and at most three times:

    - if the second draw agrees with the first, stop at two draws and accept that verdict;
    - otherwise draw a third time and accept whichever of the three, two draws agree on;
    - if all three disagree with each other (no two-of-three majority), return the
      ``INCONCLUSIVE`` sentinel -- never any one of the three draws picked arbitrarily.

    A pure function: ``draw`` is the only side-effecting thing this calls, and it is called
    exactly as many times as the algorithm needs, never more, never fewer. Nothing here makes a
    provider call itself -- ``draw`` is supplied by the caller (a real caller would wrap one
    governed model attempt per draw; this module's own tests supply ``ScriptedDraws`` instead, so
    this function and its tests never touch a provider or a network)."""
    first = draw()
    second = draw()
    if second == first:
        return VoteResult(verdict=first, draws=(first, second), agreement=2)
    third = draw()
    draws: tuple[T, ...] = (first, second, third)
    for candidate in (first, second, third):
        matches = sum(1 for value in draws if value == candidate)
        if matches >= 2:
            return VoteResult(verdict=candidate, draws=draws, agreement=matches)
    return VoteResult(verdict=INCONCLUSIVE, draws=draws, agreement=0)


# ---------------------------------------------------------------------------------------------
# Typed request shapes for the three prompt forms, each voted on via sequential_majority_vote.
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassificationRequest:
    """The four-category classification call's whole input: ONE prose line or span, no facts
    packet, no source code (M8's scope boundary). ``span_id`` is the caller's own bookkeeping key
    for the line/span being classified; it is never part of what a draw is asked to judge."""

    span_id: str
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ProseJudgeError("ClassificationRequest.text must not be empty/whitespace-only")


def classify_prose_span(
    request: ClassificationRequest, draw: Callable[[], str]
) -> VoteResult[str]:
    """Vote on ``request``'s classification via ``sequential_majority_vote``, failing closed
    (``ProseJudgeError``) if any draw returns a value outside ``PROSE_CATEGORIES`` -- never
    coerced into a valid category silently."""

    def _checked_draw() -> str:
        value = draw()
        if value not in PROSE_CATEGORIES:
            raise ProseJudgeError(
                f"classification draw {value!r} for span {request.span_id!r} is not one of "
                f"{sorted(PROSE_CATEGORIES)}"
            )
        return value

    return sequential_majority_vote(_checked_draw)


@dataclass(frozen=True)
class PairwiseComparisonRequest:
    """The pairwise benchmark-comparison call's whole input: one whole section's text, the
    benchmark's section of the same purpose, and the shared purpose label -- never combined with
    the classification or paraphrase questions (M8's scope boundary)."""

    purpose: str
    candidate_section: str
    benchmark_section: str

    def __post_init__(self) -> None:
        if not self.candidate_section.strip() or not self.benchmark_section.strip():
            raise ProseJudgeError(
                "PairwiseComparisonRequest needs both a non-empty candidate_section and a "
                "non-empty benchmark_section"
            )


def compare_section_to_benchmark(
    request: PairwiseComparisonRequest, draw: Callable[[], bool]
) -> VoteResult[bool]:
    """Vote on whether ``request.candidate_section`` is at least as clear and usable as
    ``request.benchmark_section`` (yes/no), failing closed if a draw is not a ``bool``."""

    def _checked_draw() -> bool:
        value = draw()
        if not isinstance(value, bool):
            raise ProseJudgeError(
                f"pairwise comparison draw for purpose {request.purpose!r} must be a bool, "
                f"got {value!r}"
            )
        return value

    return sequential_majority_vote(_checked_draw)


@dataclass(frozen=True)
class ParaphraseCheckRequest:
    """The M8-S sub-question's whole input: an inherited type description NOT backed by a full
    docstring fact, beside the type's real signature -- never given the facts packet or the rest
    of the candidate (M8's scope boundary)."""

    type_name: str
    description: str
    real_signature: str

    def __post_init__(self) -> None:
        if not self.description.strip() or not self.real_signature.strip():
            raise ProseJudgeError(
                "ParaphraseCheckRequest needs both a non-empty description and a non-empty "
                "real_signature"
            )


def check_type_paraphrase(
    request: ParaphraseCheckRequest, draw: Callable[[], bool]
) -> VoteResult[bool]:
    """Vote on whether ``request.description`` is a fair paraphrase of ``request.real_signature``
    (yes/no), failing closed if a draw is not a ``bool``."""

    def _checked_draw() -> bool:
        value = draw()
        if not isinstance(value, bool):
            raise ProseJudgeError(
                f"paraphrase draw for type {request.type_name!r} must be a bool, got {value!r}"
            )
        return value

    return sequential_majority_vote(_checked_draw)


# ---------------------------------------------------------------------------------------------
# The prompt file itself: loaded and minimally validated, never sent anywhere by this module.
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProseJudgePrompts:
    """The three prompt shapes loaded from ``prompts/prose_judge.yaml``, kept apart on purpose
    (M8's scope boundary: never combined into one call). Each is that shape's raw mapping exactly
    as authored; this module does not itself send anything to a provider (see the module
    docstring) -- a future, separately budgeted card does that."""

    classification: Mapping[str, Any]
    pairwise_benchmark_comparison: Mapping[str, Any]
    m8s_paraphrase_check: Mapping[str, Any]
    model_route: str


def load_prose_judge_prompts(path: Path) -> ProseJudgePrompts:
    """Load and minimally validate ``prompts/prose_judge.yaml``: fails closed with
    ``ProseJudgeError`` if the file is not a YAML mapping, if ``model_route`` is not
    ``qwen3-next`` (the project's one, binding model route), if any of ``PROMPT_SHAPES`` is
    missing, or if the classification shape's declared categories drift from
    ``PROSE_CATEGORIES``. Reads and parses text only -- no provider call, no network call."""
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ProseJudgeError(f"{path}: must parse to a YAML mapping")
    model_route = raw.get("model_route")
    if model_route != "qwen3-next":
        raise ProseJudgeError(
            f"{path}: model_route must be 'qwen3-next' (owner ruling, binding project-wide); "
            f"got {model_route!r}"
        )
    missing = [shape for shape in PROMPT_SHAPES if shape not in raw]
    if missing:
        raise ProseJudgeError(f"{path}: missing prompt shape(s): {missing}")
    classification = raw["classification"]
    if not isinstance(classification, Mapping):
        raise ProseJudgeError(f"{path}: classification must be a mapping")
    categories = classification.get("categories")
    if not isinstance(categories, Mapping) or frozenset(categories) != PROSE_CATEGORIES:
        raise ProseJudgeError(
            f"{path}: classification.categories keys must exactly equal "
            f"{sorted(PROSE_CATEGORIES)}, got {sorted(categories) if isinstance(categories, Mapping) else categories!r}"
        )
    return ProseJudgePrompts(
        classification=classification,
        pairwise_benchmark_comparison=raw["pairwise_benchmark_comparison"],
        m8s_paraphrase_check=raw["m8s_paraphrase_check"],
        model_route=model_route,
    )
