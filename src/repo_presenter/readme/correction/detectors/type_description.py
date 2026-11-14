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

Version 3 (BL-094, M9 round 43559491132, Words Python Lane L control ab8a03 line 402): a count cell
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
