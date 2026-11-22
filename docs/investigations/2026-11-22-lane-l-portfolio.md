# Lane L portfolio size: why 34, what it should be, and the plan (2026-11-22, BL-724)

Evidence base: the hosted official count run 44980313657 (2026-11-22 03:49 UTC, success; the gate line
`FAIL: Lane R independently_accepted 18 < 25` is the Lane R acceptance gate, not a Lane L finding), the stored state
refs (`refs/repository-presenter-state/{bundles,records,failures}/<slug>[@lane-l]`, fetched read-only), a zero-call
`python -m repo_presenter.recertify --all --lane L --json --remote origin` run against this worktree's `src`
(34 results, all `RECERTIFIED`, `provider_calls: 0`, `sealed_version_set == current_version_set == 810f7969970a`),
`data/registry.json`, `data/terminal_cells.json`, `data/readme_findings.json`, and the code in `src/repo_presenter/`.
Not verified: the upstream repositories' current heads (this session has no GitHub access to the `aspose-*-foss`
repositories), so every R5(a) "did upstream change" statement below is open, not asserted.

## 0. Rule readings, and where a rule conflicts with the owner's statement (conflicts first)

Owner (R50, 2026-11-22): the Lane L portfolio is equal to or a little below Lane R (about 36 to 40 handled
candidates), "certainly not 34 but more"; a gap is a named blocker per repository, not an accepted state.

1. **No conflict on "handled".** R44 and BL-022/BL-724 define Lane L success as 100% *handled*: accepted edits and
   justified no-action are reported separately, and R20 lists the terminal outcomes (accepted edit, `NO_ACTION_JUSTIFIED`,
   `NOT_APPLICABLE`, valid `BLOCKED_EXTERNAL`). The count's `pipeline_good=34` already includes the 5 no-action cells
   (29 accepted edits + 5 no-action). So "36 to 40 handled" is attainable under the rules as written.
2. **Real conflict if the owner means 36-40 *accepted edits*.** R16/R35 forbid counting `NO_ACTION_JUSTIFIED` as accepted,
   and R5 (strict, confirmed by R20) requires a verified upstream change AND a verified defect. R21 requires at least one real
   verified defect removed. Accepted edits are already 29, above the R35 finish line (25). Reaching 36 accepted edits would need 7
   more cells with a real defect, and the 5 no-action cells and GIS cannot supply them (no defect / no README). Only the 5 failing
   cells can possibly add accepted edits: at most 29 + 5 = 34 accepted edits, 39 handled with the 5 no-action seals, 40 with GIS
   NOT_APPLICABLE (see section 3). So the owner's number is reachable only as "handled", never as "accepted" edits.
   Report this reading to the owner; it is the interpretation already chosen in BL-022/BL-025.
3. **GIS .NET Lane L is NOT_APPLICABLE (R20), not a failure.** It has no live README (`data/terminal_cells.json`, recorded
   2026-11-13, pinned revision 1d38758, `recheck_by` 2026-11-20 is overdue). R20 counts it as a terminal outcome, but the official
   count script (`ops/checks/portfolio_delivery_count.py`) does not read `terminal_cells.json` (only `propose/portfolio_gate.py`,
   the cohort selector, `present.yml` and `recertify.yml` do), so it is invisible in "records / pipeline_good". Whether the
   owner's "Lane L portfolio" should include it is a presentation choice; under R44 it is handled.
4. **Possible conflict: R5(a) is not enforced in production.** `lane_l_trigger.compute_trigger` has no production caller
   (BL-188, still true on main: the only references are `lane_l_run.py` docs and `scripts/measure_m1.py`). Production Lane L
   runs the correction engine on any detected defect. Consequence: current Lane L seals were never gated by "upstream changed"; a
   strict R5 reading would reclassify some of the 29 accepted edits and the 5 no-action seals (BL-187/BL-188). The owner's wish for
   a *larger* Lane L collides with enforcing R5 strictly. Recommended reading: keep R5 strict for *counting an accepted edit*
   (record the trigger result per seal) and do not use R5 to *exclude* a cell from "handled" when its README has a verified
   defect: R20 says such a defect "routes to Lane R as an owned finding, never silently dropped", which is a terminal outcome.
5. **Gap in the counter, not in the rules:** the R20 "defect with no upstream change -> routed to Lane R" outcome has no
   counted representation (no entry in `terminal_cells.json`, no seal), so five cells that are in fact handled by that route
   show as "not good". The owner asked for named blockers; this is the one structural item that is a decision, not a fix (see 3).

## 1. Lane L state per repository (40 active; 41 registered, Cells PHP inactive per R29)

Counts reproduced: `bundles/<slug>@lane-l` exists for 34 of 40 active cells; `bundles/<slug>` (Lane R) for 38. All 34 Lane L
seals re-certify zero-call under the current version set (no seal is counted only under an older version set; the count's
`older_version_sets` rows are older seal *commits* of the same 34 cells, not extra repositories). Lane R lacks GIS .NET (BC-02, no
README) and Words Java.

| Lane L state | Cells | Count |
|---|---|---|
| Sealed, accepted edit (counted, `independently_accepted`; 5 `content_bound`, 24 `revision_only` binding) | 3D .NET, 3D Java, 3D Python, 3D TypeScript, BarCode Python, Cells .NET/Cpp/Go/Java/Python/Rust/TypeScript, Email .Net, Email Cpp, Font Python, HTML Python, Note Python, Page Python, PDF Go, PDF Python, PDF Java, PSD .NET, PSD Python, Slides .NET, Slides Cpp, Slides Java, Words .NET, Words Java, Words Python | 29 |
| Sealed, `NO_ACTION_JUSTIFIED` (README byte-identical to live; R16, never accepted) | Imaging .NET, PDF .NET, OCR .NET, OMR Python, PSD Java | 5 |
| Terminal, `NOT_APPLICABLE` (no README, R20; not in count) | GIS .NET | 1 |
| Attempted, failed, nothing sealed | Email Python, PDF Cpp, PDF TypeScript, Slides Python, TeX Python | 5 |
| Never attempted / not recertifying / older-set-only | none | 0 |

The count's `records=40` is the 40 active cells; it excludes Cells PHP (inactive). Lane L = 34 good = 29 + 5, 6 cells absent
from the good count: the 5 failed cells and GIS.

Per failed cell (latest attempt per the failure records and state records; all failed under older code, none has been re-run
since the Lane L version set last changed, 810f7969970a, Nov 15):

| Cell | Lane L attempts (hosted) | Blocking class | Lane R state (for context) |
|---|---|---|---|
| Email Python | 1x, 2026-11-15 run 43695398192 | `lane_l_unrepaired_defect`: `format_overclaim` x2, README marks `CFB` supported but no SUPPORTED format fact; no content edit possible, so R21 net improvement cannot carry it | sealed; 6 OPEN findings in `readme_findings.json` routed Lane R |
| Slides Python | 2x, 11-15 (43691420257) and 11-18 (44414886517) | `claim_contradiction`: 1 finding, README lists `.pptm .ppsx .ppsm .potx .potm` with no SUPPORTED format fact | sealed, accepted |
| TeX Python | 1x, 11-15 (43691421848) | `lane_l_unrepaired_defect`: `format_overclaim` (SVG) + `failing_example` (example 9 raises `aspose_tex.exceptions.InputError`) | sealed |
| PDF Cpp | 4x, 11-14 to 11-18 (latest 44414882228) | 77 blocking: 65 `claim_contradiction|lane_l_correction|member_owner` (rows like `PngDevice ... inherits ImageDevice and declares ...` attributing members to the wrong type), 10 inherited-unit contradictions, 2 failing C++ examples | sealed, accepted |
| PDF TypeScript | 2x, 11-14 and 11-15 | `job_error: LaneStepFailure ... left no failure record`; the state record also shows `ProviderCallBudgetError: budget of 100` (a block R45 removed) | sealed (but see BL-511/BL-624) |

## 2. Why Lane L is 34 and not 39-40

1. **Five cells never produced a Lane L seal**, each for a root cause above, not for lack of attempts the loop would make:
   the cohort selector marks them held/capped/idempotent ("last attempt ran this code on this upstream revision and did not
   seal") because nothing has changed in their failure scope, so no hosted run has been spent since Nov 15 / Nov 18.
2. **The failing mechanism is the strict "unrepaired defect blocks unless net improvement" rule (L-05, R21).** A net improvement
   needs at least one evidenced CONTENT edit and no new contradiction (`lane_l_review.net_improvement`). For Email Python,
   TeX Python and Slides Python the only findings are claims the extractor has no SUPPORTED fact for; the engine has no
   evidenced edit to make, so zero edits plus a residual defect is `REFUSED_LANE_R_RECOMMENDED`, never sealed. That is
   correct under R21 *unless the fact is missing from the extractor* (then the cell is a Lane R/extractor class fix, R36).
3. **PDF Cpp is a defect in Lane L's own correction output** (65 `lane_l_correction` member-owner contradictions: the engine
   introduced rows the facts contradict). A net-improving edit that creates contradictions fails R21 criterion 4.
4. **PDF TS had a harness/job error and a since-removed budget cap**, so it has never had a valid Lane L review under current code.
5. **GIS .NET has no README**, so Lane L is NOT_APPLICABLE by definition (R20); it is handled but not sealed and not in the count.
6. **R5(a) is not wired**, so the count has no notion of "no upstream change, defect present" (BL-188); such cells are neither
   "accepted" nor "no-action" and are simply absent from `pipeline_good`.
7. Lane R is not "39-40" either: 38 sealed (32 to 39 across runs), GIS and Words Java missing. The comparison number is 38, with
   18 independently accepted. Lane L is 34 sealed with 29 independently accepted (revision_only binding for 24, so BL-189 content
   binding is open for Lane L too).

## 3. What brings Lane L to "equal or slightly below Lane R"

Target set: Lane R sealed = 38 (40 only if GIS and Words Java seal). Lane L handled today = 34 sealed + GIS NOT_APPLICABLE = 35.
Reaching 38 to 40 needs 3 to 5 of the 5 failed cells to reach a terminal outcome. Ranked by probability and cost
(all runs are normal `present` run requests, dispatched by the supervisor; none sent here):

| Rank | Cell | Next concrete action | Expected terminal outcome | R5/R21 can it count |
|---|---|---|---|---|
| 1 | Slides Python | Zero-call first: check whether the `.pptm/.ppsx/...` formats are real in the pinned source (Lane R already sealed, so facts exist). If real: extractor/facts class fix (R36), then rerun Lane L. If false: the correction engine should remove them. Then `{"job":"present","repository":"aspose-slides-foss/Aspose.Slides-FOSS-for-Python","ecosystem":"python","lane":"L"}` | Accepted edit if one evidenced removal lands; else BLOCKED_EXTERNAL/route to Lane R | Counts as accepted only with one verified removed defect (R21) and an R5(a) trigger recorded (see below) |
| 2 | TeX Python | Same format-overclaim check (SVG). Example 9 is a verified failing example: BL-133 withholds a CONTRADICTED kept example with a recorded R14/R21 decision, which is the one evidenced edit that makes the run a net improvement. Also the R50 issue-system test case. Rerun Lane L | Accepted edit via BL-133 withhold; residual SVG overclaim carried as a recorded residual | Yes, if the withheld example is verified by the example verifier; counts as the real removed defect |
| 3 | Email Python | Verify `CFB` wiring in the source (the Email .Net sibling already carries Cfb types). If reachable: add the capability fact (extractor class), rerun. If not: correction removes the overclaim | Accepted edit or Lane R route | Same bar |
| 4 | PDF TypeScript | Diagnose the `LaneStepFailure ... no failure record` job error first (BL-624 and BL-511 are open on its Lane R side); fix the harness so a failure writes its record, rerun Lane L once | Unknown until a valid review exists | Same bar |
| 5 | PDF Cpp | Fix Lane L's member-owner correction output (the Lane R analog BL-320 already landed; the `lane_l_correction` path needs the same "member list is held to the type the sentence is about" rule), prove zero-call on the stored candidate, then rerun | Accepted edit once the engine stops introducing contradictions | Same bar |
| 6 | GIS .NET | Leave NOT_APPLICABLE; refresh the overdue R24/R20 recheck (head_of vs pinned 1d38758) and keep it listed beside the count | NOT_APPLICABLE | Handled (R20), never accepted |

Fallback for any of cells 1 to 5 that does not seal after one valid run (R12, R36): record R20's "defect with no upstream change
routes to Lane R" as an owned finding (`data/readme_findings.json` already holds 6 OPEN rows for Email Python) and add the cell to
`data/terminal_cells.json` with outcome `ROUTED_LANE_R`-style evidence (the file's existing mechanism; BL-025's INTERPRETATION already
says R16 outcomes belong there, no new store), so the count/report can show it as handled and separate from accepted. This
needs a one-line owner confirmation that a documented, evidenced "defect routed to Lane R" is an acceptable Lane L terminal for the
"handled" tally; it is permitted by R20's text but was never exercised and never counted.

Resulting portfolio under each reading:

| Reading | Lane L | vs Lane R 38 |
|---|---|---|
| Today, sealed only | 34 (29 accepted + 5 no-action) | 4 below |
| Today + GIS NOT_APPLICABLE as handled | 35 | 3 below |
| + Slides Python, TeX Python, Email Python seal | 38 (32 accepted + 5 no-action + 1 NA) | equal |
| + PDF TS and PDF Cpp also seal | 40 (34 accepted + 5 no-action + 1 NA) | slightly above; only if both are real accepted edits |
| + any cell not sealable closed by documented Lane R routing | up to 40 handled | counts as handled only |

## 4. Blockers per class

- **Extractor fact gaps (format/capability claims with no SUPPORTED fact):** Email Python, TeX Python, Slides Python. One class fix
  (capability/format facts for Python packages) unblocks three cells and likely removes the same findings from Lane R rows.
- **Lane L correction-engine bug (member owner):** PDF Cpp only (65 of its 77 findings).
- **Harness/job error with no failure record:** PDF TS (also a Lane R open item).
- **No README:** GIS .NET (terminal, not fixable by this pipeline).
- **R5(a) trigger unwired (BL-188) and stale no-action (BL-187):** affects all 34 sealed Lane L cells' standing, in particular the 5
  no-action seals, which could be reclassified if the owner or the gate enforces R5 strictly.
- **Acceptance binding:** 24 of 29 accepted are `revision_only` (BL-189), a count-quality risk, not a size one.

## 5. Recommended order of work (parallel, supervisor-dispatched)

1. Zero-call, parallel (no provider calls): (a) check CFB / SVG / pptm format reachability in the three pinned sources and
   the existing facts; (b) reproduce PDF Cpp's `lane_l_correction` member-owner rows locally from the stored `failures@lane-l` record;
   (c) read PDF TS's `LaneStepFailure` from run logs; (d) refresh GIS's `recheck_by`.
2. Fix the classes found (extractor facts; Lane L member-owner rule; failure-record harness), each proven zero-call, with the
   `recertify --all` before/after diff that RULINGS item 13 requires.
3. Dispatch Lane L run requests for Slides Python, TeX Python, Email Python first (batch of three, within R25's six), then PDF Cpp
   and PDF TS; command shape via `/home/user/.supervisor/push_request.sh <id> '<json>'` (the script pushes
   `run-requests/<id>` with `run-request.json`; `proof_dispatch.sh` loops it over `proof_cells.json` with 25 s spacing and
   hard-codes `"lane": "R"`, so a Lane L dispatch needs `"lane": "L"` and the five cells above).
4. Record R5(a) trigger outcome per accepted seal (BL-188), without letting it shrink "handled".
5. Report to the owner: the "accepted edits vs handled" conflict (section 0, item 2), and the decision on a counted "routed to Lane R"
   terminal (item 5).

## 6. Rules relied on

R4/R35 (about 25 accepted edits; 29 already), R5 (strict trigger), R10 (no seal lost), R14 (drops decided and recorded), R16 (no-action never accepted),
R20 (terminal outcomes; defect routed to Lane R), R21 (net improvement), R24 (external block terminal, 7-day recheck), R36 (root-cause fix per class),
R44 (Lane L 100% handled), R45 (budgets measure, never block), R50 (Lane L about Lane R). Backlog: BL-724, BL-022, BL-025, BL-187, BL-188, BL-189, BL-133, BL-320, BL-624, BL-511.
