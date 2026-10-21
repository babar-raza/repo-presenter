"""The item test for a list kept as written: which of its items a destination section states.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/list_coverage.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry).

Three callers read the one test, so they cannot disagree about what "states an item" means:
placement (``coverage.py``, which drops a kept list only for the items its destination states),
validation (judging whether a finished section states every item a list placement dropped), and
authoring (which names the lists a section's units may fold into their own words).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Collection, Mapping
from typing import Any

from repo_presenter.core.facts import FactsDocument

_AS_WRITTEN = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
_BULLET = re.compile(r"^(?:[-*+]|\d{1,3}[.)])\s+(.*)$")
_BOLD_LEAD = re.compile(r"^\s*(?:\*\*|__)(.+?)(?:\*\*|__)")
_LEAD_BREAK = re.compile(r"\s(?:-{1,2}|–|—)\s|:\s|\.\s|\(")
_LEAD_WORDS = 6
_CODE_LEAD_WORDS = 3
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_NON_WORD = re.compile(r"[^A-Za-z0-9]+")
_STOPWORDS = frozenset(
    {"the", "and", "for", "with", "that", "this", "are", "not", "but", "its", "can", "has"}
    | {"was", "were", "any", "all", "use", "uses", "used", "from", "into", "than", "yet", "via"}
)
_STEM = 5
_PRESENT_SHARE = 0.5
_MIN_ITEMS = 2
_LINK_DESTINATION = re.compile(r"\]\(\s*<?([^)\s>]+)")
OWED_SECTIONS = frozenset({"scope_limitations", "development_testing"})


def list_items(text: str) -> list[str]:
    """The top-level bullets of a Markdown list, each with its wrapped and nested lines."""
    items: list[list[str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _BULLET.match(line)
        if match is not None:
            items.append([match.group(1).strip()])
        elif items:
            items[-1].append(line.strip())
    return [" ".join(parts) for parts in items]


def _lead(item: str) -> str:
    """What the item is about: its bold phrase, else its words up to the first dash or colon."""
    bold = _BOLD_LEAD.match(item)
    if bold is not None:
        return bold.group(1)
    head = _LEAD_BREAK.split(item, maxsplit=1)[0]
    limit = _CODE_LEAD_WORDS if head.lstrip().startswith("`") else _LEAD_WORDS
    return " ".join(head.split()[:limit])


def _stems(text: str) -> set[str]:
    """Lower-case word stems of ``text``."""
    words: set[str] = set()
    for chunk in _NON_WORD.split(text):
        for word in _CAMEL.split(chunk):
            token = word.lower()
            if token in _STOPWORDS or not (len(token) >= 3 or any(c.isdigit() for c in token)):
                continue
            words.add(token[:_STEM])
    return words


def stems(text: str) -> set[str]:
    """The word stems this module compares text by."""
    return _stems(text)


def item_links(item: str) -> list[str]:
    """The document links an item carries: its Markdown destinations other than in-page anchors."""
    return [dest for dest in _LINK_DESTINATION.findall(item) if not dest.startswith("#")]


def missing_items(
    unit_text: str,
    destination_text: str,
    *,
    by_link: bool = False,
    document_text: str = "",
) -> list[str]:
    """The items of ``unit_text`` whose subject the destination text never states."""
    destination = _stems(destination_text)
    items = list_items(unit_text)
    said_by = Counter(stem for item in items for stem in _stems(item))
    missing: list[str] = []
    for item in items:
        links = item_links(item) if by_link else []
        if links:
            if not any(link in document_text for link in links):
                missing.append(item)
            continue
        lead, whole = _stems(_lead(item)), _stems(item)
        if not (lead or whole):
            continue
        own = {stem for stem in whole if said_by[stem] == 1} or whole
        if not (_shares(lead, destination) or _shares(own, destination)):
            missing.append(item)
    return missing


def _shares(subject: set[str], destination: set[str]) -> bool:
    """Whether the destination holds at least ``_PRESENT_SHARE`` of ``subject``'s stems."""
    return bool(subject) and len(subject & destination) >= max(
        1, math.ceil(len(subject) * _PRESENT_SHARE)
    )


def kept_lists(
    dispositions: Mapping[str, Any],
    section_id: str,
    owed: Collection[str],
    facts: FactsDocument,
) -> dict[str, str]:
    """The list units kept as written in ``section_id`` that its authored units may fold into
    their own words."""
    texts = {fact.id: fact.value for fact in facts.by_kind("inherited_unit")}
    return {
        unit: texts[unit]
        for entry in dispositions.get("dispositions", [])
        if entry.get("disposition") in _AS_WRITTEN
        and entry.get("destination_section") == section_id
        and (unit := str(entry.get("unit_id", ""))).endswith(".list")
        and unit in owed
        and unit in texts
        and len(list_items(texts[unit])) >= _MIN_ITEMS
    }
