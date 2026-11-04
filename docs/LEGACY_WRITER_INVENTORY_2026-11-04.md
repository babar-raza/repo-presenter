# Legacy write-capable effect inventory and proposed disposition — 2026-11-04

Resolves R2 of the 2026-11-04 pre-execution correction directive. **This supersedes the "newly
discovered" framing in `docs/STATUS_ASSESSMENT_AND_RECOVERY_PLAN_2026-11-04.md` §3.1/§4: the
risk itself was already raised and explicitly left open on 2026-10-24** (`docs/DECISION_LOG.md`,
heading "2026-10-24: The old repo's P3/P4... is real, live production — not just documented..."),
quoting its own closing line verbatim: *"Whether to let it keep running unattended or pause it
first is an operational decision for the owner, not an engineering one — not decided or acted on
in this entry."* Nothing below is new risk; it is the same still-open risk, re-inspected with
sharper, more current evidence, and corrected on one material point.

## Correction to this session's own earlier framing

`docs/STATUS_ASSESSMENT_AND_RECOVERY_PLAN_2026-11-04.md` characterized the legacy repo as "a
live, currently-active second writer." A deeper, job-level inspection (this pass) shows that
framing overstated the present danger: the write-capable steps inside the legacy scheduled
workflows are real and armed, but currently **fail-closed** — their authorization environment
variable is unset, so the most recent `issues-scheduled.yml` run (2026-11-03T11:19:27Z) shows
every real-write step ("Mint an issues-write token," "File approved handoffs," "Close approved
issues," "Update filed issues") with `conclusion: "skipped"`; only the read-only counting step
ran. `sealing-scheduled.yml`'s most recent run shows the same pattern — only its read-only
"Plan this run" job executed. **Correct characterization: dormant-but-armed, not actively
writing.** The operational risk is that someone could set that authorization secret without this
repository's knowledge, not that writes are happening right now.

## Per-workflow classification (from each file's own `permissions:` block, read directly)

| Workflow | Classification | Evidence |
|---|---|---|
| `verify-app-installation.yml` | READ-ONLY | `contents: read` only |
| `monitor.yml` | READ-ONLY | `contents: read`, own comment: "makes no repository write, opens no PR" |
| `liveness.yml` | READ-ONLY | `contents: read`, `pull-requests: read` |
| `issues-scheduled.yml` | WRITE-CAPABLE, **currently gated closed** | gated step mints `issues: write`; last real run skipped every write step (authorization env var unset) |
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
| `issues-scheduled.yml` (legacy) | **Keep scheduled, keep gated closed**, until TC-010 (this repo's own issues lifecycle) is ready to take over as the single owner | Already fail-closed; no urgency to touch it; touching it without authorization would itself be an unauthorized write to someone else's governance surface |
| `propose.yml` (legacy) | **Keep as-is (manual, dormant)** | Not scheduled; zero recent activity; lowest risk of the write-capable set |
| `candidates-publish.yml` (legacy) | **Keep as-is** | Scoped to the control repo only, not an external upstream surface |
| `monitor.yml` / `liveness.yml` / `verify-app-installation.yml` / `audit-app-installations.yml` (legacy) | **Keep running** | Read-only; genuinely just observability |
| `mirror-gitlab.yml` (legacy) | **Flag for the owner specifically** | Directly relevant to the standing exit plan (eventual full GitHub+GitLab overwrite of `repository-presenter`) — the owner should know this mirror is still live before that cutover is planned in detail |
| This repository's own future App-token/publishing work (TC-009, TC-011) | **Blocked on this table's owner sign-off** | Building a second write path to the same upstream App installation before an explicit single-owner-per-effect decision would recreate exactly the dual-writer risk this inventory exists to prevent |

**No disposition above has been owner-approved.** This table is a proposal with a recommended
default per row, not a decision — per the directive's own instruction (§9.J): identify the exact
scope of the needed decision and a safe default, rather than asking for blanket approval. The
safe default, if the owner takes no other action, is the "Keep ... as-is / gated closed" rows
above (preserves the status quo, changes nothing about the legacy system), **except** that no new
work proceeds on TC-009/TC-011 until this table is explicitly signed off, because that is the one
row where silence would be unsafe rather than merely cautious.

<!-- OWNER_APPROVED_WRITER_DISPOSITION marker intentionally absent: this has not happened yet. -->
