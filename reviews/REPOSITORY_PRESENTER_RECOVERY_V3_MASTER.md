# Repository Presenter: Evidence-Led Dual-Lane Recovery and Shipment Contract (v3)

**Execution authority:** This is a handoff for an independent VS Code supervisor, *not a declaration that its current state has already been verified locally*. The supervisor MUST inspect the working tree and the new remote head before changing anything. It MUST reconcile this handoff into the repository's existing authorities after bootstrap verification, without creating a second permanent project cursor. **Mission: first real useful upstream README PR quickly; independently prove Lane L and Lane R; then unattended operation with the existing issue reporter preserved.**

**Audit time:** 16 October 2026, Asia/Karachi. GitHub is mutable; all dated findings below are snapshots. **Pinned observed `repository-presenter` `main`:** `2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c` (commit timestamp 2026-10-15T14:09:12Z). **Pinned observed `foss-mcp` `main`:** `11d258a6d9a1e8c688aca66bd0ab1117f7da6d9a` (2026-10-14T20:07:24Z). **Former optimizer main:** `a8a163f7e9a7beeac1d2ef8b7c02e8e4bd5a7815`. Do not silently use these older SHAs as live HEAD in the future. Inspect `git rev-parse HEAD`, `git rev-parse origin/main`, `git ls-remote`, open PRs, workflow history, changed packages and exact target HEAD before executing.

**Companion files (same folder as this document):** `REPOSITORY_PRESENTER_SUPERVISOR_BOOTSTRAP_V3.md` is the detailed supervisor installation/preflight checklist; `REPOSITORY_PRESENTER_LIVE_README_INVENTORY_2026-10-16.csv` is the complete, 46-row upstream inspection inventory, including 45 readable READMEs and one confirmed absent `README.md`; `REPOSITORY_PRESENTER_START_V3.txt` is the VS Code startup instruction. The repository itself MUST contain only project-approved copies of these after reconciliation, not several competing plans.

**Precise meaning of evidence.** `SOURCE_INSPECTED` means the indicated code or README was read at its current default branch during this audit. `REMOTE_OBSERVED` means a Github read/write run was viewed; a green workflow is not proof of a target README PR. `REQUIRES_LOCAL_VERIFICATION` means information available from GitHub is not sufficient to prove execution, current candidate counts, installed GitHub App privileges, local filesystem or signed-off acceptance. `HYPOTHESIS` indicates an implementation hazard shown by control flow that needs a reproducer; do not call it a confirmed production defect until tested.

---

## 0. Mandatory operator instruction (no optional planning-only exit)

1. Perform **G0 live recon and evidence capture** now. Do not blindly trust this report, previous assistant reports, historical `project/state.yaml` counts, or worker explanations. Inspect actual remote and local HEADs, status, worktrees, current upstream org inventory, README blobs, scheduled workflow runs and target effects. Preserve exact outputs, source SHAs and last successful/failed run links. This step is read-only.
2. Build a **working supervisor** using `foss-mcp`'s code and operational rules as a reference, adapted and tested in Repository Presenter (instructions in companion bootstrap). Do not just create `SUPERVISOR.md` or copy YAML files. Prove dispatch, independent verification, negative control, integration, restart, state derivation, worker scope refusal and heartbeat before dispatching product work.
3. Keep **Lane R and Lane L distinct and first-class**. Neither is a fallback for the other. Lane L detects and documents *newly introduced* capabilities even if they are not among the old README's consumed facts. Lane R authors/rebuilds a **complete** README where the live README is demonstrably below a stable, source-grounded standard, or when missing and implementation is actually present.
4. Establish the **shared write path** early. A correct README with no external authorized effect is an unfinished transaction. Run one sandbox canary, then the owner-authorized production pilot(s); verify the target-side PR, patch and re-dispatch behavior. Only pre-authorized target/effect classes may be written. Never silently expand authorization or use a PAT as a substitute for the target-scoped App token.
5. Keep the existing upstream **issue filing** service operational, independently checked; do not reimplement or disable an already-proven production capability for architectural cleanliness.
6. Stop after **two equivalent failures** and escalate with a root cause. A third same-signature attempt without a changed causal mechanism is not authorized. Do not create gates, validators, rubric revisions, global reseal waves, reports, or refactoring work unconnected to an immediate external acceptance criterion.
7. Report progress as **verified external outcome**, not code count or sealed-candidate count. At minimum: upstream README PRs opened, merged, current/obsolete; distinct Lane R and Lane L outcomes; issues filed/closed with verified URLs; last unattended end-to-end successful time; typed permissions/infra blockers.

### Stop/go and authority boundaries

- **Automatic execution starts only after the supervisor preflight reaches `PREFLIGHT_PASS`.** The startup agent may perform read-only reconnaissance and build/test the supervisor beforehand. It must not start unrestricted autonomous writes beforehand.
- **Initial target write** is one owner-selected or previously expressly authorized target, with authorization rechecked from repository evidence. The existence of a GitHub App token does **not** authorize a target write. A sandbox target is not a production target.
- **No direct default-branch push to upstream product repositories.** PR-only and separate write-token job. No automatic merge unless existing owner policy *explicitly* covers that exact repository/capability and no maintainer objection, checks pass and source SHA is pinned. The audit does not issue new permissions.
- The current repository says agents work in isolated worktrees. Follow that until an owner-authorized replacement rule is integrated; do not rewrite unrelated `main` working-tree changes. Only a supervisor-approved integration PR lands product code on main.
- `.venv` only for Python dependencies; Git Bash on Windows 11. Do not use untracked Python environments or `pip` into the global installation. Paths in older `foss-mcp` prompts such as `D:\Users\prora` are **historical** and must be replaced with the verified checkout path and local `.venv` path. Prefer repo-relative paths in taskcards and scripts.

---

## 1. True starting picture: remotely verified and explicitly unverified

| Item | Status observed 2026-10-16 | Evidence and corrective implication |
|---|---|---|
| Main repository | `babar-raza/repository-presenter`, HEAD `2df2d9d8` | `https://github.com/babar-raza/repository-presenter/commit/2df2d9d8f081a4cb1353d98a0b197e759c1e6b0c`; refresh on first execution |
| Old product cursor | `project/state.yaml`, `updated_at: 2026-10-14T18:00:00+05:00`; 44 registry entries; `current_candidates: 29`, `authorizable_candidates: 0`, gate `G3_PYTHON_COHORT`, item `G3-W11` | These are **declared cursor figures**, not a live, freshly recomputed local `repository-presenter status` result; supervisor must run `status --json`, verify bundle hashes, and capture difference |
| Registry | 44 entries: 42 `dry_run`, 2 `full` (3D/Java, Cells/Java) at observed main | `data/registry.json`; current modes sharply limit autonomous upstream README PR scope. Permission issue is distinct from candidate quality |
| Canonical organizations | 16 Aspose FOSS product orgs, 46 visible product/companion repositories excluding `.github` configuration repository; 45 root `README.md` files inspected, GIS/.NET root `README.md` absent | See CSV manifest for 46 names, default branch, SHA, README file line count and exceptions |
| **JMAP migration drift** | All eight JMAP repos now appear in org `aspose-jmap-foss`, while registry still names `aspose-email-foss/Aspose.JMAP-FOSS-for-*` | **Verified inventory mismatch**; use stable GitHub repo ID, follow redirects if applicable, re-verify installed App access; never create duplicate registry records based on owner name alone |
| Additional visible repos | `aspose-psd-foss/Aspose.PSD-FOSS-for-Java` (README 3-line stub) and `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP` (specialized 189-line companion README) | Neither is in the 44-entry registry. Classify as `NEW_PRODUCT_CANDIDATE` vs `COMPANION`; no silent admission. PSD/Java may be the simplest Lane R demo **only if source is processable** |
| README generation | Large multi-stage R pipeline present; 29 sealed candidate count on old cursor; 0 authorizable on old cursor | Candidate state alone does not prove production readiness; judge and effect MUST be re-run against current pinned input |
| Lane L deterministic correction | Built `components/readme_correction/`; old independent Oct 13 review found **20 pushable** corrected bundles, 19 with minor fixes, 5 do not push out of 44 (historic worktree evidence, not current checkout proof) | Those bundles are useful low-cost **shared PR spine** pilots, but mostly diagram fixes; they **do not** establish product-change detection |
| Lane L semantic update | `detectors/gaps.py` reports unshown examples/public types/formats, but writes no prose; `engine.py` has **zero model calls** | **Missing core capability**: new source/API feature → verified semantic change → authored incremental prose/example → delta acceptance. Build on existing detector rather than pretending `correct-readme` is Lane L complete |
| Scheduled orchestration | `monitor.yml` and `sealing-scheduled.yml` exist. `sealing-scheduled.yml` calls `present.yml` (full composition), not equivalent scheduled Lane L authoring | Proper event routing and novel-capability triggers still needed; don't infer autonomous L production from Actions presence |
| Existing issue filer | Production issue reporter exists and has filed upstream Cells issues; `issues-scheduled.yml` exists | Preserve and recheck actual issues and repeated-dispatch dedup. Do not overwrite or create a parallel issue bot |
| Hosted recent results | 2026-10-15 14:09 UTC CI success (`38748858884`), 2026-10-15 21:27 UTC monitor success (`38810055322`), 2026-10-16 00:43 UTC liveness success (`38831066578`) | Green CI/monitor/liveness **does not prove** Lane R or L published an upstream README PR. Inspect job steps, latest attempts and effect receipts |
| Sandbox proposal | Earlier run `38738363742` had GitHub App installation query 404 for `babar-raza/presenter-sandbox` (previous audit) | Needs a fresh scoped preflight; old failure could be fixed by the time this executes. Do not declare still broken without reproduction |
| Open control repo PRs | #328, #317, #233, #214 observed OPEN | Preserve, classify overlap and blockers, do not bulk merge or abandon them automatically |
| Main optimizer | Legacy `babar-raza/foss-readme-optimizer` HEAD `a8a163f7...` | Read-only oracle and provenance; never repeat its 0-delivery gating machinery |
| Site README refresh skill | User confirms `readme-refresh` from private `aspose.org` generates many current top banner/badge sections | Private `aspose.org` was **not accessible** through this GitHub inspection (404); local supervisor must locate/read its skill, examples and actual generated provenance. Do not claim skill source inspected here |

### First mandatory evidence bundle (before implementing)

Create a `G0-BASELINE` evidence bundle with `git rev-parse`, `git status --porcelain=v1`, `git worktree list --porcelain`, `git log`, `git diff --stat`, current remote PRs, runs, GH app target preflight, `repository-presenter status --json` output, `registry.json` count/modes, JMAP redirect/ID mapping, per-repo README HEAD SHA, one representative candidate's digest/recheck/judge, one issue ledger entry, one proposal effect dry-run. Record UTC timestamps, exact commands, exit codes, tool version and SHA-256 of output files. Errors are typed (`INACCESSIBLE`, `NOT_RUN`, `UNVERIFIED`), never zeros or presumed passes. Do not commit secrets/tokens or unredacted runner environment.

**Do not treat an inventory snapshot as a truth assessment.** Each README's claims about formats, installations, editions, API types, versions, dependencies and examples require independent source/registry/build verification before patching or declaring it ready.

---

## 2. Live upstream README audit and reusable presentation standard

**Scope actually inspected:** all 46 product/companion GitHub repositories publicly returned by org searches of `aspose-3d-foss`, `aspose-barcode-foss`, `aspose-cells-foss`, `aspose-email-foss`, `aspose-font-foss`, `aspose-gis-foss`, `aspose-html-foss`, `aspose-imaging-foss`, `aspose-note-foss`, `aspose-page-foss`, `aspose-pdf-foss`, `aspose-psd-foss`, `aspose-slides-foss`, `aspose-tex-foss`, `aspose-words-foss` and `aspose-jmap-foss`. The org `.github` meta repo is excluded as non-product. The inspector read each available root `README.md`, its opening, numbered heading structure and linked badge/banner placement; full README text was loaded (not only snippets). The accompanying CSV records **exact README blob SHA** so the agent can prove whether a target changed since this inspection.

### Observed commonality, without imposing an artificial template

- **31 of 46** have an already linked product banner. Many also have a badges row at the top. Treat this whole visual/header section from `readme-refresh` as **preserved by default**, including exact URLs, image accessibility text, positioning and whitespace. Verify freshness only if a grounded defect is found. **Banner missing is not automatically a defect.** Do not introduce generic banners just to make a linter green.
- Most generated-family README structures use H1 → badges → linked banner → 1–2 paragraph product intro → Navigation → At a Glance → Key Capabilities → Installation → Dependencies → Quick Start → Additional Examples → API Reference → Documentation & Resources → Scope and Limitations → Development and Testing → License. Some are shorter, longer, or lack a section for good reasons. Thus the **shared template is semantic, not a single forced literal sequence**.
- Live bespoke examples **must not be flattened to the generated shell**: `Cells/Python` has `Features`, `Supported formats`, `Scope`, `Examples and API`; `Slides/.NET` has `What it can do`, `What it cannot do`, `Choosing an edition`, `Security`; `Words/.NET` has `The story behind this code` and `Enjoying it? Star it ⭐`; `Font/Python` has buyer journeys, variable-font workflows, CLI and MCP; `PSD/.NET` has audience, mental model, scoped limits; `PDF/Go` has `Feature Showcase` and `Third-Party Notices`; `PDF/C++` has build modes, `Project Structure` and `Third-Party Notices`; `Cells/Go` has `Detailed Documentation` and `Constraints`.
- Length is not a quality verdict. `PDF/TypeScript` is ~4,630 lines, `PDF/.NET` ~1,890, `PDF/Java` ~1,676, while JMAP README variants have ~200 lines. A universal 300-line limit would destroy valuable inherited examples/API detail; format long reference data in `<details>` or move it only if accepted and the links are preserved. Never drop content merely to meet a line budget.
- **Markdown parsing is mandatory**: `3D/Python` L227-L230 and `PDF/Java` L1651-L1667 contain `#` comments inside fenced code; these are NOT document H1 headings. `Cells/Go` L105 **is** an extra rendered H1 outside a fence and deserves correction, while preserving its surrounding explanatory text and anchor/navigation semantics.
- **No unproven 'improvement'**: a newly rewritten README loses if it drops accurate scenarios, examples, warnings, limitations, support paths, contributor guidance, attribution, license notices, product history, customer context, or platform-specific install instructions. All material inherited units get an explicit disposition with evidence.

### Canonical v3 README archetype contract (not a forced global document)

| Semantic element | Core policy | Preserve/author decision |
|---|---|---|
| Product identity H1 | Required exactly once in **rendered Markdown** | Preserve live wording unless demonstrably wrong; special file/package name variants okay |
| Existing badge row | Preservation-default asset | Never reorder/remove/recreate without verified destination/reason; add only a warranted new fact-backed badge |
| Existing linked product banner | Preservation-default asset | Keep image and link from `readme-refresh` as-is unless genuinely broken or inaccurate; absence does not trigger addition |
| Product value proposition | Required for real library, precise scope | Retain strong live prose and limitations; for Lane R replace only when baseline objectively weak and new version independently better |
| Navigation / At a Glance | Optional unless already present or usability explicitly benefits | Preserve working anchors; verify Mermaid rendered visually and semantically before changing; never add large diagrams gratuitously |
| Capabilities and real use cases | Required for meaningful product | Source-backed; separate supported, partial, experimental and unsupported; audience-specific terms allowed |
| Installation and prerequisites | Required when installation is available | Registry-backed vs source-only vs native build, with platform-specific commands; no invented package availability |
| Quick Start | Required for processable library, with honest evidence tier | Verified run/compile where feasible; if input fixture absent, label prerequisite and do not claim it ran |
| Additional examples and feature showcase | Optional, but preserve live material | Include value-bearing walkthroughs, not token example spam; do not delete working examples for brevity |
| Supported formats and scope | Conditional on real capabilities | State direction, caveats and exclusions; avoid 'reads+writes' conflation |
| API reference | Conditional: tailored size/format | Keep meaningful source-backed API summaries, hubs, detailed member lists or links; avoid duplicating whole large autogenerated surfaces unnecessarily |
| Dependencies, build and tests | Conditional but accurately reflect toolchain | Never stitch commands from unrelated CI jobs; verify intended sequence; mention optional tooling distinctly |
| Documentation, community, security | Conditional/preserve | Preserve accurate links, guides, contributing files, support channels, caveats |
| Limitations, release maturity | Required if known limitations matter | Never turn disclaimers into marketing claims or omit limitations to look polished |
| Enterprise Edition link | Where appropriate and source-backed | Follow existing product policy; avoid new premature promotion or misleading capability equivalence |
| License and third-party notices | Required where applicable | Preserve actual legal text/links, notices and other attribution; never infer license from banner or prior README |
| **Bespoke/customer-authored sections** | **Must-carry by default** | Retain heading, position, prose, links, tables and code unless individual claims are contradicted; no global rewrite based on template difference |

**Template identity:** one `common core` of semantic roles with per-family/per-ecosystem/per-repository variants; no absolute section order. The renderer can use an outline suggestion for a **true R generation with no inherited standard**. For all existing READMEs, layout is a *constraint* for where changes should be made, not permission to rewrite. Use `data/readme_standard/{common.yaml,assignments.yaml,survey.json}` as **historic inventory and policy sources**; reconcile with current heads before freezing v3. Preserve records of owner decisions OD-01 through OD-10. Explicitly distinguish hard factual/safety controls from optional stylistic preferences.

### Mandatory section preservation ledger

For every README edit, create `inherited_sections.json` recording each Markdown-AST section and typed units: `id`, `heading`, `start/end byte`, `live_blob_sha`, `text_sha256`, `classification` (`CORE`, `CUSTOM`, `LEGAL`, `CODE`, `LINKS`, `ASSET`), `disposition` (`EXACT_PRESERVE`, `VERIFIED_AMEND`, `VERIFIED_MOVE`, `SUPERSEDE_REDUNDANT`, `OMIT_FALSE`, `OWNER_REVIEW`), `evidence_ids`, `rationale`, `original_bytes`, and `new_location`. `EXACT_PRESERVE` is default. `OMIT_FALSE` requires both contradiction evidence and a nonfabricated replacement/notice. `OWNER_REVIEW` does not authorize omission. Prove byte retention for untouched protected sections; reject a proposed regeneration that silently drops an inherited `CUSTOM` section. The reviewer receives the ledger AND the live README AND the complete diff.

### Three concrete upstream retention anchors

- [`Cells/Java: Project Structure L261`](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java/blob/master/README.md#L261): preserve map unless new files/source prove it obsolete.
- [`Words/.NET: The story behind this code L928`](https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-.NET/blob/master/README.md#L928): authorial history is valuable and is not 'template noise'; preserve, subject to factual verification.
- [`Font/Python: Three Buyer Workflows L7; CLI Highlights L424; MCP Server L534`](https://github.com/aspose-font-foss/Aspose.Font-FOSS-for-Python/blob/main/README.md#L424): separate audience and workflow blocks should survive both lanes; do not replace with generic capability bullets.

**Additional retention anchors:** [`PDF/Go Feature Showcase L298; Third-Party Notices L1026`](https://github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Go/blob/main/README.md#L298), [`Cells/Go Project Structure L382; Detailed Documentation L529; Constraints L533`](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/blob/main/README.md#L382), [`Slides/.NET What it cannot do L373; Security L536`](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET/blob/main/README.md#L373), [`PSD/.NET Mental Model L30; Out of Scope L181`](https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-.NET/blob/main/README.md#L30), [`PDF/C++ Project Structure L486; Third-Party Notices L914`](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp/blob/main/README.md#L486), [`Words/.NET Enjoying it? Star it L947`](https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-.NET/blob/master/README.md#L947).

### `readme-refresh` cross-system contract

The site skill-generated HEADER is **trusted as presentation provenance but not as a fact authority**. The supervisor must `rg --hidden -n "readme-refresh|banner-readme|README"` in the local private `aspose.org` skills tree; read the exact skill contract and examples; compare its expected badge/banner pattern against the 31 observed linked banners, identify any reserved markers and source synchronization rules. The skill, if authoritative for this header, remains owner of initial header creation and branding; Presenter preserves it and may emit a **reviewable request** for the skill or its operator if an actual branding defect exists. Do not build an unrequested second banner generator. Tests must demonstrate no-op on a valid skill-generated header; existing badge/banner URLs stay identical in both lanes unless specifically authorized to change.

---

## 3. Exact repository-specific reuse/change/retire map (observed main)

The paths below are **source links pinned by the audited main commit**. Line ranges mark public contracts and risk boundaries. Re-open locally with `nl -ba`/`rg -n` at the **actual current SHA** before modifying; line locations are not promises across subsequent commits. `KEEP` does not mean bug-free, it means reuse it after targeted tests. Do not port old code merely because it exists. For shared code changes, preserve unaffected test behavior.

| Component and exact location | Measured behavior | Recovery action and proof |
|---|---|---|
| `AGENTS.md` L1-170 | Owns agent conduct, two lanes, protected inherited material, two-failure cutoff, isolated worktrees, current old priorities | **KEEP safety; amend only conflicting old gate ownership during cutover**; no second governance authority |
| `plans/idea.md` L1-~90 and operating model below | Owner business charter with historic note about legacy authority and first target authorization | **KEEP mission;** current target/date caveats reverified; do not reinstate retired mission graph |
| `project/state.yaml` L1-~100 | Single current cursor, old `G3`, N/44 and legacy queue | **KEEP canonical path, CHANGE derived schema/cursor only after supervisor preflight**; immutable old snapshot captured beforehand |
| `docs/EXECUTION_STATE_MACHINE.md` / `docs/STATE_MACHINE.md` | Huge existing G0-G7 build and runtime plans | **RETIRE old execution ordering only after owner/supervisor logged cutover.** Migrate safety predicates selectively; no parallel active gate graphs |
| `project/loop-prompt-ship.md` L1-~85 | Has Lane R primary, L fallback, seven serial rungs; rung-3 declared done 2026-10-15 | **RETIRE as active dispatcher at cutover**, preserve dated evidence; use supervisor taskcards instead |
| `data/registry.json` (`entries`, observed 44) | 8 stale JMAP owners; 42 dry-run vs 2 full | **MODIFY registry identity reconciliation** using stable repository ID and App availability; independently authorize any change of write mode |
| `data/readme_standard/{common.yaml,assignments.yaml,survey.json}` | Live-first standard and Oct 11 survey; body still has legacy rule contradictions | **KEEP semantic core and prior owner rulings; REBASE factual snapshot to current HEAD**, extend for preserved bespoke sections; no unconditional structure/line budget |
| `src/repository_presenter/cli.py` L440-~710 (`build_parser`), L1472-~1640 (`main`), L4168-4529 (`run_present`) | 4,795-line CLI, R and correction commands, direct monolithic present transaction | **WRAP first**, introduce typed `route`, `run-r`, `run-l`, `effect` adapters, keep old CLI as compatibility shim; no wholesale rewrite prior to PR |
| `components/readme/extractors/platforms/{python,net,java,cpp,go,rust,typescript,nodejs}*.py` | Eight platform-specific adapters and example readers | **KEEP**, run targeted code/fixture/registry tests; repair only proven gaps; no re-port from optimizer |
| `components/readme/evidence/facts/`, `core/facts.py`, `core/snapshot/capture.py`, `core/git_safety/clone.py` | Supported/unsupported evidence, pinned snapshot, push-disabled clone | **KEEP and SHARE** between lanes. All derived claims cite exact repo SHA/evidence kind |
| `components/readme/composition/{planning.py,authoring.py,renderer.py}` | R planning, agentic authored units and deterministic render | **KEEP/ADAPT R**; keep as authoring engine; add explicit preservation ledger, fact-tier prose quality and stable v3 profile |
| `components/readme/reconciliation/{dispositions.py,patch.py}` | Inherited content disposition and patching | **KEEP/ADAPT**; use default protected-content preservation; no whole-unit loss due to partial overlap |
| `components/readme/repair/rounds.py` L344, L660, L904, L1152 | `run_round`, `round_defects`, `repair_defect`, `run_transaction`, bounded repair path | **KEEP R targeted repairs**, enforce no retries after same signature and no blanket recompose |
| `components/readme/review/independent/review.py` L335, L1990, other review checks | Independent LLM reviewer with complex demotion/refutation logic | **KEEP only as a reviewer ADVISORY unless independence established**; add genuinely separate review input/channel and deterministic factual acceptance |
| `components/readme/acceptance/judge.py` L81-114, L369, L451, L503, L605, L692 | Six-clause computed judge; reviewer verdict explicitly advisory; original reconstruction and inherited comparisons | **KEEP architecture**, freeze baseline; ensure real R independently passes content/presentation, inherited disposition, exact pin; do not count `not worse` as quality proof alone |
| `components/readme/bundle/{seal.py,recheck.py}` | Content-addressed seals, scoped invalidation, provider no-op proof | **KEEP**, per-candidate recheck not global; cannot gate actual first PR on all other candidates resealing |
| `core/noop_proof.py` L417; `core/candidates.py` L482-~647 | Fresh-process ledger identity and gate for proposable candidate | **KEEP and PROVE**, preserve independent proof/authorization separation |
| `components/readme_correction/engine.py` L69-125 | Pure edit detector, bounded span edits, deterministic/idempotent proof | **KEEP as Lane L's mechanical fast path**; no model and no novelty discovery |
| `components/readme_correction/detectors/gaps.py` L39-148 | Detects unshown examples, symbols and formats as *report-only* | **EXTEND into typed semantic work queue**, not automatically actionable content |
| `components/readme_correction/detectors/{stale,additions,examples,claims,links,sections,structure}.py` | Selected corrections and report-only defects | **KEEP with truth controls**, unit tests, real README fixtures |
| `components/readme_correction/run.py` L85-156 | Exact pinned facts/README, returns status and bundle | **KEEP as L fast path**, add semantic-change stage AFTER new facts are discovered; don't weaken its confinement rules |
| `components/readme_correction/check.py` L183; `settle.py` L45-83; `gate.py` L84-211 | Baseline-relative validation and candidate loader; no worsening allowed | **KEEP for minimal edits;** extend delta acceptance to semantic authoring and protected-section ledger |
| `components/readme_correction/pull_request.py` | Existing correction PR descriptions; may overreport verifications if mixed | **KEEP**, verify prose cites actual evidence; no internal check narration or false PR claims |
| `components/monitor/relevance.py` L137, L168, L200-270 | `classify_change` asks if files *consumed by sealed README* changed | **CRITICAL EXTENSION**: add NEW fact/public export/registry/source novelty detection, not just consumed path comparison; regression fixture adds new uncited file exporting feature, must classify material |
| `components/monitor/drift.py` L138-202; `core/sealing_plan.py` L411-539 | Observe upstream head and choose drifted entries, cap 3, cooldown | **KEEP transport/runtime safety**, replace selection from one R-only reseal queue with typed R/L routing and independent priority/budgets |
| `core/state/{cas,git_backend,trigger,recovery,present_transaction}.py` | Durable CAS and recovery backend wired mainly around `present` | **KEEP backend if tests prove safe**, extend lane/effect identity, leases, recovery; don't maintain a separate `foss-mcp` runtime ledger unless state is unified |
| `components/propose/effect.py` L95-120, L146, L212-~463 | Target-scoped token, explicit owner-controlled write flag, candidate hash and idempotent proposal effect | **KEEP and RE-PROVE remote-effect execution**, unify effect identity for R and L without bypassing policy |
| `core/authorization/proposal.py`, `core/registry/write_gate.py`, `.github/workflows/propose.yml` L45-85 & L355-550 | Exact candidate/trigger authorization, sandbox and target-scoped GitHub App creation | **KEEP**, debug sandbox App 404; recheck permissions and approval scope; idempotent actual URL evidence required |
| `components/issues/{draft,quality,redetect,ledger,file,lifecycle}.py` | Upstream defect detector and issuer; `file.py` L99-112, L220-350 | **KEEP LIVE**, independently QA already-filed issues, dedup/close safety; no second filer |
| `.github/workflows/issues-scheduled.yml` | Scheduled upstream issue filing | **KEEP and independently smoke-test**, avoid pausing just because README repair is in progress |
| `.github/workflows/monitor.yml` / `present.yml` / `sealing-scheduled.yml` | Monitor, R composition, scheduled R-only seal and external propose | **KEEP existing as safe adapters until v3 cutover**, then route to separate R/L jobs; never run v1/v3 writes for same target/effect concurrently |
| `.github/workflows/candidates-publish.yml` and `components/candidates_publish/` | Control repo candidate bookkeeping | **KEEP if useful**, avoid making candidate-publication PR a blocker for an otherwise authorized upstream PR |
| `tools/reviewer/*`, `evidence/build/G3_PYTHON_COHORT/*`, `docs/DEFECT_INDEX.md` | Rich audits and historic mechanisms | **PRESERVE READ-ONLY**, mine only verified findings affecting chosen pilot; no portfolio-wide mechanical replay |
| `foss-readme-optimizer` `src/readme_agent/` | Large inherited implementable corpus | **REFERENCE ONLY**. No mass copying or resurrection of its outdated gates |

### Specific previously observed failure chains the agent MUST test

1. **Novelty miss in Lane L**: `monitor/relevance.py` L168-L233 can classify head changes as irrelevant if none of *already consumed* paths changed. A new API module and export added outside old consumption can therefore be missed. Prove with a fixture and fix discovery independently of consumption. This is a **control-flow hazard**, not an externally reproduced live outage until test.
2. **Semantic L missing**: `readme_correction/detectors/gaps.py` L39 explicitly reports without authoring. A fully green correction cannot prove that feature documentation is current; add generated prose grounded in delta, with isolated validation.
3. **R quality gap**: `acceptance/judge.py` L1-80 calls independent LLM reviewer advisory. Maintain deterministic factual gates, but add an editorial independent reviewer/holdout who can block demonstrably poor composition through an explicitly ratified, bounded rubric; do not self-grade or demote a valid rejection without evidence.
4. **Regression after unrelated version bump**: `bundle/recheck.py` and the already recorded rung-3 bump proof are salvageable. Test nonconsumed bump retained accepted candidate. Never version-stale all 44.
5. **GitHub App missing installation**: re-run sandbox canary read-only App installation query first. If absent, typed `BLOCKED_EXTERNAL` and ask for exact installation/permission action; proceed with independent local work; no fabricated success.
6. **Registry-mode delivery trap**: readiness for 42 dry-run entries is not permission to submit. A real issue filed does not authorize a README effect. Secure a genuine owner-selected/full-mode authorized pilot and record exact target grant.
7. **Stale survey**: `data/readme_standard/survey.json` is dated Oct 11; today’s README blobs have changed. Build new snapshot; keep old as historical, not as current live quality evidence.
8. **Source path changes**: eight JMAP locations changed; all authorization records, relative links, registry keys, cached state and install visibility must be reconciled without losing identity or filing duplicates.

---

## 4. Independent Lane R: generate and regenerate full product READMEs

**Intent:** produce a fully coherent, source-backed README that delivers meaningfully higher product utility and presentation quality where there is no README or the current README objectively fails the stable standard. Not a fallback for Lane L and not a generic template fill.

### R route admission

`R_GENERATE` only if no `README.md` AND independently verified source/package implementation supports a useful README (no package-placeholder prose); `R_REGENERATE` only if baseline quality assessment finds **material** missing, false, confusing, bloated, or incoherent experience not resolvable by reasonable incremental changes; `R_DEFER_NONPROCESSABLE` if no usable implementation evidence. A high-quality `readme-refresh` README does **not** automatically need regeneration. Retain its banner, badges and custom sections unless verifiably defective. The R planner must write a testable **before/after editorial benefit hypothesis** and preserve full inherited unit ledger.

### R production states

`DISCOVERED -> SOURCE_PINNED -> PROCESSABILITY_PASS -> BASELINE_GRADED -> R_ADMITTED -> FACTS_READY -> INHERITANCE_CATALOGUED -> PLAN_READY -> COMPOSED -> DETERMINISTIC_CHECKS_PASS -> INDEPENDENT_REVIEW_PASS -> REPRODUCIBLE -> AUTHORIZATION_CHECK -> EFFECT_PENDING -> PR_REMOTE_CONFIRMED -> WATCHING -> MERGED | CLOSED | SUPERSEDED`. Other terminals `NOOP_TRUE`, `BLOCKED_EXTERNAL`, `FAILED_INTERNAL`, `INELIGIBLE`. No skipping external effect confirmation. `R_NEEDS_REPAIR` returns only to causal stage (max 2 equivalent signatures). Store source SHA, candidate digest, profile version, model/prompt digests, fact digests, inherited unit ledger, validation, independent editor verdict, reviewer independence provenance, zero-call proof, effect fingerprint and actual upstream PR URL.

### R acceptance contract

- Every capability, format direction, install command and example in generated README is supported at the source SHA (or explicitly uncertain/omitted). Never infer full API support from a package name, upstream aspirational docs or Enterprise Edition product.
- Each valuable existing section has exact keep/verified edit/move/disposition; no silent deletion of community notes, examples, warnings, customer-specific sections, notices, or production instructions. Preserve existing badges and banner by default. For a **true generation with no README**, no inherited unit ledger needed beyond legal/source repository assets.
- Quick Start proves first-use viability using actual available toolchains, dependencies, fixtures and pin; distinguish `EXECUTED`, `COMPILED`, `STATICALLY_VERIFIED`, `UNVERIFIED` and `UNSUPPORTED`. Reject an unsupported example as a confirmed runnable example.
- Cohesive, product-specific narrative; appropriate audience, top useful tasks, usable steps, accurate feature/limitations. Avoid empty boilerplate, unnecessary 1000-line API dumps, duplicate text and process-internal narration. A specialist independent editor judges end-user utility against current README; must **beat baseline**, not merely match valid headings.
- Renderer preserves Markdown AST, renders Mermaid/links/fences, no broken anchors, has a real deletion/retention diff audit. The no-op proof uses two distinct processes and zero extra model calls, but never makes portfolio publication depend on re-proving unrelated candidates.
- Publication is always independently reauthorized and source-fresh; PR body names meaningful before/after content and verification without internal gate vocabulary; actual PR readback and second-dispatch idempotency required.

### R pilot selection, with explicit uncertainty

`PSD/Java` has a 3-line README and is absent from the registry, making it a possible **high-value new R candidate**, **if** source has real production implementation and the owner explicitly admits/writes it. `GIS/.NET` has no README, but might be a placeholder: do **not** create a fictitious product README. Existing R canary `3D/Python` has substantial material already and may *not* merit full regen without a measurable issue. Do not pick the pilot for convenience alone: read the current upstream source and select the first **admitted, processable, measurably substandard** README with deliverable permission. The supervisor must record why the chosen pilot was R, and why L would not suffice. Else select an already authorized candidate with objectively deficient core content. **The R exit gate cannot be satisfied by a diagram-only or one-heading patch.**

---

## 5. Independent Lane L: live README change maintenance

**Intent:** keep a currently worthwhile README synchronized with *new* or *changed* user-visible product behavior; preserve irrelevant material exactly. This is a **semantic maintenance engine** with a deterministic correction accelerator, not just a fixed detector list.

### L change discovery (decisive design correction)

At each authorized repository head, independently compare `last_processed_upstream_sha` (or last accepted source baseline) to HEAD; record changed/added/deleted file paths, touched manifests, exported symbols, public API signatures, declared and tested formats, build/dependency/install metadata, package versions, docs, examples, release metadata and relevant tests. **Include newly created paths and symbols**, even when no old fact cited them. Build typed `CapabilityDelta` facts (`ADDED`, `CHANGED`, `REMOVED`, `BEHAVIOR_SHIFT`, `INSTALL`, `VERSION`, `EXAMPLE`, `DEPRECATION`, `DOCS`, `NO_USER_FACING_CHANGE`, `UNVERIFIED`). Use language-specific parsers and compare public surfaces, not simply changed filename counts or LLM prose guesses.

A change in code can be irrelevant to visitors; positive novelty signals must be verified as public and useful. Conversely no currently consumed path changed does **not** imply no new public functionality. The monitor must reconcile both: `CONSUMED_DRIFT` and `NOVELTY_DELTA`, and classify `SOURCE_CHANGED_BUT_NO_README_IMPACT` with reason/coverage proof, not a default shortcut.

### L content planner and editor

1. Bind new facts to existing README sections through headings, concepts, examples, anchors and already documented capability families; preserve section order and existing top chrome.
2. For deterministic facts (version, broken link, proven badge, missing closing tag), execute existing `readme_correction` engine with bounded span replacements.
3. For new feature or semantic behavior, use a bounded LLM editorial job, constrained to `CapabilityDelta` + verified facts + existing section context. It may add an H3/example/list item or revise a precise capability statement, but **cannot** rewrite untouched sections.
4. When a changed capability contradicts current README claims, correct the claim and relevant installation/examples/limitations together, including removal of obsolete references. If public evidence is incomplete, hold that specific claim/report-only; continue other independent deltas.
5. For each edit, record source evidence, original byte span, replacement, section, impact, reason, user value, rendered effect and before/after verification. The output is a narrow patch bundle.
6. Independent review checks omission of each must-carry delta, content utility, protected sections, correct before/after claim and patch scope. `NOOP` only when no material user-visible delta remains; failure to detect an added public API is not a valid no-op.

### L runtime states

`HEAD_OBSERVED -> BASELINE_PINNED -> CHANGESET_DISCOVERED -> FACT_DELTA_VERIFIED -> IMPACT_CLASSIFIED -> L_ADMITTED -> EDIT_PLAN_READY -> PATCH_PREPARED -> CONFINEMENT_CHECK -> DELTA_VALIDATION -> INDEPENDENT_DELTA_REVIEW -> SOURCE_RECHECK -> AUTHORIZATION_CHECK -> EFFECT_PENDING -> PR_REMOTE_CONFIRMED -> WATCHING -> MERGED | CLOSED | SUPERSEDED`; plus `NOOP_VERIFIED`, `NEEDS_UPSTREAM_ISSUE`, `BLOCKED_EXTERNAL`, `FAILED_INTERNAL`.

### L acceptance contract

- All material changes documented or individually typed/justified as not user-facing, blocked or deferred.
- **Unrelated README bytes remain identical**; core sections, visuals and bespoke headings preserved. An added new example is unit tested or accurately labeled with evidence tier.
- No new inaccuracies introduced; old disproven claims removed; no broken links/anchors/new bad headings; show diff vs current live HEAD.
- No dummy PRs for code formatting/lockfile movement with no user impact. Avoid speculative SEO/brand changes when repository only added a feature.
- A **real new feature** originating in newly added source path, plus a changed/deprecated public signature, must both be caught by positive fixtures. A solely style/diagram update is NOT Lane L's product-change delivery proof.
- Stale source after drafting causes bounded rebase + impact recheck; don't overwrite newer maintainer edits or duplicate existing PRs.

### L pilot

Choose a repository with a **current source revision delta that introduces or changes an actual public capability**, reachable with existing owner permission. If none currently exists, create a deterministic local fixture to prove detection, then await real change for the *production* milestone; do **not** fabricate a source change or claim a format-only PR meets L delivery. A historical Cells/Go gap in public types and its real second H1 are useful for the **mechanical correction smoke**, but not sufficient evidence of novel feature detection. Preserve `Cells/Go` `Project Structure`, `Detailed Documentation`, `Constraints`, and its valid header.

---

## 6. Shared runtime: routing, permissions, conflicts, issues and autonomy

### Routing state decision

A repository has independent dimensions: `R_quality_obligation`, `L_unhandled_source_delta`, `issue_defects`, `processability`, `authorization_scope`. The router returns `R_ONLY`, `L_ONLY`, `BOTH_EVALUATE`, `NOOP`, `DEFER_NONPROCESSABLE`, or `BLOCKED_READ`. It never routes a new feature only based on how many facts the old README consumed. When both lanes have outstanding work on the **same README**, choose one effect owner at a time: prefer an independently ready R replacement that already incorporates the L delta, otherwise ship the narrow L first, then rebase R. No simultaneous competing PR writers for `(repo, README.md)`; effect lock keyed by stable repo ID and target path.

### Effect state and dedup

`CANDIDATE_READY` is not `WRITE_ALLOWED`. Separate `POLICY_VALID`, `APP_INSTALLED`, `TOKEN_MINTED`, `PERMISSION_VERIFIED`, `AUTHORIZATION_VALID`, `BASE_FRESH`, `NO_CONFLICT`, `PR_SUBMITTED`, `PR_READBACK_CONFIRMED`. Exact effect identity = stable repo ID + canonical target path + lane + upstream base SHA + candidate diff hash + explicit authorization policy version. Before retrying a failed network call, query GitHub branch and PR history for the fingerprint to reconcile a possibly succeeded POST; don't open duplicate PRs. If the same candidate already exists, return same target URL. Merged PR supersedes baseline; closed without merge requires disposition.

### Authorization flow

Use read-only token for fact capture; separately mint short-lived App installation token **inside one write job** scoped to the exact authorized repository and permission. Verify installation and repo membership, expiration, minimum `contents:write` / `pull_requests:write`, plus target and candidate policy. File issues with `issues:write` only through existing issue workflow; issues and README effect grants do not imply each other. Owner-selected first production repo/capability and existing exact authorization record must be confirmed. Only once a first production effect is verified and owner-approved class-scoped standing policy is explicitly recorded may the scheduler operate automatically for that class.

### Preserve live issue reporting

Existing issues workflow and code remain in service. Audit already created Cells issues: source evidence, root cause, duplication, current status, whether README can be fixed despite defect, and correct close/update state. Do not file issues for analyzer false positives such as an existing license under alternative path until the policy actually verifies it is defective. Stop an issue class if repeated false positives appear. Keep per-repo issue budget and repeat-run idempotency. A product README blocked by one source defect must not automatically block unrelated projects/lane work.

### Autonomy and scheduling

One read-only observation pass per interval discovers source HEAD movement, registry/release metadata, newly public APIs, known broken claims, quality/drift and issue closure. Each event becomes independent bounded work with immutable signature. Lane L updates under semantic changes; R runs only with explicit quality mandate/admission or new processable repo, not every HEAD move. Scheduler enforces per-repo lease and cross-lane effect exclusivity, queue caps, provider budgets, durable checkpoints and exact resumability. Each run writes outcome record regardless of no-op/blocker and includes next-resume predicate. Prove two unattended cycles: new work → upstream PR; unchanged head → ZERO model calls / ZERO new PRs. Then prove restart after failure and rerun no duplication.

---

## 7. Build state machine and rapid delivery execution gates

**Supervisor preflight is prerequisite for any work card.** Implementation may run in parallel on disjoint scopes after it is established. Use at most eight gates; do not force all 46 upstream repos through each gate. The specific gate numbering is a v3 proposal and must be reconciled with existing `docs/EXECUTION_STATE_MACHINE.md` at cutover.

| Gate | Minimum independently measured outcome | Blocker policy |
|---|---|---|
| `G0_RECON` | Current repo/portfolio/credentials/status/PR/workflow/skill audit, SHA-pinned; restoration plan and protection of old commits; named first PR pilot | Read failures recorded. No live write. Continue inspect accessible scopes |
| `G1_SUPERVISOR_READY` | Port/adapt supervisor, schema/cursor adapter, card scopes, instructions/status channels; prove full dispatch→worker commit→independent verify→falsifier→integrate→restart on synthetic card. `PREFLIGHT_PASS` recorded | Do not dispatch production card until all control-plane negatives pass |
| `G2_FIRST_UPSTREAM_README_PR` | Target selected by owner policy; sandbox canary real read-back; one smallest **useful** existing independent correction (optional) submitted to real authorized target, exact diff and second-run dedup | If no App rights, `BLOCKED_EXTERNAL`; work on R/L independently but do not claim G2 complete |
| `G3_L_PRODUCT_CHANGE` | Source public-feature novelty proof, semantic incremental authoring, preserved bespoke/readme-refresh sections, independent delta acceptance, actual Lane L PR with feature update | Real PR is mandatory; no diagram-only proxy |
| `G4_R_FULL_REGEN` | Measurably inadequate but processable README selected, full source-backed reconstruction, positive baseline-quality improvement and lossless inherited units, actual Lane R PR | No README/placeholder not automatic eligible; no stub inventing |
| `G5_CROSS_LANE_AUTONOMY` | Both lanes individually scheduled, effects authorized, no conflicting PRs, same SHA no-op; merged R baseline handed to L; source drift correct | Typed infra blocks don't erase verified work in other lane |
| `G6_ISSUES_PLATFORM_SCALE` | Issue bot preserved and QA'd; additional ecosystems representative; new repo admission controlled; coverage/routing and formats tested | Do not re-open 46 candidate wave until deliveries pass |
| `G7_PRODUCTION_SEAL` | Production runbook, rate limits, restart, dashboards, release evidence, rollback, 2-run unattended proof and thresholds; full repo registry reconciled | No release based on green tests alone; external outcomes |

### Critical path rules

- G0 and G1 **before code workers are unleashed**. G2 should be the first external README outcome; G3 and G4 may execute in parallel once shared effect is established. G5 cross-lane depends on both G3 and G4.
- The supervisor must dispatch **one atomic work card per verification boundary** with explicit file ownership; two workers never edit a common file or commit provenance concurrently.
- Stop global bootstrap refinements once G1 passes; the next time spent must be G2 real delivery or verified external blocker. A perfect supervisor cannot substitute for a PR.
- A known quality defect on one pilot is repaired there; shared policies change only if a falsifiable systemic mechanism is demonstrated. Do not run an unrelated portfolio-wide reseal to 'get confidence'.

### First twelve executable cards (write scopes are proposals; validate against current files)

| ID | Goal / read dependencies | Exclusive write scope | Exit artifact / independent falsifier |
|---|---|---|---|
| `RP-001` | Frozen current-state & 46-repo inventory recon, read `AGENTS.md`, `state.yaml`, open PRs/actions, JMAP mapping | `evidence/recovery/G0/**` | Full source-verified manifest; falsifier: stale supplied README SHA rejected |
| `RP-002` | `foss-mcp` supervisor adaptation; bootstrap companion | `ops/gatectl.py`, `ops/gatecli.py`, `ops/gateverify.py`, `ops/cardlint.py`, `ops/integrate.py`, selected `ops/tests/**`, `schemas/recovery/**` | preflight report including bad-scope, false negative and restart control; no direct state mutation from worker |
| `RP-003` | Durable cursor + channels + migration, after RP-002 | `ops/{instructions,status,open_questions}.jsonl`, `project/state.yaml`, documented approved authority files, `plans/recovery/**` | deterministic state rebuild; old cursor snapshot hash; falsifier: manual cursor drift refused |
| `RP-004` | GH App read/write **sandbox** preflight, diagnose 404, effect audit | `tests/components/propose/**`, targeted proposal integration test and `evidence/recovery/G2/**` | real sandbox PR readback, identical re-dispatch no duplicate, source SHA/authorization checked |
| `RP-005` | Independently verify one useful old correction against current live README and source | `evidence/recovery/G2/correction/**`, minimal owned correction fix if needed | verified diff/content, with reasons and no authorial loss; return authorizable candidate without unneeded R reseal |
| `RP-006` | Submit first owner-authorized upstream useful correction after RP-004/005 | existing effect workflow/config/code where proven necessary; effect ledger | actual target-side upstream PR URL, exact patch, second-dispatch same URL |
| `RP-007` | Novelty detector including newly added exports/paths and registry/version changes | `components/monitor/**` or dedicated `components/change_impact/**`, focused tests | positive new public feature test fails with old consumed-only classifier, passes new one; private-only file change stays no-op |
| `RP-008` | Lane L semantic delta authoring and scoped reconciliation | dedicated `components/readme/live_delta/**`, focused tests; shared façade only later integration | new feature example/prose anchored to accepted facts; untouched custom sections byte-exact; source coverage matrix |
| `RP-009` | Independent L delta acceptance & PR path | `components/readme/live_delta/acceptance/**`, separate test fixtures | R-independent review, unsupported claim refused, delta omission refused; real L PR readback |
| `RP-010` | Lane R smallest successful full generation; port retained code via adapter | R composition/reconciliation/acceptance focused files, R pilot fixtures only | objective before/after score, all inherited CUSTOM/legal units protected, no fictional features, real R PR |
| `RP-011` | Scheduler two-lane routing/effect locks/recovery | `.github/workflows/` selected, `core/state/**`, targeted scheduler tests | unattended R and L recorded independently, no duplicate PR, no conflicting writes, restart works |
| `RP-012` | Issue regression/quality + platform scale/release | `components/issues/**` *only if broken*, `tests/components/issues/**`, release docs | existing filed issues retained, false positives corrected, no duplication, final release record grounded in remote effects |

**No false dependency:** RP-007 through RP-010 should be split into nonoverlapping smaller cards as needed, with actual dependencies; execute disjoint source-only tasks while RP-006 waits on external App approval. Taskcards must name actual symbols, code SHA, test commands and repo-specific fixtures, not just one sentence. The supervisor owns new card creation and verification; the worker never writes its card or verdict.

---

## 8. Failure modes, negative controls and release evidence

Every implementation area includes affirmative and negative tests. The following are **must-fail when deliberately broken**, not checklist-only claims:

1. A newly created source file exports a real API and tests it, none of its paths were consumed by prior README → L signals `ADDED_PUBLIC_API`.
2. New private helper only → L does not make a PR.
3. Modified public parameter default or supported format direction → L flags appropriate existing prose/code.
4. Removed public method → L removes/deprecates stale claim, not a new feature announcement.
5. Source HEAD changed after draft → effect refuses/rebases, does not push stale patch.
6. Valid `readme-refresh` title/badges/banner unchanged after Lane L pass.
7. Valid banner absent on bespoke README → no automatic generic asset inserted.
8. Broken link/false badge → exact evidence-based correction only.
9. Markdown `#` comment in `python`/`bash` fenced block → no extra heading found.
10. Real second H1 outside a fence (`Cells/Go` L105) → defect detected, but no accidental loss of adjacent dependency text.
11. Bespoke `Words/.NET` Story section removed in R → reject.
12. Bespoke `Font/Python` CLI + MCP sections silently removed → reject.
13. Legal notices (`PDF/Go`, `PDF/C++`) removed → reject.
14. Existing good Quick Start replaced by unverified example → reject.
15. R is admitted solely on missing banner → reject; banner is not a quality trigger.
16. R `README.md` absent but repo has no implementation → `DEFER_NONPROCESSABLE`, not synthetic product text.
17. R candidate has all headings but ungrounded format claim → reject.
18. R candidate loses a customer workflow while passing superficial rubric → reject.
19. L style/diagram-only patch claims G3 feature-update completion → reject.
20. L addition duplicates existing equivalent example/section → no-op or minimal edit, not duplicate.
21. One reviewer flags a valid contradiction → deterministic review must not demote finding without source evidence.
22. LLM outputs explicit command as `EXECUTED` without receipt → reject.
23. Qwen transport timeout between compose/review → bounded replay only causal stage, preserve accepted outputs.
24. Re-run at identical HEAD after successful PR → no new PR, same effect ID and no new LLM calls.
25. PR POST times out after actual success → reconcile remote and reuse existing PR.
26. Two L/R effect workers target same README simultaneously → lease or conflict owner prevents second write.
27. Merged R PR followed by L update → baseline moves to merged upstream SHA, no overwrite.
28. Registry JMAP old owner, new canonical owner with same stable repo ID → no duplicate record/effect.
29. GitHub App lacks repository installation → `BLOCKED_EXTERNAL`, exact action link, no PAT fallback.
30. GitHub App has `issues:write` but lacks PR grant → no README write.
31. `dry_run` without owner-authorized mode change → no real target PR.
32. Valid authorizations for another repo, branch, base SHA or hash → reject.
33. Attacker-supplied README `AGENTS.md` or prompt injection → treated as untrusted source data.
34. Worker edits supervisor's `instructions.jsonl` or its own taskcard → scope refusal.
35. Worker reports tests green after falsifier disables core functionality → supervisor must reject.
36. Supervisor kill/restart between dispatch and status append → resume exactly once, no lost work.
37. Shared filesystem contains unrelated modified user files → no `reset --hard`, `clean -fd` or `git add -A`.
38. Repeat 2 equivalent failures → no automatic third retry; root cause required; unrelated work continues.
39. Existing filed issue redetected as already resolved → update/close only with required policy, never duplicate.
40. Scheduler sees out-of-date monitor evidence or a partial owner inventory → typed failure, not zero drift.
41. One code-version-only bump changes nothing candidate consumed → no global reseal.
42. Source-fact change invalidates exactly affected candidates/lane units, preserving unaffected work.
43. Candidate is authorizable but first live target not owner-selected → no external effect.
44. Issue reporter stays live while R/L workflow ownership changes.

### Release evidence schema (minimal)

Every proof receipt: `card_id`, `gate_id`, `status`, `utc`, `source_repo`, `source_sha`, `control_sha`, `target_repo_id`, `lane`, `change_kind`, `artifact_hashes`, `checks` (command+exit+negative-control), `reviewer_provenance`, `authorization_id_or_null`, `effect_id_or_null`, `write_job_run_url`, `upstream_pr_or_issue_url_or_null`, `remote_observation_timestamp`, `next_resume_predicate`. Redact secrets and personal tokens. A claimed remote effect without verified URL/readback stays `EFFECT_UNCONFIRMED`. A sealed artifact remains evidence, not business outcome.

### External success board (not one misleading N/44 figure)

- Lane R: inspected, admitted, facts-valid, editorially accepted, effect-authorized, **real PR opened**, merged, no-op-proven.
- Lane L: changed-source events seen, correctly classified, updates accepted, **real meaningful PR opened**, merged, no-op-proven.
- Issue pipeline: verified upstream defects, issues actually filed, fixed and closed; quality false positives flagged.
- Shared platform: last completed scheduled end-to-end R/L, latest failed run and typed blocker, effects pending remote reconciliation, active leases/locks, GitHub App installation gaps.
- Report per repository as needed; never conflate no-change, unknown, unprocessable, blocked, failing and successful.

---

## 9. Cutover, rollback and time-to-value controls

1. **Before cutover:** snapshot current main, open worktree list and unmerged PR list, candidate dirs and old authorization files. Preflight source and write permission; do not delete any evidence or disable issues. Use an isolated bootstrap branch/worktree and no direct `main` changes.
2. **Shadow supervisor:** adapt `foss-mcp` ops code but run a disposable card that writes only test fixtures and no external effects; generated state projection is compared to expected current project schema, without overwriting authoritative cursor. Test crash/restart, scope, negative controls and exact tree SHA. It must pass G1 preflight.
3. **Single atomic authority cutover:** supervisor-integrated change to `AGENTS.md`, `docs/EXECUTION_STATE_MACHINE.md`, `docs/STATE_MACHINE.md`, `docs/SUPERVISION.md`, `project/state.yaml` and taskcards, preserving prior cursor in `evidence/recovery/baseline/`. One unified project cursor, one verified gatectl writer, no two active prompts. During cutover, pause **old README sealing/proposal producer** using existing `REPOSITORY_PRESENTER_SEALING_PAUSED` mechanism (verify variable and workflow); **leave issue filing alone**. Verify no simultaneous old scheduler/readme effect transactions remain.
4. **First external proof:** sandbox then one authorized real target. Live effect can only run with explicit owner-approved scope; target must be chosen by owner or match existing authorization. If authorization missing, record exact missing permission and continue L/R local development. Do not invent owner consent, move `dry_run` to `full`, or open a production PR for convenience.
5. **Progressive switch:** route 1 repo through v3 R, 1 repo through v3 L, then both schedule. Maintain v1 read-only observability until new external proof passes; no dual writes. Compare old/new pipeline behavior on pinned snapshots. Resume old authorized proposal path (if needed) only through controlled rollback, with no duplicate ownership.
6. **Rollback:** stop v3 dispatch, reconcile pending GitHub POSTs, release stale leases only after expiry/verified release, restore previous workflow ownership and old gate provenance from immutable snapshot via a reviewed change (no destructive worktree reset). Keep upstream PRs untouched unless separately authorized. Issue reporter remains on its existing workflow.

### Fast-delivery time budget (operational guard, not a promised ETA)

- Spend **one bounded recon window** producing actionable `G0` baseline, not another open-ended research report.
- Spend **one bounded supervisor-bootstrap cycle** on tested dispatch/verify/restart; refuse feature creep in governance.
- Move immediately to a narrow correction proposal under verified permissions, then a true feature-impact Lane L PR and a full Lane R PR. Both first-lane milestones are externally observed. If permissions block the real PR, give exact failure and independent next task rather than extending a loop.
- Keep branch/test suite scopes proportional. Focused tests and representative live fixtures first; run official CI before integration. A whole-portfolio batch cannot be a prerequisite for the first two real PRs.

### What the supervisor must deliver to owner at its first checkpoint

`current_main_sha`, `working_tree_clean`, `unmerged_worktrees`, `registry_count_and_mode`, `jmap_old_vs_new_org_ids`, `readme_inventory_verified_count`, `readme_refresh_skill_path_or_blocker`, `live_candidate_status_count`, `issue_bot_recent_remote_effects`, `sandbox_app_scope_status`, `foss_mcp_supervisor_preflight_verdict`, `active_taskcard`, `first_owner-authorized_PR_target`, `first_external_upstream_effect_or_exact_blocker`, `next_safe_command`. Every field must be observed or typed unknown; no copied green claim.

### Explicit acceptance of this handoff

This handoff succeeds only if the VS Code supervisor (a) checks the current true state rather than trusting snapshots, (b) demonstrates its own `foss-mcp`-style governance with negative control before worker dispatch, (c) preserves existing code, legal/customer material and readme-refresh assets by default, (d) produces distinct meaningful upstream R and L README PRs and safe issue effects, and (e) achieves unattended operation without rerunning the old all-repositories reseal/repair treadmill.
