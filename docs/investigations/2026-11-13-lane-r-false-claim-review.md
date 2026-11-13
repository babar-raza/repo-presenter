# 2026-11-13 — Lane R false-claim review: 105 findings, 68 registered, 12 root-cause classes

Backlog: BL-003 (source: owner feedback 8640135b4c, "False claim is the biggest problem"). Rulings applied: R10, R14,
R36(b), R38 (Pareto, first principles), R40 (backlog integrity, honest reporting).

## What was reviewed

Five independent reviewer agents fact-checked the five Lane R candidates that certified under current code on
2026-11-13, each against its pinned source and the package registries:

| Repository | Revision | Seal | Findings | Registered |
|---|---|---|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-.NET | 52b0f00ebf28 | 03b940a46f7b | 25 | 19 |
| aspose-3d-foss/Aspose.3D-FOSS-for-Python | 65b1f577c0f1 | 4812255e83c2 | 24 (+1 added on re-verification) | 18 |
| aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | f71fe5595ebd | 269b6ae5d8f7 | 17 | 10 |
| aspose-email-foss/Aspose.Email-FOSS-for-.Net | 59125b4732df | e8cc8cca4d3a | 16 | 8 |
| aspose-words-foss/Aspose.Words-FOSS-for-.NET | 0d3f1add920f | 56668e8abf63 | 23 | 13 |
| **Total** | | | **105 (+1)** | **68** |

Verdicts: FALSE 36, MISLEADING 30, UNSUPPORTED 4, INTERNAL_WORDING 19, MISPLACED 16. Each reviewed README is
byte-identical to the sealed `README.md` (`git show <seal>:<revision>/README.md`, compared with `cmp`).

Inputs and decisions are kept with this document, one file per repository:
`docs/investigations/2026-11-13-lane-r-false-claim-review/<repository>.review.json`. Each item keeps the reviewer's
quote, verdict, truth and evidence, and adds `root_cause` (class below), `reverified`, and, where the supervisor changed
something, `review_quote`/`review_truth` (the original), `occurrences`, `register: false` + `skip_reason`.

## Registration (reproducible)

The rows were written through the register's own API. A small importer was added to `src/repo_presenter/readme_findings.py`
(`import_review`, CLI `python -m repo_presenter.readme_findings import`), so the step can be repeated, not done by hand.
It registers FALSE/UNSUPPORTED/MISLEADING items as OPEN `lane_r` rows. INTERNAL_WORDING and MISPLACED items are skipped,
because deterministic checks own those classes (BL-002, BL-004). The importer **refuses** any quote that is not printed
exactly `occurrences` times (default 1) in the sealed README, and then writes nothing. This is the 2026-11-13 lesson: the
bare `dotnet build` row also matched the correct build line and could never clear. Descriptions follow the a963daa
convention: `confirmed <verdict> claim: <quote[:90]>`.

```bash
git show 03b940a46f7b:52b0f00ebf28a0b4173921725ff170685ec2c502/README.md > /tmp/3dnet.md
PYTHONPATH=src python -m repo_presenter.readme_findings import --repository aspose-3d-foss/Aspose.3D-FOSS-for-.NET \
  --readme /tmp/3dnet.md --review docs/investigations/2026-11-13-lane-r-false-claim-review/Aspose.3D-FOSS-for-.NET.review.json \
  --date 2026-11-13
# (the same for the other four; output: registered 19/18/10/8/13)
```

`data/readme_findings.json` went from 72 rows to 140 rows. The diff only adds rows; no existing row changed.

### Re-verification (≥ 10 required; 36 done)

The supervisor cloned each repository at its pinned revision and checked 36 items against the source, plus the
registries via curl (nuget flat-container and nuspec, PyPI JSON). Every item marked `"reverified": true` was confirmed,
except the three below. Examples: `FileFormat.FBX7400Binary`/`WavefrontOBJ` are plain `new FileFormat(...)` instances
whose `CreateSaveOptions` is the base virtual that throws (FileFormat.cs:66,83,347-350); `NurbsSurface.ToMesh` returns a
placeholder grid and does not throw; `RenderFactory` has no throw. 3D Python's `Scene.save` raises NotImplementedError
for `.dae`, because `FbxExporter` (registered before Collada) inherits `Exporter.supports_format`, which raises. Its OBJ
writer writes a `str` to a `'wb'` file. `Style.Font`/`Borders` are `{ get; private set; }`. `AttachMethod*` are
`const int`. `DirectoryEntry.IsRoot/IsStorage/IsStream` are methods. `DocumentPositionMovement` is `public` only under
`#if CPLUSPLUS`. `Story.Shapes` is `internal`. NuGet lists Aspose.Words.FOSS 26.2.0 and 26.3.0. The Words nuspec declares
SkiaSharp, LibTiff.NET and Microsoft.Win32.Registry. SkiaSharp 2.88.8's nuspec has no Linux native-asset dependency.

**Dropped (3), with reasons:**

| Item | Reason |
|---|---|
| Words #12 "The suite covers 307 test files" (UNSUPPORTED) | **Refuted.** 307 is exactly the number of `.cs` files under `Aspose.Words.Tests/` that declare a test method (the NET suite rule in `core/ecosystems.py`, reproduced with grep at 0d3f1add920f). The reviewer's 310 also counted `[TestFixture]`-only files. |
| Words #9 "`System.Text.Encoding.CodePages` 7.0.0 … used by the .NET Standard 2.0 and .NET 8 targets" (MISLEADING) | **Not confirmed false.** Aspose.Foundation.csproj:81 references it for every target except net462. The line sits in the build-from-source list it documents (maintainer text, upstream README.md:113). The missing nuspec entry is a packaging matter. |
| Words #11 "- `ILRepack 2.0.46`" (MISLEADING) | **True line.** The defect is an omission (the test project's development dependencies). Registering the quote would force a true line out, so the omission is tracked as class K06 instead. |

**Quotes tightened or re-targeted (6), so no quote can match correct text:** 3D Python #6 (the whole "cannot detect or
dispatch … `RuntimeError` if you try" clause), #20 ("optional `Mesh`-derived entities, and materials") and #21 ("The
test suite, located in the tests/ directory, uses the standard-library unittest framework"); Words #13 ("come out as
placeholders (see what's not included)") and #14 ("The engine underneath … (see the story below)"); Cells #6. For Cells
#6, the reviewer quoted the true line "Requires .NET `net8.0`". The row quotes the actual misleading maintainer sentence
instead: "It runs on Windows, Linux, and macOS, and does not require … any native Office installation." Its truth says
Linux PDF export needs SkiaSharp.NativeAssets.Linux (csproj:54 SkiaSharp 2.88.8; SkiaSharp nuspec).

**Deliberate repeat (1):** 3D Python #23 "This is raised in Scene.Open/Scene.Save when no licenses are applied." The same
false row is printed in both API tables, so the row is registered with `occurrences: 2`.

**Added (1):** 3D Python prints the reviewer's #20 relation a second time in the member reference ("optional
`Mesh`-derived `Entity`, and materials"). It was found during re-verification and registered as MISLEADING.

**Not registered, and why:** 3D Python #3 ("could not be confirmed on PyPI") is internal wording (BL-002). It is not a
confirmed false claim: PyPI's project URL really points at `github.com/aspose-3d/Aspose.3D-for-Python`. The fix is BL-002's
ownership rule, not a register row. Email #8 ("which is what NuGet actually built and published from") is internal wording
and unverifiable rather than proven false (csproj 0.1.0, registry 26.7.0). 3D .NET #22 ("293 types") is internal wording;
the reviewer's own recount (294 + 3 delegates, one nested in an internal class) does not establish a single true number.

## Root-cause classes (Pareto, by pipeline cause, not by symptom)

Counts are over the 105 reviewer items (+1 added). "Not shown" is the number of items on lines that the independent
reviewer is never sent (`readme/review/scope.py::reviewable_lines`, measured on the sealed READMEs; 47 of 106).

| Class | Items | Registered | Not shown to reviewer | Responsible code | Smallest root fix |
|---|---|---|---|---|---|
| **K02 Behaviour/capability claimed beyond the real code path**: stubs reached through virtual dispatch or a dispatcher list, metadata-only types sold as features, "throws" claims for members that do not throw, doc comments of the commercial product ("raised when no licenses") | **29** | 29 | 11 | `readme/evidence/facts/source_detail.py` (implementation facts only for a body that throws directly); `readme/validation/surface_claims.py::_stub_findings` (rule (j) keys only on maintainer limitation statements); `readme/evidence/facts/formats.py` (direction facts ignore dispatch order) | Propagate `implementation: always throws` one hop: a static field built as the base type whose virtual throws (`new FileFormat(...)` → `CreateSaveOptions`), and an exporter list whose earlier entry raises in `supports_format`. Rule (j) fires on SUPPORTED implementation facts as well, and an inverse rule fails "X throws" when X's body has no throw. |
| **K12 Placement / duplication** (resource lists in Scope, license twice, install under Development) | 16 | 0 | 4 | `readme/composition/placement.py` | BL-004 (owned there) |
| **K11 Internal / pipeline wording** ("verified public surface", "this checkout", "is a public symbol with members", `text`→`TEXT` ×57) | 14 | 0 | 8 | `readme/composition/renderer.py:958,1084`; `composition/components/terminology.py::canonical_forms` (adds every file extension, `text` included, as an upper-case term) | BL-002. Add `text` to `WORD_EXTENSIONS`. |
| **K03 Member kind / accessor errors in API tables** (property, field or const called a method; static factory called a constructor; get-only property "Gets or sets") | 8 | 8 | 7 | `extractors/surface/extractor.py` (properties and fields emitted with `symbol_kind="method"`, accessor dropped) → `readme/composition/authoring.py::type_members` | Carry member kind (method/property/field/const) and the setter's accessibility into the `public_symbol` fact. Render and author from it. A surface_claims rule fails "Gets or sets" on a get-only property and "method" on a non-method. |
| **K04 Member mis-attribution** (names a member the type lacks, cross-binds two same-named types, wrong base type) | 8 | 8 | 5 | `readme/validation/surface_claims.py::_table_findings` (rule (i) checks type names only); authoring packets key types by simple name | Extend rule (i) to `Type.Member` pairs and "properties such as A, B" lists against that type's members. Key packets by qualified name. |
| **K05 Type counts include non-public types** (`#if CPLUSPLUS`-public, public struct nested in an internal class) | 6 | 5 | 4 | `extractors/surface/_vendor/aspose_extraction/tree_helpers.py::_in_excluded_preproc_branch` (excludes nodes inside a false branch, not a declaration whose *modifier* is chosen by `#if/#else`); C# type collection ignores enclosing-type visibility | Resolve the effective access modifier through `#if X public #else internal #endif`. A type is public only if every enclosing type is public. Rule (h) and the renderer count then agree with the real surface. |
| **K06 Dependencies from the project file, not the published package** | 6 | 2 | 4 | `extractors/platforms/net.py::_dependency_facts` (product csproj `PackageReference` only; `dependency:none` when it has none) | Prefer the published package's dependency groups (registry, already fetched for `package:published_version`) or the nuspec; include referenced projects; emit `dependency:none` only when the registry agrees. Flag transitive native-asset gaps (SkiaSharp on Linux). |
| **K07 Repository documents described without being read** (AGENTS.md as "contribution guidelines", samples "use version 26.10.0", stale PyPI readiness doc "confirms") | 6 | 6 | 0 | `readme/composition/authoring.py` documentation_resources slot binding (`bound["link:<id>"] = {<link fact>}`, the URL only) | A `document_summary` fact (title plus first heading or paragraph, from `source_detail`) bound to each link slot, and a claim check against it. |
| **K08 Unverified maintainer prose carried verbatim** (must-carry: platforms "Docker, serverless", "NuGet package landing soon", "see … below" after reordering, dangling "(see what's not included)") | 5 | 5 | 0 | `readme/reconciliation/dispositions.py::_settle_unresolved` (every unresolved maintainer unit kept PRESERVE_ATTRIBUTED unless a fact contradicts it); no cross-reference re-check after placement | (a) A deterministic cross-reference check: direction words against the rendered section order, and the anchor must exist. (b) Reuse Lane L's `stale_package_version` "not yet published" detector as a Lane R contradiction against `package:published_version`. (c) A host or platform claim with no supporting fact becomes R36's "state as unverified" alternative, never printed as verified fact. |
| **K01 Examples compiled, never executed** (.NET), and fragments never compiled | 3 | 3 | 3 | `extractors/platforms/net_examples.py::verify_net_examples` (compile-only bar, module docstring); `::_is_fragment` (an undeclared lower-case local → NOT_VERIFIED, which masked `Body.Shapes` being internal) | Run the compiled program (`dotnet run`, same isolated workspace, timeout). An unhandled API exception is CONTRADICTED; a missing input file stays UNRESOLVED (the Python rule). Lane R prints no NOT_VERIFIED fragment (BL-008 policy). |
| **K10 Pipeline-mandated template text** ("Enterprise Edition" for a product the repository calls the commercial Aspose.Words for .NET; self-linking resource bullets) | 3 | 1 | 0 | `readme/composition/components/shell.py` enterprise_relationship + BC-06 edition-name rule (`reconciliation/dispositions.py:1180`); documentation_resources self-link | Name the commercial product as the repository or nuspec does (fact-backed). Forbid a link slot that targets its own section. |
| **K09 Authored value transcription** (".NET Framework 4.62" from `net462`) | 1 | 1 | 0 | authored prose; no numeric check against TargetFrameworks facts | A claims rule: a .NET Framework version in prose equals the one derived from the `TargetFrameworks` fact. |
| **K00 Refuted on re-verification** | 1 | 0 | 1 | — | — |
| **Total** | **106** | **68** | **47** | | |

**Pareto reading.** Five classes (K02, K03, K04, K05, K06) are extractor or fact-model gaps. They hold 57 items (54%)
and 52 of the 68 registered false claims (76%). They share one root: the facts under-describe what the code does
(member kind, accessor, effective visibility, behaviour through dispatch, published dependencies). Every downstream stage
(authoring, deterministic checks, reviewer) trusts those facts. Fixing the fact model removes the class in every
repository at once. Repairing each README does not; that only repeats the symptom.

### Cross-cutting class: why the independent reviewer and M8 passed all of these

Measured on the five sealed `review_verdict.json` files:

1. **47 of 106 items are on lines the reviewer is never shown.** `readme/review/scope.py::reviewable_lines` excludes
   everything the renderer prints (API tables, dependency lists, type counts, fences, member bullets) by construction.
   That design was chosen on 2026-10 calibration evidence, because 130 of 159 earlier findings targeted renderer text.
   The consequence is that renderer-printed false facts are reviewed by nobody.
2. **The reviewer judges consistency with the facts, not with the source.** A unit's packet holds its text, the facts
   it may cite and an original-README excerpt (`readme/review/sectionwise.py::unit_packet`), and no code. A sentence
   that restates a wrong fact (member kind "method", 618 types, `dependency:none`, "a type named X exists, so X works")
   is "supported". The reviewer therefore shares the extractor's error, the common mode TC-017a's probes were meant to
   break.
3. **All five verdicts are ACCEPT with 0 findings** over 3, 3, 3, 5 and 5 unit reviews (Words: a ~1,700-line README
   in 5 units), `calibration_status: NOT_PASSED`, `acceptance_label: uncalibrated`. Observed fact: all five carry the
   same `reply_sha256` (a8982e5a…) for different request hashes. Interpretation, not verified: that is the canonical
   empty-findings reply.
4. **M8 is a prose-quality judge** (wording, R26). It is not a truth check, so it cannot catch any class above by design.

Smallest root fix (BL items below): the independent fact-check that found these 105 becomes a hosted pipeline stage
with source access, re-verifies each finding deterministically where it can, and writes register rows automatically.
Each confirmed class becomes a deterministic check.

## R10 — the honest outcome

With the 68 rows registered, BC-18 fails each of the five seals. These are genuine defects, not a regression of the
mechanism. Each seal is recorded NEEDS_REPAIR in `data/recertification_baseline.json`, with a justification naming
BC-18. No seal is deleted or demoted; the next Lane R run's targeted repair receives each quote and truth. Lane R's live
certified count falls from 5 to 0. This is a recorded demotion for genuine defects. `project/state.yaml` is resynced to
the live number.

## No recurrence (owner, 2026-11-13: "an already caught problem should not reappear")

BC-18 (`readme/validation/must_correct.py`) now treats every quoted register row of the repository and lane as a
permanent regression check, OPEN or RESOLVED (`readme_findings.regression_rows`). A row recorded as refuted (evidence
beginning `REFUTED`, `readme_findings.is_refuted`) never blocks: the two Email .NET 26.7.0 rows quote true text. An OPEN
row keeps its repair instruction and citation. A RESOLVED row printed again is handed its stored truth (it is not
citable; citations stay OPEN-only). A Lane L candidate is held to `lane_l` rows, a Lane R candidate to `lane_r` rows.
Tests: `tests/readme/validation/test_must_correct.py` (a resolved row's quote reappearing fails; a refuted row does not;
lane routing). The register currently has no RESOLVED row that is not refuted, so this change makes no certified seal
newly fail. The R10 gate confirms it (results below).

## Gate results (2026-11-13, worktree code, zero provider calls)

- `python -m repo_presenter.recertify --all --lane R --json`: the five seals are NEEDS_REPAIR on BC-18 only (19/18/10/8/13 printed rows).
- `python -m repo_presenter.recertify --gate --remote origin --base-baseline <origin/main baseline>`: `OK: no seal that re-certified in the baseline regressed (45 seals checked)`; certified under current code: lane R 0, lane L 26.
- No RESOLVED, non-refuted register row exists, so the no-recurrence change makes no seal newly fail (no R10 justification needed for it).
- Full suite: 5967 passed, 29 skipped, 1 deselected.
