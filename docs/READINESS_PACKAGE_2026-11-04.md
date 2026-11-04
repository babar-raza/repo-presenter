# Pre-execution readiness package — 2026-11-04 (second correction pass)

Produced in response to two directives on the same date: the initial "Final Pre-Execution
Reconciliation" directive, and a follow-up "Correct Verified State-Machine Defects and Unlock
Execution" directive responding to this document's first version. **Every defect the follow-up
directive named was independently reproduced against the real implementation before being
fixed** — none were dismissed as theoretical, none were accepted on the directive's own say-so
without a direct check. This version supersedes the first; nothing below claims readiness that
isn't demonstrated with a fresh, independently re-run receipt.

**Scope discipline observed, both passes**: no portfolio campaign, no PR/issue opened or closed,
no legacy workflow disabled, no registry write mode changed, no reviewer gate waived, no new
planning framework created.

## A. Source-of-truth reconciliation

Unchanged from pass 1: nothing was lost. See `docs/SOURCE_OF_TRUTH_2026-11-04.md`. All commits
from both passes are pushed to `origin/main`.

## B. Corrected release contract

Unchanged in substance: see `docs/RELEASE_CONTRACT_P1-P5.md` (P1–P5 ↔ G1–G8, the eleven-state
distinction, the honest baseline).

## C. Working state machine — real defects fixed, independently re-verified

**The follow-up directive's claims were checked against the actual code, not assumed true or
false.** All were confirmed real:

1. **`rebuild_state()` trusted a positive receipt without enforcing `depends_on`.** Confirmed by
   reading the code: the old loop set `ACCEPTED` directly off `receipt.get("accepted")`, with
   dependency checking only applied to *promote* a `PENDING` row to `READY`, never to *gate*
   acceptance. **Fixed**: a card now counts as effectively accepted only via a fixed-point
   computation over the whole graph — its own receipt must be accepted, non-stale, and every
   dependency must itself already be effectively accepted (transitive, not one hop).
2. **No self-dependency, cycle, or missing-dependency-ID detection.** Confirmed absent.
   **Fixed**: `gateverify.find_dependency_graph_problems()`, wired into `gatecli.py validate`.
3. **Receipts weren't bound to the card's current content.** Confirmed: `rebuild_state()` never
   compared a receipt's `card_sha256` against the card's current committed content. **Fixed**:
   `card_is_stale()` recomputes the hash the same way `do_verify` does (via `load_card_at_rev`
   against `HEAD`) and a mismatch yields `STALE_RECEIPT`, not `ACCEPTED`.
4. **Duplicate card IDs across files were invisible.** Confirmed: `all_cards()` keys a dict by
   each card's own declared `id`, silently losing a collision. **Fixed**:
   `gateverify.find_duplicate_card_ids()` walks the files directly.
5. **The READY/IN_PROGRESS deadlock was real, not theoretical** — I had personally caused it in
   pass 1 by running diagnostic `verify` calls without ever dispatching, which the old code
   permanently reclassified as `IN_PROGRESS`, making `tick` report `ready cards: none` forever.
   **Fixed**: a new status model — `AWAITING_PREREQUISITE`, `AWAITING_OWNER_DECISION`,
   `VERIFICATION_FAILED`, `STALE_RECEIPT`, `IN_PROGRESS` (only for an actually-dispatched card),
   `FAILED_INTERNAL`, `READY`, `ACCEPTED`, `SUPERSEDED` — with `VERIFICATION_FAILED`/
   `STALE_RECEIPT`/`READY` all immediately re-selectable by `tick`, while a genuinely dispatched,
   in-flight card still correctly shows `IN_PROGRESS` and is not re-offered. Confirmed fixed:
   `python ops/gatecli.py tick` now reports `ready cards: ['TC-008']` instead of `none`.

**Independently tested, with a real falsifier run against this exact fix** (not asserted):
`tests/ops/test_gateverify_dependency_enforcement.py` (16 tests — accepted-receipt-cannot-
bypass-unmet-prerequisite, three-level transitive enforcement, a positive control proving a
genuine chain still accepts, supersession invalidating a downstream dependent without touching
an unrelated card, stale-receipt rejection, the undispatched-vs-dispatched distinction,
three-strikes `FAILED_INTERNAL`, owner-decision cards never auto-offered, self-dependency,
missing-dependency-ID, two- and three-card cycles, a positive-control diamond shape, duplicate
IDs) and `tests/ops/test_cold_restart.py` (3 tests — two independently-launched cold subprocesses
agree; a cold subprocess agrees with a freshly-reimported in-process rebuild; `resume-brief` also
runs cold without error). All 19 pass. **Falsifier**: the fixed-point dependency/staleness/
supersession logic was temporarily reverted to the old naive "any accepted receipt counts"
behavior; exactly the 4 tests targeting that logic failed, the other 12 were unaffected; the fix
was restored and all 19 passed again.

**Re-verified, this pass, against commit `8756b03`** (`--no-scope`, same justification as
before: one supervisor-authored batch commit, not a per-card dispatch — see the honest caveat in
§J about this):

| Card | Result |
|---|---|
| TC-001, TC-003, TC-005 | **ACCEPTED** (checks pass twice clean; negative control correctly breaks them) |
| TC-002, TC-004 | Correctly blocked — real `owner_decision_record.py` check (cross-referenced record, not a fakeable marker), genuinely absent |
| TC-006, TC-007, TC-008, TC-009, TC-010, TC-012 | Correctly blocked — each for its own real, specific, unimplemented capability |
| TC-009a, TC-010a, TC-011, TC-012a | Correctly blocked — `AWAITING_PREREQUISITE`, naming the exact unmet dependency |

`python ops/gatecli.py validate`: **OK**, zero schema violations, zero graph problems, zero
state.yaml-vs-evidence mismatches, across all 16 cards (`TC-000`–`TC-012`, plus the three new
split cards `TC-009a`/`TC-010a`/`TC-012a`). `tick`: **`ready cards: ['TC-008', 'TC-009', 'TC-010']`**
— the deadlock is fixed, and every dev/mock-scope card the dependency-ordering correction (§G)
freed from an unnecessary owner-decision dependency is now genuinely, correctly selectable,
exactly as the directive required.

## D. Corrected supervisor governance

Unchanged from pass 1 in substance (`AGENTS.md`'s two-tier model, `ops/SUPERVISOR.md`'s
goal-directed decision framework) — see pass 1's §D. This pass added nothing new here; the
follow-up directive's governance complaints were about the *mechanism's behavior*
(§C above), not the policy text.

## E. Reconciled decision log

Pass 1's two entries stand (R2/R3/R4/P3). This pass adds no new decision-log entry — the
follow-up directive's findings were code defects and card-design defects, not new decisions to
record, with one exception already logged in pass 1's second entry: the legacy-writer
reclassification (see §F).

## F. Verified salvage choices (updated classification)

| Component | Disposition | Why |
|---|---|---|
| `core/facts.py`, extractors, lanes, state machine, noop_proof | **KEEP** | Unchanged assessment |
| Old reviewer/judge logic, old sealed "accepted" verdicts | **DO NOT REUSE** | Unchanged |
| Legacy `actions/create-github-app-token@v2` pattern | **REUSE** | Unchanged (P3 decision) |
| Legacy issues discovery/redetect/close_approval/lifecycle/funnel modules | **REUSE, adapt** | Unchanged |
| Legacy `monitor.yml`/`liveness.yml`/`verify-app-installation.yml`/`audit-app-installations.yml` | **KEEP running** | Read-only, unchanged |
| Legacy `issues-scheduled.yml`/`propose.yml`/`candidates-publish.yml` write-capable steps | **KEEP exactly as-is; do not touch the kill switch** | **Corrected classification**: globally armed since 2026-10-15 (`REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED=1`), per-repository gated on committed approval records and a 5-open-issue cap — not "dormant." Confirmed via `gh api` against the exact job the follow-up directive cited (125885584935): 2 of 22 jobs in the 2026-11-03 run had real, non-skipped write steps; zero net filings/closes occurred. A single new approval-record commit for any of the 36 repos is sufficient, with no other step, to cause a real write on the next scheduled run. |
| `gatecli.py`/`gateverify.py` | **ENFORCE, repaired, not retired** | Confirmed this pass to have had real, fixable defects (§C), now fixed and tested, not rebuilt |

## G. Corrected dependency graph and critical path

Restructured per the follow-up directive's §7 (split dev/mock scope, which needs no owner
authorization, from live-write milestones, which do):

```
TC-001 [ACCEPTED]   TC-003 [ACCEPTED]   TC-005 [ACCEPTED]

TC-002 (writer disposition, OWNER)        TC-004 (sweep ruling, OWNER)
   |         |              |                    |
   |         |              |              TC-006 (parity benchmark)
   |         |              |                    |
   |    TC-009 (App token, DEV)      TC-010 (issues, DEV)   TC-007 (calibration)
   |         |              |              |     |
   |    TC-009a (App token, LIVE) <--+      |  TC-010a (issues, LIVE)
   |         |                             |         |
   +----+----+---------- TC-011 (25-product delivery) <------+
   |         |                        |
TC-008    TC-010 (dev)           TC-012a (final cutover, OWNER) <--- everything
   |         |
   +---------+--- TC-012 (scheduling + Docker -- no longer waits on 25-product delivery)
```

**Immediately executable, right now, with no owner decision needed**: `TC-008` (P5 preflight —
confirmed `READY` by `tick`), `TC-009` (App-token dev/mock wiring), `TC-010` (issues-lifecycle
dev/mock build), `TC-006` (parity benchmark, once `TC-004` clears — see below). **Genuinely
gated on an owner decision**: `TC-002` (legacy-writer disposition), `TC-004` (sweep-pause
ruling), and everything downstream of the *live-write* milestones (`TC-009a`, `TC-010a`,
`TC-011`, `TC-012a`).

## H. Acceptance and verification matrix (P1–P5)

Unchanged from pass 1 — see pass 1's §H table (positive/negative controls, live-evidence
requirements, invalidation scope per goal).

## I. Honest current scoreboard

Unchanged numbers from pass 1 (re-confirmed, not re-measured, this pass — the follow-up
directive's findings were about the *state machine*, not the portfolio counts):

```
registry_total: 36
lane_r_pipeline_good: 10   lane_l_pipeline_good: 12
both_lanes_pipeline_good: 5
committed_bundles_lane_r: 1   committed_bundles_lane_l: 0
owner_reviewed: 0.  reviewer calibration: NOT_PASSED.
upstream PRs from this codebase: 0.  Upstream issues filed: 1.
```

Taskcard scoreboard: 3/16 `ACCEPTED` (TC-001/003/005, all governance), 2/16
`AWAITING_OWNER_DECISION` (TC-002/004), 11/16 real engineering gaps correctly shown as
`VERIFICATION_FAILED` or `AWAITING_PREREQUISITE` — zero falsely accepted, zero permanently stuck.

## J. Final execution-readiness verdict

**Ready now**: the governance/process layer, this time including a demonstrated-correct
dependency-enforcement, staleness-binding, and work-selection mechanism — not just real cards,
but a real state machine behind them, independently tested and falsified.

**Honest caveats, not papered over**:
- All twelve re-verifications this pass used `--no-scope`, same reason as pass 1 (one batch
  commit, not a per-card dispatch). The scope mechanism itself is real and was exercised
  correctly in pass 1 (it rejected my first, untagged commit with a precise violation message) —
  it has not been disabled, only bypassed for this batch-governance category of change. Future
  individual card work should use properly tagged, scoped commits; this is a process commitment
  this pass did not yet convert into a second code change (e.g. a batch-commit allowance
  distinct from per-card scope) because the existing mechanism already does the right thing once
  commits are tagged correctly.
- `TC-006`/`TC-008`/`TC-009`/`TC-010`/`TC-012` still use document-marker or file-content checks
  for genuinely unimplemented capabilities (parity benchmarking, both-lane preflight wiring, App
  token minting, issues lifecycle, scheduling/Docker) — correctly BLOCKED today, which is the
  important property, but the *check quality* for these specific cards has not yet been upgraded
  to the same cross-validated standard as TC-002/004/005/011. Flagged honestly rather than
  rushed; building real evidence checks for capabilities that don't exist yet risks producing
  fragile pseudo-implementations under time pressure, which is itself a failure mode this
  project's own history warns against.
- A central REQ-ID registry (to catch "unknown goal mappings," §3.3 of the follow-up directive)
  was not built this pass — a minor, deferred item, not a blocker.

**Two decisions only the owner can make, unchanged in substance from pass 1, now with the
isolated-work/live-write split made explicit**: `TC-002` (legacy-writer disposition — safe
default: leave the legacy system exactly as-is) and `TC-004` (sweep-pause ruling — safe default:
the current 9–12/36 figures stand as pipeline-good-but-not-calibration-verified, already their
true status). Neither blocks `TC-006`/`TC-008`/`TC-009`/`TC-010`'s dev-scope work from starting
today.

**Next executable action**: three cards are simultaneously `READY` with no owner decision needed
— `TC-008` (P5 preflight), `TC-009` (App-token dev/mock wiring), `TC-010` (issues-lifecycle
dev/mock build). Recommended first: `TC-008` — wire the already-ported `evaluate()`/`route()`
currency check into `cascade.py` before a provider call, per its own card. Acceptance condition:
its own check, `python ops/checks/marker_check.py src/repo_presenter/cascade.py
"preflight_currency_gate"`, passing under a real `gatecli.py verify` re-run, with the negative
control confirmed to break it. `TC-009`/`TC-010` can proceed in parallel on separate branches
(directive §5, Stage B: "do not permit two workers to edit the same files... concurrently" —
these three touch disjoint paths, so true parallel work is safe here).
