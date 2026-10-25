# Decision log

A running record of architectural/scope decisions this project has made that are not fully
captured by a single commit message, so they are not re-litigated or forgotten. Authority:
subordinate to `AGENTS.md`'s table — this file records decisions, it does not grant any authority
of its own. The live execution cursor for any decision here is `project/state.yaml`, never this
file.

Format per entry: date, decision, why, what it does NOT decide, where the detail lives.

---

## 2026-10-24: Port the old repo's no-op-proof/bundle-integrity layer additively; correct the premise that caching depends on it

**Decision**: build a new, additive no-op-proof + bundle-integrity + currency layer in this
repository, modeled on the old repository's `core/noop_proof.py` / `core/candidates.py` /
`components/readme/bundle/seal.py`, but introduced only for *future* cascades — never retroactively
applied to, or capable of invalidating, any already-produced candidate. Full assessment, target
design, and ordered implementation plan: `plans/PLAN_bundle_integrity_and_noop_proof.md`.

**Why**: the owner observed the old repo's sealed-bundle architecture (manifest + `CURRENT` pointer
+ dependency fingerprints + a lifecycle state machine) looks more traceable and accountable than
this repository's current flat-file evidence layout, and asked for a deep, first-principles
assessment before committing to a port. That assessment (a dedicated research pass against both
repositories' actual code, not from memory) found:

- The owner's specific premise — that the old repo's "zero new provider calls" caching is *driven
  by* the sealed-bundle format — is **not correct**. Caching is implemented by `core/llm/jobs.py`'s
  `CallStore` (a flat, content-addressed file cache keyed by request hash), which has **already
  been ported** into this repository and is **already working** (this session already found and
  fixed the one real bug in it — a throwaway `tempfile.mkdtemp()` workspace discarding the cache
  every run; see `project/state.yaml`). `CallStore` has no dependency on the bundle/manifest
  format in either repository's actual code.
- What the old repo's bundle layer genuinely provides, with **no equivalent in this repository
  today**, is real and worth building: a formal, process-independent no-op proof
  (`verify_noop_pair`/`measure_invocation`), tamper-evident bundle integrity, and a durable,
  machine-readable per-repository `CURRENT`/currency state — the exact vocabulary mission §8
  requires (`CURRENT, RECHECKED_CURRENT, UPDATE_OPTIONAL, UPDATE_REQUIRED, UNVERIFIED_SOURCE,
  UNVERIFIED_CHECK, INVALID_FACT, BLOCKED_EFFECT`), which this repository's current partial port of
  `readme/bundle/recheck.py` does not yet fully match either (a separate, smaller correction, not
  contingent on the rest of this decision).
- The old repo's `candidates.py` reader is structurally safe to introduce additively: verified
  directly that it silently does not count, read, or judge any repository with no `candidates/`
  bundle tree — the "never invalidate already-accepted candidates" requirement is a property of the
  code as written, not something that needs to be bolted on separately.

**What this does NOT decide**: it does not approve porting the *entire* old bundle system in one
undertaking (the original, broader "option A"). The plan explicitly narrows scope: port the
no-op-proof primitive first (smallest, zero-prerequisite, immediately useful against the
already-working cache); read the bundle writer (`seal.py`, 1,203 lines, not yet read at all) before
deciding how to port it; and treat the "reviewer" scope-runner as new design work against this
session's own `readme/review/independent_reviewer.py`, not a port of the disqualified old module.
It also does not change or re-port `CallStore`/the ledger — those are correct as they stand.

**Where the detail lives**: full evidence-cited assessment, target architecture, ordered
implementation steps, and verification strategy — `plans/PLAN_bundle_integrity_and_noop_proof.md`.
Live tracking card — `project/state.yaml`'s `PORT_BUNDLE_INTEGRITY_LAYER`.

---

## 2026-10-24: The old repo's P3/P4 (hosted GitHub Actions, GitHub App, issue/PR automation) is real, live production — not just documented; issue filing moves to a committed-approval model

**Decision**: (1) treat the old repo's `.github/workflows/`, GitHub App identity, and issue/PR
automation as real, salvageable, proven infrastructure — not a design reference to rebuild from
scratch; (2) adopt the old repo's real approval-gated issue-filing model going forward, replacing
this repository's own interim "draft a markdown file, wait for a chat go-ahead" pattern; (3) flag
an operational risk to the owner rather than deciding it unilaterally.

**Why**: the owner stated "we completed P3 & P4 in old repo" and asked if that work could be
reused, and separately ruled that issue filing should no longer need a human to file each one,
citing the old repo's system as "tested and proved." A dedicated investigation (read-only,
verified via `gh run list`/`gh api` against the real `babar-raza/repository-presenter` remote —
not narration) found:

- **GitHub Actions hosting is real and currently running.** 13 workflow files exist; several
  (`Liveness`, `Monitor`, a daily `Sealing` job, a daily `Upstream issues` job) show
  `completed success` runs through **2026-10-24T11:34:11Z — today, during this session.**
  `present.yml` and `propose.yml` both have real successful `workflow_dispatch` runs.
- **The GitHub App identity is confirmed real, not a placeholder.** The real open PR this
  automation produced (`aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp#7`) is authored by
  `repository-presenter[bot]`, `is_bot: true` — exactly `EXPECTED_APP_SLUG` in this repository's
  own `token_provenance.py`, now corrected from "unconfirmed placeholder" to "confirmed real."
  It is the same App (installed on the target upstream repos, not on either supervisor's own
  checkout), so there is no reason for this repository to register a new one.
- **Issue filing is real and autonomous, but not human-free.** `.github/workflows/
  issues-scheduled.yml` gates filing on a committed per-defect approval record
  (`ops/issue_approvals/<handoff_id>.json`: evidence digest, approver, approved/expires
  timestamps) existing and matching the finding's evidence digest. Once that one committed
  approval exists, the scheduled, capped job files and closes autonomously with no further
  human step. **The owner's premise that no human step remains was corrected, not just
  accepted**, per mission non-negotiable #7 (observations, not claims): one committed approval
  per defect is still real and required — that is the model being adopted, not a looser one.
- **Real filed issues are extensive** (e.g. 5 on one repository, 3 on another — far more than
  this repository's own "1 filed" count, because that count is this repository's own history,
  not the shared upstream portfolio's).
- **The old repo's daily "Sealing" workflow is the live production backbone of the exact
  sealed-bundle architecture** the separate `PORT_BUNDLE_INTEGRITY_LAYER` decision above is
  porting from source — a running reference implementation exists, not just old code.

**Operational risk flagged, not resolved here**: the old repo's hosted automation is continuing
to file real issues and open real PRs against the same upstream portfolio this new repository is
being built to eventually replace, concurrently with this session's own work. Whether to let it
keep running unattended or pause it first is an operational decision for the owner, not an
engineering one — not decided or acted on in this entry.

**What this does NOT decide**: it does not port all 13 old workflows at once (mission §12: "one
small vertical slice on GitHub Actions before broader automation" applies here too); it does not
independently re-verify `EXPECTED_APP_ID`'s numeric value (no app-level JWT access in the
investigation's environment — slug confirmed, numeric id not); it does not resolve the
operational-risk question above.

**Where the detail lives**: `project/state.yaml`'s `GITHUB_ACTIONS_HOSTING_GAP_2026_10_24` (full
finding, salvage decision, ordered next steps) and `DECIDE_NEXT_ISSUE_FILINGS` (the issue-filing
adoption decision); `docs/MISSION_AUTHORITY.md`'s "Upstream defect reporting" bullet (the binding
product-requirement correction); `src/repo_presenter/github/token_provenance.py` (the corrected
App-identity docstring); `plans/idea.md`'s top annotation (the pointer from the still-verbatim
old product-requirements text to this ruling).

---

## 2026-10-24: Correcting the GitHub Actions salvage sizing after reading the real workflows and CLI in full; resolving the no-op invocation-scope question with real production precedent

**Decision**: correct the same-day earlier framing ("adapt proven workflow definitions, a
materially smaller task") after actually reading all six core old-repo workflows and the CLI
they call in full. The real gap is a missing single-process orchestrator (the old repo's
`present` command), not a YAML-adaptation exercise. Separately: wire `core/noop_proof.py`'s
`Invocation` into this repository's five LLM-calling scripts now, at the per-script scope
already reasoned toward, rather than wait to match the old repo's own proven (but structurally
incompatible) per-whole-pipeline scope.

**Why**: a follow-up investigation (same research thread as the earlier same-day P3/P4 finding,
continued rather than restarted, read-only, `gh`/file-verified) read `present.yml`, `propose.yml`,
`issues-scheduled.yml`, `sealing-scheduled.yml`, `monitor.yml`, `liveness.yml` in full, plus the
CLI they call (`src/repository_presenter/cli.py`, 4,828 lines, ~30 subcommands). Found:

- `present.yml`'s entire design assumes ONE command (`repository-presenter present`) runs the
  whole per-repository pipeline in one process, invoked twice for the no-op proof. This
  repository's six separate scripts (`run_lane_r_{investigation,reconciliation,planning,
  authoring_real,coherence}.py`) have no equivalent — there is no single call that could be
  invoked twice the same way.
- Durable state across ephemeral runners (mission §9's own requirement) uses three distinct real
  mechanisms in the old repo — a dedicated git-ref namespace
  (`refs/repository-presenter-state/records/...`) for sealed bundles, Actions artifacts for
  monitor evidence, and the Actions API itself for sealing cooldown history — none of which this
  repository has any equivalent of.
- The GitHub App is confirmed the *same* one this repository's `token_provenance.py` already
  names (provisioned via a real one-time manifest-flow registration,
  `tools/github_app/{manifest.json,register.html,register_exchange.py}`) — no new App
  registration needed if this project keeps using it.
- Toolchain-provisioning steps in `present.yml` (dotnet/JDK/Node/Go/Rust/g++/cmake/ninja) are
  directly portable as-is, independent of everything else.

**Invocation-scope resolution**: the old repo's real precedent answers the question
`plans/PLAN_bundle_integrity_and_noop_proof.md` left open after step 1 (one invocation per
script-run vs. one per whole cascade) — in production it's the latter, one invocation per whole
`present` call. Decided NOT to copy that scope directly: building a `present`-equivalent
orchestrator is itself the large undertaking named above, and forcing today's wiring to wait for
it would block real progress on a separate, already-scoped decision. Kept the per-script scope,
wired `Invocation.begin()`/`attach_ledger()`/`.write()` into all five LLM-calling scripts today.
If a `present`-equivalent orchestrator is ever built, the invocation scope should likely be
revisited to match the old repo's own proven, coarser grain then — not before.

**What this does NOT decide**: whether to build the `present`-equivalent orchestrator (large) or
adapt workflows to the six-script shape (smaller, diverges from proven design) — both remain open,
named as the next real decision in `project/state.yaml`'s `GITHUB_ACTIONS_HOSTING_GAP_2026_10_24`.
Does not re-verify whether a sealed bundle's durable commit target would be the working tree or
the dedicated git-ref namespace found here — flagged as a re-check needed before
`core/candidates.py` is ported (`PORT_BUNDLE_INTEGRITY_LAYER` step 3). Does not live-demonstrate
`verify_noop_pair` against a real script run (no fresh clone was available in this environment;
deferred to the next real cascade run rather than fabricated).

**Where the detail lives**: `project/state.yaml`'s `GITHUB_ACTIONS_HOSTING_GAP_2026_10_24`
(corrected salvage sizing, full CLI/gap findings) and `PORT_BUNDLE_INTEGRITY_LAYER` (the
invocation-wiring record); `plans/PLAN_bundle_integrity_and_noop_proof.md`'s "Invocation-scope
question resolved" section (full reasoning).

---

## 2026-10-25: seal.py's adaptation is blocked on the orchestrator decision, not an independent planning task

**Decision**: do not attempt to adapt `readme/bundle/seal.py` against this repository's real
artifact shapes yet. A full read of its 1,203 lines (not just its import list, already checked
2026-10-25) found two concrete reasons its adaptation is blocked on the exact same undecided
question `GITHUB_ACTIONS_HOSTING_GAP_2026_10_24` already named `BLOCKED_NEEDS_OWNER_DECISION`
(build a `present`-equivalent single-process orchestrator, or not): (1) `seal_candidate()`'s
entire I/O model assumes one `transaction: Path` — a single staging directory holding every
artifact for one repository's one cascade run together — which this repository's deliberately
split evidence layout (`scripts/_lane_r_output/<repo>/` vs. `evidence/build/<phase>/<repo>/`)
does not have; (2) more seriously, `seal_candidate()`'s whole no-op-proof model needs exactly one
ledger per sealed transaction, but this repository's own 2026-10-24 invocation-wiring decision
deliberately wired five separate per-script ledgers instead, precisely because no
present-equivalent single process exists yet to hold one. Did build and commit, independently of
this finding, the smaller pieces that remain useful regardless of how the orchestrator question
resolves: `core/snapshot/capture.py`, `noop_proof.py`'s ledger-reconciliation functions, the
`RAW_CALLS_FILENAME` constant, and a new `REVIEWER_LOGIC_VERSION` + persisted
`review_verdict.json` artifact for `independent_reviewer.py`.

**Why**: the owner's own "plan carefully before building from scratch" directive. Adapting
seal.py around a transaction/ledger shape that does not exist here would mean either quietly
assuming the orchestrator already exists (it does not) or inventing a new, undesigned multi-ledger
aggregation mechanism unasked — exactly the kind of unplanned from-scratch build that directive
warns against.

**What this does NOT decide**: whether to build the `present`-equivalent orchestrator or redesign
the no-op proof for multiple per-script ledgers instead — both remain open, as
`GITHUB_ACTIONS_HOSTING_GAP_2026_10_24` already says. Does not touch `core/candidates.py`, which
is blocked the same way (that card's own next_step (3) already said so).

**Where the detail lives**: `project/state.yaml`'s `PORT_BUNDLE_INTEGRITY_LAYER` (`step_6_done_
2026_10_25_seal_py_adaptation_is_blocked_not_just_unplanned`) and `GITHUB_ACTIONS_HOSTING_GAP_
2026_10_24` (`confirmed_independently_2026_10_25`); `plans/PLAN_bundle_integrity_and_noop_proof.md`.

---

## 2026-10-25: Owner decision — build the present-equivalent orchestrator

**Decision**: the owner was asked directly (three cards — `GITHUB_ACTIONS_HOSTING_GAP_2026_10_24`,
`PORT_BUNDLE_INTEGRITY_LAYER`, `WIRE_GATEVERIFY_TO_PORTFOLIO` — all converge on this one blocker)
how to resolve the missing single-process orchestrator. The owner chose: build the
present-equivalent orchestrator — one process wraps the six existing scripts end to end for one
repository, matching the old repo's proven design exactly (one `Invocation`/`Ledger`, one
`transaction` directory), over redesigning the no-op proof for multiple per-script ledgers, and
over deferring further.

**Why**: this also unblocks the GitHub Actions hosting gap (mission non-negotiable #1), and the
components it wraps (composition, review via `independent_reviewer.py`, render) already exist and
are proven — this is wiring, not new invention, per `GITHUB_ACTIONS_HOSTING_GAP_2026_10_24`'s own
next_step note.

**What this does NOT decide**: the orchestrator's exact internal shape (a new script vs. a CLI
subcommand vs. a library function multiple callers use) — that is this session's own next planning
pass, recorded in `project/state.yaml`'s new `BUILD_PRESENT_EQUIVALENT_ORCHESTRATOR` card.

**Where the detail lives**: `project/state.yaml`'s `BUILD_PRESENT_EQUIVALENT_ORCHESTRATOR`.
