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

---

## 2026-10-26: A premature RETIRE classification almost lost real salvageable product logic

**Decision**: correct `migration/reuse-manifest.yaml`'s disposition for the old repo's
`core/state/{cas,git_backend,health,recovery,schema,trigger}.py` (1,666 of 2,122 lines) from
`RETIRE` to `PENDING_REVIEW_FOR_PORT`. These six files, plus `present_transaction.py` (already
`PENDING_REVIEW`), are a real, production-proven 23-state repository-transaction machine — crash
recovery, trigger deduplication, and lease/fencing-token worker coordination across ephemeral
GitHub Actions runners, backed by a real git-ref CAS store (one ref per repository, written via
pure plumbing commands). This is exactly mission section 9's own "durable state across ephemeral
runners" requirement, and mission non-negotiable #1 (a hosted GitHub Actions system) cannot be
honestly satisfied without something like it.

**Why**: the owner's own 2026-10-26 instruction — before any "replace the old repo" step, confirm
everything needed has genuinely been salvaged, and keep `plans/*.md` in scope rather than taking
"this repo has produced everything we need" at face value. A direct re-check found these six files
had been marked `RETIRE` by name-pattern match alone ("core/state" sounds like supervisor-cursor
plumbing, already superseded by `project/state.yaml` per `docs/MISSION_AUTHORITY.md`'s own mapping
table) — never actually read. That mapping is correct for the old repo's own retired Level-8
*mission graph* (a build-time supervisor concept); it has nothing to do with this subsystem, which
is *runtime*, per-repository transaction state for a hosted product. Reading all seven files in
full confirmed they are real product logic, not retired plumbing — and `core/retry.py`'s own
`RETRY_POLICIES` already carries a `"state_cas"` policy key, added in this repository's very first
salvage commit (2026-10-21) with a comment naming `core/state/cas.py` explicitly: this need was
anticipated early and then dropped, not newly invented today.

**What this does NOT decide**: when to actually port this subsystem (tracked as
`GITHUB_ACTIONS_HOSTING_GAP_2026_10_24`'s own next-step prerequisite, ordered dependency plan in
the manifest's own entry) or how the hosted vertical slice itself is built. Does not retroactively
change any already-sealed candidate — nothing here was ever pulled, so nothing else depends on it.

**Where the detail lives**: `migration/reuse-manifest.yaml`'s own corrected entry;
`project/state.yaml`'s `GITHUB_ACTIONS_HOSTING_GAP_2026_10_24`
(`major_correction_2026_10_26_durable_state_backend_was_wrongly_marked_retire`).

## 2026-10-27: Independent LLM reviewer, Phase 1 (pure-code core): clarifications to plan D1-D5

**Decided / clarified** (`plans/PLAN_independent_llm_reviewer.md` stays the design; these are the
places Phase 1 had to choose where the plan was silent or ambiguous):

1. One typed claim per finding. D2 says a finding is cleared only if "every typed field it declares"
   is disproved. A single `Clearance` per finding cannot prove two fields, so the contract (D4)
   requires `claim_kind` to name the one typed field the finding fills and refuses a finding that
   fills another; two typed claims are two findings. Non-typed kinds (`contradiction`,
   `unsupported_claim`, `quality`) fill none, so a quality complaint cannot be dressed as an absence.
2. Clearances err toward blocking. Presence is strict (exact text, case-sensitive, whole-token,
   inside the named section; an unlocatable section never clears); "is it in the evidence" is lenient
   (Markdown stripped, case-folded) so uncertainty keeps the finding standing. Strings under three
   characters, a string the finding quotes itself, a multi-word "name", and a cited non-SUPPORTED
   fact all leave a finding BLOCKING. A bundle of both present and unsourced strings is in neither
   `absence_present` nor `absence_unsourced` and keeps blocking (the old repository's combined
   "settled" ruling is not ported). `names_supported` is equality only; a bare member name is not
   resolved through a dotted symbol's tail.
3. The quote check tolerates Markdown syntax and ellipsis fragments (the old repository measured
   three real failures from stricter matching) but not case changes, paraphrase, the 80-character
   anchor, or a quote scoped to the wrong section.
4. A deterministic-only verdict (no model asked) still folds to ACCEPT when nothing blocks, so the
   existing cascade is unchanged, but `ReviewVerdict.model_reviewed` is False and
   `review_verdict.json` records `model_verdict: null`. Phase 2 must make "a model reviewed this" a
   precondition of sealing and of the `present.py` gate (D4: a run with no valid review cannot be
   sealed).
5. Schema-1 `judgment` findings (never produced by any shipped rule) do not load under schema 2.

**What this does NOT decide**: the packet, prompt v15 wording, the model route, cascade stage S10, or
repair routing (Phase 2); calibration thresholds (Phase 3). No existing candidate is invalidated: the
reviewer scope re-checks sealed content (`REVIEWER_LOGIC_VERSION` 3 -> 4), it regenerates nothing.

**Where the detail lives**: `src/repo_presenter/readme/review/{findings,clearances,reply,verdict,verdict_io,matching}.py`;
`tests/readme/review/test_{clearances,review_contract,review_invariants}.py`;
`migration/reuse-manifest.yaml` (`p1_core_2026_10_27`).

---

## 2026-10-27: Independent LLM reviewer, Phase 2 (the job, stage S10, the gates): clarifications to plan D1-D8

**Decided / clarified** (`plans/PLAN_independent_llm_reviewer.md` stays the design; the places Phase 2
had to choose where the plan was silent, plus one amendment):

1. Amendment to D2, found by Phase 1: a finding carries ONE typed claim, so two claims are two
   findings. Prompt v15 says so, and the call schema (`readme/review/packet.py::review_schema`)
   narrows each finding to its `claim_kind`'s own shape: `claim_kind` plus exactly the typed field
   that kind needs (`absent`, `unsupported_names` or `omission`) and no other. The manifest schema
   keeps the typed fields optional so a stored reply is judged by the wider schema on replay.
2. Prompt v15 removes the advisory tier (a finding without a section or stage blocks, stage
   `unclear`), removes the sentence that made a quote containing a SUPPORTED fact value "supported
   by definition" (D3: not a clearance), and keeps the mechanical quote / absent / unsupported_names
   / omission contract. `model_route` is `gpt-oss` (D6), recorded as PROVISIONAL on the D9 calibration
   gate; a test pins that the reviewer's route differs from every authoring job's.
3. Evidence only (D6c): the packet drops every `rationale` / `reason` field the planner and the
   reconciler attached to a decision. The two READMEs are wrapped in begin/end lines carrying the
   SHA-256 of the wrapped text, so the text cannot contain its own closing line; facts and
   dispositions are declared evidence, not instructions. The wrapped text is the README byte for
   byte; the contract checks quotes against the raw candidate.
4. Stage S10 runs when S9 leaves no deterministic finding AND no failing blocking check (BC-xx):
   a failing blocking check is a deterministic rejection in the sense of D7, though it is not in
   `ReviewVerdict`. Consequence to watch: a candidate with a persistent BC failure is never sent to
   the model and, being unreviewed, never seals. It used to seal on the deterministic verdict alone.
5. Provider calls per review: one when the first reply is valid, two with the one re-ask (`run_job`
   with no `narrow` or `recover`), none on a call-store replay (the verdict is rebuilt from the
   stored reply; the model served is read back from the store). A transport retry of one attempt
   is its own counted call. Each repair round adds its repair calls, the re-asked downstream
   stages and one re-review.
6. Repair routing: blocking findings go through `defect_bridge.build_defects` (which now hands the
   repair the finding's text, instruction and typed claim, not only its quote) into
   `repair_defect`, at most `review_repair_rounds` (default 2) rounds; one fingerprint is attempted
   once, so a finding that returns after its repair is recorded re-raised and the candidate is
   BLOCKED with `llm_review.blocked_predicate`'s exact text. `repair.loop.settle_candidate`, which
   owns its own rounds, passes `review_repair_rounds=0`.
7. `ReviewUnavailable` (second invalid reply, or a provider unreachable through the bounded
   transport retries) propagates out of `run_cascade`; `present.run_present` records it as a
   transient failure and seals nothing. `present._cascade_and_seal` refuses any verdict whose
   `model_reviewed` is False, and `propose.effect` refuses an unreviewed ACCEPT too, so a
   deterministic-only verdict can neither seal nor be proposed.

**What this does NOT decide**: calibration thresholds, the corpus and whether `gpt-oss` keeps the
route (Phase 3); whether a 6000-token output budget suffices for a reasoning model (unmeasured; a
`finish_reason: length` is a hard `JobError`, not a retry); the packet's size on a large surface
(facts keep the existing symbol bounds and `symbol_index` is capped at 1500 values). No sealed
candidate is invalidated: a reviewer prompt, model or logic change reaches only the `reviewer` scope
(asserted in `tests/readme/review/test_llm_review.py`).

**Where the detail lives**: `src/repo_presenter/readme/review/{packet,llm_review}.py`,
`src/repo_presenter/cascade.py` (`_settle_s9`, `_review_defects`, stage S10),
`prompts/independent_review.yaml`; `tests/readme/review/test_llm_review.py`,
`tests/test_cascade_s10.py`, `tests/test_present_review.py`; `migration/reuse-manifest.yaml`
(`p2_job_2026_10_27`).

---

## 2026-10-27: Independent LLM reviewer, Phase 3 (calibration): the gate FAILS, and why

**Decided / found** (`plans/PLAN_independent_llm_reviewer.md` D6, D9 V4-V6; the numbers and raw data are
in `docs/investigations/2026-10-27-independent-reviewer-calibration.md` and its `-data/` directory):

1. The calibration corpus, the mutation operators, the metrics harness and the live adapter are built
   (`src/repo_presenter/readme/review/calibration/`, `scripts/run_reviewer_calibration.py`, 75 tests). The
   always-accept and always-reject stubs fail the corpus gate by test; an oracle passes it. A
   catch is scored only when a blocking finding mentions the defect (`Case.targets`): a REJECT for an
   unrelated reason is not a catch, and 6 of gpt-oss's 11 scored rejections were of that kind. The
   plan's literal "any rejection" recall is reported beside it.
2. Live, 165 ledger-counted calls (8 probe, 157 calibration; the cap was 8 and 200). Answers: the
   per-kind `oneOf` call schema is accepted by the gateway (no flattening, `packet.py` unchanged);
   `max_output_tokens: 6000` is NOT enough for gpt-oss (2 of 99 replies hit the ceiling, 23 exceeded
   4000); first replies were JSON- and schema-valid 100% of the time but contract-valid only 46% for
   gpt-oss and 36% for qwen3-next; the packet is 65,000-81,000 prompt tokens.
3. **Gate result: FAIL** for gpt-oss and for qwen3-next. gpt-oss, reviewer alone and on target: recall
   0.40 contradiction, 0.00 content loss, 0.00 unsupported claim, 0.00 broken install (targets 0.90);
   false-reject 0.00 on 2 answered clean twins (limit 0.10); JSON-valid first reply 1.00; stability 0.20
   on 5 cases (target 0.90), 54% of reviews unavailable. qwen3-next: false-reject 0.67 and worse recall.
   The pipeline as a whole passes content loss and broken install only because the deterministic stage
   catches them first. No rule, clearance, threshold or prompt was changed to improve these numbers.
4. Findings that are decisions for later cards, each needing its failing test first: (a) D4 requires a
   factuality finding to cite a product fact, but an `unsupported_claim` has none to cite (24 of 27
   product-fact errors were an honest `unsupported_claim` with empty `fact_ids`), so the plan's own
   motivating class is unreachable; (b) gpt-oss returns empty content to the re-ask in 26 of 27 cases,
   because of the `[system, user, assistant, user]` shape in `core/llm/jobs._re_ask`, shared by every
   job (a single user message returned content 3 of 3); (c) the models cannot reliably copy a quote
   verbatim into the named section: re-labelling the section by code fixes 6 of 32 invalid gpt-oss
   replies, so the remedy is to have code derive the quote and section from cited line numbers.
5. Route: `model_route: gpt-oss` stays PROVISIONAL and is NOT confirmed. It remains the better of the
   two on precision (D6a independence is the reason to keep it), but the route exception of D6 (fall
   back to qwen3-next with a stronger deterministic holdout) is also not warranted on this evidence:
   qwen3-next false-rejects clean candidates with unclearable `quality` findings and shares the authors'
   blind spots. No cohort or PR work should read the reviewer's verdict until the re-measurement of
   item 4 passes the same corpus.

**What this does NOT decide**: whether any amendment of item 4 is accepted (supervisor decision, with
a blast-radius query for (b)); the final corpus size (3 vetted clean twins and 5 repeat cases are too
few for a trustworthy gate reading; the plan's 4 clean twins were not reachable because no complete
python candidate passes S9 today); anything about Lane L; the budget for the next live pilot.

**Where the detail lives**: `docs/investigations/2026-10-27-independent-reviewer-calibration.md`,
`docs/investigations/2026-10-27-reviewer-calibration-data/`, `migration/reuse-manifest.yaml`
(`p3_calibration_2026_10_27`).

---

## 2026-10-27: Independent LLM reviewer, Phase 3b (the four fixes and the second measurement): still FAILS

**Decided / found** (details, tables and raw data: `docs/investigations/2026-10-27-reviewer-calibration-iteration-2.md`):

1. Owner decision, binding, overrides plan D6a: one model, qwen3-next, for the whole system. The reviewer
   routes to it (prompt v16) and the manifest says it is NOT model independence; independence rests on a
   separate job, prompt and ledger attribution, the evidence-only packet, untrusted-data delimiting,
   temperature 0 with a fixed seed, and deterministic holdouts. The withdrawn model id is gone from `src/`,
   `prompts/`, `scripts/`, `tests/` and `.github/` and `tests/test_withdrawn_model.py` keeps it out. Cost: the
   five authoring manifests' `route_rationale` was reworded, which changes their file hash and therefore
   the `prompts.<job>` dependency (authoring scope) of any sealed bundle; this is consumed-scope invalidation
   by design and nothing was regenerated here.
2. D4 amended: a `contradiction` cites a product fact; an `unsupported_claim` and a `quality` finding cannot
   (24 of 27 iteration-1 fact errors were an honest unsupported claim with no fact), so the contract asks for
   what is checkable, the cited text. The model cites candidate lines and code derives the quote and the
   section (`resolve_cited_lines`); the call schema has no `quote`. **No clearance was added** for
   unsupported claims: term overlap with SUPPORTED facts cannot prove a claim supported (the 27-of-30
   incident), the structural test that no clearance reads a quote against a fact stays, and a mechanical audit
   of the claim's distinctive terms is recorded as the finding's `evidence` and decides nothing.
3. A `quality` finding against renderer-owned text (every deterministic section and At a Glance) is a
   reviewer scope error: the reply is invalid (re-ask, then `ReviewUnavailable`). It demotes nothing.
4. Re-ask shape: blast-radius query done (the store key is the first request's hash; 28 stored outputs and 206
   ledger rows in the repository, none keyed by a re-ask payload). `reask_shape: single_user` exists as a
   per-manifest option, default unchanged, and is not enabled: its motivation was the withdrawn model.
5. `max_output_tokens` 9000 (headroom; qwen3-next peaked at 2452). `REVIEWER_LOGIC_VERSION` 4 -> 5, reviewer
   scope only (asserted).
6. The no-re-roll invariant is enforced: `RerollRefused` when a request with a blocking verdict has no stored
   reply; structural tests pin the API (no bypass parameter, two callers, the fresh-store code only in the
   calibration adapter). Limit, stated: the guard lives beside the call store, so a wholly new store is not seen;
   production builds the store from the transaction directory.
7. The harness skipped java/go/cpp/rust/typescript only because it did not call `plugin_for`; fixed. It
   yielded mutant bases in java and typescript, but still 3 clean twins: every Lane R base's own twin trips a
   deterministic rule (`live_readme_loss`) and is kept as an unscored twin.
8. Measurement, 121 of the authorised 150 calls (cap 200), 0 to the withdrawn model, qwen3-next: recall
   (reviewer alone, on target) contradiction 0.36, content loss 0.00, unsupported claim 0.25, broken install
   0.50 (target 0.90, all FAIL); false-reject 0.33 on 3 clean twins (FAIL; 0/2 on the vetted twins);
   JSON-valid first reply 1.00 (PASS); stability 0.90 over 10 cases x 3 fresh (PASS, but 6 of the 10 are ACCEPTed
   every time); contract-valid first reply 0.68 (was 0.36); unavailable 0.20 (was 0.46). The pipeline passes
   content loss and broken install only through the deterministic stage. Causes: the model ACCEPTs most
   defective candidates; with the fact rule removed it files `unsupported_claim` freely (87% of findings,
   many against renderer-printed lines, 29 duplicates); the 12-line cap causes 8 of 13 invalid first replies.
9. Recommendation (each needs its failing test first): deterministic claim checks for version, package,
   format and install claims; a checkable unsupported-claim contract and renderer-printed-line scope; allow a
   whole-section citation for omission, absence and quality findings; merge identical findings; section-by-
   section review; fresh hosted cascade runs for more clean twins. Do not enable the gate for cohort or PR work.

**What this does NOT decide**: whether any item of 9 is accepted (supervisor); the Lane L reviewer; the
budget of a third iteration.



---

## 2026-10-27: Lane L hosted parity (L1-L10): a second, equal lane that is corrected, reviewed, sealed and has its own transaction

**Decided / built** (`plans/PLAN_lane_l_hosted.md` is the design; this records the decisions and what they cost):

1. **A Lane L candidate** is the live README with the engine's minimal evidenced edits, judged as a whole. Its
   outcomes are `CORRECTED`, `NO_CHANGE_WARRANTED` (legitimate: the live README is the candidate, still
   model-reviewed, never an invented improvement) and a refusal that is not a candidate,
   `REFUSED_LANE_R_RECOMMENDED` (a defect no deterministic edit may repair; named, never masked; which findings
   are defects is a closed table where an unknown detector is a defect). Artifacts: corrected README, the live
   README's bytes, patch, `corrections.json` (edit list and report), `holdouts.json`, facts, review verdict, ledger.
2. **The final README is what is reviewed, not the delta.** Model-free holdouts first (confinement re-proved from
   the edit list, determinism, the reviewer's own claim and retention rules over the final text, any unrepaired
   defect); only a candidate that clears them reaches `review_with_model`, unchanged (same job, route, fold,
   no-re-roll guard). `ReviewUnavailable` is a retryable failure; a deterministic-only verdict never seals.
3. **The lane dimension is a versioned, additive layout.** Layout v1 IS Lane R and is not moved; Lane L lives in
   `candidates/<slug>/lane-l/` with its own `CURRENT`; manifest schema 1 reads as Lane R, schema 2 names its lane
   and a reader refuses a manifest in the wrong lane's tree. A bundle sealed in schema 1 keeps being rewritten as
   schema 1 by its own proof; Lane R's `dependencies.json` gained no key. `CURRENT` is per lane (one pointer cannot
   name two revisions). One status model (`portfolio_status`, a row per repository per lane); counts are separate
   per lane; the drift monitor and the candidates-publish overlay take a lane (the overlay no longer replaces the
   whole slug, so publishing one lane cannot delete the other's committed candidate).
4. **Blast radius, queried first** (counts in the plan, section 6): 2 slugs, 14 tracked files, 1 sealed bundle
   (schema 1, READY_FOR_PROPOSAL), 36 untracked scratch repositories, 2 live durable-state refs (both Lane R, both
   load unchanged). No sealed bundle was edited, moved or resealed; the committed bundle's manifest and `CURRENT`
   are pinned by digest in a test.
5. **Consumed-scope invalidation for Lane L**: source revision and the live README's bytes and the fact records
   invalidate; the correction engine and each detector are the new `correction` scope (stage COMPOSING, update
   available, never invalidating); the review prompt and logic are reviewer scope; a prompt or renderer Lane L
   never ran cannot reopen it. Lane L's dependencies name no host, Python or toolchain so a rerun elsewhere
   writes the same bytes. Detector versions are pinned to their module sources by test.
6. **One durable transaction per lane.** `GitStateBackend(lane=...)` keeps Lane L's record in
   `.../records/<owner>__<name>@lane-l` (`@` cannot be in a GitHub name, so no repository can own the key; a `__`
   suffix could have); the record names its lane; a record of the other lane in a lane's ref is refused; the
   existing refs are exactly what they were.
7. **Hosted**: `present.py --lane R|L` (default R); `present.yml` has a `lane` input (`both` default). Both lanes
   read the one secret-free facts artifact; Lane L runs in the credentialed job on validated facts only, executes
   no repository code and builds no facts. `both` runs two processes; Lane L runs after a Lane R failure (status
   function) but not without the facts.
8. **A shared defect found by the cross-machine requirement and fixed**: the Python example verifier quoted pip's
   error with the checkout's absolute path and a CRLF (`python_examples._redact`), so two machines sealed different
   `facts.json` for one revision. Blast radius: the only two unscrubbed tool-output sites of the five example
   verifiers; 13 Python registry entries; 0 sealed Python bundles. Hosted Linux runs share a workspace path, which
   is why no hosted run showed it.
9. A structural test (`tests/readme/review/test_no_reroll.py`) listed the only two callers of `review_with_model`;
   Lane L's `lane_l_review.py` is now the second production caller and the list says so.

**What this does NOT decide**: PR eligibility of a Lane L candidate (needs the reviewer calibration gate, a Lane L
corpus, and `propose/effect.py` accepting a lane; the reviewer prompt is written for Lane R's shape, with the
renderer-owned-section and plan/dispositions wording, and is uncalibrated for Lane L); a Lane L recheck runner
(`recheck_bundle` is unported for both lanes); the cohort pilot and any hosted run (none was dispatched; nothing
here was run on a runner); the reviewer's own scope, which `readme/review/scope.py` defines by Lane R's shell
(installation, license, badges, navigation, every fenced block and table row are "renderer-printed" and never
shown to the model): true of a Lane R candidate, false of a Lane L one, so for Lane L the model never sees that
text and only the deterministic holdouts cover it until the reviewer API can be told the candidate is not
renderer-owned (that file is not touched here); the `claim_*` and `additions` detectors the old engine had (not ported), so a real
README with a wrong version or install command is refused with a Lane R recommendation rather than repaired.

**Two things the state card should say differently**: its "zero provider calls" rerun is a call-store replay of a
stochastic reviewer (mission section 7 step 8 distinguishes that from repeatability), so the cache restore is part
of the proof; and "a lane dimension in CURRENT" is a `CURRENT` per lane.

**Where the detail lives**: `plans/PLAN_lane_l_hosted.md`; `src/repo_presenter/{lane_l_run,present}.py`,
`lane_l_review.py`, `readme/correction/report.py`, `readme/bundle/{seal,invalidation,evaluation}.py`, `core/candidates.py`,
`core/state/{git_backend,schema,present_transaction}.py`, `.github/workflows/present.yml`;
`tests/test_lane_l_hosted.py`, `tests/test_lane_l_review.py`, `tests/test_present_lanes.py`, `tests/core/test_candidates_lanes.py`,
`tests/core/state/test_lane_state.py`, `tests/readme/bundle/test_seal_lane_l.py`,
`tests/readme/correction/test_lane_l_{report,determinism}.py`; `migration/reuse-manifest.yaml` (the "Lane L hosted parity" entry).


---

## 2026-10-27: Independent LLM reviewer, iteration 3 (deterministic claim checks, sectionwise review, calibration status): the gate still FAILS, differently

**Decided / found** (details, tables and raw data: `docs/investigations/2026-10-27-reviewer-calibration-iteration-3.md`; plan amendments in `plans/PLAN_independent_llm_reviewer.md` section 8):

1. **Why the pipeline missed `contradict_version` and `contradict_package_name`**: the version rule did not read the renderer's own sentence
   (a comma before "version"), the identity rule read install commands inside fences only, and nothing read a format list. `validation/claims.py`
   now does (BC-14 and `claim_contradiction`). Blast radius queried before commit over 41 READMEs on disk: 0 findings added, 0 removed. Two
   false positives found while writing it (a sibling product sharing the family prefix; a module path) are negative controls.
2. **One bounded unit per call.** A review is split into units of author-written text (<= 4,500 characters); a unit never shows a line the renderer
   printed (headings, tables, fences, diagram, deterministic sections, member bullets, sentences the renderer appends to authored lines), and a line
   not shown cannot be cited by any claim kind. This replaces the "do not criticise renderer text" instruction with a check. The model sees the
   facts the text may cite (symbols with their extracted docstrings), the part of the original that shares its words and per-line support hints
   (a search aid; it decides nothing and never names an inherited unit). Dispositions and validation are no longer sent. **The closed clearance
   catalogue is unchanged**; no hint, audit or overlap clears anything.
3. **Contract**: whole-section citations for omission, absence and quality (a locator, not a quote, so `absence_present` still works); the 12-line
   cap stays for contradiction and unsupported claim; a finding names a section of its own unit; identical findings merge; unit replies merge
   (ids renumbered before any clearance) and fold once; an unavailable unit makes the review unavailable unless another unit already rejects it;
   the no-re-roll record is per unit request. `REVIEWER_LOGIC_VERSION` 6, prompt v17, reviewer scope only.
4. **Calibration status is a committed file the code reads and never writes** (`data/reviewer_calibration.json`, `NOT_PASSED`): fail closed;
   `PASSED_WITH_DECLARED_LIMITS` needs a non-empty owner acceptance in the committed file; a verdict records the status and an `uncalibrated`
   label; `propose_candidate` refuses with `REVIEW_UNCALIBRATED` unless the verdict and the file both permit. Not done here (bundle code belongs to the
   Lane L change): the sealed manifest itself does not yet repeat the label; the sealed `review_verdict.json` (already hashed in the manifest) carries it.
5. **New deterministic holdout**: a prose paragraph printed twice. **Measurement now scores a catch only when a blocking finding cites lines holding the
   defect's own text** (the smoke run counted a finding about another sentence as catching a real contradiction).
6. **Result**, 229 calls of the authorised 300 (cap 350), all qwen3-next: tier 1 pipeline on-target recall 1.00 for version, package name, format,
   install, content loss, invented name and repeated paragraph; tier 2 reviewer alone 11/11 injected unsupported claims and 11/11 filler, 0/2 and
   1/2 on the two real-defect classes; false-reject 1/3 on the first pass and 7/12 over all draws of the 3 scored twins (one flawed, one adjudicated as
   carrying a probable real unsupported format claim); stability 6/8 = 0.75; JSON-valid first reply 1.00; contract-valid 0.98; unavailable 0/109;
   17,025 mean prompt tokens per call. Failing gates: false-reject, stability, and the two real-defect classes (n = 2 each).
7. **Honesty about method**: the prompt and evidence were adjusted on 34 calls over the same three scored twins; run7's twin gained a repair that the
   smoke run found and a reading of inherited unit 061 confirmed. No further clean twins are derivable offline (the sealed hosted bundles of runs 1, 5, 6, 7 are one
   stale candidate; run2/run3 and every Lane R base trip a deterministic rule on their own twin).

**What this does NOT decide**: whether to run fresh hosted cascades for more clean twins (needed before the gate can be read); the owner's
acceptance of any declared limit (unavailable while shared gates fail); Lane L calibration (`review_with_model(..., rendered=False)` exists for
a maintainers' README, uncalibrated).

---

## 2026-10-28: First qwen3-next cohort (five new ecosystems) — a generalization gap in S9 accounting, not five one-off ecosystem defects

**Decision**: the 2026-10-27 cohort's three REJECTs sharing the earlier .NET/Python shape (Java, Go, TypeScript)
were diagnosed as one generalization gap, per mission section 12 ("two equivalent failures force a changed
causal approach"), not patched per finding. Root cause: the "is this kept unit printed" test
(`independent_reviewer.unprinted_kept_units`, shared by `disposition_coverage_rule` and
`accounting.account_unprinted_units` on purpose, so the two can never disagree) only recognized a full exact
text match, or — for a list only — every item stated within its own destination section; `placement.py`'s own
`uncovered()`/`uncovered_block()` can legitimately print just the *uncovered remainder* of a kept paragraph or
table (same-section, or cross-section via `placement.py`'s `_STATED_BY`/"also"), which the check had no concept
of at all. Fixed by recognizing the same sentence-overlap test placement's own drop rests on
(`coverage.states_all`), guarded by two properties a genuine trimmed remainder always has and a unit entirely
paraphrased away never does: every link or command the unit carries is still in the document
(`coverage.hard_tokens`), and at least one sentence or item of it is printed word for word, not merely restated
(`coverage.partly_printed`, new — this guard is what keeps the fix from reopening the measured .NET/Python
list-redundancy case, where neither list item is ever printed verbatim). A second, related gap: an
`OMIT_UNSUPPORTED` unit (usually a heading) whose own rationale already says it is redundant with a real
section, but cites no fact — the authoring model used the word "omit" for the exact "covered elsewhere" shape
`_uncited_heading` already repairs for the word "supersede", and the old dispatcher matched that literal
disposition string only. Fixed by `accounting._uncited_redundant_omission`, which proves the covering section
from the rendered document (never the rationale's prose), with a minimum-stem floor so a short label such as
"Maven:" is never matched by sentence-overlap alone.

**Why**: three of five brand-new-ecosystem hosted runs hit the identical cause class on the first try — direct
evidence the earlier fix (`accounting.py` commits `b0c72f9`, `4604b62`) was correct for the two shapes it was
built from but did not generalize, because it reasoned from one literal disposition word and one literal-match
test rather than from what the renderer can actually do to a kept or omitted unit's text. Per-ecosystem
inspection (Java: 3 of 4 findings were this shape, 1 a real dropped hyperlink left blocking; Go: 2 of 6 headings
were this shape, 4 were genuinely lost content — a directory-tree code block and a `docs/usage.md` link neither
restated anywhere — correctly left blocking; TypeScript: 0 of 2 findings were this shape, both are a missing
fact-extraction gap for a later card, not an accounting question) confirms the fix is general, not a sixth
one-off patch: it resolves the shape wherever it is real and leaves every genuinely-lost unit exactly as
blocking as before.

**Two further decisions on the same cohort**:
- **Cpp (40555595204, authoring `OutputRejectedError`, transient, never reached the reviewer)**: the rejection
  is correct, not a missing fact. `intro` cited `` `reference.aspose.org` `` (a bare domain, copied from the
  live README's own prose) as a verified identifier; the only fact that exists for it is the full URL
  (`link_target`, value `https://reference.aspose.org/cells/cpp/`), never the bare domain. Minting a new fact
  by string-slicing another fact's URL would be manufacturing evidence to satisfy a validator, not extraction.
  `composition/authoring_retry.py`'s own documented remedy ("a stray identifier is deliberately NOT rewritten
  into words: that would launder an unevidenced claim") is exactly the self-healing retry this case calls for,
  already ported and already tested. No code changed for this one.
- **Rust (40555609801, deterministic BC-07 failed, no LLM review reached — working as designed)**: BC-07 found
  two real things. One is a genuine renderer bug, fixed: the fixed, cross-ecosystem `NOT_VERIFIED_NOTE`
  (`composition/retained_examples.py`) said "...against this revision", a banned narration phrase
  (`readme/correction/text_gate.py`'s own catalog), so BC-07 necessarily fails every time *any* ecosystem ever
  retains an unverified example — reworded, meaning unchanged, with a falsifier test
  (`narration(NOT_VERIFIED_NOTE) == []`, and the old wording confirmed to still fail it). The other is a
  genuine, still-open content defect, left alone: `inherited_unit:048.paragraph` says "summarized in the
  module-grouped table below" but no table follows it in that section — a dangling forward reference needing
  S4/authoring repair, not a check fix.

**What this does NOT decide**: TypeScript's missing Node/TypeScript engine-version fact (parallel to Java's
`package:java_release`) — a real gap, left for a future extraction card. Go's two genuinely lost units and
Rust's dangling table reference — real content defects needing an S4/authoring repair pass on a live rerun, not
a check or accounting change. None of the five runs has been re-dispatched hosted; this is proven offline
against the downloaded evidence (`C:\Users\babar\AppData\Local\Temp\cohort1\<run-id>\`), not yet against a
fresh hosted pass.

**Where the detail lives**: `src/repo_presenter/readme/review/independent_reviewer.py` (`_kept_text_printed`),
`src/repo_presenter/readme/repair/accounting.py` (`_uncited_redundant_omission`, `_section_covering`,
`_heading_children`), `src/repo_presenter/readme/composition/coverage.py` (`partly_printed`),
`src/repo_presenter/readme/composition/retained_examples.py` (`NOT_VERIFIED_NOTE`);
`tests/readme/repair/test_accounting_generalization.py` (16, new, parametrized across java/go/typescript/
net/python); `tests/readme/repair/test_accounting_uncited.py`, `tests/readme/composition/test_retained_examples.py`,
`tests/readme/review/test_scope.py` (updated); `migration/reuse-manifest.yaml` (the matching entry, with the
full per-run measured-defect breakdown and blast-radius query).

---

## 2026-10-28: Re-run confirmed the S9 fix on real hosted data; two further things investigated, one fixed, one confirmed as a real capability gap (not a bug)

**Context**: the 2026-10-28 cohort re-run (java 40571532257, go 40571547837, typescript 40571563106, cpp
40571540396, rust 40571555199, all after `0f98ca2`) confirmed the S9 generalization fix on real hosted data
(commit `adbfcb9`) and surfaced two further things, both investigated against the actual downloaded evidence,
never from code alone.

**Bug 1 (Cpp, run 40571540396) — fixed**: two inherited code blocks (a NuGet `PackageReference` snippet, a CMake
`find_package` snippet) were `OMIT_UNSUPPORTED` with empty `fact_ids` and the rationale "is not supported by
facts and is not placeable", yet the repository's own `package:distribution.aspose.cells.cpp.foss` fact
(`SUPPORTED`, value `"Aspose.Cells.Cpp.FOSS"`) is spelled verbatim inside the first block's own text. The claim
is false — a matching fact exists — so `live_readme_loss_rule`'s own `_accounting_units`
(`readme/review/independent_reviewer.py`), which requires `fact_ids` truthy before counting a disposition as
accounting for anything, correctly refused to count it, and the content was reported lost even though a
disposition existed. Root cause located precisely: `normalize()`'s own self-audit (`_omission_gap`, via
`ctx.named` = `composition.authoring.inherited_unit_named_symbols`) only recognizes a verbatim match against a
SUPPORTED `public_symbol`/`import_path` fact — never a `package` or `link_target` fact — so this exact shape is
invisible to both `coverage_findings()`'s own self-audit and to `normalize()`'s folds. Confirmed NOT a
packet-construction bug: `package:distribution.aspose.cells.cpp.foss` (kind `package`) is in
`prompts/source_reconciliation.yaml`'s own `fact_kinds` list and was `SUPPORTED`, so the model saw it in the
packet and simply failed to cite it on this hosted run — a deterministic backfill is the right fix regardless
of why the model missed it, the same way `_omits_contradicted_command` and the existing `PLACING`-only
named-symbol backfill already fix a model's missed citation deterministically rather than trusting it to get
every call right. Fixed in `normalize()` with a new, narrowly-scoped fold (`_spelled_supported_facts`,
`_OMISSION_CITABLE_KINDS = {"package", "link_target"}`): an `OMIT_UNSUPPORTED` disposition with empty
`fact_ids` whose unit text spells a `SUPPORTED` `package` or `link_target` fact's value verbatim (length-guarded
against trivial matches) gets that fact backfilled as its citation and an honest rationale — the disposition
value is never changed, never loosened, and a unit with no such match is left exactly as uncited as before.
Proven general with two independent ecosystem shapes, not a C++ special case: a C++ `package` match (the real
defect) and a Go `link_target` match (`link_target:044` = `"docs/usage.md"`, found independently to be the
exact same shape in the Go re-run's own `OMIT_UNSUPPORTED` units 069/071 — see below), plus a negative control
proving a genuinely unsupported block stays uncited.

**Investigation 2 (why repair didn't already fix the remaining Java/Go `live_readme_loss` findings) — real
evidence read, not inferred from code**: downloaded the actual re-run artifacts (`40571532257` java,
`40571547837` go) via `gh run download`, not just the first-cohort runs, and read `ledger.jsonl`,
`dispositions.json` vs `dispositions.composed.json`, and `review_verdict.json` directly.
- **Java (1 remaining: the dropped `src/test/java/com/aspose/threed/` link)**: repair WAS attempted — two
  `targeted_repair` logical calls are in the ledger (stage `S11`/S4-routed), each retried once by `run_job`'s
  own re-ask, both ultimately `response_invalid`. The model oscillated between `OMIT_UNSUPPORTED` with no
  citable fact (rejected: `uncited_prose_omit`) and `VERIFIED_PRESERVE`/`VERIFIED_MOVE` that keeps the paragraph
  verbatim (rejected by `repair/loop.py`'s own `refuse_noop`: the defect is that the paragraph's embedded
  markdown link was rendered as plain text by S6/composition, not that the disposition is wrong — S4's own
  disposition already correctly cites `build_test_asset:tests`/`link_target:030` and places the paragraph
  verbatim). This is case **(a)**: repair rounds exhausted because the actual cause is an S6 rendering defect
  (a kept paragraph's embedded link loses its href) that an S4 disposition patch structurally cannot reach —
  a real Lane R gap (S4's patch repair never touches how a kept unit's own markdown is re-emitted), not a
  routing bug, and not fixed here (out of this card's `write_paths`; needs its own card against S6/composition).
- **Go (4 remaining: 2 headings, 1 directory-tree code block, 1 `docs/usage.md` link)**: zero `targeted_repair`
  ledger entries — repair was never invoked, confirmed by the ledger, not assumed. Traced why: three of the four
  findings' own units (045 `Project Structure` heading, 047 the directory-tree code block, and the 070 heading)
  are `OMIT_UNSUPPORTED` with empty `fact_ids` whose rationale claims redundancy but names nothing a fact backs
  — genuinely unsupported content with no literal fact match in its own text (a free-hand ASCII directory tree,
  bare headings), so this is real case **(a)**: content with no accounting path, not a routing gap; a
  `defect_bridge` bug was considered (whether `live_readme_loss` findings about content missing from every kept
  unit can ever be located and routed to S4) but a repairable disposition-level fix for *this* content would
  still need something to cite, which does not exist, so widening the router alone would not have produced a
  different outcome for these three. The fourth (`docs/usage.md`, units 069/071) is the exact same shape Bug 1
  fixes: `link_target:044` (`SUPPORTED`, value `"docs/usage.md"`) is spelled verbatim in both units' own text,
  uncited — this one the normalize() fix above resolves the same way it resolves the Cpp case, confirming the
  fix generalizes across ecosystems on real hosted evidence, not just a crafted test.

**What this does NOT decide**: the Java S6 link-stripping defect (a kept unit's own markdown link losing its
href on render) and the Go directory-tree/heading content with no fact at all — both need a real Lane R
placement/rendering capability this card does not build, not a reconciliation or repair-routing fix. Neither
historical run's own JSON evidence was rewritten; the fix is proven against fresh unit tests reproducing both
ecosystem shapes plus a negative control, per `AGENTS.md`'s falsifier discipline, not by editing downloaded
artifacts.

**Where the detail lives**: `src/repo_presenter/readme/reconciliation/dispositions.py` (`_spelled_supported_facts`,
`_OMISSION_CITABLE_KINDS`, the new fold in `normalize()`); `tests/readme/reconciliation/test_dispositions.py`
(3 new tests: C++ package match, Go link_target match, negative control); `project/state.yaml`'s
`INDEPENDENT_LLM_REVIEWER.hosted_run_log` (the run IDs and the supervisor's own re-run record); evidence read
from `C:\Users\babar\AppData\Local\Temp\cohort2\{40571540396,40571532257,40571547837}\`.

---

## 2026-10-28: A structural blocking check gets the same bounded repair chance an S4 defect gets; the root cause was a routing gap, not a masking repair

**Decision**: widen `cascade.py`'s S9 settle loop (renamed `_s4_defects`/`_repair_s4` to
`_settle_defects`/`_repair_defects`) so it attempts a repair for ANY `validation_defects` result
whose causal stage `repair_defect` (`readme/repair/loop.py`) actually dispatches on — S4
reconciliation, S5 planning, or S6 authoring — instead of only S4. The filter is now
`defect.repairable` (`stage is not None`), the identical test `_review_defects` already applies to
the reviewer's own S10 findings; BC-12 (and any other structural check) is never loosened or
bypassed — `validate_candidate` still judges the recomposed README exactly as before.

**Why**: a real hosted re-run (aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 40679621466) failed
BC-12 ("product-name position spells the canonical name") in `development_testing`, and
`present.py` reported the run never reached the independent reviewer. The puzzle: the FIRST run of
the same repository (40571540396) reached the reviewer and reported a REJECT from `live_readme_loss`
instead, never mentioning BC-12 — and the only code change between the two runs relevant to this
repository/path is commit `48995fe` (a dispositions.py citation backfill fold, touching nothing in
`structure.py`/`blocking.py`). Downloaded and diffed BOTH runs' full artifact sets (`gh run download
40571540396`, `40679621466`) to prove the cause rather than guess it:
- `README.coherent.md` line 211 is **byte-for-byte identical** in both runs ("Aspose.Cells FOSS for
  C++ is published on NuGet as `Aspose.Cells.Cpp.FOSS`...").
- `validation.json`'s BC-12 record is **identical** in both runs: `FAIL`, `development_testing`,
  `"product name 'Aspose.Cells FOSS' is not the canonical name 'Aspose.Cells FOSS for Cpp'"`.
- `repairs.json` (run1 only; run2 had none at the point of failure) shows exactly ONE attempt,
  `disposition_coverage:0`, stage `S4` — BC-12 was never attempted in either run.
- `review_verdict.json` in run1 carries `"source": "deterministic"`, `"model_served": null`,
  `"reason": "2 deterministic finding(s) block"` — this is `review_candidate`'s own deterministic
  pre-screen verdict (S9's `live_readme_loss`/`disposition_coverage` rules), NOT the LLM reviewer.
  Run2's equivalent file is `"verdict": "ACCEPT"`, `"findings": []`, also `model_served: null` — the
  pre-screen found nothing (commit `48995fe` fixed its one real defect), but the LLM was still never
  asked, because `run_cascade`'s own outer loop guards S10 with
  `while not verdict.blocking_findings and not blocking_failures(settled.validation)`, and
  `blocking_failures(validation)` is non-empty (BC-12) in BOTH runs.

So BC-12 was blocking, identically, in both runs, every round, from the first pass onward — it was
never masked by a repair, never fixed and re-broken, and no check ordering or caching differed.
The only thing that differed is which `present.py` message surfaced: `_cascade_and_seal` raises on
the FIRST failing condition it finds — `verdict.verdict != "ACCEPT"` — and run1's deterministic
pre-screen found its own (real, separate, now-fixed) REJECT first, so the message named
`live_readme_loss` and never reached the second condition (`not verdict.model_reviewed`, which
names the still-failing blocking checks) that would have named BC-12. Run2's pre-screen passed
(ACCEPT, 0 findings), so for the first time the message fell through to the second condition and
finally named BC-12 — a defect that had been there, unrepaired and unreported by name, since before
Bug 1 was ever fixed.

The real, generalizable gap `cascade.py`'s own code confirmed this against: `_s4_defects` computed
every `validation_defects` result (which already routes a `COMPOSING`-stage check naming an
LLM-owned section to `S6`, exactly as `repair_defect` can revise) and then threw away everything
except `stage == "S4"` before ever calling `_repair_defects`. BC-12 is no different in kind from an
S4 disposition-citation defect or a reviewer's own S6 finding — `repair_defect` already dispatches
all three stages identically — but the S9 settle loop only ever gave the S4 shape a bounded repair
attempt. The outer S10 loop cannot make up the difference either: it depends on
`blocking_failures(validation)` already being empty before the model is even asked, so a non-S4
blocking check had no path to a bounded repair anywhere in the cascade.

**What this does NOT decide**: the real "C++" vs "Cpp" text in the repository's own fixtures was
never hand-edited (per the task's own constraint) — the fix is routing, not a text patch, and BC-12
itself is unchanged. `readme/repair/loop.py::settle_candidate` (a separate, currently-unwired
wrapper around `run_cascade` that `present.py` does not call) has the same restriction — it builds
defects only from the reviewer's verdict, never from `validation_defects` — left as a known,
out-of-scope follow-up since it is not on the path that produced either hosted run. No sealed
candidate is affected: `candidates/` holds exactly one sealed bundle
(`aspose-3d-foss__Aspose.3D-FOSS-for-.NET@52b0f00e`), unrelated to this repository and this check,
and this change only widens which defects get a repair *attempt* inside the cascade — it cannot
change what `validate_candidate`/`seal_candidate` ultimately accept.

**Where the detail lives**: `src/repo_presenter/cascade.py` (`_settle_defects`, `_repair_defects`,
and the module docstring); `tests/test_cascade_s9.py`
(`test_a_failure_routed_to_any_of_s4_s5_s6_reaches_the_settle_repair`, extended with a real BC-12
case; two new end-to-end tests: `test_a_structural_defect_is_now_repaired_the_same_way_an_s4_defect_is`
— the falsifier, reverting the filter to `stage == "S4"` makes all three fail — and
`test_a_repair_that_still_fails_bc12_blocks_again_and_is_never_retried`, the negative control
proving BC-12 is never loosened: a repair accepted by `unit_checks` but still spelling the name
wrong is recorded `repaired` yet re-raises and blocks again, never retried a second time); evidence
read from `gh run download 40571540396`/`40679621466` (both runs' full artifact sets, not committed,
read from the session scratchpad).

---

## 2026-10-28: BC-07's own RECONCILING finding named its inherited unit in the message text but never carried it as a field, so the S4 patch router it was already wired into (`d2ca65b`, above) could never resolve a target

**Decision**: `readme/validation/structure.py::_reference_failures` (BC-07, the "dangling
`table below`/similar forward-reference" sub-check) now passes `unit=unit` to the `Failure` it
already builds for the RECONCILING case, instead of only interpolating the same `unit` value into
`detail`'s prose. No other file changes meaning: `Failure` (`validation/failures.py`) already
declares a `unit` field for exactly this purpose ("the inherited unit a reconciliation failure is
about... never prose parsed back out of `detail`"), `blocking.py::validate_candidate` already
serialises `failure.unit` into the failure record's `unit_id` key when it is not `None`, and
`reconciliation/patch.py::failing_units` already reads only that field — every downstream piece of
plumbing this needed was already built (mostly today, by `71e54d5`/`5c68d19`/`4604b62`/`0f98ca2`/
`d2ca65b`). `_reference_failures` computed the right unit, every time, and then silently dropped it
on the floor before constructing the `Failure` — a one-keyword-argument gap, not a design gap.

**Why**: a real hosted Lane R run (40688097016, aspose-cells-foss/Aspose.Cells-FOSS-for-Rust) was
blocked by BC-07's finding `"inherited_unit:048.paragraph is kept as written but says 'table
below' but no table follows it in this section: ...'"` (`causal_stage` RECONCILING). `repairs.json`
showed stage-S4 routing already worked (`d2ca65b` wired it) but the one attempt was recorded
`unrepairable`: `"no stored disposition of an inherited unit is named by this defect; a
whole-batch revision would regenerate unrelated units"` — even though the finding's own `detail`
text literally names `inherited_unit:048.paragraph`. The same defect shape was independently found
the same day on this repository's Lane L run (a dangling "table below" reference), confirming a
real, recurring README defect class, not a fluke.

Traced the chain rather than guessing: `_repair_reconciliation` (`readme/repair/loop.py`) calls
`_named_units`, which calls `patch.failing_units(defect.record)` first (a validation-source
`Defect.record` has no `quote` field, so `_named_units`'s own quote-matching fallback — built for
the reviewer's LLM findings, not validator findings — can never fire here; `failing_units` reading
a field is the *only* path for this defect class). `failing_units` reads `failure.get("unit_id")`
for each entry in `record["failures"]`. Those entries are exactly what `blocking.py::validate_candidate`
serialises per `Failure`: `{"section_id": ..., "causal_stage": ..., "detail": ...,
**({"unit_id": failure.unit} if failure.unit is not None else {})}`. `install.py`'s own BC-02
reconciliation check (`Failure("RECONCILING", detail, unit=unit)`, line 282) already does this
correctly, proving the field and the serialisation path both work and are exercised elsewhere —
`structure.py`'s sibling check was simply the one call site that never threaded the value through,
even though its own docstring already said "RECONCILING, naming the unit" and its own `unit`
variable already held the right value two lines above the `Failure(...)` call that dropped it.

**Why this is the fix and not a parsing shim**: the task's own framing asked whether the cleaner
fix is a structural field on `Failure`/the check rather than parsing prose downstream. The field
already exists, is already documented as the non-prose channel, and is already read exactly that
way by `failing_units` and populated exactly that way by a sibling check — so the correct, smallest
fix is wiring the one call site that forgot it, not adding a new field or any text-extraction logic
anywhere. No prose parsing was added or needed.

**Tests**: `tests/readme/validation/test_registry_checks.py`:
`test_bc07_routes_a_kept_sentence_whose_referent_was_dropped_to_reconciliation` (existing) extended
to assert the RECONCILING failure's own record now carries `unit_id ==
"inherited_unit:002.paragraph"`, not only the prose `detail`. New test
`test_bc07s_reconciling_finding_now_routes_to_a_real_s4_patch_target` drives the real production
path end to end — `validate_candidate` → `readme.repair.targeted.validation_defects` →
`readme.reconciliation.patch.failing_units` — and asserts the BC-07 defect now resolves to
`["inherited_unit:002.paragraph"]` and routes `S4`. Its negative control: the same check's sibling
branch (a dangling reference that matches no inherited unit, i.e. genuinely-authored prose) still
serialises no `unit_id` and `failing_units` still returns `[]` — the fix never fabricates a target
when none exists. Falsifier confirmed by hand: stashing the one-line `structure.py` change makes
both the extended existing test and the new test fail with the exact symptom reported
(`unit_id` missing / `failing_units` empty), restoring it makes both pass; `_named_units`'s and
`patch_scope`'s own existing "names no unit" fallbacks (`tests/readme/reconciliation/test_patch.py`)
were re-run unchanged and still pass, proving the fix adds a real target without weakening the
"never fabricate" guard those tests already enforce.

**What this does NOT decide**: `readme/repair/loop.py::settle_candidate`'s separate,
currently-unwired `build_defects`/`review.defect_bridge` path (noted as a known follow-up in
`d2ca65b`'s entry above) is untouched — this fix is in `structure.py`'s check itself, so both the
wired `validate_candidate`/`validation_defects` path and any future caller of the check benefit
identically; it was not necessary to touch `defect_bridge.py` (confirmed by reading it: it never
parses a finding's own text for a unit id for any finding source — it only matches a structured
`quote` field against `composition/placement.py`'s placed texts, which is the correct structural
equivalent for the reviewer's LLM-finding shape and was already free of the bug this card fixes).
No fresh hosted re-run of Aspose.Cells-FOSS-for-Rust was dispatched to confirm the repair now
succeeds live (this project's live-provider-call constraint); the fix is proven offline against a
reproduction of the exact finding text and the exact routing chain the hosted run exercised.

**Where the detail lives**: `src/repo_presenter/readme/validation/structure.py`
(`_reference_failures`); `tests/readme/validation/test_registry_checks.py`.

---

## 2026-10-31: An independent status review found the pipeline's headline status unsupported; adopt evidence-gated status words, a branch-and-live-check push gate, and derived counts

**Decision**: the following working rules are adopted, owner-approved on 2026-10-31 after an
independent status review (re-verified against primary evidence in the same session):
(1) the words "confirmed", "sealed" and "accepted" are used for a candidate only when a committed
bundle exists, `data/reviewer_calibration.json` is PASSED, and the owner has reviewed it; otherwise
the wording is "observed on run <id>" / "ready for review"; (2) a change that touches the hosted
path goes on a branch and gets one live check before it merges to `main`; (3) the repository is
searched for the constraint or keyword before a fix is built; (4) two failed rounds on one finding
class, any revert, or a broken `main` means stop and report; (5) portfolio counts come from a
derived command over the registry, the origin state refs and `candidates/`, never from typed
values; (6) a fix is verified (tests plus live evidence) by an agent other than its author;
(7) any revert, regression or push to `main` gets a same-day entry here; (8) no portfolio-widening
dispatches until calibration iteration 4 is run or the owner waives it in writing.

**Why**: verified facts at the time of the review. `data/reviewer_calibration.json` is NOT_PASSED
(three iterations on 2026-10-27, `fdc9b83` last; iteration 4 never run although the precondition in
`project/state.yaml` "at least 3 more real, independently-verified bases" is very likely met).
`candidates/` holds one full bundle (3D-.NET, `6f8f9cb`, a manual seal) whose `review_verdict.json`
is a 100-byte logic-v1 deterministic ACCEPT, with no model review; it dropped all 9 runnable
examples and has overlapping opening paragraphs and contradictory format claims. The hosted
workflow (`.github/workflows/present.yml`) has no step that commits a candidate; output survives
only as a 14-day artifact and an evictable cache, plus one `record.json` per repository on the
origin state refs. Latest durable records (49, fetched 2026-10-31): Lane R good state
(ACCEPTED/READY_FOR_PROPOSAL) 4 of 36, Lane L 4 of 36, both lanes 1 (Cells-Java). 130 hosted runs
since 2026-10-27: 16 green, 114 red. The `state.yaml` counters `lane_r_accepted: 34`,
`lane_l_accepted: 36` and `repositories_independently_reviewed: 36` come from the 2026-10-21
manual sweep (`evidence/build/P1_PORTFOLIO_SCALE/`), not from hosted runs or a derived command.
Regressions found only by live checks, each pushed before it was checked: `968eb55` generalized
the duplicate-preserved-paragraph check beyond "opening" and produced two false positives
(VERIFIED_REWRITE contamination; blob contamination in list-heavy `api_reference`), reverted in
`694bf6d`; `b72fe9e` added `uniqueItems` to `authoring_schema`, which the gateway answers with
HTTP 400 (documented at `readme/investigation/dossier.py:56`), so Lane R section_authoring failed
on `main`; the correction is `4f9258b` (branch `fix/restore-main-bound-citations`).

**What this does NOT decide**: the calibration route (larger corpus, second-model reviewer, or
declared limits), the persistence mechanism for candidates and its token, taskcards versus amending
`AGENTS.md`, the pilot repository, and per-defect upstream authorization. Those stay with the owner.

**Where the detail lives**: `project/state.yaml` (PORTFOLIO_WIDENING_2026_10_30 entries, now
annotated), `data/reviewer_calibration.json`, `docs/investigations/2026-10-27-reviewer-calibration-iteration-3.md`.

**Addendum, same day (live check of the correction `4f9258b`)**: dispatched from the branch, not
`main`: run 41173975804 (Imaging-.NET, the original target) and run 41173983873 (Words-.NET, which
reached composition before). Both now reach composition, validation and review, so the HTTP 400
is gone and section_authoring completes. Neither is sealed. Imaging-.NET: independent review REJECT
with 4 blocking `live_readme_loss` omissions (headings "Additional Examples", "Probe a File
Asynchronously", "Count Frames in a Multi-Frame GIF or a Multi-Page DJVU", "Detect a Format From an
Unseekable Stream"). Words-.NET: no LLM review made, deterministic-only verdict, BC-06 still fails.
Those are separate findings and were not touched. A fresh agent that did not write the change
checked out `4f9258b` detached and ran the full suite: 3,371 passed, 11 skipped; it also confirmed
every call site that hashes or sends the authoring schema agrees. Merged to `main` fast-forward.

**Addendum (derived matrix merged)**: `scripts/portfolio_status.py` / `core/portfolio_matrix.py` merged
fast-forward from `e6bd2d9`. A fresh agent that did not write it recomputed the counts from the
fetched origin refs with its own script and matched the tool exactly (Lane R attempted 28 / good 4,
Lane L attempted 21 / good 4, both lanes 1 = Cells-Java, committed bundles R 1 / L 0), and ran the
full suite: 3,377 passed, 11 skipped. Known limitations it found, not fixed here: the committed-bundle
count treats a `CORRUPT_BUNDLE` as committed (the per-row column shows the true status); it reads
records only for registry entries; it does 72 sequential fetches and a transient error aborts the run.

---

## 2026-10-31: Owner delegates the open decisions and sets the target; decisions taken

**Owner direction**: the owner withdrew the "ask the owner" posture ("analyze everything yourself and
take appropriate decisions") and set the target: aspose.org has finalized README candidates, and this
project must autonomously produce candidates for both lanes matching their structure and quality.

**What the reference is (verified by read-only investigation of the sibling checkout)**: the canonical
store `aspose.org/reports/repo-presenter-regen-full/{family}/{platform}/readme.md` holds 37 candidates,
35 of the 36 registry products (GIS/.NET has none). All share one fixed 12-section template
(`data/readme_template_contract.json`) and are gated by deterministic checks
(`readme_refresh_checks.py`). 31 of the products had an earlier version merged upstream (Aug/Sep); the
current ones mostly sit at AWAITING_REVIEW (human approval pending); four were pushed on 2026-10-10.
Its example policy: run each block, ship the ones it cannot run with a recorded BLOCKED-WITH-REASON
(240 of 285 blocks) rather than dropping them. Structure already largely agrees with this repository's
renderer (same section order, banner, link caps, Enterprise Edition rule). The measured gap is content:
this repository drops anything UNRESOLVED, so outputs lose Quick Start / Additional Examples (hosted
Words-.NET run lacks both; Imaging-.NET is rejected by `live_readme_loss`), run 204 lines against
300 (Imaging-.NET) and 1,275 against 935 (Words-.NET), and the committed 3D-.NET bundle has 2 code
fences against 11.

**Decisions**:
1. *Reference and lanes.* The aspose.org candidates are the quality reference for Lane R. Lane L keeps
   its mission definition (minimal, evidenced correction of the live README; quality bar is no defect
   and no regression, not conversion to the template). If the owner wants Lane L to converge on the
   template, that changes the lane definition and is stated, not assumed. No aspose.org text is copied
   into this repository; comparison tooling reads the sibling checkout at run time and commits metrics
   only.
2. *First fix: examples.* Original examples whose fact is UNRESOLVED (not CONTRADICTED) are kept with a
   recorded "not verified" reason instead of being dropped, as aspose.org does. CONTRADICTED examples
   are still refused.
3. *Persistence.* A sealed bundle is pushed to a git ref in the existing state-ref family (no GitHub App
   token, no PR), pointed at from the durable record, with an export command to materialize it.
4. *Calibration.* Not re-run now. Status stays NOT_PASSED and outputs stay labelled uncalibrated.
   Iteration 4 runs after parity is shown on the pilot set, using the aspose.org candidates as a local-only
   reference corpus (far larger n than the 3 clean twins before). Rule 8 of the adopted rules is amended:
   dispatches are allowed to verify a specific change on named repositories (at most three per change);
   coverage sweeps stay paused until the pilot set reaches parity.
5. *Process.* `AGENTS.md` is amended to describe what is actually done (work items in `state.yaml` plus
   this log; branch, live check and independent verifier) instead of per-fix taskcards.
6. *Pilot set.* Imaging-.NET, 3D-.NET, Words-.NET: each has an aspose.org candidate, the hosted facts job
   has a .NET toolchain so examples can actually run, and each already reaches review. Cells-Java stays the
   first delivery candidate later (both lanes good, registry mode `full`).
7. *Upstream effects.* No issue or PR is filed on any Aspose repository without an explicit instruction
   naming that action.

**What this does NOT decide**: whether upstream PRs should be opened for finished candidates, and
whether Lane L should adopt the template (items 1 and 7).

**Where the detail lives**: this log; the investigation outputs are recorded in the entries that follow
as each change lands.

---

## 2026-10-31: Durable bundles and example-failure classification merged; first parity measurement against aspose.org

**Decision**: two changes merged to `main` (tip `b1eb1e4`), each with a branch, an independent verifier
(a fresh agent that did not write it) and live hosted checks before merging.

1. *Durable bundles* (`470f820`..`2753fdc`). `core/state/bundle_store.py` publishes a sealed bundle to
   `refs/repository-presenter-state/bundles/<key>` (same key and `@lane-l` suffix as the record ref) inside
   the transaction, before the record commits; a bundle that cannot be stored is a visible failure
   (`::error::` and a failed record), never a ready candidate. `export_bundle` restores it byte for byte.
   The first live run (41177479590, PDF-.NET Lane L) failed because `present.py` passes a relative
   candidates path and the git plumbing runs in another directory (every unit test used absolute paths);
   fixed in `3223c54`, then run 41177983444 pushed the bundle and an export from the real origin verified
   as READY_FOR_PROPOSAL. Independent review also hardened export (all paths checked before the first
   write, absolute / drive-qualified / backslash / `..` paths refused, empty destination required).
   Backfill: the nine good records' artifacts (which expire 2026-11-13/14) were published to nine bundle
   refs: 3D-Java L, Cells-.NET R, Cells-Cpp R, Cells-Java R and L, Cells-Rust L, HTML-Python R, Imaging-.NET R,
   PDF-.NET L. Eight are the sealed-stage bundle (manifest state ACCEPTED, before the second-run no-op
   proof); PDF-.NET L is the no-op-proven one. All are pipeline-level artifacts of an uncalibrated
   reviewer, not accepted candidates.
2. *Example classification* (`9610373`, `b9eb8ea`, `b1eb1e4`). Root cause of the dropped examples was not
   "unverified examples are dropped" (the retained-examples path already keeps UNRESOLVED ones) but the
   verifiers labelling fragments and product-build failures CONTRADICTED, which is never kept. Hosted
   Words-.NET: all five examples failed with CS0234 in the product's own `ArrayUtil.cs`; Imaging-.NET:
   three failed with CS0103 on `bytes`, `cancellationToken`, `GetUploadStream`. .NET now counts only a
   diagnostic filed against `Program.cs`; CS0103 is a fragment only for a local or an unqualified
   placeholder call, never a qualifier (`RemovedStatic.Foo()`, found by independent review); a
   product-file diagnostic is NOT_VERIFIED; a diagnostic naming no file keeps its FAILED reading.
   TypeScript: TS2304 on a lower-case local only. Accepted residual risk: a removed lower-case class
   (`widgets.Create()`) reads as a local.

**Observed on live runs (pipeline-level, uncalibrated reviewer)**: Imaging-.NET Lane R went from REJECT (four
`live_readme_loss` headings) to a model-reviewed ACCEPT with zero findings, twice (41177736649 and, with the
hardened rule, 41178722091). Against the aspose.org candidate (metrics only): 251 lines against 307, 9 code
fences against 8, 2 `<details>` each, 13 links against 12, 6 Aspose links each, one Mermaid diagram each,
shared headings in the same order; ours lacks three headings (Development dependencies and two example
sub-headings). Words-.NET regained Quick Start and Additional Examples (both absent before) but is
blocked by BC-06: "4 Aspose links exceed the ceiling of 3 (auto budget from 1153 visible words and 0
verified examples)", while every aspose.org candidate carries 5 to 6. That budget (`link_budget.py`,
`AUTOMATIC_TOTAL_CAP`) is the next gap; it is not touched here.

**What this does NOT decide**: the link-ceiling policy, calibration iteration 4, or any upstream effect.

**Where the detail lives**: `src/repo_presenter/core/state/bundle_store.py`, `net_examples.py`
(`classify_build_failure`), `tests/core/state/test_bundle_store.py`, `tests/extractors/platforms/`.

---

## 2026-10-31: `format_overclaim` only flags a claim as a defect with evidence of absence (merged `1392d0e`)

**Decision**: merge `fix/format-overclaim-evidence` to main. The detector previously treated *any*
table/diagram claim lacking a matching SUPPORTED fact as a hard, sealing-blocking defect — including
when the repo's extracted facts hold no format/capability fact at all (an extractor gap, not evidence
the claim is false). It now requires a `has_picture` signal (at least one SUPPORTED fact of the
relevant kind exists for this repo) before an unmatched or UNRESOLVED claim can count as a defect;
otherwise it is reported as `NO_EVIDENCE_OF_ABSENCE` (added to both `REPORT_ONLY_REASONS` and
`NOT_A_DEFECT_REASONS`) and does not block. A CONTRADICTED match is still always a hard defect,
checked ahead of the `has_picture` gate, so a real contradiction blocks even with zero other facts.
Detector version bumped 1→2 with its source-hash pin updated.

**Why**: 53 of 65 Lane L over-claim findings across the hosted portfolio came from repos whose facts
hold no format/capability fact at all — an extractor gap read as a defect, refusing the whole
candidate (Barcode, Email-.Net, Imaging, PDF-Cpp, PDF-TypeScript, Slides-Java, TeX). 3D-.NET, the one
real over-claim the owner's ruling names, has sixteen SUPPORTED formats and simply lacks U3D/RVM/AMF/
HTML5, so it still correctly blocks.

**Evidence**: 91/91 `tests/readme/correction/` tests pass (fresh checkout). A different, fresh agent
independently reviewed the diff cold (no prior context), traced the priority order (SUPPORTED →
not flagged; CONTRADICTED → hard defect before any `has_picture` check; UNRESOLVED or
`not has_picture` → report-only; otherwise → hard defect), confirmed the version/hash-pin wiring, and
verified by tracing the code path that a claim with zero matching facts of any kind in a fact-rich
(`has_picture=True`) repo is still a hard defect, not silently allowed — returned PASS with no
concerns. Two hosted Lane L live checks confirm the fix in production: aspose-imaging-foss/
Aspose.Imaging-FOSS-for-.NET (run 41180657552) and aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python
(run 41180663528) both transitioned REVIEWING → ACCEPTED, where both were previously REJECTed purely
on false format-overclaim findings (BMP/GIF/JPEG/PNG/... for Imaging; SVG/PNG for Barcode).

**What this does NOT decide**: calibration iteration 4, or whether either ACCEPTED record is
owner-reviewed (it is not — "ACCEPTED" here is the pipeline-level reviewer state, never an owner
acceptance).

**Where the detail lives**: `src/repo_presenter/readme/correction/detectors/format_overclaim.py`,
`model.py`, `report.py`, `tests/readme/correction/detectors/test_format_overclaim.py`.

---

## 2026-10-31: link-carry-aware loss checking merged (`fix/link-carry-check`)

**Decision**: merge `fix/link-carry-check` to main (merge commit `4397f33`, non-fast-forward since
the branch had diverged from a since-merged main). `coverage.py` / `accounting.py` /
`independent_reviewer.py` add `_carries_link`/`carries_hard_tokens` so a link-carrying omission check
credits a link that was actually carried into the output under different surrounding prose, instead
of only matching exact text equality.

**Why**: link-text-equality checks were producing false `live_readme_loss` findings on links that
were genuinely carried into the output, just reworded around.

**Evidence**: a different, fresh agent reviewed the diff cold, confirmed the change narrows (never
broadens) leniency versus the prior bare-substring check, ran the shipped tests (6/6 pass) plus a
self-constructed mutation falsifier (reverting the new link-context check to pure substring equality
fails exactly the 2 tests that target this fix, confirming the suite isn't vacuous), and ran the
broader `tests/readme/composition/ tests/readme/repair/ tests/readme/review/` suite (681 pass, no
collateral breakage) — PASS, with one explicitly pre-existing, not-introduced-by-this-diff residual
note (an unanchored substring match that could treat `TODO.md.bak` as carrying a link to `TODO.md`;
the old code had the identical weakness for every href, so this is a follow-up, not a regression).
Hosted re-run on the branch (aspose-3d-foss/Aspose.3D-FOSS-for-Java, run 41180364402) confirms the fix
in production: the `live_readme_loss` finding on link `AGENTS.md` (false: it was carried, just
reworded) is gone, and the run now progresses to `source_reconciliation`, where it fails on a
separate, pre-existing, unrelated defect — `uncited_redundant_defer`: `DEFER_UNRESOLVED` on a
code_block that isn't a tracked example — progress, not a regression. That defect is a new,
unrelated fix-queue item (code_block disposition in source reconciliation), out of scope here.

**What this does NOT decide**: the newly-exposed `uncited_redundant_defer` defect, or the
unanchored-substring-match follow-up noted above; neither is fixed in this branch.

**Where the detail lives**: `src/repo_presenter/readme/composition/coverage.py`,
`src/repo_presenter/readme/repair/accounting.py`, `src/repo_presenter/readme/review/independent_reviewer.py`,
`tests/readme/composition/test_link_carry.py`.

---

## 2026-10-31: link-budget word-count tiers, backed by a rerunnable calibration script (merged `fix/link-budget-tiers`)

**Decision**: merge `fix/link-budget-tiers` to main (merge commit, non-fast-forward since the branch
had diverged from a since-merged main). `link_budget.py`'s `_automatic_total` replaces the flat
`AUTOMATIC_TOTAL_CAP=4` ceiling on auto-inserted Aspose links with word-count tiers
`(300,2),(500,3),(2000,4),(3000,5)`, else 6, each still clamped to `min(tier_value,
AUTOMATIC_TOTAL_CAP)`.

**Why**: aspose.org's own sealed candidates carry 4-5 contextual Aspose links against this project's
flat ceiling of 2-3 for a typical-sized README, and the flat tiers were producing deterministic BC-06
failures (hosted Words-.NET: "4 Aspose links exceed the ceiling of 3") before a candidate ever reached
model review.

**Evidence quality fix**: a fresh agent's first review found the tier logic itself sound (exact
boundaries traced and matched by test, cap clamped everywhere, monotonically no worse than the old
tiers for any word count under the default cap, 137+121+331 tests passing) but raised a CONCERN per
AGENTS.md ("evidence records come from tooling, never from model narration"): the docstring and a
test docstring asserted specific numbers (35 candidates, 586-word minimum, "23 of 35" failures) with
no script or artifact in the repo a reviewer could rerun to check them. Fixed by adding
`scripts/link_budget_calibration.py`, a read-only script that measures the real aspose.org sibling
checkout and prints the same counts on demand; the docstrings now cite it and state what it reports
as of 2026-10-31 rather than asserting fixed prose. Rerunning it (in an isolated worktree, to avoid a
branch-checkout race with concurrent verification agents in the shared working directory) gives: 35
candidates, none under 586 visible words, 33 of 35 needing exactly 4 contextual links (1 needs 5, 1
needs 1); under the old tiers previously shipped on main, 23 of 35 fail BC-06 with zero verified
examples; under these new tiers, only 1 of 35 still fails (the one needing 5 against a cap still
fixed at 4 — a real residual gap, not fixed here). A second fresh-agent pass on this follow-up
commit confirmed the script is genuine (not hardcoded) and its output matches the docstrings
exactly, with 455 (`tests/readme/composition/ tests/readme/validation/`) plus 140
(the two specific files) tests passing — PASS, no concerns.

**Evidence (hosted re-run from the branch, not main)**: aspose-words-foss/Aspose.Words-FOSS-for-.NET
(run 41180018042) previously failed deterministically on BC-06 before this fix; on the branch it
clears BC-06 and reaches `presentation_planning`, where it now fails on a separate, pre-existing
model-output defect (the model assigns several `link_target:NNN` ids to more than one citation) —
progress, not a regression, and a new, unrelated fix-queue item (duplicate link-target assignment at
presentation-planning), out of scope here.

**What this does NOT decide**: the newly-exposed duplicate-link-target-assignment defect, or the
residual words/net-shaped gap (needs 5 contextual links, cap stays at 4) — neither is fixed here.

**Where the detail lives**: `src/repo_presenter/readme/composition/link_budget.py`,
`scripts/link_budget_calibration.py`, `tests/readme/composition/test_siblings.py`,
`tests/readme/validation/test_registry_checks.py`.
