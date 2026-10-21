"""What a kept inherited unit is about, read from the heading path it sat under in the source.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/source_topics.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry). It lives under ``composition`` because placement may not import
reconciliation; it is a registry of patterns, not a branch.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from repo_presenter.core.facts import Fact

_TOPICS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "furniture",
        re.compile(
            r"\b(?:licen[cs]\w*|copyright|notices?|third party|navigation|table of contents|"
            r"contents|badges?|banner)\b"
        ),
    ),
    (
        "build",
        re.compile(r"\b(?:tests?|testing|build|building|develop\w*|contribut\w*|compil\w*|ci)\b"),
    ),
    (
        "example",
        re.compile(
            r"\b(?:examples?|usage|samples?|tutorials?|recipes?|demos?|quick start|how to)\b"
        ),
    ),
    ("setup", re.compile(r"\b(?:setup|set up|getting started)\b")),
    (
        "install",
        re.compile(r"\b(?:install\w*|requirements?|prerequisites?|depend\w*|extras?|packages?)\b"),
    ),
    ("api", re.compile(r"\b(?:api|reference|classes|methods?|namespaces?|modules?)\b")),
    (
        "limits",
        re.compile(
            r"\b(?:limit\w*|supported|compatib\w*|known|restrictions?|caveats?|status|roadmap|notes?)\b"
        ),
    ),
    (
        "capabilities",
        re.compile(r"\b(?:features?|capabilit\w*|overview|about|highlights?|why|what)\b"),
    ),
    (
        "resources",
        re.compile(
            r"\b(?:docs?|documentation|links?|resources?|community|contact|help|learn\w*|"
            r"changelog|releases?|acknowledg\w*|credits?)\b"
        ),
    ),
)
_SPACE = re.compile(r"[^a-z0-9]+")


def source_heading(unit: Fact | None) -> str | None:
    """The heading path the extractor recorded for an inherited unit, or ``None``."""
    if unit is None:
        return None
    section = (unit.attributes or {}).get("section")
    return section or None


def heading_parts(section: str) -> list[str]:
    """A heading path ("Product > Installation > Requirements") as lower-case parts."""
    return [
        part for part in (_SPACE.sub(" ", p.lower()).strip() for p in section.split(">")) if part
    ]


def root_heading(units: Sequence[Fact]) -> str | None:
    """The README's title as the first part of its units' heading paths."""
    firsts = Counter(
        path[0]
        for unit in units
        if (section := source_heading(unit)) and (path := heading_parts(section))
    )
    if not firsts:
        return None
    root, count = firsts.most_common(1)[0]
    return root if count * 2 > sum(firsts.values()) else None


def topic_of(parts: Sequence[str]) -> str | None:
    """The topic of a heading path's parts: the first, deepest part that names one."""
    for part in reversed(parts):
        for topic, pattern in _TOPICS:
            if pattern.search(part):
                return topic
    return None


def path_topic(heading_path: str | None, root: str | None = None) -> str | None:
    """The topic of a heading path, with the README's title (``root``) taken off the front."""
    parts = heading_parts(heading_path) if heading_path else []
    if parts and root is not None and parts[0] == root:
        parts = parts[1:]
    return topic_of(parts) if parts else None


def unit_topic(unit: Fact | None, root: str | None = None) -> str | None:
    """The topic of one inherited unit from its own heading path (:func:`path_topic`)."""
    return path_topic(source_heading(unit), root)
