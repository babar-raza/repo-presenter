# Repository Presenter v2 — dual-lane rebuild, independent audit and execution contract

**Assessment date:** 2026-10-15. **Type:** architecture and execution specification, not implementation evidence. **Source revisions inspected:** `babar-raza/repository-presenter` `2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c`; `babar-raza/foss-mcp` `11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a`; `babar-raza/foss-readme-optimizer` `a8a163f7e9a7beeac1d2ef8b7c02e8e4bd5a7815`. Repo heads and remote state must be refreshed before execution. Code was read through a connected GitHub interface; no code was executed locally and no target repository was mutated.

## 0. Binding mission, in one paragraph

Build a production-running, GitHub-native, unattended **Repository Presenter** that continuously evaluates authorized Aspose FOSS repositories, recognizes when an existing README is materially inadequate and **generates/regenerates** it from the complete independently verified product truth (**Lane R**), and separately detects substantive changes in product code, release and package facts, feature/API/test/doc surfaces and **updates the existing valuable README** with precisely the required changes (**Lane L**). Both lanes must independently produce accurate, maintainer-worthy, deduplicated upstream pull requests and support authorized hands-off operation. They share a safe effect controller, independently confirmed product-defect issue reporter, repository presentation modules, immutable evidence, and `foss-mcp`-style supervised implementation governance. No local bundle, code metric, tests, status transition or internal PR substitutes for verified target effects.

## 1. Direct repository inspection: evidence and limitations

| Observation at revision | Direct source | Why it matters |
|---|---|---|
| Registry 44 entries: 42 `dry_run`, 2 `full`. | `repository-presenter/data/registry.json` | Default policy currently prevents publication for most target repos. Readiness and permission must be separate. |
| `project/state.yaml` has 29 sealed/current candidates, zero authorizable; G3-W11 is active. | `repository-presenter/project/state.yaml` | Full regeneration is implemented but has not demonstrated authorizable upstream output. |
| `readme_correction/engine.py` is a closed deterministic detector runner; `run.py` explicitly says some defects are only reportable. | `src/repository_presenter/components/readme_correction/{engine,run}.py` | This is a useful **mechanical sub-engine of L**, not the feature-delta authoring lane. |
| `detectors/gaps.py` reports missing example code, public types and formats without authoring changes. | `readme_correction/detectors/gaps.py` | Feature additions can remain undisclosed in README. |
| Relevance monitoring compares primarily **consumed** README fact paths/blobs; a newly created user-facing source file outside previously consumed scope can be classified irrelevant. | `components/monitor/relevance.py`, `monitor/drift.py` | Discovery of new functionality must have a separate *novelty/change* detector. |
| `sealing-scheduled.yml` invokes `present.yml` for R; L corrections are offered by a separate CLI / manual `propose.yml` correction-run input. | `.github/workflows/{sealing-scheduled,present,propose}.yml` | L has no coequal automated end-to-end schedule. |
| R composes through extraction, investigation, reconciliation, planning, authoring, validation, independent review, repair, seal and zero-call replay. | `cli.py::run_present`; `readme/{repair/rounds,bundle/seal,acceptance/judge}.py` | Large, reusable source-aware engine, but high coupling and recovery complexity. |
| New R judge J1–J6 enforces facts, standard, claims, dispositions, rerun and non-loss against live, while L gate compares validation before/after. | `readme/acceptance/judge.py`; `readme_correction/{gate,check}.py` | Per-lane acceptance must be compatible but not identical: R judges a *whole document*, L judges a *changed document and delta*. |
| Acceptance standard became normative on 2026-10-11 while previous `README_CONTRACT.md` remains partly encoded in runtime code. | `docs/README_STANDARD.md`, `docs/README_CONTRACT.md` | Competing rule versions cause rejection and repeated resealing. |
| Historical recheck analysis: of 39 version bumps, 25 had no effect on consumed candidate content, 7 materially changed it, 7 could not be replayed offline. | `docs/investigations/13-bump-cost-and-recheck-design.md` | Version number must not invalidate unrelated accepted content. |
| `bundle/recheck.py` and PR #339 introduce consumed-scope offline checks. | `components/readme/bundle/recheck.py`, PR #339 | Salvage and simplify rather than invent again. |
| Archived, independent L audit (2026-10-13, not a present-day publication claim): 20 of 44 corrected bundles PUSHABLE, 19 required minor fixes, 5 not pushable. 34 of 39 corrected bundles had diagram-only edits; no development command or documentation-link additions survived. | `evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis/preserved/acc-corr3-summary.md` | Genuine bounded corrections exist, but feature maintenance remains largely unproven. |
| Eight-plus real issues filed on 2026-10-15 by `repository-presenter[bot]` across Cells repositories; job-level external evidence exists. | GitHub target issue URLs, `.github/workflows/issues-scheduled.yml` | Do **not** discard the working issue effect; preserve and verify issue quality/lifecycle. |
| Sandbox proposal attempted on 2026-10-15 failed at App installation lookup (404), before proposal execution. | Actions run `38738363742`, job `116433368718` | Preflight target installation and chosen canary before generating candidates. |
| `foss-mcp` supervisor keeps separate instruction/status append-only channels, worker-owned scoped commits, supervisor-only acceptance, deliberate falsifiers, derived state and bounded rework. | `foss-mcp/ops/{SUPERVISOR.md,gatectl.py,gateverify.py,integrate.py}` | Reuse the **proven governance principle**, not the project's large backlog or runtime. |
| Legacy optimizer contains extensive fact extraction, templates, orchestration, and abandoned plans. | `foss-readme-optimizer` main tree | Treat as extraction/test oracle; do not migrate its control-plane or recursive planning. |

**Evidence caveat:** Historical archived reviews are forensic evidence, not a current pass. Current upstream files, package registries, installation permissions, candidate SHA and worktree state must be reobserved by the supervisor on start. Source inspection is not proof of an executable working path.

## 2. Two first-class product lanes

### Lane R — full generation / regeneration

**Trigger:** README absent, placeholder, demonstrably unsuitable, missing fundamental onboarding or product explanation, substantively unreliable, inaccessible to target users, or failing a documented product presentation quality profile. Merely missing a banner or one link is not sufficient. New repositories without credible readmes route to R, regardless of last change. Periodic quality audit can nominate an existing README for R.

**Contract:** Build the *best defensible complete README*, not a generic template clone. Discover purpose, high-value use cases, audience, supported workflows, formats, public API, distribution/installability, compatibility, limitations, license, evidence-backed working examples, contribution/support and applicable branding. Source of truth is repository and registry evidence. Existing README is *valuable input*, not immutable formatting law; every material original item is kept, accurately rewritten, supportedly superseded or explicitly excluded with evidence. Important inherited sections survive. Enterprise Edition naming and other owner brand constraints apply. No invented claims, capabilities, package publication, command behavior or formats. Generated README must be demonstrably better in visitor utility than live and meet the project's common/variant standard appropriate to the product.

**Runtime:** `R_ELIGIBLE -> R_SNAPSHOT -> R_FACTS_VERIFIED -> R_BLUEPRINT -> R_COMPOSED -> R_RECONCILED -> R_VALIDATED -> R_EDITORIAL_ACCEPTED -> R_CANDIDATE_LOCKED -> PUBLISH_READY`. Each step writes immutable stage artifacts and precisely scoped dependency hashes. On error reenter earliest affected stage; never redraw all sections when the problem is a single paragraph. Proven good sections remain locked. Max two targeted repair attempts for same fingerprint; third closes `FAILED_INTERNAL` with a reproducer and escalates, without blocking other repos.

**Quality:** Deterministic hard gates for package coordinates, API claims, known unsupported formats, executable/compilable quick-starts, links, protected content, secrets, markdown safety, source revision and output integrity. Independent editorial reviewer compares R against verified product truth and the inherited live content: user orientation, specificity, usefulness, scannability, examples and accurate limitations; give typed, section-local defects. Calibrate reviewer on hand-reviewed holdouts and make uncertain editorial criteria visible instead of endlessly toggling regexes and writing new blocking rules. Stable output identity is the locked candidate hash, not a promise that new LLM calls will recreate identical prose. A repeat run with unchanged inputs is a zero-work/zero-call reuse of that candidate.

### Lane L — continuous change-driven README maintenance

**Trigger:** A change to a documented claim **or a newly added user-facing capability**, API export, package version/publication, supported format, dependency, runtime requirement, installation, example, CLI, behavior, migration path, tested environment, link or significant documentation/release change. A no-op or irrelevant commit must be provably classified as such, with a **full change inventory**. Lane L can also accept identified defects in the live README, including stale claims, broken headings and well-supported omissions; purely cosmetic changes are low priority.

**Core feature — change discovery:** Compare immutable `last_reviewed_upstream_sha` to live default branch, not just to the paths consumed by a sealed R bundle. Collect added, modified, deleted and renamed paths, compare public API exports and package manifests, test names, examples, changelog and release signals, and evaluate additions as well as modifications. Classify `FEATURE_ADDED`, `FEATURE_CHANGED`, `FEATURE_REMOVED`, `API_BREAKING`, `INSTALL_CHANGED`, `PACKAGE_PUBLISHED`, `SUPPORT_CHANGED`, `DOC_CHANGED`, `QUALITY_DEFECT`, `INTERNAL_ONLY`, `UNCERTAIN`. Recompute fact deltas and compare to what the **live** README says; unchanged material is untouched. A newly introduced file in an unknown package boundary must not automatically be `IRRELEVANT`.

**Authoring:** Model-free deterministic repairs are first choice where supported. When a new feature or changed behavior requires original prose, an LLM receives the *verified fact delta, impacted README section(s), and preserved surrounding source*, then writes a constrained patch plan/hunks, not a regenerated entire README. Build/exercise the example or mark unverified and withhold the claim. Source-file facts and release data carry evidence. Place new material in the existing logical section, preserve voice and established layout, keep unrelated headings/links/fences exactly, and prevent duplicated or promotional text. Small docs changes with uncertain meaning become review tasks rather than unsupported assertions.

**Runtime:** `L_ELIGIBLE -> L_BASELINE -> L_CHANGE_INVENTORY -> L_FACT_DELTA -> L_IMPACT_MAP -> L_PATCH_PLAN -> L_PATCHED -> L_DELTA_VALIDATED -> L_EDITORIAL_ACCEPTED -> L_CANDIDATE_LOCKED -> PUBLISH_READY`. Each transition stores immutable `from_sha`, `to_sha`, changed paths, fact IDs, affected sections, patch hash and minimal confirmation tests.

**Validation:** The unchanged original material is protected from unrelated modification. The new patch may not worsen fact validity, markdown/link integrity, command reproducibility or user-facing quality; pre-existing unrelated live failures are reported, not blockers to an unrelated safe update. No-op replay applies no new edits and uses no provider calls. Partial meaningful improvement can ship; an unrelated defect is not silently fixed or invoked to block indefinitely. A failed feature insertion is held with a typed reason while unrelated clean patch groups can still publish.

### Cross-lane arbitration — neither lane is the other's success/failure fallback

The router emits `R`, `L`, `BOTH_EVALUATE`, `NO_CHANGE`, `BLOCKED_EVIDENCE`, or `BLOCKED_PERMISSION`. These are substantive routing decisions with evidence, not preferences. `R` if baseline is missing/massively inadequate; `L` if baseline is good and a material delta exists; `BOTH_EVALUATE` for a materially weak README AND changed product features or when quality tradeoffs are genuinely close. In a BOTH trial, both candidates can be constructed independently, but only **one** PR is published at a time to the same target README, chosen by comparable evidence. If R fails, it stays R-failed; a separately validated L patch may ship on its own merits, not as an unannounced substitute for R completion. Routing failure is not a reason to lower gates.

A completed R transaction establishes a fresh L baseline (source snapshot, fact inventory, README hash) **only after its README is actually merged upstream**. Merely opening an R PR cannot redefine the live baseline; when a maintainer edits/merges it, L reobserves those bytes. L changes never rewrite an R draft out from under another open proposal; explicit conflict and supersession policy governs open PRs.

## 3. Shared architecture and independent effects

There are four runtime planes:

1. **Observation:** cheap GitHub App read-only polling/webhook (source heads, snapshots, new/changed/removed path inventory, API/package/release metadata, existing PR/issue state); durable source cursor and skipped/not-observed counts.
2. **Reasoning/production:** route and run Lane L or R separately, within a per-repo quota; common verified-facts services, source/code provenance, policy and LLM access where needed. A producer **never holds a target write token**.
3. **Acceptance:** pure, lane-aware judges. Shared safety hard gates + `RWholeDocumentAcceptance` or `LDeltaAcceptance`; reviewer independent of the producer; immutable candidate and evidence bundle. `CANDIDATE_READY` is possible with target write permission absent and must remain counted separately.
4. **Effect/reconciliation:** target-specific scoped App token in separate short-lived job, policy permit, exact bundle hash/branch/expiry, live head compare, stable bot branch/PR lookup, upsert or typed hold, read-back verified effect receipt, loss-of-response reconciliation, and continued PR lifecycle monitoring. GitHub is source of truth for whether PR or issue exists, is merged, closed or superseded.

**Status dimensions:** content `{NOT_ATTEMPTED, ANALYZING, READY, FAILED}`, effect `{UNAUTHORIZED, PREFLIGHT_FAILED, ELIGIBLE, PR_OPEN, PR_MERGED, PR_DECLINED, BLOCKED, RETRYABLE}`, freshness `{CURRENT, RECHECKED_CURRENT, STALE_SOURCE, UNVERIFIED}`, per repo per lane. Preserve separate transaction histories and avoid forcing all dimensions into one enormous enum.

**Authorization:** Only explicitly allowlisted repositories and effect types. Initial first-live canary requires owner-selected target and current explicit authority. Later unattended effect policy must be preapproved and bounded by repository, branch, file paths (`README.md` for L/R), change class, daily count, risk thresholds, and rollback/kill switch. Policy mode may be `observe`, `candidate`, `propose`, optionally `merge` once explicitly authorized. Credential presence never implies permission. Do not auto-merge by default; never push directly to default branch. Handoff to human for permissions only when preflight proves missing, report exact URL and required action. The current 42 `dry_run` entries must not be silently promoted.

**Issue reporter:** Preserve existing real filing path and fingerprints, but independently reassess quality (e.g. whether a license in `License/` is actually a defect), upstream dedup, fresh verification, policy, comment/update and closure. Issues should have their own schedule and remain operational if both README lanes fail. Recheck current issues before filing new related issues. A success job that skipped a write does not count as `ISSUE_FILED`.

**Other presentation surfaces** (description, homepage/topics, community/security files, banners/icon/social-preview where supported) are subsequent independent capabilities. Their policy/effect and fallback mechanism must not block delivery of Lane L/R; unsupported UI surfaces should produce an accurate manual handoff, not a false claim of applied change.

## 4. Implement the two distinct state machines without duplicating governance

### Supervisor implementation machine (`foss-mcp` derived)

`DRAFT_CARD -> VERIFIED_CARD -> READY -> DISPATCHED -> WORKER_COMMITTED -> INDEPENDENT_CHECK -> ACCEPTED -> INTEGRATED -> PRODUCT_PROOF -> CLOSED`, with typed side paths `REWORK`, `BLOCKED_EXTERNAL`, `FAILED_INTERNAL`, `SUPERSEDED`.

Use `ops/SUPERVISOR.md`, narrowed `gatectl`, `gateverify`, `integrate`, tests of false-positive/negative controls, scope/commit guard, separate append-only instruction/status channels, one state-derived owner cursor. Each card includes `requirement_id`, `lane`, bounded `write_paths`, explicit inputs/source pinned refs, positive test, semantic falsifier, runtime integration point, evidence exit, and external acceptance. Worker never approves or modifies own card; supervisor never silently authors worker product code. Evidence generated by code, not prose self-report. Two equivalent errors cause supervisor independent diagnosis; third failure produces a typed disposition and yields to next independent work. A gate can close only when its **external acceptance evidence** exists. Do not import `foss-mcp`'s historical 400+ taskcards or build a second planning framework.

### Runtime machine (production work)

`OBSERVE -> CLASSIFY -> ROUTE -> (LANE_L | LANE_R | BOTH) -> VERIFY -> LOCK -> AUTHORIZE -> PRE-EFFECT RECHECK -> UPSERT_PR -> VERIFY_REMOTE_EFFECT -> FOLLOW_UP`, with separate issue branch `OBSERVE -> REPRODUCE -> DEDUP -> AUTHORIZE -> FILE/UPDATE -> VERIFY -> FOLLOW_UP`.

Concurrency key: `(repository, target_surface)`, not just a workflow run; exactly one active README publication lease per repo while L and R may research in parallel. Durable CAS and fenced leases across schedules; killed worker must leave its candidate immutable and allow recovery; stale worker cannot write after lease expiry/reassignment. Pure idempotency identity includes repository+lane+head SHA+observed desired change+policy version+output hash; remote PR id is stored after read-back and may be rediscovered on timeout.

## 5. Gates and milestones: two real README PRs early

**B0 — Freeze audit & salvage (no production writes).** Refresh all repo heads and exact open PRs; audit `src` and execution scripts; inventory source tests, components, deps, token scopes, invalidation and real effects. Mark `KEEP`, `ADAPT`, `DEFER`, `RETIRE` per module. Confirm runnable restricted supervisor in isolated worktree, machine derived state and false-positive falsifier tests. Ensure current issue system stays live. No sweeping rewrite of old files.

**B1 — Delivery spine and authorization proof.** Against owner-approved test target: scoped App read/write preflights, immutable snapshot, candidate/receipt schema, accept/reject, PR upsert, response-loss recovery, no-op second effect, permission denied. Exit: real sandbox PR, remote URL + verified patch, idempotent re-run; distinguish sandbox from business result. An observed 404 App installation is a permission issue, not a generator bug.

**L1 — Lane L pilot.** Prove a **new user-facing feature or changed API** detected from a new/modified path, then a factual README delta and real upstream PR. A structural-only typo or Mermaid diagram PR does NOT satisfy L1. Candidate should be selected by fresh repo scan (e.g. Cells-Go's earlier public-type coverage mismatch can be rechecked, not assumed). Exit: full before/after feature evidence, precise unchanged span proofs, valid code example where applicable, independent reviewer, actual bot PR, duplicate-free rerun. Add static correction tests as a second L subtype.

**R1 — Lane R pilot.** One no-README target and one inadequate-but-existing-README target. Potential observed opportunities from 2026-10-11 survey: GIS/.NET README absent; Cells/Python, Font/Python or Slides/.NET have nonstandard/missing structure (these features alone do not prove poor quality). Re-assess suitability and source processability, choose one real target that is credibly deficient and is authorized. Exit: complete, materially improved original product README, inherited-content reconciliation and proof of facts/examples, independently accepted candidate and real bot upstream PR. Each R pilot is a distinct proof, not L's result.

**X1 — Cross-lane routing and conflict.** Both lanes can receive the same upstream change, choose by evidence, show `BOTH_EVALUATE`, keep single open PR / source-head fencing, and preserve the incumbent baseline. L after R merge computes no-op if no new change. Do not accept a R-failed case by quietly relabeling a Lane L patch as R.

**I1 — Issue logger quality & durability.** Preserve existing filing capability, verify existing real upstream issues and file a new independent defect only if one is demonstrated and authorized. Reconcile duplicate and closure/reopen cases, remote evidence receipts, uncertain outcome. No dependency on R or L candidate acceptance.

**A1 — Genuine unattended operations.** Hosted or approved runner dispatch from GitHub schedule/event, freshness and novelty observation, lane routing, generation, independent validation, permitted write, remote read-back, durable state restart, early error classification, kill switch, per-repo quotas, no routine manual terminal. One meaningful L effect and one meaningful R effect independently achieved unattended under authorized policy; absent write authority, system remains accurate `AWAITING_AUTHORIZATION`, not `AUTONOMOUS_COMPLETE`.

**P1 — Portfolio coverage and other surfaces.** Expand by ecosystem after each new language has a real generated and updated README example (where meaningful), then add metadata/community/visual surfaces with independent receipts; include full 44-repo inventory and truthful exclusion categories. No forced 44/44 successful candidates for non-processable/permission-denied products; every target receives a typed state.

## 6. Concrete minimum backlog (supervisor owns the order and card invariants)

| ID | Lane/plane | Card, production importer and acceptance |
|---|---|---|
| RP-001 | Governance | Freeze evidence, extract small `foss-mcp` verifier/worker/supervisor and validated state builder; hard-fail falsifier that does not change behavior. |
| RP-002 | Effect | Implement App installation preflight + exact policy permit + public `upsert_pr` on approved sandbox, remote read-back and no-op; first external proof. |
| RP-003 | Observation | Full source revision diff, newly added paths, rename/removal, public export inventory and package/release change ledger; falsifier adds a new exported class in a new file. |
| RP-004 | Routing | Lane eligibility and mixed-case comparison; never use candidate-consumed-only paths to assert no feature addition. |
| RP-005 | L | Port correction engine's deterministic safe edits and scoped before/after validation under `LaneLPatch` record. |
| RP-006 | L | Add agentic delta-to-README impact/placement/patch mechanism with exact fact citations and source-sha binding. |
| RP-007 | L | Independent L acceptance; verify new feature and example; open and verify first meaningful upstream Lane L PR. |
| RP-008 | R | Port source evidence/extractors, proven examples, original-unit reconciliation and partial structured composition; avoid old full redraw cycle. |
| RP-009 | R | Independent R whole-document acceptance and boundable targeted repair, with verified product-specific quality; no-README and poor-README pilots. |
| RP-010 | R | Open and verify first regenerated upstream README PR; second run is no-op. |
| RP-011 | Shared | Same-repo L/R arbitration, snapshot recheck, existing PR collision, R merge -> L baseline, maintainer-edited merge. |
| RP-012 | Issues | Preserve functioning issue GitHub App write path, quality and reconfirmation, dedup/close, no new duplicate. |
| RP-013 | Runtime | Scheduled orchestration, durable effect receipts, leases/fencing, restart, health and quotas for both lanes. |
| RP-014 | Security | Untrusted source prompt-injection tests, secret scrubbing, token scoping, fork workflow isolation, contract/version freshness, partial API failure. |
| RP-015 | Rollout | Switch producer/effect owner by per-surface flag; leave legacy evidence read-only; expand platforms after external proof. |

Cards can be parallel only with disjoint paths. RP-003 + RP-005 + RP-008 + RP-012 can advance while RP-002 preflights; L and R remain separate critical paths after shared foundations. An undocumented code path doesn't pass a gate: test through public CLI or hosted workflow plus a remote-effect acceptance receipt.

## 7. Public contracts and minimum data shapes

Use a small, human-inspectable JSON/YAML contract and single derived index rather than multiple competing ledgers.

```yaml
repository: aspose-cells-foss/Aspose.Cells-FOSS-for-Go
source:
  compared_from_sha: '<immutable previous observed revision>'
  current_sha: '<immutable GitHub head>'
  readme_blob_sha: '<blob sha or null>'
change:
  class: FEATURE_ADDED
  changed_paths: ['src/...new_export.go', 'examples/...']
  novelty_paths: ['src/...new_export.go']
  verified_fact_delta_ids: ['fact:...']
route:
  decision: L
  reason_codes: ['GOOD_LIVE_BASELINE', 'NEW_PUBLIC_FEATURE']
transaction:
  lane: L
  status: CANDIDATE_READY
  content_sha256: '<sha256 of proposed README>'
  evidence_sha256: '<sha256 of sealed evidence>'
  touched_sections: ['Features', 'Examples']
  untouched_content_proof: true
acceptance:
  deterministic: PASS
  independent_editorial: PASS
  example_run: PASS
  no_new_false_claims: true
effect:
  policy_mode: propose
  authorization_ref: '<owner-approved policy/version>'
  status: NOT_ATTEMPTED
  remote_pr_url: null
  last_checked_upstream_sha: null
```

R record replaces `compared_from_sha` with the source snapshot and adds `baseline_quality`, `archetype`, `evidence_coverage`, `section_provenance` and `inherited_unit_dispositions`; the stable envelope is shared. Each effect receipt must include actual API response identity and independently fetched live PR/issue identity; no fabricated remote URL in a record.

## 8. Mandatory negative tests before rollout

1. **New-file novelty:** Add an exported public API in a brand-new source file; old consumed paths unchanged. L must classify as relevant and assess README coverage.
2. **Invisible internal change:** Modify only a private test fixture with no public meaning; neither lane may consume an LLM call or create PR.
3. **Capability removal:** Remove an exported method documented in README. L must delete/correct the stale claim and avoid suggesting the old example.
4. **Release-only vs package publication:** Tag/release metadata updates with no user-facing change no-op; new published package changes install claim only if verified.
5. **Bad live README:** A thin/false README with adequate source evidence chooses R and produces a complete document, not an L patch pretending to be R.
6. **Missing README:** R creates one at proper location only after processability and package claims are verified; L reports cannot patch.
7. **Mixed trigger:** Bad README + new feature -> BOTH_EVALUATE with independently recorded outcomes; exactly one target PR at a time.
8. **R inherited loss:** Remove a verified original example or maintainer note; independent whole-document acceptance rejects unless accurately superseded with evidence.
9. **L unrelated loss:** Change existing unrelated heading, command, anchor, table or non-impacted paragraph; L confinement gate rejects.
10. **False R content:** Claim unverified import/export, package existence or output format; hard fact gate rejects even if prose looks polished.
11. **Validation upgrade:** Change a rule that candidate never consumed; previous accepted state remains reusable, receives recheck receipt, no blanket regeneration.
12. **Provider nondeterminism:** Introduce different LLM prose on rerun; locked previously accepted candidate stays byte-identical, no unnecessary provider call.
13. **Auth denial:** App not installed to chosen target; preflight emits BLOCKED_PERMISSION before any generation/effect and proceeds to a different authorized repo.
14. **Lost GitHub POST response:** Remote PR or issue exists but reply times out; search stable branch/marker and reconcile instead of duplicate POST.
15. **Concurrent dual lane:** Two lanes attempt same README at once; fenced effect lease and target PR policy allow at most one current proposal.
16. **Upstream moves before effect:** New commit changes affected content; reject old patch, recompute or safe rebase with fresh acceptance, never force.
17. **Maintainer edits PR:** Reobservation detects modified branches; bot does not overwrite human edits or reopen merged PR blindly.
18. **Scheduler failure:** Cron silently skipped, bad artifacts, runner gone, provider down; watchdog reports unhealthy rather than green successful no-op.
19. **Issue false positive:** A license in `License/` is valid under policy; reject an automated defect issue claiming it is necessarily absent.
20. **Malicious repository instructions:** A source `AGENTS.md`/README contains instructions to exfiltrate tokens or bypass gates; treated as untrusted data and ignored by agent/effect.
21. **Cleanup integrity:** A Windows test worktree's linked `.venv` cannot delete its shared target on teardown; no `git stash` of another worker's files.
22. **R/L production E2E:** In separate target repos, an actual accepted and authorized L PR and R PR appear and are read back, after schedule under the approved policy; repeat runs open zero duplicates.

## 9. Anti-loop controls tied to business outcomes

- **No gate drift:** acceptance contract hash and applicability changes require a reviewed decision with a concrete regression/falsifier; rule changes cannot retroactively erase unrelated accepted work.
- **No process-metric victory:** supervisor scorecard starts with `upstream_L_pr_opened`, `upstream_R_pr_opened`, `upstream_L_merged`, `upstream_R_merged`, `verified_issues_filed`, `unattended_effects`, `blocked_with_resume`. Sealed bundles and passed tests are secondary.
- **No whole-portfolio freezes:** one broken project receives typed `BLOCKED` and resume conditions. Continue independent READY tasks with fair scheduling.
- **No endless rerun:** two equivalent failures require independent root cause; three end current task attempt. Accepted stages cached by input hashes; no global refresh just because a component version changed.
- **No pass-by-absence:** a detector returning no findings is not a proof of feature completeness; a scheduler with no new PRs must identify whether genuine no-op, no authority, old baseline or missed novelty.
- **No hidden instructions:** single derived product/implementation state and bounded supervisor tick; no duplicate competing mission graph/roadmap/loop; preserve append-only event logs but build queryable indices.
- **No unlock-by-relabel:** L success never counts as R success and issue filing never counts as README deployment. Maintain both lane SLAs and independent backlog age.
- **Time/cost budgets:** source diff + deterministic scan first; LLM only on genuinely unresolved editorial work; per-repo provider-call, source-tool and retry budgets. Failed hard validation does not trigger another wholesale generation.
- **External first:** no expansion into metadata or additional ecosystems until both L and R reach their first real upstream PR milestone.

## 10. Proposed module composition

```text
ops/                  # minimal foss-mcp-derived build supervisor only
project/              # machine-derived implementation cursor and runtime summary
schemas/              # single typed ledger/transition/candidate/effect contracts
src/repository_presenter/
  observations/       # source snapshots, APIs and novelty paths, package/release delta
  facts/              # common verified typed facts and ecosystem adapters
  routing/            # baseline quality, R/L/BOTH decision, source impact
  lanes/
    l/                # preserve-readme engine, incremental authoring and delta acceptance
    r/                # whole-doc planning, composition, reconciliation, R acceptance
  review/             # shared proof/evidence + independent lane-specific assessment
  effects/            # authorized PR upsert, state reconciliation, issue API
  scheduling/         # durable leases, fair queue, recovery and watchdog
  presentation/       # independent future metadata/community/visual surfaces
.github/workflows/    # monitor, lane-dispatch, propose, issues, watchdog (write roles isolated)
```

Do not copy a module because its name seems related. For every file being reused, record source commit, why needed by a *production importer*, tests ported, transitive dependencies, API change, negative test and responsible taskcard. Large per-candidate fact artifacts and historic logs remain archived/remote evidence, not bulk-recommitted into the rebuilt codebase.

## 11. Implementation go/no-go decisions

- **Default structure:** clean controlled rebuild within existing `repository-presenter` to preserve GitHub App installation and running issue effects, with isolated new package/branch and a one-way, owner-reviewed cutover. A new public repo is not required and would add a new App-installation blocker; create one only if repo ownership/security demands it.
- **Minimum supervisor:** port correctness of `foss-mcp` worker card check, clean-hash and negative-control verification, derived-state, integration and restart, not its portfolio-sized task history.
- **Lane concurrency:** independent workers, shared source fact snapshot, one target README effect lock, lane-labeled receipts, no hidden fallback.
- **First pilots:** one meaningfully changed feature (L), one poor existing README (R), plus no-README R calibration and one functioning issue-effect regression. Pick each only after live verification and policy preflight; do not mistake missing banner/diagram for proof of poor product documentation.
- **Open questions requiring owner authority:** initial upstream pilot repos; whether existing preapprovals on Cells carry over to replacement effect class; production mode for other 42 dry-run entries; auto-merge policy; runner selection and LLM gateway availability. None should stall code or read-only testing of other features. No agent invents approvals.

## 12. Ready-to-paste supervisor bootstrap directive

> You are the **implementation supervisor** for Repository Presenter v2. Read this entire specification, `repository-presenter/plans/idea.md`, the exact current `project/state.yaml`, Lane R and Lane L source code, workflows, review evidence and `foss-mcp/ops/SUPERVISOR.md`, `gatectl.py`, `gateverify.py`, `integrate.py` and relevant tests. Treat this specification as the proposed replacement architecture, not proof the old or new system works. Refresh GitHub heads and all current upstream effects. Do not modify any upstream target without current owner-scoped authorization.
>
> Your first work is a read-only **salvage manifest** marking each existing module KEEP/ADAPT/DEFER/RETIRE with source revision, imports and tests. Then establish one derived-state implementation taskcard system from `foss-mcp` (worker commits; independent supervisor verifies; negative-control falsifiers; bounded rework). Author executable B0, B1, L1, R1, X1, I1 and A1 card chains, naming public integration point, precise inputs/outputs, disjoint writable paths, and external proof. Run cards in dependency order, prioritizing first real Lane L and Lane R upstream PRs, while maintaining the existing issue effect. L must truly discover and document newly introduced product functionality, including files never previously consumed by a README. R must independently regenerate a complete poor/missing README and improve on inherited value. One lane must never be relabeled as the other or held as an invisible fallback.
>
> Before each dispatch, verify the card, its falsifier and permission preflight. Never trust a worker's PASS claim; independently review committed code in a clean, pinned environment, then record the computed verdict and integrate. On two equivalent failures diagnose root cause, at three stop and route to another ready card. Never expand a gate, add a new validator or regenerate all candidates as a way to escape an isolated failure. A result is `SHIPPED_L`, `SHIPPED_R` or `ISSUE_FILED` only after independently querying the real upstream PR/issue URL; a local bundle, sandbox demo, workflow-green check or internal PR does not count. A merge requires separate proof. Provide a short, real state table on each supervisor wake: L candidate/PR/merged, R candidate/PR/merged, issues filed/confirmed, external blockers, current active card, and next executable card. Once both lane pilots and effect proof pass, wire unattended scheduled production and demonstrate safe, idempotent external effects for both lanes. Never silently turn owner approval into a credential-based permission.

## 13. Key source links

- [Repository Presenter](https://github.com/babar-raza/repository-presenter)
- [Legacy README Optimizer](https://github.com/babar-raza/foss-readme-optimizer)
- [foss-mcp](https://github.com/babar-raza/foss-mcp)
- [Presenter's product mission](https://github.com/babar-raza/repository-presenter/blob/main/plans/idea.md)
- [Lane L correction engine](https://github.com/babar-raza/repository-presenter/blob/main/src/repository_presenter/components/readme_correction/engine.py)
- [Lane L uncovered-information detector](https://github.com/babar-raza/repository-presenter/blob/main/src/repository_presenter/components/readme_correction/detectors/gaps.py)
- [Presenter's consumed-dependency relevance detector](https://github.com/babar-raza/repository-presenter/blob/main/src/repository_presenter/components/monitor/relevance.py)
- [Lane R composition and repair](https://github.com/babar-raza/repository-presenter/blob/main/src/repository_presenter/components/readme/repair/rounds.py)
- [Lane R current acceptance judge](https://github.com/babar-raza/repository-presenter/blob/main/src/repository_presenter/components/readme/acceptance/judge.py)
- [Regeneration consumed-scope recheck](https://github.com/babar-raza/repository-presenter/blob/main/src/repository_presenter/components/readme/bundle/recheck.py)
- [README standard](https://github.com/babar-raza/repository-presenter/blob/main/docs/README_STANDARD.md)
- [Historic L corrections independent review](https://github.com/babar-raza/repository-presenter/blob/main/evidence/build/G3_PYTHON_COHORT/reseal-and-refresh/analysis/preserved/acc-corr3-summary.md)
- [Historical invalidation cost study](https://github.com/babar-raza/repository-presenter/blob/main/docs/investigations/13-bump-cost-and-recheck-design.md)
- [Current scheduled pipeline](https://github.com/babar-raza/repository-presenter/blob/main/.github/workflows/sealing-scheduled.yml)
- [Upstream issue workflow](https://github.com/babar-raza/repository-presenter/blob/main/.github/workflows/issues-scheduled.yml)
- [foss-mcp supervisor constitution](https://github.com/babar-raza/foss-mcp/blob/main/ops/SUPERVISOR.md)
- [foss-mcp state verifier](https://github.com/babar-raza/foss-mcp/blob/main/ops/gateverify.py)
