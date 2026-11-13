"""What a review unit may show the model: only the text an author wrote (reviewer logic 6).

The renderer prints the identity, badges, banner, navigation, At a Glance diagram, installation,
dependencies, third-party notices and license from facts. In the mixed sections it prints the
headings, tables, fenced examples, ``<details>`` wrappers, "Not verified" notes and the member
reference bullets. None of that is a claim an author made, and iteration 2 of the calibration found
130 of 159 unsupported-claim findings aimed at exactly such text. So it is never sent: a line the
reviewer is not shown cannot be cited (``reply.validate_review_reply`` rejects a citation of a line
outside the unit), which excludes renderer-owned text from every claim kind by construction.

``reviewable_lines`` is structural, not lexical: it reads the shell section a line is under and the
Markdown shape of the line, and it never looks at what the line says. A line is reviewable when it
is prose, under a section the renderer does not own wholesale, outside every fence.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from typing import Any

from repo_presenter.core.facts import Fact, FactsDocument
from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL
from repo_presenter.readme.composition.placement import ATTRIBUTED, ATTRIBUTION_LINE
from repo_presenter.readme.review.matching import present
from repo_presenter.readme.validation.text import section_lines

#: Sections the renderer prints wholesale from facts (owner ``D``) and the diagram.
RENDERER_SECTIONS: frozenset[str] = frozenset(
    {section.id for section in SEMANTIC_SHELL if section.owner == "D"} | {"at_a_glance"}
)
OPENING = "opening"
STRUCTURE = "structure"
_FENCE = re.compile(r"^\s*(```|~~~)")
_NOT_VERIFIED = "> **Not verified:**"
_SURFACE_SUMMARY = re.compile(r"^The verified public surface has \d+ types?\.\s*$")
_TABLE_DELIMITER = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")
#: A Core API table row as the renderer prints it: ``| `Name` | description |``.
_TYPE_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|(.*)\|$")
#: Markup lines the renderer (or a reader's Markdown) owns rather than an author: headings, tables,
#: HTML tags, badge and banner images, horizontal rules, "Not verified" notes, and the attribution
#: line the renderer prints before maintainer content kept as PRESERVE_ATTRIBUTED (a label, not a
#: claim; the maintainer content under it stays shown).
_MARKUP_START = (
    "#", "|", "<", "[![", "![", "---", "***", "___", _NOT_VERIFIED, ATTRIBUTION_LINE
)
#: Sentences the renderer writes into a section an author otherwise owns (``composition.renderer``:
#: ``_development_sentences``, the resources and API summaries, the Enterprise lead, the issues
#: bullet). They are facts the renderer computed, not claims an author made, so they are removed from
#: what a unit shows; ``tests/readme/review/test_scope.py`` renders the fixture's
#: ``renderer_sentences`` and asserts every one is covered here.
_RENDERER_SENTENCES = tuple(
    re.compile(pattern)
    for pattern in (
        r"The suite covers \d+ test files under `[^`]*`\.",
        r"The \[[^\]]*\]\([^)]*\) runs .*?\.(?=\s|$)",
        r"Releases run through the \[[^\]]*\]\([^)]*\)\.",
        r"The verified public surface has \d+ types?\.",
        (
            r"It covers all \d+ verified public types; the \[API Reference\]\(#api-reference\) "
            r"section above covers the essentials\."
        ),
        r"These limitations don't apply to \[[^\]]*\]\([^)]*\)\.",
        r"(?:- )?Found a bug or have a feature request\? \[Open an issue\]\([^)]*\)\.",
    )
)


def shown_text(row: str) -> str:
    """``row`` without the sentences the renderer appended to it; blank when nothing else is left."""
    text = row
    for pattern in _RENDERER_SENTENCES:
        text = pattern.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip() if text != row else row


def _first_heading(rows: list[str]) -> int | None:
    inside = False
    for index, row in enumerate(rows):
        if _FENCE.match(row):
            inside = not inside
        elif not inside and row.startswith("## "):
            return index
    return None


def _is_markup(stripped: str) -> bool:
    return stripped.startswith(_MARKUP_START)


def _member_bullet(stripped: str, section: str) -> bool:
    """The API reference's member reference is printed from the symbol facts."""
    return section == "api_reference" and (
        stripped.startswith("- `") or _SURFACE_SUMMARY.match(stripped) is not None
    )


def _table_delimiter(row: str) -> bool:
    return _TABLE_DELIMITER.match(row.strip()) is not None


def _table_data_row(rows: list[str], index: int) -> bool:
    """``rows[index]`` is a body row of a Markdown table: a ``|`` row that is neither the delimiter
    row (``| --- | --- |``) nor the header row right above one. A header row holds column labels; a
    body row holds whatever its author wrote in the cells, prose included."""
    row = rows[index].strip()
    if not row.startswith("|") or _table_delimiter(row):
        return False
    following = rows[index + 1] if index + 1 < len(rows) else ""
    return not _table_delimiter(following)


def authored_table_lines(readme: str, facts: FactsDocument) -> frozenset[int]:
    """The 1-based numbers of the API reference table rows whose description an author wrote.

    The renderer prints the Core API table from facts, but a type with no docstring and no
    signature gets the sentence authored for it in a bounded batch (``renderer._symbol_description``:
    the ``type:<fact id>`` unit). That sentence is an author's claim like any other, and iteration 4
    of the calibration found real unsupported claims in exactly such cells (own Cells C++, own HTML
    Python), which the reviewer was never shown. Structural, like ``reviewable_lines``: a row is
    authored when its type is a SUPPORTED class or enum with neither a docstring nor a signature and
    its description is not the renderer's ``Public <kind>.`` fallback."""
    return frozenset(authored_type_rows(readme, facts))


def authored_type_rows(readme: str, facts: FactsDocument) -> dict[int, Fact]:
    """``authored_table_lines`` with the type fact each row describes: the fact whose
    ``type:<fact id>`` unit the row's description is (``renderer._symbol_description``)."""
    from repo_presenter.readme.composition.renderer import api_reference_names

    names = api_reference_names(facts)
    authored_types: dict[str, Fact] = {}
    fallbacks: dict[str, str] = {}
    for fact in facts.by_kind("public_symbol"):
        attributes = fact.attributes or {}
        kind = attributes.get("symbol_kind")
        if fact.polarity != "SUPPORTED" or kind not in {"class", "enum"}:
            continue
        if attributes.get("docstring") or attributes.get("signature"):
            continue
        name = names.get(fact.value, fact.value.rsplit(".", 1)[-1])
        authored_types.setdefault(name, fact)
        fallbacks[name] = f"Public {kind}."
    if not authored_types:
        return {}
    owners = section_lines(readme)
    found: dict[int, Fact] = {}
    for number, row in enumerate(readme.splitlines(), 1):
        if owners[number - 1] != "api_reference":
            continue
        match = _TYPE_ROW.match(row.strip())
        if match is None or match.group(1) not in authored_types:
            continue
        description = match.group(2).strip()
        if description and description != fallbacks[match.group(1)]:
            found[number] = authored_types[match.group(1)]
    return found


def line_sections(
    readme: str, rendered: bool = True, authored: Collection[int] = (), *, headings: bool = False
) -> list[str | None]:
    """For each line (0-based), the section whose author-written prose it is, or ``None`` when the
    line is not reviewable text.

    ``rendered`` says the candidate was printed by this project's renderer (Lane R), which owns the
    deterministic sections, the diagram, the member reference and the sentences ``shown_text``
    removes. A corrected live README (Lane L) was written by the maintainers: nothing in it is the
    renderer's, so with ``rendered=False`` only Markdown that is never prose (fences, headings, HTML,
    images, horizontal rules, a table's header and delimiter rows) is withheld; a table's body rows
    are the maintainers' text and are shown, and sections are still named.

    ``authored`` (1-based, ``authored_table_lines``) are rows of a renderer-printed table whose cell
    an author wrote; they are reviewable in a rendered candidate too.

    ``headings`` (the M9 blind auditor only, ``scripts/run_m9_auditor.py``) makes a heading line
    reviewable too. The auditor's question is whether a defect sits anywhere in the document, and a
    sentence written onto the title line is prose the reader sees: the 2026-11-13 hosted round
    43445578226 missed all 11 of its D/D14 seeds because the seed operators append to the first
    paragraph, which is the ``# Title`` line, and a heading was never shown. Every other caller keeps
    the default, so its units and request hashes are unchanged byte for byte."""
    rows = readme.splitlines()
    owners = section_lines(readme)
    first = _first_heading(rows)
    classified: list[str | None] = []
    inside = False
    extra = set(authored)
    for index, row in enumerate(rows):
        stripped = row.strip()
        if _FENCE.match(row):
            inside = not inside
            classified.append(None)
            continue
        if inside or not stripped:
            classified.append(None)
            continue
        if rendered and index + 1 in extra:
            classified.append(owners[index] or STRUCTURE)
            continue
        heading = headings and stripped.startswith("#")
        if heading and not rendered:
            classified.append(OPENING if first is None or index < first else owners[index] or STRUCTURE)
            continue
        if _is_markup(stripped) and not heading and (rendered or not _table_data_row(rows, index)):
            classified.append(None)
            continue
        if rendered and not shown_text(stripped):
            classified.append(None)
            continue
        if first is None or index < first:
            section: str | None = OPENING
        else:
            section = owners[index] or STRUCTURE
        if rendered and (
            section in RENDERER_SECTIONS or _member_bullet(stripped, section)
        ):
            classified.append(None)
        else:
            classified.append(section)
    return classified


def reviewable_lines(readme: str, rendered: bool = True) -> tuple[int, ...]:
    """The 1-based numbers of the lines a reviewer may be shown and may cite, ascending."""
    return tuple(
        number
        for number, section in enumerate(line_sections(readme, rendered), 1)
        if section is not None
    )


def section_of_line(readme: str, number: int, rendered: bool = True) -> str | None:
    """The section a reviewable line belongs to, or ``None`` for a line that is not reviewable."""
    classified = line_sections(readme, rendered)
    return classified[number - 1] if 1 <= number <= len(classified) else None


def maintainer_lines(
    readme: str, facts: FactsDocument, dispositions: Mapping[str, Any]
) -> frozenset[int]:
    """The 1-based numbers of the candidate lines that are attributed maintainer text: a line whose
    stripped text is a stripped line of an inherited unit reconciliation kept as
    ``PRESERVE_ATTRIBUTED`` (docs/MAINTAINER_CONTENT_PRESERVATION.md). Like ``reviewable_lines`` it
    reads only structure, never meaning: it matches the unit's own lines, so a kept line the
    renderer changed (an anchor it resolved) is not marked and stays judged like authored text.

    The exemption holds only while no fact contradicts the text (DECISION_LOG 2026-11-06, "reviewer
    rule for inherited text"; reviewer logic 10): a unit whose own fact is CONTRADICTED, or whose
    disposition cites a CONTRADICTED fact, marks no line, and a line holding the value of a
    CONTRADICTED product fact is not marked. Such text is judged like generated text, so a finding
    on it stands. Inherited text kept verbatim without the attribution (``VERIFIED_PRESERVE``,
    ``VERIFIED_MOVE``) is never marked either.

    A corrected live README (Lane L, ``rendered=False``) is reviewed without S4 dispositions, so it
    has no ``PRESERVE_ATTRIBUTED`` unit and this set is empty there: nothing changes for Lane L."""
    contradicted = {fact.id: fact for fact in facts.facts if fact.polarity == "CONTRADICTED"}
    kept = {
        str(row.get("unit_id", ""))
        for row in dispositions.get("dispositions", [])
        if isinstance(row, Mapping)
        and row.get("disposition") == ATTRIBUTED
        and not any(str(fact_id) in contradicted for fact_id in row.get("fact_ids") or ())
    }
    if not kept:
        return frozenset()
    texts = {
        line.strip()
        for fact in facts.by_kind("inherited_unit")
        if fact.id in kept and fact.polarity != "CONTRADICTED"
        for line in fact.value.splitlines()
        if line.strip()
    }
    refuted = [fact.value for fact in contradicted.values() if fact.kind != "inherited_unit"]
    return frozenset(
        number
        for number, row in enumerate(readme.splitlines(), 1)
        if row.strip()
        and row.strip() in texts
        and not any(present(value, row) for value in refuted)
    )
