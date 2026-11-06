# AGENTS.md — Repository Presenter (new repository)

Binding authority table and roles for anyone or anything working in this
repository. Keep this short; the owner's goals and conflict rulings live in
`docs/CONSOLIDATED_GOALS_2026-11-06.md` (top authority), detailed requirements in
`docs/MISSION_AUTHORITY.md`, the live cursor in `project/state.yaml`; no derived
document overrides those.

## READ THIS BEFORE ANYTHING — owner's consolidated goals (2026-11-06)

`docs/CONSOLIDATED_GOALS_2026-11-06.md` is the owner's consolidated statement of goals and requirements
(14 sections, verbatim) plus the owner's rulings on the points where older records conflicted with it
(benchmark, upstream writes, accepted-candidate target, Lane L definition, new sections, issue scope,
autonomous resumption, record order, public attribution, versions and seals, supervisor conduct). It is the **top row** of the authority table below: where any other
record in this repository (this file included) disagrees with it, it wins and the other record is corrected.
The sections below remain binding wherever they do not conflict with it.

## BINDING OWNER RULINGS R9–R11 (2026-11-06) — every session and worker follows these

Full text: `docs/CONSOLIDATED_GOALS_2026-11-06.md` Part B; operating detail: `ops/SUPERVISOR.md` items 1–7.

- **R9 — attribution is internal only.** Never print a maintainer attribution, "not verified" note or any
  provenance wording in a public README. Attribution lives only in internal records. BC-07 enforces it.
- **R10 — one standard for all candidates; a version bump never loses a seal.** Never count only "current
  version" seals, never let a bump zero a count, never regenerate a sealed candidate because a version moved.
  Re-certify existing seals from stored outputs (zero provider calls); repair only a seal that fails a real
  check, by a bounded targeted repair; never delete or demote a seal. Every mechanism change must pass the
  no-regression gate (no passing seal may start failing unless each case is a justified genuine defect).
- **R11 — decide, don't ask; report results; work in parallel.** Ask the owner only for actions only the owner
  can perform; lead every report with accepted-per-lane and delivered-upstream numbers.

## READ THIS FIRST — owner-adopted corrective plan (2026-11-03)

`docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md` is **owner-adopted, binding authority**,
not a one-time report to skim and forget. It evaluates this project against eight explicit goals
(G1–G8: Lane L/Lane R production with 25+ independently accepted candidates each, an operational
issues module, candidate publishing with mandatory tests against `cells/net` and `3d/python`,
GitHub App integration, autonomous Docker/GitHub-Actions production execution, parity with
aspose.org's refresh-candidate skill, and not repeating the two trashed predecessor projects'
failure modes) and found that four of those eight capabilities exist only as unexercised library
code nothing calls. **It was amended the same day (2026-11-03) after an external, independently-
authored counter-review — see the document's own §K — which independently confirmed additional,
real gaps the original pass missed: a reviewer-calibration gate that is itself `NOT_PASSED`, a
registry `dry_run` mode blocking one of the two G4-mandatory targets, a third never-called publish
mechanism, a real ~14% GitHub Actions success rate, and a `run_cascade.py` exit-code defect that
masks a failed seal as success.** Its corrective plan (§I) is tracked as ten live cards in
`project/state.yaml`'s `next_ready_items`, ids `AUDIT_2026_11_01_ITEM_1` through `_10`. **Every
session working in this repository must read the audit (including §K) before treating any other
planning document as current, and must treat its ten cards as real, open work — not a document
that was once read and can now be ignored.** The mission document and `MISSION_AUTHORITY.md`
still answer "what must the product do"; the audit answers "what must get fixed, concretely,
before any of that counts as delivered" — the two are complementary, not in conflict, and this
row does not reorder the authority table below.

## READ THIS SECOND — P1–P5 release contract (2026-11-04)

The owner's 2026-11-04 pre-execution-correction directive **strengthens, and does not cancel**,
the Nov-01 audit's goals and gates — it freezes five primary delivery objectives (P1–P5, see
`docs/RELEASE_CONTRACT_P1-P5.md`) and requires the ten `AUDIT_2026_11_01_ITEM_*` narrative blocks
in `project/state.yaml` to become real, mechanically-enforced taskcards instead of prose nobody
re-reads. **That has now been done**: `project/taskcards/TC-001.yaml` through `TC-012.yaml` are
the real, schema-conformant, dependency-ordered release-gate cards (Stage-0 reconciliation plus
the ten corrective items), enforced by `ops/gatecli.py`/`ops/gateverify.py` exactly as
`ops/SUPERVISOR.md` already describes — the narrative `AUDIT_2026_11_01_ITEM_*` blocks in
`project/state.yaml` are now historical record, superseded by these cards, not a second
parallel source of truth. `docs/READINESS_PACKAGE_2026-11-04.md` is the full reconciliation
package (source-of-truth record, release contract, state machine, corrected governance,
reconciled decision log, salvage table, dependency graph, acceptance matrix, honest scoreboard,
and readiness verdict). Read it, and run `python ops/gatecli.py validate` / `tick`, before
treating any status number in this repository as current.

## Authority table

| Question | Authority |
|---|---|
| What are the project's goals and requirements, and how were conflicts between older records resolved? | `docs/CONSOLIDATED_GOALS_2026-11-06.md` (owner, 2026-11-06; top authority — corrects every lower row where they disagree) |
| What must get fixed before the mission's own goals count as delivered? | `docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md`, strengthened by `docs/RELEASE_CONTRACT_P1-P5.md` (owner-adopted 2026-11-03/04; corrective-plan cards live in `project/taskcards/TC-001..TC-012.yaml`, enforced via `ops/gatecli.py`) |
| What must the product do, for whom, with what quality bar? | `docs/MISSION_AUTHORITY.md` |
| What is currently true / in progress / blocked right now? | `project/state.yaml` (the only execution cursor — never hand-edited; see below) |
| What old code/tests/fixtures may this repo reuse, and how? | `migration/reuse-manifest.yaml` |
| What actually happened historically, independently re-verified? | `docs/history-reconstruction.md` |
| How does the supervisor/worker loop run day to day? | `ops/SUPERVISOR.md` |
| Why was a given architectural/scope decision made, and what did it deliberately not decide? | `docs/DECISION_LOG.md` (records decisions; grants no authority of its own — the live cursor for any decision is still `project/state.yaml`) |

If two of the above conflict, the first row wins; a lower row is corrected to
match, never the reverse.

## Roles

| | Supervisor | Worker |
|---|---|---|
| Authors taskcards, picks next action | yes | never |
| Writes product code | never directly — see note | only inside its card's declared `write_paths` |
| Runs tests / falsifiers and decides ACCEPT / REWORK | yes, independently re-run, never trusted from the worker's own report | never grades its own work |
| Updates `project/state.yaml` | yes, via tooling only, never hand-written | never |
| Commits | supervisor stages and commits after independent verification | worker's diff is reviewed before it is committed |

In this repository the supervisor is the Claude Code session carrying this
mission. A "worker" is either (a) a bounded subagent dispatched with a
self-contained taskcard and no access to the acceptance criteria beyond what
the card states, or (b) the supervisor session itself acting under an explicit
taskcard with its own re-run verification step — but never self-graded: even
when the supervisor writes the code, it re-runs the stated tests/falsifier
from a clean state before marking the card accepted, exactly as it would for a
dispatched worker. This preserves the "a worker cannot mark its own tests
accepted" property from `ops/SUPERVISOR.md` even in a single-session context.

## Non-negotiables (carried from the mission document, not restated in full)

1. Two equal first-class lanes (Lane L, Lane R) — neither disposable, neither
   measured by the other's delivery.
2. Live upstream README is the structural/organizational/tone reference;
   repository evidence wins for factual truth only.
3. Consumed-scope invalidation only — never a global reseal (`docs/MISSION_AUTHORITY.md`
   references mission §8 in full).
4. Portfolio-first: every shared-defect fix gets a blast-radius query before
   the fix and a targeted (not global) recheck after.
5. No agent, test harness, or reviewer may silently grade or overrule its own
   negative finding. A `REJECT` is blocking unless an explicit, proven,
   deterministic refutation resolves it.
6. Evidence records come from tooling, never from model narration.
7. Report observations, not claims of progress (mission §13). A workflow is
   not "succeeded" until its hosted run and exact downstream effect are
   inspected.
8. The objective, not just the process: maximize the number of candidates both
   lanes produce across the whole portfolio (the "forest," mission plan §6),
   never optimize for one repository or one defect class in isolation. Each
   candidate's structure, tone, and presentation follow aspose.org's own
   README-refresh skill output. **Amended 2026-11-06 (owner ruling,
   `docs/CONSOLIDATED_GOALS_2026-11-06.md` ruling R2):** the aspose.org
   readme-refresh outputs already PUBLISHED upstream are the **minimum quality
   floor** for both lanes — a candidate must equal or exceed the published
   README for its product — not merely a structure/tone reference; repository
   evidence still wins for factual truth. A fix that clears one hosted-run failure but does not
   move the portfolio-wide candidate count, or that drifts from this
   structural/tone reference, is incomplete relative to this goal even if its
   own tests are green.

## Taskcard discipline — two-tier model (TWO_TIER_TASKCARD_MODEL_ADOPTED_2026-11-04)

The 2026-10-31 decision log (`docs/DECISION_LOG.md`, "Owner delegates the open decisions and
sets the target," decision 5) ruled that this file would be amended to describe what was
actually being done — narrative work items in `project/state.yaml` plus a decision-log entry,
branch, live hosted check, and independent verifier for routine fixes — instead of a per-fix
taskcard for every change. **That amendment was logged but never made** until this entry; the
contradiction between the decision log and this section (both AGENTS.md and `ops/SUPERVISOR.md`)
is resolved here, not by another decision-log paragraph alone.

Two tiers, by kind of work, not by size:

1. **Routine code fixes** (the day-to-day fix-queue sweep: a defect found against a real
   repository, a branch, a fix, an independent cold-verifier subagent, a live hosted re-check,
   a `docs/DECISION_LOG.md` entry) — **no per-fix taskcard file**, per the 2026-10-31 decision,
   now actually in force. This is the project's own proven, practiced discipline; it does not
   need the heavier mechanism below to work.
2. **Release-gate items** — anything that blocks a P1–P5/G1–G8 goal from counting as delivered
   (see `docs/RELEASE_CONTRACT_P1-P5.md`'s eleven-state distinction) — **use a real
   `project/taskcards/TC-NNN.yaml` card**, self-contained: a worker never reads this file or the
   mission document, only its card. A card states: objective, `write_paths`, `depends_on` (a
   real dependency edge to another card, mechanically enforced), checks (a falsifiable,
   re-runnable command — see `ops/SUPERVISOR.md` for the no-backslashes / semantic-break / UTF-8
   authoring rules carried over from `foss-mcp`), `source_refs`, `negative_control`, and
   `recovery`. A card is `ACCEPTED` only when `ops/gatecli.py verify`/`review` has independently
   re-run its checks twice clean and confirmed its negative control actually breaks them — never
   from a worker's or an agent's own report of having run them, and never by hand-editing a
   receipt or `project/state.yaml`'s card-derived fields (those are a function of evidence, per
   `ops/gateverify.rebuild_state`, not a narration).

This mechanism already existed (`ops/gatecli.py`, `ops/gateverify.py`, built 2026-10-21) and was
exercised exactly once (`TC-000`, a smoke test) before going dormant — the gap was data, not
code. `project/taskcards/TC-001.yaml` through `TC-012.yaml` are the first real use of it since.
