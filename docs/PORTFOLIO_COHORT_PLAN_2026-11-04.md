# Portfolio cohort authorization plan — 2026-11-04

Resolves §12 of the follow-up directive. Planning only — does **not** change any registry write
mode, does **not** start a campaign. `data/registry.json` is unmodified by this document.

## Current real baseline (re-confirmed this pass)

- 36 registered repositories; 30 `mode: dry_run`, 6 `mode: full`.
- 5 repositories both-lane pipeline-good (Cells-Java, Cells-Rust, Cells-TypeScript, Email-.Net,
  Imaging-.NET) of the 25-common-product target.
- 1 repository has a sealed, independently-reviewed bundle committed to `candidates/`.
- 0 repositories have a confirmed live upstream delivery.

## Per-repository cohort checklist (what every one of the 25 needs, before counting toward P1)

| Check | Source | Automatable today? |
|---|---|---|
| Product/repository eligibility | `data/registry.json`, `active: true` | Yes |
| Current upstream revision (not stale) | fresh clone, compared to the sealed bundle's `source_revision` | Yes |
| Both-lane processability | `scripts/portfolio_status.py` (`record_r`/`record_l`) | Yes |
| Required ecosystem toolchain available | `present.yml`'s per-ecosystem setup steps | Yes, for `net`/`java`; others degrade to `NOT_VERIFIED` |
| Output quality verified | `scripts/parity_benchmark.py` against the `aspose.org` reference, where one exists | Partial — structural only, not factual/prose quality (R11, still open) |
| Lane selection and preservation policy | owner decision, per repository | No — owner-level |
| Write-mode authorization | owner decision; `write_gate.py` enforces | No — owner-level, one repo (`3d/python`) named explicitly in `TC-009b` |
| PR permission and merge dependency | `TC-009b`'s own gate | No — owner-level |
| Live verification | `gh api` against the real upstream default branch | Yes, once a PR exists |
| Failure/retry disposition | supervisor fix-queue sweep (already practiced, `AUDIT_2026_11_01_ITEM_7`) | Yes |

## Staged cohort sizing (bounded, not all-at-once)

1. **Cohort 0 (proof, already done):** 1 repository (3D-.NET), Lane R only. Complete.
2. **Cohort 1 (next, no new owner decision needed to start):** the 4 remaining both-lane
   pipeline-good repositories (Cells-Java, Cells-Rust, Cells-TypeScript, Email-.Net) — run the
   fix-queue sweep to close any remaining lane gaps, then benchmark each against its
   `aspose.org` reference the same way TC-006 did for 3D-.NET.
3. **Cohort 2 (after TC-007 passes calibration and TC-009b proves both mandatory pilots):**
   bounded batches of 5 repositories at a time from the remaining 31, prioritizing repositories
   whose toolchain is fully automatable (`net`/`java`) over ones that degrade to
   `NOT_VERIFIED`-only example checks.
4. **Cohort 3 (final):** the remainder, once failure-rate and quality from Cohorts 1–2 justify
   wider parallelism (directive §5: "increasing parallelism as failure rates and quality
   permit," not a fixed schedule).

## What this plan does NOT do

Flip any registry entry's `mode`. Dispatch any hosted run. Authorize any PR. Those are explicit,
later, owner-gated steps (`TC-002`, `TC-004`, `TC-009b`, `TC-011`) — this document exists so that
when those gates clear, there is already a reviewable, bounded, sequenced plan rather than an
improvised all-at-once campaign.
