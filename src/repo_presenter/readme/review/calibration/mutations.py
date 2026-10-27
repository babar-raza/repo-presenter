"""Mutation operators over a real candidate README (plan D9 V4).

Each operator makes ONE edit to a clean README and returns it as a ``Mutation``: the span of the
clean text that was replaced (``start``..``end``, an insertion when both are equal), the
replacement, and the class of defect the edit injects. The mutated README is, by construction and
by test, the clean README with exactly that span replaced; nothing else differs. Every mutant has
an expected verdict (``REJECT``) and is paired with its clean twin in ``corpus``.

An operator returns ``None`` when the candidate has no place for its edit (a README that never
prints a version cannot be given a wrong one); the corpus then simply has no such mutant for that
base. Operators are pure functions of the candidate and are deterministic.

Operators never take their target from the reviewer's own output, and every injected string is
checked against the candidate's facts so the injected defect really is one: an unsupported claim
shares no distinctive word with any fact value, a contradicting version is not a fact, an invented
API name is no fact value.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from repo_presenter.readme.review.calibration.outcomes import REJECT
from repo_presenter.readme.review.calibration.sources import SourceCandidate

#: The defect classes. The first four are the plan's high-severity gate classes (D9 V5).
HIGH_SEVERITY_CLASSES = (
    "contradiction",
    "content_loss",
    "unsupported_claim",
    "broken_install",
)
CLASSES = (
    *HIGH_SEVERITY_CLASSES,
    "duplicate_paragraph",
    "invented_api",
    "promotional_filler",
)

#: Claims no fact can support, each with the words that would show a fact does. An operator uses the
#: first claim none of whose keywords occurs in any fact value or in the live README.
UNSUPPORTED_CLAIMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "It preserves every attribute through a full round-trip with complete fidelity.",
        ("round-trip", "fidelity"),
    ),
    (
        "Every conversion is verified byte-for-byte lossless against the reference implementation.",
        ("lossless", "byte-for-byte"),
    ),
    (
        "It runs up to ten times faster than the leading commercial libraries.",
        ("faster", "commercial libraries"),
    ),
    (
        "It is deployed in production by more than five hundred enterprises worldwide.",
        ("enterprises", "production"),
    ),
)
PROMOTIONAL_FILLER = (
    "It is a powerful, cutting-edge, best-in-class solution that revolutionizes the way "
    "developers build amazing experiences."
)
#: Formats and APIs the candidate cannot support, tried in order.
FOREIGN_FORMATS = (".step", ".iges", ".usdz", ".x3d", ".blend")
_FENCE = re.compile(r"^(```|~~~)")


@dataclass(frozen=True)
class Mutation:
    operator: str
    klass: str
    start: int
    end: int
    replacement: str
    readme: str
    note: str
    expected: str = REJECT
    #: Lower-case words a reviewer's finding must contain to be about THIS edit (``harness``
    #: scores a rejection that names none of them as off target).
    targets: tuple[str, ...] = ()


def _fences(text: str) -> list[tuple[int, int]]:
    """Character ranges of fenced code blocks, fences included."""
    ranges: list[tuple[int, int]] = []
    opened: int | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        if _FENCE.match(line):
            if opened is None:
                opened = offset
            else:
                ranges.append((opened, offset + len(line)))
                opened = None
        offset += len(line)
    if opened is not None:
        ranges.append((opened, len(text)))
    return ranges


def _inside(position: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in ranges)


def h2_sections(text: str) -> list[tuple[str, int, int]]:
    """``(title, start, end)`` of every ``## `` section outside code fences; a section runs from
    its heading to the next ``## `` heading (or the end)."""
    fences = _fences(text)
    heads: list[tuple[str, int]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.startswith("## ") and not _inside(offset, fences):
            heads.append((line[3:].strip(), offset))
        offset += len(line)
    return [
        (title, start, heads[index + 1][1] if index + 1 < len(heads) else len(text))
        for index, (title, start) in enumerate(heads)
    ]


def paragraphs(
    text: str, start: int = 0, end: int | None = None
) -> list[tuple[int, int]]:
    """Blank-line separated prose paragraphs in ``text[start:end]``, fences, headings, lists,
    tables, quotes, images/badges and raw HTML excluded."""
    end = len(text) if end is None else end
    fences = _fences(text)
    found: list[tuple[int, int]] = []
    for match in re.finditer(r"(?:[^\n]+\n?)+", text[start:end]):
        s, e = start + match.start(), start + match.end()
        block = text[s:e].rstrip("\n")
        if _inside(s, fences) or not block.strip():
            continue
        first = block.lstrip()[:1]
        if first in "#|>-*<![" or re.match(r"\d+[.)] ", block.lstrip()):
            continue
        found.append((s, s + len(block)))
    return found


def opening_paragraph(text: str) -> tuple[int, int] | None:
    """The first prose paragraph of at least 60 characters (the product's opening statement)."""
    for s, e in paragraphs(text):
        if e - s >= 60:
            return s, e
    return None


def _fact_values(source: SourceCandidate) -> str:
    return "\n".join(fact.value for fact in source.facts.facts).lower()


def _build(
    source: SourceCandidate,
    operator: str,
    klass: str,
    start: int,
    end: int,
    new: str,
    note: str,
    targets: tuple[str, ...] = (),
) -> Mutation:
    clean = source.readme
    return Mutation(
        operator,
        klass,
        start,
        end,
        new,
        clean[:start] + new + clean[end:],
        note,
        targets=tuple(target.lower() for target in targets),
    )


def _prose_occurrence(text: str, needle: str) -> int | None:
    """Position of the first occurrence of ``needle`` outside code fences and link targets."""
    fences = _fences(text)
    for match in re.finditer(re.escape(needle), text):
        position = match.start()
        if _inside(position, fences):
            continue
        line_start = text.rfind("\n", 0, position) + 1
        line = text[
            line_start : text.find("\n", position) if "\n" in text[position:] else None
        ]
        if "](" in line and line.find("](") < position - line_start < line.find(
            ")", line.find("](")
        ):
            continue
        if line.lstrip().startswith(("[![", "![", "<")):
            continue
        return position
    return None


def inject_unsupported_claim(
    source: SourceCandidate, variant: int = 0
) -> Mutation | None:
    opening = opening_paragraph(source.readme)
    if opening is None:
        return None
    known = _fact_values(source) + "\n" + source.original.lower()
    usable = [
        claim
        for claim, words in UNSUPPORTED_CLAIMS
        if not any(word in known for word in words)
    ]
    if not usable:
        return None
    claim = usable[variant % len(usable)]
    words = next(words for text, words in UNSUPPORTED_CLAIMS if text == claim)
    return _build(
        source,
        "inject_unsupported_claim",
        "unsupported_claim",
        opening[1],
        opening[1],
        " " + claim,
        f"appended to the opening paragraph: {claim}",
        (*words, claim[:30]),
    )


def _wrong_version(version: str) -> str | None:
    parts = version.split(".")
    if not parts[0].isdigit():
        return None
    return ".".join([str(int(parts[0]) + 1), *parts[1:]])


def contradict_version(source: SourceCandidate) -> Mutation | None:
    versions = [f.value for f in source.facts.facts if f.id == "package:version"]
    if not versions:
        return None
    wrong = _wrong_version(versions[0])
    known = _fact_values(source)
    if wrong is None or wrong.lower() in known:
        return None
    position = _prose_occurrence(source.readme, versions[0])
    if position is None:
        return None
    return _build(
        source,
        "contradict_version",
        "contradiction",
        position,
        position + len(versions[0]),
        wrong,
        f"package version {versions[0]} stated as {wrong}",
        (wrong,),
    )


def contradict_package_name(source: SourceCandidate) -> Mutation | None:
    names = [f.value for f in source.facts.facts if f.id == "package:name"]
    if not names:
        return None
    name = names[0]
    wrong = f"{name}-core" if "-" in name else f"{name}.Core"
    if wrong.lower() in _fact_values(source):
        return None
    position = _prose_occurrence(source.readme, f"`{name}`")
    if position is None:
        return None
    return _build(
        source,
        "contradict_package_name",
        "contradiction",
        position + 1,
        position + 1 + len(name),
        wrong,
        f"package name `{name}` stated as `{wrong}` in prose",
        (wrong,),
    )


def contradict_format(source: SourceCandidate) -> Mutation | None:
    formats = [
        f.value
        for f in source.facts.facts
        if f.kind == "format" and f.polarity == "SUPPORTED" and f.value.startswith(".")
    ]
    known = _fact_values(source) + "\n" + source.readme.lower()
    foreign = next((ext for ext in FOREIGN_FORMATS if ext not in known), None)
    if foreign is None:
        return None
    for value in dict.fromkeys(formats):
        position = _prose_occurrence(source.readme, f"`{value}`")
        if position is not None:
            return _build(
                source,
                "contradict_format",
                "contradiction",
                position + 1,
                position + 1 + len(value),
                foreign,
                f"supported format `{value}` stated as `{foreign}`",
                (foreign,),
            )
    return None


def drop_section(source: SourceCandidate) -> Mutation | None:
    """Remove one whole ``##`` section: limitations first, then examples, then capabilities."""
    sections = h2_sections(source.readme)
    for wanted in ("scope", "limitation", "additional examples", "key capabilities"):
        for title, start, end in sections:
            if wanted in title.lower():
                return _build(
                    source,
                    "drop_section",
                    "content_loss",
                    start,
                    end,
                    "",
                    f"dropped the whole section '{title}'",
                    (title, wanted),
                )
    return None


def duplicate_paragraph(source: SourceCandidate) -> Mutation | None:
    """Repeat a prose paragraph of at least 120 characters, right after itself."""
    for s, e in paragraphs(source.readme):
        if e - s >= 120:
            text = source.readme[s:e]
            return _build(
                source,
                "duplicate_paragraph",
                "duplicate_paragraph",
                e,
                e,
                "\n\n" + text,
                f"repeated the paragraph beginning '{text[:60]}'",
                ("duplicat", "repeat", "redundan", text[:40]),
            )
    return None


def _transposed(command: str) -> str:
    """``command`` with the last two adjacent, different characters swapped: a typo that is
    neither a prefix nor a superstring of the real command."""
    for index in range(len(command) - 1, 0, -1):
        if command[index] != command[index - 1]:
            return (
                command[: index - 1]
                + command[index]
                + command[index - 1]
                + command[index + 1 :]
            )
    return command


def break_install_command(source: SourceCandidate) -> Mutation | None:
    commands = [
        f.value
        for f in source.facts.facts
        if f.kind == "install_command" and f.polarity == "SUPPORTED"
    ]
    fences = _fences(source.readme)
    for command in commands:
        position = source.readme.find(command)
        if position == -1 or not _inside(position, fences) or len(command) < 8:
            continue
        broken = _transposed(command)
        if broken == command:
            continue
        return _build(
            source,
            "break_install_command",
            "broken_install",
            position,
            position + len(command),
            broken,
            f"install command `{command}` printed as `{broken}`",
            (broken,),
        )
    return None


def invent_api_name(source: SourceCandidate) -> Mutation | None:
    known = _fact_values(source)
    symbols = {
        f.value
        for f in source.facts.facts
        if f.kind == "public_symbol" and f.polarity == "SUPPORTED"
    }
    fences = _fences(source.readme)
    for match in re.finditer(r"`([A-Za-z_][\w.]*)`", source.readme):
        name = match.group(1)
        if name not in symbols or len(name) < 5 or _inside(match.start(), fences):
            continue
        invented = name + "Turbo"
        if invented.lower() in known:
            continue
        return _build(
            source,
            "invent_api_name",
            "invented_api",
            match.start(1),
            match.end(1),
            invented,
            f"API name `{name}` printed as the nonexistent `{invented}`",
            (invented,),
        )
    return None


def add_promotional_filler(source: SourceCandidate) -> Mutation | None:
    opening = opening_paragraph(source.readme)
    if opening is None:
        return None
    return _build(
        source,
        "add_promotional_filler",
        "promotional_filler",
        opening[1],
        opening[1],
        " " + PROMOTIONAL_FILLER,
        "appended generic promotional filler to the opening paragraph",
        ("promotional", "cutting-edge", "best-in-class", "revolutioniz"),
    )


OPERATORS: dict[str, Callable[[SourceCandidate], Mutation | None]] = {
    "inject_unsupported_claim": inject_unsupported_claim,
    "contradict_version": contradict_version,
    "contradict_package_name": contradict_package_name,
    "contradict_format": contradict_format,
    "drop_section": drop_section,
    "duplicate_paragraph": duplicate_paragraph,
    "break_install_command": break_install_command,
    "invent_api_name": invent_api_name,
    "add_promotional_filler": add_promotional_filler,
}


def changed_span(clean: str, mutated: str) -> tuple[int, int, int]:
    """``(start, clean_end, mutated_end)``: the smallest region in which the two texts differ
    (common prefix and common suffix removed)."""
    limit = min(len(clean), len(mutated))
    start = 0
    while start < limit and clean[start] == mutated[start]:
        start += 1
    tail = 0
    while tail < limit - start and clean[-1 - tail] == mutated[-1 - tail]:
        tail += 1
    return start, len(clean) - tail, len(mutated) - tail
