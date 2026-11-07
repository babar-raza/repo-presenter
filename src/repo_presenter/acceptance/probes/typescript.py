"""Independent export-surface probe for TypeScript: a thin wrapper, reusing the existing reader.

``extractors/platforms/typescript_barrel.py``'s ``entry_barrel``/``reexported_names`` are already
a genuinely independent reader of the package's actual barrel file -- TypeScript has no
``public`` keyword at module scope, so only the entry point the manifest declares (directly or
through another barrel) decides what a consumer can reach. This module never reimplements that
reading; it only (a) locates the package directory the barrel reader needs, which it does not do
itself, and (b) answers "is this name declared anywhere in source at all" (public or private),
which the barrel reader does not answer since it only ever reads the re-export graph.

Three-valued contract (see the package docstring): ``None`` means the probe cannot tell -- here,
when no ``package.json`` can be found under ``repo_root`` at all (``exported``/``count``), or
when no TypeScript source file exists under ``repo_root`` at all (``exists``).
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_presenter.extractors.platforms.typescript_barrel import (
    entry_barrel,
    reexported_names,
)
from repo_presenter.extractors.surface.npm_package import IGNORED_DIRECTORIES, TYPESCRIPT_MODULES

_TOP_DECL = re.compile(
    r"(?:export\s+)?(?:declare\s+)?(?:default\s+)?(?:abstract\s+)?"
    r"(?:class|interface|enum|function|const|let|var|type)\s+([A-Za-z_$][\w$]*)"
)
_KIND_DECL = {
    "class": re.compile(
        r"(?:export\s+)?(?:declare\s+)?(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)"
    ),
    "enum": re.compile(r"(?:export\s+)?(?:declare\s+)?enum\s+([A-Za-z_$][\w$]*)"),
    "function": re.compile(
        r"(?:export\s+)?(?:declare\s+)?(?:default\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)"
    ),
}
_CLASS_OPEN = re.compile(r"\bclass\s+([A-Za-z_$][\w$]*)[^{;]*\{")
_MEMBER_DECL = re.compile(
    r"(?:public\s+|private\s+|protected\s+|readonly\s+|static\s+|async\s+|get\s+|set\s+)*"
    r"([A-Za-z_$][\w$]*)\s*[(:=]"
)
_NOT_A_MEMBER = frozenset({"constructor", "if", "for", "while", "switch", "return"})


def _is_excluded(path: Path, root: Path) -> bool:
    return any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts)


def _source_files(repo_root: Path) -> list[Path]:
    if not repo_root.is_dir():
        return []
    return sorted(
        p
        for suffix in TYPESCRIPT_MODULES.suffixes
        for p in repo_root.rglob(f"*{suffix}")
        if not _is_excluded(p, repo_root)
    )


def _find_package(repo_root: Path) -> Path | None:
    """The directory holding the package's own ``package.json``, shallowest first."""
    if (repo_root / "package.json").is_file():
        return repo_root
    if not repo_root.is_dir():
        return None
    candidates = [
        path
        for path in repo_root.rglob("package.json")
        if not _is_excluded(path, repo_root)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda path: (len(path.relative_to(repo_root).parts), str(path)))
    return candidates[0].parent


def _barrel(repo_root: Path) -> Path | None:
    package = _find_package(repo_root)
    if package is None:
        return None
    return entry_barrel(package)


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


def _class_members(repo_root: Path, owner: str) -> set[str] | None:
    """Member names declared in every ``class owner { ... }`` body found in the tree.

    ``None`` when ``owner`` itself is never declared as a class anywhere.
    """
    found: set[str] | None = None
    for path in _source_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in _CLASS_OPEN.finditer(text):
            if match.group(1) != owner:
                continue
            found = found or set()
            body_end = _brace_match(text, match.end() - 1)
            body = text[match.end() : body_end]
            for member in _MEMBER_DECL.findall(body):
                if member not in _NOT_A_MEMBER:
                    found.add(member)
    return found


def exists(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` is declared anywhere in the source, public or private.

    A dotted name is read as ``Owner.member``; anything deeper keeps only the last two parts.
    ``None`` when no TypeScript source exists under ``repo_root`` at all.
    """
    files = _source_files(repo_root)
    if not files:
        return None
    parts = qualified_name.split(".")
    if len(parts) == 1:
        name = parts[0]
        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if any(match.group(1) == name for match in _TOP_DECL.finditer(text)):
                return True
        return False
    owner, member = parts[-2], parts[-1]
    members = _class_members(repo_root, owner)
    if members is None:
        return False
    return member in members


def exported(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` is reachable from the package's own barrel entry point.

    ``True``/``False`` when the probe can tell; ``None`` when no ``package.json`` (and so no
    entry point to check against) can be found under ``repo_root`` at all.
    """
    barrel = _barrel(repo_root)
    if barrel is None:
        return None
    names = reexported_names(barrel)
    parts = qualified_name.split(".")
    top = parts[0] if len(parts) == 1 else parts[-2]
    if top in names:
        return True
    existing = exists(repo_root, qualified_name)
    if existing is None:
        return None
    return False


def count(repo_root: Path, kind: str) -> int | None:
    """How many of the package's exported declarations of ``kind`` the probe can count.

    ``None`` when no ``package.json``/entry point is found at all, or when ``kind`` is not one of
    ``"class"``, ``"enum"`` or ``"function"`` (this probe's syntactic reach for TypeScript).
    """
    pattern = _KIND_DECL.get(kind)
    if pattern is None:
        return None
    barrel = _barrel(repo_root)
    if barrel is None:
        return None
    names = reexported_names(barrel)
    found: set[str] = set()
    for path in _source_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in pattern.finditer(text):
            if match.group(1) in names:
                found.add(match.group(1))
    return len(found)
