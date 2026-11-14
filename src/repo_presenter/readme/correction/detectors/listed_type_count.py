"""A public-type count said to be "listed below" over fewer table rows, made true by stating both.

BC-14 rule (h) (``readme/validation/surface_claims.py``, BL-065/K05) fails a sentence that says its
"N public types" are listed below when the type-table rows that follow, up to the next level-1/2
heading, number fewer than N; its remedy is "state the count of what is listed, or list every
type". Real cases (Lane L, 2026-11-13), both made by this lane's own correction:

* Aspose.Cells FOSS for C++: "The full public surface — 197 public types — is listed below" over
  197 rows, eight of which (``BitReader``, ``XmlParser``, ``Workbook_Impl``, ...) name a type the
  public surface does not have and are removed (``absent_type_row``). The facts record 195 public
  types; 189 rows are left.
* Aspose.HTML FOSS for Python: "The library exposes 243 public types in total, listed below by
  module" over 243 rows; ``stale_type_count`` makes the total the computed 303 and
  ``absent_type_row`` removes five rows, so 238 are listed.

Which statement is true, decided from the facts:

* the number of rows is not the number of public types (195 / 303 recorded), so N must not become
  the row count — that would trade one false claim for another;
* the total stays the facts' count, and the sentence states how many of them the table lists:
  "..., 238 of them listed below by module" / "— 195 public types — has 189 of them listed
  below". The rows are never touched (R14), and no type is invented to fill the table;
* a stated total ABOVE the facts' count is left as written (``stale_type_count``'s rule: the
  maintainers may count kinds the extractor does not record), EXCEPT when the sentence's own total
  equalled its own table's row count and rows of that table were removed as absent from the public
  surface: then the total demonstrably counted types that are not public, and it becomes the
  facts' count (Cells C++: 197 -> 195).

The count this detector judges is the one the corrected README states (``stale_type_count``'s
replacement when it rewrites it) and the rows are those ``absent_type_row`` leaves, so the edit is
exactly what makes the corrected sentence pass rule (h) (``states_listed_count``). It fails closed
(no edit, the validator's finding stays) when the listed phrase is "as follows" (no short wording
that stays true), or is split by a line break or a code span.

Version 2 (BL-093, M9 round 43559491132): every listing verb rule (h) now reads -- listed, organized,
grouped, shown, documented, tabulated -- and "are <verb> ... below" is made true too:
PDF Python's "385 public types are organized by module below" (284 rows) becomes "385 public types —
284 of them organized by module below".
"""

from __future__ import annotations

import re

from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.detectors.absent_type_row import absent_type_row
from repo_presenter.readme.correction.detectors.stale_type_count import (
    _SENTENCE_END,
    _paragraphs,
    stale_type_count,
)
from repo_presenter.readme.correction.model import (
    FALSE_CLAIM_FIX,
    Context,
    DetectorResult,
    Edit,
    ReadmeLine,
)
from repo_presenter.readme.validation.surface_claims import (
    _LISTED_HERE,
    _PUBLIC_CONTEXT,
    _PUBLIC_QUALIFIER,
    _SECTION_HEADING,
    _TABLE_ROW,
    _TYPE_COUNT,
    _evidence_type_count,
    _supported,
    states_listed_count,
    type_counts,
)

DETECTOR = "listed_type_count"
_CITED = 8  # the same sample convention as stale_type_count / absent_type_row
_AUX = re.compile(r"(?i)^(?P<aux>is|are)\s+")
#: The leading "[is|are] <verb>" of a listing phrase: the words an edit rewrites.
_HEAD = re.compile(r"(?i)^(?:(?:is|are)\s+)?[\w-]+")


def _rows_after(lines: tuple[ReadmeLine, ...], number: int) -> list[ReadmeLine]:
    """The type-table rows after line ``number`` up to the next level-1/2 heading (rule (h)'s own
    reading, ``surface_claims._rows_listed_after``)."""
    rows: list[ReadmeLine] = []
    for line in lines:
        if line.number <= number or line.in_fence:
            continue
        if _SECTION_HEADING.match(line.text):
            break
        if _TABLE_ROW.match(line.text):
            rows.append(line)
    return rows


def _sentence_bounds(joined: str, at: int) -> tuple[int, int]:
    """``stale_type_count._sentence_around``'s cut, as offsets into ``joined``."""
    cuts = [0] + [m.end() for m in _SENTENCE_END.finditer(joined)] + [len(joined)]
    for left, right in zip(cuts, cuts[1:]):
        if left <= at < right:
            return left, right
    return 0, len(joined)


def _contiguous(span: list[int]) -> bool:
    return bool(span) and -1 not in span and span == list(range(span[0], span[0] + len(span)))


@detector(DETECTOR)
def listed_type_count(ctx: Context) -> DetectorResult:
    types, classes = type_counts(ctx.facts)
    if types == 0:
        return DetectorResult()
    allowed_types = {types, _evidence_type_count(ctx.facts)}
    cited = tuple(fact.id for fact in _supported(ctx.facts, "public_symbol")[:_CITED])
    removed = {edit.start for edit in absent_type_row(ctx).edits}
    rewritten = {edit.start: edit.replacement for edit in stale_type_count(ctx).edits}
    edits: list[Edit] = []
    claimed: set[int] = set()
    for run in _paragraphs(ctx):
        chars: list[str] = []
        where: list[int] = []
        for index, line in enumerate(run):
            if index:
                chars.append(" ")
                where.append(-1)
            for column, char in enumerate(line.text):
                if char != "`":
                    chars.append(char)
                    where.append(line.start + column)
        joined = "".join(chars)
        for match in _TYPE_COUNT.finditer(joined):
            offset, finish = _sentence_bounds(joined, match.start())
            sentence = joined[offset:finish]
            if not (
                _PUBLIC_QUALIFIER.search(match.group("qualifiers"))
                or _PUBLIC_CONTEXT.search(sentence)
            ):
                continue
            listed_here = _LISTED_HERE.search(sentence)
            if listed_here is None:
                continue
            noun = match.group("noun").lower()
            computed = classes if noun == "classes" else types
            last_char = next(
                (where[i] for i in range(finish - 1, offset - 1, -1) if where[i] >= 0), -1
            )
            last_line = next(line.number for line in run if line.start <= last_char <= line.end)
            rows = _rows_after(ctx.lines, last_line)
            left = [row for row in rows if row.start not in removed]
            if not left:
                continue
            stated_text = match.group("count")
            stated = int(stated_text.replace(",", ""))
            count_span = where[match.start("count") : match.end("count")]
            if not _contiguous(count_span) or ctx.readme[
                count_span[0] : count_span[-1] + 1
            ] != stated_text:
                continue
            final_text = rewritten.get(count_span[0], stated_text)
            final = int(final_text.replace(",", ""))
            allowed = allowed_types | ({classes} if noun == "classes" else set())
            count_edit: Edit | None = None
            if (
                count_span[0] not in rewritten
                and stated > max(allowed)
                and stated == len(rows)
                and len(left) < len(rows)
                and len(left) <= computed
            ):
                # The total was the table's own row count, and rows of that table name types the
                # public surface does not have: the total counted them, so it is refuted.
                final = computed
                count_line = next(
                    line.number for line in run if line.start <= count_span[0] <= line.end
                )
                final_text = f"{computed:,}" if "," in stated_text else str(computed)
                count_edit = Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector=DETECTOR,
                    start=count_span[0],
                    end=count_span[-1] + 1,
                    original=stated_text,
                    replacement=final_text,
                    fact_ids=cited,
                    rationale=(
                        f"line {count_line} states {match.group(0).strip()!r} as the count of the "
                        f"{len(rows)} table rows that follow, but {len(rows) - len(left)} of them "
                        "name a type no public_symbol fact records; the facts record "
                        f"{types} public types ({classes} classes), so the total is {computed}"
                    ),
                )
            if count_edit is not None:
                edits.append(count_edit)
            if len(left) >= final or states_listed_count(sentence, len(left)):
                continue  # the (corrected) total is what the table lists, or already says so
            if final not in allowed:
                # v2 (BL-093): a total the facts do not record (PDF .NET's 983 = 969 class/enum facts +
                # 14 delegates) is the maintainers' own; rewording its sentence would make it the
                # pipeline's claim without making it true. It stays, and its listed-count finding with
                # it (a pre-existing R21 residual when the rows were the live README's).
                continue
            phrase = listed_here.group(0)
            if phrase.lower() == "as follows":
                continue
            # v2: only the leading "[is|are] <verb>" is rewritten, so the rest of the phrase may wrap
            # onto the next line ("summarized in the module-grouped table" / "below.")
            head = _HEAD.match(phrase).group(0)
            phrase_at = offset + listed_here.start()
            span = where[phrase_at : phrase_at + len(head)]
            if not _contiguous(span) or ctx.readme[span[0] : span[-1] + 1] != head:
                continue
            if span[0] in claimed:
                continue
            aux = _AUX.match(head)
            listed_count = f"{len(left):,}" if "," in final_text else str(len(left))
            if aux is not None and aux.group("aux").lower() == "are":
                # v2 (BL-093): "385 public types are organized by module below" ->
                # "385 public types — 284 of them organized by module below"
                replacement = f"— {listed_count} of them {head[aux.end():]}"
            elif aux is not None:
                verb = "Has" if aux.group("aux")[0].isupper() else "has"
                replacement = f"{verb} {listed_count} of them {head[aux.end():]}"
            else:
                replacement = f"{listed_count} of them {head}"
            phrase = head
            claimed.add(span[0])
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector=DETECTOR,
                    start=span[0],
                    end=span[-1] + 1,
                    original=phrase,
                    replacement=replacement,
                    fact_ids=cited,
                    rationale=(
                        f"line {last_line} says its {final} public types are {phrase!r}, but the "
                        f"table rows that follow list {len(left)}; the total is the facts' and "
                        "stays, and the sentence now states how many are listed (no row dropped)"
                    ),
                )
            )
    return DetectorResult(edits=tuple(edits))
