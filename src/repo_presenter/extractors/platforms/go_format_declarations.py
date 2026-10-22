"""Static format declarations of a Go product, read from its source, never compiled or run.

New engineering, not a port -- the old repository never built this for Go either (confirmed:
identical ``return []`` stub). Designed against the real, live source of
``aspose-cells-foss/Aspose.Cells-FOSS-for-Go`` (2026-10-22).

A fourth, again-different idiom from .NET (identifier-correlated switch), Java (extension-string
dispatch chain), and C++ (qualified enum reference): this product has no format enum, no class
hierarchy, and no string-literal constructor argument anywhere. Format support is expressed
entirely through exported Go identifiers and their doc comments:

1. A **named-verb method** whose identifier itself states the format: ``ExportToCSV``,
   ``ImportFromCSV`` -- the format name is a literal suffix of the Go identifier.
2. The package's **primary ``Load``/``Save``** functions, which carry no format name in their
   identifier at all -- the real source states the format only in English prose directly above
   the function (``// Load opens the .xlsx file at path...``), so this reader reads the extension
   out of that doc comment.

Stated honestly, not worked around: unlike .NET's declared-class-vs-dispatch-switch split, Java's
declared-constructor-vs-equals-chain split, or C++'s declared-enum-vs-qualified-reference split,
Go's idiom gives this reader no second, independent signal to corroborate against -- an exported
Go function's mere existence already implies the code compiles and the identifier (or its doc
comment) is the only format statement there is. Both a "declaration" and a "registration" record
are emitted from the same single reading for this reason; this reader genuinely cannot produce
the "declared but never wired up" gap the other three readers can, because Go's own language
idiom does not physically separate "intent to support a format" from "a function that does it"
the way a class hierarchy or enum-plus-dispatch-table does. This is a property of the real source
measured, not a design shortfall hidden here.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_presenter.core.examples import FormatDeclaration

_SOURCE_SUFFIX = ".go"
_MAX_FILE_BYTES = 2_000_000

# `func (wb *Workbook) ExportToCSV(...)` / `func ImportFromCSV(...)` -- the format name is a
# literal suffix of the identifier itself.
_NAMED_METHOD = re.compile(
    r"^func\s+(?:\([^)]*\)\s*)?(ExportTo|SaveAs|ImportFrom|LoadFrom)(\w+)\s*\(",
    re.MULTILINE,
)
_OUTPUT_VERBS = frozenset({"ExportTo", "SaveAs"})

# The package's primary `Load(...)` / `(wb *Workbook) Save(...)` -- exact identifier match only
# (not a prefix), so this never matches the internal `LoadWorkbook`/`SaveWorkbook` helpers they
# call, which carry no format statement of their own.
_BARE_METHOD = re.compile(r"^func\s+(?:\([^)]*\)\s*)?(Load|Save)\s*\(", re.MULTILINE)

# An extension-looking token inside a doc comment: `.xlsx` in "opens the .xlsx file at path".
_DOC_EXTENSION = re.compile(r"\.([a-z]{2,5})\b")


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def _normalize(name: str) -> str:
    return "." + name.lower()


def _preceding_comment(lines: list[str], func_line_index: int) -> str:
    """The contiguous block of ``//`` doc-comment lines immediately above a func declaration."""
    collected: list[str] = []
    index = func_line_index - 1
    while index >= 0 and lines[index].strip().startswith("//"):
        collected.append(lines[index])
        index -= 1
    return "\n".join(reversed(collected))


def _named_declarations(text: str) -> list[tuple[str, str, int]]:
    """``(extension, direction, line_number)`` from every ``ExportTo``/``ImportFrom``-shaped
    method name."""
    found: list[tuple[str, str, int]] = []
    for match in _NAMED_METHOD.finditer(text):
        verb, suffix = match.group(1), match.group(2)
        direction = "output" if verb in _OUTPUT_VERBS else "input"
        line = text.count("\n", 0, match.start()) + 1
        found.append((_normalize(suffix), direction, line))
    return found


def _bare_declarations(text: str) -> list[tuple[str, str, int]]:
    """``(extension, direction, line_number)`` from the package's primary ``Load``/``Save``,
    reading the extension out of the doc comment immediately above (the only place the real
    source states it -- the identifier itself carries no format name)."""
    lines = text.splitlines()
    found: list[tuple[str, str, int]] = []
    for match in _BARE_METHOD.finditer(text):
        verb = match.group(1)
        direction = "output" if verb == "Save" else "input"
        line = text.count("\n", 0, match.start()) + 1
        comment = _preceding_comment(lines, line - 1)
        extension_match = _DOC_EXTENSION.search(comment)
        if extension_match is None:
            continue
        found.append((_normalize(extension_match.group(1)), direction, line))
    return found


def format_declarations(root: Path, tree_paths: list[str]) -> list[FormatDeclaration]:
    """Every exported format-shaped method, read once and reported as both declaration and
    registration together (see this module's docstring for why Go's idiom gives no second,
    independent signal to corroborate the two readings against, unlike .NET/Java/C++)."""
    declarations: list[FormatDeclaration] = []

    go_paths = [p for p in tree_paths if p.endswith(_SOURCE_SUFFIX) and not p.endswith("_test.go")]
    for rel_path in go_paths:
        text = _read(root / rel_path)
        if text is None:
            continue
        found = [*_named_declarations(text), *_bare_declarations(text)]
        for extension, direction, line in found:
            declarations.append(
                FormatDeclaration(
                    extension=extension,
                    direction=None,
                    kind="declaration",
                    source_path=rel_path,
                    line=line,
                    detail=f"an exported method states extension {extension!r}",
                )
            )
            declarations.append(
                FormatDeclaration(
                    extension=extension,
                    direction=direction,
                    kind="registration",
                    source_path=rel_path,
                    line=line,
                    detail=f"the same method is the only {direction} signal this reader has",
                )
            )
    return declarations
