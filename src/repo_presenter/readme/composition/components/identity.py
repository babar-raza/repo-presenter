"""The identity component: the complete canonical product name the H1 and the prose use.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/components/identity.py`` per migration/reuse-manifest.yaml
("readme/composition/" entry).

Derived deterministically from the governed repository name (``Aspose.3D-FOSS-for-Python`` becomes
``Aspose.3D FOSS for Python``): hyphens separate words, dots stay inside the family name, and
nothing is abbreviated.
"""

from __future__ import annotations

import re

from repo_presenter.core.registry.models import RegistryEntry


def product_name(entry: RegistryEntry) -> str:
    """``Aspose.3D-FOSS-for-Python`` -> ``Aspose.3D FOSS for Python``."""
    parts = [part for part in entry.name.split("-") if part]
    if len(parts) > 2 and parts[0] == "Aspose" and parts[2].upper() == "FOSS":
        parts[:2] = [f"{parts[0]}.{parts[1]}"]
    return " ".join(parts)


def product_name_tokens(name: str) -> frozenset[str]:
    """The name's space-separated tokens, each an identifier the prose may spell as written."""
    return frozenset(token for token in name.split(" ") if token)


_NAME_SEPARATOR = r"[\s._-]*"


def _noncanonical_name_pattern(canonical: str) -> re.Pattern[str]:
    segments = [part for part in re.split(r"[\s._-]+", canonical) if part]
    foss = next((i for i, part in enumerate(segments) if part.lower() == "foss"), None)
    head, tail = (segments, []) if foss is None else (segments[: foss + 1], segments[foss + 1 :])
    pattern = _NAME_SEPARATOR.join(re.escape(part) for part in head)
    if tail:
        rest = _NAME_SEPARATOR.join(re.escape(part) for part in tail)
        pattern += f"(?:{_NAME_SEPARATOR}{rest})?"
    return re.compile(r"(?<![A-Za-z0-9])" + pattern + r"(?![A-Za-z0-9])", re.IGNORECASE)


_IDENTIFIER_CUE_BEFORE = re.compile(
    r"(?i)\b(?:package|namespace|assembly|module|crate|named|called)\s+(?:`)?$"
)
_IDENTIFIER_CUE_AFTER = re.compile(
    r"(?i)^(?:`)?\s+(?:version|package|namespace|assembly|module|crate)\b"
)


def _is_technical_identifier(found: str, before: str, after: str) -> bool:
    if any(character.isspace() for character in found):
        return False
    if "-" in found or "_" in found:
        return True
    return bool(_IDENTIFIER_CUE_BEFORE.search(before) or _IDENTIFIER_CUE_AFTER.match(after))


_ELISION_MARK = "…"


def elide_noncanonical(text: str, canonical: str) -> tuple[str, tuple[str, ...]]:
    """``text`` with every forbidden non-canonical variant of ``canonical`` replaced by an
    ellipsis, plus the variants removed, in the order found."""
    pattern = _noncanonical_name_pattern(canonical)
    removed: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        found = match.group(0)
        if found == canonical:
            return found
        before = text[max(0, match.start() - 24) : match.start()]
        after = text[match.end() : match.end() + 24]
        if _is_technical_identifier(found, before, after):
            return found
        removed.append(found)
        return _ELISION_MARK

    elided = pattern.sub(_replace, text)
    return elided, tuple(removed)


_IDENTIFIER_CONTINUES = re.compile(r"^(?:\.[A-Za-z0-9_]|[/\\_]|::)")
_IDENTIFIER_CONTINUED = re.compile(r"(?:[A-Za-z0-9_]\.|[/\\_]|::)$")
_ANOTHER_TAIL = re.compile(r"^\s+for\b", re.IGNORECASE)
_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)


def _is_spelling_of_the_name(found: str, canonical: str, before: str, after: str) -> bool:
    """Whether ``found`` stands for the product name in running prose, as opposed to the
    canonical name itself, a technical identifier or part of a longer one."""
    if found == canonical or _is_technical_identifier(found, before, after):
        return False
    if _IDENTIFIER_CONTINUES.match(after) or _IDENTIFIER_CONTINUED.search(before[-2:]):
        return False
    return _ANOTHER_TAIL.match(after) is None


def canonicalise_name_variants(text: str, canonical: str) -> str:
    """``text`` with every separator, case or suffix variant of ``canonical`` that stands for the
    product name in running prose rewritten to ``canonical``."""
    pattern = _noncanonical_name_pattern(canonical)

    def _rewrite(segment: str, base: int) -> str:
        def _replace(match: re.Match[str]) -> str:
            start, end = base + match.start(), base + match.end()
            before, after = text[max(0, start - 24) : start], text[end : end + 24]
            if _is_spelling_of_the_name(match.group(0), canonical, before, after):
                return canonical
            return match.group(0)

        return pattern.sub(_replace, segment)

    out: list[str] = []
    cursor = 0
    for code in _CODE.finditer(text):
        out.append(_rewrite(text[cursor : code.start()], cursor))
        out.append(code.group(0))
        cursor = code.end()
    out.append(_rewrite(text[cursor:], cursor))
    return "".join(out)


def spells_the_product(token: str, canonical: str) -> bool:
    """Whether the whole ``token`` is a separator, case or suffix variant of ``canonical``."""
    return _noncanonical_name_pattern(canonical).fullmatch(token) is not None
