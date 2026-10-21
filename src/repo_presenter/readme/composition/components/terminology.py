"""The governed technical-terminology registry and heading-case grammar: one owner.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/components/terminology.py`` per migration/reuse-manifest.yaml
("readme/composition/" entry). The renderer normalises prose to the forms returned by
``canonical_forms``, so this is the single place that vocabulary is data.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

UPPERCASE_TERMS: frozenset[str] = frozenset(
    {
        "PDF",
        "XLSX",
        "HTML",
        "PS",
        "EPS",
        "XPS",
        "API",
        "JSON",
        "XML",
        "CSV",
        "SVG",
        "URL",
        "HTTP",
        "SDK",
        "CLI",
    }
)
MIXED_CASE_TERMS: frozenset[str] = frozenset({"glTF", "npm"})
WORD_EXTENSIONS: frozenset[str] = frozenset(
    {"max", "ply", "dat", "raw", "bin", "log", "map", "mat", "tag", "ini", "one"}
)
ORDINARY_TWO_LETTER_WORDS: frozenset[str] = frozenset(
    {
        "am",
        "an",
        "as",
        "at",
        "be",
        "by",
        "do",
        "go",
        "he",
        "hi",
        "if",
        "in",
        "is",
        "it",
        "me",
        "my",
        "no",
        "of",
        "oh",
        "ok",
        "on",
        "or",
        "so",
        "to",
        "up",
        "us",
        "we",
    }
)
ORDINARY_WORDS: frozenset[str] = WORD_EXTENSIONS | ORDINARY_TWO_LETTER_WORDS
MIN_EXTENSION_LENGTH = 2

LOWER_WORD = re.compile(r"(?<![.\w:-])[a-z]{2,}(?![\w:-])")
ANY_CASE_WORD = re.compile(r"(?<![.\w:-])[A-Za-z]{2,}(?![\w:-])")
_CODE_SPAN = re.compile(r"`[^`]*`")


def canonical_forms(extensions: Iterable[str] = ()) -> dict[str, str]:
    """Lowercase spelling to canonical form for every term this document owns."""
    forms = {term.lower(): term for term in UPPERCASE_TERMS | MIXED_CASE_TERMS}
    for raw in extensions:
        extension = raw.lstrip(".").lower()
        if (
            len(extension) >= MIN_EXTENSION_LENGTH
            and extension.isalpha()
            and extension not in ORDINARY_WORDS
        ):
            forms.setdefault(extension, extension.upper())
    return forms


def noncanonical_terms(text: str, forms: dict[str, str]) -> list[tuple[str, str]]:
    """(found, canonical) for each standalone word in ``text`` spelled other than canonically."""
    found: list[tuple[str, str]] = []
    for match in ANY_CASE_WORD.finditer(_CODE_SPAN.sub(" ", text)):
        word = match.group(0)
        canonical = forms.get(word.lower())
        if canonical is not None and word != canonical and (word, canonical) not in found:
            found.append((word, canonical))
    return found


MINOR_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "but",
        "or",
        "nor",
        "for",
        "so",
        "yet",
        "as",
        "at",
        "by",
        "in",
        "of",
        "on",
        "to",
        "up",
        "via",
        "vs",
        "per",
        "from",
        "with",
        "into",
        "onto",
        "over",
    }
)
_EDGE_PUNCTUATION = ".,:;!?\"'()[]{}<>*"


def _identifier_like(word: str) -> bool:
    """A token whose spelling is its own: it carries a digit, a path or call separator, or a
    capital after its first letter."""
    return any(char.isdigit() or char in "._/\\()@#=+" for char in word) or any(
        char.isupper() for char in word[1:]
    )


def title_case_violations(text: str, forms: dict[str, str] | None = None) -> list[str]:
    """The words of a heading that title case forbids; empty when the heading is in title case."""
    forms = forms or {}
    words = []
    for raw in _CODE_SPAN.sub(" ", text).split():
        word = raw.strip(_EDGE_PUNCTUATION)
        if any(char.isalpha() for char in word):
            words.append(word)
    violations: list[str] = []
    for index, word in enumerate(words):
        if _identifier_like(word) or forms.get(word.lower()) == word:
            continue
        edge = index in (0, len(words) - 1)
        if word[:1].isupper() or (not edge and word.lower() in MINOR_WORDS):
            continue
        violations.append(word)
    return violations


def _capitalised(word: str) -> str:
    """``word`` with the first letter of each hyphen-joined segment raised."""
    return "-".join(part[:1].upper() + part[1:] for part in word.split("-"))


def to_title_case(text: str, forms: dict[str, str] | None = None) -> str:
    """``text`` in title case: the deterministic repair of what :func:`title_case_violations`
    finds."""
    forms = forms or {}
    pieces = re.split(r"(`[^`]*`|\s+)", text)
    word_pieces = [
        index
        for index, piece in enumerate(pieces)
        if piece
        and not piece.isspace()
        and not piece.startswith("`")
        and any(char.isalpha() for char in piece.strip(_EDGE_PUNCTUATION))
    ]
    for position, index in enumerate(word_pieces):
        piece = pieces[index]
        core = piece.strip(_EDGE_PUNCTUATION)
        if _identifier_like(core) or forms.get(core.lower()) == core:
            continue
        edge = position in (0, len(word_pieces) - 1)
        if core[:1].isupper() or (not edge and core.lower() in MINOR_WORDS):
            continue
        start = piece.index(core)
        pieces[index] = piece[:start] + _capitalised(core) + piece[start + len(core) :]
    return "".join(pieces)
