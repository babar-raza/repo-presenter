"""Remove this machine's absolute paths from a toolchain's output before it becomes a receipt.

A receipt becomes a fact's evidence and a fact is published, so a runner's workspace, a temp
directory or a home directory must not appear in it, and a path that differs per machine would
move a sealed candidate's bytes for a reason that is not the repository (mission section 7 step 8,
the seal's no-op proof). The file name, line and column stay: `Program.cs(3,41): error CS1503: ...`
is the diagnostic; the directory it was found in is the machine.

Hosted run 40474666141 (2026-10): a relative run directory made the tool print the checkout root
as well as the run directory, and the scrub - which removed the run directory in whichever
spelling a `set` happened to iterate first - left `/home/runner/work/.../Program.cs(3,41)` in the
receipt. Every spelling is now removed longest first, and any absolute path under a conventional
machine root is reduced to its file name even when no caller named it.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

_MIN_BASE_LENGTH = 4
_SEPARATOR = r"[\\/]+"
# The characters that end a path inside a diagnostic: whitespace, the punctuation compilers put
# around `file(line,col)`, `file:line` and `[project]`, and quotes.
_SEGMENT = r"[^\s:()\[\]\"'<>|*?\\/]+"
_MACHINE_ROOTS = (
    "home|Users|root|tmp|var|private|opt|mnt|usr|srv|workspace|github|__w|runner|run"
)
_POSIX_PATH = re.compile(rf"(?<![\w.:/~-])/(?:{_MACHINE_ROOTS})/(?:{_SEGMENT}/)*")
_WINDOWS_PATH = re.compile(
    rf"(?<![\w])(?:\\\\\?\\)?[A-Za-z]:{_SEPARATOR}(?:{_SEGMENT}{_SEPARATOR})*"
)


def _spellings(path: Path) -> set[str]:
    spelled: set[str] = set()
    for variant in (path, path.resolve()):
        text = str(variant)
        for candidate in (text, variant.as_posix(), text.removeprefix("\\\\?\\")):
            if len(candidate) >= _MIN_BASE_LENGTH:
                spelled.add(candidate)
    return spelled


def _base_pattern(spelling: str, *, whole_path: bool) -> re.Pattern[str]:
    parts = [part for part in re.split(_SEPARATOR, spelling) if part]
    leading = len(spelling) - len(spelling.lstrip("\\/"))
    lead = rf"[\\/]{{{leading}}}" if leading else ""
    body = _SEPARATOR.join(re.escape(part) for part in parts)
    flags = re.IGNORECASE if re.match(r"[A-Za-z]:", spelling) else 0
    start = r"(?:\\\\\?\\)?(?<![\w.~-])" + lead + body
    if whole_path:
        return re.compile(start + rf"{_SEPARATOR}(?:{_SEGMENT}{_SEPARATOR})*", flags)
    return re.compile(start + rf"(?:{_SEPARATOR}|(?![\w.-]))", flags)


def scrub_machine_paths(text: str, *bases: Path) -> str:
    """``text`` without any absolute path prefix that names where this run happened.

    ``bases`` are the directories the caller knows the tool may print (run directory, checkout,
    workspace, product source); so is the current directory. Each is removed in every spelling
    (as given, resolved, either separator, Windows drive letters in any case), longest first, so a
    nested directory is never half-removed, and what follows it stays (`src/Widget.cs`). A path
    under the temp or home directory is cut back to its file name whatever its depth, and so is
    any other absolute path under a conventional machine root or a drive letter. Text with no
    path in it comes back unchanged.
    """
    patterns: list[tuple[str, bool]] = []
    for base in (*bases, Path(os.getcwd())):
        patterns.extend((spelling, False) for spelling in _spellings(base))
    for ambient in (tempfile.gettempdir(), str(Path.home())):
        patterns.extend((spelling, True) for spelling in _spellings(Path(ambient)))
    cleaned = text
    for spelling, whole_path in sorted(
        set(patterns), key=lambda item: (-len(item[0]), item[1], item[0])
    ):
        cleaned = _base_pattern(spelling, whole_path=whole_path).sub("", cleaned)
    cleaned = _WINDOWS_PATH.sub("", cleaned)
    return _POSIX_PATH.sub("", cleaned)
