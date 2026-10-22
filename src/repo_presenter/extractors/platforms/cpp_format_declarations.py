"""Static format declarations of a C++ product, read from its source, never compiled or run.

New engineering, not a port -- the old repository never built this for C++ either (confirmed:
identical ``return []`` stub). Designed against the real, live source of
``aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`` (2026-10-22).

A third, again-different idiom from .NET's (identifier-correlated switch) and Java's (extension-
string-correlated equals-chain): this product states formats as a plain ``enum class LoadFormat``
/``enum class SaveFormat`` with no extension string literal anywhere in source -- just an
enumerator name (``Xlsx``) and a doc comment ("XLSX format."). There is nothing to read as "the
extension" except the enumerator's own name, so this reader's declaration source normalizes the
enumerator name itself to an extension (``Xlsx`` -> ``.xlsx``) -- a heuristic, stated plainly, not
a literal read the way the other two readers have. Registration is simpler here than either
sibling: every real use of a format is a fully-qualified reference (``LoadFormat::Xlsx`` /
``SaveFormat::Xlsx``), so any such reference outside the enum's own declaration is "registered" in
that direction, correlated by enumerator name (like .NET, not like Java).

Measured against the real repository: this is the one ecosystem measured so far where declared
and registered are NOT a known mismatch -- both enums have exactly one member (``Xlsx``, plus
``LoadFormat``'s ``Auto`` auto-detection sentinel), and the real ``XlsxWorkbookSerializer.cpp``
gate (``if (options.GetSaveFormat() != SaveFormat::Xlsx) { ... }``) references that one member
directly. A clean/no-finding result here is a correct, honest read of a product with a genuinely
small declared surface, not a sign the reader missed something -- the value of building it is
having the signal in place at all, so a *future* revision that grows the enum without wiring the
new member into the serializer is caught the same way the .NET/Java gaps were.

Sentinel enumerators that name no real format (``Auto``, ``Unknown``, ``None``, ``Default``,
``Custom``) are excluded from the declared set entirely -- they are not a format claim either way.

Deliberately text/regex-based, not a full C++ parse, for the same reason as its siblings: a
regex failure here fails closed (finds nothing) rather than silently wrong.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_presenter.core.examples import FormatDeclaration

_SOURCE_SUFFIXES = (".h", ".hpp", ".cpp", ".cc", ".cxx")
_MAX_FILE_BYTES = 2_000_000

_SENTINELS = frozenset({"auto", "unknown", "none", "default", "custom"})

# `enum class LoadFormat { ... }` / `enum class SaveFormat { ... }` -- captures the direction
# keyword and the enum body. The gap before `{` excludes `;` deliberately: a forward declaration
# (`enum class SaveFormat;`, the real shape this repository's own Workbook.h uses before its
# Save() overloads) has no body at all, and without that exclusion `[^{]*` would skip straight
# past the semicolon and greedily match the next unrelated `{...}` block anywhere later in the
# file, reading ordinary method parameter names as fake enumerators (measured real bug,
# 2026-10-22: this exact forward declaration produced five garbage "declarations" from
# Workbook.h's own method signatures before this fix).
_ENUM_BLOCK = re.compile(
    r"\benum\s+class\s+(LoadFormat|SaveFormat)\b[^{;]*\{([^}]*)\}",
    re.DOTALL,
)

# One enumerator inside an enum body: a bare identifier followed by an optional `= N` and a
# trailing comma (the last member may omit the comma, handled by also allowing end-of-body).
_ENUMERATOR = re.compile(r"\b([A-Za-z_]\w*)\s*(?:=\s*-?\d+\s*)?(?:,|\Z)")

# A fully-qualified reference naming a direction and a member: `SaveFormat::Xlsx`.
_QUALIFIED_REF = re.compile(r"\b(LoadFormat|SaveFormat)::(\w+)\b")


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def _normalize(name: str) -> str:
    return "." + name.lower()


def _declared_members(text: str) -> list[tuple[str, str, int]]:
    """``(enum_type, enumerator_name, line_number)`` for every non-sentinel member of a
    ``LoadFormat``/``SaveFormat`` enum block."""
    declared: list[tuple[str, str, int]] = []
    for block in _ENUM_BLOCK.finditer(text):
        enum_type, body = block.group(1), block.group(2)
        body_start = block.start(2)
        for member in _ENUMERATOR.finditer(body):
            name = member.group(1)
            if name.lower() in _SENTINELS:
                continue
            line = text.count("\n", 0, body_start + member.start()) + 1
            declared.append((enum_type, name, line))
    return declared


def format_declarations(root: Path, tree_paths: list[str]) -> list[FormatDeclaration]:
    """Every ``LoadFormat``/``SaveFormat`` enum member (declaration) and every fully-qualified
    reference to one outside its own enum block (registration), correlated by enumerator name --
    the only identifier C++ gives this reader to join on, since no extension string literal
    appears anywhere near the declaration itself (unlike the .NET/Java sources).

    A member declared but never referenced anywhere else in the tree is reported as declared-only:
    ``format_facts()`` will then mark it UNRESOLVED, never SUPPORTED -- the same mechanism as the
    .NET/Java readers, even though this specific repository currently has no such gap to surface.
    """
    declarations: list[FormatDeclaration] = []
    all_declared: dict[tuple[str, str], tuple[int, str]] = {}
    input_registered: set[str] = set()
    output_registered: set[str] = set()

    source_paths = [p for p in tree_paths if p.endswith(_SOURCE_SUFFIXES)]
    for rel_path in source_paths:
        text = _read(root / rel_path)
        if text is None:
            continue
        for enum_type, name, line in _declared_members(text):
            all_declared.setdefault((enum_type, name), (line, rel_path))
        for enum_type, name in _QUALIFIED_REF.findall(text):
            if enum_type == "LoadFormat":
                input_registered.add(name)
            else:
                output_registered.add(name)

    for (enum_type, name), (line, rel_path) in sorted(all_declared.items()):
        extension = _normalize(name)
        direction = "input" if enum_type == "LoadFormat" else "output"
        declarations.append(
            FormatDeclaration(
                extension=extension,
                direction=None,
                kind="declaration",
                source_path=rel_path,
                line=line,
                detail=f"{enum_type}::{name} declares extension {extension!r}",
            )
        )
        registered = input_registered if direction == "input" else output_registered
        if name in registered:
            declarations.append(
                FormatDeclaration(
                    extension=extension,
                    direction=direction,
                    kind="registration",
                    source_path=rel_path,
                    line=line,
                    detail=f"{enum_type}::{name} referenced outside its own enum declaration",
                )
            )
    return declarations
