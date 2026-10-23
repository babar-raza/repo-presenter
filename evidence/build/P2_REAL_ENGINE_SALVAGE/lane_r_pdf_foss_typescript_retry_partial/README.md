# aspose-pdf-foss/TypeScript retried — S4's missing-disposition rejection does not recur, but a brand-new blocker surfaces at S8

2026-10-23. `aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript`. First attempt at this repository's
cascade (around the twenty-fourth cascade round, 2026-10-22) failed closed at S4
`source_reconciliation` on a missing-disposition rejection, compounded by a separate pre-existing
gap: `run_lane_r_reconciliation.py` has no `recover=` wired for S4 at all.

Retried the full cascade from S4 onward with a fresh LLM sample.

## The real result, stage by stage

| Stage | Calls | Outcome |
|---|---|---|
| S4 `source_reconciliation` (retry) | 14 batches, 14 calls | All accepted. 541 inherited units reconciled (the full, uncapped set — this is the largest `source_reconciliation` fan-out run this session). The original missing-disposition rejection did not recur. |
| S5 `presentation_planning` | 1 call | Accepted on the first attempt. |
| S6 `section_authoring` | 1 per authored task | All accepted on the first attempt. |
| Render | 0 (deterministic code) | 155,143 characters, 1,525 lines — the largest pre-coherence render this session, surpassing the twenty-third cascade's 133,810. |
| S8 `coherence` | 3 batches planned, 1 call fired | **Failed closed, deterministically**: `section_authoring: output truncated at the manifest's max_output_tokens (8000); raise the budget or bound the output, never retry.` |

## A new, distinct, unrelated rough edge — not a retry-fixable fluke

Unlike every other S6/S8 rejection documented this session (which are content-level semantic
rejections that a fresh LLM sample can clear), this failure is a **deterministic token-budget
truncation**: the `section_authoring` (coherence mode) manifest caps `max_output_tokens` at 8000,
and this repository's first coherence batch exceeds that cap. The job framework's own error message
is explicit that retrying is pointless here (`never retry` — raising the budget or shrinking the
batch are the only fixes, both of which are source changes out of this evidence-gathering round's
scope).

This is the **seventh distinct unrelated pre-existing rough edge** observed this session (after:
the "TrueType" identifier rejection, two title-restatement rejections, the "cites facts outside
this section's set" rejection, the missing-disposition S4 rejection with no `recover=`, and the
"sections()" identifier rejection). It is also the first one tied directly to this repository's
sheer scale (541 inherited units, 155K characters pre-coherence) rather than to any single
sentence's wording.

## Honest scope limits

- S4 reconciliation and S6 authoring are now fully unblocked and reproducibly succeed for this
  repository (confirmed via a real, independent retry, not a cache hit).
- S8 coherence cannot complete for this repository as currently batched/budgeted. This blocker is
  structural (token budget vs. batch size), not stochastic — a further retry with the same batch
  sizes would be expected to fail the same way every time, so it is not retried again this round.
- This repository remains without a full S3-S8 cascade. The new blocker is recorded here rather
  than silently retried, per the "no agent may silently grade or overrule its own negative finding"
  non-negotiable.
