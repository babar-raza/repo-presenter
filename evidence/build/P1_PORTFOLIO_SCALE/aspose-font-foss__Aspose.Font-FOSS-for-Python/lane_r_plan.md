# Lane R plan — aspose-font-foss/Aspose.Font-FOSS-for-Python

## Case classification

Mission §7 case (B)-leaning: the live README is substantial and clearly carries
real, valuable, repository-specific content (the buyer-persona framing, the
capability snapshot, the variable-font workflow depth) — but it does not
conform to the portfolio's fixed-core contract at all (see `facts.json`
`F-STRUCTURAL-NONCONFORMANCE`: no badge row, no banner, no standard Navigation,
no At a Glance diagram, no canonically-named Installation/Scope and
Limitations/Development and Testing sections, no Enterprise Edition link).

## Status: BLOCKED_NEEDS_FULL_REBUILD, not attempted this pass

A genuine Lane R reconstruction here means building the fixed-core skeleton
(badge row with a *verified* build-status/package/license badge — none exist
today to reuse; a banner image at the family's conventional
`products.aspose.org/media/font/python/banner-readme.png` path, **not yet
confirmed to actually resolve** and must not be fabricated into the candidate
without checking; a real At a Glance diagram grounded in verified format/
capability facts) while retaining every one of the "Three Buyer Workflows" /
"Who Is This For?" / "Capability Snapshot" sections as inherited additions,
per mission §3's "each live README owns its own tone... never replaced by a
template" rule — this is a genuinely large composition task (the live
document covers ~30 distinct classes and dozens of CLI commands), not a
few-line patch, and doing it honestly (verifying the banner URL, badges, and a
representative sample of the ~30-class capability surface) is disproportionate
to this batch pass's time budget alongside 5 other repositories.

**Recorded as a specific, named follow-up item, not silently skipped:**
`NEXT_READY_ITEM: aspose-font-foss Lane R full rebuild` — requires (1)
confirming or sourcing a real banner image URL, (2) deriving real package/
build/license badges, (3) spot-verifying a representative sample (8-10) of the
~30-class capability surface by execution (the package is pip-installable per
`facts.json` F-PKG-NAME-WRONG-IN-README's corrected name), (4) composing the
fixed-core skeleton around the existing persona content as inherited
additions, (5) independent review.

## What *was* done this pass

The one confirmed, severe, safe-to-fix defect (missing/wrong installation
instructions — `facts.json` F-PKG-NAME-WRONG-IN-README) was corrected via Lane
L (`lane_l_candidate.md`, `lane_l_candidate.diff`) since that's a minimal,
evidence-backed, safe patch regardless of the larger structural question. No
`lane_r_candidate.md` is produced for this repository this pass — producing
one that merely re-wrapped the Lane L patch without actually building the
fixed-core skeleton would misrepresent Lane R's own output as more complete
than it is.
