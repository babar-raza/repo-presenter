# Pre-execution readiness package — 2026-11-04

Produced in response to the owner's 2026-11-04 directive ("Final Pre-Execution Reconciliation,
Supervisor Correction, and Fastest Safe Delivery Plan"). This is the single evidence-backed
readiness package the directive's §9 asked for (deliverables A–J). It strengthens, and does not
replace or weaken, `docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md` (owner-adopted binding
authority) or `docs/MISSION_AUTHORITY.md`. **Scope discipline observed**: no portfolio campaign
was run, no PR or issue was opened/closed, no legacy workflow was disabled, no registry write
mode was changed, no reviewer gate was waived, and no new planning framework was created — every
mechanism used below (`gatecli.py`/`gateverify.py`) already existed.

## A. Source-of-truth reconciliation

See `docs/SOURCE_OF_TRUTH_2026-11-04.md` in full. Summary: nothing was lost. The documents the
directive said were missing from GitHub `main` were simply one unpushed local commit (`b4a03b8`,
parent `e78f9dc` — exactly the independent audit's own cited HEAD). This pass's own commits are
pushed as part of closing this out (see §J).

## B. Corrected release contract

See `docs/RELEASE_CONTRACT_P1-P5.md` in full: P1–P5 mapped to G1–G8, the eleven-state
distinction (implemented → tested → exercised → independently verified → accepted → owner
approved → upstream authorized → PR created → merged/live → live-verified → goal delivered),
and the current honest baseline against it.

## C. Working state machine

**Finding, independently confirmed this pass**: the dependency-graph engine, the fail-closed
"`state.yaml` must match the evidence-derived rebuild" check, and the independent-verification-
plus-negative-control discipline all already existed in `ops/gatecli.py`/`ops/gateverify.py`
(built 2026-10-21) and had simply never been fed real data beyond one smoke-test card (`TC-000`).
The fix was data, not code: `project/taskcards/TC-001.yaml` through `TC-012.yaml` now give it a
real dependency graph (Stage-0 reconciliation plus the ten `AUDIT_2026_11_01_ITEM_*` corrective
items), machine-readable (`id`, `depends_on`, `write_paths`, `checks`, `negative_control`,
`evidence`, `closeout`, `recovery` per `schemas/taskcard.schema.json`).

**Independently re-run this pass** (`python ops/gatecli.py verify TC-NNN --base <HEAD> --head
<HEAD> --no-scope` — `--no-scope` used because this is one supervisor-authored batch commit
covering all twelve cards, not the one-card-per-dispatch worker flow `check_scope` assumes; every
other part of the verification — two clean runs, structural gate, negative control required to
break the checks — ran exactly as it would for a dispatched worker):

| Card | Result | Real reason |
|---|---|---|
| TC-001 (source-of-truth) | **ACCEPTED** | Checks passed twice clean; negative control correctly broke them |
| TC-003 (two-tier governance) | **ACCEPTED** | Same |
| TC-005 (release contract + dashboard sync) | **ACCEPTED** | Same |
| TC-002 (legacy-writer disposition) | BLOCKED (`IN_PROGRESS`) | Owner-approval marker genuinely absent — correct, not yet decided |
| TC-004 (sweep-pause ruling) | BLOCKED | Owner-ruling marker genuinely absent |
| TC-006 (parity benchmark) | BLOCKED | Benchmark report doesn't exist yet |
| TC-007 (calibration iteration 4) | BLOCKED | `data/reviewer_calibration.json` status is still `NOT_PASSED` |
| TC-008 (preflight) | BLOCKED | `preflight_currency_gate` not wired into `cascade.py` yet |
| TC-009 (App-token reuse) | BLOCKED | Decision recorded (check 1 passed); wiring into `present.yml` not done (check 2 failed) |
| TC-010 (issues lifecycle) | BLOCKED | Discovery module doesn't exist yet |
| TC-011 (25-product delivery) | BLOCKED | Real count is 0, not 25 |
| TC-012 (production cutover) | BLOCKED | No schedule trigger, no Dockerfile, no cutover record yet |

`python ops/gatecli.py validate` after these receipts were written: `TC-001/003/005: ACCEPTED`,
all others `IN_PROGRESS`, `TC-000: ACCEPTED` (unaffected) — **`validate: OK`**, no schema
violations, no `state.yaml`-vs-evidence mismatch. `python ops/gatecli.py tick`: `ready cards:
none` (every unaccepted card has a real, open blocker — exactly the property the directive asked
for: the supervisor cannot proceed on an uncompleted goal without a real card moving).

## D. Corrected supervisor governance

`AGENTS.md`: added a "READ THIS SECOND" section pointing to this package and the P1–P5 contract;
the authority-table row now names both the Nov-01 audit and `docs/RELEASE_CONTRACT_P1-P5.md`;
the "Taskcard discipline" section is rewritten into the two-tier model
(`TWO_TIER_TASKCARD_MODEL_ADOPTED_2026-11-04`): routine fixes keep the 2026-10-31 discipline
(branch, decision log, independent verifier, no card file); release-gate items get a real
`TC-NNN.yaml` card.

`ops/SUPERVISOR.md`: added `RELEASE_GATE_CARDS_REINSTATED_2026-11-04` explaining the mechanism
was always there, just unfed; and a "Goal-directed decision framework" section implementing the
directive's §3.3 verbatim as an operating procedure (which goal is blocked, smallest action,
reuse-before-rebuild, parallel-safety, complexity-rejection, stop-repeating-failed-signatures,
and a named, narrow escalation list instead of "ask the owner about the plan").

## E. Reconciled decision log

New `docs/DECISION_LOG.md` entry, 2026-11-04: corrects R2's framing (the legacy-writer risk was
already named 2026-10-24, not newly discovered — and is now more precisely dormant-but-armed,
not actively writing); actually implements R3 (two-tier model, not just another paragraph);
flags R4 as a real, confirmed, **unresolved** governance violation (the 2026-10-31 sweep-pause
was never lifted before the sweep that produced today's 9–12/36 figures) rather than resolving it
unilaterally; and records the P3 decision (reuse `actions/create-github-app-token@v2`, no new
JWT code, per the directive's own stated preference — this one *is* a routine implementation
decision resolvable from evidence, not an owner-level call).

## F. Verified salvage choices

| Component | Disposition | Why |
|---|---|---|
| `core/facts.py`, extractors, lanes, state machine, noop_proof | **KEEP** | Real, working, independently verified core (unchanged assessment from both prior audits) |
| Old reviewer/judge logic, old sealed "accepted" verdicts | **DO NOT REUSE** | The exact fold-bug quality failure this project was rebuilt to avoid |
| Legacy `actions/create-github-app-token@v2` pattern (`propose.yml`, `candidates-publish.yml`) | **REUSE** | Proven, already working; decided this pass (TC-009) — do not rebuild JWT signing |
| Legacy issues `discovery`/`redetect`/`close_approval`/`lifecycle`/`funnel` modules | **REUSE, adapt** | Tested, working patterns; this repo's filing-only module is missing exactly these pieces (TC-010) |
| Legacy `monitor.yml`/`liveness.yml`/`verify-app-installation.yml`/`audit-app-installations.yml` | **KEEP running, no change** | Read-only, genuinely just observability |
| Legacy `issues-scheduled.yml`/`propose.yml`/`candidates-publish.yml` write-capable steps | **KEEP gated closed pending owner sign-off (TC-002)** | Dormant-but-armed; touching without authorization is itself an unauthorized write to someone else's governance surface |
| `gatecli.py`/`gateverify.py` | **ENFORCE, not retire** | Confirmed this pass to already do exactly what the directive's §3.2 asked for |

## G. Shortest-path implementation graph

```
TC-001 (source reconciliation)        TC-002 (writer disposition, OWNER)   TC-004 (sweep ruling, OWNER)   TC-003 (governance)   TC-005 (dashboard)
        |                                   |              |                       |
    [done]                                  |              |                   TC-006 (parity benchmark)
                                             |              |                       |
                                       TC-009 (App token)  TC-010 (issues)      TC-007 (calibration)
                                             |              |                       |
                                             +------>  TC-011 (25-product delivery) <------+
                                                              |
                                                        TC-012 (production cutover)
```

Tracks, per the directive's §5: **Track A** (quality) = TC-006 → TC-007; **Track B** (caching) =
TC-008, independent, may run now; **Track C** (App/publishing) = TC-002 → TC-009 → TC-011; **Track
D** (issues/legacy cutover) = TC-002 → TC-010 → TC-012. TC-008 is the only card with no
dependency at all and is real work that could start immediately without waiting on any owner
decision.

## H. Acceptance and verification matrix (P1–P5)

| Goal | Positive control | Negative control | Live external evidence required | Invalidation scope |
|---|---|---|---|---|
| P1 | A repo reaches state 10 (live-verified) | A repo whose live README is already correct must take the no-change path, never a manufactured PR | `gh api` read of the real upstream README/PR, not the local durable record | Per-repository only |
| P2 | One handoff clears discover→close end to end | An unauthorized/uncertain write is refused, not silently retried | The real upstream issue's state after the claimed close | Per-handoff |
| P3 | A minted token verifies via `token_provenance.py` | A token from the wrong installation is rejected | N/A (mechanism-level) | N/A |
| P4 | One unattended scheduled run completes and is independently inspected | A runner failure triggers bounded retry, not silent success | The real Actions run log | N/A |
| P5 | An unchanged rerun shows zero provider calls after simulated cache eviction | A genuinely changed input must NOT be skipped | `CallStore`/ledger record, not a print statement | Consumed scope only, never global |

## I. Honest current scoreboard (no inherited false-green counts)

Fresh, this session, `python scripts/portfolio_status.py` (read-only):

```
registry_total: 36
lane_r_pipeline_good: 10   lane_l_pipeline_good: 12
both_lanes_pipeline_good: 5
committed_bundles_lane_r: 1   committed_bundles_lane_l: 0
owner_reviewed: 0 (not tracked -- no record exists)
reviewer calibration: NOT_PASSED (unchanged since 2026-10-27)
upstream PRs from this codebase: 0.  Upstream issues filed: 1.
```

**Gap to P1 (25 common, both-lane, calibration-passing, live-delivered products): 20 more
repositories need both-lane pipeline-good status (5 → 25), and every one of the 25 — including
all 5 already both-lane-good — needs a calibration-passing reviewer pass before it counts,
since none exists today. Gap to confirmed live delivery: 25 (real count: 0).**

Taskcard scoreboard (§C): 3/12 release-gate cards `ACCEPTED` (all governance/process cards
completable without an owner decision or new product code); 9/12 `IN_PROGRESS` with a specific,
real, open blocker each; 0 falsely accepted.

## J. Final execution-readiness verdict

**Ready now**: the governance/process layer. Real taskcards exist, are schema-valid, and three
are independently `ACCEPTED` under re-run verification. The dependency graph correctly computes
`ready cards: none` — meaning the supervisor cannot proceed past a blocked gate by narrative
alone anymore.

**Blocked, with exact scope and a safe default for each**:
- **TC-002** (legacy-writer disposition) — owner decision needed: approve, amend, or reject the
  proposed per-writer disposition in `docs/LEGACY_WRITER_INVENTORY_2026-11-04.md`. Safe default
  if the owner takes no action: everything stays as-is (dormant-but-armed legacy workflows keep
  running unchanged); TC-009/TC-010 simply do not proceed.
- **TC-004** (sweep-pause ruling) — owner decision needed: ratify the 9–12/36 figures retroactively,
  or require them re-verified under the still-standing pause. Safe default if the owner takes no
  action: the figures stand as "pipeline-good, not yet calibration-verified" (already their true
  status per §B), and no further broad sweep is dispatched.
- Everything else (TC-006 through TC-012) is real, bounded engineering work with no owner
  decision required to *start* — only to reach the specific live-publication/App-auth/issues
  steps inside TC-009/TC-010/TC-011 that touch the legacy-shared upstream surface, which wait on
  TC-002.

**Not claimed**: no goal above is claimed complete. P1–P5 all remain open. This package is a
readiness correction, not a delivery report — per the directive's own instruction, "do not
declare readiness without a working state machine and an enforceable goal-completion contract."
The state machine now exists and is demonstrated working, honestly, above; the goals themselves
are not yet met.
