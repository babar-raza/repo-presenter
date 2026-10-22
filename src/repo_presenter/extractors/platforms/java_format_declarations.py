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
regex failure here fails closed (finds nothing) rather than silently wrong. Known limitation,
stated plainly: a method that dispatches an extension but whose handler is itself an unimplemented
stub (e.g. this repository's own ``GltfReader.load()``, a ``// TODO`` returning an empty ``Scene``)
is still read as "registered" -- telling dispatched-but-stubbed apart from genuinely working needs
reading the handler body's own implementation, not just whether a dispatch arm exists, and is not
attempted here.
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

    java_paths = [p for p in tree_paths if p.endswith(_SOURCE_SUFFIX)]
    for rel_path in java_paths:
        text = _read(root / rel_path)
        if text is None:
            continue
        for extension, line in _declared_extensions(text):
            all_declared.setdefault(extension, (line, rel_path))
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
    return declarations
