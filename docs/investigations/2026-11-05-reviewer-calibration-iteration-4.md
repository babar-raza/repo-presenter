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
