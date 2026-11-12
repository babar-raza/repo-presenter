"""Independent export-surface probe for Java: a new, independent reader built from source text.

The vendored engine's own ``lang/java.py``'s ``export_surface`` returns ``(None, None)``
unconditionally -- "No reachability signal implemented for Java yet." This module never reads
the main engine's symbol table: it is a new, independent syntactic reader. Public top-level and
nested types/members are declarations carrying the ``public`` keyword, and for a nested member,
its enclosing type must also be ``public`` -- read directly from the source text by a simple
brace-matching scan, never from the main engine's own parse.

Three-valued contract (see the package docstring): ``None`` means no ``.java`` source at all is
found under ``repo_root`` -- the probe cannot tell because there is nothing here that looks like
a Java package to read.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

_TYPE_OPEN = re.compile(
    r"(?P<mods>(?:@\w+(?:\([^)]*\))?\s*|public\s+|private\s+|protected\s+|static\s+|final\s+"
    r"|abstract\s+)*)"
    r"(?P<keyword>class|interface|enum|record)\s+(?P<name>[A-Za-z_]\w*)\b[^{;]*\{"
)
_MEMBER_ANY = re.compile(
    r"(?P<mods>(?:public\s+|private\s+|protected\s+|static\s+|final\s+|abstract\s+"
    r"|synchronized\s+|native\s+)*)"
    r"[\w\[\]<>,.?]+\s+(?P<name>[A-Za-z_]\w*)\s*"
    r"(?:\([^;{}]*\)\s*(?:throws\s+[\w.,\s]+)?\s*[{;]|=[^;{}]*;|;)"
)


class _TypeInfo(TypedDict):
    name: str
    kind: str
    public: bool
    members: dict[str, bool]


def _brace_match(text: str, open_index: int) -> int:
    """The index just past the ``{`` at ``open_index``'s matching ``}``, or ``len(text)``."""
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    return len(text)


def _scan_members(body: str) -> list[tuple[str, str]]:
    """Every (mods, name) member declared directly in ``body``, skipping each method's own body.

    A method's body is skipped by brace matching rather than left for the regex to re-enter, so a
    local variable declared inside it (``int count = 0;``) is never mistaken for a field or
    method of the enclosing type.
    """
    found: list[tuple[str, str]] = []
    pos = 0
    while True:
        match = _MEMBER_ANY.search(body, pos)
        if match is None:
            break
        found.append((match.group("mods"), match.group("name")))
        pos = _brace_match(body, match.end() - 1) if body[match.end() - 1] == "{" else match.end()
    return found


def _parse_file(text: str) -> list[_TypeInfo]:
    spans = []
    for match in _TYPE_OPEN.finditer(text):
        spans.append(
            {
                "start": match.start(),
                "body_start": match.end(),
                "end": _brace_match(text, match.end() - 1),
                "mods": match.group("mods"),
                "keyword": match.group("keyword"),
                "name": match.group("name"),
            }
        )
    for span in spans:
        parent_index = None
        parent_size = None
        for other_index, other in enumerate(spans):
            if other is span:
                continue
            if other["start"] <= span["start"] and span["end"] <= other["end"]:
                size = other["end"] - other["start"]
                if parent_size is None or size < parent_size:
                    parent_size, parent_index = size, other_index
        span["parent"] = parent_index

    types: list[_TypeInfo] = []
    for index, span in enumerate(spans):
        body = list(text[span["body_start"] : span["end"]])
        for child_index, child in enumerate(spans):
            if child["parent"] != index:
                continue
            start = child["start"] - span["body_start"]
            end = child["end"] - span["body_start"]
            for k in range(max(start, 0), min(end, len(body))):
                body[k] = " "
        own_body = "".join(body)
        members = {name: "public" in mods.split() for mods, name in _scan_members(own_body)}
        types.append(
            {
                "name": span["name"],
                "kind": "enum" if span["keyword"] == "enum" else "class",
                "public": "public" in span["mods"].split(),
                "members": members,
            }
        )
    return types


def _collect_types(repo_root: Path) -> dict[str, list[_TypeInfo]]:
    found: dict[str, list[_TypeInfo]] = {}
    if not repo_root.is_dir():
        return found
    for path in sorted(repo_root.rglob("*.java")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for type_info in _parse_file(text):
            found.setdefault(type_info["name"], []).append(type_info)
    return found


def count(repo_root: Path, kind: str) -> int | None:
    """How many public types of ``kind`` ("class" covers class/interface/record; "enum" too).

    ``None`` when no ``.java`` source exists under ``repo_root`` at all, or when ``kind`` is not
    ``"class"`` or ``"enum"``.
    """
    if kind not in ("class", "enum"):
        return None
    types = _collect_types(repo_root)
    if not types:
        return None
    return sum(
        1
        for occurrences in types.values()
        if any(o["kind"] == kind and o["public"] for o in occurrences)
    )


def exists(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` (a type, or ``Type.member``) is declared anywhere at all.

    Public or private both count as "exists". ``None`` when no ``.java`` source exists under
    ``repo_root`` at all.
    """
    types = _collect_types(repo_root)
    if not types:
        return None
    parts = qualified_name.split(".")
    if len(parts) == 1:
        return parts[0] in types
    owner, member = parts[-2], parts[-1]
    occurrences = types.get(owner)
    if not occurrences:
        return False
    return any(member in o["members"] for o in occurrences)


def exported(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` carries the ``public`` keyword (and, for a member, so does its
    enclosing type).

    ``True``/``False`` when the probe can tell; ``None`` when no ``.java`` source exists under
    ``repo_root`` at all.
    """
    types = _collect_types(repo_root)
    if not types:
        return None
    parts = qualified_name.split(".")
    if len(parts) == 1:
        occurrences = types.get(parts[0])
        if not occurrences:
            return False
        return any(o["public"] for o in occurrences)
    owner, member = parts[-2], parts[-1]
    occurrences = types.get(owner)
    if not occurrences:
        return False
    for occurrence in occurrences:
        if member in occurrence["members"] and occurrence["public"] and occurrence["members"][member]:
            return True
    return False
