"""A maintainers' API table cell that does not describe its type, replaced by the type's own doc
comment summary when the source has one; reported when it has none.

A type's description says what the type is for. Three cell shapes say nothing of the kind, and the
owner rejected each by name in the Aspose.3D FOSS for Java Lane L review (2026-11-13):

* a count -- "Class with 18 methods and 6 properties.", "Enum with 2 members.";
* a label -- "Interface in the 3D JAVA API.", "Public class.", "X is a public symbol ...";
* file-header bookkeeping quoted as if it were a summary -- "Created by lexchou on 12/14/2016."
  (``extractors.surface.doc_text.is_bookkeeping``).

When the row's type (a SUPPORTED type-level ``public_symbol`` fact, resolved by the row's name
uniquely) carries a doc comment that ``doc_text.usable_doc`` accepts -- no hole, no markup, no
bookkeeping -- the cell is a verified defect: the source states what the type is, and the README
states something else. Only that cell's text is replaced (a ``FALSE_CLAIM_FIX`` within one line),
by the summary exactly as the Lane R renderer quotes it (``|`` as ``/``, no backticks); the type
name, the other cells and every other row are untouched.

When the type has no usable doc comment nothing in the evidence says what it is for, so Lane L
does not guess: the cell is reported (``NO_DOC_COMMENT``, not a defect the run could repair -- only
authored prose can describe such a type, which is Lane R's job). A cell of any other shape is the
maintainers' own description and is never touched.

Version 2 (BL-080, 2026-11-13): a cell of any shape that a SUPPORTED fact refutes as a whole -- an
exception type described as thrown that no library code throws, a stub described as working -- is
replaced by the fact-true text the Lane R renderer prints for the same type (:func:`fact_true_cell`).

Version 3 (BL-098, M9 round 43559491132, Words Python Lane L control ab8a03 line 402): a count cell
the facts refute is made true. ``| `Style` | Class with 11 properties. |`` -- ``Style`` declares 15
annotated fields (``light_document_model.py:1012-1027`` at 2d2efee2) -- reads "Class with 15
properties.": each stated tally is held to the type fact's ``member_counts`` (the extractor's own
methods/properties/fields of the class body, ``source_detail.python_member_counts``, read for sealed
facts by ``recertify.current_surface``): "methods" to the public methods (with or without the dunders
and ``__init__``),
"properties" to fields plus properties (or either alone), "fields" to fields; a count matching any
reading stays, a wrong one becomes fields plus properties / public methods. A count above every
reading is refuted only for a class with no base that could add members (``inherits``): inherited
members never make a count smaller, so a count below them is refuted whatever the bases. "members", values,
constants and functions, or a type with no ``member_counts``, are never judged. Only the wrong numbers change; the row and its other cells stay (R14). A cell that
the type's doc comment can replace is still replaced by it, as before.

Version 4 (BL-005, owner feedback 536baa63f4: "Above are all wrong description ... Handle this on
global level"): a count, label or bookkeeping cell of a type with no usable doc comment is no longer
only reported: it is replaced by :class:`TypeDescriber`'s fact-true description (the type's kind,
nearest bases, member names by recorded kind, Python fields, enum values) -- never purpose text --
and the same describer serves Lane R (``renderer._described``, ``surface_claims.kept_unit_form``).
A type the facts say nothing more about is still reported (``NO_DOC_COMMENT``).

:func:`cell_shape` is the one classification of a description cell, shared with
``scripts/measure_type_descriptions.py`` (the portfolio Pareto measurement), so the measurement and
the correction cannot disagree about which cells are bad.
"""

from __future__ import annotations

import re
from typing import Any

from repo_presenter.core.facts import Fact
from repo_presenter.extractors.surface.doc_text import is_bookkeeping, usable_doc
from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.model import (
    FALSE_CLAIM_FIX,
    MAX_SPAN,
    Context,
    DetectorResult,
    Edit,
    Finding,
)

DETECTOR = "type_description"

SHAPE_DOC = "doc_comment"
SHAPE_COUNT = "count_only"
SHAPE_LABEL = "boilerplate_label"
SHAPE_BOOKKEEPING = "doc_bookkeeping"
SHAPE_OTHER = "other_prose"
#: The shapes that do not describe a type.
NON_DESCRIPTIVE: frozenset[str] = frozenset({SHAPE_COUNT, SHAPE_LABEL, SHAPE_BOOKKEEPING})

_TYPE_KINDS = frozenset({"class", "enum", "interface", "struct", "trait"})
_TALLY = r"\d+\s+(?:methods?|members?|propert(?:y|ies)|values?|fields?|constants?|functions?)"
_COUNT = re.compile(
    rf"^(?:class|enum(?:eration)?|interface|struct|trait|type|module|record)\s+with\s+{_TALLY}"
    rf"(?:\s*(?:,|and)\s*{_TALLY})*\.?$",
    re.IGNORECASE,
)
_LABEL = re.compile(
    r"^(?:class|enum(?:eration)?|interface|struct|trait|type)\s+in\s+the\s+[^.]*\bAPI\.?$"
    r"|^public\s+(?:class|enum|interface|struct|trait|type|symbol)\.?$"
    r"|^\S+\s+is\s+a\s+public\s+(?:symbol|class|enum|interface|type)\b",
    re.IGNORECASE,
)
_NAME_CELL = re.compile(r"^\s*`([A-Za-z_][\w.]*)`\s*$")


def _plain(text: str) -> str:
    return " ".join(text.replace("`", "").replace("*", "").split()).strip()


def cell_shape(description: str, docstring: str = "", symbol: str = "") -> str:
    """The shape of one API table description cell, given its type's stored doc comment."""
    text = _plain(description)
    if is_bookkeeping(text):
        return SHAPE_BOOKKEEPING
    if _COUNT.match(text):
        return SHAPE_COUNT
    if _LABEL.search(text):
        return SHAPE_LABEL
    summary = _plain(usable_doc(docstring, symbol)) if docstring else ""
    if summary:
        a, b = text.lower().rstrip("."), summary.lower().rstrip(".")
        if a.startswith(b[:40]) or b.startswith(a[:40]):
            return SHAPE_DOC
    return SHAPE_OTHER


_TALLY_PART = re.compile(r"(?i)(?P<count>\d+)\s+(?P<kind>methods?|members?|propert(?:y|ies)|fields?)\b")
# "properties" may be read as fields plus properties, fields alone or properties alone; "methods" with
# or without the dunder methods: a count matching any reading is left as the maintainers wrote it.


def member_counts(fact: Fact) -> dict[str, int] | None:
    """The type fact's ``member_counts`` attribute as ``{"method": n, "property": n, "field": n}``."""
    raw = (fact.attributes or {}).get("member_counts")
    if not raw:
        return None
    try:
        counts = {k: int(v) for k, v in (part.split("=", 1) for part in raw.split(","))}
    except ValueError:
        return None
    return counts if {"method", "dunder", "init", "property", "field", "inherits"} <= set(counts) else None


def true_count_cell(cell: str, fact: Fact) -> str | None:
    """``cell`` with every tally the type's ``member_counts`` refutes replaced by the true count (the
    noun's number agreeing), or ``None`` when no tally is refuted or none can be judged."""
    counts = member_counts(fact)
    if counts is None or not _COUNT.match(_plain(cell)):
        return None
    # Every reading a maintainer's count can truthfully have; the first is what a wrong count becomes.
    # "members" is never judged: maintainers use it for enum-like constants as well (PDF Python
    # ``Encoding``: "1 method and 4 members", its four class-level constants).
    readings = {
        "method": tuple(dict.fromkeys((
            counts["method"], counts["method"] + counts["dunder"], counts["method"] + counts["init"],
            counts["method"] + counts["dunder"] + counts["init"],
        ))),
        "propert": (counts["property"] + counts["field"], counts["field"], counts["property"]),
        "field": (counts["field"],),
    }
    changed = False

    def fix(match: re.Match[str]) -> str:
        nonlocal changed
        kind = match.group("kind").lower()
        key = next((k for k in readings if kind.startswith(k)), None)
        stated = int(match.group("count"))
        if key is None or stated in readings[key]:
            return match.group(0)
        if counts["inherits"] and stated > max(readings[key]):
            return match.group(0)  # a base may add members the maintainers counted: not refuted
        true = readings[key][0]
        changed = True
        noun = {"method": "method", "propert": "property", "field": "field"}[key]
        word = noun if true == 1 else {"property": "properties"}.get(noun, noun + "s")
        if match.group("kind")[0].isupper():
            word = word.capitalize()
        return f"{true} {word}"

    fixed = _TALLY_PART.sub(fix, cell)
    return fixed if changed else None


def type_facts_by_name(facts: list[Fact]) -> dict[str, list[Fact]]:
    """SUPPORTED type-level public symbols, by full value and by their last segment."""
    found: dict[str, list[Fact]] = {}
    for fact in facts:
        if fact.kind != "public_symbol" or fact.polarity != "SUPPORTED":
            continue
        if (fact.attributes or {}).get("symbol_kind") not in _TYPE_KINDS:
            continue
        for key in {fact.value, fact.value.rsplit(".", 1)[-1]}:
            found.setdefault(key, []).append(fact)
    return found


def description_rows(ctx: Context) -> list[tuple[int, int, str, str]]:
    """``(line number, cell offset, type name, cell text)`` of every two-column table row outside
    a fence whose first cell is one code-spanned name."""
    rows: list[tuple[int, int, str, str]] = []
    for line in ctx.lines:
        text = line.text
        if line.in_fence or not text.lstrip().startswith("|") or not text.rstrip().endswith("|"):
            continue
        bars = [i for i, char in enumerate(text) if char == "|" and (i == 0 or text[i - 1] != "\\")]
        if len(bars) != 3:
            continue
        name = _NAME_CELL.match(text[bars[0] + 1 : bars[1]])
        if name is None:
            continue
        raw = text[bars[1] + 1 : bars[2]]
        cell = raw.strip()
        if not cell or set(cell) <= set("-: "):
            continue
        offset = line.start + bars[1] + 1 + (len(raw) - len(raw.lstrip()))
        rows.append((line.number, offset, name.group(1), cell))
    return rows


#: At most this many names of one kind are listed in a fact-true description; more read "including".
DESCRIBED_NAMES = 6
#: At most this many enum values are listed (the renderer's own enum fallback cut).
DESCRIBED_VALUES = 8
#: The README's own kind noun for a type, kept in a fact-true description when no fact says otherwise.
_NOUNS = {"class": "Class", "interface": "Interface", "struct": "Struct", "trait": "Trait", "enum": "Enum"}
_ROOT_BASES = frozenset({"object", "Object", "System.Object"})


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


class TypeDescriber:
    """Fact-true descriptions of types from their verified members, bases and enum values, built
    once per facts document (BL-005, owner feedback 536baa63f4: "Class with 1 method.",
    "Interface in the 3D JAVA API.", "Enum with 2 members." and "Created by lexchou on
    12/14/2016." are not descriptions).

    Never purpose text: only what the facts state -- the type's declared kind (``type_kind``), the
    types it derives from (``bases``/``declaration``, else the file a member it carries was declared
    in, which is where an inherited member's evidence points), the names of its own public
    constructors, methods and other members by the kind the facts record, and an enum's values.
    The list phrases are the shapes BC-14's member-kind rule reads ("the methods a, b and c",
    "methods including ..."), with a kind word only where the facts record that kind, so the
    renderer, the correction and the validator cannot disagree about a row."""

    def __init__(self, facts: Any) -> None:
        from repo_presenter.readme.validation.surface_claims import member_kind

        self._member_kind = member_kind
        self.facts = facts
        self.members: dict[str, list[Fact]] = {}
        self.values: dict[str, list[Fact]] = {}
        self.types_by_path: dict[str, list[Fact]] = {}
        self.types_by_name: dict[str, list[Fact]] = {}
        symbols = [f for f in facts.by_kind("public_symbol") if f.polarity == "SUPPORTED"]
        type_values = {
            f.value
            for f in symbols
            if (f.attributes or {}).get("symbol_kind") in _TYPE_KINDS | {"module"}
        }
        for fact in symbols:
            kind = (fact.attributes or {}).get("symbol_kind")
            if kind in _TYPE_KINDS and fact.evidence:
                self.types_by_path.setdefault(fact.evidence[0].path, []).append(fact)
            if kind in _TYPE_KINDS:
                self.types_by_name.setdefault(fact.value.rsplit(".", 1)[-1], []).append(fact)
            if fact.value in type_values:
                continue
            owner = fact.value.rpartition(".")[0]
            if owner:
                self.members.setdefault(owner, []).append(fact)
        for fact in facts.by_kind("enum_member"):
            if fact.polarity == "SUPPORTED":
                self.values.setdefault(str((fact.attributes or {}).get("enum", "")), []).append(fact)

    @staticmethod
    def _owners(fact: Fact) -> list[str]:
        attributes = fact.attributes or {}
        owners = [fact.value, attributes.get("defined_at", "")]
        owners += [p.strip() for p in str(attributes.get("public_paths", "")).split(",")]
        return list(dict.fromkeys(o for o in owners if o))

    def _direct_candidates(self, fact: Fact) -> list[str]:
        """The simple names of the types ``fact`` derives from: its declared bases, else the type
        declared in each file one of its member facts' evidence points at (an inherited member)."""
        from repo_presenter.readme.validation.surface_claims import _base_names

        bases = [b for b in _base_names(fact) if b and b not in _ROOT_BASES]
        if bases:
            return list(dict.fromkeys(bases))
        home = fact.evidence[0].path if fact.evidence else ""
        found: list[str] = []
        for owner in self._owners(fact):
            for member in self.members.get(owner, []):
                path = member.evidence[0].path if member.evidence else ""
                if not home or not path or path == home:
                    continue
                stem = path.rsplit("/", 1)[-1].split(".", 1)[0]
                declared = [
                    t for t in self.types_by_path.get(path, []) if t.value.rsplit(".", 1)[-1] == stem
                ]
                if len(declared) == 1 and declared[0].value != fact.value and stem not in found:
                    found.append(stem)
        return found

    def _ancestors(self, name: str, seen: frozenset[str] = frozenset()) -> set[str]:
        """Every type name above the type of simple name ``name`` (unique only), transitively."""
        if name in seen:
            return set()
        matches = self.types_by_name.get(name, [])
        if len(matches) != 1:
            return set()
        above = set(self._direct_candidates(matches[0]))
        for base in list(above):
            above |= self._ancestors(base, seen | {name})
        return above

    def bases(self, fact: Fact) -> list[str]:
        """The nearest types ``fact`` derives from: a candidate that is an ancestor of another
        candidate is reached through it, so it is not named (``VertexElementPolygonGroup`` derives
        from ``VertexElementIntsTemplate``, which derives from ``VertexElement``)."""
        candidates = self._direct_candidates(fact)
        if len(candidates) < 2:
            return candidates
        above: set[str] = set()
        for name in candidates:
            above |= self._ancestors(name)
        return [name for name in candidates if name not in above] or candidates

    def describe(self, fact: Fact, noun: str = "") -> tuple[str, tuple[str, ...]]:
        """``(description, cited fact ids)``; an empty description when the facts state nothing
        about the type beyond its name. ``noun`` is the README's own kind word ("Interface"), kept
        only when the facts record no kind of their own."""
        from repo_presenter.readme.validation.surface_claims import type_kind

        attributes = fact.attributes or {}
        if attributes.get("symbol_kind") == "enum":
            values: list[Fact] = []
            for owner in self._owners(fact):
                values += self.values.get(owner, [])
            names = sorted({v.value.rsplit(".", 1)[-1] for v in values})
            if not names and attributes.get("enum_values"):
                # A sealed Java enum read before the surface recorded its constants: the values
                # re-certification read from its declaration at the pinned revision (BL-006).
                names = sorted({v.strip() for v in str(attributes["enum_values"]).split(",") if v.strip()})
            if not names:
                return "", ()
            shown = names[:DESCRIBED_VALUES]
            lead = "Enumerates values including" if len(names) > len(shown) else "Enumerates"
            cited = tuple(dict.fromkeys(v.id for v in values))[:DESCRIBED_VALUES]
            return f"{lead} {_join(shown)}.", (fact.id, *cited)
        simple = fact.value.rsplit(".", 1)[-1]
        home = fact.evidence[0].path if fact.evidence else ""
        members: list[Fact] = []
        for owner in self._owners(fact):
            members += self.members.get(owner, [])
        own = [
            member
            for member in members
            if not (home and member.evidence and member.evidence[0].path not in {"", home})
        ]
        bases = self.bases(fact)
        groups: dict[str, list[str]] = {"constructor": [], "method": [], "property": [], "field": [], "member": []}
        cited: list[str] = [fact.id]
        for member in own:
            name = member.value.rsplit(".", 1)[-1]
            recorded = self._member_kind(member, simple)
            signature = (member.attributes or {}).get("signature", "")
            path = member.evidence[0].path if member.evidence else ""
            if recorded == "constructor" or name in {simple, "__init__", "constructor"}:
                key = "constructor"
            elif name.startswith("_"):
                continue
            elif recorded == "method" or (
                # A Python property's signature has a parameter list too (``paragraphs(self)``):
                # with no recorded kind, a Python member is only ever called a member.
                recorded is None and "(" in signature and not path.endswith((".py", ".pyi"))
            ):
                key = "method"
            elif recorded in {"property", "field"}:
                key = recorded
            else:
                key = "member"
            if name not in groups[key]:
                groups[key].append(name)
                if len(cited) < 1 + DESCRIBED_NAMES * 2:
                    cited.append(member.id)
        if not groups["field"] and not groups["property"] and attributes.get("fields"):
            # A Python class's annotated fields, as the surface records them on the type fact
            # (``fields``: Page Python ``AxialShading``: "color_space, coords, domain, function,
            # extend"); the surface records no member fact for them.
            groups["field"] = [
                name for name in dict.fromkeys(f.strip() for f in str(attributes["fields"]).split(","))
                if name and not name.startswith("_")
            ]
        singular = {"methods": "method", "properties": "property", "fields": "field", "members": "member"}
        listed: list[str] = []
        for key, word in (("method", "methods"), ("property", "properties"), ("field", "fields"), ("member", "members")):
            names = groups[key]
            if not names:
                continue
            shown = names[:DESCRIBED_NAMES]
            if len(names) > len(shown):
                listed.append(f"{word} including {_join(shown)}")
            elif len(shown) == 1:
                listed.append(f"the {singular[word]} {shown[0]}")
            else:
                listed.append(f"the {word} {_join(shown)}")
        clauses: list[str] = []
        if bases:
            clauses.append(f"inherits from {_join(bases)}")
        if listed:
            clauses.append("declares " + " and ".join(listed))
        elif groups["constructor"]:
            signatures = [
                (m.attributes or {}).get("signature", "")
                for m in own
                if m.value.rsplit(".", 1)[-1] in {simple, "__init__", "constructor"}
                or self._member_kind(m, simple) == "constructor"
            ]
            bare = bool(signatures) and all(s.replace(" ", "").endswith("()") for s in signatures)
            clauses.append(
                "declares a public no-argument constructor" if bare else "declares a public constructor"
            )
        # A type with no member fact is NOT described as empty: measured over the 46 sealed facts
        # documents, 1,300+ such types do have members the surface records elsewhere (Python
        # dataclass fields as ``member_field`` facts, C# indexers), so "declares no public
        # members" would be a false claim. Such a cell stays as written and is reported.
        if not clauses:
            return "", ()
        body = " and ".join(clauses)
        kind = type_kind(fact)
        word = _NOUNS.get(kind or "", "") or (noun if kind is None else "")
        text = f"{word} that {body}." if word else f"{body[0].upper()}{body[1:]}."
        return text, tuple(cited)


def describer_for(facts: Any) -> TypeDescriber:
    """The :class:`TypeDescriber` of ``facts``, built once per document object."""
    cache = getattr(describer_for, "_cache", None)
    if cache is None or cache[0] is not facts:
        cache = (facts, TypeDescriber(facts))
        describer_for._cache = cache  # type: ignore[attr-defined]
    return cache[1]


def _cell_noun(cell: str) -> str:
    """The README's own kind word a label or count cell opens with ("Interface in the ..."), or ''."""
    first = _plain(cell).split(" ", 1)[0].lower()
    first = "enum" if first.startswith("enum") else first
    return _NOUNS.get(first, "")


def label_replacement(facts: Any, types: dict[str, list[Fact]], name: str, cell: str) -> tuple[str, tuple[str, ...]] | None:
    """``(replacement, cited fact ids)`` for a description cell of ``name`` that is only a count,
    a label or bookkeeping: the type's usable doc comment, else :class:`TypeDescriber`'s fact-true
    description; ``None`` when the cell describes its type, names no unique type, or the facts
    state nothing that could replace it."""
    candidates = types.get(name) or types.get(name.rsplit(".", 1)[-1]) or []
    docs = {(fact.attributes or {}).get("docstring") or "" for fact in candidates}
    if len(docs) != 1:
        return None
    fact = candidates[0]
    docstring = docs.pop()
    if cell_shape(cell, docstring, fact.value) not in NON_DESCRIPTIVE:
        return None
    summary = usable_doc(docstring, fact.value) if docstring else ""
    if summary and not is_bookkeeping(summary):
        text, cited = summary, (fact.id,)
    else:
        text, cited = describer_for(facts).describe(fact, _cell_noun(cell))
    text = " ".join(text.replace("|", "/").replace("`", "").split())
    return (text, cited) if text and text != cell else None


def fact_true_label_cells(text: str, facts: Any) -> str:
    """``text`` (a rendered Lane R README) with every API table cell that is only a count, a label
    or bookkeeping replaced by :func:`label_replacement` -- the cells a kept maintainers' table
    carries verbatim (Cells TypeScript ``037.table``: "Class in the Cells TYPESCRIPT API.",
    "Class with 5 methods and 2 properties."; 3D Python ``FileFormat``). The renderer's own rows
    never take these forms (``renderer._label_only``); the row, its name cell and every other
    cell are untouched (R14), and the replacement is the Lane L correction's own (one rule)."""
    from repo_presenter.core.registry_entry_stub import RegistryEntryStub

    types = type_facts_by_name(list(facts.facts))
    if not types:
        return text
    ctx = Context(
        entry=RegistryEntryStub(repository=facts.repository, family="", platform="", ecosystem=""),
        facts=facts,
        readme=text,
        tree_paths=(),
    )
    edits: list[tuple[int, int, str]] = []
    for _number, offset, name, cell in description_rows(ctx):
        found = label_replacement(facts, types, name, cell)
        if found is not None and text[offset : offset + len(cell)] == cell:
            edits.append((offset, offset + len(cell), found[0]))
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


#: What a whole-stub type's cell reads after the correction: the Lane R renderer's own wording
#: (``composition.renderer._stub_marked``), so both lanes describe the type the same way.
STUB_DESCRIPTION = "Not implemented."


def fact_true_cell(
    ctx: Context, name: str, fact: Fact, cell: str, stubs: Any = None
) -> tuple[str, str, str] | None:
    """``(replacement, refuting fact id, why)`` when a SUPPORTED fact refutes the maintainers'
    description cell of ``name`` as a whole, else ``None``:

    * an exception type the cell says is thrown ("Exception raised by internal rendering
      drivers.") while an ``implementation`` fact says no library code throws or constructs it
      (``code_path_claims.refuted_thrown_description``, the rule's own judgement) reads
      ``NOT_THROWN_DESCRIPTION``, exactly as the Lane R renderer prints it (BL-079);
    * a type the maintainers' own limitation statements say only throws
      (``surface_claims.StubIndex``), described as working, reads ``STUB_DESCRIPTION`` -- unless
      every method body of the type was read and returns a value (``type_returns_values``): the
      limitation statement is then the false one (3D .NET's ``RenderFactory``), and the cell is
      left as written.

    Decision (BL-080, 2026-11-13): replace the cell, keep the row. The type is real public API;
    only what the cell says it does is false, and the row's other cells are untouched. Measured:
    Aspose.3D-FOSS-for-.NET, hosted Lane L run 43513031042, REJECTed with 18 blocking findings
    because the run made no content edit, so not one pre-existing defect could ride as an R21
    residual; four of them were such cells (``DriverException``, ``ExportException``,
    ``ImportException``, ``InitializationException``) and one ``Watermark``, all maintainer text
    this correction can make fact-true."""
    from repo_presenter.readme.validation.code_path_claims import (
        NOT_THROWN_DESCRIPTION,
        refuted_thrown_description,
        type_returns_values,
    )
    from repo_presenter.readme.validation.surface_claims import StubIndex, describes_as_working

    plain = _plain(cell)
    refuting = refuted_thrown_description(fact.value, plain, ctx.facts)
    if refuting is not None and plain != NOT_THROWN_DESCRIPTION:
        return NOT_THROWN_DESCRIPTION, refuting, "says the type is thrown, but no library code throws it"
    stubs = stubs if stubs is not None else StubIndex(ctx.facts)
    short = name.rsplit(".", 1)[-1]
    if (
        short in stubs.types
        and describes_as_working(plain)
        and not type_returns_values(short, ctx.facts)
    ):
        return STUB_DESCRIPTION, stubs.types[short], "describes a stub as working"
    return None


@detector(DETECTOR)
def type_description(ctx: Context) -> DetectorResult:
    types = type_facts_by_name(list(ctx.facts.facts))
    if not types:
        return DetectorResult()
    from repo_presenter.readme.validation.surface_claims import StubIndex

    stubs = StubIndex(ctx.facts)
    edits: list[Edit] = []
    findings: list[Finding] = []
    for number, offset, name, cell in description_rows(ctx):
        candidates = types.get(name) or types.get(name.rsplit(".", 1)[-1]) or []
        docs = {(fact.attributes or {}).get("docstring") or "" for fact in candidates}
        if len(docs) != 1:
            continue  # no such type, or two types of that name documented differently
        fact = candidates[0]
        docstring = docs.pop()
        refuted = fact_true_cell(ctx, name, fact, cell, stubs)
        if refuted is not None:
            replacement, refuting, why = refuted
            if len(cell) <= MAX_SPAN and ctx.readme[offset : offset + len(cell)] == cell:
                edits.append(
                    Edit(
                        kind=FALSE_CLAIM_FIX,
                        detector=DETECTOR,
                        start=offset,
                        end=offset + len(cell),
                        original=cell,
                        replacement=replacement,
                        fact_ids=(fact.id, refuting),
                        rationale=f"line {number}: the cell {cell!r} {why}; {refuting} says so",
                    )
                )
            continue
        shape = cell_shape(cell, docstring, fact.value)
        if shape not in NON_DESCRIPTIVE:
            continue
        summary = usable_doc(docstring, fact.value) if docstring else ""
        if summary and is_bookkeeping(summary):
            summary = ""
        if not summary:
            # Version 4 (BL-005): no doc comment says what the type is, so the cell is replaced by
            # what the facts state about it -- its kind, bases, member names or enum values --
            # never by a count or a label, and never by invented purpose text. The row stays (R14).
            described, cited = describer_for(ctx.facts).describe(fact, _cell_noun(cell))
            if described:
                replacement = " ".join(described.replace("|", "/").replace("`", "").split())
                if (
                    replacement != cell
                    and len(cell) <= MAX_SPAN
                    and ctx.readme[offset : offset + len(cell)] == cell
                ):
                    edits.append(
                        Edit(
                            kind=FALSE_CLAIM_FIX,
                            detector=DETECTOR,
                            start=offset,
                            end=offset + len(cell),
                            original=cell,
                            replacement=replacement,
                            fact_ids=cited,
                            rationale=(
                                f"line {number}: the {shape.replace('_', ' ')} cell {cell!r} does "
                                f"not describe {name} and the source has no doc comment that does; "
                                "the verified facts' own kind, bases, members or values replace it"
                            ),
                        )
                    )
                    continue
        corrected = None if summary else true_count_cell(cell, fact)
        if (
            corrected is not None
            and len(cell) <= MAX_SPAN
            and ctx.readme[offset : offset + len(cell)] == cell
        ):
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector=DETECTOR,
                    start=offset,
                    end=offset + len(cell),
                    original=cell,
                    replacement=corrected,
                    fact_ids=(fact.id,),
                    rationale=(
                        f"line {number}: the count cell {cell!r} miscounts the own public members of "
                        f"{name} ({(fact.attributes or {}).get('member_counts')}); the true count replaces it"
                    ),
                )
            )
        if summary and not is_bookkeeping(summary):
            replacement = " ".join(summary.replace("|", "/").replace("`", "").split())
            if (
                replacement != cell
                and len(cell) <= MAX_SPAN
                and ctx.readme[offset : offset + len(cell)] == cell
            ):
                edits.append(
                    Edit(
                        kind=FALSE_CLAIM_FIX,
                        detector=DETECTOR,
                        start=offset,
                        end=offset + len(cell),
                        original=cell,
                        replacement=replacement,
                        fact_ids=(fact.id,),
                        rationale=(
                            f"line {number}: the {shape.replace('_', ' ')} cell {cell!r} does not "
                            f"describe {name}; its own doc comment does, and replaces it"
                        ),
                    )
                )
                continue
        findings.append(
            Finding(
                DETECTOR,
                number,
                cell,
                f"the {shape.replace('_', ' ')} cell does not describe {name}, and the source has "
                "no doc comment that does; only authored prose can (Lane R)",
                (fact.id,),
                report_only_reason="NO_DOC_COMMENT",
            )
        )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
