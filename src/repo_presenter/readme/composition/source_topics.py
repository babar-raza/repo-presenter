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
#: A sentence that states the project's license terms ("This project is licensed under the MIT
#: License", "... provided without warranty under the MIT License"). The License section prints
#: that statement from the ``license`` facts; anywhere else it is misplaced (BL-004: Aspose.3D FOSS
#: for .NET and Cells Go printed it as a "limitation" under Scope and Limitations). Deliberately
#: not the bare word "License": ``License``/``Metered`` are also API class names a limitation may
#: name.
LICENSE_STATEMENT = re.compile(
    r"\blicen[cs]ed\s+under\b|\bunder\s+(?:the\s+)?(?:terms\s+of\s+the\s+)?\[?[\w.\- ]{1,30}"
    r"\blicen[cs]e\b(?!\s*(?:key|file|management|class|api)\b)",
    re.IGNORECASE,
)
_LICENSE_HEADING = re.compile(r"\blicen[cs]\w*\b")
#: The license clause of a sentence that also says other things: "is licensed under the MIT
#: License", ", distributed under the MIT license", "and is released under the Apache-2.0 License".
_LICENSE_CLAUSE = re.compile(
    r"(?P<lead>,\s*(?:and\s+)?|\s+and\s+)?"
    r"(?:(?:is|are)\s+)?(?:(?:also|freely)\s+)?"
    r"(?:licen[cs]ed|distributed|released|provided|available|published|offered)\s+under\s+"
    r"(?:the\s+)?(?:terms\s+of\s+the\s+)?\[?[\w.\-` ]{0,30}?\blicen[cs]e\b`?\]?(?:\([^)]*\))?"
    r"(?:,?\s+as\s+stated\s+in\s+[^,.;]*)?"
    r"(?P<tail>\s+and\s+)?",
    re.IGNORECASE,
)
_CLAUSE_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`\[(*_])")
#: A sentence left with this few words after its license clause goes says nothing else.
_MIN_REMAINING_WORDS = 4


def _without_license_clause(sentence: str) -> str:
    """``sentence`` without its license clause, or ``""`` when nothing else is left of it."""
    match = _LICENSE_CLAUSE.search(sentence)
    if match is None:
        return ""
    if match.group("lead") and match.group("tail"):
        joiner = match.group("lead") if "," in match.group("lead") else " and "
    elif match.group("tail") and match.start() > 0:
        joiner = " "
    else:
        joiner = ""
    rest = sentence[: match.start()].rstrip() + joiner + sentence[match.end() :].lstrip()
    rest = " ".join(rest.split())
    rest = re.sub(r"\s+([.,;!?])(?=\s|$)", r"\1", rest)
    rest = re.sub(r"[,;]\s*([.!?])$", r"\1", rest).strip(" ,;")
    if not rest.endswith((".", "!", "?")):
        rest += "."
    if is_license_statement(rest) or len(rest.rstrip(".!?").split()) < _MIN_REMAINING_WORDS:
        return ""
    return rest


def without_license_statement(text: str) -> str:
    """``text`` (one authored Scope and Limitations unit) without any statement of the project's
    license: a sentence that only states the license goes, and a sentence that also says other
    things keeps them ("This project is licensed under the MIT License and requires Python 3.10 or
    later." -> "This project requires Python 3.10 or later."). Empty when nothing is left.

    Decision (BL-089, supervisor 2026-11-14, audit O8a): the BC-05 section-fit rule stays (owner
    feedback on 3D .NET: the License section states the license, Scope never does); the producer
    side is fixed here and in the authoring packet. Measured: hosted Lane R runs 43516330798 (Cells
    Python, two Scope sentences) and 43520974296 (Cells TypeScript: "The package version is 1.0.0
    and is named excel-cells, distributed under the MIT license.") failed BC-05 on nothing else,
    and the targeted repair returned the unit unchanged twice (a no-op)."""
    if not is_license_statement(text):
        return text
    kept: list[str] = []
    for sentence in _CLAUSE_SENTENCE_END.split(text.strip()):
        if not is_license_statement(sentence):
            kept.append(sentence)
            continue
        rest = _without_license_clause(sentence)
        if rest:
            kept.append(rest)
    return " ".join(kept)


def is_license_statement(text: str) -> bool:
    """Whether ``text`` states the project's license terms (:data:`LICENSE_STATEMENT`)."""
    return LICENSE_STATEMENT.search(text.replace("`", "")) is not None


def under_license_heading(heading_path: str | None) -> bool:
    """Whether a unit's own (deepest) source heading is the License heading."""
    parts = heading_parts(heading_path) if heading_path else []
    return bool(parts) and _LICENSE_HEADING.search(parts[-1]) is not None


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
