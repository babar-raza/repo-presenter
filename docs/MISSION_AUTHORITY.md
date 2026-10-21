# Mission Authority — Repository Presenter (new repository)

This file is the single normative product+operating authority for this repository,
distilled 2026-10-21 per `plans/repository_presenter_fresh_start_supervisor_prompt.md`
("the mission document"). It does not duplicate that document; it resolves which
source governs when two documents disagree, and extracts the still-valid outcome
requirements from the old repository's `plans/idea.md`.

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
| Old repo `plans/idea.md` | Still the product-requirements source (authority order #2 above); read, not copied |
| Old repo `AGENTS.md`, `docs/EXECUTION_STATE_MACHINE.md`, `docs/STATE_MACHINE.md` | Forensic evidence / salvage source only; superseded here by `AGENTS.md` + `project/state.yaml` (this repo) |
| Old repo `project/state.yaml` (gates G0–G3, work items G3-W11..W19) | Forensic evidence of what was attempted and why it stalled; this repo's own `project/state.yaml` is the only execution cursor here |
| Old repo `migration/reuse-manifest.yaml` (its own pull from `foss-readme-optimizer`) | A precedent for this repo's own `migration/reuse-manifest.yaml`, not a transitive authority — its dispositions are claims to re-check, per mission §3 |
| `foss-mcp` `ops/SUPERVISOR.md` and `ops/*.py` | Reference mechanics only (mission says "not an external mission authority for this application"); adapted into this repo's `ops/`, stripped of foss-mcp-specific gate IDs/paths |
| This repo's own prior `reviews/REPOSITORY_PRESENTER_RECOVERY_V1..V5*.md` (pre-2026-10-21 planning docs, from before this mission document existed) | Superseded. Left in place as history, not deleted; carry no authority over this file or the mission document |
