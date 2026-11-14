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
in this package follows (see ``links.broken_link``). Two further shapes are fixed under a
narrower, explicit condition (detector versions 2 and 3), and one shape remains deliberately NOT
auto-fixed:

* a bare "the commercial product" with no product name on its own line is rewritten to
  ``<name> — Enterprise Edition`` when every OTHER commercial-product mention in the README's
  prose (outside code fences) names one and the same product (compared case- and whitespace-
  insensitively): then the bare phrase can only mean that product, and the name is one the README
  itself already spells out;
* 2026-11-09 (VS0's real Slides-FOSS-for-Java finding, line 754 -- "the commercial product" with
  NO other commercial-product mention anywhere in the prose at all, so the rule above found
  nothing): falls back to the README's own H1, with " FOSS" removed, derived EXACTLY the way
  ``readme.composition.renderer._enterprise_paragraph`` already derives the same name for
  GENERATED text (further truncated at " for " when the live-verified enterprise target is a
  family-level page, not platform-specific). The H1 is the candidate's canonical FOSS name by
  construction (this package's own ``structure.second_h1`` rule enforces there is exactly one),
  never a guess and never looked up from the registry -- see ``_commercial_name_from_h1``'s own
  docstring. With NEITHER a prose mention NOR a readable H1 (never happens in practice, but never
  assumed), it stays a finding, exactly as before;
* a "commercial ... product" phrase split across a hard line-wrap (a real, if rarer, shape in a
  hard-wrapped README) -- this architecture's ``FALSE_CLAIM_FIX`` edit kind is one physical line by
  construction (``model.Edit.__post_init__``), so a multi-line rewrap is out of scope for this
  edit kind regardless.

Version 4 (BL-070, M9 round 43559491132; both cases are aspose.org's own published READMEs, R42):

* a "commercial ..." phrase that directly follows a link already naming the product (Cells C++ at
  9f852d0f, lines 566-567: "[Aspose.Cells for C++ — Enterprise Edition](…), the commercial product
  line this FOSS edition's API is modeled on") is an appositive of a correctly named product, not a
  substitute for its name: it is left as aspose.org published it (no edit, no finding). Version 3
  rewrote it to "…, the Aspose.Cells for C++ — Enterprise Edition line this FOSS edition's API is
  modeled on", repeating the name and breaking the sentence;
* a matched name without its platform, at a platform-level enterprise target (Words Python at
  2d2efee2, line 625: "the commercial Aspose.Words" hard-wrapped before "API"), takes the full name
  the README itself gives the Enterprise Edition ("Aspose.Words for Python — Enterprise Edition",
  line 630), else the one platform-qualified commercial name its prose agrees on, else the H1
  name -- aspose.org's anchor contract (``skills/readme-refresh.md``: platform relationship ->
  "Aspose.{Family} for {public_platform} — Enterprise Edition"). Version 3 wrote "Aspose.Words —
  Enterprise Edition", a name the repository never uses. With no such full name it is reported.

Anything not fixed is reported as a finding instead (never silently dropped), with the exact
matched text and why it was not guessed.

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
_BARE_PRODUCT = re.compile(r"(?i)(?:the\s+)?commercial\s+product\b")
_SUSPECT = re.compile(
    r"(?i)\bcommercial\s+(?:product\b|edition\b|version\b|Aspose\.[A-Za-z0-9+#]+\b)"
)


#: A markdown link whose text names an Aspose product, closing the text before a match (an optional
#: comma, dash or "the" between them): the phrase that follows is that link's appositive.
_NAMED_LINK_BEFORE = re.compile(
    r"\[[^\]]*\bAspose\.[^\]]*\]\([^)\s]+\)\s*[,;:—–-]?\s*(?:the\s*)?$", re.IGNORECASE
)
#: "Aspose.X for Y — Enterprise Edition" as the README itself writes it (link text or prose).
_FULL_EE_NAME = re.compile(r"(Aspose\.[A-Za-z0-9+#]+\s+for\s+[A-Za-z0-9.+#]+)\s*[—–-]+\s*Enterprise\s+Edition")


def _follows_named_link(ctx: Context, line, start: int) -> bool:
    """Whether the text before ``start`` on ``line`` -- with the previous prose line of the same
    paragraph when the match opens the line -- ends with a link already naming the product."""
    before = line.text[:start]
    if not before.strip():
        index = ctx.lines.index(line)
        previous = ctx.lines[index - 1] if index > 0 else None
        if previous is not None and not previous.in_fence and previous.text.strip():
            before = previous.text + " " + before
    return bool(_NAMED_LINK_BEFORE.search(before))


def _full_names(ctx: Context) -> list[str]:
    """The platform-qualified Enterprise Edition names the README itself writes, first-seen order."""
    names: dict[str, str] = {}
    for line in ctx.lines:
        if line.in_fence:
            continue
        for match in _FULL_EE_NAME.finditer(line.text):
            names.setdefault(_normalized(match.group(1)), " ".join(match.group(1).split()))
    return list(names.values())


def _platform_name(ctx: Context, name: str, enterprise, sole_product: str | None) -> str | None:
    """``name`` as the Enterprise Edition is named at the target's level: unchanged when it already
    carries its platform or the target is family-level; else the README's own full name for it
    (``_full_names``), the prose's one platform-qualified name, or the H1 name -- whichever starts
    with ``name`` + " for "; ``None`` when none does (reported, never guessed)."""
    if " for " in f" {_normalized(name)} " or (enterprise.attributes or {}).get("level") == "family":
        return name
    prefix = _normalized(name) + " for "
    candidates = [*_full_names(ctx), *([sole_product] if sole_product else [])]
    h1 = _commercial_name_from_h1(ctx, enterprise)
    if h1:
        candidates.append(h1)
    for candidate in candidates:
        if _normalized(candidate).startswith(prefix):
            return candidate
    return None


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < s_end and end > s_start for s_start, s_end in spans)


def _normalized(name: str) -> str:
    return " ".join(name.lower().split())


def _single_named_product(ctx: Context) -> str | None:
    """The one product name every named ``commercial <Aspose.X for Y>`` mention in the README's
    prose agrees on, spelled as first written; ``None`` when there is none or more than one."""
    names: dict[str, str] = {}
    for line in ctx.lines:
        if line.in_fence:
            continue
        for rule in (_LINK_RULE, _BARE_RULE):
            for match in rule.finditer(line.text):
                names.setdefault(_normalized(match.group(1)), " ".join(match.group(1).split()))
    return next(iter(names.values())) if len(names) == 1 else None


#: The README's one H1 (the template has exactly one -- ``structure.py``'s own ``second_h1``
#: detector enforces that elsewhere in this package), matching that module's own ``_H1`` pattern.
_H1_LINE = re.compile(r"^#(?!#)[ \t]+(\S.*)$")


def _commercial_name_from_h1(ctx: Context, enterprise) -> str | None:
    """2026-11-09 (VS0's Slides-FOSS-for-Java finding, line 754: a bare 'commercial product'
    phrase with no product name named anywhere else in the README's own prose -- ``sole_product``
    reads None, and the fix used to be skipped there). The commercial Enterprise Edition name,
    derived EXACTLY the way ``readme.composition.renderer._enterprise_paragraph`` already derives
    it for GENERATED text (``name = context.name.replace(" FOSS", "")``, further truncated at
    " for " when the live-verified target is a family-level page, not a platform-specific one):
    the README's own H1 is always the candidate's canonical FOSS name (enforced by this same
    package's own ``structure.second_h1`` rule, so it is never a guess, never looked up from the
    registry, and already matches the H1's own ``family``/``platform`` exactly because both the
    H1 and ``enterprise``'s URL are derived from the same registry entry). ``None`` when no H1
    line is found at all -- never invented."""
    for line in ctx.lines:
        if line.in_fence:
            continue
        match = _H1_LINE.match(line.text)
        if match is not None:
            # v4: "Aspose.PSD.FOSS for .NET" (PSD .NET's H1) spells the edition with a dot
            name = re.sub(r"[ .]FOSS\b", "", match.group(1).strip())
            if (enterprise.attributes or {}).get("level") == "family":
                name = name.split(" for ", 1)[0]
            return name
    return None


@detector(DETECTOR)
def enterprise_edition_naming(ctx: Context) -> DetectorResult:
    enterprise = ctx.fact(ENTERPRISE_FACT_ID)
    sole_product = _single_named_product(ctx)
    # Fall back to the H1-derived name only when the README's own prose names no commercial
    # product at all (sole_product is None) -- a prose mention, when one exists, is never
    # overridden by this fallback.
    if sole_product is None and enterprise is not None:
        sole_product = _commercial_name_from_h1(ctx, enterprise)
    edits: list[Edit] = []
    findings: list[Finding] = []
    for line in ctx.lines:
        if line.in_fence:
            continue
        claimed: list[tuple[int, int, str | None]] = []  # (start, end, replacement) within the line
        appositives: list[tuple[int, int]] = []  # v4: after a link already naming the product

        def full(name: str) -> str | None:
            return name if enterprise is None else _platform_name(ctx, name, enterprise, sole_product)

        for match in _LINK_RULE.finditer(line.text):
            label, url = match.group(1), match.group(2)
            named = full(label)
            claimed.append((match.start(), match.end(),
                            None if named is None else f"[{named} — Enterprise Edition]({url})"))
        occupied = [(s, e) for s, e, _ in claimed]
        for match in _BARE_RULE.finditer(line.text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            if _follows_named_link(ctx, line, match.start()):
                appositives.append((match.start(), match.end()))
                continue
            named = full(match.group(1))
            claimed.append((match.start(), match.end(),
                            None if named is None else f"{named} — Enterprise Edition"))
        occupied = [(s, e) for s, e, _ in claimed] + appositives
        for match in _BARE_PRODUCT.finditer(line.text):
            if _overlaps(match.start(), match.end(), occupied):
                continue
            if _follows_named_link(ctx, line, match.start()):
                appositives.append((match.start(), match.end()))
                continue
            if sole_product is not None and enterprise is not None:
                named = full(sole_product)
                claimed.append(
                    (match.start(), match.end(), None if named is None else f"{named} — Enterprise Edition")
                )
        occupied = [(s, e) for s, e, _ in claimed] + appositives
        for start, end, replacement in claimed:
            original = line.text[start:end]
            if replacement is None:
                findings.append(
                    Finding(
                        DETECTOR,
                        line.number,
                        original,
                        f"names the aspose.com product with a substitute for its proper name ({original!r}); "
                        "the fix is not applied because the README gives no platform-qualified name "
                        "for it at a platform-level Enterprise Edition target",
                    )
                )
                continue
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
