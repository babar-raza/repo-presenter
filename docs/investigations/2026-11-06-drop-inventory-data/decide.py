"""Decide every distinct dropped item from evidence: deterministic rules + recorded manual reviews."""
import json, re, subprocess
from pathlib import Path
from functools import lru_cache

SP = Path('/tmp/claude-0/-home-user/542f6e2c-a780-567b-84f4-4e5f84153686/scratchpad')
CL = SP / 'clones'
it = json.load(open(SP / 'items.json'))
links_http = json.load(open(SP / 'link_status.json'))

def clone(x):
    return CL / f"{x['repository'].replace('/', '__')}@{x['revision'][:12]}"

def facts(x):
    return json.load(open(Path(x['bundle']) / 'facts.json'))['facts']

@lru_cache(None)
def public_names(bundle):
    out = set()
    for f in json.load(open(Path(bundle) / 'facts.json'))['facts']:
        if f['kind'] in ('public_symbol', 'enum_member') and f['polarity'] == 'SUPPORTED':
            v = str(f['value'])
            out.add(re.split(r'::|\.', re.split(r'[(\s]', v.strip(), maxsplit=1)[0])[-1].lower())
    return frozenset(out)

@lru_cache(None)
def readme(bundle):
    return (Path(bundle) / 'README.md').read_text(encoding='utf-8')

@lru_cache(None)
def readme_code_tokens(bundle):
    toks = set()
    for span in re.findall(r'`([^`\n]+)`', readme(bundle)):
        for part in re.split(r'[^\w]+', span.lower()):
            if part:
                toks.add(part)
    for m in re.findall(r'```.*?```', readme(bundle), re.S):
        toks.update(p for p in re.split(r'[^\w]+', m.lower()) if p)
    return frozenset(toks)

# --- language public surfaces (source of truth at the revision) ---
@lru_cache(None)
def rust_exports(c):
    lib = (Path(c) / 'src/lib.rs').read_text()
    names = set()
    for blk in re.findall(r'pub use api::\{(.*?)\};', lib, re.S):
        names |= {n.lower() for n in re.findall(r'\b([A-Za-z_]\w*)\b', blk) if n != 'as'}
    return frozenset(names)

@lru_cache(None)
def ts_exports(c):
    names = set()
    for p in ('aspose_cells/index.ts', 'aspose_cells/html/index.ts'):
        t = (Path(c) / p).read_text()
        for blk in re.findall(r'export\s+(?:type\s+)?\{(.*?)\}', t, re.S):
            for part in blk.split(','):
                part = re.sub(r'\btype\b', '', part).strip()
                if part:
                    names.add(part.split(' as ')[-1].strip().lower())
                    names.add(part.split(' as ')[0].strip().lower())
    return frozenset(names)

@lru_cache(None)
def cpp_header_decl(c, name):
    inc = Path(c) / 'Aspose.Cells.Foss.Cpp/include'
    p = subprocess.run(['grep', '-rnE', '-m1', rf'^\s*(class|struct|enum( class)?)\s+{re.escape(name)}\b[^;]*$', str(inc)], capture_output=True, text=True)
    return p.stdout.splitlines()[0].replace(str(c) + '/', '')[:120] if p.stdout else ''

def subject_surface(x, name):
    """(is_public, evidence) for a table row subject, from the language's own export mechanism."""
    c = clone(x)
    repo = x['repository']
    low = name.lower()
    if 'Rust' in repo:
        return low in rust_exports(str(c)), 'src/lib.rs:41-67 `pub use api::{...}` re-export list' + ('' if low in rust_exports(str(c)) else f' omits {name} (mod api is private, lib.rs:39)')
    if 'TypeScript' in repo:
        ok = low in ts_exports(str(c))
        return ok, 'aspose_cells/index.ts + aspose_cells/html/index.ts exports' + ('' if ok else f' omit {name}')
    if 'Cpp' in repo:
        d = cpp_header_decl(str(c), name)
        return bool(d), (f'declared in public header {d}' if d else f'{name} is not declared under Aspose.Cells.Foss.Cpp/include (implementation-only type)')
    ok = low in public_names(x['bundle'])
    ev = 'verified public surface (facts.json public_symbol/enum_member)'
    if ok:
        return ok, ev
    if 'Python' in repo:
        f, exported = py_private(x, name)
        if exported:
            return True, f'{name} defined in {f} and exported by a package __init__'
        ev = f'{name} is defined only in private module {f or "(not found)"} and no package __init__ exports it'
        if 'HTML' in repo and '/css/' in f:
            ev += '; src/aspose_html/css/__init__.py:3 "Public API: select() and element_matches(). All other names are internal."'
        return False, ev
    return ok, ev + f' does not include {name}'

def requalified(x, name, suffix):
    """A `Name-suffix` row is carried when the README prints `<qualifier>.Name` with a qualifier sharing a token with suffix."""
    want = {t.lower() for t in re.split(r'[_.]', suffix) if t}
    for span in re.findall(r'`([^`\n]+)`', readme(x['bundle'])):
        parts = span.split('.')
        if len(parts) > 1 and parts[-1] == name and want & {t.lower() for p in parts[:-1] for t in re.split(r'[_.]', p)}:
            return True
    return False

def py_private(x, name):
    """Python: (defining file, exported?) for a class name — exported when any package __init__ names it."""
    c = clone(x)
    p = subprocess.run(['grep', '-rlE', rf'^class {re.escape(name)}\b', str(c / 'src')], capture_output=True, text=True)
    f = p.stdout.splitlines()[0].replace(str(c) + '/', '') if p.stdout else ''
    q = subprocess.run(['grep', '-rlE', rf'["\']{re.escape(name)}["\']|import[^\n]*\b{re.escape(name)}\b', str(c / 'src'), '--include=__init__.py'], capture_output=True, text=True)
    return f, bool(q.stdout.strip())

FILLER = re.compile(r'^(class|struct|enum|interface|trait|type)\b( with [\w ,]+)?( in the .*api)?\.?$', re.I)

def norm(s):
    return re.sub(r'[^a-z0-9]+', '', s.lower())

def owed_spans(x):
    """Missing code spans naming a verified public member that the README prints nowhere."""
    pub = public_names(x['bundle'])
    toks = readme_code_tokens(x['bundle'])
    owed = []
    for m in re.finditer(r"span '([^']+)'", x['missing']):
        s = m.group(1)
        head = re.split(r'[(\s]', s.strip(), maxsplit=1)[0]
        last = re.split(r'::|\.', head)[-1].lower()
        if not last or not re.match(r'^[a-z_]\w*$', last):
            continue
        if last in pub and last not in toks:
            owed.append(s)
    return owed

# --- manual reviews (supervisor reading of item + candidate + source); index -> (decision, rule, evidence) ---
K, A = 'KEEP_DROPPED', 'READD'
M = {
 # code blocks
 5: (A, 'R-CORRECTION-PRINTED', 'CORRECT_WITH_EVIDENCE but the corrected PackageReference is printed nowhere (candidate prints only `dotnet add package Aspose.Cells.FOSS`); package:published_version 26.10.0 (nuget) gives the correction Version="26.10.0"'),
 18: (K, 'R-CONTRADICTED', 'example:002 FAILED (receipts); reproduced locally: g++ -std=c++17 -fsyntax-only with Aspose.Cells.Foss.Cpp/include fails "no match for operator[]" because the block omits #include "aspose/cells_foss/WorksheetCollection.h" (Workbook.h:26 only forward-declares it; operator[](std::string_view) is WorksheetCollection.h:44)'),
 44: (A, 'R-HARNESS', 'example:006 failed only on `undefined: generateSmallPNG`, the helper the block itself names; examples/picture/main.go:12-46 defines it and contains this exact code; the block is a labelled excerpt'),
 69: (A, 'R-HARNESS', 'example:005 RuntimeError is aspose/cells_foss/pdf_renderer.py:138-143 ("PDF export requires skia-python") because the harness lacked the optional dependency the block itself annotates (# Requires skia-python; README.md:39-43 install line); .csv/.md/.json/.pdf are registered in aspose/cells_foss/workbook.py:68-73'),
 507: (A, 'R-CODE-EVIDENCE', 'supervisor decision 2026-11-06 (first entry): src/Aspose.Imaging.Foss/Aspose.Imaging.Foss.csproj exists; build-from-source install path'),
 514: (K, 'R-CONTRADICTED', 'example:001 executed and FAILED with AttributeError on the maintainers\' own fixture testfiles/SimpleTable.one (page.Title.TitleText on a page whose Title is None, src/aspose/note/model.py:1156ff); executed evidence, not a harness artifact'),
 548: (K, 'R-VERSION-REPLACED', 'candidate README.md:60-66 prints the same Maven <dependency> with <version>26.9.0</version> = package:version (pom.xml) = package:published_version (maven); only the stale 26.6.0 is gone'),
 549: (K, 'R-VERSION-REPLACED', 'candidate README.md:70-71 prints `implementation \'org.aspose:aspose-pdf-foss:26.9.0\'` (package:published_version 26.9.0); only the stale 26.6.0 is gone'),
 612: (K, 'R-VERSION-REPLACED', 'candidate README.md:66 prints the verified `dotnet add package Aspose.3D.FOSS` (install_command:dotnet) and its lead-in names version 26.1.0 (package:version); the pin is carried in prose'),
 618: (A, 'R-CODE-EVIDENCE', 'unverified (UNRESOLVED), not contradicted; every identifier exists: Scene.cs, Shading/LambertMaterial.cs, Entities/Box.cs, FileFormat.FBX7400Binary (FileFormat.cs), DiffuseColor (MaterialTests.cs)'),
 620: (A, 'R-CODE-EVIDENCE', 'unverified, not contradicted; Scene.FromFile (Scene.cs:314), FileFormat.WavefrontOBJ (FileFormat.cs:83)'),
 621: (A, 'R-CODE-EVIDENCE', 'unverified, not contradicted; Scene.FromFile(string, FileFormat) Scene.cs:314, RootNode.ChildNodes'),
 623: (A, 'R-CODE-EVIDENCE', 'unverified, not contradicted; PbrMaterial.FromMaterial(Material) Shading/PbrMaterial.cs:154'),
 625: (A, 'R-CODE-EVIDENCE', 'unverified, not contradicted; ObjLoadOptions (Formats/FormatOptions.cs), FlipCoordinateSystem / NormalizeNormal FormatOptions.cs:26,42, Scene.Open(string, LoadOptions) Scene.cs:226'),
 626: (A, 'R-CODE-EVIDENCE', 'unverified, not contradicted; ColladaSaveOptions (Formats/FormatOptions.cs), Box, CreateChildNode'),
 627: (A, 'R-CODE-EVIDENCE', 'unverified, not contradicted; FileFormat.cs:182 throws ArgumentException("Unsupported file format: ...") for an unknown extension, exactly what the block catches'),
 642: (A, 'R-CODE-EVIDENCE', 'src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj exists; the clone URL is the repository itself'),
 644: (A, 'R-CODE-EVIDENCE', 'src/converter/Converter.csproj exists (PackageId Aspose.3D.Converter, line 10)'),
 # prose and list items
 1: (A, 'R-PROSE-VALID', 'platform claim consistent with src/Aspose.Cells_FOSS/Aspose.Cells_FOSS.csproj (net8.0, no Office interop reference); printed nowhere in the candidate'),
 2: (A, 'R-PROSE-VALID', 'csproj TargetFramework is net8.0 only (package:target_framework); migration note printed nowhere'),
 3: (A, 'R-PROSE-VALID', 'same: upgrade guidance for net8.0-only package; printed nowhere'),
 4: (K, 'R-CARRIED', 'candidate prints "exports workbooks to PDF using `PdfSaveOptions` ... and the `SaveFormat` enumeration"'),
 7: (K, 'R-LINK-DEAD', 'RELEASE_NOTES_V26.10.0.md does not exist at the revision (link_target CONTRADICTED)'),
 8: (A, 'R-PROSE-VALID', 'true at the revision: the repository root has no tests/ directory (Aspose.Cells_FOSS.sln, License, documentation, samples, src only)'),
 9: (A, 'R-PROSE-VALID', 'true at the revision (no test project); maintainer caveat about coverage printed nowhere'),
 10: (K, 'R-CARRIED', 'candidate links [MIT License](LICENSE.txt); LICENSE.txt exists at the root, same license'),
 13: (A, 'R-PROSE-VALID', 'opening claims (MIT-licensed, no Microsoft Excel required) printed nowhere; candidate opening is a generated summary'),
 14: (A, 'R-PROSE-VALID', 'Aspose.Cells-compatible API shape and dependency-free C++17 (CMakeLists.txt:4 CMAKE_CXX_STANDARD 17) printed nowhere'),
 16: (A, 'R-PROSE-VALID', 'NuGet package Aspose.Cells.Cpp.FOSS is real (nuget.org 200; package:distribution fact); Windows-only/MSVC restriction is maintainer platform knowledge printed nowhere, nothing contradicts it'),
 17: (K, 'R-POSITIONAL', 'positional lead-in ("collected below") for a section whose only example is contradicted (example:002)'),
 19: (K, 'R-CARRIED', 'candidate prints "from a path or an in-memory `std::vector<std::uint8_t>` stream via one of `Workbook`\'s" constructors'),
 35: (K, 'R-CARRIED', 'candidate prints the limitation with `UnsupportedFeatureException`; only the message literal is gone'),
 36: (A, 'R-LINK-RESOLVES', 'Aspose.Cells.Foss.Cpp.Tests/README.md exists; printed nowhere'),
 38: (A, 'R-PROSE-VALID', 'pure-Go, ECMA-376, no third-party dependency (go.mod has no require block) - opening claims printed nowhere'),
 40: (K, 'R-CARRIED', 'Cells.Get/Cells.Set with A1-style references and the four value types are printed; only the second example token "B2" is gone'),
 42: (K, 'R-CARRIED', 'candidate prints StreamingReader.ProcessRows and "keeping memory proportional to one row\'s width"'),
 46: (K, 'R-CARRIED', 'printed verbatim except `Worksheet.Cells()` rendered as `Worksheet.Cells`'),
 47: (K, 'R-CARRIED', 'printed: A1-style only, tuple/array indices unsupported'),
 48: (K, 'R-LEADIN', 'lead-in of the test command, which the candidate prints (go test ./...)'),
 49: (A, 'R-PROSE-VALID', 'true at the revision: examples/go.mod:7 `replace github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go/v26 => ../` and require v26.0.0; maintainer build guidance printed nowhere'),
 50: (A, 'R-PROSE-VALID', 'same unit: actionable fix for the examples module version; printed nowhere'),
 51: (A, 'R-PROSE-VALID', 'true: examples write to outputfiles/ (examples/picture/main.go:52 "outputfiles/picture.xlsx", run from examples/); printed nowhere'),
 53: (K, 'R-CARRIED', 'printed in Scope and Limitations (A1-style only)'),
 58: (A, 'R-PROSE-VALID', 'Worksheet.setTabColor/setZoom etc. exist in src/main (public); row/column sizing, hiding, outline grouping printed nowhere'),
 59: (A, 'R-PROSE-VALID', 'CalculationProperties and stored error values (#N/A, #VALUE!, #REF!) printed nowhere; candidate keeps only "not a full calculation engine"'),
 60: (K, 'R-CARRIED', 'candidate prints "Requires Java `17` (`maven.compiler.target` in `pom.xml`)"'),
 61: (K, 'R-CARRIED', 'candidate lists `org.junit.jupiter:junit-jupiter 5.10.2` under Development Dependencies (test-only by placement)'),
 62: (K, 'R-CARRIED', 'candidate lists `org.apache.poi:poi-ooxml 5.3.0` under Development Dependencies'),
 67: (A, 'R-PROSE-VALID', 'pure-Python, no Microsoft Excel required - printed nowhere (candidate opening is generated)'),
 72: (K, 'R-LINK-DEAD', 'RELEASE_NOTES.md does not exist at the revision (link_target CONTRADICTED)'),
 74: (A, 'R-PROSE-VALID', 'what each crate is for (Cargo.toml dependencies) and that OOXML packaging is implemented in-crate - candidate lists crate names only'),
 76: (K, 'R-CARRIED', 'candidate prints "`aspose-cells-foss-rust` is not published on crates.io yet"'),
 77: (K, 'R-CARRIED', 'CORRECT_WITH_EVIDENCE: candidate prints the git-dependency install for Cargo.toml'),
 78: (A, 'R-PROSE-VALID', 'dependency purpose (zip 0.6 = XLSX container) printed nowhere; candidate lists `zip 0.6` only'),
 79: (A, 'R-PROSE-VALID', 'dependency purpose (roxmltree 0.20 = part XML parsing) printed nowhere'),
 80: (K, 'R-CARRIED', 'both links (samples/, samples/README.md) are printed in Documentation & Resources'),
 87: (K, 'R-COUNT', '"213 public types" is not the reachable surface: src/lib.rs:41-67 re-exports ~150 names (mod api is private); the count is contradicted'),
 197: (K, 'R-CARRIED', 'candidate prints `LoadOptions { try_repair_package: true, try_repair_xml: true, ..LoadOptions::default() }`'),
 201: (K, 'R-CARRIED', 'candidate prints "`WorksheetsMut.remove_at` returns a CellsError::Unsupported error"'),
 202: (A, 'R-PROSE-VALID', 'maintainer scope caveat (not a complete Aspose.Cells match, early-stage) printed nowhere'),
 203: (A, 'R-PROSE-VALID', '.github/workflows/ci.yml exists; the job list (fmt, check, clippy, test, sample smoke tests, cargo bench) printed nowhere; candidate prints only the OS matrix'),
 204: (A, 'R-PROSE-VALID', 'every named file exists in samples/ (basic.rs ... document_properties.rs); printed nowhere'),
 205: (A, 'R-PROSE-VALID', '.github/workflows/pages.yml exists; cargo doc / GitHub Pages guidance printed nowhere'),
 207: (A, 'R-PROSE-VALID', 'opening: .xlsx (SpreadsheetML) without Microsoft Excel - printed nowhere'),
 225: (K, 'R-CARRIED', 'candidate prints Workbook as entry point with its worksheets collection and Worksheet/Cell/Style classes'),
 303: (K, 'R-CARRIED', 'printed verbatim with qualified names (Workbook.toCsv ...)'),
 304: (A, 'R-LINK-RESOLVES', 'agents.md exists at the repository root; printed nowhere'),
 306: (K, 'R-CARRIED', 'CORRECT_WITH_EVIDENCE (name spelling): candidate opening states MSG/EML read-write, CFB inspection, native implementation'),
 307: (A, 'R-PROSE-VALID', 'no Outlook installation needed, service/desktop/CLI fit: printed nowhere (dependency half is printed)'),
 312: (K, 'R-CARRIED', 'candidate prints SetProperty/GetPropertyValue beyond the typed members'),
 313: (K, 'R-CARRIED', 'printed (AddRecipient, AddAttachment, AddEmbeddedMessageAttachment)'),
 314: (K, 'R-CARRIED', 'printed (MapiMessage.LoadFromEml, SaveToEml, native MIME)'),
 315: (A, 'R-PROSE-VALID', 'behaviour of ValidationIssues (populated by strict parsing on structural anomalies) printed nowhere; only the member signature is listed'),
 316: (K, 'R-CARRIED', 'candidate prints the package id `Aspose.Email.Foss` with version'),
 317: (A, 'R-PROSE-VALID', 'runs on Windows, Linux, macOS, Docker, serverless - named as a true loss in validation/supersession.py docstring; printed nowhere'),
 318: (K, 'R-CARRIED', 'candidate prints the csproj path with no PackageReference and native MSG/EML handling'),
 319: (K, 'R-POSITIONAL', 'positional lead-in ("beyond the Quick Start example above"); supersession.exempt positional_only'),
 321: (A, 'R-PROSE-VALID', 'CfbReader for diagnosing damaged/non-standard files - named as a true loss in validation/supersession.py docstring; printed nowhere'),
 322: (K, 'R-CARRIED', 'candidate prints "The verified public surface has 29 types"'),
 328: (K, 'R-CARRIED', 'printed in Scope and Limitations'),
 336: (K, 'R-CARRIED', 'JSContext bridge printed; document.querySelector/window.getComputedStyle are JavaScript-side names, not Python public symbols'),
 337: (A, 'R-PROSE-VALID', 'install-from-source mechanism (PYTHONPATH; pyproject.toml [tool.pytest.ini_options] pythonpath = ["src"]) printed nowhere; candidate only points back to Installation'),
 338: (K, 'R-CARRIED', 'candidate prints quickjs>=1.19,<2 behind the js extra'),
 342: (K, 'R-COUNT', 'count + positional pointer to the module table; the candidate prints its own API table'),
 485: (K, 'R-CARRIED', 'printed verbatim except the private function names `_matches_pseudo_class`, `_pseudo_not` (internal)'),
 486: (A, 'R-PROSE-VALID', 'every named test directory exists under tests/ (test_html ... test_file_io.py); printed nowhere'),
 491: (A, 'R-PROSE-VALID', 'the DIRM-vs-FORM:DJVU distinction (counts pages, not dictionaries/thumbnails) printed nowhere'),
 492: (A, 'R-PROSE-VALID', 'AVIF/HEIC ispe/pitm/ipma/ipco dimension rule and brand detection printed nowhere'),
 493: (A, 'R-PROSE-VALID', 'ImageInfo values are positive or null (never zero/negative) - printed nowhere'),
 496: (K, 'R-CARRIED', 'candidate prints the csproj path with no PackageReference'),
 497: (A, 'R-VERSION', 'tests/Aspose.Imaging.Foss.Tests/Aspose.Imaging.Foss.Tests.csproj:12-14 pins Microsoft.NET.Test.Sdk 17.12.0, xunit 2.9.2, xunit.runner.visualstudio 2.8.2; versions printed nowhere'),
 498: (A, 'R-VERSION', 'Aspose.Imaging.Foss.Tests.csproj:11 coverlet.collector 6.0.2; version printed nowhere'),
 502: (A, 'R-LEADIN', 'lead-in of the unseekable-stream example the candidate prints; its explanation (non-seekable streams are buffered internally) printed nowhere'),
 503: (A, 'R-PROSE-VALID', 'indirect/truncated DJVM reports FrameCount null - printed nowhere (rest of the item is printed)'),
 505: (K, 'R-CARRIED', 'candidate prints TargetFrameworks netstandard2.0;net8.0'),
 506: (A, 'R-LEADIN', 'lead-in of inherited_unit:018.code_block, which is READD (first decision); a lead-in is kept with its block'),
 513: (A, 'R-PROSE-VALID', 'build/twine role (release tooling, not needed to use or test) printed nowhere'),
 519: (A, 'R-PROSE-VALID', 'aspose.note._internal is an implementation detail (src/aspose/note/_internal exists) - the warning half is printed nowhere'),
 534: (K, 'R-CARRIED', 'candidate prints License.SetLicense() and Metered.SetMeteredKey() as no-ops'),
 535: (K, 'R-CARRIED', 'same'),
 539: (K, 'R-CARRIED', 'candidate prints IncorrectDocumentStructureException "for an unexpected object graph"'),
 540: (K, 'R-LEADIN', 'lead-in of the test command; ci.yml link printed'),
 542: (A, 'R-PROSE-VALID', 'ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS exists (src/aspose/note/saving/pdf_writer.py:31); Base-14 default printed nowhere'),
 544: (A, 'R-PROSE-VALID', 'ISO 32000-1:2008 target and JDK-only module dependencies (java.*, javax.crypto, javax.imageio, javax.xml.*) printed nowhere'),
 613: (A, 'R-PROSE-VALID', 'src/converter/Converter.csproj exists with PackageId Aspose.3D.Converter (line 10); printed nowhere'),
 614: (K, 'R-CARRIED', 'candidate prints the csproj path with no PackageReference'),
 615: (A, 'R-VERSION', 'src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj:10-12 pins these versions; printed nowhere'),
 616: (A, 'R-VERSION', 'Aspose.ThreeD.Tests.csproj:16 coverlet.collector 6.0.2; printed nowhere'),
 628: (K, 'R-CARRIED', 'candidate prints Scene FromFile/FromStream/Save and RootNode'),
 630: (A, 'R-LINK-RESOLVES', 'aspose.org family documentation URL of the same pattern sibling seals print (e.g. https://reference.aspose.org/cells/rust/); host unreachable from this sandbox (URLError), no link_target fact contradicts it'),
 631: (A, 'R-LINK-RESOLVES', 'as #630 (kb.aspose.org)'),
 632: (A, 'R-LINK-RESOLVES', 'as #630 (reference.aspose.org)'),
 633: (A, 'R-LINK-RESOLVES', 'docs/foss-net-progress.md exists at the revision'),
 634: (A, 'R-LINK-RESOLVES', 'docs/release-26.2.0.md exists at the revision'),
 635: (A, 'R-LINK-RESOLVES', 'AGENTS.md exists at the revision'),
 636: (A, 'R-LINK-RESOLVES', 'the repository\'s own issues page (repository cloned at the revision)'),
 637: (K, 'R-CARRIED', 'PLY round-trip and the non-dispatched PlyFormat/FileFormat.PLY NotImplementedException are printed; only the literal `Scene.Open("model.ply")` spellings are gone'),
 638: (A, 'R-PROSE-VALID', 'NurbsCurve.Evaluate/EvaluateAt throw NotImplementedException (Entities/NurbsCurve.cs:109,117) - limitation printed nowhere'),
 639: (A, 'R-PROSE-VALID', 'scope boundary (rendering, PDF/Draco only in the Enterprise Edition) printed nowhere; the 3D candidate has no enterprise section'),
 641: (A, 'R-LEADIN', 'lead-in of #642 (READD)'),
 643: (A, 'R-LEADIN', 'lead-in of #644 (READD)'),
 645: (A, 'R-LINK-RESOLVES', 'AGENTS.md exists at the revision'),
 193: (A, 'R-API-IDENT', 'pub fields of exported CellStyle (src/Aspose.Cells_FOSS/Style.rs:73,76 `pub pattern`, `pub fill_color`); printed nowhere (facts.json misses struct fields)'),
 200: (A, 'R-API-IDENT', 'variant `Io(String)` of exported enum CellsError (src/Aspose.Cells_FOSS/api.rs:661); printed nowhere'),
 480: (A, 'R-API-IDENT', 'URL.can_parse (src/aspose_html/url/_url.py:63, URL exported from aspose_html) printed nowhere'),
 481: (K, 'R-CARRIED', 'detect_encoding / EncodingDetectionResult and WHATWG BOM/meta/UTF-8 sniffing printed; get_canonical_name is internal (encoding/__init__.py:5-9 __all__ omits it)'),
 483: (A, 'R-API-IDENT', 'JSContext.register_module / eval_module (src/aspose_html/js/_quickjs_bridge.py:346,375; JSContext in js/__init__.py:46 __all__) printed nowhere'),
 484: (K, 'R-CARRIED', 'ModuleRegistry printed; ModuleLoadPolicy is internal (js/__init__.py:46 __all__ omits it)'),
 532: (A, 'R-API-IDENT', 'public Outline attributes (src/aspose/note/model.py:945-1013 HorizontalOffset ... ReservedWidth) printed nowhere (facts.json misses attributes)'),
 536: (A, 'R-API-IDENT', 'FileFormat members Unknown/OneNoteOnline/OneNote2007 (src/aspose/note/enums.py:10-14) printed nowhere'),
 537: (A, 'R-API-IDENT', 'HorizontalAlignment members (src/aspose/note/enums.py:17-20) printed nowhere'),
 538: (A, 'R-API-IDENT', 'TagStatus.Disabled (src/aspose/note/enums.py:26) printed nowhere'),
 348: (K, 'R-API-PRIVATE', 'SelectorList is imported by src/aspose_html/css/__init__.py:9 for internal use but excluded from __all__ (line 11: select, element_matches) and the module docstring (line 3) says "All other names are internal"'),
 530: (K, 'R-API-PRIVATE', 'AttachmentTagFlowable is a class nested inside a function in src/aspose/note/saving/pdf_writer.py:1362 (not importable); the row itself says Internal'),
 531: (K, 'R-API-PRIVATE', 'OutlinePrefixFlowable is nested inside a function in src/aspose/note/saving/pdf_writer.py:1238 (not importable); the row itself says Internal'),
 # headings / html / badges with a non-default decision
 43: (K, 'R-CARRIED', 'misparsed paragraph: candidate prints "requires Go version 1.24.5" and no third-party dependency'),
 541: (K, 'R-HEADING', '<details> wrapper markup the renderer replaces (supersession EXEMPT_KINDS html_block)'),
 610: (A, 'R-LINK-RESOLVES', 'product banner and page resolve (products.aspose.org/3d/net/ 200, banner-readme.png 200); the 3D candidate prints no banner'),
 617: (A, 'R-LEADIN', 'heading of the Quick Start block #618 (READD); the candidate has no Quick Start'),
 619: (A, 'R-LEADIN', 'heading of the Additional Examples section whose blocks are READD'),
 622: (A, 'R-LEADIN', 'heading of #623 (READD)'),
 624: (A, 'R-LEADIN', 'heading of #625 (READD)'),
 629: (A, 'R-LEADIN', 'heading of the Documentation & Resources list whose items are READD'),
 640: (A, 'R-LEADIN', 'heading of the Development and Testing section whose blocks are READD'),
}

decisions = []
for x in it:
    i, e, k = x['i'], x['evidence'], x['piece_kind']
    if i in M:
        d, rule, ev = M[i]
    elif k == 'code_block':
        if x['item'].lstrip('`~ \n').lower().startswith('mermaid') and '```mermaid' in readme(x['bundle']):
            d, rule, ev = K, 'R-DIAGRAM', 'maintainers\' mermaid diagram; the candidate draws its own At a Glance diagram from verified facts'
        else:
            raise SystemExit(f'undecided code block #{i}')
    elif k == 'heading':
        d, rule, ev = K, 'R-HEADING', 'heading markup the renderer owns; the content under it is decided item by item'
    elif k == 'badge_row':
        d, rule, ev = K, 'R-BADGE', 'badge markup the renderer rebuilds; what the missing badges show (license, package version, runtime floor, contributor/issue counts) is printed elsewhere or is a decorative count'
    elif k == 'table_item':
        name = e.get('subject', '')
        rq = re.match(r'^([A-Za-z_]\w*)-([A-Za-z_]\w*)$', name)
        base = rq.group(1) if rq else name.split('(')[0]
        if 'subject_path_exists' in e:
            if e['subject_path_exists']:
                d, rule, ev = A, 'R-LINK-RESOLVES', f'{name} exists at the revision'
            else:
                d, rule, ev = K, 'R-LINK-DEAD', f'{name} does not exist at the revision'
        elif e.get('requalified_printed') or (rq and requalified(x, rq.group(1), rq.group(2))):
            d, rule, ev = K, 'R-API-REQUALIFIED', f'carried as `{e["requalified"]}` (package-qualified) in the candidate API table'
        else:
            pub, sev = subject_surface(x, base)
            cells = [c.strip() for c in x['item'].strip().strip('|').split('|')]
            desc = cells[-1] if len(cells) > 1 else ''
            if not pub:
                d, rule, ev = K, 'R-API-PRIVATE', sev
            elif FILLER.match(desc.strip()):
                d, rule, ev = K, 'R-API-FILLER', f'generator filler ("{desc}") replaced by a descriptive row for public {base}'
            elif not re.search(r'\|\s*`(?:[\w]+[.:]+)*' + re.escape(base) + r'`\s*\|', readme(x['bundle'])):
                d, rule, ev = A, 'R-API-ROW-MISSING', f'{base} is public ({sev}) and the candidate prints no row for it'
            elif norm(desc) and norm(desc) in norm(readme(x['bundle'])):
                d, rule, ev = K, 'R-CARRIED', 'description printed (markup differs only)'
            else:
                d, rule, ev = A, 'R-API-DESC', f'{base} is public ({sev}); the maintainer description (missing: {x["missing"][:120]}) was replaced by a generic restatement'
    elif k in ('list_item', 'sentence'):
        owed = owed_spans(x)
        if owed:
            d, rule, ev = A, 'R-API-IDENT', 'public member(s) printed nowhere in the candidate: ' + ', '.join(owed[:6])
        else:
            d, rule, ev = K, 'R-CARRIED', 'every public member the item names is printed in the candidate and its substance is restated (paraphrase)'
    else:
        raise SystemExit(f'undecided #{i} {k}')
    decisions.append(dict(x, decision=d, rule=rule, decision_evidence=ev))
json.dump(decisions, open(SP / 'decisions.json', 'w'), indent=1)
from collections import Counter
print(Counter(x['decision'] for x in decisions))
print(Counter((x['rule'], x['decision']) for x in decisions))
