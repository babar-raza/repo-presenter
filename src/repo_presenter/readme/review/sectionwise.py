"""Review units and their bounded packets (reviewer logic 6).

Iteration 2 gave one model one question over a packet of about 70,000 tokens (both READMEs and every
fact), and it accepted 27 of 41 defective candidates. A review unit is one section, or a small group
of adjacent ones, whose author-written text fits ``UNIT_CHARS``; a section larger than that is split
between lines. The unit's packet is that text (``scope.reviewable_lines``: nothing the renderer
printed), the facts the text may cite and the part of the original README it draws on
(``evidence``), and the unit's own plan entries, about 10,000 to 15,000 tokens whatever the size of
the repository.

The unit's lines keep the candidate's own numbers (``0042| text``), so a citation means the same
thing in every unit and ``reply.resolve_cited_lines`` still derives the exact quote from the whole
candidate. A gap between two shown lines is marked, never numbered: the text between them was
printed by the renderer or belongs to another unit, and the reviewer cannot cite it.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from repo_presenter.core.facts import FactsDocument
from repo_presenter.core.llm.prompts import LoadedManifest
from repo_presenter.readme.review.evidence import (
    original_excerpt,
    support_hints,
    unit_facts,
)
from repo_presenter.readme.review.packet import (
    delimited,
    review_schema,
    without_narrative,
)
from repo_presenter.readme.review.scope import authored_type_rows, line_sections, shown_text

#: Most characters of author-written text one unit shows (about 1,100 tokens); the facts and the
#: original excerpt are bounded separately (``evidence``).
UNIT_CHARS = 4_500


@dataclass(frozen=True)
class ReviewUnit:
    index: int
    sections: tuple[str, ...]
    lines: tuple[int, ...]
    #: Whether the candidate was printed by the renderer (``scope.line_sections``); a corrected live
    #: README is not, and none of its text is withheld as the renderer's.
    rendered: bool = True

    @property
    def label(self) -> str:
        return f"u{self.index}"


def _runs(
    readme: str, rendered: bool, authored: Collection[int] = ()
) -> list[tuple[str, list[int]]]:
    """``(section, line numbers)`` for each run of reviewable lines under one section."""
    runs: list[tuple[str, list[int]]] = []
    for number, section in enumerate(line_sections(readme, rendered, authored), 1):
        if section is None:
            continue
        if runs and runs[-1][0] == section:
            runs[-1][1].append(number)
        else:
            runs.append((section, [number]))
    return runs


def plan_units(
    readme: str,
    max_chars: int = UNIT_CHARS,
    *,
    rendered: bool = True,
    authored: Collection[int] = (),
) -> tuple[ReviewUnit, ...]:
    """The review units of ``readme``, in document order: whole sections packed together while
    their text fits ``max_chars``, a longer section split between lines. Every reviewable line is
    in exactly one unit. A candidate with no author-written text has no units. ``authored``
    (``scope.authored_table_lines``) adds the renderer-printed table rows whose cell an author
    wrote."""
    rows = readme.splitlines()

    def size(numbers: Sequence[int]) -> int:
        return sum(len(rows[n - 1]) + 1 for n in numbers)

    pieces: list[tuple[str, list[int]]] = []
    for section, numbers in _runs(readme, rendered, authored):
        if size(numbers) <= max_chars:
            pieces.append((section, numbers))
            continue
        chunk: list[int] = []
        for number in numbers:
            if chunk and size([*chunk, number]) > max_chars:
                pieces.append((section, chunk))
                chunk = []
            chunk.append(number)
        if chunk:
            pieces.append((section, chunk))
    grouped: list[tuple[list[str], list[int]]] = []
    for section, numbers in pieces:
        if grouped and size([*grouped[-1][1], *numbers]) <= max_chars:
            if grouped[-1][0][-1] != section:
                grouped[-1][0].append(section)
            grouped[-1][1].extend(numbers)
        else:
            grouped.append(([section], list(numbers)))
    return tuple(
        ReviewUnit(index, tuple(sections), tuple(numbers), rendered)
        for index, (sections, numbers) in enumerate(grouped, 1)
    )


def _shown(unit: ReviewUnit, row: str) -> str:
    return shown_text(row) if unit.rendered else row


def unit_text(unit: ReviewUnit, readme: str) -> str:
    """The unit's text: its reviewable lines, one per line, without numbers or gaps and without any
    sentence the renderer appended to an authored line (``scope.shown_text``)."""
    rows = readme.splitlines()
    return "\n".join(_shown(unit, rows[n - 1]) for n in unit.lines)


def numbered_unit(unit: ReviewUnit, readme: str) -> str:
    """The unit's lines as ``NNNN| text`` with the candidate's own numbers; an interior gap is
    marked by a line that carries no number."""
    rows = readme.splitlines()
    shown: list[str] = []
    previous = None
    for number in unit.lines:
        if previous is not None and number > previous + 1:
            shown.append(
                f"      .. (candidate lines {previous + 1}-{number - 1} are not shown: "
                "renderer-printed text or another review unit)"
            )
        shown.append(f"{number:04d}| {_shown(unit, rows[number - 1])}")
        previous = number
    return "\n".join(shown)


def unit_packet(
    unit: ReviewUnit,
    *,
    units: Sequence[ReviewUnit],
    repository: str,
    candidate_readme: str,
    original_readme: str,
    facts: FactsDocument,
    plan: Mapping[str, Any],
    maintainer_lines: Collection[int] = (),
) -> dict[str, Any]:
    """The packet ``prompts/independent_review.yaml`` declares, for one unit. Evidence only: the
    author's rationale for a plan entry is dropped, and the dispositions and the deterministic
    validation result are not sent (they are the deterministic stage's, not the reviewer's).
    ``maintainer_lines`` (``scope.maintainer_lines``) are sent only as the shown line numbers that
    are attributed maintainer text -- a structural label, not a disposition or a rationale."""
    text = unit_text(unit, candidate_readme)
    given, members = type_row_facts(unit, candidate_readme, facts)
    records = unit_facts(
        facts,
        text,
        sections=unit.sections,
        cited=plan_cited_fact_ids(plan, unit.sections, facts),
        given=given,
        members=members,
    )
    rows = candidate_readme.splitlines()
    entries = [
        entry
        for entry in plan.get("sections", [])
        if isinstance(entry, Mapping) and entry.get("section_id") in unit.sections
    ]
    return {
        "repository": repository,
        "review_scope": {
            "unit": unit.label,
            "sections": list(unit.sections),
            "other_units": [
                {"unit": other.label, "sections": list(other.sections)}
                for other in units
                if other.index != unit.index
            ],
            "plan": without_narrative(entries),
        },
        "candidate_section": delimited(
            "candidate_section", text, shown=numbered_unit(unit, candidate_readme)
        ),
        "original_excerpt": delimited(
            "original_excerpt", original_excerpt(original_readme, text)
        ),
        "facts": records,
        "maintainer_lines": sorted(n for n in unit.lines if n in set(maintainer_lines)),
        "support_hints": support_hints(
            {n: _shown(unit, rows[n - 1]) for n in unit.lines}, records
        ),
    }


def type_row_facts(
    unit: ReviewUnit, readme: str, facts: FactsDocument
) -> tuple[list[str], dict[str, list[str]]]:
    """For the authored API reference rows the unit shows (``scope.authored_type_rows``), the fact
    ids each row's ``type:<fact id>`` unit was given and the member names listed with each type,
    read through the same function the type batch is built from (``authoring.type_unit_facts``):
    what the reviewer is shown for a row is exactly what its author was told it may state."""
    if not unit.rendered or "api_reference" not in unit.sections:
        return [], {}
    from repo_presenter.readme.composition.authoring import type_unit_facts

    rows = authored_type_rows(readme, facts)
    given: list[str] = []
    members: dict[str, list[str]] = {}
    for number in unit.lines:
        type_fact = rows.get(number)
        if type_fact is None:
            continue
        names, implementation = type_unit_facts(type_fact, facts)
        given.extend([type_fact.id, *(fact.id for fact in implementation)])
        if names:
            members[type_fact.id] = names
    return list(dict.fromkeys(given)), members


def plan_cited_fact_ids(
    plan: Mapping[str, Any], sections: Sequence[str], facts: FactsDocument
) -> list[str]:
    """The fact ids the plan carries into ``sections``, in plan order: every fact id found in the
    plan fields that feed those sections (``repair.targeted.SECTION_PLAN_CARRIERS``, the planning
    contract's own wiring -- ``material_limitations`` into Scope and Limitations,
    ``core_capabilities`` into Key Capabilities...). These are what the unit's text was written
    from, so the reviewer is shown them whatever their word overlap with it."""
    from repo_presenter.readme.repair.targeted import SECTION_PLAN_CARRIERS

    known = {fact.id for fact in facts.facts}
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            if node in known:
                found.append(node)
        elif isinstance(node, Mapping):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    for section in sections:
        for field, _kind in SECTION_PLAN_CARRIERS.get(section, ()):
            walk(plan.get(field))
    return list(dict.fromkeys(found))


def unit_schema(loaded: LoadedManifest, unit: ReviewUnit) -> dict[str, Any]:
    """The call schema for one unit: a finding names one of the unit's own sections."""
    return review_schema(loaded, {}, sections=unit.sections)
