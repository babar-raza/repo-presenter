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
