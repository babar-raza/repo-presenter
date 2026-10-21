"""Shared example-verification types: what a platform plugin receives and what it returns.

Ported (REUSE, verbatim apart from the import path) from the old repository-presenter project's
``core/examples.py`` per migration/reuse-manifest.yaml ("readme/composition/" entry) -- needed by
``readme/composition/renderer.py``'s ``printed_example`` (what a README prints for a verified
example fact: exactly the program its receipt compiled, including the usings/imports a verifier
supplied).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from repo_presenter.core.facts import Fact

ExampleOutcome = Literal["EXECUTED", "FAILED", "TIMED_OUT", "NEEDS_INPUT", "NOT_VERIFIED"]
FormatDirection = Literal["input", "output"]
RECEIPTS_FILENAME = "examples.json"

_MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
_DURATION = r"(?:\d+\.\d+\s?(?:s|secs?|seconds?)|\d+(?:\.\d+)?\s?(?:ms|milliseconds?|µs|us|ns))"
_VOLATILE: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,9})?"
            r"(?:\s?(?:Z|UTC|[+-]\d{2}:?\d{2}))?"
        ),
        "<timestamp>",
    ),
    (
        re.compile(
            rf"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (?:{_MONTHS}) [ \d]\d \d{{2}}:\d{{2}}:\d{{2}}"
            r"(?: \d{4})?"
        ),
        "<timestamp>",
    ),
    (re.compile(r"(?<![\d:.])\d{1,2}:\d{2}:\d{2}[.,]\d{1,9}(?!\d)"), "<time>"),
    (
        re.compile(rf"(?i)\b(in|took|after|elapsed|duration)(?P<sep>[:=\s]+){_DURATION}\b"),
        r"\1\g<sep><duration>",
    ),
    (re.compile(r"\((?:\d+\.\d+s|\d+(?:\.\d+)?ms)\)"), "(<duration>)"),
    (re.compile(r"(?i)\b(pid|process id)(?P<sep>[ =:#]*)\d+\b"), r"\1\g<sep><pid>"),
    (
        re.compile(
            r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        ),
        "<uuid>",
    ),
    (re.compile(r"\b(at )0x[0-9a-fA-F]{6,}\b"), r"\g<1>0x<address>"),
    (re.compile(r"\b0x[0-9a-fA-F]{12,}\b"), "0x<address>"),
    (re.compile(r"\btmp[a-z0-9_]{8}\b"), "tmp<random>"),
)


def stable_output(text: str) -> str:
    """``text`` with every moment- or process-dependent spelling replaced by a fixed token."""
    for pattern, replacement in _VOLATILE:
        text = pattern.sub(replacement, text)
    return text


def collapse_blank_runs(text: str) -> str:
    """``text`` with every run of two or more empty lines reduced to one empty line."""
    kept: list[str] = []
    previous_empty = False
    for line in text.split("\n"):
        empty = not line.strip()
        if not (empty and previous_empty):
            kept.append(line)
        previous_empty = empty
    return "\n".join(kept)


PRELUDE_ATTRIBUTE = "prelude"
_PACKAGE_LINE = re.compile(r"^\s*package\s+[\w.]+\s*;\s*$")


def with_prelude(code: str, prelude: str) -> str:
    """``code`` as a reader must see it for the verifier's program to be theirs: the supplied
    lines first, one per line. A Java ``package`` declaration has to stay the first statement."""
    lines = [line.strip() for line in prelude.splitlines() if line.strip()]
    if not lines:
        return code
    body = code.split("\n")
    at = 0
    for index, line in enumerate(body):
        if line.strip():
            at = index + 1 if _PACKAGE_LINE.match(line) else 0
            break
    head, tail = body[:at], body[at:]
    while tail and not tail[0].strip():
        tail = tail[1:]
    return "\n".join([*head, *([""] if head else []), *lines, *tail])


def printed_example(fact: Fact) -> str:
    """The example a README prints for ``fact``: exactly the program its receipt compiled,
    including the usings or imports the verifier supplied."""
    return with_prelude(fact.value, (fact.attributes or {}).get(PRELUDE_ATTRIBUTE, ""))


@dataclass(frozen=True)
class FormatClaim:
    """A file extension one example statement loads (input) or saves (output), by code line."""

    extension: str
    direction: FormatDirection
    line: int
    literals: tuple[str, ...] = field(default=(), compare=False)


FormatDeclarationKind = Literal["declaration", "registration"]


@dataclass(frozen=True)
class FormatDeclaration:
    """A static statement about a format, read from the product's own source without importing
    it."""

    extension: str
    direction: FormatDirection | None
    kind: FormatDeclarationKind
    source_path: str
    line: int
    detail: str


@dataclass(frozen=True)
class ExampleCandidate:
    """One code block of the existing README that claims to be a runnable example."""

    ordinal: int
    language: str
    code: str
    source_path: str
    start_line: int
    end_line: int
    unit_id: str


@dataclass(frozen=True)
class MeasuredBuild:
    """What driving a package's own build proved, independent of any README example."""

    verified: bool
    command: str
    summary: str


@dataclass(frozen=True)
class FixtureBinding:
    """An input file staged under the name the example opens."""

    literal: str
    source_path: str
    produced_by: int | None = None


@dataclass(frozen=True)
class ExampleReceipt:
    """The verification outcome of one candidate, with redacted output."""

    ordinal: int
    outcome: ExampleOutcome
    return_code: int | None
    stdout: str
    stderr: str
    detail: str
    fixtures: tuple[FixtureBinding, ...] = ()
    build_verified: bool = True
    build_command: str = ""
    source_roots: tuple[str, ...] = ()
    prelude: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "stdout", stable_output(self.stdout))
        object.__setattr__(self, "stderr", stable_output(self.stderr))


def write_receipts(receipts: list[ExampleReceipt], path: Path) -> None:
    """Write the receipts as one deterministic JSON document."""
    payload = [asdict(receipt) for receipt in sorted(receipts, key=lambda r: r.ordinal)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
