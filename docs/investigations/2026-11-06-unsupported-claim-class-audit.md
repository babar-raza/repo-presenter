# What `real:unsupported_claim` and `real:contradiction` measure: a per-case audit (2026-11-06)

Follows `2026-11-06-reviewer-calibration-iteration-5.md` (NOT_PASSED). **No provider call was made.** The corpus was
loaded from the iteration-5 corpus cache the harness builds on its zero-call path (`run_reviewer_calibration.py
corpus|estimate @…/inputs.args --cache-corpus …/corpus5.pkl`); every one of the 113 registered real-defect cases (100
`unsupported_claim`, 13 `contradiction`; registration sha256 `3352ced4…`) was read: the labelled span, the base's
facts, and the upstream repository at the facts revision (every clone under `/home/user/upstream` is checked out at
exactly the case's `facts_revision`; read-only). Nothing in the registration, labels, thresholds or
`data/reviewer_calibration.json` was changed. Per the iteration-4 rule, reference (`ref:`) and live-README (`live5:`)
text stays local: those cases are named by id and README line only; own-bundle text is already committed
(`-data/own-repairs.json`, `-data/own5-repairs.json`) and is quoted.

Classes (one per case; the deciding question is what the **repository** says, then who wrote the sentence):

* **A** false: the repository contradicts it (wrong count, nonexistent or non-public type, a stub sold as a feature, a
  failing example, a wrong package name). A real defect; must be caught.
* **B** true: the source or project files show it; the facts extractor did not record it. A facts-coverage gap.
* **C** not decidable from the repository but plausible maintainer knowledge (platforms, editions, history, units).
  Valuable content under goals §5; a defect only when printed as the README's own claim instead of being recorded
  internally as attributed (R9).
* **D** generator-authored and unsupported (neither true nor false from the repository; template wording or an
  invented verification narrative).
* **E** label error (the sentence is fine).

"Origin" is whether the span (whitespace-normalised) occurs in the base's original live README (`inherited`) or not
(`generated`: written by this pipeline for `own:`/`own5:`, by the aspose.org readme-refresh for `ref:`).

## 1. Result

| Kind | n | A false | B true, facts miss it | C maintainer knowledge | D generated, unsupported | E label error |
|---|---|---|---|---|---|---|
| `real:unsupported_claim` | 100 | **13** (8 inh / 5 gen) | **69** (49 inh / 20 gen) | **14** (8 / 6) | **4** (1 / 3) | 0 |
| `real:contradiction` | 13 | **10** (8 / 2) | 1 (1 / 0) | 0 | 0 | **2** (1 / 1) |

**Of the 100 "unsupported claims", 69 are true.** The class mostly measures whether a reviewer will reject true
sentences that the extracted facts happen not to state. Only 17 (A + D) are defects a reviewer must catch; 14 (C)
belong to the disposition stage. The contradiction class is mostly sound (10 of 13 real).

### Examples (three per class)

| Class | Case | Sentence (own bases quoted) | Repository evidence |
|---|---|---|---|
| A | `own:cells-cpp/real:unsupported_claim:1` (L260) | "CellFormatValue represents the formatted value of a cell." | `Aspose.Cells.Foss.Cpp/include/aspose/cells_foss/CellFormatValue.h:12-40` (NumFmtId/FontId/FillId/BorderId: a style record) |
| A | `own5:note-python/real:unsupported_claim:0` (L455) | "…for all 39 public types." (same line also says 37) | `src/aspose/note/__init__.py:37` (`__all__` holds 33 names) |
| A | `ref:3d-python/real:contradiction:6` (L412) | (API-table row: Scene renders) | `aspose/threed/Scene.py:186-187` (`render` raises `NotImplementedError`) |
| B | `own:cells-go/real:unsupported_claim:0` (L58) | "…with automatic deduplication of identical styles during save." | `aspose/cells_foss/style.go:93`: the `Style` docstring says exactly this in its **second** sentence; the fact keeps only the first |
| B | `own:imaging-net/real:unsupported_claim:10` (L159) | "enum of the 14 detectable formats, plus `Unknown`…" | `src/Aspose.Imaging.Foss/ImageFormat.cs` (`Unknown` + 14 members) |
| B | `own5:imaging-net/real:unsupported_claim:2` (L248) | "`Microsoft.NET.Test.Sdk` 17.12.0, `xunit` 2.9.2, … used only by the test project." | `tests/Aspose.Imaging.Foss.Tests/Aspose.Imaging.Foss.Tests.csproj:12-14` (exact versions) |
| C | `own5:email-net/real:unsupported_claim:0` (L12) | "…runs on Windows, Linux, macOS, Docker containers, and serverless functions" | repo states only `net8.0` (`src/Aspose.Email.Foss/Aspose.Email.Foss.csproj:3`) |
| C | `own5:email-net/real:unsupported_claim:1` (L315) | Enterprise Edition adds IMAP/SMTP/POP3, TNEF, … | vendor knowledge; nothing in the repo |
| C | `own5:cells-typescript/real:unsupported_claim:0` (L239) | "requires Node.js 18 or later and TypeScript 5 or later" | `package.json:17` (`typescript ^5.9.3`, true); no `engines` field, Node 18 is the maintainers' statement |
| D | `own:cells-java/real:unsupported_claim:4` (L422) | "…183 public types organized into one module." | one Maven artifact, five packages, no `module-info.java`: template wording, neither true nor false |
| D | `ref:slides-net/real:unsupported_claim:1` (L68) | (claims every capability was exercised and XML-verified) | no verification record; every example fact UNRESOLVED (no dotnet SDK): an invented verification result (goals §4) |
| D | `ref:font-python/real:unsupported_claim:11` (L178) | (outputs said to mirror a demo site's fixtures) | no demo site or fixture generator in the repo |
| E | `own:html-python/real:contradiction:3` (L399) | "ValidityState provides information about the validity of a form control's value." | true: `src/aspose_html/dom/html/_form_elements.py:970-990` computes the flags; the "not implemented" limitation it was labelled against is stale |
| E | `ref:html-python/real:contradiction:7` (L186) | (JSContext example) | example matches the API (`dom/_node.py:708`, `dom/_document.py:1661`, `js/_quickjs_bridge.py:465,516`); the recorded ImportError is the `quickjs` import guard (`js/__init__.py:36-41`), i.e. the verification environment. Low confidence |
| B (contr.) | `ref:page-python/real:contradiction:0` (L7) | ("pure-Python") | package has no compiled sources; `pyproject.toml:11` requires `skia-python`, which the same paragraph discloses. Contested term (same call for `ref:`/`live5:cells-python` and `live5:psd-python`, which is stdlib-only and plainly true) |

### Fact kinds missing for the 70 B cases

| Missing fact kind | Cases |
|---|---|
| enum members (incl. save formats, overloads) | 17 |
| implementation behaviour not in a public docstring (buffering, defaults, getters that always return a constant, setters that throw, immutability, per-format handlers) | 13 |
| project/build/test files: test/dev dependencies (3), CMake settings and presets (2), Makefile targets (2), pytest config (1), file inventory (2), test-asserted behaviour (2) | 12 |
| dependency/package metadata: third-party licence notices (3), package build type "pure-Python"/stdlib-only (4), dependency purpose and native assets (1), runtime floor from `requirements.txt` (1), dependency inventory (1) | 10 |
| docstring text beyond the first sentence, and docstrings/comments of private modules and internal types | 9 |
| members that are not separate symbols: dataclass/pydantic fields, instance attributes, abstract-base members, module exports not re-exported | 7 |
| format-standard identity (`.xlsx` is ECMA-376, `.eml` is RFC 5322/MIME) | 2 |

The commonest single cause is the extractor's first-sentence docstring cut and its symbol-only view: enum members,
fields and overloads are code the repository plainly contains.

## 2. Who is responsible

| Class | n (uc + contr) | Responsible component | What it should do |
|---|---|---|---|
| A | 23 (13 + 10) | **reviewer**, and deterministic checks where the falsity is mechanical; for inherited A also the **reconciliation disposition** (keeping contradicted inherited text) | 20 of 23 are mechanically checkable once facts exist: wrong public-type counts (5), listed types that do not exist or are not exported (5), stubs that throw `NotImplemented`/`Unsupported` described as working (6), a CONTRADICTED example printed (2: `ref:note-python/…:4`, `ref:psd-python/…:8`, both already CONTRADICTED facts), package name / registry state (2, one caught). 3 need semantic judgement (`CellFormatValue`, `Row`, `AssetInfo` descriptions) |
| B | 70 (69 + 1) | **facts extractor** | record the fact kinds above; the claim then has a supporting fact and stops being a "defect" |
| C | 14 | **reconciliation disposition** (inherited) / **generator** (paraphrased maintainer text) | keep as `PRESERVE_ATTRIBUTED`, recorded internally (R9); not a reviewer claim finding |
| D | 4 | **generator** (prevent); reviewer (catch) | never emit counts or structure phrases not computed from facts; never narrate verification |
| E | 2 | **curation** (labels) | corrected in the next pre-registered corpus, not in iteration 5 |

## 3. Iteration-5 recall by responsibility (from the recorded results)

Computed from `results-it5.jsonl` (qwen3-next, all 113) and `results-it5-gptoss.jsonl` (gpt-oss, the 24 + 2 real
cases it reached), with the harness's own `on_target` rule (REJECT and a quote holding the defect text) and pipeline =
deterministic block or on-target. Nothing was re-scored or written as a status.

| Scope | qwen3-next reviewer | qwen3-next pipeline | gpt-oss reviewer | gpt-oss pipeline |
|---|---|---|---|---|
| unsupported, all (recorded) | 2/100 = 0.02 | 14/100 = 0.14 | 6/24 = 0.25 | 16/24 |
| unsupported, **A + D only** | **0/17 = 0.00** | 2/17 = 0.12 | 2/5 = 0.40 | 4/5 |
| unsupported, B (true claims) | 1/69 hit, 9/69 rejected | 9/69 | 2/15 hit, **14/15 rejected** | 9/15 |
| contradiction, all | 0/13 = 0.00 | 2/13 = 0.15 | 0/2 | 1/2 |
| contradiction, **A only** | **0/10 = 0.00** | 2/10 = 0.20 | 0/1 | 1/1 |
| **both kinds, A + D** | **0/27** | **4/27 = 0.15** | 2/6 | 5/6 |

Of the 4 qwen pipeline catches on A + D, only one is about the defect: `live5:psd-net/real:contradiction:0` by the
deterministic `claim_contradiction` rule. The other three (`own:cells-cpp` uc:1, uc:8, contr:13) are blocked by BC-07
(public text) for something else in the README. qwen3-next REJECTed 7 of the 23 A cases, each for another line.

So re-scoping the class does **not** rescue the reviewer: on the defects that really are its job, qwen3-next finds 0 of
27. What the re-scoping shows is that the gate is mostly asking for the wrong thing. 69 % of the unsupported-claim
cases are true sentences. A reviewer that "passes" them at ≥ 0.90 would have to reject true, sourced README content.
That conflicts with goals §5 and is the same behaviour that gives gpt-oss its 6/6 false rejects: it "caught" 14 of 15
true claims. The deterministic entailment check's 46 % clean-twin rejection has the same cause. Clean twins are full
of B-type sentences, and an entailment test against facts that lack those kinds cannot tell B from A.

## 4. Recommendation (no threshold lowered, no frozen label changed)

1. **Fix the facts extractor first** (70 cases, the largest lever). Add the kinds in §1: full docstrings, plus
   private/internal module docstrings flagged as such; enum members; dataclass/pydantic fields and overloads; export
   lists (`__all__`, crate re-exports, `index.ts`); test/dev dependencies and build files (csproj test projects,
   CMake, presets, Makefile, pytest config); licence-notice files; a "stub" polarity for members whose body only
   throws `NotImplemented`/`Unsupported`; computed public-type counts. Measure the gain with zero calls: rebuild the
   iteration-5 corpus with the new facts and count how many labelled spans gain a supporting fact (B) or a
   contradicting one (A).
2. **Turn mechanical A into deterministic checks**, the tier that already reaches 1.00 on every class it covers:
   count mismatch, non-exported or nonexistent API-table names, stub-described-as-working, and a CONTRADICTED example
   printed verbatim. That covers 20 of the 23 A cases. The last two facts already exist, yet nothing blocked them.
3. **Generator**: refuse uncomputed counts or structure phrases and any verification narrative (D).
4. **Disposition**: route C through `PRESERVE_ATTRIBUTED` (internal attribution, R9). Score C cases against the
   disposition stage, not the reviewer.
5. **Calibration**: iteration 5 stays as recorded (NOT_PASSED). The next pre-registered corpus is built after step 1.
   Labels are then judged against the richer facts, so a true claim becomes clean because a fact supports it, not
   because someone relabels it. The two E cases are corrected there, with this audit as the recorded reason.
   Real-defect recall is reported per responsible component (A + D for the reviewer and deterministic tier, C for
   dispositions) with the 0.90 threshold unchanged. Spend no more provider calls until steps 1–2 are measured
   offline: they move the cases the reviewer is actually failing (0/27) into a tier that does not depend on it.

## 5. Every case

Verdicts: R reject / A accept, `/hit` on target, `/pre` blocked by the deterministic stage; `-` not asked.

| Case | Class | Origin | README line | Repository evidence | Missing fact kind (B) | qwen3-next | gpt-oss |
|---|---|---|---|---|---|---|---|
| `own5:note-python/real:unsupported_claim:0` | A | generated | 455 | src/aspose/note/__init__.py:37 (__all__ has 33 names; the same README line says 37) |  | R | R/hit |
| `own5:pdf-java/real:unsupported_claim:0` | A | inherited | 1508 | src/main/java: 937 top-level + 305 nested public types; facts 1181; README says 1026 |  | A | - |
| `own:cells-cpp/real:unsupported_claim:1` | A | generated | 260 | Aspose.Cells.Foss.Cpp/include/aspose/cells_foss/CellFormatValue.h:12-40 (NumFmtId/FontId/FillId/BorderId: a style record) |  | R/pre | R/pre |
| `own:cells-cpp/real:unsupported_claim:8` | A | generated | 359 | Aspose.Cells.Foss.Cpp/include/aspose/cells_foss/Row.h:19-31 (only Height/IsHidden) |  | R/pre | R/pre |
| `ref:3d-typescript/real:unsupported_claim:27` | A | inherited | 315 | src/aspose/threed/AssetInfo.ts:3-7 (empty class: no author/application/date/unit/axis members) |  | A | - |
| `ref:cells-cpp/real:unsupported_claim:15` | A | inherited | 447 | no Workbook_Impl anywhere in the repository (grep over sources) |  | A | - |
| `ref:cells-cpp/real:unsupported_claim:7` | A | generated | 271 | Aspose.Cells.Foss.Cpp/include: 192 distinct public type definitions; the 197-row table includes a type that does not exist |  | A | - |
| `ref:cells-python/real:unsupported_claim:6` | A | generated | 247 | aspose/cells_foss/__init__.py:85 (__all__ 84 names; 160 classes over 72 files): 130 matches nothing |  | A | - |
| `ref:cells-rust/real:unsupported_claim:36` | A | inherited | 410 | src/Aspose.Cells_FOSS/Core/RowModel.rs:2 exists but is not re-exported by src/lib.rs:40-63 (not public API) |  | A | - |
| `ref:cells-rust/real:unsupported_claim:4` | A | inherited | 338 | src/lib.rs:40-63 (crate root re-exports about 115 types, not 213) |  | A | - |
| `ref:cells-typescript/real:unsupported_claim:20` | A | inherited | 205 | aspose_cells/xmldom.d.ts:2 (ambient declaration of the xmldom dependency, not a library class) |  | A | - |
| `ref:cells-typescript/real:unsupported_claim:29` | A | inherited | 206 | aspose_cells/types.ts:274 (a string-union type alias, not a class) |  | A | - |
| `ref:html-python/real:unsupported_claim:21` | A | inherited | 434 | src/aspose_html/js/__init__.py:46 (__all__ omits ModuleLoadPolicy; defined only in private _module_loader.py:39) |  | R | - |
| `live5:cells-python/real:unsupported_claim:0` | B | inherited | 10 | as ref:cells-python :0 (contested term) | package build type (pure/py3-none-any) | A | - |
| `live5:cells-python/real:unsupported_claim:1` | B | inherited | 23 | aspose/cells_foss/workbook.py:45,410,462 | enum members / save-format support | A | - |
| `live5:cells-python/real:unsupported_claim:2` | B | inherited | 142 | aspose/cells_foss/workbook.py:45,462 | enum members / save-format support | A | - |
| `live5:psd-python/real:unsupported_claim:0` | B | inherited | 10 | only stdlib imports under src/ (pytest in tests); requirements.txt | package build type / dependency inventory | A | - |
| `live5:psd-python/real:unsupported_claim:2` | B | inherited | 70 | requirements.txt:2 (python>=3.7) | runtime version floor from requirements.txt | A | - |
| `live5:psd-python/real:unsupported_claim:3` | B | inherited | 76 | only stdlib imports under src/aspose_psd_foss | dependency inventory (stdlib-only) | A | - |
| `own5:email-net/real:unsupported_claim:2` | B | generated | 319 | tests/Aspose.Email.Foss.Tests/Aspose.Email.Foss.Tests.csproj:10-16 (exact packages and versions) | test/dev dependencies | A/pre | R/pre |
| `own5:imaging-net/real:unsupported_claim:0` | B | generated | 216 | src/Aspose.Imaging.Foss/Formats/WmfFormatHandler.cs:47 ("assumes a conventional 96 DPI target") | implementation comments | A/pre | U/pre |
| `own5:imaging-net/real:unsupported_claim:1` | B | generated | 217 | src/Aspose.Imaging.Foss/Formats/DicomFormatHandler.cs:8-16 | internal-type docstrings | A/pre | R/pre |
| `own5:imaging-net/real:unsupported_claim:2` | B | inherited | 248 | tests/Aspose.Imaging.Foss.Tests/Aspose.Imaging.Foss.Tests.csproj:12-14 | test/dev dependencies | A/pre | R/pre |
| `own5:note-python/real:unsupported_claim:1` | B | generated | 467 | THIRD_PARTY_NOTICES.md:5-8 (ReportLab, BSD 3-Clause) | third-party license notices | R/hit | R/hit |
| `own5:note-python/real:unsupported_claim:2` | B | inherited | 470 | THIRD_PARTY_NOTICES.md:8 | third-party license notices | A | R |
| `own:cells-go/real:unsupported_claim:0` | B | inherited | 58 | aspose/cells_foss/style.go:93 (Style doc: "automatically deduplicates identical styles during save") | docstring beyond first sentence | A/pre | R/pre |
| `own:cells-go/real:unsupported_claim:1` | B | generated | 62 | aspose/cells_foss/streaming_reader.go:52 ("peak memory is proportional to the widest row") | docstring beyond first sentence | A/pre | R/pre |
| `own:cells-java/real:unsupported_claim:0` | B | generated | 51 | src/main/java/org/aspose/cells_foss/PictureCollection.java:27,37,49 (byte[]/InputStream/String overloads); ImageType.java:5-8 | method overloads; enum members | A | R |
| `own:cells-rust/real:unsupported_claim:2` | B | inherited | 84 | src/Aspose.Cells_FOSS/AutoShapeType.rs:3-6 (Rectangle, Star*, *Arrow variants) | enum members | R/pre | R/pre |
| `own:html-python/real:unsupported_claim:0` | B | generated | 49 | src/aspose_html/dom/_cascade.py:1-16 (!important > specificity > source order; inline as author (1,0,0); inheritance) | private-module / implementation docstrings | R | R/hit |
| `own:html-python/real:unsupported_claim:4` | B | generated | 544 | src/aspose_html/encoding/detection.py:52-60 (WHATWG sniff: BOM, override, meta charset prescan, default) | docstring beyond first sentence | R | R |
| `own:imaging-net/real:unsupported_claim:10` | B | inherited | 159 | src/Aspose.Imaging.Foss/ImageFormat.cs (Unknown + 14 members) | enum members | A | R |
| `own:imaging-net/real:unsupported_claim:18` | B | inherited | 198 | src/Aspose.Imaging.Foss/Formats/*FormatHandler.cs (frameCount: 1 except Gif/Ico/DjVu/Tiff) | implementation behaviour | A | R |
| `own:imaging-net/real:unsupported_claim:9` | B | inherited | 115 | src/Aspose.Imaging.Foss/ImageProbe.cs:43,139-144 (EnsureSeekable buffers into MemoryStream) | implementation behaviour | R | R |
| `ref:3d-java/real:unsupported_claim:5` | B | inherited | 474 | src/main/java/com/aspose/threed/Axis.java:3-10 (six constants incl. X_AXIS, NEGATIVE_Z_AXIS) | enum members | A | - |
| `ref:3d-net/real:unsupported_claim:6` | B | inherited | 575 | src/main/Aspose.ThreeD/Aspose/ThreeD/Formats/IOService.cs:65,86 (PlyReader/PlyWriter registered); roundtrip tests | internal implementation types | A | - |
| `ref:3d-python/real:unsupported_claim:23` | B | generated | 510 | aspose/threed/entities/TextureMapping.py:2-13 | enum members | A | - |
| `ref:3d-typescript/real:unsupported_claim:16` | B | inherited | 267 | src/aspose/threed/animation/Interpolation.ts:1-8 | enum members | A | - |
| `ref:barcode-python/real:unsupported_claim:17` | B | inherited | 221 | src/aspose_barcode_foss/_internal/models/options.py:28 QrEncodeMode; _internal/standards/qr/segments.py:42-48 | enum members | A | - |
| `ref:barcode-python/real:unsupported_claim:18` | B | inherited | 222 | src/aspose_barcode_foss/_internal/bootstrap.py:129 ("error correction levels L/M/Q/H") | enum members | A | - |
| `ref:barcode-python/real:unsupported_claim:4` | B | inherited | 56 | src/aspose_barcode_foss/_internal/parsers/qr.py:25,200 (versions 1-40) | internal constants / validation | A | - |
| `ref:cells-cpp/real:unsupported_claim:2` | B | inherited | 81 | Aspose.Cells.Foss.Cpp/src/aspose/cells_foss/Hyperlink.cpp:126-148 (CellReference / mailto: Email / External) | enum members / implementation behaviour | A | - |
| `ref:cells-go/real:unsupported_claim:0` | B | inherited | 7 | aspose/cells_foss/workbook.go:29,49 (ECMA-376); .xlsx is by definition ECMA-376 OOXML | format standard identity | A | - |
| `ref:cells-go/real:unsupported_claim:1` | B | inherited | 67 | aspose/cells_foss/style.go:93; workbook.go:84-85 | docstring beyond first sentence | A | - |
| `ref:cells-java/real:unsupported_claim:2` | B | inherited | 100 | src/main/java/org/aspose/cells_foss/AutoShapeType.java (39 constants = UNKNOWN + 38 presets); XlsxWorkbookDrawings.java:49 (preserved verbatim) | enum members / implementation behaviour | A | - |
| `ref:cells-java/real:unsupported_claim:3` | B | inherited | 104 | src/main/java/org/aspose/cells_foss/core/CellValueKind.java:19-20; XlsxWorkbookSerializer.java:762-777 | enum member docstrings / implementation behaviour | A | - |
| `ref:cells-net/real:unsupported_claim:11` | B | generated | 495 | src/Aspose.Cells_FOSS/SaveFormat.cs:14 (Xlsx only, no vbaProject handling anywhere) | save-format / unsupported-part behaviour | A | - |
| `ref:cells-net/real:unsupported_claim:6` | B | generated | 86 | License/SkiaSharp.LICENSE.txt (file exists) | third-party license notices | A | - |
| `ref:cells-net/real:unsupported_claim:7` | B | generated | 90 | src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj:54 SkiaSharp 2.88.8; SkiaSharp used only under src/Aspose.Cells_FOSS/Rendering/; per-OS native assets are SkiaSharp package metadata | dependency purpose / native-asset platform requirements | A | - |
| `ref:cells-python/real:unsupported_claim:0` | B | inherited | 7 | pyproject.toml:28-31; no compiled sources in aspose/ (contested term: pycryptodome is a compiled dependency) | package build type (pure/py3-none-any) | A | - |
| `ref:cells-python/real:unsupported_claim:4` | B | generated | 104 | aspose/cells_foss/workbook.py:45,69,462 (SaveFormat.TSV, .tsv extension map) | enum members / save-format support | A/pre | - |
| `ref:cells-typescript/real:unsupported_claim:73` | B | inherited | 233 | aspose_cells/html/htmlTable.ts:15-18 (exported interface, exactly 2 properties) | module-level exports not re-exported by the index | A | - |
| `ref:email-cpp/real:unsupported_claim:0` | B | inherited | 8 | CMakeLists.txt (no find_package/third-party link); tests/test_cfb.cpp:108 (deterministic round-trip); MIME EML | build dependencies / test-asserted behaviour | A | - |
| `ref:email-cpp/real:unsupported_claim:5` | B | inherited | 112 | CMakeLists.txt:9-10 | build settings | A | - |
| `ref:email-cpp/real:unsupported_claim:6` | B | inherited | 113 | CMakePresets.json:10-12 (default preset, generator Ninja) | build settings | A | - |
| `ref:email-net/real:unsupported_claim:0` | B | inherited | 62 | src/Aspose.Email.Foss/Msg/Mime/EmlMessageMapper.cs:101,274 (message/rfc822 MIME parsing) | format standard identity | A | - |
| `ref:email-net/real:unsupported_claim:2` | B | inherited | 97 | tests/Aspose.Email.Foss.Tests/Aspose.Email.Foss.Tests.csproj:10-16 | test/dev dependencies | A | - |
| `ref:email-net/real:unsupported_claim:6` | B | inherited | 217 | src/Aspose.Email.Foss/Msg/MsgStorageRole.cs:5 (Generic = 0) | enum members | A | - |
| `ref:email-python/real:unsupported_claim:0` | B | inherited | 78 | aspose/email_foss/msg/mapi_message.py:60-81,264,1096 (DEFAULT_SMTP_ADDRESS_TYPE, search keys) | implementation defaults | A | - |
| `ref:email-python/real:unsupported_claim:11` | B | inherited | 328 | aspose/email_foss/cfb/writer.py:58-64 (dataclass fields) | dataclass fields | A | - |
| `ref:email-python/real:unsupported_claim:12` | B | inherited | 329 | aspose/email_foss/cfb/writer.py:38-52 (children field, add_stream) | dataclass fields | A | - |
| `ref:font-python/real:unsupported_claim:24` | B | generated | 968 | Makefile:18-25 (test/lint targets run uv run ...) | build/test targets content | A | - |
| `ref:html-python/real:unsupported_claim:40` | B | inherited | 551 | pyproject.toml:43-45 ([tool.pytest.ini_options] pythonpath=["src"], testpaths) | test configuration | A | - |
| `ref:imaging-net/real:unsupported_claim:2` | B | inherited | 57 | src/Aspose.Imaging.Foss/Formats/ (14 handlers); WebPFormatHandler.cs:41,50 (VP8L/VP8X) | supported formats from handlers | A | - |
| `ref:imaging-net/real:unsupported_claim:20` | B | inherited | 172 | src/Aspose.Imaging.Foss/ImageInfo.cs:3-9 (sealed, get-only properties) | type modifiers / immutability | A | - |
| `ref:imaging-net/real:unsupported_claim:7` | B | inherited | 58 | HeaderValues.PositiveOrNull used by all 14 handlers (e.g. Formats/PngFormatHandler.cs:36-38) | implementation behaviour | A | - |
| `ref:note-python/real:unsupported_claim:24` | B | inherited | 393 | src/aspose/note/model.py:1130-1143 (IsBordersVisible slot/attribute) | instance attributes | R | - |
| `ref:page-python/real:unsupported_claim:11` | B | inherited | 485 | src/aspose/page/ps/output.py:40 (no_compression field); ps/fonts.py:67 | dataclass fields | A | - |
| `ref:page-python/real:unsupported_claim:22` | B | inherited | 540 | Makefile:34-48 (unittest discover -s tests; uv build; check: test build) | build/test targets content | A | - |
| `ref:psd-net/real:unsupported_claim:2` | B | generated | 71 | src/Aspose.PSD.FOSS.Test/FixtureDocumentTests.cs:37,76,107 (no-mutation save byte-for-byte) | test-asserted behaviour | A | - |
| `ref:psd-net/real:unsupported_claim:23` | B | generated | 321 | src/Aspose.PSD.FOSS/PsdImage.cs:61-69 (get => 6; set throws ArgumentOutOfRangeException), :86 internal IsPsb | property implementation | A | - |
| `ref:psd-net/real:unsupported_claim:27` | B | generated | 322 | src/Aspose.PSD.FOSS/Resources/PreservedResourceBlock.cs:42; PsdImage.cs:110-114 (ActiveLayer => Layers.FirstOrDefault()) | property implementation | A | - |
| `ref:psd-python/real:unsupported_claim:11` | B | generated | 322 | src/aspose_psd_foss/layers/layer.py:233-255 (setters raise NotSupportedException) | property implementation | A | - |
| `ref:psd-python/real:unsupported_claim:13` | B | generated | 336 | requirements.txt (python>=3.7 only); no pyproject.toml/setup.py; src/aspose_psd_foss_test/*tests.py | project-file inventory | A | - |
| `ref:slides-net/real:unsupported_claim:6` | B | generated | 108 | src/Aspose.Slides.Foss/ImageCollection.cs:108 (dedup of identical data) | implementation behaviour | A | - |
| `ref:tex-python/real:unsupported_claim:19` | B | inherited | 260 | src/aspose_tex/presentation/__init__.py:89-160,172,266,349 | member signatures of abstract/base classes | A | - |
| `ref:tex-python/real:unsupported_claim:20` | B | inherited | 267 | src/aspose_tex/presentation/__init__.py:547-558 | docstring beyond first sentence | A | - |
| `ref:tex-python/real:unsupported_claim:21` | B | inherited | 296 | src/aspose_tex/data/hyphenation/ (only .gitkeep); _fonts/font_manager.py:230-235 | project-file inventory | A | - |
| `ref:words-net/real:unsupported_claim:14` | B | inherited | 868 | Aspose.Words/Model/Document/LoadFormat.cs (Auto, Docx, Docm, ..., Markdown plus Doc, Rtf, Html, ...) | enum members | A | - |
| `ref:words-python/real:unsupported_claim:47` | B | inherited | 551 | aspose/words_foss/light_document_model.py:1104-1114 (pydantic fields styles, lists, sections) | model (pydantic) fields | R | - |
| `ref:words-python/real:unsupported_claim:5` | B | inherited | 80 | aspose/words_foss/saving.py:263-268 (ECMA376_2006, ISO29500_2008_TRANSITIONAL) | enum members | R | - |
| `ref:words-python/real:unsupported_claim:8` | B | inherited | 324 | aspose/words_foss/document.py:378-382 (format from output_path suffix) | docstring beyond first sentence | R | - |
| `live5:cells-net/real:unsupported_claim:0` | C | inherited | 9 | src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj:3 net8.0; OS list is maintainer statement (PDF export needs SkiaSharp native assets) |  | A | - |
| `own5:cells-typescript/real:unsupported_claim:0` | C | generated | 239 | package.json:17 typescript ^5.9.3 (TS 5 true); no engines field, Node 18 floor is maintainer statement (live README:102) |  | R/hit | R/hit |
| `own5:cells-typescript/real:unsupported_claim:1` | C | generated | 235 | Enterprise Edition capabilities: vendor knowledge |  | R | R |
| `own5:email-net/real:unsupported_claim:0` | C | inherited | 12 | no platform statement in repo; src/Aspose.Email.Foss/Aspose.Email.Foss.csproj:3 net8.0 only (Docker/serverless not derivable) |  | A/pre | R/hit/pre |
| `own5:email-net/real:unsupported_claim:1` | C | generated | 315 | Enterprise Edition capabilities: vendor knowledge, nothing in repo |  | A/pre | R/pre |
| `ref:3d-net/real:unsupported_claim:1` | C | inherited | 84 | round-trip tests exist (src/test/Aspose.ThreeD.Tests/roundtrip/SceneRoundTripTests.cs) but "full fidelity" across OBJ/STL is an unverifiable absolute |  | A | - |
| `ref:3d-typescript/real:unsupported_claim:15` | C | inherited | 265 | src/aspose/threed/animation/KeyFrame.ts:9,25-35 (time: number, unit unstated) |  | A | - |
| `ref:cells-go/real:unsupported_claim:10` | C | inherited | 462 | Enterprise Edition capabilities: vendor knowledge |  | A | - |
| `ref:cells-java/real:unsupported_claim:6` | C | inherited | 500 | Enterprise Edition capabilities: vendor knowledge |  | A | - |
| `ref:cells-rust/real:unsupported_claim:54` | C | inherited | 572 | Enterprise Edition capabilities: vendor knowledge |  | A | - |
| `ref:note-python/real:unsupported_claim:40` | C | inherited | 445 | Enterprise Edition capabilities: vendor knowledge |  | R | - |
| `ref:slides-net/real:unsupported_claim:14` | C | generated | 738 | cross-edition comparison measured 2026-08-16: maintainer history, not derivable from this repository |  | A | - |
| `ref:words-net/real:unsupported_claim:0` | C | generated | 9 | project history (DOC reverse engineering, WordML, Full2Foss): maintainer knowledge |  | A | - |
| `ref:words-net/real:unsupported_claim:2` | C | generated | 11 | provenance (genuine engine since 2003): maintainer knowledge |  | A | - |
| `own:cells-java/real:unsupported_claim:3` | D | inherited | 218 | src/main/java/org/aspose/cells_foss/{,core,packaging,validation,xml} (one Maven artifact, five packages, no module-info): template wording, neither true nor false |  | A | R/hit |
| `own:cells-java/real:unsupported_claim:4` | D | generated | 422 | same as :3 (generated restatement) |  | A | R |
| `ref:font-python/real:unsupported_claim:11` | D | generated | 178 | no demo site or generated fixtures in the repository (only cli.py:1868 web-optimize-demo command) |  | A | - |
| `ref:slides-net/real:unsupported_claim:1` | D | generated | 68 | no verification record in the repository; every example fact UNRESOLVED (no dotnet SDK): an invented verification claim |  | A | - |
| `live5:psd-net/real:contradiction:0` | A | inherited | 56 | NuGet registry fact package:published_version 26.10.0; samples/Aspose.PSD.NuGet.Samples.*; README:56 vs :66 contradict each other |  | A/pre | - |
| `own:cells-cpp/real:contradiction:13` | A | generated | 402 | Aspose.Cells.Foss.Cpp/src/aspose/cells_foss/xml/WorkbookXmlMapper.cpp:13,22 (throws UnsupportedFeatureException) |  | A/pre | R/pre |
| `ref:3d-java/real:contradiction:2` | A | inherited | 322 | src/main/java/com/aspose/threed/FileSystem.java:88-99,203,208 (zip FS constructible, read/write throw) |  | A | - |
| `ref:3d-java/real:contradiction:3` | A | inherited | 440 | src/main/java/com/aspose/threed/FileSystem.java:203,208 (UnsupportedOperationException) |  | A | - |
| `ref:3d-net/real:contradiction:5` | A | inherited | 448 | src/main/Aspose.ThreeD/Aspose/ThreeD/Utilities/Watermark.cs:10 (NotImplementedException) |  | A | - |
| `ref:3d-python/real:contradiction:15` | A | inherited | 768 | aspose/threed/utilities/Watermark.py:5-6 (NotImplementedError) |  | R | - |
| `ref:3d-python/real:contradiction:6` | A | inherited | 412 | aspose/threed/Scene.py:186-187 (render raises NotImplementedError) |  | R | - |
| `ref:font-python/real:contradiction:8` | A | generated | 110 | pyproject.toml:6 (name = "aspose-font-foss") |  | A | - |
| `ref:note-python/real:contradiction:4` | A | inherited | 112 | src/aspose/note/model.py:1157 (Title: Title / None); example recorded failing with AttributeError on SimpleTable.one |  | R | - |
| `ref:psd-python/real:contradiction:8` | A | inherited | 154 | src/aspose_psd_foss/resources/preservedresourceblock.py:11 (attribute is id, not resource_id) |  | A | - |
| `ref:page-python/real:contradiction:0` | B | inherited | 7 | pyproject.toml:11 (skia-python required); package itself has no compiled sources; the same paragraph discloses skia native parts (contested term) | package build type (pure/py3-none-any) | A | - |
| `own:html-python/real:contradiction:3` | E | generated | 399 | src/aspose_html/dom/html/_form_elements.py:970-990 (input computes value_missing/pattern/range flags); the "not implemented" limitation it is labelled against is stale |  | R | R |
| `ref:html-python/real:contradiction:7` | E | inherited | 186 | example matches the API (src/aspose_html/dom/_node.py:708, _document.py:1661, js/_quickjs_bridge.py:465,516); the recorded ImportError is the quickjs import guard (js/__init__.py:36-41), i.e. the verification environment (low confidence) |  | A | - |
