# Repository Presenter: reconciled delivery program (2026-11-07)

## 0. READ FIRST (binding on any agent executing this plan)

1. **Read `docs/CONSOLIDATED_GOALS_2026-11-06.md` in full before any step** (Part A: owner's goals verbatim; Part B: rulings R1-R15; Part E: rulings R16-R26, 2026-11-07). It is the top authority: where this plan disagrees, the file wins and the plan is corrected. Then read `AGENTS.md`, `docs/MISSION_AUTHORITY.md`, `ops/SUPERVISOR.md`.
2. Every card carries `satisfies` (the goal clause it serves). After TC-012c, `gatecli validate` refuses any card without one. Re-read the goals at every card boundary.
3. The predecessors were trashed for:
   - self-graded acceptance;
   - seals invalidated by version churn;
   - plans that executed one card in eight;
   - Lane L quietly demoted;
   - circular metrics.

   Each has a named control in §9.
4. **Reporting header, every report:** `Lane R calibrated accepted | Lane L calibrated accepted | mechanism-passing only | actual upstream PRs | actual upstream issues | live-verified`, then what newly passed, what failed, and the next action removing the largest blocker.

**The goals:**

| Goal | Required outcome |
|---|---|
| G1 Lane L | Maintain live READMEs with minimal, evidence-backed, byte-preserving edits, triggered by a verified upstream change and a verified defect (R5) |
| G2 Lane R | Regenerate inadequate or missing READMEs from fresh source evidence, retaining valuable existing content |
| Target | About 25 independently accepted per lane (R4), or the complete portfolio (R13); Lane L per R20. **Both are reported; neither replaces the other** |
| G3 Issues | Real defect discovery, dedup, evidence, filing, tracking, redetection, closure, under safe authorization |
| G4 Publication | Reliable PR pipeline; mandatory integration proof on Cells/.NET and 3D/Python |
| G5 GitHub App | Scoped installation tokens; independently verified effects |
| G6 Autonomy | Unattended Actions and Docker: scheduling, bounded retries, recovery, durable state, observability |
| G7 Quality | Equal or exceed the published aspose.org README (R2): usefulness, correctness, completeness, examples, presentation, preservation |
| G8 Delivery | No endless planning, fake progress, false acceptance, churn, idle supervisor or test-only capability |
| Cross-cutting | Fresh truth and product-knowledge refresh; discovery of eligible repositories; maintainer content preserved without public attribution (R9); two independent lanes; independent QA; zero calls for unchanged inputs (P5); foss-mcp supervision; every repository accounted for; controlled writes; prepared, owner-approved replacement of `repository-presenter` |
| Principle | **Optimize for verified upstream value, not internal activity** (§14) |

## 1. Context

The review of `origin/main` (`545259436`) found 0 accepted candidates, five failed calibrations, 14 of 24 seals needing repair, 207 of 649 wrongly dropped items, and a supervisor that monitors but does not execute. A plan was built from code evidence, an architect's attack, preflight measurements and owner rulings.

The owner's corrective review (A-L) then found gaps in that plan. Those were reconciled, and a second independent architect audit of the reconciled plan found a further 14 defects, including:
- an audit cycle that made the first acceptance unreachable;
- forgeable acceptance records;
- parallelism that `gatecli` can't support yet.

All 14 are corrected below; §4 shows each verdict with its evidence.

## 2. Evidence base (verified on `origin/main` unless marked)

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
| F10 | Replay rests on best-effort `actions/cache` (`present.yml:211,294`); batch-chained keys; repairs overwrite under the original key; normalized outputs stored | `jobs.py:559-660`; `repair/loop.py:312` |
| F11 | Link and product-page verdicts re-fetched each run; UNCHECKED flips facts | `facts/links.py:380-400` |
| F12 | Lane L census: **19** with an upstream change; **16** with both a change and a defect; 5 with a defect and no change; GIS .NET has no README | Upstream API, all 36 |
| F13 | L-05 requires every detected defect repaired; 87 of 108 unrepaired are failing examples; only 3 detector families can edit | 22 failed Lane L records |
| F14 | About 61% of sampled failing examples (20/33) are verifier false positives; 3 are genuine API drift | Classified against upstream |
| F15 | Registry `full` modes inherited (`d074b23`); `full` arms issue filing; legacy PRs #7 on Cells C++ and Java; legacy issue writer armed | Registry history; legacy inventory |
| F16 | R14 rules are post-generation checks: 463 mechanical, 40 partly, 147 judgement; 144 decisions hand-made | `decide.py`; `drop_decisions.json` |
| F17 | Of 912 sealed units: 59% superseded, 32% kept, 9% omitted or deferred | 12 `dispositions.json` |
| F18 | Independent export readers exist only for Python and TypeScript; Rust's reader exists but its reachability is untrusted | `cpp.py:10,92`, `java.py:10,90`, `go.py:18,111`, `csharp.py:22-27`, `surface/extractor.py:229-234` |
| F19 | The secret-holding job has no toolchain and the toolchain job has no secrets (test-enforced) | `present.yml:7-13`; `tests/test_present.py` |
| F20 | Cost: Lane R seal median 86 calls (~1M tokens; ~14k tokens per call), max 217; Lane L ~4 calls; 18% Lane R re-asks | 24 bundle ledgers |
| F21 | State refs: fast-forward is client behaviour only (`git_backend.py:242`); refs under `refs/repository-presenter-state/` have no server protection; no CODEOWNERS; second idle local session exists | `bundle_store.py:38,110-141`; repo settings |
| F22 | Email .NET upstream HEAD equals its Lane R seal revision (`59125b4`); it is the only R seal that re-certifies | `gh api`; baseline |
| F23 | The parity benchmark is "the README published upstream", read at run time; no record says which live READMEs are aspose.org output | `readme/parity_gate.py` |
| F24 | `gatecli` has exactly one lease slot | `gatecli.py:411` |
| F25 | Registry ecosystems include Rust (1); hosted facts job sets up only Python, .NET and Java explicitly | `data/registry.json`; `present.yml:101-148` |
| F26 | The issues module has no ported redetection | `issues/file.py:103` |
| F27 | This machine's system-level `core.autocrlf=true` corrupts `git archive` output (used by `seal_history`/`recertify`), producing false "BUNDLE: corrupt" results in local verification. Fixed per-invocation with `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.autocrlf GIT_CONFIG_VALUE_0=false`; never via `git config` (no config file may be edited). Confirmed: a local re-run with this override exactly reproduced the committed `data/recertification_baseline.json` (R 1/12, L 9/12) | this session, 2026-11-07 |

## 3. Owner rulings: provenance

All were selected by the owner in interactive forms in this session (2026-11-07), among options the supervisor wrote; free text is quoted. Recorded verbatim with that provenance in `docs/CONSOLIDATED_GOALS_2026-11-06.md` Part E. None is inferred, and none widens write authority beyond what was selected.

| # | Ruling | Source |
|---|---|---|
| R16 | Justified no-edit Lane L = `NO_ACTION_JUSTIFIED`: terminal for R15, never an accepted candidate | "No-action: terminal, uncounted" |
| R17 | Sandbox-only writes before R15; mandatory targets exercised up to the write, with no write | "Sandbox only, R15 strict" |
| R18 | qwen3-next for every product route; supervisor (Claude or Codex) manually reviews qwen3-next output for audit and prompt tuning | "qwen3-next for everything"; owner plan comment |
| R19 | Superseded by the Final Directive (§8.4): the autonomy bridge is not lower priority; it runs from the start | "Build now, in parallel" (initial answer, since strengthened) |
| R20 | Strict R5; Lane L done = R13 complete-portfolio branch (every repository terminal); excluded defects go to Lane R | "Strict R5; done = full portfolio" |
| R21 | Lane L accepted on net improvement; residuals recorded internally and in the PR description | "Net improvement, residuals listed" |
| R22 | Nine repositories allowlisted for draft PRs only; three pilots switched to `full`; **upstream** issue filing off; CI consistency check; legacy PRs count as existing | "One authority; PRs only"; "Add them to allow list" |
| R23 | Superseded by R25 (history: "no budget allocation at this stage ... repop the same question") | free text |
| R24 | A repository blocked by a verified upstream defect is terminal for R15 under §6.2's evidence rules | "Evidenced external block is terminal" |
| R25 | Provider envelope 9,000 calls / 100M tokens; batches of six; per-batch cap 1.5x measured median; stop and report if cost per sealed candidate exceeds 2x the previous batch; zero-call steps first | re-asked: "Envelope with per-batch caps" |
| R26 | Prose judge measured first; rung (c) only after it fails; until then outputs are provisional | "No: measure the judge first" |

R22 scopes "issues off" to upstream repositories. R7 still allows issues on this repository (watchdog, blockers).

**Final Directive (2026-11-07, "Continuous Autonomous Execution"):** supersedes R19 and any looser reading of R8/R11. Full text: §8.4 and `docs/CONSOLIDATED_GOALS_2026-11-06.md` Part E.

**Owner actions** (open; none assumed):
1. Environment restricted to `main`, holding provider and App secrets and the audit seed key.
2. `recertification-gate` as a required check, with admins enforced.
3. **CODEOWNERS with required owner review** on `ops/audit/**`, the audit and acceptance workflows, `data/acceptance_*`, `ops/checks/calibration_status.py`, `src/repo_presenter/acceptance/`. Without it the supervisor could change the writer it is judged by.
4. Confirm R3's "reviewer calibration PASSED" means `acceptance_calibration.json` PASSED.
5. Sandbox repository with the App installed.
6. Write route for the hosted verify job.
7. Sweep-pause `LIFTED` marker (schedule).
8. Cutover approval.

Actions 1, 3 and 4 gate M1.

## 4. Review reconciliation matrix

**Owner's review A-L:**

| Concern | Verdict | Root cause | Correction (section) | Verification | Goal |
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

**Second architect audit (14 defects), all accepted after checking the code:**

| # | Defect | Fix |
|---|---|---|
| 1 | M9 seeds into *accepted* candidates, so M1 is unreachable (cycle) | Audit certification uses seeded copies of ≥10 sealed candidates per lane in any state; the candidate path is `provisionally-accepted` → audited → `independently-accepted` (§5.1, §5.3) |
| 2 | A1 needs production candidates, which need TC-024, which needs A1 (cycle) | TC-022a freezes A1 from the 924 never-asked cases, the 24 existing seals' units, and synthetic twins; production candidates feed a later A2 |
| 3 | Hosted-writer records forgeable by the supervisor's push rights | Counter accepts a record only with a verified GitHub artifact attestation from the writer workflow on `main` plus an API-confirmed successful run; CODEOWNERS owner review on acceptance code (owner action 3) |
| 4 | One lease slot; no `satisfies` check | TC-012c (per-card leases + `satisfies` validation) moves to the front |
| 5 | Rust and others not covered, so M7 is unreachable | Rust, Go, C++, TypeScript explicit in TC-017a and TC-021 |
| 6 | Sandbox flags break compilation | Dependency restore in an earlier networked step running no candidate code; cache mounted read-only; `--tmpfs /work:rw,exec`; unprivileged user (§6.4) |
| 7 | File-ownership overlaps | Re-done (§8.2) with serialized merges |
| 8 | Missing prerequisites (TC-022→TC-025, TC-028→TC-024, TC-033 gate source) | Added |
| 9 | Card numbers clash with the design's §6 map | Step 0 amends the design's map with a dated note |
| 10 | Thresholds vaguer than the design | Listed verbatim (§5.2) |
| 11 | Eligibility inflated (19 vs 16) | Both reported: 19 changed, 16 changed and defective |
| 12 | Budget omissions, tokens not computed | Recomputed (§7) |
| 13 | Coverage gaps: G3 redetection, knowledge refresh, discovery, G5, Docker | TC-035, TC-020, TC-031, TC-029, TC-021 (§8.2) |
| 14 | Auditor identity is self-declared | Independence rests on blind seeds, clean controls and code scoring, not identity (§5.3) |

**Already resolved (shown, not redone):** R10 zero-call recertification (`tests/test_recertify.py:72-79`); two-job trust boundary (`tests/test_present.py`); effect-specific write gate (`write_gate.py`).

## 5. The acceptance contract (one contract for TC-007, TC-011, records, counter, publication)

### 5.1 States (per candidate per lane; append-only; computed by code)

| State | Meaning | Written by |
|---|---|---|
| `generated` | output exists (new, repaired, restored, deterministic edit) | pipeline |
| `sealed` | sealed and durably published | pipeline |
| `deterministically-validated` | blocking checks and applicable deterministic mechanisms pass under current code | `recertify` / harness |
| `provisionally-accepted` | §5.2 items 1-4 hold | hosted acceptance writer |
| `independently-accepted` | provisional + its audit passed (§5.3) | hosted acceptance writer |
| `publication-ready` | accepted + R22 authority + R15/R24 gate + R3 gates | `propose.effect` precondition |
| `delivered` | PR exists (API) | counter |
| `live-verified` | merged + live README byte-equal to the seal | counter |

`mechanism-passing` = `deterministically-validated` or `provisionally-accepted`; it is never counted as accepted.

Terminal non-candidate states, separate: `NO_ACTION_JUSTIFIED`, `NOT_APPLICABLE`, `BLOCKED_EXTERNAL`.

### 5.2 Conditions (thresholds verbatim from the adopted design; none lowered)

1. **Every applicable class has a certificate.** Every class in `data/acceptance_responsibility.json` applicable to the lane has an owning mechanism with an append-only PASSED certificate in `data/acceptance_calibration.json`, measured on held-out A1 at the design's gates, with minimum n=30 per recall class and n≥50 clean twins and Wilson intervals reported:

   | Mechanism | Gates |
   |---|---|
   | M1 | recall ≥0.90; determinism 1.00 |
   | M2 | recall ≥0.90 per owned class; clean false reject ≤0.04 |
   | M3 | recall ≥0.90 per ecosystem; false CONTRADICTED ≤0.02 |
   | M4, M6 | recall ≥0.90 |
   | M5 | recall ≥0.90; R14 agreement 1.00; false reject ≤0.02 jointly with M7 |
   | M7 | recall ≥0.90; self-parity 1.00 |
   | M8 | recall ≥0.90 per class; false reject ≤0.02; JSON ≥0.90; stability ≥0.90 |
   | M10 | recall ≥0.90 |

   M3 must be certified for the candidate's ecosystem. Under R26, D14/D15 are owned by M8 until a recorded M8 failure opens rung (c).
2. **End-to-end gates PASSED on A1:** real A+D on-target recall ≥0.90; every operator ≥0.90; clean false reject ≤0.10.
3. **This candidate passes:** all mechanism verdicts PASS under the certified versions.
4. **Canaries:** every per-candidate canary was caught.
5. **Audit:** the candidate's audit passed (§5.3). Defective-accepted: 0 of the first 5 accepted per lane; then ≤1 of 10 and ≤2 of 25; M9 evidence validity 1.00.

**Fail-closed:**
- A missing, malformed or unknown file, an unowned class, a version without a certificate, or PASSED beside a failed gate: all NOT_PASSED.
- A record without a verified attestation (§5.3) does not exist for counting.
- `data/reviewer_calibration.json` stays the frozen iteration-5 record; a test asserts nothing writes PASSED there.

**One contract, every consumer:**
- **TC-007** check: `calibration_status.py PASSED --file data/acceptance_calibration.json --matrix data/acceptance_responsibility.json`. Negative controls: a mechanism set to NOT_PASSED; a class deleted. Each must fail.
- **TC-011:** counts only attested `independently-accepted` records. Negative control: invalidating the M2 certificate drops both lanes to 0.
- **`propose.effect` and `publication_ready`:** read only attested records.

**Mandatory CI negative tests:**
- deterministic-only → not counted and not publishable;
- provisional → not counted and not publishable;
- record lacking attestation, or attested by another workflow or ref → ignored;
- terminal states never increment accepted.

### 5.3 Audit independence (M9)

| Property | Mechanism | Test |
|---|---|---|
| Separation | auditor sessions get no generator context and never wrote the code or prompts under audit. Session metadata is recorded but **not relied on**: independence rests on the rows below | — |
| Frozen criteria | rubric, prompt and hash-ranked sample from a pre-committed cohort, committed and hashed before the audit | hash mismatch → void |
| Blind seeds | a hosted seeder job (from `main`) makes seeded copies of ≥10 sealed candidates per lane (≥20 seeds of shapes A, D, D9, D14, D15) and encrypts the manifest with the Environment key; the commitment hash is committed. Nobody who audits or supervises sees seeds | seed text in auditor inputs → void |
| Clean controls | known-clean copies are mixed in blind; auditor false-flag rate ≤0.10 is required, so "flag everything" cannot pass | false-flag gate |
| Source inspection | findings `supported \| false \| unverifiable` with `path:line@revision` against the pinned clone | — |
| Re-checkable evidence | code verifies each citation exists and holds the text (validity 1.00); a second auditor checks a hash-ranked 20% of citations support their verdicts | invalid → unresolved → no accept |
| Independent scoring | a hosted scorer from `main` decrypts after the audit is committed and computes recall, false-flag and defective-accepted | supervisor-computed score rejected |
| Dev/holdout isolation | tuning uses audit findings (dev); certificates only on held-out slices; failed slices burned | slice reuse refused |
| Attestation | seeder, scorer and acceptance writer emit GitHub artifact attestations; the counter runs `gh attestation verify --signer-workflow <writer>@refs/heads/main` and confirms the run via the API | forged-push record ignored (test) |
| Change control | CODEOWNERS owner review on all acceptance and audit code and data (owner action 3) | unreviewed change to those paths cannot merge |
| Model vs deterministic | deterministic mechanisms re-derive from source; the audit is model judgement; neither treats generator rationales as evidence | rationale edited to "verified" changes no verdict |

**Fail-closed:** with no Environment key, no seeder, so no audit passes and nothing is accepted.

## 6. Policies

### 6.1 Metrics (separate, never summed)

| Metric | Per lane |
|---|---|
| Registry coverage | n of 36 accounted for |
| Lane L R5 status | changed 19 / changed and defective 16 / unchanged 16 / no README 1 (today) |
| Terminal non-candidates | `NO_ACTION_JUSTIFIED`, `NOT_APPLICABLE`, `BLOCKED_EXTERNAL` counts |
| Candidates | sealed; deterministically validated; provisionally accepted |
| Accepted | independently accepted, **always shown as n/25** |
| Lane L completion (R20) | shown beside n/25, not instead of it |
| Findings | open findings by route and age |
| Upstream | PRs and issues created; live-verified |

R15 (with R16, R20, R24) requires every active repository terminal in both lanes. Terminal means: accepted; an R16 no-action; an R20 Lane-L-ineligible state with its finding routed; `NOT_APPLICABLE`; or a valid `BLOCKED_EXTERNAL`. Missing tooling on our side is never terminal.

### 6.2 Lane L, no orphaned class
- **R5 as written:** an upstream change and a defect. The earlier drift-only restriction is removed; drift or original is informational.
- **Baseline:** latest Lane L seal revision, else the presenter's last README commit, else the last README commit. It advances only under the current defect set.
- **Maintainer README edits after the baseline:** the live README is re-read at HEAD (M1); edits are computed on current bytes; older-byte candidates are stale and re-run.

**Findings register** (`data/readme_findings.json`, code-written; every finding has exactly one state and owner):

| Class | Route | Owner | Terminal when |
|---|---|---|---|
| Defect, upstream changed | Lane L edit (R21) | Lane L | edit accepted, or residual recorded |
| Defect, no upstream change | Lane R must-correct obligation | Lane R | Lane R accepted with it corrected |
| Maintainer README change introducing a defect | by change status, as above | per route | as above |
| Valid improvement, no trigger | Lane R | Lane R | Lane R accepted |
| Lane R not yet accepted for that repository | `OPEN`, visible, re-checked each batch | supervisor | never hidden; age reported |
| Source or library defect | `BLOCKED_EXTERNAL` + issue draft | supervisor | upstream fix lands, then re-run |

**`BLOCKED_EXTERNAL` validity:**
- reproduced by a recorded command at a pinned SHA;
- scope-specific evidence;
- issue draft prepared (filed only when authorized);
- follow-up owner named;
- re-checked on every upstream commit and at least every 7 days;
- unblock condition stated as a command;
- stale (no re-check in 7 days) → not terminal.

### 6.3 Preservation, replay, freshness
- **Obligations inventory per item**, over all units (retained, superseded, transformed, omitted): must-carry, may-drop or undecided.
- **Semantic preservation:** rule-tested equivalence (re-qualified names, same file at another path, same snippet at the verified version); paraphrase is an undecided item, audited.
- **Source-consistent maintainer material** is must-carry unless a probe positively contradicts it (R9 internal attribution).
- **Reader disagreement** → UNKNOWN: never blocks inherited text, never licenses generated text.
- **Judgement items** are stored decisions; no stored decision outranks a current check; audit findings tombstone them.
- **Replay keys:** item bytes + cited fact digests + source-file digests behind those facts + prompt and mechanism version. An incomplete key means no replay.
- **Integrity:** content-addressed entries with checksums; corrupt or missing = absent.
- **Concurrency:** fetch, union, retry ×3, then fail closed (retryable).
- **Source change:** targeted invalidation of affected keys only.
- **Observation freshness:** links and product pages 7 days; registry and package 24 hours before any publish; re-observed at publish; UNCHECKED never changes content.
- **Missing store:** recompute mechanical decisions; undecided ones re-asked within budget (ledgered) or the last seal kept; never silent regeneration.
- **Fixtures vs holdouts:**
  - the 649 R14 decisions are a regression fixture (fidelity 1.00), never a holdout;
  - holdouts are new drops from repairs and new repositories decided before scoring, plus a hash-ranked held-out part of the 147 judgement items.

### 6.4 Security and write authorization

| Path | Controls | Test |
|---|---|---|
| Third execution job | Hosted runner with `permissions: {}`, no secrets, `persist-credentials: false`. A preceding step restores dependencies with network but runs no candidate code; the cache is mounted read-only. Candidate code runs in the facts image: `docker run --network none --read-only --tmpfs /work:rw,exec,size=1g --user 65534 --cpus 2 --memory 2g --pids-limit 256 --cap-drop ALL --security-opt no-new-privileges`, with a timeout. No `actions/cache` restore. Inputs and outputs are size-limited, schema-validated JSON, treated as hostile | workflow parse test; canary snippet attempting network, write and env-dump must fail |
| Sandbox publication | entry bound to `provider_identity.repository_id`, valid only outside the registry; token minted with `repositories: [sandbox]` | registered or mismatched id → refused |
| Hosted verify | candidate tests run in a no-secret, read-only job; a `workflow_run` job from `main` validates the hash-bound artifact and writes receipts with attestation | branch-modified workflow changes nothing |
| Acceptance writes | attested hosted writer only; CODEOWNERS on acceptance paths | forged record ignored |
| Upstream writes | R22 (allowlist ∩ `full`, CI-checked); R15/R24; R3; legacy PRs in duplicate detection; upstream issues off | `dry_run` allowlisted → CI fails; duplicate → refused |
| Secrets | until owner action 1: no provider or App secret reaches any job outside the `main`-validated run-request path; seeder and writer fail closed without the Environment | missing Environment → non-zero exit before any write |
| App permissions (G5) | actual installation permissions read and recorded; per-effect token scope verified on the sandbox | mismatch → card fails |

## 7. Inference classes and budget (R25)

| Activity | Class | Calls |
|---|---|---|
| Recertify, obligations, probes, verifier, ledgers, funnel, census | no inference | 0 |
| Store-present rerun | replay | 0 |
| Item-level restore | no inference **only if proved** (TC-019 measures first); else product | 0 to ~1,000 (repairs of 12 seals at median) |
| Audit, labelling, tuning review | supervisory (Claude/Codex) | session time, outside R25 |
| M8 calibration | product | ≤500 |
| M8 on existing passing seals | product | ~8.6 prose units × 2.2 draws ≈ 19 per seal → ≤450 |
| M8 canaries (1 in 5 candidates) | product | ~100 |
| Cold rerun measurement (cohort of 6, ×2) | product, fresh inference | ~1,000 |
| Lane R generation, 22 never-sealed | product | 1,900-3,800 (median, up to 2x for reruns) |
| Lane L runs (M8 on edited prose; ~4 per run measured) | product | ~150 |
| **Total** | | **~5,100-7,000 calls** |

Tokens at the measured ~11.6-14k per call: **~59-98M of the 100M envelope**, so **tokens, not calls, are the binding constraint.** The budget gate tracks both and stops at the cap. If the upper estimate materializes, the 2x stop rule triggers first and the owner gets the measured numbers. Unauthorized routes are fail-closed by TC-015: no budget file or an exhausted batch means any non-replay call raises.

## 8. Program

### 8.1 Step 0 (supervisor; no card)
1. Fast-forward local `main`; clean tree. Confirm the idle second session holds no lease and does no work; record sole ownership.
2. `gatecli validate`, `doctor`, `tick`, `recertify --all --json`; reproduce the baseline.
3. Record R16-R26 verbatim with provenance (Part E, AGENTS.md). Amend the design's §6 card map with a dated note pointing to this program. Commit this plan as `docs/DELIVERY_PLAN_2026-11-07.md` (linked from AGENTS.md's first section), the reconciliation matrix, and decision-log entries for every retained, corrected and rejected recommendation. Routine-tier fixes (no card): stale design header, checkpoint line, mission matrix, `tick` historical gate. Update memory.
4. `data/provider_budget.json` from R25.
5. **VS0, zero calls:** the full path with today's mechanisms on Email .NET (Lane R; F22) and Slides Java (Lane L; R5 trigger present, naming defect). Record every gate each fails. Work follows those failures.
6. Raise owner actions 1-4 once, as precise items.

### 8.2 Cards (each in its own worktree and lease; merged in the stated order; verified by a fresh subagent plus `gatecli review`)

| Card | Scope | Depends | Owns | For |
|---|---|---|---|---|
| TC-012c | Per-card leases (disjoint `write_paths`) + `satisfies` validation | — | `ops/gatecli.py`, `ops/gateverify.py` (first) | everything parallel |
| TC-013 | Contract §5.1-5.2: records, certificate reader, attestation check, counter, `propose.effect` and `publication_ready` gates, TC-007/011 re-authored, negative tests | TC-012c | `src/repo_presenter/acceptance/` (record, reader), `ops/checks/portfolio_delivery_count.py`, `calibration_status.py`, `propose/effect.py` (first) | M1 |
| TC-015 | Budget gate (calls and tokens), inference-class tags | TC-012c | `core/llm/budget.py`, `jobs.py` (first) | product calls |
| TC-016 | Three-valued verifier, preludes, C++ fix; false-CONTRADICTED ≤0.02 on the 33 | TC-012c | `extractors/platforms/*_examples.py`, `readme/validation/provenance.py` | M1, M2 |
| TC-017a | Independent probes: C++, Java, Go, .NET, Rust (fixed reachability); reuse Python and TS; gate on the 20 mechanical A cases | TC-012c | `src/repo_presenter/acceptance/probes/` | M1, M2 |
| TC-018 | Obligations inventory, R14 rules as verification over all units, content ledger, §6.3 rules | TC-012c | `readme/validation/units.py`, `supersession.py`, `parity.py`, `readme/obligations/` | M1 |
| TC-020 | M7 scorecard; per-repository benchmark provenance (F23); product-knowledge refresh step | TC-012c | `readme/parity_gate.py`, `data/benchmarks.json`, facts `product_pages.py` | M1 |
| TC-014 | Audit §5.3: seeder, scorer, writer with attestations, clean controls, protocol | TC-013; owner actions 1, 3 | `.github/workflows/audit-*.yml`, `ops/audit/` | M1 |
| TC-017b | M2 claim proof: line-provenance classifier (new module), closed and open world, narrative ban | TC-017a, TC-016 | `readme/validation/claims*.py`, `surface_claims.py`, `readme/validation/line_provenance.py` | M1 |
| TC-021 | Hosted execution with explicit Python, .NET, Java, C++, Go, Rust, TS/Node toolchains; third sandbox job (§6.4); networked facts inside Docker | TC-016 | `.github/workflows/execute-*.yml`, sandbox runner, `present.yml` (first) | M1, M2 |
| TC-022a | Freeze A1: 924 cases + 24 seals' units + synthetic twins; stratified; second labeller with κ; digest committed | TC-013 | `data/acceptance_responsibility.json`, `data/registrations/A1*` | M1 |
| TC-022b | Harness measuring M1-M7, M10 and end to end on A1 | TC-022a, TC-016, TC-017b, TC-018, TC-020, TC-021, TC-025 | `ops/calibration/`, `data/acceptance_calibration.json` (via attested writer) | M1 |
| TC-023 | M8 prose judge: contract, sequential majority, calibration on A1's M8 slice (≤500 calls); a recorded failure opens a rung-(c) card | TC-015, TC-022a | `prompts/prose_judge.yaml`, `readme/review/prose_judge.py` | M1 |
| TC-024 | Seal-path switch: deterministic path + M8; canaries; import-graph check | TC-013, TC-017b, TC-018, TC-021, TC-023 (contract) | `present.py`, `recertify.py` (first), `bundle_store.py`, `cascade.py` (first) | M1, M2 |
| TC-025 | Lane L rebuilt: baseline, outcomes, net improvement, findings register, detectors (naming shapes, stale versions and packages, links), earned no-action | TC-016, TC-017a; merges after TC-024 | `lane_l*.py`, `readme/correction/`, `data/readme_findings.json` | M2 (M10 cert for M1's matrix) |
| TC-019 | Generator constraints (S3) + item-level restore (zero-call share measured first) | TC-018, TC-024 | `readme/reconciliation/`, `composition/`, `cascade.py` (after TC-024), `recertify.write_recertified` (after TC-024) | repairing seals; M4 |
| TC-028 | No-regression gate hardening; pre-computed justifications for the obligations change | TC-024 | `recertify.py` gate function (after TC-024) | M3 |
| TC-027 | Funnel §6.1; watchdog creates diagnosis cards that pre-empt the queue; this repository's own issues (R7) | TC-013, TC-012c | `ops/checks/delivery_funnel.py`, `supervisor-tick.yml`, `gatecli.py` (after TC-012c) | M3, M5 |
| TC-029 | Write authority R22; sandbox binding; R15 patch with R16/R20/R24 states; `BLOCKED_EXTERNAL` validity; App-permission recording (G5) | TC-013 | allowlist, registry modes, `propose/portfolio_gate.py`, `core/registry/`, `propose/effect.py` (after TC-013) | M4, M6 |
| TC-030 | Decision store + pinned observations + rerun harness; removes `actions/cache` | TC-015, TC-024, TC-021 | `core/state/decision_store.py`, `jobs.py` (after TC-015), `facts/links.py`, `present.yml` (after TC-021) | M3 |
| TC-031 | Evaluation cohorts (stratified, seeded, pre-registered); production queue with both-lanes coverage; org discovery (§7) | TC-012c | `data/eval_cohorts.json`, `ops/queue/`, `monitor/discovery.py` wiring | M4 |
| TC-032 | Engineering bridge: hosted verify (§6.4), routine dispatch | TC-012c, TC-027 | bridge workflows, `scripts/run_request.py`, `gatecli.py` (after TC-027) | M5 |
| TC-033 | Production schedule; `scheduled_execution_gate.py` reads `acceptance_calibration.json` and budget | TC-015, TC-031, TC-032, TC-030 | `scheduled_execution_gate.py`, `present.yml` schedule (after TC-030) | M5 |
| TC-035 | Issues lifecycle completion: redetection port (F26), tracking, closure on sandbox, read-only on issue #4 | TC-029 | `src/repo_presenter/issues/` | M6 |
| TC-009b, TC-010a | Re-authored per §6.4 and R17 | TC-029, TC-035; sandbox | existing | M6 |
| TC-012b | 72-hour unattended proof with injected failures | TC-032, TC-033 | evidence only | M5 |
| TC-034, TC-012a | Cutover preparation; owner-approved cutover | M6 | — | M7 |

**Serialized merges for shared files:**

| File | Merge order |
|---|---|
| `gatecli.py` | TC-012c → TC-027 → TC-032 |
| `propose/effect.py` | TC-013 → TC-029 |
| `jobs.py` | TC-015 → TC-030 |
| `present.yml` | TC-021 → TC-030 → TC-033 |
| `recertify.py`, `cascade.py` | TC-024 → TC-025 (import surface) → TC-019 → TC-028 |
| `provenance.py` | TC-016 only (TC-017b uses a new module) |

### 8.3 Milestones

| M | Definition | Exit (command) | Requires |
|---|---|---|---|
| M1 | First **independently accepted** Lane R | attested record; counter Lane R ≥1 | TC-012c-018, TC-020-025, TC-022a/b, TC-023; owner actions 1, 3, 4 |
| M2 | First independently accepted Lane L **real edit** (R5-valid, net improvement) | attested record; counter Lane L ≥1; byte-identity outside hunks | M1 mechanisms (TC-025 already in) |
| M3 | Repeatability, preservation, non-regression | store rerun byte-identical at 0 calls; cold agreement on undecided ≥0.90, judge majority ≥0.95 (budgeted); R14 fixture 1.00, holdouts ≥0.95 (drops) and ≥0.90 (judgement); a real mechanism change merges through the required gate with no count lost; 0 of first 5 accepted per lane defective | TC-019, TC-027, TC-028, TC-030; owner action 2 |
| M4 | Portfolio execution | 36 of 36 accounted for in both lanes; n/25 per lane reported; Lane L R20 completion; A2 from production; within R25 | TC-029, TC-031; budget |
| M5 | Autonomy with recovery | TC-012b: 72 hours unattended; injected worker death and lease expiry recovered; diagnosis cards acted on | TC-032, TC-033; owner actions 6, 7 |
| M6 | Authorized GitHub operations | sandbox draft PR, duplicate refusal, issue file-track-redetect-close via API; mandatory targets through every gate up to the write; App scope verified | TC-035, TC-009b, TC-010a; owner action 5 |
| M7 | Production delivery and cutover | after R15/R24 and R3: upstream draft PRs delivered and live-verified; owner-approved cutover | TC-012a; owner action 8 |

Complete only at M7, with M4's numbers reported. Terminal coverage or accepted cards alone never mean completion.

**Shortest path to M1:**
1. Step 0 / VS0;
2. TC-012c;
3. TC-013 ∥ TC-015 ∥ TC-016 ∥ TC-017a ∥ TC-018 ∥ TC-020 ∥ TC-022a;
4. TC-017b ∥ TC-021 ∥ TC-014 ∥ TC-023 (calibration after its registration);
5. TC-024 → TC-025 merge;
6. TC-022b;
7. Email .NET provisional, then audited: **M1**.

Lane R throughput: existing seals repair once TC-019 lands; new generation starts once TC-024 lands, through the queue under R25. Neither waits for TC-027, TC-030 or TC-031-033.

### 8.4 Continuous execution guarantee (owner directive 2026-11-07, supersedes R19's "lower priority")

**Operating loop:** PLAN → DISPATCH → EXECUTE → VERIFY → INTEGRATE → UPDATE STATE → SELECT NEXT → REPEAT. It never stops at a card, milestone, commit, failure or report. It extends `gatecli`, `gateverify`, leases and run-requests; no new framework.

- **TC-032 moves to the front, directly after TC-012c**, in parallel with the M1 cards.
- **Dispatch:** `gatecli dispatch-next --holder <worker>` leases every READY card whose `write_paths` are disjoint from live leases, up to a concurrency limit (default 4). After each verified ACCEPT, `worker-tick` immediately leases the next card.
- **Execute:** in this session, through worktree subagents. Beyond this session, a scheduled Claude cloud routine (the `schedule` skill) runs `gatecli resume-brief`, takes leases and works cards. Hosted jobs go through run-requests, since cloud sessions can't dispatch workflows directly.
- **Verify:** `gatecli review` re-runs checks and negative controls, then the hosted verify job (§6.4) attests the result. A worker never grades itself.
- **Recovery:**
  - expired lease → card READY again;
  - attempt 3 → `FAILED_INTERNAL` with diagnosis, then the next card;
  - rejected push → fetch, union, retry;
  - transient provider error → bounded retry, then marked retryable;
  - a dead session → the next routine run resumes from `ops/instructions.jsonl` and receipts (no conversation context needed).
- **Stall response:** READY work with no live lease past 60 min, or a funnel flat for 72 h, creates a **diagnosis card** with the top failure signature. It pre-empts the queue and is worked, not just reported.
- **Proof** (TC-032 exit, before M5): a recorded run in which the bridge, starting cold from durable state only, leases a READY card, a worker commits, hosted verify accepts, the next card is leased automatically, and an injected worker kill plus lease expiry both recover. The receipts and run IDs are committed.

## 9. Risk and regression register

| # | Risk | Owner | Preventive control | Falsifiable test | Response |
|---|---|---|---|---|---|
| 1 | Deterministic-only or provisional counted or published | TC-013 | §5 contract | CI negative tests | block merge |
| 2 | Self-certification or forgery | TC-014 / owner | blind seeds, clean controls, hosted scorer, attestation, CODEOWNERS | forged-record and leaked-seed tests | void; report |
| 3 | Unbudgeted calls or tokens | TC-015 | budget gate | uncredited call raises | stop batch |
| 4 | Reruns differ | TC-030 | store, keys, observations, majority | store byte-identical; cold measured | widen rules; re-key |
| 5 | Store freezes or stale replays | TC-030 | audit-consistent seeding; complete keys; tombstones | stale-key mutation | invalidate; recertify |
| 6 | Verifier "fixes" correct examples | TC-016 | three-valued first | ≤0.02 false CONTRADICTED | no repair |
| 7 | M2 misses false claims or common mode | TC-017 | independent probes; UNKNOWN on disagreement | held-out recall; probe-disabled control | no certificate |
| 8 | M8 fails | TC-023 | narrow scope; majority voting | A1 measurement | recorded failure → rung (c) (R26) |
| 9 | Orphaned finding | TC-025/027 | findings register | CI: every finding has an owner | triage |
| 10 | Terminal states inflate completion | TC-027/029 | §6.1; `BLOCKED_EXTERNAL` validity | funnel test | refuse |
| 11 | Sandbox or verify abused for production writes | TC-029/032 | id binding; `main`-only privileged jobs | refusal tests | fail closed |
| 12 | Sandbox escape | TC-021 | container limits | canary snippet | disable job |
| 13 | Workers overwrite each other | TC-012c | per-card leases; ownership; serialized merges | `doctor` scope check | revert; re-dispatch |
| 14 | Mechanism change breaks seals | TC-028 | required gate; cited justifications | gate test | refuse change |
| 15 | Infrastructure before output | supervisor | M1 path excludes TC-027/030-033; diagnosis cards | 72 h flat → diagnosis card | pre-empt queue |
| 16 | Goal drift | TC-012c | §0; `satisfies` validated | card without it refused | not executed |
| 17 | Upstream drift; concurrent writers | TC-029/030 | M1 freshness re-read; legacy PRs as existing; upstream issues off | stale-README test | recertify before PR |
| 18 | Interrupted work | TC-012c | lease expiry; idempotent transactions | kill-worker test | re-dispatch |
| 19 | Provider unavailable | TC-015 | bounded retry; ledgered failures | fault injection | retryable; next card |
| 20 | Rejected pushes | TC-030 | fetch, union, retry, fail closed | concurrent-writer test | retryable |
| 21 | Cache loss | TC-030 | store in refs | evicted-cache run | replay from refs |
| 22 | Owner actions delay M1 | supervisor | raised once in Step 0; everything else proceeds | — | report exact blocker |
| 23 | Token envelope exhausted | TC-015 | token tracking; 2x stop rule | ledger | stop; report with numbers |
| 24 | Local Windows git environment corrupts verification (F27) | supervisor | `GIT_CONFIG_*` env-var override per invocation; never a persisted `git config` change | re-run matches the committed hosted baseline | document per-command, don't edit config |

**Confidence:**
- *High:* diagnosis; contract; Lane L numbers; cycle removal.
- *Moderate:* M2 recall; probe accuracy.
- *Unknown until measured:* cold agreement on undecided items, M8 passability, A1 reaching minimum n from existing data (if not, the gap is reported and A1 waits for production candidates under budget), per-batch conversion and cost.

## 10. Pre-execution verification
1. Two independent architect audits were done. The second's 14 defects are corrected (§4); a third audit of the final card YAML runs before Step 0 commits.
2. Every §0 goal row maps to a card and a milestone exit (§8.2, §8.3); `docs/GOAL_TRACEABILITY.md` is produced by a check that fails on an unmapped goal.
3. No weakening: thresholds verbatim, iteration 5 frozen, R9, R10 and NN5 intact; additions only add strictness.
4. Vertical slice: VS0 has no prerequisites; the M1 path is minimal given §5.2.
5. Rulings traced (§3).
6. Ownership table and serialized merges have no overlap.
7. Failure modes (§9 rows 18-21) each have a test.
8. Existing evidence, seals and findings are preserved; nothing is deleted.

## 11. Deliverables (committed after verification and a clean-tree check)
1. `docs/reviews/2026-11-07-plan-reconciliation.md` (§4 with evidence).
2. `docs/DELIVERY_PLAN_2026-11-07.md` (this document).
3. `project/taskcards/TC-012c, TC-013..TC-035`, plus re-authored TC-007, TC-009b, TC-010a, TC-011.
4. `docs/GOAL_TRACEABILITY.md` (check-generated).
5. `evidence/funnel/2026-11-07.{json,md}` (one-off script now; TC-027 replaces it).
6. Critical path (§8.2-8.3).
7. Risk and regression plan (§9).
8. `docs/DECISION_LOG.md` entries.

**Current funnel (2026-11-07, from state refs, reproduced locally with the `GIT_CONFIG_*` override and matching the committed baseline exactly):**

| | Lane R | Lane L |
|---|---|---|
| Registered | 36 | 36 |
| Durable records | 34 | 34 |
| Sealed (latest) | 12 | 12 |
| Deterministically validated (recertified) | 1 | 9, of which 8 are no-ops and 1 is a naming edit with no upstream change |
| Provisionally accepted / independently accepted | 0 / 0 | 0 / 0 |
| R5: changed / changed and defective | — | 19 / 16 |
| Upstream PRs / issues by this system | 0 / 0 | 0 / 0 |

Historical: 1 owner-authorized issue (#4, 2026-10-21). Legacy: 2 open PRs (#7).

After approval: Step 0, then TC-012c, then the M1-path cards in parallel worktrees immediately.
