# Plan: bundle integrity + no-op proof layer (not a full sealed-bundle migration)

Status: Step 1 DONE 2026-10-24 (ported, tested; see "Step 1 execution log" near the end of this
file for what was built and a real integration gap it surfaced). Steps 2–7 not started. Authority:
subordinate to `plans/repository_presenter_fresh_start_supervisor_prompt.md`
(the mission document) and `AGENTS.md`; this file is a living plan, not an authority document — if it
ever conflicts with the mission document, the mission document wins and this file is corrected.
Logged per owner instruction, 2026-10-24: "after analysis, log it in decision logs, plans and
especially in state machine so we do not forget about anything." See also `docs/DECISION_LOG.md`
(the decision this plan implements) and `project/state.yaml`'s `PORT_BUNDLE_INTEGRITY_LAYER` card
(the live execution cursor for it).

Trigger: owner observed that the old repository's "sealed bundle" architecture
(`candidates/<owner>__<name>/<revision>/manifest.json` + `CURRENT` pointer + `dependencies.json` +
a lifecycle state machine) looks more traceable/accountable than this repository's current flat-file
evidence layout, and specifically believed the old repo's "zero new provider calls" caching was
*driven by* that architecture — concluding it should be ported (option A, agreed) without
invalidating already-produced candidates. This plan is the deep, evidence-driven assessment the
owner asked for before any such port, built via a dedicated research pass (not from memory) against
both repositories' actual code.

## Assessment scope

- **System/component**: whether/how to port the old repo's bundle-integrity and no-op-proof layer
  (`core/candidates.py`, `components/readme/bundle/seal.py`, `core/noop_proof.py`, and the
  unported remainder of `components/readme/bundle/recheck.py`).
- **Intended outcome**: durable, tooling-verified answers to "is this candidate still current under
  the running code" and "did this rerun really make zero new provider calls" — the literal
  requirement in mission §8 ("verify unchanged rerun with zero new provider calls").
- **Current sources of truth**: `src/repo_presenter/core/llm/jobs.py` (`CallStore`, `run_job`),
  `core/llm/ledger.py` (`canonical_hash`, `CallRecord`, `summarize`), `readme/bundle/{recheck,
  evaluation,invalidation}.py` (partially ported), `project/state.yaml`, `migration/reuse-manifest.yaml`.
- **Inputs and consumers**: LLM job calls (producer of ledger records); `propose/effect.py`
  (consumer of a narrower, single-field staleness check — not this layer); a future repair loop
  (would-be consumer, does not exist yet); the owner/supervisor, who currently has no tooling-backed
  way to verify a "no-op" claim beyond reading ledger counts by hand.
- **Evidence inspected**: old repo's `core/noop_proof.py` (524 lines, read in full),
  `core/candidates.py` (646 lines, read through the state-machine/counting logic),
  `core/llm/jobs.py` in both repositories (`CallStore` class and `run_job`'s cache-hit path),
  `project/state.yaml` (lines ~829–836, the 2026-10-23 workspace-caching bug and fix),
  `migration/reuse-manifest.yaml`'s existing bundle/candidates/caching entries, and
  `plans/repository_presenter_fresh_start_supervisor_prompt.md` §8.
- **Missing evidence** (explicitly, not glossed over): `components/readme/bundle/seal.py` (1,203
  lines, the bundle *writer*) has not been read in this pass at all — only referenced indirectly via
  `candidates.py`'s imports. `recheck.py`'s five scope-runners (`_recheck_presentation/_authoring/
  _validator/_reviewer/_extraction`) were not re-read line-by-line this pass; their dependency
  closure was taken from this repository's own `recheck.py` docstring (an earlier, already-recorded
  investigation), not independently re-verified against the old file directly in this pass.

## Current-state reconstruction

- **Actual execution flow today**: `scripts/run_lane_r_*.py` → `core/llm/jobs.py::run_job()` →
  `CallStore.get(request_sha256)` (cache hit/miss) → a ledger record (`provider_call` or
  `cache_reuse`) appended → output written to `scripts/_lane_r_output/<repo>/*.json` and
  `evidence/build/<phase>/<repo>/*.json` — flat files, no manifest, no seal, no `CURRENT` pointer.
- **Components actually used**: `CallStore` — confirmed working, not theoretical: `project/state.yaml`
  already records that every call this session was showing `cache_reused=False` because each script
  invocation used a fresh `tempfile.mkdtemp()` workspace, discarding the cache every run; fixing that
  to a persistent `workspace/calls` directory made caching work. `readme/bundle/evaluation.py` and
  `invalidation.py` are recorded as fully ported, but **this plan has not independently re-verified
  that anything currently calls them** — flagged as a to-verify item before relying on them further,
  not assumed safe.
- **State and artifact flow**: no state field exists on disk for any repository's candidate beyond
  "whatever the last script run happened to write." "State" today is prose in `project/state.yaml`'s
  narrative cards, not a structured, machine-readable per-repository record.
- **Gates and validators**: `readme/review/independent_reviewer.py` (built 2026-10-24) checks
  factual/structural soundness of a candidate's *content* — an orthogonal concern, not currency.
  `propose/effect.py`'s `recheck_source` checks one field (the source revision string) immediately
  before a write — a narrow, working, already-sufficient check for that one call site, not a
  general dependency-currency model.
- **Downstream consumption**: nothing in this repository currently consumes a currency verdict in
  production. There is no repair loop and no scheduled regeneration job that would act on
  "this candidate is stale."
- **Observed inconsistencies**: the already-fixed `tempfile.mkdtemp()` caching bug (see above) is a
  real, previously-measured inconsistency, and it is fully explained by a missing durable directory
  — not by anything related to bundle sealing.

## Symptoms (not causes)

- The owner's belief that LLM-call caching depends on the sealed-bundle format — a reasonable
  inference from the old repo's packaging (both concerns lived under the same `bundle`/`candidates`
  subsystem name), but not borne out by the actual code.
- No way today to *prove*, to a skeptical reader, that a claimed "unchanged rerun, zero new calls"
  actually happened across two independent process runs — only ledger counts, read and reported by
  narration.
- No per-repository machine-readable state distinguishing fresh/stale/needs-recheck.

## Root causes

1. **The caching mechanism and the integrity/currency mechanism are independent in the old repo's
   own code, but co-located under one subsystem name, creating an appearance of coupling that the
   code itself does not have.**
   Evidence: `core/candidates.py` never imports `core/llm/jobs.py` or vice versa (direct read,
   both files). `CallStore`'s cache-hit path (`run_job`, old repo and this repo, same logic) needs
   nothing but a `request_sha256` and a directory — no manifest, no seal, no `CURRENT` pointer.
   First failing boundary: an assumption, not a code defect. Affected scope: this one decision.
   Confidence: HIGH (both files read directly; call graph traced).

2. **This repository has no no-op-proof primitive at all** (`core/noop_proof.py`'s
   `ProcessIdentity`/`verify_noop_pair`/`measure_invocation` have zero equivalent).
   Evidence: `core/llm/ledger.py::summarize()` only counts one ledger's own records; nothing
   verifies two independent process runs, checks process identity, or compares invocation records.
   First failing boundary: mission §8's explicit "verify unchanged rerun with zero new provider
   calls" requirement — unimplemented today. Affected scope: every future "no-op proven" claim this
   project makes is currently a narrated claim, not a tooling-verified one (in tension with mission
   non-negotiable #6, "evidence records come from tooling, never from model narration" — the same
   failure shape AGENTS.md's own worker/supervisor no-self-grading rule exists to prevent, just
   applied to cache-reuse claims instead of test results). Confidence: HIGH.

3. **No `CURRENT`-pointer/state-machine exists for any repository's candidate.**
   Evidence: `scripts/_lane_r_output/<repo>/` has no state file; `project/state.yaml`'s own record
   of "what happened" for any one repository is free-text narrative inside long cards, not a
   structured per-repository field. First failing boundary: whenever a second process or person
   needs a repository's state without reading supervisor prose. Affected scope: portfolio-wide.
   This is a known, intentionally deferred gap (P1 "smallest working first" discipline), not a
   regression. Confidence: HIGH.

## Structural weaknesses

- No machine-readable per-repository currency state (root cause 3).
- No tamper-evident integrity check on any stored candidate artifact — a hand-edited or corrupted
  `facts.json`/`content_units.json` would go unnoticed by any tooling today.
- No formal, independently-verified no-op proof (root cause 2) — currently self-reported, which is
  exactly the shape of risk AGENTS.md's "a worker cannot mark its own tests accepted" rule targets.
- **A port-fidelity gap against the mission document itself**, independent of the old repo: mission
  §8 names the currency states `CURRENT, RECHECKED_CURRENT, UPDATE_OPTIONAL, UPDATE_REQUIRED,
  UNVERIFIED_SOURCE, UNVERIFIED_CHECK, INVALID_FACT, BLOCKED_EFFECT`. This repository's already-ported
  `readme/bundle/recheck.py` only has a single `UNVERIFIED` (not split into `_SOURCE`/`_CHECK`) and
  has no `INVALID_FACT` or `BLOCKED_EFFECT` state at all. This needs correcting regardless of any
  bundle-porting decision.

## What should be preserved

- `CallStore` + `canonical_hash` (`core/llm/jobs.py`, `core/llm/ledger.py`) — proven working,
  already debugged once (the workspace-directory fix). **Not touched by this plan.**
- `readme/bundle/recheck.py`'s currency-state model, `classify()`, the receipt cache, and the patch
  round-trip — already ported, self-contained (pending the to-verify spot-check above).
- `readme/bundle/evaluation.py` and `invalidation.py` — already fully ported per their own
  docstrings (same to-verify caveat).
- The existing flat-file evidence layout (`scripts/_lane_r_output/`, `evidence/build/`) for every
  repository's existing work — must never be retroactively rewritten by this plan.
- `readme/review/independent_reviewer.py` + `defect_bridge.py` (built 2026-10-24) — an orthogonal
  concern (factual/structural soundness vs. currency); no overlap, no conflict, nothing to change.

## What must be redesigned or newly built

- A no-op-proof primitive: port `core/noop_proof.py`'s bundle-independent ~460 lines
  (`ProcessIdentity`, `Invocation`, `verify_noop_pair`, `measure_invocation`) — usable immediately
  against the *existing* `CallStore`/ledger, with **no bundle dependency at all**.
- A new, additive `candidates/` directory tree (sealed bundles) for *future* cascades only — port
  `candidates.py`'s reader (646 lines) and enough of `seal.py` (1,203 lines, not yet read — read
  this before any porting decision on it) to actually write a sealed bundle.
- Align `recheck.py`'s `CURRENCY_STATES` with mission §8's full vocabulary (add the
  `UNVERIFIED_SOURCE`/`UNVERIFIED_CHECK` split, `INVALID_FACT`, `BLOCKED_EFFECT`) — a correction to
  the existing port, independent of the bundle-porting question.
- Finish `recheck.py`'s five scope-runners, but only against the *new* sealed format, and only
  after the writer (`seal.py` port) exists — there is nothing to recheck until something is sealed.

## Production-grade target design

**Architecture**: two layers, kept independent exactly as the evidence shows they already are.
*Layer 1* (complete, unchanged): `CallStore`/ledger content-addressed caching — "don't redo
expensive work." *Layer 2* (new): bundle integrity + no-op proof + currency — "prove and track" —
built additively alongside the existing flat-file evidence, never replacing it for anything already
written.

**Component responsibilities**:
- `noop_proof.py` (ported subset): verifies two independent process runs against a shared ledger
  slice; no bundle dependency; callable today against any existing
  `scripts/_lane_r_output/<repo>/calls/` ledger.
- `candidates.py` (ported): reads a *new* `candidates/<owner>__<name>/<revision>/` tree only.
  Verified directly: `iter_sealed_bundles` returns an empty generator the instant
  `root / "candidates"` does not exist, and a repository with no `CURRENT` file is "silently not
  counted," never an error and never a false invalidation. This is a structural, not a
  to-be-added, safety property.
- `seal.py` (to be read in full, then ported/adapted): writes a sealed bundle only as a new, opt-in
  step appended *after* today's existing render step — the same additive pattern as today's
  facts-persistence fix (fix/extend going forward, never rewrite existing evidence in place).
- `recheck.py` (extend the existing port): the five scope-runners operate only against sealed
  bundles; any repository with no bundle is reported `UNVERIFIED` (or left unmodeled), never
  silently `CURRENT` and never invalidated, by the same construction as `candidates.py` above.

**State model**: per-repository, per-revision sealed bundle with an explicit `CURRENT` pointer, the
full mission-§8-aligned currency states, and supersession rules. Legacy flat-file evidence carries
no state field and stays outside this model entirely — unmodeled, exactly as today, not "stale."

**Interfaces/schemas**: `manifest.json` (bundle identity + `upstream_blobs` + `dependencies.json`'s
per-dependency-class fingerprints), aligned to mission §8's "per-repository, per-stage and where
useful per-section dependency fingerprints" language.

**Failure handling**: a corrupt or unreadable manifest is a hard `BundleError`, never a silent zero
— preserved verbatim from the old repo's own design.

**Observability**: extend the existing `recheck.render_lines()`-style table output once sealing
exists, so a bundle-state table is printable the same way other evidence already is.

**Security**: no change — local evidence only, same trust boundary as the rest of this repository.

**Compatibility**: fully additive by construction (verified via `candidates.py`'s own
early-return/not-counted behavior, not merely asserted).

**Recovery**: same fail-closed discipline as `clone.py`/`propose/effect.py` elsewhere in this
project — an unreadable bundle state is an error, never guessed.

**Scale**: one `candidates/<repo>/<revision>/` directory per repository per revision; same order of
magnitude as the existing `evidence/build/` layout. No scale concern identified.

## Implementation direction (ordered, with dependencies and safeguards)

1. Port `noop_proof.py`'s bundle-independent ~460 lines first — no dependency on anything else new.
   Immediately usable to formally verify this session's own "zero new provider calls" claims
   against the *existing* `CallStore` ledger. Smallest, highest-leverage, zero migration risk.
2. Read `seal.py` in full (1,203 lines) — a real evidence gap today; must happen before any
   porting decision on it, per this project's own "verify, don't guess" discipline.
3. Port `candidates.py` (646 lines). Required safeguard: a falsifier test proving it never
   counts, reads, or invalidates any repository directory that has no `candidates/` bundle.
4. Port/adapt `seal.py` to write a sealed bundle as a new, opt-in step appended to the existing
   render pipeline (e.g. a new sibling to `scripts/run_lane_r_render.py`) — additive only, never
   replacing the existing flat-file write.
5. Align `recheck.py`'s `CURRENCY_STATES` with mission §8's full vocabulary — small, independent
   of steps 1–4.
6. Finish `recheck.py`'s five scope-runners against the new sealed format only after steps 2–4
   exist. The "reviewer" scope-runner cannot be a faithful port of the old, disqualified
   `review/independent/review.py` — it needs fresh design against this session's own
   `readme/review/independent_reviewer.py` + `defect_bridge.py`, which is new design work, not a
   port, and should be scoped as its own step when reached.
7. Only then: revisit `WIRE_GATEVERIFY_TO_PORTFOLIO`'s original ask (project/state.yaml), now that
   something real exists to wire it to.

## Verification strategy

- **Focused**: one test file per ported module (`noop_proof`, `candidates`, later `seal`), each
  re-verified against this repository's own shapes, same discipline as every other port this
  session (not a blind copy of the old tests).
- **Integration**: the full chain `REAL INPUT → run_lane_r_render.py (existing) → new seal step →
  candidates.py reader → recheck.py scope-runner → OBSERVED currency verdict`, run against one real
  repository end to end.
- **Negative control**: a deliberately corrupted `manifest.json` must raise `BundleError`, never
  silently pass — mission section 11's "a checker that accepts everything is broken" discipline,
  applied here.
- **E2E no-op proof**: run the same cascade twice, in two genuinely distinct OS processes, and
  assert `verify_noop_pair` reports zero new provider calls. This is the literal mission §8
  requirement, currently unachievable, and becomes possible after step 1 alone — it does not need
  steps 2–6 at all.
- **Rerun/idempotency**: a second seal of the same revision must no-op or correctly supersede,
  never duplicate.
- **Stale-state/invalidation**: changing exactly one dependency class (e.g. a prompt hash) must
  flip only that repository's bundle to `UPDATE_REQUIRED` (with the correct `rerender_only` vs.
  `recompose` cost split) — never a portfolio-wide reseal (mission non-negotiable #3).
- **Legacy-safety regression gate** (the most important control for the owner's own stated
  concern): a permanent test asserting `candidates.py`/`recheck.py` never emit a verdict for any
  repository directory lacking a `candidates/` bundle — the concrete guarantee that existing
  "ready for review" candidates (see `project/state.yaml`'s `owner_review_status` note) are never
  touched, reclassified, or invalidated by this work.

## Tradeoffs and risks

- **Benefits**: a real, tooling-verified no-op proof (closes the non-negotiable #6 gap); eventual
  per-repository machine-readable currency state; tamper-evident integrity; closes the gap between
  this repository's actual behavior and mission §8's own stated requirement.
- **Costs**: roughly 2,500–3,000+ lines of new porting/build work for `noop_proof.py` +
  `candidates.py` + `seal.py` + the recheck runners — and `seal.py` is still unread, so this is a
  floor, not a ceiling. Two of the five scope-runners cascade into modules already disqualified
  (`review/independent/review.py`) or recorded as "not a port candidate as a whole"
  (`validation/registry.py`); the reviewer runner specifically needs fresh design against this
  session's own new reviewer, not a port.
- **Migration risk**: LOW, *conditional* on the additive-only discipline actually holding — verified
  structurally today (`candidates.py`'s own early-return behavior), but only as long as every future
  change to this code preserves that "ignore what doesn't exist" property; a careless future edit
  could silently break it. The legacy-safety regression gate above exists specifically to catch that.
- **Compatibility risk**: LOW — no existing caller of `CallStore`, the ledger, or the currently-ported
  `recheck.py`/`evaluation.py`/`invalidation.py` needs to change.
- **Operational risk**: the new sealing step appended to the render pipeline adds a write; it must be
  checked for idempotency/collision exactly as the existing facts-persistence fix was.
- **Likely limits**: the "reviewer" scope-runner cannot be a faithful port; expect it to need its own
  short design pass when step 6 is reached.
- **Rejected alternative**: porting the *entire* old bundle system in one undertaking, as option A
  originally described it. Rejected because (a) the evidence shows caching does not need it, which
  removes the strongest urgency argument for doing it all at once; (b) `seal.py` is still unread, so
  the true scope of "all at once" is not yet known; and (c) two of the five scope-runners are blocked
  on non-portable modules regardless of how much effort goes into `candidates.py`/`seal.py`
  themselves — spending that effort before confirming the blocked runners' path forward would be
  exactly the kind of ahead-of-need, un-scoped building the owner's own 2026-10-24 directive warned
  against.

## Final assessment

**STRUCTURAL_REDESIGN_REQUIRED** — not "sound" (the no-op-proof/currency layer does not exist in any
form today) and not mere "hardening" (this is new capability, not a fix to an existing one). The
redesign is narrowly scoped, however: additive only, never replacing the proven-working caching
layer the original premise mistakenly targeted, and its single highest-leverage, lowest-risk,
zero-prerequisite first step (porting `noop_proof.py`'s process-verification code against the
already-working `CallStore`/ledger) is immediately actionable without touching anything else in
this plan.

## Step 1 execution log (2026-10-24)

**What was built**: `src/repo_presenter/core/noop_proof.py` — the bundle-independent subset of
the old repo's `core/noop_proof.py` (524 lines old; this port is ~380 lines, not ~460 as first
estimated — see correction below). Ported: `ProcessIdentity` (process identity read from the OS,
never a placeholder, Windows/macOS/Linux readings all carried over verbatim), `Invocation`
(`begin`/`run_ref`/`attach_ledger`/`document`/`write`), `InvocationRecord`/
`read_invocation_record`, `Measurement`/`measure_invocation`/`require_zero_provider_calls`,
`Verification`/`verify_noop_pair`, and the typed `NoOpProofError` reason constants. Explicitly NOT
ported (deferred to the `candidates.py` step, since they read a sealed bundle's own manifest
fields): `ledger_totals`, `reconcile_ledger`, `LedgerReconciliationError`, `LEDGER_TOTALS_MISMATCH`.

**Sizing correction**: the original estimate ("~460 of 524 lines are bundle-independent") was
close but not exact once actually ported — `ledger_totals()` itself turned out unnecessary to
port at all (not just bundle-independent-but-deferred): this repository's own
`core/llm/ledger.py::summarize()` already computes the equivalent one-sided ledger sums. Only the
narrower, per-`invocation_id` count `measure_invocation` needs was genuinely new. Net: the ported
file is smaller than first estimated, and nothing was lost by trimming it.

**Tests**: `tests/core/test_noop_proof.py`, ported from the old repo's own test file (same
fixtures: `Rerun`, `record()`, `identity()` helpers, same negative controls). 20 of the old file's
tests ported; the "reconciling totals" section (6 tests) and the two CLI/hosted-workflow tests
were dropped along with the code they exercise (no CLI command or workflow exists here yet). One
adaptation was needed and is itself worth recording: the old test's
`test_two_real_processes_have_distinct_identities_that_share_a_boot` spawns a bare `python -c
"import repository_presenter..."` subprocess, which worked in the old repo because its package
was pip-installed; this repository's `repo_presenter` is only importable via `tests/conftest.py`'s
own `sys.path.insert`, so the ported test's subprocess call needed an explicit `PYTHONPATH` env
var pointing at `src/` to import at all. All 20 pass. Full repository suite re-run clean: 1,546
passed, 0 failed, 11 skipped (the 2 CMake-toolchain failures present in some earlier runs this
session did not recur here — consistent with the earlier finding that they are an environment
flake, not a regression).

**Real integration gap found while scoping step 1 further** (not yet resolved, not yet acted on):
none of `scripts/run_lane_r_{investigation,reconciliation,planning,authoring_real,coherence,
render}.py` currently construct an `Invocation`, pass an `invocation_id` into their `Ledger`, or
write an invocation record to disk (checked directly: `Ledger(workspace / "ledger.jsonl")` is
called with no `invocation_id` argument in `run_lane_r_investigation.py`, and the two real ledgers
on disk today — `scripts/_lane_r_output/aspose-pdf-foss__Aspose.PDF-FOSS-for-TypeScript/llm_cache/
ledger.jsonl` and the aspose-words-foss/.NET equivalent — confirm every record's `invocation_id`
is `None`). This means the newly-ported `verify_noop_pair`/`measure_invocation` primitive, while
complete and correctly tested against faithful synthetic fixtures, cannot yet be exercised against
any real script run — there is nothing stamped to measure.

This was deliberately NOT fixed by wiring `Invocation` into the scripts this tick, because doing
so blind would answer a real design question by accident rather than by decision: **does one
script-run (one OS process, e.g. one `run_lane_r_investigation.py` invocation) count as one
"invocation" for no-op-proof purposes, or does one full S3-S8 cascade for one repository —
necessarily spanning several separate script processes, by this repository's own architecture —
count as one logical invocation that should be proven a no-op as a whole?** The old repo's own
model assumed a single hosted `present` process ran the entire cascade, so "one invocation" and
"one process" were the same thing there; this repository deliberately split each stage into its
own script, so they are not the same thing here, and nothing has decided which one the no-op proof
should apply to. Wiring the scripts before deciding this would likely need rework once decided.

**Next step, concretely**: before any script is touched, decide the invocation-scope question
above (owner input may be needed — this is a real design choice, not a fact to look up), then wire
`Invocation.begin()`/`attach_ledger()`/`.write()` into the chosen scope and re-run
`verify_noop_pair` against two real consecutive runs of a real repository as the first live proof
(the step 1 unit tests prove the primitive is correct; they do not yet prove it works against this
repository's actual scripts). This step comes before `candidates.py` (originally "step 3") in
practice, even though it was not named as its own numbered step in the original "Implementation
direction" list above — that list is corrected by this note, not silently superseded.

## Invocation-scope question resolved, with real production precedent now in hand (2026-10-24)

A separate, parallel investigation (triggered by the owner reporting "we completed P3 & P4 in old
repo") read the old repo's real, currently-running production workflows in full — not just its
source tree in the abstract. This surfaced the actual, proven answer to the question above:
**in production, one invocation is one whole-repository `present` command execution** — one CLI
call that runs admission, facts, composition, review, render, and sealing for one repository in
one process, invoked twice by `present.yml` (`--invocation-record first.json` / `second.json`),
gated by `repository-presenter verify-noop-proof --first ... --second ...`. This is the exact
design `core/noop_proof.py` was built for, now confirmed as a live production exercise of it, not
just a theory — strong validation that today's port (`core/noop_proof.py`,
`tests/core/test_noop_proof.py`) got the primitive itself right.

**It does not resolve the question in this repository's favor as a straight copy, and the
divergence is deliberate, not an oversight**: the old repo's "one invocation, one process" design
works because `present` is a single monolithic command. This repository has no such command —
the pipeline is six separate scripts (`run_lane_r_{investigation,reconciliation,planning,
authoring_real,coherence}.py`, `render.py` makes no LLM calls and was correctly left unwired),
each its own OS process even for a single non-rerun execution, with file-based handoffs. Mapping
the old repo's exact invocation scope onto that would require first building a
`present`-equivalent single-process orchestrator — itself a large, separate undertaking (see the
2026-10-24 P3/P4 investigation's own gap list, recorded in `project/state.yaml`'s
`GITHUB_ACTIONS_HOSTING_GAP_2026_10_24`). Decided instead, for now: keep the per-script invocation
scope already reasoned toward earlier (one `Invocation.begin()` per script run, matching
`readme/bundle/recheck.py`'s own per-scope currency model) — wired into all five LLM-calling
scripts today. This is a real, deliberate adaptation, not a blind copy of the proven old-repo
design; if a `present`-equivalent orchestrator is ever built (see the P3/P4 finding), the
invocation scope should likely be revisited to match the old repo's own proven, coarser grain at
that point, not before.

**What was actually wired, 2026-10-24**: `Invocation.begin()` at the top of each script's gateway
section, the resulting `invocation_id` passed into that script's `Ledger(...)`, and after the
job(s) complete, `invocation.attach_ledger(...)` + `invocation.write(workspace / "invocations" /
f"{invocation.invocation_id}.json", ...)`. Applied to `run_lane_r_investigation.py`,
`_reconciliation.py`, `_planning.py`, `_authoring_real.py`, `_coherence.py` — all five scripts
that make LLM calls. `render.py` makes none and needs no invocation. All five compile; full suite
re-run clean (see commit log for the exact count). This was in fact live-demonstrated shortly
after, incidentally: `LANE_R_CASCADE_COMPLETION_2026_10_24` (`project/state.yaml`) ran
`run_lane_r_authoring_real.py` and `run_lane_r_coherence.py` for real against
`aspose-words-foss/.NET`, and both wrote a real invocation record under
`llm_cache/invocations/`, proving the wiring works end to end against a live gateway call, not
just in unit tests.

## Step 2 (read seal.py in full) — done 2026-10-25, corrected from an overly pessimistic first read

**First read, from the import list alone**: seal.py (1,203 lines) imports from ~18 modules,
several of which looked immediately disqualifying — `readme/review/independent/review.py`
(disqualified, fold-bug) and `readme/validation/registry.py` (not a port candidate as a whole,
per `migration/reuse-manifest.yaml`) among them. This produced an initial, alarmed conclusion
that seal.py "cannot be ported wholesale" and would need a from-scratch redesign.

**Corrected after actually checking which imports resolve, per this project's own standing
discipline (verify, don't conclude from an import list alone)**: ran every one of seal.py's ~18
imports against this repository's real `src/`, under the project's own interpreter (not a bare
system Python missing `pydantic`/`jsonschema`/`markdown_it` — the first check run used the wrong
interpreter and produced false "module missing" results, caught and redone). The real result is
far better than the first read suggested:

- **Already present and resolve cleanly, no action needed**: `readme/bundle/invalidation.py`
  (`STATE_INVALIDATED`/`STATE_UPDATE_AVAILABLE`/`ScopeError`/`route`), `readme/composition/
  authoring.py`'s `NORMALISATION_VERSION`, `readme/composition/components/shell.py`'s
  `SHELL_VERSION`, `readme/composition/policy.py` (`POLICY_VERSION`/`policy_packet`),
  `readme/composition/renderer.py`'s `RENDERER_VERSION`, `readme/evidence/facts/inherited.py`'s
  `INHERITED_UNITS_VERSION`, `extractors/surface/extractor.py`'s `EXTRACTOR_VERSION`,
  `core/llm/jobs.py`'s `CallStore`, `core/llm/ledger.py` (`LEDGER_FILENAME`/`canonical_hash`/
  `parse_records` -- `parse_records` specifically was not known to exist before checking),
  `core/llm/prompts.py`'s `PromptRegistry`, `core/registry/models.py`'s `RegistryEntry`,
  `core/secrets.py` (`ConfiguredSecret`/`scan_for_secrets` -- `scan_for_secrets` not known to
  exist before checking), `core/toolchains.py`'s `toolchain_fingerprint`.
- **Genuinely missing, small**: `readme/composition/authoring.py`'s `RAW_CALLS_FILENAME`
  constant (trivial to add); `core/noop_proof.py`'s `LedgerReconciliationError`/`ledger_totals`/
  `reconcile_ledger` (exactly the bundle-manifest-reading subset step 1 deliberately deferred --
  confirmed correctly deferred to exactly this point, not missed); `core/snapshot/capture.py`
  (167 lines, whole module not ported -- previously deferred alongside `clone.py`, which has
  since been ported and live-exercised; capture.py itself was never circled back to).
- **Genuinely missing, needs a decision, not a mechanical port**: `core/candidates.py` (the
  planned step 3 itself, expected); `readme/review/independent/review.py`'s
  `REVIEWER_LOGIC_VERSION` and `readme/validation/registry.py`'s `VALIDATOR_VERSION`/
  `BLOCKING_CHECKS`/`record_replay_verdict`. Read what these actually are, not just their
  names: `REVIEWER_LOGIC_VERSION`/`VALIDATOR_VERSION` are plain version-number strings (`"21"`,
  `"23"`) -- fingerprints of which mechanism version produced a bundle, for invalidation-scope
  purposes (mission §8), not logic to port. `record_replay_verdict` is 15 lines that overwrite
  one specific check's (`"BC-11"`, the no-op-proof check itself) verdict to `PASS` after a
  successful replay, on a `validation.json`-shaped document this repository has no equivalent
  of (its own checks run inline during authoring/coherence, never consolidated into one
  artifact). None of this needs the disqualified modules' actual logic -- it needs this
  repository's OWN version constant for `independent_reviewer.py` (does not exist yet) and an
  equivalent small patch function for whatever this repository's own no-op-proof record ends up
  being, once that exists.
- **A real, newly-discovered gap seal.py's own `REQUIRED_ARTIFACTS` tuple surfaces**:
  `REQUIRED_ARTIFACTS` includes `validation.json` and `review.json` -- this repository produces
  neither. `readme/review/independent_reviewer.py::review_candidate` returns a `ReviewVerdict`
  object that is never persisted to disk per repository (only a portfolio-wide aggregate,
  `evidence/build/P2_REAL_ENGINE_SALVAGE/independent_review_report.json`, exists). Sealing a
  bundle meaningfully needs a per-repository review-verdict artifact that does not exist yet --
  this is new, genuinely needed work, not a port of anything.

**Revised sizing**: seal.py is substantially MORE portable than the first read suggested. The
real remaining gap before it could be adapted is: port `capture.py` (167 lines); port the 3
deferred `noop_proof.py` functions (small, already fully understood from step 1's own reading);
add a `RAW_CALLS_FILENAME` constant; design (not port) a small `independent_reviewer.py` version
constant and a per-repository persisted review-verdict artifact; THEN adapt seal.py's own logic
against this repository's real `REQUIRED_ARTIFACTS` shape (`facts.json`, `dispositions.json`,
`plan.json`, `content_units.coherent.json`, `README.coherent.md`, `llm_cache/ledger.jsonl`,
`llm_cache/invocations/*.json`, plus the new review-verdict artifact) -- not the old repo's own
`validation.json`/`review.json` shape, which this project does not and should not replicate.

**Deliberately not started this tick**: none of the above was built. This is the planning pass
the owner's own "plan carefully before building from scratch" directive asks for, applied to a
genuinely large remaining piece -- recorded precisely so the next session does not have to
re-derive it, and does not inherit the first read's overly pessimistic (and wrong) conclusion.

## seal.py's full read, 2026-10-25 — adaptation is blocked, not just unplanned

Read seal.py's full 1,203 lines (step 2 above only checked its import list). Two concrete,
previously-unconfirmed reasons its adaptation is blocked on the same orchestrator decision
`GITHUB_ACTIONS_HOSTING_GAP_2026_10_24` already flags, not an independently schedulable design
task:

1. `seal_candidate()`'s whole I/O model assumes one `transaction: Path` — a single staging
   directory holding every artifact for one repository's one cascade run together. This
   repository's real evidence is deliberately split across `scripts/_lane_r_output/<repo>/`
   (render output) and `evidence/build/<phase>/<repo>/` (facts/handoffs) — a chosen architecture,
   not an oversight a path-remapping adapter should paper over.
2. More seriously: `seal_candidate()`'s no-op-proof model (`measure_invocation`/
   `reconcile_ledger` against `inputs.transaction / LEDGER_FILENAME`) needs exactly one ledger
   per sealed transaction. This repository's own 2026-10-24 invocation-wiring decision
   deliberately wired FIVE separate `Invocation`/`Ledger` pairs per repository cascade — one per
   script — precisely because no present-equivalent single process exists. There is no single
   "the ledger" to point seal.py's proof at.

Full detail: `project/state.yaml`'s `PORT_BUNDLE_INTEGRITY_LAYER` step_6 and
`docs/DECISION_LOG.md`'s 2026-10-25 entry. Not started this tick, correctly: this needs the
owner's orchestrator decision first.
