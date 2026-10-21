"""An audience, benefit, or use case is stated only when an accepted fact states it.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/audience.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry).

A sentence of an authored unit that makes an audience, suitability, usage, or spared-cost claim is
refused unless the claim, word for word in substance, is already in the text of an accepted fact
the unit may cite. It sits beside ``authoring.py`` and imports nothing from it, so
``authoring.unit_checks`` can call it.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Mapping
from typing import Any

from repo_presenter.core.facts import FactsDocument

AUDIENCE_SECTIONS = frozenset({"opening"})

_ROLE = (
    r"(?:developers?|programmers?|engineers?|coders?|teams?|users?|analysts?|scientists?|"
    r"researchers?|testers?|integrators?|professionals?|practitioners?|maintainers?|"
    r"designers?|artists?|students?|hobbyists?|beginners?|experts?|customers?|clients?|"
    r"organi[sz]ations?|businesses|companies|enterprises|people|anyone|everyone|you)"
)
_MODIFIERS = (
    r"(?:(?!(?:the|a|an|this|that|these|those|your|its|their|our|of|to|in|on|with|each|every|"
    r"and|or|as|at|is|are)\b)[\w.#+/-]+\s+){0,2}?"
)
_WORD = r"[\w-]+"

_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:enables?|enabling|allows?|allowing|lets?|letting|helps?|helping|empowers?|"
        r"empowering|equips?|equipping)\s+(?:(?:the|all|any)\s+)?" + _MODIFIERS + _ROLE + r"\b",
        r"\b" + _ROLE + r"\s+(?:can\s+|may\s+|typically\s+|commonly\s+|often\s+)*"
        r"(?:use|uses|using|include|includes|including|who|that|building|build|builds|"
        r"needing|need|needs|wanting|want|wants|looking|seeking|working|benefit|benefits|"
        r"rely|relies|writing|creating|developing)\b",
        r"\b(?:for|by|among|targeting)\s+(?:(?:all|any|many|most|both)\s+)?"
        + _MODIFIERS
        + _ROLE
        + r"\b",
        r"\b" + _ROLE + r"\s+(?:in|across|within|from|at)\b",
        r"\b(?:widely|commonly|typically|often|frequently|primarily|mainly|mostly)\s+used\b",
        r"\b(?:ideal|ideally\s+suited|well[- ]suited|best\s+suited|suitable|suited|perfect|"
        r"perfectly\s+suited|great|excellent|useful|handy|helpful|valuable|beneficial|"
        r"appropriate)\s+(?:for|to|when|if)\b",
        r"\b(?:designed|intended|aimed|geared|tailored|targeted)\s+(?:for|at|toward|towards)\b",
        r"\b(?:making|makes|made)\s+it\s+(?:\w+\s+)?(?:suitable|ideal|useful|perfect|attractive|"
        r"appealing|well[- ]suited|a\s+good\s+fit|a\s+great\s+fit)\b",
        r"\buse[- ]cases?\b",
        r"\b(?:whether|if|when)\s+you(?:'re|\s+are|\s+need|\s+want)?\b",
        r"\bfor\s+(?:those|anyone|everyone|people)\b",
        r"\bwithout\s+(?:(?:requiring|needing|the\s+need\s+for|having\s+to\s+\w+(?:\s+for)?)\s+)?"
        r"(?:an?\s+|the\s+|any\s+)?(?:" + _WORD + r"\s+){0,2}?"
        r"(?:licen[cs]es?|licen[cs]ing|suites?|subscriptions?|purchases?|fees?|payments?)\b",
        r"\b(?:saves?|spares?|eliminates?|removes?|reduces?|avoids?)\s+(?:the\s+)?"
        r"(?:need|time|effort|hassle|cost|burden|complexity|boilerplate|overhead)\b",
        r"\b(?:simplif(?:y|ies|ying)|streamlin(?:e|es|ing)|accelerat(?:e|es|ing)|"
        r"speed(?:s|ing)?\s+up)\b",
    )
)

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'(\[])")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d{1,3}[.)])\s+")
_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {"the", "and", "for", "with", "that", "this", "are", "not", "but", "its", "can", "has", "have"}
    | {"was", "were", "any", "all", "from", "into", "than", "via", "who", "which", "such", "also"}
    | {"their", "they", "them", "you", "your", "our", "out", "own", "per", "etc", "use", "uses"}
)
_STEM = 5
_QUOTE_LIMIT = 200
_TRAILING_CONNECTORS = frozenset(
    {"and", "or", "but", "so", "that", "which", "who", "to", "for", "of", "by", "in", "with"}
    | {"making", "makes", "while", "when", "where", "enabling", "allowing"}
)
_MIN_HEAD_WORDS = 5
_PREDICATE = re.compile(
    r"\b(?:is|are|was|provides?|offers?|supports?|reads?|writes?|converts?|creates?|generates?|"
    r"renders?|parses?|loads?|saves?|exports?|imports?|targets?|requires?|runs?|exposes?|"
    r"includes?|handles?|models?|implements?|processes|contains?|has|have|uses?|depends?|"
    r"ships?|works?|extracts?|builds?|manipulates?|edits?|opens?|serializes?|validates?)\b",
    re.IGNORECASE,
)

UNSUPPORTED_AUDIENCE = "states an audience, benefit, or use case that no accepted fact states"


def support_texts(accepted_ids: Collection[str], facts: FactsDocument) -> list[str]:
    """The text an audience claim may rest on: the value of every SUPPORTED fact in the section's
    accepted set, and nothing else."""
    return [
        fact.value
        for fact in facts.facts
        if fact.id in accepted_ids and fact.polarity == "SUPPORTED"
    ]


def sentences(text: str) -> list[str]:
    """``text`` as sentences, in order, a bullet marker dropped."""
    found: list[str] = []
    for raw in text.splitlines():
        line = _BULLET.sub("", raw).strip()
        found.extend(part.strip() for part in _SENTENCE_BREAK.split(line) if part.strip())
    return found


def content_words(text: str) -> frozenset[str]:
    """The stems of ``text``'s words that carry meaning: no stopwords, none under three letters."""
    return frozenset(
        word[:_STEM]
        for word in _TOKEN.findall(text.lower())
        if len(word) > 2 and word not in _STOPWORDS
    )


def trigger_start(sentence: str) -> int | None:
    """Where the first audience, benefit, or use-case phrase of ``sentence`` begins, or ``None``."""
    starts = [match.start() for pattern in _PATTERNS if (match := pattern.search(sentence))]
    return min(starts) if starts else None


def _support_windows(support: Iterable[str]) -> list[frozenset[str]]:
    """Every sentence of every supporting text, and every pair of adjacent sentences."""
    windows: list[frozenset[str]] = []
    for text in support:
        parts = [content_words(sentence) for sentence in sentences(text)]
        windows.extend(parts)
        windows.extend(parts[index] | parts[index + 1] for index in range(len(parts) - 1))
    return windows


def unsupported_audience_sentences(text: str, support: Iterable[str]) -> list[str]:
    """The sentences of ``text`` that make an audience, benefit, or use-case claim no ``support``
    text makes, in order."""
    texts = list(support)
    windows: list[frozenset[str]] | None = None
    unsupported: list[str] = []
    for sentence in sentences(text):
        start = trigger_start(sentence)
        if start is None:
            continue
        claim = content_words(sentence[start:])
        if windows is None:
            windows = _support_windows(texts)
        if not any(claim <= window for window in windows):
            unsupported.append(sentence)
    return unsupported


def audience_errors(
    units: Iterable[Mapping[str, Any]], support: Iterable[str], section: str
) -> list[str]:
    """One refusal per unit sentence that states an unsupported audience, benefit, or use case."""
    if section not in AUDIENCE_SECTIONS:
        return []
    texts = list(support)
    errors: list[str] = []
    for unit in units:
        for sentence in unsupported_audience_sentences(str(unit.get("text", "")), texts):
            quoted = sentence if len(sentence) <= _QUOTE_LIMIT else sentence[:_QUOTE_LIMIT] + "..."
            errors.append(
                f"unit {unit.get('slot')}: {UNSUPPORTED_AUDIENCE} ({quoted!r}); state what the "
                "product is and does from the cited facts, as its own actions (it reads, writes, "
                "converts ...), and delete the audience, use-case, suitability, or 'without "
                "requiring ...' wording without replacing it by another"
            )
    return errors


def _trimmed(sentence: str, start: int) -> str | None:
    """``sentence`` cut back to the clause before ``start`` when that clause is a sentence on its
    own, else ``None``."""
    words = sentence[:start].rstrip(" ,;:-").split()
    while words and words[-1].lower().strip(",;:") in _TRAILING_CONNECTORS:
        words.pop()
    head = " ".join(words).rstrip(",;:")
    if len(words) < _MIN_HEAD_WORDS or _PREDICATE.search(head) is None:
        return None
    return head + "."


def strip_audience_claims(text: str, support: Iterable[str]) -> str | None:
    """``text`` with each unsupported audience claim deleted."""
    flagged = set(unsupported_audience_sentences(text, support))
    if not flagged:
        return None
    kept: list[str] = []
    for sentence in sentences(text):
        if sentence not in flagged:
            kept.append(sentence)
            continue
        start = trigger_start(sentence)
        trimmed = _trimmed(sentence, start) if start is not None else None
        if trimmed is not None:
            kept.append(trimmed)
    return " ".join(kept) if kept else None


def strip_audience_units(
    output: dict[str, Any], support: Iterable[str], section: str
) -> dict[str, Any] | None:
    """Last-resort correction for a ``section_authoring`` reply: the unsupported audience claims
    of each unit removed in place."""
    if section not in AUDIENCE_SECTIONS:
        return None
    units = output.get("units")
    if not isinstance(units, list):
        return None
    texts = list(support)
    changed = False
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("text"), str):
            continue
        stripped = strip_audience_claims(unit["text"], texts)
        if stripped is not None:
            unit["text"] = stripped
            changed = True
    return output if changed else None
