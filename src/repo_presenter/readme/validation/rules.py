"""Pure rules behind BC-06's link ceilings and BC-07's badge row.

ADAPT from the old repository-presenter project's ``components/readme/validation/links/rules.py``
(133 lines). Each function takes plain values and returns the problems it finds as sentences; the
checks in ``links.py`` and ``structure.py`` wrap them as routed failures. Nothing here reads a
file, the network or a clock.

Not ported: ``enterprise_anchor_problems``. It required the anchor text to open "full-featured",
which ``docs/MISSION_AUTHORITY.md``'s owner correction R2/R3 retired; the rule would reintroduce
that retired wording. The Enterprise Edition naming rule that remains is the edition-substitute
check in ``links.py``.

The rules, each with the ``plans/idea.md`` line it enforces:

* Aspose-link ceilings: "Otherwise the system derives conservative maxima deterministically from
  the README's visible content size and verified code examples. Every slot is a ceiling, not a
  target" (``composition/link_budget.py`` derives them; ``readme_link_budget`` measures).
* Badge row: "one compact badge row in a stable order: package or release, platform/runtime, real
  build status, license, then contributors when those slots are supported. Badges may be omitted
  when their claims or targets are unavailable, but they may not be duplicated, split across
  multiple header rows, or fabricated merely to fill the row."
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from repo_presenter.core.examples import printed_example
from repo_presenter.core.facts import FactsDocument
from repo_presenter.readme.composition.link_budget import (
    LinkBudget,
    code_sha256,
    measure_content,
    resolve_link_budget,
)
from repo_presenter.readme.composition.policy import PlanningPolicy
from repo_presenter.readme.composition.renderer import (
    BADGE_ORDER,
    EXTRA_BADGE_SLOT,
    badge_slot,
    line_counts,
)

# The markers an example fact's evidence carries once it has actually run.
EXECUTION_MARKERS = (": EXECUTED", ": COMPILED")
_BADGE = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!\[[^\]]*\]\([^)]*\)")


def verified_example_hashes(facts: FactsDocument) -> set[str]:
    """The normalized digests of every example that actually ran at this revision."""
    return {
        code_sha256(code)
        for fact in facts.by_kind("example")
        for code in (fact.value, printed_example(fact))
        if fact.polarity == "SUPPORTED"
        and any(
            marker in (evidence.detail or "")
            for evidence in fact.evidence
            for marker in EXECUTION_MARKERS
        )
    }


def readme_link_budget(
    readme: str, facts: FactsDocument, policy: PlanningPolicy
) -> LinkBudget:
    """The exact per-slot Aspose-link ceilings of this rendered document."""
    return resolve_link_budget(
        measure_content(readme, verified_example_hashes(facts)),
        policy.link_allocation,
        policy.aspose_links_max,
    )


def effective_visible_lines_budget(policy: PlanningPolicy, benchmark_readme: str | None) -> int:
    """The visible-line budget BC-07 holds a candidate to: ``max(policy budget, the published
    README's own visible lines)`` when a benchmark README is present, else the policy budget.

    Supervisor ruling 2026-11-10 (owner goals R2, top authority: the published README is the
    minimum quality floor, so the floor must be satisfiable). Measured: published aspose.org
    READMEs run 545-598 lines (Cells Go, Cpp), so a candidate that keeps the floor (BC-17) can never
    fit a fixed 300 visible lines. Only the LINE budget relaxes; BC-07's other sub-rules (the Core API
    table's rows against the verified public types, one H1, badge order, fences, narration, ...)
    are untouched."""
    if not benchmark_readme:
        return policy.visible_lines_budget
    published_visible, _total = line_counts(benchmark_readme)
    return max(policy.visible_lines_budget, published_visible)


def badge_problems(row: str, expected: Sequence[tuple[str, str]]) -> list[str]:
    """Why the badge ``row`` breaks the contract, against the badges the facts support.

    ``expected`` is what the renderer derives from verified facts, ``(slot, markdown)`` in
    ``BADGE_ORDER``. A badge may be missing (omission is allowed); it may not repeat a slot, sit
    out of order, or differ from the supported badge for its slot, because a badge no fact
    supports is a fabricated one.
    """
    supported = {slot: markdown for slot, markdown in expected if slot != EXTRA_BADGE_SLOT}
    extras = {markdown for slot, markdown in expected if slot == EXTRA_BADGE_SLOT}
    problems: list[str] = []
    seen: list[str] = []
    extra_seen: set[str] = set()
    for token in _BADGE.findall(row):
        if token in extras:
            # A maintainers' badge the slot badges did not carry (renderer._carried_extra_badges):
            # verified by being exactly the badge the renderer derives, always after the slots.
            if token in extra_seen:
                problems.append(f"duplicate carried badge {token[:60]!r}")
            extra_seen.add(token)
            seen.append(EXTRA_BADGE_SLOT)
            continue
        slot = badge_slot(token)
        if slot is None:
            problems.append(f"badge {token[:60]!r} fills no recognized slot")
            continue
        if slot in seen:
            problems.append(f"duplicate {slot} badge")
        seen.append(slot)
        if slot not in supported:
            problems.append(
                f"{slot} badge is not supported by any verified fact: {token[:80]!r}"
            )
        elif token != supported[slot]:
            problems.append(
                f"{slot} badge differs from the verified one: {token[:80]!r}"
            )
    ranks = [
        len(BADGE_ORDER) if slot == EXTRA_BADGE_SLOT else BADGE_ORDER.index(slot) for slot in seen
    ]
    if ranks != sorted(ranks):
        problems.append(
            f"badge order {', '.join(seen)} breaks the stable order {', '.join(BADGE_ORDER)}"
        )
    return problems
