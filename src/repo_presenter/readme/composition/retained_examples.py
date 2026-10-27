"""Inherited examples the run could not verify: kept verbatim, marked, never claimed to work.

Mission section 7: ``NOT_VERIFIED`` is not ``FALSE``. An example whose fact is UNRESOLVED (no
runner, no toolchain, needs input) is neither supported nor contradicted, so the README the project
already published for it is not ours to delete. Reconciliation supersedes the example's inherited
units into Quick Start or Additional Examples (``retain_unverified_examples``, the stage after
S4), and the renderer reprints them exactly as written beside a fixed, renderer-owned note that
says the example could not be verified. A CONTRADICTED example is never retained, and a SUPPORTED
one keeps the verified path (planned, authored lead-in, printed from its receipt, unmarked).

What is retained is read from two things only: the facts (which inherited code block each
UNRESOLVED example is, checked against the example's own code) and the dispositions (which units
reconciliation handed to the section). A disposition set that never went through that stage
renders nothing here, so existing sealed bundles render as they did.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from repo_presenter.core.facts import Fact, FactsDocument

NOT_VERIFIED_NOTE = (
    "> **Not verified:** this example is carried over unchanged from the project's existing "
    "README. It could not be compiled or run here."
)
QUICK_START = "quick_start"
ADDITIONAL_EXAMPLES = "additional_examples"
EXAMPLE_SECTIONS = frozenset({QUICK_START, ADDITIONAL_EXAMPLES})
SECTION_LABELS = {
    QUICK_START: "Quick Start",
    ADDITIONAL_EXAMPLES: "Additional Examples",
}

_UNIT_REFERENCE = re.compile(r"unit (inherited_unit:[0-9]+\.[a-z_]+)")
_UNIT_ORDER = re.compile(r"^inherited_unit:(\d+)(?:\.(\d+))?\.")
_DETAILS_TAG = re.compile(r"^\s*</?details\b", re.IGNORECASE)
_LEAD_KINDS = frozenset({"paragraph", "heading"})


@dataclass(frozen=True)
class RetainedExample:
    """One UNRESOLVED example and the inherited units that frame it in the existing README."""

    example_id: str
    code_unit: str
    section: str
    lead_units: tuple[str, ...]
    section_heading_unit: str | None
    wrapper_units: tuple[str, ...]


@dataclass(frozen=True)
class RetainedBlock:
    """What the renderer prints for one retained example: its framing text, then the code."""

    example_id: str
    section: str
    lead_texts: tuple[str, ...]
    code: str


def _kind(unit_id: str) -> str:
    return unit_id.rsplit(".", 1)[-1]


def _order(unit_id: str) -> tuple[int, int]:
    match = _UNIT_ORDER.match(unit_id)
    return (int(match.group(1)), int(match.group(2) or 0)) if match else (0, 0)


def _normalized(code: str) -> str:
    return "\n".join(line.rstrip() for line in code.splitlines() if line.strip())


def _fence_body(unit_text: str) -> str:
    lines = unit_text.splitlines()
    if len(lines) < 2 or not lines[0].startswith(("```", "~~~")):
        return ""
    return "\n".join(
        lines[1:-1] if lines[-1].strip().startswith(lines[0][:3]) else lines[1:]
    )


def _heading_level(unit_text: str) -> int:
    return len(unit_text) - len(unit_text.lstrip("#"))


def _example_unit(example: Fact, units: Mapping[str, Fact]) -> str | None:
    """The inherited code block an example fact is, or ``None`` when the fact names no unit that
    is a code block carrying the example's own code."""
    for evidence in example.evidence:
        match = _UNIT_REFERENCE.search(evidence.detail or "")
        if match is None:
            continue
        unit = units.get(match.group(1))
        if (
            unit is not None
            and _kind(unit.id) == "code_block"
            and _normalized(_fence_body(unit.value)) == _normalized(example.value)
        ):
            return unit.id
    return None


def _framing(
    index: int, ordered: list[Fact]
) -> tuple[tuple[str, ...], str | None, tuple[str, ...]]:
    """The heading and paragraph units directly before the code block at ``index`` (back to and
    including the section heading, or to a ``<details>`` wrapper), and that wrapper."""
    leads: list[str] = []
    section_heading: str | None = None
    wrappers: list[str] = []
    position = index - 1
    while position >= 0:
        unit = ordered[position]
        kind = _kind(unit.id)
        if kind == "html_block" and _DETAILS_TAG.match(unit.value):
            wrappers.append(unit.id)
            break
        if kind not in _LEAD_KINDS:
            break
        if kind == "heading" and _heading_level(unit.value) <= 2:
            section_heading = unit.id
            break
        leads.append(unit.id)
        position -= 1
    following = ordered[index + 1] if index + 1 < len(ordered) else None
    if (
        following is not None
        and _kind(following.id) == "html_block"
        and _DETAILS_TAG.match(following.value)
    ):
        wrappers.append(following.id)
    return tuple(reversed(leads)), section_heading, tuple(wrappers)


def retained_examples(facts: FactsDocument) -> list[RetainedExample]:
    """Every UNRESOLVED example that is an inherited code block, in README order, with its section.

    Without a SUPPORTED example the first one is the Quick Start and the rest are Additional
    Examples; beside a SUPPORTED example (planned into Quick Start by S5) all of them are
    Additional Examples. CONTRADICTED examples are never listed."""
    ordered = sorted(facts.by_kind("inherited_unit"), key=lambda fact: _order(fact.id))
    units = {fact.id: fact for fact in ordered}
    positions = {fact.id: index for index, fact in enumerate(ordered)}
    unverified: list[tuple[str, str]] = []
    for example in facts.by_kind("example"):
        if example.polarity != "UNRESOLVED":
            continue
        unit = _example_unit(example, units)
        if unit is not None:
            unverified.append((unit, example.id))
    unverified.sort(key=lambda pair: _order(pair[0]))
    supported = any(
        example.polarity == "SUPPORTED" for example in facts.by_kind("example")
    )
    retained: list[RetainedExample] = []
    for ordinal, (unit, example_id) in enumerate(unverified):
        section = ADDITIONAL_EXAMPLES if supported or ordinal else QUICK_START
        leads, heading, wrappers = _framing(positions[unit], ordered)
        retained.append(
            RetainedExample(example_id, unit, section, leads, heading, wrappers)
        )
    return retained


def adopts(entry: Mapping[str, Any] | None, retained: RetainedExample) -> bool:
    """Whether a disposition hands its unit to the retained example's section."""
    return (
        entry is not None
        and entry.get("disposition") == "SUPERSEDE_REDUNDANT"
        and entry.get("destination_section") == retained.section
        and retained.example_id in (entry.get("fact_ids") or [])
    )


def active_retained(
    facts: FactsDocument, dispositions: Mapping[str, Any]
) -> list[RetainedBlock]:
    """The blocks the renderer prints: retained examples whose code unit reconciliation handed to
    the section, each with the framing units it handed over too, in README order."""
    entries = {
        str(entry.get("unit_id")): entry
        for entry in dispositions.get("dispositions", [])
        if isinstance(entry, Mapping)
    }
    text = {fact.id: fact.value for fact in facts.by_kind("inherited_unit")}
    blocks: list[RetainedBlock] = []
    for retained in retained_examples(facts):
        if not adopts(entries.get(retained.code_unit), retained):
            continue
        leads = tuple(
            text[unit].strip()
            for unit in retained.lead_units
            if unit in text and adopts(entries.get(unit), retained)
        )
        blocks.append(
            RetainedBlock(
                retained.example_id,
                retained.section,
                leads,
                text[retained.code_unit].strip("\n"),
            )
        )
    return blocks


def block_body(block: RetainedBlock) -> str:
    """The code inside a retained block's fence, as ``fence_body`` reads it."""
    return _fence_body(block.code)


def normalized_code(code: str) -> str:
    """``code`` as two copies of one example compare: no blank lines, no trailing spaces."""
    return _normalized(code)


def block_lines(block: RetainedBlock) -> list[str]:
    """One retained example as the README prints it: framing text, the note, the code as written."""
    lines: list[str] = []
    for text in (*block.lead_texts, NOT_VERIFIED_NOTE, block.code):
        if lines:
            lines.append("")
        lines.extend(text.split("\n"))
    return lines
