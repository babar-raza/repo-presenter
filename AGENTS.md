# AGENTS.md — Repository Presenter (new repository)

Binding authority table and roles for anyone or anything working in this
repository. Keep this short; detailed requirements live in
`docs/MISSION_AUTHORITY.md`, the live cursor lives in `project/state.yaml`, and
neither this file nor a derived document ever overrides those.

## Authority table

| Question | Authority |
|---|---|
| What must the product do, for whom, with what quality bar? | `docs/MISSION_AUTHORITY.md` |
| What is currently true / in progress / blocked right now? | `project/state.yaml` (the only execution cursor — never hand-edited; see below) |
| What old code/tests/fixtures may this repo reuse, and how? | `migration/reuse-manifest.yaml` |
| What actually happened historically, independently re-verified? | `docs/history-reconstruction.md` |
| How does the supervisor/worker loop run day to day? | `ops/SUPERVISOR.md` |

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
