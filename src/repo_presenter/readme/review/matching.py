"""Text matching the LLM-review contract checks and the clearances share.

Two directions, deliberately asymmetric. Whatever lets a finding be CLEARED (a string is "present",
a name "equals" a fact) uses the strict readers here, so uncertainty leaves the finding BLOCKING.
Whatever asks "is this text anywhere in the evidence?" (the ``absence_unsourced`` clearance, the
reviewer's quote check) uses the lenient reader, so uncertainty also leaves the finding standing.
The leniency exists only to make clearing harder or to tolerate Markdown syntax a reader does not
see; it is never a way to accept a reviewer's claim.

Ported (ADAPT) from the old repository's ``review/independent/review.py``: ``_normalized`` and its
three measured Markdown asymmetries (fence lines, Mermaid node quotes, link targets),
``_section_slice``'s lesson that text present elsewhere in a README does not disprove a gap in the
section a finding names, and the ellipsis rule for quotes. NOT ported: the 80-character quote
anchor and ``absence_restated``'s word-overlap similarity -- both let an approximate match stand in
for a located one.
"""

from __future__ import annotations

import re

from repo_presenter.readme.validation.text import section_texts

#: Strings shorter than this are not decidable: they sit inside unrelated text by coincidence.
MIN_CLAIM_CHARS = 3
#: Sections that have no ``## `` heading of their own: they live before the first heading.
PREAMBLE_SECTIONS = frozenset({"identity", "badges", "banner", "opening"})
#: Whole-document concerns, not one section.
DOCUMENT_SECTIONS = frozenset({"structure", "document"})

_TYPOGRAPHY = str.maketrans(
    {
        "—": "-",
        "–": "-",
        "‒": "-",
        "‑": "-",
        " ": " ",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
    }
)
_WHITESPACE = re.compile(r"\s+")
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…)\s*")
_MARKUP = (
    re.compile(r"(?m)^\s*```[^\n]*$"),
    re.compile(r"```[A-Za-z0-9_+-]*"),
    re.compile(r"<[^>\n]+>"),
    re.compile(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+"),
    re.compile(r"(?m)^\s*#{1,6}\s+"),
    re.compile(r"\*\*|__|(?<!\w)[*_](?=\S)|(?<=\S)[*_](?!\w)"),
    re.compile(r'(?<=\[)"|"(?=\])'),
)
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_WORD = re.compile(r"[A-Za-z0-9_]")


def spaced(text: str) -> str:
    """Typography folded and whitespace runs collapsed; nothing else."""
    return _WHITESPACE.sub(" ", text.translate(_TYPOGRAPHY)).strip()


def plain(text: str) -> str:
    """Text as a reader sees it: no code spans, links read as their label, no Markdown syntax.
    Case is kept, so this is never looser than a case-sensitive comparison."""
    reduced = _LINK.sub(r"\1", text.translate(_TYPOGRAPHY))
    for pattern in _MARKUP:
        reduced = pattern.sub("", reduced)
    return _WHITESPACE.sub(" ", reduced.replace("`", "")).strip()


def present(needle: str, haystack: str) -> bool:
    """Whether ``needle`` occurs in ``haystack`` exactly (typography and whitespace aside), as a
    whole token at each end that is a word character. Too-short needles are never present."""
    wanted = spaced(needle)
    if len(wanted) < MIN_CLAIM_CHARS:
        return False
    lead = r"(?<![A-Za-z0-9_])" if _WORD.fullmatch(wanted[0]) else ""
    tail = r"(?![A-Za-z0-9_])" if _WORD.fullmatch(wanted[-1]) else ""
    return re.search(lead + re.escape(wanted) + tail, spaced(haystack)) is not None


def loosely_in(needle: str, haystack: str) -> bool:
    """Whether ``needle`` might occur in ``haystack``: Markdown syntax ignored, case ignored,
    any substring. Used only where a ``True`` keeps a finding standing."""
    wanted = plain(needle).casefold()
    if not wanted:
        return True
    return wanted in plain(haystack).casefold()


def quote_located(quote: str, candidate: str) -> bool:
    """A reviewer's quote is the candidate's own text: an exact run (typography and whitespace
    aside) or the same run once Markdown syntax the reader does not see is dropped. An ellipsis
    abbreviates between exact fragments, every one of which must be located. A paraphrase, a
    change of case, or a quote of the original README is not located."""
    fragments = [part for part in _ELLIPSIS.split(quote.strip()) if part.strip()]
    if not fragments or any(len(spaced(part)) < MIN_CLAIM_CHARS for part in fragments):
        return False
    flat, reduced = spaced(candidate), plain(candidate)
    return all(spaced(part) in flat or plain(part) in reduced for part in fragments)


def section_scope(section_id: str, candidate: str) -> str | None:
    """The candidate's own text for the section a finding names, or ``None`` when that section
    cannot be located (a missing section is not a reason to search everywhere)."""
    if section_id in DOCUMENT_SECTIONS:
        return candidate
    if section_id in PREAMBLE_SECTIONS:
        first = re.search(r"(?m)^## ", candidate)
        return candidate[: first.start()] if first else candidate
    return section_texts(candidate).get(section_id)
