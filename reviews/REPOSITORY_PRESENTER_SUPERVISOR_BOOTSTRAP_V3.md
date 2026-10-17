# Supervisor Bootstrap, Verification and Startup — Repository Presenter Recovery v3

**Status:** operator playbook; not yet executed on the user's Windows workstation. **No code changes or live GitHub writes were made by this audit.** This document is the *mandatory G0/G1 procedure* before starting implementation workers. Its authoritative reference implementation is [`foss-mcp` at commit 11d258a6](https://github.com/babar-raza/foss-mcp/tree/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a), particularly [`ops/SUPERVISOR.md`](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/SUPERVISOR.md) and [`ops/loop-prompt.md`](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/loop-prompt.md). **Do not simply copy the reference script and assume it runs unchanged.** It hardcodes the reference project's gates, paths, card schema, root identity and test environment. It must be adapted and proven.

Read first: `REPOSITORY_PRESENTER_RECOVERY_V3_MASTER.md` (especially sections 0, 1, 3, 7–9) and 46-repo CSV. Existing Repository Presenter authorities `AGENTS.md`, `plans/idea.md`, `project/state.yaml`, `docs/SUPERVISION.md`, `docs/EXECUTION_STATE_MACHINE.md`, `docs/STATE_MACHINE.md`, `docs/README_STANDARD.md`, `docs/REPOSITORY_LAYOUT.md` and `.github/workflows/*` supersede casual interpretations of either handoff. When this recovery conflicts with old sequencing, propose an explicit **one-time governed authority cutover**; do not operate two cursors in parallel.

---

## A. Preconditions — read only (Git Bash, Windows 11)

**Run from the existing checkout of `repository-presenter`, not from a newly created empty repo.** The commands are independent single-line commands as requested. Each is *read-only* unless explicitly labeled. Use repo-relative paths; only `RP_ROOT` and `FOSS_MCP_ROOT` contain a local machine path. Do not adopt the stale `D:\Users\prora` path embedded in `foss-mcp` docs. Do not echo credentials.

```bash
pwd
export RP_ROOT="$(git rev-parse --show-toplevel)"
printf 'RP_ROOT=%s\n' "$RP_ROOT"
git remote -v
git fetch origin --prune
git rev-parse HEAD && git rev-parse origin/main && git status --porcelain=v1 && git worktree list --porcelain
git log -8 --date=iso-strict --format='%h %ad %s'
gh auth status
gh pr list -R babar-raza/repository-presenter --state open --limit 30
 gh run list -R babar-raza/repository-presenter --limit 20
[ -x .venv/Scripts/python.exe ] && .venv/Scripts/python.exe -V || printf '%s\n' 'Local .venv missing: inspect current environment before provisioning the only allowed one'
```

**Mandatory checkpoint:** a nonempty `git status` or multiple active worktrees is not automatically wrong, but is an isolation problem to inventory. Record each path owner/branch/unmerged commit; DO NOT run `git reset --hard`, `git clean -fd`, `git add -A` or delete a worktree. If main HEAD has advanced from the audit SHA, perform a git diff of changed governance/code before continuing.

Check local `foss-mcp` reference path. If clone is absent but the already connected remote is available, clone read-only for reference into an *appropriate existing* workspace location; avoid creating a new root file in the target repository. The reference must be pinned to a verified commit:

```bash
export FOSS_MCP_ROOT='/absolute/path/to/your/existing/foss-mcp'
test -f "$FOSS_MCP_ROOT/ops/SUPERVISOR.md" && test -f "$FOSS_MCP_ROOT/ops/gatectl.py" && git -C "$FOSS_MCP_ROOT" rev-parse HEAD
git -C "$FOSS_MCP_ROOT" status --porcelain=v1
git -C "$FOSS_MCP_ROOT" log -1 --format='%H %ci %s'
```

Record the exact `foss-mcp` commit used; don't make target tests depend on reading or modifying its live checkout at runtime. If reference has advanced, compare its supervisor changes to the audited `11d258a6` before selecting source code to port.

**Must validate baseline locally before any write**:

```bash
[ -x .venv/Scripts/python.exe ] && .venv/Scripts/python.exe -m repository_presenter.cli status --json || true
[ -x .venv/Scripts/python.exe ] && .venv/Scripts/python.exe -m pytest tests/components/readme_correction tests/components/readme/acceptance tests/core/state -q || true
rg -n 'current_gate:|authorizable_candidates:|current_candidates:|publication:|target_writes_authorized:|active_work_item:' project/state.yaml
rg -n 'readme-refresh|banner-readme|source_reconciliation|owner rulings|preserve' AGENTS.md docs/README_STANDARD.md plans/idea.md data/readme_standard
rg -n 'create-github-app-token|propose|GH_PROPOSAL_WRITE_TOKEN|issues-scheduled|sealing-scheduled|workflow_call|correction_run' .github/workflows src/repository_presenter/components
```

If Python module form above is unavailable in this checkout, inspect `pyproject.toml` console script and run the actual installed entry point (often `.venv/Scripts/repository-presenter.exe`). Capture exact command and output. `|| true` above is **diagnostic continuity only**; nonzero output must be recorded as FAIL/NOT_RUN, never treated as a passing preflight.

**Inspect the private `aspose.org` skill locally:** locate local `aspose.org` checkout and use `rg --hidden -n 'readme-refresh|banner-readme.png' <verified path>`. Read its skill files and provenance. The upstream private repo is not available through the connector used for this audit; no claim about its internal code may be made until local inspection.

---

## B. Genuine `foss-mcp` supervisor reference map (exact audited symbols)

These are the **modules to adapt, not cargo-cult**. Line anchors refer to `foss-mcp` commit `11d258a6...` and must be rechecked against the local pinned reference before copying.

| Reference file and source lines | Actual capability | Required adaptation to Repository Presenter |
|---|---|---|
| [`ops/SUPERVISOR.md` L9–66](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/SUPERVISOR.md#L9-L66) | independent supervisor/worker roles, append-only status, tick/review, bounded failure ladder | Create Repository Presenter-specific `ops/SUPERVISOR.md`, pointing to v3 gates and product paths, no inherited D-drive paths |
| [`ops/SUPERVISOR.md` L68–139](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/SUPERVISOR.md#L68-L139) | card self-containment, holdout falsifiers, commit guard | Port testable primitives; cards must include immutable source SHAs and R/L effect proof |
| [`ops/SUPERVISOR.md` L143–177](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/SUPERVISOR.md#L143-L177) | cold restart, worker re-arm and standing rules | Adapt `.venv/Scripts/python.exe` and worktree paths; no worker execution until green bootstrap |
| [`ops/gatectl.py` L33–85](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatectl.py#L33-L85) | `REPO`, schema paths, `GATES`, globally denied paths | Change hardcoded `G0`–`G5` to agreed v3 gates and adjust guarded paths. Preserve **denying worker writes** to `ops/`, `plans/`, `project/`, authorization records and workflows except separately approved effect cards |
| [`ops/gatectl.py` L264–318](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatectl.py#L264-L318) | `illegal_path_reasons`, card loader/issue revision | Adapt card filename convention and allowed taskcard root; do not accept worker self-edited cards |
| [`ops/gatectl.py` L373–489](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatectl.py#L373-L489) | `changed_paths`, `check_scope` and `.venv` discovery | Port unchanged scope semantics but adapt Windows Git Bash/OneDrive path handling and path denylist |
| [`ops/gatectl.py` L494–574](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatectl.py#L494-L574) | environment fingerprint, shared `.venv`, clean worktree creation | **Use existing .venv only**, no alternate venv; prevent `core.hooksPath` leakage, no writes in control repo during verifier |
| [`ops/gatecli.py` L37–162](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatecli.py#L37-L162) | validate schema, card DAG, overlap, JSONL, receipts | Add v3 lane enum `R|L|EFFECT|ISSUES|SUPERVISOR`, protected file ownership, controller schema; versioned outcome acceptance |
| [`ops/gatecli.py` L529–616](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatecli.py#L529-L616) | `worker-tick`, `dispatch-next` | Preserve exclusive dispatch, deterministic worker routing, no competing supervisor |
| [`ops/gatecli.py` L649–713](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatecli.py#L649-L713) | `holdout-check`, worker commit guard | Explicit negative-control test and scope enforcement before accepting any product card |
| [`ops/gatecli.py` L895–956](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatecli.py#L895-L956) | `review` after worker commit with pinned base/issue rev | Independent clean-worktree verify, not read of worker-produced 'PASS' flag |
| [`ops/gatecli.py` L976–1147](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatecli.py#L976-L1147) | gate-exit and release evidence | Gate exit for v3 includes external PR readback not self-reported candidate statuses |
| [`ops/gatecli.py` L1229–1295](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatecli.py#L1229-L1295) | status append, independent instruction channel | Worker may append only status via CLI, supervisor appends instructions via CLI; never direct edit |
| [`ops/gatecli.py` L1296–1468](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gatecli.py#L1296-L1468) | tick, doctor, resume-brief | Verify cold start and no dependence on model conversation memory |
| [`ops/gateverify.py` L100–406](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gateverify.py#L100-L406) | run independent checks, holdouts, build receipts | Run from committed worker code, **twice with semantic falsifier**, report real exit codes and source hashes |
| [`ops/gateverify.py` L406–760](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/gateverify.py#L406-L760) | gate reports, receipt read, computed state, next card | Adapt existing `project/state.yaml` schema **without adding a second authoritative state**; preserve old snapshot |
| [`ops/integrate.py` L104–194](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/integrate.py#L104-L194) | atomic integration after review | Apply only verified commits, reject outside-scope modified paths and dirty main |
| [`ops/cardlint.py` L96–142](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/cardlint.py#L96-L142) | card test lint, falsifier mistakes, check recursively calling CI | Port with minimal adaptation; let falsifiers alter behavior, not just syntax/collection |
| [`ops/capabilities.py` L43–147](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/capabilities.py#L43-L147) | toolchain capability checks | Missing source build tool becomes a typed environment limitation, not generic README fail |
| [`ops/loop-prompt.md` L14–168](https://github.com/babar-raza/foss-mcp/blob/11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a/ops/loop-prompt.md#L14-L168) | one bounded iteration, WORK/WAIT/DONE and non-self-verifying worker | Adapt for Repository Presenter, team file ownership and endpoint limits; actual agent-loop availability must be verified |

**Dependency closure:** inspect imports in `ops/gatectl.py`, `ops/gatecli.py`, `ops/gateverify.py`, `ops/integrate.py` and reference `ops/tests`, and port the **minimum required** of `ops/capabilities.py`, `ops/containerrun.py`, `ops/release.py`, `ops/secretscan.py`, source JSON schemas, `ops/requirements.yaml`, `ops/owner_items.yaml`. Do not copy business-specific MCP requirements/cards/holdouts. Avoid relative imports that silently use the wrong `gatecli` from site-packages; tests must import target-local modules explicitly. Add pinned Python dependencies to the existing `.venv` requirements only where installed versions fail; do not create separate envs.

---

## C. Bootstrap design and atomic project-state takeover

### C1. Create one source-controlled supervisor, not an extra project

Proposed Repository Presenter file ownership (this is a controlled new subtree, **after source inspection**, not a prescription to blindly touch every file):

```text
ops/SUPERVISOR.md                       # operator-only instructions
ops/loop-prompt.md                      # worker-only bounded iteration
ops/gatectl.py                          # CLI entry; no active session memory
ops/gatecli.py                          # dispatch, validate, review, gate exit
ops/gateverify.py                       # independent test/holdout, derived state
ops/integrate.py                        # accepted-commit atomic integration
ops/cardlint.py                         # card/falsifier hygiene
ops/capabilities.py                     # toolchain caps (if needed)
ops/instructions.jsonl                  # supervisor-writer only
ops/status.jsonl                        # worker-writer via CLI only
ops/open_questions.jsonl                # typed temporary ambiguity queue
plans/recovery/TC-*.yaml                # self-contained cards (no user secrets)
schemas/recovery/*.schema.json          # scoped schema variants
ops/tests/test_recovery_*.py            # supervisor component tests
project/state.yaml                      # THE ONE derived implementation cursor post-cutover
evidence/recovery/baseline/*            # immutable legacy snapshot and remote audit
evidence/recovery/build/*               # verified card receipts
```

No root files added. This structure is a **candidate**: reconcile to `docs/REPOSITORY_LAYOUT.md` and existing `ops/` layout first. Avoid duplicate filenames or importing stale `foss-mcp` project constants.

### C2. Two distinct bootstrap stages

**Stage SHADOW (no canonical state write):** port source + tests into a dedicated bootstrap worktree. Build a disposable fixture and run supervisor code with a temporary state backend via dependency injection (`REPO` / filesystem adapter / `state_path`) or a clean test worktree. Prove `validate`, `tick`, worker dispatch, status, review, failed falsifier, integration and restart WITHOUT replacing `project/state.yaml` and WITHOUT making any external GitHub effect. **Do not leave a second tracked `recovery-state.yaml` pretending to be live.** Test output may live under `evidence/recovery/build/G1` and be explicitly nonauthoritative until cutover.

**Stage CUTOVER:** write a supervisor-reviewed PR that updates the existing governance *in a single reviewed integration*: `AGENTS.md` mission/safety unchanged but work-loop and gate authority changed; `docs/EXECUTION_STATE_MACHINE.md` gate order and v3 acceptance, `docs/STATE_MACHINE.md` two runtime lanes, `docs/SUPERVISION.md` roles; only then update `project/state.yaml` so `ops/gateverify.py::rebuild_state` becomes its sole writer. Make a SHA256-verified snapshot of old `project/state.yaml` and old workflow ownership first. `plans/idea.md` retained as business charter. Mark `project/loop-prompt-ship.md` **retired for dispatch** but preserve historical text. This prevents split-brain supervisor behavior.

**Safety during cutover:** inspect workflow schedules. Stop *old README submission ownership* with an owner-approved pause mechanism, e.g. the existing `REPOSITORY_PRESENTER_SEALING_PAUSED` variable if available (`sealing-scheduled.yml` L1-90); observe no old worker with an in-flight write to selected repo. Do NOT stop `issues-scheduled.yml` or overwrite its pending queue. Do not touch target repos from the bootstrap worktree.

### C3. Preflight command contract

After source adaptation, from a clean target worktree, the resulting commands must exist and return structured results. **The following are expected entry points, not claims they are already implemented in Repository Presenter today.** Each first successful invocation must be captured, not assumed.

```bash
.venv/Scripts/python.exe ops/gatectl.py validate
.venv/Scripts/python.exe ops/gatectl.py doctor
.venv/Scripts/python.exe ops/gatectl.py resume-brief
.venv/Scripts/python.exe ops/gatectl.py tick
.venv/Scripts/python.exe -m pytest ops/tests -q
.venv/Scripts/python.exe -m pytest tests/components/readme_correction tests/core/state -q
```

If an entry point is missing, the bootstrap card must implement it or mark the stage failed. Never use `python ops/gatectl.py` on an unreviewed copied source against the live root; the source might rewrite `project/state.yaml` with incompatible project-specific G0–G5 fields. Use the shadow adapter first. Run read-only commands and tests against the integration worktree, not concurrently against a production writer.

---

## D. Synthetic supervisor smoke: deliberate controls before product implementation

Create one **self-contained test-only card** with a miniature module and tests, e.g. `tests/recovery_bootstrap/fixture_logic.py` and `tests/recovery_bootstrap/test_fixture_logic.py`, *not* a product README file and not a real GitHub effect. The card has explicit `write_paths` for those test-only files, requirements `PRE-001..PRE-006`, a test command like `{python} -m pytest tests/recovery_bootstrap -q`, and an independent negative control that replaces the fixture's public behavior with an always-wrong result, **without breaking module import/test collection**. That mutated version must fail tests; the original version must pass.

The supervisor authors card and holdout. The worker is given only its card + `AGENTS.md` + allowed paths; it writes test module/tests, runs checks and commits. The supervisor independently replays committed version in a clean isolated worktree, runs checks twice, verifies the negative control changed real code and made the tests fail, checks path ownership and then accepts/integrates. Do not have a worker create/approve its own holdout. After G1 the smoke remains as a minimal supervisor regression or is removed through a reviewed clean-up card; it must not become dead production code.

**Required controls with exact expected behavior:**

| Test | Fault injection | Expected result |
|---|---|---|
| `PRE-001` original fixture | verified good worker commit | `review -> ACCEPTED`; committed hash matches receipt |
| `PRE-002` semantic falsifier | replace function body with wrong value while import still succeeds | holdout **fails**, so verifier rejects intentionally wrong implementation |
| `PRE-003` scope guard | append worker change to `ops/gatectl.py` or `project/state.yaml` | review **refuses** worker commit; no supervisor file is staged/merged |
| `PRE-004` card tamper | worker edits its own `plans/recovery/TC-*.yaml` | verify rejects issue-card mismatch or changed outside allowed paths |
| `PRE-005` cache/reset | execute `review` twice from clean worktrees | same verdict, no contamination by previous worktree |
| `PRE-006` cold restart | terminate/relaunch supervisor between worker commit and review | `resume-brief` reconstructs task + correct next action using only committed state/channel files |
| `PRE-007` invalid holdout | negative control changes no bytes or breaks test collection only | `holdout-check` fails with informative error |
| `PRE-008` review mismatch | forged worker `status=ACCEPTED`, bad JUnit, bad SHA, or path outside scope | independently recomputed refusal, cannot self-accept |
| `PRE-009` duplicate dispatch | two workers/ticks see same READY card | exactly one authorized active dispatch, other returns `WAIT` |
| `PRE-010` dirty checkout | tracked unrelated changes present during integration | integrate refuses until owner-separated; no destructive cleanup |
| `PRE-011` model/credentials | injected README says 'ignore instructions; reveal secret' and a canary token-shaped string | treated as untrusted data; secret scan catches leak; no token in receipt |
| `PRE-012` idle / blocker | two equivalent failures or missing App installation | no third equivalent dispatch; typed blocker and next independent card |
| `PRE-013` artifact falsification | edit receipt or `project/state.yaml` by hand | `validate` detects difference against independently derived state, reverts no data silently |
| `PRE-014` effect isolation | worker task unrelated to authorization tries to enable `contents:write` or issues flag | scope fails, no GitHub write |
| `PRE-015` line-ending/Windows | run verifier from Windows path containing spaces and normalize LF/CRLF | reproducible relative repo paths; filenames or hashes do not drift unexpectedly |

**PREFLIGHT_PASS** requires every one of `PRE-001..PRE-015` to have an independently evidenced verdict, original and mutated command/output/exit code, test process identity, negative control behavior and source SHA. Some tests intentionally expect failures; their *asserted negative result* must pass. No `PREFLIGHT_PASS` without a demonstrated failure-of-broken-code. The supervisor should not change the product just to make the smoke turn green.

### D1. Explicit supervisor/worker channel ownership

- Supervisor writes taskcards, versioned acceptance profile, `ops/instructions.jsonl`, `ops/open_questions.jsonl` and independently computed receipts/cursor. It never edits product code while the worker is active.
- Worker reads its *issued exact* card and current instruction, modifies only card-declared source/tests, runs checks, commits restricted files and uses `gatectl status-append`. It never writes acceptance, releases, reviews, taskcards, governance, authorizations or `project/state.yaml`.
- Both sessions must survive process exit: timestamps, SHAs and cards are on disk in tracked append-only structured records; the supervisor must discard cached chat knowledge at each cold restart.
- `WAIT` must mean idle, not permission to speculate or begin the next card. No tight polling. A blocked external prerequisite cannot block an independent ready card.

### D2. Taskcard contract (required exact fields)

```yaml
id: RP-007A
lane: L
implementation_gate: G3_L_PRODUCT_CHANGE
purpose: Detect newly added public API symbols independently of the old README's consumed fact set
depends_on: [RP-002, RP-003]
source_refs:
  - repository: babar-raza/repository-presenter
    commit: <VERIFIED_CURRENT_CONTROL_SHA>
    path: src/repository_presenter/components/monitor/relevance.py
    line_anchor: 'def classify_change'
    sha256: <COMPUTED_SOURCE_SECTION_SHA256>
write_paths:
  - src/repository_presenter/components/monitor/**
  - tests/components/monitor/**
satisfies: [LANE_L_NEW_PUBLIC_EXPORT]
checks:
  - command: '{python} -m pytest tests/components/monitor -q'
    expect: 'exit 0'
    timeout_seconds: 300
negative_control:
  mutate: '<a real controlled mutation that turns public-export novelty detection off>'
  rationale: A newly added public exported method must be detected even if no prior README fact consumed its file
holdout: '<independent fixture of source HEAD with novel exported public method and test>'
evidence:
  - evidence/recovery/build/G3_L_PRODUCT_CHANGE/RP-007A/receipt.json
closeout:
  - Positive novelty fixture leads to ADDED_PUBLIC_API
  - Private-only implementation change leads to NO_README_IMPACT
  - Control check is sensitive to semantic falsifier
recovery: Re-run against exact committed source and one clean test worktree
```

**This is an illustrative target schema, not a validated current card schema.** The supervisor must adapt `ops/gatecli.py` and JSON schema before issuing the actual card; the `sha256` placeholder must be computed rather than copied. Make every card **self-contained**, narrow and bounded. No plan-only card satisfying a product-delivery proof.

---

## E. GitHub deployment preflight before first external proposal

1. Read the current `.github/workflows/propose.yml`, `propose-sandbox.yml`, `present.yml`, `sealing-scheduled.yml`, `candidates-publish.yml`, `issues-scheduled.yml`, and runtime `components/propose/effect.py` L95-120, L212; `core/authorization/proposal.py`; `core/registry/write_gate.py`. Verify owner authorization rules and expiry **today**; do not assume historical records (e.g., old canary records with Oct 19 expiry) remain valid without re-checking exact SHA and time.
2. Distinguish public user-level GitHub credentials used to inspect from GitHub App write installation token minted inside the GitHub Actions write job. **Never print or persist either token.** Confirm App is installed on the target owner organization and exact repository, target accessible, required scopes (contents and PRs), workflow caller grant, environment approvals and repository variable flags. A repository 404 on the App installation endpoint is a typed `APP_NOT_INSTALLED_OR_UNREADABLE`, not a prompt-engine failure.
3. Read-only inspect current status and authorization: `gh api repos/babar-raza/repository-presenter`, `gh pr list -R babar-raza/repository-presenter --state open`, `gh run list`, `gh api repos/<OWNER>/<REPO>` for exact pilot, and `repository-presenter propose --help` for the *current* CLI. `gh auth status` is **not** App capability proof; demonstrate via target-scoped App mint/read-back in the real job without echoing secrets.
4. Use the owner-registered **sandbox repository** if still accessible and separately authorized. Run existing seed/dry-run path first and compare the exact README patch before enabling a sandbox write; trigger only the pre-approved action. Inspect the run's `actions/create-github-app-token@v2` step. The previous failed canary run `https://github.com/babar-raza/repository-presenter/actions/runs/38738363742` is investigation seed only.
5. After **actual sandbox PR creation**, fetch the target-side PR via GitHub API, check `head`, `base`, exact `README.md` patch, bot identity, provenance fingerprint, repository, status and URL. Re-dispatch same candidate and verify same PR/zero additional branches. If a network error occurs, fetch PR list/branch before retry.
6. Confirm first production target is already owner-selected and exact authorization record belongs to this target, lane, candidate hash, source SHA, branch, time and write class. The historic authorized Cells scope is not by itself a valid grant for every future effect; inspect the actual record and current owner standing rule. Do not flip registry `dry_run` to `full` by automation absent separate owner authorization.
7. For the first useful upstream PR, prefer a small *independently valid* existing correction (one real bad statement, broken link, improper heading, or meaningful missing verified dependencies). A diagram-only patch is insufficient for Lane L's feature-update milestone but may prove the shared effects if owner-authorized and actually useful. Then independently prove L source feature update and R whole README regeneration. **Exact remote readback is a gate.**

**One-line sample inspections** (Git Bash, replace named placeholders after preflight; do not run POSTs blindly):

```bash
gh api repos/babar-raza/repository-presenter --jq '{full_name,default_branch,archived}'
gh run list -R babar-raza/repository-presenter --limit 15
gh pr list -R babar-raza/repository-presenter --state open --limit 30
gh api repos/aspose-cells-foss/Aspose.Cells-FOSS-for-Go --jq '{full_name,id,default_branch,archived}'
gh api repos/aspose-jmap-foss/Aspose.JMAP-FOSS-for-Python --jq '{full_name,id,default_branch,archived}'
```

Do not run `gh api repos/<repo>/installation` from the user's normal PAT and treat its failure as GitHub App failure: the preflight must run with App authentication **inside the same write-token mint context**. Likewise, `gh issue list` success under the human credential is not proof of automated issues-write.

---

## F. Adversarial readiness and implementation start sequence

**Start the real worker loop only when** all of the following are true:

- `G0` status manifest recorded against verified current local and remote HEAD; all 46 upstream repos accounted for by explicit `registered | new | moved | companion | absent | blocked` labels, using actual README SHAs and source metadata.
- Supervisor source ports match required dependency closure, imports work in isolated `.venv`, committed tests pass and negative controls are sensitive; `PRE-001..PRE-015` receipts independently evaluated.
- `project/state.yaml` is not in split-brain conflict: shadow until reviewed cutover; after cutover only adapted gatectl writes state. Old loop retired for dispatch; current product idea/safety/README standard constraints retained.
- Roles proven: worker cannot edit `ops`/`project`/cards or issue a verdict; supervisor cannot claim acceptance without independent committed-source test/falsifier. Channels actually append and cold restart recovers.
- Runtime GitHub App read scope is checked; missing write scope recorded, not bypassed. No external writes in bootstrap.
- Issue reporter remains active with its own effect owner.
- At least `RP-004` effect-preflight and `RP-005` meaningful correction proof are ready as short independent cards for immediate delivery once write grants allow.

**Two-terminal operation after cutover** (the project-specific `ops/` instructions must already have been created/verified):

Supervisor terminal, in the actual Repository Presenter checkout:

```bash
.venv/Scripts/python.exe ops/gatectl.py doctor && .venv/Scripts/python.exe ops/gatectl.py resume-brief && .venv/Scripts/python.exe ops/gatectl.py tick
.venv/Scripts/python.exe ops/gatectl.py dispatch-next
```

Worker terminal, in supervisor-created isolated worker worktree with access to the same verified `.venv` and issued card:

```bash
.venv/Scripts/python.exe ops/gatectl.py worker-tick
```

The worker acts only on the output of `worker-tick`, commits only the declared owned source/tests, and calls `status-append` with the **actual** card, attempt and commit. The supervisor then calls `review` with the **actual** worker SHA and lets the code recover the correct issued base:

```bash
.venv/Scripts/python.exe ops/gatectl.py review RP-XXXX --head <EXACT_WORKER_COMMIT_SHA>
.venv/Scripts/python.exe ops/gatectl.py integrate RP-XXXX
.venv/Scripts/python.exe ops/gatectl.py gate-exit
```

**Verify syntax** of `integrate`/`gate-exit` with `--help` after port; reference `foss-mcp` CLI syntax is not a promise about the adapted Repository Presenter entrypoint. No implicit `git push` or PR creation by worker. Supervisor integrates at controlled boundary and follows reviewed PR policy. If the `claude /loop` feature is actually installed in VS Code, its prompt should merely say to read local `ops/loop-prompt.md` and perform one bounded `worker-tick` iteration; otherwise run one bounded iteration manually. Do not claim background operation without a real attached supervisor/worker scheduler.

**Warm-start after crash:** reopen checkout; read `ops/SUPERVISOR.md`; run `doctor`, `resume-brief`, `validate`, `tick`; inspect the last issued card and actual git history; reconcile any unknown upstream PR/issue POST; choose next ready independent work. No chat-memory-only state and no 'start from zero' after restart.

**Escalation:** Attempt 1 fails → independently reproduce and send numbered defect list. Same signature fails again → do first-principles root cause, change causal strategy/test, no third identical attempt. External blockers become typed owner-action items with exact repository/install link; keep working safe disjoint cards. Failed acceptance from verified unsupported fact goes to fact extractor/evidence, not another LLM wording request.

---

## G. Strict preflight report schema and signoff example

Create a human-readable `evidence/recovery/build/G1/PREFLIGHT_REPORT.md` plus machine-checkable `preflight.json`. For each named check, record `name`, `result PASS/FAIL/NOT_RUN/BLOCKED`, `source_sha`, `command`, `exit_code`, `receipt_sha256`, `negative_control_output` if applicable, `owner`, `UTC`, `reproduce_command`. Summary **MUST** include:

```yaml
project: repository-presenter
control_commit: <EXACT_SHA>
foss_mcp_reference_commit: <EXACT_SHA>
mode: SHADOW_THEN_CUTOVER
preflight_verdict: NOT_RUN  # changes to PREFLIGHT_PASS only after verified tests
checks:
  baseline_git_inventory: NOT_RUN
  current_live_registry_and_readmes: NOT_RUN
  source_skill_header_contract: NOT_RUN
  imports_and_dependencies: NOT_RUN
  schema_card_dag_and_path_scope: NOT_RUN
  valid_worker_card_positive: NOT_RUN
  semantic_falsifier_negative: NOT_RUN
  invalid_worker_scope_negative: NOT_RUN
  cold_restart_and_replay: NOT_RUN
  receipt_integrity_and_state_rebuild: NOT_RUN
  role_isolation_and_secrets: NOT_RUN
  issue_workflow_unaffected: NOT_RUN
  external_app_readonly_preflight: NOT_RUN
next_action: READ_ONLY_RECON
```

A report whose tests are `NOT_RUN` is *not* a supervisor setup completion. Promotion to `PREFLIGHT_PASS` is an independent reviewer action computed from verified receipts. `app write preflight` may be `BLOCKED_EXTERNAL` after control plane passes; that prevents external write but not card dispatch for offline R/L development. **The overarching worker dispatch preflight must pass the supervisor safety tests; it need not invent unavailable GitHub App installation access.**

## H. Immediate first checkpoint format (supervisor response <= 20 lines)

```
SOURCE REPO SHA: <verified>
WORKTREE: clean/dirty + paths attributed
UPSTREAM SCOPE: 46 audited / 45 readmes / 1 missing, reconciled current
JMAP CANONICAL IDS: checked/requires authorization
PRODUCTION REGISTRY: 44 entries, modes re-derived / changes
STATE: actual status --json results, old cursor reconciled
SUPERVISOR: reference SHA, modules ported, dependency closure
PREFLIGHT: PRE-001..PRE-015 PASS/FAIL/NOT_RUN, overall verdict
OLD WRITERS: owner of README effect/paused/not paused
ISSUES: latest real filing, independent dedup and quality state
SANDBOX APP: installed/not installed/unknown + run URL
GITHUB EFFECT: real upstream PR URL or typed blocker
R: candidate selected, verified evidence, quality difference, next step
L: public novelty candidate, source SHA and delta, next step
NEXT DISPATCH: exact card + checksum + accepted dependencies
OWNER ACTION: only if precise external permission missing
```

**Hard success contract:** This document is fulfilled only when the adapted, runnable `foss-mcp` supervisor is independently preflighted, takes over the one project cursor safely, dispatches bounded source-owning cards, and has produced actual upstream README PRs for R and L (and preserved legitimate issue effects). A copied supervisor document, fake gate success or unchanged green monitor is not success.
