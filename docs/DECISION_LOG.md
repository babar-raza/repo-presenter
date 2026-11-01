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

---

## 2026-10-31: structural parity measurement and durable-bundle counts merged (`feat/aspose-parity`, `feat/matrix-durable-bundles`)

**Decision**: merge both to main. `core/aspose_parity.py` + `scripts/aspose_parity.py` measure how
close our candidate is to the equivalent finalized aspose.org README — counts (lines, code fences,
`<details>` blocks, links, Aspose links, Mermaid diagrams) and heading *names*, read either from an
explicit `--readme` path or restored from this repo's own durable bundle ref via `export_bundle`,
compared against the sibling aspose.org checkout. `core/portfolio_matrix.py` gains
`stored_bundle_refs(remote)` (one read-only `git ls-remote`) and `MatrixRow.stored_r`/`stored_l`, so
`scripts/portfolio_status.py` can report how many repositories actually have a durable bundle, not
just a pipeline-level record state.

**Why**: the sibling `aspose.org` checkout is private/read-only and must never have its body text
copied into this public repository (only counts and heading names may ever leave it); the portfolio
matrix's existing three sources (registry, record state, `candidates/`) did not yet surface the
durable-bundle layer added earlier this session.

**Evidence**: two different, fresh agents independently reviewed each diff cold. For
`feat/aspose-parity`: read `measure`/`compare`/`render` line by line and confirmed the only four
`print()` call sites in the whole diff emit counts, ratios, a bool, or heading names — never body
prose, never a link URL, never a code-block body; ran the real CLI against the live sibling checkout
(6 repositories) and inspected every printed line to confirm no leak; 7/7 tests pass. One non-blocking
defense-in-depth nit: `reference_path` does not itself validate `family`/`platform` against
path-traversal characters (relies on upstream registry validation, whose platform regex technically
permits a literal `..` token) — can resolve at most one directory higher inside the already-trusted
aspose.org reports tree, never escape it, and requires a contrived entry in this repo's own
first-party `registry.json`, not externally reachable input; tracked as a fix-queue follow-up, not
blocking. For `feat/matrix-durable-bundles`: confirmed `stored_bundle_refs` is read-only (a single
`git ls-remote`), that the push side (`publish_bundle`) and read side use the identical `bundle_ref`
function so Lane R/L counts cannot cross-contaminate, that `build_matrix`'s new parameter defaults to
`()` with five pre-existing call sites proving backward compatibility by actually passing, and that
8/8 new tests plus 668/668 across `tests/core/` pass with no collateral breakage.

**What this does NOT decide**: the `reference_path` defense-in-depth nit is not fixed here.

**Where the detail lives**: `src/repo_presenter/core/aspose_parity.py`, `scripts/aspose_parity.py`,
`tests/core/test_aspose_parity.py`, `src/repo_presenter/core/portfolio_matrix.py`,
`scripts/portfolio_status.py`, `tests/core/test_portfolio_matrix.py`.

---

## 2026-10-31: `presentation_planning`'s own `recover=` is now actually wired (merged `fix/presentation-planning-recover-wiring`)

**Decision**: merge `fix/presentation-planning-recover-wiring` to main. `cascade.py`'s `_run_planning`
now passes `recover=recover_planning_output` into its `run_job` call.

**Why**: `planning.py`'s `recover_planning_output` (combining `recover_duplicate_link_assignments`
and `recover_uncited_capability_titles`) already existed, documented as "the single `recover=`
combining both deterministic last resorts" — but nothing ever imported or passed it into the one
`run_job` call site that runs presentation_planning. Dead code, never reachable on a real run. This
is exactly the duplicate-link-target-assignment item the `fix/link-budget-tiers` merge surfaced and
left open (see the entry above): once the model assigns the same `link_target` fact to more than one
`links` entry and repeats the mistake on its own re-ask, the job had no recovery and failed outright
with `OutputRejectedError`, refusing the whole candidate.

**Evidence**: a fresh agent, cold, in an isolated worktree, independently confirmed: the diff is
exactly the claimed one-line `recover=recover` wiring plus its import, with no unrelated changes;
`recover_duplicate_link_assignments` keeps the first assignment of each target and drops later
repeats without mutating the caller's dict; the two new tests
(`tests/readme/composition/test_planning_recovery.py`, 5 unit tests on the recovery functions
directly, and `tests/test_cascade_s9.py`'s new
`test_a_persistent_duplicate_link_assignment_is_recovered_at_presentation_planning`, a full
`run_cascade` integration test with a fake model that repeats the duplicate-link plan on both
attempts) pass; the falsifier (temporarily removing just the `recover=recover,` kwarg) reproduces the
exact live failure text verbatim (`output rejected twice; last rejection: link 'link_target:001' is
assigned more than once; never the same target twice`) before the wiring is restored; the full suite
is 3447 passed, 13 skipped (up from 3441, +6 new tests), exit 0. The reviewer also confirmed the
safety property directly from `run_job`'s own code: `recover`'s correction is re-parsed from the raw
rejected reply (never an aliased live object) and re-validated from scratch through the identical
`plan_checks` before being accepted — it is never trusted on `recover`'s own say-so, so it can only
ever strip an exact duplicate repeat or add a citation whose fact value already literally spells the
title's term; a model emitting anything else still fails outright, not silently waved through.

**Evidence (hosted re-run from the branch, not main)**: aspose-words-foss/Aspose.Words-FOSS-for-.NET
Lane R (run 41204961354). The durable record (`refs/repository-presenter-state/records/
aspose-words-foss__Aspose.Words-FOSS-for-.NET`) shows `failure.detail` for this run names no
duplicate-link-target error anywhere; the candidate now reaches `independent_review` and fails there
on a separate, pre-existing, already-documented reviewer-contract issue (`finding F02: a contradiction
finding must cite at least one product fact`, the same shape recorded in the 2026-10-27
reviewer-calibration data under `docs/investigations/`), classified `transient`/retryable — progress,
not a regression, and unrelated to this fix.

**Open follow-up, noted but not acted on**: the same reviewer flagged that `scripts/run_lane_r_planning.py`
(a standalone manual debug script) and `readme/repair/loop.py`'s `_repair_plan` (which looks up an
already-accepted plan via a different job, `targeted_repair`) also reference the `presentation_planning`
prompt manifest without this `recover=`; neither is the automated `run_cascade` pipeline this bug lived
in, so both are out of scope here — a possible future card, not a defect in this one.

**What this does NOT decide**: the `independent_review` F02 contract issue surfaced on this hosted
re-run is not fixed here; neither is the `run_lane_r_planning.py`/`repair/loop.py` follow-up.

**Where the detail lives**: `src/repo_presenter/cascade.py`,
`src/repo_presenter/readme/composition/planning.py` (`recover_planning_output`,
`recover_duplicate_link_assignments`, pre-existing, now wired),
`tests/readme/composition/test_planning_recovery.py`, `tests/test_cascade_s9.py`.

---

## 2026-11-01: `independent_review` F02 (Words-.NET) investigated — not a bug, no fix made

**Finding**: the fix-queue item opened by the `fix/presentation-planning-recover-wiring` merge
(aspose-words-foss/Aspose.Words-FOSS-for-.NET, run 41204961354, `finding F02: a contradiction
finding must cite at least one product fact (not only inherited text)`) is the reviewer's own
anti-circularity rule (`reply.py`'s `_finding_errors`, `needs_fact` for `claim_kind == "contradiction"`)
working as designed, not a defect.

**Evidence**: downloaded the run's own evidence artifact and read the real rejected reply
(`llm_cache/calls/190578db959d.rejected-2.json`). The model's `F02` finding (`claim_kind:
"contradiction"`) claims the authored `scope_limitations` text wrongly credits the commercial
edition with "document comparison, mail merge, and document protection," and cites only
`inherited_unit:067.list` (the live README's own inherited feature list) as evidence — no extracted
product fact. The deterministic check correctly refuses this: citing the README's own unverified
prose as proof the README is wrong is circular, exactly the shape of self-grading
`docs/MISSION_AUTHORITY.md`'s new "Do not repeat the predecessor projects' mistakes" section (lesson
1) warns against. Loosening the rule, or adding a `recover=` that drops/rewrites the finding to make
the reply pass, would risk hiding a genuine defect the same way the old repo's acceptance-integrity
bug did — the two candidate "fixes" considered (drop the finding and flip to ACCEPT when
`findings` empties; backfill a synthetic product-fact citation) were both rejected for this reason,
not attempted.

**What this does NOT decide**: whether a real `capability`/`format`-kind extracted fact *should*
exist for "document comparison"/"mail merge are not in this FOSS package" (which would let a future
correct finding cite it) is a separate, unexplored extractor-scope question, not resolved here. The
record's own `transient`/retryable classification stands: a plain re-run may simply get a compliant
reply from the model on its own.

**Where the detail lives**: `src/repo_presenter/readme/review/reply.py` (`_finding_errors`,
`needs_fact`), `src/repo_presenter/readme/review/llm_review.py` (the `independent_review` `run_job`
call site, confirmed to have no `recover=` wired — deliberately left that way here).

---

## 2026-11-01: installation code block omitted when superseded by a contradicted install command (merged `fix/installation-contradicted-command-omit`)

**Decision**: merge `fix/installation-contradicted-command-omit` to main. `normalize()`'s generic
"destination renders nothing" fold now folds to `OMIT_UNSUPPORTED` (citing the contradicted fact)
instead of `DEFER_UNRESOLVED` when `destination == "installation"`, `rendering_fact_ids` comes back
empty, and a CONTRADICTED `install_command` fact exists.

**Why**: measured live (aspose-3d-foss/Aspose.3D-FOSS-for-Java, hosted run 41180364402): the only
`install_command` fact is CONTRADICTED and this ecosystem (plain Maven/Gradle) has no
`package:distribution.*` fallback, so `rendering_fact_ids("installation", ...)` came back empty for
six units (three Maven/Gradle dependency snippets and their lead-in paragraphs) even though
`renderer.py`'s own `_installation()` still prints a real sentence here ("The package `X` is not yet
published..."). The model's own `SUPERSEDE_REDUNDANT` answer was substantively correct; normalize()
force-reverted it to `DEFER_UNRESOLVED`, and `placement_errors`'s own `uncited_redundant_defer` then
refused the three code_block units outright across all 3 asks — an unwinnable loop.

**Evidence**: downloaded the real hosted-run evidence artifact and reproduced the exact failure
against the real `facts.json`/model reply before writing anything (not guessed). 3 new tests in
`test_dispositions.py`, including a negative control (no CONTRADICTED fact at all keeps the prior
`DEFER_UNRESOLVED` behavior, untouched). Falsifier: reverting just the new branch reproduces the
exact live rejection (`DEFER_UNRESOLVED` instead of `OMIT_UNSUPPORTED`) in the new test, nothing else.
A fresh agent, cold, in an isolated worktree, independently confirmed: diff scope exactly matches the
claim; `command_block_units` never matches the xml/kotlin/groovy-fenced Maven/Gradle blocks (so the
separate "a command block is never OMIT_UNSUPPORTED while build/install facts exist" guard never
fires, despite this repo having 6 SUPPORTED `build_test_asset` facts); both `_omission_gap` and the
`UNCITED_PROSE_OMIT` check independently confirmed to pass the fix's output for both `code_block` and
`paragraph` kinds; full suite 3450 passed, 13 skipped, exit 0 (matching the commit's own claim). One
noted, unexercised theoretical edge case (a CONTRADICTED install_command fact coexisting with a total
absence of any `package:name` fact) — not found possible in any real extractor, not blocking.

**Evidence (hosted re-run from the branch, not main)**: aspose-3d-foss/Aspose.3D-FOSS-for-Java Lane R
(run 41233168620). The durable record's `failure.detail` for this run names no
`uncited_redundant_defer`/`DEFER_UNRESOLVED` anywhere; the candidate now reaches `independent_review`
and gets a full REJECT with 5 unrelated content-quality findings (F01–F05, across
`documentation_resources`/`scope_limitations`/`development_testing`) — progress, not a regression,
and out of scope here.

**What this does NOT decide**: the 5 content-quality findings this hosted re-run surfaced are not
investigated or fixed here.

**Where the detail lives**: `src/repo_presenter/readme/reconciliation/dispositions.py`
(`_matching_unresolved_install` is a separate, related fix from the same session, not part of this
one — see its own entry), `tests/readme/reconciliation/test_dispositions.py`.

---

## 2026-11-01: installation code block deferred when matching an UNRESOLVED install command (merged `fix/unresolved-install-command-defer`)

**Decision**: merge `fix/unresolved-install-command-defer` to main. `normalize()`'s "installation"
fold now backfills a citation and keeps `DEFER_UNRESOLVED` (instead of leaving it uncited) when a
code block's own command lines literally match a genuinely UNRESOLVED `install_command` fact;
`placement_errors`'s own `uncited_redundant_defer` exemption is widened the same way `example_status`
already works -- keyed by the unit itself, never by what a disposition cites.

**Why**: measured live (aspose-page-foss/Aspose.Page-FOSS-for-Python, hosted run 41137901672, unit
013.code_block "pip install aspose-page-foss"): `install_command:pip` is UNRESOLVED (the registry
could not confirm ownership) -- `DEFER_UNRESOLVED` is the objectively correct disposition for this,
but the only existing exemption from `uncited_redundant_defer` was a tracked example's own UNRESOLVED
status, never an install_command's, so the model's answer was refused outright across all 3 asks.

**Evidence**: 3 new tests including a dedicated gaming-resistance test (a disposition citing the
right UNRESOLVED fact on the WRONG, unmatched code block gets no exemption and stays rejected,
proving `unresolved_install_units` is keyed by the unit's own text, never by what a disposition
claims). Falsifier confirmed. A fresh agent, cold, in an isolated worktree, independently verified:
diff scope, the literal-match helper's correctness, the gaming-resistance property, full suite 3453
passed/13 skipped/exit 0. One noted, out-of-scope limitation: the earlier (already-merged) CONTRADICTED
branch in the same fold is a global check (any CONTRADICTED install_command fact anywhere in the
facts, not specific to the current unit) and would preempt this new UNRESOLVED branch for a repo
that happens to carry both a CONTRADICTED and an unrelated UNRESOLVED install_command fact
simultaneously -- a plausible but not-yet-observed shape, belonging to the earlier fix's own scope,
not fixed here.

**Evidence (hosted re-run from the branch, not main)**: aspose-page-foss/Aspose.Page-FOSS-for-Python
Lane R (run 41236483023). The durable record's `failure.detail` names no `uncited_redundant_defer`
anywhere; the candidate now reaches `independent_review` and fails there on an unrelated
`live_readme_loss` finding for the same code block -- progress, not a regression, a new, unrelated,
not-yet-investigated fix-queue item.

**What this does NOT decide**: the newly-exposed `live_readme_loss` finding, or the noted
CONTRADICTED/UNRESOLVED-coexistence limitation above.

**Where the detail lives**: `src/repo_presenter/readme/reconciliation/dispositions.py`
(`_matching_unresolved_install`), `tests/readme/reconciliation/test_dispositions.py`.

---

## 2026-11-01: .htm/.html format alias asserted deterministically (merged `fix/htm-html-format-alias`)

**Decision**: merge `fix/htm-html-format-alias` to main. `format_facts()` now synthesizes a
SUPPORTED `.htm` fact for any direction whose `.html` fact is SUPPORTED, unless real `.htm`
evidence already exists -- never the reverse, never overwriting real evidence.

**Why**: measured and recorded in this project's own `project/state.yaml` history
(aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript): the README correctly claims both `.html` and `.htm`
are recognized, but the product's own source only ever contains the literal string `"html"` in its
format-dispatch code, never also `"htm"` -- so the extractor only ever produced a fact for `.html`.
`.htm`/`.html` are the same format everywhere this tool has measured; this fold asserts that one
deterministic alias, not an inference from unverified prose.

**Evidence**: 3 new tests (positive case, an UNRESOLVED `.html` negative control, and a real-`.htm`-
evidence-is-never-overwritten negative control). Falsifier confirmed. A fresh agent, cold, in an
isolated worktree, independently verified: diff scope, correctness of the SUPPORTED-only guard, the
evidence-dict gap check, direction extraction, no duplicate/conflicting facts (confirmed with the
verifier's own constructed adversarial test), full suite 3453 passed/13 skipped/exit 0, and the
one-directional design as a deliberate, evidence-bounded scope limit rather than a gap. One
tangential, non-blocking finding: `format_overclaim`'s own loose substring matching already
tolerated `.htm` as a substring of `.html`, so this fix's practical value is less about unblocking
that specific detector and more about making the `FactsDocument` itself honestly reflect real `.htm`
support for any other consumer that reads `format` facts directly.

**Evidence (hosted re-run from the branch, not main)**: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript
Lane R (run 41236496887). The durable record's `failure.detail` names no `.htm`/format-overclaim
finding anywhere; the candidate now reaches `independent_review` and fails there on
`disposition_coverage` for `inherited_unit:037.html_block` ("View Selected API Surface") -- the
EXACT same renderer-owned-collapsible-wrapper shape independently found and fixed on
aspose-pdf-foss/Aspose.PDF-FOSS-for-Java this same session (`fix/renderer-owned-details-wrapper`),
confirmed directly: reproducing this run's own real facts/dispositions through that fix's
`normalize()` folds the unit to `SUPERSEDE_REDUNDANT` with zero errors -- a second, independent,
real-world confirmation of that fix, not a new open item.

**What this does NOT decide**: nothing new; the `disposition_coverage` finding this hosted run
surfaced is already covered by the separate, in-flight `fix/renderer-owned-details-wrapper`.

**Where the detail lives**: `src/repo_presenter/readme/evidence/facts/formats.py`
(`_htm_alias_facts`), `tests/readme/evidence/facts/test_formats.py`.

---

## 2026-11-01: a renderer-owned collapsible wrapper is no longer kept-but-unprinted (merged `fix/renderer-owned-details-wrapper`)

**Decision**: merge `fix/renderer-owned-details-wrapper` to main. `normalize()` now recognizes an
inherited `html_block` unit that IS the `api_reference`/`additional_examples` sections' own
`<details>/<summary>` collapsible wrapper (renderer.py's own fixed, unconditional
`API_SURFACE_SUMMARY`/`ADDITIONAL_EXAMPLES_SUMMARY` labels -- never the original README's wording)
and folds it from `VERIFIED_PRESERVE`/`VERIFIED_MOVE` to `SUPERSEDE_REDUNDANT`, but only when there
is exactly one opening-shaped and exactly one closing-shaped candidate per destination --
deliberately failing closed (no fold at all) on ambiguity rather than guessing.

**Why**: measured live (aspose-pdf-foss/Aspose.PDF-FOSS-for-Java, hosted run 41147002918): the
model kept `inherited_unit:050.html_block` ("View the Core API Surface") as VERIFIED_PRESERVE into
`api_reference`, but the renderer always prints "View the Complete Public API Surface" there
instead -- the preserved text never actually appeared, an unrepairable `disposition_coverage`
defect. A sibling unit's original wording happened to be byte-identical to the renderer's own
`additional_examples` label, which is exactly why this was never caught generally before: the same
shape, masked by coincidence on that one unit.

**Evidence, in three rounds, each closing a real gap a fresh independent verifier found cold**:
1. First version (shape-only match): an independent verifier found it would also fold a genuine,
   legitimate per-example "click to see output" `<details>` toggle an author might nest inside
   `additional_examples` -- a real, plausible idiom, not merely theoretical.
2. Second version (ordinal-extreme bound: lowest-ordinal open, highest-ordinal close): a second
   independent verifier reproduced concretely that if the model disposed the TRUE wrapper some
   other way (`OMIT_UNSUPPORTED`, destination `None`, invisible to the per-destination scan) while
   a nested toggle was disposed `PLACING` into the same destination, the "extreme" was just
   whichever nested toggle sorted first/last, and got wrongly folded.
3. Third, shipped version (cardinality-exactly-one): never guesses among ambiguous candidates --
   more than one `PLACING` match of a given shape for a destination means no fold for that side at
   all. A third independent verifier confirmed this closes the second verifier's exact reproduced
   scenario (multiple nested toggles), does not regress the original single-pair defect, and
   confirmed the one remaining, explicitly disclosed residual gap (a single nested toggle
   PLACING-disposed into the same destination while the true wrapper is independently routed to
   destination `None`) is genuinely as narrow as stated -- not hidden, not worse than disclosed,
   never observed live, and requires two independent, compounding model choices to construct at all.

Full suite green at every round (3454, 3455, 3455 passed respectively as the fix evolved; 13
skipped; exit 0 each time). Broader reconciliation/review/repair/cascade check: 676 passed.

**Evidence (hosted re-run from the branch, not main)**: aspose-pdf-foss/Aspose.PDF-FOSS-for-Java
Lane R, run 41237173263 -- the durable record's `last_transition.to_state` is **`ACCEPTED`**
(pipeline-level, not owner-reviewed; its `failure` field is stale from the PREVIOUS run, confirmed
by `last_transition.occurred_at` matching this run's own completion time, not the earlier failure's).
This fix alone cleared the last blocking defect for this specific candidate. Independently
corroborated on a second, different repository: aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript Lane R
(run 41236496887, surfaced while re-checking the separate `fix/htm-html-format-alias` merge) hit the
exact same `disposition_coverage` shape on a different unit ("View Selected API Surface"); confirmed
directly against that run's own real facts/dispositions that this fix resolves it too, with zero
`normalize()`/`placement_errors()` errors.

**What this does NOT decide**: the disclosed residual gap (single nested toggle + true wrapper
disposed to destination `None`) is not closed here, by design -- recorded as a known, narrow,
never-observed-live limitation rather than chased further, per this project's own stop rule and the
"forest, not trees" framing (`AGENTS.md` non-negotiable #8).

**Where the detail lives**: `src/repo_presenter/readme/reconciliation/dispositions.py`
(`_collapsible_wrapper_bounds`, whose own docstring carries the full three-round history),
`tests/readme/reconciliation/test_dispositions.py`.

---

## 2026-11-01: `live_readme_loss` on Page-Python's install snippet investigated — not a bug, no fix made

**Finding**: the fix-queue item opened by the `fix/unresolved-install-command-defer` merge
(aspose-page-foss/Aspose.Page-FOSS-for-Python, run 41236483023, `live_readme_loss [omission]: code
block 'pip install aspose-page-foss'`) is the independent reviewer's own accounting rule correctly,
by design, blocking a genuinely unverifiable install claim — not a defect.

**Evidence**: `install_command:pip`'s own real evidence (`facts.json`, downloaded from the earlier
hosted run): PyPI confirms a distribution named `aspose-page-foss` exists, but "the registry lists
no source repository to compare with this one" -- there is no way to confirm THIS repository
actually owns that published package name, as opposed to some unrelated third party. `DEFER_UNRESOLVED`
is deliberately excluded from `independent_reviewer.py`'s `ACCOUNTING_DISPOSITIONS`
(`{SUPERSEDE_REDUNDANT, CORRECT_WITH_EVIDENCE, VERIFIED_REWRITE, OMIT_UNSUPPORTED}`) -- a disposition
that itself means "the facts neither confirm nor deny this claim" cannot also "account for" the
content it defers, by the reviewer's own design; `dispositions.py`'s own `uncited_redundant_defer`
error message already states this consequence directly ("a deferral with no destination leaves it
unaccounted for later, as if the content had simply vanished"). The `fix/unresolved-install-command-
defer` merge fixed a real, different defect (the model's correct DEFER_UNRESOLVED answer being wrongly
*refused at S4* before it was ever recorded); it was never going to make this specific candidate seal,
because the underlying real-world fact -- an unconfirmable PyPI ownership claim -- correctly still
blocks sealing at S9/review, via a different, equally legitimate mechanism. Progress (the pipeline now
reaches review instead of failing at S4), not a regression, and not something a reconciliation/review
code change should paper over.

**What this does NOT decide**: whether `aspose-page-foss`'s PyPI listing could or should be reconciled
by other means (e.g. a maintainer updating the PyPI project's source-repository metadata) is a
registry/data question for the actual package maintainer, entirely outside this pipeline's scope.

**Where the detail lives**: `src/repo_presenter/readme/review/independent_reviewer.py`
(`ACCOUNTING_DISPOSITIONS`, `live_readme_loss_rule`, `_accounting_units`).

---

## 2026-11-01: 3D-Java's F01-F05 content-quality findings investigated — already-working repair loop, not a pipeline bug, no fix made

**Finding**: the 5-finding REJECT surfaced on aspose-3d-foss/Aspose.3D-FOSS-for-Java (run
41233168620, while live-checking `fix/installation-contradicted-command-omit`) is the repair
loop correctly, repeatedly firing against genuinely free-form, unsupported prose in S6-authored
text -- not a routing bug, not unused machinery, and not a single fixable root cause.

**Evidence**: downloaded the run's own `review_verdict.json`/`repairs.json`. All 5 findings
(F01, F03, F04, F05: `unsupported_claim`; F02: `contradiction`) carry `causal_stage: "S6"` and
`fact_ids: []` -- the reviewer's own "audit" trail shows some of the claim's distinctive terms do
match real SUPPORTED facts, but the *compound* sentence as a whole still asserts more than any
single fact confirms (e.g. F01: "the full API reference offers a complete, browsable reference
for all 266 public types" -- `266` and `reference.aspose.org` are each individually real, but
nothing confirms the reference is "complete" or "browsable"). `repairs.json` shows the repair
loop already fired across at least 5-6 distinct rounds, spanning `development_testing`,
`scope_limitations`, `key_capabilities`, `opening`, `documentation_resources`, and
`api_reference` -- correctly routed per `review/defect_bridge.py`'s own `causal_stage`-based
dispatch (confirmed: `S4_RULES = {"disposition_coverage"}`, everything else routes to S6, exactly
as documented) -- successfully resolving several named findings per round (e.g. `F10` repaired by
removing an unsupported "targeting runtime version 21" clause) while the model's own revised
prose kept introducing new overclaims elsewhere, re-raising a differently-labeled finding the next
round. Finding labels (F01, F02, ...) are per-round, not globally stable IDs, confirmed by the
same label appearing against different `section_id`s across different repair attempts.

**Why not fixed**: this is not a deterministic code defect with a single, boundable root cause --
it is the designed repair loop genuinely converging slowly against a repository whose live README
makes more free-form, unverifiable editorial claims than the round budget fully resolves in one
run. Per this project's own stop rule (two-plus rounds on the same finding class without full
convergence), this is recorded plainly rather than chased with a speculative fix; the available
remedies (raising `max_rounds`, or changing the repair prompt's own instructions) are policy/prompt
decisions with real cost tradeoffs, not a pipeline logic bug.

**What this does NOT decide**: whether `max_rounds` should be raised, or the repair prompt
improved, for repositories with this shape of content; not investigated further here.

**Where the detail lives**: `src/repo_presenter/readme/review/defect_bridge.py` (confirmed
correctly routing every `causal_stage` to the right repair dispatch), `src/repo_presenter/readme/
repair/loop.py`, this run's own `repairs.json`/`review_verdict.json`.

---

## 2026-11-01: native build-artifact extensions exempted from the wrong-name claim rule (merged `fix/file-like-native-build-extensions`)

**Decision**: merge `fix/file-like-native-build-extensions` to main. `claim_findings`/
`_prose_name_findings`'s own `_FILE_LIKE` regex now also exempts `.lib`, `.dylib`, `.o`, and
`.obj` -- the direct platform-siblings of the already-exempted `.dll`/`.so`/`.a` (Windows/Unix
shared and Unix static libraries), the exact same category of native build artifact.

**Why**: measured against aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp's own real candidate text
(`evidence/build/P1_PORTFOLIO_SCALE/.../lane_r_candidate.md`): the README honestly names the SAME
static-library artifact under both its Unix suffix (`libaspose_pdf_foss.a`, already exempted) and
its MSVC suffix (`aspose_pdf_foss.lib`, not exempted before this fix) -- the second form was
wrongly flagged as an unverified second package.

**Evidence**: reproduced directly against current code with the real sentence and the real CMake
`project()` identity (`aspose_pdf_foss`, itself confirmed by the README's own `.a` sibling
mention): `claim_findings` returns one finding before the fix, zero after. 5 new tests (4
parametrized over `lib`/`dylib`/`o`/`obj`, 1 negative control). Falsifier confirmed. A fresh agent,
cold, in an isolated worktree, independently re-verified the real-world false positive end to end
(reproducing it on `main`, confirming it's gone on the branch), the regex anchoring, the falsifier,
and the full suite (3466 passed/13 skipped/exit 0). One narrow, honestly-flagged, *unconfirmed*
residual concern: `.lib` is a plausible (but not observed in-portfolio) suffix for a legitimate
.NET/NuGet `X.Lib`-style sub-package name, which this exemption would now also hide if a README
ever falsely claimed one -- `.o`/`.obj`/`.dylib` carry no such risk the verifier could construct.

**Evidence (hosted re-run from the branch, not main) -- inconclusive, documented honestly**: two
live-check attempts (aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp run 41274861054, aspose-slides-foss/
Aspose.Slides-FOSS-for-Cpp run 41276299775) were both blocked by unrelated, pre-existing earlier-
stage defects before the pipeline ever reached the validation stage this fix touches: PDF-Cpp by
the already-documented BC-08 staleness issue (`docs/DECISION_LOG.md`'s own `nineteenth_fix_live_
verified_insufficient_deeper_staleness_cause_found` entry, `project/state.yaml`); Slides-Cpp by a
separate S4 `uncovered_supersession` rejection on an unrelated PowerShell install snippet. Neither
run's own failure reason names `claim_findings`/a wrong-name finding, so this fix cannot be shown
to have caused a new regression on either, but it also cannot be shown to have let either
candidate progress further -- this specific defect may never have caused an *observed* hosted
failure on its own (both repos' earlier hosted attempts were already blocked by other issues first).
Merging on the strength of the direct, repeated, cold-reproduced code-level evidence (mission's own
"evidence from tooling" bar, satisfied without a hosted run) rather than spending further hosted-run
budget chasing a clean end-to-end confirmation this defect's own shape does not require.

**What this does NOT decide**: the BC-08 staleness issue (PDF-Cpp) and the PowerShell
`uncovered_supersession` issue (Slides-Cpp) are pre-existing and not addressed here.

**Where the detail lives**: `src/repo_presenter/readme/validation/claims.py` (`_FILE_LIKE`),
`tests/readme/validation/test_claims_surface.py`.

---

## 2026-11-01: an omission commenting on a contradicted example gets its citation backfilled (merged `fix/omit-companion-contradicted-example`)

**Decision**: merge `fix/omit-companion-contradicted-example` to main. `normalize()` now backfills
the citation for an uncited `OMIT_UNSUPPORTED` paragraph that comments on the code example
directly above it in the same section, when that example's own fact is CONTRADICTED -- scoped to
the single nearest preceding code_block, regardless of its polarity, so it never reaches past a
fine code_block to cite an earlier, unrelated one.

**Why**: measured live (aspose-pdf-foss/Aspose.PDF-FOSS-for-Python, hosted run 41142404776, unit
164.paragraph, "Use `dry_run=True`..."): the model's own disposition and rationale were already
correct in substance ("no fact supports the claim about dry_run or keep parameters"), but
`fact_ids` stayed empty because neither parameter name is a package or link_target fact's own
value, the only two kinds the existing `_spelled_supported_facts` backfill (added earlier this
session) can match. The example this paragraph comments on is CONTRADICTED -- the clearest
possible citation available, deterministically findable from the unit's own position.

**Evidence, in three rounds, each closing a real gap found cold**:
1. First version (search backward for the nearest preceding CONTRADICTED code_block, skipping
   non-contradicted ones): a first independent verifier found it could misattribute a paragraph
   to a FARTHER, unrelated CONTRADICTED example when a NEARER, non-contradicted code_block sits
   between them -- reproduced directly against a real section shape in aspose-words-foss/.NET's
   own facts.json (a NuGet snippet, a paragraph, a "build from source" alternative, another
   paragraph).
2. Second, shipped version (find the single nearest code_block regardless of polarity; cite it
   only if that exact one is contradicted): a second independent verifier confirmed this closes
   the first gap (constructed a 3-code_block adversarial case; confirmed the 2-code_block
   nearer-one-contradicted case still works) with no further issue found.
3. While live-checking this exact fix, a SECOND real occurrence of the same shape surfaced on the
   SAME repository (run 41276313821, unit 193.paragraph commenting on 191.code_block's own
   CONTRADICTED example) -- but did not get backfilled. Root-caused directly (not guessed):
   `reconciliation_batches` splits units into contiguous ranges, unit 191 fell in an earlier batch
   than 193, and `reconciliation_batch_facts` deliberately narrows `normalize()`'s own view of
   `inherited_unit` facts to the current batch only (an existing, documented design that prevents
   a different real bug -- `binding_errors` demanding full coverage per batch). The companion
   code_block was simply invisible to this call, so the fold safely did nothing -- confirmed by
   feeding the real batch-scoped facts for this exact case and reproducing the exact rejection
   byte-for-byte. This is a genuine coverage limit (a missed backfill, never a wrong one), not a
   correctness bug; disclosed directly in the function's own docstring rather than hidden, with a
   dedicated test proving the cross-batch case is a safe no-op. Fully closing it needs threading
   whole-document unit visibility into this fold without reopening the batch-isolation design --
   a separate, more general problem (any fold needing cross-batch context would hit it), logged
   as a new fix-queue item, not attempted here.

Full suite green at every round (3464, 3465, 3466 passed respectively; 13 skipped; exit 0 each
time). Broader reconciliation/review/repair/cascade check: 684 passed.

**What this does NOT decide**: the batch-boundary coverage limit (any fold needing visibility
into a different reconciliation batch's own units hits the same wall) is logged as its own,
separate, more general fix-queue item -- not attempted here.

**Where the detail lives**: `src/repo_presenter/readme/reconciliation/dispositions.py`
(`_preceding_contradicted_example`, whose own docstring carries the full three-round history),
`tests/readme/reconciliation/test_dispositions.py`.

---

### 2026-11-01: Slides-Cpp `uncovered_supersession` on a NuGet install snippet -- investigated, root-caused as a model-compliance gap, no pipeline fix (reverted before merge)

**Decision**: no code change. Documented the investigation directly in
`src/repo_presenter/readme/reconciliation/dispositions.py`'s own top-of-file comment, next to the
`RECOVERED_COVERAGE_RATIONALE`/`_recover_uncovered` porting note it extends.

**Why**: the pre-existing, already-blocked live check from `fix/file-like-native-build-extensions`
(aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp, run 41276299775) was investigated to completion.
Real failure (durable state record, `failure.detail`, read directly): `inherited_unit:033.code_block`
(a PowerShell `Install-Package Aspose.Slides.Cpp.FOSS` snippet under "Install From NuGet on
Windows") was `SUPERSEDE_REDUNDANT` into `installation`, which renders only the verified CMake
command -- rejected as `uncovered_supersession` three attempts running. Read the ledger directly:
the model's own narrowed retry oscillated between that same `SUPERSEDE_REDUNDANT` and an equally-
rejected free-form `DEFER_UNRESOLVED` (refused by `uncited_redundant_defer`), never once trying the
one, zero-ambiguity escape hatch the rejection text names explicitly on both attempts: `VERIFIED_
MOVE`/`VERIFIED_PRESERVE` into `development_testing` -- a `PLACING`-into-`placeable` disposition
`_fold_uncovered`'s own existing branch accepts immediately, no further gap, no retry needed.

Found this is a documented, half-ported gap: the old repository's own `_recover_uncovered` fold
(a last-attempt deferral with a typed `RECOVERED_COVERAGE_RATIONALE` sentinel, per TC-DSP-01) was
never ported here -- confirmed by this module's own top-of-file comment and by
`tests/readme/reconciliation/test_patch.py`'s wave-4 3D-Java fixture, which still simulates the
fold's effect by hand because it does not exist. Implemented it (first as a new `_fold_uncovered`
branch, then relocated to the later, more specific per-entry pass after seeing it fire too early
and swallow the already-fixed `contradicted_install`/`unresolved_install_command` backfills) and
reproduced the real defect fixed, byte-for-byte, against the real downloaded `facts.json`.

**Reverted before merge**: `test_supersede_redundant_by_installation_is_still_refused_when_the_
literal_block_is_not_what_it_renders` (same file, pre-existing, already guarding a *different*
prior regression) failed. Its own docstring: fixing an earlier over-eager force-revert "must not
paper over the real gap" -- a `PackageReference` XML snippet in the exact same shape (`SUPERSEDE_
REDUNDANT` into `installation`, gap persists, `ids` non-empty) must stay a loud, blocking
`uncovered_supersession`, not a silent deferral, because the *same* zero-ambiguity escape hatch
(`VERIFIED_MOVE` into `development_testing`) is still reachable there too. Checked directly: both
shapes are structurally indistinguishable from the pipeline's own point of view (`nearest_holdable`
resolves a valid home for both; neither is a tracked example; neither matches an UNRESOLVED install
fact). No principled rule separates "truly stuck" from "available escape not taken" here, so any
fold general enough to fix the Slides-Cpp case reopens the regression the sibling test exists to
block. Per AGENTS.md's non-negotiable #5 ("no agent...may silently overrule its own negative
finding"), did not narrow the fold further to dodge the conflict without evidence that a narrower
rule is actually correct -- reverted the code change entirely and kept only the documentation.

This is recorded as what it is: a genuine, cold-reproduced, real-evidence finding that is a model-
compliance gap (the model had the exact fix named for it, twice, and did not take it), not a
pipeline defect -- the same category as the already-logged diagram-steer model-compliance limit,
recorded plainly rather than forced into a fix that would reopen an already-settled regression.

**Evidence**: real downloaded run artifacts (`gh run download 41276299775`), the real durable
state record (`git show refs/repository-presenter-state/records/aspose-slides-foss__Aspose.Slides-
FOSS-for-Cpp:record.json`), the real `llm_cache/ledger.jsonl` (all three reconciliation attempts
for the failing batch, confirming the oscillation), and a cold repro script run twice (against the
unfixed code, reproducing the real rejection byte-for-byte; against the reverted code, confirming
no regression). Full suite: 3471 passed, 13 skipped, exit 0, confirmed unchanged by the documentation-
only diff.

**What this does NOT decide**: whether the `source_reconciliation` prompt/narrowing template
itself should be strengthened to push the model toward the named escape hatch more mechanically --
not attempted here, and not clearly warranted given the diagram-steer precedent of not chasing
model compliance with prompt hacks absent stronger evidence it would generalize.

**Where the detail lives**: `src/repo_presenter/readme/reconciliation/dispositions.py`'s own
top-of-file comment (`RECOVERED_COVERAGE_RATIONALE`).

---

### 2026-11-01: six-repository portfolio-impact sweep on `main` -- one confirmed real win, one new root-caused fix, two confirmed-recurring deferrals, one not-a-bug, one new pending candidate

**What this does**: dispatched fresh `present.yml` (`both` lanes) runs on `main` for six repositories
spanning five ecosystems (aspose-cells-foss/Python, aspose-slides-foss/.NET, aspose-words-foss/.NET,
aspose-pdf-foss/Cpp, aspose-email-foss/Cpp, aspose-3d-foss/.NET) to measure today's merged fixes'
real portfolio effect and surface new defects, per AGENTS.md non-negotiable #4 (blast-radius query
before, targeted recheck after). All six GitHub Actions jobs showed red; triaged each one's real
durable-state record individually rather than taking the red job status at face value.

**Finding 0 -- a real, confirmed portfolio win, and an operational correction to this session's own
"authoritative signal" heuristic**: aspose-cells-foss/Aspose.Cells-FOSS-for-Python's Lane R is
genuinely **ACCEPTED** on `main` as of this sweep (`last_transition.to_state: ACCEPTED`,
`occurred_at` matching this exact run, `present: ... lane R exit 0, durable state ACCEPTED` read
directly from the hosted job's own log) -- the job showed red only because Lane L failed
separately on 3 genuine, correct findings about the real upstream repository (a failing example,
an unverified TSV format claim, a broken `RELEASE_NOTES.md` link; Lane L's own "may not repair"
design, not a pipeline defect). Discovered, and corrected for, a real gap in this session's own
"trust `last_transition`, not `failure.detail`, for freshness" rule: when a repository's record
is ALREADY in a terminal failure state (e.g. `FAILED_INTERNAL` from a prior run) and a NEW run
fails again, `present_transaction.py`'s own `_commit_outcome` (`hops = _failure_hops(current_state)`
comes back empty, since the registry has no `FAILED_INTERNAL -> FAILED_INTERNAL` self-loop) takes
a deliberate, documented fallback path (`refresh_failure`) that updates `failure.detail`/
`failure.occurred_at` WITHOUT writing a new `last_transition` -- by design ("the record must still
describe THIS failure, not the first one it ever recorded"), not a bug. Confirmed this against
all five of today's remaining failures via `recent_trigger_dedup_keys[run:<id>]` matching
`active_transaction_id`: freshness must be checked via the dedup-key match or `failure.occurred_at`
when `last_transition.occurred_at` predates the run, never via `last_transition` alone when `state`
is a repeat terminal failure. Recorded here since it would otherwise mislead any future investigation
that repeats this session's own prior heuristic unconditionally.

**Finding 1 -- real, root-caused, fixed**: see `fix/verified-move-heading-identity-citation`
(aspose-slides-foss/Aspose.Slides-FOSS-for-.NET, run 41284665612) -- a third shape of the
already-known heading-accounting gap (`VERIFIED_MOVE`/`VERIFIED_PRESERVE`, not just
`SUPERSEDE_REDUNDANT`/`OMIT_UNSUPPORTED`), where a citation backfill alone cannot close the gap
because `disposition_coverage_rule` never consults `fact_ids` for a kept disposition. Fixed,
tested, falsifier-confirmed; cold independent verification in progress before merge.

**Finding 2 -- confirmed recurring, already deferred, not re-investigated**:
aspose-email-foss/Aspose.Email-FOSS-for-Cpp's `duplicate_paragraph` finding on this run is the
exact same `inherited_unit:043.paragraph` (API Reference) case this decision log's own
`twentieth_fix_second_live_round_found_a_second_false_positive_generalization_reverted` entry
already found, root-caused, and deliberately deferred pending a per-citation (not per-section)
generalization. No new investigation added; the existing deferral stands.

**Finding 3 -- same shape as an already-decided not-a-bug, not re-investigated in full**:
aspose-3d-foss/Aspose.3D-FOSS-for-.NET's three `llm:factuality`/S6/`fact_ids: []` findings (format-
support overclaims) match this log's own `3D-Java F01-F05... already-working repair loop, not a
pipeline bug` entry's shape exactly (same causal stage, same claim kind, a repair round already
fired and changed the text). Treated as the same category without a full fresh reproduction,
given the strength of the existing precedent; not logged as a separate root-cause investigation.

**Finding 4 -- already known, not re-investigated**: aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp's
`BC-08` failure is the same already-extensively-investigated (eighteenth/nineteenth fix chain),
deliberately deferred cache-staleness/content-dropping defect. No new ground covered.

**Finding 5 -- new, pending, NOT fixed (insufficient evidence for a fix yet)**:
aspose-words-foss/Aspose.Words-FOSS-for-.NET's Lane R failed at `independent_review` itself (not
reconciliation): the model's own REJECT reply's finding F05 (`claim_kind: contradiction`, citing
only `inherited_unit:013.paragraph`) was rejected twice running (job's own 2-attempt limit, no
narrowing mechanism) for "a contradiction finding must cite at least one product fact (not only
inherited text)". Read directly: F05's claim ("adds the full feature set of Aspose.Words for
.NET... not present in this FOSS package") is a correct, self-evident FOSS-vs-commercial-edition
contradiction that plausibly only needs a product/identity fact backfilled alongside the inherited
citation -- but this is a single occurrence, not confirmed recurring, so per this session's own
standing discipline (never fix from one data point) this is logged as a new fix-queue candidate,
not acted on.

**Where the detail lives**: durable-state records for each of the six repositories (`git show
refs/repository-presenter-state/records/<slug>[@lane-l]:record.json`); `fix/verified-move-
heading-identity-citation`'s own commit for Finding 1; this entry for Findings 0 and 5.

---

### 2026-11-01: `fix/verified-move-heading-identity-citation` merged -- a kept heading the renderer never prints is accounted for as a last resort, two real cold-review gaps closed first

**Decision**: merged to `main`. A heading kept `VERIFIED_PRESERVE`/`VERIFIED_MOVE` into a
placeable section, which `placement.py`'s own `renders_verbatim()` structurally never prints as
written, is now accounted (disposition flipped to `SUPERSEDE_REDUNDANT`, citing the repository's
own identity fact) at S9 (`readme/repair/accounting.py`'s `account_unprinted_units`), but ONLY as
a true last resort: after the existing, more precise `_decide`/`_heading_facts`/`_example_heading`
machinery has already had its chance, and only when the heading carries no code-block payload
relationship (`_payload_row`) and its destination is genuinely included in the finished plan.

**Why, and the two real gaps a cold review found before this was safe to merge**: this is
Finding 1 from the six-repository portfolio sweep (above) -- a third shape of the already-known
heading-accounting gap, found on aspose-slides-foss/Aspose.Slides-FOSS-for-.NET run 41284665612.
The first attempt (reconciliation/dispositions.py, a new `normalize()` fold, same shape as the
existing SUPERSEDE_REDUNDANT/OMIT_UNSUPPORTED heading-identity fold) went through one full cycle
of real-data reproduction, falsifier, and full-suite-clean before its own first cold, independent
verification -- which found a real, concrete bug: gating the disposition-flip on `not cited` left
an ALREADY-cited `VERIFIED_MOVE`/`VERIFIED_PRESERVE` heading untouched, since
`disposition_coverage_rule` never consults `fact_ids` for a kept disposition at all. Fixing that
gap, a full-suite run surfaced a SECOND, more serious problem self-caught, not by the verifier:
2 pre-existing `tests/test_cascade_s9.py` tests regressed, revealing the fix was in the wrong
place entirely -- `normalize()` runs at S4, too early, pre-empting an already-existing, more
precise S9 mechanism (`_decide`'s own heading branch) that cites a section-specific fact (e.g. a
`public_symbol`) whenever one exists. Relocating the fix into `accounting.py`'s own decision chain
(as a last-resort fallback, not a competing early fold) then broke 3 MORE pre-existing negative-
control tests (`test_a_heading_with_no_facts_to_cite_is_left_alone`,
`test_a_kept_heading_over_an_example_the_readme_does_not_print_is_left_alone`,
`test_a_heading_before_an_omission_no_fact_contradicts_is_left_alone`) -- each one proof that this
module's own design philosophy ("no fact is invented"; a unit is left alone, not papered over,
when nothing precise can be found) would be violated by a fallback too eager to fire. Two guards
(`_payload_row(...) is None`; destination actually in the plan's own included sections) close
exactly that gap, each earned by one of the three broken tests, not guessed in advance.

**Evidence**: real downloaded artifacts (`gh run download 41284665612`) reproduced the exact
defect (`inherited_unit:029.heading`, "### Why the `!`", VERIFIED_MOVE into `additional_examples`,
no example/payload relationship at all -- a heading over explanatory prose) against the real
`facts.json`/`dispositions.composed.json`. Falsifier confirmed twice (once per location). Full
suite clean at every stage (3471 -> 3475 passed, 13 skipped, exit 0 throughout). TWO full,
independent cold reviews in isolated worktrees, the first finding a real gap and the second
(after relocation) finding none, including its own adversarial hunt for a parallel masking risk
(a sibling uncited paragraph/list) that it confirmed, empirically, already existed identically on
`main` before this change -- not newly introduced.

**What this does NOT decide**: whether `live_readme_loss_rule`'s own deterministic tracking
should be widened to cover plain prose (paragraph/list) loss the way it already tracks headings,
fences, links and install commands -- the second verifier's own adversarial case exposed this as
a real, pre-existing blind spot, unrelated to this fix, not touched here.

**Where the detail lives**: `src/repo_presenter/readme/repair/accounting.py`
(`_uncited_kept_heading_identity`, whose own docstring carries the two-location history),
`tests/readme/repair/test_accounting_uncited.py`.

---

### 2026-11-01: live-verified the heading-identity-citation merge; two new, real, deliberately-not-fixed findings surfaced behind it

**What this does**: dispatched a fresh `present.yml` (`both` lanes) run for aspose-slides-foss/
Aspose.Slides-FOSS-for-.NET on merged `main` (run 41290354317) specifically to confirm the merged
fix's real effect, per this project's own "verify live, never trust tests alone" rule.

**Confirmed**: the original defect is gone. The durable record's `failure.detail` no longer
mentions `inherited_unit:029.heading`/`disposition_coverage`/`live_readme_loss` at all -- the
candidate progressed past S9 entirely, now blocking on two different, earlier-invisible checks
(`BC-06`, `BC-12`) that `validation.json` already showed failing on the UNFIXED run too (so
neither is a regression this merge caused; both were always there, simply masked behind the
heading defect that failed the candidate first).

**New finding A -- real, root-caused, NOT fixed (architecturally deep, matches an already-
deferred class)**: `BC-06`'s own repair (`readme/repair/loop.py::_repair_plan`) failed with "the
causing plan is not in the call store" -- it recomputes the S5 planning call's own request hash
from the CURRENT `rc.dispositions` and looks up the cache by that hash; when `present.yml`
restores a previous run's sealed bundle/call store and the dispositions have since changed (as
this very fix did), the recomputed hash no longer matches what is cached, and the repair fails
closed before ever asking the model anything. This is the same root architecture issue already
logged (`nineteenth_fix_live_verified_insufficient_deeper_staleness_cause_found`, this log, 2026-
10-30): "a genuine citation can silently go stale as later reconciliation work shifts a unit's
disposition, invisible until something downstream tries to re-validate it" -- here the symptom is
a repair lookup miss rather than a citation mismatch, but the cause is identical. Not fixed, for
the same reason as before: this needs the deeper, already-deferred cache-invalidation fix, not a
narrow patch on top. Recorded as a SECOND independent confirmation that this architectural item is
real and recurring, strengthening (not newly establishing) the case for eventually prioritizing it.

**New finding B -- real, root-caused, NOT fixed (naive fix would contradict an existing, deliberate
test)**: `BC-12`'s own `canonical_name_failures` (`readme/validation/structure.py`) flagged
"Aspose.Slides FOSS" as not matching the canonical "Aspose.Slides FOSS for .NET" inside this
repository's own "Related Aspose FOSS Products" list (`documentation_resources`): "- **[Aspose.
Slides FOSS for Java](...)** -- Aspose.Slides FOSS for Java provides a Java API...". Reproduced
directly (`canonical_name_pattern`/`_is_technical_identifier` called against the real README
text): the regex's own optional tail only ever tries to consume THIS repository's own tail
("for .NET"); "for Java" doesn't match it, so the match stops at the bare head, which is then
compared against the full canonical and correctly fails by the check's own narrow logic. The
repair (S6, `documentation_resources`) then correctly refused to "fix" it (a no-op, rejected
twice) -- there is nothing to fix; a sibling product's own, different, equally-canonical name is
not a misspelling. Checked for an easy fix and found none that would not contradict an EXISTING,
deliberate test: `test_bc12_fails_a_product_name_variant_in_prose`'s own parametrization
explicitly requires "Aspose.3D FOSS for Java" (used as the bare subject of a sentence describing
THIS product's own capabilities) to FAIL -- i.e. the check's job is precisely to catch a sentence
that confuses which product it is describing, which lexical pattern-matching alone cannot
distinguish from a correctly-structured "related products" list item (each with its own distinct
link target, correctly describing a genuinely different repository) without new, structural
(list-item + link-target) awareness this check does not have today. Not attempted here --
recorded as a real, well-scoped, but not a quick fix, same discipline as the duplicate_paragraph
generalization this log already reverted once rather than force past what was safely designed.

**What this does NOT decide**: whether either new finding is worth the investment of (A) the
deeper cache-invalidation fix or (B) teaching `canonical_name_failures` genuine structural
(list-item/link-target) awareness -- both are logged as separate, real, future fix-queue
candidates, not attempted here.

**Where the detail lives**: real downloaded artifacts (`gh run download 41290354317`); `readme/
repair/loop.py::_repair_plan` (finding A); `readme/validation/structure.py::canonical_name_
failures`/`canonical_name_pattern`/`_is_technical_identifier`, `tests/readme/validation/
test_registry_checks.py::test_bc12_fails_a_product_name_variant_in_prose` (finding B).

---

### 2026-11-01: a second five-repository fresh sweep -- one fix (SECTION_ABSENT), one new deferred finding, three confirmed matches to already-established non-bug patterns

**What this does**: dispatched five more fresh `present.yml` (`both` lanes) runs on `main`, each
against a repository/ecosystem not yet tried this session (aspose-3d-foss/Java, aspose-font-foss/
Python, aspose-note-foss/Python, aspose-psd-foss/.NET, aspose-tex-foss/Python), continuing the
portfolio-wide sweep per AGENTS.md non-negotiable #8. Also confirmed, in passing: aspose-3d-foss/
Aspose.3D-FOSS-for-Java's Lane L genuinely re-ran and re-confirmed ACCEPTED today (`present: ...
lane L exit 0, durable state ACCEPTED`, a fresh bundle pushed) -- its durable record's own
`last_transition` stays dated 2026-10-28 because a repeat success landing on the SAME terminal
state it already held has no registered self-loop to record through, the exact same `last_
transition`-can-be-stale-on-a-repeat-terminal-state property this log already found for
`FAILED_INTERNAL`, now confirmed for `ACCEPTED` too -- not a new defect, generalizing an already-
recorded one.

**Fixed**: see `fix/section-absent-authored-heading-title` -- aspose-psd-foss/Aspose.PSD-FOSS-for-
.NET's Lane R blocked on BC-05 with a deferred unit classified `UNCLASSIFIED` (hard `BLOCK`) even
though its own rationale correctly named a genuinely section-absent cause; the classifier's own
string match for the absent section's name never recognized the section's own authored heading
text ("Documentation & Resources"), only its bare `section_id` or an underscore-to-space
conversion of it, neither of which can produce an ampersand. Fixed, tested, falsifier-confirmed;
independent cold verification in progress before merge.

**New finding -- real, root-caused, NOT fixed (same discipline as BC-06/BC-12 above: real but not
a quick, safe fix)**: aspose-note-foss/Aspose.Note-FOSS-for-Python's Lane R `live_readme_loss`
finding (`link tools/regenerate_pdf_goldens.py`) is a genuinely different shape from anything
fixed today: four units (`inherited_unit:094-097`, two paragraphs and two code blocks) are
disposed `SUPERSEDE_REDUNDANT`/`VERIFIED_PRESERVE` into `development_testing`, uncited -- and the
content IS genuinely, correctly printed there (confirmed directly: the exact command and link
text appear in the real candidate README at lines 477/512/516). The loss is not a rendering
defect; it is that `live_readme_loss_rule`'s own link-accounting (`_accounting_units`) requires
non-empty `fact_ids` on an `ACCOUNTING_DISPOSITIONS` member to count a unit as covering anything,
and `account_unprinted_units` (the mechanism that backfills exactly this kind of missing citation)
is scoped to UNPRINTED kept units only (`unprinted_kept_units`) -- a unit that IS printed, just
uncited, is invisible to it by design. `development_testing` is not fact-driven the same way
`scope_limitations`/`key_capabilities` are (`_section_covering`'s own fact lookup would find
nothing to cite there either), so this is the same "no precise fact available" shape the heading
fix above closed for headings, but for printed, uncited, non-heading content -- a new, different
accounting path, not a guard widening. Not attempted here: this is a genuinely new function to
design and prove safe (the heading fix alone took two regression rounds against pre-existing
negative controls before it was safe), not a quick follow-on.

**Confirmed matches to already-established non-bug patterns, not re-investigated in full**:
aspose-3d-foss/Aspose.3D-FOSS-for-Java's `llm:factuality`/S6/empty-`fact_ids` findings (7 of them,
7 repair rounds already fired) match the `3D-Java F01-F05`/`3D-.NET` entries' own "already-working
repair loop" shape exactly. aspose-tex-foss/Aspose.TeX-FOSS-for-Python's 5 `live_readme_loss`
findings are all `DEFER_UNRESOLVED` code blocks citing a real `CONTRADICTED` example fact each --
the same, deliberately-by-design `Page-Python`-entry exclusion (`DEFER_UNRESOLVED` is not in
`ACCOUNTING_DISPOSITIONS`, on purpose). aspose-font-foss/Aspose.Font-FOSS-for-Python's
`source_reconciliation` rejection (a file-tree/structure diagram code block, oscillating between
`OMIT_UNSUPPORTED`-uncited and `DEFER_UNRESOLVED`-forbidden across all 3 attempts, never trying a
real placement) matches the Slides-Cpp `uncovered_supersession` entry's own model-compliance-gap
shape, generalizing it from headings to a code block with nothing citable at all.

**Where the detail lives**: `src/repo_presenter/readme/validation/deferrals.py`
(`_section_absent`, `_SECTION_TITLES`), `tests/readme/validation/test_deferrals.py`; this entry
for the Note-Python finding and the three confirmed non-bug matches.

---

### 2026-11-01: `fix/section-absent-authored-heading-title` merged -- a real pre-existing substring-match risk found, confirmed not newly introduced, not chased further

**Decision**: merged to `main`.

**Why**: fixes the real, live-evidenced PSD-.NET bug (above) exactly as designed: `SECTION_
ABSENT`'s matcher now also recognizes a section's own authored heading text, not only its
`section_id` or an underscore-to-space conversion of it.

**What the independent cold verifier found, and how it was resolved without blocking the merge**:
the verifier confirmed the fix correct for the stated case, then found and reproduced a real,
separate concern: `_section_absent` matches on bare substring containment of a title in free-text
rationale, with no check that the unit's own source section is actually the one named -- every
other positional matcher in this file (`_build_path`, `_at_a_glance`, `_install_steps`, etc.)
corroborates via `ctx.parts`/`ctx.sections`, this one does not. The verifier constructed a working
adversarial rationale (an unrelated, genuinely novel defect whose free text happens to echo an
absent section's title as an aside) that gets silently downgraded from blocking `UNCLASSIFIED` to
non-blocking `SECTION_ABSENT`/`ADVISORY`. Per AGENTS.md's non-negotiable #5, this finding was not
dismissed on say-so: checked deterministically, by running the identical adversarial input against
unmodified `main`'s own PRE-EXISTING matching form (`"documentation resources"`, the underscore-to-
space conversion, no ampersand) -- confirmed it ALREADY misclassifies the same way, unconditionally,
today, before this fix ever touched the file. This fix extends an already-shipped design's reachable
phrasings by two or three (the section titles), it does not introduce a new category of risk; of the
three genuinely new matches, `development_testing`'s title is provably inert (`_build_path`, checked
first, always matches first on the same substrings "development"/"testing"), leaving only
`documentation_resources` and `third_party_notices` as the real marginal addition. A structural fix
(requiring the unit's own source heading to corroborate, matching the file's other matchers) was
considered and rejected: the real target case's own upstream heading is literally "Documentation"
(the README's own section name), which does not match the shell's canonical title "Documentation &
Resources" either -- that corroboration requirement would most likely have broken the exact case
this fix exists to close. Full suite: 3476 passed, 13 skipped, exit 0.

**What this does NOT decide**: whether `_section_absent`'s whole design (free-text substring
matching, no structural corroboration) should eventually be tightened across the board, for both
the pre-existing forms and the new one -- a real, legitimate, but genuinely pre-existing question,
not created by this merge, not attempted here.

**Where the detail lives**: `src/repo_presenter/readme/validation/deferrals.py`
(`_section_absent`, `_SECTION_TITLES`).

---

### 2026-11-01: live-verified the SECTION_ABSENT merge; a real repair-loop oscillation found behind it on the same repository

**What this does**: dispatched a fresh `present.yml` (Lane R only) run for aspose-psd-foss/
Aspose.PSD-FOSS-for-.NET on merged `main` (run 41294881468).

**Confirmed**: the original defect is gone -- the durable record's `failure.detail` no longer
names `BC-05`/`UNCLASSIFIED` at all; the candidate progressed all the way to independent review
before blocking on a single, different, unrelated finding (`claim_contradiction`).

**New finding -- real, confirmed, NOT fixed (needs a focused repair-loop investigation this pass
did not have room for)**: this is the already-named, previously-unevidenced "PSD-.NET stale-
publication detector" fix-queue item from earlier this session, now with real evidence. The
facts genuinely show `package:published_version` SUPPORTED at `26.10.0` -- the package IS
published -- yet the final candidate's review finding reads "the README says the package is not
published to NuGet yet... but a package-registry reading lists it." Read `repairs.json` directly:
across 7 repair rounds, the SAME sentence was flipped in BOTH directions by two different repair
sources -- one round (label `F04`, routed from an LLM review finding, stage S6) rewrote a
CORRECT "published... version 26.10.0" sentence INTO the false "not yet published" claim; a
LATER round (label `BC-14`, routed from the deterministic `claim_failures` check that also backs
`claim_contradiction`) correctly rewrote it back. The final candidate still carries the wrong
text regardless, so either a repair round beyond the 7 recorded reverted it again, or the `F04`-
sourced wrong rewrite was reapplied after `BC-14`'s correct one for a reason not traced in this
pass. Not root-caused to a single mechanism this session; recorded with the real, specific
repair-ledger evidence (the two opposing diffs) rather than guessed at, for a dedicated follow-up
rather than a rushed fix layered onto an already-substantial day's worth of changes.

**Where the detail lives**: real downloaded artifacts (`gh run download 41294881468`),
specifically `cascade/repairs.json`'s `F04` and `BC-14`-labeled attempts; `src/repo_presenter/
readme/validation/blocking.py` (`BC-14` -> `claim_failures`); `src/repo_presenter/readme/review/
independent_reviewer.py`'s own `claim_contradiction` rule (same underlying `claims.claim_
findings`).

---

### 2026-11-01: a third five-repository fresh sweep -- one clean full ACCEPT, two fresh Lane L ACCEPTs, one genuine upstream data gap, two confirmed model-reliability non-bugs

**What this does**: dispatched five more fresh `present.yml` (`both` lanes) runs on `main`, each
against a repository not yet tried this session (aspose-gis-foss/.Net, aspose-html-foss/Python,
aspose-barcode-foss/Python, aspose-imaging-foss/.NET, aspose-words-foss/Python), continuing the
portfolio sweep.

**Confirmed real wins, no fix needed**: aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET's Lane R
is a clean, full, green ACCEPT today (both jobs green, no sub-step failure at all) -- the third
distinct full/fresh portfolio win confirmed this session (after Cells-Python's Lane R and this
candidate's own earlier Lane L). aspose-html-foss/Aspose.HTML-FOSS-for-Python's Lane L and
aspose-words-foss/Aspose.Words-FOSS-for-Python's Lane L are BOTH freshly `ACCEPTED` today
(confirmed via the trigger-dedup-key match, not stale), even though each repository's own Lane R
failed in the same run for unrelated reasons (below) -- two more real wins the red overall job
status alone would have hidden.

**Genuine upstream data gap, not a pipeline defect**: aspose-gis-foss/Aspose.GIS.FOSS-for-.Net
failed with "no README.md at the pinned revision ... this cascade has nothing to reconcile
without one." Confirmed directly against the real repository (`gh api repos/aspose-gis-foss/
Aspose.GIS.FOSS-for-.Net/contents/`): the repository genuinely has no `README.md` (or any
variant) at its root at all -- only a solution file, a test project and a source project.
Explains this repository's own long-standing `OBSERVED`/never-transitioned durable state seen
earlier this session. Nothing for this pipeline to do; the upstream repository needs a README
before it can ever be presented.

**Confirmed model-reliability non-bugs (not pipeline defects), each checked against the real
evidence rather than assumed**:
- aspose-html-foss/Aspose.HTML-FOSS-for-Python's Lane R `F01` omission finding claims the
  candidate omits a specific sentence about `CSSRule.type`/`CSSRule.css_text` -- but the sentence
  IS verbatim in the real candidate README (confirmed directly, `grep` against the real
  `README.coherent.md`). The reason the built-in `omission_present` clearance (`readme/review/
  clearances.py`) did not clear this false claim: the reviewer's own `missing_quotes` text is
  itself fabricated -- it inserts a parenthetical, "(the CSSOM base-rule stubs)", that appears
  nowhere in the real document, and drops the backticks the real text has -- so no literal-ish
  match can succeed, correctly, since the "proof" quote the clearance would need to find isn't
  real text at all. A genuine reviewer hallucination inside its own finding, not a clearance bug:
  the clearance refusing to trust a fabricated quote is the correct behavior.
- aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python's Lane R `section_authoring` rejection (a
  `scope_limitations` unit's text containing a forbidden `pip install` command, rejected 3 times
  running) shows the model's OWN recorded reasoning on one attempt explicitly stating the command
  "must not include" the literal install command and should state the requirement generically --
  then its own `text` field includes "...running pip install ." verbatim anyway, in the SAME
  reply. A within-reply self-contradiction, the same model-compliance-gap category as the
  Slides-Cpp/Font-Python findings already logged this session, not a pipeline defect.

**Confirmed match to an already-established non-bug pattern, not re-investigated in full**:
aspose-words-foss/Aspose.Words-FOSS-for-Python's Lane R findings are all `causal_stage: S6`,
empty `fact_ids`, with 4 repair rounds already active -- the same "`3D-Java`/`3D-.NET`
already-working repair loop" shape.

**Where the detail lives**: real downloaded artifacts for each run; `gh api repos/aspose-gis-
foss/Aspose.GIS.FOSS-for-.Net/contents/` (the GIS finding); `src/repo_presenter/readme/review/
clearances.py::omission_present` (the HTML-Python finding); this entry for all five.

---

### 2026-11-01: a fourth five-repository fresh sweep -- two more full real wins, one fixed (.NET version padding), one new fix in flight (lead-in coordination), four confirmed non-bug matches

**What this does**: dispatched five more fresh `present.yml` (`both` lanes) runs on `main`
(aspose-cells-foss/.NET, aspose-email-foss/.Net, aspose-pdf-foss/.NET, aspose-slides-foss/Java,
aspose-slides-foss/Python).

**Confirmed real wins, no fix needed**: aspose-email-foss/Aspose.Email-FOSS-for-.Net is a clean,
full, green ACCEPT (both jobs green). aspose-cells-foss/Aspose.Cells-FOSS-for-.NET's Lane R is a
genuine, fresh `exit 0, durable state ACCEPTED` today (confirmed directly from the hosted job's
own log, not just the record, since a repeat-success-on-the-same-terminal-state can leave the
record's own dedup-key match ambiguous -- the log line is unambiguous). aspose-pdf-foss/
Aspose.PDF-FOSS-for-.NET's Lane L is freshly `ACCEPTED` today. The fifth and sixth real wins
confirmed this session.

**Fixed**: see `fix/dotnet-four-part-version-padding` -- aspose-cells-foss/Aspose.Cells-FOSS-for-
.NET's own `<PackageReference ... Version="26.10.0.0" />` snippet (.NET's 4-part assembly-version
convention) was wrongly flagged as contradicting the registry's 3-part release ("26.10.0"), the
same release, not a real mismatch. Fixed, tested (including adversarial negative controls for a
genuine differing revision and a prerelease tag), independently cold-verified with 10 additional
adversarial cases beyond the branch's own tests, merged.

**New fix, in flight**: see the next entry below -- aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET's
Lane R BC-07 dangling-colon failure, a lead-in/payload coordination gap for `UNRESOLVED`-example
payloads.

**Confirmed model-reliability/known-pattern non-bugs, not re-investigated in full**:
- aspose-cells-foss/Aspose.Cells-FOSS-for-.NET's Lane L `claim_contradiction` ("shown at version
  26.10.0.0, but the registry's current stable release is 26.10.0") is the Lane L review path
  hitting the EXACT SAME version-padding gap `fix/dotnet-four-part-version-padding` fixes --
  expected to clear on its own once that fix reaches a fresh Lane L run; not separately
  investigated.
- aspose-slides-foss/Aspose.Slides-FOSS-for-Java's Lane R `live_readme_loss` (a code block quoting
  the literal error message "Export format 'Pdf' is not supported...") and Lane L's Enterprise
  Edition naming finding, and aspose-slides-foss/Aspose.Slides-FOSS-for-Python's Lane R
  `duplicate_paragraph` (the already-logged, already-deferred `email-foss/Cpp`-class finding,
  confirmed recurring on a THIRD repository) and Lane L `claim_contradiction` (a format list) were
  surfaced but not investigated in full this round, given the volume of confirmed real work
  already landed -- flagged for a future pass, not lost.

**Where the detail lives**: real downloaded artifacts for each run; `fix/dotnet-four-part-
version-padding`'s own commit; the next entry for the lead-in coordination fix.

---

### 2026-11-01: live-verified the version-padding merge

**What this does**: dispatched a fresh `present.yml` (Lane L) run for aspose-cells-foss/
Aspose.Cells-FOSS-for-.NET on merged `main` (run 41302284239).

**Confirmed**: the version-mismatch finding is gone -- the candidate progressed to a single,
different, genuine upstream content defect instead (`lane_l_unrepaired_defect [contradiction]`:
`'RELEASE_NOTES_V26.10.0.md' is not in the tree and no unique file stands in for it`), which Lane
L correctly refuses to repair on its own, recommending Lane R. Not a pipeline defect; the
upstream repository's own README links to a release-notes file that does not exist in the tree.

**Where the detail lives**: the durable record for aspose-cells-foss/Aspose.Cells-FOSS-for-
.NET@lane-l.

---

### 2026-11-01: `fix/lead-in-unresolved-example-coordination` merged -- a pre-existing, now
slightly-widened gap found and honestly disclosed, not chased

**Decision**: merged to `main`. `coordinate_neighbor_promises`'s own `_settle_lead_in` now also
coordinates a lead-in with a payload whose example is `UNRESOLVED` (not only `SUPPORTED`),
closing the real aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET BC-07 defect this entry's own earlier
report named.

**What the independent cold verifier found, and why it did not block the merge**: the SAME
`verified_example` flag this fix widens also gates a DIFFERENT, untested branch in `_settle_
lead_in` (reached when the LEAD-IN's own disposition is `DEFER_UNRESOLVED`, not the payload's) --
that branch promotes the lead-in with no `_bare_lead_in` gate at all, unlike its own sibling
`elif` branch immediately below it, which does require `_bare_lead_in` (the lead-in's own
sentence making no specific, checkable claim) before promoting. The verifier constructed a
concrete case (a lead-in asserting "the library fully supports PDF version 2.0 extraction:",
`DEFER_UNRESOLVED`, beside a `SUPERSEDE_REDUNDANT` payload) where this ungated branch silently
promotes the lead-in's own specific, unverified claim, and confirmed `placement_errors` does not
catch it either (`coverage_findings`'s own `plan_dependent` gap for a `SUPERSEDE_REDUNDANT`-into-
placeable fold is filtered out before becoming an error, by design, for an unrelated reason).
Per AGENTS.md's non-negotiable #5, checked rather than dismissed: the verifier confirmed, with
the SUPPORTED polarity (entirely unchanged by this diff), that this exact silent promotion
already happens identically on unmodified `main` -- this fix only extends an already-latent,
already-untested shortcut to one more input shape (`UNRESOLVED`), it does not create the gap.
Logged as a separate, real follow-up (gate that branch the same way its own sibling already
does, or pin the current behavior deliberately with a test), not attempted here. Full suite:
3478 passed, 13 skipped, exit 0.

**Where the detail lives**: `src/repo_presenter/readme/reconciliation/dispositions.py`
(`_settle_lead_in`, the `state == "DEFER_UNRESOLVED"` branch around line 2194).

---

### 2026-11-01: live-verified the lead-in coordination merge

**What this does**: dispatched a fresh `present.yml` (Lane R) run for aspose-pdf-foss/
Aspose.PDF-FOSS-for-.NET on merged `main` (run 41303579390).

**Confirmed**: the BC-07 dangling-colon finding is gone -- the candidate progressed to the single,
already-known, already-deferred `duplicate_paragraph` finding (confirmed recurring on a fourth
repository now: email-foss/Cpp, slides-foss/Python, and this one). No new investigation needed.

**Where the detail lives**: the durable record for aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET.

---

### 2026-11-01: a fifth five-repository fresh sweep -- two more full real wins, one confirmed-
recurring already-known gap, two genuine upstream content issues, one more model-compliance match

**What this does**: dispatched five more fresh `present.yml` (`both` lanes) runs on `main`
(aspose-3d-foss/Python, aspose-cells-foss/Cpp, aspose-pdf-foss/Java, aspose-pdf-foss/Python,
aspose-pdf-foss/TypeScript).

**Confirmed real wins, no fix needed**: aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp's and
aspose-pdf-foss/Aspose.PDF-FOSS-for-Java's Lane R are both genuine, fresh `exit 0, durable state
ACCEPTED` today (the eighth and ninth real wins confirmed this session).

**Confirmed recurrence of an already-known, deliberately-narrow gap, not re-investigated**:
aspose-pdf-foss/Aspose-PDF-FOSS-for-Python's and aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript's
Lane R `source_reconciliation` rejections are both `uncited_prose_omit` on a paragraph describing
a function's own parameter names (`pages=`, `dry_run=`, `uniform=`) with no fact to cite -- the
same shape this session's own `_spelled_supported_facts`/`_OMISSION_CITABLE_KINDS` fold (merged
earlier, scoped deliberately narrow to `package`/`link_target` fact kinds only) was already known
not to cover: a parameter name is neither of those fact kinds. Confirms the already-logged
limitation is real and recurring across ecosystems; not widened here without new design work.

**Confirmed genuine upstream content issues, not pipeline defects**:
- aspose-pdf-foss/Aspose.PDF-FOSS-for-Java's Lane L `claim_contradiction` ("shown at version
  26.6.0, but the registry's current stable release is 26.9.0") is a real, true staleness: both
  `package:version` and `package:published_version` facts agree on `26.9.0`, so `26.6.0` is
  simply an outdated number somewhere in the upstream README, not a padding/format artifact like
  the earlier Cells-.NET finding.
- aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp's Lane L failing example (a genuine upstream C++
  compile error) correctly blocks Lane L, recommending Lane R (which already succeeded).

**Confirmed match to the model-compliance-gap category, not a pipeline defect**: aspose-3d-foss/
Aspose.3D-FOSS-for-Python's Lane R oscillated between `uncited_prose_omit` and `dangling_pointer`
for the same forward-referencing sentence ("The full public class index is listed below by
module.") across its 3 attempts, never landing on any of the dispositions named in its own
rejection text -- the same category as the already-logged Slides-Cpp/Font-Python findings.

**Where the detail lives**: real downloaded artifacts for each run.
