r"""Format/capability OVER-claiming: a README asserts a format or capability works, with nothing
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

Second claim source, added 2026-10-22: the Mermaid "At a Glance" diagram's Starting
Points/Outputs node labels (``i\d+["..."]``/``o\d+["..."]`` inside a ```mermaid fence), the
exact shape the known aspose-3d-foss/Aspose.3D-FOSS-for-.NET U3D/RVM/AMF/HTML5 over-claim
actually lives in (confirmed live: that README's claim is in this diagram and in prose, never a
table, so the table-only check never fired against it). Still deliberately bounded, not general
prose parsing: only acronym-shaped tokens (``[A-Z0-9]{2,6}`` with at least one letter, so "3MF"
and "HTML5" both match but ordinary words like "An"/"existing" cannot, since they are not
all-caps) inside these two specific node-ID prefixes, which this project's own README contract
(``docs/MISSION_AUTHORITY.md``) already fixes as "Starting Points"/"Outputs" by convention --
not a regex let loose on arbitrary prose.

Known limitation, stated plainly rather than silently extended: a prose sentence outside a
table or the At a Glance diagram ("this library also exports OBJ files" in a plain paragraph)
still makes the same over-claim in a shape neither check parses; broadening further is future
work, not attempted here, to avoid a regex fragile enough to itself over-claim what it detects.
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
# Mermaid At a Glance node: `    o3["3MF or RVM file (Microsoft 3MF, AVEVA PDMS RVM)"]`.
_MERMAID_IO_NODE = re.compile(r'^\s*[io]\d+\["([^"]+)"\]\s*$')
# An acronym-shaped token: 2-6 chars, all uppercase letters/digits, at least one letter (so "3MF"
# and "HTML5" both match; a bare number or an ordinary capitalized word like "An" does not).
_ACRONYM = re.compile(r"\b(?=[A-Z0-9]*[A-Z])[A-Z0-9]{2,6}\b")
# Short acronym-shaped words that are not format/capability names and would otherwise false-
# positive inside a Starting-Points/Outputs node label's ordinary English. AVEVA/PDMS are a real
# measured false positive (2026-10-22): aspose-3d-foss/Aspose.3D-FOSS-for-.NET's own node label
# reads `"3MF or RVM file (Microsoft 3MF, AVEVA PDMS RVM)"` -- a vendor name and a product suite
# name clarifying what RVM is, not a second and third file-format claim.
_NOT_A_FORMAT = frozenset({"AN", "OR", "A", "3D", "2D", "ID", "IO", "AVEVA", "PDMS"})


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


def _mermaid_claims(ctx: Context) -> list[tuple[int, str, str]]:
    """``(line number, claimed label, raw line)`` for every acronym-shaped token named inside a
    Mermaid At a Glance Starting-Points/Outputs node, one claim per token (a node naming two
    formats, "3MF or RVM file", yields two separate claims so each is checked on its own)."""
    claims: list[tuple[int, str, str]] = []
    for line in ctx.lines:
        if not line.in_fence:
            continue
        match = _MERMAID_IO_NODE.match(line.text)
        if match is None:
            continue
        label_text = match.group(1)
        for token in _ACRONYM.findall(label_text):
            if token in _NOT_A_FORMAT:
                continue
            claims.append((line.number, token, line.text))
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
    seen: set[tuple[int, str]] = set()
    for number, label, raw in [*_table_claims(ctx), *_mermaid_claims(ctx)]:
        if (number, label) in seen:
            continue  # the same node/row naming the same token twice is one claim, not two
        seen.add((number, label))
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
