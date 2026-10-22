"""Static format declarations of a Rust product, read from its source, never compiled or run.

New engineering, not a port -- the old repository never built this for Rust either (confirmed:
identical ``return []`` stub). Designed against the real, live source of
``aspose-cells-foss/Aspose.Cells-FOSS-for-Rust`` (2026-10-22).

Structurally close to the C++ reader -- a plain ``enum LoadFormat``/``enum SaveFormat`` with no
extension string literal anywhere, and a qualified reference (``LoadFormat::Xlsx``) as the
registration signal -- but independently investigated against this product's own real source,
not assumed to generalize from C++'s sibling repository. Two real differences from C++ measured
directly:

1. Rust enums cannot be forward-declared without a body the way C++'s ``enum class SaveFormat;``
   can -- every ``enum ... { ... }`` found is a complete definition, so the forward-declaration
   false positive that had to be fixed in the C++ reader has no Rust counterpart to guard
   against.
2. Rust's exhaustiveness checking means a ``match`` over an enum must name every variant (or use
   a wildcard arm) to compile at all. This repository's real gate functions
   (``ensure_supported_load_format``/``ensure_supported_save_format`` in ``Workbook.rs``) name
   every declared variant explicitly, including the sentinel ``LoadFormat::Auto`` -- which is why
   this ecosystem's registration signal, unlike C++'s sibling finding, corroborates both
   directions for Xlsx. The design still matters: a *future* revision that widened a match with a
   wildcard arm (``_ => Ok(())``) rather than naming a new variant explicitly would stop
   referencing that variant by name, and this reader would correctly report it as declared-only.

Sentinel enumerators that name no real format (``Auto``, ``Unknown``, ``None``, ``Default``,
``Custom``) are excluded from the declared set, the same convention as the C++ reader.

Deliberately text/regex-based, not a full Rust parse, for the same reason as its siblings: a
regex failure here fails closed (finds nothing) rather than silently wrong.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_presenter.core.examples import FormatDeclaration

_SOURCE_SUFFIX = ".rs"
_MAX_FILE_BYTES = 2_000_000

_SENTINELS = frozenset({"auto", "unknown", "none", "default", "custom"})

# `pub enum LoadFormat { ... }` / `enum SaveFormat { ... }` -- captures the direction keyword and
# the enum body. Rust has no forward-declaration form (unlike C++'s `enum class SaveFormat;`), so
# every match here is necessarily a complete definition.
_ENUM_BLOCK = re.compile(
    r"\benum\s+(LoadFormat|SaveFormat)\b[^{]*\{([^}]*)\}",
    re.DOTALL,
)

# One enumerator inside an enum body: a bare identifier followed by a comma (or end of body for
# the last member). Attribute lines (`#[default]`) never end in a comma right after the
# identifier they decorate, so they never match this pattern themselves.
_ENUMERATOR = re.compile(r"\b([A-Za-z_]\w*)\s*(?:,|\Z)")

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
    """``(enum_type, enumerator_name, line_number)`` for every non-sentinel, non-attribute
    member of a ``LoadFormat``/``SaveFormat`` enum block."""
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
    reference to one outside its own enum block (registration), correlated by enumerator name.

    A member declared but never referenced anywhere else in the tree is reported as declared-
    only: ``format_facts()`` will then mark it UNRESOLVED, never SUPPORTED.
    """
    declarations: list[FormatDeclaration] = []
    all_declared: dict[tuple[str, str], tuple[int, str]] = {}
    input_registered: set[str] = set()
    output_registered: set[str] = set()

    rust_paths = [p for p in tree_paths if p.endswith(_SOURCE_SUFFIX)]
    for rel_path in rust_paths:
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
