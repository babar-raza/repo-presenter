# Independent LLM reviewer, iteration 4: a 41-base corpus against the aspose.org reference

Date: 2026-11-05. Card: `project/taskcards/TC-007.yaml`. Follows
`2026-10-27-reviewer-calibration-iteration-3.md` (gate failed: false-reject, stability, two real-defect
classes). Decision log 2026-10-31, decision 4: iteration 4 uses the aspose.org candidates as a
**local-only** reference corpus (far larger n than iteration 3's three clean twins).

**Section 1 was committed before any provider call of this iteration.** The git history of this file is
the proof that the corpus, the labels and the selection were fixed before the reviewer was asked.
Results are appended in section 2 by a later commit.

## 1. Pre-registration

### 1.1 What is measured

The reviewer **as it exists** is measured: prompt `independent_review` v17, `REVIEWER_LOGIC_VERSION` 6, model
route `qwen3-next`. Nothing about the reviewer (prompt, contract, clearances, thresholds) is changed in this
iteration. Thus the whole corpus is held out relative to the reviewer's development: v17 was developed on
iteration 3's run5/run7/run9, none of which is in this corpus. If the gate fails, a changed reviewer must be
measured on a new held-out set; it is never re-scored on this one (directive R5).

Gate thresholds are unchanged (`harness.py`): pipeline on-target recall ≥ 0.90 per tier-1 defect; reviewer-alone
on-target recall ≥ 0.90 per tier-2 defect, including every real-defect class the corpus holds; false-reject on
scored clean twins ≤ 0.10; first-reply JSON validity ≥ 0.90; stability ≥ 0.90.

### 1.2 Bases (41)

* **7 own bases**: the sealed Lane R bundles on origin (`refs/repository-presenter-state/bundles/*`) whose
  re-render is byte-identical and whose twin passes the deterministic stage today: Cells .NET, C++, Go, Java,
  Rust; HTML Python; Imaging .NET. Revisions in `-data/` (equal to the upstream HEAD of each clone). Five other
  sealed bundles (Cells Python and TypeScript, Email .NET, Note Python, PDF Java) are **excluded**: each fails
  BC-04 today, so the production pipeline blocks them before review and a verdict on them would measure the
  base, not the reviewer.
* **34 reference bases**: the aspose.org refresh candidates (`reports/repo-presenter-regen-full/<family>/<platform>/readme.md`
  of the sibling checkout at `32cb4ebd2c9e5e35dcdd7616e4d9091a7bed4fd4`), judged against **this project's facts**
  regenerated locally at each clone's revision with the production facts stage
  (`python -m repo_presenter.present --stage facts`; no .NET SDK in this container, so .NET examples are
  NOT_VERIFIED, never CONTRADICTED). Reviewed with `rendered=False` (every prose line shown); only the
  text-reading deterministic rules apply (`claim_contradiction`, `duplicate_paragraph`), since a README this
  renderer did not print has no disposition record. **Excluded**: PDF TypeScript (54 review units, cost) and
  GIS .NET (no aspose.org candidate). No aspose.org text is committed: only digests and counts.
* Iteration 3's bases (run5/run7/run9 hosted work directories) **cannot be rebuilt** in this environment: the
  artifact download host is denied by the session's network policy. Its two real-defect classes are measured
  again here on new, larger material (section 1.3).

### 1.3 Labels (fixed before any reviewer call)

Each base was read against its facts by a curator agent (8 agents, one brief,
`CURATION_BRIEF.md`; the brief quotes the reviewer's own standard of what is and is not a finding). A curator
records every sentence the standard says is a finding as a minimal `Repair` (`old` exact and unique, `klass`
`unsupported_claim` or `contradiction`, a reason naming the search or the contradicting fact). The repaired README
is the clean twin (expected ACCEPT); each repair undone alone is a real-defect case (expected REJECT). Every file
was checked mechanically (JSON, `old` occurs once, repairs apply in order, cited fact ids exist).

* 1,005 repairs: 936 `unsupported_claim`, 69 `contradiction` (own bases: 62, committed in
  `-data/own-repairs.json`; reference bases: 943, local only).
* 4 supervisor repairs on two reference bases (PDF .NET, PDF Java): an install line pinned to an older version,
  which the **deterministic** version rule flags; added before any reviewer call.
* Digests: `repairs.json` (merged, local) `f15ab12cf2f5f49f64b67f80d2c386d0365d9a7618cf6cc34c5a1922a2f0cd22`;
  `own-repairs.json` `b254db813e6877ea61a851ebcb29aa07f84ac23b82d038f9390704c7c7754c7c`; per-base README and facts
  digests in `-data/inputs-digests.txt`.
* `-data/tolerate.json`: four own twins fail S9 preservation checks after their repairs (Cells C++, Go, Rust;
  Imaging .NET), because a repair deletes an unsupported claim from text the renderer kept from the
  maintainers' README, and BC-04/05/07 require that text. Tolerated as the twin's baseline (iteration-3
  precedent), each with the stated reason.
* Known, stated label policies: maintainer-written limitation bullets were left alone unless they name an
  unsupported identifier or number or make a positive capability claim; an "Enterprise Edition adds ..." clause
  is unsupported (one curator of the 8 left it, on own bases only, where it is renderer-printed and never shown
  to the reviewer); code blocks were changed only where an example fact for exactly that code is CONTRADICTED.

**Label policy for scoring (fixed now):** a scored clean twin's rejection by the reviewer counts as a false reject,
with no post-hoc relabelling. Where a curator missed a real defect the reviewer finds, that makes the measurement
stricter, never easier. Rejections of clean twins are listed in section 2 with an adjudication that is reported,
never gated.

### 1.4 Corpus and selection

1,299 cases built offline (zero calls): 37 scored clean twins (python 13, net 9, java 5, cpp 4, go 2, rust 2,
typescript 2), 4 unscored twins (the deterministic stage still blocks them: own Cells C++, Cells Go, Imaging .NET
on preservation rules; reference Slides Python on the version rule), 253 mutants (every operator applicable to
each base), 1,005 real-defect cases.

Asked: every clean and unscored twin, every mutant, and at most **2 real-defect cases per base**, ranked by the
SHA-256 of the case id (`calibration/selection.py`): 375 cases, of which 81 real defects (74 unsupported_claim,
7 contradiction). Mutants by operator: add_promotional_filler 41, break_install_command 20, contradict_format 15,
contradict_package_name 21, contradict_version 6, drop_section 41, duplicate_paragraph 41,
inject_unsupported_claim 41, invent_api_name 27.

Stability: 10 cases (5 scored clean twins, 5 defect cases, hash-ranked) reviewed 3 more times with no cache;
a case is stable only when all 4 reviews return the same verdict.

Budget: hard cap **620** physical provider calls (estimated: 451 unit calls for the first pass, about 90 for
stability, the rest for contract re-asks). A budget stop makes the run incomplete, and an incomplete run is
never recorded as `PASSED`.

### 1.5 How the status is recorded

`data/reviewer_calibration.json` is written by `scripts/run_reviewer_calibration.py --write-status` from the
run's two-tier report (`calibration/record.status_document`): `PASSED` only when every gate passes **and** every
selected case was asked; `LIMITS_ONLY` and everything else are `NOT_PASSED`; `owner_acceptance` is never
written. No hand edit.

### 1.6 Reproduce

```
python scripts/run_reviewer_calibration.py live --all --real-per-base 2 --stability 10 \
  --cap 620 --tag it4 --out <dir> --repairs <repairs.json> --tolerate <tolerate.json> \
  --bundle own:<...>=<revision dir>,<clone> ...  --reference ref:<...>=<aspose.org readme>,<facts>,<clone> ... \
  --write-status data/reviewer_calibration.json
```

## 2. Results (appended after the run; section 1 is unchanged)

**Status: `NOT_PASSED`** — computed by `--write-status` from the complete run (375 of 375 selected cases asked,
no budget stop) and committed as `data/reviewer_calibration.json` unchanged. 11 gates fail; the gate is not close.
The reviewer (prompt v17, logic 6, `qwen3-next`) is unchanged by this iteration; nothing was loosened.

### 2.1 One deviation from the pre-registration

The 620-call cap was too low: a mutant that shifts unit boundaries re-asks more than one unit, and contract re-asks
cost more than estimated. The first invocation stopped at the cap after 330 of 375 cases and wrote `NOT_PASSED`
(incomplete) — kept in `-data/run-output-stopped-at-620.txt`. The decision to resume was taken **before any result
was read**, and the run was resumed once with cap 900 under the same tag: the 330 answered cases replayed from the
call store at zero cost, the remaining 45 cases and the stability repeats were asked. Total physical calls: **845**
(620 + 225), 3.79 M tokens in the resumed invocation's accounting. Consequence: first-reply JSON validity is
measured over the 196 unit replies of the resumed invocation only (replays carry no first-reply record): 196/196
valid; contract-valid 179/196 = 0.91.

### 2.2 Whole corpus (the gated numbers)

| Gate | Value | n | Need |
|---|---|---|---|
| pipeline[break_install_command] | 0.80 | 20 | ≥ 0.90 FAIL |
| pipeline[contradict_format] | 0.87 | 15 | FAIL |
| pipeline[contradict_package_name] | 1.00 | 21 | PASS |
| pipeline[contradict_version] | 0.67 | 6 | FAIL |
| pipeline[drop_section] | 0.17 | 41 | FAIL |
| pipeline[duplicate_paragraph] | 1.00 | 41 | PASS |
| pipeline[invent_api_name] | 0.67 | 27 | FAIL |
| reviewer_alone[add_promotional_filler] | 0.32 | 41 | FAIL |
| reviewer_alone[inject_unsupported_claim] | 0.29 | 41 | FAIL |
| reviewer_alone[real:contradiction] | 0.00 | 7 | FAIL |
| reviewer_alone[real:unsupported_claim] | 0.00 | 74 | FAIL |
| false_reject_rate (scored clean twins) | 0.16 (6/37) | 37 | ≤ 0.10 FAIL |
| json_valid_first_reply | 1.00 | 196 | PASS |
| stability (4 reviews identical) | 0.70 (7/10) | 10 | ≥ 0.90 FAIL |

The real-defect zero is not a scoring artifact: of the 74 real unsupported-claim cases the reviewer **accepted 61**;
its 13 rejections cite other lines, never the defect (checked by reading the quotes against `Case.defect_text`).
The 7 real contradictions were all accepted.

### 2.3 By base kind (reported, not gated)

| | own bases (rendered, 7) | reference bases (`rendered=False`, 34) |
|---|---|---|
| tier-1 pipeline | all 1.00 except invent_api_name 0.86 (n=7) | install 0.71, format 0.83, version 0.60, drop_section 0.00 (n=34), invent_api 0.60 |
| reviewer-alone filler / injected claim | 0.86 / 0.71 (n=7 each) | 0.21 / 0.21 (n=34 each) |
| reviewer-alone real unsupported claim | 0/13 | 0/61 (+ real contradiction 0/7) |
| false reject | 0/4 | 6/33 = 0.18 |

Reading:

1. **The reviewer does not find a real unsupported claim, on either kind of base (0/81).** It catches a blatant
   injected one in a small rendered unit most of the time (0.71), which is iteration 3's 11/11 seen on a fair
   sample. A real one is the maintainers' own phrasing, plausible and specific; v17 accepts it. This is the
   failure iteration 3 already named (0/2), now with n = 81 instead of 2.
2. **Shown a whole README (`rendered=False`), the reviewer degrades sharply**: injected claims and filler fall to
   0.21. Units there hold far more authored text per call than a rendered candidate's (a reference README is
   2-10x denser), and the model misses an inserted sentence among many specific ones. This bears on Lane L, whose
   corrected live README is reviewed the same way.
3. **Content loss on reference bases is undetectable by construction** (0/34): with no disposition record, only
   the reviewer can notice a missing section, and its contract says a difference from the original is not a
   finding. The tier-1 `drop_section` gate is therefore only meaningful on own bases (7/7).
4. **False rejects: 6 of 33 reference twins, 0 of 4 own.** Adjudication of the 6 (reported, never gated): one is a
   clear reviewer error (Font Python: "no required third-party dependencies" and two dev-tool lines, each backed by
   a dependency fact; rejected in all 4 draws), one is a defect the curator missed (Words Python: "126 public types"
   against 199 class and enum facts), four are mixed or undecided. Even re-labelling generously, the recall gates
   fail by wide margins; the conclusion does not depend on this adjudication.

### 2.4 What this measurement also found (outside the reviewer)

* **Facts coverage gaps** (production facts stage, run locally): 17 of 34 products have **no format fact**; every
  C++ and TypeScript product has **0 symbols with a docstring**; enum members and dataclass/pydantic fields are not
  extracted; Imaging .NET has 17 public symbols. Under the reviewer's own contract an honest README for these
  products is full of "unsupported" claims (the curators removed up to 91 per README). Caveat: this container has
  no .NET SDK, so .NET example facts are UNRESOLVED here, and any format fact derived from an executed .NET
  example is missing; hosted facts would be richer for .NET.
* **Contract conflict on own bases**: four sealed, ACCEPTed own candidates (Cells C++, Go, Rust; Imaging .NET)
  carry maintainer claims no fact supports, which the S9 preservation checks (BC-04/05/07) require to stay. A
  reviewer that applied its own contract correctly would reject them, and the deterministic stage would refuse
  the repaired text. One of the two rules must move; that is a design decision, not a fix.
* **Upstream breakage**: `aspose-tex-foss/Aspose.TeX-FOSS-for-Python` at `181015d` (2026-09-02, "Refresh README:
  verified examples and documentation links") has its indentation collapsed to one space: 102 of 119 Python files
  do not parse (checked with `ast`, nothing executed). The facts stage correctly reports 9 of 10 README examples
  CONTRADICTED (IndentationError). No issue was filed (decision log 2026-10-31, decision 7).

### 2.5 What follows

TC-007 is not accepted: its check (`calibration_status.py PASSED`) correctly fails. Per the escalation ladder this is
a repeated failure on the same signature (iterations 1-4), so the next step is root-cause work, not a fifth
re-run of the same reviewer: (a) the reviewer's acceptance of plausible real unsupported claims (0/81), (b) its
degradation on dense whole-README units, (c) the facts-coverage gaps above, which make the contract unsatisfiable
for honest READMEs of 17+ products. Any changed reviewer is measured on a **new** held-out set (this corpus has now
been seen).

Data (`-data/`): `results-own-bases.jsonl` (the 71 own-base cases in full), `verdicts-by-base.json` (verdict counts
per base, all 41), `run-output.txt` and `run-output-stopped-at-620.txt` (the runner's printed metrics). The full
results file (`77b3febf4fa494b8050aa09679ac234fe4f1f079bef9ddb3d34b0e961585d4b2`) quotes aspose.org text and stays
local.

### 2.6 A gate defect found while recording this result

`python ops/gatecli.py review TC-007` (receipt in `evidence/build/GATE1_QUALITY/TC-007/`) correctly fails the card's
check, **and** reports a scope violation: `data/reviewer_calibration.json: touches a globally denied path`.
`ops/gatectl.py`'s `GLOBAL_DENY` (paths "no taskcard may EVER declare in write_paths") includes `data/**`, `docs/**`,
`evidence/**` and `.github/**`, yet 9 of the 18 cards declare such paths as their only or main write paths
(TC-002, TC-004, TC-007, TC-009a, TC-009b, TC-010a, TC-011, TC-012a). As configured, **none of them can ever be
ACCEPTED, whatever their checks say** — that is every card not yet accepted, including TC-011 (P1 delivery).
`doctor` and `validate` do not detect a card that declares a denied path. Not fixed here: changing what the release
gate accepts is reported to the owner with a proposed fix rather than made unilaterally.
