"""BC-18: a false claim the findings register owes a correction for is no longer printed.

The register (``readme_findings``) holds, per repository, the exact README text an independent
reviewer confirmed false (``quote``) and the one sentence of what the source says (``truth``).
Nothing in the pipeline used to force the candidate to stop printing it: a Lane R candidate could
seal with the claim intact. This check fails while an OPEN Lane R row's quote is still in the
rendered README, and names where it is printed so the existing per-unit S4 patch (an inherited unit,
``repair/loop.py::_repair_reconciliation``) or per-section S6 repair (an authored section) is handed
the quote and the truth as its instruction.

No recurrence (owner, 2026-11-13: "an already caught problem should not reappear"): every quoted
row of the repository whose route is the candidate's lane is a permanent regression check, OPEN or
RESOLVED (``readme_findings.regression_rows``); only a row recorded as refuted (``is_refuted``: its
claim was true after all) never blocks. An OPEN row keeps its repair instruction and citation; a
RESOLVED row that is printed again is handed its stored truth as the instruction (it is not
citable -- the citation lookup stays OPEN-only). A Lane L candidate is held only to ``lane_l``-route
rows, a Lane R candidate only to ``lane_r``-route rows.

It is a no-op -- and so changes no existing seal's outcome -- when the register is missing, empty or
unreadable for the repository, or when no such row carries a quote.

The confirmed row is itself the evidence this check trusts, so a repair answering it may cite the
row (``FindingRecord.citation_id``, ``finding:<hex>``) wherever a disposition cites a fact:
CORRECT_WITH_EVIDENCE on prose, or a code block kept as written whose printed form then leaves
out exactly the lines that print the row's quote (``without_quoted_lines``). Measured (hosted Lane
R, 2026-11-13): PSD .NET run 43419183454 (a paragraph answered CORRECT_WITH_EVIDENCE with no fact
to cite) and Cells Java run 43419171411 (``mvn javadoc:javadoc   # generates
docs/apidocs/index.html`` inside a block of true build commands) were both unrepairable because
the repair had nothing it was allowed to cite. ``open_finding_citations`` is the one lookup every
reader of such a citation uses (binding, placement, BC-08, BC-17, the reviewer), and it admits only
OPEN rows of the repository being judged that carry a quote -- the rows this check enforces.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable
from pathlib import Path

from repo_presenter.readme.validation.failures import Candidate, Failure
from repo_presenter.readme.validation.text import section_texts
from repo_presenter.readme.validation.units import placements_of
from repo_presenter.readme_findings import (
    CITATION_PREFIX,
    DEFAULT_FINDINGS_PATH,
    LANE_L,
    LANE_R,
    STATUS_OPEN,
    FindingRecord,
    FindingsRegisterError,
    must_correct_rows,
    read_findings,
    regression_rows,
)


def _squash(text: str) -> str:
    return " ".join(text.split())


def open_finding_citations(
    repository: str | None, path: Path | None = None
) -> dict[str, FindingRecord]:
    """Every citable register row, by its ``citation_id``: the OPEN Lane R rows that carry a
    quote, of ``repository`` (or of every repository when it is ``None`` -- the ID already embeds
    its repository, so a reader without one, the parity gate's sealed view, cannot mistake it).
    A missing or unreadable register cites nothing."""
    register = path if path is not None else DEFAULT_FINDINGS_PATH
    try:
        if repository is not None:
            rows = must_correct_rows(repository, register)
        else:
            rows = [
                row
                for row in read_findings(register)
                if row.route == LANE_R and row.status == STATUS_OPEN and row.quote
            ]
    except (OSError, ValueError, FindingsRegisterError):
        return {}
    return {row.citation_id(): row for row in rows}


def cited_finding_quotes(
    fact_ids: Iterable[object], repository: str | None, path: Path | None = None
) -> list[str]:
    """The quotes of the OPEN register rows ``fact_ids`` cite; empty (and the register unread)
    when none of them is a register citation."""
    cited = [str(fid) for fid in fact_ids if str(fid).startswith(CITATION_PREFIX)]
    if not cited:
        return []
    rows = open_finding_citations(repository, path)
    return [rows[fid].quote for fid in cited if fid in rows]


def quoted_lines(text: str, quotes: Collection[str]) -> list[int]:
    """The indexes of the lines inside ``text``'s code fence that print one of ``quotes`` (both
    whitespace-squashed, as BC-18 matches). The fence lines themselves never count."""
    wanted = [_squash(quote) for quote in quotes if _squash(quote)]
    if not wanted:
        return []
    lines = text.split("\n")
    return [
        index
        for index, line in enumerate(lines)
        if not line.lstrip().startswith(("```", "~~~"))
        and any(quote in _squash(line) for quote in wanted)
    ]


def without_quoted_lines(text: str, quotes: Collection[str]) -> str:
    """A kept code block's printed form without the lines a cited register row confirms false.
    Unchanged when no line prints a quote, or when every line of the block's body does (nothing
    would be left to keep: that block is withheld, not kept)."""
    drop = set(quoted_lines(text, quotes))
    if not drop:
        return text
    lines = text.split("\n")
    body = [
        index
        for index, line in enumerate(lines)
        if line.strip() and not line.lstrip().startswith(("```", "~~~"))
    ]
    if set(body) <= drop:
        return text
    return "\n".join(line for index, line in enumerate(lines) if index not in drop)


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`\[(*_])")


def without_quoted_sentences(text: str, quotes: Collection[str]) -> str:
    """A kept paragraph's printed form without the sentences that print a cited register row's
    quote (the shortest run of consecutive sentences holding it, whitespace-squashed as BC-18
    matches). Every other sentence is printed exactly as written. Unchanged when no sentence run
    holds a quote, or when the quote takes the whole paragraph (that unit is withheld, not kept)."""
    wanted = [_squash(quote) for quote in quotes if _squash(quote)]
    if not wanted:
        return text
    cuts = [0, *(match.end() for match in _SENTENCE_END.finditer(text))]
    spans = [(start, end) for start, end in zip(cuts, [*cuts[1:], len(text)])]
    drop: set[int] = set()
    for quote in wanted:
        best: tuple[int, int] | None = None
        for first in range(len(spans)):
            for last in range(first, len(spans)):
                if quote in _squash(text[spans[first][0] : spans[last][1]]):
                    if best is None or last - first < best[1] - best[0]:
                        best = (first, last)
                    break
        if best is not None:
            drop.update(range(best[0], best[1] + 1))
    if not drop or len(drop) == len(spans):
        return text
    kept = "".join(text[start:end] for index, (start, end) in enumerate(spans) if index not in drop)
    return kept.rstrip()


def withheld_form(unit_id: str, text: str, quotes: Collection[str]) -> str:
    """The printed form of a kept unit whose disposition cites OPEN register rows with these
    quotes: a code block without the lines that print them, a paragraph without the sentences
    that do. Any other kind is unchanged (it is corrected or withheld as a whole)."""
    if not quotes:
        return text
    if unit_id.endswith(".code_block"):
        return without_quoted_lines(text, quotes)
    if unit_id.endswith(".paragraph"):
        return without_quoted_sentences(text, quotes)
    return text


def omission_holds(unit_id: str, text: str, quotes: Collection[str]) -> bool:
    """Whether keeping the unit while citing these quotes stops it printing every one of them,
    with something of it still left to print."""
    printed = _squash(withheld_form(unit_id, text, quotes))
    return bool(quotes) and bool(printed) and not any(
        _squash(quote) in printed for quote in quotes
    )


def withheld_text_holds(unit_id: str, text: str, quotes: Collection[str], item: str) -> bool:
    """Whether ``item`` (a command, an identifier, a block) is printed by the unit as written but
    not by its withheld form: the part of it the cited register rows confirm false."""
    wanted = _squash(item)
    if not wanted or wanted not in _squash(text):
        return False
    return wanted not in _squash(withheld_form(unit_id, text, quotes))


def line_omission_holds(text: str, quotes: Collection[str]) -> bool:
    """Whether keeping a code block with these cited quotes stops it printing every one of them."""
    return omission_holds(".code_block", text, quotes)


def _instruction(row: FindingRecord) -> str:
    truth = row.truth or "remove or correct the claim"
    return (
        f"The README text {row.quote!r} is false ({row.description}). Correct it: {truth}"
        + (f" (evidence: {row.evidence})" if row.evidence else "")
        + f". The confirmed register row is citable evidence: cite {row.citation_id()} in fact_ids"
    )


def _regression_instruction(row: FindingRecord) -> str:
    truth = row.truth or "remove or correct the claim"
    return (
        f"The README text {row.quote!r} was confirmed false ({row.description}) and corrected before"
        f"; it must never be printed again. Correct it: {truth}"
        + (f" (evidence: {row.evidence})" if row.evidence else "")
    )


def must_correct_failures(candidate: Candidate) -> list[Failure]:
    """One failure per place a register quote (an open row, or a resolved one printed again) is
    printed."""
    route = LANE_L if candidate.lane.upper() in ("L", "LANE_L") else LANE_R
    try:
        rows = regression_rows(
            candidate.entry.repository,
            route,
            candidate.findings_path if candidate.findings_path is not None else DEFAULT_FINDINGS_PATH,
        )
    except (OSError, ValueError, FindingsRegisterError):
        return []
    if not rows:
        return []
    readme = _squash(candidate.readme)
    printed = [row for row in rows if _squash(row.quote) in readme]
    if not printed:
        return []
    placed = [(p.unit_id, _squash(p.text)) for p in placements_of(candidate) if p.outcome == "placed"]
    sections = {name: _squash(text) for name, text in section_texts(candidate.readme).items()}
    failures: list[Failure] = []
    for row in printed:
        quote = _squash(row.quote)
        if row.status == STATUS_OPEN:
            instruction = _instruction(row)
            detail = f"open finding ({row.description}) still printed: {instruction}"
        else:
            instruction = _regression_instruction(row)
            detail = f"resolved finding ({row.description}) printed again: {instruction}"
        units = [unit for unit, text in placed if quote in text]
        if units:
            failures.extend(
                Failure("RECONCILING", detail, unit=unit, quote=row.quote, instruction=instruction)
                for unit in units
            )
            continue
        named = [name for name, text in sections.items() if quote in text]
        failures.extend(
            Failure("COMPOSING", detail, section=name, quote=row.quote, instruction=instruction)
            for name in (named or [None])
        )
    return failures
