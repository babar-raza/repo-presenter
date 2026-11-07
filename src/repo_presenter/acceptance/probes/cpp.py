"""Independent export-surface probe for C++: a new, independent reader built from header paths.

The vendored engine's own ``lang/cpp.py``'s ``export_surface`` returns ``(None, None)``
unconditionally -- "No reachability signal implemented for C++ yet." The main engine does tag
``visibility: "internal"`` for C++ headers under an ``internal/`` path segment
(``api_surface.py``'s ``_CPP_ONLY_VENDOR_SEGMENTS``), but that tag comes from the same engine a
probe exists to check independently, so this module never reads it: it re-derives public/private
from the header tree itself, from scratch, by reading the actual header paths on disk.

Rule (matching, not calling into, ``api_surface.py``'s own filter): a declaration is public when
it is declared in a header file under the package's own tree, excluding any path with an
``internal`` segment (exact segment match -- ``international`` is not excluded).

Three-valued contract (see the package docstring): ``None`` means no C++ header at all is found
under ``repo_root`` -- the probe cannot tell because there is nothing here that looks like a C++
package to read.
"""

from __future__ import annotations

import re
from pathlib import Path

_HEADER_SUFFIXES = (".h", ".hpp", ".hh", ".hxx")
_INTERNAL_SEGMENT = "internal"
_IGNORED_DIRECTORIES = frozenset({".git", "build", "cmake-build-debug", "out"})

_KIND_DECL = {
    "class": re.compile(r"\b(?:class|struct)\s+([A-Za-z_]\w*)\b(?!\s*;)"),
    "enum": re.compile(r"\benum(?:\s+class)?\s+([A-Za-z_]\w*)\b"),
}
_ANY_DECL = re.compile(r"\b(?:class|struct|enum(?:\s+class)?)\s+([A-Za-z_]\w*)\b(?!\s*;)")


def _is_internal(path: Path, root: Path) -> bool:
    return _INTERNAL_SEGMENT in path.relative_to(root).parts


def _header_files(repo_root: Path) -> list[Path]:
    if not repo_root.is_dir():
        return []
    return sorted(
        p
        for suffix in _HEADER_SUFFIXES
        for p in repo_root.rglob(f"*{suffix}")
        if not any(part in _IGNORED_DIRECTORIES for part in p.relative_to(repo_root).parts)
    )


def _declared_names(headers: list[Path], pattern: re.Pattern[str]) -> set[str]:
    found: set[str] = set()
    for path in headers:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        found.update(pattern.findall(text))
    return found


def count(repo_root: Path, kind: str) -> int | None:
    """How many public (non-``internal/``) declarations of ``kind`` the probe can count.

    ``None`` when no C++ header exists under ``repo_root`` at all, or when ``kind`` is not
    ``"class"`` or ``"enum"`` (this probe's syntactic reach for C++).
    """
    pattern = _KIND_DECL.get(kind)
    if pattern is None:
        return None
    headers = _header_files(repo_root)
    if not headers:
        return None
    public_headers = [h for h in headers if not _is_internal(h, repo_root)]
    return len(_declared_names(public_headers, pattern))


def exists(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` (its last ``::``/``.``-separated segment) is declared anywhere.

    Public or private (``internal/``) both count as "exists". ``None`` when no C++ header exists
    under ``repo_root`` at all.
    """
    headers = _header_files(repo_root)
    if not headers:
        return None
    name = re.split(r"::|\.", qualified_name)[-1]
    return name in _declared_names(headers, _ANY_DECL)


def exported(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` is declared under a header path with no ``internal`` segment.

    ``True``/``False`` when the probe can tell; ``None`` when no C++ header exists under
    ``repo_root`` at all.
    """
    headers = _header_files(repo_root)
    if not headers:
        return None
    name = re.split(r"::|\.", qualified_name)[-1]
    public_headers = [h for h in headers if not _is_internal(h, repo_root)]
    if name in _declared_names(public_headers, _ANY_DECL):
        return True
    return False
