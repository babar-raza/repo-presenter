"""A stated public-type count the facts refute outright, rewritten to the computed count.

BC-14 rule (h) (``readme/validation/surface_claims.py``) fails a README sentence that says "N public
types" when the SUPPORTED type-level ``public_symbol`` facts (class and enum) count differently, and
its own remedy is "state the computed count or none". When the stated number is BELOW the facts'
count the claim is refuted outright - every type fact names a defining location - so the number can
be replaced by the computed one without choosing between two readings. Real cases (Lane L re-
certification, 2026-11-09): Aspose.HTML FOSS for Python states 243 public types where the facts
record 303 (302 classes); Aspose.Words FOSS for Python states 146 where they record 198 (175).

Deliberately NOT fixed, and left to the validator's finding instead:

* a stated count ABOVE the facts' count - the maintainers may count kinds the extractor does not
  record (Aspose.PDF FOSS for .NET: 983 = 969 class/enum facts + 14 public delegates), so rewriting
  it could delete a true statement;
* a number that is itself split by a line break or a code span (an edit is one short fragment of
  one line); a sentence hard-wrapped around the number is matched, as the validator reads it.

Only the digits change; the surrounding words, the qualifier and the noun are untouched, and the
thousands separator style of the original is kept. The matching rule is ``surface_claims``' own
(`_TYPE_COUNT`, the "public" qualifier or a "public API surface" context on the same line), so a
claim this detector rewrites is exactly one that validator would have flagged.
"""

from __future__ import annotations

import re

from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.model import (
    FALSE_CLAIM_FIX,
    Context,
    DetectorResult,
    Edit,
    ReadmeLine,
)
from repo_presenter.readme.validation.surface_claims import (
    _PUBLIC_CONTEXT,
    _PUBLIC_QUALIFIER,
    _TYPE_COUNT,
    _evidence_type_count,
    _supported,
    type_counts,
)

DETECTOR = "stale_type_count"
_CITED = 8  # evidence facts named on an edit; the count is a function of all of them


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _paragraphs(ctx: Context) -> list[list[ReadmeLine]]:
    """Runs of consecutive prose lines (no fence, no table row, no blank line): a hard-wrapped
    README breaks a sentence over lines, and the validator reads the sentence, not the line."""
    runs: list[list[ReadmeLine]] = []
    current: list[ReadmeLine] = []
    for line in ctx.lines:
        if line.in_fence or not line.text.strip() or line.text.lstrip().startswith("|"):
            if current:
                runs.append(current)
            current = []
            continue
        current.append(line)
    if current:
        runs.append(current)
    return runs


def _sentence_around(joined: str, begin: int, end: int) -> str:
    cuts = [0] + [m.end() for m in _SENTENCE_END.finditer(joined)] + [len(joined)]
    for left, right in zip(cuts, cuts[1:]):
        if left <= begin < right:
            return joined[left:right]
    return joined


@detector(DETECTOR)
def stale_type_count(ctx: Context) -> DetectorResult:
    types, classes = type_counts(ctx.facts)
    if types == 0:
        return DetectorResult()
    allowed_types = {types, _evidence_type_count(ctx.facts)}
    symbols = _supported(ctx.facts, "public_symbol")
    cited = tuple(fact.id for fact in symbols[:_CITED])
    edits: list[Edit] = []
    for run in _paragraphs(ctx):
        # The paragraph as the validator reads it (code-span backticks dropped, line breaks as
        # single spaces), with the absolute README offset of every kept character (-1: a break).
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
            sentence = _sentence_around(joined, match.start(), match.end())
            if not (
                _PUBLIC_QUALIFIER.search(match.group("qualifiers"))
                or _PUBLIC_CONTEXT.search(sentence)
            ):
                continue
            stated_text = match.group("count")
            stated = int(stated_text.replace(",", ""))
            noun = match.group("noun").lower()
            allowed = allowed_types | ({classes} if noun == "classes" else set())
            floor = min(value for value in allowed if value > 0)
            if stated in allowed or stated >= floor:
                continue  # right, or not refuted outright (at or above a known count)
            span = where[match.start("count") : match.end("count")]
            if -1 in span or span != list(range(span[0], span[0] + len(span))):
                continue  # the number itself is split by a line break or a code span
            begin, finish = span[0], span[-1] + 1
            if ctx.readme[begin:finish] != stated_text:
                continue
            computed = classes if noun == "classes" else types
            replacement = f"{computed:,}" if "," in stated_text else str(computed)
            if replacement == stated_text:
                continue
            line_number = next(
                line.number for line in run if line.start <= begin <= line.end
            )
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector=DETECTOR,
                    start=begin,
                    end=finish,
                    original=stated_text,
                    replacement=replacement,
                    fact_ids=cited,
                    rationale=(
                        f"line {line_number} states {match.group(0).strip()!r}; the facts record "
                        f"{types} public types ({classes} classes), so a count of {stated} is "
                        f"refuted and is replaced by the computed {computed}"
                    ),
                )
            )
    return DetectorResult(edits=tuple(edits))
