# repo-presenter supervisor procedure

The supervisor session's constitution. A cold restart reads this file and
`python ops/gatecli.py resume-brief` and loses nothing -- no state has ever
lived in a session's context.

Repository: `C:\Users\babar\Documents\GitHub\repo-presenter`

Adapted 2026-10-21 from `foss-mcp`'s `ops/SUPERVISOR.md` (reference mechanics
only -- see `docs/MISSION_AUTHORITY.md`). foss-mcp ran the supervisor and a
single worker as two separate Claude sessions in two terminal windows; in this
repository, per `AGENTS.md`, the supervisor is the session carrying the
mission, and a "worker" is either a dispatched subagent with a self-contained
card, or the supervisor session itself acting explicitly under a card with its
own independent re-verification step. The "separate worker window on Sonnet"
framing below does not apply here -- everything else does.

## Roles

| | Supervisor | Worker |
|---|---|---|
| Authors taskcards + falsifiers | yes | never |
| Dispatches | yes | never |
| Writes product code | never | only inside its card's `write_paths` |
| Runs `verify` / `review` | yes | **never** |
| Commits | at card/gate boundaries | never |

The split exists for one reason: a loop that graded its own homework would
forfeit the property the whole design rests on. The worker produces a commit;
`gatecli.py` computes whether that commit is acceptable.

## RELEASE_GATE_CARDS_REINSTATED_2026-11-04

This mechanism (`gatecli.py`/`gateverify.py`) was built 2026-10-21, exercised exactly once
(`TC-000`, a smoke test), then went dormant for release-blocking work — not because it didn't
work, but because nothing ever fed it real cards for anything beyond the smoke test. The gap was
data, not code: `gateverify.rebuild_state()` already computes real `READY`/`BLOCKED`/
`IN_PROGRESS`/`ACCEPTED` status from a `depends_on` dependency graph across taskcard files, and
`cmd_validate` already refuses when `project/state.yaml`'s hand-written fields disagree with
that rebuild — both existed, unused, until `project/taskcards/TC-001.yaml` through `TC-012.yaml`
(2026-11-04) gave them a real graph to compute over: the Stage-0 reconciliation items plus the
ten `AUDIT_2026_11_01_ITEM_*` corrective-plan items, now real cards instead of narrative blocks
in `project/state.yaml`'s `next_ready_items`. See AGENTS.md's "Taskcard discipline — two-tier
model" for which kind of work gets a real card (release-gate items) versus which stays on the
lighter, already-proven routine-fix discipline (branch, decision-log entry, independent
verifier, no card file).

## Goal-directed decision framework (per the 2026-11-04 directive, §3.3)

At every decision point, the supervisor answers, in order:

1. Which primary goal (P1–P5, `docs/RELEASE_CONTRACT_P1-P5.md`) is currently blocked, and by
   which specific, named card (`python ops/gatecli.py tick` prints the real READY set)?
2. What is the smallest action that removes its most important blocker?
3. What pre-existing, already-working capability can perform that action (prefer reuse over
   rebuild — see `docs/READINESS_PACKAGE_2026-11-04.md` §F's salvage table)?
4. What evidence will prove success, independently, not from a worker's own report?
5. What can proceed in parallel, and what must be serialized for safety (never two writers
   against the same upstream repository/effect; see `docs/LEGACY_WRITER_INVENTORY_2026-11-04.md`)?
6. Would the proposed change increase delivery capability, or only system complexity? Reject the
   latter.
7. Has an approach already failed on this exact failure signature? Stop repeating it; do
   root-cause analysis instead (the escalation ladder below, applied to the signature, not the
   card).

**Escalate to the owner only for genuine owner-level decisions**: production write permission,
a deliberate release-policy change, a destructive cutover, or — concretely, right now — the
three open items named in `project/taskcards/TC-002.yaml` and `TC-004.yaml` (legacy-writer
disposition; the 2026-10-31 sweep-pause ruling). Do not ask for routine implementation decisions
that evidence can already resolve. Never claim a goal complete on test counts, taskcards,
commits, documentation, or architecture alone — only on the eleven-state distinction in
`docs/RELEASE_CONTRACT_P1-P5.md` reaching the state actually claimed.

## Owner operating directive (2026-11-06) — supersedes any looser wording above

1. **The supervisor decides; it does not ask.** Every implementation, design, sequencing, tuning or
   trade-off choice is made by the supervisor against `docs/CONSOLIDATED_GOALS_2026-11-06.md` and the
   failure history of `repository-presenter` and `foss-readme-optimizer`, recorded in
   `docs/DECISION_LOG.md` with its evidence, and acted on in the same turn. A question to the owner is
   a defect: it stalls autonomous execution and invites a choice made without the context.
   The ONLY things that reach the owner are **actions only the owner can physically perform**
   (repository Settings, secrets, environments, App installation, org permissions) and a widening of
   external write authority beyond `data/upstream_write_allowlist.json`. Those are stated once as a
   precise action item, never as a multiple-choice question, and work continues on everything else.
2. **Report results, not narratives.** Lead every report with the delivery numbers: Lane R and Lane L
   independently accepted (calibrated reviewer), pipeline-good (uncalibrated, reported separately),
   upstream PRs/issues delivered and live-verified. Then only what changed and what blocks the next
   increment. No restated summaries.
3. **The goals are the spec.** Before any task, check it against the 14 sections of the consolidated
   goals; a gap found later in a goal already stated is a supervisor defect, recorded as such.
4. **Parallel by default.** Independent work runs as several isolated workers at once (worktrees);
   the supervisor verifies each result independently (tests, gate review, real runs) and merges.
   Waiting on a single worker while other READY work exists is a defect.

### Version sets and release trains (owner ruling 2026-11-06 — binding)

5. **One version set per release set.** Every candidate that is counted, accepted or delivered together was
   produced under the same single version set: every prompt (name, version, sha), reviewer logic, renderer,
   shell, normalisation, correction engine, detectors, model routes. Candidates under different version sets
   are never summed, compared as one portfolio, or delivered as one set.
6. **A version bump never invalidates a seal.** A sealed candidate is an immutable record of what its version
   set produced; a later change or a failed re-run never demotes or deletes it. Counts come from seal history
   grouped by version-set fingerprint, never from a transaction record's latest state.
7. **Release trains, not drip regeneration.** Mechanism changes accumulate on `main`. A release train pins one
   version set and regenerates every target repository under it; while a train runs, no mechanism change
   merges (a change that must land restarts the train from zero under the new set). Counts reported to the
   owner are the current train's, with older version sets shown separately. Per-fix pilot runs are diagnostics
   and are never counted as a release set.

## Channel

Two append-only JSONL files, one writer each, both git-tracked:

- `ops/instructions.jsonl` -- **supervisor appends only** (via `gatecli.py instruct`).
  Dispatches, rework defect lists, root causes.
- `ops/status.jsonl` -- **worker appends only**, and only via
  `gatecli.py status-append`, which fills the timestamp and commit hash itself.

Nothing that matters lives in either session's context. Either side can die and
be replaced without loss.

## Tick

1. `python ops/gatecli.py tick` -- bounded brief.
2. `python ops/gatecli.py doctor` -- drift, uncommitted supervisor-owned paths,
   taskcard schema violations.
3. If the worker has committed (a new `committed` line in `ops/status.jsonl`):

   ```
   python ops/gatecli.py review TC-NNN --base <base-rev> --head <worker commit>
   ```

   `--base` should be the revision the card was dispatched against (recorded
   in the matching `dispatch` line of `ops/instructions.jsonl`'s `issue_rev`).
   Do not guess a base by hand.

4. On ACCEPTED -> commit the evidence, update `project/state.yaml` from the
   rebuild (`python ops/gatecli.py validate` prints the derived rows), then
   dispatch the next card.
5. On REWORK REQUIRED -> follow the escalation ladder below.

### Autonomous continuation (owner ruling R8, 2026-11-06)

`dispatch-next` and `worker-tick` drive the same state machine without a human in the loop;
they are not a second one. The lease lives in `ops/instructions.jsonl` (the channel this file
already names): a `dispatch` line with a `lease` object (holder, base SHA, acquired/expires)
acquires it, a `rework` line renews it, `lease_release` ends it on a verdict, `lease_expired`
ends it when the holder went silent -- `gateverify.rebuild_state()` then derives the card as
READY again. One lease slot: one worker at a time.

- `python ops/gatecli.py dispatch-next --holder <session>` -- leases the first READY card in
  `tick`'s order and prints a JSON assignment (card, write_paths, checks, commit tag, the
  `review`/`verify` commands that judge it). Idempotent for the same holder while the lease is
  live; refuses a different holder; never dispatches a card awaiting a prerequisite or owner.
- `python ops/gatecli.py worker-tick` -- for the leased card, finds `(GATE/TC-NNN)` commits
  since the lease base and judges the newest one ONLY through `gateverify.do_verify` (never
  self-certified): accepted -> release; failed -> `rework` + renewed lease (attempt 3 ->
  FAILED_INTERNAL, release); no progress past `expires_at` -> `lease_expired`; then leases the
  next READY card. `--dry-run` writes nothing.
- `.github/workflows/supervisor-tick.yml` runs `doctor`, `tick` and `worker-tick --dry-run`
  hourly (read-only, no secrets, no push) as the liveness signal; the supervisor session does
  the real dispatch.

## Escalation ladder (carried from foss-mcp, same lessons)

| Attempt | Action |
|---|---|
| 1 fails | Append a **specific numbered defect list** -- never "try again". Reproduce the failure yourself first. |
| 2 fails, same signature | Stop dispatching. Read the failing code yourself and append the **actual root cause**. |
| Any attempt whose output contains non-ASCII, a `WinError`, or an encoding exception | Go straight to supervisor root-cause at attempt 1. This machine defaults to cp1252. |
| 3 fails | `FAILED_INTERNAL` with a written diagnosis. Split the card or notify. **Move to the next READY card -- the loop never halts on one bad card.** |

## Authoring a card

Every card is self-contained: the worker never reads `AGENTS.md`,
`docs/MISSION_AUTHORITY.md`, or the mission document -- only its own card file
under `project/taskcards/`. Include `source_refs` so a card cannot silently
outlive the section it came from, and `satisfies` so a missing requirement is
a hard gap rather than a silent omission.

**Authoring a falsifier -- the rule that cost the most to learn** (foss-mcp's
own words, kept verbatim because the lessons are general, not project-specific):

- No backslashes. Use `chr()` / `bytes([...])`. A backslash crossing YAML and a
  shell arrives doubled, and a regex that matches nothing exits 0.
- Prefer a semantic break (rebind the guard) over a textual one (regex on
  source). Formatting changes source shape; it does not change semantics.
- `verify` fails a falsifier that leaves the tree byte-identical, but that
  catches only the crudest case. A falsifier that changes the wrong thing
  still looks applied.
- Force UTF-8 explicitly: `python -X utf8 -c "...read_text(encoding='utf-8')
  ...write_text(..., encoding='utf-8')"`. This machine defaults to cp1252.
- Prefer breaking the function the tests actually CALL. A structural falsifier
  against an eagerly-importing package breaks test *collection*, which proves
  a file exists rather than that the code works.
- Ask the only question that matters: **does the suite still pass when the
  thing it tests is broken?**

## Committing

**Never `git add -A`.** Run:

```
python ops/gatecli.py commit-guard
```

It refuses when there is uncommitted work outside the paths you intend to
stage. Stage explicit paths, always.

## Cold restart

```
python ops/gatecli.py resume-brief
```

Then resume ticking. If a dispatched worker subagent also died, re-dispatch
it with the same card id; its next turn picks up from the files.

## What v1 defers (see migration/reuse-manifest.yaml for the full adaptation note)

Not yet ported from foss-mcp, because this repository has at most one taskcard
(`TC-000-smoke`) so far and these only pay for themselves once a queue exists:

- `preflight` (multi-card queue management; `dispatch-next`/`worker-tick` were ported
  2026-11-06 under owner ruling R8 -- see "Autonomous continuation" above)
- `gate-exit` (multi-card gate-level re-verification)
- `integrate` (atomic cherry-pick of an accepted worker branch onto main)
- `release-record` (Docker image bookkeeping -- not relevant to this project)
- the container-runner fallback and pinned-venv-by-lockfile-hash (this repo
  has no `requirements.lock` yet; verification currently runs under whatever
  Python invoked `gatecli.py`, with that interpreter's version recorded in the
  receipt's fingerprint so a mismatch is at least visible)
- holdout-check / supervisor-authored holdout tests under `evidence/holdout/`
  (needed once there is a second independent check to defend against a card
  and its own test suite sharing the same wrong idea)

## Standing rules for this session

- Never hand-write `project/state.yaml`'s card-driven fields once taskcards
  exist. `gatecli.py validate` compares the committed file against a fresh
  rebuild from receipts + `ops/instructions.jsonl`.
- Never accept a worker's claim that checks passed. Re-run them with
  `gatecli.py review`.
- A `REJECT`/`REWORK REQUIRED` verdict is never converted to `ACCEPT` because
  a defect is inconvenient to fix (mission §4, `AGENTS.md` non-negotiable #5).
- **Never idle-wait on one in-flight thing with nothing else going.** A hosted
  run, a dispatched verifier subagent, and a background test suite all notify
  on completion — waiting for that notification is not a reason to stop
  working. While one is in flight, start the next ranked fix-queue item's
  investigation, dispatch another independent check, or do other useful prep
  work in parallel, same as the portfolio-first framing (`AGENTS.md`
  non-negotiable #8) already asks for across repositories, applied here across
  time. Report genuine status when asked, but do not spend a turn only
  reporting "still waiting" when there was other real work available to start
  (owner correction, 2026-11-01).
