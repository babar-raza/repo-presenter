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
from collections.abc import Collection, Iterable, Mapping
from pathlib import Path
from typing import Any

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


_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def prints_quote(text: str, quote: str) -> bool:
    """Whether ``text`` prints ``quote`` (both squashed): as written, or with its markdown links
    reduced to their labels (``flat_squash``), the two ways the README can print a kept unit."""
    wanted = _squash(quote)
    return bool(wanted) and (wanted in _squash(text) or wanted in flat_squash(text))


def flat_squash(text: str) -> str:
    """``text`` squashed, with each markdown link reduced to its label: the README prints a kept
    unit's link as its label when its target is not printable (Words .NET ``013.paragraph``:
    "(see [the story](#the-story-behind-this-code) below)" reads "(see the story below)"), and a
    register quote is that printed text (BL-210)."""
    return _squash(_MD_LINK.sub(r"\1", text))


#: The rationale ``reconciliation.dispositions._fold_register_omitted_units`` writes on an
#: inherited unit it omits citing the findings register rows that refute it (audit O4, BL-088).
#: The register row is the recorded R14 decision; BC-17 (``parity_gate.disposition_is_non_loss``),
#: live_readme_loss (an accounting disposition with a cited row) and S4's own coverage self-audit
#: (``_omission_gap``) all read this marker plus the citation, so they cannot disagree.
REGISTER_OMITTED_RATIONALE = "Omitted citing the findings register, which confirms it false: "


def is_register_omission(entry: Mapping[str, Any], path: Path | None = None) -> bool:
    """Whether a disposition is an omission on the findings register's evidence: OMIT_UNSUPPORTED,
    the fold's own rationale, and at least one cited OPEN register row that carries a quote."""
    return (
        entry.get("disposition") == "OMIT_UNSUPPORTED"
        and str(entry.get("rationale") or "").startswith(REGISTER_OMITTED_RATIONALE)
        and bool(cited_finding_quotes(entry.get("fact_ids") or (), None, path))
    )


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
                if prints_quote(text[spans[first][0] : spans[last][1]], quote):
                    if best is None or last - first < best[1] - best[0]:
                        best = (first, last)
                    break
        if best is not None:
            drop.update(range(best[0], best[1] + 1))
    if not drop or len(drop) == len(spans):
        return text
    kept = "".join(text[start:end] for index, (start, end) in enumerate(spans) if index not in drop)
    return kept.rstrip()


def without_quoted_rows(text: str, quotes: Collection[str]) -> str:
    """A kept table's printed form without the body rows that print a cited register row's quote
    (each row whitespace-squashed, as BC-18 matches). The header and its separator always stay.
    Unchanged when no row prints a quote, or when every body row does (that table is withheld,
    not kept)."""
    wanted = [_squash(quote) for quote in quotes if _squash(quote)]
    if not wanted:
        return text
    lines = text.split("\n")
    body = [
        index
        for index, line in enumerate(lines)
        if index >= 2 and line.strip().startswith("|")
    ]
    drop = {index for index in body if any(prints_quote(lines[index], quote) for quote in wanted)}
    # A quote that spans rows (Words .NET ``049.table``: a whole row and the start of the next)
    # withholds the rows its lines print in full; the row it only begins stays.
    for raw in quotes:
        parts = [flat_squash(part) for part in raw.split("\n") if part.strip()]
        if len(parts) < 2:
            continue
        for index in body:
            if flat_squash(lines[index]) == parts[0] and all(
                body_index in body and flat_squash(lines[body_index]).startswith(part)
                for body_index, part in zip(range(index + 1, index + len(parts)), parts[1:])
            ):
                drop.add(index)
    if not drop or set(body) <= drop:
        return text
    return "\n".join(line for index, line in enumerate(lines) if index not in drop)


_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def without_quoted_items(text: str, quotes: Collection[str]) -> str:
    """A kept list's printed form without the items (a marker line, its continuation lines and
    its nested sub-items) that print a cited register row's quote: the innermost item that prints
    it, so a quote in a nested sub-item withholds that sub-item only (P2, 2026-11-14: Email C++'s
    two signature bullets sit under the single top-level item of ``053.list`` and
    ``059.003.list``). Unchanged when no item prints one, or when every item does (that list is
    withheld, not kept)."""
    wanted = [_squash(quote) for quote in quotes if _squash(quote)]
    if not wanted:
        return text
    # One block per item marker line, at any depth, with its continuation lines; a block's
    # subtree is the block and every deeper block right after it.
    blocks: list[tuple[int, list[str]]] = []
    lead: list[str] = []
    for line in text.split("\n"):
        if _LIST_ITEM.match(line):
            blocks.append((len(line) - len(line.lstrip(" \t")), [line]))
        elif blocks:
            blocks[-1][1].append(line)
        else:
            lead.append(line)
    if not blocks:
        return text

    def subtree_end(index: int) -> int:
        end = index + 1
        while end < len(blocks) and blocks[end][0] > blocks[index][0]:
            end += 1
        return end

    def joined(start: int, end: int) -> str:
        return "\n".join(line for _depth, lines in blocks[start:end] for line in lines)

    # Each quote withholds the innermost item that prints it whole: a nested sub-item when the
    # quote sits inside it (Email C++ ``053.list``/``059.003.list``: a signature bullet under the
    # one top-level type item, which withheld whole would withhold the whole list), else the
    # nearest enclosing item, as for a top-level item.
    dropped = [False] * len(blocks)
    ends = [subtree_end(index) for index in range(len(blocks))]
    for quote in wanted:
        holding = [prints_quote(joined(index, ends[index]), quote) for index in range(len(blocks))]
        for index in range(len(blocks)):
            if not holding[index] or any(holding[child] for child in range(index + 1, ends[index])):
                continue
            for member in range(index, ends[index]):
                dropped[member] = True
    if not any(dropped) or all(dropped):
        return text
    kept = [line for (_depth, lines), drop in zip(blocks, dropped) if not drop for line in lines]
    return "\n".join([*lead, *kept])


def withheld_form(unit_id: str, text: str, quotes: Collection[str]) -> str:
    """The printed form of a kept unit whose disposition cites OPEN register rows with these
    quotes: a code block without the lines that print them, a paragraph without the sentences
    that do, a table without the rows and a list without the items that do. Any other kind is
    unchanged (it is corrected or withheld as a whole).

    Tables and lists (hosted Lane R runs 43473790998, 3D .NET ``050.table``, and 43473796319, 3D
    Python ``060.table`` / ``010.list``): the register confirmed single rows of the maintainers'
    type table false after the seal that restored it, so keeping the table printed them (BC-18) and
    superseding it lost its true rows' members (BC-05/BC-17) -- no disposition could pass."""
    if not quotes:
        return text
    if unit_id.endswith(".code_block"):
        return without_quoted_lines(text, quotes)
    if unit_id.endswith(".paragraph"):
        return without_quoted_sentences(text, quotes)
    if unit_id.endswith(".table"):
        return without_quoted_rows(text, quotes)
    if unit_id.endswith(".list"):
        return without_quoted_items(text, quotes)
    return text


def withheld_rows_form(unit_id: str, text: str, quotes: Collection[str]) -> str:
    """``withheld_form`` for the kinds ``surface_claims.kept_unit_form`` does not withhold itself
    (a table's rows, a list's items); every other kind is returned as given. The renderer
    (``placement``) and the reviewer's printed test apply it before ``kept_unit_form``."""
    if quotes and unit_id.endswith((".table", ".list")):
        return withheld_form(unit_id, text, quotes)
    return text


def omission_holds(unit_id: str, text: str, quotes: Collection[str]) -> bool:
    """Whether keeping the unit while citing these quotes stops it printing every one of them,
    with something of it still left to print."""
    printed = withheld_form(unit_id, text, quotes)
    return bool(quotes) and bool(_squash(printed)) and not any(
        prints_quote(printed, quote) for quote in quotes
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


# --- BL-210: the correction BC-18 owes, applied before the seal ----------------------------------
#
# BC-18 only ever *judged*: a sentence an OPEN register row confirms false stayed printed until a
# model repair happened to drop it, and when the false text was the whole unit the repair refused
# (3D .NET ``scene.Save("output.obj", FileFormat.WavefrontOBJ);``, four hosted runs running).
# ``register_corrected`` is the deterministic, zero-call correction of the AUTHORED text: it
# withholds exactly what a row confirms false (a sentence, or a whole capability / API hub when
# nothing true is left of it) and returns an R14 record per change, citing the row. The inherited
# half is ``reconciliation.dispositions._fold_register_kept_units``; the plan's examples are
# ``corrected_plan_examples``. Measured on the 8 failing Lane R seals (``recertify --all``).

#: The rule id every record of this correction carries (R14).
REGISTER_CORRECTION_RULE = "BL-210"
#: A register quote or unit text shorter than this (plain, squashed) is never matched by containment.
_MIN_MATCH = 12


def _plain(text: str) -> str:
    return " ".join(text.replace("`", "").split())


def _correction_rows(repository: str, path: Path | None) -> list[FindingRecord]:
    try:
        rows = regression_rows(repository, LANE_R, path if path is not None else DEFAULT_FINDINGS_PATH)
    except (OSError, ValueError, FindingsRegisterError):
        return []
    return [row for row in rows if len(_plain(row.quote)) >= _MIN_MATCH]


def _record(slot: str, section: str, rows: Collection[FindingRecord], action: str) -> dict[str, Any]:
    return {
        "rule": REGISTER_CORRECTION_RULE,
        "slot": slot,
        "section": section,
        "action": action,
        "findings": sorted(row.citation_id() for row in rows),
    }


def register_corrected(
    plan: Mapping[str, Any],
    units: Mapping[str, Any],
    repository: str,
    path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """``(plan, units, records)`` with the authored text a register row confirms false withheld.

    * A unit whose text prints a row's quote loses the shortest run of sentences that prints it
      (``without_quoted_sentences``); every other sentence is kept as written.
    * A unit that is nothing but the false text (its text is the quote, or lies inside it) is
      dropped when its slot can stand without it: a capability leaves the plan and the later ones
      are renumbered; an API hub or type row falls back to the renderer's fact-true row (R43(4),
      recorded the way that fallback already is). The opening and the other prose slots are never
      dropped: they stay for BC-18 to judge.
    * Pure and idempotent; with no register rows, or nothing printing one, the inputs come back
      unchanged and ``records`` is empty. Each change is one R14 record naming the rule and the
      register rows (also appended to ``units["register_corrections"]``).
    """
    import copy

    rows = _correction_rows(repository, path)
    unit_list = [u for u in units.get("units", []) if isinstance(u, Mapping)]
    if not rows or not unit_list:
        return dict(plan), dict(units), []
    new_plan = copy.deepcopy(dict(plan))
    new_units = copy.deepcopy(dict(units))
    records: list[dict[str, Any]] = []
    dropped_caps: list[int] = []
    omitted = list(new_units.get("omitted") or [])
    kept: list[dict[str, Any]] = []
    for unit in new_units["units"]:
        slot, section = str(unit.get("slot", "")), str(unit.get("section", ""))
        text = str(unit.get("text", ""))
        plain = _plain(text)
        inside = [r for r in rows if _plain(r.quote) in plain]
        covering = [r for r in rows if len(plain) >= _MIN_MATCH and plain in _plain(r.quote)]
        if not inside and not covering:
            kept.append(unit)
            continue
        # A quote that is the whole unit cannot be withheld sentence by sentence, but withholding the
        # sentences the other rows confirm false changes the unit, so it no longer prints it
        # (Cells C++ opening: one row quotes the whole paragraph, another its third sentence).
        partial = [r for r in inside if _plain(r.quote) != plain]
        if partial:
            corrected = without_quoted_sentences(text, [_plain(r.quote) for r in partial]).strip()
            if (
                corrected
                and corrected != text
                and not any(_plain(r.quote) in _plain(corrected) for r in rows)
            ):
                unit["text"] = corrected
                records.append(_record(slot, section, inside, "sentence_withheld"))
                kept.append(unit)
                continue
        involved = [*inside, *covering]
        if slot.startswith("capability:") and slot.split(":", 1)[1].isdigit():
            dropped_caps.append(int(slot.split(":", 1)[1]))
            records.append(_record(slot, section, involved, "capability_dropped"))
            continue
        if slot.startswith(("hub:", "type:")):
            from repo_presenter.readme.composition.authoring import API_ROW_FALLBACK_REASON

            omitted.append(
                {
                    "fact_id": slot.split(":", 1)[1],
                    "reason": API_ROW_FALLBACK_REASON
                    + f"; withheld by {REGISTER_CORRECTION_RULE}: the findings register "
                    "confirms its text false",
                    "section": section,
                }
            )
            records.append(_record(slot, section, involved, "api_row_fallback"))
            continue
        kept.append(unit)
    if dropped_caps:
        gone = sorted(set(dropped_caps))
        caps = new_plan.get("core_capabilities", [])
        new_plan["core_capabilities"] = [c for i, c in enumerate(caps, start=1) if i not in gone]
        renumbered: list[dict[str, Any]] = []
        for unit in kept:
            slot = str(unit.get("slot", ""))
            if slot.startswith("capability:") and slot.split(":", 1)[1].isdigit():
                index = int(slot.split(":", 1)[1])
                unit["slot"] = f"capability:{index - sum(1 for g in gone if g < index)}"
            renumbered.append(unit)
        kept = renumbered
    new_units["units"] = kept
    if omitted != list(new_units.get("omitted") or []):
        new_units["omitted"] = omitted
    if records:
        new_units["register_corrections"] = [*new_units.get("register_corrections", []), *records]
    return new_plan, new_units, records


def corrected_plan_examples(
    plan: Mapping[str, Any], units: Mapping[str, Any], facts: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(plan, units)`` without the planned examples whose code prints a line a register row
    confirms false (``planning.register_refuted_example_ids``; a fresh plan can no longer select
    them, a sealed plan still may - BL-210).

    A refuted additional example leaves ``additional_example_ids`` with its ``workflow:`` unit. A
    refuted Quick Start example is replaced by the next example that is not refuted: the second
    Quick Start one, else an additional one. The replacement brings the text already authored
    about it (``lead_in:2`` / its ``workflow:`` unit) as the slot's lead-in, so the lead-in always
    describes the code printed under it; a refuted second Quick Start example with nothing to
    replace it is dropped with its lead-in. A refuted first one with nothing to replace it stays
    (the section must print code), for BC-18 to judge. One R14 record per change."""
    from repo_presenter.readme.composition.planning import register_refuted_example_ids

    refuted = register_refuted_example_ids(facts)
    first = plan.get("quick_start_example_id")
    second = plan.get("second_quick_start_example_id")
    additional = list(plan.get("additional_example_ids", []))
    if not refuted or not (first in refuted or second in refuted or any(i in refuted for i in additional)):
        return dict(plan), dict(units)
    new_plan = dict(plan)
    new_units = dict(units)
    all_units = [dict(u) for u in units.get("units", []) if isinstance(u, Mapping)]
    records: list[dict[str, Any]] = []

    def unit_of(slot: str) -> dict[str, Any] | None:
        return next((u for u in all_units if u.get("slot") == slot), None)

    def drop(slot: str) -> None:
        all_units[:] = [u for u in all_units if u.get("slot") != slot]

    def note(slot: str, example_id: str, action: str, replacement: str = "") -> None:
        records.append(
            {"rule": REGISTER_CORRECTION_RULE, "slot": slot, "section": "examples",
             "action": action, "example": example_id, "replacement": replacement, "findings": []}
        )

    pool: list[tuple[str, str]] = []  # (example id, slot of the unit that introduces it)
    if second and second not in refuted:
        pool.append((str(second), "lead_in:2"))
    for example_id in additional:
        if example_id not in refuted and example_id not in (first, second):
            pool.append((str(example_id), f"workflow:{example_id}"))

    def replace(slot: str, old: Any) -> bool:
        if not pool:
            return False
        example_id, source_slot = pool.pop(0)
        source = unit_of(source_slot)
        target = unit_of(slot)
        if source is None or target is None:
            return False
        target["text"] = source.get("text", "")
        target["fact_ids"] = list(dict.fromkeys([example_id, *source.get("fact_ids", [])]))
        key = "quick_start_example_id" if slot == "lead_in" else "second_quick_start_example_id"
        new_plan[key] = example_id
        if source_slot == "lead_in:2":
            new_plan["second_quick_start_example_id"] = None
        else:
            new_plan["additional_example_ids"] = [
                i for i in new_plan.get("additional_example_ids", []) if i != example_id
            ]
        drop(source_slot)
        note(key, str(old), "example_replaced", example_id)
        return True

    if first in refuted:
        replace("lead_in", first)
    if second in refuted:
        if not replace("lead_in:2", second):
            new_plan["second_quick_start_example_id"] = None
            drop("lead_in:2")
            note("second_quick_start_example_id", str(second), "example_withheld")
    for example_id in [i for i in new_plan.get("additional_example_ids", []) if i in refuted]:
        new_plan["additional_example_ids"] = [
            i for i in new_plan["additional_example_ids"] if i != example_id
        ]
        drop(f"workflow:{example_id}")
        if new_plan.get("flagship_example_id") == example_id:
            new_plan["flagship_example_id"] = None
        note(f"workflow:{example_id}", str(example_id), "example_withheld")
    new_units["units"] = all_units
    new_units["register_corrections"] = [*new_units.get("register_corrections", []), *records]
    return new_plan, new_units


def withheld_printed_text(readme: str, repository: str, path: Path | None = None) -> str:
    """The rendered README without the lines and sentences an OPEN register row confirms false that
    reach it from no unit this module can correct: text the renderer derives from facts (the
    Dependencies sentence, an API table row), the last stop of BL-210's correction.

    Outside code fences and tables only. A line that is the whole quote is dropped; otherwise the shortest run of sentences holding it
    is withheld from its line. Anything a quote still matches afterwards stays for BC-18 to judge,
    and a README no row is printed in is returned unchanged (so a passing seal never changes)."""
    rows = _correction_rows(repository, path)
    if not rows:
        return readme
    flat = flat_squash(readme)
    quotes = [q for q in (flat_squash(r.quote) for r in rows) if q in flat]
    if not quotes:
        return readme
    lines = readme.split("\n")
    drop: set[int] = set()
    inside = False
    for index, line in enumerate(lines):
        if line.strip().startswith(("```", "~~~")):
            inside = not inside
            continue
        if inside or not line.strip():
            continue
        plain = flat_squash(line)
        for raw in rows:
            parts = [flat_squash(p) for p in raw.quote.split("\n") if p.strip()]
            for part in parts:
                if not part or len(part) < _MIN_MATCH:
                    continue
                if line.lstrip().startswith("|"):
                    continue  # a table row is a unit's or the API table's: never dropped here
                elif plain == part:
                    drop.add(index)
                elif part in plain and len(parts) == 1:
                    kept = without_quoted_sentences(line, [part])
                    if kept != line and part not in flat_squash(kept):
                        lines[index] = kept
    # A heading whose whole body was withheld goes with it (nothing is left under it to print).
    for index, line in enumerate(lines):
        if not line.startswith("#") or index in drop:
            continue
        body = []
        for follow in range(index + 1, len(lines)):
            if lines[follow].startswith("#"):
                break
            body.append(follow)
        if any(i in drop for i in body) and all(i in drop or not lines[i].strip() for i in body):
            drop.add(index)
    kept_lines = [line for index, line in enumerate(lines) if index not in drop]
    return "\n".join(kept_lines)
