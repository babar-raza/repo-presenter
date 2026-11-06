# Safe checkpoint — 2026-11-06 (owner: "stop at a safe checkpoint")

Everything below is committed; nothing is running. No upstream write has ever been made by this repository.

## Delivery (state remote, re-certified under current code, zero provider calls)
| | Lane R | Lane L |
|---|---|---|
| Counted (latest seal passes every current check) | 1 | 9 |
| Independently accepted (calibrated) | 0 | 0 |
| Delivered upstream | 0 | 0 |

Every decrease today is a stricter check finding a **real** defect in an existing seal, each justified in
`data/recertification_baseline.json`, never a version bump discarding seals (R10 re-certification prevents that):
Imaging .NET R (dropped `<ProjectReference>` install block — BC-17), HTML Python L and Words Python L (live READMEs list
non-exported/nonexistent types and wrong type counts — BC-14). No seal was deleted; each needs a targeted repair.

## Where the work stands (resume here)
1. **Drop inventory (R14) — done, not yet applied.** `docs/investigations/2026-11-06-drop-inventory.md`,
   `data/drop_decisions.json`: 649 distinct dropped items across all 59 seals; 207 wrong drops (READD), 442 correct;
   the pipeline agrees with 73.7 %. Next: implement the rule table generally in reconciliation/BC-05/BC-17 (no hand
   fixes), measure agreement → 1.00 on the inventory, re-certify, targeted repairs.
2. **Acceptance redesign (R12) — adopted, S0–S4 started then stopped at checkpoint.** `docs/design/2026-11-06-acceptance-redesign.md`;
   stages S0–S3 and S4 workers were stopped before committing; restart them from the design.
3. **R15 enforcement** — `docs/wip/r15-portfolio-gate.patch` (portfolio readiness gate in `propose/effect.py`); its
   tests were not run; apply, inject a readiness reader in the publish-path tests, verify, then merge.
4. **Open PR #43** (mechanical false-claim rules BC-14, acceptance design, justified baseline) — CI result to check before merge.
5. **Then (R13)** portfolio-wide runs for all 36 repositories, both lanes, once, under the improved pipeline.

## Rules in force
R1–R15 in `docs/CONSOLIDATED_GOALS_2026-11-06.md` Part B and the top of AGENTS.md; operating rules in `ops/SUPERVISOR.md`.
