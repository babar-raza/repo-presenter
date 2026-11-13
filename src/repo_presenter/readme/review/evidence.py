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
from types import MappingProxyType

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
#: 240, not 120: Aspose.BarCode Python's ``generate`` signature is 131 characters and the cut fell
#: before ``-> Barcode``, the return type its API reference sentence states (run 43430657331).
SIGNATURE_CHARS = 240
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
#: Fact kinds whose evidence detail (and ``message`` attribute) a record carries: what makes a
#: format UNRESOLVED or a member unimplemented is stated there, not in the value.
_EVIDENCED_KINDS = frozenset({"format", "implementation"})
EVIDENCE_DETAILS = 3
EVIDENCE_CHARS = 360
#: Most facts the plan's citations for a unit's sections may add (``unit_facts``'s ``cited``).
MAX_CITED = 60
_REEXPORT_OF = re.compile(r"\bre-export of ([A-Za-z_][\w.]*)")
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
    attributes = fact.attributes or {}
    for name, limit in (
        ("symbol_kind", 40),
        # BL-063 (K03): what a member really is and whether a caller may set it, so the reviewer
        # can tell a property from a method and a read-only property from a settable one.
        ("member_kind", 40),
        ("settable", 10),
        ("type_kind", 40),
        ("docstring", DOC_CHARS),
        ("signature", SIGNATURE_CHARS),
    ):
        text = attributes.get(name)
        if text:
            record[name] = text if len(text) <= limit else text[:limit] + " ..."
    if fact.kind == "public_symbol":
        # A type re-exported from a private module keeps its doc comment only as
        # ``docstring_full`` (``source_detail``): ``renderers.PngRenderer`` reads "Render a barcode
        # into PNG output", which is what a sentence saying it renders PNG rests on, and an alias
        # (``aspose_barcode_foss.PngRenderer``) is the class its evidence names. Aspose.BarCode
        # Python, run 43430657331: both sentences were filed unsupported without either shown.
        full = attributes.get("docstring_full")
        if full and not attributes.get("docstring"):
            record["docstring"] = full if len(full) <= DOC_CHARS else full[:DOC_CHARS] + " ..."
        target = next(
            (
                match.group(1)
                for evidence in fact.evidence
                for match in _REEXPORT_OF.finditer(evidence.detail or "")
            ),
            None,
        )
        if target:
            record["reexport_of"] = target
    if fact.kind in _EVIDENCED_KINDS:
        # What the extractor read is the claim's proof for these kinds: a format UNRESOLVED
        # because its only dispatch is "an unimplemented stub", a member that "throws
        # UnsupportedOperationException" with the source's own message. Without it the reviewer
        # sees `.fbx UNRESOLVED` and cannot verify "no working load or save path" (Aspose.3D
        # Java Lane R, run 43413886429: six such scope_limitations sentences filed unsupported).
        message = (fact.attributes or {}).get("message")
        if message:
            record["message"] = (
                message if len(message) <= DOC_CHARS else message[:DOC_CHARS] + " ..."
            )
        details = "; ".join(
            dict.fromkeys(e.detail for e in fact.evidence[:EVIDENCE_DETAILS] if e.detail)
        )
        if details:
            record["evidence"] = (
                details if len(details) <= EVIDENCE_CHARS else details[:EVIDENCE_CHARS] + " ..."
            )
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


#: Fact kinds a claim's distinctive term can be proven (or refuted) by beyond the symbols and core
#: facts: what the source implements, its fields and project files. Maintainer README units are
#: never term evidence (they are the claims, not support for them).
_TERM_EVIDENCE_KINDS = frozenset(
    {"implementation", "member_field", "internal_symbol", "project_file", "package"}
)
#: Most facts one distinctive name pulls in, and the most the whole term group may carry.
MAX_TERM_FACTS_PER_NAME = 3
MAX_TERM_FACTS = 24
#: A format-named enumeration (``LoadFormat``, ``SaveFormat``, ``ImageFormat``) lists, by its
#: members, the formats the product reads or writes -- the proof a "reads DOCX, RTF, Markdown"
#: claim needs, though the claim names no identifier.
MAX_FORMAT_MEMBERS = 16
_FORMAT_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]{2,}")


def _format_members(text: str, enum_members: list[Fact]) -> list[Fact]:
    """Members of format-named enumerations whose own name (``DOCX``, ``MARKDOWN``, ``PDF``) the
    unit's text writes as a word, in any case: the enumeration is what makes the format claim
    checkable, and ``_symbol_matches`` only finds a member the text writes as a dotted path."""
    tokens = {token.lower() for token in _FORMAT_TOKEN.findall(text)}
    chosen = [
        fact
        for fact in enum_members
        if "format" in fact.id.lower()
        and fact.value.rsplit(".", 1)[-1].lower() in tokens
    ]
    return sorted(chosen, key=lambda fact: fact.id)[:MAX_FORMAT_MEMBERS]


def _stems(text_words: Iterable[str]) -> frozenset[str]:
    return frozenset(word[:5] for word in text_words if len(word) >= 5)


def _term_support(
    names: Iterable[str], candidates: list[Fact], unit_words: frozenset[str] = frozenset()
) -> list[Fact]:
    """Facts of the evidence kinds whose id or value spells a name the unit writes as code, so a
    claim about ``Document.light_document_model`` is shown what the source says that attribute
    does (here: its getter raises ``ValueError``), whatever its word overlap with the unit."""
    chosen: dict[str, Fact] = {}
    for name in names:
        wanted = name.lower()
        hits = [
            fact
            for fact in candidates
            if wanted in fact.id.lower() or wanted in fact.value.lower()
        ]
        # The facts about this name that also share the unit's other words come first: for
        # "`Scene` rendering is not implemented" that is ``scene.render`` throwing, not the
        # shortest ``scene.*`` ids (``Scene.save``, ``Scene.VERSION``).
        stems = _stems(unit_words - {wanted})
        hits.sort(
            key=lambda fact: (
                -sum(stem in fact.id.lower() or stem in fact.value.lower() for stem in stems),
                len(fact.id),
                fact.id,
            )
        )
        for fact in hits[:MAX_TERM_FACTS_PER_NAME]:
            chosen.setdefault(fact.id, fact)
        if len(chosen) >= MAX_TERM_FACTS:
            break
    return sorted(chosen.values(), key=lambda fact: fact.id)[:MAX_TERM_FACTS]


def unit_facts(
    document: FactsDocument,
    text: str,
    *,
    sections: Iterable[str],
    cited: Iterable[str] = (),
    given: Iterable[str] = (),
    members: Mapping[str, Sequence[str]] = MappingProxyType({}),
) -> list[dict[str, str]]:
    """The fact records one unit carries, bounded to ``FACTS_CHARS``. ``text`` is the unit's
    reviewable text; ``sections`` names its sections (an example lead-in carries the examples).
    ``cited`` are the fact ids the plan carries into those sections (a limitation's or
    capability's ``fact_ids``): the facts the text was written from, carried right after the core
    facts so no word-overlap ranking can leave them out.

    ``given`` are the facts an authored API reference row was written from, exactly as its type
    batch gave them (``authoring.type_unit_facts``: the type fact and its implementation facts),
    and ``members`` the verified member names that batch listed with each type fact: the type's
    record carries them as ``members``, the same field the author was shown. They come right after
    the plan's citations, before every ranked or name-matched group, uncapped but for
    ``FACTS_CHARS``: a row's sentence restates nothing else (Aspose.3D TypeScript run
    43430680427)."""
    wanted = set(sections)
    facts = [fact for fact in document.facts if fact.id not in _EXCLUDED]
    unit_words = words(text)
    core = [fact for fact in facts if fact.kind in CORE_KINDS]
    symbols = _symbol_matches(
        identifiers(text),
        [fact for fact in facts if fact.kind in {"public_symbol", "enum_member"}],
    )
    enum_members = [fact for fact in facts if fact.kind == "enum_member"]
    support = _format_members(text, enum_members) + _term_support(
        identifiers(text),
        [fact for fact in facts if fact.kind in _TERM_EVIDENCE_KINDS],
        unit_words,
    )
    by_id = {fact.id: fact for fact in facts}
    citations = [by_id[fact_id] for fact_id in dict.fromkeys(cited) if fact_id in by_id][
        :MAX_CITED
    ]
    rows = [by_id[fact_id] for fact_id in dict.fromkeys(given) if fact_id in by_id]
    ranked = _ranked(
        unit_words,
        [
            fact
            for fact in facts
            if fact.kind not in CORE_KINDS
            and fact.kind not in {"public_symbol", "enum_member", "example", "link_target"}
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
    # ``support`` is last: it only spends budget the groups above left over, so adding it can never
    # displace a fact the reviewer was already shown.
    for group in (core, citations, rows, ranked, symbols, examples, links, support):
        for fact in group:
            if fact.id in seen:
                continue
            record = _record(fact)
            if members.get(fact.id):
                record["members"] = ", ".join(members[fact.id])
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
