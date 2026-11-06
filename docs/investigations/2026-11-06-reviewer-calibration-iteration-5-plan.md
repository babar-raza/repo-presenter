# Reviewer calibration iteration 5: pre-registered plan (no provider call made)

Date: 2026-11-06. Follows `2026-11-06-reviewer-rootcause.md` and the decision-log entry "reviewer rule for inherited
text". Card: `project/taskcards/TC-007.yaml`. **No provider call was made to prepare this.** Everything below was
computed offline: the corpus build, the selection and the call estimate (`run_reviewer_calibration.py register` /
`estimate`).

**This section is committed before any run.** The git history of this file and of `-data/registration.json` is the
proof that the cases, labels and stability subset were fixed before the reviewer was asked. Results go in a later
section, added by a later commit.

## 1. What is measured

The reviewer as it is at run time: prompt `independent_review` (v19 in this tree; v20 if the supervisor merges it
first), `REVIEWER_LOGIC_VERSION` 9, model route of the manifest. Thresholds are the ones in `harness.py`, unchanged:
pipeline on-target recall >= 0.90 per tier-1 defect, reviewer-alone on-target recall >= 0.90 per tier-2 defect
(every real-defect class held), false reject <= 0.10 over scored clean twins, first-reply JSON validity >= 0.90,
stability >= 0.90. The registration pins the README and defect digests, not the prompt: a prompt merged before the
run is the reviewer measured, and the status document records its version.

## 2. Held out: what was used to tune prompts v18-v20 and is not measured again

* **v18 / v19** (2026-11-05) were written from the owner's maintainer-content requirement and the dispositions of the
  12 sealed bundles (`2026-11-05-maintainer-content-calibration.md`). They used no calibration case.
* **v20** (the rules adopted on 2026-11-06) comes from the root-cause replay of iteration 4. Excluded from iteration 5
  (`-data/excluded.txt`, part 1): **every mutant and real-defect case iteration 4 asked (334 ids)**, whether or not
  the report quotes it. Iteration 4's twins are kept (they are the call-store base of the held-out real-defect cases
  of the same base); a twin used to tune is asked but **unscored** (`-data/unscored.json`): the 6 iteration-4 false
  rejects (Font Python, Note Python, PDF Go, Slides Java, PDF .NET, Words Python) and the unstable `own:html-python`.
* Held-out real defects: iteration 4 asked 2 of each base's curated repairs; the other **924 were never asked**.
  Iteration 5 asks up to 3 more per base, hash-ranked (`selection.cap_real_defects`).
* New material (never asked in any iteration): 6 own Lane R bundles, 4 live maintainer READMEs, 8 Lane L bundles
  (section 3). Caveat stated now: the 8 Lane L READMEs are each 0.97-1.0 line-similar to the aspose.org candidate of
  the same product that iteration 4 asked (two are byte-identical: 3D TypeScript, Cells Java); they are new cases
  because they are judged against the **hosted facts their bundle was sealed with**, not iteration 4's local facts,
  and their twins are the Lane L candidate production sealed. Their mutants are new.

## 3. Corpus (51 bases, 1,465 cases built, 288 registered)

| Source | Bases | How loaded | Scored twins | Unscored twins | Mutants | Real defects |
|---|---|---|---|---|---|---|
| iteration-4 own bundles (`own:`) | 7 | `--bundle` (iteration-4 exports) | 3 | 4 | 0 (all asked in it4) | 15 |
| iteration-4 aspose.org candidates (`ref:`) | 26 of 34 | `--reference` | 9 | 17 | 0 (all asked in it4) | 78 |
| new own Lane R bundles (`own5:`) | 6 | `bundle_store.export_bundle` from origin, `--bundle` | 4 | 2 | 49 | 12 |
| new live maintainer READMEs (`live5:`) | 4 | `--reference` (live README, iteration-4 facts) | 4 | 0 | 25 | 8 |
| Lane L bundles (`lanel5:`) | 8 | `export_bundle(..., "L")`, `--lane-l` (new loader) | 8 | 0 | 50 | 0 |
| **total** | **51** | | **28** | **23** | **124** | **113** |

* New scored clean twins: **16** (own5 Cells Python, Cells TypeScript, Note Python, PDF Java; live5 Cells .NET, Cells
  Python, PSD Python, PSD .NET; Lane L 3D Java, 3D TypeScript, BarCode Python, Cells Java, Cells Rust, Cells
  TypeScript, Email .NET, Imaging .NET). **Short of the 20 asked for.** Each was verified clean against the
  deterministic stage with zero calls: no deterministic rule fires (`corpus.deterministic_findings`, Lane L's holdout
  rules for `rendered=False`) and no blocking check fails beyond its stated baseline (`-data/tolerate.json`). Two more
  new own twins (Email .NET, Imaging .NET, the 2026-11-06 seals) became unscored: removing their unattributed
  unsupported claims removes text their dispositions print verbatim, so `disposition_coverage` fires on the twin.
  Rejected sources, each with the reason: Lane L HTML Python and Words Python (an iteration-4 repair removes live
  content, and 20-39 uncurated lines of table descriptions no fact states), Lane L PDF Go / PDF .NET (183 / 341
  uncurated lines), live Font Python and Slides .NET (dense with claims no fact states), the pilot cascades (not
  durable: their scratch directory changed during this work), 3D .NET in `candidates/` (twin blocked by
  `live_readme_loss`). The portfolio has no further sealed or reference README never asked; more clean twins need
  new candidates.
* Scored clean twins total **28** (12 from iteration 4, not used to tune). The false-reject gate allows 2 of 28.
* Mutants by operator: add_promotional_filler 18, break_install_command 12, contradict_format 7,
  contradict_package_name 12, contradict_version 6, drop_section 18, duplicate_paragraph 18, inject_unsupported_claim
  18, invent_api_name 15. Real defects: unsupported_claim 100, contradiction 13.
* Cost exclusion (`-data/excluded.txt`, part 2, decided from the estimate before any verdict): every remaining case of
  8 reference bases with the costliest whole-README units (PDF .NET/Python/C++/Java/Go, Slides Python/C++/Java; all
  8 twins unscored anyway), 240 ids.
* Stability: 20 cases (10 scored clean twins, 10 defect cases), hash-ranked among cases with at most 4 review units
  (`--stability-max-units 4`, a cost bound fixed before any verdict).

### 3.1 Labels and the inherited-text rule

Decided rule: an inherited sentence is exempt from claim findings only when it is printed under the maintainer
attribution (`PRESERVE_ATTRIBUTED`) and no fact contradicts it; inherited text printed as the README's own claim is
judged like generated text. Applied:

* Reference, live and Lane L READMEs (`rendered=False`) carry no attribution, so every unattributed inherited
  unsupported claim is a defect. Iteration 4's curation brief already labelled them so ("a claim only an inherited
  unit states is still unsupported"), so its 1,005 labels stand unchanged.
* Iteration-4 own bundles predate `PRESERVE_ATTRIBUTED` (none of their units has it): unchanged.
* New own bundles: attributed lines (Email .NET 154-156, 242-246; Imaging .NET 11-14, 227-229, 267-269) were
  **not** labelled (none is contradicted by a fact; for example "29 classes and enumerations" equals the 23 class and
  6 enum facts). The unattributed platform list "runs on Windows, Linux, macOS, Docker containers, and serverless
  functions" (Email .NET, inherited, printed as the README's own claim) **is** a real defect.
* New labels (same standard as `CURATION_BRIEF.md`, each checked by searching non-inherited fact values and
  attributes): own5 13 repairs (committed in full, `-data/own5-repairs.json`), live5 12 (one contradiction: PSD .NET
  "not published to NuGet" against `package:published_version` 26.10.0 on nuget). Lane L twins reuse the iteration-4
  repairs of the same product's text (251 apply exactly once) plus 3 lint repairs of uncurated table cells (Cells TypeScript), all as
  twin-only repairs (`klass` null: no real-defect case, because those labels were judged against other facts). A
  curator miss makes the false-reject measurement stricter, never easier.

### 3.2 Pre-registration digests

| File | SHA-256 |
|---|---|
| `-data/registration.json` (288 cases: id, role, expected verdict, class, label, README and defect digests; 20 stability ids) | `3352ced4974d64372cb7094bc9fa7ff2f27b8d654db2126891931489b8a6975c` |
| `-data/excluded.txt` | `d5db25cd7a388d10e01a091400e377ebe0eb8b313992ee3bc1c5c5ee7e9420f5` |
| `-data/own5-repairs.json` | `14f20b80ee99fbddfac7e96907b9596fc218b37342ef1c7e731401b562a44e56` |
| `-data/tolerate.json` | `e67a0802bb4dc18595bde6ccc0b5db890cf6469daf1223c8db0e60e3bad9bcc4` |
| `-data/unscored.json` | `61be859053e5bbf7787b24b34f3f6a083ce51e77ff9f55748e50ddc17af6bd20` |
| `repairs5.json` (all repairs, local: quotes aspose.org and maintainer README text) | `b7e7e21a16469472375669df4d57f642a8468584344d33b35bfe5ec16aef1a0d` |

`registered_cases` rebuilds the corpus and refuses to run if any registered case is missing or its role, expected
verdict, class, label, README digest, facts revision or defect digest differs. Bundle refs exported (origin,
2026-11-06): Lane R Email .NET `c304dbed`, Imaging .NET `6c25dafd`, Cells Python `f36a02fd`, Cells TypeScript
`f10b84af`, Note Python `42dbb549`, PDF Java `391e1d5b`; Lane L 3D Java `77f3fc2c`, 3D TypeScript `3d6409a7`, BarCode
Python `182c2a20`, Cells Java `30f1fad5`, Cells Rust `153a3017`, Cells TypeScript `9e932b6e`, Email .NET `8dfeb22d`,
Imaging .NET `13979c8e`. A reseal moves the ref; the digests then refuse the run rather than measure a new README.

## 4. Call estimate (zero calls)

`estimate` walks the registered cases in run order and hashes every review unit's request with
`llm_review.planned_requests`, the function the live review itself uses to build what it sends, against the call
store and journal on disk:

```
cases 288: 1130 unit requests, 617 not replayable from the store
stability 20 cases x 3 fresh reviews: 147 requests
  clean 28 cases 94 | mutant 124 cases 180 | real_defect 113 cases 215 | unscored_twin 23 cases 128
requests 764; expected calls 841 at re-ask rate 0.10; worst case 1528 (every request re-asked)
cap 1000: expected 841 leaves 159 (16%) headroom
```

The re-ask rate is iteration 4's (17 of 196 first replies broke the contract). Transport retries are not modelled;
iteration 4 had 1 HTTP 502 in 845 calls. If re-asks exceed about 31 % the cap stops the run, which is then
incomplete and `NOT_PASSED`; resuming it is section 5.

## 5. The run command (supervisor)

Inputs are local paths of this session (`-data/inputs.args`, one argument per line: the 51 bases, the repairs,
tolerations, unscored list, registration and a corpus cache). From the repository root:

```
PYTHONPATH=src python scripts/run_reviewer_calibration.py estimate \
  @docs/investigations/2026-11-06-reviewer-calibration-iteration-5-data/inputs.args \
  --out <OUT> --tag it5 --max-calls 1000
PYTHONPATH=src python scripts/run_reviewer_calibration.py live \
  @docs/investigations/2026-11-06-reviewer-calibration-iteration-5-data/inputs.args \
  --out <OUT> --tag it5 --max-calls 1000 --write-status data/reviewer_calibration.json
```

`--max-calls` (alias of `--cap`) bounds the physical calls in `<OUT>/ledger.jsonl` across every invocation. Resume
after an interruption or a cap stop: **re-run the identical command** (raise `--max-calls` only by an owner decision).
Each completed review is appended to `<OUT>/journal-it5.jsonl` (`ReviewJournal`, keyed by store, case, README digest,
prompt digest, logic version and model) and is taken from there with no request, first-reply flags included, so the
resumed run measures first-reply validity over the whole run (iteration 4 lost that). A review the cap interrupted
replays its answered units from the call store; at most the one unit in flight when a process is killed is asked
again. Stability runs only after a complete first pass. `estimate` on the same `<OUT>` reports what is left to spend.
`--write-status` writes `PASSED` only when every gate passes and every registered case was asked.

## 6. Code (this commit)

* `llm_review.planned_requests`: the unit/packet/hash part of `review_with_model`, now shared by the dry run.
* `calibration/estimate.py` (zero-call estimate), `calibration/registration.py` (pre-registration and its check),
  `reviewers.ReviewJournal` / `review_key` (resume), `sources.load_lane_l_bundle_candidate`,
  `Base.unscored_reason`; script modes `register` / `estimate`, `--registered`, `--exclude`, `--unscored`,
  `--lane-l`, `--stability-max-units`, `--max-calls`, `@file` arguments.
* Tests: `tests/readme/review/calibration/test_calibration_iteration5.py` (the estimate equals the requests a scripted
  live run sends; an interrupted run resumes to exactly the uninterrupted call count; an unavailable review is not
  re-asked; registration refuses a changed README or label; the Lane L loader).
