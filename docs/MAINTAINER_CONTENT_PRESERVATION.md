# Maintainer-Authored Content Preservation & Calibration

Owner requirement, 2026-11-05 (`docs/DECISION_LOG.md`, anchor
`OWNER-REQUIREMENT-2026-11-05-MAINTAINER-CONTENT`). Recorded verbatim as the owner gave it, in answer to
the conflict reviewer calibration iteration 4 found between the S9 preservation checks (which keep
maintainer text no fact supports) and the reviewer's contract (which rejects such text as unsupported).
Binding for both lanes; referenced from `docs/MISSION_AUTHORITY.md`.

---

**Objective:** Preserve valuable maintainer-authored information from live upstream READMEs, even when it
cannot be independently verified against repository evidence.

**Requirements:**

1. **Preserve unverified but valuable content**, including project history, maintainer insights, future
   plans, background information, and other context that may benefit users, public awareness, or product
   understanding.
2. **Distinguish unverified from false.** Lack of repository evidence alone is not grounds for deletion.
   Preserve such content with appropriate attribution or qualification; do not present uncertain claims as
   verified facts.
3. **Review and refine problematic content** that:
   - Contradicts verified upstream repository truth.
   - Misrepresents the product or damages brand credibility.
   - Contains excessive, irrelevant, or promotional links.
   - Uses keyword stuffing, manipulative SEO, or other low-quality practices.
   - Provides little or no value to consumers.
4. **Apply proportionate remediation:** Retain valuable content as-is where appropriate; otherwise
   clarify, qualify, rewrite, reorganize, or merge it into the candidate. Remove content only when it is
   demonstrably harmful, misleading, irrelevant, or beyond reasonable repair.
5. **Preserve maintainer intent and unique knowledge.** Avoid unnecessary rewriting, loss of historical
   context, or replacing valuable human-authored information with generic generated content.
6. **Calibrate through portfolio-wide examination.** Systematically inspect live READMEs across products
   and platforms, identify recurring patterns and edge cases, and refine preservation rules based on actual
   examples rather than assumptions.
7. **Maintain traceability.** Record what was preserved, modified, relocated, or removed, with
   justification. Never silently discard meaningful maintainer-authored information.

**Acceptance criteria:** Candidates retain the maximum useful maintainer knowledge without compromising
factual accuracy, consumer value, readability, brand integrity, or SEO quality.

**Guiding principle:** Repository truth governs verifiable technical claims; maintainer knowledge remains
valuable even when independently unverifiable. Treat the two differently rather than automatically
discarding the latter.

---

## What this changes, as of 2026-11-05 (supervisor note, not part of the requirement)

* **The reviewer's standard.** `prompts/independent_review.yaml` v17 says "a specific claim that only
  such a unit [an inherited maintainer unit] states is still unsupported". Under this requirement that is
  correct only for a claim presented as verified; unverified maintainer content that is attributed or
  qualified is not a defect. The reviewer contract has to distinguish the two.
* **Calibration labels.** Iteration 4's curators removed unverified maintainer text as `unsupported_claim`
  defects. The next held-out corpus must label attributed maintainer content as clean and only
  unattributed, presented-as-verified, contradicted or harmful content as defective.
* **S9 preservation checks (BC-04/05/07)** stay: they already refuse silent loss, which requirement 7
  demands. What is new is a recorded, attributed way to keep the content rather than a choice between
  verbatim retention and deletion.
* **Not implemented yet.** No code, prompt or label changed with this record.
