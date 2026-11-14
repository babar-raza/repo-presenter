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

_AS_WRITTEN = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE", "PRESERVE_ATTRIBUTED"})
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


#: A bullet that LEADS with a document link (optionally bold): ``**[Getting started](url)** --
#: ...``. Such an item is a pointer to a resource, the shape Documentation and Resources prints one
#: line per link; it is never a statement of what the product cannot do (BL-004).
_RESOURCE_ITEM = re.compile(r"^\s*(?:\*\*|__)?\[[^\]]+\]\(\s*<?(?!#)[^)\s>]+")


def resource_link_items(text: str) -> list[str]:
    """The top-level items of ``text`` that lead with a document link (not an in-page anchor)."""
    return [item for item in list_items(text) if _RESOURCE_ITEM.match(item)]


def is_link_list(text: str) -> bool:
    """Whether ``text`` is a list of resource links: at least two items, every one carrying a
    document link (not an in-page anchor). The maintainers' "Documentation & Resources" list is
    the real case (Aspose.3D FOSS for .NET 059.list, Cells C++ 053.list, Email .NET 055.list,
    Words .NET 080.list)."""
    items = list_items(text)
    return len(items) >= _MIN_ITEMS and all(item_links(item) for item in items)


#: A resource item's own description: the text after its leading (optionally bold) link and the
#: dash or colon that follows it, ``**[Getting started guide](url)** — installation, ...``.
_RESOURCE_DESCRIPTION = re.compile(
    r"^\s*(?:\*\*|__)?\[[^\]]+\]\(\s*<?[^)\s>]+>?\s*\)(?:\*\*|__)?\s*(?:—|–|-{1,2}|:)\s*"
    r"(?P<text>\S.*)$"
)
_SHELL_OWNED_LINKS = frozenset(
    {
        "link_target:product.banner",
        "link_target:product.enterprise",
        "link_target:product.homepage",
        "link_target:badge.ci",
    }
)


def kept_link_descriptions(
    dispositions: Mapping[str, Any] | None, facts: FactsDocument
) -> dict[str, str]:
    """``link_target`` fact id -> the maintainers' own description of it, for every item of a
    resource-links list kept as written in Documentation and Resources (P4, 2026-11-14).

    Documentation and Resources prints one line per planned link, never a kept unit's text, so a
    kept links list is printed through its links; its item descriptions are the maintainers'
    words for those links, so the line is rendered from the link fact and that description
    (R43(2): Documentation and Resources from facts plus kept maintainer text), never authored.
    Measured: 3D .NET ``059.list``, Cells C++ ``053.list``, Words .NET ``080.list`` and PDF Java
    (seals older than BL-004, whose plans carried only part of each list). Only an item with
    exactly one document link and a description after it counts; the first item wins."""
    if not dispositions:
        return {}
    by_value: dict[str, str] = {}
    for fact in sorted(facts.by_kind("link_target"), key=lambda f: f.id):
        if (
            fact.polarity == "SUPPORTED"
            and fact.id not in _SHELL_OWNED_LINKS
            and not fact.value.startswith("#")
        ):
            by_value.setdefault(fact.value, fact.id)
    texts = {fact.id: fact.value for fact in facts.by_kind("inherited_unit")}
    found: dict[str, str] = {}
    for entry in dispositions.get("dispositions", []):
        unit = str(entry.get("unit_id", ""))
        text = texts.get(unit, "")
        if (
            entry.get("disposition") not in _AS_WRITTEN
            or entry.get("destination_section") != "documentation_resources"
            or not unit.endswith(".list")
            or not is_link_list(text)
        ):
            continue
        for item in list_items(text):
            links = item_links(item)
            lead = _GROUP_LEAD.match(item)
            if len(links) > 1 and lead is not None:
                # One item naming several links under a bold lead (PDF Java ``126.list``: "**In-repo
                # topic guides**: [Getting Started](docs/getting-started.md), [Text Extraction]
                # (...), ..."): each link line is described by that lead, the maintainers' words.
                for link in links:
                    if link in by_value:
                        found.setdefault(by_value[link], f"{lead.group(1).strip()}.")
                continue
            if len(links) != 1 or links[0] not in by_value:
                continue
            match = _RESOURCE_DESCRIPTION.match(item)
            if match is not None:
                description = match.group("text").strip()
            else:
                # A link inside the item's sentence (Words .NET ``080.list``: "The public API
                # matches the commercial [Aspose.Words for .NET](...), so ..."): the sentence is
                # the description, its link printed as its label beside the line's own link.
                description = _INLINE_LINK.sub(r"\1", item).strip()
            if description:
                found.setdefault(by_value[links[0]], description)
    return found


_INLINE_LINK = re.compile(r"\[([^\]]+)\]\(\s*<?[^)\s>]+>?\s*\)")
_GROUP_LEAD = re.compile(r"^\s*(?:\*\*|__)([^*_\[\]]+?)(?:\*\*|__)\s*:")


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
