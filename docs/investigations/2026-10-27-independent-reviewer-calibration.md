> NOTE (2026-10-27, owner decision): the gpt-oss route was withdrawn by the owner; the system uses qwen3-next only. This file is kept unchanged as a historical measurement record and its route recommendation (section 7) is superseded; see 2026-10-27-reviewer-calibration-iteration-2.md.


# Independent LLM reviewer, Phase 3: live probe and calibration

Date: 2026-10-27. Plan: `plans/PLAN_independent_llm_reviewer.md` (D6, D9 V4-V6, section 4 phase 3).
Status of the reviewer after this investigation: **the gate FAILS; gpt-oss is not yet fit to review,
and neither is qwen3-next.** The numbers below are observations from one gateway on one day. No rule,
clearance or threshold was loosened to produce them, and nothing here is owner-reviewed.

Raw data (all of it, nothing summarised away): `docs/investigations/2026-10-27-reviewer-calibration-data/`.
Commands to repeat it: section 8.

## 1. Budget and what ran

Every call went through `core/llm/jobs.run_job` (via `readme.review.llm_review.review_with_model`),
so every call is a ledger record; the cap was enforced by `Ledger.reserve_provider_call` before a
request was sent. The gateway key and endpoint were read from the environment and never logged
(the data directory was checked for both).

| Stage | Physical provider calls | Cap |
|---|---|---|
| 1. Probe (`ledger-probe.jsonl`) | 8 | 8 |
| 2-3. Calibration (`ledger-stage3.jsonl`) | 157 (156 replies, 1 transport retry) | 200 |
| of which: gpt-oss full pass | 56 | |
| of which: qwen3-next full pass | 58 | |
| of which: 3 fresh repeats, 5 cases | 24 | |
| of which: re-ask shape diagnostic (3 cases) | 6 | |
| of which: prompt-variant trial (8 cases) | 13 | |

43 calls of the 200 were deliberately left unspent: the questions they could still answer would not
change the recommendation. The run never reached the cap.

## 2. Stage 1: live probe (8 calls)

One complete real candidate, the Python cascade output of hosted run 9
(`aspose-3d-foss/Aspose.3D-FOSS-for-Python`), plus the .NET output of run 7 for a second view.
Run 9's deterministic reviewer verdict is ACCEPT with no finding; its S9 blocking checks BC-02 (the
registry's ownership receipt for the package name) and BC-07 (a dangling colon and a "listed below"
pointer inside two inherited units) FAIL, so production would not have sent it to S10. Run 7 passes
every deterministic check.

| # | Model | Candidate | prompt tok | completion tok | seconds | Outcome |
|---|---|---|---|---|---|---|
| 1 | gpt-oss | run 9 | 77277 | 2797 | 35.8 | first reply contract-valid; REJECT_FACTUAL, 2 findings |
| 2 | qwen3-next | run 9 | 78675 | 1546 | 42.9 | contract-valid; REJECT_PRESENTATION, 8 findings |
| 3 | gpt-oss | run 7 | 67906 | 3432 | 52.0 | contract-valid; REJECT_FACTUAL, 1 finding |
| 4 | qwen3-next | run 7 | 69014 | 22 | 11.9 | contract-valid; ACCEPT, 0 findings |
| 5-6 | gpt-oss | run 9 (repeat A) | 77277 / 77759 | 2161 / 346 | 32.8 / 4.8 | first reply broke the contract (a factuality finding with no product fact); re-ask returned EMPTY content: ReviewUnavailable |
| 7-8 | gpt-oss | run 9 (repeat B) | 77277 / 77901 | 3285 / 470 | 34.6 / 7.4 | first reply broke the contract (a quote not in its named section); re-ask returned EMPTY content: ReviewUnavailable |

**(a) The per-kind `oneOf` call schema.** Accepted by the gateway for strict `json_schema` on both
models, in every call of the investigation: every first reply (about 160 across the probe and stage 3)
parsed and matched the schema; the only non-JSON replies were gpt-oss's empty re-ask replies (5.1),
which is not a schema problem. **No flattening is needed and `packet.py` was not changed.**

**(b) `max_output_tokens: 6000` for gpt-oss.** Not enough headroom. Over the 99 gpt-oss replies of
stage 3: median 2539 completion tokens, 23 replies above 4000, and **2 hit the 6000 ceiling**
(`finish_reason: length`, a hard `JobError`, recorded as `TruncatedOutput`). qwen3-next peaked at
2452. gpt-oss reasons first: in the one first reply captured raw, `reasoning_content` was 12,932
characters before a 1,907-character JSON answer (`probe-raw-messages.jsonl`). Decision: a reasoning model needs a budget of at least ~9000, or the
reviewer should not run on one. Not changed here (it is a manifest edit that changes the request
hash and belongs with the route decision, see section 7).

**(c) First-reply validity and finding quality.** Read against the candidates, not trusted:

* Probe 1 (gpt-oss, run 9). F02 (a paragraph ending in a colon with nothing after it) is real: it is
  BC-07's finding about inherited unit 039. F01 quotes the README's own sentence that the package
  "could not be confirmed on PyPI" and calls it a contradiction; the sentence is the renderer's honest
  statement of the BC-02 receipt, so `contradiction` is the wrong kind, but the README does print an
  internal diagnostic, which is a real flaw. Neither finding is invented.
* Probe 3 (gpt-oss, run 7). F01 is a genuine catch: the Scope section says the library "exposes
  `Aspose.ThreeD.Render` and `Aspose.ThreeD.Utilities` for rendering", while inherited unit 061 says
  rendering is not implemented in this FOSS build. No deterministic rule saw it, and qwen3-next
  ACCEPTed the same candidate (probe 4).
* Probe 2 (qwen3-next, run 9), 8 findings: one real (the README says "337 types" in one place and
  "305 public types" in another), the rest renderer-owned layout (the diagram) or preference against
  the original, which the prompt rules out of scope, or a claim about text the candidate does not
  contain. qwen3-next's findings are mostly `quality`, which no clearance can ever disprove.
* First-reply contract validity over the 4 gpt-oss first replies of the probe: 2 of 4. The re-ask
  succeeded 0 of 2 (see 5.1).

**(d) Packet size.** 65,000-81,000 prompt tokens per call (median 68,000 for gpt-oss, 69,000 for
qwen3-next), of which the two READMEs and the facts are almost all. Latency: gpt-oss median 31 s, maximum 88 s; qwen3-next median 27 s, maximum 59 s.

## 3. Stage 2: the corpus and the harness (all offline, tested)

Code: `src/repo_presenter/readme/review/calibration/` (`sources`, `mutations`, `corpus`, `harness`,
`reviewers`, `outcomes`), runner `scripts/run_reviewer_calibration.py`, 75 tests in
`tests/readme/review/calibration/`.

* **Bases (real complete candidates, re-derived offline from their cascade artifacts):** run 5 and
  run 7 (.NET, `aspose-3d-foss/Aspose.3D-FOSS-for-.NET`, two different authored candidates) and run 9
  (Python). Run 2, run 3 and the sealed bundle fail their own S9 checks. Of the 36
  `scripts/_lane_r_output` directories, 15 (net or python, with complete artifacts) were re-derived after
  cloning each repository and re-running the deterministic stage: none passes (their dispositions predate
  the accounting step, so each reports lost live-README content). The rest are java, go, cpp, rust or
  typescript, which the renderer does not support (`ConfigError: no ecosystem spec registered`), or
  lack artifacts. They are therefore not corpus bases; the two recorded defects below are the only
  non-net/python material.
* **Clean twins.** A twin is its base with the defects this project's own reading found removed, each
  removal recorded as data (`REPAIRS` in the runner):
  run 7: `full round-trip fidelity` (no fact says it; only the maintainers' README does) and the Scope
  sentence that says the library exposes rendering (contradicts inherited unit 061); run 5: `full
  round-trip fidelity`; run 9: none possible, because its two BC-07 items sit inside inherited units that
  must print verbatim (editing them fails BC-03/BC-05). **Run 9's twin is therefore a known-flawed
  baseline, not a clean candidate:** BC-02 and BC-07 are carried as its stated baseline, and it also
  contains the PyPI diagnostic sentence and the 337-vs-305 inconsistency. It is scored as a clean twin
  anyway because that is the only Python material, and its results are read with that in mind.
  Only **3 clean twins** exist (the plan asked for at least 4). A fourth was available only by scoring
  a recorded twin whose deterministic context is stale; two such twins (font, duplicate opening) were
  asked and reported separately, never in the false-reject gate.
* **Mutants (26),** one per operator per base where the operator applies: `inject_unsupported_claim`,
  `contradict_version`, `contradict_package_name`, `contradict_format`, `drop_section`,
  `duplicate_paragraph`, `break_install_command`, `invent_api_name`, `add_promotional_filler`. Each
  differs from its twin in exactly one declared span (a test per operator proves the mutant is the twin
  with that span replaced and nothing else, that injected strings are no fact value, and that each
  mutant carries the words a finding about it must mention).
* **Real defects (5):** run 7 unsupported claim, run 7 contradiction, run 5 unsupported claim, and the two
  recorded cases: the aspose-font-foss inherited install command `pip install "aspose-font[mcp]"`
  (python) and the ninth cascade's duplicate opening (typescript). The two recorded READMEs are used as
  written; their dispositions are stale against today's facts, so their repaired twins are kept but
  unscored, and the duplicate opening has no twin.
* **Size:** 35 cases (3 clean + 1 unscored twin + 5 real defects + 26 mutants), 3 ecosystems (net,
  python, typescript). Class sizes: contradiction 10, unsupported_claim 5, content_loss 3, broken_install
  3, duplicate_paragraph 4, invented_api 3, promotional_filler 3.
* **What the deterministic stage alone does** (the `deterministic stage alone` column below): it
  blocks all 3 content-loss, all 3 broken-install and all 3 invented-API cases, 4 of 10 contradictions
  (the three format edits and run 9's version edit; the prose version and package-name edits slip
  through), 1 of 4 duplicates (the recorded duplicate opening), and none of the unsupported claims or
  filler.
* **A catch must be on target.** Reading the first results showed that a REJECT can be for a reason
  unrelated to the defect (section 5.4). The harness therefore scores a catch only when a blocking
  finding mentions the defect (`Case.targets`), and reports the plan's literal "any rejection" recall
  beside it. Both are given below.
* **The gate cannot be passed by a stub.** Tests: `always_accept` fails every recall gate;
  `always_reject` fails the false-reject gate and, being on target nowhere, every recall gate; a gate
  with no measurement fails; an oracle reviewer passes every gate, so the gate is passable.

## 4. Stage 3: results

Two models ran the same 35 cases (gpt-oss as routed by prompt v15; qwen3-next by override), once each,
cache-bypassed against a fresh store. Then 3 fresh repeats of 5 gpt-oss cases. "Unavailable" is a
review that could not be obtained (second invalid reply, or a hard error); it is never counted as an
ACCEPT or as a catch.

### 4.1 Per-case outcomes

`on target` = a blocking finding mentions the injected or recorded defect; `off target` = it rejected
for another reason. For clean rows only the verdict is meaningful.

| case | class | deterministic stage alone | gpt-oss | qwen3-next |
|---|---|---|---|---|
| run5/clean | clean | - | accept | unavailable |
| run5/real:unsupported_claim:0 | unsupported_claim | - | reject, off target | unavailable |
| run5/inject_unsupported_claim | unsupported_claim | - | unavailable | unavailable |
| run5/contradict_version | contradiction | - | reject, on target | unavailable |
| run5/contradict_package_name | contradiction | - | reject, on target | reject, on target |
| run5/contradict_format | contradiction | BC-04 | unavailable | unavailable |
| run5/drop_section | content_loss | BC-05,BC-06,disposition_coverage,live_readme_loss | unavailable | accept |
| run5/duplicate_paragraph | duplicate_paragraph | - | unavailable | unavailable |
| run5/break_install_command | broken_install | BC-02,BC-14,claim_contradiction | unavailable | unavailable |
| run5/invent_api_name | invented_api | BC-04 | unavailable | unavailable |
| run5/add_promotional_filler | promotional_filler | - | unavailable | unavailable |
| run7/clean | clean | - | accept | reject |
| run7/real:unsupported_claim:0 | unsupported_claim | - | unavailable | accept |
| run7/real:contradiction:1 | contradiction | - | reject, on target | reject, on target |
| run7/inject_unsupported_claim | unsupported_claim | - | unavailable | accept |
| run7/contradict_version | contradiction | - | reject, on target | accept |
| run7/contradict_package_name | contradiction | - | unavailable | unavailable |
| run7/contradict_format | contradiction | BC-04 | accept | accept |
| run7/drop_section | content_loss | BC-06,disposition_coverage,live_readme_loss | reject, off target | accept |
| run7/duplicate_paragraph | duplicate_paragraph | - | accept | unavailable |
| run7/break_install_command | broken_install | BC-02,BC-14,claim_contradiction | unavailable | reject, on target |
| run7/invent_api_name | invented_api | BC-04 | reject, on target | reject, off target |
| run7/add_promotional_filler | promotional_filler | - | reject, off target | reject, on target |
| run9/clean | clean | - | unavailable | reject |
| run9/inject_unsupported_claim | unsupported_claim | - | unavailable | reject, off target |
| run9/contradict_version | contradiction | BC-05,disposition_coverage | unavailable | reject, on target |
| run9/contradict_package_name | contradiction | - | unavailable | unavailable |
| run9/contradict_format | contradiction | BC-04 | unavailable | reject, off target |
| run9/drop_section | content_loss | BC-05,BC-06,disposition_coverage,live_readme_loss | unavailable | unavailable |
| run9/duplicate_paragraph | duplicate_paragraph | - | reject, off target | unavailable |
| run9/invent_api_name | invented_api | BC-04 | unavailable | unavailable |
| run9/add_promotional_filler | promotional_filler | - | unavailable | unavailable |
| font/clean (unscored twin) | - | disposition_coverage,live_readme_loss | reject | reject |
| font/recorded:broken_install | broken_install | claim_contradiction,disposition_coverage,live_readme_loss | reject, off target | reject, off target |
| duplicate_opening/recorded | duplicate_paragraph | disposition_coverage,duplicate_opening_paragraph,live_readme_loss | reject, off target | reject, on target |

(The first pass also asked a duplicate-opening "twin" identical to the defect, 2 calls per model; the
corpus builder no longer creates it and it is not counted anywhere.)

### 4.2 Metrics and gates (reviewer alone; "pipeline" adds the deterministic stage)

| Measure | gpt-oss | qwen3-next | Gate |
|---|---|---|---|
| recall, contradiction (n=10), on target / any rejection | 4/10 / 4/10 | 3/10 / 4/10 | >= 0.90 |
| recall, content loss (n=3) | 0/3 / 1/3 | 0/3 / 0/3 | >= 0.90 |
| recall, unsupported claim (n=5) | 0/5 / 1/5 | 0/5 / 1/5 | >= 0.90 |
| recall, broken install (n=3) | 0/3 / 1/3 | 1/3 / 2/3 | >= 0.90 |
| recall, duplicate paragraph (n=4), invented API (n=3), filler (n=3), on target | 0/4, 1/3, 0/3 | 1/4, 0/3, 1/3 | not gated |
| pipeline recall (deterministic + reviewer, on target): contradiction / content loss / unsupported / install | 8/10, 3/3, 0/5, 3/3 | 6/10, 3/3, 0/5, 3/3 | >= 0.90 |
| false-reject on clean twins (n=3) | 0/3 (1 unavailable) | 2/3 (1 unavailable) | <= 0.10 |
| JSON/schema-valid first reply | 35/35 = 1.00 | 33/33 = 1.00 | >= 0.90 |
| **contract-valid first reply** (no re-ask needed) | 16/35 = 0.46 | 12/33 = 0.36 | (not in plan) |
| reviews that ended unavailable | 19/35 = 0.54 | 16/35 = 0.46 | - |
| re-asks that produced a contract-valid reply | 0/19 | 5/21 | - |
| stability, identical verdict over 3 fresh reviews (n=5 cases) | 1/5 = 0.20 (that one was unavailable 3 times) | not run | >= 0.90 |
| approved yield (clean twins the pipeline approves) | 2/3 | 0/3 | - |
| content-loss rate (content-loss mutants the pipeline approves) | 0/3 = 0.00 | 0/3 = 0.00 | - |
| cost, physical calls per case | 54/35 = 1.54 | 57/35 = 1.63 | - |

**Gate verdict, gpt-oss (reviewer alone, on target):** recall contradiction FAIL (0.40), content loss FAIL
(0.00), unsupported claim FAIL (0.00), broken install FAIL (0.00); false-reject PASS (0.00, but on only
the 2 clean twins that returned a verdict, n=3 asked); JSON-valid first reply PASS (1.00); stability FAIL
(0.20, n=5). Under the plan's literal "any rejection" recall it fails the same four (0.40, 0.33, 0.20,
0.33). **qwen3-next fails these too and also false-reject (0.67).** The pipeline as a whole passes
content loss and broken install only because the deterministic stage catches them before any model
is asked; it fails contradiction (0.80) and unsupported claim (0.00).

Stability needs care: of the 15 fresh gpt-oss reviews, 9 were unavailable. The verdict-bearing repeats
did not disagree with each other (run7/clean accept twice, run7/duplicate_paragraph accept twice;
run7/contradict_version and run7/invent_api_name returned one verdict each), but n is far too small
to call the model repeatable, and a model that is unavailable 60% of the time is not stable in the
sense that matters.

### 4.3 Adjudication of what the models actually said

* **gpt-oss on the clean twins:** pass 1 accepted run5/clean and run7/clean and was unavailable for
  run9/clean (a quote it placed in the wrong section, then an empty re-ask); the repeat run accepted
  run7/clean twice more and was unavailable for run5/clean three times. So 4 verdict-bearing reviews,
  4 ACCEPT, 0 rejects, on 2 candidates: the 0.00 false-reject rate rests on that.
* **gpt-oss rejected 11 scored candidates; 5 on target, 6 off target.** On target: run5 and run7 wrong
  version (2), run5 wrong package name, run7 invented API (`SceneTurbo`), run7's real rendering
  contradiction. Off target: run5's real "round-trip fidelity" case was rejected for a missing
  "Enterprise Relationship" section; run7's dropped Scope section for an unrelated claim about a `using`
  line; run7's filler for an omission in Scope; run9's duplicate for an install command; the font install
  defect for an unrelated `.ttf` claim about EotFont; the duplicate opening for a "License section is
  missing" that is false (the candidate has one). A recurring invented demand (an "Enterprise
  Relationship" section, sometimes with an empty quote) appears in three gpt-oss rejects.
* **gpt-oss never flagged the two "full round-trip fidelity" cases (run5, run7) as such**, nor any
  injected unsupported claim: 4 of its 5 unsupported-claim reviews were unavailable for one reason
  (5.2), and the one verdict was off target.
* **qwen3-next on clean twins:** run7/clean got 6 findings and run9/clean 8, all `quality`, almost all
  preferences against the original or comments on renderer-owned layout, which the prompt tells the
  reviewer is out of scope. Quality findings can never be cleared (D2), so qwen3-next would block
  nearly every candidate. One finding on run9 (337 vs 305 types) is a real flaw of the twin.
* **One clearance fired in 45 verdict-bearing reviews:** `absence_present` cleared a qwen3-next claim
  that a `<details>` wrapper was missing from the API section (all three strings are there). The
  omission findings of both models named phrases that really are absent from the section, so none was
  disproved.
* Run 9's twin is a known-flawed baseline (section 3); a REJECT of it is not clearly a false reject.

## 5. Why the reviewer is not usable yet: four failures, with evidence

### 5.1 The re-ask returns nothing for gpt-oss (a bug in the interaction, not in the model's judgment)

Of the 27 gpt-oss re-asks in the ledgers (the probe's 2 and stage 3's 25 in the standard shape), 26
returned no content (JSON error at position 0, a few hundred completion tokens) and 1 hit the 6000-token
ceiling. Where raw capture was on, the reply was `content: null` with `finish_reason: stop` and no
`reasoning_content`. qwen3-next's re-asks returned content (5 of 21 became valid). The re-ask is
`[system, user, assistant(bad reply), user(correction)]`. Diagnostic (3 calls' worth of first replies,
6 calls, `reask-flat`): the same re-ask folded into ONE user message (previous reply quoted inside it)
returned non-empty JSON 3/3; those replies were still contract-invalid, so the empty-content defect is
real but fixing it does not by itself recover the reply. The shape lives in `core/llm/jobs._re_ask`, shared by
every job, so it was NOT changed here (blast radius: all authoring stages that run on qwen3-next).

### 5.2 The contract forbids the model from reporting an unsupported claim correctly

D4 requires a factuality finding to cite at least one non-inherited product fact. An
`unsupported_claim` is, by definition, a claim **no fact supports**, so there is none to cite.
Across the 59 invalid first replies kept in the stores (gpt-oss 37, qwen3-next 22), 27 findings failed
that rule: **25 were `unsupported_claim` findings, 24 of them with an empty `fact_ids`** (the model
told the truth), and 2 were contradictions (one citing only inherited text, one citing none). In 9 of
the 59 invalid first replies (8 gpt-oss, 1 qwen3-next) this was the ONLY error. This one rule makes the "unsupported claim"
gate class (the plan's own motivating example) structurally unreachable. Recommended: amend D4 so that
`unsupported_claim` needs a quote and no fact while `contradiction` still needs a fact, with a failing
test first (a contradiction with no fact must still be invalid). Not done here: it is the reviewer's own
contract, and the instruction was to report, not to loosen.

### 5.3 The models cannot reliably copy a quote into the right section

Of the invalid first replies, the dominant error is `quote is not the candidate's <section> text`. An
offline experiment (no calls) re-labelled every quote with the section it is actually in: that would have
made only 6 of 32 invalid gpt-oss replies and 0 of 22 qwen3-next replies valid. Most remaining quotes
are not in ANY section verbatim (reformatted tables and mermaid, joined lines, abbreviated text). So
this is quote infidelity, not mislabelling. A prompt paragraph telling the model where a quote must
live and which facts to cite (a scratch "v16", not committed) gave 3 contract-valid first replies in 8
cases that had all failed before, which is the same as the baseline rate on a fresh draw (6/15 in the
repeat run): **no demonstrated effect**, n=8.

### 5.4 A rejection is not a catch

Section 4.3: 6 of gpt-oss's 11 rejections are for a reason unrelated to the defect. A gate on rejections
alone would have passed `run5/real:unsupported_claim` and `run7/drop_section` for the wrong reason.

### 5.5 The 6000-token output budget (answer to 2(b))

2 of 99 gpt-oss replies truncated (hard failure), 23 exceeded 4000 tokens.

## 6. Limitations of these numbers

* Small samples: 3 clean twins (2 with a verdict from gpt-oss), 3-10 cases per class, 5 repeat cases.
  A single contract-valid gpt-oss reply per case is what most per-case rows rest on.
* One gateway, one day, temperature 0 and seed 1; the gateway is not deterministic (the same request
  returned an unavailable and then a valid reply for the identical duplicate-opening text).
* Bases come from one repository family (aspose-3d-foss) in two ecosystems; no java/go/cpp/rust/
  typescript candidate could be re-rendered. Cohort-level claims are out of reach.
* The Python twin is a known-flawed baseline. The recorded cases use stale dispositions.
* "On target" is a keyword test on the finding's quote and text; it was cross-checked by reading the
  findings of all 11 scored gpt-oss rejections and agreed with every judgment made by hand; the
  qwen3-next flags were not all read.

## 7. Recommendation

**Route: keep `gpt-oss` as the reviewer's route (independence, D6a) but do not enable the gate for any
cohort or PR path yet; do not fall back to qwen3-next.** qwen3-next is the same model that authors the
candidates, ACCEPTed the uncurated run 7 in the probe (both real defects in it), missed the version
edit and both real unsupported claims in the corpus (though it caught the rendering contradiction when
isolated), and false-rejected 2 of 3 clean twins with `quality` findings no clearance can disprove. gpt-oss, when it answers, was precise on
literal contradictions (version, package name, API name, the real rendering claim) and never rejected a
clean twin it answered on, but it answers a contract-valid review only 46% of the time and its re-ask is
empty. Changes to make, each with its failing test or measurement first, then re-run the same corpus
(`scripts/run_reviewer_calibration.py`, section 8) before reading any new number:

1. **Contract (new card, test first):** `unsupported_claim` needs a quote, not a product fact (5.2).
   Offline-measurable immediately against the stored replies in `replies.jsonl`: 8 of 38 invalid
   gpt-oss first replies had it as their only error.
2. **Re-ask shape for reasoning models (core change, blast-radius query first):** a single user message
   instead of an assistant turn (5.1). Falsifier: the scripted client returns empty content for the
   current shape.
3. **Output budget:** `max_output_tokens` of at least 9000 for the gpt-oss route (5.5), or shorten the
   reasoning. This changes the request hash, so it is a reviewer-scope recheck only (D8).
4. **Quote fidelity (design decision for the supervisor):** have the model cite line numbers of the
   numbered candidate and let code extract the quote and derive the section, instead of asking a
   model to retype text. It removes both failure modes of 5.3 and the "wrong reason" class of 5.4 can then
   be scored mechanically. This is a packet, prompt and contract change.
5. **Enlarge the corpus before the next gate reading:** at least 4 vetted clean twins (needs a Python
   candidate that passes S9, so a fresh cascade run or a pre-LLM-clean Lane R refresh), n >= 10 per gated
   class, and 10 repeat cases.

No new clearance is recommended on this evidence: the one clearance that fired (`absence_present`) did
its job, and the wrong findings seen were `quality` or `contradiction` kinds, which D2 says no code can
disprove.

## 8. Reproduce

```
PYTHONPATH=src python scripts/run_reviewer_calibration.py corpus \
  --work run5=<run5>/.present-work --work run7=<run7>/.present-work --work run9=<run9>/.present-work \
  --recorded-clones <dir with the clones of the two recorded repositories>
PYTHONPATH=src python scripts/run_reviewer_calibration.py live --out <dir> --cap 200 --per-class 9 --tag gptoss1 ...
# fresh repeats: --fresh --repeats 3 --only <case ids>;  another model: --model qwen3-next;
# a candidate prompt: --prompts <manifests dir>
```

`--work` points at the extracted `.present-work` of a downloaded hosted `present` run. The run
directories used here (hosted runs 40472312302, 40479146713, 40489172171) are not committed.
The first full pass (`results-gptoss1.jsonl`, `results-qwen1.jsonl`) was written before the harness's
outcome words were lower-cased and before on-target scoring, so its verdicts are upper-case and carry no
`evidence` field; the tables above were recomputed from it and the stored replies with the committed
code. Stage 3's `ledger-stage3.jsonl` has 157 physical attempts, 112 `response_invalid` markers (rejected
replies, no request sent) and one `connection_error` retry.
