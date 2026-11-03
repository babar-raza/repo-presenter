# Mission Authority — Repository Presenter (new repository)

This file is the single normative product+operating authority for this repository,
distilled 2026-10-21 per `plans/repository_presenter_fresh_start_supervisor_prompt.md`
("the mission document"). It does not duplicate that document; it resolves which
source governs when two documents disagree, and extracts the still-valid outcome
requirements from the old repository's `plans/idea.md`.

## Corrective plan (owner-adopted 2026-11-03) — read before anything else in this file

`docs/AUDIT_2026-11-01_FIRST_PRINCIPLES_EVALUATION.md` is owner-adopted binding authority. It
evaluated this project against eight explicit goals the owner stated directly (G1/G2: Lane L and
Lane R production, 25+ independently accepted candidates each; G3: an operational issues module;
G4: candidate publishing, with `cells/net` and `3d/python` as mandatory integration tests; G5:
GitHub App integration; G6: autonomous Docker + GitHub Actions production execution; G7: parity
with, and non-duplication of, aspose.org's own refresh-candidate skill; G8: deliver without
repeating the two trashed predecessor projects' failure modes) and found, with direct code-level
and `gh api` evidence, that G3, G4, G5, and the autonomy half of G6 exist only as real but
never-exercised library code — nothing calls them. **Amended 2026-11-03 (same day) after an
external, independently-verified counter-review (audit §K): a wired caller alone would still face
an uncalibrated-reviewer gate and a `dry_run` registry-mode gate on one of the two G4-mandatory
targets; a third never-called publish mechanism exists; real Actions history shows a ~14% success
rate; and a `run_cascade.py` exit-code defect masks a failed seal as success.** This file's own
"Authority order" below still governs *what the product must do*; the audit governs *what must
concretely get fixed before any of that counts as delivered*, and its corrective plan (§I) is
tracked as ten live cards in `project/state.yaml`'s `next_ready_items` (`AUDIT_2026_11_01_ITEM_1`
through `_10`). Do not treat the audit as read once and closed — it stays open until every one of
those ten cards is marked `DONE` by the same independent-verification discipline (not
self-reported) this project already applies to every other acceptance.

Numeric note for anyone tempted to quote an old figure: this file's history and `project/
state.yaml`'s own history contain at least three *other* "how many accepted candidates is enough"
numbers (20/36, 28+, "all 36 both lanes") from earlier, now-superseded framings. The audit's own
25+ target is the current one. `project/state.yaml`'s `progress.counters_status` block is the
place to find the real, reproducible current count (`python scripts/portfolio_status.py`) — not
any number quoted in prose anywhere, including this file.

## Exit plan: this repository is a temporary salvage/rebuild workspace (owner instruction, 2026-11-01)

The end state the owner wants is **one** maintained repository, named
`repository-presenter`, hosted on both GitHub and GitLab. This repository
(`repo-presenter`, the "new repository" this file otherwise refers to) is not
that end state — it is a temporary workspace whose job is to salvage every
usable component from the old `repository-presenter` repo and rebuild the
rest from scratch, under this file's own authority and the predecessor
failure modes recorded below ("Do not repeat the predecessor projects'
mistakes"). Once this repository is ready (judged against the mission's own
non-negotiables, the portfolio objective in `AGENTS.md` non-negotiable #8,
and the owner's own review — never a pipeline's own green state, per that
section's lesson 5), the live `repository-presenter` repo on GitHub and
GitLab is to be **completely and promptly overwritten** with this
repository's content, retiring the old one outright rather than merging or
reconciling histories.

**This is a future, owner-triggered action, not a standing instruction to act
now.** Nothing in the current taskcard/branch/merge workflow should attempt
or prepare the overwrite itself (no force-push to the old repo, no history
rewrite, no GitLab remote configuration) until the owner explicitly says this
repository is ready and gives the go-ahead — consistent with the Git Safety
Protocol's bar for destructive, hard-to-reverse, cross-repository actions.
What it does change now: "done" for this whole effort is not "this repo's own
tests pass" — it is "this repo is good enough to become the one
`repository-presenter` repo everyone uses," which is the portfolio-wide,
forest-level framing non-negotiable #8 already states, now with its own
concrete exit criterion.

## Authority order (binding, highest first)

1. **`plans/repository_presenter_fresh_start_supervisor_prompt.md`** (the mission
   document) — the owner's current binding instruction set. Its 8 non-negotiables
   (§1), its lane definitions (§6–7), its invalidation contract (§8), and its
   priority ladder (§12, P0–P4) govern over anything below when they conflict.
2. **Old repo `plans/idea.md`** (`E:\Users\prora\OneDrive\Documents\GitHub\repository-presenter\plans\idea.md`,
   read in full 2026-10-21, including its embedded 2026-09-02 authority note and
   2026-10-11 owner-correction table) — the underlying human product-requirements
   source for *what a good README looks like* and *what the system must do*. Still
   binding wherever the mission document does not override it.
3. **This file (`docs/MISSION_AUTHORITY.md`)** — the distillation of (1) and (2)
   into one compact, queryable requirement catalog for this repository. Derived,
   not independently authoritative; if it drifts from (1) or (2), (1)/(2) win and
   this file is corrected.

Everything from the old `repository-presenter` repo not named above —
`AGENTS.md`, `docs/EXECUTION_STATE_MACHINE.md`, `docs/STATE_MACHINE.md`,
`docs/README_STANDARD.md`, `project/state.yaml`, its task queue (`G3-W11`..`W19`),
`ops/`, decision log, investigations — is **forensic evidence and a salvage
source only** (mission §1, §3), never a controlling authority here. Its own
`AGENTS.md` even says as much about its *own* predecessor (`foss-readme-optimizer`);
the same relationship now applies one level down, from that repo to this one.

## Critical fact this authority must not lose (found 2026-10-21, see `docs/history-reconstruction.md`)

On **2026-10-20** — one day before the mission document's own latest cited anchor
(PR #350/#348) — the owner personally reviewed the old repo's Lane L candidates and
ruled, verbatim: *"Lane L is also broken like Lane R, so it is not a deliverable...
I am sure when I review them manually, I will find more problems."* The recorded
investigation found, across 34 Lane L bundles: 71/366 example facts CONTRADICTED,
8 contradicted links + 80 unresolved, 30 missing-API findings across 19
repositories, and undetected false format claims (3D-.NET advertises formats its
own `IOService.cs` rejects). The old repo's live `authorizable_candidates` count is
**0 of 36**, despite Gates G0–G2 accepted and 28 candidates sealed.

This does not contradict the mission document's non-negotiable #2 (both lanes
equal, neither disposable) — that is an architectural requirement about what the
*new* system must support, not a claim that the old lanes currently work. It does
mean: **the old repo's validator/judge/reviewer chain has a demonstrated,
owner-confirmed blind spot** (it graded candidates ready that were not). Mission
§3's warning — "any system whose validation or reviewer shares the same causal
blind spot as its producer" must be re-evaluated before reuse — applies squarely
to `readme/review/independent/review.py`, `readme/acceptance/judge.py`, and the
BC-04/BC-14 validators. No component from that chain may be pulled with a `REUSE`
disposition in `migration/reuse-manifest.yaml`; at most `ADAPT` or `FIXTURE_ONLY`,
and only behind an independent re-verification this repo builds itself.

## Do not repeat the predecessor projects' mistakes (owner instruction, 2026-11-01)

This repository is the **third** iteration: `babar-raza/foss-readme-optimizer` →
the old `repository-presenter` repo (trashed) → this repo. Both predecessors
were trashed, not merely superseded, and the owner's explicit instruction is
that this project must not get stuck in the same kind of loop, or repeat the
same mistakes, as either of them. The concrete, independently re-verified
failure modes from the immediate predecessor (`docs/history-reconstruction.md`,
2026-10-21) are the operative lessons; `foss-readme-optimizer`'s own specific
failure modes have not yet been independently inspected from this repo and must
not be assumed beyond what `migration/reuse-manifest.yaml` already states about
it (a transitive, not-yet-inspected salvage source) — do not fabricate detail
for it that isn't independently confirmed.

From the old `repository-presenter` repo, confirmed directly against its own
evidence, not trusted from its own framing of itself:

1. **Self-grading hid 27 of 30 sealed reviews' real defects.** An overbroad
   demotion rule folded `REJECT` to `ACCEPT` whenever a finding's quoted span
   matched a literal SUPPORTED fact value, conflating "this phrase is factually
   correct" with "this finding has no merit" — hiding a dropped security
   warning and a false API claim among others. This is exactly non-negotiable
   #5 above (no agent/harness/reviewer may silently grade or overrule its own
   negative finding); it was violated at scale, silently, for over a month.
2. **A fix landed, but nothing already sealed was ever re-checked against it.**
   The acceptance-integrity bug was fixed 2026-10-10; the 28 candidates sealed
   before that fix were never independently re-verified against the fixed
   logic — the project kept treating them as valid output regardless. A fix
   is not complete until its effect on already-produced state is checked, not
   just its effect on new output going forward.
3. **An elaborate plan was authored, then abandoned after step one.** The
   "Lane R dependability rebuild" (8 cards C1–C8, 9 metrics, floors) only ever
   executed card C1; C2 through C8 never ran. Planning depth is not progress;
   a plan this repository adopts must be tracked to actual completion or
   explicitly abandoned with a reason, never left to quietly stall.
4. **Scope was narrowed quietly, then the narrowing was confirmed broken
   anyway.** Lane L was internally demoted to non-primary on 2026-10-14, six
   days *before* the owner's own in-person review concluded Lane L "is also
   broken like Lane R, so it is not a deliverable." Silently lowering the bar
   on a lane does not make its output trustworthy — it was still broken when
   someone actually looked.
5. **Automated "ACCEPT" was not trustworthy even after the known bug was
   fixed; manual review still found far more wrong.** The owner's own
   2026-10-20 manual pass found 71/366 example facts CONTRADICTED, 8
   contradicted + 80 unresolved links, and 30 missing-API findings across 19
   repositories that the automated chain had not caught. Owner- or
   human-reviewed status is never assumed from a pipeline's own green state.
6. **Self-measuring metrics were circular at least once already.** The old
   repo's own earlier dependability audit counted only the units the model
   chose to keep (so deferring everything scored 100%), and some of its
   metrics were restatements of the very gates they were meant to test. A
   metric that cannot fail by construction is not a metric; this was caught
   and fixed once already in the predecessor and must not be reintroduced here.

**How this applies going forward:** before trusting any "ACCEPT"/sealed/green
state in this repository, ask whether it could be hiding the same shape of
defect as (1) or (6) above; before marking a fix complete, apply lesson (2) by
checking its effect on already-produced candidates, not just new runs; before
treating a multi-step plan as in progress, apply lesson (3) by confirming the
later steps actually ran, not just the first one; never narrow a lane's scope
or ambition quietly per lesson (4) — any such narrowing is a decision-log
entry, named and justified, not a silent default.

## Still-valid outcome requirements (distilled from `idea.md`)

A README candidate (either lane) must, at minimum:

- Have exactly one factual H1, one compact badge row (package/release, platform,
  real build status, license, contributors where supported) in that stable order.
- Place one product banner (single link to `products.aspose.org/{family}/{platform}/`)
  between the badge row and the opening — this is correct and is *not* promotion
  before the product is explained (idea.md owner correction R1, 2026-10-11).
- Explain the product before any other Aspose promotional destination.
- Use the complete canonical product name at every visitor-facing identity
  position; package/namespace/command identifiers may use their exact technical
  form only where that identifier is itself the subject.
- Name the `aspose.com` commercial product **"Enterprise Edition"** everywhere,
  with no substitute wording ("commercial", "paid version", etc.), and no
  "full-featured ... Enterprise Edition" prefix (owner correction R2/R3).
- Preserve two kinds of structure: a **fixed core** every candidate shares
  (product explanation, navigation, At a Glance, capabilities, installation,
  minimal example, additional examples, API reference, scope/limitations,
  development/contribution, license) and **inherited additions** — extra
  headings the live README already carries (History, an MCP section, etc.) —
  retained in place, never dropped (owner correction R5).
- Each live README owns its own tone, prose structure, and heading skeleton;
  these are never replaced by a template (owner correction R4). Only what a
  verified fact or standing constraint forces is corrected.
- At a Glance is a typed capability graph: three mother blocks (Inputs, Core
  capabilities, Outputs) run strictly left-to-right, never stacked; no label is
  ever clipped — boxes grow to fit text (owner correction R7).
- Every claim (identifier, number, version, package, format, capability) traces
  to a verified fact with a `SUPPORTED` / `CONTRADICTED` / `UNVERIFIED`
  disposition — "not verified" is never silently presented as false *or* true.
- Aspose-link density adapts to the README's own size/content; configured
  maxima are ceilings, never targets; no link without direct adjacent-content
  utility.
- Upstream defect reporting (confirmed, reproducible, deduplicated issues) is a
  separate effect path from README changes, not a substitute for either.
- **Owner ruling, 2026-10-24 (overrides idea.md's "bounded interim fallback... for a human
  to file" language for this repository going forward):** issue filing is not a per-issue
  chat-authorized action anymore. Adopt the old repo's own real, production-proven model
  (confirmed live, not from narration — see `docs/DECISION_LOG.md`'s 2026-10-24 entry): one
  committed, evidence-digest-bound approval record per defect
  (`ops/issue_approvals/<handoff_id>.json`), then a scheduled, capped, autonomous job files
  (and closes) with no further human step. This is NOT a fully human-free system — exactly
  one committed approval per defect is still required, which is what was actually proven, not
  a looser "no owner step at all" model.
- Visual-asset/social-preview delivery is explicitly **not required for the
  initial pilot** — a bounded interim handoff is acceptable (idea.md §"Visual
  Assets and Social Preview"). Do not let this consume P1–P2 budget.

## What this repository does *not* inherit automatically

- The old repo's gate IDs (`G0`..`G3`), work-item IDs (`G3-W11`..`W19`), its
  `project/state.yaml` cursor, its 36-repository denominator as a hard count
  (mission §5: "the historic denominator ... is not current authority" — it is
  a *starting* portfolio list to re-verify, not a target to hit), and its
  `authorizable_candidates: 0/36` framing. This repo derives its own cursor,
  gates, and counts, informed by but not copied from the old one (mission §3:
  "No ... old plan copy").
- The old repo's `review.py`/`judge.py` acceptance logic, until independently
  re-verified here (see critical fact above).
- `docs/README_STANDARD.md` / `docs/README_CONTRACT.md` prose wording — the
  *content rules* above are salvaged as outcome requirements; the *documents*
  themselves are old-repo artifacts, not reused verbatim.

## Legacy-to-current mapping

| Named in old materials | Resolves to, in this repository |
|---|---|
| Old repo `plans/idea.md` | Still the product-requirements source (authority order #2 above); copied verbatim into this repo's own `plans/idea.md` 2026-10-23 for local convenience (no authority change — the external original still wins on drift) |
| Old repo `AGENTS.md`, `docs/EXECUTION_STATE_MACHINE.md`, `docs/STATE_MACHINE.md` | Forensic evidence / salvage source only; superseded here by `AGENTS.md` + `project/state.yaml` (this repo) |
| Old repo `project/state.yaml` (gates G0–G3, work items G3-W11..W19) | Forensic evidence of what was attempted and why it stalled; this repo's own `project/state.yaml` is the only execution cursor here |
| Old repo `migration/reuse-manifest.yaml` (its own pull from `foss-readme-optimizer`) | A precedent for this repo's own `migration/reuse-manifest.yaml`, not a transitive authority — its dispositions are claims to re-check, per mission §3 |
| `foss-mcp` `ops/SUPERVISOR.md` and `ops/*.py` | Reference mechanics only (mission says "not an external mission authority for this application"); adapted into this repo's `ops/`, stripped of foss-mcp-specific gate IDs/paths |
| This repo's own prior `reviews/REPOSITORY_PRESENTER_RECOVERY_V1..V5*.md` (pre-2026-10-21 planning docs, from before this mission document existed) | Superseded. Left in place as history, not deleted; carry no authority over this file or the mission document |
