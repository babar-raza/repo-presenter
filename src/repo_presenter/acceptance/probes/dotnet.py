"""Independent export-surface probe for .NET/C#: a new, positive public-surface reader.

The vendored engine's own ``lang/csharp.py``'s ``export_surface`` returns only a deny-list of
``internal_names`` -- membership means UNREACHABLE, the opposite polarity from Python/Rust's own
``export_surface`` (see that module's docstring, "polarity note"). A name absent from that
deny-list is not thereby proven public: ``protected``/``internal`` members are also absent from a
pure internal-name deny-list. This module never reads that deny-list; it is a new, independent,
positive reader: a type or member is public when its declared accessibility is ``public`` (or
the implicit default for an interface member, which C# treats as public whether or not the
keyword is written), and -- for a nested type or member -- every enclosing type must also be
public, read directly from the source text.

Three-valued contract (see the package docstring): ``None`` means no ``.cs`` source at all is
found under ``repo_root`` -- the probe cannot tell because there is nothing here that looks like
a .NET package to read.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

_TYPE_OPEN = re.compile(
    r"(?P<mods>(?:\[[^\]]*\]\s*|public\s+|private\s+|protected\s+|internal\s+|static\s+"
    r"|sealed\s+|abstract\s+|partial\s+)*)"
    r"(?P<keyword>class|struct|interface|enum|record)\s+(?P<name>[A-Za-z_]\w*)\b[^{;]*\{"
)
_MEMBER_ANY = re.compile(
    r"(?P<mods>(?:\[[^\]]*\]\s*|public\s+|private\s+|protected\s+|internal\s+|static\s+"
    r"|sealed\s+|abstract\s+|virtual\s+|override\s+|readonly\s+|async\s+)*)"
    r"[\w\[\]<>,.?]+\s+(?P<name>[A-Za-z_]\w*)\s*"
    r"(?:\([^;{}]*\)\s*(?:=>[^;{}]*;|\{|;)|\{[^{}]*\}|=[^;{}]*;|;)"
)


class _TypeInfo(TypedDict):
    name: str
    keyword: str
    own_public: bool
    effective_public: bool
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


def _scan_members(body: str, interface_body: bool) -> dict[str, bool]:
    """Every member declared directly in ``body``, mapped to its own effective public-ness.

    An interface member is public whether or not it carries the keyword; a method's own body is
    skipped by brace matching rather than left for the regex to re-enter, so a local variable
    never reads as a field of the enclosing type.
    """
    found: dict[str, bool] = {}
    pos = 0
    while True:
        match = _MEMBER_ANY.search(body, pos)
        if match is None:
            break
        name = match.group("name")
        public = interface_body or "public" in match.group("mods").split()
        found[name] = found.get(name, False) or public
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

    def effective_public(index: int, seen: frozenset[int] = frozenset()) -> bool:
        if index in seen:
            return False
        span = spans[index]
        own = "public" in span["mods"].split()
        parent = span["parent"]
        if parent is None:
            return own
        return own and effective_public(parent, seen | {index})

    types: list[_TypeInfo] = []
    for index, span in enumerate(spans):
        body = list(text[span["body_start"] : span["end"]])
        for child in spans:
            if child["parent"] != index:
                continue
            start = child["start"] - span["body_start"]
            end = child["end"] - span["body_start"]
            for k in range(max(start, 0), min(end, len(body))):
                body[k] = " "
        own_body = "".join(body)
        members = _scan_members(own_body, interface_body=span["keyword"] == "interface")
        types.append(
            {
                "name": span["name"],
                "keyword": span["keyword"],
                "own_public": "public" in span["mods"].split(),
                "effective_public": effective_public(index),
                "members": members,
            }
        )
    return types


def _collect_types(repo_root: Path) -> dict[str, list[_TypeInfo]]:
    found: dict[str, list[_TypeInfo]] = {}
    if not repo_root.is_dir():
        return found
    for path in sorted(repo_root.rglob("*.cs")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for type_info in _parse_file(text):
            found.setdefault(type_info["name"], []).append(type_info)
    return found


def count(repo_root: Path, kind: str) -> int | None:
    """How many public types of ``kind`` ("class" covers class/struct/interface/record; "enum"
    too) the probe can count.

    ``None`` when no ``.cs`` source exists under ``repo_root`` at all, or when ``kind`` is not
    ``"class"`` or ``"enum"``.
    """
    if kind not in ("class", "enum"):
        return None
    types = _collect_types(repo_root)
    if not types:
        return None
    wanted = {"enum"} if kind == "enum" else {"class", "struct", "interface", "record"}
    return sum(
        1
        for occurrences in types.values()
        if any(o["keyword"] in wanted and o["effective_public"] for o in occurrences)
    )


def exists(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` (a type, or ``Type.member``) is declared anywhere at all.

    Public or private both count as "exists". ``None`` when no ``.cs`` source exists under
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
    """Whether ``qualified_name`` is declared ``public`` (or is an interface member), with every
    enclosing type also public.

    ``True``/``False`` when the probe can tell; ``None`` when no ``.cs`` source exists under
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
        return any(o["effective_public"] for o in occurrences)
    owner, member = parts[-2], parts[-1]
    occurrences = types.get(owner)
    if not occurrences:
        return False
    for occurrence in occurrences:
        if member in occurrence["members"] and occurrence["effective_public"] and occurrence["members"][member]:
            return True
    return False
