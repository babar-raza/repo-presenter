# Lane R document plan — aspose-3d-foss/Aspose.3D-FOSS-for-Python

Per mission §7 step 4: "Derive a repository-specific document plan from the *live*
structure and same-family/current-peer observations; no universal forced section
order or uniform prose voice."

## Case classification

This repository falls under mission §7 case (A): "a substantial live README as the
structural/content baseline" — not case (B) (deficient or missing). The live README
is 793 lines, already matches the fixed-core section set exactly (Navigation, At a
Glance, Key Capabilities, Installation, Dependencies, Quick Start, Additional
Examples, API Reference, Documentation & Resources, Scope and Limitations,
Development and Testing, License), already uses the correct badge order, the correct
banner placement, the correct Enterprise Edition naming, and a left-to-right,
non-stacked At a Glance diagram. It already discloses nine precise, evidence-cited
limitations in its own voice (the COLLADA-export-unreachability bullet in particular
is independently reproducible and, on fresh re-derivation this session, exactly
matches the live text's own stated root cause — see `facts.json`
`F-COLLADA-EXPORT-UNREACHABLE`).

## Why this plan converges to the live structure rather than inventing a new one

Mission §7 is explicit that Lane R "can rebuild a coherent, excellent document, but
not by treating inherited content as disposable inputs to a generic shell," and
mission §3 (idea.md distillation, `docs/MISSION_AUTHORITY.md`) holds that "each live
README owns its own tone, prose structure, and heading skeleton; these are never
replaced by a template." Given a live document that already satisfies the fixed-core
contract, correctly orders its own content, and is independently verified accurate on
every unit this session had time to check except one (see `content_units.json`), the
*correct* Lane R output is not a differently-organized document — it is the same
structure and voice, with only the independently-verified defect corrected. A
Lane R engine that produced a materially different document here, for no reason
other than demonstrating that it *can* generate from scratch, would itself be a
mission violation (generic-shell overfitting), not a stronger proof.

The genuinely independent parts of this exercise, auditable separately from Lane L's
output: (1) the full content-unit inventory (`content_units.json`, 26 units, every
one individually dispositioned against `facts.json`, not copied from the Lane L
diff); (2) this plan document, reasoned from the live structure and the fixed-core
contract rather than from the Lane L patch; (3) the independent review below, which
re-derives its verdict from the inventory and facts, not from the Lane L review.

## What a *different* peer-family observation would have changed, and didn't

The sibling repository `aspose-3d-foss/Aspose.3D-FOSS-for-.NET` is the same product
family on a different platform. Its own README was not independently re-verified
this session (out of scope for the P1 single-pinned-repository slice), so no
cross-platform structural borrowing was applied here — doing so without verifying
the .NET README's own current accuracy would import unverified content, which
mission §3's "each live README owns its own tone" rule and the general
no-invented-claims rule both forbid. This is recorded as a deliberate scope boundary
for P1, not an oversight: cross-family harmonization is explicitly a P2 concern
(mission §12, "generalize by failure class... representative cross-ecosystem
cohort"), not a P1 one.

## Resulting candidate

Given the above, the Lane R candidate for this repository is `lane_r_candidate.md`,
which is byte-identical to `lane_l_candidate.md` — not because Lane R deferred to
Lane L's output, but because both lanes, applied independently to the same verified
facts and the same live-structure-as-reference rule, correctly converge on the same
document when the live README is already this close to the verified truth. A
portfolio with a weaker or missing live README would show the two lanes' outputs
diverge far more; this pinned repository happens to be a case where they shouldn't.
