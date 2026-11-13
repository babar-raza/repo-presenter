"""A text link to a file the tree does not contain at all, with nothing to repair it to: unlinked,
its anchor text kept word for word.

``links.broken_link`` repairs a missing target to the one file that stands in for it, and
``versioned_link_target`` to the unique newest versioned sibling. Neither applies when the tree
holds nothing the link could mean, and ``broken_link`` then reports the link as an unrepaired
defect, which blocks the whole Lane L candidate. Cells .NET (``RELEASE_NOTES_V26.10.0.md``) and
Cells Python (``RELEASE_NOTES.md``) are the real case: at their pinned revisions the trees hold no
release-notes file of any name (checked 2026-11-13), so the README sends a reader to a 404.

Decision (owner rulings R14/R21, ``docs/DECISION_LOG.md`` 2026-11-13): a dead link is a verified
defect, and removing only the dead target while printing the maintainer's words unchanged loses
nothing a reader could use. Guessing a new target is still never done. Only a plain
``[text](target)`` link is unlinked; an image, an empty anchor, or a link that is not alone on its
line in that exact spelling is left to ``broken_link``'s report.

A separate detector, not a change to ``broken_link``, so that no sealed Lane L candidate's recorded
``detectors.broken_link`` version is reopened (R10); ``report.unrepaired_defects`` drops the
sibling's finding for the fact this edit cites.
"""

from __future__ import annotations

import posixpath
import re
from urllib.parse import quote

from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.detectors.links import (
    _GITHUB_WEB,
    _MISSING_IN_TREE,
    _WHERE,
    _repair,
)
from repo_presenter.readme.correction.detectors.versioned_link_target import _newest_versioned
from repo_presenter.readme.correction.model import (
    BROKEN_LINK,
    Context,
    DetectorResult,
    Edit,
)

DETECTOR = "dead_link"


def _text_link(text: str, spelled: str) -> re.Match[str] | None:
    """The one ``[anchor](spelled)`` text link on the line, or None (image, empty anchor, or not
    exactly one)."""
    found = list(re.finditer(r"\[([^\[\]\n]+)\]\(" + re.escape(spelled) + r"\)", text))
    if len(found) != 1:
        return None
    match = found[0]
    if match.start() > 0 and text[match.start() - 1] == "!":
        return None
    if not match.group(1).strip():
        return None
    return match


@detector(DETECTOR)
def dead_link(ctx: Context) -> DetectorResult:
    edits: list[Edit] = []
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
            continue
        number = int(where.group(1))
        if not 1 <= number <= len(ctx.lines):
            continue
        line = ctx.lines[number - 1]
        target = fact.value
        if _repair(ctx, target) is not None:
            continue  # broken_link repairs it
        base = posixpath.dirname(ctx.readme_path)
        wanted = posixpath.normpath(posixpath.join(base, target.split("#", 1)[0]))
        pool = [path for path in ctx.tree_paths if path != ctx.readme_path]
        if _newest_versioned(pool, wanted) is not None:
            continue  # versioned_link_target repairs it
        forms = [target, quote(target, safe="/#:@")]
        spelled = next((form for form in forms if f"]({form})" in line.text), None)
        if spelled is None:
            continue
        match = _text_link(line.text, spelled)
        if match is None:
            continue  # broken_link reports it, left exactly as written
        edits.append(
            Edit(
                kind=BROKEN_LINK,
                detector=DETECTOR,
                start=line.start + match.start(),
                end=line.start + match.end(),
                original=match.group(0),
                replacement=match.group(1),
                fact_ids=(fact.id,),
                rationale=(
                    f"the tree does not contain {target!r} and holds no file that stands in for "
                    "it; the dead link is removed and its text kept word for word"
                ),
            )
        )
    return DetectorResult(edits=tuple(edits), findings=())
