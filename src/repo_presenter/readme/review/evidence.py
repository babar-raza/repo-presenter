"""The evidence one review unit carries: the facts its text may cite and the part of the original
README it draws on (reviewer logic 6).

Selection decides what the reviewer SEES, never what is true or what clears a finding: contract
validation and every clearance still read the whole facts document and the whole candidate. A fact
the retrieval misses can only make the reviewer less informed (it may then file an unsupported claim
the full facts would refute), which stays a blocking finding rather than becoming a quiet
acceptance. Retrieval is therefore generous where a miss is costly:

* the product's own identity facts (name, version, install command, formats, dependencies, licence,
  build and test assets, import paths) are always carried;
* a public symbol is carried when the unit's text names it (an identifier or dotted path, in a code
  span or not), whatever its polarity, so a withheld symbol is visible to the reviewer, with the
  docstring, kind and signature the extractor read (authored text paraphrases them, so a reviewer
  without them cannot tell a supported claim from an invented one);
* inherited README units and other facts are ranked by the words they share with the unit's text
  (the unit that says rendering is not implemented is found by a sentence about rendering);
* examples are carried for units that hold an example lead-in, link targets for the resources unit.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping, Sequence

from repo_presenter.core.facts import Fact, FactsDocument

#: Fact kinds that describe the product itself and are small: always carried.
CORE_KINDS = frozenset(
    {
        "identity",
        "package",
        "install_command",
        "format",
        "dependency",
        "license",
        "build_test_asset",
        "import_path",
    }
)
#: Most JSON characters of fact records one unit carries (about 9,000 tokens).
FACTS_CHARS = 36_000
#: Longest fact value shown whole; a longer one is cut and says so.
VALUE_CHARS = 700
#: Longest docstring or signature a symbol record carries.
DOC_CHARS = 240
SIGNATURE_CHARS = 120
#: The attributes of a fact that say what it is or does, in the order a record shows them.
DOC_ATTRIBUTES = ("symbol_kind", "docstring", "signature")
MAX_SYMBOLS = 60
MAX_SYMBOLS_PER_NAME = 3
MAX_RANKED = 16
MAX_EXAMPLES = 12
MAX_LINKS = 40
#: Most characters of the original README a unit carries (about 1,500 tokens).
EXCERPT_CHARS = 6_000
_EXCLUDED = frozenset({"identity:revision"})
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:(?:\.|::)[A-Za-z_][A-Za-z0-9_]*)*")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]{3,}")
_STOP = frozenset(
    [
        "this",
        "that",
        "with",
        "from",
        "have",
        "been",
        "were",
        "will",
        "would",
        "could",
        "should",
        "their",
        "there",
        "which",
        "about",
        "into",
        "than",
        "then",
        "them",
        "these",
        "those",
        "only",
        "also",
        "such",
        "each",
        "other",
        "more",
        "most",
        "some",
        "when",
        "where",
        "while",
        "what",
        "your",
        "yours",
        "using",
        "used",
        "uses",
        "use",
        "into",
        "over",
        "under",
        "between",
        "through",
        "within",
        "without",
        "across",
        "after",
        "before",
        "being",
        "both",
        "does",
        "done",
        "make",
        "made",
        "many",
        "much",
        "must",
        "need",
        "just",
        "like",
        "very",
        "well",
    ]
)


_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_CODE_LIKE = (
    re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:(?:\.|::)[A-Za-z_][A-Za-z0-9_]*)+"),
    re.compile(r"[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+"),
    re.compile(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+"),
)


def identifiers(text: str) -> tuple[str, ...]:
    """The names ``text`` writes as code: every identifier inside a code span, and every dotted,
    CamelCase or snake_case token outside one. Plain words are not names."""
    found: list[str] = []
    for span in _CODE_SPAN.findall(text):
        found.extend(match.group(0) for match in _IDENTIFIER.finditer(span))
    bare = _CODE_SPAN.sub(" ", text)
    for pattern in _CODE_LIKE:
        found.extend(match.group(0) for match in pattern.finditer(bare))
    names = (name.replace("::", ".") for name in found)
    return tuple(dict.fromkeys(name for name in names if len(name) >= 3))


def words(text: str) -> frozenset[str]:
    """The lower-case content words of ``text`` (four letters or more, no stop words)."""
    return frozenset(
        word.lower() for word in _WORD.findall(text) if word.lower() not in _STOP
    )


def _record(fact: Fact) -> dict[str, str]:
    value = fact.value
    if len(value) > VALUE_CHARS:
        value = value[:VALUE_CHARS] + " ... [value cut for length]"
    record = {
        "id": fact.id,
        "kind": fact.kind,
        "value": value,
        "polarity": fact.polarity,
    }
    for name, limit in (
        ("symbol_kind", 40),
        ("docstring", DOC_CHARS),
        ("signature", SIGNATURE_CHARS),
    ):
        text = (fact.attributes or {}).get(name)
        if text:
            record[name] = text if len(text) <= limit else text[:limit] + " ..."
    return record


def _symbol_matches(names: Iterable[str], symbols: list[Fact]) -> list[Fact]:
    """Public symbols a unit names: equal to a named path, or ending in it at a dot."""
    lowered = [(fact.value.lower(), fact) for fact in symbols]
    chosen: dict[str, Fact] = {}
    for name in names:
        wanted = name.lower()
        hits = [
            fact
            for value, fact in lowered
            if value == wanted or value.endswith("." + wanted)
        ]
        hits.sort(key=lambda fact: (len(fact.value), fact.id))
        for fact in hits[:MAX_SYMBOLS_PER_NAME]:
            chosen.setdefault(fact.id, fact)
        if len(chosen) >= MAX_SYMBOLS:
            break
    return sorted(chosen.values(), key=lambda fact: fact.id)[:MAX_SYMBOLS]


def _ranked(unit_words: frozenset[str], candidates: list[Fact]) -> list[Fact]:
    if not unit_words:
        return []
    scored: list[tuple[float, str, Fact]] = []
    for fact in candidates:
        shared = unit_words & words(fact.value)
        if shared:
            scored.append((len(shared) / math.sqrt(len(unit_words)), fact.id, fact))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return sorted((row[2] for row in scored[:MAX_RANKED]), key=lambda fact: fact.id)


def unit_facts(
    document: FactsDocument, text: str, *, sections: Iterable[str]
) -> list[dict[str, str]]:
    """The fact records one unit carries, bounded to ``FACTS_CHARS``. ``text`` is the unit's
    reviewable text; ``sections`` names its sections (an example lead-in carries the examples)."""
    wanted = set(sections)
    facts = [fact for fact in document.facts if fact.id not in _EXCLUDED]
    unit_words = words(text)
    core = [fact for fact in facts if fact.kind in CORE_KINDS]
    symbols = _symbol_matches(
        identifiers(text), [fact for fact in facts if fact.kind == "public_symbol"]
    )
    ranked = _ranked(
        unit_words,
        [
            fact
            for fact in facts
            if fact.kind not in CORE_KINDS
            and fact.kind not in {"public_symbol", "example", "link_target"}
        ],
    )
    examples = (
        [fact for fact in facts if fact.kind == "example"][:MAX_EXAMPLES]
        if wanted & {"quick_start", "additional_examples"}
        else []
    )
    links = (
        [fact for fact in facts if fact.kind == "link_target"][:MAX_LINKS]
        if "documentation_resources" in wanted
        else []
    )
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    size = 2
    for group in (core, ranked, symbols, examples, links):
        for fact in group:
            if fact.id in seen:
                continue
            record = _record(fact)
            cost = len(str(record)) + 2
            if size + cost > FACTS_CHARS:
                continue
            seen.add(fact.id)
            records.append(record)
            size += cost
    return sorted(records, key=lambda record: record["id"])


def _blocks(original: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for row in original.splitlines():
        if not row.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(row)
    if current:
        blocks.append("\n".join(current))
    return blocks


def original_excerpt(original: str, text: str, *, cap: int = EXCERPT_CHARS) -> str:
    """The blocks of ``original`` that share the most words with ``text``, in original order,
    at most ``cap`` characters; blocks that were skipped between two shown ones leave a marker."""
    unit_words = words(text)
    blocks = _blocks(original)
    scored = []
    for index, block in enumerate(blocks):
        shared = unit_words & words(block)
        if shared:
            scored.append((len(shared) / math.sqrt(len(unit_words) or 1), index))
    scored.sort(key=lambda row: (-row[0], row[1]))
    chosen: list[int] = []
    size = 0
    for _score, index in scored:
        length = min(len(blocks[index]), cap) + 2
        if size + length > cap:
            continue
        chosen.append(index)
        size += length
    out: list[str] = []
    previous = -2
    for index in sorted(chosen):
        if previous != -2 and index != previous + 1:
            out.append("[... other parts of the original README not shown ...]")
        out.append(blocks[index][:cap])
        previous = index
    return (
        "\n\n".join(out)
        if out
        else "(no part of the original README shares words with this text)"
    )


#: Most fact ids one line's hint lists.
MAX_HINTS = 8
_HINT_EXCLUDED_KINDS = frozenset({"inherited_unit", "example"})


def support_hints(
    rows: Mapping[int, str], records: Sequence[Mapping[str, str]]
) -> dict[str, list[str]]:
    """For each shown line, the ids of the carried facts whose VALUE occurs in it: a public symbol the
    line names, a format, the package name, a link target. A search aid for the reviewer, nothing
    more: a line with hints can still claim what no fact says, a line with none may paraphrase a
    docstring, and the hint never clears or confirms anything (``review.clearances`` is a closed
    catalogue that reads no hint). An inherited README unit is never a hint: it is maintainer text,
    not evidence of support."""
    symbols = [r for r in records if r["kind"] == "public_symbol"]
    others = [
        r
        for r in records
        if r["kind"] not in _HINT_EXCLUDED_KINDS and r["kind"] != "public_symbol"
    ]
    hints: dict[str, list[str]] = {}
    for number, row in rows.items():
        lowered = row.lower()
        found: set[str] = set()
        for name in identifiers(row):
            wanted = name.lower()
            for record in symbols:
                value = record["value"].lower()
                if value == wanted or value.endswith("." + wanted):
                    found.add(record["id"])
        for record in others:
            value = record["value"].strip().lower()
            if (len(value) >= 4 or (value.startswith(".") and len(value) >= 3)) and value in lowered:
                found.add(record["id"])
        if found:
            hints[f"{number:04d}"] = sorted(found)[:MAX_HINTS]
    return hints
