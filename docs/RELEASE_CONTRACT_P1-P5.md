# Release contract: P1–P5 — 2026-11-04

**Deliverable B** of the 2026-11-04 pre-execution correction directive. **Status: RELEASE_CONTRACT_ADOPTED_2026-11-04.**

This freezes the owner's five primary delivery objectives (P1–P5) as measurable release
acceptance criteria, mapped onto the existing G1–G8 requirements from
`docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md`. It strengthens, and does not replace or
weaken, any safety gate that document already established. Where P1–P5 is stronger than a
historical task-closure criterion, this contract governs *release* acceptance; the historical
record stays intact and unedited (non-negotiable #6, no rewriting accepted history).

## The eleven states (never collapsed into one another)

1. Work item implemented (code exists).
2. Tests passed (unit/integration, possibly mocked).
3. Capability exercised (ran at least once, for real).
4. Independent verification passed (a non-authoring check, not self-graded).
5. Candidate accepted (pipeline-level terminal state — `ACCEPTED`/`READY_FOR_PROPOSAL`).
6. Owner approval granted, where required.
7. Upstream action authorized (an explicit, named, owner-given go-ahead for a specific target).
8. Upstream PR created.
9. Upstream change merged or already live.
10. Live result independently verified (checked against the real upstream repo, not the local record).
11. Goal delivered (the full chain above, for that specific product/effect, end to end).

A status report that quotes one of these for a product does not imply any other. In particular:
"pipeline-good" (state 5, the only thing `core/portfolio_matrix.py` and `scripts/
portfolio_status.py` currently compute) says nothing about states 6–11.

## P1–P5 ↔ G1–G8 mapping and acceptance criteria

| Owner goal | Maps to | Measurable release acceptance criteria |
|---|---|---|
| **P1** — both lanes, 25 common products, live delivery | G1, G2, G7 | **Both** lanes pipeline-good (state 5) on the **same** >=25 authorized repository identities; each has a reproducible acceptance receipt under a calibration-*passing* reviewer (not merely state 5 under the current `NOT_PASSED` reviewer); quality >= the matching `aspose.org` refresh-candidate output, judged per lane's own role (Lane L = preservation + minimal correction, Lane R = complete regeneration); one selected output per repository reaches state 10 (live-verified), with an explicit no-change policy covering the "already correct, nothing to push" case — never a manufactured PR. |
| **P2** — operational issues lifecycle | G3 | Discovery → classification → dedup → approval → filing → assignment (where authorized) → tracking → re-detection → verified resolution → authorized closing, demonstrated end to end at least once with independent confirmation at state 10, not just one hand-run filing (today's actual evidence: filing only, states 1–3, not 4 for the lifecycle as a whole). |
| **P3** — reuse the existing GitHub App | G5 | Prefer the legacy repo's proven `actions/create-github-app-token@v2` pattern over new JWT/private-key code in this repo, unless a documented, specific requirement proves that insufficient (decided this pass — see `docs/DECISION_LOG.md`, 2026-11-04). Never reuse the old reviewer/judge or its historical `ACCEPT` verdicts as quality authority (already the case; re-affirmed). |
| **P4** — GitHub Actions execution & autonomy | G6 | Both lanes, full issues lifecycle, App publishing, scheduling, bounded retry/recovery, durable state/evidence, the existing two-job trust boundary (upstream code never sees write credentials or the LLM key), and the previously-accepted local-Docker validation requirement at the smallest credible scope — all through GitHub-hosted runners, demonstrated unattended at least once (state 3) and independently confirmed (state 4). |
| **P5** — durable caching, zero unnecessary calls | — (new, strengthens G6/G8) | A durable, source-aware preflight proves currentness **before** a provider call is made (not only after, via `noop_proof.py`'s current after-the-fact two-process ledger check), survives Actions-cache eviction, and is proven with zero recorded provider requests on an unchanged rerun. Correct invalidation is scoped (consumed-scope only, never a global reseal) — already a standing non-negotiable; P5 makes the *proof* mandatory, not just the intent. |

## Current honest baseline against this contract (see also Deliverable I, §4 of `docs/READINESS_PACKAGE_2026-11-04.md`)

Fresh run, this session, `python scripts/portfolio_status.py` (read-only, no state mutation):

```
registry_total: 36
lane_r_pipeline_good: 10   lane_l_pipeline_good: 12
both_lanes_pipeline_good: 5  (Cells-Java, Cells-Rust, Cells-TypeScript, Email-.Net, Imaging-.NET)
committed_bundles_lane_r: 1   committed_bundles_lane_l: 0
owner_reviewed: not tracked -- no owner review record exists anywhere in this repository
upstream PRs from this codebase: 0.  Upstream issues filed: 1 (local token, by hand, owner-authorized).
reviewer calibration: NOT_PASSED (data/reviewer_calibration.json, unchanged since 2026-10-27).
```

**Gap to P1's 25-common-products target: 20 more repositories need BOTH lanes pipeline-good
(currently 5), and every one of the resulting candidates — old and new — needs to clear a
calibration-passing reviewer before any of them count toward the 25, since none has today.**
**Gap to confirmed live delivery: 25, since the real count is 0.**

## What this contract does NOT decide

Whether the 2026-10-31 sweep that raised Lane R from 4 to 9–10 and Lane L from 4 to 12 (see
`docs/DECISION_LOG.md`, 2026-10-31 entry, decision 4: "coverage sweeps stay paused until the pilot
set reaches parity") is retroactively ratified, or must be re-verified under the paused rule, is
**not decided by this contract** — it is an explicit, open owner decision; see
`docs/READINESS_PACKAGE_2026-11-04.md` §E and `project/taskcards/TC-004.yaml`.
