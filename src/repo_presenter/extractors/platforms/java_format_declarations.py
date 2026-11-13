"""Static format declarations of a Java product, read from its source, never compiled or run.

New engineering, not a port -- the old repository never built this for Java either (confirmed:
identical ``return []`` stub). Designed against the real, live source of
``aspose-3d-foss/Aspose.3D-FOSS-for-Java`` (2026-10-22). This repository's real defect shape is
*not* the same as .NET's (a declared class with no matching dispatch arm anywhere): here, every
declared ``FileFormat`` constructor call hardcodes ``canImport``/``canExport`` to ``true``
regardless of whether any code path actually handles it, so those two booleans are not a usable
registration signal -- they are noise, stated by the declaration site itself, not corroborated by
anything. The real, load-bearing registration signal is the ``ext.equals("...")`` dispatch chain
inside ``FileFormat``'s own ``load``/``save``/``createLoadOptions``/``createSaveOptions`` methods,
which only matches 4 of the ~30 declared formats (stl, obj, gltf/glb, fbx) -- every other declared
format (Universal3D, RVM, AMF, HTML5 among them) throws at the one real entry point.

Two independent static sources, mirroring the .NET/Python readers' own two-source design, but
correlated by extension string directly rather than by a format identifier -- Java's own dispatch
chain tests the extension literal itself (``ext.equals("stl")``), it never names a ``FileFormat``
constant the way the .NET switch does, so there is no identifier to join on:

1. **Declaration**: any ``new FileFormat(...)`` or ``super(...)`` constructor call (direct or
   inside a ``class X extends FileFormat`` subclass) whose positional arguments are
   ``(type, version, contentType, extension, extensions[], canImport, canExport)`` -- the
   extension string immediately following the ``FileContentType.X`` argument.
2. **Registration**: inside a method whose name contains "load" or "save" (``load``, ``save``,
   ``createLoadOptions``, ``createSaveOptions``), an ``ext.equals("...")`` or
   ``extension.equals("...")`` dispatch arm -- direction from the method name.

Deliberately text/regex-based, not a full Java parse, for the same reason as the .NET reader: a
regex failure here fails closed (finds nothing) rather than silently wrong.

A dispatch arm whose handler is an unimplemented stub is not a registration (the Python reader's
own rule, ``python_format_declarations._is_stub``). Measured (hosted Lane R run 43394954743): the
arm ``ext.equals("gltf") || ext.equals("glb")`` constructs ``GltfReader`` and calls its ``load``,
whose whole body is ``// TODO: implement GLTF loading`` and ``return new Scene();``; read as
registered, ``format:input.gltf`` was SUPPORTED and the README claimed the product reads glTF.
The handler is resolved by name inside the arm (``X v = new X(...)`` then ``v.m(...)``, or
``new X(...).m(...)``) and its method ``m`` read from the class's own body. A method whose body,
comments removed, is empty, a lone ``return`` of nothing / ``null`` / a literal / a no-argument
``new T()``, or a lone not-implemented throw, is a stub; a direction whose every resolved handler
is a stub is reported as a directional *declaration* (so ``format_facts`` keeps an UNRESOLVED fact
with the evidence) and not as a registration. An arm whose handler cannot be resolved keeps the
earlier reading (registered), so nothing that worked before is demoted on a guess.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_presenter.core.examples import FormatDeclaration

_SOURCE_SUFFIX = ".java"
_MAX_FILE_BYTES = 2_000_000
_METHOD_WINDOW_LINES = 40

# `new FileFormat(FileFormatType.STL, new Version(1, 0, 0), FileContentType.BINARY, "stl", ...)`
# or a subclass `super(FileFormatType.RVM, new Version(1, 0, 0), contentType, ".rvm", ...)` --
# the third positional argument (content type) is sometimes a `FileContentType.X` literal and
# sometimes a passed-through parameter (this repository's own ``RvmFormat`` constructor), so this
# anchors on the two arguments that are always literal (``FileFormatType.X``, ``new Version(...)``)
# and reads whichever string literal comes immediately after whatever the third argument is.
_DECLARED_EXTENSION = re.compile(
    r"FileFormatType\.\w+\s*,\s*new\s+Version\([^)]*\)\s*,\s*[\w.]+\s*,\s*"
    r"\"(\.?[A-Za-z0-9]{1,6})\""
)

# A method declaration header ending its signature with `{` on the same line -- true of every real
# load/save/createLoadOptions/createSaveOptions method measured in this repository's own source.
# Modifiers are zero or more, never required: this repository's own ``load``/``save`` methods are
# package-private (no modifier keyword at all), only the static facade methods use ``static``.
_METHOD_HEADER = re.compile(
    r"^[ \t]*(?:(?:public|private|protected|static|final|abstract|synchronized)\s+)*"
    r"[\w<>\[\],.]+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{",
    re.MULTILINE,
)

# `ext.equals("stl")` or `extension.equals(".pdf")` -- the dispatch arm itself.
_EQUALS_DISPATCH = re.compile(r"\b\w+\.equals\(\s*\"(\.?[A-Za-z0-9]{1,6})\"\s*\)")


# A handler constructed inside a dispatch arm and the method called on it.
_HANDLER_VARIABLE = re.compile(r"\b(\w+)\s*=\s*new\s+(\w+)\s*\(")
_HANDLER_CHAINED = re.compile(r"\bnew\s+(\w+)\s*\([^()]*\)\s*\.\s*(\w+)\s*\(")
_CLASS_HEADER = re.compile(r"\bclass\s+(\w+)\b[^{;]*\{")
_STUB_RETURN = re.compile(
    r"return(?:\s+(?:null|true|false|-?\d+(?:\.\d+)?[fFdDlL]?|\"[^\"]*\""
    r"|new\s+[\w.<>]+\s*\(\s*\)))?\s*;"
)
_STUB_THROW = re.compile(
    r"throw\s+new\s+\w*(?:UnsupportedOperation|NotImplemented|NotSupported)\w*\s*\([^;]*\)\s*;"
    r"|throw\s+new\s+\w+\s*\(\s*\"[^\"]*not\s+(?:yet\s+)?(?:implemented|supported)[^\"]*\"\s*\)\s*;",
    re.IGNORECASE,
)
_NOT_A_METHOD = frozenset({"if", "for", "while", "switch", "catch", "synchronized"})


def _skip_literal_or_comment(text: str, index: int) -> int:
    """The index just past a string/char literal or comment starting at ``index``, else ``index``."""
    if text.startswith("//", index):
        end = text.find("\n", index)
        return len(text) if end < 0 else end
    if text.startswith("/*", index):
        end = text.find("*/", index + 2)
        return len(text) if end < 0 else end + 2
    if text[index] in "\"'":
        quote = text[index]
        position = index + 1
        while position < len(text) and text[position] != quote and text[position] != "\n":
            position += 2 if text[position] == "\\" else 1
        return position + 1
    return index


def _strip_comments(text: str) -> str:
    """``text`` with comments blanked (newlines and length kept, literals kept)."""
    out = list(text)
    index = 0
    while index < len(text):
        skipped = _skip_literal_or_comment(text, index)
        if skipped == index:
            index += 1
            continue
        if text.startswith(("//", "/*"), index):
            for position in range(index, min(skipped, len(text))):
                if out[position] != "\n":
                    out[position] = " "
        index = skipped
    return "".join(out)


def _block_end(text: str, opening: int) -> int:
    """The index of the ``}`` closing the ``{`` at ``opening``, or ``-1``."""
    depth = 0
    index = opening
    while index < len(text):
        skipped = _skip_literal_or_comment(text, index)
        if skipped != index:
            index = skipped
            continue
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _is_stub_body(inner: str) -> bool:
    """Whether a method body (between its braces, comments removed) does nothing real."""
    body = inner.strip()
    return not body or bool(_STUB_RETURN.fullmatch(body) or _STUB_THROW.fullmatch(body))


def _class_methods(text: str) -> dict[str, dict[str, list[bool]]]:
    """For each class declared in ``text``: each method name to whether each body is a stub."""
    stripped = _strip_comments(text)
    classes: dict[str, dict[str, list[bool]]] = {}
    for header in _CLASS_HEADER.finditer(stripped):
        opening = header.end() - 1
        end = _block_end(stripped, opening)
        if end < 0:
            continue
        body = stripped[opening + 1 : end]
        methods = classes.setdefault(header.group(1), {})
        for method in _METHOD_HEADER.finditer(body):
            if method.group(1) in _NOT_A_METHOD:
                continue
            start = method.end() - 1
            close = _block_end(body, start)
            if close < 0:
                continue
            methods.setdefault(method.group(1), []).append(_is_stub_body(body[start + 1 : close]))
    return classes


def _arm_handlers(body: str) -> list[tuple[list[str], list[tuple[str, str]]]]:
    """``(extensions, [(handler_class, method)])`` for each dispatch arm of a method window: the
    extensions its condition tests and the handlers its block constructs and calls."""
    stripped = _strip_comments(body)
    arms: list[tuple[list[str], list[tuple[str, str]]]] = []
    position = 0
    for match in _EQUALS_DISPATCH.finditer(stripped):
        if match.start() < position:
            continue
        opening = stripped.find("{", match.end())
        end = _block_end(stripped, opening) if opening >= 0 else -1
        if end < 0:
            break
        condition = stripped[match.start() : opening]
        extensions = [_normalize(ext) for ext in _EQUALS_DISPATCH.findall(condition)]
        block = stripped[opening + 1 : end]
        handlers = [
            (cls, method)
            for variable, cls in _HANDLER_VARIABLE.findall(block)
            for method in re.findall(rf"\b{re.escape(variable)}\s*\.\s*(\w+)\s*\(", block)
        ]
        handlers += _HANDLER_CHAINED.findall(block)
        arms.append((extensions, handlers))
        position = opening
    return arms


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def _normalize(extension: str) -> str:
    return "." + extension.lower().lstrip(".")


def _declared_extensions(text: str) -> list[tuple[str, int]]:
    """``(extension, line_number)`` for every ``FileFormat``/``super`` constructor call found."""
    declared: list[tuple[str, int]] = []
    for match in _DECLARED_EXTENSION.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        declared.append((_normalize(match.group(1)), line))
    return declared


def _method_windows(text: str) -> list[tuple[str, str]]:
    """``(method_name, body_text)`` for every method header matched, direction undetermined."""
    lines = text.splitlines()
    windows: list[tuple[str, str]] = []
    for match in _METHOD_HEADER.finditer(text):
        name = match.group(1)
        start_line = text.count("\n", 0, match.start())
        body = "\n".join(lines[start_line : start_line + _METHOD_WINDOW_LINES])
        windows.append((name, body))
    return windows


def format_declarations(root: Path, tree_paths: list[str]) -> list[FormatDeclaration]:
    """Every ``.java`` file's format constructor declarations and load/save dispatch
    registrations, correlated by extension string (Java's own dispatch tests the literal
    extension, never a format identifier, so there is nothing else to join on).

    An extension declared by a constructor call but never matched by any load/save dispatch arm
    is correctly reported as declared-but-not-registered: ``format_facts()`` will then mark it
    UNRESOLVED, never SUPPORTED -- exactly the real gap between this repository's declared
    ``FileFormat`` surface (~30 formats, all with ``canImport``/``canExport`` hardcoded true) and
    its actually-reachable one (4 formats: stl, obj, gltf/glb, fbx).
    """
    declarations: list[FormatDeclaration] = []
    all_declared: dict[str, tuple[int, str]] = {}
    input_registered: set[str] = set()
    output_registered: set[str] = set()
    # (direction, extension) -> the handlers its dispatch arms call, resolved once every file is
    # read (a handler class may be declared in another file).
    handled: dict[tuple[str, str], set[tuple[str, str]]] = {}
    methods: dict[str, dict[str, list[bool]]] = {}

    java_paths = [p for p in tree_paths if p.endswith(_SOURCE_SUFFIX)]
    for rel_path in java_paths:
        text = _read(root / rel_path)
        if text is None:
            continue
        for extension, line in _declared_extensions(text):
            all_declared.setdefault(extension, (line, rel_path))
        for cls, found in _class_methods(text).items():
            for method, stubs in found.items():
                methods.setdefault(cls, {}).setdefault(method, []).extend(stubs)
        for name, body in _method_windows(text):
            lowered = name.lower()
            is_load = "load" in lowered
            is_save = "save" in lowered
            if not is_load and not is_save:
                continue
            matched = {_normalize(ext) for ext in _EQUALS_DISPATCH.findall(body)}
            if is_load:
                input_registered.update(matched)
            if is_save:
                output_registered.update(matched)
            directions = ("input",) * is_load + ("output",) * is_save
            for extensions, handlers in _arm_handlers(body):
                for extension in extensions:
                    for direction in directions:
                        handled.setdefault((direction, extension), set()).update(handlers)

    def stubs_of(direction: str, extension: str) -> list[str]:
        """The handlers of a direction when every one resolved is a stub, else ``[]``."""
        resolved = [
            (f"{cls}.{method}", all(methods[cls][method]))
            for cls, method in sorted(handled.get((direction, extension), ()))
            if method in methods.get(cls, {})
        ]
        if not resolved or not all(stub for _, stub in resolved):
            return []
        return [name for name, _ in resolved]

    stubbed = {
        (direction, extension): stubs_of(direction, extension)
        for direction, registered in (("input", input_registered), ("output", output_registered))
        for extension in registered
    }
    input_registered = {ext for ext in input_registered if not stubbed[("input", ext)]}
    output_registered = {ext for ext in output_registered if not stubbed[("output", ext)]}

    for extension, (line, rel_path) in sorted(all_declared.items()):
        declarations.append(
            FormatDeclaration(
                extension=extension,
                direction=None,
                kind="declaration",
                source_path=rel_path,
                line=line,
                detail=f"a FileFormat constructor call declares extension {extension!r}",
            )
        )
        if extension in input_registered:
            declarations.append(
                FormatDeclaration(
                    extension=extension,
                    direction="input",
                    kind="registration",
                    source_path=rel_path,
                    line=line,
                    detail=f"{extension!r} matched by a load/createLoadOptions dispatch arm",
                )
            )
        if extension in output_registered:
            declarations.append(
                FormatDeclaration(
                    extension=extension,
                    direction="output",
                    kind="registration",
                    source_path=rel_path,
                    line=line,
                    detail=f"{extension!r} matched by a save/createSaveOptions dispatch arm",
                )
            )
        for direction in ("input", "output"):
            stubs = stubbed.get((direction, extension))
            if stubs:
                declarations.append(
                    FormatDeclaration(
                        extension=extension,
                        direction=direction,  # type: ignore[arg-type]
                        kind="declaration",
                        source_path=rel_path,
                        line=line,
                        detail=(
                            f"{extension!r} is dispatched for {direction} only to "
                            f"{', '.join(stubs)}, an unimplemented stub; not a registration"
                        ),
                    )
                )
    return declarations
