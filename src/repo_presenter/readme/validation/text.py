"""Pure Markdown text readers the blocking checks share: fences, prose, sections, URLs.

Ported (ADAPT, import paths and public names only) from the old repository-presenter project's
``components/readme/validation/registry.py`` helper block. Nothing here reads a file, the network
or a clock; every function takes the README text (or its lines) and returns what it finds.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from typing import Any

from markdown_it import MarkdownIt

from repo_presenter.readme.composition.components.shell import SEMANTIC_SHELL

SPAN = re.compile(r"`([^`]+)`")
LINK_DESTINATION = re.compile(r"\]\([^)]*\)")
URL = re.compile(r"https?://\S+")
# A command a README prints at the start of a line: a package tool or build tool, optionally
# prefixed with a shell prompt. A word continued by a hyphen (``python-pptx``) is a package name.
COMMAND = re.compile(
    r"^\s*(?:[$>]\s*)?(?:pip3?|python3?(?:\s+-m)?|npm|npx|yarn|pnpm|dotnet|mvn|gradle|go|"
    r"cargo|cmake|make|git)\b(?!-)",
    re.IGNORECASE,
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    """The digest of a JSON-serialisable value, keys sorted, so equal content hashes equal."""
    return sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8"))


def normalized(text: str) -> str:
    return "\n".join(
        line.rstrip() for line in text.replace("\r\n", "\n").splitlines()
    ).strip()


def fences(readme: str) -> list[tuple[str, str]]:
    """(language, body) of every fenced block, in document order, read through CommonMark.

    The info string's first word is the language; the rest is free text CommonMark does not
    constrain. A tilde fence and a multi-word info string parse the same way a reader's does.
    """
    found: list[tuple[str, str]] = []
    for token in MarkdownIt("commonmark").parse(readme):
        if token.type != "fence":
            continue
        info = token.info.strip()
        language = info.split()[0] if info else ""
        found.append((language, token.content))
    return found


def outside_fences(readme: str) -> list[str]:
    lines: list[str] = []
    inside = False
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") and not inside:
            inside = True
        elif stripped == "```" and inside:
            inside = False
        elif not inside:
            lines.append(line)
    return lines


def outside_lines(readme: str) -> list[tuple[str, str | None]]:
    """(line, shell section id) for every line outside a fenced block, in document order."""
    found: list[tuple[str, str | None]] = []
    inside = False
    for line, section in zip(readme.splitlines(), section_lines(readme), strict=True):
        stripped = line.strip()
        if stripped.startswith("```") and not inside:
            inside = True
        elif stripped == "```" and inside:
            inside = False
        elif not inside:
            found.append((line, section))
    return found


def prose(lines: Sequence[str]) -> str:
    """Prose outside code spans, link destinations, URLs, and headings."""
    kept = [line for line in lines if not line.startswith("#")]
    text = "\n".join(kept)
    text = SPAN.sub(" ", text)
    text = LINK_DESTINATION.sub("]", text)
    return URL.sub(" ", text)


def section_lines(readme: str) -> list[str | None]:
    """The headed shell section each line falls under, by line index: None for a line before
    the first shell heading, under a heading the shell does not name, or the ``## `` heading
    line itself; a fence's lines stay with their section."""
    by_heading = {
        section.heading: section.id for section in SEMANTIC_SHELL if section.heading
    }
    sections: list[str | None] = []
    current: str | None = None
    inside = False
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") and not inside:
            inside = True
        elif stripped == "```" and inside:
            inside = False
        if not inside and line.startswith("## "):
            current = by_heading.get(line[3:].strip())
            sections.append(None)
            continue
        sections.append(current)
    return sections


def section_texts(readme: str) -> dict[str, str]:
    """The text under each headed shell section, keyed by section id."""
    texts: dict[str, list[str]] = {}
    for line, section in zip(readme.splitlines(), section_lines(readme), strict=True):
        if section is not None:
            texts.setdefault(section, []).append(line)
    return {section: "\n".join(lines) for section, lines in texts.items()}


def visible_prose(readme: str) -> str:
    """The README text a visitor reads as prose, line for line: fenced blocks, code spans, link
    destinations and bare URLs are blanked to spaces (newlines kept), so a match's line number is
    its line number in the README. Headings stay: a name or edition in a heading is visible."""
    kept: list[str] = []
    inside = False
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") and not inside:
            inside = True
            kept.append("")
        elif stripped == "```" and inside:
            inside = False
            kept.append("")
        else:
            kept.append("" if inside else line)
    text = "\n".join(kept)
    for pattern in (SPAN, LINK_DESTINATION, URL):
        text = pattern.sub(lambda match: re.sub(r"[^\n]", " ", match.group(0)), text)
    return text


def located(readme: str, text: str, offset: int) -> str | None:
    """The shell section the line holding ``text[offset]`` renders in, None when it has none."""
    sections = section_lines(readme)
    line = text.count("\n", 0, offset)
    return sections[line] if line < len(sections) else None


def fence_body(value: str) -> tuple[str, str]:
    """(language, body) of an inherited code block's source text."""
    lines = value.splitlines()
    if lines and lines[0].strip().startswith("```"):
        language = lines[0].strip()[3:].strip()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return language, "\n".join(lines)
    return "", value


def unit_type(unit_id: str) -> str:
    return unit_id.rsplit(".", 1)[-1]
