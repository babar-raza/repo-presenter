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

from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL
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
#: Markup lines the renderer (or a reader's Markdown) owns rather than an author: headings, tables,
#: HTML tags, badge and banner images, horizontal rules, "Not verified" notes.
_MARKUP_START = ("#", "|", "<", "[![", "![", "---", "***", "___", _NOT_VERIFIED)
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


def line_sections(readme: str, rendered: bool = True) -> list[str | None]:
    """For each line (0-based), the section whose author-written prose it is, or ``None`` when the
    line is not reviewable text.

    ``rendered`` says the candidate was printed by this project's renderer (Lane R), which owns the
    deterministic sections, the diagram, the member reference and the sentences ``shown_text``
    removes. A corrected live README (Lane L) was written by the maintainers: nothing in it is the
    renderer's, so with ``rendered=False`` only Markdown that is never prose (fences, tables,
    headings, HTML, images, horizontal rules) is withheld, and sections are still named."""
    rows = readme.splitlines()
    owners = section_lines(readme)
    first = _first_heading(rows)
    classified: list[str | None] = []
    inside = False
    for index, row in enumerate(rows):
        stripped = row.strip()
        if _FENCE.match(row):
            inside = not inside
            classified.append(None)
            continue
        if inside or not stripped or _is_markup(stripped):
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
