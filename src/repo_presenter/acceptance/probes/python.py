"""Independent export-surface probe for Python: a thin wrapper, reusing the existing reader.

``extractors/platforms/python_surface.py``'s ``inspect_public_surface`` is already a genuinely
independent, ``ast``-based reader: a name is public when it has no leading underscore and, when
the module declares a literal ``__all__``, is listed there (``_public_name``). This module never
reimplements that policy; it only (a) discovers the package directories ``inspect_public_surface``
needs, which it does not do itself, and (b) answers "does this name exist in source at all"
(public or private), which ``inspect_public_surface`` does not answer since it only ever collects
the public surface.

Three-valued contract (see the package docstring): ``None`` means the probe cannot tell -- here,
when no Python package can be found under ``repo_root`` at all, or when the name's own module
could not be parsed (a real syntax error, not a policy choice).
"""

from __future__ import annotations

import ast
from pathlib import Path

from repo_presenter.extractors.platforms.python_surface import (
    PublicSurface,
    inspect_public_surface,
)

#: The literal ``SymbolKind`` vocabulary ``extractor.py``/``python_surface.py`` already use.
_SUPPORTED_KINDS = frozenset({"module", "class", "enum", "function", "method", "unknown"})
_EXCLUDED_PARTS = frozenset({"__pycache__", "build", "dist", "tests", "test", "docs", "examples"})


def _discover_package_dirs(repo_root: Path) -> list[str]:
    """Top-level directories that look like Python packages (contain ``__init__.py``).

    A plain top-level layout (``pkg/__init__.py``) and the common src-layout
    (``src/pkg/__init__.py``) are both tried; neither is assumed. This is a filesystem scan, not
    a reimplementation of the public/private policy ``inspect_public_surface`` already owns.
    """
    found: list[str] = []
    if not repo_root.is_dir():
        return found
    for candidate_root, prefix in ((repo_root, ""), (repo_root / "src", "src/")):
        if not candidate_root.is_dir():
            continue
        for entry in sorted(candidate_root.iterdir()):
            if (
                entry.is_dir()
                and entry.name not in _EXCLUDED_PARTS
                and not entry.name.startswith(".")
                and (entry / "__init__.py").is_file()
            ):
                found.append(f"{prefix}{entry.name}")
    return found


def _surface(repo_root: Path) -> PublicSurface | None:
    package_dirs = _discover_package_dirs(repo_root)
    if not package_dirs:
        return None
    return inspect_public_surface(repo_root, package_dirs)


def _raw_declarations(repo_root: Path, package_dirs: list[str]) -> tuple[set[str], set[str]]:
    """Every dotted name declared anywhere in source (public or private), and unparseable modules.

    A flat, independent existence scan: every module, class, function and method defined in the
    tree, regardless of leading underscore or ``__all__`` -- a different, simpler question than
    the public/private policy ``inspect_public_surface`` already answers, so it is answered here
    rather than by reading that reader's own private helpers.
    """
    declared: set[str] = set()
    unparseable: set[str] = set()
    for package_dir in package_dirs:
        package_path = repo_root / package_dir
        source_root = package_path.parent
        if not package_path.is_dir():
            continue
        for path in sorted(package_path.rglob("*.py")):
            relative = path.relative_to(source_root)
            if any(part in _EXCLUDED_PARTS for part in relative.parts):
                continue
            is_package = path.name == "__init__.py"
            parts = relative.parent.parts if is_package else relative.with_suffix("").parts
            module = ".".join(parts)
            if not module:
                continue
            try:
                tree = ast.parse(
                    path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path)
                )
            except SyntaxError:
                unparseable.add(module)
                continue
            declared.add(module)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    declared.add(f"{module}.{node.name}")
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                            declared.add(f"{module}.{node.name}.{item.name}")
            for node in tree.body:
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    declared.add(f"{module}.{node.name}")
    return declared, unparseable


def _module_of(qualified_name: str) -> str:
    """The longest declared-module-looking prefix of ``qualified_name`` -- best effort."""
    return qualified_name.rsplit(".", 1)[0] if "." in qualified_name else qualified_name


def count(repo_root: Path, kind: str) -> int | None:
    """How many public symbols of ``kind`` the independent Python reader can count.

    ``None`` when no Python package is found under ``repo_root`` at all, or when ``kind`` is not
    one of this codebase's own ``SymbolKind`` values. Never ``0`` to mean "could not tell" --
    a package with zero public symbols of ``kind`` legitimately counts as ``0``.
    """
    if kind not in _SUPPORTED_KINDS:
        return None
    surface = _surface(repo_root)
    if surface is None:
        return None
    return sum(1 for symbol in surface.symbols if symbol.kind == kind)


def exists(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` is declared anywhere in the source, public or private.

    ``True``/``False`` when the probe can tell; ``None`` when the module that would declare it
    could not be parsed (a real syntax error), or when no Python package is found at all.
    """
    package_dirs = _discover_package_dirs(repo_root)
    if not package_dirs:
        return None
    declared, unparseable = _raw_declarations(repo_root, package_dirs)
    if qualified_name in declared:
        return True
    module = _module_of(qualified_name)
    while module:
        if module in unparseable:
            return None
        module = _module_of(module) if "." in module else ""
    return False


def exported(repo_root: Path, qualified_name: str) -> bool | None:
    """Whether ``qualified_name`` is reachable from the package's own public surface.

    Reuses ``inspect_public_surface`` for the policy decision (name has no leading underscore,
    and is in ``__all__`` when one is declared). ``True``/``False`` when the probe can tell;
    ``None`` when the probe cannot determine existence or resolution at all.
    """
    surface = _surface(repo_root)
    if surface is None:
        return None
    by_name = {symbol.qualified_name: symbol for symbol in surface.symbols}
    symbol = by_name.get(qualified_name)
    if symbol is not None:
        # kind == "unknown" means an unresolved re-export chain: a real ambiguity, not a no.
        return None if symbol.kind == "unknown" else True
    existing = exists(repo_root, qualified_name)
    if existing is None:
        return None
    return False
