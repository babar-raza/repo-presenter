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

:func:`cell_shape` is the one classification of a description cell, shared with
``scripts/measure_type_descriptions.py`` (the portfolio Pareto measurement), so the measurement and
the correction cannot disagree about which cells are bad.
"""

from __future__ import annotations

import re

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


@detector(DETECTOR)
def type_description(ctx: Context) -> DetectorResult:
    types = type_facts_by_name(list(ctx.facts.facts))
    if not types:
        return DetectorResult()
    edits: list[Edit] = []
    findings: list[Finding] = []
    for number, offset, name, cell in description_rows(ctx):
        candidates = types.get(name) or types.get(name.rsplit(".", 1)[-1]) or []
        docs = {(fact.attributes or {}).get("docstring") or "" for fact in candidates}
        if len(docs) != 1:
            continue  # no such type, or two types of that name documented differently
        fact = candidates[0]
        docstring = docs.pop()
        shape = cell_shape(cell, docstring, fact.value)
        if shape not in NON_DESCRIPTIVE:
            continue
        summary = usable_doc(docstring, fact.value) if docstring else ""
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
