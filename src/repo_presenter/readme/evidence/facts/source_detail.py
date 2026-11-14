"""Source-detail facts: what the code states beyond the public symbol table (class-B audit kinds).

`docs/investigations/2026-11-06-unsupported-claim-class-audit.md`: 69 of 100 "real unsupported
claims" were TRUE, and missing only because the extractor kept the first sentence of a docstring
and a symbol-only view. Everything here is read mechanically from the source at the pinned
revision, with the path and line it came from; nothing is inferred from a name or guessed:

* ``public_symbol`` facts gain ``docstring_full`` (the whole doc comment, not its first sentence)
  and, for a type, ``declaration`` (the declaring line, so ``sealed``/``abstract``/``final`` are
  stated); an enum's fact gains ``members`` and ``member_count``;
* ``enum_member`` facts for the shapes the vendored engine misses: TypeScript, Go typed
  constants, Python ``Enum`` subclasses and constant-only classes;
* ``member_field``: dataclass/pydantic/attrs/NamedTuple/TypedDict fields, ``__slots__`` and
  ``self.x =`` attributes of a public Python class;
* ``module_export``: a TypeScript/JavaScript ``export`` the package entry point does not re-export
  (true of the module, never claimed to be public API);
* ``internal_symbol``: a non-public type or private module, with its own documentation and where
  it is constructed (a reader/writer registered in a dispatcher);
* ``implementation``: a public member whose body throws (``NotSupportedException``,
  ``NotImplementedError``...), stated as ``always`` only when the throw is the body's only
  statement; a member whose body returns one literal; a named literal constant;
* ``standard_reference``: a specification the source names (``ECMA-376``, ``RFC 5322``...).

Polarity is SUPPORTED: each fact restates the source. A claim the source contradicts is caught by
these facts the other way (a stub member's ``implementation`` fact says it always throws).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Sequence
from dataclasses import replace
from pathlib import Path, PurePosixPath

from repo_presenter.core.facts import Evidence, Fact, fact_id
from repo_presenter.readme.evidence.facts.source_text import (
    BRACE_LANGUAGES,
    body_span,
    is_test_path,
    language_of,
    leading_comment,
    line_at,
    line_offsets,
    product_sources,
    read_text,
    split_top_level,
    strip_comments,
)

DOC_CHARS = 4000
#: Caps per kind, so a very large repository's facts stay bounded.
CAPS = {
    "member_field": 6000,
    "module_export": 3000,
    "internal_symbol": 4000,
    "implementation": 6000,
    "standard_reference": 200,
}
_LINE = re.compile(r"\bline (\d+)\b")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_TYPE_KINDS = frozenset({"class", "enum", "unknown"})


def _declared_line(fact: Fact) -> tuple[str, int] | None:
    for evidence in fact.evidence:
        match = _LINE.search(evidence.detail or "")
        if match and int(match.group(1)) > 0 and language_of(evidence.path):
            return evidence.path, int(match.group(1))
    return None


def _slug_ok(kind: str, *parts: str) -> str | None:
    try:
        return fact_id(kind, *parts)  # type: ignore[arg-type]
    except ValueError:
        return None


class _Collector:
    """New facts, deduplicated by ID and capped per kind."""

    def __init__(self, taken: Iterable[str]) -> None:
        self.ids = set(taken)
        self.facts: list[Fact] = []
        self.counts: dict[str, int] = {}
        #: member -> "throws" | "none": whether a member whose own body was read throws anywhere
        #: in it (K02, 2026-11-13: "X throws" is checkable only when the body was read).
        self.bodies: dict[str, str] = {}

    def body(self, member: str, throws: bool) -> None:
        if throws or self.bodies.get(member) != "throws":
            self.bodies[member] = "throws" if throws else "none"

    def add(
        self,
        kind: str,
        parts: Sequence[str],
        value: str,
        path: str,
        line: int,
        detail: str,
        attributes: dict[str, str] | None = None,
    ) -> None:
        if not value.strip() or self.counts.get(kind, 0) >= CAPS.get(kind, 10_000):
            return
        identifier = _slug_ok(kind, *parts)
        if identifier is None or identifier in self.ids:
            return
        cleaned = {k: v for k, v in (attributes or {}).items() if k and v}
        self.ids.add(identifier)
        self.counts[kind] = self.counts.get(kind, 0) + 1
        self.facts.append(
            Fact(
                identifier,
                kind,  # type: ignore[arg-type]
                value,
                (Evidence(path, f"line {line}; {detail}"),),
                attributes=cleaned or None,
            )
        )


# --- Python -----------------------------------------------------------------------------------

_DATACLASS_DECORATORS = frozenset({"dataclass", "dataclasses.dataclass", "attr.s", "attrs", "define", "frozen", "attr.define", "attrs.define", "attrs.frozen", "mutable"})  # fmt: skip
_FIELD_BASES = frozenset({"BaseModel", "NamedTuple", "TypedDict", "Struct", "BaseSettings", "SQLModel"})  # fmt: skip
_ENUM_BASES = frozenset({"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag", "ReprEnum"})
_CONSTANT_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
_THROWS = re.compile(r"(?:NotImplemented|NotSupported|Unsupported|Invalid|OutOfRange|Argument|Error|Exception)")


def _python_tree(root: Path, path: str) -> ast.Module | None:
    text = read_text(root, path)
    if text is None:
        return None
    try:
        return ast.parse(text)
    except (SyntaxError, ValueError):
        return None


def _node_at(tree: ast.Module, line: int) -> ast.AST | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) and node.lineno == line:
            return node
    return None


def _decorator_names(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    names = []
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        names.append(ast.unparse(target))
    return names


def _literal(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str | int | float | bool | bytes):
        text = repr(node.value)
        return text if len(text) <= 120 else None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _literal(node.operand)
        return f"-{inner}" if inner else None
    return None


def _own_statements(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):  # type: ignore[attr-defined]
        body = body[1:]
    return body


def _raises(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[ast.Raise, str, str]]:
    """``(raise, exception name, first string argument)`` for each raise in the function's own
    body (nested functions and classes excluded)."""
    found = []
    stack: list[ast.AST] = list(node.body)
    while stack:
        current = stack.pop()
        if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
            continue
        if isinstance(current, ast.Raise) and current.exc is not None:
            exc = current.exc
            call = exc if isinstance(exc, ast.Call) else None
            name = ast.unparse(call.func if call else exc).rsplit(".", 1)[-1]
            message = ""
            if call and call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
                message = call.args[0].value
            if _IDENT.fullmatch(name):
                found.append((current, name, message))
        stack.extend(ast.iter_child_nodes(current))
    return found


def _accessor(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    for name in _decorator_names(node):
        if name == "property" or name.endswith("cached_property"):
            return "getter"
        if name.endswith(".setter"):
            return "setter"
        if name.endswith(".deleter"):
            return "deleter"
    return ""


def _python_members(
    out: _Collector, root: Path, owner: str, path: str, node: ast.ClassDef
) -> tuple[list[str], list[str]]:
    """Fields, constant members and member implementation facts of one public Python class.
    Returns (enum-like member names, field names)."""
    decorators = _decorator_names(node)
    bases = [ast.unparse(base).rsplit(".", 1)[-1] for base in node.bases]
    is_enum = any(base in _ENUM_BASES for base in bases)
    has_fields = any(d.rsplit("(", 1)[0] in _DATACLASS_DECORATORS for d in decorators) or any(
        base in _FIELD_BASES for base in bases
    )
    members: list[tuple[str, int, str | None]] = []
    fields: list[tuple[str, int, str, str]] = []
    others = 0
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    if target.id == "model_config":
                        continue
                    members.append((target.id, item.lineno, _literal(item.value)))
                elif isinstance(target, ast.Name) and target.id == "__slots__":
                    try:
                        slots = ast.literal_eval(item.value)
                    except (ValueError, TypeError, SyntaxError):
                        slots = ()
                    if isinstance(slots, str):
                        slots = (slots,)
                    for slot in slots if isinstance(slots, list | tuple) else ():
                        if isinstance(slot, str) and not slot.startswith("_"):
                            fields.append((slot, item.lineno, "", "__slots__"))
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            name = item.target.id
            if name.startswith("_") or "ClassVar" in ast.unparse(item.annotation):
                continue
            if is_enum:
                members.append((name, item.lineno, _literal(item.value)))
            elif has_fields:
                fields.append((name, item.lineno, ast.unparse(item.annotation), "field"))
        elif isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
            others += 1
            if item.name == "__init__":
                for sub in ast.walk(item):
                    targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target] if isinstance(sub, ast.AnnAssign) else []
                    for target in targets:
                        if (
                            isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"
                            and not target.attr.startswith("_")
                        ):
                            annotation = ast.unparse(sub.annotation) if isinstance(sub, ast.AnnAssign) else ""
                            fields.append(
                                (
                                    target.attr,
                                    getattr(sub, "lineno", item.lineno),
                                    annotation,
                                    "instance attribute set in __init__",
                                )
                            )
            _python_function(out, f"{owner}.{item.name}", path, item)
    enum_names: list[str] = []
    if is_enum or (members and all(_CONSTANT_NAME.match(name) for name, _, _ in members) and len(members) >= 2):
        how = "enum member" if is_enum else "class-level constant"
        for name, line, literal in members:
            if not (is_enum or _CONSTANT_NAME.match(name)):
                continue
            enum_names.append(name)
            out.add(
                "enum_member",
                [f"{owner}.{name}"],
                f"{owner}.{name}",
                path,
                line,
                f"{how} of {owner}",
                {"enum": owner, "member_kind": "enum" if is_enum else "class_constant", "literal": literal or ""},
            )
    field_names: list[str] = []
    seen: set[str] = set()
    for name, line, annotation, how in fields:
        if name in seen:
            continue
        seen.add(name)
        field_names.append(name)
        out.add(
            "member_field",
            [f"{owner}.{name}"],
            f"{owner}.{name}",
            path,
            line,
            f"{how} of {owner}",
            {"owner": owner, "type": annotation, "field_source": how},
        )
    return enum_names, field_names


def _python_function(
    out: _Collector, member: str, path: str, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> None:
    name = member.rsplit(".", 1)[-1]
    if name.startswith("_") and name != "__init__":
        return
    accessor = _accessor(node)
    statements = _own_statements(node)
    raises = _raises(node)
    if statements and not all(isinstance(s, ast.Pass) or (isinstance(s, ast.Expr) and isinstance(getattr(s, "value", None), ast.Constant)) for s in statements):
        out.body(member, bool(raises))
    for raise_node, exception, message in raises:
        always = len(statements) == 1 and statements[0] is raise_node
        label = f"{member}{' ' + accessor if accessor else ''}"
        out.add(
            "implementation",
            ["throws", member, accessor or "body", exception],
            f"{label} raises {exception}" + ("" if always else " (conditionally)"),
            path,
            raise_node.lineno,
            "raise statement in the member's own body",
            {"aspect": "throws", "member": member, "accessor": accessor, "exception": exception, "condition": "always" if always else "conditional", "message": message[:300]},
        )
    if len(statements) == 1 and isinstance(statements[0], ast.Return):
        literal = _literal(statements[0].value)
        if literal is not None:
            label = f"{member}{' ' + accessor if accessor else ''}"
            out.add(
                "implementation",
                ["returns", member, accessor or "body"],
                f"{label} always returns {literal}",
                path,
                statements[0].lineno,
                "the member's only statement returns a literal",
                {"aspect": "constant_return", "member": member, "accessor": accessor, "returns": literal},
            )


def _python_module_detail(
    out: _Collector,
    root: Path,
    path: str,
    module: str,
    tree: ast.Module,
    public: bool,
    public_names: set[str],
) -> None:
    """Module constants, and the docstrings of a private module and its classes."""
    for item in tree.body:
        if isinstance(item, ast.Assign | ast.AnnAssign):
            targets = item.targets if isinstance(item, ast.Assign) else [item.target]
            literal = _literal(item.value)
            for target in targets:
                if isinstance(target, ast.Name) and _CONSTANT_NAME.match(target.id.lstrip("_")) and literal is not None:
                    out.add(
                        "implementation",
                        ["constant", module, target.id],
                        f"{target.id} = {literal}",
                        path,
                        item.lineno,
                        f"module-level constant of {module}",
                        {"aspect": "constant", "owner": module, "name": target.id, "literal": literal},
                    )
    if public:
        return
    doc = ast.get_docstring(tree, clean=True)
    if doc:
        out.add(
            "internal_symbol",
            [module],
            module,
            path,
            1,
            "private module docstring",
            {"symbol_kind": "module", "visibility": "private", "docstring_full": " ".join(doc.split())[:DOC_CHARS]},
        )
    for item in tree.body:
        # A definition a public path re-exports is public, and is read as a public symbol.
        if isinstance(item, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) and item.name not in public_names:
            doc = ast.get_docstring(item, clean=True)
            qualified = f"{module}.{item.name}"
            attributes = {"symbol_kind": "class" if isinstance(item, ast.ClassDef) else "function", "visibility": "private"}
            if doc:
                attributes["docstring_full"] = " ".join(doc.split())[:DOC_CHARS]
            out.add("internal_symbol", [qualified], qualified, path, item.lineno, "definition in a private module", attributes)
            if isinstance(item, ast.ClassDef):
                _python_members(out, root, qualified, path, item)
            else:
                _python_function(out, qualified, path, item)


def _module_of(path: str, package_roots: Sequence[str]) -> str:
    pure = PurePosixPath(path)
    for root in package_roots:
        if path.startswith(root.rstrip("/") + "/"):
            relative = pure.relative_to(PurePosixPath(root).parent)
            parts = relative.with_suffix("").parts
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            return ".".join(parts)
    parts = pure.with_suffix("").parts
    return ".".join(p for p in parts if p not in ("src", "__init__"))


_REEXPORT = re.compile(r"re-export of ([\w.]+)")


def _reexported_definition(
    root: Path, tree_paths: Sequence[str], fact: Fact, trees: dict[str, ast.Module | None]
) -> tuple[str, ast.AST] | None:
    for evidence in fact.evidence:
        match = _REEXPORT.search(evidence.detail or "")
        if match is None:
            continue
        module, _, name = match.group(1).rpartition(".")
        suffixes = (module.replace(".", "/") + ".py", module.replace(".", "/") + "/__init__.py")
        for path in tree_paths:
            if not path.endswith(suffixes):
                continue
            tree = trees.setdefault(path, _python_tree(root, path))
            for item in tree.body if tree is not None else ():
                if isinstance(item, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) and item.name == name:
                    return path, item
    return None


_PROPERTY_DECORATORS = frozenset({"property", "cached_property", "functools.cached_property", "abstractproperty"})
#: Bases that add no member a README counts as the class's own.
_ROOT_BASES = frozenset({"object", "BaseModel", "NamedTuple", "TypedDict", "Generic", "ABC", "Protocol", "Struct", "BaseSettings"})


def python_member_counts(node: ast.ClassDef, field_names: Sequence[str]) -> str:
    """``"method=N,dunder=N,init=N,property=N,field=N,inherits=0|1"`` for one Python class's own body (BL-098):
    public methods, dunder methods other than ``__init__``, whether it defines ``__init__``,
    ``@property``-like members, and the
    fields ``_python_members`` reads (dataclass/pydantic/attrs fields, ``__slots__``, ``self.x`` set
    in ``__init__``), and whether a non-root base may add members. Inherited members are not counted. What a "Class with N properties." cell is
    held to (``type_description.true_count_cell``)."""
    methods = dunders = init = properties = 0
    seen: set[str] = set()
    for item in node.body:
        if not isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) or item.name in seen:
            continue
        seen.add(item.name)
        if item.name == "__init__":
            init = 1
        elif item.name.startswith("__") and item.name.endswith("__"):
            dunders += 1
        elif item.name.startswith("_"):
            continue
        elif any(name in _PROPERTY_DECORATORS for name in _decorator_names(item)):
            properties += 1
        else:
            methods += 1
    fields = len([name for name in dict.fromkeys(field_names) if name not in seen])
    # whether a base may add members a maintainer's count includes (anything but a root base)
    inherits = int(any(
        ast.unparse(base).rsplit(".", 1)[-1].split("[", 1)[0] not in _ROOT_BASES for base in node.bases
    ))
    return f"method={methods},dunder={dunders},init={init},property={properties},field={fields},inherits={inherits}"


def class_member_counts_from_source(text: str, owner: str, path: str, line: int) -> str | None:
    """``python_member_counts`` of the class declared at ``line`` of ``text`` (None when there is none)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    node = _node_at(tree, line)
    if not isinstance(node, ast.ClassDef):
        return None
    _enum, fields = _python_members(_Collector(()), Path("."), owner, path, node)
    return python_member_counts(node, fields)


def _python_detail(out: _Collector, root: Path, tree_paths: Sequence[str], symbols: list[Fact]) -> dict[str, dict[str, str]]:
    """Per public symbol id, the attributes to add; and every Python detail fact."""
    updates: dict[str, dict[str, str]] = {}
    trees: dict[str, ast.Module | None] = {}
    public_files: set[str] = set()
    public_last = {fact.value.rsplit(".", 1)[-1] for fact in symbols}
    for fact in symbols:
        located = _declared_line(fact)
        if located is None or not located[0].endswith(".py") or is_test_path(located[0]):
            continue
        path, line = located
        public_files.add(path)
        tree = trees.setdefault(path, _python_tree(root, path))
        if tree is None:
            continue
        kind = (fact.attributes or {}).get("symbol_kind", "")
        node = tree if kind == "module" and line == 1 else _node_at(tree, line)
        if node is None:
            # A re-export whose definition sits in a module the surface does not scan (a private
            # module): its evidence names the origin, and the definition is read there.
            definition = _reexported_definition(root, tree_paths, fact, trees)
            if definition is None:
                continue
            path, node = definition
        doc = ast.get_docstring(node, clean=True)  # type: ignore[arg-type]
        extra: dict[str, str] = {}
        if doc:
            full = " ".join(doc.split())[:DOC_CHARS]
            if full != (fact.attributes or {}).get("docstring", ""):
                extra["docstring_full"] = full
        if isinstance(node, ast.ClassDef) and kind in ("class", "enum"):
            enum_names, field_names = _python_members(out, root, fact.value, path, node)
            if enum_names:
                extra["members"] = ", ".join(enum_names)
                extra["member_count"] = str(len(enum_names))
            if field_names:
                extra["fields"] = ", ".join(field_names)
            if kind == "class" and not enum_names:
                extra["member_counts"] = python_member_counts(node, field_names)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and kind == "function":
            # A method is read with its class (every accessor of a property included).
            _python_function(out, fact.value, path, node)
        if extra:
            updates[fact.id] = extra
    # Classes are walked whole above (members included); module-level detail for every module.
    roots = sorted({p.rsplit("/", 1)[0] for p in public_files if p.endswith("__init__.py")}, key=len)
    for path in product_sources(tree_paths):
        if not path.endswith(".py"):
            continue
        tree = trees.setdefault(path, _python_tree(root, path))
        if tree is None:
            continue
        module = _module_of(path, roots)
        private = any(part.startswith("_") and part != "__init__" for part in module.split("."))
        _python_module_detail(
            out, root, path, module, tree, public=not private, public_names=public_last
        )
    return updates


# --- brace languages --------------------------------------------------------------------------

_ENUM_DECL = re.compile(r"\benum\b(?:\s+(?:class|struct))?\s+(\w+)")
_TYPE_DECL = {
    "csharp": re.compile(r"^\s*(?:\[[^\]]*\]\s*)*((?:(?:public|internal|private|protected|sealed|static|abstract|partial|readonly|unsafe|file|ref|new)\s+)*)(class|struct|interface|enum|record(?:\s+struct|\s+class)?)\s+(\w+)", re.MULTILINE),
    "java": re.compile(r"^\s*((?:(?:public|protected|private|abstract|final|static|sealed|non-sealed|strictfp)\s+)*)(class|interface|enum|record|@interface)\s+(\w+)", re.MULTILINE),
    "typescript": re.compile(r"^\s*((?:(?:export|default|declare|abstract)\s+)*)(class|interface|enum|type|function|const|let)\s+(\w+)", re.MULTILINE),
    "javascript": re.compile(r"^\s*((?:(?:export|default)\s+)*)(class|function|const|let)\s+(\w+)", re.MULTILINE),
    "rust": re.compile(r"^\s*((?:pub(?:\([^)]*\))?\s+)?)(struct|enum|trait|union|type)\s+(\w+)", re.MULTILINE),
    "go": re.compile(r"^\s*()type\s+(?:\(\s*)?()(\w+)\s+(?:struct|interface|\w)", re.MULTILINE),
    "cpp": re.compile(r"^\s*()(class|struct|enum\s+class|enum\s+struct|enum)\s+(?:\w+_EXPORT\s+|\[\[[^\]]*\]\]\s*)?(\w+)\s*(?:final\s*)?[:{]", re.MULTILINE),
}
_THROW = {
    "csharp": re.compile(r"\bthrow\s+new\s+([A-Z]\w*)\s*\((?:[^;]*?\"([^\"]*)\")?"),
    "java": re.compile(r"\bthrow\s+new\s+([A-Z]\w*)\s*\((?:[^;]*?\"([^\"]*)\")?"),
    "typescript": re.compile(r"\bthrow\s+new\s+([A-Z]\w*)\s*\((?:[^;]*?[\"'`]([^\"'`]*)[\"'`])?"),
    "javascript": re.compile(r"\bthrow\s+new\s+([A-Z]\w*)\s*\((?:[^;]*?[\"'`]([^\"'`]*)[\"'`])?"),
    "cpp": re.compile(r"\bthrow\s+(?:std::)?([A-Za-z_][\w:]*)\s*[({](?:[^;]*?\"([^\"]*)\")?"),
    "rust": re.compile(r"\b(unimplemented|todo)!\s*\((?:\s*\"([^\"]*)\")?"),
    "go": re.compile(r"\b(errors\.New|fmt\.Errorf)\s*\(\s*\"([^\"]*not (?:implemented|supported)[^\"]*)\"", re.IGNORECASE),
}
_LITERAL = re.compile(r"""^(?:-?\d+(?:\.\d+)?[fFdDmMlLuU]*|true|false|null|None|nil|"[^"\n]{0,100}"|'[^'\n]{0,100}')$""")
_CONST = {
    "csharp": re.compile(r"^\s*(?:(?:public|internal|private|protected|static|new)\s+)*const\s+[\w.<>?]+\s+(\w+)\s*=\s*([^;]+);", re.MULTILINE),
    "java": re.compile(r"^\s*(?:(?:public|private|protected)\s+)?(?:static\s+final|final\s+static)\s+[\w.<>\[\]]+\s+([A-Z][A-Z0-9_]*)\s*=\s*([^;]+);", re.MULTILINE),
    "typescript": re.compile(r"^\s*(?:export\s+)?(?:const|(?:(?:public|private|protected)\s+)?static\s+readonly)\s+([A-Z][A-Z0-9_]*)\s*(?::\s*[\w.<>\[\]|]+)?\s*=\s*([^;\n]+);?", re.MULTILINE),
    "javascript": re.compile(r"^\s*(?:export\s+)?const\s+([A-Z][A-Z0-9_]*)\s*=\s*([^;\n]+);?", re.MULTILINE),
    "rust": re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?const\s+([A-Z][A-Z0-9_]*)\s*:\s*[^=]+=\s*([^;]+);", re.MULTILINE),
    "go": re.compile(r"^\s*(?:const\s+)?([A-Za-z]\w*)\s+(?:\w+\s+)?=\s*([^\n/]+?)\s*(?://.*)?$", re.MULTILINE),
    "cpp": re.compile(r"^\s*(?:static\s+|inline\s+)*constexpr\s+[\w:<>]+\s+(\w+)\s*=\s*([^;]+);", re.MULTILINE),
}


def _enum_members_at(text: str, offset: int, language: str) -> list[tuple[str, int]]:
    """Member names of the enum whose declaration starts at ``offset``, with their offsets."""
    span = body_span(text, offset, language)
    if span is None or text[span[0]] != "{":
        return []
    first, last = span
    body = strip_comments(text[first + 1 : last], language)
    if language == "java":
        cut = next((i for i, char in enumerate(body) if char == ";" and _depth_zero(body, i)), None)
        if cut is not None:
            body = body[:cut]
    names: list[tuple[str, int]] = []
    for start, piece in split_top_level(body, ","):
        stripped = piece
        lead = len(stripped) - len(stripped.lstrip())
        stripped = stripped.lstrip()
        # Attributes and annotations ahead of a member.
        while True:
            match = re.match(r"(?:#\[[^\]]*\]|\[[^\]]*\]|@\w+(?:\([^)]*\))?)\s*", stripped)
            if not match:
                break
            lead += match.end()
            stripped = stripped[match.end() :]
        name = re.match(r"[A-Za-z_]\w*", stripped)
        if name is None:
            continue
        if language == "rust" and re.match(r"\s*:", stripped[name.end() :]):
            continue  # a struct field, not a variant
        names.append((name.group(0), first + 1 + start + lead))
    return names


def _depth_zero(text: str, index: int) -> bool:
    depth = 0
    for char in text[:index]:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
    return depth == 0


def _go_typed_constants(text: str) -> dict[str, list[tuple[str, int]]]:
    """``type -> [(constant, offset)]`` for the constants a ``const (...)`` block declares with a
    named type (a bare continuation line repeats the previous type, as Go's own rule does)."""
    found: dict[str, list[tuple[str, int]]] = {}
    for block in re.finditer(r"^const\s*\(\s*\n(.*?)^\)", text, re.MULTILINE | re.DOTALL):
        current = ""
        for line in re.finditer(r"^[ \t]*([A-Za-z_]\w*)(?:[ \t]+([A-Za-z_][\w.]*))?[ \t]*(=.*)?$", block.group(1), re.MULTILINE):
            name, typ, assign = line.group(1), line.group(2), line.group(3)
            if typ and assign or typ and not assign:
                current = typ
            elif assign and not typ:
                current = ""
            if current:
                found.setdefault(current, []).append((name, block.start(1) + line.start(1)))
    return found


def _brace_detail(out: _Collector, root: Path, tree_paths: Sequence[str], symbols: list[Fact], existing_members: set[str]) -> dict[str, dict[str, str]]:
    updates: dict[str, dict[str, str]] = {}
    by_file: dict[str, list[tuple[int, Fact]]] = {}
    for fact in symbols:
        located = _declared_line(fact)
        if located is None or is_test_path(located[0]):
            continue
        path, line = located
        language = language_of(path)
        if language not in BRACE_LANGUAGES:
            continue
        by_file.setdefault(path, []).append((line, fact))
    for path, entries in by_file.items():
        text = read_text(root, path)
        if text is None:
            continue
        language = language_of(path) or ""
        lines = text.splitlines()
        offsets = line_offsets(text)
        go_constants = _go_typed_constants(text) if language == "go" else {}
        for line, fact in entries:
            if line > len(lines):
                continue
            extra: dict[str, str] = {}
            doc, _ = leading_comment(lines, line - 1, language)
            current = (fact.attributes or {}).get("docstring", "")
            if doc and doc[:DOC_CHARS] != current and len(doc) > len(current):
                extra["docstring_full"] = doc[:DOC_CHARS]
            kind = (fact.attributes or {}).get("symbol_kind", "")
            offset = offsets[line - 1]
            if kind in _TYPE_KINDS:
                declaration = lines[line - 1].strip()
                if declaration and len(declaration) <= 240:
                    extra["declaration"] = declaration.rstrip("{").strip()
                names: list[tuple[str, int]] = []
                if _ENUM_DECL.search(lines[line - 1]) or kind == "enum":
                    names = _enum_members_at(text, offset, language)
                elif language == "go":
                    names = go_constants.get(fact.value.rsplit(".", 1)[-1], [])
                for name, position in names:
                    value = f"{fact.value}.{name}"
                    if value in existing_members:
                        continue
                    out.add(
                        "enum_member",
                        [value],
                        value,
                        path,
                        line_at(offsets, position),
                        f"member of enum {fact.value}",
                        {"enum": fact.value},
                    )
                if names:
                    extra["members"] = ", ".join(name for name, _ in names)
                    extra["member_count"] = str(len(names))
            elif kind in ("method", "function"):
                _brace_member(out, text, offsets, offset, path, language, fact.value)
            if extra:
                updates[fact.id] = extra
    return updates


def _brace_member(out: _Collector, text: str, offsets: Sequence[int], offset: int, path: str, language: str, member: str) -> None:
    span = body_span(text, offset, language)
    if span is None:
        return
    first, last = span
    body = strip_comments(text[first : last + 1], language)
    pattern = _THROW.get(language)
    inner = body.strip()
    inner = inner[2:].strip() if inner.startswith("=>") else inner.strip("{}").strip()
    name = member.rsplit(".", 1)[-1]
    if pattern is not None and inner and re.search(rf"\b{re.escape(name)}\s*(?:<[^>]*>)?\s*\(", text[offset:first]):
        # A method whose own body was read (a signature, then the body): whether it throws at all.
        out.body(member, bool(pattern.search(body)))
    if pattern is not None:
        for match in pattern.finditer(body):
            exception = match.group(1).rsplit("::", 1)[-1].rsplit(".", 1)[-1]
            if language in ("rust", "go"):
                exception = {"unimplemented": "unimplemented!", "todo": "todo!"}.get(exception, "error")
            message = match.group(2) or ""
            accessor = ""
            if language == "csharp":
                before = body[: match.start()]
                found = list(re.finditer(r"\b(get|set|init)\s*(?:=>|\{)", before))
                if found:
                    accessor = {"get": "getter", "set": "setter", "init": "init"}[found[-1].group(1)]
            if accessor:
                lead = re.split(r"\b(?:get|set|init)\s*(?:=>|\{)", body[: match.start()])[-1]
            else:
                lead = body[: match.start()].lstrip().removeprefix("=>").lstrip().removeprefix("{")
            # Unconditional only when the throw is the first thing the (accessor) body does.
            always = not lead.strip() and language not in ("go",)
            label = f"{member}{' ' + accessor if accessor else ''}"
            verb = "returns an error" if language == "go" else "panics" if language == "rust" else "throws"
            out.add(
                "implementation",
                ["throws", member, accessor or "body", exception],
                f"{label} {verb} {exception if language not in ('go',) else repr(message)}" + ("" if always else " (conditionally)"),
                path,
                line_at(offsets, first + match.start()),
                "throw in the member's own body",
                {"aspect": "throws", "member": member, "accessor": accessor, "exception": exception, "condition": "always" if always else "conditional", "message": message[:300]},
            )
    single = re.fullmatch(r"(?:return\s+)?(.+?);?", inner, re.DOTALL)
    if single and ";" not in single.group(1) and "\n" not in single.group(1).strip():
        expression = single.group(1).strip()
        if _LITERAL.match(expression) and (inner.startswith("return") or body.strip().startswith("=>")):
            out.add(
                "implementation",
                ["returns", member, "body"],
                f"{member} always returns {expression}",
                path,
                line_at(offsets, first),
                "the member's only statement returns a literal",
                {"aspect": "constant_return", "member": member, "returns": expression},
            )
    if language == "csharp":
        for accessor, expression in re.findall(r"\b(get)\s*=>\s*([^;]+);", body):
            if _LITERAL.match(expression.strip()):
                out.add(
                    "implementation",
                    ["returns", member, "getter"],
                    f"{member} getter always returns {expression.strip()}",
                    path,
                    line_at(offsets, first),
                    "the getter's only expression is a literal",
                    {"aspect": "constant_return", "member": member, "accessor": "getter", "returns": expression.strip()},
                )


_TYPE_WORDS = frozenset({"class", "struct", "interface", "enum", "record", "trait", "union", "type"})
_INTERNAL = {
    "csharp": lambda modifiers: "public" not in modifiers and "protected" not in modifiers,
    "java": lambda modifiers: "public" not in modifiers and "protected" not in modifiers,
    "typescript": lambda modifiers: "export" not in modifiers,
    "javascript": lambda modifiers: "export" not in modifiers,
    "rust": lambda modifiers: modifiers.strip() != "pub",
    "go": lambda _modifiers: True,
    "cpp": lambda _modifiers: True,
}


def _internal_and_exports(out: _Collector, root: Path, tree_paths: Sequence[str], symbols: list[Fact]) -> None:
    """Non-public types (with their documentation and where they are constructed), TypeScript
    exports the entry point does not re-export, named literal constants, and the members of
    every non-public type's own body that throw."""
    public_last = {fact.value.rsplit(".", 1)[-1] for fact in symbols}
    sources = [p for p in product_sources(tree_paths) if language_of(p) in BRACE_LANGUAGES]
    internal: list[tuple[str, str, int]] = []
    texts: dict[str, str] = {}
    for path in sources:
        text = read_text(root, path)
        if text is None:
            continue
        texts[path] = text
        language = language_of(path) or ""
        lines = text.splitlines()
        offsets = line_offsets(text)
        pattern = _TYPE_DECL.get(language)
        for match in pattern.finditer(text) if pattern else ():
            modifiers, what, name = match.group(1) or "", match.group(2) or "type", match.group(3)
            line = line_at(offsets, match.start(3))
            if language == "go":
                if name[:1].isupper():
                    continue
            elif language == "cpp":
                continue  # a C++ header's visibility is not stated per type
            elif not _INTERNAL[language](modifiers):
                if language in ("typescript", "javascript") and name not in public_last and what in ("class", "interface", "enum", "type", "function"):
                    members = ""
                    if what in ("interface", "class"):
                        span = body_span(text, match.start(3), language)
                        if span is not None and text[span[0]] == "{":
                            body = strip_comments(text[span[0] + 1 : span[1]], language)
                            props = [p for _, p in split_top_level(body, ";\n") if re.match(r"\s*(?:readonly\s+)?[A-Za-z_$][\w$]*\??\s*:", p)]
                            if props:
                                members = f"{what} with {len(props)} {'property' if len(props) == 1 else 'properties'}"
                    doc, _ = leading_comment(lines, line - 1, language)
                    out.add(
                        "module_export",
                        [PurePosixPath(path).with_suffix("").as_posix(), name],
                        name,
                        path,
                        line,
                        f"exported {what} not re-exported by the package entry point",
                        {"module": path, "declaration_kind": what, "reexported": "no", "shape": members, "docstring_full": doc[:DOC_CHARS]},
                    )
                continue
            if what.split()[0] not in _TYPE_WORDS or (name in public_last and language != "go"):
                continue
            doc, _ = leading_comment(lines, line - 1, language)
            internal.append((name, path, line))
            _internal_throws(out, text, offsets, match.start(3), path, language, name)
            out.add(
                "internal_symbol",
                [PurePosixPath(path).with_suffix("").as_posix(), name],
                name,
                path,
                line,
                f"non-public {what.split()[0]} declaration",
                {"symbol_kind": what.split()[0], "visibility": "internal", "declaration": lines[line - 1].strip()[:240], "docstring_full": doc[:DOC_CHARS]},
            )
        _constants(out, text, offsets, path, language)
    # Where each internal type is constructed (a reader or writer registered in a dispatcher).
    if internal:
        names = {name for name, _, _ in internal}
        constructed: dict[str, list[str]] = {}
        construction = re.compile(r"\bnew\s+(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")\s*[(<{]")
        for path, text in texts.items():
            offsets = line_offsets(text)
            for match in construction.finditer(text):
                where = constructed.setdefault(match.group(1), [])
                if len(where) < 5:
                    where.append(f"{path}:{line_at(offsets, match.start())}")
        if constructed:
            updated = []
            for fact in out.facts:
                where = constructed.get(fact.value, []) if fact.kind == "internal_symbol" else []
                if where:
                    # Each construction site is evidence too: a reader or writer registered in a
                    # dispatcher is proved by the line that constructs it.
                    sites = tuple(
                        Evidence(site.rsplit(":", 1)[0], f"line {site.rsplit(':', 1)[1]}; constructs {fact.value}")
                        for site in where
                    )
                    fact = replace(
                        fact,
                        evidence=(*fact.evidence, *sites),
                        attributes={**(fact.attributes or {}), "constructed_at": ", ".join(where)},
                    )
                updated.append(fact)
            out.facts[:] = updated


_MEMBER_DECL = re.compile(
    r"(?:^|\n)[ \t]*(?:(?:public|internal|private|protected|override|static|virtual|sealed|async"
    r"|final|abstract|synchronized|pub(?:\([^)]*\))?|fn)\s+)+[\w<>\[\],.?: ]*?\b(\w+)\s*\("
)


def _internal_throws(
    out: _Collector,
    text: str,
    offsets: Sequence[int],
    start: int,
    path: str,
    language: str,
    owner: str,
) -> None:
    """Each throw in a non-public type's own body, named by the member declared before it."""
    span = body_span(text, start, language)
    pattern = _THROW.get(language)
    if span is None or pattern is None or text[span[0]] != "{":
        return
    body = strip_comments(text[span[0] : span[1] + 1], language)
    members = [(m.start(1), m.group(1)) for m in _MEMBER_DECL.finditer(body)]
    for match in pattern.finditer(body):
        before = [name for position, name in members if position < match.start()]
        if not before or before[-1] in ("if", "for", "while", "switch", "catch", "using", "lock"):
            continue
        member = f"{owner}.{before[-1]}"
        exception = match.group(1).rsplit("::", 1)[-1].rsplit(".", 1)[-1]
        if language in ("rust", "go"):
            exception = {"unimplemented": "unimplemented!", "todo": "todo!"}.get(exception, "error")
        out.add(
            "implementation",
            ["throws", path, member, exception],
            f"{member} throws {exception} (non-public type)",
            path,
            line_at(offsets, span[0] + match.start()),
            "throw in a non-public type's member",
            {
                "aspect": "throws",
                "member": member,
                "exception": exception,
                "visibility": "internal",
                "message": (match.group(2) or "")[:300],
            },
        )


def _constants(out: _Collector, text: str, offsets: Sequence[int], path: str, language: str) -> None:
    pattern = _CONST.get(language)
    if pattern is None:
        return
    if language == "go":
        # Only inside const blocks or `const X = ...` lines.
        regions = [m.span(1) for m in re.finditer(r"^const\s*\(\s*\n(.*?)^\)", text, re.MULTILINE | re.DOTALL)]
        regions += [m.span() for m in re.finditer(r"^const\s+\w+.*$", text, re.MULTILINE)]
    else:
        regions = [(0, len(text))]
    for begin, end in regions:
        for match in pattern.finditer(text, begin, end):
            name, value = match.group(1), match.group(2).strip()
            if not _LITERAL.match(value):
                continue
            out.add(
                "implementation",
                ["constant", PurePosixPath(path).with_suffix("").as_posix(), name],
                f"{name} = {value}",
                path,
                line_at(offsets, match.start(1)),
                "named literal constant",
                {"aspect": "constant", "name": name, "literal": value},
            )


# --- behaviour through the real code path (K02, 2026-11-13) -----------------------------------
#
# docs/investigations/2026-11-13-lane-r-false-claim-review.md, class K02: a fact restated what a
# member's own body does, never what the code path a caller takes does. Two shapes are read here:
# an exception type no library code ever throws or constructs (Cells C++ ``FormulaException`` /
# ``StyleException``: constructors only; 3D Python ``TrialException``: a commercial doc comment),
# and a public static instance built as a type whose virtual member only throws (3D .NET
# ``FileFormat.WavefrontOBJ = new FileFormat(...)``, whose ``CreateSaveOptions`` is the base
# virtual that throws NotImplementedException).

_EXCEPTION_TYPE = re.compile(r"(?:Exception|Error)$")
_NEVER_THROWN_LANGUAGES = frozenset({"python", "csharp", "java", "cpp", "typescript", "javascript"})
_STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\\n])*"' + r"|'(?:\\.|[^'\\\n])*'")
_NOT_A_USE_LINE = re.compile(r"^\s*(?:#\s*include|import\b|using\b|package\b|export\s*(?:\{|\*)|from\b)")
_BASE_LIST = re.compile(r"\b(?:class|struct|record|interface)\s+(\w+)\b[^{;]*?(?::|\bextends\b|\bimplements\b)([^{;]*)\{")


def _python_uses(tree: ast.Module, names: set[str]) -> tuple[set[str], dict[str, set[str]]]:
    """Exception names a module uses outside their own class body and outside imports, and the
    base-class edges (``class D(X)`` -> ``{X: {D}}``) it declares."""
    used: set[str] = set()
    derived: dict[str, set[str]] = {}

    def visit(node: ast.AST, inside: str | None) -> None:
        if isinstance(node, ast.Import | ast.ImportFrom):
            return
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = ast.unparse(base).rsplit(".", 1)[-1]
                if base_name in names:
                    derived.setdefault(base_name, set()).add(node.name)
            for child in [*node.decorator_list, *node.keywords, *node.body]:
                visit(child, node.name)
            return
        if isinstance(node, ast.Name) and node.id in names and node.id != inside:
            used.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in names and node.attr != inside:
            used.add(node.attr)
        for child in ast.iter_child_nodes(node):
            visit(child, inside)

    visit(tree, None)
    return used, derived


def _brace_uses(text: str, language: str, names: set[str], stem: str = "") -> tuple[set[str], dict[str, set[str]]]:
    """Exception names a brace-language file uses: any mention that is not an include/import
    line, the type's own declaration or body, an out-of-line definition of its members
    (``X::X(``), or a base list (``class D : public X``, recorded as an edge instead)."""
    cleaned = _STRING_LITERAL.sub(lambda m: " " * len(m.group(0)), strip_comments(text, language))
    used: set[str] = set()
    derived: dict[str, set[str]] = {}
    bases: list[tuple[int, int]] = []
    for match in _BASE_LIST.finditer(cleaned):
        bases.append(match.span(2))
        for base in _IDENT.findall(match.group(2)):
            if base in names:
                derived.setdefault(base, set()).add(match.group(1))
    own: list[tuple[int, int]] = []
    pattern = re.compile(r"\b(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")\b")
    for match in re.finditer(r"\b(?:class|struct|interface|record)\s+(\w+)", cleaned):
        if match.group(1) in names:
            span = body_span(cleaned, match.end(), language)
            own.append((match.start(), span[1] if span else match.end()))
    offsets = line_offsets(cleaned)
    for match in pattern.finditer(cleaned):
        position = match.start()
        if any(begin <= position < end for begin, end in own) or any(begin <= position < end for begin, end in bases):
            continue
        line = line_at(offsets, position)
        start = offsets[line - 1]
        end = offsets[line] if line < len(offsets) else len(cleaned)
        if _NOT_A_USE_LINE.match(cleaned[start:end]):
            continue
        name = match.group(1)
        qualified_by = cleaned[max(0, position - len(name) - 2) : position]
        if qualified_by == f"{name}::" or cleaned[max(0, position - 1) : position] == "~":
            continue  # ``X::X(...)``, ``X::~X()``: the type's own constructor/destructor defined
        if cleaned.startswith("::", match.end()) and stem == name:
            continue  # ``X::member(...)`` defined out of line in X's own source file
        used.add(name)
    return used, derived


def _never_thrown(out: _Collector, root: Path, tree_paths: Sequence[str], symbols: list[Fact]) -> None:
    """An ``implementation`` fact for each public exception type no product source throws,
    constructs or otherwise uses (directly, or through a type derived from it): it is declared
    and nothing more, so "throws ``X``" describes no code path."""
    exceptions: dict[str, Fact] = {}
    for fact in symbols:
        kind = (fact.attributes or {}).get("symbol_kind", "")
        name = fact.value.rsplit(".", 1)[-1].rsplit("::", 1)[-1]
        located = _declared_line(fact)
        if kind not in _TYPE_KINDS or not _EXCEPTION_TYPE.search(name) or located is None:
            continue
        if language_of(located[0]) not in _NEVER_THROWN_LANGUAGES:
            continue
        if name in exceptions:
            exceptions[name] = None  # type: ignore[assignment]  # two public types, one name: undecidable
            continue
        exceptions[name] = fact
    names = {name for name, fact in exceptions.items() if fact is not None}
    if not names:
        return
    sources = [
        path for path in product_sources(tree_paths) if (language_of(path) or "") in _NEVER_THROWN_LANGUAGES
    ]
    tracked = set(names)
    used: set[str] = set()
    derived: dict[str, set[str]] = {}
    # A type derived from a tracked one is tracked too (it is thrown as its base), to a fixpoint.
    for _ in range(4):
        used, derived = set(), {}
        for path in sources:
            text = read_text(root, path)
            if text is None or not any(name in text for name in tracked):
                continue
            language = language_of(path) or ""
            if language == "python":
                try:
                    tree = ast.parse(text)
                except (SyntaxError, ValueError):
                    return  # a file that does not parse could hold the throw: decide nothing
                file_used, file_derived = _python_uses(tree, tracked)
            else:
                file_used, file_derived = _brace_uses(text, language, tracked, PurePosixPath(path).stem)
            used |= file_used
            for base, subs in file_derived.items():
                derived.setdefault(base, set()).update(subs)
        grown = tracked | {sub for subs in derived.values() for sub in subs}
        if grown == tracked:
            break
        tracked = grown
    else:
        return  # the hierarchy did not settle: decide nothing

    def thrown(name: str, seen: frozenset[str] = frozenset()) -> bool:
        if name in used:
            return True
        return any(sub not in seen and thrown(sub, seen | {name}) for sub in derived.get(name, ()))

    for name in sorted(names):
        if thrown(name):
            continue
        fact = exceptions[name]
        path, line = _declared_line(fact)  # type: ignore[misc]
        out.add(
            "implementation",
            ["never_thrown", fact.value],
            f"{fact.value} is never thrown or constructed by the library's own code (declared only)",
            path,
            line,
            "no product source throws, constructs or uses the type outside its own declaration",
            {"aspect": "never_thrown", "member": fact.value, "type": name},
        )


_STATIC_INSTANCE = re.compile(
    r"\bstatic\b[^=;(]*?\b[\w.]+(?:<[^>]*>)?\s+(?P<name>\w+)\s*=\s*new\s+(?P<type>[\w.]+)\s*(?:<[^>]*>)?\s*\("
)


def _shared_prefix(left: str, right: str) -> int:
    shared = 0
    for a, b in zip(left.split("."), right.split("."), strict=False):
        if a != b:
            break
        shared += 1
    return shared


def _static_instance_throws(out: _Collector, root: Path, symbols: list[Fact]) -> None:
    """A public static field initialised with ``new T(...)`` carries T's members: each member of
    T that only throws (its fact already says so, an inherited virtual included) throws when
    reached through the field, so the field is a stub for that member (one dispatch hop)."""
    types = {
        fact.value: fact
        for fact in symbols
        if (fact.attributes or {}).get("symbol_kind", "") in _TYPE_KINDS
    }
    always: dict[str, list[Fact]] = {}
    for fact in out.facts:
        attributes = fact.attributes or {}
        if fact.kind == "implementation" and attributes.get("aspect") == "throws" and attributes.get("condition") == "always" and not attributes.get("visibility"):
            owner = attributes.get("member", "").rpartition(".")[0]
            if owner:
                always.setdefault(owner, []).append(fact)
    if not always:
        return
    for fact in symbols:
        located = _declared_line(fact)
        if located is None or language_of(located[0]) not in ("csharp", "java"):
            continue
        text = read_text(root, located[0])
        if text is None:
            continue
        lines = text.splitlines()
        if located[1] > len(lines):
            continue
        match = _STATIC_INSTANCE.search(lines[located[1] - 1])
        owner, _, field = fact.value.rpartition(".")
        if match is None or match.group("name") != field or not owner:
            continue
        # An inherited copy (the surface lists a base's static on every subclass) is not stated
        # again: only the type that declares the field, in the field's own file, carries it.
        declared_owner = _declared_line(types[owner]) if owner in types else None
        if declared_owner is None or declared_owner[0] != located[0]:
            continue
        constructed = match.group("type")
        suffix = "." + constructed
        candidates = [value for value in types if value == constructed or value.endswith(suffix)]
        if not candidates:
            continue
        # The type in the field's own namespace wins; two equally close candidates decide nothing.
        ranked = sorted(candidates, key=lambda value, home=owner: _shared_prefix(value, home), reverse=True)
        if len(ranked) > 1 and _shared_prefix(ranked[0], owner) == _shared_prefix(ranked[1], owner):
            continue
        resolved = ranked[0]
        for stub in always.get(resolved, []):
            attributes = stub.attributes or {}
            member = attributes.get("member", "").rsplit(".", 1)[-1]
            exception = attributes.get("exception", "")
            out.add(
                "implementation",
                ["throws", fact.value, member, exception],
                f"{fact.value}.{member} throws {exception} ({field} is constructed as "
                f"{constructed}, whose {member} only throws)",
                located[0],
                located[1],
                f"static instance constructed as {constructed}; {stub.id}",
                {
                    "aspect": "throws",
                    "member": f"{fact.value}.{member}",
                    "field": fact.value,
                    "via": attributes.get("member", ""),
                    "exception": exception,
                    "condition": "always",
                    "dispatch": "static_instance",
                },
            )


# --- standards --------------------------------------------------------------------------------

_STANDARD = re.compile(
    r"\b(ECMA-\d{2,4}|ISO(?:/IEC)?[ -]?\d{3,5}(?:-\d{1,2})?|RFC[ -]?\d{3,4}|WHATWG|W3C|ITU-T [A-Z]\.\d{1,4}|IEC \d{4,5})(?![\w-])"
    r"|message/(rfc822)",
    re.IGNORECASE,
)


def _normal_standard(match: re.Match[str]) -> str:
    if match.group(2):
        return "RFC 822"
    text = match.group(1).upper()
    text = re.sub(r"^RFC[ -]?", "RFC ", text)
    text = re.sub(r"^ISO/IEC[ -]?", "ISO/IEC ", text)
    text = re.sub(r"^ISO(?=\d)", "ISO ", text)
    text = re.sub(r"^ISO-(?=\d)", "ISO ", text)
    return text


def _standards(out: _Collector, root: Path, tree_paths: Sequence[str]) -> None:
    found: dict[str, list[tuple[str, int, str]]] = {}
    for path in product_sources(tree_paths):
        text = read_text(root, path)
        if text is None:
            continue
        offsets = None
        for match in _STANDARD.finditer(text):
            standard = _normal_standard(match)
            places = found.setdefault(standard, [])
            if len(places) >= 3:
                continue
            offsets = offsets or line_offsets(text)
            line = line_at(offsets, match.start())
            context = text[offsets[line - 1] : offsets[line] if line < len(offsets) else len(text)]
            places.append((path, line, " ".join(context.split())[:400]))
    for standard, places in sorted(found.items()):
        path, line, context = places[0]
        out.add(
            "standard_reference",
            [standard],
            standard,
            path,
            line,
            "the source names this specification",
            {"context": context, "also_at": ", ".join(f"{p}:{n}" for p, n, _ in places[1:])},
        )
        # Every place is evidence.
        if len(places) > 1 and out.facts and out.facts[-1].value == standard:
            last = out.facts[-1]
            out.facts[-1] = replace(
                last,
                evidence=(*last.evidence, *(Evidence(p, f"line {n}; {c}") for p, n, c in places[1:])),
            )


# --- entry point -------------------------------------------------------------------------------


def with_source_detail(root: Path, tree_paths: Sequence[str], facts: Sequence[Fact]) -> list[Fact]:
    """``facts`` with the public symbols' detail attributes added and every source-detail fact
    appended. Deterministic: same tree, same facts, same output."""
    symbols = [fact for fact in facts if fact.kind == "public_symbol"]
    existing_members = {fact.value for fact in facts if fact.kind == "enum_member"}
    out = _Collector(fact.id for fact in facts)
    updates: dict[str, dict[str, str]] = {}
    updates.update(_python_detail(out, root, tree_paths, symbols))
    updates.update(_brace_detail(out, root, tree_paths, symbols, existing_members))
    _internal_and_exports(out, root, tree_paths, symbols)
    _static_instance_throws(out, root, symbols)
    _never_thrown(out, root, tree_paths, symbols)
    _standards(out, root, tree_paths)
    for fact in symbols:
        # A method whose own body was read and holds no throw at all (K02: "X throws" is false).
        if out.bodies.get(fact.value) == "none" and (fact.attributes or {}).get("symbol_kind") in ("method", "function"):
            updates.setdefault(fact.id, {})["body_throws"] = "no"
    result: list[Fact] = []
    for fact in facts:
        extra = updates.get(fact.id)
        if extra:
            attributes = {**(fact.attributes or {}), **{k: v for k, v in extra.items() if v}}
            fact = replace(fact, attributes=attributes)
        result.append(fact)
    return [*result, *out.facts]


__all__ = ["CAPS", "with_source_detail"]
