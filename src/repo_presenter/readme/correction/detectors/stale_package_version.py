"""Auto-fix for a README's own stale package-version and publication claims.

TC-025's census (``docs/investigations/2026-11-07-vs0-vertical-slice.md``) named two concrete,
real shapes that block otherwise-good Lane L runs, ordered by how many real repositories they
cover:

* a pinned-version claim the README states in prose ("pins version 26.6.0") that the package
  registry's current reading (``package:published_version``) has since moved past -- the PDF Java
  case this session's own recertification baseline recorded ("pins version 26.6.0, registry lists
  26.9.0");
* a "not published" claim the README still makes after the registry has started listing the
  package -- the PSD .NET case ("says not published to NuGet, registry lists it").

Both rules fire only against ``package:published_version`` (``core/package_registry.
PUBLISHED_VERSION_FACT_ID``), the one fact that states what a reader can install today; without it
on record (SUPPORTED) nothing is corrected, only reported -- the same "never guess, only compare
against verified evidence" discipline every detector in this package follows (see
``enterprise_edition.enterprise_edition_naming``).

Each match is a one-line, short span (``FALSE_CLAIM_FIX``): the pinned-version rule replaces only
the version number's own characters, the publication rule replaces only the "is not ... published
to <registry>" fragment it matched, in each case leaving the surrounding sentence exactly as the
maintainers wrote it.
"""

from __future__ import annotations

import re

from repo_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID
from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.model import (
    FALSE_CLAIM_FIX,
    MAX_SPAN,
    Context,
    DetectorResult,
    Edit,
    Finding,
)

DETECTOR = "stale_package_version"

#: "pins version 26.6.0" / "pinned to version 26.6.0" / "pinned at version 26.6.0". The captured
#: group is the version number alone, so the edit never touches the surrounding words.
_PINNED_VERSION = re.compile(
    r"(?i)\b(?:pins?\s+version|pinned\s+(?:to|at)\s+version)\s+(\d+(?:\.\d+){1,3})\b"
)
#: "is not published to NuGet" / "is not yet published to PyPI", etc. The one registry name this
#: detector recognizes is captured so the replacement can name the same one back.
_NOT_PUBLISHED = re.compile(
    r"(?i)\bis\s+not(?:\s+yet)?\s+published\s+to\s+"
    r"(NuGet|PyPI|Maven(?:\s+Central)?|npm|crates\.io|RubyGems|pkg\.go\.dev)\b"
)


@detector(DETECTOR)
def stale_package_version(ctx: Context) -> DetectorResult:
    published = ctx.supported(PUBLISHED_VERSION_FACT_ID)
    edits: list[Edit] = []
    findings: list[Finding] = []
    for line in ctx.lines:
        if line.in_fence:
            continue
        for match in _PINNED_VERSION.finditer(line.text):
            claimed = match.group(1)
            if published is None:
                findings.append(
                    Finding(
                        DETECTOR,
                        line.number,
                        claimed,
                        f"the README pins version {claimed!r}; no "
                        f"{PUBLISHED_VERSION_FACT_ID} fact is on record to check it against",
                    )
                )
                continue
            if claimed == published.value:
                continue  # the pin already matches the registry's current reading
            start, end = match.start(1), match.end(1)
            if end - start > MAX_SPAN:
                continue
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector=DETECTOR,
                    start=line.start + start,
                    end=line.start + end,
                    original=claimed,
                    replacement=published.value,
                    fact_ids=(published.id,),
                    rationale=(
                        f"line {line.number} pins version {claimed!r}; the package registry's "
                        f"current release is {published.value!r}"
                    ),
                )
            )
        for match in _NOT_PUBLISHED.finditer(line.text):
            registry = match.group(1)
            if published is None:
                findings.append(
                    Finding(
                        DETECTOR,
                        line.number,
                        match.group(0),
                        "the README says the package is not published to "
                        f"{registry}; no {PUBLISHED_VERSION_FACT_ID} fact is on record to check "
                        "it against",
                    )
                )
                continue
            start, end = match.start(), match.end()
            if end - start > MAX_SPAN:
                continue
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector=DETECTOR,
                    start=line.start + start,
                    end=line.start + end,
                    original=match.group(0),
                    replacement=f"is published to {registry}",
                    fact_ids=(published.id,),
                    rationale=(
                        f"line {line.number} says the package is not published to {registry}; "
                        f"the package registry already lists it at {published.value!r}"
                    ),
                )
            )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
