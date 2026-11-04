# Repo Presenter — Consolidated Status Assessment, Audit Reconciliation, and Forward Plan

**Date:** 2026-11-04. **Read-only investigation; this document records observations and proposes
a plan — it does not itself change authority.** It does not override
`docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md` (owner-adopted binding authority per
`AGENTS.md`'s top row), `docs/MISSION_AUTHORITY.md`, or `project/state.yaml`. Where this document
disagrees with or adds to the adopted audit, that is flagged explicitly, the same way the adopted
audit's own §K treats an external review — as evidence to independently check, not inherit.

**Method:** (1) a full independent status investigation of the repository as it stood on
2026-10-31, run as four parallel evidence-gathering passes (mission/governance docs; `project/
state.yaml` portfolio counters; Lane R/Lane L code plus a fresh, self-run `pytest` pass; the
reuse manifest, git history, and real upstream-delivery evidence); (2) a direct read of both
`docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md` (including its same-day §K amendment) and
`docs/repo_presenter_independent_audit_2026-11-03.md`, compared claim-by-claim; (3) independent
re-verification, via live `gh api`/`gh run list` calls against the real repositories (not taken
from either audit's own say-so), of the single most consequential new claim the Nov-03 audit
raised. Every figure below is traced to a file, a `git`/`gh` command, or a durable state record.

**Evidence labels used throughout:** `CODE` = source inspected directly · `TEST` = test run or
result inspected · `LIVE` = a real GitHub job/PR/issue/workflow observed via `gh` · `DOCUMENTED` =
the repository describes behavior whose effect was not independently established this pass ·
`UNVERIFIED` = no credible evidence either way. "Accepted," "pipeline-good," and "owner-accepted"
are never used interchangeably below — see §2.5 and §3.4 for why that distinction is load-bearing.

---

## 1. Executive summary

Three things are true at once, and none of them cancels the others out:

1. **The core pipeline is real and it works.** Lane R has produced at least one, and as of the
   latest recorded hosted runs up to ten, independently-reviewed (not self-graded) candidates
   against real repositories; Lane L has reached a comparable pipeline-level count. The test
   suite is large, mostly unmocked at the logic layer, and passes.
2. **The project's own core quality gate — the independent LLM reviewer — has never passed its
   own calibration test**, as of every date checked (2026-10-28 through 2026-11-03). Nothing that
   has been marked "accepted" anywhere in this project has been produced or re-checked under a
   calibration-passing reviewer version.
3. **Nothing has reached a real upstream consumer.** Zero pull requests have ever been opened by
   this codebase against any upstream Aspose repository. One real issue has been filed, by hand,
   once. Separately — and this is the one genuinely new, independently-confirmed finding in this
   pass — **the predecessor repository is not dead history to learn from; it is a second,
   currently-live production system**, still firing twelve active scheduled GitHub Actions
   workflows against the same upstream App installation, as recently as under 24 hours before
   this document was written. No existing authority document, including the just-adopted audit,
   accounts for that.

The shortest honest description of where this stands: a well-built evidence/generation core,
sitting behind a quality gate that has never opened, with zero real-world deliveries, and a second
unsupervised system quietly still running in parallel. None of that requires a rewrite. All of it
requires closing specific, named gaps in a specific order — §6 gives that order.

---

## 2. Consolidated status assessment

### 2.1 Overall project status

This is a from-scratch rebuild of a project the owner personally ruled dead on 2026-10-20: the
predecessor `repository-presenter` had `authorizable_candidates: 0/36` despite 28 "sealed"
candidates, caused by a reviewer bug that silently folded 27 of 30 `REJECT` findings into `ACCEPT`
(`docs/history-reconstruction.md`, independently re-verified; fix landed on the old repo
2026-10-10, ten days before the owner's own manual review caught the damage). This repository's
own governance (`docs/MISSION_AUTHORITY.md`) forbids reusing anything from that old review/judge
chain and treats old "sealed" candidates as untrusted holdout material only.

Against that backdrop: a real pipeline exists (`present.py` → `cascade.py` for Lane R, `lane_l.py`/
`lane_l_run.py` for Lane L, one shared facts/review/seal transaction model), a large passing test
suite exists (3,367 passed / 11 skipped / 0 failed on 2026-10-31's run; 3,484/3,486 passed, 13
skipped reported — not independently rerun — by 2026-11-03), and a 36-product portfolio registry
exists. As of the latest independently-confirmed state-file figures (2026-11-03,
`scripts/portfolio_status.py`): Lane R pipeline-good on 9–10 of 36 registered products, Lane L
pipeline-good on 12 of 36. **Owner review of any candidate: zero, ever** (`project/state.yaml`'s
own `owner_review_status` entry, 2026-10-24, still true). **Upstream PRs opened: zero, ever.**

### 2.2 Current capabilities — what it can do today, unattended

- Generate a fully new, cited, independently-reviewed README from scratch for a real repository,
  with a real LLM provider, end to end — demonstrated multiple times against real repositories as
  of the Nov-01/03 hosted runs (`LIVE`, e.g. run `41657452717`, 2026-11-03: facts SUCCESS, Lane R
  SUCCESS).
- Surgically patch an already-live README (Lane L's actual job) — pipeline-good count exists
  (12/36) but **no sealed Lane L candidate was found in `candidates/` as of 2026-10-31**, and
  `plans/PLAN_lane_l_hosted.md` records Lane L's reviewer scope logic as still Lane-R-shaped as of
  2026-10-27. Whether the 12 "pipeline-good" Lane L records now include genuinely sealed,
  structurally-correct patch bundles (as opposed to Lane-R-shaped full rewrites) was not
  re-confirmed in this pass — flagged `UNVERIFIED`, worth a direct check before relying on the 12
  figure for anything but a pipeline-stage count.
- File a real upstream GitHub issue — demonstrated once (`aspose-3d-foss/Aspose.3D-FOSS-for-
  Python#4`, local human token, not the App).
- Open or merge a pull request upstream from this codebase — never done, anywhere, for any
  product (`LIVE`-checked via `gh api search/issues?type:pr` against both G4-mandatory targets,
  per the Nov-01 audit; independently consistent with this pass's own findings).
- Run autonomously on a schedule — no. `.github/workflows/present.yml` has `workflow_dispatch`
  only; its own comment calls scheduling "an owner decision... not yet made."
- Process non-.NET/Python ecosystems with execution-level verification — no; Java/Node/Go/Rust/
  CMake/Maven toolchains are absent from the execution environment used for development
  (`docs/PORTFOLIO_SCALE_PLAYBOOK.md`), so those ecosystems get code-reading verification only.

### 2.3 Lane R (regeneration)

Implemented; verified end-to-end on real data for a small, growing set of the 36 registered
products (9–10 as of 2026-11-03, up from exactly 1 physically-sealed candidate as of the
2026-10-31 snapshot in `candidates/`). The gap between the state-file's "pipeline-good" counters
and the physically-committed bundle count in `candidates/` (1 committed as of the latest figures
cited in the Nov-03 independent audit) is real and should not be collapsed: "pipeline-good" means
the durable state record reached `ACCEPTED`/`READY_FOR_PROPOSAL`; it does not mean the bundle is
committed into `candidates/`, reviewed by the owner, or produced under a calibration-passing
reviewer. The one committed Lane R bundle that exists (`aspose-3d-foss__Aspose.3D-FOSS-for-.NET`,
sealed 2026-10-26) was sealed under `reviewer_logic_version: "1"` — five versions behind the
currently committed calibration record (`"6"`, `status: NOT_PASSED`) — confirmed by direct read of
its own `review_verdict.json` (§K, Nov-01 audit; independently consistent with this pass).

### 2.4 Lane L (live updates)

Implemented, unit-tested, with a comparable pipeline-good count (12/36) to Lane R, but materially
weaker real-world evidence: `PLAN_lane_l_hosted.md` ("BUILT 2026-10-27... not run hosted, not
owner-reviewed" as of that date) and the absence of any sealed Lane L bundle in `candidates/` as
of 2026-10-31 both predate the more recent pipeline-good figure. Given this repository's own
binding history — the old repo's Lane L was the exact capability the owner personally ruled "not
a deliverable" on 2026-10-20 — Lane L's current numbers deserve the same scrutiny Lane R's got in
§2.3 before being quoted as equivalent to Lane R's progress, not less.

### 2.5 Supervisor and orchestration

Real design, unevenly practiced:

- The worker/supervisor split (`ops/SUPERVISOR.md`) and the seal/no-op-proof machinery are real
  and actively exercised (75+ "sealed" occurrences, 28+ "no_op_proof" occurrences in `state.yaml`
  history, with genuine mixed pass/fail outcomes, not a static log).
- The documented taskcard mechanism is not the one in use: `project/taskcards/` contains exactly
  one file (`TC-000.yaml`); actual work tracking happens as narrative blocks in `state.yaml`'s
  `next_ready_items`. The Nov-01 audit names this itself (dimension 19, `FAIL`) as a live instance
  of a predecessor failure mode ("an elaborate plan authored then abandoned after step one").
- Queue/integration infrastructure (`dispatch-next`, `gate-exit`, `integrate`/atomic cherry-pick to
  main) is explicitly deferred — even a finished, reviewed candidate has no automated path to land
  on `main`, let alone upstream.
- The portfolio dashboard at the top of `state.yaml` has gone stale **three times** now: the
  2026-10-21 informal sweep (36/34, caught as false-green 2026-10-28), the self-admitted staleness
  the Nov-01 audit found (not regenerated since 2026-10-31), and — independently confirmed by this
  pass, directly in the file — a third, smaller recurrence as of 2026-11-03: the top dashboard
  block (`state.yaml` lines 23/48/51) still reads `lane_r_accepted: 9`, while a later card in the
  same file (`AUDIT_2026_11_01_ITEM_7`, line 5106, re-run the same day) reports `Lane R 10/25`.
  Nobody resynced the top block after the later run.

### 2.6 Portfolio-wide progress — the forest

- Registered: 36 products (`data/registry.json`), against a mission-document target of "28+".
- Pipeline-good (durable state reached `ACCEPTED`/`READY_FOR_PROPOSAL`): Lane R 9–10/36, Lane L
  12/36, as of the latest confirmed figures (2026-11-03).
- Physically committed, sealed bundles in `candidates/`: 1 (Lane R), 0 confirmed for Lane L as of
  2026-10-31 (not re-checked this pass for Lane L's later count — see §2.4).
- Owner-reviewed: 0 of 36, ever.
- Upstream PRs: 0, ever, anywhere in this codebase's history.
- Upstream issues: 1 real filed issue; 2 drafted but explicitly withheld pending owner
  authorization; 21 total upstream defects found; 2 confirmed pre-existing via dedup.
- Registry write-mode: 30 of 36 entries are `dry_run` (cannot be live-published regardless of
  token/caller), 6 are `full` — including one of the two G4-mandatory targets
  (`aspose-3d-foss/Aspose.3D-FOSS-for-Python`) sitting in `dry_run`.

Technical progress is real; business outcome — a product reaching an actual Aspose consumer or
maintainer through this system — remains at zero.

### 2.7 Quality and production readiness

The single most important fact in this whole assessment: **the independent LLM reviewer — the
one gate that is supposed to authorize anything to ship — has failed its own calibration target
every time it has been checked**, from the first calibration run (2026-10-27) through the latest
confirmed read of `data/reviewer_calibration.json` (`status: NOT_PASSED`, failed gates
`false_reject_rate`, `stability`, `reviewer_alone[real:contradiction]`,
`reviewer_alone[real:unsupported_claim]`). `propose/effect.py` independently refuses to publish
anything while this holds, regardless of token availability — confirmed by direct code read
(`propose/effect.py:320-335`). Nothing "accepted" anywhere in this project has passed under a
calibration-passing reviewer. Separately, the real GitHub Actions run history for the one existing
workflow shows roughly a 14–15% success rate under manual triggering alone (160 failures / 187
completed runs as of the Nov-01 audit's §K pull; 160/188 per the Nov-03 independent audit's
slightly later pull) — meaning turning on a schedule today would mean scheduling a workflow that
fails about six times in seven, not a dormant-but-reliable one.

### 2.8 Outstanding work, prioritized

See §6 for the full dependency-ordered plan. In short: the reviewer calibration gate must pass; at
least one real, sealed Lane L candidate must exist; the owner must review the small set of real
candidates that exist; the state-file counters must stop drifting out of sync with themselves; a
real upstream delivery (issue or PR) must be exercised at least once end to end; and — newly
identified this pass — **the relationship between this repository and the still-live predecessor
repository must be reconciled before either system is trusted to write anywhere unattended.**

### 2.9 Realistic production timeline

No calendar date is supportable from the evidence gathered. The dependency chain is real and
short to state, long to clear: calibration passes → a real Lane L candidate is sealed → the owner
reviews the resulting small set → a real delivery (issue or PR) is exercised once → the live
predecessor system's writers are reconciled with this one → only then does scaling past the
current single-digit-to-low-teens pipeline-good counts to the remaining registry become meaningful
rather than compounding an unverified gate across more cases.

---

## 3. Reconciliation: what the Nov-03 independent audit found that the owner-adopted Nov-01
   audit (including its own same-day §K amendment) did not

The Nov-01 audit's §K amendment already independently verified and incorporated: reviewer
calibration `NOT_PASSED`, `propose/effect.py`'s calibration refusal, the registry `dry_run` block
on one G4-mandatory target, the ~14% Actions success rate, the `run_cascade.py` exit-0-on-unsealed
defect, the missing `LICENSE`, the unenforced lockfile, and a third never-called publish
mechanism (`candidates_publish/effect.py`). The Nov-03 independent audit re-confirms all of these
(and notes three — the root README, the LICENSE, the exit-code defect — as already fixed by the
time it ran). None of that is new. The following four items are new, and three of the four I have
independently re-verified myself rather than taking either document's word for it:

**3.1 — The predecessor repository is a live, currently-running second production system, not
closed history. `LIVE`, independently re-verified in this pass.** Direct query against GitHub,
not from either audit's narration:

```
gh api repos/babar-raza/repository-presenter/actions/workflows
  → 12 workflows, every one state: "active", including
    Liveness, Monitor, Sealing (scheduled), Upstream issues (scheduled),
    Candidates Publish, Propose, Propose (sandbox canary), CI,
    Verify GitHub App Installation, Audit GitHub App Installations Across Registry Orgs,
    Mirror to GitLab, Present

gh run list --repo babar-raza/repository-presenter --limit 8
  → every recent run is schedule-triggered and succeeded, most recently
    "Liveness" at 2026-11-04T00:11:03Z — under 24 hours before this document was written,
    despite the repository's own source tree being frozen since 2026-10-20T05:42:34Z.
```

This repository's own history/authority documents (`docs/history-reconstruction.md`,
`docs/MISSION_AUTHORITY.md`) correctly treat the old repo's *code and review logic* as untrusted
holdout material. None of them register that the old repo's *infrastructure* is still live and
actively writing — including an issues-lifecycle funnel (per the Nov-03 audit: PENDING 40,
APPROVED 11, FILED 1 — not independently re-verified line-by-line in this pass, but the workflow
firing it is confirmed live) and a scheduled "Sealing" job. **There are two systems with
write-capable paths toward the same upstream App installation and the same target repositories,
with no reconciliation between them, and this was unflagged until the Nov-03 independent audit.**
This is the one finding in this whole reconciliation with real safety consequence, not just
documentation value.

**3.2 — A direct strategic correction to the adopted plan's item 4.** The currently-adopted
corrective plan (`AUDIT_2026_11_01_ITEM_4`) commits to adding fresh JWT-signing/installation-
token-minting Python code to `github/client.py` for G5. Given 3.1 is real, the Nov-03 audit's
counter-proposal is directly actionable: the old repo's `propose.yml`/`candidates-publish.yml`
already mint App tokens successfully via `actions/create-github-app-token@v2` inside GitHub
Actions — a proven, already-working mechanism that avoids writing new private-key/JWT handling
code at all. This needs an owner decision before item 4 work starts, not a default toward the more
expensive option.

**3.3 — A meta-governance finding about the corrective plan's own closure criteria.** The Nov-01
audit's own §F accountability table names, from the *old* repository, the failure mode "plan depth
tracked as progress; nothing gated claiming 'in progress' on the dependency actually finishing."
The Nov-03 audit points out that the ten just-adopted `AUDIT_2026_11_01_ITEM_*` cards can close on
documented deferral without their underlying G-goal being met — i.e., the remediation plan has the
same structural weakness as the failure it's remediating. This was not named anywhere in the
adopted audit itself.

**3.4 — The stale-dashboard pattern recurring a third time, inside 48 hours of being named as a
fix item.** Already covered in §2.5; independently confirmed directly in `state.yaml` during this
pass (line 23/48/51 vs. line 5106).

**Not independently re-verified in this pass, flagged accordingly:** the Nov-03 audit's more
specific content-quality claims about the one stored Lane R candidate ("double opening," an
"At-a-Glance graph fan-out" not matching the required topology) — the audit itself labels these a
2026-10-26 historical artifact, not evidence the current engine still produces them, and this pass
did not re-audit the bundle's content line-by-line to confirm or refute. Treat as an open lead.

---

## 4. Forward plan

This plan does not replace the ten adopted `AUDIT_2026_11_01_ITEM_*` cards; it inserts one new
item ahead of them (3.1's reconciliation is a genuine blocking precondition, not parallel work),
corrects the approach on one existing item (3.2), and adds one governance fix (3.3) that should be
applied to all ten cards' closure criteria, not just logged separately.

### Stage 0 (NEW — insert ahead of existing item 1): Reconcile the live predecessor system

**Why first:** every later stage that touches a real upstream write (issues, publishing, App
auth) is unsafe to build out while a second, unsupervised, currently-active writer exists against
the same targets with no coordination.

- Inventory every active writer in the old repo: the 12 live workflows found in §3.1, what each
  one can write, and its current cadence.
- Reconcile the old issues-lifecycle funnel (PENDING/APPROVED/FILED/RESOLVED counts) against this
  repository's own issue records before either system files or closes anything else.
- Make an explicit, dated, owner-approved decision per writer: keep running (name why), pause, or
  retire — recorded in `docs/DECISION_LOG.md`, not inferred from silence.
- **Gate:** a single document or table naming every active write-capable path across both repos,
  its current owner, and its disposition (keep/pause/retire) — before Stage 3 (publication) work
  proceeds.

### Stage 1 (was item 1): Decide the taskcard mechanism's fate

Unchanged from the adopted plan. **Gate:** one `DECISION_LOG.md` entry, either reinstating
supervisor/worker taskcards or formally retiring `ops/gatecli.py`/`ops/SUPERVISOR.md`.

### Stage 2 (was item 2, with 3.3's fix applied): Automate the dashboard, with closure teeth

- Build the script that regenerates `state.yaml`'s top counters from real git refs (as the Nov-01
  audit's own research thread had to do by hand).
- Apply 3.3's correction here specifically: this card's own closure condition must require the
  dashboard to have stayed in sync across at least one subsequent hosted run, not just that the
  script exists and ran once — otherwise this item is exactly the kind of card that could close
  while the goal (a dashboard nobody has to hand-reconcile) remains unmet, which is what happened
  between the Nov-01 audit and the Nov-03 one.
- **Gate:** the dashboard survives a real hosted run without drifting out of sync (verified on a
  second occasion, not just the first).

### Stage 3 (was items 3–4, reordered with 3.2's correction): Issues caller, then App auth — reuse before rebuild

- Before any new credential code is written: confirm whether the old repo's
  `actions/create-github-app-token@v2` pattern can be adapted into `present.yml` directly. Default
  to this unless a concrete, documented reason makes it unsuitable (3.2).
- Give the issues module one real caller (discovery + file + dedupe), against one real,
  owner-named repository, independently checked.
- **Gate:** a real installation token minted and verified end to end, by whichever mechanism was
  chosen, plus one real issues-module run independently confirmed.

### Stage 4 (was item 5): First live publications against both G4-mandatory targets

Unchanged in substance, with its three already-identified preconditions (minted/verified App
token; reviewer calibration passing; `aspose-3d-foss/Aspose.3D-FOSS-for-Python`'s registry mode
moved from `dry_run` to `full`, an explicit owner decision) — now also gated on Stage 0's
reconciliation being complete, so a live publication from this repo cannot collide with an
unreconciled write from the old one. **Gate:** one real, bot-authored, independently-confirmed PR
against each mandatory target.

### Stage 5 (was item 6): Decide the scheduling question

Unchanged, now also conditioned on Stage 0: a schedule should not be turned on for this repo while
the old repo's schedules remain unreconciled. **Gate:** either a `schedule:` trigger fires once
unattended, or a dated decision-log entry explains why not yet.

### Stage 6 (was item 7): Continue the fix-queue sweep toward 25+ per lane

Unchanged — already working, should not pause for the stages above. Apply the same scrutiny from
§2.4 to Lane L's count specifically before quoting it as equivalent progress to Lane R.

### Stage 7 (was item 8): Pull aspose.org's deterministic checks

Unchanged, lowest priority, matching G7's own "optional acceleration" framing.

### Stage 8 (was items 9–10): Housekeeping

README/LICENSE/exit-code items — per the Nov-03 audit, these are already closed as of its run;
confirm and mark done rather than re-doing them.

---

## 5. Recommended immediate next actions

1. Record this document and its Stage 0 finding in `docs/DECISION_LOG.md` (done alongside this
   document — see the dated entry).
2. Get an explicit owner decision on Stage 0's writer-by-writer disposition before any Stage 3/4
   work proceeds — this is a decision only the owner can make (which old-repo writers to keep,
   pause, or retire), not one this session should make unilaterally.
3. Re-run `scripts/portfolio_status.py` before quoting any lane-count figure in future work, given
   the confirmed drift between the top dashboard and the latest card.
4. Treat Lane L's 12/36 pipeline-good figure as needing the same committed-bundle check Lane R's
   got in this pass, before relying on it as equivalent evidence.

---

## 6. Confidence notes

High confidence, independently re-verified this pass: §3.1 (live `gh api`/`gh run list` output),
§2.5's dashboard-drift claim (direct `state.yaml` line citations). Carried forward from the Nov-01
audit's §K and the Nov-03 independent audit, not independently re-run this pass but consistent
with prior independent verification: calibration status, registry dry-run split, Actions success
rate, the `run_cascade.py` defect. Explicitly flagged `UNVERIFIED` and not re-checked this pass:
Lane L's committed-bundle count as of 2026-11-03/04, the stored Lane R candidate's specific
content-quality defects beyond the heading-structure check already done in §K.
