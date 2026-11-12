"""Static format evidence for Python products that do not use a FileFormat/register_plugin layout.

``python_format_declarations`` reads the one layout the 3D product uses (a ``FileFormat`` module
plus ``register_plugin`` calls). Most other Python products state their formats in plainer
shapes, and for those no format fact could ever reach SUPPORTED without an executed example, so a
true "supports TSV / PDF / BMP" claim in a README read as an unconfirmed over-claim (Lane L review
rejections, 2026-11-09, Cells / Page / Slides / Font Python). This module reads two additional
STATIC sources from the syntax tree, never importing or executing anything and never reading README
prose, and keeps the same corroboration rule the rest of ``formats.py`` has: an extension becomes
SUPPORTED only when BOTH hold.

* a **declaration** (direction-less): a literal collection whose members are all dotted extensions
  (``_SUPPORTED_EXTENSIONS = (".ttf", ".otf")``; a ``{'.tsv': cls.TSV}`` extension map), or a
  non-stub function named for the format (``encode_bmp``); and
* a **registration** (with a direction): a branch of a direction-named function that dispatches on
  that extension (``if fmt == "bmp": return encode_bmp(...)``; ``elif save_format ==
  SaveFormat.TSV: self.save_as_csv(...)``, the member resolved to its extension through the
  extension map above) and whose body is real code, not a bare ``raise``.

One source alone leaves the fact UNRESOLVED, exactly as before.
"""

from __future__ import annotations

import ast
import re

from repo_presenter.core.examples import FormatDeclaration, FormatDirection

_DOTTED = re.compile(r"^\.[a-z0-9]{1,8}$")
_BARE = re.compile(r"^[a-z0-9]{2,6}$")
_SKIP_PARTS = ("test", "tests", "testdata", "example", "examples", "docs", "scripts")
_OUTPUT_TOKENS = frozenset(
    {"save", "write", "export", "encode", "dump", "render", "serialize", "emit", "convert", "to"}
)
_INPUT_TOKENS = frozenset(
    {"load", "read", "open", "import", "decode", "parse", "deserialize", "from", "ingest"}
)
_OUTPUT_ROLES = ("writer", "exporter", "saver", "encoder", "serializer", "renderer")
_INPUT_ROLES = ("reader", "importer", "loader", "decoder", "parser")
_FORMAT_NAME_HINT = re.compile(r"(?:format|fmt|ext|suffix|kind|type)", re.IGNORECASE)
#: Codec-style names only: ``encode_bmp`` / ``decode_tiff`` name a format; ``read_name``,
#: ``parse_line``, ``write_html`` name a parser step or a report, which is not a format
#: declaration (measured: Page's PostScript tokenizer and Cells' sparkline code).
_FORMAT_FUNCTION = re.compile(r"^_?(?:encode|decode)_([a-z0-9]{2,6})$")
_NOT_A_FILE_FORMAT = frozenset(
    {"utf8", "utf16", "utf32", "base64", "base85", "ascii", "hex", "latin1", "bytes", "str",
     "int", "float", "bool", "none", "list", "dict", "value", "name", "string"}
)


def _skipped(relative: str) -> bool:
    parts = [part.lower() for part in relative.replace("\\", "/").split("/")]
    return any(part in _SKIP_PARTS or part.startswith("test_") for part in parts)


def _normalized(literal: object, *, dotted_only: bool) -> str | None:
    if not isinstance(literal, str):
        return None
    text = literal.strip().lower()
    if _DOTTED.match(text):
        return text
    if not dotted_only and _BARE.match(text):
        return "." + text
    return None


def _all_constants(node: ast.AST) -> list[object] | None:
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        if not all(isinstance(e, ast.Constant) for e in node.elts):
            return None
        return [e.value for e in node.elts]  # type: ignore[attr-defined]
    return None


def _tokens(name: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return [t for t in spaced.lower().split("_") if t]


def _direction_of(name: str, class_name: str | None, relative: str) -> FormatDirection | None:
    tokens = set(_tokens(name))
    out, inn = bool(tokens & _OUTPUT_TOKENS), bool(tokens & _INPUT_TOKENS)
    if out != inn:
        return "output" if out else "input"
    if out and inn:
        return None
    haystack = " ".join(filter(None, (class_name, relative.rsplit("/", 1)[-1]))).lower()
    for role in _OUTPUT_ROLES:
        if role in haystack:
            return "output"
    for role in _INPUT_ROLES:
        if role in haystack:
            return "input"
    return None


def _walk_without_raises(node: ast.AST):
    """``ast.walk`` that does not descend into ``raise`` statements: ``raise NotImplementedError(..)``
    contains a Call, but it is the opposite of an implementation."""
    if isinstance(node, ast.Raise):
        return
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _walk_without_raises(child)


def _is_real_code(body: list[ast.stmt]) -> bool:
    """A branch that does something: any call or a return of a value; a bare raise/pass is not."""
    for statement in body:
        for node in _walk_without_raises(statement):
            if isinstance(node, ast.Call):
                return True
            if isinstance(node, ast.Return) and node.value is not None:
                if not (isinstance(node.value, ast.Constant) and node.value.value is None):
                    return True
    return False


def _function_is_stub(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = [
        s
        for s in function.body
        if not (
            isinstance(s, ast.Expr)
            and isinstance(s.value, ast.Constant)
            and isinstance(s.value.value, str)
        )
    ]
    return not body or all(isinstance(s, (ast.Raise, ast.Pass)) for s in body)


def _dict_extension_map(node: ast.Dict) -> dict[str, list[str]]:
    """``{'.tsv': cls.TSV}`` -> ``{'TSV': ['.tsv']}``; only dicts whose keys are ALL dotted
    extensions (two or more) qualify, and only attribute/name values are mapped."""
    keys = [_normalized(k.value, dotted_only=True) if isinstance(k, ast.Constant) else None for k in node.keys]
    if len(keys) < 2 or any(k is None for k in keys):
        return {}
    mapping: dict[str, list[str]] = {}
    for key, value in zip(keys, node.values, strict=False):
        member = value.attr if isinstance(value, ast.Attribute) else getattr(value, "id", None)
        if member and key:
            mapping.setdefault(member, []).append(key)
    return mapping


def _declarations(modules: dict[str, ast.Module]) -> tuple[list[FormatDeclaration], dict[str, list[str]]]:
    found: list[FormatDeclaration] = []
    member_extensions: dict[str, list[str]] = {}
    for relative, tree in modules.items():
        if _skipped(relative):
            continue
        for node in ast.walk(tree):
            extensions: list[str] = []
            if isinstance(node, ast.Dict):
                mapping = _dict_extension_map(node)
                for member, exts in mapping.items():
                    member_extensions.setdefault(member, []).extend(exts)
                    extensions.extend(exts)
                detail = "extension map states {ext}"
            else:
                constants = _all_constants(node)
                if constants is None or len(constants) < 2:
                    continue
                normalized = [_normalized(c, dotted_only=True) for c in constants]
                if any(n is None for n in normalized):
                    continue
                extensions = [n for n in normalized if n]
                detail = "extension collection states {ext}"
            for extension in sorted(set(extensions)):
                found.append(
                    FormatDeclaration(
                        extension, None, "declaration", relative, node.lineno,
                        detail.format(ext=extension),
                    )
                )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                match = _FORMAT_FUNCTION.match(node.name)
                if match and match.group(1) not in _NOT_A_FILE_FORMAT and not _function_is_stub(node):
                    extension = "." + match.group(1)
                    found.append(
                        FormatDeclaration(
                            extension, None, "declaration", relative, node.lineno,
                            f"{node.name}() implements {extension}",
                        )
                    )
    return found, member_extensions


def _test_extensions(test: ast.expr, members: dict[str, list[str]]) -> list[str]:
    """Extensions a branch condition dispatches on."""
    out: list[str] = []
    for node in ast.walk(test):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            left, right = node.left, node.comparators[0]
            op = node.ops[0]
            for subject, other in ((left, right), (right, left)):
                name = ast.unparse(subject)
                if isinstance(op, (ast.Eq, ast.Is, ast.In)):
                    constants = _all_constants(other)
                    if isinstance(other, ast.Constant):
                        constants = [other.value]
                    if constants is not None:
                        hinted = bool(_FORMAT_NAME_HINT.search(name))
                        for constant in constants:
                            ext = _normalized(constant, dotted_only=not hinted)
                            if ext:
                                out.append(ext)
                        if constants:
                            break
                    if isinstance(other, ast.Attribute) and other.attr in members:
                        if _FORMAT_NAME_HINT.search(name):
                            out.extend(members[other.attr])
                            break
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "endswith"
            and node.args
        ):
            arg = node.args[0]
            literals = _all_constants(arg) or ([arg.value] if isinstance(arg, ast.Constant) else [])
            for literal in literals:
                ext = _normalized(literal, dotted_only=True)
                if ext:
                    out.append(ext)
    return sorted(set(out))


def _registrations(
    modules: dict[str, ast.Module], members: dict[str, list[str]]
) -> list[FormatDeclaration]:
    found: list[FormatDeclaration] = []
    for relative, tree in modules.items():
        if _skipped(relative):
            continue
        scopes: list[tuple[str | None, ast.AST]] = [(None, tree)] + [
            (node.name, node) for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        for class_name, scope in scopes:
            for function in scope.body:  # type: ignore[attr-defined]
                if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                direction = _direction_of(function.name, class_name, relative)
                if direction is None:
                    continue
                for branch in ast.walk(function):
                    if not isinstance(branch, ast.If) or not _is_real_code(branch.body):
                        continue
                    for extension in _test_extensions(branch.test, members):
                        found.append(
                            FormatDeclaration(
                                extension, direction, "registration", relative, branch.lineno,
                                f"{function.name}() dispatches {extension} to real "
                                f"{direction} code",
                            )
                        )
    return found


def dispatch_declarations(modules: dict[str, ast.Module]) -> list[FormatDeclaration]:
    """Declarations and registrations read from literal collections, extension maps, format-named
    functions and direction-named dispatch branches, in a stable order."""
    declarations, members = _declarations(modules)
    declared = {d.extension for d in declarations}
    # A dispatch branch on a literal that no declaration states is not a format at all (``fmt ==
    # "string"``, ``kind == "vec3"``): only dispatches on a DECLARED extension are kept.
    registrations = [r for r in _registrations(modules, members) if r.extension in declared]
    found = declarations + registrations
    unique = {(d.kind, d.direction or "", d.extension, d.source_path, d.line): d for d in found}
    return sorted(
        unique.values(),
        key=lambda d: (d.kind, d.direction or "", d.extension, d.source_path, d.line),
    )
