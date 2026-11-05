# Legacy write-capable effect inventory and proposed disposition — 2026-11-04

Resolves R2 of the 2026-11-04 pre-execution correction directive. **This supersedes the "newly
discovered" framing in `docs/STATUS_ASSESSMENT_AND_RECOVERY_PLAN_2026-11-04.md` §3.1/§4: the
risk itself was already raised and explicitly left open on 2026-10-24** (`docs/DECISION_LOG.md`,
heading "2026-10-24: The old repo's P3/P4... is real, live production — not just documented..."),
quoting its own closing line verbatim: *"Whether to let it keep running unattended or pause it
first is an operational decision for the owner, not an engineering one — not decided or acted on
in this entry."* Nothing below is new risk; it is the same still-open risk, re-inspected with
sharper, more current evidence, and corrected on one material point.

## Correction to this session's own earlier framing (twice now)

`docs/STATUS_ASSESSMENT_AND_RECOVERY_PLAN_2026-11-04.md` characterized the legacy repo as "a
live, currently-active second writer." The first correction pass (same day) called this
overstated and claimed "dormant-but-armed... authorization environment variable is unset" —
**that correction was itself wrong, in the risky direction, and is now corrected again** against
real evidence an independent check caught (the owner's follow-up directive, confirmed directly
via `gh api repos/babar-raza/repository-presenter/actions/jobs/125885584935` and its logs, not
accepted on the directive's own say-so):

- The repository-level kill switch, `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED`
  (a committed Actions **variable**, not an unset secret), has been `"1"` since 2026-10-15 —
  **globally armed**, not unset.
- Per-job eligibility is gated differently: each of the 22 "File and close `<repo>` (owner-gated
  write)" jobs in a given `issues-scheduled.yml` run only executes its real-write steps
  (`actions/create-github-app-token@v2` minting a repo-scoped `issues: write` token, then filing/
  closing) if that specific repository has at least one **committed approval-record file** for an
  eligible defect, and fewer than 5 currently-open issues (a per-repo cap). In the 2026-11-03 run
  (41626576391), checked across all 22 jobs: 2 of 22 (3D-TypeScript, Tex-Python) had real,
  non-skipped write steps; the other 20 (including the Cells-Cpp job this session sampled first,
  which is where the wrong "unset" conclusion came from) correctly skipped because *that specific
  repository* had zero eligible approval records that day — not because the switch was off.
- **Net real external effect of that entire run, grepped directly across all 22 write jobs: zero**
  — `filed=True` never appears, no issue was closed, no comment was posted. The two armed jobs
  found only already-filed issues (#4–#8, correctly not re-filed) or hit "no approval record" /
  "open-issue cap reached: 5 of 5" on every other candidate.

**Correct characterization, now: globally armed, per-repository-gated, zero real external
effects in the most recently inspected run.** The actual risk is sharper than "dormant": **a
human committing one new approval-record file for any of the 36 registered repositories is
sufficient, with no other step, to cause a real external GitHub write on the next scheduled
run** — there is no separate re-arming action required. `project/taskcards/TC-002.yaml`'s risk
classification is corrected accordingly.

## Per-workflow classification (from each file's own `permissions:` block, read directly)

| Workflow | Classification | Evidence |
|---|---|---|
| `verify-app-installation.yml` | READ-ONLY | `contents: read` only |
| `monitor.yml` | READ-ONLY | `contents: read`, own comment: "makes no repository write, opens no PR" |
| `liveness.yml` | READ-ONLY | `contents: read`, `pull-requests: read` |
| `issues-scheduled.yml` | WRITE-CAPABLE, **globally armed since 2026-10-15, per-repo gated** | repo-level kill switch `REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED` = `"1"`; each per-repo job mints `issues: write` and files/closes for real if that repo has a committed approval record and is under its 5-open-issue cap — 2 of 22 jobs did so for real on 2026-11-03, with zero net filings/closes that day |
| `propose.yml` | WRITE-CAPABLE, **not currently scheduled** | gated job mints `contents: write` + `pull-requests: write`; has not run at all (manual-only) since 2026-10-19 |
| `candidates-publish.yml` | WRITE-CAPABLE, **scoped to the control repo only** | writes into this control repo's own `candidates/<slug>/` tree, not an external upstream repo |
| `sealing-scheduled.yml` | Orchestrator, read-only ambient token | calls the three above as reusable workflows; last run only executed its read-only planning job |
| `candidates-publish.yml`, `verify-app-installation.yml`, `monitor.yml`, `liveness.yml`, `sealing-scheduled.yml`, `issues-scheduled.yml`, `propose.yml`, `propose-sandbox.yml`, `ci.yml`, `audit-app-installations.yml`, `mirror-gitlab.yml`, `present.yml` | (full set, 12 workflows, all `state: active`) | `gh api repos/babar-raza/repository-presenter/actions/workflows` |

## Real external effects found (not inferred)

- **Open bot-authored PRs: two**, not one as earlier audits cited — `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp#7` (previously known) and `aspose-cells-foss/Aspose.Cells-FOSS-for-Java#7` (newly surfaced this pass, same "At a Glance diagram" style change). Zero closed or merged bot PRs anywhere across the nine target orgs checked.
- **Open issues**: `aspose-3d-foss/Aspose.3D-FOSS-for-Python#4`, confirmed `OPEN`, zero comments.
- The Nov-03 independent audit's funnel claim (PENDING 40 / APPROVED 11 / FILED 1 / RESOLVED 0) was **not independently re-verified line-by-line this pass** — flagged `UNVERIFIED`, a lead for whoever picks up TC-002's remaining work.

## Proposed disposition (per writer/effect) — awaiting owner approval, not yet decided

| Writer/effect | Proposed disposition | Why |
|---|---|---|
| `issues-scheduled.yml` (legacy) | **Keep scheduled, keep the kill switch at its current value**, until TC-010 (this repo's own issues lifecycle) is ready to take over as the single owner | It is globally armed, not dormant -- flipping it off is itself a write to someone else's governance surface without authorization; the safer action is to not add new approval-record commits for repos this new system is also working on, not to touch the switch |
| `propose.yml` (legacy) | **Keep as-is (manual, dormant)** | Not scheduled; zero recent activity; lowest risk of the write-capable set |
| `candidates-publish.yml` (legacy) | **Keep as-is** | Scoped to the control repo only, not an external upstream surface |
| `monitor.yml` / `liveness.yml` / `verify-app-installation.yml` / `audit-app-installations.yml` (legacy) | **Keep running** | Read-only; genuinely just observability |
| `mirror-gitlab.yml` (legacy) | **Flag for the owner specifically** | Directly relevant to the standing exit plan (eventual full GitHub+GitLab overwrite of `repository-presenter`) — the owner should know this mirror is still live before that cutover is planned in detail |
| This repository's own future App-token/publishing work (TC-009, TC-011) | **Blocked on this table's owner sign-off** | Building a second write path to the same upstream App installation before an explicit single-owner-per-effect decision would recreate exactly the dual-writer risk this inventory exists to prevent |

**No disposition above has been owner-approved.** This table is a proposal with a recommended
default per row, not a decision — per the directive's own instruction (§9.J): identify the exact
scope of the needed decision and a safe default, rather than asking for blanket approval. The
safe default, if the owner takes no other action, is "keep everything exactly as-is" (preserves
the status quo, changes nothing about the legacy system — do not flip
`REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED`, do not commit new approval-record files for the
legacy system on this project's behalf), **except** that no new work proceeds on the *live-write*
steps of TC-009/TC-011 (isolated implementation, mock-token testing, dry-run planning, and local
validation are explicitly NOT gated by this, per the directive's §6) until this table is
explicitly signed off, because that is the one row where silence would be unsafe rather than
merely cautious.

**Owner decision (2026-11-05): the proposed table above is approved as written** — see
`docs/DECISION_LOG.md`, entry "2026-11-05: owner rules on TC-002, TC-004, ...", item 1. It approves the
dispositions only; it authorizes no specific upstream write.

OWNER_APPROVED_WRITER_DISPOSITION: 2026-11-05 ref=OWNER-DECISIONS-2026-11-05-TC002
