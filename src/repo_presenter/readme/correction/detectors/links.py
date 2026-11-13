"""Broken relative links: a README link whose target the pinned tree does not contain.

The link facts already record, per README link, the line it sits on and whether the tree contains
its target. A link is repaired only to a path the tree does contain, found deterministically (the
same path with different letter case, else the one file of that name); with no unique repair it is
reported and left exactly as written - deleting a maintainer's link, or guessing where it should
point, is not a correction.

Ported (ADAPT, import paths only) from the old repository's
``components/readme_correction/detectors/links.py`` per ``migration/reuse-manifest.yaml`` -- this
detector is genuinely self-contained (only ``model.py`` and stdlib), so nothing else changed.
"""

from __future__ import annotations

import posixpath
import re
from urllib.parse import quote

from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.model import (
    BROKEN_LINK,
    Context,
    DetectorResult,
    Edit,
    Finding,
    ReadmeLine,
)

_WHERE = re.compile(r"^line (\d+); (\w+);")
_MISSING_IN_TREE = re.compile(r"^MISSING: tree does not contain ")
_GITHUB_WEB = re.compile(
    r"^(?:\.\./)+(?:issues|pulls?|wiki|discussions|actions|releases|projects|security|tags|labels"
    r"|milestones|compare|commits?)(?:[/?#].*)?$"
)


def _repair(ctx: Context, target: str) -> str | None:
    """The unique tracked path ``target`` was meant to name, as a link from the README, or None."""
    base = posixpath.dirname(ctx.readme_path)
    wanted = posixpath.normpath(posixpath.join(base, target.split("#", 1)[0]))
    pool = [path for path in ctx.tree_paths if path != ctx.readme_path]
    same_path = [path for path in pool if path.lower() == wanted.lower()]
    named = [path for path in pool if posixpath.basename(path) == posixpath.basename(wanted)]
    for candidates in (same_path, named):
        if len(candidates) == 1:
            relative = posixpath.relpath(candidates[0], base or ".")
            anchor = target.split("#", 1)[1] if "#" in target else ""
            return relative + (f"#{anchor}" if anchor else "")
    return None


def _line_holding(ctx: Context, number: int, forms: list[str]) -> ReadmeLine:
    """The README line that holds the link a fact records at line ``number``.

    The link facts record the line their block starts on (markdown-it's block map), so a link in
    the second or later line of a soft-wrapped paragraph - a badge row written one badge per line,
    Aspose.PSD-FOSS-for-Python's ``[![License: MIT](...)](License/LICENSE.txt)`` on line 5 of a
    block starting on line 3 - is not on its recorded line. The block's own lines, up to its first
    blank line, are searched; exactly one of them holding the link is that line. Anything else
    keeps the recorded line, so the finding below still reports it as not found or ambiguous.
    """
    recorded = ctx.lines[number - 1]
    if any(f"]({form}" in recorded.text for form in forms):
        return recorded
    block: list[ReadmeLine] = []
    for line in ctx.lines[number - 1 :]:
        if not line.text.strip():
            break
        block.append(line)
    holding = [line for line in block if any(f"]({form}" in line.text for form in forms)]
    return holding[0] if len(holding) == 1 else recorded


@detector("broken_link")
def broken_link(ctx: Context) -> DetectorResult:
    edits: list[Edit] = []
    findings: list[Finding] = []
    for fact in ctx.facts.by_kind("link_target"):
        if fact.polarity != "CONTRADICTED" or len(fact.evidence) < 2:
            continue
        where = _WHERE.match(fact.evidence[0].detail or "")
        if (
            where is None
            or where.group(2) != "relative"
            or not _MISSING_IN_TREE.match(fact.evidence[1].detail or "")
        ):
            continue
        if _GITHUB_WEB.match(fact.value):
            continue  # ../../issues resolves on github.com to the repository's issues page
        number = int(where.group(1))
        if not 1 <= number <= len(ctx.lines):
            continue
        target = fact.value
        forms = [target, quote(target, safe="/#:@")]
        line = _line_holding(ctx, number, forms)
        spelled = next((form for form in forms if f"]({form}" in line.text), None)
        if spelled is None:
            findings.append(
                Finding(
                    "broken_link",
                    number,
                    line.text,
                    f"link to {target!r} not found on its line",
                    (fact.id,),
                )
            )
            continue
        index = line.text.find(f"]({spelled}") + 2
        end = index + len(spelled)
        if line.text.count(f"]({spelled}") != 1 or line.text[end : end + 1] not in {")", " "}:
            findings.append(
                Finding(
                    "broken_link",
                    number,
                    line.text,
                    f"link to {target!r} is ambiguous on its line",
                    (fact.id,),
                )
            )
            continue
        repaired = _repair(ctx, target)
        if repaired is None:
            findings.append(
                Finding(
                    "broken_link",
                    number,
                    line.text,
                    f"{target!r} is not in the tree and no unique file stands in for it",
                    (fact.id,),
                )
            )
            continue
        replacement = quote(repaired, safe="/#:@") if spelled != target else repaired
        rationale = f"the tree does not contain {target!r}; it contains {repaired!r}"
        # A link fact is one distinct target; the README may link it from more than one line
        # (PSD Python: the License badge and the License section's "[MIT License](...)"). Every
        # prose line linking it exactly once, unambiguously, gets the same repair.
        for holder in (
            line,
            *(
                other
                for other in ctx.lines
                if other is not line
                and not other.in_fence
                and other.text.count(f"]({spelled}") == 1
            ),
        ):
            at = holder.text.find(f"]({spelled}") + 2
            stop = at + len(spelled)
            if holder.text[stop : stop + 1] not in {")", " "}:
                continue
            edits.append(
                Edit(
                    kind=BROKEN_LINK,
                    detector="broken_link",
                    start=holder.start + at,
                    end=holder.start + stop,
                    original=spelled,
                    replacement=replacement,
                    fact_ids=(fact.id,),
                    rationale=rationale,
                )
            )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
