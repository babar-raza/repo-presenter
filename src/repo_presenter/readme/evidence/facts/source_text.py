"""Reading source files for the source-detail facts: languages, comments, bodies, product files.

Language-neutral helpers only. Nothing here decides what a fact says; it locates text the
repository itself contains (a doc comment above a declaration, the body a declaration opens, the
members an enum body lists) and hands back the exact line it came from.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path, PurePosixPath

from repo_presenter.extractors.surface.doc_text import (
    resolve_jsdoc_inline,
    resolve_rst_roles,
    resolve_xml_inline,
)

#: File suffix -> language. ``.d.ts`` is an ambient declaration, not the library's source.
LANGUAGES: dict[str, str] = {
    ".py": "python",
    ".cs": "csharp",
    ".java": "java",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".js": "javascript",
    ".mjs": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".h": "cpp",
    ".hh": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
}
BRACE_LANGUAGES = frozenset({"csharp", "java", "typescript", "javascript", "rust", "go", "cpp"})
#: Path parts that are never the product's own source.
_NOT_PRODUCT = frozenset(
    {
        "examples", "example", "samples", "sample", "docs", "doc", "benchmarks", "benchmark",
        "node_modules", "vendor", "third_party", "thirdparty", "external", "build", "dist",
        "target", "bin", "obj", ".github", "__pycache__", "fixtures", "testdata", "scripts",
    }
)  # fmt: skip
_TEST_PART = re.compile(r"(?:^|[._-])tests?(?:$|[._-])|^test_|_test$|^spec$|^specs$", re.IGNORECASE)
_TEST_FILE = re.compile(
    r"(?:^test_.*\.py|.*_test\.(?:py|go|rs|cpp|cc)|.*Tests?\.(?:cs|java)|.*\.(?:test|spec)\.[jt]sx?)$"
)
MAX_FILE_BYTES = 2_000_000


def language_of(path: str) -> str | None:
    if path.endswith(".d.ts"):
        return None
    return LANGUAGES.get(PurePosixPath(path).suffix.lower())


def is_test_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return any(_TEST_PART.search(part) for part in parts[:-1]) or bool(
        _TEST_FILE.match(parts[-1] if parts else "")
    )


def is_product_source(path: str) -> bool:
    """A source file of the library itself: a known language, not a test, sample or vendored file."""
    if language_of(path) is None:
        return False
    parts = [part.lower() for part in PurePosixPath(path).parts[:-1]]
    if any(part in _NOT_PRODUCT for part in parts):
        return False
    return not is_test_path(path)


def product_sources(tree_paths: Iterable[str]) -> list[str]:
    return sorted(path for path in tree_paths if is_product_source(path))


@lru_cache(maxsize=4096)
def _read(path: str) -> str | None:
    file = Path(path)
    try:
        if not file.is_file() or file.stat().st_size > MAX_FILE_BYTES:
            return None
        return file.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def read_text(root: Path, relative: str) -> str | None:
    return _read(str(root / relative))


def clear_cache() -> None:
    _read.cache_clear()


# --- comments ---------------------------------------------------------------------------------

#: Lines between a doc comment and its declaration that belong to neither (attributes,
#: annotations, decorators, Rust attributes, C++ templates and export macros).
_DECORATION = re.compile(r"^\s*(?:\[[^\]]*\]?\s*$|@\w|#\[|#!\[|template\s*<|\w+_EXPORT\b)")
_LINE_DOC = {
    "csharp": re.compile(r"^\s*///(?!/)"),
    "rust": re.compile(r"^\s*//[/!](?!/)"),
    "cpp": re.compile(r"^\s*//[/!]?(?!/)"),
    "go": re.compile(r"^\s*//"),
    "java": None,
    "typescript": None,
    "javascript": None,
}
_RULER = re.compile(r"^[\s/*=#~_-]*$")
_TAG = re.compile(r"<[^<>\n]+>")


def clean_comment(text: str) -> str:
    """A doc comment's text as a reader sees it: markers, inline markup and tags gone."""
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"^\s*(?:/\*\*?|\*/|///?!?|\*(?!/))", "", raw)
        line = re.sub(r"\*/\s*$", "", line)
        if _RULER.fullmatch(line):
            continue
        lines.append(line.strip())
    joined = " ".join(lines)
    joined = resolve_rst_roles(resolve_jsdoc_inline(resolve_xml_inline(joined)))
    joined = _TAG.sub(" ", joined)
    return " ".join(joined.split())


def leading_comment(lines: Sequence[str], declaration: int, language: str) -> tuple[str, int]:
    """The doc comment directly above the 0-based ``declaration`` line, cleaned, and its first
    0-based line (``("", declaration)`` when none). Decorations in between are skipped; a blank
    line ends the search."""
    index = declaration - 1
    while index >= 0 and _DECORATION.match(lines[index]) and not lines[index].strip().startswith("/"):
        index -= 1
    if index < 0:
        return "", declaration
    current = lines[index].rstrip()
    if current.endswith("*/"):
        start = index
        while start >= 0 and "/*" not in lines[start]:
            start -= 1
        if start < 0 or "/**" not in lines[start] and language in ("java", "typescript", "javascript"):
            return "", declaration
        return clean_comment("\n".join(lines[start : index + 1])), start
    pattern = _LINE_DOC.get(language)
    if pattern is None:
        return "", declaration
    start = index
    while start >= 0 and pattern.match(lines[start]):
        start -= 1
    start += 1
    if start > index:
        return "", declaration
    return clean_comment("\n".join(lines[start : index + 1])), start


# --- bodies -----------------------------------------------------------------------------------


def _skip(text: str, position: int, language: str) -> int:
    """The position just past a string, character literal or comment starting at ``position``,
    or ``position`` itself when none starts there."""
    two = text[position : position + 2]
    if two == "//":
        end = text.find("\n", position)
        return len(text) if end < 0 else end
    if two == "/*":
        end = text.find("*/", position + 2)
        return len(text) if end < 0 else end + 2
    char = text[position]
    if char in "\"`" or (char == "'" and language != "rust"):
        quote = char
        index = position + 1
        while index < len(text):
            if text[index] == "\\":
                index += 2
                continue
            if text[index] == quote:
                return index + 1
            if text[index] == "\n" and quote != "`":
                return index
            index += 1
        return len(text)
    return position


def matching_brace(text: str, opening: int, language: str) -> int:
    """The index of the ``}`` that closes the ``{`` at ``opening`` (``-1`` when unbalanced)."""
    depth = 0
    index = opening
    while index < len(text):
        skipped = _skip(text, index, language)
        if skipped != index:
            index = skipped
            continue
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def line_offsets(text: str) -> list[int]:
    offsets = [0]
    for match in re.finditer("\n", text):
        offsets.append(match.end())
    return offsets


def line_at(offsets: Sequence[int], position: int) -> int:
    """The 1-based line of ``position``."""
    low, high = 0, len(offsets) - 1
    while low < high:
        middle = (low + high + 1) // 2
        if offsets[middle] <= position:
            low = middle
        else:
            high = middle - 1
    return low + 1


def body_span(text: str, start: int, language: str) -> tuple[int, int] | None:
    """The body a declaration starting at ``start`` opens: ``(first, last)`` character positions
    of a ``{...}`` block, or of an expression body ``=> ...;``. ``None`` for a declaration that
    ends at ``;`` first (abstract, interface or forward declaration)."""
    index = start
    depth = 0  # parentheses, so a lambda default or a parameter list never opens a body
    while index < len(text):
        skipped = _skip(text, index, language)
        if skipped != index:
            index = skipped
            continue
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            if char == "{":
                end = matching_brace(text, index, language)
                return (index, end) if end > 0 else None
            if char == ";":
                return None
            if text.startswith("=>", index) and language in ("csharp", "typescript", "javascript"):
                end = index
                while end < len(text):
                    jumped = _skip(text, end, language)
                    if jumped != end:
                        end = jumped
                        continue
                    if text[end] in ";\n" and text[end] == ";":
                        return index, end
                    if text[end] == "{":
                        close = matching_brace(text, end, language)
                        if close < 0:
                            return None
                        end = close
                    end += 1
                return None
        index += 1
    return None


def strip_comments(text: str, language: str) -> str:
    """``text`` with comments replaced by spaces (strings kept), same length."""
    out = list(text)
    index = 0
    while index < len(text):
        skipped = _skip(text, index, language)
        if skipped != index:
            if text.startswith(("//", "/*"), index):
                for position in range(index, skipped):
                    if out[position] != "\n":
                        out[position] = " "
            index = skipped
            continue
        index += 1
    return "".join(out)


def split_top_level(text: str, separators: str = ",") -> list[tuple[int, str]]:
    """``text`` split at separators outside brackets, with each piece's start offset."""
    pieces: list[tuple[int, str]] = []
    depth = 0
    begin = 0
    for index, char in enumerate(text):
        if char in "([{<":
            depth += 1
        elif char in ")]}>":
            depth = max(0, depth - 1)
        elif depth == 0 and char in separators:
            pieces.append((begin, text[begin:index]))
            begin = index + 1
    pieces.append((begin, text[begin:]))
    return pieces


__all__ = [
    "BRACE_LANGUAGES",
    "LANGUAGES",
    "body_span",
    "clean_comment",
    "clear_cache",
    "is_product_source",
    "is_test_path",
    "language_of",
    "leading_comment",
    "line_at",
    "line_offsets",
    "matching_brace",
    "product_sources",
    "read_text",
    "split_top_level",
    "strip_comments",
]
