# Plan reconciliation record — 2026-11-07

Standalone evidence record for the full program at `docs/DELIVERY_PLAN_2026-11-07.md`. This file holds the
evidence base, the owner-review reconciliation matrix, and the second independent-architect audit, so a future
session can verify what was found and how each finding was resolved without re-deriving it.

## Chain of review

1. An external independent review of `origin/main` (`545259436`, 2026-11-06) found 0 independently accepted
   candidates, five failed reviewer calibrations, 14 of 24 latest seals needing repair, and 207 of 649 dropped
   README items wrongly dropped, diagnosing a monolithic LLM reviewer asked to prove everything and a
   supervisor that monitors but does not execute.
2. The supervisor verified every claim against the code (not taken on faith), found corrections and 21
   additional findings (F1-F21 below), and built a first delivery plan.
3. The owner's own corrective review (concerns A-L) found gaps in that plan: acceptance integrity, supervisor
   self-certification, zero-call honesty, Lane R deferral, Lane L orphaned classes, false portfolio completion,
   evaluation/scheduling conflation, no vertical slice, replay and freshness gaps, security gaps, a flat
   critical path, conflated milestones, and missing pre-execution verification.
4. The plan was reconciled against A-L, then a second independent architect audit of the reconciled plan found
   14 further defects, the most damaging being a circular audit requirement that made the first acceptance
   unreachable and forgeable acceptance records.
5. All corrections were folded into `docs/DELIVERY_PLAN_2026-11-07.md`. The owner recorded rulings R16-R26 and a
   "Final Directive" on continuous autonomous execution; both are in `docs/CONSOLIDATED_GOALS_2026-11-06.md`
   Part E verbatim.

## Evidence base (verified on `origin/main` unless marked; F27 found in this session during execution)

| # | Finding | Evidence |
|---|---|---|
| F1 | 8 of the 9 "counted" Lane L seals are byte-identical to the live README | Blob SHAs at each baseline seal |
| F2 | R5's upstream-change trigger not implemented; `monitor/drift.py` unused | `correction/engine.py:77`; `drift.py:175-178` |
| F3 | The old reviewer blocks sealing as well as counting (31 of 44 `FAILED_INTERNAL`) | 68 records; `present.py:348-352` |
| F4 | All failures predate the fixes since 2026-11-01; 17 of 94 hand dispatches succeeded | Record dates; Actions history |
| F5 | Production gated on calibration, which needs production candidates | `scheduled_execution_gate.py:22,75`; design §4.1 |
| F6 | `recertification-gate` not required; substring justification; unreadable base trusts the PR | Branch protection; `recertify.py:700-715` |
| F7 | A no-edit result can't get a model ACCEPT, yet sealing demands one | `present.py:348`; `recertify.py` `_model_accept` |
| F8 | The model doesn't repeat at temperature 0, seed 1 (three identical-hash calls, three different answers); reviewer stability 0.70-0.90 | Imaging seals; it3-it5 |
| F9 | Same revision and versions, different README (Imaging: 7 of 60 disposition kinds) | Seal history |
| F10 | Replay rests on best-effort `actions/cache`; batch-chained keys; repairs overwrite under the original key; normalized outputs stored | `jobs.py:559-660`; `repair/loop.py:312` |
| F11 | Link and product-page verdicts re-fetched each run; UNCHECKED flips facts | `facts/links.py:380-400` |
| F12 | Lane L census: 19 with an upstream change; 16 with both a change and a defect; 5 with a defect and no change; GIS .NET has no README | Upstream API, all 36 |
| F13 | L-05 requires every detected defect repaired; 87 of 108 unrepaired are failing examples; only 3 detector families can edit | 22 failed Lane L records |
| F14 | About 61% of sampled failing examples (20/33) are verifier false positives; 3 are genuine API drift | Classified against upstream |
| F15 | Registry `full` modes inherited; `full` arms issue filing; legacy PRs #7 on Cells C++ and Java; legacy issue writer armed | Registry history; legacy inventory |
| F16 | R14 rules are post-generation checks: 463 mechanical, 40 partly, 147 judgement; 144 decisions hand-made | `decide.py`; `drop_decisions.json` |
| F17 | Of 912 sealed units: 59% superseded, 32% kept, 9% omitted or deferred | 12 `dispositions.json` |
| F18 | Independent export readers exist only for Python and TypeScript; Rust's reader exists but its reachability is untrusted | extractor platform modules |
| F19 | The secret-holding job has no toolchain and the toolchain job has no secrets (test-enforced) | `present.yml:7-13`; `tests/test_present.py` |
| F20 | Cost: Lane R seal median 86 calls (~1M tokens), max 217; Lane L ~4 calls; 18% Lane R re-asks | 24 bundle ledgers |
| F21 | State refs: fast-forward is client behaviour only; no server protection; no CODEOWNERS; second idle local session existed | `bundle_store.py`; repo settings |
| F22 | Email .NET upstream HEAD equals its Lane R seal revision; it is the only R seal that re-certifies | `gh api`; baseline |
| F23 | The parity benchmark is read at run time; no record says which live READMEs are aspose.org output | `readme/parity_gate.py` |
| F24 | `gatecli` has exactly one lease slot | `gatecli.py:411` |
| F25 | Registry ecosystems include Rust; hosted facts job sets up only Python, .NET and Java explicitly | `data/registry.json`; `present.yml` |
| F26 | The issues module has no ported redetection | `issues/file.py:103` |
| F27 | This machine's system-level `core.autocrlf=true` corrupts `git archive` output, producing false "BUNDLE: corrupt" results in local verification; fixed per-invocation with a `GIT_CONFIG_*` environment override, never a persisted config change | this session, 2026-11-07 |

## Owner review (A-L): reconciliation matrix

| Concern | Verdict | Root cause | Correction (plan section) | Verification | Goal |
|---|---|---|---|---|---|
| A. Phase-1 "accepted" without calibration | Valid | judge-off treated as an acceptance route before its trigger | single contract §5; R26 | negative tests §5.2 | G8, §13 |
| B. Fresh subagent ≠ independent | Valid | independence procedural only | §5.3: encrypted seeds, clean controls, hosted scoring, attestation, CODEOWNERS | seeded-recall, false-flag, leak and forgery tests | §8, NN5/6 |
| C. Zero-call claims | Valid | replay, reconstruction and cold rerun conflated | §7 classes; budget gate | uncredited call raises | P5, R25 |
| D-R. Lane R deferred | Valid | budget (now R25) | Lane R on the M1 path; queue after TC-024 | M1 path has no reporting or scheduler prerequisite | G2 |
| D-L. Orphaned classes | Partial | no owned state for excluded defects; drift-only rule exceeded R5 | findings register §6.2; drift-only removed | every finding has an owner (CI) | G1, §5 |
| E. False completion | Valid | terminal ≠ accepted not enforced | §6.1 metrics; `BLOCKED_EXTERNAL` rules | terminal never increments accepted | §3, §13 |
| F. Random production order | Partial | evaluation vs scheduling conflated | cohorts vs queue (TC-031) | cohort digest pre-committed | §3 |
| G. No vertical slice | Valid | machinery-first | VS0 in Step 0; M1/M2 slices | failing gates recorded | G8 |
| H. Replay and freshness | Partial | rules unspecified | §6.3 | corruption, loss, concurrency, stale tests | §4, §9 |
| I. Security | Partial | sandbox, verify and sandbox-write paths undefined | §6.4 | per-control failing tests | §7, §9 |
| J. Critical path | Valid | flat list | §8 graph, ownership, serialization | §10 audit | G8 |
| K. Milestones | Valid | internal vs upstream conflated | §8.3 | command exits | §13 |
| L. Pre-execution verification | Valid | — | §10; audit done twice | audit reports committed | §8 |

## Second independent architect audit: 14 defects, all accepted and corrected

| # | Defect | Fix |
|---|---|---|
| 1 | M9 seeded into *accepted* candidates, making M1 unreachable (cycle) | Audit certification uses seeded copies of ≥10 sealed candidates per lane in any state; `provisionally-accepted` → audited → `independently-accepted` |
| 2 | A1 needed production candidates, which needed TC-024, which needed A1 (cycle) | TC-022a freezes A1 from the 924 never-asked cases, the 24 existing seals' units, and synthetic twins |
| 3 | Hosted-writer records forgeable by the supervisor's push rights | Counter accepts a record only with a verified GitHub artifact attestation plus an API-confirmed run on `main`; CODEOWNERS owner review |
| 4 | One lease slot; no `satisfies` check | TC-012c (per-card leases + `satisfies` validation) moved to the front |
| 5 | Rust and others not covered, so M7 was unreachable | Rust, Go, C++, TypeScript made explicit in TC-017a and TC-021 |
| 6 | Sandbox flags as drafted would break compilation | Networked dependency-restore step before isolation; read-only cache mount; writable exec tmpfs |
| 7 | File-ownership overlaps | Re-done with serialized merge order |
| 8 | Missing prerequisites | Added |
| 9 | Card numbers clashed with the design's own §6 map | Step 0 amends the design's map with a dated note |
| 10 | Thresholds vaguer than the adopted design | Listed verbatim |
| 11 | Eligibility inflated (19 vs 16) | Both reported separately |
| 12 | Budget omissions; tokens never computed | Recomputed with tokens as the binding constraint |
| 13 | Coverage gaps: G3 redetection, knowledge refresh, discovery, G5, Docker | Each given a card |
| 14 | Auditor identity self-declared | Independence rests on blind seeds, clean controls and code scoring, not identity |

## Already resolved before this review (shown, not redone)

- R10 zero-call recertification (`tests/test_recertify.py:72-79`).
- Two-job trust boundary (`tests/test_present.py`).
- Effect-specific write gate (`write_gate.py`).
