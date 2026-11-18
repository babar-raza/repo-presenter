# Lane R trust investigation (R46, BL-201), 2026-11-18

Four independent read-only investigations (universality, robustness, reliability and repeatability, hosted
portfolio proof) ran with zero provider calls against hosted logs, the hosted spend ledger, failure records and
seals. Their full reports and the 40-cell table are in `docs/investigations/2026-11-18-lane-r-trust/`. Numbers are
from 2026-11-18 on main `5bb37e3`/`c62045c` and are samples, not current rates; reproduce before relying on them.

## What is true (measured, agreed across lenses)

1. **The hosted runner is not the problem; the pipeline's convergence is.** 115 of 152 `present` runs since
   2026-11-13 failed, and every one failed inside the Lane step. Five were cancelled at the 90-minute job timeout (all
   PDF cells). No log shows rate limits, 403s, runner loss or disk-full. 109 of 115 failures are pipeline output.
2. **One unit-local defect costs the whole candidate.** Of 28 failing cells, 18 touch exactly one origin unit and
   17 have three findings or fewer; no failure is genuinely whole-candidate. There is no last-resort, recorded
   degrade step: after bounded asks the run raises (`OutputRejectedError`, 22 of 73 failed runs) or the seal gate
   refuses because a blocking check still fails (13 of 28 current failures never reach the model reviewer).
3. **Failures repeat by class; they are defects, not noise.** 3D Python fails `claim_contradiction` 8 times in a
   row across 8 code versions; Cells .NET ends BC-05 four times running. On re-runs, 36% of the failure classes were
   new to that cell, so code and check churn re-rolls the dice.
4. **Ecosystem does not predict success; product family and size do.** Email 3 of 3, Cells 4 of 7, small cells all
   certify; PDF 0 of 6, Slides 0 of 4, 3D 0 of 4, Words 0 of 3. aspose.org publication does not predict it.
5. **No frozen-code pass over the portfolio has ever happened.** The planner is a failure-queue drain (6 cells per
   fire, certified cells skipped, 13 code fingerprints in 5 days); the best same-code coverage was 22 of 40 cells
   interleaved over seven hours. Same-code repeat agreement is unmeasured (2 groups, both PDF).
6. **"Same version set" does not mean "same bytes".** `RENDERER_VERSION` is hand-bumped; renderer changes landed
   without a bump in at least five commits. Imaging .NET's latest seal has the current version set yet re-renders to
   a different README (line 208).
7. **Preflight on hosted never skips** (0 of 119): every cell's `facts` digest differs between runs (volatile
   product-page observations, toolchain strings), so each run reopens extraction and spends calls.
8. **BC-18 is the first-wave blocker for sealed cells**: 6 of the 8 failing seals fail only on register-confirmed
   false claims that were added after they sealed.

First hosted cohort under R45 (6 repair cells, 11:06Z) corroborates: all failed early on four unrelated classes
(links in Scope, member-kind/stub claims, reviewer contract broken, edition name rejected).

## Fixes, by class (all inside existing components, R27), each naming the property it improves

| Backlog | Fix | Removes | Falsifier | Improves |
|---|---|---|---|---|
| BL-210 | Register-driven correction before seal in the existing BC-18 step: an inherited sentence matching an OPEN register row is omitted; an authored one gets the row's `truth` text. R14 record per drop. | 6 of the 8 failing seals | zero-call `recertify --all` on the 8: at least 4 flip; fewer means the hypothesis is wrong | reliable, repeatable |
| BL-220 | Terminal-safe authoring and planning: before raising, the existing `recover` hooks drop the single failing slot (or invalid fact id, or edition-name sentence) when it is not must-carry; must-carry falls to the inherited text with an R14 record | the 6 `OutputRejectedError` cells | the stored rejection messages become tests; no raise | robust, universal |
| BL-230 | Terminal-safe disposition and placement: when a disposition cannot be satisfied after bounded asks, apply the one honest alternative deterministically (keep verbatim in a placeable section, or print the contradicting fact, or withhold with the register row as evidence) and make the "kept but not printable" and "superseded but unstated" rules agree; re-home links out of Scope into Documentation and Resources | 12 cells (BC-05, BC-08, BC-17, live_readme_loss, disposition_coverage) | zero-call replay on sealed dispositions; unrepairable repairs fall from 54 | universal, robust |
| BL-240 | Repair asks the model only when the check cannot compute the answer: where the check text names the keep action (10 of 22 unrepairable repairs), apply it deterministically on the first refusal | wasted calls, nondeterminism | replay the 10 logged cases | repeatable, reliable |
| BL-250 | Version fingerprint cannot under-report: a golden-render test fails when a rendered byte changes without a component version bump (no derived hash, so acceptances are not reset by every edit) | equal version set, different bytes | recertify reports `readme_changed` false for every sealed-by-current seal | repeatable |
| BL-260 | Preflight compares the facts that matter: exclude volatile observations and host strings from the facts digest used to reopen extraction, keep them in `facts.json` | 68 of 68 reopenings | rerun a sealed cell twice on hosted: skip or recertify, zero calls | repeatable, robust |
| BL-270 | Progress and time-box: stage and per-call progress lines; a wall-clock budget inside `run_cascade` that stops repair rounds near 60 minutes and applies the degrade step, so the 90-minute cancel is a safety net only | undiagnosable cancels (5 PDF runs) | no cancelled run without a last-stage line | reliable, universal |
| BL-203 | Frozen-code portfolio proof pass over all 40 cells, then a same-code repeat (design in the hosted-proof report: freeze, quiesce the planner, dispatch 40, sealed cells re-exercised by zero-call recertify, verdict PASS = run success and CERTIFIED at that SHA, agreement split generated-twice vs replayed) | the missing proof | the R46 bar | proven on hosted, repeatable |
| BL-202 | The five-property scorecard in the existing supervisor tick, from ledger, recertify and failure records | invisible trust gap | numbers match a hand computation | all |

## Ordering and limits

BL-210 first (cheapest, zero-call testable, immediate Lane R count), then BL-220 and BL-230 (the two biggest
classes), then BL-240, BL-250, BL-260, BL-270, and the first proof pass once a batch has merged (R46 cadence).
Not determined: the share of model nondeterminism (no same-code, cold-cache Lane R repeat exists), the cause of the
25 to 30 minute settle rounds on PDF cells, GitHub concurrency and provider rate-limit headroom at 40 parallel runs,
and Actions cache sizes. The proxy blocks run artifacts, so stored call stores could not be replayed here.
