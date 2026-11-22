# Component inventory, gaps and parallel work plan (2026-11-22)

Scope: owner feedback R50 (BL-720), deadline R49 (today). Read-only investigation at `origin/main` c9de0c94 plus the old
project checkout (`/home/user/babar-raza/repository-presenter`, a shallow clone at 494a8e0). No push, PR, dispatch or
upstream write. Sources read: `docs/RULINGS.md`, `AGENTS.md`, `plans/idea.md`, `docs/CONSOLIDATED_GOALS_2026-11-06.md`,
`migration/reuse-manifest.yaml`, `docs/MISSION_AUTHORITY.md`, `project/backlog.yaml`, `.github/workflows/*`, `src/`,
`docs/DECISION_LOG.md` (2026-10-24, 2026-11-04), `docs/LEGACY_WRITER_INVENTORY_2026-11-04.md`, and the companion
investigation `2026-11-22-github-app-delivery-and-issues.md` (delivery and issues in detail: not repeated here).

Evidence limits: hosted run ids below were read with `gh run list/view` on this repository on 2026-11-22. The old
project's own run history and the TeX Python / 3D TypeScript issue trackers are not readable from this session (proxy
refuses them), so "worked before" for the old project rests on the decision log, the 2026-11-04 legacy inventory and
the old repository's files, not on fresh run ids. Effort is S (under a day), M (1 to 3 days), L (more) for a worker who
ports from the old project; "worked before" means the old code ran in production, not that the port was ever run here.

## 1. Inventory (idea.md and consolidated goals, beyond Lane R regeneration)

State key: LIVE = running on Actions on a schedule or chain with a successful run; PARTIAL = runs but narrower than the
goal; CODE-ONLY = library and tests exist, no workflow or caller; MISSING = not in this repository.

| # | Component (source in idea.md / goals) | Old project origin | State in this repo (code, tests) | Hosted evidence (workflow, successful run) | Missing | Effort |
|---|---|---|---|---|---|---|
| C1 | Planner, cohort chain, run-request engine (goals s7, R37) | old `sealing-scheduled.yml` (planning), foss-mcp ops | `scripts/select_scheduled_cohort.py`, `scheduled_execution_gate.py`, `run_request.py`, `present.yml` cohort job; `tests/test_cohort_chain.py`, `test_scheduled_cohort_selection.py` | present (schedule) 44966567041, cohort-chain 44985829460, run-request-execute 44985259952 (validate + present/facts success) | scheduled fires are planning-only (other jobs skipped); BL-077 chain depends on run-request pushes; BL-032 unattended sealing run | S |
| C2 | Lane R present (regenerate) | old readme composition and cascade (REUSE/ADAPT) | `readme/` (58k lines), `cascade.py`, `present.py` | run-request-execute 44974988531 (facts + present success) | 85 percent bar (30 of 40 sealed, 75 percent) | out of scope here (Lane R workers) |
| C3 | Lane L present (live README maintenance), R5 trigger | old `readme_correction/` (9k lines, partial ADAPT) | `lane_l.py`, `lane_l_run.py`, `lane_l_review.py`, `readme/correction/`; **`lane_l_trigger.py` has no production caller** (BL-188); `tests/test_lane_l_*.py` | same present chain runs Lane L step (`present.yml` line 482); 34 of 34 seals recertify (checkpoint 2026-11-20) | R5 trigger wiring; 6 to 8 cells with neither seal nor terminal record (BL-025, BL-724 owns the per-repo table); stale no-action not re-evaluated (BL-187/190) | M |
| C4 | Change detection and freshness: discovery of new repos, drift vs sealed bundle, 30-day registry recheck (idea.md "monitors every admitted repository", goals s4, s9) | old `components/monitor/` (2,025 lines, in production `monitor.yml`) | `monitor/{discovery,drift,freshness,org_listing,relevance}.py` PORTED (1,769 lines) with 7 test files; manifest: "no entry point, no workflow calls them"; `install_state.py` and the drift contract not ported | none (no `monitor.yml`); old `monitor.yml` cron every 6 h (read-only) | a workflow plus CLI that runs `observe_drift`, `observe_registry_gaps`, freshness; feeds the cohort selector and the Lane L trigger; new-repo intake report | M |
| C5 | Knowledge extraction / facts (7 ecosystems, example verification) | old `extractors/` and `evidence/facts` (SUPERSEDED_BY_INVESTIGATION, then ported) | `extractors/` (60 files, 21.9k lines), net/java execution-backed example verifiers | present/facts job success in 44985259952 and 44974988531 | PHP extractor for Cells PHP (R29, sanctioned exception); stale example receipts (BL-131) | M (PHP only) |
| C6 | Registry, portfolio inventory, exclusions | old `core/registry/` (REUSE/ADAPT) | `data/registry.json` (40 active + exclusions), `registry_observations.json`, `registry_exclusions.json` | recertify 44985165233 (reads the registry) | automatic discovery of new repositories is C4 | in C4 |
| C7 | Recertify gate (R10, R41) | new design | `recertify.py`, `.github/workflows/recertify.yml`, `tests/test_recertify*.py` | recertify (push) 44985165233, 44977826904 | none material | done |
| C8 | Independent acceptance: M9 audit chain (seed, audit, score, acceptance write) | old reviewer plus new M9 design | `acceptance/` (3.9k lines), `scripts/run_m9_*.py`, `audit-seed.yml`, `audit-score.yml`, `acceptance-write.yml` | audit-seed 44967674204 (schedule, gate/seed/audit/write/score all success); acceptance-write 43252306864 | audit false-flag gate not passing (round 6; BL-700); independent acceptance 1 of 40 | L (owned by audit workers) |
| C9 | Supervisor tick, state machine, taskcards, leases (goals s8, R8, R44) | foss-mcp ops (ADAPT) | `ops/gatecli.py`, `gatectl.py`, `gateverify.py`, `project/state.yaml`, `backlog.yaml`, `supervisor-tick.yml` | supervisor-tick (hourly) 44961494269, success | tick observes and reports only; the execution bridge (TC-032, plan 8.4) was never built (BL-027); old `liveness.yml` dead-man not ported | M (bridge), S (liveness) |
| C10 | Reporting: delivery count, budget status, failure Pareto, trust scorecard (goals s3, s13) | new | `ops/checks/portfolio_delivery_count.py`, `core/llm/budget.py`, `failures.py`, `ops/checks/backlog_check.py` | supervisor-tick 44961494269 prints Delivery, Budget, Backlog, Failure classes; run-request `count` 44980313657 | Lane R trust scorecard (BL-202) | S |
| C11 | Issue management through the App (R39): discover, record, dedup, comment, close, reopen | old `components/issues/` (5,468 lines in production `issues-scheduled.yml`, 22 jobs, one approval record per defect) | `issues/` (3,149 lines; model and approval REUSED verbatim; file, close, monitor, pilot, reproduce written here); old `batch, classes, close_approval, draft, funnel, ledger, lifecycle, quality, readiness, redetect, registry_evidence, source_parse` NOT ported; `tests/issues/` (17 files) | `issues.yml` (daily) 44916351515: App token minted, 5 issues imported, decisions planned, **dry run only**, 9 cycles, 0 live | pilot is one repository (3D TypeScript), mode `dry_run`, kill switch unset; no filing job; TeX Python and every other repository invisible; detail in the companion investigation WP-3 to WP-6 | M |
| C12 | Upstream defect handoff pipeline (idea.md "Upstream Defect Reporting") | old `evidence/upstream-defects/` (52 handoffs across 22 directories) + `ops/issue_approvals/` (19 records) | `scripts/plan_pending_handoffs.py` (read-only), 7 unfiled drafts (BL-036, unverified at current revisions) | none | re-verification of the 52 old handoffs at current heads; approval-record flow; filing job (WP-4 of companion) | M |
| C13 | README PR delivery through the App: branch, draft PR, allowlist, R15 gate | old `propose.yml`, `propose-sandbox.yml`, `candidates-publish.yml`, `verify-app-installation.yml` (live PRs Cells C++ #7, Cells Java #7) | `propose/` (1,219 lines), `candidates_publish/` (612), `authorization/`, `github/client.py`, `mint-app-token.yml`; `tests/propose`, `tests/candidates_publish`; `propose_candidate` has no caller | `tc-009a-mint-proof.yml` run 42200695015 (mint only, per companion); no PR-creating run | no `propose.yml`, no sandbox proof (R17, BL-028), allowlist 9 of 40 (companion WP-1, WP-2, WP-7) | M |
| C14 | Review page and feedback loop (R47, BL-009/300) | new | `scripts/review_page/build.py` + `template.html`, `docs/REVIEW_PAGE.md` | none: the page is rebuilt and republished from a Claude session; feedback is read by a session watcher | no hosted refresh; Actions cannot publish a Claude artifact (stated in `docs/REVIEW_PAGE.md`); feedback store is the artifact `db` | M (alternative host) |
| C15 | State mirror and repository mirror | old `mirror-gitlab.yml` | `refs/repository-presenter-state/*`, `gitlab-mirror.yml`, `core/state/` (ported) | Mirror GitHub to GitLab (push) 44991140060; state refs written by recertify and issues runs | none | done |
| C16 | Repository metadata, topics, description, community files, visual assets, social preview (idea.md "Central Agent", "Visual Assets") | old `components/metadata/` (1,023 lines, never read in detail) and `readme_diagram` (1,711) | none (manifest: DEFERRED, "not planned"); At a Glance is a Mermaid block inside the README | none | everything; idea.md says deferred until the README and issue core runs, social preview is manual-UI | L (start with M read-only audit) |
| C17 | Provider budget and cost-per-seal measurement (R31, R45) | new | `core/llm/budget.py`, `data/provider_budget.json` (`enforcement: measure`) | budget status in supervisor-tick 44961494269; present reserve-cohort step | none | done |
| C18 | Docker / local-runner parity (idea.md "Execution Environments", G6) | old Dockerfile | `Dockerfile`, `ops` | none proven (BL-048) | cold-runner zero-call proof (BL-047), container facts stage | S-M |

## 2. What the table says

- **LIVE and healthy:** C1, C2 (target not met), C7, C9 (observer), C10, C15, C17. A scheduled present fire is planning
  only; real work arrives through run requests and the cohort chain.
- **PARTIAL:** C3 (Lane L exists and seals, trigger not wired, 34 handled against about 40), C8 (chain runs, gate fails),
  C11 (dry-run on one repository).
- **CODE-ONLY, ported and never called:** C4 monitor, C13 propose and candidates publish. These are the two largest
  "worked before, here unused" items and are mostly workflow-and-CLI shells around code that already has tests.
- **MISSING:** C12 filing and handoff flow, C14 hosted refresh, C16 metadata, C9 execution bridge, PHP extractor.
- Reuse-manifest pattern: the manifest records `DEFERRED`/"no consumer yet" for exactly C4, C13 shells, C16, and
  `PARTIAL_PORT` for monitor. The old repository still holds the shells (`monitor.yml`, `propose.yml`,
  `propose-sandbox.yml`, `candidates-publish.yml`, `issues-scheduled.yml`, `liveness.yml`, `sealing-scheduled.yml`) and the
  unported issue modules, so porting is adaptation, not design.

## 3. Ranking

Value is scored against the goals (R44 targets, R49 components, R50 owner asks), effort from section 1.

| Rank | Gap | Value | Effort | Why this position |
|---|---|---|---|---|
| 1 | G-A Issues live and generalised (C11, C12): TeX Python pilot, 3D TypeScript live, filing job | high: owner named it, R39, R49 | M | mechanics exist and ran nine hosted cycles; flips are config plus two small jobs |
| 2 | G-B Delivery workflow and sandbox proof (C13) | high: R50(2), R49 | M | code ported with tests; needs `propose.yml`, a sandbox target (owner or `babar-raza/repo-presenter` per BL-028) |
| 3 | G-C Lane L reach to about 40 and the R5 trigger wired (C3) | high: R44 Lane L 100 percent, R50(4) | M | trigger module exists, BL-188; per-repo blockers are BL-724 |
| 4 | G-D Monitor workflow: drift, discovery, freshness (C4) | high: idea.md core, feeds G-C and R15 freshness (BL-187/190) | M | 1,769 ported lines with tests, no entry point |
| 5 | G-E Hosted review page and feedback intake (C14) | medium-high: R47 | M | needs a host other than the Claude artifact (Pages or a committed page) and a feedback source; platform limit |
| 6 | G-F Supervisor execution bridge and liveness (C9) | medium: R8, Final Directive | M | decision needed on the smallest bridge (BL-027) |
| 7 | G-G PHP extractor (C5) | medium: R29, one cell | M | sanctioned exception, existing plugin pattern |
| 8 | G-H Metadata / visual assets audit (C16) | medium-low: idea.md says after the core | M read-only, L apply | deferred by the owner's own sequencing |
| 9 | G-I Docker parity, cold-runner proof (C18) | low-medium | S-M | BL-047, BL-048 |

Not in this list because other workers own them: Lane R seal rate, M9 audit gate (C8), Lane L per-repo table (BL-724),
delivery and issue detail (companion document).

## 4. Parallel work plan (all packages start at once; none waits for another unless stated)

Each package is one worker, one branch, a PR to `main` by the supervisor, evidence recorded as a hosted run id.

| WP | Work | Files touched (conflict surface) | Acceptance | Evidence |
|---|---|---|---|---|
| WP-1 Issues live and TeX | Companion WP-3, WP-5, WP-6, WP-4: pilot `live` on 3D TypeScript with the kill switch, TeX Python added in `dry_run` with an `ast.parse` reproduction, filing job gated by approval records | `data/issue_pilot.json`, `data/issue_reproductions/`, `issues.yml`, `issues/` | one App comment posted; TeX cycle reports VERIFIED_RESOLVED at 07db3203 (dry run); no filing without approval | issues.yml run ids, state ref cycle |
| WP-2 Delivery | Companion WP-1, WP-2: `propose.yml` + `propose-sandbox.yml` adapted from the old files, sandbox draft PR by `repository-presenter[bot]`, duplicate refusal | new workflows, `propose/`, registry sandbox entry | draft PR on sandbox from a hosted run; second run refuses duplicate; no upstream repository touched (R15, R17) | run ids, PR url |
| WP-3 Monitor | Add `monitor.yml` (schedule every 6 h, read-only) and a CLI entry that runs drift, discovery, freshness over the registry and writes the report to a state ref and the job summary; wire the result into `select_scheduled_cohort.py` so drift outranks "recertified, skip" (BL-187/190) | new `monitor.yml`, `monitor/__init__`/CLI, `scripts/select_scheduled_cohort.py` | scheduled run succeeds; report lists per-repo change class (relevant, irrelevant, unreadable), unregistered org repositories and 30-day rechecks; cohort selector takes drift as input; offline tests with relevant/irrelevant/unreadable controls | monitor run id, test output |
| WP-4 Lane L trigger | Wire `lane_l_trigger.compute_trigger/classify_outcome` into the production Lane L step; irrelevant change does no provider call; unknown fails closed; `NO_ACTION_JUSTIFIED` requires clean probes (BL-188) | `present.py`, `lane_l_run.py`, `lane_l_trigger.py`; touches `present.yml` lightly | negative controls pass; hosted Lane L run records a trigger decision | run id, tests |
| WP-5 Lane L reach | BL-724/025: terminal outcome or named blocker for every active repository lacking a Lane L seal | `data/terminal_cells.json`, run requests | per-repo table; count within a little of Lane R | official count run |
| WP-6 Hosted review page | Build the page in a workflow (reuse `scripts/review_page/build.py`), publish to a stable host (Pages or a committed `docs/` page on a mirror branch), add a feedback intake that a scheduled job reads (issue label or file) and turns into backlog items | `scripts/review_page/`, new workflow | page rebuilt by Actions after each recertify; one test feedback entry becomes a backlog item without a session | run id, URL |
| WP-7 Supervisor bridge | Decide and build the smallest execution bridge: scheduled tick reads the next eligible backlog item and writes a run request or lease (BL-027); port `liveness.yml` dead-man | `supervisor-tick.yml`, `ops/gatecli.py` | plan 8.4 proof: lease, work, verify, next lease from durable state; liveness alert on a stale tick | run ids |
| WP-8 PHP extractor | `extractors/platforms/php.py` in the existing plugin pattern (R29), Cells PHP activated | `extractors/platforms/`, registry entry | facts job succeeds for Cells PHP; tests | run id |
| WP-9 Metadata audit | Read-only: port `capture`/`proposal` observation half of old `components/metadata/` to report topics, description, community files, license, security file per repository; no write | new `metadata/` package, report | report for all 40 repositories on a state ref | run id |
| WP-10 Parity and cold runner | BL-047 zero-call cold-runner proof; BL-048 Docker facts stage | `Dockerfile`, `ops` | proof runs | run ids |

Cross-package touch points to sequence by the supervisor at merge time only: WP-1 and WP-2 both edit `data/` and the
registry (merge order: WP-2 registry sandbox entry first); WP-3 and WP-4 both feed the cohort selector (WP-3 merges first,
WP-4 rebases); WP-5 edits `data/terminal_cells.json` only through run requests.

## 5. Conflicts with R27 (architecture freeze) and other rules

- R50(1) says every `plans/idea.md` component is in scope and R27 "does not stop reusing a component that worked in the
  previous project". WP-2, WP-3, WP-9 add workflows and WP-1 adds a record flow: all are reuse of old components through
  `migration/reuse-manifest.yaml`, and each needs its manifest entry updated in the same commit (the manifest is a
  ledger: "a module enters when a taskcard pulls it"). WP-6 and WP-7 are new mechanisms (a hosted page host, an execution
  bridge): R27 still applies to them unless the supervisor records them under R50 or R37, so they are the two packages
  to record explicitly. WP-8 is the R29 exception already.
- R22 (issue filing off on every upstream repository) and R7 versus R50(3) "all issues logged and managed": R39 amended
  R22 for the pilot only and `data/issue_pilot.json` says widening is the owner's call. R50 reads as that call, but the
  file text is explicit, so WP-1 should record the owner's R50 wording as the authority before widening beyond the pilot
  plus TeX Python (R12: report the conflict first).
- R15 and R17: no upstream push before both lanes pass; WP-2 must stay on a sandbox. Today's deadline (R49) can be met
  for workflows and dry runs, not for live upstream PRs.
- R45/R31: none of these packages spends provider budget except WP-4 hosted proofs; measure, do not block.
- Disk: this session saw the shared disk fall to 1.2 GB free while the investigation ran (another process). Workers
  should not clone the old repository again; read it at `/home/user/babar-raza/repository-presenter`.

## 6. Today (R49) realistic status per component

Demonstrable on Actions today with a successful run: C1, C2 (partially), C7, C8 (chain runs), C9, C10, C15, C17, C11
(dry run). Achievable today by flags and small adaptations: C11 live pilot (owner variable plus a mode flip), C4 monitor
workflow (shell around ported code), C13 dry-run propose workflow. Not achievable today without owner action: live PRs
(R15, sandbox), C16, C14 hosted publication target, C3 reaching about 40.
