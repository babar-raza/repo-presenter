from pathlib import Path
src=Path('C:/Users/babar/AppData/Local/Temp/mnt_data/REPOSITORY_PRESENTER_RECOVERY_V4_SINGLE_SOURCE_EXECUTION.md').read_text(encoding='utf-8')

def between(a,b,new):
    global src
    i=src.index(a)
    j=src.index(b,i+len(a))
    src=src[:i]+new.rstrip()+"\n\n"+src[j:]

def rep(a,b):
    global src
    if a not in src: print('MISSING',a[:100]); return
    src=src.replace(a,b)

rep('# REPOSITORY PRESENTER — SINGLE-SOURCE RECOVERY, SUPERVISOR BOOTSTRAP & SHIPMENT CONTRACT (V4)', '# REPOSITORY PRESENTER — AUTHORITY-PRESERVING RECOVERY, VERIFIED SUPERVISION & UPSTREAM DELIVERY (V5)')
rep('**One document. One implementation authority. Complete handoff.**', '**One document. Existing project authorities only. Complete evidence-led handoff.**')
rep('**Created:** 2026-10-16', '**Revised:** 2026-10-16')
rep('execute a single controlled authority cutover, and dispatch bounded worker taskcards','verify integration with the preexisting mission state machine, and dispatch only work admitted under its existing cursor')
rep('Existing repository-specific authorities remain legally/operationally authoritative until the **reviewed cutover**, at which point this specification is reconciled into them, never maintained as a competing permanent state machine.', 'Existing repository authorities remain authoritative at all times. There is **no authority cutover**. Any change is admitted and committed through their own change process; this handoff is external research, not an authority or runnable alternate mission.')
rep('**Precedence when material conflicts appear:** current live upstream source/facts + explicit owner safety/effect approval > `plans/idea.md` product mission and prior explicit owner rulings > existing `AGENTS.md` safety and current live effect controls > this v4 **recovery execution sequencing** > older `project/loop-prompt-ship.md` and other historical implementation ladders. This is not a license for the agent to override security, owner permissions, protected README content, or legal notices. A verified conflict must be recorded with source commit and exact resolution as part of the controlled cutover; do **not** allow two concurrent active task queues.',
'''**Precedence:** **existing `AGENTS.md` defines the authority hierarchy**. `plans/idea.md` owns product outcomes, `docs/EXECUTION_STATE_MACHINE.md` owns implementation order/gate exit, `docs/STATE_MACHINE.md` owns runtime transitions, `docs/SUPERVISION.md` owns agent-session supervision, `project/state.yaml` is the sole cursor, `docs/README_STANDARD.md` owns README structure and preservation, `docs/README_CONTRACT.md` owns assembly/checks until migrated, `docs/REPOSITORY_LAYOUT.md` owns file placement, and `migration/reuse-manifest.yaml` owns reuse. The owner may direct a governance change; that change becomes executable only after being correctly recorded in the existing `docs/DECISION_LOG.md`, applicable normative source(s), cursor/work-item registration and tests. **This V5 document never outranks or suspends an existing authority.** Current repo/default-branch source is evidence, not a governance override. No competing task graph, new G0–G7, new state writer or assumed `foss-mcp` authority is permitted.''')

between('### A2. Recovery governance before production worker dispatch','### A3. Hard definition of delivery', '''### A2. Authority-compliant supervisor upgrade and dispatch

7. **Run the existing authority's orientation first.** `project/state.yaml` currently names gate `G3_PYTHON_COHORT`, active item `G3-W11`; `AGENTS.md` directs the executor to `project/loop-prompt-ship.md`. Read the actual current file, the corresponding `docs/EXECUTION_STATE_MACHINE.md` G3 clauses, decision log and active work item. Treat all counts and these IDs as **2026-10-16 observations to reverify locally**. The recovery's preliminary reconnaissance is a substep of the **existing** current item, not an invented `G0_RECON` gate.
8. **Check the project’s own supervisor first**, including `docs/SUPERVISION.md`, `tools/reviewer/procedure.md`, `tools/reviewer/reviewer_check.py`, `tools/reviewer/reconcile.py`, `project/loop-prompt.md`, `project/loop-prompt-ship.md`, `project/loop-prompt-lane.md`, `project/lanes/`, `tests/test_governance_consistency.py`, `tests/test_register_integrity.py`, `.github/workflows/liveness.yml`. Prove which parts already work, fail, duplicate or need to be strengthened before proposing any `foss-mcp` port.
9. **Build a crosswalk, not a new plan authority.** Map each missing supervisor capability (exclusive dispatch, supervisor/worker provenance, falsifier/holdout, independent review, cold restart, commit guard, derived-state validation) to the existing authoritative file, owning **existing work item**, current test/entry point and integration mechanism. Preserve work-item IDs and gate order. For missing scope/coverage, follow the current owner admission process and add or revise a registered item within the existing `docs/EXECUTION_STATE_MACHINE.md` and `project/state.yaml`—no parallel backlog.
10. **Prove supervisor improvements in an isolated worktree with synthetic taskcards**, while using the **existing cursor/schema** as the only authoritative build state. The test harness may use an in-memory or temporary fixture; it must not write a second tracked `state.yaml`, and a ported `foss-mcp` `gatectl.py` must not overwrite `project/state.yaml`. Independently run the 15 negative and positive tests in Section E; separately prove legacy reviewer and liveness still work.
11. **If existing mission governance needs amendment, use its own admission process.** `AGENTS.md` changes only where actual agent-conduct or hierarchy language must change; its authority is not replaced. Amend `docs/EXECUTION_STATE_MACHINE.md` only for approved gate/work-order/predicate revisions, `docs/SUPERVISION.md` for supervisor mechanics, `docs/STATE_MACHINE.md` only for product runtime behavior, and `project/state.yaml` only for an admitted, evidence-backed cursor transition; land coherent tests and `docs/DECISION_LOG.md` owner ruling. Obey existing 210-line AGENTS / 520-line execution-document budgets **by replacement, not append-only inflation**. No automatic cursor ownership transfer.
12. After the supervisor is independently preflighted and incorporated under current authorities, resume **the currently admitted work item** and execute the fastest legal delivery-critical tasks. Existing G3 acceptance requires a judged R candidate and sandbox-proven proposal path. Expand L's feature-delta work as a distinct admitted current/future work item under the **existing G3–G7 machine**, respecting gate dependencies or recording an explicit authorized amendment. Keep existing issue scheduling operational. External writes remain separately authorized and scoped.
''')

rep('| F29 | Single cursor and safe cutover | Old `AGENTS.md`, `project/state.yaml`, gate docs and loop conflicts if copied blindly | `AGENTS.md`, `loop-prompt-ship.md`, `foss-mcp` constants | Shadow preflight, atomic reviewed cutover to one cursor | SUPERVISOR | SOURCE_INSPECTED |',
'| F29 | No authority replacement / one existing mission cursor | `AGENTS.md` forbids competing plans; `docs/EXECUTION_STATE_MACHINE.md` owns order; `docs/SUPERVISION.md` already governs sessions | `AGENTS.md` L15–65, ESM L85–168, existing reviewer procedure; `project/state.yaml` L5–71 | **Retain the existing state machine and cursor; crosswalk missing foss-mcp verification controls and amend only under its own work-item admission. No cutover or new gate graph.** | SUPERVISOR | SOURCE_INSPECTED |')
rep('**Earlier ladder — superseded:** `project/loop-prompt-ship.md` treated R as primary and L as fallback, and placed broad acceptance work before first PR. Under this owner handoff, preserve its proved technical fixes and authorizations but retire its old priority/dispatch sequence at the **single reviewed cutover**.',
'**Earlier ladder — CURRENT UNTIL DULY CHANGED:** `project/loop-prompt-ship.md` is explicitly named as the executor queue by `AGENTS.md`. It cannot be retired or bypassed by this document. Its R-primary/L-fallback ordering conflicts with the owner’s newer independently coequal L/R objective; the supervisor must record that owner direction in the existing `docs/DECISION_LOG.md` and amend the governing `AGENTS.md`/`docs/EXECUTION_STATE_MACHINE.md`/cursor/loop as applicable **before** acting on a changed order, preserving accepted results.')
rep('**foss-mcp proof pattern — retained in substance, not blindly copied:** supervisor owns cards/falsifiers/acceptance, worker owns scoped code commit, `gatectl` calculates derived state, concrete semantic negative controls prove non-vacuity, restart recovery and holdouts.',
'**foss-mcp proof pattern — OPTIONAL MECHANICS, never authority:** augment current supervisor with scoped worker changes, independent falsifiers, replay checks and restart behavior. Existing authorized executor/cursor transition process owns `project/state.yaml`; `gatectl` may validate/derive a projection but cannot become a rival mission or sole state writer without a separately approved hierarchy amendment.')
rep('**This v4 document is the entire handoff.**','**This v5 document is the entire handoff.**')
rep('**Section D preserves the full previously audited v3 master specification.**', '**Section D preserves the source evidence and lane design from prior audits; wherever a historical proposal assumed a new authority, V5 replaces that procedure with existing-cursor integration.**')
rep('**All referenced companion material is embedded in Sections C and E/G of this V4 file. This document must be reconciled into project-approved existing authorities after verified supervisor cutover; it must not remain a competing runtime controller.**',
'**All prior evidence is embedded in Sections B/C/D/E/F/G. This document does not govern the runtime or authorize a cutover. Only existing repository authorities govern execution and may be changed through their normal admission/commit/verification process.**')
rep('**Audit time:** 16 October 2026, Asia/Karachi.', '**Audit time:** 16 October 2026, Asia/Karachi.')
rep('use an isolated bootstrap branch/worktree and no direct `main` changes','use a worktree approved by the existing `scripts/new_worktree.sh` and no direct ad-hoc `main` mutations')
rep('| `AGENTS.md` L1-170 | Owns agent conduct, two lanes, protected inherited material, two-failure cutoff, isolated worktrees, current old priorities | **KEEP safety; amend only conflicting old gate ownership during cutover**; no second governance authority |', '| `AGENTS.md` L1–208 | Owns hierarchy, agent conduct, two lanes, protected inherited material, two-failure cutoff, isolated worktrees | **KEEP ABSOLUTELY**. Only modify if a documented owner-approved conduct/priority amendment requires it; no alternate authority; stay within 210-line cap |')
rep('| `docs/EXECUTION_STATE_MACHINE.md` / `docs/STATE_MACHINE.md` | Huge existing G0-G7 build and runtime plans | **RETIRE old execution ordering only after owner/supervisor logged cutover.** Migrate safety predicates selectively; no parallel active gate graphs |',
'| `docs/EXECUTION_STATE_MACHINE.md` / `docs/STATE_MACHINE.md` | **Existing authoritative** G0–G7 build gates and separate runtime machine | **KEEP AND CONTINUE**. Modify predicates/order narrowly under the official admission and decision-log process, not via cutover; retain gate history/accepted evidence; keep ESM at ≤520 lines |')
rep('| `project/loop-prompt-ship.md` L1-~85 | Has Lane R primary, L fallback, seven serial rungs; rung-3 declared done 2026-10-15 | **RETIRE as active dispatcher at cutover**, preserve dated evidence; use supervisor taskcards instead |',
'| `project/loop-prompt-ship.md` L1–94 | **Current active executor queue**, named by `AGENTS.md`; R primary, L fallback; rung-3 declared done historically | **KEEP IN FORCE UNTIL OFFICIALLY AMENDED** to incorporate dual-lane delivery and verified supervision; do not dispatch contrary tasks before change |')
rep('**KEEP existing as safe adapters until v3 cutover**, then route to separate R/L jobs; never run v1/v3 writes for same target concurrently','**KEEP existing producers/effect owners**; add source-delta L routing via accepted work items/tests after official state-machine admission; never introduce a second writer for a target')

between('## D7. Build state machine and rapid delivery execution gates','## D8. Failure modes, negative controls and release evidence', '''## D7. Fast recovery work packages **mapped into existing G0–G7** (NOT new gates)

**No new G0–G7 IDs are created here.** The existing ESM remains normative: `G0_FOUNDATION`, `G1_FIRST_VALID_CANDIDATE`, `G2_STABILITY_UNDER_CHANGE` (accepted), **current** `G3_PYTHON_COHORT` / `G3-W11`, then existing G4, G5, G6 and G7. This table is a suggested *subtask crosswalk* which the supervisor must admit through the current `project/state.yaml` and existing process. It is **not a queue, task graph or substitute for the official cursor**. Workers may never self-dispatch from this table.

| Recovery need | Existing authority / admissible parent | Minimal proof to incorporate |
|---|---|---|
| Baseline recon & governance conflict check | `AGENTS.md` §Read Before Acting, ESM §5–6, **current G3-W11** research/orient | Source-pinned baseline, official `repository-presenter status`, discrepancy ledger, no state alteration merely for recon |
| Improve supervisor independence/role protection | `docs/SUPERVISION.md`, `tools/reviewer/procedure.md`, ESM current or separately owner-admitted work item; `AGENTS.md` if role conduct changes | Existing reviewer/procedure still works; independent falsifier and blocked worker scope; no new cursor writer |
| Judge acceptance & bounded R candidate | **current G3-W11** ESM §G3 L302–323 | Judge passing clause for one current source-bound R candidate, no stale blanket reseal, source-verified content, readiness to existing proposal gate |
| Read/write GitHub effect spine | Existing ESM **G6-W02/G6-W03**, current G3 explicit dependency on sandbox-proven write path; do not invent a G2 | Existing lawful sandbox PR/remote readback; trace to existing G3 dependency or officially amend sequencing if current gate forbids building it |
| Lane L corrections / feature delta | **G3-W09** original live-first correction, plus distinct owner-admitted L source-delta extension if current item does not cover it; runtime ESM G4/G7 as applicable | Useful correction is not semantic L feature delivery. Novel new public export gets grounded diff and authorized upstream PR |
| Full R regeneration | **current G3-W11** and ESM §G3 | Complete R diff, inherited content traced, independent quality proof, PR after exact per-target write authorization |
| Unattended L/R | Existing **G5/G7** runtime/hosted items after gate prerequisites; only within scope already built or newly admitted | Two separately observed scheduled runs, source drift and no-op tests |
| Issue bot preservation | Existing G6/G7 issue work items and `issues-scheduled.yml` | Existing remote issue receipts remain, no missed scheduling or duplicate write |
| Registry/JMAP/other platform admission | Existing G4/G5 discovery & write-scope governance | Stable repo IDs, updated allowed registry through owner-approved process; no blanket `full` |

### Subtask execution order within the CURRENT authoritative item

1. **Check, do not override, the active cursor**. Record stale observations, test current sources and trace all previously accepted G0–G2 evidence. Read live owner decisions that modified G3; never reset earlier gates.
2. **Supervisor capability gap analysis** against existing `docs/SUPERVISION.md`, `tools/reviewer/procedure.md`, reviewer check, liveness and channels. Mark `ALREADY_PRESENT_AND_PROVEN`, `PRESENT_BUT_FAILED`, `MISSING_REQUIRED`, `NOT_NEEDED_FOR_FIRST_PR` for every `foss-mcp` feature. Missing capability additions need a sanctioned scoped work item. No all-of-`foss-mcp` copying as a prerequisite to shipping.
3. **Preflight proposed strengthening** in disposable fixtures/worktree, using current mission's channels and cursor only; tests `SV-P01..15` in Section E, without introducing a new version of `G0/G1` or hardcoding incompatible state schema. Deliver evidence to current work item's `evidence/build/G3_PYTHON_COHORT/...` path after verifying allowed paths.
4. **Prove the smallest current G3 judge/result**, then its **already admitted** sandbox proposal dependency; if current docs don't permit an effect implementation in G3, amend ESM via the official owner/dependency process or continue with an already-implemented G6 adapter—not a silent out-of-order jump.
5. **Admit R and L separately** within the existing machine. Execute scoped tasks for new-API delta observation, authored L patch, independently accepted complete R candidate, shared effect, and no-op using appropriate G3/G4/G6/G7 work items. One shared-code writer at a time; worktree isolation; no dual effect writer.
6. **Reconcile status and receipts in the canonical cursor** *only* at accepted work-item transitions. Never overwrite it with the `foss-mcp` `rebuild_state()` output; compare derived projections and flag mismatch for the authorized executor to resolve with proof.

### Taskcard specimens — **proposed subcards, not authorized free-standing mission IDs**

| Suggested local specimen | Register under | Exclusive technical focus and current code anchor | Required negative control |
|---|---|---|---|
| `SV-CHECK` | Approved current G3 supervisor subtask | `tools/reviewer/reviewer_check.py` L285, L833; `docs/SUPERVISION.md` L1–78 | False accepted work item or illegal worker file change must be rejected |
| `SV-FALSIFIER` | Approved current G3 supervisor subtask | existing reviewer check + minimal port of `foss-mcp ops/gateverify.py` L168/209 **only if needed** | Mutating code's real semantic behavior makes independent suite red |
| `SV-RESTART` | Approved current G3 supervisor subtask | existing `liveness.yml`, reviewer procedure L57–95, durable mission channels | Cold restart exactly resumes current `G3-W11`, never forks a second work item |
| `R-JUDGE` | `G3-W11` | `components/readme/acceptance/judge.py` L692; `cli.py` status; `bundle/recheck.py` | Fake fact, loss of custom section, irrelevant version bump all handled correctly |
| `E-SANDBOX` | Existing ESM G3 dependent proof / G6 approved item | `components/propose/effect.py` L212; `propose.yml` | Missing App installation denied, lost POST reconciled, duplicate PR zero |
| `L-NOVELTY` | `G3-W09` successor or owner-admitted L item | `components/monitor/relevance.py` L200–268; `detectors/gaps.py` L39 | New previously unconsumed public export detected; private-only change does not trigger |
| `L-COMPOSE` | owner-admitted L change-authoring item | `components/readme_correction/engine.py` L69–125; new minimal L semantic adapter | Unrelated README bytes remain exact; no unsupported capability |
| `R-REGEN` | `G3-W11` | existing R composer/repair/judge, no architecture rewrite | README demonstrably stronger, inherited content correctly retained |
| `BOTH-ROUTE` | current-approved runtime work item | existing `monitor/drift.py`, scheduling workflow | No L/R double write, merged R becomes new L baseline |
| `ISSUES-QA` | existing G6/G7 issue item, independent | `components/issues/file.py` L300; `issues-scheduled.yml` | Duplicate/false positive refused; working bot unchanged |

**Registration rule:** Every card issued by a new controller must be an *implementation subcard* linked to a real existing work-item ID, current gate, owned paths, declared acceptance and provenance. If no suitable current item exists, first use the project's official owner admission and decision process; this is a governance BLOCKED state for that work, not permission to invent `G3_L_PRODUCT_CHANGE`. No separate `plans/recovery/` authority unless the existing layout and `AGENTS.md` explicitly authorize it.
''')

between('## D9. Cutover, rollback and time-to-value controls','## E. Integrated supervisor implementation, PRE-001..015 and activation instructions', '''## D9. In-place supervisor strengthening, rollback and fast delivery

1. **Before editing**: snapshot SHA/status/open worktrees/PRs, the active `G3-W11` scope, owner items, accepted gate evidence and actual cursor; use `scripts/new_worktree.sh` as the existing authority requires. No separate mission files.
2. **Gap assessment**: run current reviewer/liveness checks, inspect `tools/reviewer/reviewer_check.py`, `reconcile.py`, role channels, reviewer procedure and lane prompts. Adopt only `foss-mcp` functions that measurably close an actual capability gap. Prefer adding independently testable guards to current supervisor over replacing it.
3. **Admit the targeted change**: where necessary, record an owner-directed mission outcome/order correction in `docs/DECISION_LOG.md` and update the minimum authoritative source(s) (`AGENTS.md` for conduct, ESM for gate order, SUPERVISION for roles, runtime for transitions). Preserve approved gate IDs, historical receipts and current work-item cursor. Change tests in same commit and stay within AGENTS/ESM line budgets.
4. **Shadow tests**: use existing G3-bound synthetic card with the original cursor read-only; test worker/supervisor scope, falsifier, result reconciliation and cold start. Deliberately fail a broken module and a mismatched cursor. Do not overwrite `project/state.yaml`; do not copy an MCP `G0`–`G5` graph into it.
5. **Activation**: only after current authority's work item accepts the modification, enable the new verification feature in its existing supervisor route (reviewer procedure/primary loop/liveness as applicable). No replacement executor, no second writer. If optional checker faults, revert its hook through a scoped reviewed commit while the original supervised service continues. Do not pause functioning issues or already-authorized deliveries simply to make governance prettier.
6. **External proof**: follow current ESM G3/G6 scope, sandbox-first and owner-approved exact target. Track actual R and L PRs separately. No blanket registry writes; no whole-portfolio reseal as a pilot prerequisite.
7. **Rollback**: deactivate only the newly added verifier/adapter, preserve existing `project/state.yaml` and all gate history, reconcile in-flight effects and never silently reverse upstream PRs. Record failure under current active item/`FAILED_INTERNAL` or typed external item per AGENTS rules.

### First response contract from the VS Code supervisor

Return the existing `project/state.yaml` gate/item plus observed source SHA, worktree/CI status, command-derived candidate counts and 44-entry registry reconciliation; current supervisor feature matrix; the exact authorized G3 work item to strengthen; changes (if any) needed in `AGENTS.md` and who authorized them; result of current reviewer/liveness preflight; first lawful next **work item** and one command; and target-side effects or precise blockers. No alternate status dashboard.
''')

between('## E-C. Bootstrap design and atomic project-state takeover','## E-D. Synthetic supervisor smoke: deliberate controls before product implementation', '''## E-C. Bootstrap **within** the pre-existing supervisor — no project-state takeover

### Step E-C1. Prove existing infrastructure before importing MCP utilities

**Mandatory inspected entry points:** `docs/SUPERVISION.md` L1–100 owns session roles, channel writers and liveness; `tools/reviewer/procedure.md` L57–126 owns current supervisor startup, checks, corrective action and lane deployment; `tools/reviewer/reviewer_check.py` L285 (`repo_checks`), L505 (`ci_state`), L544 (`behaviour_checks`), L833 (`main`) reads and enforces supervision; `tools/reviewer/reconcile.py` L128 (`reconcile`) reconciles actual candidate/project state; `project/loop-prompt.md` L48–121 owns executor orient/select/implement; `project/loop-prompt-ship.md` L1–94 is the **current** executor queue; `tests/test_governance_consistency.py` L62/104/207/430 enforces official queue/budgets/gate/registry; `tests/test_register_integrity.py` L140–153 ties reviewer defects to existing work items; `.github/workflows/liveness.yml` is already a scheduled dead-man. **Do not call these missing or replace them without testing.**

1. Read each in the existing `AGENTS.md` order, first `project/state.yaml`, then `docs/EXECUTION_STATE_MACHINE.md` G3 and active `G3-W11`, then the named ship loop. Current ESM says G3-W11 is about the accepted R candidate, bump immunity, judge/status and sandbox-proven proposal. Existing work items G3-W09/G3-W10 and the G6-G7 register matter for L and effects.
2. Run `tools/reviewer/reviewer_check.py` through the **actual documented entry point**, invoke `tools/reviewer/reconcile.py` only with its verified safe flags/inputs, inspect latest `liveness.yml` runs, and read existing `plans/<mission>/loop-status.jsonl` and `loop-instructions.jsonl` if a mission directory is active. Capture command/exit/output/current SHA. Never assume a CLI flag absent from `--help`.
3. Compare the reference `foss-mcp` source at pinned SHA to each existing primitive using a coverage matrix. `KEEP_EXISTING` whenever the current tool already provides reliable independent verification; `ADAPT_INTO_EXISTING` for explicit gaps; `PORT_SMALL_LIBRARY` only if a reproducible absence and tests justify it; `DO_NOT_PORT` for the `foss-mcp` mission graph/cursor writer and backlog.
4. Before changing session roles or taskcard structure, check whether `AGENTS.md` and `docs/SUPERVISION.md` permit it. If not, **register an owner-directed governance amendment**, with exact diff, evidence and regression tests, in the existing decision/admission workflow. The user's new direction establishes the desired behavior, but code may not treat this document as an override that already took effect.

### Step E-C2. Minimal addition policy and no new cursor

The preferred architecture is **current supervisor + an optional independently verifiable worker-admission/holdout utility**. It is **not** `ops/gatectl.py` as the new state owner. Reuse actual `foss-mcp` implementation details as bounded, test-covered helpers:

- `foss-mcp ops/gatectl.py::check_scope` L454 and `changed_paths` L373 → possible worker provenance guard in existing reviewer review/integration route.
- `foss-mcp ops/gateverify.py::run_holdout` L168 and `do_verify` L209 → optional clean-source semantic falsifier verification, independently owned by current supervisor.
- `foss-mcp ops/gatecli.py::cmd_commit_guard` L713 and `cmd_review` L895 → compare and reuse only missing guard/receipt behavior, not the MCP command's parser or gate exit writer.
- `foss-mcp ops/gatecli.py::cmd_resume_brief` L1451 → extract a read-only resumable synopsis from existing `project/state.yaml` + mission channels; no own queue.
- `foss-mcp ops/integrate.py::integrate` L146 → *pattern* for accepted commit integration; actual target's `project/loop-prompt-lane.md` and `tools/reviewer/procedure.md` remain governing.

All proposed new helpers must have an importer from the **existing approved route**. A standalone `ops/` script never called by `tools/reviewer/procedure.md` or the sanctioned executor is not a completed feature. Tests must prove both that it is invoked and that bypass/invalid behavior is refused.

**State invariant:** Existing `project/state.yaml` remains under existing authorized executor/cursor transition rules in `AGENTS.md` L47–64 and L181–208, `docs/EXECUTION_STATE_MACHINE.md` L114–168. A derived/verifier file or `foss-mcp` parser cannot rewrite this file. If a new helper produces a projected state it is **advisory verification input**, compared to source-of-truth state. Existing accepted gate evidence and current item identity survive. No new `project/recovery-state.yaml`, `plans/recovery` authority or `G0_RECON`/`G1_SUPERVISOR_READY` gate IDs.

### Step E-C3. Preflight and activation

Run all Section E-D **SV-P01–SV-P15** checks in an authorized synthetic worktree/fixture. A deliberately damaged implementation must cause the independent suite to fail, then the correct version to pass. Reproduce supervisor restart and current cursor continuity. `SV-PREFLIGHT_PASS` is **verification evidence attached to the admitted G3/current supervision work item**, not a new state-machine gate or substitute for `G3-W11`'s judge/effect acceptance.

Once the current mission's work item authorizes the change and its tests/evidence are committed, activate the adapted verifier through the **existing** `tools/reviewer/procedure.md` / primary executor path. Prefer a reversible opt-in check that can be enabled only for the first pilot; don't create a second supervisor session controlling a different queue. Preserve the running issue service and existing authorized GitHub effect jobs.
''')

# Correct preflight nomenclature global and lingering imports
src=src.replace('PRE-001','SV-P01').replace('PRE-002','SV-P02').replace('PRE-003','SV-P03').replace('PRE-004','SV-P04').replace('PRE-005','SV-P05').replace('PRE-006','SV-P06').replace('PRE-007','SV-P07').replace('PRE-008','SV-P08').replace('PRE-009','SV-P09').replace('PRE-010','SV-P10').replace('PRE-011','SV-P11').replace('PRE-012','SV-P12').replace('PRE-013','SV-P13').replace('PRE-014','SV-P14').replace('PRE-015','SV-P15')
rep('`PREFLIGHT_PASS`','`SV-PREFLIGHT_PASS`')
rep('`G3_L_PRODUCT_CHANGE`','`G3-W09 / admitted L-delta extension`')
rep('`G4_R_FULL_REGEN`','`G3-W11`')
rep('`G0` status manifest','current G3-W11 baseline evidence')
rep('`G1` preflight','supervisor work-item preflight')
rep('G1 preflight','supervisor work-item preflight')
rep('first two real PRs', 'first distinct L and R PRs')

between('### D1. Explicit supervisor/worker channel ownership','### D2. Taskcard contract (required exact fields)', '''### D1. Existing roles/channels (do not create a duplicate)

Per `docs/SUPERVISION.md` L16–78, current roles include owner, supervisor reviewer, primary executor, worktree lane agents, in-band monitors and `.github/workflows/liveness.yml`. Existing durable status/instruction channels are **per mission** under `plans/<mission>/loop-status.jsonl` and `loop-instructions.jsonl`; read their current mission selection and do not create another `ops/status.jsonl` live writer. Existing `tools/reviewer/procedure.md` is the supervisor's operational entry point; `project/loop-prompt-ship.md` is the current executor queue by `AGENTS.md` mandate.

- The **owner** authorizes changes to mission/gate/permission policy. The reviewer supervisor owns independent review, lane orchestration and evidence checks. It may propose governance changes through existing admission; it does not patch product files.
- The **primary executor** owns the current cursor and code implementation within official work-item scope, with accepted transitions recorded in the same commit. Additional worker/lane agents own only an expressly dispatched subset; they never grant acceptance or change external permissions.
- An imported `foss-mcp` helper is a **mechanical validator called from the existing authorized workflow**, never an alternate dispatch center. Its outputs are independent receipts with work-item and SHA references, not a new durable truth source.
- Existing liveness/reviewer monitors remain active. A faulty new verifier must be safely deactivated while the original cursor, channels and issue workflow remain consistent.
''')

between('### D2. Taskcard contract (required exact fields)','## E-E. GitHub deployment preflight before first external proposal', '''### D2. Bounded *subcard* specimen under an already-admitted work item

```yaml
# Example subordinate verifier input; NOT a new project/state.yaml or a mission file
parent_gate: G3_PYTHON_COHORT
parent_work_item: G3-W11
subtask: SUPERVISION-HOLDOUT
purpose: Verify an independently enforced semantic negative control in the existing supervisor
source_refs:
  - repository: babar-raza/repository-presenter
    revision: <CURRENT_VERIFIED_SHA>
    path: tools/reviewer/reviewer_check.py
    symbol: repo_checks
    sha256: <ACTUAL_HASH_AT_DISPATCH>
write_paths:
  - tests/tools/reviewer/**
  - tools/reviewer/** # only if expressly admitted into G3-W11 owned_paths
checks:
  - command: '{python} -m pytest tests/tools/reviewer -q'
    expect_exit: 0
negative_control:
  purpose: Mutate the real acceptance path so an invalid worker commit is incorrectly admitted
  expect: The independently run same suite must fail on the altered implementation
closeout:
  - The official reviewer entry point invokes the verified guard
  - A missing or stale parent work-item authorization refuses dispatch
  - project/state.yaml stays at its canonical gate/item unless its official transition is accepted
```

**Before issuing**: if `G3-W11`'s current owned paths do not include `tools/reviewer/**` or this test area, do **not** make the card write them. Obtain a reviewed owner-admitted work-item/path change under the existing ESM/cursor and validate `tests/test_governance_consistency.py` and `tests/test_register_integrity.py`. The example's check path is indicative; discover the real test path. The real card must resolve `<...>` placeholders, match the approved schema and be checkable by the current supervisor. Subcards never replace `next_ready_items` or the current item.
''')

between('## E-F. Adversarial readiness and implementation start sequence','## E-G. Strict preflight report schema and signoff example', '''## E-F. Adversarial readiness and **legal start sequence**

**Start new workers only after**: current `project/state.yaml` and authoritative queue are independently reverified; the proposed supervisor enhancement has a named and accepted **existing mission work-item scope**; the current supervisor, liveness and durable channels are demonstrably operational; scoped `SV-P01–SV-P15` controls pass including semantic mutation, negative scope, cold restart and no duplicate cursor; and the proposed worker can read its parent gate, task, permitted paths and exact current SHA.

The only permissible mission state remains one current gate/work item in `project/state.yaml`, with any transitions made through the existing actor and commit process. The project need **not** wait for replacement control-plane machinery or a new empty `ops/` tree; if original reviewer behavior passes its own tests, it may continue while independent verifiers are added. The issue reporter continues on its existing schedule.

**Existing approved supervisor startup** (run in Git Bash after verifying actual local path, interpreter and commands; exact `python` executable may be `.venv/Scripts/python.exe`):

```bash
git rev-parse --show-toplevel && git status --porcelain=v1 && git worktree list --porcelain
.venv/Scripts/python.exe -m pytest tests/test_governance_consistency.py tests/test_register_integrity.py -q
.venv/Scripts/python.exe tools/reviewer/reviewer_check.py --help
.venv/Scripts/python.exe tools/reviewer/reconcile.py --help
gh run list --workflow liveness.yml -R babar-raza/repository-presenter --limit 8
```

**`--help` does not certify actual support for these two scripts.** If the script lacks a parser or executes during flag inspection, inspect its `__main__` before invoking; record the chosen supported command. Follow `tools/reviewer/procedure.md` §0 for the actual operating startup and §2b for worktree lanes. For any new read-only utility, add `--help` and a no-side-effect `--check` mode, and test them. Do not run a copied MCP `gatectl tick` against this project unless it has been explicitly adapted, admitted and proven to leave the authoritative cursor unchanged.

**Ready for a real README effect** additionally requires the existing exact target authorization `mode: full`, valid authorization record, App installation, source-fresh candidate and write-token-only effect job; target-side remote readback. Nothing in the supervisor preflight supplies that permission.
''')

between('## G. Embedded one-paste VS Code startup prompt (standalone and complete)','## H. Evidence chain, unresolved questions, and terminal acceptance', '''## G. One-paste VS Code startup instruction — the **existing mission controls execution**

```text
YOU ARE THE REPOSITORY PRESENTER SUPERVISOR / INDEPENDENT REVIEWER. YOUR TASK IS TO RECOVER AND SHIP THE CURRENT PROJECT UNDER ITS EXISTING, UNBROKEN AUTHORITY HIERARCHY. DO NOT INVENT A NEW AUTHORITY, GATE GRAPH, MISSION OR CURSOR.

READ THIS FULL V5 SINGLE DOCUMENT AS EXTERNAL EVIDENCE AND THE OWNER'S RECOVERY GOAL. THEN FOLLOW THE REPOSITORY'S AUTHORITY ORDER, BEGINNING WITH project/state.yaml, the current gate in docs/EXECUTION_STATE_MACHINE.md, and project/loop-prompt-ship.md, AS DIRECTED BY AGENTS.md. plans/idea.md remains the outcome authority. docs/SUPERVISION.md remains the supervisor-role authority. docs/STATE_MACHINE.md remains runtime authority. README_STANDARD and README_CONTRACT retain their assigned responsibilities. GitHub source is factual evidence; it is not a competing order of command.

FIRST: RECONCILE TRUE STATE WITHOUT EDITS OR GUESSES. Inspect local and origin main commits, worktrees and unmerged work, CI/liveness, historical gates/cursor, project/status computed counts and all external PR/issue receipts. Reverify 44-entry registry and all 46 organization-visible repositories, default branch README blobs, README content patterns, JMAP move, missing GIS README and external companions. Locate the PRIVATE aspose.org readme-refresh skill and inspect actual output/provenance before proposing header changes. Label all findings as VERIFIED, HISTORICAL_ONLY, NEEDS_REPRO, or BLOCKED_EXTERNAL. Preserve readme-refresh banners/badges and bespoke/customer sections unless source-proven wrong. Assess the 37 prior F-findings in Section B and exact symbol/line map Section D; do not drop earlier analysis.

SECOND: VERIFY EXISTING SUPERVISION BEFORE IMPORTING. Inspect docs/SUPERVISION.md, tools/reviewer/procedure.md, tools/reviewer/reviewer_check.py, tools/reviewer/reconcile.py, project/loop-prompt*.md, project/lanes/, live mission JSONL channels, tests/test_governance_consistency.py, tests/test_register_integrity.py and liveness.yml. Execute safe current checks. Compare with foss-mcp ops/SUPERVISOR.md, gatectl.py, gatecli.py, gateverify.py, integrate.py, cardlint.py. Record PRESENT_PROVEN, PRESENT_BROKEN, MISSING_REQUIRED, or NOT_NEEDED_FIRST_PR. Reuse the existing supervisor wherever it already works. Introduce only minimal scoped verification/holdout/commit provenance features through its existing importer and tests. DO NOT transfer cursor-writing authority to copied gatectl or create plans/recovery or an alternative G0-G7.

THIRD: REGISTER ANY CHANGES LEGALLY. The observed cursor is G3_PYTHON_COHORT / G3-W11, with G0–G2 accepted; verify freshly. Current G3-W11 work-item scope is limited and may not authorize supervisor source changes. If needed, make an explicit owner-directed governance proposal and update the MINIMUM relevant authoritative source(s) via the existing admission/decision/CI route: AGENTS.md only for agent-conduct/hierarchy wording, docs/EXECUTION_STATE_MACHINE.md for build-order/gate acceptance and work-item registration, docs/SUPERVISION.md for supervisor mechanics, docs/STATE_MACHINE.md for runtime, and project/state.yaml only for accepted authorized cursor transitions. Preserve 210/520 line caps, existing gate IDs, accepted evidence, register integrity, authorized effect constraints, and existing loop until a correct governed amendment activates an approved replacement instruction IN THAT SAME AUTHORITY, not in a second system. This owner's dual first-class L/R objective should be codified, not silently assumed to supersede the R-primary/L-fallback 2026-10-14 owner ruling.

FOURTH: PREFLIGHT. In an isolated worktree created under the existing scripts, run SV-P01..SV-P15 from Section E. A deliberately broken real code behavior MUST fail an independent check; a correct one passes. Test scope prohibition, clean-tree replay, invalid parent/owner item, restart, role separation, cursor identity, Windows UTF-8/.venv, no secret emission, no unauthorized effect. The optional verifier must be called by the EXISTING supervisor or executor, not remain an inert new CLI. Record receipts under the approved work item; label SV-PREFLIGHT_PASS as evidence, never as a new GATE. Do not launch a separate autonomous worker queue.

FIFTH: SHIP FAST THROUGH THE EXISTING WORK ITEMS. Resume current G3-W11 judge/bump-proof/real R candidate path. Prove existing sandbox proposal wiring within its already-approved ESM/G6 route and the legal G3 dependency; do not auto-advance gates. Obtain at least one useful pre-authorized upstream correction PR as optional shared-effect smoke. Under owner-admitted existing/current or successor L work item, detect a newly introduced PUBLIC API in a previously unconsumed path, author a minimal source-grounded feature update, preserve unrelated README bytes, independently accept and deliver an actual L upstream PR. Under G3-W11, complete high-quality Lane R regeneration and deliver an actual R upstream PR. Keep issue bot operating. Then strengthen unattended independent L/R routing and source-aware no-op via existing G5/G7 items and accepted runtime rules. Do not reinterpret diagram-only changes as L semantic proof or a locally sealed bundle as an upstream effect.

SIXTH: REPORT TRUE STATE: exact gate/item from project/state.yaml; current main SHA/CI; live status/registry; verification of readme-refresh; prior F-findings and any drift; existing supervisor feature matrix; any approved authority amendments (or exact unmet owner ruling); SV preflight with test/falsifier evidence; first legal work-item implementation; verified upstream PR/issue URLs or typed exact external blockers. Continue bounded safe work; two identical failures trigger diagnosis, not another loop. Do not end at recommendations. Never change target authorization, secrets, or registry dry_run/full without the owner's exact existing rules.

YOUR NEXT ACTION IS READ-ONLY RECONCILIATION UNDER G3-W11, NOT A 'G0_RECON' STATE TRANSITION AND NOT A SUPERVISOR TAKEOVER.
```
''')

# Replace salient contradictory sentence strings throughout leftover sections.
for a,b in [
 ('only after verified supervisor cutover','only after legal current-work-item activation'),
 ('single reviewed cutover','existing authority-governed amendment'),
 ('single atomic authority cutover','reviewed, authority-preserving amendment'),
 ('at cutover','after authorized integration'),
 ('before cutover','before scoped integration'),
 ('old loop retired for dispatch','existing loop remains in force until its authority-approved amendment'),
 ('after cutover','after scoped integration'),
 ('G0 read-only verification','read-only current-work-item verification'),
 ('G0 live recon','current G3-W11 live recon'),
 ('G1 supervisor','current-work-item supervisor'),
 ('G0 baseline','current G3-W11 baseline'),
 ('G1 readiness','current-work-item supervisor readiness'),
 ('`project/state.yaml` sole writer','existing authorized executor/cursor actor'),
 ('one verified gatectl writer','one existing authorized cursor writer, gatectl check-only'),
 ('new v3','updated existing'),
 ('v3 cutover','approved in-place upgrade')
]:
    src=src.replace(a,b)

# Remove unsafe assertion from E-B map and restate the mapping table as reference in its preface
rep('Create Repository Presenter-specific `ops/SUPERVISOR.md`, pointing to v3 gates and product paths, no inherited D-drive paths','Compare with existing `docs/SUPERVISION.md` and `tools/reviewer/procedure.md`; port only missing tested behavior, without creating new active `ops/SUPERVISOR.md`')
rep('Change hardcoded `G0`–`G5` to agreed v3 gates and adjust guarded paths. Preserve **denying worker writes** to `ops/`, `plans/`, `project/`, authorization records and workflows except separately approved effect cards','Do **not** import hardcoded `G0`–`G5` or a cursor writer. Extract only scoped path guards behind the existing reviewer; preserve protected paths and official work-item ownership')
rep('Add v3 lane enum `R|L|EFFECT|ISSUES|SUPERVISOR`, protected file ownership, controller schema; versioned outcome acceptance','Compare against existing supervision/work-item typing; adopt missing schema checks under existing tests without new mission roles or gate IDs')
rep('Gate exit for v3 includes external PR readback not self-reported candidate statuses','Do not import this gate exit controller; use target current ESM predicates, augment existing evidence verifier with real PR readback')
rep('Adapt existing `project/state.yaml` schema **without adding a second authoritative state**; preserve old snapshot','Keep this MCP state rebuilder **out of production**. Read-only derived reconciliation may compare with existing schema; official current cursor never transferred')
rep('Port the minimal working dependency closure into the existing repository','Adopt only proven missing small utilities into the existing supervisor path')
rep('**Dependency closure:** inspect imports in `ops/gatectl.py`, `ops/gatecli.py`, `ops/gateverify.py`, `ops/integrate.py` and reference `ops/tests`, and port the **minimum required**','**Reference dependency inspection:** inspect imports in the MCP utility files and only selectively adapt a proven-missing helper, never their full production dependency closure')
rep('`project/state.yaml` is not in split-brain conflict: shadow until reviewed cutover; after scoped integration only adapted gatectl writes state. Old loop retired for dispatch; current product idea/safety/README standard constraints retained.',
'`project/state.yaml` remains the sole pre-existing cursor; its writer/transition procedure remains as prescribed in current `AGENTS.md`. New utilities are read-only validators with approved imports, never dispatchers or owners. The existing ship loop remains binding unless amended by the original authorities.')
rep('**Two-terminal operation after scoped integration** (the project-specific `ops/` instructions must already have been created/verified):','**Reference-only MCP two-terminal commands below are NOT executable for this repository as-is.** They must not be used; follow the existing `tools/reviewer/procedure.md` and executor/lanes. The following examples are retained as a rejected anti-pattern:')
# Ensure code fence anti-pattern clearly non-executable
rep('```bash\n.venv/Scripts/python.exe ops/gatectl.py doctor', '```text\n# NONEXECUTABLE MCP EXAMPLE — DO NOT USE AS REPOSITORY PRESENTER STARTUP\n.venv/Scripts/python.exe ops/gatectl.py doctor')
# Fix stored taskcard legacy example if anywhere outside replaced
src=src.replace('G3_L_PRODUCT_CHANGE','existing owner-admitted L item').replace('G0_RECON','read-only current-item recon').replace('G1_SUPERVISOR_READY','current-item supervisor preflight').replace('G2_FIRST_UPSTREAM_README_PR','existing G3/G6 proposal path').replace('G5_CROSS_LANE_AUTONOMY','existing G5/G7 autonomy work').replace('G6_ISSUES_PLATFORM_SCALE','existing G6/G7 issues work').replace('G7_PRODUCTION_SEAL','existing G7 production work')
# Header/titles patches
rep('## E. Integrated supervisor implementation, SV-P01..015 and activation instructions','## E. In-place supervisor improvement, SV-P01..15 and approved activation instructions')
rep('### Detailed supervisor bootstrap (v3 research integrated into V4)','### Supervisor reference research integrated as **in-place upgrades**, not controller replacement')
rep('## F. Supplemental operational contracts preserved from the earlier complete recovery review','## F. Supplemental operational contracts preserved as **design evidence under current authority**')
rep('**This is a handoff for an independent VS Code supervisor, *not a declaration', '**This is a handoff for an independent VS Code supervisor, *not a declaration')
# Add formal constitutional verification chapter in first 10 lines after intro
needle='## Navigation and precedence'
constitution='''## Constitutional audit and mandatory reconciliation before any work

**What was wrong in V4:** it proposed a replacement cursor writer and an eight-gate recovery machine. Both conflicted with the literal `AGENTS.md` prohibition on competing authority and with the existing supervisor. This V5 retains and reconciles prior evidence, but **revokes those proposed changes**, including independent `G0_RECON`, `G1_SUPERVISOR_READY`, `plans/recovery/`, a replacement `ops/` dispatcher and an atomic `project/state.yaml` takeover.

### Inspected authority—specific, pinned source references

| Authority | Verified source anchor at `repository-presenter` commit `2df2d9d8` | Invariant |
|---|---|---|
| `AGENTS.md` | [L15–46](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/AGENTS.md#L15-L46) | Reads `project/state.yaml` first, then ESM gate, then active `project/loop-prompt-ship.md`; no competing plans/state authorities |
| `AGENTS.md` | [L47–65](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/AGENTS.md#L47-L65) and [L181–208](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/AGENTS.md#L181-L208) | Worktree isolation, one shared-code item, coherent status/evidence commit, executor owns approved cursor transition, failure routing |
| `docs/EXECUTION_STATE_MACHINE.md` | [L85–168](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/docs/EXECUTION_STATE_MACHINE.md#L85-L168) | Owns sequence, current gate, status schema and G0–G7. Work-item addition/gate amendment through existing method, not handoff override |
| `docs/EXECUTION_STATE_MACHINE.md` | [L302–323](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/docs/EXECUTION_STATE_MACHINE.md#L302-L323) | Current G3 R acceptance: candidate, scoped bump proof, judge, sandbox-proven proposal path |
| `project/state.yaml` | [L5–71](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/project/state.yaml#L5-L71) | Live authority map; last observed G3/G3-W11, 29 sealed vs 0 authorizable; owned paths **do not include `tools/reviewer/`** |
| `docs/SUPERVISION.md` | [L1–78](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/docs/SUPERVISION.md#L1-L78) | Already has supervisor/primary executor/lane agents/monitors/liveness and mission JSONL channels |
| `tools/reviewer/procedure.md` | [L57–165](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/tools/reviewer/procedure.md#L57-L165) | Already has reviewer startup, correction ladder and worker lane coordination |
| `tools/reviewer/reviewer_check.py` | [L285, L505, L544, L833](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/tools/reviewer/reviewer_check.py#L285-L833) | Existing checks, CI corroboration, liveness and supervisor orchestration; upgrade demonstrated gaps only |
| `tools/reviewer/reconcile.py` | [L128](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/tools/reviewer/reconcile.py#L128-L203) | Existing candidate/evidence reconciliation; not a new queue |
| `tests/test_governance_consistency.py` | [L62–127, L207–213, L430](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/tests/test_governance_consistency.py#L62-L127) | Queue/order, 210/520-line limits, G3 predicates and registry denominator must remain green |
| `tests/test_register_integrity.py` | [L140–153](https://github.com/babar-raza/repository-presenter/blob/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c/tests/test_register_integrity.py#L140-L153) | A new/updated defect or work item must have proper register traceability |

**Two owner-direction conflicts to resolve in existing authorities, not in this document:** (1) the earlier 2026-10-14 `G3-W11`/ship loop described R as primary and `/readme-refresh` as fallback, while the new owner request requires independent first-class Lane L new-feature authoring and Lane R full regeneration; (2) any wish to change supervisor/worker write ownership must be reconciled against the already defined `docs/SUPERVISION.md` roles. The user has now explicitly directed continuity of the existing mission authority. Record this as an owner-directed decision and update only its governing documents/tests, retaining all accepted gate evidence; do not let an assistant-authored prompt pretend to supersede an earlier owner ruling without that admission.

### Mandatory authority-compatibility test before implementing any subtask

For each requested change, the supervisor must produce a recorded mapping: `desired outcome → current product authority → current gate/work-item ID → permitted owned paths → exact proposal for changed authority if any → owner decision/approval source → executable test(s) → receipt in existing evidence → cursor transition actor`. If any mapping lacks a currently admitted work item or write path, classify that implementation `AWAITING_GOVERNED_ADMISSION`; conduct read-only investigation/other permitted tasks instead. A reviewer may **propose** an amended work item; it may not create authority by renaming a file or writing a second plan. `foss-mcp` is inspected solely as a source of validation *techniques*.

---

'''
src=src.replace(needle,constitution+needle,1)
# Prevent top text wrong
rep('## Navigation and precedence','## Navigation (execution precedence is solely the repository’s AGENTS.md hierarchy)')
# Revise source section F any standalone alternate state phrasing benign? allow extra source-internals with note.
# State policy references that implicitly require new executor loops.
rep('project/state.yaml                      # THE ONE derived implementation cursor post-cutover','project/state.yaml                      # EXISTING canonical cursor; never taken over by imported utility')
rep('`project/state.yaml` sole writer','existing canonical cursor actor')
rep('## E-D. Synthetic supervisor smoke: deliberate controls before product implementation','## E-D. Synthetic independent verification controls **inside the current work item**')
# replace problematic top instruction against step count
rep('**One document. One implementation authority. Complete handoff.**','**One document. Existing authorities only. Complete handoff.**')
# Sanity
Path('C:/Users/babar/AppData/Local/Temp/mnt_data/REPOSITORY_PRESENTER_RECOVERY_V5_AUTHORITY_PRESERVING.md').write_text(src,encoding='utf-8')
print('bytes',len(src.encode()),'lines',len(src.splitlines()))