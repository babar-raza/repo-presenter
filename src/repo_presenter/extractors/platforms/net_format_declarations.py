"""Static format declarations of a .NET product, read from its C# source, never compiled or run.

New engineering, not a port -- the old repository never built this for any ecosystem except
Python (confirmed directly against ``E:\\...\\repository-presenter``'s ``net.py``: identical
``return []`` stub). Designed against the real, live source of
``aspose-3d-foss/Aspose.3D-FOSS-for-.NET`` (2026-10-22), whose own ``IOService.cs`` is a textbook
case of exactly the defect class this reader exists to catch: a large, declared ``FileFormat``
surface (``Universal3D``, ``RvmText``/``RvmBinary``, and others, in ``FileFormat.cs``), but a
dispatch switch (``CreateImporter``/``CreateExporter``) that only matches 8 of them
(Obj/Stl/Gltf/Fbx/Microsoft3MF/Collada/Ply/Discreet3DS) -- every other declared format throws
``NotSupportedException`` at the one real entry point, which is exactly the live README's
U3D/RVM/AMF/HTML5 over-claim (independently confirmed earlier in this same session).

Two independent static sources, mirroring the Python reader's own two-source design:

1. **Declaration**: a nested class ``X : FileFormat`` (or ``: SomeFormat``) whose constructor
   calls ``base(".ext", ...)`` -- the extension the format class itself states.
2. **Registration**: a dispatch switch arm matching ``FileFormat.X`` (or ``== FileFormat.X``)
   inside a method whose name says which direction it handles (Importer/Reader/Load vs.
   Exporter/Writer/Save). A format with NO matching arm in either direction's dispatch method,
   however loudly it is declared elsewhere, is not reachable -- exactly what happened here.

Deliberately text/regex-based, not a full C# parse: the switch-expression-arm and
base-constructor-call shapes are syntactically regular enough that a full parse (the vendored
tree-sitter C# grammar, already available for surface extraction) is not needed for this first
cut, and a regex failure here fails closed (finds nothing) rather than silently wrong.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_presenter.core.examples import FormatDeclaration

_SOURCE_SUFFIX = ".cs"
_MAX_FILE_BYTES = 2_000_000

# internal class ObjFormat : FileFormat { public ObjFormat() : base(".obj", ... }
_CLASS_DECL = re.compile(
    r"\bclass\s+(\w+)\s*:\s*\w*Format\b(?:(?!\bclass\b).)*?base\(\s*\"(\.[A-Za-z0-9]{1,6})\"",
    re.DOTALL,
)

# A dispatch arm naming a format identifier: `FileFormat.ObjFormat` or `== FileFormat.ObjFormat`
# or `case FileFormat.ObjFormat:` -- any syntax, we only need the identifier after the dot.
_FORMAT_REF = re.compile(r"\bFileFormat\.(\w+)\b")

# A method whose name says which direction it dispatches. Order matters: check Import-ish
# keywords before Export-ish ones only where a name could plausibly match both (it won't here,
# kept simple and explicit).
_IMPORT_METHOD = re.compile(
    r"\b(?:Create|Get)?\w*(?:Import|Importer|Reader|Load)\w*\s*\([^)]*FileFormat"
)
_EXPORT_METHOD = re.compile(
    r"\b(?:Create|Get)?\w*(?:Export|Exporter|Writer|Save)\w*\s*\([^)]*FileFormat"
)
# A whole method body, from its header through the matching close brace, kept simple: take the
# header line plus the next N lines up to the next top-level method header or class close. This
# is intentionally crude (text-window, not brace-counting) -- good enough for a single dispatch
# method's switch body, which is what every real sample measured so far looks like.
_METHOD_WINDOW_LINES = 60


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def _declared_extensions(text: str) -> dict[str, tuple[str, int]]:
    """``{format_identifier: (extension, line_number)}`` from every ``class X : ...Format``
    constructor that calls ``base(".ext", ...)``."""
    declared: dict[str, tuple[str, int]] = {}
    for match in _CLASS_DECL.finditer(text):
        name, extension = match.group(1), match.group(2).lower()
        line = text.count("\n", 0, match.start()) + 1
        declared.setdefault(name, (extension, line))
    return declared


def _method_windows(text: str, header_pattern: re.Pattern[str]) -> list[tuple[str, int]]:
    """``(body_text, start_line)`` for every method whose header matches ``header_pattern``."""
    lines = text.splitlines()
    windows: list[tuple[str, int]] = []
    for match in header_pattern.finditer(text):
        start_line = text.count("\n", 0, match.start())
        body = "\n".join(lines[start_line : start_line + _METHOD_WINDOW_LINES])
        windows.append((body, start_line + 1))
    return windows


def format_declarations(root: Path, tree_paths: list[str]) -> list[FormatDeclaration]:
    """Every ``.cs`` file's format class declarations and import/export dispatch registrations.

    A format identifier declared (an ``X : FileFormat`` class with a stated extension) but never
    matched by any import OR export dispatch arm anywhere in the tree is correctly reported as
    declared-but-not-registered: ``format_facts()`` (``readme/evidence/facts/formats.py``) will
    then mark it UNRESOLVED, never SUPPORTED, which is exactly the real bug this reader exists
    to surface -- not an over-claim fix by itself (that is ``format_overclaim.py``'s job reading
    the resulting facts), just the missing corroborating signal that lets it work.
    """
    declarations: list[FormatDeclaration] = []
    all_declared: dict[str, tuple[str, int, str]] = {}
    import_registered: set[str] = set()
    export_registered: set[str] = set()

    cs_paths = [p for p in tree_paths if p.endswith(_SOURCE_SUFFIX)]
    for rel_path in cs_paths:
        text = _read(root / rel_path)
        if text is None:
            continue
        for name, (extension, line) in _declared_extensions(text).items():
            all_declared.setdefault(name, (extension, line, rel_path))
        for body, _start in _method_windows(text, _IMPORT_METHOD):
            import_registered.update(_FORMAT_REF.findall(body))
        for body, _start in _method_windows(text, _EXPORT_METHOD):
            export_registered.update(_FORMAT_REF.findall(body))

    for name, (extension, line, rel_path) in sorted(all_declared.items()):
        declarations.append(
            FormatDeclaration(
                extension=extension,
                direction=None,
                kind="declaration",
                source_path=rel_path,
                line=line,
                detail=f"class {name} : ...Format declares extension {extension!r}",
            )
        )
        if name in import_registered:
            declarations.append(
                FormatDeclaration(
                    extension=extension,
                    direction="input",
                    kind="registration",
                    source_path=rel_path,
                    line=line,
                    detail=f"FileFormat.{name} matched by an import/reader dispatch arm",
                )
            )
        if name in export_registered:
            declarations.append(
                FormatDeclaration(
                    extension=extension,
                    direction="output",
                    kind="registration",
                    source_path=rel_path,
                    line=line,
                    detail=f"FileFormat.{name} matched by an export/writer dispatch arm",
                )
            )
    return declarations
