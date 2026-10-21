"""Text hygiene for authored units: a sentence cut off, or one that slipped into another script.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``components/readme/composition/text_hygiene.py`` per migration/reuse-manifest.yaml ("readme/
composition/" entry). Called from ``authoring.unit_checks`` as one more repairable error.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

from repo_presenter.core.facts import FactsDocument

MAX_UNIT_CHARS = 1500
_PHRASE_SLOT_PREFIXES = ("workflow:", "link:")
_TERMINAL = frozenset(
    ".!?:;)]}\"'`*"
    "…”’"
    "。！？：；）」』"
)
_FOREIGN_SCRIPTS = (
    "CJK",
    "HIRAGANA",
    "KATAKANA",
    "HANGUL",
    "CYRILLIC",
    "ARABIC",
    "HEBREW",
    "THAI",
    "DEVANAGARI",
)
_SHOWN_CHARACTERS = 4
_QUOTE_TAIL = 40


def foreign_script(character: str) -> str | None:
    """The script name when ``character`` is a letter of a script an English README never uses."""
    if character.isascii() or not character.isalpha():
        return None
    name = unicodedata.name(character, "")
    return next((script for script in _FOREIGN_SCRIPTS if name.startswith(script)), None)


def _source_text(facts: FactsDocument) -> tuple[str, bool]:
    """The text the unit may legitimately echo, and whether the upstream README is Latin-script."""
    verified = " ".join(fact.value for fact in facts.facts if fact.polarity == "SUPPORTED")
    inherited = " ".join(fact.value for fact in facts.by_kind("inherited_unit"))
    letters = [character for character in inherited if character.isalpha()]
    foreign = sum(foreign_script(character) is not None for character in letters)
    latin = not letters or foreign * 2 < len(letters)
    return f"{verified} {inherited}", latin


def hygiene_errors(units: Iterable[Mapping[str, Any]], facts: FactsDocument) -> list[str]:
    """One error per authored unit that was cut off, left the document's language, or is a pasted
    list."""
    errors: list[str] = []
    source, latin = _source_text(facts)
    for unit in units:
        slot = str(unit.get("slot", "?"))
        text = str(unit.get("text", "")).strip()
        if not text:
            continue
        if latin:
            strangers = sorted(
                {
                    character
                    for character in text
                    if foreign_script(character) is not None and character not in source
                }
            )
            if strangers:
                scripts = sorted({foreign_script(character) or "" for character in strangers})
                errors.append(
                    f"unit {slot}: contains {''.join(strangers[:_SHOWN_CHARACTERS])!r} "
                    f"({', '.join(scripts)} script) in an English README; write the whole "
                    "sentence in English"
                )
        if not slot.startswith(_PHRASE_SLOT_PREFIXES) and text[-1] not in _TERMINAL:
            errors.append(
                f"unit {slot}: ends without terminal punctuation "
                f"(...{text[-_QUOTE_TAIL:]!r}); it reads as cut off, so finish the sentence or "
                "end it where it is complete"
            )
        if len(text) > MAX_UNIT_CHARS:
            errors.append(
                f"unit {slot}: is {len(text)} characters, past the {MAX_UNIT_CHARS} a single unit "
                "may take; say each point once, in a sentence, and leave the rest to the section's "
                "other units"
            )
    return errors
