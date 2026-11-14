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


_RELEASE_NOTES = re.compile(r"(?i)release[\s_-]*notes|change[\s_-]*log|\breleases?\b")
_VERSION = re.compile(r"(?i)(?<![\w.])v?(\d+(?:\.\d+)+)(?!\w)")


def releases_target(ctx: Context, anchor: str, target: str) -> tuple[str, str] | None:
    """``(url, tag)`` a dead release-notes link is repaired to, or ``None``: the repository's
    Releases page when it has release tags (``ctx.release_tags``), or that one tag's release page
    when the link names the version exactly one tag carries ("V26.10.0 release notes" ->
    ``.../releases/tag/V26.10.0``, tag ``""`` otherwise).

    Version 2 (BL-010, owner feedback a922e11316 on Cells Python: "Why the link was removed. isn't
    it active. No need to remove a link which has active source."): version 1 unlinked a
    release-notes link to a file the tree never held, but the repository does publish its
    releases (Cells Python: tags V26.3.0 .. V26.10.0; Cells .NET: V26.4.0 .. V26.10.0), so the
    link had a live destination. The words stay; only the dead target changes. A link that names
    no release notes, or a repository with no release tag, is unlinked exactly as before."""
    if not ctx.release_tags or not _RELEASE_NOTES.search(f"{anchor} {target}"):
        return None
    repository = ctx.entry.repository
    if not repository or repository.count("/") != 1:
        return None
    base = f"https://github.com/{repository}/releases"
    wanted = {m.group(1) for m in _VERSION.finditer(f"{anchor} {target}")}
    tagged = [t for t in ctx.release_tags if t.lstrip("vV") in wanted]
    if len(tagged) == 1:
        return f"{base}/tag/{quote(tagged[0], safe='')}", tagged[0]
    return base, ""


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
        releases = releases_target(ctx, match.group(1), target)
        if releases is not None:
            url, tag = releases
            cited = [tag] if tag else list(ctx.release_tags[:3])
            target_start = line.start + match.start() + len(match.group(1)) + 3
            edits.append(
                Edit(
                    kind=BROKEN_LINK,
                    detector=DETECTOR,
                    start=target_start,
                    end=target_start + len(spelled),
                    original=spelled,
                    replacement=url,
                    fact_ids=(fact.id,),
                    rationale=(
                        f"the tree does not contain {target!r}; the repository publishes its "
                        f"releases as tags ({', '.join(cited)}), so the release-notes link points "
                        "at its Releases page, its text kept word for word"
                    ),
                    locators=tuple(f"tag:{t}" for t in cited),
                )
            )
            continue
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
