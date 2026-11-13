# OWNER RULINGS — read this first, every session, every agent

**This file is binding and is read before any work.** It is printed into every new Claude Code session by the
SessionStart hook in `.claude/settings.json`, referenced on the first lines of `AGENTS.md` and `CLAUDE.md`, and
guarded by `tests/test_rulings_in_focus.py` (CI fails if any reference or ruling goes missing). The full text and
provenance of R1–R27 is in `docs/CONSOLIDATED_GOALS_2026-11-06.md` Part B and Part E; where this summary and that
text differ, that text governs. A new owner ruling is added here and there in the same commit.

## The goal (one paragraph)

Deliver high-quality README files across the authorized Aspose FOSS portfolio, through two independent lanes —
**Lane R** (regenerate) and **Lane L** (maintain the live README with only evidence-justified edits) — with **at
least 25 certified candidates in each lane** out of the portfolio, at or above the published aspose.org
readme-refresh benchmark, preserving valuable maintainer content, every claim verified, and real upstream delivery
(draft PRs) only once every candidate of both lanes passes. **Judge all work by certified candidates produced, not
by machinery built.**

## Before you do anything, check

1. Does this work move a certified-candidate count, or remove a named blocker of one? If not, do not do it (R27, R31).
2. Is it a fix to an existing component, not new architecture? (R27; the only sanctioned exception is R29.)
3. Will it lose or demote a seal? It must not (R10); a newly failing seal needs a justified genuine defect.
4. Does it drop anything from a live README? Only with a recorded decision and rule (R14).
5. Does any public README text carry attribution/provenance wording? It must not (R9).
6. Is it an upstream write? Not before every candidate of both lanes passes (R15), PRs only, drafts, allowlist (R3/R22).
7. Am I about to ask the owner something I can decide? Decide (R11). Stuck after repeated tries? Change approach (R12).
8. Is something blocked upstream or failing in the system? Work it by R36: verify, list honest alternatives, decide one — never just park it; classify failures into classes and fix each class once, proven before spending hosted runs.
9. Is the supervisor session about to do by hand something the hosted system should do (R37)? Make the system do it.
10. Is this being executed through the governed pipeline, and will it be done only when reproducible, verified and evidenced (R38)? Re-read `docs/R38_CHECKPOINT.md` from time to time.
11. Did everything I called next / not done / left for later / blocked become a `project/backlog.yaml` item, and did every decision-log entry get a `Backlog:` line (R40)? Prose-only follow-ups are how work was silently dropped.
12. Is this a fix for owner feedback or a defect? It applies to both lanes and every candidate, and it is done only after every candidate is re-verified under the fixed code, with evidence (R41).

## New rulings, 2026-11-13 (owner)

| # | Ruling |
|---|---|
| **R28** | **Words Java is a machine port of Words .NET**, not standard native Java. Its README work needs dedicated handling (port-aware facts and examples; API naming follows the port, not idiomatic Java assumptions). Treat as a recorded work item; do not present it as a native Java library. |
| **R29** | **A PHP extractor is needed** (Cells PHP). This is the one sanctioned exception to the R27 freeze: add a PHP platform plugin in the existing plugin pattern (`extractors/platforms/`), nothing broader. Until it exists, Cells PHP is registered but inactive. |
| **R30** | **PDF Go MCP is out of scope at this stage** (maybe in future). Excluded in `data/registry_exclusions.json`. |
| **R31** | **Provider budget reset.** The LLM budget is reset (new envelope in `data/provider_budget.json`) and may be spent on anything that **improves the certified numbers** — never on building machinery. Spend that does not move a count, or remove a blocker of one, is a defect. |
| **R32** | **Sweep pause lifted** (`OWNER_RULING_SWEEP_PAUSE: LIFTED` in `docs/DECISION_LOG.md`), on the condition that it is used to produce results: portfolio runs proceed, judged by certified counts after every wave. |
| **R33** | **"Accepted" is defined by the acceptance contract**: a candidate is independently accepted when it re-certifies under current code and holds an attested M9 acceptance record under a PASSED `data/acceptance_calibration.json`. The frozen `data/reviewer_calibration.json` (NOT_PASSED, iteration 5) no longer gates counting or upstream writes; this replaces R3's "reviewer calibration PASSED". Condition: it is used to produce results. |
| **R34** | **Portfolio grows to 41 products**: the 36 plus OCR .NET, OMR Python, PSD Java, Words Java (R28) and Cells PHP (R29, inactive until its extractor exists). |
| **R35** | **Lane L finish line**: 25 Lane L candidates that each remove at least one real, verified defect (R21 net improvement). A product with no warranted change is `NO_ACTION_JUSTIFIED` — a terminal outcome reported separately, never counted toward the 25 (R16). |
| **R36** | **Problem handling: never park, solve at the root.** **(a) Upstream blockers** — a blocker is never just reported. For each: (1) verify it against the pinned source (the blocker itself may be our misreading); (2) list every honest alternative inside the existing system: state the claim as unverified instead of verified, give the source-checkout path, omit the claim citing the fact that contradicts it, keep the maintainer text attributed, mark the item report-only; (3) pick the alternative that yields a certified candidate with no false claim, and record the decision (R14); (4) only when no honest alternative exists, make the repository terminal under R24 with the evidence and a drafted product issue (filed only as R7/R15 allow). **(b) System issues** — (1) before fixing, classify every failure across the whole portfolio by shape and fix each *class* once, at its root cause, never one run at a time; (2) prove a fix with a zero-call or local reproduction (unit test from the real failing shape, local recertify/replay, local end-to-end run where possible) before spending hosted runs, which are for sealing; (3) when a fix does not hold, re-trace the real path — never retry the same thing; (4) question the check and its data as well as the candidate: contradicting rules, wrong register entries and over-broad quotes are system defects; (5) when blocked on an action only the owner can take, bring the ask together with an alternative path the owner can approve instead. (Owner, 2026-11-13.) |
| **R37** | **The system runs itself on GitHub Actions.** The whole loop — select the cells that need work, run them in batches of six, record measured spend, seed the M9 audit, run the blind auditors, score, write the attested acceptance, count — is driven by scheduled and chained workflows with no owner dispatch and no supervisor-session step. The supervisor session oversees, diagnoses and fixes; it is never the engine. Trust safeguards stay: the seed key only in the acceptance-audit environment, every seed burned once, one open seed batch at a time, auditor findings frozen before scoring, the attested writer the only road to acceptance, owner-only budget caps. The hosted blind auditor (`scripts/run_m9_auditor.py`, reusing the existing independent reviewer) and its bot branch namespaces (`audit-findings/`, `audit-attempt/`) are sanctioned by this ruling as an exception to the R27 freeze, like R29. (Owner, 2026-11-13: "this should be wired to the system so everything is autonomous"; "in goals, we have defined that the system has to run autonomously on GitHub actions, think from that point of view".) |
| **R38** | **Mandatory Principle: Pipeline-First Execution, First Principles, and Pareto Optimization.** All execution tasks run through existing or minimally extended repeatable, deterministic, verifiable, governed pipelines; manual one-off execution never substitutes for a reusable process. First principles (real objective, source of truth, simplest sound solution); Pareto (remove systemic bottlenecks, never skip mandatory checks); pipeline-first (reuse, extend the smallest component, reproducible without undocumented agent actions; manual investigation and approvals allowed, manual production execution not); verification and evidence preserved; no unnecessary architecture; a missing pipeline is a gap to resolve. **Done = reproducible through the governed pipeline, verified, evidence available.** Full verbatim text: `docs/R38_PIPELINE_FIRST.md`; checkpoint re-injected on every owner prompt (`docs/R38_CHECKPOINT.md`). (Owner, 2026-11-13.) |
| **R39** | **Issue management system (owner, 2026-11-13).** (1) Issues are managed through the **repository-presenter** GitHub App identity (`repository-presenter[bot]`), as on https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript/issues. (2) The system **periodically checks each issue's status against what has been fixed** upstream (re-verify the recorded evidence at the latest revision) and **updates the issue status**: close with the fixing revision as evidence when the defect no longer reproduces, keep open (with a dated re-check) while it does, reopen if it regresses. (3) It is an **autonomous** issue manager in every way possible: scheduled on GitHub Actions (R37), through the existing `src/repo_presenter/issues/` lifecycle (discovery, dedup, file, labels, track, close, reopen) extended minimally (R38), never by hand. (4) **Pilot**: issue recording, monitoring and periodic open/close maintenance, starting with aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript (its five open repository-presenter issues are the first monitored set); widening the pilot is the owner's call. This amends R22's "issue filing stays off", R17's sandbox-only and R7's scope for issues on the pilot repositories only: every issue must still be a verified product/source defect with reproducible evidence at a pinned revision, deduplicated, and no attribution/provenance wording appears in any README (R9). PRs stay under R15/R22. |
| **R40** | **Persistent, autonomously managed backlog.** A structured backlog of every goal, requirement, task, defect, gap, debt, blocked and deferred item (`project/backlog.yaml`, checked by `ops/checks/backlog_check.py`), managed autonomously: discovery, dedup, prioritisation, dependencies, status, scheduling, verification, closure. Requirements reconstructed from all instructions/goals/plans/decisions/feedback, never invented; pipeline-only execution (R38); every item with status, path, acceptance, evidence; never closed without reproducible proof; continuous reconciliation; honest reporting (facts vs assumptions vs unverified); failure recovery; transparent next work. Full verbatim text and the supervisor's feasibility check: `docs/R40_BACKLOG.md`. (Owner, 2026-11-13.) |
| **R41** | **Feedback is global; every candidate is re-verified after a global fix.** Owner feedback on any one candidate applies to both lanes and every candidate in the portfolio (unless it says otherwise): the fix is made to the class at its root (R36/R38), and after it lands **every candidate in both lanes is re-verified under the fixed code** through the governed pipeline — zero-call re-certification of every seal (`recertify --write`, which also applies renderer/correction fixes to sealed candidates) and a pipeline re-run of every cell whose re-certification no longer passes. A feedback or defect item is `done` only with evidence of that portfolio-wide re-verification (the run id and its per-lane result), never because one candidate looks right. (Owner, 2026-11-13: "feedbacks are for global, both lanes and all candiates so all must be reverified after a global fix".) |

## All rulings in force (one line each)

| # | Topic | Ruling |
|---|---|---|
| R1 | Record order | Consolidated goals are the top authority; conflicting lower records are amended. |
| R2 | Benchmark | A candidate must equal or exceed the published aspose.org README for that product. |
| R3 | Upstream writes | Allowlisted repositories only, every gate passing, first PR a draft; calibration gate per R33. |
| R4 | Target | About 25 accepted per lane, counted independently. |
| R5 | Lane L trigger | A verified upstream change and a verified defect; minimal, byte-preserving edits. |
| R6 | New sections | Specific content-describing headings allowed; generic catch-alls forbidden. |
| R7 | Issues | Upstream: product/source defects only; here: own blockers. |
| R8 | Resumption | `dispatch-next` / `worker-tick` and a scheduled supervisor tick. |
| R9 | Attribution | Internal only; never in a public README in any form. |
| R10 | Seals | One standard for all candidates; a version bump never loses a seal; re-certify, never regenerate for a version. |
| R11 | Conduct | Decide, don't ask; report results first; parallel workers. |
| R12 | Stuck | After repeated failure, change approach from first principles; solve once. |
| R13 | Coverage | Complete portfolio or at least 25 per lane; never a handful of pilots. |
| R14 | Drops | Every live-README drop examined, decided, recorded and calibrated. |
| R15 | Push timing | No upstream push before every candidate of both lanes is sealed, validated and passed. |
| R16 | No-edit Lane L | `NO_ACTION_JUSTIFIED` is terminal but never counted toward 25. |
| R17 | Sandbox | Upstream-write mechanics proven on an owner sandbox before R15 holds. |
| R18 | Model | qwen3-next for every product route. |
| R19 | (superseded by the Final Directive) | |
| R20 | Lane L done | Strict R5; done when every repository has a terminal outcome. |
| R21 | Lane L bar | Net improvement: every edit verified, no new defect, at least one real defect removed. |
| R22 | Write authority | One authority, draft PRs only, nine allowlisted repositories. |
| R23 | (superseded by R25, now R31) | |
| R24 | External blockers | A verified upstream defect makes a repository terminal for R15. |
| R25 | Budget envelope | Superseded in amount by R31's reset; batches of six, measured cost. |
| R26 | Prose judge | Measure M8 first; fallback ladder only on a recorded failure. |
| R27 | **Architecture freeze** | Only fixes that make the existing system work; judge work by certified candidates. |
| R28–R41 | 2026-11-13 | See the table above. |
| Final Directive | Continuous execution | PLAN → DISPATCH → EXECUTE → VERIFY → INTEGRATE → UPDATE STATE → NEXT; never stop at a report. |
