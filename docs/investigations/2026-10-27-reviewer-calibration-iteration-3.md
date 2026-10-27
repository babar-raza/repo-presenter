> NOTE (2026-10-27): measured on qwen3-next only (the owner's binding decision); every call in this iteration went to it (229 of 229).

# Independent LLM reviewer, iteration 3: deterministic claim checks, sectionwise review, calibration status

Date: 2026-10-27. Follows `2026-10-27-reviewer-calibration-iteration-2.md` (whole-document packets; gate failed).
Plan amendments: `plans/PLAN_independent_llm_reviewer.md` section 8. Raw data: `2026-10-27-reviewer-calibration-iteration-3-data/`
(every result line, every stored or rejected reply, the ledger, the corpus listing; the gateway key and endpoint appear nowhere, checked).

**Status: the gate still FAILS, but the failure moved.** Tier 1 (what code decides) passes in full at pipeline level. Tier 2: the
reviewer alone now catches 11/11 injected unsupported claims and 11/11 promotional filler (iteration 2: 2/8 and 1/3), and misses the two subtle
real defects it was measured on. Four gates fail: false-reject on clean twins, stability, and the two real-defect tier-2 classes
(n = 2 each). No threshold, rule or clearance was loosened or added. Nothing here is owner-reviewed.

## 1. What was changed (each failing-test-first; falsifiers noted)

| # | Change | Tests |
|---|---|---|
| 1 | **Why the pipeline missed `contradict_version` / `contradict_package_name`**: (a) the version rule did not read the sentence the renderer itself prints, `(`Pkg`, version 27.1.0)` (a comma between the name and "version"; also `Pkg package (version V)`); (b) the identity rule read install commands inside fences only, so a package name in prose was never judged; (c) nothing read a format list (BC-04 owns single identifiers). Fixed in `validation/claims.py` (BC-14 and `claim_contradiction`): the version tail accepts punctuation; rule (f) flags a code span in prose that is the identity spelled exactly plus a suffix (`Aspose.3D.FOSS.Core`), unless a SUPPORTED fact value, namespace, dependency, registry-confirmed distribution or file name; rule (g) flags an extension in a sentence that lists two or more extensions when one is a SUPPORTED format and it is not. Two false positives found while writing it (a sibling product `Aspose.3D.Converter`, a module path `Aspose.Cells_FOSS.Formats`) became negative controls. **Blast radius, measured before commit: `claim_findings` over 41 READMEs on disk (9 hosted/Lane R candidates re-derived, run2, run3, 30 Lane R outputs with facts): 0 findings added, 0 removed.** | `test_claims_surface.py`; falsifier: revert the tail change / the two rules |
| 2 | **Sectionwise review** (`review/sectionwise.py`, `scope.py`, `evidence.py`): the candidate is split into units of 4,500 characters of author-written text or less (one section or a few adjacent ones; a longer section splits between lines). A unit shows only the lines an author wrote: no heading, table, fence, `<details>`, badge, "Not verified" note, diagram, deterministic section, API member bullet, nor a sentence the renderer appended to an authored line (`"It covers all N verified public types..."`, the Enterprise lead, the issues bullet, the CI and suite sentences; a sync test renders the fixture's `renderer_sentences` and asserts every one is stripped). A line a unit did not show cannot be cited by any claim kind (contract error), so renderer-owned text is excluded from `unsupported_claim` by construction, not by instruction. The packet: the unit's numbered text (real candidate line numbers, gaps marked), the facts it may cite (identity, formats, dependencies, licence always; the public symbols its text names, with the docstring, kind and signature the extractor read; inherited units and other facts ranked by shared words; examples and links only for units that hold them), the part of the original that shares its words, per-line support hints (ids of facts whose values occur in the line; a search aid that decides nothing, never an inherited unit), the unit's plan entries without the author's reason. Dispositions and validation are no longer sent. | `test_scope.py`, `test_sectionwise_packet.py` |
| 3 | **Contract**: an omission, absence or quality finding may cite a whole section (first and last shown line); a contradiction or unsupported claim keeps the 12-line cap. A whole-section citation of an omission or absence is a locator, not a quote (`quote` stays empty), so `absence_present` still clears a false "missing" claim (tested). A finding names a section of its own unit (call-schema enum and contract). Findings of one kind on the same lines merge into the first, which stays BLOCKING and records the count. Unit replies merge into one reply (ids renumbered before any clearance, since a clearance binds the id), folded once; an insufficient unit blocks the whole review retryably; an unavailable unit makes the review unavailable unless another unit's blocking finding already rejects it. Replay is zero calls and byte-identical; the no-re-roll record is per unit request. **The Phase 1 clearance catalogue is unchanged** (four functions; the structural test that no clearance reads a quote against a fact value passes). | `test_scoped_contract.py`, `test_sectionwise_review.py` |
| 4 | **Calibration status**: `data/reviewer_calibration.json` (`NOT_PASSED`, with these numbers), read by `review/calibration_status.py`, which fails closed (missing or malformed file, unknown status, `PASSED` beside failed gates, another reviewer version, `PASSED_WITH_DECLARED_LIMITS` with an empty `owner_acceptance` all read as `NOT_PASSED`) and has no writer (tested). A verdict records the status it was made under and an `acceptance_label` (`uncalibrated` unless the status permits; recomputed on read, never trusted from the file). `propose_candidate` refuses with `REVIEW_UNCALIBRATED` unless the verdict's recorded status and the committed file both permit. | `test_calibration_status.py`, `tests/propose/test_effect.py` (new gate tests); two falsifiers (gate disabled; empty acceptance honoured) verified to fail |
| 5 | **New deterministic holdout**: the same prose paragraph (120 characters or more) printed twice (`independent_reviewer.duplicate_paragraph_rule`). Over the 41 READMEs it fires on 2 older Lane R outputs that really repeat a paragraph, 0 on any current-generation candidate. | `test_duplicate_paragraph_rule.py` |
| 6 | **Measurement**: `harness.evaluate_tiers` (two-tier report, per defect label, reviewer-alone beside pipeline for tier 1); a catch is **on target** only when a blocking finding cites lines that hold the defect's own text (`Case.defect_text`: the injected span, or the span a repair removes); keywords remain only for absences. The smoke run showed why: a finding about another sentence on the same topic had been counted as catching a real contradiction. Per-unit first-reply validity, tokens and units are recorded. | `test_calibration_tiers.py`, `test_calibration_harness.py`, `test_calibration_live.py` |
| 7 | `rendered=False` on `review_with_model`, `plan_units` and the scope functions for a maintainers' README (Lane L): nothing is withheld as renderer-owned there, only Markdown that is never prose. Default unchanged. | `test_scope.py`, `test_sectionwise_review.py` |

Prompt v17, `REVIEWER_LOGIC_VERSION` 6 (reviewer scope only: asserted). The 33 `review_verdict.json` files in the repository still load.

## 2. Corpus, bases and budget

109 cases (iteration 2: 88): bases run5, run7 (.NET), run9 (Python), run2, run3 (earlier hosted .NET candidates, added), the six Lane R bases, two recorded defects.
**Clean twins: still 3 scored (run5, run7, run9, a known-flawed baseline) and 9 unscored (indicative).** More are not achievable offline:
the hosted sealed bundles of runs 1, 5, 6 and 7 are one and the same older candidate (BC-07 and `live_readme_loss`), run2 and run3 fail the same
rules, and every Lane R output's dispositions predate the accounting step so its own twin trips `live_readme_loss`. A sixth clean twin needs
a fresh hosted cascade run per ecosystem. run7's twin gained a third repair, found by this iteration's smoke run and confirmed by reading
inherited unit 061: the API hub sentence "The Render module provides ... rendering" contradicted "Rendering is not implemented in this FOSS build".

Calls (all through `run_job`, ledger-counted, hard cap 350, authorised 300): **229 made**, all to qwen3-next: prompt development on 4 smoke runs 34;
the main pass 127 (109 cases, 249 units, 125 distinct requests; a mutant replays every unit it leaves untouched, so it costs one call);
stability 68 (8 cases x 3 fresh reviews, no cache). 71 of the 300 unspent. Honest note on development: the prompt and the evidence were adjusted on
those 34 calls over run5, run7 and run9 (docstrings added to symbol facts, support hints, an inherited unit is not support, criterion guidance), which are also the scored clean twins.

## 3. Results (qwen3-next, prompt v17, route qwen3-next)

### Tier 1: what code decides (gate: pipeline on-target recall >= 0.90 per class; reviewer alone reported, not gated)

| Defect | n | pipeline (deterministic stage + reviewer) | reviewer alone |
|---|---|---|---|
| wrong version | 10 | **10/10** | 2/10 |
| wrong package name | 11 | **11/11** | 0/11 |
| unsupported format in a list | 7 | **7/7** | 5/7 |
| broken install command | 8 (+1 recorded) | **8/8** (1/1) | 0/8 (0/1) |
| dropped section (content loss) | 11 | **11/11** | 0/11 |
| invented API name | 11 | **11/11** | 10/11 |
| repeated paragraph | 11 (+1 recorded) | **11/11** (1/1) | 4/11 (0/1) |

The reviewer alone cannot see a version, package name or install line that the renderer printed (it is not shown), which is the point:
code carries them. (Iteration 2's deterministic stage caught none of the version and package-name mutants on its corpus.)
In the high-severity classes: broken install 9/9, content loss 11/11, contradiction 29/30 (the miss is tier 2).

### Tier 2: only a model can judge (target: reviewer-alone on-target recall >= 0.90)

| Defect | n | reviewer alone | iteration 2 |
|---|---|---|---|
| injected unsupported claim | 11 | **11/11** | 2/8 |
| promotional filler | 11 | **11/11** | 1/3 |
| real unsupported claim ("full round-trip fidelity", run5 and run7) | 2 | **0/2** (run5 rejected the candidate, but for a different sentence) | 0/2 |
| real contradiction with an inherited limitation (run7: "exposes Render", "Render module provides ...") | 2 | **1/2** | 1/1 |

The injected claims are blatant by construction ("ten times faster than the leading commercial libraries"); the two real ones are the maintainers'
own phrase, which an inherited README unit also states. The prompt says such a claim is still unsupported; the model did not apply it.

### Shared gates

| Measure | Result | Gate |
|---|---|---|
| false-reject on scored clean twins, first pass | 1/3 = 0.33 (run9, the flawed baseline; 0/2 on run5 and run7) | <= 0.10 **FAIL** |
| the same twins over all 12 reviews (first pass + 9 fresh) | 7/12 = 0.58 (run5 3 of 4 draws, run7 1 of 4, run9 3 of 4) | FAIL |
| JSON/schema-valid first reply (per unit) | 125/125 = 1.00 (stability run 66/66) | >= 0.90 PASS |
| contract-valid first reply (per unit) | 123/125 = 0.98 (stability run 64/66) | not gated (iteration 2: 0.68) |
| reviews that ended unavailable | 0/109 (0/24 fresh) | iteration 2: 10/51 |
| stability, identical verdict over 3 fresh reviews | **6/8 = 0.75** (run7/clean and run9/clean each split 2-1) | >= 0.90 **FAIL** |
| approved yield / content-loss approved | 2/3 first pass; 0/11 | - |
| cost | 1.17 calls per case in a pass that shares units; 2.83 calls per fresh review; mean prompt 17,025 tokens per call (target 15,000: missed by 13%), mean completion 373; median latency 6.3 s | - |

Adjudication of the false rejects (findings read, not summarised). run5's twin: three fresh reviews of four rejected it with the same findings. One is
probably real: line 55 names Universal 3D, AMF, PDMS RVM and an HTML5 web-viewer export that no SUPPORTED format fact states (they appear only in
docstrings and inherited text), so the twin is not clean; two are wrong (`.3ds` "has no fact" although `format:input.3ds` exists; the Formats
namespace sentence). run9's twin is the flawed baseline. run7's twin was accepted three times in four. So the 0.58 mixes true positives
against a twin I called clean, and false ones; I did not repair run5 further because that would be tuning the corpus to the reviewer.
The four rejected unscored twins (Cells Java, Cells TypeScript, Font, the duplicate-opening twin) cite unsupported claims on inherited limitation text.

## 4. Why the gate still fails

1. **Stability 0.75 and false-reject 0.58 are the same problem**: for a candidate whose text is borderline the model's verdict flips between draws
   (run5 was ACCEPTed once in the main pass and rejected three times fresh). A single draw is therefore not a measurement of a candidate.
   The no-re-roll invariant means a blocking draw is final, so the cost of this instability falls on approved yield, not on safety.
2. **The two subtle real defects are missed** (n = 2 each; no claim is made beyond that): a claim that only the maintainers' README states, and an
   "exposes X" sentence beside a limitation that says X is not implemented, when the limitation is two lines away in the same unit.
3. **Tier 1 is carried by code, and that is now measured**: every class code decides is at 1.00 pipeline recall.
4. Per-call packets were 17,000 tokens on average (the target was 15,000), about a quarter of the whole-document packet.

## 5. Decision for the supervisor (not taken here)

The gate semantics decision allows `PASSED_WITH_DECLARED_LIMITS` only if every tier-1 and shared gate passes and tier 2 falls short. Here two
shared gates fail, so neither `PASSED` nor `PASSED_WITH_DECLARED_LIMITS` is available, whatever the owner would accept. `data/reviewer_calibration.json`
stays `NOT_PASSED`; no candidate is PR-eligible and a sealed ACCEPT is labelled `uncalibrated`. Next items, each needing its failing test first and none loosening a rule:
(a) a fresh hosted cascade run per ecosystem for 3 or more further clean twins (the gate cannot be read at n = 3, one flawed); (b) measure
stability with the decision rule fixed in advance (this iteration measured one draw per case for recall and three for stability); (c) the two
real-defect classes need more real cases than two each; (d) trim the packet to the 15,000-token target (fewer ranked inherited units).

## 6. Limitations

3 scored clean twins (1 flawed, 1 adjudicated as carrying a probable real defect); n = 1 to 11 per label, 2 for each real-defect label; one gateway, one day,
temperature 0 and seed 1 (the gateway is not deterministic); prompt development on the scored twins (section 2); 4 ecosystems (net, python, java, typescript); on-target is a containment test of the defect's own text in the cited lines (stricter than iteration 2's keywords, so numbers are not comparable
with iteration 2's "on target"); the stability set is 8 cases, 3 of them clean twins.

## 7. Reproduce

```
export MSYS2_ARG_CONV_EXCL="*"   # Git Bash on Windows
PYTHONPATH=src python scripts/run_reviewer_calibration.py live \
  --work run5=<run5>/.present-work --work run7=<run7>/.present-work --work run9=<run9>/.present-work \
  --work run2=<run2>/.present-work --work run3=<run3>/.present-work --recorded-clones <dir> \
  --lane-r NAME=scripts/_lane_r_output/<repo>,<clone>[,BC-07,...] ... \
  --cache-corpus <corpus.pkl> --out <dir> --cap 350 --tag pass1 --all
# stability: --fresh --repeats 3 --tag stab --only <8 ids>
```
