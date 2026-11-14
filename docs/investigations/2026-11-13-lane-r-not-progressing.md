# 2026-11-13: why Lane R does not certify. A manual audit of every Lane R failure to date

Backlog: BL-085 (owner, 2026-11-13: "Lane R is not progressing at all. Every failure must be categorised and reviewed
deeply to find appropriate solution and that solution must be integrated to pipeline for repeatability"). Scope
change, owner via supervisor: "Run manual audit on every lane R failure to date then present the findings and stop for
further discussion." **This document is the deliverable. It decides nothing.** The options in section 7 are for the
owner to discuss. Zero LLM calls were made. Nothing was pushed.

## 0. Headline numbers

* **Lane R certified now: 2 of 40 active cells.** Cells Go (seal from run 43473811437) and Email Python (seal from run
  43525320899). Both RECERTIFIED under main `0655d41`.
* **Hosted Lane R runs audited:** 27 runs since 2026-11-12 (`gh run list --workflow present.yml`; the earlier
  successes in that window were empty-target schedule fires). 25 runs failed Lane R, 2 sealed. This includes the two
  post-PR #69 runs (version set `f39787980017`). Two runs started at 2026-11-14T00:03Z were still in progress and are
  not audited.
* **Seals audited:** the latest seal of all 18 Lane R cells that have one, re-judged by zero-call
  `recertify --all --json --remote origin` on main `0655d41`. 16 are NEEDS_REPAIR.
* **Cells not reached:** 27 of the 40 active Lane R cells had **no hosted Lane R run at all** since 2026-11-12. Of those,
  22 have never been sealed; the other 5 hold a NEEDS_REPAIR seal (section 6).
* **Final blocking findings:** 193 across the 25 failed runs, and 245 on the 16 NEEDS_REPAIR seals. Classified into 25
  concrete classes (section 3).
* **Whack-a-mole, measured:** over every re-run of a cell, 20 blocking classes appeared, and **10 of them (50%) had
  never blocked that cell before**. 7 of those 10 came from checks or facts that landed on main between the two runs
  (section 4, S2). The candidate had not changed; the check had.

## 1. Method (reproducible, zero calls)

1. Hosted logs: `gh run view <id> --log --job <present job>` for every run above. The run artifacts could not be
   downloaded: the proxy refuses the blob host, so call stores and READMEs of failed attempts were not readable. Only
   the Lane R step's `blocking`, `finding`, `repair`, `restore` and `failure` lines were extracted. A run's *final*
   blocking set is:
   * the `blocking` lines when no LLM review was made;
   * the review's `finding` lines when it returned REJECT;
   * the JobError otherwise.

   In R,L runs, the Lane L step's findings were excluded.
2. Seals: `git fetch origin '+refs/repository-presenter-state/*:…'`, then
   `PYTHONPATH=src python -m repo_presenter.recertify --all --json --remote origin`, keeping Lane R.
3. Origins: each seal was re-rendered under current code (`render_readme` on the stored plan, units and dispositions).
   Each printed register quote, and each quoted BC detail, was traced to the unit that prints it: authored unit,
   authored type row, inherited unit (with its disposition), planned example, or the renderer from a fact's docstring
   (`repair.loop.renderer_printed_facts`).
4. Evidence for verdicts: the register row's own evidence (source `file:line@revision`, `data/readme_findings.json`),
   the fact that the check cites, and code reading of the check. For KIND_WORD findings, the facts were re-extracted
   locally: `present --stage facts` for 3D Python, Email .NET, Email C++, at the same revisions. The logged sentences
   were then replayed through the current `claim_findings` and the renderer's `kind_true_text`.
5. The classifier and its data (`extract_hosted.py`, `classify.py`, `hosted_lane_r.jsonl`, `recertify_lane_r.json`,
   `classified.json`) are left **uncommitted** in `docs/investigations/2026-11-13-lane-r-not-progressing/` on the
   branch's worktree, per the "commit only the doc" instruction. They are available for BL-084 (the in-pipeline
   classifier).

## 2. Every failed hosted Lane R run

The version set is `a6b436407f14` for every run except the last two, which ran on `f39787980017`. Classes are defined
in section 3. Repair outcome counts are taken from the run's `repair` lines. "noop" means the revision was identical
to the stage's own output. "ledger" means a changes-ledger refusal ("change R01 claims …"). "facts-defect" means
renderer-printed text that no revision can reach. "supersede-target" means "still SUPERSEDE_REDUNDANT, name another
section". "no-disp" means no stored disposition names the defect. "out-of-unit" means a rewrite of another unit was
refused.

| Run | Cell | main | Final outcome | Final blocking findings (class × n) | Repair attempts |
|---|---|---|---|---|---|
| 43473790998 | 3D .NET | 71825ae | no LLM review; BC-05, BC-17, BC-18 | LIVE_ITEM_LOST 12 (050.table ids Detect, GetFormatByExtension, …), REGISTER_ROW_REPRINTED 7, SUPERSEDED_SUBSTANCE_LOST 1 | repaired 2; supersede-target 2; noop 2; escalated 1 |
| 43473796319 | 3D Python | 71825ae | no LLM review; BC-05, BC-17, BC-18 | REGISTER_ROW_REPRINTED 6, LIVE_ITEM_LOST 4 (060.table, 010.list), SUPERSEDED_SUBSTANCE_LOST 1 | repaired 5; supersede-target 2; out-of-unit 2; noop 1 |
| 43473803090 | Cells .NET | 71825ae | no LLM review; BC-18 | REGISTER_ROW_REPRINTED 5 (Borders/Font "Gets or sets", Save bullet, samples "26.10.0", AGENTS.md "outlines how to contribute") | repaired 3; no-disp 1; noop 1 |
| 43473807336 | Cells C++ | 71825ae | no LLM review; BC-18 | REGISTER_ROW_REPRINTED 3 (FormulaException/StyleException, LoadFormat single member, "195 public types") | rationale refused 2; no-disp 1 |
| 43489976823 | 3D .NET | 2b95fb0 | REJECT 3 | NEVER_THROWN_CLAIMED_THROWN 1 (DriverException), RETURNS_CLAIMED_NOT_IMPLEMENTED 2 (RenderFactory, NurbsSurface.ToMesh) | repaired 4; noop, facts-defect, no-disp, out-of-unit 1 each |
| 43489981024 | 3D Python | 2b95fb0 | REJECT 10 | NEVER_THROWN_CLAIMED_THROWN 7 (Export/Import/Parse/Trial/Driver/Initialization/ShaderException), STUB_CLAIMED_WORKING 3 (.dae output) | repaired 8; supersede-target 2; noop, facts-defect, no-disp 1 each |
| 43489984973 | Cells .NET | 2b95fb0 | REJECT 1 | SAMPLES_REFERENCE_MISSTATED 1 | repaired 2; facts-defect 1 |
| 43489988826 | Cells C++ | 2b95fb0 | no LLM review; BC-02 | UNPROVEN_SOURCE_BUILD 1 (`cmake --build build`) | repaired 7 (BC-02 "repaired" as VERIFIED_PRESERVE, which still prints it); ledger 1 |
| 43506729349 | 3D .NET | b067b73 | REJECT 1 | NEVER_THROWN_CLAIMED_THROWN 1 (DriverException) | repaired 2; ledger, noop, facts-defect, no-disp, out-of-unit 1 each |
| 43506732935 | 3D Python | b067b73 | REJECT 51 | KIND_WORD_MISREAD_LIST 41, NEVER_THROWN_CLAIMED_THROWN 7, STUB_CLAIMED_WORKING 2, WRONG_BASE_TYPE 1 | repaired 6; ledger, supersede-target, facts-defect, no-disp 1 each |
| 43506738071 | Cells .NET | b067b73 | REJECT 1 | SAMPLES_REFERENCE_MISSTATED 1 | repaired 4; ledger 1; facts-defect 1 |
| 43513031042 | 3D .NET | f62e4af | no LLM review; BC-18 | REGISTER_ROW_REPRINTED 3 (`scene.Save(..., FBX7400Binary)`, `WavefrontOBJ`, `Version` bullet) | facts-defect 1; noop 1 |
| 43513034263 | 3D Python | f62e4af | REJECT 42 | KIND_WORD_MISREAD_LIST 41, STUB_CLAIMED_WORKING 1 | ledger 3; repaired 2; still-fails 1 |
| 43513037866 | Cells .NET | f62e4af | no LLM review; BC-18 | REGISTER_ROW_REPRINTED 1 (`- Save: Saves the workbook to an XLSX file…`, renderer hub bullet) | repaired 2; facts-defect 1 |
| 43516323114 | Cells C++ | f62e4af | REJECT 3 (LLM) | LLM_UNSUPPORTED_CLAIM 3 (F01–F03 scope_limitations) | ledger 2 (unit blanked); repaired 1 |
| 43516326802 | Cells Java | f62e4af | REJECT 1 | LIVE_ITEM_LOST 1 (live_readme_loss `mvn compile`) | repaired 2 |
| 43516330798 | Cells Python | f62e4af | no LLM review; BC-05, BC-07, BC-18 | SECTION_FIT_LICENSE_IN_SCOPE 2, KEPT_TEXT_FORMATTING 2, REGISTER_ROW_REPRINTED 1 (`style.font.color = "#FF0000"`) | repaired 4; ledger 1; no-disp 1 |
| 43516334907 | Cells Rust | f62e4af | JobError | JOB_OUTPUT_TRUNCATED (section_authoring > 8000 tokens) | none (job error) |
| 43520974296 | Cells TypeScript | f62e4af | no LLM review; BC-05 | SECTION_FIT_LICENSE_IN_SCOPE 1 | repaired 6; noop 3 |
| 43520977467 | Email .NET | f62e4af | REJECT 9 | KIND_WORD_MISREAD_LIST 9 (MapiProperty "… and a constructor") | repaired 3; ledger 2; still-fails 1 |
| 43520980658 | Email C++ | f62e4af | REJECT 3 | KIND_WORD_MISREAD_LIST 3 (directory_entry.is_root "field") | supersede-target 2; repaired 2; noop 1 |
| 43525324808 | HTML Python | f62e4af | no LLM review; BC-07, BC-18 | INTERNAL_WORDING_TYPE_ROW 12 ("NodeFilter class is a public symbol in aspose_html.dom."), REGISTER_ROW_REPRINTED 1 (QuickJS bridge) | noop 1; not-a-fact-value 1 (`el.setAttribute`); repaired 1 |
| **43529876835** | 3D .NET | **0655d41** | REJECT 4 | KEPT_EXAMPLE_BLOCK_UNPRINTABLE 2 (024/028.code_block "kept but not printed"), LIVE_ITEM_LOST 2 (`using Aspose.ThreeD;` blocks) | repaired 1 (moved to additional_examples); unrepairable 2 |
| **43529879702** | 3D Python | **0655d41** | REJECT 1 | STUB_CLAIMED_WORKING 1 (line 1087: ".dae output") | ledger 2 |

Repair outcomes across all 25 runs: 67 repaired, and 54 unrepairable or escalated. The unrepairable ones break down
as follows:

| Reason | Count |
|---|---|
| noop | 14 |
| ledger | 14 |
| supersede-target | 9 |
| facts-defect | 8 |
| no-disp | 7 |
| out-of-unit | 4 |
| still-fails | 2 |
| rationale refused | 2 |
| not-a-fact-value | 1 |
| other | 1 |
| escalated | 1 |

A "repaired" finding often reappears or is replaced by another class in the next round. Each targeted repair gets
two tries ("output rejected twice").

## 3. Classes, verdicts and evidence (Pareto)

The table is sorted by the number of cells blocked. The origin labels are:

* "type row": the authored sentence that describes one type in the Core API table;
* "inherited": maintainer README text kept as written;
* "renderer/fact": printed by the renderer from a fact's docstring.

| Class | Hosted findings (cells) | Seal findings (cells) | Rule | Origin | Verdict | Evidence checked |
|---|---|---|---|---|---|---|
| REGISTER_ROW_REPRINTED | 27 (6) | 112 (16) | BC-18 | On the 16 seals, under current code: authored unit 48, type row 3, inherited 44 (all VERIFIED_PRESERVE/MOVE or PRESERVE_ATTRIBUTED, none citing the row), renderer/fact 1 (3D .NET `Chunk`), renderer-transformed text 16 | Genuine defect: our text (authored) or maintainer text that we kept | Each row's register evidence. Examples: HTML `src/aspose_html/js/_dom_proxy.py:8-10@bf0f1e7a` (QuickJS bridge writes through `el.setAttribute`); Cells .NET `Style.Borders { get; private set; }`; 3D .NET `FileFormat.cs:66,83,347-350` (FBX7400Binary/WavefrontOBJ save throws); 2026-11-13 false-claim review |
| KIND_WORD_MISREAD_LIST | 94 (3) | 0 | claim_contradiction / BC-14 | Type rows | **Mixed: largely a false positive of our own check** at f62e4af. 3D Python: of 41 rows, 16 were the rule misreading verb/conjunct lists (BL-080's measurement); 25 were type rows truly calling properties methods. Email .NET and Email C++: all 11 sentences are false positives ("provides properties for Flags, … Value, and a constructor") | Replay on re-extracted facts at the same revisions. 3D Python: 25 distinct sentences, 11 still fire under the current rule, **0 after the renderer's `kind_true_text`**. Email .NET (8) and Email C++ (3): 0 fire under the current rule |
| LIVE_ITEM_LOST | 18 (3) | 5 (1) | BC-17 / live_readme_loss | Inherited | Genuine loss in our dispositions (3D .NET 050.table, 3D Python 060.table/010.list, PDF Java). False positive for Cells Java `mvn compile` (a register-withheld kept block; BL-082) | Repair answered VERIFIED_MOVE into additional_examples and was refused: "that section prints its own content … name another section" |
| NEVER_THROWN_CLAIMED_THROWN | 16 (2) | 0 | claim_contradiction | Renderer/fact (Core API docstrings, e.g. "This is raised in Scene.Open/Scene.Save when no licenses are applied.") | Genuine defect in the maintainers' docstrings, printed by us | `implementation:never_thrown.*` facts (BL-062). Gone from Lane R since f62e4af (BL-079: fact-true row) |
| SECTION_FIT_RESOURCE_IN_SCOPE | 0 | 20 (4) | BC-05 | Inherited resource lists (3D .NET 059.list, Cells C++ 053.list, Email .NET 055.list, Words 080.list) placed in Scope and Limitations | Genuine placement defect. The seals predate the BL-004 rule; no regenerated candidate shows it | Sealed dispositions |
| SECTION_FIT_LICENSE_IN_SCOPE | 3 (2) | 1 (1) | BC-05 | Authored scope sentence that also names the license | **Check needs owner judgement.** The sentence states package facts and also mentions the license (TypeScript: "The package version is 1.0.0 and is named excel-cells, distributed under the MIT l…"). That is a duplicate, not a falsehood | Run logs |
| SUPERSEDED_SUBSTANCE_LOST | 2 (2) | 3 (1) | BC-05 | Inherited tables | Genuine | Same loop as LIVE_ITEM_LOST |
| INTERNAL_WORDING_TYPE_ROW | 12 (1) | 89 (3) | BC-07 | Type rows ("X class is a public symbol in Y"; "Aspose.ThreeD.Utilities.Matrix4 is a public symbol with members …") | Genuine defect in our text. `_TYPE_OBJECTIVE` forbids the phrase; the model wrote it anyway; no check runs at authoring | `authoring.py` `_TYPE_OBJECTIVE`; `public_text._ANALYSIS`. HTML run: no repair was even attempted for BC-07 |
| STUB_CLAIMED_WORKING | 7 (1) | 0 | claim_contradiction | Authored (3D Python ".dae" output; line 1087 in both the f62e4af and post-#69 runs) | Genuine | `format:output.dae` reachable only through a stub (FbxExporter registered before Collada raises in `supports_format`). Repair refused twice by the changes ledger (BL-083) |
| MEMBER_NOT_OF_TYPE | 0 | 6 (2) | BC-14 | Inherited table row / authored | Genuine (3D .NET `GetExtra`/`SetExtra` bound to the GLTF `Property`; Cells .NET `FillPattern`/`Color`/`Border` as properties of `Style`) | Member facts |
| KEPT_EXAMPLE_BLOCK_UNPRINTABLE (new) | 2 (1) | 0 | disposition_coverage, plus live_readme_loss | Inherited example code blocks 024/028 (3D .NET) | **Rules disagree. No disposition can pass** (S4) | `placement.renders_verbatim` (`placement.py:102-109`) never prints a C# example fence verbatim, only through the plan's examples. BL-081 makes example:001/002 unselectable because the register refutes them. So VERIFIED_PRESERVE → "kept but not printed", and SUPERSEDE/omit → live_readme_loss. Zero-call `placements()` replay: 028.code_block → `owned_elsewhere` |
| SAMPLES_REFERENCE_MISSTATED | 2 (1) | 0 | claim_contradiction | Authored | Genuine | `project_file:samples.product_reference` (15 ProjectReference). Did not recur at f62e4af |
| KEPT_TEXT_FORMATTING | 2 (1) | 0 | BC-07 | Inherited (Cells Python 023.heading title case; 008.paragraph ends in ":" with nothing after it) | Defect in maintainer text, kept as written; the check is right | BL-083 |
| LLM_UNSUPPORTED_CLAIM | 3 (1) | 0 | LLM factuality | Authored scope_limitations (Cells C++) | Genuine ("supports only Clear, GetFilterColumns …"). This is the **only LLM-reviewer finding** that blocked a Lane R run in this window | Repair blanked the unit and the changes ledger refused it (BL-083) |
| RETURNS_CLAIMED_NOT_IMPLEMENTED | 2 (1) | 1 (1) | claim_contradiction | Authored limitation | Genuine (RenderFactory has no throw) | Body facts |
| WRONG_BASE_TYPE | 1 (1) | 2 (1) | claim_contradiction / BC-14 | Authored ("optional Mesh-derived entities") | Genuine (Entity's base is SceneObject); also a register row | Base facts |
| UNPROVEN_SOURCE_BUILD | 1 (1) | 0 | BC-02 | Inherited code block | Defect in maintainer text (an unproven build). Our repair kept it, so the repair was wrong | Build receipt "no build exited 0" |
| TYPE_COUNT_VS_LISTED | 0 | 1 (1) | BC-14 | Inherited (Cells C++ "195 public types is listed below", 157 rows) | Genuine | |
| SUPERSEDED_UNCITED, INTERNAL_WORDING_PROSE, KIND_WORD_TYPE_KIND | 0 | 1, 1, 3 | BC-04, BC-07, BC-14 | Seals only (PDF Java, PSD .NET "verified public surface", Cells .NET "Color a class") | Genuine | |
| JOB_OUTPUT_TRUNCATED | 1 (1) | 0 | JobError | Job error | Pipeline error | Cells Rust api_reference: 13 slots, 88 omittable entries, about 8,200 tokens. Fixed in BL-082, not yet re-run |

**Verdict totals.**

| Verdict | Hosted findings | Seal findings |
|---|---|---|
| Genuine defect in our text | ~70 | ~150 |
| Genuine defect in maintainer text kept or printed by us (inherited register rows, docstrings, formatting, unproven build) | ~45 | ~70 |
| False positive of our own check | ~70 (KIND_WORD at f62e4af, Cells Java live-loss) | 0 |
| Rule disagreement (no legal disposition) | 2 | 0 |
| Job error | 1 | 0 |

## 4. Structural root causes (deeper than the symptom)

**S1. The findings register binds only at the end, at BC-18. It never binds at authoring or reconciliation.** This is
the top class by cells (16 seals, 6 hosted cells).

* The authoring packet's `do_not_claim` is built only from CONTRADICTED/UNRESOLVED facts of kinds
  format/install/link/example (`authoring.py`, `authoring_tasks`). No register row ever reaches the author.
* `unit_checks` never tests a unit against the register.
* S4 cites register rows only for CORRECT_WITH_EVIDENCE paragraphs that hold commands
  (`dispositions._fold_register_corrections`). The withheld-form machinery (`must_correct.withheld_form`, applied by
  placement, BC-05/BC-17, the reviewer and the parity gate) exists, but it works only when the model happens to cite
  the row.
* The result: of the 112 register quotes printed by the 16 seals, 51 are authored and 44 are inherited units kept
  uncited. Each regeneration re-authors the same false sentence from the same facts. Example: HTML capability:6 "an
  optional QuickJS-backed bridge …", printed again in 43525324808. Repair then spends its two tries rediscovering it.

**S2. Checks and facts land between rounds before their producer-side counterpart.** This is the measured cause of
the whack-a-mole. Of the 10 classes that were new to a cell on a re-run:

* 5 came from commit `3e85cbf` (BL-062/066: new `implementation:*` facts and rule (j)), which landed between rounds 1
  and 2: NEVER_THROWN ×2, RETURNS_CLAIMED_NOT_IMPLEMENTED, STUB_CLAIMED_WORKING, SAMPLES_REFERENCE_MISSTATED.
* 2 came from commit `11e6937` (BL-063/065: member-kind and base rules), which landed between rounds 2 and 3:
  KIND_WORD_MISREAD_LIST, WRONG_BASE_TYPE.
* 1 is the new rule disagreement after BL-081: KEPT_EXAMPLE_BLOCK_UNPRINTABLE.
* Only 2 were new defects surfacing as older ones cleared: UNPROVEN_SOURCE_BUILD and LLM_UNSUPPORTED_CLAIM.

Each new check shipped without the matching producer change: no renderer correction, and no constraint in the
authoring packet. The renderer correction arrived one round later (BL-079, BL-080). The biggest single class by count,
KIND_WORD at 94 findings, was mostly a false positive of a newly added rule. **The check moved, not the candidate.**
`recertify --all` is a zero-call replay of every stored candidate, but it was not used as a pre-merge gate to show
what a new check would fail.

**S3. Repair cannot reach the defect often enough.** Of the 121 attempts, 54 did not repair. The unrepairable ones,
by structural cause:

* (a) 14 no-op revisions. The model returns the same text.
* (b) 14 changes-ledger refusals. The model blanks a unit or names an unchanged path (BL-083, open).
* (c) 9 supersede-target refusals. Repair is allowed to answer VERIFIED_MOVE into a section that "prints its own
  content", and is then refused.
* (d) 8 "facts defect" refusals for renderer-printed text. The ledger names this a dead end, and nothing downstream
  acts on it. BL-079 and BL-080 closed two shapes by hand (thrown rows, hub bullets). The Core API docstring row
  (`Chunk`) is still open.
* (e) 7 cases where no stored disposition names the defect.

Two tries per defect, with these refusal paths, explains why a cell needs several hosted rounds per class.

**S4. Rules disagree, so some units have no passing disposition.**

* 3D .NET, post-#69: inherited example code blocks 024/028 hold register-refuted lines. BL-081 makes their examples
  unselectable. `renders_verbatim` refuses to print an example fence outside the plan. disposition_coverage refuses
  "kept but not printed". live_readme_loss refuses "lost". The only consistent answer is OMIT citing the register row,
  and no prompt or deterministic fold offers it.
* The supersede-target loop (S3c) is the same shape: the repair's destination list and BC-05's supersession test
  disagree on which sections may take a moved unit.

**S5. Sequential discovery inside a run.** When any BC check fails, no LLM review is run ("a deterministic-only
verdict is never sealed"). The review stage's deterministic rules (claim_contradiction, disposition_coverage,
live_readme_loss) are not reported in that run, so their findings appear only in the next round. Zero-call recertify
runs both in one pass. A cell's full list of blockers is therefore knowable before a hosted run, but nothing computes
it.

**S6. The hosted loop concentrates on a few cells.** 25 failed Lane R runs went to 11 cells. 3D .NET, 3D Python, Cells
.NET and Cells C++ alone took 17 runs. 27 of 40 active cells got no Lane R run at all in the window: 22 never sealed,
plus Imaging .NET, Note Python, PDF Java, PSD .NET and Words .NET, which hold NEEDS_REPAIR seals. Even if every retried
cell certified, Lane R would reach 13, not 25.

**S7. The reviewer packet is not the bottleneck now.** In 25 runs, the LLM reviewer produced a blocking finding once
(Cells C++ F01–F03, genuine). Every other "REJECT" came from deterministic rules inside the review stage. The
2026-11-13 false-claim review finding still stands: 47 of 106 false claims sat on renderer lines the reviewer is never
shown. But in this window those were caught deterministically (BC-18, BC-14) rather than missed.

**Architectural or local?** Each item below can be fixed inside the existing components:

| Cause | Fix location |
|---|---|
| S1 | Packet records, a unit check and an S4 fold |
| S3(b) | BL-083 |
| S3(d) | Renderer fallback |
| S4 | A deterministic OMIT-with-register disposition, or one shared destination rule |
| S5 | A zero-call pre-run report |
| S6 | Cohort selection |

S2 is a process rule: a new check ships with its producer counterpart and a recertify-all diff. None of these needs a
new stage. S6 is in a file another worker owns (BL-084 scope).

## 5. What today's fixes demonstrably changed

| Change (merged on main) | Evidence of effect |
|---|---|
| BL-080: the kind-list rule reads sentences correctly, plus the renderer's `kind_true_text` on Core API rows | **3D Python: 42 → 1** (43513034263 at f62e4af → 43529879702 at 0655d41). The 41 KIND_WORD findings are gone. Zero-call replay on re-extracted facts: 25 distinct sentences, 0 findings after `kind_true_text`. The remaining 1 is STUB_CLAIMED_WORKING (.dae), refused by the changes ledger (BL-083). Email .NET's 9 and Email C++'s 3 KIND findings do not fire under the current rule (replay); hosted confirmation is pending |
| BL-079: never-thrown rows become a fact-true description | NEVER_THROWN: 7 (3D Python, b067b73) → 0 at f62e4af and after; 3D .NET 1 → 0 |
| BL-080: register-refuted hub bullets are not printed | Cells .NET's only blocker at f62e4af (`Save` bullet) no longer prints under recertify. 3D .NET `Version` bullet: gone post-#69 |
| BL-081: register-refuted examples are unselectable | 3D .NET: BC-18 on `scene.Save(…FBX7400Binary/WavefrontOBJ)` gone post-#69. **It also created KEPT_EXAMPLE_BLOCK_UNPRINTABLE (S4)** |
| BL-082: omitted-list cap; live-loss honours withheld blocks | Cells Rust truncation and Cells Java `mvn compile`: fixed in code, not re-run yet |
| Email Python | Sealed in 43525320899 (Lane R count 1 → 2) |

**Prototypes measured in this audit (uncommitted, per the scope change; patch kept in the worktree).** Each is an
option in section 7, not a decision.

* **P1. Renderer: a Core API row never prints analysis wording or a register quote.** The renderer strips the "X is a
  public symbol" lead and keeps the member list, else uses the fact-true fallback. Zero-call recertify of all 18 seals:
  BC-07 type rows 89 → 0, and Chunk's BC-18 is cleared. No new finding on any seal; the R10-relevant Cells Go and Email
  Python seals are unchanged. Detail counts: 3D .NET 87 → 33, Email .NET 35 → 9, Words 28 → 15. A first version that
  printed "Public class." lost 3D .NET 054.table's member substance and raised a new BC-05/BC-17. The kept-substance
  version does not.
* **P2. S4 fold: cite the register row for every kept inherited unit that prints a register quote,** when something
  is left to print. Zero-call replay on 16 seals: register quotes printed 108 → 81. **But** a full re-judgement with
  recertify's own `_evaluate_lane_r` shows 5 new findings:
  * 3 disposition_coverage: 3D .NET 028.code_block and 061.list; Cells Python 020.code_block.
  * 2 BC-17 section_coverage: PSD .NET 033.paragraph's "Samples" h2; Words 083.list's "Enjoying it? Star it" h2. The
    withheld part carried a heading.

  This is S4 again. Example code blocks and heading-bearing units would have to be excluded, or routed to
  OMIT-with-register.
* **P3. Authoring: register rows go into `do_not_claim`, and `unit_checks` rejects a unit that prints a register
  quote, with the row's truth.** Unit tests on HTML's QuickJS row only. Its effect needs LLM calls, so it is not
  measured here.

## 6. Per-cell status (40 active Lane R cells)

"Seal" is the recertify result on main 0655d41. "Last hosted" is the most recent hosted run since 2026-11-12.

| Cell | Seal | Last hosted | What blocks it now |
|---|---|---|---|
| Cells Go | RECERTIFIED | 43473811437 sealed | Certified |
| Email Python | RECERTIFIED | 43525320899 sealed | Certified (Lane L REJECT is separate) |
| 3D Python | NEEDS_REPAIR (BC-14, BC-18) | 43529879702 (0655d41) | 1 finding: .dae stub claim, authored; the changes-ledger refusal (BL-083) |
| 3D .NET | NEEDS_REPAIR | 43529876835 (0655d41) | KEPT_EXAMPLE_BLOCK_UNPRINTABLE 024/028, plus live_readme_loss (S4 rule disagreement) |
| Cells .NET | NEEDS_REPAIR | 43513037866 (f62e4af) | BC-18 `Save` bullet, fixed by BL-080 since then; not re-run on 0655d41 |
| Cells C++ | NEEDS_REPAIR | 43516323114 (f62e4af) | LLM F01–F03 unsupported scope claims; the repair blanked the unit (BL-083) |
| Cells Java | NEEDS_REPAIR | 43516326802 (f62e4af) | live_readme_loss false positive, fixed by BL-082; not re-run |
| Cells Python | NEEDS_REPAIR | 43516330798 (f62e4af) | License in Scope ×2; kept text formatting ×2; BC-18 `style.font.color` (BL-081 fix not re-run) |
| Cells Rust | NEEDS_REPAIR | 43516334907 (f62e4af) | JobError truncation, fixed by BL-082; not re-run |
| Cells TypeScript | NEEDS_REPAIR | 43520974296 (f62e4af) | License in Scope ×1 (SECTION_FIT_LICENSE_IN_SCOPE: does the check need owner judgement?) |
| Email .NET | NEEDS_REPAIR | 43520977467 (f62e4af) | KIND_WORD false positives, cleared under the current rule by replay; not re-run |
| Email C++ | NEEDS_REPAIR | 43520980658 (f62e4af) | KIND_WORD false positives, cleared by replay; not re-run |
| HTML Python | NEEDS_REPAIR | 43525324808 (f62e4af) | INTERNAL_WORDING_TYPE_ROW ×12 (P1 would clear it); BC-18 QuickJS, authored (S1; P3) |
| Imaging .NET | NEEDS_REPAIR (BC-18 ×5) | none | Not attempted. The seal fails on 5 register rows (3 authored, 2 inherited) |
| Note Python | NEEDS_REPAIR (BC-18 ×7) | none | Not attempted. P2 replay: 7 → 3 |
| PDF Java | NEEDS_REPAIR (BC-04/05/17/18) | none | Not attempted |
| PSD .NET | NEEDS_REPAIR (BC-07, BC-18 ×2) | none | Not attempted |
| Words .NET | NEEDS_REPAIR (BC-05/07/18) | none | Not attempted |
| 3D Java, 3D TypeScript, BarCode Python, Font Python, GIS .NET, Page Python, PDF Go, PDF Python, PDF .NET, PDF C++, PDF TypeScript, PSD Python, Slides .NET/C++/Java/Python, TeX Python, Words Python, OCR .NET, OMR Python, PSD Java, Words Java (22) | No seal | None since 2026-11-12 | **Never attempted by the hosted loop in this window.** No outcome to audit |
| Cells PHP | — | — | Inactive (R29: no extractor yet) |

## 7. Options for discussion (not decided)

The certified-count effects below are estimates. The assumptions are stated in each row.

| # | Option | Addresses | Trade-off | Expected effect on certified Lane R |
|---|---|---|---|---|
| O1 | Re-run the 9 retried cells whose last blocker is already fixed on main: Cells .NET, Cells Java, Cells Rust, Email .NET, Email C++, Cells Python, 3D Python after BL-083, and others | S2, S5 | Costs hosted runs. History says about 50% hit a new class | +3 to +6 |
| O2 | Point the cohort at the 27 unattempted cells, before more retries of the same four | S6 | Uncharted classes. The S1 fixes should land first, or the same BC-18/BC-07 classes recur | The only route to 25. With S1 fixed, perhaps 30–40% certify on the first or second run: +8 to +11, unverified |
| O3 | S1 at the source: P3 (register into the packet plus a unit check), P2 restricted to non-example units, P1 | S1, BC-07 | Changes request hashes, so all authoring is re-called on the next run of a cell (the next run needs new calls anyway). P2 needs an S4 rule for example blocks | Removes the top class by cells (16 seals, 6 hosted). Zero-call: BC-07 89 → 0; register quotes 108 → 81 before P3 |
| O4 | An OMIT-with-register disposition: a deterministic fold, accepted by disposition_coverage, live_readme_loss, BC-05 and BC-17, for units with no printable form | S4 | Drops maintainer text. R14 requires the decision to be recorded; the register row is the citation | Unblocks 3D .NET; prevents the supersede-target loop |
| O5 | A zero-call pre-run report: recertify-style full judgement (BC checks plus the review's deterministic rules) of the latest stored attempt, listing every class before a hosted run | S5, S2 | A small extension of recertify; needs the failed attempt's outputs stored where the session can read them (artifacts are unreadable through this proxy) | Fewer wasted rounds. Turns the 50% new-class rate into a pre-known list |
| O6 | Process rule: every new check or fact lands with its producer counterpart, plus a `recertify --all` diff in the PR | S2 | Slower merges | Prevents check-induced whack-a-mole (7 of 10 new classes) |
| O7 | Repair: BL-083 (a blank unit becomes a plan-level drop), a third try only for noop revisions, OMIT offered for supersede targets | S3 | More calls per defect | Cells C++ and 3D Python are the immediate cases |
| O8 | Owner rulings on two checks: SECTION_FIT_LICENSE_IN_SCOPE (is a license mention in Scope a defect?), and whether maintainer formatting defects (title case, dangling colon) in kept text block or are auto-corrected | R36(b)(4) | — | Cells TypeScript and Cells Python |

## 8. On record: the baseline, and how to measure against it

At the owner's direction (2026-11-14: "make analysis part of the main so it's on record and we can always measure
against it"), this audit is the Lane R baseline. Everything it was built from lives beside this document in
`docs/investigations/2026-11-13-lane-r-not-progressing/`:

| File | What it is |
|---|---|
| `hosted_lane_r.jsonl` | The frozen input: the Lane R `blocking`/`finding`/`repair`/`restore`/`failure` lines of every hosted present run audited (26 runs, 13 cells), extracted from the job logs by `extract_hosted.py` |
| `recertify_lane_r.json` | The frozen input: the latest seal of every sealed Lane R cell (18), re-judged with zero calls under main `0655d41` |
| `classify.py` | The classifier: rule, class (this document's vocabulary), printing origin, verdict, repair outcome |
| `classified.json` | Its output: one row per finding (193 hosted, 245 on seals) |
| `baseline.json` | The frozen headline: certified cells, attempts, findings and cells per class, repair outcomes. Never hand-edited; `measure.py --write-baseline` regenerates it from the frozen inputs and refuses to change it |
| `measure.py` | Compares any later state with the baseline, class by class (classes GONE, NEW, shrinking) |

`tests/test_lane_r_audit_baseline.py` fails CI if the baseline stops being reproducible from its inputs.

Baseline, 2026-11-14T00:00Z:
- **Certified Lane R:** 2 (Cells Go, Email Python).
- **Sealed Lane R cells needing repair:** 16 of 18.
- **Hosted Lane R runs:** 26, covering 13 cells.
- **Repairs:** 67 of 130 repaired.
- **Top hosted classes:** KIND_WORD_MISREAD_LIST 94, REGISTER_ROW_REPRINTED 27, LIVE_ITEM_LOST 18, NEVER_THROWN_CLAIMED_THROWN 16, INTERNAL_WORDING_TYPE_ROW 12.

To measure a later state:

```bash
gh run view <id> -R babar-raza/repo-presenter --log --job <present job id> > LOGDIR/<id>.log   # for each run to measure
python docs/investigations/2026-11-13-lane-r-not-progressing/extract_hosted.py LOGDIR > NEW/hosted_lane_r.jsonl
PYTHONPATH=src python -m repo_presenter.recertify --all --json --remote origin > NEW/recertify_all.json
python docs/investigations/2026-11-13-lane-r-not-progressing/measure.py --hosted NEW/hosted_lane_r.jsonl --recertify NEW/recertify_all.json
```

## 9. Gate state

Only this document is committed on branch `bl-085-lane-r-deep-review`. No code changes are committed, so the R10 gate,
the test suite, gatecli and the backlog check are as on main `0655d41`. During the audit, the uncommitted prototypes
were checked against all 18 seals by zero-call recertify: no new finding on any seal, and Cells Go and Email Python
still RECERTIFIED.

The scope change said to commit only this document, so no backlog item was added. BL-085 and the per-class items
(BL-086 onwards) are proposed in section 7 and await the owner's discussion.
