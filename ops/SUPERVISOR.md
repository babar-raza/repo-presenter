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

- `dispatch-next` / `worker-tick` / `preflight` (multi-card queue management)
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
