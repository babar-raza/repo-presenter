"""Static format declarations of a TypeScript product, read from its source, never compiled or
run.

New engineering, not a port -- the old repository never built this for TypeScript either
(confirmed: identical ``return []`` stub). Designed against the real, live source of
``aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript`` (2026-10-22).

A fifth, again-different idiom, and the one measured case so far where scoping the registration
signal to the *right* method body -- not just any reference anywhere in the tree, the way the
C++/Rust readers correlate -- is the difference between a correct reading and a wrong one. This
product declares a single string-valued ``SaveFormat`` enum (``XLSX = "xlsx"``, ``CSV = "csv"``,
``JSON = "json"``, ``MARKDOWN = "markdown"``, ``HTML = "html"``) and a ``detectFormat()`` helper
that maps a file extension to one of those members. A reader that treated any qualified
``SaveFormat.X`` reference anywhere in the file as "registered" would read CSV/JSON/MARKDOWN as
wired up, because ``detectFormat()`` references all three -- but ``detectFormat()`` only *guesses*
which format a path implies; it is not the method that actually writes a file. The real write
dispatch, ``Workbook.save()``, special-cases only ``SaveFormat.HTML`` and falls through to a
generic ZIP writer for everything else, including CSV/JSON/MARKDOWN -- so calling
``save("report.csv")`` in this real repository actually writes XLSX/ZIP bytes to a ``.csv`` path,
not real CSV content. (This repository's own README does not over-claim this: it correctly
documents CSV/JSON/MARKDOWN export only through the separate, genuinely-working ``toCsv()``/
``toJson()``/``toMarkdown()`` text-returning methods, never through ``save()`` with those
``saveFormat`` values -- a real latent bug in the product's own code, not a documentation defect,
and out of this tool's scope to fix.) This reader is therefore scoped to read qualified
``SaveFormat.X`` references only from inside ``save()``'s own body, not the whole file, so it
reports CSV/JSON/MARKDOWN as declared-but-unregistered rather than falsely corroborated.

There is no ``LoadFormat`` enum at all; ``Workbook.load()`` dispatches on a raw extension string
literal (``ext === "html"``), so the input-direction registration signal is a literal string
comparison inside ``load()``'s own body, matched against a declared extension's value.

Deliberately text/regex-based, not a full TypeScript parse, for the same reason as its siblings:
a regex failure here fails closed (finds nothing) rather than silently wrong. Unlike the .NET/
Java readers' fixed-size line window, method bodies here are found by depth-counting parens and
braces to their real matching close -- a fixed window was tried first and measurably bled into
the next method on a dense file (caught by this module's own unit tests), which would have
corrupted exactly the signal this reader exists to get right, so it was replaced before this
reader was trusted against the real repository.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_presenter.core.examples import FormatDeclaration

_SOURCE_SUFFIX = ".ts"
_MAX_FILE_BYTES = 2_000_000

# `export enum SaveFormat { ... }` -- captures the body.
_ENUM_BLOCK = re.compile(r"\benum\s+SaveFormat\b[^{]*\{([^}]*)\}", re.DOTALL)

# One string-valued member: `XLSX = "xlsx",`.
_ENUM_MEMBER = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*\"([^\"]{1,10})\"")

# A method declaration named exactly `save` or `load`, anchored at the start of its line (so a
# mid-expression call like `htmlDoc.load(filePath)` is never mistaken for the declaration).
_METHOD_ANCHOR = re.compile(r"^[ \t]*(?:static\s+)?(?:async\s+)?\b(save|load)\b\s*\(", re.MULTILINE)

# A qualified reference to a SaveFormat member: `SaveFormat.HTML`.
_QUALIFIED_REF = re.compile(r"\bSaveFormat\.(\w+)\b")

# A bare string-literal extension comparison inside load(): `ext === "html"` or `"html" === ext`.
_STRING_LITERAL = re.compile(r"\"([a-z0-9]{1,10})\"")


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def _normalize(extension: str) -> str:
    return "." + extension.lower().lstrip(".")


def _declared_members(text: str) -> list[tuple[str, str, int]]:
    """``(member_name, extension, line_number)`` for every ``SaveFormat`` enum member."""
    declared: list[tuple[str, str, int]] = []
    for block in _ENUM_BLOCK.finditer(text):
        body = block.group(1)
        body_start = block.start(1)
        for member in _ENUM_MEMBER.finditer(body):
            name, value = member.group(1), member.group(2)
            line = text.count("\n", 0, body_start + member.start()) + 1
            declared.append((name, _normalize(value), line))
    return declared


def _method_body(text: str, method_name: str) -> str | None:
    """The named method's own body, found by depth-counting parens (to skip past a parameter
    list whose type annotations may themselves contain brace pairs, e.g.
    ``options?: { password?: string; saveFormat?: SaveFormat }``) and then depth-counting braces
    from the body's real opening brace to its matching close. Exact, not a fixed-size window --
    a window risks bleeding into the next method's body on a file where methods sit close
    together, which would corrupt exactly the signal this reader exists to get right."""
    for match in _METHOD_ANCHOR.finditer(text):
        if match.group(1) != method_name:
            continue
        paren_depth = 0
        i = text.index("(", match.start())
        while i < len(text):
            if text[i] == "(":
                paren_depth += 1
            elif text[i] == ")":
                paren_depth -= 1
                if paren_depth == 0:
                    break
            i += 1
        else:
            continue
        brace_start = text.find("{", i + 1)
        if brace_start == -1:
            continue
        brace_depth = 0
        j = brace_start
        while j < len(text):
            if text[j] == "{":
                brace_depth += 1
            elif text[j] == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    return text[brace_start : j + 1]
            j += 1
    return None


def format_declarations(root: Path, tree_paths: list[str]) -> list[FormatDeclaration]:
    """Every ``SaveFormat`` enum member (declaration), corroborated against a registration
    signal read only from the method body that actually performs that direction's I/O --
    ``save()`` for output, ``load()`` for input -- not any reference anywhere in the tree.

    A member declared but never referenced inside the real write/read dispatch is reported as
    declared-only: ``format_facts()`` will then mark it UNRESOLVED, never SUPPORTED -- exactly
    the real gap between this repository's declared ``SaveFormat`` surface and what ``save()``
    actually implements.
    """
    declarations: list[FormatDeclaration] = []
    all_declared: dict[str, tuple[int, str]] = {}
    name_to_extension: dict[str, str] = {}
    output_registered: set[str] = set()
    input_registered_extensions: set[str] = set()

    ts_paths = [p for p in tree_paths if p.endswith(_SOURCE_SUFFIX)]
    for rel_path in ts_paths:
        text = _read(root / rel_path)
        if text is None:
            continue
        for name, extension, line in _declared_members(text):
            all_declared.setdefault(extension, (line, rel_path))
            name_to_extension[name] = extension

        save_body = _method_body(text, "save")
        if save_body is not None:
            output_registered.update(_QUALIFIED_REF.findall(save_body))

        load_body = _method_body(text, "load")
        if load_body is not None:
            input_registered_extensions.update(
                _normalize(token) for token in _STRING_LITERAL.findall(load_body)
            )

    for extension, (line, rel_path) in sorted(all_declared.items()):
        declarations.append(
            FormatDeclaration(
                extension=extension,
                direction=None,
                kind="declaration",
                source_path=rel_path,
                line=line,
                detail=f"SaveFormat declares extension {extension!r}",
            )
        )
        member_name = next(
            (name for name, ext in name_to_extension.items() if ext == extension), None
        )
        if member_name is not None and member_name in output_registered:
            declarations.append(
                FormatDeclaration(
                    extension=extension,
                    direction="output",
                    kind="registration",
                    source_path=rel_path,
                    line=line,
                    detail=f"SaveFormat.{member_name} referenced inside save()'s own body",
                )
            )
        if extension in input_registered_extensions:
            declarations.append(
                FormatDeclaration(
                    extension=extension,
                    direction="input",
                    kind="registration",
                    source_path=rel_path,
                    line=line,
                    detail=f"extension {extension!r} compared directly inside load()'s own body",
                )
            )
    return declarations
