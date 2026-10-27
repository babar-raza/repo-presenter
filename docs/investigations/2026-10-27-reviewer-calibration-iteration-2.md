> NOTE (2026-10-27): measured on qwen3-next only. The owner withdrew the gpt-oss route (binding decision, same day); no call in this iteration went to it (0 of 121).

# Independent LLM reviewer, Phase 3b: the four fixes, the re-measurement, and why the gate still fails

Date: 2026-10-27. Follows `2026-10-27-independent-reviewer-calibration.md` (iteration 1; its route
recommendation is superseded). Plan: `plans/PLAN_independent_llm_reviewer.md` (amendments in section 7).
Raw data: `2026-10-27-reviewer-calibration-iteration-2-data/` (every result line, every stored or
rejected reply, the ledger, the corpus listing; the gateway key and endpoint appear nowhere, checked).

**Status: the gate FAILS on qwen3-next.** Two of seven criteria pass (JSON-valid first reply, stability). The four
recall gates and the false-reject gate fail. Precision and reply validity improved a great deal; recall did
not. No threshold, rule or clearance was loosened, none was added, and nothing here is owner-reviewed.

## 1. What was fixed (each failing-test-first, each with a falsifier that makes its tests fail)

| # | Cause (iteration 1) | Change | Tests | Falsifier (verified to fail the tests) |
|---|---|---|---|---|
| 1 | D4 demanded a product fact of an `unsupported_claim`, which has none by definition (24 of 27 fact errors) | `contradiction` still needs one (any criterion); `unsupported_claim` and `quality` need none; their checkable property is the cited text, derived verbatim from the candidate. A mechanical audit of the claim's distinctive terms (identifiers, numbers, quoted phrases) against the SUPPORTED fact values and the original README is recorded as the finding's `evidence` and **decides nothing**. **No clearance was added**: the terms of a false claim are often all real ("converts glTF to STL"), so overlap cannot prove a claim supported, and any such rule is the 27-of-30 shortcut; `test_no_clearance_reads_a_quote_against_a_fact_value` and the closed catalogue stay as they were. A negative control proves an unsupported claim whose terms are all fact values still blocks. | `tests/readme/review/test_cited_lines.py` (32) | `FACTLESS_KINDS` emptied; `needs_fact` for contradiction removed; audit evidence dropped |
| 2 | gpt-oss returned nothing on the conversational re-ask | `reask_shape: single_user` is a per-manifest option of `core/llm/jobs._re_ask` (default `conversation`, unchanged). Blast radius in section 2. It is **not enabled** for the reviewer: its motivation (an empty reply from the withdrawn model) does not exist on qwen3-next, whose conversational re-ask answered. | `tests/core/llm/test_jobs.py` (4 new) | `_re_ask` ignores the shape |
| 3 | `max_output_tokens` 6000 truncated 2 of 99 replies | 9000 (prompt v16, route and logic version bumped; scope: `reviewer` only, asserted). qwen3-next peaked at 2452 in iteration 1; this is headroom, not a measured need. | `test_packet_lines.py` | budget back to 6000 |
| 4 | Quotes the model retypes are paraphrased or filed under the wrong section | The packet numbers the candidate (`0042\| text`); the call schema has `lines` and **no `quote`**; `reply.resolve_cited_lines` derives the exact quote and (for kinds about the quoted text) the section from the raw candidate, and refuses impossible citations (out of range, blank, more than 12 lines, across sections). Idempotent, so a stored reply replays identically. A model-supplied quote still present is checked verbatim. | `test_cited_lines.py`, `test_packet_lines.py` (7) | quote or section no longer derived; packet unnumbered; call schema asks for a quote |
| 5 | qwen3-next rejected clean twins with `quality` findings (iteration 1: 2 of 3) | Read the findings (section 4): the diagram and other renderer-printed text, preference against the original, and false statements typed `quality`. Prompt v16 states what is never a finding and that a statement believed false is a `contradiction` or `unsupported_claim`, never `quality`. Contract: a `quality` finding whose cited lines lie in a renderer-owned section (every deterministic section and At a Glance) invalidates the reply. This blocks (re-ask, then `ReviewUnavailable`); it demotes nothing. | `test_cited_lines.py` | `RENDERER_OWNED` check disabled |
| 6 | No-re-roll invariant (`project/state.yaml`) | `llm_review.RerollRefused`: a request that got a blocking verdict and whose stored reply is gone is refused, never re-asked; replay is allowed; the record lives beside the call store and is keyed by reviewer logic version. Structural tests: no bypass parameter on `review_with_model`; only `cascade.py` and the calibration adapter call it; the only fresh-store-per-review code is the calibration adapter (it measures stability on corpus cases, not production candidates). | `tests/readme/review/test_no_reroll.py` (11) | guard not called; blocks not recorded |
| 7 | Harness skipped java/go/cpp/rust/typescript bases | Confirmed it was only the harness: `build_source` never called `plugin_for(entry.ecosystem)` as every cascade stage does. Fixed (`calibration/sources.py`). A base whose own twin the deterministic stage already blocks is now an `unscored_twin` and its baseline rules are not counted as a catch of its mutants (`Case.baseline_rules`). | `test_calibration_sources.py`, `test_calibration_corpus.py` | spec not registered; baseline rules counted |
| 8 | Owner decision: one model | `independent_review` routes to `qwen3-next` (v16); the rationale says plainly it is NOT model independence. The model id is removed from every manifest, source file, script and test; `tests/test_withdrawn_model.py` scans for it. The five authoring manifests only had it in prose in `route_rationale`; rewording it changes their file hash, so their `prompts.<job>` dependency changes (authoring scope) for any sealed bundle. | `tests/test_withdrawn_model.py` | model id put back in a route |

## 2. Blast radius of the re-ask shape (item 2), measured before the change

* The call store is keyed by the hash of the FIRST request (`run_job`: `request_sha256` is computed
  from the initial payload and `store.put` uses it). The re-ask payload is never a key; only a ledger
  row's informational `request_sha256` for attempts after the first is the hash of the re-ask payload.
* Stored and sealed artifacts in the repository: 4 call stores under `scripts/_lane_r_output/*/llm_cache/calls`
  (28 stored outputs, 10 `*.rejected-*` files); 5 ledgers (`candidates/.../ledger.jsonl` and the 4
  `llm_cache/ledger.jsonl`: 206 rows, 15 with `derived_via_reask`, 10 of them provider calls). Every stored
  output is keyed by a first-request hash, so none depends on the re-ask shape; replay is unchanged.
* The shape is behaviour, not a key: changing it globally would change what the five qwen3-next
  authoring jobs receive on a re-ask, unmeasured. Hence a per-manifest option, default unchanged.
  Counts: 0 stored outputs invalidated, 0 manifest hashes changed by the option (only a manifest that sets it).

## 3. Budget and corpus

Calls (all through `run_job`, ledger-counted, cap enforced by `Ledger.reserve_provider_call`): authorised
150 (hard cap 200); **121 made**, none to the withdrawn model (0 of 121). Breakdown: smoke 5; main pass 65
(7 before an interrupted process, whose stored replies were then replayed, and 58); second draw of the 10 reviews
that were unavailable 17; stability 34. 29 of the 150 were left unspent.

Corpus: 88 cases built, 51 asked. Bases: hosted runs 5 and 7 (.NET), 9 (Python), and Lane R outputs re-rendered
offline for Cells .NET, Cells Python, PSD .NET, Cells Java, Cells TypeScript and 3D TypeScript, plus the two recorded
defects (4 ecosystems with a base: net, python, java, typescript; iteration 1 had net and python). Go, Cpp and Rust
bases exist only with S9 failures that cannot be repaired in text or lack artifacts (`scripts/_lane_r_output`
has `content_units.coherent.json` for only some; PDF-Go fails BC-05/06/08, Email-Cpp fails four checks).
**Still only 3 clean twins** (runs 5, 7, 9; run 9 is a known-flawed baseline): every Lane R base has a
deterministic rule firing on its own twin (`live_readme_loss`, `disposition_coverage`; their dispositions
predate the accounting step), so the pipeline would never send it to the model. Those 7 twins are kept as
`unscored_twin` and asked as indicative precision evidence. More clean twins need fresh hosted cascade runs.

## 4. Why qwen3-next rejected clean twins in iteration 1 (the findings read, not summarised)

From the 11 stored qwen3-next replies with findings on run 7, run 9 and run 5 candidates:

* **The At a Glance diagram** in 8 of 8 candidates (and the installation, dependency and API tables): the
  diagram does redeclare nodes (`Product[...]` repeated), a renderer matter, which the v15 prompt already
  declared out of scope. A rule the model ignores is not a rule: it is now a contract check.
* **Preference against the original** ("places the install after the example", "omits the original's details
  block", "adds a redundant version mention").
* **False statements typed `quality`** ("incorrectly states COLLADA export is supported", "misattributes
  triangulation"), which no clearance can ever disprove and which are not presentation findings.
* One real flaw: run 9's "337 types" against "305 public types".

## 5. Results (qwen3-next, prompt v16, route qwen3-next)

Reviewer alone, a catch counted only when a blocking finding names the defect (`on target`); "any" is the
plan's literal any-rejection. Iteration 1 is qwen3-next from the earlier record. Pass 1 is the primary
measurement, one draw per case; the second draw of the unavailable cases is reported separately.

| Measure | Iteration 1 | Iteration 2 (pass 1) | Gate |
|---|---|---|---|
| recall, contradiction (reviewer alone) | 3/10 on target, 4/10 any | **4/11 = 0.36** on target, 5/11 any | >= 0.90 FAIL |
| recall, content loss | 0/3, 0/3 | **0/6 = 0.00** on target, 2/6 any | >= 0.90 FAIL |
| recall, unsupported claim | 0/5, 1/5 | **2/8 = 0.25**, 2/8 any | >= 0.90 FAIL |
| recall, broken install | 1/3, 2/3 | **3/6 = 0.50**, 3/6 any | >= 0.90 FAIL |
| pipeline recall (deterministic + reviewer): content loss / broken install | 3/3, 3/3 | 6/6, 6/6 (the deterministic stage alone) | - |
| pipeline recall: contradiction / unsupported | 6/10, 0/5 | 4/11, 2/8 | >= 0.90 FAIL |
| false-reject, scored clean twins | 2/3 = 0.67 | **1/3 = 0.33** (run 9, the known-flawed baseline; 0/2 on the vetted twins) | <= 0.10 FAIL |
| JSON-valid first reply | 33/33 = 1.00 | **44/44 = 1.00** | >= 0.90 PASS |
| contract-valid first reply | 12/33 = 0.36 | **30/44 = 0.68** (stability run: 26/30 = 0.87) | not gated |
| reviews that ended unavailable | 16/35 = 0.46 | **10/51 = 0.20** (4 of the 10 returned a verdict on the second draw) | - |
| stability, identical verdict over 3 fresh reviews | not run | **9/10 = 0.90** (10 cases, 30 fresh reviews) | >= 0.90 PASS |
| approved yield / content-loss rate (pipeline) | 0/3 / 0.00 | 2/3 / 0.00 | - |
| physical calls per case | 1.63 | 1.14 (58 calls / 51 cases) | - |

Not gated: duplicate paragraph 0/4, invented API 0/3 (the deterministic stage catches all 3), promotional
filler 1/3. Unscored twins (7, indicative): accept 3 (Cells .NET, Cells Python, Font), reject 2 on the second
draw (PSD .NET: a `contradiction` on the install line `version 1.0.0`; 3D TypeScript: 16 copies of one finding on the
renderer's "verified public surface has 81 types"), unavailable twice 2 (Cells Java, Cells TypeScript).

The 0.90 stability is real but proves little: 6 of the 10 cases are ACCEPTed in all 3 fresh reviews, 4 of them defective.
The model is consistent about missing the defect.

## 6. Why the gate still fails (evidence)

1. **qwen3-next ACCEPTs most defective candidates.** 26 of 51 reviews were ACCEPT. Of the 41 defect cases
   (mutants and real defects), the reviewer rejected 14 and 10 of those rejections were on target. Examples
   read in the stored replies: a wrong version number accepted on run 5, run 7 and Cells Python; the real
   "rendering is exposed" contradiction accepted in all 4 reviews (1 in pass 1, 3 fresh); every injected or real
   unsupported claim on runs 5 and 7 accepted. This is the failure that matters and nothing in the
   contract can repair it: a model that returns no finding gives the contract nothing to judge.
2. **Removing the fact requirement made unsupported_claim the dominant finding** (159 of 183 findings, 87%),
   and most are false: 37 are against renderer-owned sections (install, dependencies, badges), 93 against mixed
   sections, many against text the renderer printed from facts ("The verified public surface has N types",
   the PyPI-ownership receipt, install lines). 29 findings repeat an earlier finding of the same reply, 4 of 19
   replies hit the 16-finding cap, and the audit shows what a human needs: for example `81` occurs in no fact
   value because it is a renderer-computed count. This is why run 9's twin and the 3D TypeScript
   twin reject. It is a precision problem of the new contract: iteration 1's rule kept the model from filing
   these at all, because it could not cite a fact.
3. **The 12-line cap is the main source of unavailable reviews:** 8 of the 13 rejected first replies kept in
   the pass-1 store cited more than 12 lines (usually a whole section for an omission or a quality complaint);
   the rest were 3 contradictions and 1 omission without a product fact, 2 scope errors (quality against
   renderer text), 1 nonexistent line and 1 blank span (some replies had more than one error).
   Citation accuracy is otherwise acceptable: only 9 of 127 findings with a backticked term name text that is
   not in their own cited lines.
4. The deterministic stage does the work for content loss, broken install and invented API (6/6, 6/6, 3/3).
   The reviewer is the only line against unsupported claims, and it is at 0.25.

## 7. Recommendation

**Route:** qwen3-next, as decided by the owner; it is not model-independent, so independence rests on the
structural separation and the deterministic holdouts, and this measurement says the LLM reviewer cannot be
the holdout for contradictions. **Do not enable the reviewer gate for the cohort or PR path.** `present.py`
already fails closed (an unreviewed or unavailable review never seals), so nothing unsafe ships; nothing useful
ships either until the next items pass the same corpus. Each needs its failing test first and none loosens a rule:

1. Contradiction recall (0.36) is not a prompt problem. Add deterministic claim checks for the classes that
   are decidable from facts (a version, package name, format or install command in the candidate that no
   SUPPORTED fact states) as rules in `independent_reviewer`, the way `claim_contradiction` already catches
   some; leave the LLM the claims no code can check.
2. Make unsupported-claim findings checkable the way the v15 typed claims are: a finding must name the
   distinctive term(s) it says no fact supports (as `unsupported_names` does for identifiers) so the audit
   becomes a verifiable field, and extend the renderer-owned scope check to `unsupported_claim` for the
   deterministic sections and for renderer-computed lines of mixed sections (needs the units list in the packet).
3. Contract hygiene measured above: allow an omission, absence or quality finding to cite a whole section (the
   12-line cap caused 8 of 15 invalid first replies); treat two findings that cite identical lines and kind as one.
4. Smaller packets: review section by section (a 70,000-token whole-document read is the likely cause of the
   misses; not demonstrated).
5. A fourth to tenth clean twin needs fresh hosted cascade runs per ecosystem; the Lane R outputs cannot supply them.

## 8. Limitations

3 scored clean twins (1 flawed); n = 6 to 11 per gated class; one gateway, one day, temperature 0 and seed 1
(the gateway is not deterministic); 4 ecosystems; on-target is a keyword test over the finding's cited text and
message; the 17 second-draw calls are reported separately and not mixed into the primary table; `unscored`
twins are indicative only. The re-ask option (`reask_shape`) was not exercised live.

## 9. Reproduce

```
export MSYS2_ARG_CONV_EXCL="*"   # Git Bash on Windows
PYTHONPATH=src python scripts/run_reviewer_calibration.py live \
  --work run5=<run5>/.present-work --work run7=<run7>/.present-work --work run9=<run9>/.present-work \
  --recorded-clones <dir> --lane-r NAME=scripts/_lane_r_output/<repo>,<clone>[,BC-07,...] ... \
  --out <dir> --cap 200 --tag pass1 --only "<ids from selected-cases.txt>"
# stability: --fresh --repeats 3 --only <10 ids>;  a replay with evidence: --results-name results-<tag>-evidence.jsonl
```
