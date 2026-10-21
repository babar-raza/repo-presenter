"""Auto-fix for the "Enterprise Edition" naming violation.

``docs/MISSION_AUTHORITY.md``'s still-valid outcome requirements: "Name the aspose.com commercial
product 'Enterprise Edition' everywhere, with no substitute wording ('commercial', 'paid version',
etc.)". The old repository's own validator (``components/readme/review/acceptance/
text_checks.edition_name``, BC-06) only REJECTS the violation; nothing in that repository AUTO-
FIXES it -- ``migration/reuse-manifest.yaml``'s readme_correction/ entry records this by name as a
``known_gap``: "no detector AUTO-FIXES the Enterprise Edition naming violation ... a new, small
FALSE_CLAIM_FIX-kind detector is needed here, informed by this session's own 3-repo finding."

This detector generalizes the exact pattern this session found and manually fixed three times
across the portfolio (see each repository's ``evidence/build/P1_PORTFOLIO_SCALE/<repo>/
lane_l_candidate.diff`` for the before/after text this detector's test fixtures are drawn from:
``aspose-slides-foss__Aspose.Slides-FOSS-for-Java``, ``aspose-words-foss__Aspose.Words-FOSS-for-
.NET`` and ``aspose-words-foss__Aspose.Words-FOSS-for-Python``):

* ``commercial [Aspose.X for Y](url)`` (a markdown link, "commercial" or "the commercial" in
  front) -> ``[Aspose.X for Y — Enterprise Edition](url)`` -- the product name is already spelled
  out as the link text, so the fix only moves words, it never invents one;
* ``commercial Aspose.X for Y`` / ``the commercial Aspose.X for Y product`` (plain text, the
  product name already named in full on the same line) -> ``Aspose.X for Y — Enterprise Edition``
  (the "the ... product" wrapper is dropped along with "commercial").

Both rules fire only when the product's own name (with its platform) is already spelled out, in
full, on the exact physical line the edit replaces -- no name is ever invented or looked up from
elsewhere, the same "repair only what is unique and already there" discipline every other detector
in this package follows (see ``links.broken_link``). Two shapes measured in the same three real
diffs are deliberately NOT auto-fixed, for that reason:

* a bare "the commercial product" with no product name anywhere on its own line (one of the three
  real fixes resolved this from a product name stated in an *earlier* sentence of the README --
  cross-sentence name resolution this detector does not attempt, because guessing which earlier
  name applies risks asserting the wrong platform, a worse error than leaving the sentence alone);
* a "commercial ... product" phrase split across a hard line-wrap (a real, if rarer, shape in a
  hard-wrapped README) -- this architecture's ``FALSE_CLAIM_FIX`` edit kind is one physical line by
  construction (``model.Edit.__post_init__``), so a multi-line rewrap is out of scope for this
  edit kind regardless.

Both are reported as findings instead (never silently dropped), with the exact matched text and
why it was not guessed.

The auto-fix additionally requires a ``link_target:product.enterprise`` fact to be on record
(any polarity) before it edits anything, so it always has a fact to cite as its evidence
(``Edit.__post_init__`` requires at least one ``fact_ids`` entry for a ``FALSE_CLAIM_FIX``, the
same rule ``stale_phrase`` follows in the old repo). Without that fact, every match is reported
instead -- a conservative floor: this detector never asserts there *is* a separate Enterprise
Edition product for a repository it has no evidence for.
"""

from __future__ import annotations

import re

from repo_presenter.readme.correction.detectors import detector
from repo_presenter.readme.correction.model import (
    FALSE_CLAIM_FIX,
    MAX_SPAN,
    Context,
    DetectorResult,
    Edit,
    Finding,
)

DETECTOR = "enterprise_edition_naming"
#: The fact ``report_gaps`` already keys its own Enterprise Edition finding on; the one fact this
#: detector cites as the edit's evidence.
ENTERPRISE_FACT_ID = "link_target:product.enterprise"

#: "commercial [Aspose.X for Y](url)", with an optional leading "the": the product name and its
#: platform are already spelled out as the link's own text.
_LINK_RULE = re.compile(r"(?i)(?:the\s+)?commercial\s+\[(Aspose\.[^\]]+)\]\(([^)\s]+)\)")
#: "commercial Aspose.X for Y" / "the commercial Aspose.X for Y product" in plain text.
_BARE_RULE = re.compile(
    r"(?i)(?:the\s+)?commercial\s+(Aspose\.[A-Za-z0-9+#]+(?:\s+for\s+[A-Za-z0-9.+#]+)?)"
    r"(?:\s+product)?\b"
)
#: A leftover "commercial" mention this detector recognizes as the same naming violation, but
#: cannot repair without guessing a product name: reported, never silently ignored.
_SUSPECT = re.compile(
    r"(?i)\bcommercial\s+(?:product\b|edition\b|version\b|Aspose\.[A-Za-z0-9+#]+\b)"
)


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < s_end and end > s_start for s_start, s_end in spans)


@detector(DETECTOR)
def enterprise_edition_naming(ctx: Context) -> DetectorResult:
    enterprise = ctx.fact(ENTERPRISE_FACT_ID)
    edits: list[Edit] = []
    findings: list[Finding] = []
    for line in ctx.lines:
        if line.in_fence:
            continue
        claimed: list[tuple[int, int, str]] = []  # (start, end, replacement) within the line
        for match in _LINK_RULE.finditer(line.text):
            label, url = match.group(1), match.group(2)
            claimed.append((match.start(), match.end(), f"[{label} — Enterprise Edition]({url})"))
        occupied = [(s, e) for s, e, _ in claimed]
        for match in _BARE_RULE.finditer(line.text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            claimed.append((match.start(), match.end(), f"{match.group(1)} — Enterprise Edition"))
        occupied = [(s, e) for s, e, _ in claimed]
        for start, end, replacement in claimed:
            original = line.text[start:end]
            if enterprise is None or len(original) > MAX_SPAN:
                findings.append(
                    Finding(
                        DETECTOR,
                        line.number,
                        original,
                        "names the aspose.com product with a substitute for its proper name "
                        f"({original!r}); the fix is not applied because "
                        + (
                            f"no {ENTERPRISE_FACT_ID} fact is on record to cite as its evidence"
                            if enterprise is None
                            else "the matched span is too long for a one-line fix"
                        ),
                    )
                )
                continue
            edits.append(
                Edit(
                    kind=FALSE_CLAIM_FIX,
                    detector=DETECTOR,
                    start=line.start + start,
                    end=line.start + end,
                    original=original,
                    replacement=replacement,
                    fact_ids=(enterprise.id,),
                    rationale=(
                        f"line {line.number} names the aspose.com product with a substitute for "
                        f"its proper name ({original!r}); the mission naming rule requires "
                        '"Enterprise Edition" with no substitute wording'
                    ),
                )
            )
        for match in _SUSPECT.finditer(line.text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            findings.append(
                Finding(
                    DETECTOR,
                    line.number,
                    line.text.strip()[:160],
                    f"possible Enterprise Edition naming violation ({match.group(0)!r}); the "
                    "product name and its platform are not both spelled out on this line, so the "
                    "fix is not guessed",
                )
            )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
