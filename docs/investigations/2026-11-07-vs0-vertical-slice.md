# VS0: vertical-slice baseline (2026-11-07, zero provider calls)

Per `docs/DELIVERY_PLAN_2026-11-07.md` §8.1 step 5: run the full path with today's mechanisms on one Lane R
and one Lane L case, and record every gate each fails, before building anything further. Both results below
are read from already-sealed/already-recorded evidence (no new model call, no new run); the local recertify
reproduction used the `GIT_CONFIG_*` override (F27) and matched the committed baseline exactly.

## Lane R: Aspose.Email-FOSS-for-.Net (chosen per F22: its upstream HEAD equals its seal revision)

1. **Fresh evidence:** upstream HEAD (`gh api`) == the seal's `source_revision` (`59125b4732df0eedbc4d4c2ab978698ed4348eb7`). No regeneration needed to be current.
2. **Deterministic validation:** `recertify --all` → `RECERTIFIED`, `failing_checks: []`. Passes §5.1 `deterministically-validated`.
3. **Sealed review verdict** (`review_verdict.json` in the bundle): `verdict=ACCEPT`, `model_verdict=ACCEPT`, `reviewer_logic_version=10`, `prompt_version=21` — these **already match** the current prompt/logic versions.
4. **The single blocking gate:** `classify_review` (`ops/checks/portfolio_delivery_count.py:148`) checks `calibration.status != "PASSED"` **before** checking version match, and `data/reviewer_calibration.json.status == "NOT_PASSED"`. Result: `UNCALIBRATED: "committed reviewer calibration is NOT_PASSED"`.
5. **Conclusion:** this candidate fails exactly one gate — the global calibration status — not a version mismatch, not a content defect, not preservation, not parity. It is the cleanest possible M1 candidate: once `data/acceptance_calibration.json` reaches PASSED (TC-022b) and this seal's audit passes (§5.3), it needs no repair to become `independently-accepted`. This confirms the plan's "shortest path to M1" choice of Email .NET.

## Lane L: Aspose.Slides-FOSS-for-Java (R5-eligible per the 2026-11-07 census, F12)

No seal exists for this repository in Lane L yet; its only record is the 2026-11-01 run, read here at zero cost.

1. **R5 trigger:** present per the census (upstream changed since the README was last touched; one of the 16 "changed and defective" repositories).
2. **The run's actual result** (`record.json`, `aspose-slides-foss__Aspose.Slides-FOSS-for-Java@lane-l`, `state: FAILED_INTERNAL`, 2026-11-01): the `enterprise_edition_naming` detector found one genuine Enterprise Edition naming violation at line 754 ("commercial product") but **declined to auto-fix it**, because the product name and its platform are not both spelled out on that one line — the detector's own safety rule against guessing. With one defect found and zero repaired, holdout **L-05** (`lane_l_unrepaired_defect`) blocked sealing outright, and the independent review REJECTed with that one blocking finding. Nothing sealed.
3. **Under today's rule** (every detected defect must be repaired or nothing seals), this candidate can never seal until the detector is extended to this phrasing shape.
4. **Under R21 (net improvement, adopted 2026-11-07):** this would not change the outcome by itself, because there is only one defect and it is the one left unrepaired — net improvement needs at least one real fix. **What actually unblocks this repository is TC-025's planned "remaining naming shapes" detector work**, which is exactly this case (product name and platform not co-located on one line): once that shape is handled deterministically, this becomes a real R5-valid, net-improvement Lane L edit at zero provider calls beyond the one independent-review call Lane L always makes.
5. **Conclusion:** this is a real, representative, already-recorded instance of F13's finding (unrepaired naming shapes blocking otherwise-good Lane L runs) and of R21's purpose. It is tracked as the first concrete TC-025 work item rather than re-run speculatively.

## What this confirms about the program

- The plan's M1 critical path (Email .NET) and its diagnosis of the calibration gate as the sole blocker are now confirmed against the actual sealed evidence, not inferred.
- The plan's Lane L diagnosis (detector coverage, not R5 eligibility, is the bottleneck) is confirmed against a real, already-recorded run rather than a hypothetical one.
- Nothing here required a new provider call, a new clone, or a new hosted run.
