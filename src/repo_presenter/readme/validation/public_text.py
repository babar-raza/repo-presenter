"""BC-07 (public text): the README carries nothing meant for the pipeline's own records.

Owner ruling 2026-11-06: the maintainer attribution (``PRESERVE_ATTRIBUTED``) is internal only and must
stay out of the public README "at all costs and in any shape or form". Until that ruling the renderer
printed ``composition.placement.ATTRIBUTION_LINE`` before attributed content, and the two candidates
sealed that day (Email .NET, Imaging .NET) carry it. This check refuses any README that states the
attribution or the "not independently verified" note in any wording, so neither a regression in the
renderer nor a model-authored sentence can publish it.

Owner feedback 2026-11-13 (BL-002, P0): the 3D Python Lane R README printed an install fact's
evidence detail verbatim - "could not be confirmed on PyPI (package registry: a distribution of this
name exists, but ownership not confirmed: the registry's project URLs point at another
repository)" - "raw analysis response ... False claim is the biggest problem". The same check now
refuses the pipeline's analysis vocabulary in reader prose (``analysis_markers``): registry-reading
details, ownership verdicts, fact polarities and fact ids. Code fences are not prose and are not
read for it; the bare English words "fact" and "evidence" are not refused, because preserved
maintainer prose uses them ("tags a PDF after the fact", "QA evidence report") - only their
internal compounds are.
"""

from __future__ import annotations

import re

from repo_presenter.readme.composition.placement import ATTRIBUTION_LINE
from repo_presenter.readme.composition.retained_examples import NOT_VERIFIED_NOTE
from repo_presenter.readme.validation.failures import Candidate, Failure

_INTERNAL = re.compile(
    r"maintainers?['’]?\s*(?:own\s+)?readme|not\s+independently\s+verified|"
    r"preserve_attributed|attributed\s+maintainer|inherited_unit:|"
    r"\*\*not\s+verified:?\*\*|carried\s+over\s+(?:unchanged\s+)?from\s+the\s+project",
    re.IGNORECASE,
)


# The pipeline's evidence/analysis vocabulary (``core/package_registry.py`` registry-reading
# details and ownership sentences, ``core/facts.py`` polarities and fact ids). None of it is ever a
# reader-facing statement.
_ANALYSIS = re.compile(
    r"package\s+registry\s*:|package\s+registry\s+unreachable|ownership\s+not\s+confirmed|"
    r"project\s+urls?\s+points?\s+at\s+another\s+repository|"
    r"\bthe\s+(?:package\s+)?registry['’]s\b|answered\s+ambiguously|"
    r"could\s+not\s+be\s+confirmed\s+on\b|\bnone\s+could\s+not\s+be\s+read\b|"
    r"\b(?:fact|evidence)[\s_-]*(?:ids?|details?|records?|lines?|polarit(?:y|ies))\b|"
    r"\bfacts\.json\b|"
    r"\b(?:install_command|identity|import_path|package|public_symbol):"
    r"(?:name|version|published_version|python_versions|python_requires|distribution|"
    r"repository|pip|cmake|npm|maven|nuget|cargo|go)\b|"
    # BL-003 class K11 (docs/investigations/2026-11-13-lane-r-false-claim-review.md): the
    # pipeline's own perspective printed as prose - its "verified public surface", a type that "is
    # a public symbol with members ...". ("This checkout" is NOT refused: Cells .NET's maintainers
    # wrote "This checkout does not contain a `tests/` directory" in their own README.)
    r"\bverified\s+public\s+(?:surface|types?)\b|\bis\s+a\s+public\s+symbol\b",
    re.IGNORECASE,
)
# Fact polarities and verification verdicts, as the pipeline spells them (upper case, whole word).
_POLARITY = re.compile(r"\b(?:UNRESOLVED|SUPPORTED|CONTRADICTED|NOT_VERIFIED)\b")
_FENCE = re.compile(r"^\s*(?:```|~~~)")


def _short(line: str) -> str:
    return " ".join(line.split())[:160]


def internal_markers(readme: str) -> list[str]:
    """Each line of ``readme`` that carries an internal attribution or bookkeeping marker."""
    found: list[str] = []
    for line in readme.splitlines():
        if ATTRIBUTION_LINE in line or NOT_VERIFIED_NOTE in line or _INTERNAL.search(line):
            found.append(_short(line))
    return found


def analysis_markers(readme: str) -> list[str]:
    """Each prose line of ``readme`` (code fences excluded) that prints the pipeline's internal
    evidence or analysis vocabulary (BL-002)."""
    found: list[str] = []
    fenced = False
    for line in readme.splitlines():
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced and (_ANALYSIS.search(line) or _POLARITY.search(line)):
            found.append(_short(line))
    return found


def public_text_failures(candidate: Candidate) -> list[Failure]:
    return [
        Failure(
            "COMPOSING",
            f"the public README carries an internal attribution or bookkeeping marker: {line!r}",
        )
        for line in internal_markers(candidate.readme)
    ] + [
        Failure(
            "COMPOSING",
            f"the public README prints internal evidence or analysis wording: {line!r}",
        )
        for line in analysis_markers(candidate.readme)
    ]
