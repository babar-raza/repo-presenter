from pathlib import Path
import csv,re,hashlib,datetime
D=Path('C:/Users/babar/AppData/Local/Temp/mnt_data')
master=(D/'REPOSITORY_PRESENTER_RECOVERY_V3_MASTER.md').read_text(encoding='utf-8')
bootstrap=(D/'REPOSITORY_PRESENTER_SUPERVISOR_BOOTSTRAP_V3.md').read_text(encoding='utf-8')
playbook=(D/'REPOSITORY_PRESENTER_RECOVERY_SUPERVISOR_PLAYBOOK.md').read_text(encoding='utf-8')
startup=(D/'REPOSITORY_PRESENTER_START_V3.txt').read_text(encoding='utf-8')
legacy=(D/'repository_presenter_dual_lane_rebuild_v2.md').read_text(encoding='utf-8')
rows=list(csv.DictReader((D/'REPOSITORY_PRESENTER_LIVE_README_INVENTORY_2026-10-16.csv').open(encoding='utf-8-sig',newline='')))

def esc(s):return str(s).replace('|','\\|').replace('\n',' ').strip()

def section(text,begin,end=None):
 a=text.index(begin)
 b=text.index(end,a+len(begin)) if end else len(text)
 return text[a:b].rstrip()

intro='''# REPOSITORY PRESENTER — SINGLE-SOURCE RECOVERY, SUPERVISOR BOOTSTRAP & SHIPMENT CONTRACT (V4)

**One document. One implementation authority. Complete handoff.**  
**Created:** 2026-10-16 (Pakistan time). **Inputs:** live connected GitHub inspection, all prior v1–v3 findings and execution plans in this conversation, 46-repository default-branch README survey, and `foss-mcp` supervisor source inspection. **Execution target:** the user's **existing** `babar-raza/repository-presenter` VS Code checkout. **Mode:** recovery of existing implementation, **not** greenfield rebuild. **Primary outcomes:** independently verified real upstream PR from Lane L, real upstream PR from Lane R, shared effect pathway, and unattended safe repetition, while preserving the existing working issue reporter.

> **INSTRUCTIONS FOR THE VS CODE AGENT — THIS PAGE IS THE BOOT INSTRUCTION.**
>
> You are the **IMPLEMENTATION SUPERVISOR**. Read **this entire document**, including the previously discovered problems register, source/line map, complete upstream README survey, supervisor port/preflight, staged tasks, adversarial tests and final readiness rules. **Start with G0 read-only verification against your local checkout and current GitHub; never adopt old counts or this document's pinned SHAs as current without rechecking.** Then install the smallest functional `foss-mcp`-style supervisor in a shadow environment, independently prove `PRE-001`–`PRE-015`, execute a single controlled authority cutover, and dispatch bounded worker taskcards. Deliver early external PR evidence, not additional meta-plans. Do **not** ask the human to repeat known requirements, and do not stop at a plan after G0. Log one precisely defined missing external approval and continue with other safe work. Never create a target write without existing exact owner authorization.

**This v4 document is the entire handoff.** There are **no companion files needed** to understand the task. All earlier source maps, README results, actual observed baseline, supervisor setup steps, validation controls, and startup prompts have been embedded below. Existing repository-specific authorities remain legally/operationally authoritative until the **reviewed cutover**, at which point this specification is reconciled into them, never maintained as a competing permanent state machine.

## Navigation and precedence

1. **Section A:** Executive decision, delivery definition, immediate run steps, evidence confidence, and old/new authority precedence.
2. **Section B:** Complete prior-analysis traceability: every known meaningful observation, proof, failure, retention decision, or open question is tied to an implementation action.
3. **Section C:** Verified 46-repository live README survey embedded in this document; adaptive portfolio presentation contract and protected inherited sections.
4. **Section D:** The full v3 master plan: exact source locations, KEEP/ADAPT/RETIRE map, dual-lane production state machines, 12 cards, 8 gates, negative tests and production acceptance.
5. **Section E:** Entire operational `foss-mcp` supervisor bootstrap and preflight, including real source reference links, command contracts and 15 falsifiers.
6. **Section F:** Supplementary state/effect contracts and proof matrices preserved from the previous ~100 KB recovery playbook; they add operational precision to Sections D/E.
7. **Section G:** One ready-to-paste VS Code initialization directive; single-stream work and reporting.
8. **Section H:** Evidence inventory, source snapshots, unresolved issues and explicit completion checklist.

**Precedence when material conflicts appear:** current live upstream source/facts + explicit owner safety/effect approval > `plans/idea.md` product mission and prior explicit owner rulings > existing `AGENTS.md` safety and current live effect controls > this v4 **recovery execution sequencing** > older `project/loop-prompt-ship.md` and other historical implementation ladders. This is not a license for the agent to override security, owner permissions, protected README content, or legal notices. A verified conflict must be recorded with source commit and exact resolution as part of the controlled cutover; do **not** allow two concurrent active task queues.

## A. What to do first — 0 through first external result

### A1. Freeze destructive change, verify first

1. Detect repository root from the VS Code workspace. Confirm `git rev-parse --show-toplevel`; `git status --porcelain=v1`; `git worktree list --porcelain`; `git branch -vv`; `git remote -v`; `git rev-parse HEAD`; `git ls-remote origin refs/heads/main`. Preserve uncommitted human work, worktrees, branches and open PRs; **no `git reset --hard`, `git clean`, `git add -A`, force push, or arbitrary worktree deletion**.
2. Recompute current `data/registry.json`, mode split, stable GitHub identities and JMAP move; read `project/state.yaml` but **also run actual `repository-presenter status`** and verify live sealed bundle hashes/no-op/effect statuses. If command unavailable, type `UNVERIFIED`, not zero.
3. Read existing `AGENTS.md`, `plans/idea.md`, `docs/README_STANDARD.md`, `docs/README_CONTRACT.md`, `docs/EXECUTION_STATE_MACHINE.md`, `docs/STATE_MACHINE.md`, `docs/SUPERVISION.md`, `docs/REPOSITORY_LAYOUT.md`, `project/loop-prompt-ship.md`, `project/state.yaml`, and the key source files linked in Section D. Do not rewrite governance until supervisor shadow tests pass.
4. Fetch origin/source repo state and target PR/issue/workflow histories, including the failed sandbox job from run 38738363742, the Cells issue-bot outcomes and stalled control-repo PRs (#328, #317, #233, #214). Decide each PR's merge/skip based on actual diff, current HEAD and tests; do not auto-merge merely because the old loop says so.
5. Locate the private local `aspose.org` checkout, inspect the **actual** `readme-refresh` skill and its README header/badge/banner outputs; record precise path, SHA, templates, asset responsibilities and integration rules. This source could not be read remotely here; treat it as an essential **local** G0 requirement.
6. Re-read current upstream `README.md` and source facts before any modification. Section C includes **all 46 observed repositories and pinned README file hashes**; use as a change-detection baseline, not as permanent truth. Record 404 separately from processability or missing all documentation.

### A2. Recovery governance before production worker dispatch

7. Make a read-only salvage manifest for the current implementation with `KEEP`, `ADAPT`, `RETIRE_AS_ACTIVE`, `DEFER`; each row names exact current path, symbols/lines, current hash, owner, importer(s), test(s), risk and next taskcard. Use the Section D source map as seed; independently confirm all lines at **current** local SHA.
8. Port/adapt the **minimum executable `foss-mcp` supervisor dependency closure** identified in Section E into a controlled **shadow** integration worktree; retain the existing `project/state.yaml` untouched. Do not copy the old `foss-mcp` mission backlog, project ID, host paths, or outdated numerical gates.
9. Run supervisor **positive, negative, holdout, isolated clean-worktree, role/commit-scope, dirty-tree, reboot/resume and secret** preflights `PRE-001`–`PRE-015`. A worker cannot self-certify. Preserve logs and computed receipts for *every* check. If tests are not actually run, supervisor status is `PREFLIGHT_NOT_RUN`.
10. Only after shadow `PREFLIGHT_PASS`, perform **one reviewed atomic state/control cutover** into existing authority files, retire the old active dispatch ladder, make the adapted gate controller the **single** `project/state.yaml` writer. Ensure no old and new README submitter can write the same target simultaneously. Leave the working issue pipeline alive.
11. Repair and prove the shared GitHub App **sandbox** effect using the exact installation and workflow path, then submit a useful **pre-authorized production correction PR**. Distinguish permission blockers from content readiness. Never convert `dry_run` to `full` without explicit owner approval, and never use a human PAT to bypass the App/effect contract.
12. Execute Lane L semantic *new feature/API delta* PR and Lane R complete regenerated README PR independently; preserve top chrome/bespoke sections; require exact remote PR readback and independent acceptance. Move toward unattended scheduling only after both have independent proof and no old-vs-new double writers.

### A3. Hard definition of delivery

- **`L_CORRECTION_PR_OPEN`**: an actual authorized upstream PR with a useful verified correction. Proves shared effect plumbing and a correction fast path; it **does not** prove feature-driven Lane L.
- **`L_FEATURE_PR_OPEN`**: a real upstream PR that detects a source change/new previously unconsumed public capability and makes a minimal grounded README update preserving all unrelated text. **This** proves Lane L's business requirement.
- **`R_FULL_PR_OPEN`**: a real upstream PR for a missing/poor but **processable** README, publishing a complete high-quality source-grounded document while keeping verified inherited customer-specific material. **This** proves Lane R's business requirement.
- **`ISSUE_FILED`**: a real independent issue at a target repository with read-back and dedup. Existing bot output is retained; its code must not be reimplemented unnecessarily.
- **`AUTONOMOUS_L/R`**: an actual scheduled run for the relevant lane with an observed correct route/no-op/effect and restart/permission safety. Merely having Actions YAML, green CI, a sealed candidate, control-repo candidate PR, a local diff or a passing sandbox does not meet any upstream delivery contract.

**The fastest path is existing reusable code + verified narrow fixes + external receipt. No general rewrite or portfolio-wide reseal before first distinct PRs.**

'''
# traceability matrix: explicit integrate previous research
findings=[
('F01','Repo scope and status','`repository-presenter` main `2df2d9d8…` at audit; other commits may now exist','GitHub main ref/commit; local `git`','G0 verify live remote/local; pin each receipt','G0','REMOTELY_OBSERVED'),
('F02','Current cursor','`project/state.yaml` declared 29 current/sealed, zero authorizable, G3-W11; cursor is not recomputed proof','`project/state.yaml`; `core/candidates.py`','Run actual status; hash bundles; isolate failures','G0/R','CURSOR_SNAPSHOT'),
('F03','Registry policy','44 entries, 42 `dry_run`, 2 `full` (3D/Java, Cells/Java)','`data/registry.json`','Separate content readiness from exact write authorization','G0/EFFECT','SOURCE_INSPECTED'),
('F04','Actual portfolio','16 organizations; 46 product/companion repos; 45 root READMEs and GIS/.NET 404','Section C SHA inventory, GitHub search','Reconcile stable GitHub IDs, classification, protected sections','G0/R/L','REMOTELY_OBSERVED'),
('F05','JMAP moves','8 repositories observed under `aspose-jmap-foss` while registry pointed at older email org','GitHub org inventory + registry','Identity redirect/ID repair, App installation scope; no duplicates','G0/REGISTRY','SOURCE_INSPECTED'),
('F06','Unregistered/companion','PSD/Java (3-line stub) and PDF/Go-MCP (specialized README) not in registry','Section C','Classify processability/companion; no silent enrollment or writes','G0/R','REMOTELY_OBSERVED'),
('F07','Two README lanes','Lane R full generation; Lane L meaningfully changed good README; both first-class','Product mission and `readme_correction`, `run_present`','Separate trigger/state/candidate/acceptance/PR metrics','R/L','OWNER_REQUIREMENT'),
('F08','Lane R implementation','Existing extract→reconcile→plan→compose→review→repair→seal and no-op pipeline substantial but coupled','`cli.py::run_present`; `readme/*` modules','Reuse extracted facts and authored composer; wrap rather than reimplement','R','SOURCE_INSPECTED'),
('F09','Lane R 0 authorizable','29 sealed does not equal publishable and current judge/effect thresholds unmet','`project/state.yaml`, `acceptance/judge.py`','Run six-clause verdict per candidate; fix causal defects not all candidates','R','CURSOR_SNAPSHOT'),
('F10','Lane L mechanical only','`readme_correction/engine.py` deterministic, no semantic authoring','`engine.py::collect`, `run.py::produce_correction`','Retain as fast path; add novel fact delta + authoring stages','L','SOURCE_INSPECTED'),
('F11','Known omissions are report-only','`detectors/gaps.py::report_gaps` reports symbols/formats/examples without adding prose','`gaps.py` L39–148','Turn selected verified gaps into typed L authoring work, not speculative text','L','SOURCE_INSPECTED'),
('F12','Critical novelty-blind monitor','`monitor/relevance.py` consumed-path comparison can miss newly added previously-unconsumed public API file','`classify_change`, `_classify_by_blobs`, `_classify_by_trees`','Add full source/export diff inventory; independent positive and negative fixture','L','CONTROL_FLOW_RISK_NEEDS_REPRO'),
('F13','Lane L not coequal schedule','Sealing scheduler mainly invokes `present.yml` (R), even though correction CLI and propose path exist','`.github/workflows/sealing-scheduled.yml`','Add explicit scheduled L route and result; no duplicate writers','L/AUTONOMY','SOURCE_INSPECTED'),
('F14','Mixed standards drift','Oct 11 README_STANDARD owner rulings conflict with legacy README_CONTRACT code constants','`docs/README_STANDARD.md` §6.2; `composition/*`, validation','Use one stable semantic standard; scoped code correction and holdouts','R/L','SOURCE_INSPECTED'),
('F15','Version loop cost','Old 39 version bumps: 25 no consumed candidate change; 7 material; 7 not replayable','`docs/investigations/13-bump-cost-and-recheck-design.md`','Preserve content-scoped recheck; ban unrelated global reseal','R/L/SUPERVISOR','HISTORICAL_RESEARCH'),
('F16','Bump-proof implementation','`readme/bundle/recheck.py` and PR #339 scoped recheck work','recheck module, `tools/reviewer/bump_proof/*`','Keep and exercise observed real candidates; never weaken fact validity','R/L','SOURCE_INSPECTED'),
('F17','Historical corrected bundles','Oct 13 independent audit: 20 pushable, 19 fix_required, 5 no-push','`acc-corr3-summary.md`','Revalidate current bundles, pick one useful correction to prove effect','EFFECT/L','HISTORICAL_FINDING'),
('F18','Diagram-only danger','34/39 corrected bundles diagram-only; no add_dev_commands/doc_links survived historic review','`acc-corr3-summary.md`','Never claim Lane L feature update from diagram/cosmetic patch','L','HISTORICAL_FINDING'),
('F19','Sandbox App blocker','2026-10-15 failed `propose-sandbox`: App installation mint 404; write job skipped','Actions run 38738363742, job 116433368718','Inspect installation via the write-job context; preflight before expensive content work','EFFECT','REMOTE_OBSERVED'),
('F20','Issue bot actually works','Real issues in Cells C++ and TypeScript by repository-presenter[bot]','C++ #3/#5; TypeScript #3/#4','Preserve filer/scheduler; QA claims incl license-path false positives','ISSUES','REMOTE_OBSERVED'),
('F21','Protected header provenance','`readme-refresh` generated much of top title/badge/banner; current header often correct','31 linked banner rows; `aspose.org` skill still LOCAL_UNINSPECTED','Local skill audit; preserve bytes/links by default; no duplicate banner generator','R/L','USER_RULE+SURVEY'),
('F22','Protected bespoke sections','Cells, Font, PDF, Slides, Words, PSD include useful unique headers','Section C precise section names','Per-block ledger KEEP/CORRECT/ADD/SUPERSEDE with source evidence','R/L','REMOTE_OBSERVED'),
('F23','Markdown parser hazards','`#` inside code fence not H1 (3D/Python, PDF/Java); Cells/Go real outside-fence H1','Section C file offsets','Use tokenized AST for headings and protected fenced content','R/L','REMOTE_OBSERVED'),
('F24','L vs R judge differences','R six-clause whole-document judge, L before/after delta/non-loss check','`readme/acceptance/judge.py`, `readme_correction/gate.py`','Keep different acceptance contracts and independent editorial calibration','R/L','SOURCE_INSPECTED'),
('F25','No-op and effect uncertainty','Lost POST, stale HEAD, concurrent R/L and false remote effects could duplicate work','`components/propose/effect.py`, `core/noop_proof.py`','Target-effect identity, CAS+lease, remote reconcile before retry','EFFECT','RISK_TEST_REQUIRED'),
('F26','Write gate is real','42 dry-run cannot simply submit PR; readiness != permission','`registry/write_gate.py`, proposal authorizations, Actions variables','No mode flip, PAT bypass or unapproved write; typed external blocker','EFFECT','SOURCE_INSPECTED'),
('F27','foss-mcp supervisor actual source','`ops/gatectl.py`, `gatecli.py`, `gateverify.py`, `integrate.py`, cardlint, role channels','Pinned `foss-mcp` commit `11d258a…`','Port minimum dependency closure, shadow tests, independent holdout and recovery','SUPERVISOR','SOURCE_INSPECTED'),
('F28','Not yet bootstrapped','No evidence new `foss-mcp` supervisor already installed/preflighted in local Presenter','Remote inspection != local verification','Treat installation as NOT_RUN; PRE001–015 must run before dispatch','SUPERVISOR','UNVERIFIED_LOCAL'),
('F29','Single cursor and safe cutover','Old `AGENTS.md`, `project/state.yaml`, gate docs and loop conflicts if copied blindly','`AGENTS.md`, `loop-prompt-ship.md`, `foss-mcp` constants','Shadow preflight, atomic reviewed cutover to one cursor','SUPERVISOR','SOURCE_INSPECTED'),
('F30','Time-to-value hazard','Old full-portfolio acceptance/reseal ratchets consumed months without target PRs','Historical evaluator and gate snapshots','One sand PR, one real L correction, one real L feature PR, one full R PR','DELIVERY','HISTORICAL_RESULT'),
('F31','Older optimizer is oracle only','`foss-readme-optimizer` source has useful tests and adapters, not current control authority','Pinned former `main` SHA `a8a163…`','Read selectively; no control-plane migration','SOURCE','SOURCE_INSPECTED'),
('F32','GitHub control PR backlog','Control repo PRs #328 #317 #233 #214 were open at audit, requiring reconcile','GitHub PR list Oct 16','Compare current commit/status and avoid blind merge or abandonment','G0','REMOTE_OBSERVED'),
('F33','Recent CI not proof','Liveness, Monitor and CI green Oct 15-16; sandbox effect red Oct 15','Actions recent runs + sandbox job','Track scheduled transport separately from true end-to-end write','G0/AUTONOMY','REMOTE_OBSERVED'),
('F34','Initial owner selection','Previous product owner rules require first real external target be owner-selected; some old approvals have expiration','`plans/idea.md` authority notes and exact approval records','No invented authorization; blocked target does not halt offline cards','EFFECT','OWNER_POLICY'),
('F35','Runtime/worker safety','untrusted upstream README/AGENTS.md prompt injection; worker scope and tokens','`foss-mcp` roles, Presenter `AGENTS.md`','No worker secret/effect token, no unauthorized files, falsifier must reject wrong behavior','SUPERVISOR/SECURITY','REQUIRED_TEST'),
('F36','Distinct quality tests','Banner absence alone is not R trigger; headings alone not R acceptance; L formatting alone not feature result','Current READMEs & Section D states','Use robust R quality, L actual user benefit and non-loss, early pilots','QUALITY','OWNER_REQUIREMENT'),
('F37','No desktop/private proof here','Remote GitHub inspected; local `.venv`, aspose.org private skill, App write scope are not observable','External environment boundaries','Agent must collect actual local/secret-safe receipts; do not fabricate','G0/PREFLIGHT','UNVERIFIED_LOCAL'),
]
trace='''## B. All previous analyses carried forward — immutable finding-to-action ledger

**This register is the correction for the previous fragmented prompts.** Nothing here is silently removed because a later plan did not mention it. The evidence-class column prevents stale assumptions from becoming current facts. `CONTROL_FLOW_RISK_NEEDS_REPRO` is a code-level risk that requires an executable counterexample; historical reviews are research leads, not current passing bundles. At every successful card, update its associated finding in the **single** existing supervisor state/evidence system; do not add a second task spreadsheet.

| ID | Finding | Precisely known or previously observed | Evidence location | Required action / proof | Workstream | Confidence |
|---|---|---|---|---|---|---|
'''
for f in findings:
 trace+='| '+' | '.join(esc(v) for v in f)+' |\n'
trace+='''
### B1. Explicit reconciliation of earlier recommendations

- **First older high-level rebuild idea — superseded:** "start clean" or clone large portions of former optimizer. **Final decision:** controlled recovery **inside** existing `repository-presenter`, preserve live issues/App relationships; only replace isolated components after proof that reuse is unworkable.
- **Later v2 architecture — retained:** R and L are **coequal distinct products**, source fact refresh must detect *newly added previously uncited public API*, and whole-README R acceptance must not be confused with delta-scoped L acceptance. Adapt its architecture to current code; do not rebuild the repository from zero.
- **Earlier ladder — superseded:** `project/loop-prompt-ship.md` treated R as primary and L as fallback, and placed broad acceptance work before first PR. Under this owner handoff, preserve its proved technical fixes and authorizations but retire its old priority/dispatch sequence at the **single reviewed cutover**.
- **v3 findings — retained in full:** live 46-repo inspection, use of site `readme-refresh` chrome, per-section preservation, exact source/line map, JMAP move, write-mode split, missing README, and supervisor setup/preflight.
- **foss-mcp proof pattern — retained in substance, not blindly copied:** supervisor owns cards/falsifiers/acceptance, worker owns scoped code commit, `gatectl` calculates derived state, concrete semantic negative controls prove non-vacuity, restart recovery and holdouts.
- **External effect reality:** a local candidate, sealed count, green Actions run, staging PR or branch is not a verified upstream target PR. Preserve the already functioning issue bot; repair its exact defects instead of restarting that subsystem.

'''
# survey
survey='''## C. Full current-public-README portfolio survey — embedded inventory (no external CSV dependency)

**Direct inspection scope:** all listed FOSS product organizations as visible through connected GitHub on 2026-10-16; 46 product/companion repositories (excluding the organization's config-only `.github`), 45 readable root `README.md`, and one GIS/.NET `README.md` 404. **31** live READMEs had a product-linked banner and **43** had badges by the survey's heuristic; these are observed assets, **not mandatory universal gates**. This is **structural and preservation review, not proof of every claim against code**. All live names, default branches and blob SHA values must be refreshed in the VS Code checkout before selection, but the actual survey is here so no one must search chat history.

- `readme_blob_sha` is the Git **blob** SHA of the fetched root README, *not* the commit SHA; preserve that distinction. A request for `README.md` returning 404 does not prove the repository contains no other documentation or implementation.
- `Header` means product-linked banner (B) and conventional badge(s) (D). `—` means neither; never manufacture asset URLs. A non-bannner custom README can be acceptable if purposeful and truthful.
- Repo URLs link to README on the observed default branch; if missing, open the repo root and inspect the live tree. The preserved section lists are **minimum** inherited content flags, not exhaustive; an L/R ledger must inspect **every material block**, even if absent here.

| # | Repository | Branch | README blob SHA | Lines | Header | Observed inherited sections / exception | README evidence |
|---:|---|---|---|---:|---|---|---|
'''
for i,row in enumerate(rows,1):
 title=row['repo']; branch=row['default_branch']; sha=row['readme_blob_sha']; lines=row['readme_lines_observed']; hdr=''.join((['B'] if row['existing_linked_banner']=='Y' else [])+(['D'] if row['existing_badges']=='Y' else [])) or '—'; specs=row['bespoke_sections_to_preserve'] or row['observation_or_recheck'] or 'Standard family/platform structure; inspect full content'; url=row['readme_url']
 survey+=f'| {i} | `{esc(title)}` | `{esc(branch)}` | `{esc(sha)}` | {esc(lines)} | {hdr} | {esc(specs)} | [live]({url}) |\n'
survey+='''
### C1. Common presentation pattern — **semantic archetype, never blind normalized rewrite**

An appropriate **complete** README for a processable library generally helps the user find: product title and verified distribution badges; the already-correct site-managed banner (when present); clear audience/problem statement; key capabilities and limits; installation with truthful package coordinates; runtime/dependencies; runnable minimal quick start; source-backed examples; appropriate API guide/reference; relevant documentation/support; known unsupported scope; development/testing; license and notices. At a Glance/Navigation can strengthen an otherwise incomplete README, but **absence alone is never proof Lane R should wipe out a good README**. Only generate a banner after the branding source authorizes it and the source asset exists; never assume all 46 need a banner.

**Inherited content policy:** Build a block-level ledger with `KEEP_EXACT`, `UPDATE_FACT`, `ADD_VERIFIED`, `SUPERSEDE_WITH_TRACEABLE_REPLACEMENT`, or `REMOVE_FALSE_UNSAFE` (requiring exact grounds and independent review). Protect customized sections including:

- Cells/Python's alternate compact **Features**, **Supported formats**, **Scope** and **Examples and API** headings; do not declare it substandard solely because headings differ.
- Cells/Java/Rust/Go **Project Structure**; Go **Detailed Documentation** and **Constraints**.
- Font/Python's **Three Buyer Workflows**, **Who Is This For?**, **Variable Font** workflows/discovery, **CLI Highlights**, **CLI Usage**, and **MCP Server**.
- PDF/Go's **Feature Showcase** and **Third-Party Notices**; PDF/C++'s **Project Structure** and **Third-Party Notices**; PDF Go MCP's specialized tools/configuration; never reclassify as a generic library without proof.
- PSD/.NET's **Who This Project Is For**, **Common Workflows**, **Mental Model**, **Choosing Between...**, **Samples**, **Supported Scope**, **Out of Scope**.
- Slides/.NET **What it cannot do**, **Choosing an edition**, **Security** and **Contributing**; Slides/Java's **Choosing an Edition**.
- Words/.NET's **The story behind this code**, **What's not included**, **Enjoying it? Star it**, **Contributing**. Preserve maintainers' voice and history where not contradicted by verified facts.
- All legal/license/security warnings, build/publish instructions, compat caveats, contributor/community sections even when not in survey's shorthand.

**Validation must operate on parsed CommonMark/Markdown tokens.** `#` inside fenced code is a code comment, not a heading. E.g. 3D/Python `README.md` lines 227–230 are inside a code fence, not second H1 headings; PDF/Java lines 1651–1667 are shell commands/comments, not H1 headings; Font/Python CLI inline comments are not headings. Cells/Go at line 105 instead has a genuine outside-fence H1-style line beginning `# Requires`, worth targeted correction. A README rewrite deleting examples to satisfy a naive regex is an unacceptable regression.

**Style governance:** `docs/README_STANDARD.md` and the source's owner decisions are the controlling shape contract after reconciliation. Examples do not dictate false product facts. Top title/badges/banner from `aspose.org`'s `readme-refresh` are **preserved by default**; inspect the private skill on the local machine, including its exact path/module/version, rendered examples, linkage and ownership. Do not manufacture source coordinates for the uninspected private repository. **For R, inherited blocks remain part of the full-document contract; for L, unrelated bytes remain unchanged.**

'''
# transform v3 master remove inaccurate companion line (and old top title), keep substantive beginning as source doc in part D
master=master.replace('**Companion files (same folder as this document):** `REPOSITORY_PRESENTER_SUPERVISOR_BOOTSTRAP_V3.md` is the detailed supervisor installation/preflight checklist; `REPOSITORY_PRESENTER_LIVE_README_INVENTORY_2026-10-16.csv` is the complete, 46-row upstream inspection inventory, including 45 readable READMEs and one confirmed absent `README.md`; `REPOSITORY_PRESENTER_START_V3.txt` is the VS Code startup instruction. The repository itself MUST contain only project-approved copies of these after reconciliation, not several competing plans.', '**All referenced companion material is embedded in Sections C and E/G of this V4 file. This document must be reconciled into project-approved existing authorities after verified supervisor cutover; it must not remain a competing runtime controller.**')
master=master.replace('**Execution authority:** This is a handoff for an independent VS Code supervisor,', '**Section D preserves the full previously audited v3 master specification.** This is a handoff for an independent VS Code supervisor,')
# change relative mentions to internal sections
master=master.replace('instructions in companion bootstrap','instructions in Section E').replace('See CSV manifest for 46 names', 'See Section C for 46 names').replace('in companion bootstrap', 'in Section E').replace('section in companion bootstrap','Section E')
master=master.replace('## 0. Mandatory operator instruction', '## D0. Mandatory operator instruction')
# append as original ## headers nested to not violate automated heading
master=re.sub(r'^## ([1-9][0-9]*)\.',lambda m:f'## D{m.group(1)}.',master,flags=re.M)
# E as full
bootstrap=bootstrap.replace('## A. Preconditions','## E-A. Preconditions').replace('## B. Genuine','## E-B. Genuine').replace('## C. Bootstrap','## E-C. Bootstrap').replace('## D. Synthetic','## E-D. Synthetic').replace('## E. GitHub','## E-E. GitHub').replace('## F. Adversarial','## E-F. Adversarial').replace('## G. Strict','## E-G. Strict').replace('## H. Immediate','## E-H. Immediate')
bootstrap=bootstrap.replace('See the master', 'See Section D').replace('companion master','Section D').replace('companion startup','Section G').replace('companion inventory','Section C')
# pull substantial unique excerpts from v1 playbook after chosen headers, skip initial numbers as they repeat active
supp='''## F. Supplemental operational contracts preserved from the earlier complete recovery review

**Purpose:** The previous 100 KB recovery playbook contained operational details not always visible in architectural summaries. The following sections are preserved in substance here. **In case of duplicate sequencing or terminology, Sections A/D/E are authoritative**. Section F provides more detailed acceptance and effect schemas, retries, diagnostics and examples; historical labels are not new active state machines.

'''
for a,b,label in [
('### 4.2 Effect transaction contract','### 4.3 Distinct evidence','Effect transaction detail'),
('### 4.3 Distinct evidence','### 4.4 Permission','Separate effect proof levels'),
('### 4.4 Permission','### 4.5 Handling','Permission/effect matrix'),
('### 5.2 Minimum reusable','### 5.3 Minimal','Supervisor minimum capabilities'),
('### 5.3 Minimal taskcard','### 5.4 Supervisor state','Taskcard detailed fields'),
('### 5.4 Supervisor state','### 5.5 Worktree','Single-state distinction'),
('### 5.5 Worktree','## 6. Recovery','Worker/worktree ownership'),
('### 7.1 Loop detection','### 7.2 Content','Retry anti-loop'),
('### 7.2 Content','### 7.3 No-go','Scoped invalidation'),
('### 7.3 No-go','### 7.4 Watchdog','No-go workload'),
('### 7.4 Watchdog','### 7.5 PR','Novelty/no-op watchdog'),
('### 7.5 PR','## 8. Negative','PR quality/spam controls'),
('## 8. Negative controls','## 9. Proposed typed','Historical adversarial test matrix'),
('## 9. Proposed typed','## 10. Operating','Typed runtime data contracts'),
('## 10. Operating','## 11. Recovery','Operating model and output metrics')]:
 try:
  s=section(playbook,a,b)
  supp+=f'### F. {label}\n\n'+s+'\n\n'
 except Exception as e:supp+=f'<!-- Missing section {a}: {e} -->\n'
# do not dump old 40kb verbatim; ensure unique original insights as a summarized source excerpt, not conflicting later
legacy_summary='''## H. Evidence chain, unresolved questions, and terminal acceptance

### H1. Historical analyses preserved by this single-source handoff

| Prior evidence | Material conclusions retained here | Resolution in this document |
|---|---|---|
| Initial rebuild execution spec (earlier first pass, 29 KB) | component salvage, upstream delivery, fact verification, affected-section patching | Reuse decision and delivery order in Sections A, B, D; **its original L-as-fallback priority is superseded** |
| Independent dual-lane v2 audit (40 KB) | R full generation; L changes; monitor misses newly unconsumed public export; 44 registry, 42 dry-run; 29 current/0 authorizable; version-bump analysis; 20/19/5 L audit; GitHub App sandbox 404; issue effects | Findings B01–B37 and deep source/action map in Section D; all first-class |
| v3 master (65 KB) | 46 live repo inventory, bespoke sections, branding skill, exact refs, JMAP migration, 12 cards, eight recovery gates, 44 adversarial tests | Entire plan embedded in Section D, full survey in Section C |
| `foss-mcp` supervisor bootstrap (35 KB) | exact reference code, shadow/cutover, 15 preflight failures, tested two-terminal workflow | Full bootstrap in Section E |
| Detailed recovery playbook (~100 KB) | 4-plane architecture, taskcard/effect formats, safeguards, acceptance, anti-loop, external reports | Preserved unique detail in Section F; no separate file needed |
| Prior ready-to-paste startup prompt | explicit three-stage instruction, owned write policies, upstream receipts | Embedded verbatim in Section G |

### H2. Known current-source pointers and important dates

- [Repository Presenter main at inspected revision](https://github.com/babar-raza/repository-presenter/tree/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c); [foss-mcp reference at inspected revision](https://github.com/babar-raza/foss-mcp/tree/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a); [former optimizer at inspected revision](https://github.com/babar-raza/foss-readme-optimizer/tree/a8a163f7e9a7beeac1d2ef8b7c02e8e4bd5a7815).
- [Failed GitHub App sandbox installation token mint on October 15](https://github.com/babar-raza/repository-presenter/actions/runs/38738363742): job `116433368718`; write/proposal skipped. This is a **known first diagnostic**, not proof every installation is missing.
- [Independent remote issues in Cells C++ #3](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/issues/3) and [#5](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/issues/5); [Cells TypeScript #3](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript/issues/3) and [#4](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript/issues/4), filed by `repository-presenter[bot]` on October 15. These four URLs were checked explicitly; other older reports said eight-plus, so **recompute the total instead of repeating an unverified aggregate**. License-in-subdirectory complaints require a separate false-positive check before closing/duplicating anything.
- At audit time main had four open control-repo PRs: [#328](https://github.com/babar-raza/repository-presenter/pull/328), [#317](https://github.com/babar-raza/repository-presenter/pull/317), [#233](https://github.com/babar-raza/repository-presenter/pull/233), [#214](https://github.com/babar-raza/repository-presenter/pull/214). Their mergeability at execution time is unverified and must be refreshed.
- On October 15/16 the latest observed [Liveness run 38831066578](https://github.com/babar-raza/repository-presenter/actions/runs/38831066578), [Monitor run 38810055322](https://github.com/babar-raza/repository-presenter/actions/runs/38810055322) and [CI run 38748858884](https://github.com/babar-raza/repository-presenter/actions/runs/38748858884) succeeded, but those statuses are **not** evidence of actual upstream README publishing.

### H3. Hard blockers that MUST be typed rather than guessed away

1. **Read-only external facts can be stale:** re-pin current repo and README SHA, changed source files, candidate inputs and registry before authorizing any write.
2. **Private `aspose.org` skill content unavailable to this remote audit:** local inspection and cited skill file/module is mandatory; no pretending otherwise.
3. **Windows checkout may have dirty worktrees or `.venv` path drift:** inspect before tools or supervisor control-plane writes; don't discard.
4. **`foss-mcp` source is a reference, not a drop-in binary:** its hardcoded paths, G0–G5 and schemas cannot be copied into Presenter or allowed to mutate canonical `project/state.yaml` until shadow verifier proves correctness.
5. **App installation and owner approval are separate:** do not use user-level `gh` success as proof the App can mint write token; no unauthorized dry-run promotion.
6. **R and L both need independent true upstream outcomes:** effect-spine correction alone satisfies neither semantic L nor full R milestone.
7. **`readme-refresh` top chrome and bespoke sections survive:** no banner generator, arbitrary layout uniformity, blanket rewrite or removal of material customer text without source evidence.
8. **Issue lifecycle is live production functionality:** no disabling/deleting issue workflows to simplify README recovery.

### H4. Final acceptance — all predicates must be independently proven

- **G0** local + remote audit complete, reconciled, hashes/sources linked; open/prior evidence explicitly categorized; all 46 GitHub repos accounted for.
- **G1** functional `foss-mcp`-derived supervisor shadow preflight truly passes `PRE-001`–`PRE-015`, independent holdout and falsifier; single cursor cutover checked; restart and role separation verified.
- **Effect spine** sandbox App installation/context preflight; real sandbox PR with remote readback and repeat dispatch dedup; production write only under exact owner authorization. Missing external permission is `BLOCKED_EXTERNAL` not a fabricated pass.
- **L** a real upstream `L_FEATURE_PR_OPEN` documents an added/changed public capability even from previously-unconsumed file, plus independent validation, preserved README assets/sections and rerun no-op.
- **R** real upstream `R_FULL_PR_OPEN` from poor/missing but processable repository: source-grounded complete README, protected-content ledger, improved quality, distinct authorization and rerun no-op.
- **Autonomy** real scheduled monitors for each lane, full source-delta novelty, typed exception and effect receipt, no double-writers; issue reporter functioning; no stale-revision edit, no duplicate PR, no model call on unchanged input.
- **Evidence** real target-side URLs, hashes, source revisions, test/falsifier receipts, GitHub run URLs and blocked conditions in one reported state. Green control-repo CI alone is never enough.

**No assertion of deployment:** As of writing this single-source document, the source code, repo state and some real issues were remotely observed, but the **local supervisor has not been installed or tested** by this assistant, and no GitHub write has been performed by it. The VS Code agent must execute all steps against its accessible local checkout.
'''
# actual doc
out=intro+trace+survey+'\n\n---\n\n## D. Integrated master design and exact code/file/line map (v3 evidence retained)\n\n'+master+'\n\n---\n\n## E. Integrated supervisor implementation, PRE-001..015 and activation instructions\n\n'+bootstrap+'\n\n---\n\n'+supp+'\n\n---\n\n## G. Embedded one-paste VS Code startup prompt (standalone and complete)\n\nThis prompt is embedded to eliminate the need for a separate startup artifact. **Use the exact document itself as the source; the prompt is only its entry point.**\n\n```text\n'+startup.strip()+'\n```\n\n---\n\n'+legacy_summary+'\n'
out=out.replace('## C. Full current-public-README portfolio survey', '## C. Full current-public-README portfolio survey')
path=D/'REPOSITORY_PRESENTER_RECOVERY_V4_SINGLE_SOURCE_EXECUTION.md'
path.write_text(out,encoding='utf-8')
print(path,'bytes=',path.stat().st_size,'lines=',out.count('\n')+1,'words=',len(out.split()),'SHA256=',hashlib.sha256(out.encode()).hexdigest())
print('counts',{k:out.count(k) for k in ['F01','F12','F21','PRE-001','PRE-015','README_STANDARD.md','readme-refresh','PREFLIGHT_PASS','readme_correction','run_present','L_FEATURE_PR_OPEN','R_FULL_PR_OPEN']})