# GitHub App delivery and the issue system: inventory, TeX Python assessment, gaps, work plan (2026-11-22)

Scope: owner feedback R50 (BL-721, BL-722, BL-723). Read-only investigation at `origin/main` c9de0c94. No push, no PR,
no workflow dispatch, no write to any upstream repository or issue. Limits of the evidence are stated where they bind
(section 0).

## 0. Evidence limits

- The session's GitHub proxy refuses the REST API (`gh api`, `curl api.github.com`, the issues HTML page) for
  `aspose-tex-foss/Aspose.TeX-FOSS-for-Python` and the 3D TypeScript repository ("GitHub access to this repository is
  not enabled for this session"); `add_repo` was denied by the permission classifier. So **the live issue list of TeX
  Python could not be fetched here**; section 3 is built from `git ls-remote` / shallow `git fetch` of the public code
  (allowed), the old project's committed records, and this repository's state refs. Row T0 below must be re-run by a
  worker with API read access (WP-9) before the verdict on "issues already logged upstream" is final.
- Hosted run ids quoted are those recorded in the state refs and decision log; they were not re-fetched.

## 1. README candidate delivery through the App (BL-721)

### 1.1 What exists in code
| Piece | Where | State |
|---|---|---|
| Gated PR effect for upstream repositories | `src/repo_presenter/propose/effect.py` (`propose_candidate`), `propose/pull_request.py` (title and body composition), `propose/portfolio_gate.py` (R15 gate) | Ported 2026-10-23 from the old project; **no caller anywhere** (`grep propose_candidate` finds only docstrings, tests and `TC-009b.yaml`). Its own docstring says "never armed". |
| Gates in that effect | registry write permit (`mode: full`), kill switch `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED`, independent review ACCEPT, acceptance contract (R33) `PUBLISHABLE_STATES`, `GH_PROPOSAL_WRITE_TOKEN`, committed authorization record (`authorization/proposal.py`), installation-token provenance, source-freshness recheck, PR-history check, App attribution of the PR (`verify_pull_request_app`) | Built and unit-tested with injected fakes; never exercised live. |
| Control-repository publish (candidates tree PR on this repo, not upstream) | `src/repo_presenter/candidates_publish/effect.py` | Same status: no workflow calls it. |
| App token provenance | `src/repo_presenter/github/token_provenance.py` (`EXPECTED_APP_ID = 5092474`, slug `repository-presenter`) | Real; the legacy PR `Aspose.Cells-FOSS-for-Cpp#7` is authored by `repository-presenter[bot]` (decision log 2026-10-24). |

### 1.2 Workflows
Present in this repository: `present.yml` (facts and present, no write credential), `recertify.yml`, `issues.yml`,
`mint-app-token.yml` (reusable, `workflow_call` only, **no caller**), `tc-009a-mint-proof.yml`, `acceptance-write.yml`,
`audit-*.yml`, `cohort-chain.yml`, `run-request*.yml`, `supervisor-tick.yml`, `gitlab-mirror.yml`, `ci.yml`.
**There is no `propose`/`publish`/`pr` workflow.** The old project had four that matter, all in
`babar-raza/repository-presenter/.github/workflows/`: `propose.yml` (read-only dry run job, then a write job that mints
a one-repository App token with contents:write, pull-requests:write, metadata:read and exposes it to exactly one step as
`GH_PROPOSAL_WRITE_TOKEN`), `propose-sandbox.yml` (the sandbox canary), `candidates-publish.yml` (candidates tree PR on
the control repository) and `verify-app-installation.yml` / `audit-app-installations.yml`.

### 1.3 Credentials and wiring (names only)
- Secrets on this repository: `GH_APP_ID`, `GH_APP_PRIVATE_KEY` (added by the owner 2026-11-06, run 42170741214 failed
  on their absence, run 42200695015 minted). Consumed by `actions/create-github-app-token@v2` in `mint-app-token.yml`,
  `tc-009a-mint-proof.yml` and `issues.yml` only.
- Variables (kill switches, never authorisation): `REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED` (issues, **not set**: every
  recorded cycle lists it as a live blocker), `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` and
  `REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED` (no production wiring). Name mismatch to remember: the old project
  used `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED`; this repository's issues code reads `REPO_PRESENTER_ISSUES_WRITE_AUTHORIZED`.
- Token env names: `GH_APP_INSTALLATION_TOKEN` (issues), `GH_PROPOSAL_WRITE_TOKEN`, `GH_CANDIDATES_WRITE_TOKEN`.

### 1.4 Allowlist (`data/upstream_write_allowlist.json`)
Nine repositories, effect `pull_request` only, `first_pr_as_draft: true` (Cells Rust, Email .NET, Imaging .NET owner-listed
2026-11-06; 3D Java, Cells .NET, Cells C++ and three more by R22 on 2026-11-09). **TeX Python is not allowlisted** and is
`mode: dry_run`, `issues_mode: null` in `data/registry.json`. R22 allowlists nine of 40 active repositories; delivering
all candidates upstream needs the list (and registry `mode`) widened by the owner, and CI enforces that the two agree.

### 1.5 Proof status
| Claim | Status | Evidence |
|---|---|---|
| App identity can mint a token from a hosted run | PROVEN (read-only) | TC-009a, run 42200695015, `evidence/build/GATE2_INTEGRATIONS/TC-009a/mint_proof.json` |
| App can create a branch and draft PR upstream | PROVEN IN THE OLD PROJECT ONLY | `Cells-FOSS-for-Cpp#7`, Cells Java PR; old `propose.yml` runs |
| R17 sandbox proof in this repository | **NOT DONE** | BL-028 blocked: "no sandbox entry in allowlist or registry; no sandbox binding in `propose/`"; owner action 5 (sandbox with the App installed) outstanding. Old sandbox was `babar-raza/presenter-sandbox` (D6/OWNER-11, canary seed PR #334 open and unmerged at last record) |
| `propose_candidate` against a real target | NEVER RUN | TC-009b AWAITING_OWNER_DECISION (BL-029) |
| Hosted run that opens a PR from a sealed candidate | NONE | no workflow |
| R15 gate in code | designed, not landed | `docs/wip/r15-portfolio-gate.patch`; `propose/portfolio_gate.py` exists |

### 1.6 The old project's P3/P4 model (`docs/DECISION_LOG.md` 2026-10-24, `migration/reuse-manifest.yaml`)
Approval-gated: a PR needs a committed authorization record binding repository, candidate hash, source revision, base and
presenter branch and a window of at most 7 days, merged to main before the run's trigger commit; the write job mints a
repository-scoped installation token inside the job; the PR is verified to be authored by the App. Reuse-manifest status:
`core/github/{client,token_provenance}`, `issues/{dedup,file}` ADAPTED and present; the "five-gate" stack
(registry write gate, per-handoff approval store) was PORTED later (`issues/approval.py`, `authorization/*`); the
`propose` effect ported but the workflows (`propose.yml`, `propose-sandbox.yml`, `candidates-publish.yml`) were **not**
reused, which is the central delivery gap.

## 2. Issue creation and management through the App (BL-722)

### 2.1 Code (`src/repo_presenter/issues/`, 5,000+ lines with tests in `tests/issues/`)
`discovery.py` (facts to handoffs), `dedup.py` (fingerprint marker), `file.py` (plan and file, five gates, ambiguous-create
reconciliation), `approval.py` (committed per-handoff approval record), `track.py` (occurrence ledger), `close.py`
(redetect, close with evidence, remote gates), `reproduce.py` (sandboxed re-run of a recorded reproduction),
`monitor.py` (import App issues, re-verify, decide CLOSE / dated COMMENT / REOPEN, act, record cycle), `pilot.py`.

### 2.2 Workflow `issues.yml` (daily 06:41 UTC, also `workflow_call` from `run-request-execute.yml` job `issues`)
Two jobs with a trust boundary: `reproduce` (clones the pilot repository, runs each recorded reproduction, no secret, read
token) and `maintain` (mints the App token scoped to the pilot repository with `issues: write`, validates observations as
hostile input, decides, writes only if `mode: live`, a dry-run cycle exists, the kill switch is 1 and the token verifies,
records the cycle on `refs/repository-presenter-state/issues/<owner>__<name>`).

### 2.3 Evidence (state ref `refs/repository-presenter-state/issues/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript`)
- 9 recorded cycles, 2026-11-13 (run 43473020251-1) to 2026-11-21, **all `dry_run`, `live_cycles = 0`**, all `checks: ok`.
- Five issues #4 to #8 imported and fingerprinted (obj format detection, Transform setter, FBX save/open, adm-zip
  production dependency, STL export vertices) with committed reproductions in
  `data/issue_reproductions/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript.json`. All five `STILL_REPRODUCES` at
  `66cb26df3b03`, which is still the upstream head today (`git ls-remote`, 2026-11-22), so no fix has ever been
  available to exercise the CLOSE path.
- Decisions planned: NONE for days 1 to 6, `COMMENT_STILL_REPRODUCES` from 2026-11-19 (interval logic works), never
  performed because the pilot is dry run. Live blockers recorded every cycle: pilot `mode: dry_run` in
  `data/issue_pilot.json`, kill switch not set.
- The five issues were filed by the old project's `issues-scheduled.yml` through the App (`repository-presenter[bot]`),
  gated by approvals in `ops/issue_approvals/` (10 TypeScript approvals exist there; five are live issues).

### 2.4 Data files
| File | Role |
|---|---|
| `data/issue_pilot.json` | pilot repositories, effects `issue`, `issue_comment`, mode `dry_run`, comment intervals 7 and 30 days |
| `data/issue_reproductions/<repo>.json` | recorded reproduction per issue (script, reproduces_if_any, resolved_if_all, pinned revision) |
| `/home/user/babar-raza/repository-presenter/evidence/upstream-defects/<repo>/<fp>.json` | 52 old handoffs (51 `HANDOFF_PENDING`, 1 `FILED` on the old control repo). Filed state is not committed back (dedup is by the marker in the live issue body), so `HANDOFF_PENDING` does not mean unfiled |
| old `ops/issue_approvals/*.json`, `ops/issue_close_approvals/` | owner approvals (<= 30 days) to file, separate record to close |
| old `evidence/upstream-defects/reverification.json` | per handoff verdict CONFIRMED / NOT_A_DEFECT with live head |

### 2.5 Lifecycle completeness (open, update, verify fixed, close)
| Step | Code | Hosted proof | Gap |
|---|---|---|---|
| Discover a defect from facts | `discovery.py` | none | only emits from fact kinds the registry knows; no workflow runs it; old project found its 15 by manual harvest |
| File (open) | `file.py` | old project only (#4-8) | **no workflow in this repository files**; pilot file says "creating an issue is never granted"; R22 forbids issue filing outside R39 pilot; `plan_pending_handoffs.py` is read-only |
| Dedup | `dedup.py`, marker | yes (import dedup in 9 cycles) | marker prefix of old and new both parsed: fine |
| Update (dated re-check comment) | `monitor.decide` | planned only (dry run) | never posted |
| Verify fixed | `reproduce.py` + `redetect` | STILL_REPRODUCES observed 9 times; **VERIFIED_RESOLVED never observed on a real fix** | needs a reproduction for a defect that was fixed (TeX, section 3) |
| Close with evidence | `close.py`, `monitor.decide` | none | pilot not live; closing requires `issue` effect and App token with issues:write |
| Reopen on regression | `monitor.decide`, tests | none | unexercised |
| Unverifiable issues | recorded, never auto-closed | n/a | any issue without a reproduction (all repositories except 3D TypeScript) is invisible to maintenance |
| Scope | pilot = 1 repository | | R39 says widening is the owner's call; owner feedback now asks "all issues" |

## 3. TeX Python as the end-to-end test (BL-723)

### 3.1 Facts established
| # | Item | Result | Evidence |
|---|---|---|---|
| T1 | Defect found by the old project: indentation collapsed, 102 of 119 `.py` files fail `ast.parse` at `181015d` (35 of 45 under `src/aspose_tex`), `import aspose_tex` fails at `_input/catcode.py:66` | Reproduced today from the local clone `/home/user/upstream/Aspose.TeX-FOSS-for-Python` at `181015d`: **102 of 119** | old handoff `c00f9615...`, status `HANDOFF_PENDING`, source revision `181015d` |
| T2 | Logged upstream by the App identity? | **No evidence it was ever filed.** Approved by the owner 2026-10-16 (`approved_at` 2026-10-16T11:28Z, expiry 2026-11-15, now expired), but the registry entry was `dry_run` with no `issues_mode: file`; the old scheduled job's own table says "none: no open issue in the repository ... registry (dry_run: needs issues_mode file)" (the old `issue-approval-table-final.md` row `c00f9615`). This repository's decision log 2026-10-31 decision 7 and calibration iteration 4 also say "No issue was filed". Live confirmation pending (section 0). | |
| T3 | Fixed upstream since? | **Yes.** Upstream `main` is now `07db3203` (`26.11.1`, 2026-11-09; tags `26.11`, `26.11.1`; refs/pull/1/head = the README PR). Shallow fetch: at `de943bc` (`26.11`, 2026-11-06) and at `07db3203` **0 of 248** `.py` files fail `ast.parse` (the repository was re-released with correct indentation, 378 files changed). Package import was not executed here (running upstream code was refused by the sandbox classifier). | `git ls-remote`, shallow fetch to scratch, `ast.parse` only |
| T4 | Our pinned revision | The extractor and backlog items BL-620/640/641/670 already cite pinned `07db3203` for TeX Python, i.e. this system's facts are from the fixed tree and Lane R work on TeX Python is no longer blocked by the parse defect (the open TeX Lane R blockers are BC-17 status badge and BC-05 license, README-pipeline issues, not upstream defects) | `project/backlog.yaml`, decision log 2026-11-21/22 |
| T5 | Would the system now close or comment it? | **It would do nothing at all.** TeX Python is not in `data/issue_pilot.json`, has no `data/issue_reproductions/` file, no issue was ever filed or imported, `issues_mode` is null. Had the issue been filed and a reproduction (`ast.parse` over `**/*.py`, resolved when 0 failures) been recorded, `redetect` would have returned VERIFIED_RESOLVED at `07db3203` and `decide` would CLOSE (completed) with the revision and output digest, provided the pilot were `live` | `issues/monitor.py` logic, `issues.yml` |
| T6 | Other defects of TeX Python in our records | Only one upstream defect (the parse breakage). Other TeX records are our own pipeline failures (BC-17/BC-05, BL-620/641/670/640), per R36 not upstream issues. The owner's remark that "problems logged in issues upstream" were solved since refers to issues in the upstream tracker (including any filed by people other than this system); those could not be listed here (section 0) | |
| T0 | Upstream tracker contents (issue numbers, authors, state, timelines) | **UNKNOWN: API refused** | WP-9 |

### 3.2 Verdict on the issue system, end to end
The **mechanics are sound and well gated** (dedup by fingerprint, two-job trust boundary, hostile-input validation,
decide/act/record, idempotent comment markers), and the **re-verification half works on a real defect class** (nine
hosted cycles, all `checks: ok`). But the system **does not yet work end to end**: (1) it has never performed a single
upstream write (0 live cycles, kill switch unset, pilot `dry_run`); (2) nothing in this repository can file an issue, so
the first stage of the lifecycle depends on the old project and on a manual owner approval commit; (3) the only monitored
defects are five that remain unfixed, so the close path has no live evidence; (4) TeX Python demonstrates the structural
miss: a real, owner-approved, reproducible defect sat as `HANDOFF_PENDING` because of a `dry_run` registry entry, was
fixed upstream on 2026-11-06, and the system never logged, commented on or closed it, and would not now. A defect that is
found, approved and fixed with no trace upstream is the failure to remove. Grade for the owner's question "how well does
the issue system work": monitoring 6/10 (works, narrow), lifecycle as a whole 2/10 (not live, no filing, no
generalisation).

## 4. Ranked gaps
1. **G1 (P0) No delivery workflow.** No hosted path creates a branch and draft PR from a sealed candidate through the App;
   `propose_candidate` has no caller; the old `propose.yml` was not carried over. Blocks R50(2).
2. **G2 (P0) No R17 sandbox proof** (BL-028): no sandbox repository bound, App install on it outstanding (owner action 5).
3. **G3 (P0) Issue maintenance is dry run only**: `mode: dry_run`, kill switch unset, 0 live cycles; no comment, close
   or reopen was ever posted.
4. **G4 (P0) No filing path in this repository**: nothing opens issues (R22/R7 gating, approval record per handoff, no
   workflow); the defect-to-issue stage depends on manual old-project action.
5. **G5 (P1) Pilot of one repository, reproduction coverage of one**: all other repositories (including TeX Python)
   cannot be monitored or closed; generalised reproductions (parse check, install check, example failure, build failure)
   exist only as five hand-written TypeScript scripts.
6. **G6 (P1) Allowlist covers 9 of 40**; TeX Python and 30 more are neither allowlisted nor `mode: full`.
7. **G7 (P1) Close path never exercised on a real fix** (TypeScript upstream head unchanged since 2026-10-16); TeX Python
   is the ready test case.
8. **G8 (P2) Naming/duplicated governance**: kill-switch variable differs from the old project's; the issue state lives on
   state refs, not committed handoffs, so status is invisible to `gatecli`/backlog; TC-009b and TC-010a stay
   AWAITING_OWNER_DECISION with a premise (live PRs) that R15/R17 forbid.
9. **G9 (P2) Verification of the App's PR authorship and token reach never run in this repository** (`verify_pull_request_app`
   unexercised).

## 5. Parallel work plan (R50(5): all independent packages start at once)
| WP | Work | Acceptance | Evidence | Depends |
|---|---|---|---|---|
| WP-1 (G1) | Add `propose.yml` (adapt the old file): read-only dry-run job, write job minting a one-repository App token (contents:write, pull-requests:write, metadata:read), calling `propose_candidate`; inputs fixed, trigger by `run-request-execute`; R15 portfolio gate enforced inside the job (nothing upstream before every candidate of both lanes passes) | workflow lint/CI test pins: no secret in dry-run job, token only in the gated step; dry run on a sealed candidate prints the PR title, body and refusals, zero writes | hosted dry-run run id; `tests/test_propose_workflow.py` | none |
| WP-2 (G2) | Sandbox: owner supplies (or approves `babar-raza/repo-presenter` itself per BL-028) a repository with the App installed; add a sandbox registry bound to `provider_identity.repository_id`; port `propose-sandbox.yml` | draft PR created by `repository-presenter[bot]` from a hosted run, a second run refused as duplicate, App scope verified via API | two run ids, PR URL, `verify_pull_request_app` result | WP-1 (workflow), owner action 5 |
| WP-3 (G3) | Issues pilot goes live on 3D TypeScript: set `mode: live` and the kill switch (owner/R39 authority exists), confirm the App installation has issues:write on the pilot repository | one posted dated re-check comment by the App (`COMMENT_STILL_REPRODUCES`), visible via `gh api`, replay posts nothing twice | run id; the issue-comment URL | owner sets variable |
| WP-4 (G4) | Filing job in `issues.yml` (or `issues-file.yml`): discover handoffs, require approval record (`ops/issue_approvals/`), dedup by marker, file through the App with caps; restricted to the pilot list until widened | on a sandbox repository: open, dedup refusal on rerun, label set; no filing without approval | run ids on the sandbox | WP-2 sandbox |
| WP-5 (G5/G7) | TeX Python reproduction: `ast.parse` over `**/*.py` at the revision, `resolved_if_output_empty`; add TeX to `issue_pilot.json` in `dry_run`; import the old handoff `c00f9615` (rebuilt from `evidence/upstream-defects`) as a recorded defect | dry-run cycle on TeX reports VERIFIED_RESOLVED at `07db3203` and the planned CLOSE with revision and digest evidence | state ref record; unit test from the real 102/119 and 0/248 shapes | none |
| WP-6 (G5) | Generic reproduction classes for the old 15 confirmed defects (parse, install, build, example) in `data/issue_reproductions/` | every pilot issue verifiable; unverifiable list reported | counts per repository | WP-5 |
| WP-7 (G6) | Owner decision list: widen allowlist and registry `mode` to all candidate repositories (PRs only, draft first) and the issue pilot beyond 3D TypeScript | CI test "allowlist equals registry full set" passes for the widened set | allowlist diff | owner |
| WP-8 (G8) | Reconcile kill switch names, add issue state summary into the backlog/state report, re-author TC-009b/TC-010a to the non-mutating proof (R17) | `gatecli validate` shows both cards re-authored | gatecli output | WP-2, WP-3 |
| WP-9 | Re-run T0 with API read access: list and classify every issue of `aspose-tex-foss/Aspose.TeX-FOSS-for-Python` (author, state, fixed-since) and of the 3D TypeScript repository (comments by the App) | per-issue table in this document | `gh api` output, run id if hosted | API read access |

Deadline note (R49, today): WP-3 (an owner variable plus a mode flip) and WP-5/WP-1 dry-run workflows are achievable
today; live PRs (WP-2 onward) wait on the owner sandbox and, per R15, on every candidate of both lanes passing.
