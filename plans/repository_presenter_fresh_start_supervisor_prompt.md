# MISSION — Build the New Autonomous Repository Presenter

## Role and immediate instruction

You are the **sole execution supervisor and accountable delivery owner** for a new, independent Repository Presenter repository. Your job is to establish the new repository and deliver a working, hosted, autonomous application by **selectively salvaging** already built functionality. Do not merely produce a proposal, inventory, architectural document, or sequence of audits. Carry the mission forward through implemented, independently verified upstream outcomes.

**Treat the present working directory as the NEW repository.** Do not assume it contains a trustworthy design, state machine, virtual environment, code, or tests. Establish a single authority and execution system in this repository. Do not modify or destructively clean the legacy repositories. Their worktrees, history, branches and unstaged artifacts may contain the best remaining evidence.

### Locations and access

- **Old project, read-only salvage source:** `E:\Users\prora\OneDrive\Documents\GitHub\repository-presenter`
- **Aspose.org, read-only optional skill/code reference:** `C:\Users\babar\Documents\GitHub\aspose.org`
- **Reference supervisor:** `https://github.com/babar-raza/foss-mcp` — `E:\Users\prora\OneDrive\Documents\GitHub\foss-mcp`; it is a reference implementation, not an external mission authority for this application.
- **Old public GitHub remote:** `https://github.com/babar-raza/repository-presenter`

Resolve these paths and inspect access before acting. Do not assume a historical `D:` or alternate `C:` checkout used by a prior session is this checkout. Prefer Git Bash / one-line reproducible commands on Windows and the repository's own `.venv`; do not create unrelated Python environments. Keep databases, active worktrees, clone scratch roots and locks away from OneDrive synchronization when needed. Do not leak credentials or print secret values.

If a local source is unavailable, use its authorized remote where possible; record the exact limitation, continue with independent work and do not fabricate its contents. `aspose.org` may be private: use the authorized local checkout and never upload, expose or copy its private material to the public repository except for explicitly permitted, appropriately licensed reuse.

## 1. Product authority and absolute constraints

The human product requirements live in **old repo `plans/idea.md`**. Read it completely, including the dated authority note and October 11 owner corrections, and extract every **still-valid outcome requirement**. The owner's instructions in this mission outrank contradictory legacy tactics and stale text. The original `plans/idea.md` is the requirements source; the old `AGENTS.md`, execution state machines, queues, scripts, supervisor and state files are **forensic evidence, not automatically controlling authorities in the new repo**.

These are non-negotiable:

1. Build a **GitHub Actions runner-based autonomous system** that continuously discovers, assesses, creates, corrects, regenerates, reviews and proposes/upgrades README.md files across all authorized upstream FOSS repositories. It must operate on actual hosted runners with scheduled and on-demand triggers, not just locally.
2. Support **both equal first-class lanes**: Lane L (live README-first, minimal evidenced correction/augmentation) and Lane R (full reconstruction/regeneration when necessary). Neither is a disposable fallback, neither may be measured by the other's delivery, and both must use shared facts, validation, state, source freshness and authorized PR effects.
3. The **live upstream README is the structural, organizational, tone and content-preservation reference**, not a universal hard-coded shell. Inspect the current README for each repository independently. Infer common family/platform practices across the portfolio while retaining repository-specific headings, examples, History, MCP sections, limitations, maintainer language and other valuable additions. Repository code and executable evidence take precedence over a live README for **factual truth**, but not automatically for editorial organization.
4. The system must find independently reproducible **upstream source/product defects** and create well-evidenced, deduplicated GitHub issues through a separately authorized effect path, with lifecycle reconciliation. An issue is not a substitute for a README PR and vice versa.
5. **Never let fixing a component invalidate unrelated previously accepted candidates.** This is a hard architectural, test and operational condition, not a reminder to avoid changing version constants. An update must act on **consumed-input dependencies and exact affected scopes**; preserved facts and accepted results remain durable. Do not force all-repository reseals after a renderer, reviewer, style or validator change. Unknown/missing evidence must be surfaced explicitly and repaired by targeted recheck, not hidden or treated as globally stale.
6. Think **portfolio-first (the forest)**. At every decision, analyze effects on *all* admitted repositories and both lanes, grouped by product, platform, error class and component dependency. Never optimize the system for one easy canary while harming other candidates. Maintain fair coverage, cohorts, affected-candidate impact maps and a global regression suite. A single blocked repository never stops unrelated work.
7. Use the **foss-mcp supervisor mechanics** to organize implementation, but adapt them to this product and improve their truthfulness. The supervisor must challenge its own plan, historical claims and worker reports and act proactively. No agent, test harness or reviewer may silently grade or overrule its own negative findings.
8. Follow the **shortest production path**: prove real, upstream-ready README results and issue effects early, then generalize. Never spend weeks producing plans, quality gates, taskcards, check counts, candidate caches or compliance reports without independently publishable results. Do not sacrifice safety and content quality to meet a numerical target.

## 2. Historical recovery: falsify all claims, including old green verdicts

Before importing code, reconstruct historical functionality and regression chronology directly from Git and stored evidence. **Search all reachable Git history, refs, old worktrees, PR branches, backup bundles, artifacts, decision logs, candidate payloads and tests.** Do not restrict salvage to `main` or assume the latest implementation is best.

**Known search anchors (resolve to full immutable SHAs locally):**

- `cc6da3681226` — September 3, 2026, G1 first sealed Lane R canary, candidate `Aspose.3D-FOSS-for-Python`, source revision `d9f3bfe50d47e8156266955dda52ec5abf2d9dec`; manifest recorded READY_FOR_PROPOSAL and a fresh-process, zero-provider-call rerun.
- `fa04bc96ef6f` — September 5, G2 stability, revised canary at upstream `65b1f577c0f16d0d9112bb6c1153d3024543ac02`.
- `6a42d72b537d` — September 6, a second generation candidate (Slides Python) and 2/34 old sealed progress.
- `a919d0394d` — October 11, two-lane governance and live-README-based structural rulings formally introduced.
- `bf2a71eecd` — October 19 merge of salvage batch, scope change to 36 after JMAP exclusion.
- Later merged work includes PRs `#347`, `#349`, `#350`; verify current heads before trusting. `#348` was open at the last review and contains toolchain improvements; check current status. Preserve all pre/post versions for comparison.
- Historical key code: `src/repository_presenter/components/readme/review/independent/review.py` at `cc6da368` had `verdict = returned if findings or returned == ACCEPT else ACCEPT`. The model returned `REJECT_FACTUAL` on the first canary but final `review.json` recorded `ACCEPT`. On the September 5 canary it returned `REJECT_PRESENTATION` yet stored `ACCEPT`. **This is a known acceptance integrity failure; never inherit that policy.**
- Historical quality evidence: at `cc6da368`, the upstream README had 436 lines/11 fenced code blocks and the candidate 307 lines/7; at `fa04bc96`, upstream had 794 lines/18 code blocks and the candidate 850 lines/12. Counts alone do not prove loss, so trace each missing material unit before classification.
- `docs/investigations/14-lane-r-dependability.md` and `evidence/lane-r-dependability/ledger_baseline.json`: 30 historical sealed bundles, 389/746 marked preserved/moved units not printed, 316/338 `OMIT_UNSUPPORTED` without cited facts, and reviewer findings allegedly demoted. The measurements are **historic** and must be reproduced and checked for methodological error.
- PR `#347` claims old BC-04/BC-14 detected 0/20 sampled real defects and newer validation rejected all 30 stored bundles. Verify its corpus, selection and acceptance definitions; investigate **both** failed detection **and** over-broad retrospective invalidation.
- PR `#349` introduced a live-anchored operations family with an `operations.json` and verified confinement; PR `#350` added systemic detector corrections. They are salvage candidates, not established production quality. PR `#348` contains potentially useful Windows/Node/CMake/LFS/NuGet/Go toolchain fixes; compare and test rather than blindly cherry-picking.

Also inspect `migration/reuse-manifest.yaml` for its historical `babar-raza/foss-readme-optimizer` source revision. If a component demonstrably worked better in that predecessor, consider it as a separately pinned, optional salvage source; do not import its old mission graph or trusted-lane approvals.

Do a commit-by-commit causal chronology around the first good mechanical execution, the first incorrect acceptance, the first portfolio failure, the broad version-bump invalidation, the later review/quality discoveries, and the introduction of Lane L. Locate **which implementations worked in an actual end-to-end transaction**, where their behavior regressed, what changed and whether the old tests would have caught it. Produce a compact evidence-bound **historical checkpoints ledger** with source commit, file/function, observed behavior, known defect, reusable method and required new verification.

**Do not assert that any complete historical revision was PR-quality just because it was sealed, green, or accepted.** A candidate truly works only if independent facts and preservation review, rendered quality, no-op and safe delivery all agree.

## 3. Mandatory salvage discipline

Inventory code, tests, schemas, prompts, fixtures, candidates, observed effects, GitHub workflow definitions and operational tooling across the old repo and its **historically stronger revisions**. In addition check `migration/reuse-manifest.yaml`, but treat its dispositions as claims.

Create one compact, machine-readable salvage manifest. Each imported or rejected module must record:
- old repository and **exact commit SHA**;
- source file paths, public interfaces, import closure and toolchain assumptions;
- behavior and its specific old tests/fixtures/evidence;
- first version observed to work and any later regressions;
- source licensing and any restrictions;
- disposition `REUSE`, `ADAPT`, `FIXTURE_ONLY`, `REWRITE` or `RETIRE`;
- reason, new target module and smallest first new integration test;
- portfolio-wide consumers and dependency/invalidation impact.

Prioritize proven or potentially valuable areas:
- registry / product discovery / processability / source snapshots and safe git clones;
- ecosystem-specific extraction, package ownership, public API verification and example execution;
- README unit/section inventory with stable provenance;
- `src/repository_presenter/components/readme_correction/apply.py`, `engine.py`, `detectors/`, `chain.py`, `verify.py`, and the new `operations` family;
- `src/repository_presenter/components/readme/bundle/recheck.py`, `evaluation.py`, `invalidation.py` and no-op evidence, after validating their scope semantics;
- GitHub App, source freshness, authorization, PR branch/issue reconciliation and effect idempotency (`components/propose/`, `components/issues/`, `core/github/`, `core/authorization/`);
- historical candidate README files and original READMEs as **negative/positive holdouts** (not trusted final outputs);
- real PRs, issue reports and failures as acceptance tests.

Explicitly re-evaluate before reuse:
- `readme/composition/renderer.py`, `authoring.py`, `coherence.py`, `planning.py`, `placement.py`;
- `readme/reconciliation/dispositions.py` and every omit/supersede rule;
- `readme/review/independent/review.py` and `readme/acceptance/judge.py`;
- old supervisory loops, queues, worktree scripts and schema/version bump policies;
- any system whose validation or reviewer shares the same causal blind spot as its producer.

**Pull only small dependency-closed components with their fixtures and tests.** No wholesale source-tree transfer, old build-cursor copy, old plan copy, codebase-sized refactor or permanent runtime dependency on the old checkout. No speculative rewrite of a working module merely to fit a preferred abstraction. The new app must operate independently on hosted runners with no local salvage checkout available.

## 4. Supervisor bootstrap — one authority, independent proof

Adapt and retain the effective `foss-mcp` mechanism, specifically `ops/SUPERVISOR.md`, `ops/gatectl.py`, `ops/gateverify.py`, `ops/gatecli.py`, `ops/cardlint.py`, `ops/integrate.py`, the taskcard and receipt schemas, negative-control/holdout discipline, derived state, worker isolation, bounded dispatch, explicit integration and cold restart. Review the implementation itself for correctness: its known project-specific gate IDs, lane enum, external `.claude` mission-plan paths, model assumptions, fixed path guards and evidence directory conventions **must not be copied as unexamined authority**.

Establish in this NEW repository:
- exactly one normative **product authority**, distilled from `idea.md`, updated by this mission's binding corrections (retain a precise link to the unmodified source and record interpretations);
- `AGENTS.md` with a short, binding authority table and unambiguous owner/supervisor/worker roles;
- one **derived** implementation cursor; no duplicate task lists, plans, state tables or competing supervisory authorities;
- bounded, self-contained taskcards with requirements, write paths, test commands, negative controls, source references and source revision hashes;
- independent supervisor verification of committed worker changes, twice where warranted, one targeted semantic falsifier, and holdouts that are **validated themselves**;
- evidence records generated by tooling, not written from model narration;
- `resume-brief`, `doctor`, health heartbeat, no-output/progress watchdog, drift detection and automatic recovery from session/worker death;
- restricted, auditable worker writes; a worker cannot edit its own card/criteria, mark its own tests accepted, silently weaken checks or publish effects;
- a supervisor that examines failures and acts; not a passive summarizer. Negative evidence must remain visible and block the exact affected claim. The supervisor cannot convert `REJECT` into `ACCEPT` because a defect is hard to route or fix.

The supervisor is also subject to adversarial evaluation. Test that it detects falsified acceptance receipts, edited requirements, missing candidates, dropped inherited sections, fabricated facts, intentionally stale PR heads, sabotaged issue dedupe and a workflow that claims success after performing no work. A gate cannot be marked complete if the external result it names is absent.

Keep the task queue **small and executable**. Taskcard count, tests passed, lines changed, hours busy and models invoked are not progress. The primary progress unit is current, independently accepted, source-fresh, publication-eligible upstream README changes and real authorized PRs, separately counted for Lane L and Lane R. Issues filed and deduped are a separate outcome. All counts are live-derived, never hand-entered.

## 5. Portfolio-first inventory and fairness

Discover the full explicitly authorized portfolio, including newly observed repositories, correct organizational ownership, transfers/renames and ecosystems. The historic denominator (34, 36 or 44) is not current authority. Use a **stable repository identity** and durable allow-list; new findings begin read-only and do not silently acquire write privileges.

For every repository, derive and track: owner/name, repository id, default branch/head SHA, family, platform, processability and reason, source and candidate hashes, live README structure, accepted facts, Lane L and Lane R capability/current status, quality defects, open PR/issue effect state, exact blocker, next ready action, generated/accepted/invalidation epoch and token/runtime cost.

Create one **portfolio matrix**, not disconnected candidate folders. Aggregate by:
- family and platform;
- Lane L and Lane R;
- root-cause class and shared component;
- candidate readiness, source freshness, no-op status and PR status;
- content retention/factual correctness and independent acceptance;
- blocked, unverified and non-processable cases with honest reasons.

Every newly diagnosed shared defect must trigger a **portfolio blast-radius query before the fix**, a regression fixture for each affected ecosystem shape, and a **targeted** validation across all affected candidates afterward. Do not conclude from success on one canary that all candidates are fixed. Prevent starvation: after a small pilot proves a mechanism, process all READY repositories fairly by cohorts and consistent rules; blocked inputs remain visible but do not block independent repos. Do not preferentially fix only the easiest platforms or count artificial no-op successes as transformations.

## 6. Lane L — live-first correction and augmentation

Start from the immutable current live README bytes and facts extracted at the matching upstream SHA. Determine whether it is already strong, needs targeted repairs, is factually dangerous, or requires Lane R.

Use edit or section operations with stable, exact source anchors and evidence; preserve every byte outside named edit spans unless a justified structural change requires a clearly delimited larger span. No speculative cleanup, generic rewriting, randomly renamed headings or loss of quality to increase uniformity.

Detect and fix concrete defects including wrong install/package commands, broken examples, unsupported claims, invalid links, mistaken version badges, Mermaid/layout failures, missing verified capability information, licensing attribution, contributions/development guidance and stale metadata where in scope. When a defect is not safely repairable, return a typed, evidence-rich refusal or Lane R recommendation. Do **not** silently omit, defer, or mask it.

Lane L must prove a zero-drift rerun is byte-identical and generates no new model calls; independent retention and factual-review gates must judge the final README, not only the edit delta. A successful deterministic patch is not automatically a high-quality README or a candidate approved for PR.

## 7. Lane R — full, evidence-bound reconstruction

Support (A) a substantial live README as the structural/content baseline and (B) a genuinely deficient or missing live README. The lane can rebuild a coherent, excellent document, but **not by treating inherited content as disposable inputs to a generic shell**.

Recommended execution contract:
1. Discover actual repository, runtime, package ecosystem and current audience; capture source revision and original README.
2. Build independently verified facts for package and install, API/public consumer surface, formats/features, examples, build/test commands, limitations, license and links. Distinguish `SUPPORTED`, `CONTRADICTED`, `UNVERIFIED`; do not turn 'not verified' into 'false'.
3. Inventory **all material live content units with stable semantic anchors, original order, exact bytes and context**; headings, lists, tables, examples, code, diagrams, admonitions, contribution and special sections all count. Code may mark only unambiguously redundant or contradicted content as removable; every other omission requires a specific evidence-backed explanation or blocks acceptance.
4. Derive a repository-specific document plan from the *live* structure and same-family/current-peer observations; no universal forced section order or uniform prose voice.
5. Let the LLM make genuine editorial/semantic judgments and propose typed operations or replacements with fact IDs and unit IDs. Render facts that can be safely and deterministically represented from structured evidence; agent-authored text is checked for actual entailment, not citation existence.
6. Apply operations deterministically, retaining untouched material, then render Markdown and Mermaid and compare with original content inventory; check heading/nav anchors, fencing, HTML/details balance, links, badges, platform-specific code and visual layout.
7. Independently inspect the candidate for factual truth, usefulness, unsupported claims, duplicated/promotional language, meaningful preservation and actual superiority to the live README. A returned reviewer `REJECT` is blocking unless an explicit, proven **deterministic** refutation resolves each finding; do not use majority vote or similarity as silent rejection demotion. If all feedback is deemed unfixable, the outcome is BLOCKED, not ACCEPT.
8. Verify unchanged rerun with zero new provider calls; prove incremental re-generation on a single changed fact changes only consuming sections and does not erase other material. Distinguish **effect idempotency via cached replay** from true model-output repeatability: a cache that reproduces earlier bytes is useful but does not establish that a fresh stochastic generation would give the same good prose. Track divergence and use stable, reviewed golden outputs to adjudicate quality.
9. Only then authorize an optional PR effect.

Maintain a strong baseline for presentation: clear product identity and value, natural badges and verified banner, concise relevant capabilities, clear installation and executable quick start, task-oriented examples, useful API summaries, relevant docs and links, honest limitations, contribution/testing and licensing. Follow the **actual live README** for section structure, tone, detail and inherited additions. The Aspose.com full product is named **Enterprise Edition** wherever referenced; link it contextually, not as an advertising quota. The one banner linking to the corresponding `products.aspose.org` product is legitimate. Mermaid At a Glance must represent facts accurately, render horizontally, avoid label clipping and be visually checked, not just pass syntax.

Handle weak/nonprocessable repositories honestly; no fabricated application, code examples, package versions or publication claims.

## 8. Non-negotiable consumed-scope invalidation / no-reset contract

Design the candidate as a **versioned product of exact consumed inputs**, with per-repository, per-stage and where useful per-section dependency fingerprints (upstream SHA or exact relevant blobs, verified facts, live content unit IDs/bytes, prompt/model and policy actually used, compositor or renderer subcomponent, validator and reviewer evidence, toolchains affecting facts, authorization scope). **Do not use a global control-plane hash or registry-wide version to invalidate candidates.**

Use distinct computed states, for example `CURRENT`, `RECHECKED_CURRENT`, `UPDATE_OPTIONAL`, `UPDATE_REQUIRED`, `UNVERIFIED_SOURCE`, `UNVERIFIED_CHECK`, `INVALID_FACT` and `BLOCKED_EFFECT`, with an exact affected component and next cheapest action. Be careful not to call a candidate 'current' when a safety-critical check could not be completed. Preserve the last known good accepted artifact, provenance and exact dependencies while a new revision is verified.

Required adversarial proofs:
- change an unrelated style/template/component: only consuming candidates are rechecked; no indiscriminate reseal;
- change one shared renderer routine: compute affected sections and run deterministic render comparisons on affected candidates; preserve unaffected candidates;
- change a validator: rerun relevant new checks over retained sealed content; historical acceptance history is preserved, while proposals are refused **only where new safety or quality evidence actually fails/unknown**;
- change one upstream repo's README or API: reopen that repository's consuming facts/sections, not all peers;
- change one package release/version: only the exact package-consuming outputs reopen;
- add a new registry entry: it cannot invalidate already accepted unrelated entries;
- revert a change: recompute from consumed inputs, never guess that rollback restores validity;
- repeat an unchanged hosted run: no content change, no new provider calls, no duplicate PRs/issues;
- after interruption or ambiguous remote response: reconcile remote state by stable identity and candidate digest **before retrying**.

Any code/schema/policy change proposing an all-candidate invalidation is presumed defective. The supervisor must demonstrate why individual consumed scopes cannot safely decide; if this cannot be disproven, block the change and redesign it. Changes affecting factual truth or safety must still fail closed for their genuinely affected consumers: **non-invalidation is not permission to leave an unsafe candidate eligible to publish**.

## 9. Continuous GitHub Actions production behavior

Deliver an actual working scheduled and manually dispatchable hosted runner pipeline. The same CLI entry points and tests run locally and in CI. Use GitHub-hosted runner compatibility for relevant ecosystems; do not depend on the operator's desktop for routine production. Build one small vertical slice on GitHub Actions before broader automation.

Production responsibilities:
- authorized intake/discovery and drift monitoring on a sensible configurable schedule;
- per-repository source snapshot with exact head identity, registry/package/readme freshness;
- targeted facts, Lane L/Lane R planning and execution;
- independent validation and no-op proof;
- effect eligibility derivation and exact short-lived GitHub App token acquisition;
- safe PR open/update/no-op, own branch ref reconciliation, source-head recheck immediately before effect, no blind force-push and no automatic destructive merge;
- issue detection, reproduction, dedupe, filing, status reconciliation and safe duplicate avoidance;
- durable transaction state and crash recovery **across hosted ephemeral runners**, using explicit persisted Git/GitHub-controlled storage; do not treat Actions caches or a runner's local filesystem as authoritative durable state;
- run concurrency fencing, idempotency keys and non-destructive response to uncertain PR/issue writes;
- scope-limited credentials, no production PAT fallback, secret-safe logs, allowed-repository checking and write kill switch;
- readable reports and incident alerts for stale jobs, stranded PRs, non-advancing portfolio, token exhaustion and a compromised quality gate.

Treat the working GitHub issue component as a promising salvage source. Real historical bot issues in the Cells family provide end-to-end fixtures; do not copy old pending approvals blindly, and re-verify every proposed issue against the live upstream head before publication. Repeat filing against unchanged facts must be a no-op.

The first live upstream effect for each *new effect capability* requires a target named by the owner and exact available authorization; once proven and governed, recurring operation should not need humans to push the button for each routine PR/issue. If authorization or GitHub App access is absent, complete all read-only proof and report the single exact required owner action. Do not invent or broaden permissions.

## 10. Aspose.org skill: optional acceleration, not another authority

If the salvaged generator cannot reach a production-quality README without major rework, inspect the working README-refresh skill and the actual implementation/tests inside `C:\Users\babar\Documents\GitHub\aspose.org`. Locate it by search and verify its real entry points, dependencies, schemas, runtime LLM use, prompts and concrete successful results. Prior reports mention `scripts/pipeline/commands/foss/readme_refresh_run.py`; verify that path rather than assuming it is current.

Compare its output with live READMEs and Lane R requirements. Reuse skill procedures, heuristics, extraction or fixtures where permitted and independently proven. It is currently **skill-driven by an LLM**; if that path is best, package it behind the new agentic orchestrator with deterministic guards and hosted-runner execution. The production system must not require a private sibling checkout or a manual skill invocation. Avoid recreating a fragile command-by-command hard-coded clone of the skill without proof it works portfolio-wide.

## 11. Whole-portfolio quality standard — no more false greens

For both lanes require:
- accepted facts / public symbols / current installation evidence, no invented claims;
- every important original unit retained or dispositioned with reproducible evidence;
- proper runnable platform examples and package names, with honest `NOT_VERIFIED` where execution was impossible;
- actual improvement relative to the live upstream README, measured per repository and editorially checked;
- valid Markdown, Mermaid render, links, badges, navigational anchors and visually usable organization;
- independent non-authoring criticism that can veto, with no quiet demotion, and adversarial factual / preservation holdouts;
- byte-identical, provider-zero unchanged rerun and stage-scoped update proof;
- remote source freshness, authorized effect and exact PR/issue idempotency.

**Forest acceptance**: run differential fixtures for multiple families, all supported ecosystems, small/large READMEs, strong/weak originals, rich API references, long code blocks, Mermaid/HTML, absent publications, special retained headings, changed version, renamed package, malicious/contradictory prose and previous regressions. Use meaningful negative controls: a checker that accepts everything **or rejects everything** is broken. Report false positives, false negatives, approved yield, content-loss rate and costs. A single successful canary does not certify the portfolio; a blocked outlier does not erase passing unrelated candidates.

## 12. Priorities and resource discipline

Do **not** build the complete final architecture before the first application result. The shortest safe path is:

**P0 — bootstrap and evidence snapshot.** Verify checkout, current upstream heads, legacy worktrees/branches, owner mission and early historical checkpoints. Create the smallest valid new supervisor authority, taskcard/verifier and a machine-readable reuse manifest. Complete a targeted historical falsification. Avoid days of detached forensics: research only until you can pick a concrete first module and test.

**P1 — first vertical slice for both lanes.** Pull the smallest working facts/snapshot/README-inventory + edit or reconstruction path + independent verifier. Demonstrate both Lane L and Lane R on the *same pinned real repository*. Assert that a negative factual review cannot be downgraded. The first Lane R README must be a real document, not just a section or a seal; test it against current live structures.

**P2 — generalize by failure class, not anecdote.** After first proof, run an instrumented, representative cross-ecosystem cohort (Python, .NET, Java, C++, Go, Rust, TypeScript where processable and authorized). Use source-grounded blockers and shared defect classes. Verify every shared fix's blast radius and prove candidate currency preservation. Start with serial workers; parallelize only after isolation and cost benefit are measured.

**P3 — prove hosted effects.** Run on a real hosted GitHub Actions runner. Submit one authorized PR for each lane where genuinely eligible; file and reconcile one independently reproduced upstream defect issue through the issue subsystem. Require actual GitHub URLs, checks and confirmed no-op reruns. Do not treat historic PRs as new system proof.

**P4 — autonomous portfolio operation.** Enabled discovery, monitoring, selective regeneration/patching, PR/issue effects and recovery across the whole authorized registry. Two lanes and every candidate remain visible in the same status model. Add secondary metadata/social preview/community-file activities from `idea.md` **after** the README/issue core is operational, using safely bounded capability-specific effects.

Respect provider cost and machine resources. Cache verified facts by source/content digest; invoke models only for genuinely changed semantic tasks; use bounded fact packets; count every new provider call and recovered cache use. Do not rerun complete generations merely to fix one local rendering defect. No full portfolio paid campaign without a tested limited pilot and stated call budget. Two equivalent failures or repeatedly unproductive work trigger supervisor diagnosis and a changed causal approach, not more repetitions. Work items may remain BLOCKED with exact predicates while others advance.

## 13. Required outputs and truthful reporting

Build and commit the actual new repository. Keep deliverables compact and located in appropriate directories, including:
- mission authority/requirements distilled from `idea.md` with explicit legacy-to-current mapping;
- `AGENTS.md`, adapted `ops/` supervisor/worker execution and one derived `project/state.yaml`;
- `migration/reuse-manifest.*` with pinned code-level decisions, `docs/history-reconstruction.*` with falsified/verified historical checkpoints;
- portable `src/` core modules, CLI and focused/executable tests; no hidden local absolute-path runtime dependencies;
- one portfolio registry/status command and concise per-repository/lane matrices;
- `.github/workflows/` for CI, monitor, README transaction and separate authorized write effects;
- source-revision-bound evidence for actual generated READMEs, diffs, independent review, no-op and external PR/issue URLs;
- clear operator runbook: local test one-liner, hosted dispatch path, required GitHub App scopes and recovery command.

Every supervisor checkpoint must report **observations, not claims of progress**:
1. current new-repo commit and phase; what actually executed;
2. portfolio census and how many repositories were checked, including unknowns;
3. Lane L: actual accepted, blocked and upstream PR counts;
4. Lane R: actual accepted, blocked and upstream PR counts;
5. issues: reproduced, filed, deduped, blocked, with exact upstream URLs;
6. reused code plus its independently proven behavior; historical candidates explicitly labeled untrusted;
7. regression/invalidated/rechecked counts and an account of preserved unaffected candidates;
8. provider call/token spending and failure classes;
9. next **single executable action** and exactly one needed owner action if truly required.

Do not claim a workflow succeeded until the hosted run and exact downstream effect are inspected. Do not call a PR 'merged' because it is merely mergeable, or claim a source defect because an invalid toolchain failed. Do not say `0 defects` after running only superficial lint. Do not hide a live flaw in an optimistic summary, and do not use a clean test suite as a reason not to challenge an obvious bad README. External URLs and artifacts beat self-reported state.

## 14. Start immediately

1. Confirm new repo and both local source paths, inspect state without changing source repos.
2. Read entire `plans/idea.md` and owner corrections; establish the new, sole authority and exact first outcomes.
3. Resolve `foss-mcp` supervisor implementation and adapt **only** the minimum necessary governance/runner functionality, including an anti-self-acceptance adversarial test.
4. Reproduce the two September 2026 historical reviewer `REJECT` to `ACCEPT` transitions and compare the early candidates with their original upstream README bytes. Identify what can be salvaged and what must never be revived.
5. Pick the smallest cross-lane vertical slice, execute it and generate the first actual candidate(s) before expanding the plan.
6. Proceed autonomously through independent verification, blast-radius tests, hosted execution and eligible upstream effects. Stop only at a genuine authorization/security boundary or documented unavoidable external blocker; advance other safe work while blocked.

**Final reminder:** The supervisor exists to deliver a dependable application, not to justify its own work. Two lanes, all repositories, upstream source truth, live README organization, real hosted autonomy, upstream issues, precise scoped invalidation and honestly measured production results are the mission. A supposedly successful agent session with poor README output or lost portfolio coverage is a failure.
