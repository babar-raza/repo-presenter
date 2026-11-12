# Independent acceptance, redesigned from first principles (R12) — 2026-11-06

Status: **ADOPTED** (`docs/DECISION_LOG.md`, "2026-11-06: acceptance redesign adopted (R12; stage S0)"). This
header read "not yet adopted" after that decision-log entry already recorded adoption; corrected 2026-11-07
(`docs/DELIVERY_PLAN_2026-11-07.md` Step 0 routine fix). The card map in §6 is superseded by
`docs/DELIVERY_PLAN_2026-11-07.md` §8.2, which re-sequences and renumbers S0-S12 as TC-012c and TC-013 through
TC-035 (see that document's §4 "second architect audit" items 2, 8 and 9 for why); this document's own stages,
mechanisms (M1-M10), properties (AP-1..12) and hidden factors (H1-H20) remain the substantive design and are
still binding. This document contains no code. It was written with zero provider calls, from:
`AGENTS.md` (R9–R14), `docs/CONSOLIDATED_GOALS_2026-11-06.md` (Parts A and B), `docs/RELEASE_CONTRACT_P1-P5.md`,
`data/reviewer_calibration.json`, every reviewer-calibration investigation (2026-10-27 iterations 1–3, 2026-11-05
iteration 4, 2026-11-06 root cause, iteration-5 plan and result, the unsupported-claim class audit, the
maintainer-content calibration), `docs/MISSION_AUTHORITY.md` ("Do not repeat the predecessor projects' mistakes"),
`docs/DECISION_LOG.md` (2026-11-05 to 2026-11-06), `project/taskcards/TC-007.yaml`, `ops/checks/portfolio_delivery_count.py`,
`src/repo_presenter/readme/review/` and `src/repo_presenter/readme/validation/`.

Nothing here lowers a threshold, changes a frozen label, or edits iteration 5's recorded `NOT_PASSED`.

---

## 0. The stuck problem, stated exactly

`ops/checks/portfolio_delivery_count.py` counts a candidate as **independently accepted** only when it has a sealed
**model** ACCEPT, recorded under `data/reviewer_calibration.json` status `PASSED`, at exactly the reviewer logic and
prompt version that file certifies. That file has said `NOT_PASSED` since 2026-10-27. So the count is 0 in both lanes
and will stay 0 for as long as one LLM reviewer has to pass one monolithic gate.

Five iterations have failed. Each one tried to make **one** LLM call per review unit do **every** job:

| Iteration | What changed | Result on the classes that failed |
|---|---|---|
| 1 (2026-10-27) | gpt-oss vs qwen3-next, whole-README packet of ~70k tokens | both fail; gpt-oss withdrawn by the owner |
| 2 (2026-10-27) | contract and re-ask fixes, prompt v16 | 2 of 7 gates pass |
| 3 (2026-10-27) | two-tier gate, deterministic BC-14 rules, prompt v17 | tier 1 passes at pipeline level; tier 2 fails |
| 4 (2026-11-05) | 41 bases, held-out, logic 6 | real unsupported claims 0/81 on target; false reject 6/37 |
| root cause | scope fixes (tables shown), Lane L loss rule in the harness, logic 9 | section drop 0.17 → 0.90 (deterministic) |
| 5 (2026-11-06) | prompt v21, logic 10, 288 cases | reviewer alone: real unsupported 0.02, real contradiction 0.00, promotional filler 0.56, false reject 0.14 |
| 5b | gpt-oss on a subset | false reject 6/6 |
| 5c | deterministic token entailment (BC-15/16, not merged) | false reject 13/28 |
| class audit | zero calls, 113 real cases read against upstream source | 69/100 "unsupported" claims are **true**; on the false and generated ones (A+D, 27) the reviewer finds **0** |

The audit's finding is what changes the approach. The gate asked the reviewer to reject 69 true sentences, and it
asked an LLM to prove facts that code can prove. A detector that "passed" that gate would have to destroy true,
sourced maintainer content, which goals §5 forbids. The gate was wrong as well as the reviewer, so a sixth prompt
iteration cannot fix it.

---

## 1. What "independently accepted" has to guarantee (first principles)

The owner's goals ask one thing of an accepted candidate: **someone other than its author has shown, with evidence a
sceptical reader can re-check, that publishing it upstream would improve the README without making it wrong or
losing anything of value.** Taken goal by goal, that gives these minimal properties. Each one is necessary (a goal
fails without it), and together they are sufficient (every goal clause is covered).

| # | Property the candidate must provably have | Goal clause it comes from | What failure looks like |
|---|---|---|---|
| AP-1 | **Fresh and pinned.** Facts, examples and the live README were read at pinned revisions current at seal time, or the seal re-certifies against the current revisions. | §4 "fresh, verifiable source", "read the latest live upstream README"; §9 "detect stale evidence" | stale README overwrites a newer maintainer edit |
| AP-2 | **No false checkable statement.** No sentence, table cell or code line states something the repository at that revision contradicts (counts, type existence or export, stubs described as working, formats, versions, package names, platforms, runtime floors). | §4 "validate technical claims", "never invent functionality"; §6 "reject ... inaccurate" | class A of the audit |
| AP-3 | **Generated text is grounded.** Every checkable token in text the pipeline wrote (any line not byte-traceable to the live README) is entailed by a fact the line cites. No verification narrative unless a verification record exists. | §4 "never invent ... verification results", "preserve source provenance and evidence supporting generated claims" | class D; injected claims |
| AP-4 | **Inherited text is kept unless disproved.** Maintainer text the candidate prints is byte-traceable to the live README, and no fact contradicts it. Unverifiable maintainer knowledge is kept, attributed **internally** only. | §5 "preserve ... information supplied by the original product developers"; R9 | false rejects of B and C; public attribution |
| AP-5 | **Examples work.** Every example the pipeline wrote ran or compiled at the pinned revision. Every inherited example printed is not CONTRADICTED. | §4 "validate ... examples"; §13 "generated claims and examples are technically verified" | a broken quick-start |
| AP-6 | **Install, package and links are correct.** | §4 "installation commands, and links" | wrong `pip install` name |
| AP-7 | **Nothing of value lost without a decision.** Every item dropped from the live README is accounted for by a non-loss reason or a recorded R14 decision. | §5 "measure ... retained, merged, improved, removed, or lost"; R14 | dropped `<ProjectReference>` |
| AP-8 | **At or above the published benchmark.** On every measurable dimension (content items, sections, verified examples, API coverage, install correctness), no lower than the aspose.org README published for the product; equal is allowed only with a recorded justification. | §1, §6, R2 | "attractive but inferior" |
| AP-9 | **Well-formed public text.** Structure rules, canonical names, no duplication, no attribution or provenance wording in public. | §6 structure, discoverability; R9; BC-07 | |
| AP-10 | **Prose quality.** Not promotional, generic or incoherent, and at least as readable and usable as the benchmark. | §6 "clarity", "reject ... generic" | promotional filler |
| AP-11 (Lane L) | **Justified, minimal edit.** The trigger is a verified upstream change plus a verified defect (R5). Bytes outside the edit are identical. | §2 Lane L, R5 | unrelated rewrites |
| AP-12 | **Not self-certified.** The decision is computed by code the generator does not control, from evidence the acceptance path regenerates or verifies itself, and the mechanisms are measured. | §8 "prevent self-certified completion"; non-negotiables 5, 6 | predecessor lesson 1 (27/30 hidden defects) |

AP-1 to AP-9 and AP-11 are **decidable from bytes**: the candidate, the live README, the benchmark, the repository at
the pinned SHA, and execution results. Only AP-10 needs judgement. One residual of AP-2 does too (§2, D9). The old
design assigned all twelve to the LLM reviewer.

---

## 2. One primary mechanism per defect class

### 2.1 Mechanisms

| Id | Mechanism | Kind | Exists today | Gap to close |
|---|---|---|---|---|
| **M1** | Provenance and freshness: BC-01, preflight, live-README re-read, version vector | deterministic | yes (BC-01, P5 preflight, `recertify`) | record the mechanism-version vector per acceptance (§4.4) |
| **M2** | Claim proof: (a) **line provenance**, where each printed line is classified `inherited` (byte-traceable to a live-README unit) or `generated`; (b) **closed world for generated lines**, where each checkable token (number, identifier, version, format, platform, standard, count) must equal a value of a fact the line's unit cites (extends BC-04/BC-14); (c) **open world for inherited lines**, which are blocked only by a positive contradiction from **source probes** (§2.3); (d) a **verification-narrative ban** (no "verified", "tested on", "exercised" unless a verification record exists) | deterministic | partly (BC-04 identifiers, BC-14 versions/packages/formats, `claim_contradiction`, facts v6 `2db608b`) | probes for counts, existence/export, stub polarity; typed tokens beyond identifiers; provenance classifier; narrative ban |
| **M3** | Execution: BC-03 (examples executed/compiled in isolation) | execution | yes, but Python-heavy; .NET examples UNRESOLVED in this container | hosted Docker toolchain per ecosystem; a generated example must be PASS, never UNRESOLVED |
| **M4** | Install, package, registry and links: BC-02, BC-06, BC-14 | deterministic + registry reads | yes, 1.00 on every class in it5 | none |
| **M5** | Preservation: BC-05, BC-08, BC-17, `live_readme_loss`, `disposition_coverage`, supersession substance, the R14 rule set (`data/drop_decisions.json`) | deterministic | yes (content loss 1.00 in it5) | every R14 decision becomes a regression case (§4.1) |
| **M6** | Public-text form: BC-07, BC-12, `duplicate_paragraph`, `duplicate_opening_paragraph` | deterministic | yes (1.00) | none |
| **M7** | Benchmark parity: BC-17 against the **published aspose.org README** (equal to the live README where the aspose.org output is live upstream, per R2), plus a deterministic dimension scorecard | deterministic | BC-17 loss dimensions merged (`b892850`) | scorecard dimensions with "not lower than benchmark" |
| **M8** | Prose judgement (LLM), **narrow**: shown only prose lines, never asked about factual truth. Fixed categories: `promotional`, `generic_template`, `incoherent`, `misleading_framing`; plus one pairwise question "is this section at least as clear and usable as the benchmark's section of the same purpose?" | LLM | no (today's reviewer does all twelve jobs) | new prompt and contract, its own corpus |
| **M9** | Independent sampled audit: an agent with **repository access** (the method that produced the class audit) audits a stratified sample of accepted candidates claim by claim, with `path:line` evidence that code re-checks. The auditor is calibrated by seeded defects it is not told about. | agentic + human spot-check | no (the class audit was done once, by hand) | protocol, seeding, record |
| **M10** (Lane L) | Edit justification and minimality: R5 trigger verified; byte-identity outside edit hunks; new text goes through M2/M3 | deterministic | partly (`lane_l_review` holdouts) | trigger-evidence check, hunk byte-identity |

### 2.2 Responsibility matrix (each class has exactly one primary owner)

The matrix is data. It will be committed as `data/acceptance_responsibility.json` and read by the harness. A
defect label with no owner is an error, as `DEFECT_TIERS` already makes it.

| Class | Example | Primary | Backstop (never counted in the primary's gate) | Corpus that measures the primary | Gate (unchanged thresholds) |
|---|---|---|---|---|---|
| D1 stale revision / facts | live README edited after facts | M1 | — | synthetic stale-revision cases | recall ≥ 0.90 (expected 1.00) |
| D2 wrong version / package / install | `contradict_version`, `contradict_package_name`, `break_install_command` | M4 | M2 | it5 mutants + new | recall ≥ 0.90 |
| D3 broken link | dead or mis-targeted link | M4 | — | link mutants | recall ≥ 0.90 |
| D4 example fails | CONTRADICTED example printed; generated example not run | M3 | M2 (a CONTRADICTED example's text printed is also an M2 probe hit) | example mutants per ecosystem + it5 `ref:note-python …:4`, `ref:psd-python …:8` | recall ≥ 0.90 per ecosystem with a toolchain; false CONTRADICTED ≤ 0.02 on known-good examples |
| D5 false checkable claim (audit class **A**, mechanical, 20 of 23) | wrong type count, non-exported type, stub sold as working, wrong format | M2 (c) | M8 never | 20 real A cases + operators `count_mismatch`, `nonexistent_type`, `nonexported_type`, `stub_as_working`, `contradict_format`, `invent_api_name` | recall ≥ 0.90 per operator and pooled on real A |
| D6 ungrounded generated claim (audit class **D**, injected claims) | "183 public types organized into one module", "every capability exercised and verified" | M2 (b)+(d) | — | 4 real D + `inject_unsupported_claim` + new `verification_narrative`, `uncomputed_count` | recall ≥ 0.90 |
| D7 **true** claim the facts miss (audit class **B**) | enum member list, test dependency versions | **none may reject it**. Owner: the facts extractor (M2's input) | — | the 70 B spans + every clean twin | B spans counted in the **false-reject** gate; target 0 rejected |
| D8 unverifiable maintainer knowledge (audit class **C**) | platforms, editions, history | M5 (disposition `PRESERVE_ATTRIBUTED`, internal per R9; blocked only if contradicted) | M2 (c) for contradiction | the 14 C cases + new disposition cases | disposition correct ≥ 0.90; printed without public attribution 1.00 (BC-07) |
| D9 semantic description mismatch (residual A, 3 of 23: `CellFormatValue`, `Row`, `AssetInfo`) | "X represents the formatted value" for a style record | generated text: **prevented by construction**, since M2 allows a generated type description only from `docstring_full` and otherwise prints the signature alone. Inherited text: **M8-S**, a sub-question that shows the type's source snippet beside the description | M9 | 3 real + operator `misdescribe_type` (≥ 30) | recall ≥ 0.90; see §6 fallback |
| D10 content loss / drop | `drop_section`, `<ProjectReference>` drop | M5 | M7 | it5 mutants + every R14 decision | recall ≥ 0.90; R14 decisions reproduced 1.00 |
| D11 duplicate content | `duplicate_paragraph` | M6 | — | mutants | recall ≥ 0.90 |
| D12 form / R9 leak / naming | attribution line printed, wrong canonical name | M6 | — | mutants | recall ≥ 0.90 |
| D13 below benchmark | fewer verified examples, lower API coverage, lost items | M7 | M5 | benchmark-minus-item cases | recall ≥ 0.90 |
| D14 promotional / generic prose | `add_promotional_filler`, new `generic_template` | **M8** | — | ≥ 30 per operator | recall ≥ 0.90, reviewer alone |
| D15 incoherent or less usable than benchmark | reordered steps, orphaned lead-in, worse quick-start | **M8** (pairwise) | M9 | `incoherent_reorder` ≥ 30; pairwise twins | recall ≥ 0.90 |
| D16 (Lane L) unjustified or non-minimal edit | rewrite outside a hunk, edit without trigger | M10 | — | Lane L mutants | recall ≥ 0.90 |
| D17 label error (audit class **E**) | true sentence labelled contradiction | curation (§4.2), not a candidate defect | — | — | — |

**False-reject budget.** The end-to-end limit stays **≤ 0.10** on scored clean twins. It is split in advance so
that no single mechanism can use all of it: M2 ≤ 0.04, M3 ≤ 0.02, M5+M7 ≤ 0.02, M8 ≤ 0.02. Each sub-budget is
stricter than the whole, so nothing is loosened.

**End-to-end gate (the anti-shell-game rule).** Reassigning classes must not move a failure somewhere nobody
measures. So the composed gate is also measured as a whole, at the unchanged thresholds: **pipeline on-target recall
≥ 0.90 on held-out real defects of classes A+D, ≥ 0.90 per mutation operator, and ≤ 0.10 false reject**. The
end-to-end number has to pass on its own.

### 2.3 Why M2 can reach what token entailment (5c) could not

5c rejected 13 of 28 clean twins for two reasons. It applied entailment to **every** line, and the facts lacked
the B kinds. M2 removes both causes:

1. **The provenance split.** The closed world applies only to `generated` lines. `inherited` lines (byte-traceable to
   the live README; the audit puts 49 of the 69 B sentences there) are blocked only by a **positive contradiction**. A true
   inherited sentence the facts do not mention is therefore never rejected. This is goals §5 written as a rule. The
   other 20 B sentences are generated. They must now gain a fact (S1 measures how many facts v6 supplies), or the
   generator must stop writing them (S3). Either way the cost is a repair, never a public false claim.
2. **Source probes, not just facts.** For the mechanical A shapes, M2 asks an independent code path a typed question
   about the clone at the pinned SHA:

   | Probe | Question | Audit cases it decides |
   |---|---|---|
   | `count(kind, scope)` | how many public types, exported names, enum members, handlers | 5 count cases (note-python 39 vs 33, pdf-java, cells-rust 213 vs ~115, cells-python, cells-cpp 197) |
   | `exists(name)` / `exported(name)` | is this identifier defined, and is it reachable from the public entry point (`__all__`, `lib.rs` re-exports, `index.ts`) | 5 existence/export cases (`Workbook_Impl`, `RowModel`, `ModuleLoadPolicy`, xmldom ambient, string-union alias) |
   | `stub(member)` | does the body only throw `NotImplemented*`/`Unsupported*` (facts v6 `implementation` kind) | 6 stub cases (Scene.render, Watermark ×2, FileSystem zip ×2, WorkbookXmlMapper) |
   | `example_status(text)` | is this block the text of a CONTRADICTED example fact | 2 cases |
   | `package(name)` | registry state / manifest name | 2 cases |

   A probe has a third answer, **unknown**. Unknown never blocks inherited text, and for generated text it counts
   as "not entailed". A probe is a different code path from the facts extractor where that matters. The count probe
   is an independent AST/symbol walk, not a recount of extractor output, so one extractor bug cannot both produce a
   fact and confirm it (hidden factor H9).
3. **Predecessor lesson 1 stays closed.** A finding is cleared only by a typed entailment (fact id plus equal typed
   value at the same token). A substring match anywhere in the facts never clears one. `verdict.fold_verdict` keeps
   being the only fold.

---

## 3. Independence without an unreliable judge

The old design made one LLM the source of independence. Independence is a property of the **process**: the author
cannot influence the verdict, and the verdict's error rate is measured from outside. Seven properties provide it,
and each is checkable.

| # | Independence property | How it is enforced | How it is verified |
|---|---|---|---|
| I1 | **Separate code path.** The acceptance package does not import generation, reconciliation or repair modules. | a static import-graph check in CI (like the existing "no ACCEPT assigned elsewhere" invariant test) | test fails if an import is added |
| I2 | **Separate evidence.** Acceptance re-derives or re-verifies its evidence from the clone at the pinned SHA. Generator outputs (dispositions, the claim ledger, rationales) are **claims to be checked**, never proof. | M2 probes read source; M5 re-diffs against the live README bytes; M3 re-executes | a mutation that edits a disposition rationale to "verified" changes no acceptance verdict (test) |
| I3 | **The generator's citations are falsifiable.** For generated lines the generator must cite fact ids (it already does per unit for BC-04). A wrong citation fails; it never clears. | M2 (b) | `invent_api_name` / `inject_unsupported_claim` mutants with forged citations |
| I4 | **The judgement model differs from the generator wherever possible.** M8 sees only prose lines and no facts, so it has no fact-checking burden. | model route recorded per verdict | the generator and M8 routes differ in the record, or the owner-accepted exception (§6) applies |
| I5 | **Adversarial canaries per candidate.** Every acceptance run also runs the same gate over k seeded mutants **of this very candidate** (one per deterministic operator that applies). If any canary passes, that acceptance is void. | zero calls for M2–M7/M10 canaries. M8 canaries run on a hash-ranked 1-in-5 sample of candidates (cost bound). | the acceptance record carries canary ids and outcomes; a record without them is not an acceptance |
| I6 | **External error estimate.** M9 audits a stratified sample of accepted candidates per lane, using repository access and `path:line` evidence that code re-checks. The auditor is itself measured on defects **seeded blind** into accepted candidates. | §4.3 | auditor seeded recall ≥ 0.90; defective-accepted rate ≤ 0.10 |
| I7 | **Owner spot-check, optional and never gating.** R11 forbids routine owner dependence. The owner may sample M9's audit records; disagreement becomes a labelled case. | — | — |

Why I5 matters. A corpus measures a mechanism on the corpus's distribution. A canary measures that the gate was
working **on this candidate, in this ecosystem, today**. That closes the distribution-shift gap a once-off
calibration cannot (H12).

---

## 4. Calibration, redesigned

### 4.1 Per mechanism: what is measured, on what, against what

Every corpus is **pre-registered** (digests committed before any verdict, as in iteration 5) and **held out** from
the mechanism's own development. Labels mean **truth with respect to the repository at the facts revision**, as the
class audit decided them. They are never "what the facts say". So improving the facts can legitimately turn a false
reject into an accept without anyone touching a label.

| Mechanism | Corpus (pre-registered) | Inputs it must reuse | Measured | Gates (thresholds unchanged; min n is new and only adds strictness) | Provider calls |
|---|---|---|---|---|---|
| M1 | synthetic stale-revision, moved-live-README cases | — | recall; determinism (two runs byte-identical) | recall ≥ 0.90; determinism 1.00 | 0 |
| M2 | held-out real A (≥ 30: the 20 mechanical A of it5 are **dev**, so new A comes from class-auditing a hash-ranked slice of the 924 never-asked it4/it5 real cases); D; new operators ≥ 30 each; B spans; clean twins ≥ 50 | class-audit labels (A/B/C/D/E) as **inputs**; E corrected only in the new registration, with the audit cited as the reason | on-target recall per owned class; false reject on clean twins and on B spans | recall ≥ 0.90 per class (n ≥ 30); clean FR ≤ 0.04 | 0 |
| M3 | known-good examples and mutated examples (wrong member, wrong arg, removed import) per ecosystem with a toolchain | ASPOSE_ORG_EXAMPLE_VERIFIER_FINDINGS fixes | recall; false CONTRADICTED | recall ≥ 0.90 per ecosystem; false CONTRADICTED ≤ 0.02 | 0 (hosted runner minutes) |
| M4, M6 | existing operators | it5 mutants | recall | ≥ 0.90 (it5: 1.00) | 0 |
| M5 | `drop_section` and new drop operators; **every R14 decision as a case** (dropped item → decided outcome) | `data/drop_decisions.json` | recall; R14 agreement | recall ≥ 0.90; **R14 agreement 1.00** (a recorded ruling is a regression test, not a sample); FR ≤ 0.02 jointly with M7 | 0 |
| M7 | benchmark-minus-item cases; each benchmark against itself (must pass) | published aspose.org READMEs (local text, committed digests) | recall; self-parity | recall ≥ 0.90; self-parity 1.00 | 0 |
| M8 | clean twins ≥ 50; `add_promotional_filler` ≥ 30; `generic_template` ≥ 30; `incoherent_reorder` ≥ 30; `misdescribe_type` ≥ 30 (M8-S); pairwise twins ≥ 30; stability 20 × 3 | the 18 it5 promotional mutants are **dev** | reviewer-alone on-target recall; FR; first-reply JSON; stability | recall ≥ 0.90 per class; FR ≤ 0.02; JSON ≥ 0.90; stability ≥ 0.90 | ~350 expected, cap 500 (§6) |
| M9 auditor | ≥ 20 defects seeded blind (A, D and D9 shapes) into ≥ 10 accepted candidates | — | seeded recall; evidence validity (cited `path:line` exists and holds the text) | seeded recall ≥ 0.90; evidence validity 1.00 | 0 gateway calls (agent sessions) |
| **End to end** | union of the above, held out | — | pipeline on-target recall on real A+D; per operator; FR | ≥ 0.90; ≥ 0.90; ≤ 0.10 | included above |

**Statistical honesty.** The gate stays a point estimate against the unchanged threshold. Each gate now has a
pre-registered **minimum n**: 30 per recall class and 50 clean twins, so that 0.10 means at most 5. The Wilson 95 %
interval is reported beside each number. With 28 clean twins (iteration 5), two false rejects separate PASS from
FAIL, so the measurement had almost no power (H8).

**Where the clean twins come from (R13).** The portfolio runs that R13 makes the default produce candidates on all
36 registry repositories in both lanes. Each candidate is class-audited (the M9 protocol, applied as curation) and
its defects repaired into a twin. Clean twins are therefore a by-product of production, not something extra to
find.

### 4.2 Labelling protocol (so that "never relabel to pass" is mechanical)

1. A label is decided against the repository at the case's `facts_revision`, using the audit's classes A–E. An
   independent second labeller covers a hash-ranked 20 %, Cohen's κ is reported, and disagreements are resolved by
   the supervisor with the reason recorded.
2. Labels are frozen in a registration digest before any verdict. A changed label is only ever a **new
   registration** that carries a written reason (the class audit is the reason for the two E cases). It never edits
   an old one.
3. A label never depends on facts coverage. That is how a facts improvement can move a B case from "rejected" to
   "accepted" while the label stays where it was.

### 4.3 M9 audit protocol (the external anchor)

* **Sample.** For each lane, the first 5 accepted candidates, then a hash-ranked 20 % (minimum 2) of every later
  batch of 10. The sample is stratified by ecosystem.
* **Seeding.** Before the audit, a separate process seeds k ≥ 2 defects into ~half of the sampled READMEs (copies;
  never the seal) and records which ones in a sealed file the auditor cannot read.
* **Audit.** For every checkable claim, the auditor (an agent with clone access, not the gateway generator) records
  `supported | false | unverifiable` with `path:line` evidence. Code re-checks that every citation exists and
  contains the cited text.
* **Gates.** Seeded recall ≥ 0.90 (else the audit is void and repeated with a corrected protocol). Among unseeded
  candidates, the share with ≥ 1 class A/D/D9 defect must be ≤ 0.10, i.e. 0 of the first 5, ≤ 1 of 10, ≤ 2 of 25.
* **Every real finding feeds the system (R14 pattern).** It becomes a labelled case and a rule or fact kind. The
  re-certification then shows which seals the new check fails, and those get a bounded targeted repair. No seal is
  deleted or demoted (R10).

### 4.4 How the gate composes, and how it survives change (R10)

**Acceptance record** (one per seal, append-only, beside the seal):
`{seal_commit, lane, mechanism_versions: {M1..M10: v}, verdicts: {Mi: PASS|FAIL + findings}, canaries: [...],
m8: {model, prompt_version, unit_digests}, calibration_certificate: <acceptance_calibration entry ids>}`.

**ACCEPT** holds iff every applicable mechanism verdict is PASS, every canary was caught, and every mechanism version
in the vector holds a PASSED certificate (current or historical). A deterministic REJECT is final unless code
refutes it, as non-negotiable 5 requires.

**On a mechanism change** (the single change procedure that replaces "a new calibration iteration"):

| Step | Deterministic mechanism changed | M8 changed | Calls |
|---|---|---|---|
| 1 | re-measure that mechanism on its registration (CI job) | re-measure M8 on a **new** held-out registration | 0 / ≤ 500 |
| 2 | re-measure end to end | re-measure end to end | 0 |
| 3 | `recertify` every seal from stored outputs | re-ask M8 on prose units of accepted seals whose unit digests or M8 version changed | 0 / ~3 per seal |
| 4 | no-regression gate: no PASS flips to FAIL unless each flip is a justified genuine defect | same | 0 |
| 5 | R14 suite 1.00; canary suite | same | 0 |

A seal accepted under an M8 version that held a PASSED certificate **keeps counting** until it is re-asked. A
version bump alone never zeroes the count. This replaces `classify_review`'s exact-version match, which zeroes the
count on any prompt or logic bump (H7), with "each version in the record held a PASSED certificate, and the seal
re-certifies under current code". Certificates are append-only. A version's certificate is never withdrawn by a
later version. It is withdrawn only if that version's own measurement is found invalid, and that case is recorded
explicitly.

---

## 5. Hidden factors the earlier attempts overlooked

| # | Factor | Evidence | What the design does about it |
|---|---|---|---|
| H1 | **Facts coverage was the bottleneck, not judgement.** 69 of 100 "unsupported" claims were true and missing from the facts. | class audit §1 | facts v6 (landed `2db608b`) plus the provenance split; B counts as false reject |
| H2 | **Label semantics disagreed with the goals.** "Unsupported by the facts" was treated as "false", and the gate rewarded rejecting true maintainer content, against §5. | audit §3: gpt-oss "caught" 14/15 true claims | labels mean truth vs repository; B may not be rejected |
| H3 | **The same model generated and reviewed.** qwen3-next writes plausible claims and finds the same claims plausible (correlated blind spots). | manifest routes; it5 | M8 on a different route where allowed; facts decided by code |
| H4 | **A needle-in-haystack task.** ~22–53 lines and ~93–98 facts per unit, one false sentence among them; the model returned ACCEPT with no findings on 60 of 62 shown-defect units. | root cause §1 (e) | atomic typed claims checked by code; M8 sees prose only |
| H5 | **The reviewer was denied the evidence.** It saw a fact packet. The audit that succeeded had the **repository** and grep. | class audit method | M2 probes and M9 read source |
| H6 | **One question did twelve jobs.** Truth, preservation, structure and taste were scored in a single verdict, so one weak skill sank the whole gate. | it1–it5 | one primary mechanism per class |
| H7 | **Version coupling zeroes the count.** The calibration status and `classify_review` require an exact logic/prompt match, so any reviewer bump makes every accepted seal "uncalibrated". This is the predecessor failure R10 forbids, sitting in the acceptance count. | `portfolio_delivery_count.py` `classify_review` (lines 149–166); `calibration_status.py` docstring | append-only per-version certificates (§4.4) |
| H8 | **No statistical power.** 28 clean twins at a 0.10 limit decides PASS/FAIL on 1–2 cases. Stability n = 20. | it5 | minimum n, Wilson intervals, clean twins from production |
| H9 | **Common-mode failure.** Generator and verifier share the facts extractor, so an extractor bug both writes and confirms a claim. | design reading | independent probes for counts and existence; M9 |
| H10 | **Open world vs closed world.** Inherited text cannot be held to "must be entailed" (it destroys §5 content); generated text must be (§4 provenance). Treating both the same either rejects maintainers' truth or admits invented claims. | 5c FR 0.46; it4 v17 "repeats the original" rule | the provenance split |
| H11 | **Reference bases have no provenance.** aspose.org READMEs are reviewed `rendered=False`, with every line open world, unlike production. | it4/it5 plan | the harness classifies their lines against the live README, as the audit did (`inherited`/`generated`) |
| H12 | **Calibration is not proof on this candidate.** Ecosystem shift (C++/Go/TS docstrings, .NET without an SDK) changes behaviour. | it4 facts gaps; .NET UNRESOLVED | per-candidate canaries (I5) |
| H13 | **The verification environment is part of the verdict.** A missing toolchain turns examples UNRESOLVED; an import guard was read as a contradiction (E case `ref:html-python …:7`). | audit E; verifier findings | M3 on hosted toolchains; for generated examples, UNRESOLVED never counts as PASS |
| H14 | **False rejects are expensive and destructive.** Each costs repair rounds (calls), and repair under a reject pushes the generator to delete true content, i.e. preservation loss. | it4 FR 6/37; Imaging `<ProjectReference>` drop | FR sub-budgets; B never rejected; M5 blocks deletion |
| H15 | **Cost per candidate at portfolio scale (R13).** 65–81k-token packets and ~2–3 calls per case; 36 repos × 2 lanes × repairs × repeats is unbudgeted. | it1 §2(d), it5 calls | deterministic first (0 calls); M8 on prose units only (target ≤ 15k tokens, ~2–4 calls per candidate) |
| H16 | **Attribution is internal (R9).** The judge must know which lines are maintainer lines without the README saying so. | R9, `maintainer_lines` | M5/M8 read `dispositions.json`; BC-07 refuses public wording |
| H17 | **Goodhart and circular metrics (predecessor lesson 6).** A deterministic tier "at 1.00" on operators its authors designed can overfit. | it5 tier 1 | blind-seeded M9; real held-out A+D in the end-to-end gate; new operators written before rules are tuned, and their registration frozen first |
| H18 | **Label noise.** 2 of 113 labels were wrong. | audit E | second labeller, κ, new registration only |
| H19 | **Upstream-write gate wording.** R3 names "reviewer calibration PASSED" as an upstream-write gate. | R3 | owner action item (§7.4): confirm that acceptance calibration PASSED is the successor gate |
| H20 | **Model-route authority.** The owner withdrew gpt-oss on 2026-10-27 (qwen3-next only). A different judge model is an owner-level route decision. | it1 note | M8 first measured on qwen3-next with narrow scope; a second route only by owner action (§6 rung b) |

---

## 6. Staged implementation plan

Each stage ends with a verification that is re-run independently (the supervisor re-runs it; the worker never
grades itself) and with the R10 no-regression re-certification. Gateway provider calls are counted; "agent" means
supervisor subagent sessions, not gateway calls.

| Stage | Work | Verification (falsifiable) | Gateway calls | Card |
|---|---|---|---|---|
| **S0** | Adopt this design: decision-log entry; commit `data/acceptance_responsibility.json` (matrix §2.2) and the operator list **before** any rule is tuned | the matrix loader refuses an unowned label (test); registration digests committed | 0 | TC-013 |
| **S1** | Facts coverage: measure facts v6 (`2db608b`) against the 70 B spans, rebuilding the it5 corpus with new facts | ≥ 90 % of B spans gain a supporting fact (63 of 70), and none gains a contradicting one; report per kind; recertify gate OK (24 seals) | 0 | TC-013 |
| **S2** | M2: provenance classifier; typed closed world for generated lines (extend BC-04/BC-14); source probes `count/exists/exported/stub/example_status/package`; verification-narrative ban; docstring-only generated descriptions | **dev**: it5 A+D recall (20 mechanical A ≥ 0.90) and it5 clean twins FR ≤ 0.04. Tuning is allowed here and recorded. Mutation tests per probe. A negative control that disables the probe breaks the tests. | 0 | TC-014 |
| **S3** | Generator prevention: no uncomputed counts, no verification narrative, no description without a docstring (prompts and renderer) | M2 run over the 24 seals' stored outputs reports each violation; new candidates have none | 0 (applies to new generation only; no seal regenerated, R10) | TC-014 |
| **S4** | M3: hosted toolchain jobs per ecosystem (Docker, the existing two-job trust boundary); the generated-example rule | per-ecosystem mutated-example recall ≥ 0.90, false CONTRADICTED ≤ 0.02; .NET examples become PASS/CONTRADICTED, not UNRESOLVED | 0 | TC-015 |
| **S5** | M5/M7 additions: R14 cases suite; benchmark scorecard dimensions | R14 agreement 1.00; self-parity 1.00; benchmark-minus-item recall ≥ 0.90 | 0 | TC-015 |
| **S6** | Build the **held-out acceptance registration A1**: class-audit a hash-ranked slice of the 924 never-asked real cases plus new portfolio candidates (R13); ≥ 50 clean twins; new operators; labels per §4.2 | registration digest committed before any verdict; κ reported | 0 | TC-016 |
| **S7** | Measure M1–M7, M10 and end to end (deterministic part) on A1; harness writes `acceptance_calibration.json` mechanism entries | gates of §4.1; written only by the harness; PASSED impossible while any gate fails (existing fail-closed rule) | 0 | TC-016 |
| **S8** | M8: narrow prompt and contract (prose-only units, four categories plus pairwise plus M8-S); measure on A1's M8 slice | recall ≥ 0.90 per class, FR ≤ 0.02, JSON ≥ 0.90, stability ≥ 0.90 | **~350 expected, cap 500** (estimate run first with `estimate`, zero calls) | TC-017 |
| **S9** | Wire: acceptance record and canaries; `classify_review` reads certificates (§4.4); `propose.effect` refuses unless the acceptance record holds; I1 import check; CI job re-measuring deterministic mechanisms on every PR touching them | unit tests; negative controls (canary that passes → acceptance void; missing certificate → uncalibrated) | 0 | TC-018 |
| **S10** | Accept existing seals: recertify (0 calls), then M8 on prose units of the passing seals | each lane's count is reported; failing seals go to targeted repair | **~75 (≈ 3 × 24), cap 100** | TC-018 |
| **S11** | M9 audit batch 1 (seeded) on the first 5 accepted per lane | seeded recall ≥ 0.90; defective-accepted 0 of 5 | 0 (agent) | TC-019 |
| **S12** | Portfolio production (R13) under the gate; M9 continues per batch | per-lane counts toward 25; audit gate holds | ~3 per candidate for M8, plus generation and repair | TC-011 |

**Total gateway calls to end the problem: about 425 expected, at most 600.** For comparison, iteration 5 spent 786
+ 214. This fits inside the owner-approved 1,000-call calibration budget.

**Pre-decided fallback ladder for M8** (so that M8 cannot become the next stuck problem):

| Rung | Trigger | Action | Cost |
|---|---|---|---|
| a | S8 passes | done | — |
| b | S8 fails on qwen3-next | owner action: allow one non-generator route for M8 only; measure on a **new** held-out M8 registration | ≤ 500 |
| c | b fails, or the owner declines | remove the need for judgement **by construction**. Generated prose is limited to renderer templates and bounded lead-ins with a deterministic lexicon ban on promotional/superlative wording, which moves D14 for generated text to M6. For inherited text, D14/D15 become a disposition decision under the R14 pattern (M5). For M8-S, inherited type descriptions not supported by `docstring_full` are routed as `PRESERVE_ATTRIBUTED` and checked by M9. M8 becomes advisory and is not in the gate; D15 relative to the benchmark is covered by M7's scorecard and M9's rubric. | 0 |

Rung c is the guarantee. Even if no LLM ever passes, acceptance becomes reachable by mechanisms that are already at
1.00 on their classes. The LLM is used where it helps and is never on the critical path.

---

## 7. What changes, and what does not

### 7.1 `data/reviewer_calibration.json`

* **Semantics change.** It stops gating acceptance. It stays **byte-for-byte** as the frozen record of the
  monolithic reviewer (iteration 5, `NOT_PASSED`). Nothing may write `PASSED` into it, now or later, and a test
  asserts that. Its reader (`calibration_status.py`) keeps working for that historical record.
* **New file `data/acceptance_calibration.json`**, written only by the harness:
  `{schema_version: 1, status (derived: PASSED iff every mechanism in the responsibility matrix is PASSED and the
  end-to-end gates pass), responsibility_matrix_sha256, registration_sha256, mechanisms: {Mi: {version, corpus,
  measured_on, gates: [...], status, provider_calls}}, end_to_end: {gates}, certificates: [append-only {mechanism,
  version, status, measured_on, registration}], audit: {batches: [...]}}`.
  It keeps the fail-closed reading rules: a missing or malformed file, an unknown status, PASSED beside a failed
  gate, an unowned class, or a mechanism version with no certificate all read as `NOT_PASSED`. It keeps the rule
  that `PASSED_WITH_DECLARED_LIMITS` needs a non-empty owner acceptance and has no writer.

### 7.2 TC-007

| Field | Today | Redesigned |
|---|---|---|
| purpose | the reviewer reaches PASSED | the **acceptance mechanism set** reaches PASSED on held-out registration A1, every class owned, thresholds unchanged |
| depends_on | TC-006 | TC-006, TC-013 … TC-018 |
| write_paths | `data/reviewer_calibration.json` | `data/acceptance_calibration.json` |
| check | `calibration_status.py PASSED` | `calibration_status.py PASSED --file data/acceptance_calibration.json --matrix data/acceptance_responsibility.json` (exit 0 only if derived status PASSED) |
| negative control | set status NOT_PASSED | (1) set `mechanisms.M2.status` NOT_PASSED, and (2) delete one class from the matrix; **each** must make the check fail |
| closeout | do not dispatch TC-011 until accepted | unchanged |

TC-011 (`portfolio_delivery_count.py`): "independently accepted" becomes "a sealed, pipeline-good candidate whose
acceptance record holds (§4.4) under certificates in `acceptance_calibration.json`". The separate outcomes (c)–(e)
are unchanged.

### 7.3 Not changed

| Item | Stays |
|---|---|
| thresholds | recall 0.90, false reject 0.10, JSON 0.90, stability 0.90; only minimum n and FR sub-budgets are **added** |
| iteration 5 | recorded `NOT_PASSED`; never re-scored |
| frozen labels | never edited; corrections only in a new registration with the written reason |
| on-target scoring | a catch must name the defect |
| non-negotiable 5 | a REJECT blocks unless code refutes it; `fold_verdict` is the only fold |
| R9 | no public attribution; BC-07 |
| R10 | re-certify, never regenerate on a bump, never demote, no-regression gate |
| R3 | allowlist and first PR as draft (see 7.4) |
| owner budget | ≤ 1,000 calls per calibration iteration |

### 7.4 Owner action items (only these)

1. **R3 wording.** Confirm that "reviewer calibration PASSED" in R3 is satisfied by `acceptance_calibration.json`
   PASSED. This is asked because it touches external write authority.
2. **Only if M8 rung b is reached:** allow one non-generator model route for M8.

---

## 8. The criterion that ends the problem permanently

The problem is **closed** when all of the following hold. Each is checked by a command, not by a narrative.

| # | Criterion | Check |
|---|---|---|
| E1 | `data/acceptance_calibration.json` status PASSED, written by the harness on held-out registration A1, with every class in the matrix owned and gated at unchanged thresholds and minimum n | `calibration_status.py PASSED --file … --matrix …` |
| E2 | End to end on A1: held-out real A+D on-target recall ≥ 0.90; every operator ≥ 0.90; clean false reject ≤ 0.10 with n ≥ 50 | harness report in the file |
| E3 | ≥ 1 candidate independently accepted **per lane** under it, with every canary caught | `portfolio_delivery_count.py` |
| E4 | M9 batch 1: auditor seeded recall ≥ 0.90; 0 of the first 5 accepted per lane defective | audit record |
| E5 | One real mechanism change merged through §4.4's procedure in CI with no count lost and no full recalibration | CI run + recertify gate |
| E6 | TC-007 ACCEPTED by `gatecli verify`/`review` (two clean re-runs plus both negative controls) | gate receipt |

**Why it stays solved.** After E1–E6 there is no "calibration iteration" left to fail. A change is measured per
mechanism, mostly at zero calls, in CI. Defects found by audit or by owner review become a labelled case plus a rule
or fact kind (the R14 loop), re-certification applies them, and targeted repair fixes the affected seals. The count
then grows with production (R13) toward 25 per lane. If the judgement component fails, rung c removes it from the
critical path at zero cost. No future failure mode returns the system to an all-or-nothing reviewer gate.
