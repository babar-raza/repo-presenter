# AGENTS.md — Repository Presenter (new repository)

Binding authority table and roles for anyone or anything working in this
repository. Keep this short; detailed requirements live in
`docs/MISSION_AUTHORITY.md`, the live cursor lives in `project/state.yaml`, and
neither this file nor a derived document ever overrides those.

## READ THIS FIRST — owner-adopted corrective plan (2026-11-03)

`docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md` is **owner-adopted, binding authority**,
not a one-time report to skim and forget. It evaluates this project against eight explicit goals
(G1–G8: Lane L/Lane R production with 25+ independently accepted candidates each, an operational
issues module, candidate publishing with mandatory tests against `cells/net` and `3d/python`,
GitHub App integration, autonomous Docker/GitHub-Actions production execution, parity with
aspose.org's refresh-candidate skill, and not repeating the two trashed predecessor projects'
failure modes) and found that four of those eight capabilities exist only as unexercised library
code nothing calls. Its corrective plan (§I) is tracked as nine live cards in
`project/state.yaml`'s `next_ready_items`, ids `AUDIT_2026_11_01_ITEM_1` through `_9`. **Every
session working in this repository must read the audit before treating any other planning
document as current, and must treat its nine cards as real, open work — not a document that was
once read and can now be ignored.** The mission document and `MISSION_AUTHORITY.md` still answer
"what must the product do"; the audit answers "what must get fixed, concretely, before any of
that counts as delivered" — the two are complementary, not in conflict, and this row does not
reorder the authority table below.

## Authority table

| Question | Authority |
|---|---|
| What must get fixed before the mission's own goals count as delivered? | `docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md` (owner-adopted 2026-11-03; corrective-plan cards live in `project/state.yaml`) |
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
   README-refresh skill output (mission plan §10: "optional acceleration, not
   another authority" — it informs structure/tone/presentation only, same as
   item 2's live-upstream-README reference; repository evidence still wins
   for factual truth). A fix that clears one hosted-run failure but does not
   move the portfolio-wide candidate count, or that drifts from this
   structural/tone reference, is incomplete relative to this goal even if its
   own tests are green.

## Taskcard discipline (minimum, adapted from `foss-mcp`)

Every taskcard is self-contained: a worker never reads this file or the
mission document — only its card. A card states: objective, `write_paths`,
test commands, a falsifier (a change that must make the stated tests fail —
see `ops/SUPERVISOR.md` for the no-backslashes / semantic-break / UTF-8
authoring rules carried over from `foss-mcp`), `source_refs` (what evidence or
requirement this card satisfies), and rollback instructions. A card is
ACCEPTED only when the supervisor has independently re-run its tests and
falsifier from the commit it names, not from the worker's report of having
run them.
