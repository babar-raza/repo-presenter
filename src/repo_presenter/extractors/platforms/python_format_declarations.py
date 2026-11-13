"""Static format declarations of a Python product, read from its syntax trees, never imported.

Two independent static sources corroborate a format claim: the product's ``FileFormat`` module,
which imports one format class per format it provides, each class stating its extensions as
literals; and the plugin registrations, ``register_plugin(XPlugin())`` calls whose plugin binds
an importer (input) and an exporter (output) and names its format class. An importer or
exporter whose every entry method only raises NotImplementedError is a stub and registers
nothing for its direction, so a declared but unimplemented export never reads as supported.

Ported (REUSE, near-verbatim) from the old repository-presenter project's
``components/readme/extractors/platforms/python_format_declarations.py`` per
migration/reuse-manifest.yaml; only import paths are adapted.
"""

from __future__ import annotations

import ast
from pathlib import Path

from repo_presenter.core.examples import FormatDeclaration, FormatDirection
from repo_presenter.extractors.platforms.python_format_dispatch import (
    dispatch_declarations,
)

_ENTRY_METHODS = frozenset(
    {"export", "save", "save_to_stream", "import_scene", "load", "load_from_stream", "read"}
)
_SOURCE_SUFFIX = ".py"


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


def _classes(tree: ast.Module) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _string_literals(node: ast.AST) -> list[str]:
    return [
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    ]


def _extension(literal: str) -> str | None:
    text = literal.strip().lower()
    if not text or "/" in text or " " in text:
        return None
    text = text.lstrip(".")
    return f".{text}" if text.isalnum() and 1 <= len(text) <= 5 else None


def _extensions_of(format_class: ast.ClassDef) -> list[str]:
    """The extension literals the format class's ``extensions`` (or ``extension``) returns."""
    for name in ("extensions", "extension"):
        for node in format_class.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                found = [e for e in map(_extension, _string_literals(node)) if e]
                if found:
                    return sorted(set(found))
    return []


def _is_stub(class_def: ast.ClassDef) -> bool:
    """Whether every entry method the class defines only raises NotImplementedError."""
    entries = [
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name in _ENTRY_METHODS
    ]
    if not entries:
        return False
    for method in entries:
        body = [
            s
            for s in method.body
            if not (
                isinstance(s, ast.Expr)
                and isinstance(s.value, ast.Constant)
                and isinstance(s.value.value, str)
            )
        ]  # a docstring is not a statement of intent
        raises = [s for s in body if isinstance(s, ast.Raise)]
        if len(body) != len(raises) or not all(
            "NotImplementedError" in ast.unparse(s.exc) for s in raises if s.exc is not None
        ):
            return False
    return True


def _called_class(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _returned_class(function: ast.FunctionDef) -> str | None:
    for node in ast.walk(function):
        if isinstance(node, ast.Return) and node.value is not None:
            called = _called_class(node.value)
            if called:
                return called
    return None


class _Index:
    """Every class definition under the product tree, by name, with its file and line."""

    def __init__(self, root: Path, tree_paths: list[str]) -> None:
        self.classes: dict[str, tuple[str, ast.ClassDef]] = {}
        self.modules: dict[str, ast.Module] = {}
        for relative in sorted(tree_paths):
            if not relative.endswith(_SOURCE_SUFFIX):
                continue
            tree = _parse(root / relative)
            if tree is None:
                continue
            self.modules[relative] = tree
            for name, node in _classes(tree).items():
                self.classes.setdefault(name, (relative, node))


def _declarations(index: _Index) -> list[FormatDeclaration]:
    """Every extension a format class imported by a ``FileFormat`` module states."""
    found: list[FormatDeclaration] = []
    for relative, tree in index.modules.items():
        if Path(relative).name != "FileFormat.py":
            continue
        seen: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                if not alias.name.endswith("Format") or alias.name in seen:
                    continue
                located = index.classes.get(alias.name)
                if located is None:
                    continue
                seen.add(alias.name)
                for extension in _extensions_of(located[1]):
                    found.append(
                        FormatDeclaration(
                            extension,
                            None,
                            "declaration",
                            relative,
                            node.lineno,
                            f"FileFormat imports {alias.name}, which states {extension}",
                        )
                    )
    return found


def _probe_methods(index: _Index) -> set[str]:
    """The methods a dispatcher asks each registered importer/exporter in turn (``for exporter in
    self._exporters: if exporter.supports_format(fmt): return exporter``): read from the loops
    themselves, so a product without such a dispatcher has none and nothing below changes."""
    probes: set[str] = set()
    for tree in index.modules.values():
        for loop in ast.walk(tree):
            if not isinstance(loop, ast.For) or not isinstance(loop.target, ast.Name):
                continue
            variable = loop.target.id
            for branch in loop.body:
                if not isinstance(branch, ast.If):
                    continue
                for call in ast.walk(branch.test):
                    if (
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and isinstance(call.func.value, ast.Name)
                        and call.func.value.id == variable
                    ):
                        probes.add(call.func.attr)
    return probes


def _resolve(index: _Index, class_name: str, method: str, depth: int = 0) -> tuple[str, ast.FunctionDef] | None:
    """The class that defines ``method`` for ``class_name`` (itself or the first base, through the
    product's own classes), and the definition."""
    located = index.classes.get(class_name)
    if located is None or depth > 8:
        return None
    for node in located[1].body:
        if isinstance(node, ast.FunctionDef) and node.name == method:
            return class_name, node
    for base in located[1].bases:
        found = _resolve(index, ast.unparse(base).rsplit(".", 1)[-1], method, depth + 1)
        if found is not None:
            return found
    return None


def _only_raises(function: ast.FunctionDef) -> bool:
    body = [
        s
        for s in function.body
        if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
    ]
    return bool(body) and all(isinstance(s, ast.Raise) for s in body)


def _registrations(index: _Index) -> list[FormatDeclaration]:
    """Every (direction, extension) a registered plugin implements with a non-stub class.

    Dispatch order is part of the code path (K02, 2026-11-13: 3D Python registers ``FbxExporter``
    before Collada, and ``FbxExporter`` inherits ``Exporter.supports_format``, which raises; so
    ``Scene.save('x.dae')`` raises NotImplementedError before the Collada exporter is asked). Once
    a registered class's probe method only raises, every plugin registered after it in the same
    sequence is unreachable for that direction: its formats are stated as a directional
    declaration (evidence, never a corroboration), so the fact stays UNRESOLVED."""
    found: list[FormatDeclaration] = []
    probes = _probe_methods(index)
    for relative, tree in index.modules.items():
        calls = sorted(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "register_plugin"
                and node.args
            ),
            key=lambda node: (node.lineno, node.col_offset),
        )
        blocked: dict[FormatDirection, str] = {}
        for node in calls:
            plugin_name = _called_class(node.args[0])
            located = index.classes.get(plugin_name or "")
            if located is None:
                continue
            plugin_path, plugin = located
            for declaration in _plugin_formats(
                index, plugin_name or "", plugin_path, plugin, relative, node.lineno
            ):
                blocker = blocked.get(declaration.direction)  # type: ignore[arg-type]
                if blocker is None:
                    found.append(declaration)
                    continue
                found.append(
                    FormatDeclaration(
                        declaration.extension,
                        declaration.direction,
                        "declaration",
                        relative,
                        node.lineno,
                        f"{plugin_name} is registered after {blocker}, which always raises, so the "
                        f"dispatcher never reaches it for {declaration.extension} "
                        f"({declaration.direction} unreachable)",
                    )
                )
            for direction, class_name in _roles(plugin).items():
                if direction in blocked:
                    continue
                for probe in sorted(probes):
                    resolved = _resolve(index, class_name, probe)
                    if resolved is not None and _only_raises(resolved[1]):
                        blocked[direction] = f"{class_name}.{probe} (defined by {resolved[0]})"
                        break
    return found


def _roles(plugin: ast.ClassDef) -> dict[FormatDirection, str]:
    """The importer (input) and exporter (output) class a plugin binds in ``__init__``."""
    roles: dict[FormatDirection, str] = {}
    for node in plugin.body:
        if not (isinstance(node, ast.FunctionDef) and node.name == "__init__"):
            continue
        for statement in ast.walk(node):
            if not isinstance(statement, ast.Assign):
                continue
            target = statement.targets[0]
            if not isinstance(target, ast.Attribute):
                continue
            bound = _called_class(statement.value)
            if bound is None:
                continue
            if target.attr.lstrip("_").startswith("importer"):
                roles["input"] = bound
            elif target.attr.lstrip("_").startswith("exporter"):
                roles["output"] = bound
    return roles


def _plugin_formats(
    index: _Index,
    plugin_name: str,
    plugin_path: str,
    plugin: ast.ClassDef,
    registered_in: str,
    registered_line: int,
) -> list[FormatDeclaration]:
    format_class: str | None = None
    for node in plugin.body:
        if isinstance(node, ast.FunctionDef) and node.name == "get_file_format":
            format_class = _returned_class(node)
    roles = _roles(plugin)
    if format_class is None or format_class not in index.classes:
        return []
    extensions = _extensions_of(index.classes[format_class][1])
    found: list[FormatDeclaration] = []
    for direction, class_name in sorted(roles.items()):
        located = index.classes.get(class_name)
        if located is None or _is_stub(located[1]):
            continue
        for extension in extensions:
            found.append(
                FormatDeclaration(
                    extension,
                    direction,
                    "registration",
                    registered_in,
                    registered_line,
                    f"{plugin_name} ({plugin_path}) registered with {class_name} for "
                    f"{format_class}, which states {extension}",
                )
            )
    return found


def format_declarations(root: Path, tree_paths: list[str]) -> list[FormatDeclaration]:
    """Declarations and registrations of the product's formats, in a stable order."""
    index = _Index(root, tree_paths)
    found = _declarations(index) + _registrations(index) + dispatch_declarations(index.modules)
    return sorted(found, key=lambda d: (d.kind, d.direction or "", d.extension, d.source_path))
