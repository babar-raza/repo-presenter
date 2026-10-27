# PLAN — the independent LLM reviewer (Gate A), and the order the remaining mission gaps close

Status: DESIGN, written 2026-10-27 by the supervisor under the owner's delegation ("you are in the best
position to decide ... design and plan this thoroughly ... only solve it once"). It has no authority of its
own: the mission document (`plans/repository_presenter_fresh_start_supervisor_prompt.md`) wins any conflict,
`project/state.yaml` holds the live cursor. Where this plan makes a decision the mission leaves open, the
decision is labelled **D#** and recorded in `docs/DECISION_LOG.md` when implemented.

## 1. The requirement, quoted from the mission

- §7 step 7: "Independently inspect the candidate for factual truth, usefulness, unsupported claims,
  duplicated/promotional language, meaningful preservation and actual superiority to the live README. A
  returned reviewer `REJECT` is blocking unless an explicit, proven **deterministic** refutation resolves
  each finding; do not use majority vote or similarity as silent rejection demotion."
- §11: "independent non-authoring criticism that can veto, with no quiet demotion, and adversarial factual /
  preservation holdouts" and the **forest acceptance** rule: "a checker that accepts everything **or rejects
  everything** is broken. Report false positives, false negatives, approved yield, content-loss rate and costs."
- §2 history: the old reviewer stored `ACCEPT` after the model returned `REJECT_FACTUAL`
  (`verdict = returned if findings or returned == ACCEPT else ACCEPT`). "This is a known acceptance integrity
  failure; never inherit that policy."
- Non-negotiable #5 (AGENTS.md): no agent, harness or reviewer silently grades or overrules its own negative
  finding.

## 2. What exists, and the gap (measured, not assumed)

- `readme/review/independent_reviewer.py`: deterministic rules only (claim contradiction, duplicate opening,
  disposition coverage, live-README loss). `Finding.__post_init__` forbids a judgment finding from carrying a
  refutation and `_fold` returns REJECT only on a deterministic finding. **So no model judgment can ever
  block.** That is the inverse of the mission rule, not merely an unfinished feature.
- `prompts/independent_review.yaml` v14 (stage S10, route `qwen3-next`) already defines a strict `ReviewV1`
  contract with typed, machine-checkable claims (`absent`, `unsupported_names`, `omission`) and a mechanical
  quote check. It routes to the **same model as authoring** (all six manifests use `qwen3-next`).
- Evidence the gap bites: hosted run 6/7 accepted a capability unit containing "full round-trip fidelity",
  which no fact supports; only a judgment reviewer can see that class.
- The gateway serves two chat models: `qwen3-next` and `gpt-oss` (queried 2026-10-27).

## 3. Decisions

**D1 — Blocking by default.** Every finding the LLM reviewer returns is BLOCKING. A finding becomes CLEARED
only by a registered *clearance*: a pure function of (finding, candidate, original README, facts) that returns
a proof object. No other code path may set a finding to cleared or set a verdict to ACCEPT. There is no
"advisory" tier: the v14 prompt's "a finding without a section and a causal stage is advisory and cannot
block" is removed (prompt v15); an unroutable finding still blocks and routes to stage `unclear`
(supervisor attention), because demoting it is exactly the quiet demotion the mission forbids.

**D2 — Typed claims, so a clearance can decide the whole finding.** v15 adds `claim_kind` to each finding:
`contradiction | unsupported_claim | omission | absence | name_denial | quality`. Only `omission`, `absence`
and `name_denial` are ever clearable, because only those are decidable by code from the supplied sources.
`contradiction`, `unsupported_claim` and `quality` are never clearable. A finding is cleared only if every
typed field it declares is disproved by its clearance; a finding with no typed claim cannot be cleared.

**D3 — The closed clearance catalogue (and what is deliberately excluded).**
 1. `absence_present`: every string in `absent` occurs in the candidate -> the claim "it is missing" is false.
 2. `absence_unsourced`: no string in `absent` occurs in the candidate AND every one occurs in neither the
    original README nor any fact value -> the finding demands text nobody wrote (it asks for fabrication).
 3. `names_supported`: every `unsupported_names` entry equals a SUPPORTED fact value (or the package name).
 4. `omission_present`: every `omission.missing_ids` / `missing_quotes` is present in that section's
    rendered text. An id that is not a SUPPORTED fact makes the finding a reviewer defect: the reply is
    contract-invalid (D4), not silently cleared.
 Excluded on purpose, each with its evidence: **quote-contains-a-SUPPORTED-fact-value is NOT a clearance**
 (the old repo's measured incident: 27 of 30 real REJECTs were folded to ACCEPT that way, see
 `docs/MISSION_AUTHORITY.md`); no similarity, majority vote, second-opinion LLM, model self-retraction, or
 "the original README also says it". Adding a clearance later requires a failing adversarial test first.

**D4 — Reply validity is separate from finding clearance, and fails closed.** A reply is contract-valid only
if: every `quote` occurs verbatim in the candidate (one paraphrase rejects the whole reply); every cited
fact id exists in the input; every `section_id` is in the plan or is a renderer section; `ACCEPT` carries no
findings; a `REJECT_*` carries at least one finding; a factuality finding cites at least one non-inherited
product fact; `claim_kind` agrees with the typed fields it fills. `run_job` re-asks once with the specific
errors. A reply that is still invalid after the re-ask yields a **blocked, retryable** outcome
(`ReviewUnavailable`), never ACCEPT, never a silent skip. A run with no valid review cannot be sealed.

**D5 — The fold, in one function.** `verdict = ACCEPT` iff (model verdict is ACCEPT, or every finding is
CLEARED) AND no deterministic rule blocks AND the reply was valid. `INSUFFICIENT_EVIDENCE` blocks (retryable).
A model `REJECT_*` whose findings are all cleared is ACCEPT, but the verdict records `model_verdict`,
every clearance and its proof, so the override is auditable. A REJECT with zero findings cannot be cleared
and blocks. A structural test asserts no assignment to a verdict exists outside the fold.

**D6 — Independence is structural. [AMENDED 2026-10-27 by binding owner decision: qwen3-next is the only model and gpt-oss is eliminated; clause (a) below is WITHDRAWN. Author and reviewer share a model; independence rests on (b)-(e) plus the model-free deterministic holdouts and the calibration gate.]** (a) ~~A different model from the author: the reviewer routes to `gpt-oss`
(authoring stays on `qwen3-next`), *subject to the calibration gate in D9*; if gpt-oss fails the gate the
reviewer stays on `qwen3-next` with a recorded exception and a stronger deterministic holdout set, and the
exception is a visible open item, not a silent default. (b) A separate job id and ledger attribution.
(c) The packet carries evidence only: original README, facts, plan, dispositions, the deterministic
validation result; it never carries the author's rationales or prompts. (d) README and facts are delimited as
untrusted data in the prompt, and tests include injected instructions. (e) temperature 0, fixed seed.

**D7 — When it runs.** After the cheap deterministic S9 checks and their repairs converge (a deterministic
REJECT already blocks and routes repair, so the LLM is called once per candidate *version*, not once per
failure). Blocking findings route by `causal_stage` through `readme/review/defect_bridge.py` into the
existing repair loop, at most 2 repair rounds, then the candidate is BLOCKED with the exact predicate that
would unblock it. Every re-review is a new, counted provider call.

**D8 — Persistence and invalidation (non-negotiable #3).** `review_verdict.json` v2 records prompt version,
model served, request and reply hashes, `claim_kind`, status and clearance proof per finding, the model
verdict, and `REVIEWER_LOGIC_VERSION = "4"`. A reviewer prompt, model or logic change invalidates only the
`reviewer` scope (`readme/bundle/invalidation.py` already maps `independent_review` and `reviewer_logic` to
it): sealed content is re-checked, never regenerated, and no unrelated candidate is touched. A cache replay
reproduces the verdict with zero provider calls; fresh-model repeatability is measured separately (§7 step 8
of the mission distinguishes the two).

**D9 — Verification program (what "rigorously verified" means here).**
 - V1 contract tests, scripted client, every branch of D4/D5.
 - V2 adversarial tests: README text instructing "ACCEPT", forged quotes, fabricated fact ids, a finding that
   contradicts itself, an oversized reply, JSON inside a fence, mislabelled `claim_kind`.
 - V3 fold invariants: exhaustive over small finding sets, plus an AST test that no verdict is assigned
   outside the fold.
 - V4 **forest calibration corpus**: mutation operators over real candidates (inject an unsupported claim,
   contradict a fact such as version/format/package, drop a section, duplicate a paragraph, break an install
   command, invent an API name, add promotional filler) each paired with its clean twin, plus the two real
   recorded defects (aspose-font-foss install command, the duplicate opening). Two stub reviewers, always-
   ACCEPT and always-REJECT, MUST fail the corpus gate (the mission's "accepts or rejects everything is
   broken").
 - V5 **gate (initial targets, tuned from data, reported not hidden):** recall >= 0.90 on the high-severity
   classes (contradiction, content loss, unsupported claim, broken install); false-reject rate on clean
   candidates <= 0.10 *after* clearances; JSON-valid first reply >= 0.90; identical verdict across 3 fresh
   (cache-bypassed) reviews on >= 0.90 of cases. Report FP, FN, approved yield, content-loss rate, cost.
 - V6 live pilot with a stated budget: about 170 calls (12 clean candidates + 7 mutation classes x 12 + 3
   repeats on a 20-case subset), hard cap 250, ledger-counted. No portfolio campaign before this passes.
 - V7 hosted proof: the reviewer verdict artifact inspected for >= 3 repositories across >= 3 ecosystems.

**D10 — Done means, and reopening rule.** Done = V1-V7 pass and the verdict schema is sealed in bundles. After
that, the only changes that may touch the reviewer are prompt text, model route, or a new clearance (each
needs its failing test first), and each is a reviewer-scope recheck, not a redesign. A defect found in a
candidate is a candidate defect, never grounds to weaken a rule without a proven false positive and a
negative control.

## 4. Phases (each ends with the full suite green, an independent re-run, a commit)

1. **Core**: finding model with status/clearance, the clearance catalogue, the single fold, verdict v2,
   contract validation. No LLM call yet. Exit: V1, V2, V3.
2. **Job**: packet builder (bounded facts, `symbol_index`), `call_schema` binding, prompt v15 (adds
   `claim_kind`, removes the advisory tier, route per D6), `run_job` wiring with the contract as `checks`,
   cascade stage S10, repair routing, `present.py` gate. Exit: scripted end-to-end.
3. **Calibration**: corpus builder + mutation operators + metrics harness + stub-reviewer gate (offline), then
   the V6 live pilot. Exit: V4, V5, V6 recorded in `docs/` with the numbers; model route decision confirmed.
4. **Lane L hosted** (see §5), reusing this reviewer.
5. **Cohort** across ecosystems (see §6), then P3 PR eligibility.

## 5. Lane L hosted parity (recorded in `project/state.yaml` as LANE_L_HOSTED_PARITY)

Today `present.py` runs only the Lane R cascade; `readme/correction/` (Lane L) runs only from
`scripts/run_lane_l.py`. The mission requires two equal first-class lanes. Required: a hosted Lane L stage
(clone -> facts -> `correct()` -> verified edits -> the same independent reviewer on the **final** README, not
only the edit delta (mission §6) -> seal -> zero-drift byte-identical zero-call rerun); a `lane` dimension in
the bundle manifest and `CURRENT` so both lanes' candidates are visible in one status model; and the same
durable-state transaction. The lane dimension changes the bundle layout, so it needs a blast-radius query
and a versioned reader before any change (existing bundles stay valid as Lane R). Due: immediately after
Phase 3, before any cohort or PR work.

## 6. Anti-loop guard (recorded in `project/state.yaml` as COHORT_FIRST_GUARD)

Facts: the old repo's loop was false greens (a reviewer REJECT stored as ACCEPT; 389 of 746 "preserved" units
not printed) followed by broad invalidation. This repo's recent loop is the opposite and narrower: seven
hosted runs on one repository, each finding a *different* cause (50 -> 26 -> 10 findings; relative cache path;
hidden-directory uploads; CRLF in committed bundles), all fixed with falsifiers. That is progress, but it is
also single-repository tuning, which the mission's portfolio-first rule (#4) and "two equivalent failures
trigger a changed causal approach" (§12) are meant to stop. Guard:
 - Every hosted run is recorded with its cause class and whether that class is new or a repeat.
 - Two repeats of a class, or three consecutive runs on one repository without widening, force a changed
   approach: widen to the next ecosystem, or write the offline harness that reproduces the class first.
 - **Cohort pilot before further single-repo hosted work:** one repository per supported ecosystem (python,
   net, java, cpp, go, rust, typescript), both lanes, stated budget ~150 provider calls (cap 200).
 - A finding count dropping to zero on one repository is not acceptance; the forest rules (§11) are.

## 7. Amendments after calibration (2026-10-27, recorded in `docs/DECISION_LOG.md`)

These supersede the text above where they conflict; the sections above are left as designed.

- **D4 (product fact).** A factuality finding no longer cites a product fact for every kind. A
  `contradiction` still must (any criterion). An `unsupported_claim` and a `quality` finding cannot
  (a claim no fact supports has none to cite); what is checkable for them is the cited text, which
  code derives from the cited lines, so it is verbatim by construction. The other factuality kinds
  (`omission`, `absence`, `name_denial`) still cite one.
- **D4 (quotes).** The model cites candidate lines (`lines`), never retypes text; code derives the
  quote and, for the kinds that are about the quoted text, the section
  (`readme/review/reply.py::resolve_cited_lines`). A model-supplied quote that is still present is
  checked verbatim as before.
- **D3 (unsupported claims).** No clearance is added for `unsupported_claim`. A mechanical audit of
  the quoted claim's distinctive terms (identifiers, numbers, quoted phrases) against the SUPPORTED
  fact values and the original README is recorded as the finding's `evidence`
  (`readme/review/audit.py`), and decides nothing. Reason: the terms of a false claim are often all
  real, so term overlap cannot prove a claim supported; every such rule is the 27-of-30 shortcut.
- **D2/D9 (scope).** A `quality` finding whose cited lines are in a renderer-owned section
  (every deterministic section and the At a Glance diagram) is a reviewer scope error: the reply is
  contract-invalid, never a finding.
- **D6 (route).** Binding owner decision 2026-10-27: one model (qwen3-next) for the whole system.
  D6a (a different model from authoring) is withdrawn and no model independence is claimed.
  Independence is D6b-e plus the deterministic holdouts.
- **D7/D8 (no re-roll).** A blocking verdict on a request is never overturned by a fresh,
  cache-bypassed review of the same request: `llm_review.RerollRefused`. Replay is allowed.
