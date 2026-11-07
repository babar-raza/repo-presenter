"""Independent export-surface probe for Rust: wraps the vendored engine's own `pub use` reader.

``extractors/surface/extractor.py``'s ``surface_symbols`` already refuses to trust the vendored
engine's own ``reachable: False`` mark alone, because that best-effort scan is "measurably wrong
in both directions for Rust" (it called ``semver::Version``, defined in ``lib.rs``, unreachable
by mistake, and ``aho_corasick::AhoCorasick``, re-exported through nested braces, unreachable by
mistake too). It accepts a caller-supplied ``confirms_unreachable`` function and drops an entry
only when that function independently agrees; nobody has ever supplied one.

The vendored engine's own ``lang/rust.py``'s ``export_surface``/``reexported_names`` already read
`pub use` re-exports from the crate root honestly and well -- this module reuses that reader
rather than re-deriving Rust exports from scratch, but never trusts it alone: ``confirms_unreachable_for``
builds a callable that only confirms unreachability when a SECOND, independent negative signal
also agrees -- the name's own declaration in ``lib.rs`` lacks a bare ``pub``
(``pub(crate)``/``pub(super)``/``pub(in ...)`` do not count, read directly from the source text,
independently of the vendored engine's own tree-sitter visibility check).

Three-valued contract (see the package docstring): ``None`` means no ``.rs`` source at all is
found under ``repo_root`` (``exists``), or no crate root (a directory holding ``lib.rs``) can be
found at all (``exported``/``count``) -- the probe cannot tell because there is nothing here that
looks like a Rust crate to read.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from repo_presenter.extractors.surface._vendor.aspose_extraction.lang import rust as _rust_lang

_IGNORED_DIRECTORIES = frozenset({"target", ".git"})
_BARE_PUB_DECL = re.compile(r"\bpub\s+(?:struct|enum|fn|trait|type|const|static|mod)\s+([A-Za-z_]\w*)")
_ANY_DECL = re.compile(
    r"(?:pub(?:\([\w:]+\))?\s+)?(?:struct|enum|fn|trait|type|const|static|mod)\s+([A-Za-z_]\w*)"
)
_KIND_DECL = {
    "class": re.compile(r"(?:pub(?:\([\w:]+\))?\s+)?(?:struct|trait)\s+([A-Za-z_]\w*)"),
    "enum": re.compile(r"(?:pub(?:\([\w:]+\))?\s+)?enum\s+([A-Za-z_]\w*)"),
    "function": re.compile(r"(?:pub(?:\([\w:]+\))?\s+)?fn\s+([A-Za-z_]\w*)"),
}


def _source_files(repo_root: Path) -> list[Path]:
    if not repo_root.is_dir():
        return []
    return sorted(
        p
        for p in repo_root.rglob("*.rs")
        if not any(part in _IGNORED_DIRECTORIES for part in p.relative_to(repo_root).parts)
    )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _find_crate_root(repo_root: Path) -> Path | None:
    """The directory holding ``lib.rs``, shallowest first; ``None`` when none is found."""
    if not repo_root.is_dir():
        return None
    candidates = [
        p
        for p in repo_root.rglob("lib.rs")
        if not any(part in _IGNORED_DIRECTORIES for part in p.relative_to(repo_root).parts)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: (len(p.relative_to(repo_root).parts), str(p)))
    return candidates[0].parent


def _bare_pub_names(pkg_root: Path) -> set[str] | None:
    lib_rs = pkg_root / "lib.rs"
    if not lib_rs.is_file():
        return None
    return {match.group(1) for match in _BARE_PUB_DECL.finditer(_read(lib_rs))}


def confirms_unreachable_for(pkg_root: Path) -> Callable[[dict[str, Any]], bool]:
    """Build the ``confirms_unreachable`` callable ``surface_symbols`` already accepts.

    Confirms unreachability only when two independent negative signals agree: the name is absent
    from `pub use` re-exports at the crate root (the vendored engine's own ``reexported_names``)
    AND the name's own declaration in ``lib.rs`` lacks a bare ``pub``. Never trusts either signal
    alone -- a name re-exported through nested braces (signal 1 says reachable) must not be
    confirmed unreachable merely because signal 2's regex-only scan cannot see it declared in
    ``lib.rs`` at all (it may be declared, and `pub use`-re-exported, from another module).
    """

    def confirms_unreachable(entry: dict[str, Any]) -> bool:
        raw = str(entry.get("class_import") or entry.get("name") or "")
        name = re.split(r"::|\.", raw)[-1] if raw else ""
        if not name:
            return False
        reexported = _rust_lang.reexported_names(pkg_root)
        if reexported is not None and name in reexported:
            return False  # signal 1 disagrees: it is re-exported
        bare_pub = _bare_pub_names(pkg_root)
        if bare_pub is None or name in bare_pub:
            return False  # signal 2 disagrees, or lib.rs could not be read -- stay safe
        return True  # both independent negative signals agree

    return confirms_unreachable


def count(repo_root: Path, kind: str) -> int | None:
    """How many exported items of ``kind`` ("class" covers struct/trait, plus "enum"/"function")
    the probe can count.

    ``None`` when no crate root (a directory holding ``lib.rs``) is found under ``repo_root`` at
    all, or when ``kind`` is not one of ``"class"``, ``"enum"`` or ``"function"``.
    """
    pattern = _KIND_DECL.get(kind)
    if pattern is None:
        return None
    pkg_root = _find_crate_root(repo_root)
    if pkg_root is None:
        return None
    names: set[str] = set()
    for path in _source_files(repo_root):
        for match in pattern.finditer(_read(path)):
            names.add(match.group(1))
    return sum(1 for name in names if exported(repo_root, name))


def exists(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` (its last ``::``/``.``-separated segment) is declared anywhere.

    `pub`, `pub(crate)` and unmarked declarations all count as "exists". ``None`` when no ``.rs``
    source exists under ``repo_root`` at all.
    """
    files = _source_files(repo_root)
    if not files:
        return None
    name = re.split(r"::|\.", qualified_name)[-1]
    for path in files:
        if any(match.group(1) == name for match in _ANY_DECL.finditer(_read(path))):
            return True
    return False


def exported(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` is reachable: `pub use`-re-exported at the crate root, OR
    declared with a bare ``pub`` in ``lib.rs`` -- the same two signals ``confirms_unreachable_for``
    requires to agree before calling something unreachable, read the positive way round.

    ``True``/``False`` when the probe can tell; ``None`` when no crate root is found at all.
    """
    pkg_root = _find_crate_root(repo_root)
    if pkg_root is None:
        return None
    name = re.split(r"::|\.", qualified_name)[-1]
    reexported = _rust_lang.reexported_names(pkg_root)
    if reexported is not None and name in reexported:
        return True
    bare_pub = _bare_pub_names(pkg_root)
    if bare_pub is not None and name in bare_pub:
        return True
    existing = exists(repo_root, qualified_name)
    if existing is None:
        return None
    return False
