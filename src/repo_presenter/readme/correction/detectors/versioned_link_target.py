"""A link target the tree does not contain, repaired to the unique newest of several versioned
files sharing its own stem -- the one shape ``links.broken_link`` gives up on by design.

TC-025's census named this real shape by two repositories (Cells .NET/Python's generic
``RELEASE_NOTES.md`` link against a tree that only holds dated ones, PSD Python's equivalent): the
README links a generic name the tree does not hold exactly, but the same directory holds several
files that share that name's own stem and differ only by a trailing version or year token
(``RELEASE_NOTES_24.1.0.md``, ``RELEASE_NOTES_2023.md``). ``broken_link`` requires an exact path or
an exact-basename match elsewhere in the tree and reports everything else, unrepaired, as "no
unique file stands in for it" -- correctly, for a target with no versioned sibling at all, but
also for this one, repairable shape.

This is a separate detector, not a change to ``broken_link``, so that an existing sealed Lane L
candidate's recorded ``detectors.broken_link`` version is never reopened by a capability it never
exercised; only ``detectors.versioned_link_target`` (a detector that did not exist before) is a new
dependency, and only repositories whose link this detector actually matches ever see it. The two
detectors read the very same ``link_target`` facts; when this one resolves what ``broken_link``
could not, ``report.unrepaired_defects`` drops the sibling's "no unique file stands in for it"
finding for that fact (the applied edit is the stronger, acted-upon claim), so the two can never
disagree about whether the link is fixed.

A tie at the top version, or no version-shaped suffix at all, is left exactly as before: reported by
``broken_link``, not guessed here either.
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
)
from repo_presenter.readme.correction.model import (
    BROKEN_LINK,
    Context,
    DetectorResult,
    Edit,
)

DETECTOR = "versioned_link_target"

#: A trailing version or year token: a leading separator (never glued straight onto the stem, so
#: "LICENSE2.md" is never mistaken for a versioned "LICENSE.md"), then either a bare four-digit
#: year or two or more dot/dash/underscore-separated numeric groups ("24.1.0", "2024-01").
_VERSION_SUFFIX = re.compile(r"^[_\-. ](?:\d{4}|\d+(?:[._-]\d+)+)$")
_DIGITS = re.compile(r"\d+")


def _version_key(suffix: str) -> tuple[int, ...]:
    return tuple(int(group) for group in _DIGITS.findall(suffix))


def _newest_versioned(pool: list[str], wanted: str) -> str | None:
    """Among ``pool``, the one file in ``wanted``'s own directory whose name is ``wanted``'s own
    stem plus a version/year suffix, when exactly one carries the highest version; else None."""
    directory = posixpath.dirname(wanted)
    stem, ext = posixpath.splitext(posixpath.basename(wanted))
    candidates: list[tuple[tuple[int, ...], str]] = []
    for path in pool:
        if posixpath.dirname(path) != directory:
            continue
        other_stem, other_ext = posixpath.splitext(posixpath.basename(path))
        if other_ext.lower() != ext.lower() or not other_stem.lower().startswith(stem.lower()):
            continue
        suffix = other_stem[len(stem) :]
        if _VERSION_SUFFIX.match(suffix):
            candidates.append((_version_key(suffix), path))
    if not candidates:
        return None
    candidates.sort()
    if len(candidates) > 1 and candidates[-1][0] == candidates[-2][0]:
        return None  # a tie at the top is no unique newest
    return candidates[-1][1]


@detector(DETECTOR)
def versioned_link_target(ctx: Context) -> DetectorResult:
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
        forms = [target, quote(target, safe="/#:@")]
        spelled = next((form for form in forms if f"]({form}" in line.text), None)
        if spelled is None:
            continue  # links.broken_link already reports this exact failure mode
        index = line.text.find(f"]({spelled}") + 2
        end = index + len(spelled)
        if line.text.count(f"]({spelled}") != 1 or line.text[end : end + 1] not in {")", " "}:
            continue  # ambiguous on its own line: links.broken_link already reports it
        base = posixpath.dirname(ctx.readme_path)
        wanted = posixpath.normpath(posixpath.join(base, target.split("#", 1)[0]))
        pool = [path for path in ctx.tree_paths if path != ctx.readme_path]
        newest = _newest_versioned(pool, wanted)
        if newest is None:
            continue  # not this detector's shape: links.broken_link reports it instead
        relative = posixpath.relpath(newest, base or ".")
        anchor = target.split("#", 1)[1] if "#" in target else ""
        repaired = relative + (f"#{anchor}" if anchor else "")
        edits.append(
            Edit(
                kind=BROKEN_LINK,
                detector=DETECTOR,
                start=line.start + index,
                end=line.start + end,
                original=spelled,
                replacement=quote(repaired, safe="/#:@") if spelled != target else repaired,
                fact_ids=(fact.id,),
                rationale=(
                    f"the tree does not contain {target!r}; its directory holds several "
                    f"versioned files sharing its name, and {repaired!r} is the unique newest"
                ),
            )
        )
    return DetectorResult(edits=tuple(edits), findings=())
