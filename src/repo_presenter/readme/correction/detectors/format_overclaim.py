"""Format/capability OVER-claiming: a README asserts a format or capability works, with nothing
confirming it is actually wired up or reachable.

``migration/reuse-manifest.yaml``'s readme_correction/ entry records this as a ``known_gap``: the
old repository's own ``report_gaps`` detector (``gaps.py`` in this package) only catches the
opposite direction -- a verified ``format``/``capability`` fact the README never mentions (UNDER-
claiming). Nothing in the old repository flags the direction the owner's 2026-10-20 Lane L ruling
names explicitly (``docs/MISSION_AUTHORITY.md``'s critical-fact section): "3D-.NET advertises
formats its own ``IOService.cs`` rejects".

This is necessarily more heuristic than ``report_gaps``: there is no single deterministic signal
for "the README asserts a capability" the way a ``format``/``capability`` fact's own polarity is a
single deterministic signal for whether the repository actually has it. The one shape measured
across the portfolio and used here is a markdown table row with a truthy marker cell (a checkmark,
a bare "Yes", a bare "Supported") naming a format or capability in its first cell -- the exact
shape of a format-support table like the 3D-.NET one the owner's ruling names. A row marked with a
falsy cell (a cross mark, "No", "Not supported") is a correctly-caveated claim and is never
flagged; a row whose claim a SUPPORTED fact backs is a correct claim and is never flagged either.

Because confirming an over-claim needs a human-reviewable fact citation, not blind auto-correction,
this detector never edits -- every result is a report-only ``Finding``, even when a CONTRADICTED
fact makes the over-claim certain.

Known limitation, stated plainly rather than silently extended: this detector only reads table
rows. A prose sentence ("this library also exports OBJ files") makes the same over-claim in a
shape this detector does not parse; broadening to prose is future work, not attempted here, to
avoid a regex fragile enough to itself over-claim what it detects.
"""

from __future__ import annotations

import re

from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.model import Context, DetectorResult, Finding

DETECTOR = "format_overclaim"
_CLAIMED_KINDS = frozenset({"format", "capability"})
# The cell's FULL content (after markup/whitespace stripping) must be one of these -- not a
# substring search. A substring search over an arbitrary-length prose cell (as in an API
# Reference table's description column, e.g. "...is supported by this importer.") produced real
# false positives against aspose-3d-foss/Aspose.3D-FOSS-for-Python's live README (measured
# 2026-10-22, lines 430/460/507/560: ColladaImporter/EntityRendererFeatures/Importer/Plugin all
# flagged purely because their description cell contains the word "supported" in prose).
_TRUTHY = re.compile(r"^(?:✅|✔|yes|supported|:heavy_check_mark:)$", re.IGNORECASE)
_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
_STRIP_MARKUP = re.compile(r"[`*_]")


def _table_claims(ctx: Context) -> list[tuple[int, str, str]]:
    """``(line number, claimed label, raw line)`` for every table row whose first cell names a
    format or capability and whose other cells carry at least one truthy marker."""
    claims: list[tuple[int, str, str]] = []
    for line in ctx.lines:
        text = line.text.strip()
        if line.in_fence or not (text.startswith("|") and text.endswith("|")):
            continue
        cells = [cell.strip() for cell in text.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label = cells[0]
        if not label or _SEPARATOR_CELL.match(label) or all(_SEPARATOR_CELL.match(c) for c in cells):
            continue
        if any(_TRUTHY.match(_STRIP_MARKUP.sub("", cell).strip()) for cell in cells[1:]):
            claims.append((line.number, label, line.text))
    return claims


def _normalize(label: str) -> str:
    return _STRIP_MARKUP.sub("", label).strip().lower().lstrip(".")


def _matches(token: str, fact_value: str) -> bool:
    value = fact_value.strip().lower().lstrip(".")
    if not value or not token:
        return False
    return token == value or token in value or value in token


@detector(DETECTOR)
def format_overclaim(ctx: Context) -> DetectorResult:
    relevant = [fact for fact in ctx.facts.facts if fact.kind in _CLAIMED_KINDS]
    findings: list[Finding] = []
    for number, label, raw in _table_claims(ctx):
        token = _normalize(label)
        if len(token) < 2:
            continue
        matching = [fact for fact in relevant if _matches(token, fact.value)]
        if any(fact.polarity == "SUPPORTED" for fact in matching):
            continue  # the claim is backed by a verified fact: not an over-claim
        contradicted = next((fact for fact in matching if fact.polarity == "CONTRADICTED"), None)
        if contradicted is not None:
            findings.append(
                Finding(
                    DETECTOR,
                    number,
                    raw.strip(),
                    f"the README marks {label!r} supported, but {contradicted.id} is on record "
                    f"as CONTRADICTED ({contradicted.value}); the claim is not backed by a "
                    "verified fact",
                    (contradicted.id,),
                )
            )
            continue
        findings.append(
            Finding(
                DETECTOR,
                number,
                raw.strip(),
                f"the README marks {label!r} supported, but no SUPPORTED format or capability "
                "fact confirms it is actually wired up; a human reviewer should check whether it "
                "is reachable before trusting the claim",
            )
        )
    return DetectorResult(findings=tuple(findings))
