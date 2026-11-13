<!-- Owner's consolidated goals, recorded verbatim 2026-11-06. Top row of AGENTS.md's authority table.
     Part A is the owner's text, unchanged. Part B (rulings) is the owner's own answers to the conflicts
     found when the goals were traced against older records. Part C is the trace. Part D is the honest
     assessment of the cloud supervisor's alignment, as of 2026-11-06. -->

# Part A — the goals (owner's text, verbatim)

# Repository Presenter — Consolidated Goals and Requirements

## 1. Primary Mission

Build a production-grade, autonomous **Repository Presenter** that generates, improves, maintains, and delivers high-quality README files across the complete authorized Aspose FOSS portfolio.

The system must achieve measurable upstream results rather than merely producing local candidates, reports, or successful internal tests.

The established `aspose.org` `readme-refresh` pipeline and its outputs already published to upstream repositories serve as the **minimum quality benchmark**. Repository Presenter must produce equivalent or superior results.

## 2. Two Independent Execution Lanes

**Lane R — README Regeneration**

- Generate or substantially regenerate READMEs for repositories with missing, inadequate, outdated, or poorly structured documentation.
- Produce comprehensive, accurate, source-backed, platform-specific READMEs.
- Match or outperform the published `aspose.org` `readme-refresh` outputs.
- Preserve and incorporate valuable information from existing upstream READMEs.
- Support complete candidate generation, validation, acceptance, and upstream PR delivery.

**Lane L — Live README Maintenance**

- Detect changes to upstream repositories and their documentation requirements.
- Update existing READMEs incrementally based on verified changes.
- Preserve all still-valid original content, formatting, examples, and instructions.
- Add, modify, or remove only what is justified by authoritative evidence.
- Avoid unnecessary regeneration, content loss, duplication, and unrelated modifications.
- Produce independently validated, reviewable upstream changes.

Both lanes are first-class capabilities, with separate execution, validation, and acceptance criteria.

## 3. Portfolio-Wide Coverage

- Inventory the complete authorized Aspose FOSS repository portfolio.
- Target approximately **25 independently accepted README candidates** across the eligible portfolio, subject to the authoritative acceptance plan.
- Track Lane R and Lane L coverage independently.
- Account for every repository, including skipped, ineligible, blocked, and unsupported cases.
- Do not treat pilot success as portfolio-wide completion.
- Expand from verified pilots to controlled portfolio-wide execution.
- Maintain visibility into coverage, progress, quality, failures, and actual upstream delivery.

## 4. Authoritative Knowledge and Freshness

Every candidate must be generated from fresh, verifiable source material.

- Refresh or clone upstream repositories before processing.
- Inspect code, APIs, examples, project files, dependencies, documentation, and relevant package registries.
- Refresh product/platform knowledge before generation.
- Read the latest live upstream README and account for changes made by other agents or contributors.
- Validate technical claims, compatibility information, examples, installation commands, and links.
- Never invent functionality, package availability, features, or verification results.
- Preserve source provenance and evidence supporting generated claims.

## 5. Existing README Content Preservation

Treat existing live README content as potentially valuable, especially because it may contain information supplied by the original product developers.

- Evaluate existing content before replacing or updating it.
- Preserve accurate technical details, examples, customer-facing explanations, and project-specific information.
- Integrate useful material into improved sections where appropriate.
- Introduce additional sections where important existing information does not fit the proposed structure.
- Remove content only when demonstrably incorrect, obsolete, duplicated, or contradictory.
- Measure and report what was retained, merged, improved, removed, or lost.
- Prevent unjustified destruction of valid upstream documentation.

## 6. Quality Benchmark and Independent Evaluation

Evaluate every candidate against:

1. The current live upstream README.
2. Published outputs from `aspose.org` `readme-refresh`.
3. Fresh authoritative repository evidence.
4. Established README quality, usability, and platform-specific requirements.

Evaluate technical accuracy, completeness, practical usability, structure, clarity, discoverability, example quality, links, package instructions, content preservation, and maintainability.

A candidate must demonstrably improve the documentation or provide a justified equivalent-quality outcome.

Reject candidates that are attractive but inaccurate, incomplete, generic, or inferior to existing documentation.

## 7. Autonomous GitHub Operations

The application must operate autonomously through appropriate workflows and GitHub Actions.

- Discover eligible repositories and detect relevant upstream changes.
- Determine whether Lane R, Lane L, or no action is appropriate.
- Generate and independently verify candidates.
- Create actionable upstream pull requests when authorized and all gates pass.
- Create GitHub issues for genuine blockers, problems, or actionable findings.
- Avoid duplicate issues and PRs.
- Detect already incorporated changes and avoid unnecessary activity.
- Support unattended scheduling, bounded retries, recovery, checkpoints, and idempotent reruns.
- Confirm actual GitHub outcomes rather than assuming internal execution implies success.

The system must not require continuous human prompting to perform authorized routine work.

## 8. Supervisor, State Machine, and Governance

Use the proven `foss-mcp` supervisory approach where applicable.

- Maintain an authoritative state machine.
- Define executable taskcards with dependencies, ownership, scope, and acceptance gates.
- Enforce prerequisite completion before dependent execution.
- Require independent verification supported by concrete evidence.
- Prevent self-certified completion or misleading success reports.
- Persist state across sessions, crashes, interruptions, and restarts.
- Resume ready work automatically without repeatedly waiting for human instructions.
- Respect established authority boundaries; governance changes must follow `AGENTS.md`.
- Escalate only genuine blockers or decisions requiring human authority.

The supervisor must actively drive progress toward delivery, not merely maintain administrative state.

## 9. Reliability and Reproducibility

- Ensure deterministic or reproducible behavior wherever possible.
- Implement preflight checks, bounded execution, validation, and safe failure handling.
- Maintain receipts, execution logs, source revisions, commit SHAs, and evidence.
- Enforce safe Git operations and clean working-tree rules.
- Support partial retries without invalidating unrelated completed work.
- Detect stale evidence and upstream drift.
- Avoid destructive rewrites, unauthorized publishing, and unreviewed mass changes.
- Test successful paths, failure paths, interrupted execution, and recovery scenarios.
- Fix systemic root causes rather than applying product-specific patches.

## 10. Modular Architecture and Capability Reuse

- Treat README authoring as a modular capability within Repository Presenter.
- Separate discovery, knowledge acquisition, planning, authoring, verification, supervision, and GitHub delivery.
- Reuse proven components from `aspose.org`, `foss-mcp`, and historical working implementations where appropriate.
- Avoid unnecessary reinvention or rebuilding of functioning components.
- Use established skills, predefined paths, and approved operational interfaces.
- Maintain clear contracts between components.
- Design for extension across additional products, platforms, and repository types.

## 11. Historical Recovery and Implementation Audit

Before replacing existing functionality:

- Review original requirements, `idea.md`, decisions, current implementation, and Git history.
- Identify historical revisions where Lane R or other components worked correctly.
- Determine why previously functional capabilities regressed.
- Identify reusable components, obsolete designs, architectural mistakes, and missing functionality.
- Compare implementation against actual goals rather than internal completion claims.
- Reuse working capabilities and redesign only what genuinely requires redesign.
- Preserve useful work while removing architectural causes of repeated failures.

The objective is functional recovery and reliable delivery—not another indefinite rewrite.

## 12. Execution Strategy

Follow a supervised, evidence-driven delivery sequence:

1. Reconcile requirements against implementation and historical evidence.
2. Establish an accurate inventory of capabilities, gaps, and blockers.
3. Prepare dependency-aware executable taskcards.
4. Restore and verify the critical end-to-end execution path.
5. Demonstrate Lane R and Lane L independently using bounded real-world pilots.
6. Verify candidate quality against current upstream READMEs and the Aspose.org benchmark.
7. Verify real GitHub issue and PR delivery under authorized conditions.
8. Address systemic defects exposed by pilots.
9. Expand safely across the eligible portfolio.
10. Measure final coverage, candidate acceptance, upstream outcomes, and autonomous reliability.

Do not substitute repeated planning, documentation updates, or synthetic demonstrations for real delivery.

## 13. Definition of Done

Completion requires independently verifiable evidence that:

- Both Lane R and Lane L work end to end.
- The eligible portfolio has been inventoried and reconciled.
- The accepted-candidate target has been satisfied according to the authoritative plan.
- Outputs match or exceed the established README quality benchmark.
- Valuable existing upstream documentation is preserved.
- Generated claims and examples are technically verified.
- Autonomous workflows operate correctly.
- GitHub issues and PRs are demonstrably created when warranted and authorized.
- The supervisor correctly handles dependencies, failures, recovery, and continuation.
- Real-world tests demonstrate reliability and repeatability.
- No critical undocumented gaps remain.

**Internal taskcard acceptance, passing tests, generated candidate files, or successful CI runs alone do not establish project completion.**

## 14. Fundamental Operating Principle

**Optimize for verified upstream value, not internal activity.**

Every component, architectural decision, supervisory mechanism, taskcard, and workflow must contribute directly to one or more project goals.

Continuously evaluate:

- Does this capability advance the mission?
- Is it necessary, correct, reliable, and appropriately designed?
- Is there a simpler or more effective proven approach?
- Are we preserving valuable existing work?
- Are we producing independently verifiable outcomes?
- What remains between the current implementation and real production delivery?

The final system must be autonomous, maintainable, verifiable, safe, and capable of consistently delivering superior README documentation across the portfolio.


---

# Part B — owner rulings on conflicts with older records (2026-11-06)

Asked interactively (options with stated trade-offs); the owner's choices. Each ruling corrects the named older
records; where an older record still says otherwise, this ruling wins.

| # | Point | Ruling | Older records it corrects |
|---|---|---|---|
| R1 | Record order | These goals are the **top authority** (first row of AGENTS.md's table); conflicting lower records are amended with a pointer here. | AGENTS.md (authority table, intro) |
| R2 | Quality benchmark | For any product whose aspose.org readme-refresh output is **live upstream**, a candidate (either lane) must **equal or exceed that published README**, measured against it; the local candidate store is a secondary reference. Repository evidence still wins for factual truth. | AGENTS.md non-negotiable 8; mission doc §10 ("optional acceleration, not another authority"); `plans/idea.md` ("bot-produced README changes ... not the quality standard"); decision log 2026-10-31 decision 1; TC-006 (structural parity on local candidates only) |
| R3 | Upstream writes | **Standing authorization, gated, per-repository allowlist**: PRs and issues may be created only on repositories listed in `data/upstream_write_allowlist.json`, only when every gate passes (reviewer calibration PASSED, single owner per (repository, effect) under the TC-002 disposition, no duplicate, and the first PR on a repository opened as a draft for owner review). The allowlist starts **empty**: nothing upstream is authorized until the owner lists a repository. | decision log 2026-11-04 (NO-UPSTREAM-WRITES), 2026-10-31 decision 7 (each PR/issue named) |
| R4 | Accepted-candidate target | **About 25 accepted Lane R candidates and about 25 accepted Lane L candidates, counted independently**; the products may differ ("neither lane measured by the other"). | `docs/RELEASE_CONTRACT_P1-P5.md` P1 and TC-011 (the same >=25 products on both lanes); `project/state.yaml` P1 counter text |
| R5 | Lane L definition | Lane L is triggered by (a) a **verified upstream change** since the README's last reconciled revision (API, package, examples, documentation requirements) **and** (b) a verified defect in the live README; edits stay minimal, evidence-backed and byte-preserving outside the edit. | mission doc Lane L (defect-driven only) |
| R6 | New sections | A **new section with a specific, content-describing heading** (e.g. "Project History", "Platform Support") is allowed when important maintainer content fits no standard section; generic catch-all headings ("Preserved repository details") stay forbidden. | `plans/idea.md` (unplaceable material fails closed) |
| R7 | Issue scope | Upstream repositories: product/source defects only (under R3). **This repository**: issues for its own genuine blockers and actionable findings. | mission doc / idea.md (issues for upstream product defects only) |
| R8 | Autonomous resumption | Port foss-mcp's `dispatch-next`/`worker-tick` into `ops/gatecli.py` and add a **scheduled supervisor tick** that runs tick/doctor, picks the next READY card or fix item, and reports. | `ops/SUPERVISOR.md` ("not yet ported"); no watchdog recorded |
| R9 | Maintainer attribution | **Internal only — never in the public README, in any shape or form.** Attributed maintainer content (`PRESERVE_ATTRIBUTED`) and retained unverified examples print exactly as the maintainers wrote them, with no attribution line, label, "not verified" note or provenance wording; attribution and verification status live only in the bundle's internal records (`dispositions.json`, `facts.json`) and the reviewer's `maintainer_lines`. BC-07 (`validation/public_text.py`) refuses any README that carries them. | `docs/MAINTAINER_CONTENT_PRESERVATION.md` ("under an attribution line"); renderer before v36; prompts before independent_review v21 / source_reconciliation v15 |
| R10 | Versions and seals | **One standard for every candidate, and a version bump never loses a seal.** Every candidate — sealed or new — is held to the same current pipeline and checks. A mechanism change never invalidates a seal and never forces regeneration: existing seals are **re-certified** from their stored outputs with zero provider calls (re-render, every blocking check, reviewer pre-checks) and keep counting when they pass; only a seal that fails a new check gets a targeted repair of that defect (bounded: 3 rounds; a repeated failure signature is root-caused, never retried); no seal is ever deleted or demoted; version provenance is recorded, never used to zero a count. A **no-regression merge gate** refuses a mechanism change that would make a passing seal fail unless each newly failing seal is justified by a genuine defect the new check catches. Mechanism changes are batched and rare; a candidate regenerated more than once is reported as a pipeline defect. | supervisor's 2026-11-06 "count only the current version-set fingerprint" and "release train" wording (withdrawn); preflight reopening generation stages on any consumed-version change; predecessors' reseal-everything cycles |
| R11 | Supervisor conduct | **The supervisor decides; it does not ask** — implementation, design, sequencing and trade-off choices are made against these goals and the predecessors' failure history, recorded in the decision log with evidence, and acted on. Only actions the owner alone can perform (Settings, secrets, environments, App installation) or a widening of external write authority reach the owner, as one precise action item. Reports lead with delivery numbers (accepted per lane, delivered upstream), not narratives. Independent work runs as parallel isolated workers, each verified independently before merge. | earlier interactive-question practice; `ops/SUPERVISOR.md` before 2026-11-06 |
| R12 | When stuck | **Once something stays stuck regardless of many tries, change the approach.** Stop retrying; think from first principles; examine the problem from multiple perspectives and find the hidden factors most agents overlook; design and plan it thoroughly so it is solved once. The solution must be robust, production-grade, correctly implemented and rigorously verified, and once completed it permanently resolves the problem without being revisited. (First application: reviewer calibration, failed in five iterations.) | `ops/SUPERVISOR.md` escalation ladder ("stop repeating it; do root-cause analysis") — strengthened |
| R13 | Coverage target | **The goal always was the complete portfolio, or at least 25 accepted candidates each for Lane R and Lane L.** Counts limited to a handful of pilot repositories are not progress toward the goal; work is planned and executed portfolio-wide. Upstream writes stay governed by R3. | R4 ("about 25 per lane"); the 2026-10-31 / 2026-11-04 conditional sweep pause where it is read as capping internal candidate generation at three repositories |
| R14 | Dropping live README content | **Dropping anything from a live README is serious and is never done carelessly.** Every item a candidate drops from the live README is examined by the supervisor, who decides whether the drop was correct (keep it dropped, with the evidence) or not (re-add it), and records the decision. The system is then calibrated so it makes the same decision for every similar dropped item: each decision becomes a deterministic rule or a labelled case the pipeline is measured against, and BC-17 (benchmark parity) blocks any unreviewed loss. | implicit acceptance of model omissions (e.g. "promotional") without review |
| R15 | Upstream push timing | **No upstream push before every candidate of both lanes is sealed, validated and passed.** Upstream PRs wait until the whole portfolio (every active registry repository, in Lane R and in Lane L) is sealed and passes every gate; the allowlist and calibration gates of R3 still apply on top. Enforcement in `propose/effect.py` is designed (`docs/wip/r15-portfolio-gate.patch`) and lands only once verified. | R3 (per-repository authorization as soon as gates pass); the pilot-delivery plan |
| R27 | Architecture freeze | **No further architecture expansion.** From 2026-11-09 only tweaks and fixes that make the existing system work as expected: no new mechanisms, stages, taskcard programmes, workflows, checks or record types unless a specific failing behaviour cannot be fixed inside an existing component (then the smallest change, stated as such in the PR). Work is judged only by whether candidates are produced, sealed and pass. Unmerged expansion (e.g. PR #44's programme) stays unmerged; a piece of it may land only as a small, separately reviewed fix that a named failure needs. | R12 redesign stages S5-S12; the 2026-11-07 delivery programme (R16-R26) where it adds new architecture |
| R28 | Words Java | **A machine port of Words .NET, not native Java**: needs dedicated, port-aware handling (facts, examples, API naming follow the port). (Owner, 2026-11-13.) | — |
| R29 | PHP extractor | **A PHP extractor is needed** for Cells PHP: the one sanctioned exception to R27, in the existing plugin pattern only. (Owner, 2026-11-13.) | R27 |
| R30 | PDF Go MCP | **Out of scope at this stage**, maybe in future; excluded in `data/registry_exclusions.json`. (Owner, 2026-11-13.) | — |
| R31 | Budget reset | **The provider budget is reset** and may be spent on anything that improves the certified numbers, never on building machinery. (Owner, 2026-11-13.) | R25 amounts |
| R32 | Sweep pause | **Lifted** (`OWNER_RULING_SWEEP_PAUSE: LIFTED`), conditional on producing results; portfolio runs proceed, judged by certified counts after each wave. (Owner, 2026-11-13.) | 2026-10-31 pause, TC-004 |
| R33 | "Accepted" | **Defined by the acceptance contract**: re-certified under current code plus an attested M9 acceptance record under a PASSED `data/acceptance_calibration.json`. The frozen `data/reviewer_calibration.json` no longer gates counting or upstream writes; this replaces R3's "reviewer calibration PASSED". Conditional on producing results. (Owner, 2026-11-13.) | R3 wording; `classify_review`'s frozen-file gate |
| R34 | Portfolio | **41 products**: the 36 plus OCR .NET, OMR Python, PSD Java, Words Java (R28), Cells PHP (R29; inactive until its extractor exists). (Owner, 2026-11-13.) | registry of 36 |
| R35 | Lane L finish line | **25 Lane L candidates that each remove at least one real, verified defect** (R21); `NO_ACTION_JUSTIFIED` products are terminal, reported separately, never counted (R16). (Owner, 2026-11-13.) | — |
| R36 | Problem handling | **Never park, solve at the root.** Upstream blockers: verify against the pinned source, list honest alternatives (unverified wording, source-checkout path, omit citing the contradicting fact, attributed maintainer text, report-only), pick one that yields a certified candidate with no false claim and record it; R24 terminal only when none exists. System issues: classify failures portfolio-wide and fix each class once at its root cause; prove fixes zero-call/locally before hosted runs; re-trace, never retry; question checks and their data, not only candidates; bring every owner-only ask with an alternative path. Full text: `docs/RULINGS.md`. (Owner, 2026-11-13.) | — |

# Part C — where each goal was already recorded (trace of 2026-11-06)

Every bullet of Part A was traced against AGENTS.md, `docs/MISSION_AUTHORITY.md`, the mission document
(`plans/repository_presenter_fresh_start_supervisor_prompt.md`), `plans/idea.md`, the release contract, the
2026-11-01 audit, the readiness package, `docs/MAINTAINER_CONTENT_PRESERVATION.md`, the decision log,
`ops/SUPERVISOR.md`, `project/state.yaml`, `project/mission_matrix.yaml` and the taskcards (read-only; the five
most consequential findings were re-checked by hand against the files).

* **Recorded already** (substance present): §1 mission and upstream-results principle; §2 Lane R generation,
  preservation and delivery; Lane L preservation and evidence rules; §3 inventory, independent tracking,
  accounting for every repository, pilot-is-not-portfolio, controlled expansion, visibility; §4 freshness,
  inspection, live-README reading, validation, no invention, provenance; §5 preservation, measurement,
  no unjustified destruction (`docs/MAINTAINER_CONTENT_PRESERVATION.md`); §7 dedup, no-op detection,
  scheduling/retry/recovery, outcome confirmation; §8 state machine, taskcards, prerequisites, independent
  verification, no self-certification, persistence, escalation discipline; §9 all bullets; §11 review of
  history and reuse-not-rewrite; §12 steps 1-5 and 7-10; §13 completion is not tests/CI/cards alone
  (`ops/SUPERVISOR.md`, release contract's eleven states); §14 principle.
* **Conflicts**, now resolved by Part B: benchmark (R2), upstream writes (R3), 25 target (R4).
* **Partial**, now resolved by Part B: Lane L change detection (R5), new sections (R6), issue scope (R7),
  automatic resumption (R8).
* **Partial, still open (no ruling needed; implementation or record work)**:
  1. §6 / §12 step 6: no **mechanical gate comparing a candidate against the live README** (only loss checks);
     the TC-006 parity measurement is structural, on local candidates, and NOT_PASSED. R2 makes this a gate.
  2. §13: "**repeatability**" — the release contract asks for one unattended run (state 3); supervisor
     correctness (dependencies, failures, recovery) is not among P1-P5's release criteria.
  3. §11: no analysis of **regressions inside this repository** (e.g. the ~14 % Actions success rate, candidates
     falling to FAILED_INTERNAL); `docs/history-reconstruction.md` found no revision where Lane R verifiably
     worked, in the predecessor.
  4. §4: a separate **product/platform knowledge refresh** step is not recorded.
  5. §10: **modularity and component contracts** are practised, not stated as requirements; "use established
     skills" is in tension with the mission doc's "must not require ... a manual skill invocation" (read: reuse
     the skill's logic, not a manual invocation).
  6. §6 dimension "**maintainability**" of a README is not named anywhere; §8 there is no recorded **procedure
     for changing AGENTS.md** itself.

# Part D — is the cloud supervisor working toward these goals? (honest, 2026-11-06)

The only cloud agent active on this repository is the supervisor session ("Supervisor loop for repo-presenter");
the other recent sessions are idle or finished. Its work since 2026-11-05, by goal:

| Goal | Work done (merged PRs, each with hosted CI green) | Upstream effect |
|---|---|---|
| §6 independent evaluation | Reviewer calibration iteration 4: 41-base pre-registered corpus, NOT_PASSED measured (#13) | none |
| §4 knowledge/verification | C++ docstrings, enum members, enum-declared formats as UNRESOLVED facts (#13, #20); example verifier false positives removed (61 → 28 contradicted Python examples) reusing aspose.org's classifier, with aspose.org's own defects logged (#18, #19) | none |
| §5 preservation | `PRESERVE_ATTRIBUTED`, reviewer contract scope, supersession rule, repeatable audit (#21, #22) | none |
| §8 governance | Gate defect fixed (8 cards could never be accepted), owner-record checker self-reference fixed, TC-002/TC-004 accepted (#13-#17) | none |
| §7 GitHub delivery | TC-009a mint workflow merged (#15); not run (this session cannot dispatch: HTTP 403); TC-010a verified to have no honest target (#19) | none |
| §3/§13 delivery | **No new candidate regenerated, no candidate accepted, 0 upstream PRs or issues.** Portfolio unchanged since 2026-11-04: Lane R 10, Lane L 12, both lanes 5 pipeline-good; live-delivered 0. A 3-repository local pilot is blocked by the LLM gateway's ~30 s timeout (HTTP 502). | none |

Assessment against §14 ("verified upstream value, not internal activity"): the work is real and verified, and
each piece removes a defect that would have produced wrong candidates or false issues, but **none of it has yet
produced upstream value**. The three things between the current state and delivery are external to the code:
(1) the gateway timeout (blocks regeneration and calibration), (2) workflow-dispatch rights for this session
(blocks hosted runs, the mint and autonomy, R8), and (3) an R3 allowlist entry (blocks any upstream PR). With
those, the next steps in order are: regenerate a bounded pilot under the new rules, build calibration iteration 5
under R2/R4/R5 and the preservation requirement, and only then the first gated draft PR.

# Part E — owner rulings on the 2026-11-07 independent delivery review

An external independent review of `origin/main` (`545259436`) found 0 independently accepted candidates, five
failed reviewer calibrations, 14 of 24 latest seals needing repair, and 207 of 649 dropped README items wrongly
dropped. The supervisor verified the review's claims against the code, built a delivery plan, had it attacked by
an independent architect twice, preflighted its risks with real measurements, and put the resulting open
questions to the owner in interactive forms on 2026-11-07. The owner's selections are recorded verbatim below,
each with the question the supervisor asked and the free text the owner added where given. None of these is
inferred; where the supervisor needed a decision no form covered, it is recorded as a supervisor decision under
R11, not an owner ruling, in `docs/DELIVERY_PLAN_2026-11-07.md`.

| # | Point | Ruling | Owner's selection / words | Older records it corrects |
|---|---|---|---|---|
| R16 | Lane L no-edit outcome | A justified no-edit Lane L result is recorded as `NO_ACTION_JUSTIFIED`. It is terminal for R15's every-repository coverage rule but is **never counted as an accepted candidate** toward R4's ~25. If fewer than 25 repositories have a real R5 trigger, that number is reported honestly and the release decision returns to the owner. | "No-action: terminal, uncounted" | the supervisor's earlier practice of counting byte-identical Lane L seals (9 of 12) as accepted |
| R17 | Upstream writes before R15 | **Sandbox only.** Real draft PRs and issue file-to-close are proven on an owner-owned sandbox repository. Cells/.NET and 3D/Python (the two mandatory G4 targets) are exercised through every gate up to the write, with no write. No upstream PR or issue is created by this system until R15 holds. | "Sandbox only, R15 strict" | — |
| R18 | Model routes | **qwen3-next for every product route** (generator, prose judge M8, and the Lane R/L pipeline generally) — no second product model. Supervisor engineering work (this session, Claude or Codex) includes manual review of qwen3-next's output, used to audit candidates and to tune prompts; that review is supervisory work, not a product route, and does not reopen the qwen3-next-only ruling. | "qwen3-next for everything"; plan-comment confirmation: "That is correct. the supervisor agent could be claude or codex. Plus any manual review work should be done by them to assess work of the qwen2-next so the supervisor could further tweak the prompts to get the desired results." | clarifies [[qwen3-next-only-no-gpt-oss]] does not also forbid a different-model supervisor audit |
| R19 | Autonomy bridge priority | Superseded same day by the owner's "Final Directive: Continuous Autonomous Execution" (below): the engineering bridge is not lower priority — it runs from the start, in parallel with first-acceptance work. | "Build now, in parallel" (initial form answer, since strengthened) | — |
| R20 | Lane L completion | **Strict R5** (an upstream change AND a verified defect; no relaxation to "source-proven defect alone"). Lane L is "done" under R13's complete-portfolio branch once every repository has a terminal outcome (accepted, `NO_ACTION_JUSTIFIED`, `NOT_APPLICABLE` or a valid `BLOCKED_EXTERNAL`); eligibility grows as upstream repositories change. A defect with no upstream change is never silently dropped: it is routed to Lane R as a recorded, owned finding (`data/readme_findings.json`), per the owner's review concern D-L. | "Strict R5; done = full portfolio" | the supervisor's draft "drift-only" restriction, which the owner's review (concern D) found exceeded R5 and which is removed |
| R21 | Lane L acceptance bar | A Lane L candidate is accepted on **net improvement**: every edit justified and verified, no new defect introduced, at least one real defect removed. Residuals (defects correctly left unrepaired) are recorded internally and listed in the PR description — **never** in the README itself (R9). | "Net improvement, residuals listed" | the earlier all-or-nothing L-05 rule (every detected defect must be repaired or nothing seals), which the Lane L census showed blocks all 22 failing runs mostly on unfixable example findings |
| R22 | Write authority reconciliation | **One authority, PRs only.** All nine repositories (the three R3-allowlisted pilots plus the six inherited `mode: full` repositories) are allowlisted for draft pull requests only. The three pilots (Cells Rust, Email .NET, Imaging .NET) are switched from `registry.json` `mode: dry_run` to `mode: full`. Issue filing stays **off** on every upstream repository (R7 still permits issues on this repository itself). CI fails if the allowlist and registry `full`/`dry_run` sets ever disagree. The two open legacy-system PRs (`#7` on Cells C++ and Cells Java) count as existing PRs for this system's duplicate-PR detection. The legacy writer (`repository-presenter`) is left exactly as TC-002 already disposed it — untouched. | "One authority; PRs only"; plan-comment: "Add them to allow list" (re: the six inherited `full` repos) | the two lists (R3 allowlist; registry `mode`) had never been reconciled — the six `full` modes were inherited unchanged from the old repository on 2026-10-21 and never decided in this repository; "Add them to allow list" is read together with "One authority; PRs only" as PRs-only, consistent with issues staying off |
| R23 | Provider budget, first ask | Superseded by R25. The owner's free text when first asked: "no budget allocation at this stage. however, when project is ready and we have deployed it to production, we will allocate budget. In case budget is required right now, repop the same question, and I will select one of the options." | (quoted above) | — |
| R24 | External blockers and R15 | A repository blocked by a **verified upstream defect** (reproduced at a pinned revision, with scope-specific evidence, e.g. a syntax error in the upstream source itself) is **terminal for R15**, not an indefinite portfolio-wide block. The evidence is recorded, an issue candidate is prepared (filed only once issues are authorized upstream, R17), a follow-up owner is named, and the block is re-checked at least every 7 days; a stale check is not terminal. It unblocks automatically once the upstream fix lands and the repository is re-run. | "Evidenced external block is terminal" | the R15 patch (`docs/wip/r15-portfolio-gate.patch`) as drafted, which counted only `RECERTIFIED` with no terminal-external case, making one unfixable upstream repository (e.g. a library with a source syntax error) block upstream publication for the whole portfolio forever |
| R25 | Provider budget, final | **Envelope, not per-batch approval.** A ceiling of 9,000 provider calls / 100,000,000 tokens for the whole programme, spent in batches of six repositories. Each batch is capped at 1.5x the measured median cost of the previous batch. The supervisor stops and reports to the owner, with measured numbers, if a batch's cost per sealed candidate exceeds 2x the previous batch's. Zero-call steps (recertification, item-level restore, deterministic rule checks) always run first and are never charged against this envelope. | re-asked after R23: "Envelope with per-batch caps" | — |
| R26 | Prose-judge fallback ladder | **Measure the judge first.** The acceptance redesign's M8 fallback ladder stays rung (a) then, only on a *recorded* M8 calibration failure, rung (c) (the judge is removed from the critical path and a deterministic wording ban plus a full independent audit take over the prose classes). Rung (c) is not authorized pre-emptively: the supervisor may not skip straight to it to avoid spending the M8 calibration budget. | "No: measure the judge first" | — |

**Owner directive, same day (2026-11-07), titled "Final Directive: Continuous Autonomous Execution" — supersedes
R19's "lower priority" wording and any looser reading of R11/R8:** the supervisor is authorized to begin
executing the delivery program and to continue autonomously toward project completion. The operating model is
`PLAN → DISPATCH → EXECUTE → VERIFY → INTEGRATE → UPDATE STATE → SELECT NEXT WORK → REPEAT`, and this loop does
not stop after a plan, a taskcard, a milestone, a successful commit, a failed test, a completed worker
assignment, or a progress report. The system must: dispatch the next eligible task automatically after a
verified completion; keep independent READY tasks executing concurrently within safe write-scope limits; recover
automatically from worker failures, expired leases, interrupted sessions, rejected pushes and transient service
errors; resume from durable checkpoints without relying on the previous supervisor's conversation context; detect
stalled work and take corrective action rather than merely report inactivity; respect dependencies while
continuing unrelated work; and preserve results, evidence and candidate seals across restarts. This extends the
existing `gatecli`/`gateverify`/taskcard/lease/run-request mechanisms (`ops/SUPERVISOR.md`) — it is not a new
supervisory framework, and the scheduled `supervisor-tick` observer is explicitly named as insufficient on its
own: the actual execution bridge (`TC-032`, moved to the front of the program) must be built and proved to
resume and advance work, not merely report on it. Full detail: `docs/DELIVERY_PLAN_2026-11-07.md` §8.4.

**Full text, evidence, the review's own concerns A-L and how each was resolved, and the complete reconciled
delivery program:** `docs/DELIVERY_PLAN_2026-11-07.md`. Where this Part E and that document differ in wording,
this Part E (the owner's own recorded selections) governs; the document's narrative must be corrected to match.
