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

Without that fact, a "pinned version" or "not published" claim is reported with
``report_only_reason="NO_EVIDENCE_OF_ABSENCE"`` (not a blocking defect): no fact confirms OR
refutes it, so it may already be true (Aspose.BarCode FOSS for Python: the README correctly says
the package is not published, PyPI genuinely has no release under that name, and the detector has
no fact either way). ``format_overclaim`` reports the same shape the same way. A fact that exists
and contradicts the claim always becomes an edit, never a finding, so every finding this detector
raises is this no-evidence shape.

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
from repo_presenter.readme.validation.claims import other_subject_denial_lines

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
    # A trailing "yet" ("is not published to NuGet yet") belongs to the claim: leaving it behind
    # produced "is published to NuGet yet", which the independent review rightly REJECTed
    # (Aspose.PSD-FOSS-for-.NET Lane L, 2026-11-09).
    r"(?:\s+yet\b)?"
)

#: "The package metadata is defined in this repository, but `Aspose.PSD.FOSS` is not published to
#: NuGet yet." -- a whole sentence whose only contrast ("..., but X is not published") the fix
#: removes. Rewriting just "is not published" left "..., but `X` is published to NuGet.", which the
#: independent review REJECTed as a contradiction (PSD .NET and 3D .NET Lane L, 2026-11-10), so a
#: sentence of exactly this shape is replaced as a whole by "`X` is published to R.".
_NOT_PUBLISHED_SENTENCE = re.compile(
    r"(?i)(?:(?<=^)|(?<=[.!?]\s))[^.!?\n]{0,120}?,\s+but\s+(`[^`\n]{1,60}`)\s+is\s+not(?:\s+yet)?"
    r"\s+published\s+to\s+"
    r"(NuGet|PyPI|Maven(?:\s+Central)?|npm|crates\.io|RubyGems|pkg\.go\.dev)(?:\s+yet)?\s*\."
)


@detector(DETECTOR)
def stale_package_version(ctx: Context) -> DetectorResult:
    published = ctx.supported(PUBLISHED_VERSION_FACT_ID)
    edits: list[Edit] = []
    findings: list[Finding] = []
    # A "not published" statement about another artifact (the converter tool, a sample) is not
    # this package's publication claim: nothing contradicts it, so it is never rewritten.
    other_subject = other_subject_denial_lines(ctx.readme, ctx.facts)
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
                        report_only_reason="NO_EVIDENCE_OF_ABSENCE",
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
        sentence_spans: list[tuple[int, int]] = []
        if line.number - 1 in other_subject:
            continue
        for match in _NOT_PUBLISHED_SENTENCE.finditer(line.text):
            registry = match.group(2)
            if published is None:
                continue  # the plain rule below reports it as a finding
            start, end = match.start(), match.end()
            if end - start > MAX_SPAN:
                continue
            sentence_spans.append((start, end))
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector=DETECTOR,
                    start=line.start + start,
                    end=line.start + end,
                    original=match.group(0),
                    replacement=f"{match.group(1)} is published to {registry}.",
                    fact_ids=(published.id,),
                    rationale=(
                        f"line {line.number} says {match.group(1)} is not published to {registry}; "
                        f"the package registry already lists it at {published.value!r}"
                    ),
                )
            )
        for match in _NOT_PUBLISHED.finditer(line.text):
            if any(match.start() < e and match.end() > b for b, e in sentence_spans):
                continue
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
                        report_only_reason="NO_EVIDENCE_OF_ABSENCE",
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
