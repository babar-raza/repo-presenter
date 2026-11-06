# Reviewer calibration iteration 4: root cause from the recorded data

Date: 2026-11-06. Follows `2026-11-05-reviewer-calibration-iteration-4.md` (prompt v17, logic 6, `qwen3-next`,
`NOT_PASSED`). **No provider call was made.** Every verdict below was rebuilt from iteration 4's call store with the
iteration-4 code (`eb74bd0`) and a ledger whose call budget was 0, so a request missing from the store raised
instead of being sent. The replay reproduced the recorded first-pass verdicts of 366 of 375 cases; the other 9 have no stored reply for one
unit (8 recorded `unavailable`, 1 a REJECT with an unavailable unit). Stability repeats were replayed from their own
fresh stores. Iteration 4 is **not
re-scored** (directive R5); the effect of the fixes on its data is reported, never recorded as a status.
Reference-base text stays local (iteration 4, section 1.2): reference cases are named by id only.

## 1. The 81 real-defect cases (74 unsupported_claim, 7 contradiction): 0 detected

| Class | n | own / ref | What happened |
|---|---|---|---|
| (a) defect on a line no unit showed | **19** | 3 / 16 | 15 in a **table body cell**, 4 in a **fenced code block**. `scope.line_sections` withholds every `|` row and every fence, for Lane L (`rendered=False`) too, and for the authored cells of Lane R's API table. |
| (b) shown, reported, scored off target | **1** | 0 / 1 | Right kind (`unsupported_claim`), but the finding cites 2 of the defect's 4 lines; `on_target` needs the whole defect text in the quote. |
| (b') reported under another category | 0 | | No finding on a defect line had another kind. |
| (c) cleared by `clearances.py` | **0** | | No finding touching a defect was CLEARED (the four clearances cover absence/name_denial/omission only). |
| (d) folded by `verdict.py` | **0** | | 60 of the 62 shown-defect units returned the model's own `ACCEPT` with **zero findings**: nothing reached the fold. |
| (e) shown, not noticed | **61** | 10 / 51 | **42** repeat the original README verbatim (also an `inherited_unit` fact); **19** do not. 9 of the 61 cases were REJECTed for other lines. |

Examples (own-base text is already committed in `-data/own-repairs.json`):

* (a) table cell: `own:html-python/real:unsupported_claim:2` (`| SubtleCrypto | SubtleCrypto provides cryptographic
  operations such as encryption, decryption, signing, and verification. |`: no docstring, so the renderer printed the
  sentence authored for the type, and scope treated it as renderer-printed); `own:cells-cpp/real:unsupported_claim:2`
  (same mechanism); `ref:cells-typescript/real:unsupported_claim:54` (an "Interface with N properties" count no fact
  supports). (a) code: `ref:cells-cpp/real:contradiction:6`, `ref:cells-go/real:contradiction:6`,
  `ref:slides-cpp/real:contradiction:4` (a CONTRADICTED example; 4 of the 7 real contradictions are code).
* (b) `ref:page-python/real:unsupported_claim:19` (a 4-line limitation bullet; the finding cites lines 522-523).
* (e) in original: `own:cells-rust/real:unsupported_claim:0` ("starts with one sheet, `"Sheet1"`"),
  `own:cells-go/real:unsupported_claim:3` ("all 14 public types"), `own:imaging-net/real:unsupported_claim:17`.
  Prompt v17 says: "A sentence that repeats the original's own claim, restates a fact ... is not a finding". The model
  followed its prompt; the labels followed the curation brief. Prompt v18/v19 (logic 7/8) moved further the same way
  (attributed maintainer text is not an unsupported claim).
* (e) not in original (true misses): `own:cells-go/real:unsupported_claim:2` ("ECMA-376 Agile Encryption (SHA-512 key
  derivation, AES-256-CBC)"), `own:cells-java/real:unsupported_claim:1` ("18 of the 25 `ChartType` values"),
  `own:html-python/real:unsupported_claim:5` ("all 243 public types"). Units are dense (median 22 shown lines and ~98
  facts per own unit, 53 lines and ~93 facts per Lane L unit); for each of these the model returned ACCEPT with no
  finding.

The 13 recorded REJECTs of real cases: 1 is (b), 3 are (a) cases rejected for other lines, 9 are (e) rejected for
other lines. None cites the defect, as iteration 4 section 2.2 said.

## 2. Section deletion (pipeline 7/41 = 0.17; reviewer alone 0/41)

* **Not visible to the reviewer at all.** A unit's packet holds its own lines, the facts and `original_excerpt` (the
  part of the original README that shares words with the unit's text, `evidence.original_excerpt`). The dropped
  section's text shares nothing with the remaining units, so it is in no excerpt; there is no diff and no list of
  original headings; and the prompt says a drop compared with the original is never a finding. 0/41 is by
  construction.
* **Pipeline 0/34 on reference bases was a harness defect.** `corpus.deterministic_rules` ran only
  `claim_contradiction` and `duplicate_paragraph` for `rendered=False`, while Lane L's production holdouts
  (`lane_l_review.holdout_findings`) also run `live_readme_loss` against the live README. And `pre_llm` subtracted the
  twin's baseline by **rule name**, so a new `live_readme_loss` finding on a twin that already lost a link was
  invisible. Own bases: 7/7 (disposition rules).

## 3. False rejects of clean twins (6/37, all reference twins; own 0/4)

| Twin | Blocking findings | Rule / cause |
|---|---|---|
| `ref:font-python` | 1 contradiction + 6 unsupported (dependencies, limitations) | the "unscoped absolute dependency claim" portfolio rule fired although dependency facts prove "no required dependencies"; dev-tool lines backed by dependency facts filed as unsupported. Reviewer error, all 4 draws. |
| `ref:note-python` | 1 contradiction + 6 unsupported (api_reference) | bare type names (`Document`, `Image`) filed as `unsupported_claim`; fact values are dotted. Not a `name_denial`, so `names_supported` could not check it. |
| `ref:pdf-go` | 5 unsupported (api_reference) | texts say "the facts show ..." / "omits the limitation ...": contradictions/omissions filed as unsupported, without a fact. |
| `ref:slides-java` | 4 unsupported (installation, dependencies) | registry-version and "no runtime dependencies" lines. |
| `ref:pdf-net` | 1 contradiction (limitations) | undecided. |
| `ref:words-python` | 2 unsupported ("126 public types") | a real defect the curator missed. |

Top causes: `unsupported_claim` filed against identifier/dependency text a fact does support (3 twins), and kind
mislabelling that bypasses the typed clearances (2 twins).

**Stability (7/10).** All 3 unstable cases (`ref:pdf-go/clean`, `own:html-python/clean`,
`ref:pdf-go/real:unsupported_claim:63`) owe 6 of their 9 divergent draws to `UNAVAILABLE` (reply broke the contract
twice), not to opposite verdicts: an `omission` citing only `inherited_unit` facts (pdf-go u5, 4 draws), and
citations of a blank or hidden line (html-python u3). Run-wide, 8 of the 14 unavailable reviews cite a blank line, 7 of
them in the gap right after a line an injection mutant lengthened (1 more was an HTTP 502).

## 4. Code fixes (branch `w/reviewer-rootcause`)

| Defect | Fix | Test |
|---|---|---|
| Lane L table body rows never shown (11 ref real defects) | `scope.line_sections`: with `rendered=False` a table body row is reviewable; header and delimiter rows are not | `test_scope.py::test_a_live_readme_table_body_row_is_reviewable_but_its_header_and_rule_are_not` |
| Lane R API-table description an author wrote (no docstring/signature) treated as renderer text (3 own real defects) | `scope.authored_table_lines` + `plan_units(authored=...)`, used by `llm_review` | `test_scope.py::test_an_api_table_row_whose_description_an_author_wrote_is_reviewable` (own:html-python shape) |
| Reference bases lack Lane L's `live_readme_loss` | `corpus.deterministic_findings` runs it for `rendered=False` (no dispositions) | `test_calibration_reference.py::test_a_reference_drop_section_mutant_is_blocked_as_lane_l_blocks_it` |
| Rule-name baseline hides new findings | `Case.baseline_findings`, `finding_key` (rule, evidence, quote); `pre_llm` subtracts findings | `test_calibration_reference.py::test_a_new_finding_of_a_rule_the_twin_already_trips_is_still_a_catch`, updated `test_calibration_corpus.py::test_the_baseline_rule_is_not_a_catch_of_a_mutant` |

`REVIEWER_LOGIC_VERSION` 8 -> 9 (scope changed). Effect on iteration 4's recorded verdicts (reported, not gated):
15 of the 19 hidden real defects become visible (the 4 code blocks stay hidden by design); pipeline `drop_section`
0.17 -> **0.90**, `break_install_command` 0.80 -> **1.00**, others unchanged. **Decision point:** the Lane L stage
blocks 23 of the 33 scored reference twins (they lose live headings/links/commands), so by the existing policy they
become unscored twins, including 5 of the 6 false rejects. That is what production would do, but it leaves 14 scored
clean twins, too few for the 0.10 gate: iteration 5 needs more clean twins (own bundles, Lane L candidates).
Cost: Lane L units per twin set 115 -> 248 (tables), own 20 -> 34.

Not changed: `on_target` (class (b) is 1 case; no mutant had only a partial-span hit), clearances, fold, tiers.

## 5. Recommended prompt changes (not made)

1. **Original-README rule vs labels (42/81).** Decide one rule before iteration 5. If the labels stand, replace "A
   sentence that repeats the original's own claim ... is not a finding" with: "Repeating the original README never
   makes a claim supported: the original and `inherited_unit` facts are unverified maintainer text. A specific
   checkable claim (number, count, version, standard, algorithm, list of supported items, behaviour) that no product
   fact states is an `unsupported_claim` even when the original says it; a difference from the original is still not
   a finding." This conflicts with v18/v19's attributed-maintainer exemption (owner policy,
   `docs/MAINTAINER_CONTENT_PRESERVATION.md`); iteration 5's label policy must match whichever rule is chosen.
2. **Claim ledger (19 true misses).** Require, before the verdict, one entry per shown sentence holding a number,
   identifier, standard or capability: the fact id that states it, or a finding. ACCEPT is valid only when every
   entry has a fact id.
3. **Tables (logic 9).** Replace "API reference tables and member lists ... are NOT shown" with "a table row shown to
   you is author text: judge and cite it like any other line".
4. **False rejects.** "A dependency line that equals a dependency fact is supported, `none required` included"; "a
   claim that an identifier does not exist is a `name_denial`, never an `unsupported_claim`"; "an `unsupported_claim`
   cites no fact: if your text says what a fact shows, it is a `contradiction` or an `omission`".
5. **Stability.** "Cite only a numbered, non-blank line; a long line keeps one number however it wraps"; "an omission
   cites a product fact, never only an `inherited_unit`".

## 6. Iteration 5 cost estimate

Iteration 4: 845 physical calls for 375 cases at ~3.3 units/twin. At logic 9 a same-shape held-out corpus (41 bases,
~375 cases, stability 10x3) needs about 280 twin units + ~350 mutant and ~90 real-defect changed units + ~210
stability units (fresh, all units) + ~10% re-asks: **~1,000-1,100 calls**, plus ~150 for 20 extra clean twins. Set
the cap at **1,300** so the run cannot stop early (iteration 4's cap was hit).
