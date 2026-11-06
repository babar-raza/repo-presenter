"""BC-07 (public text): the README carries nothing meant for the pipeline's own records.

Owner ruling 2026-11-06: the maintainer attribution (``PRESERVE_ATTRIBUTED``) is internal only and must
stay out of the public README "at all costs and in any shape or form". Until that ruling the renderer
printed ``composition.placement.ATTRIBUTION_LINE`` before attributed content, and the two candidates
sealed that day (Email .NET, Imaging .NET) carry it. This check refuses any README that states the
attribution or the "not independently verified" note in any wording, so neither a regression in the
renderer nor a model-authored sentence can publish it.
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


def internal_markers(readme: str) -> list[str]:
    """Each line of ``readme`` that carries an internal attribution or bookkeeping marker."""
    found: list[str] = []
    for line in readme.splitlines():
        if ATTRIBUTION_LINE in line or NOT_VERIFIED_NOTE in line or _INTERNAL.search(line):
            found.append(" ".join(line.split())[:160])
    return found


def public_text_failures(candidate: Candidate) -> list[Failure]:
    return [
        Failure(
            "COMPOSING",
            f"the public README carries an internal attribution or bookkeeping marker: {line!r}",
        )
        for line in internal_markers(candidate.readme)
    ]
