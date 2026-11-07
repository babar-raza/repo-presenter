"""Independent export-surface probe for Go: a new, independent reader built from source text.

The vendored engine's own ``lang/go.py``'s ``export_surface`` returns ``(None, None)``
unconditionally -- "No reachability signal implemented for Go yet." This module never reads the
main engine's symbol table: it is a new, independent syntactic reader. An identifier is exported
per Go's own rule -- its first letter is uppercase -- at package scope, read directly from the
source text.

Three-valued contract (see the package docstring): ``None`` means no ``.go`` source at all is
found under ``repo_root`` -- the probe cannot tell because there is nothing here that looks like
a Go package to read.
"""

from __future__ import annotations

import re
from pathlib import Path

_IGNORED_DIRECTORIES = frozenset({"vendor", ".git", "testdata"})
_TYPE_DECL = re.compile(r"(?m)^type\s+([A-Za-z_]\w*)\b")
_FUNC_DECL = re.compile(r"(?m)^func\s+([A-Za-z_]\w*)\s*\(")
_METHOD_DECL = re.compile(r"(?m)^func\s*\(\s*[A-Za-z_]\w*\s+\*?([A-Za-z_]\w*)\s*\)\s*([A-Za-z_]\w*)\s*\(")
_TOP_VAR_CONST = re.compile(r"(?m)^(?:const|var)\s+([A-Za-z_]\w*)\b")


def _source_files(repo_root: Path) -> list[Path]:
    if not repo_root.is_dir():
        return []
    return sorted(
        p
        for p in repo_root.rglob("*.go")
        if not any(part in _IGNORED_DIRECTORIES for part in p.relative_to(repo_root).parts)
    )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _types(repo_root: Path) -> set[str]:
    return {
        name
        for path in _source_files(repo_root)
        for name in _TYPE_DECL.findall(_read(path))
    }


def _functions(repo_root: Path) -> set[str]:
    return {
        name
        for path in _source_files(repo_root)
        for name in _FUNC_DECL.findall(_read(path))
    }


def _top_level_names(repo_root: Path) -> set[str]:
    names = _types(repo_root) | _functions(repo_root)
    for path in _source_files(repo_root):
        names.update(_TOP_VAR_CONST.findall(_read(path)))
    return names


def _methods(repo_root: Path) -> dict[str, set[str]]:
    by_receiver: dict[str, set[str]] = {}
    for path in _source_files(repo_root):
        for receiver, method in _METHOD_DECL.findall(_read(path)):
            by_receiver.setdefault(receiver, set()).add(method)
    return by_receiver


def count(repo_root: Path, kind: str) -> int | None:
    """How many exported (capitalized) declarations of ``kind`` the probe can count.

    ``None`` when no ``.go`` source exists under ``repo_root`` at all, or when ``kind`` is not
    ``"class"`` (Go's ``type`` declarations), ``"function"`` or ``"method"``.
    """
    if kind not in ("class", "function", "method"):
        return None
    files = _source_files(repo_root)
    if not files:
        return None
    if kind == "class":
        return sum(1 for name in _types(repo_root) if name[:1].isupper())
    if kind == "function":
        return sum(1 for name in _functions(repo_root) if name[:1].isupper())
    return sum(
        1
        for receiver, methods in _methods(repo_root).items()
        if receiver[:1].isupper()
        for method in methods
        if method[:1].isupper()
    )


def exists(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` (a package-scope identifier, or ``Type.Method``) is declared.

    Exported or unexported both count as "exists". ``None`` when no ``.go`` source exists under
    ``repo_root`` at all.
    """
    files = _source_files(repo_root)
    if not files:
        return None
    parts = qualified_name.split(".")
    if len(parts) == 1:
        return parts[0] in _top_level_names(repo_root)
    owner, member = parts[-2], parts[-1]
    return member in _methods(repo_root).get(owner, set())


def exported(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` is exported per Go's own rule: its first letter is uppercase.

    For ``Type.Method``, both the method name and its receiver type must be capitalized -- an
    unexported receiver type is not reachable from outside the package however its methods are
    named. ``True``/``False`` when the probe can tell; ``None`` when no ``.go`` source exists
    under ``repo_root`` at all.
    """
    files = _source_files(repo_root)
    if not files:
        return None
    parts = qualified_name.split(".")
    if len(parts) == 1:
        name = parts[0]
        if name not in _top_level_names(repo_root):
            return False
        return name[:1].isupper()
    owner, member = parts[-2], parts[-1]
    if member not in _methods(repo_root).get(owner, set()):
        return False
    return bool(owner[:1].isupper() and member[:1].isupper())
