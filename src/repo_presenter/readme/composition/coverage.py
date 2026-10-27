"""How much of a kept unit its destination section already states: the whole-content test behind
the drop rule in ``placement.py``.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/coverage.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry).

A kept unit is dropped only when the destination, as it renders without the unit, STATES
everything the unit says; otherwise the unit is carried, or only the part the destination does
not state is (the unit's uncovered remainder). A fact id is a citation, not a statement: two
pieces of content resting on the same fact can say different things, so the rule asks the
question it means, from text alone.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence

from repo_presenter.readme.composition.list_coverage import (
    item_links,
    list_items,
    missing_items,
    stems,
)

COMMAND = re.compile(
    r"^\s*(?:[$>]\s*)?(?:pip3?|python3?(?:\s+-m)?|npm|npx|yarn|pnpm|dotnet|mvn|gradle|go|"
    r"cargo|cmake|make|git)\b(?!-)",
    re.IGNORECASE,
)
SENTENCE_SHARE = 0.7

_RELEASE = re.compile(
    r"(?<![\w.])v?\d+(?:\.\d+){2,}(?:[-+][0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?(?!\w)"
)
RELEASE_TOKEN = "<release>"

_SPAN = re.compile(r"`([^`]+)`")
_URL = re.compile(r"https?://[^\s<>)\]`]+")
_BULLET = re.compile(r"^(?:[-*+]|\d{1,3}[.)])\s+")
_PROTECTED = re.compile(r"`[^`\n]*`|\]\([^)\s]*\)|https?://[^\s<>)\]]+|<[^>\n]+>")
_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\[\"'(*_<])")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def unversioned(text: str) -> str:
    """``text`` with every release number of three or more components replaced by one token."""
    return _RELEASE.sub(RELEASE_TOKEN, text)


class _Indexed:
    """One destination's text, indexed once for the sentence test."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.squashed = _squash(unversioned(text))
        self.stems = stems(unversioned(text))

    def states(self, sentence: str, share: float) -> bool:
        squashed = _squash(unversioned(sentence))
        if squashed.strip() and squashed in self.squashed:
            return True
        subject = stems(_URL.sub(" ", unversioned(sentence)))
        if not subject:
            return False
        return len(subject & self.stems) >= math.ceil(len(subject) * share)


class Destinations:
    """The document as it renders with no kept unit placed, section by section."""

    def __init__(
        self, section_text: Callable[[str], str], section_ids: Sequence[str]
    ) -> None:
        self._section_text = section_text
        self._section_ids = tuple(section_ids)
        self._texts: dict[str, str] = {}
        self._indexed: dict[str, _Indexed] = {}
        self._document: str | None = None

    @classmethod
    def of(cls, sections: Mapping[str, str]) -> Destinations:
        return cls(lambda section_id: sections.get(section_id, ""), tuple(sections))

    @property
    def section_ids(self) -> tuple[str, ...]:
        return self._section_ids

    def text(self, section_id: str) -> str:
        if section_id not in self._texts:
            self._texts[section_id] = self._section_text(section_id)
        return self._texts[section_id]

    def index(self, section_id: str) -> _Indexed:
        if section_id not in self._indexed:
            self._indexed[section_id] = _Indexed(self.text(section_id))
        return self._indexed[section_id]

    def merged(self, section_id: str, also: Sequence[str]) -> _Indexed:
        """The index of ``section_id`` read together with the sections ``also``."""
        if not also:
            return self.index(section_id)
        key = "\x00".join((section_id, *also))
        if key not in self._indexed:
            texts = [self.text(section_id)]
            texts.extend(
                self.text(other) for other in also if other in self._section_ids
            )
            self._indexed[key] = _Indexed("\n\n".join(texts))
        return self._indexed[key]

    @property
    def document(self) -> str:
        if self._document is None:
            self._document = "\n\n".join(
                self.text(section_id) for section_id in self._section_ids
            )
        return self._document


def sentences(text: str) -> list[str]:
    """``text`` split into its sentences, each a substring of ``text``."""
    masked = _PROTECTED.sub(lambda match: "\x00" * len(match.group(0)), text)
    parts: list[str] = []
    start = 0
    for boundary in _BOUNDARY.finditer(masked):
        parts.append(text[start : boundary.start()])
        start = boundary.end()
    parts.append(text[start:])
    return [part for part in parts if part.strip()]


def list_blocks(text: str) -> list[str]:
    """The top-level items of a Markdown list, each as written."""
    blocks: list[list[str]] = []
    for line in text.splitlines():
        if _BULLET.match(line):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
    return ["\n".join(block).rstrip() for block in blocks]


def hard_tokens(text: str) -> list[str]:
    """The commands and links ``text`` carries."""
    found = [span.strip() for span in _SPAN.findall(text) if COMMAND.match(span)]
    found.extend(item_links(text))
    found.extend(url.rstrip(".,;:") for url in _URL.findall(text))
    return list(dict.fromkeys(token for token in found if token))


def _squash(text: str) -> str:
    return f" {_NON_WORD.sub(' ', text.lower()).strip()} "


def _carries_all(text: str, shown: Destinations) -> bool:
    """Whether the document holds every command and link ``text`` carries."""
    tokens = hard_tokens(text)
    return not tokens or all(token in shown.document for token in tokens)


def _uncovered_items(
    text: str,
    destination: _Indexed,
    shown: Destinations,
    by_link: bool,
    elsewhere: _Indexed | None = None,
) -> str | None:
    """The items of a kept list the destination does not state, or ``None`` for text that is not
    a list."""
    blocks = list_blocks(text)
    if not blocks:
        return None
    absent = set(
        missing_items(
            text,
            destination.text,
            by_link=by_link,
            document_text=shown.document if by_link else "",
        )
    )
    absent_elsewhere = (
        set(missing_items(text, elsewhere.text)) if elsewhere is not None else set()
    )

    def stated_elsewhere(item: str) -> bool:
        return (
            elsewhere is not None
            and item not in absent_elsewhere
            and elsewhere.states(item, SENTENCE_SHARE)
        )

    open_items = []
    for block in blocks:
        item = " ".join(list_items(block))
        first = next(iter(list_items(block)), "")
        if (first in absent and not stated_elsewhere(item)) or not _carries_all(
            block, shown
        ):
            open_items.append(block)
    return text if len(open_items) == len(blocks) else "\n".join(open_items)


def uncovered(
    unit_id: str,
    text: str,
    shown: Destinations,
    section_id: str,
    *,
    by_link: bool = False,
    lead_in: bool = False,
    also: Sequence[str] = (),
    only_also: bool = False,
) -> str:
    """The part of the kept unit ``text`` that section ``section_id`` of ``shown`` does not state,
    as written; empty when it states all of it."""
    destination = _Indexed("") if only_also else shown.index(section_id)
    elsewhere = shown.merged(also[0], also[1:]) if also else None
    if by_link and unit_id.rsplit(".", 1)[-1] != "list":
        links = item_links(text)
        if links and all(link in destination.text for link in links):
            return ""
    if unit_id.rsplit(".", 1)[-1] == "list":
        remainder = _uncovered_items(text, destination, shown, by_link, elsewhere)
        if remainder is not None:
            return remainder
    parts = sentences(text)
    if not parts:
        return ""
    open_parts = [
        part
        for part in parts
        if not _carries_all(part, shown)
        or not (
            lead_in
            or destination.states(part, SENTENCE_SHARE)
            or (elsewhere is not None and elsewhere.states(part, SENTENCE_SHARE))
        )
    ]
    return text if len(open_parts) == len(parts) else " ".join(open_parts)


def states_all(kept: str, text: str, share: float = SENTENCE_SHARE) -> bool:
    """Whether ``kept`` states every sentence of ``text``."""
    parts = sentences(text)
    indexed = _Indexed(kept)
    return bool(parts) and all(indexed.states(part, share) for part in parts)


def partly_printed(unit_text: str, readme_text: str) -> bool:
    """Whether at least one sentence (or, for a list, item) of ``unit_text`` is printed, word for
    word, somewhere in ``readme_text``. ``states_all`` alone only proves every part is restated in
    some form; a unit entirely reworded, with nothing of it surviving verbatim, is not a trimmed
    remainder (placement's own ``uncovered``/``uncovered_block`` always leaves the uncovered part
    exactly as written) -- it is a unit nothing of which actually renders, and must not be
    confused with one."""
    squeezed = _squash(readme_text)
    items = list_items(unit_text)
    parts = items if items else sentences(unit_text)
    return any(_squash(part).strip() and _squash(part) in squeezed for part in parts)


def _loose(line: str) -> str:
    return " ".join(unversioned(line).split()).lower()


def _block_body(text: str) -> list[str]:
    """The lines of a fenced code block that say something: fences, blank lines and comments
    dropped."""
    return [
        raw.strip()
        for raw in text.splitlines()
        if raw.strip() and not raw.strip().startswith(("```", "~~~", "#", "//"))
    ]


def uncovered_block(text: str, shown: Destinations, sections: Sequence[str]) -> str:
    """``text`` (a kept code block) when the ``sections`` lack a line of it, else the empty
    string."""
    lines = _block_body(text)
    if not lines:
        return text
    printed = [
        line
        for section in sections
        if section in shown.section_ids
        for line in _block_body(shown.text(section))
    ]
    exact = set(printed)
    loose = {_loose(line) for line in printed}
    covered = all(
        (line in exact) if COMMAND.match(line) else (_loose(line) in loose)
        for line in lines
    )
    return "" if covered else text
