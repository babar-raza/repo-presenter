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
