<!--
NOT FILED. This is a complete, evidence-backed proposal only. Filing it as a real
GitHub issue requires an explicit owner go-ahead; this session has not exercised or
been authorized to use this repository's Issues effect path.

CORRECTION (2026-10-21): an independent review found this draft's original "Impact"
section overstated the consequence of the nuspec gap below as a "runtime load
failure" risk. That consequence was retested directly (both by that review and,
independently again, by the supervisor session acting on its finding) and does NOT
reproduce: a fresh `dotnet add package Aspose.Words.FOSS` into a new net8.0 console
app, followed by `new Document()` (the README's own Quick Start), completes with no
exception. The same was also true for a self-contained publish and a trimmed
self-contained publish of that app -- in all three cases `System.Text.Encoding.
CodePages.dll` was present and loaded successfully, because the .NET SDK's implicit
`Microsoft.NETCore.App` framework reference supplies that assembly for any net5.0+/
netstandard2.0-via-net8.0 project regardless of what the consumed package's nuspec
declares. The nuspec omission itself is still real and still worth fixing as a
packaging-metadata hygiene gap (see below, re-scoped), but it is NOT a reproduced
runtime-failure risk for the README's own documented consumption scenario, nor for
self-contained or trimmed self-contained publishing. The "Impact" section below has
been corrected accordingly; the original, broader "risks a runtime load failure"
framing should not be filed as written.
-->

**Target repository:** `aspose-words-foss/Aspose.Words-FOSS-for-.NET`
**Target revision:** `0d3f1add920f5294d726b4f286c2d6ba7c3ae22c` (current `master` as of 2026-10-21)

## Proposed title

Published `Aspose.Words.FOSS` nuspec is missing the `System.Text.Encoding.CodePages`
dependency declaration for the `.NETStandard2.0` and `net8.0` targets (metadata gap;
does not reproduce as a runtime failure under standard .NET SDK consumption -- see
corrected Impact section below)

## Proposed body

`Package/Aspose.Words.FOSS.nuspec`'s `<dependencies>` element declares, for the
`.NETStandard2.0` group:

```xml
<group targetFramework=".NETStandard2.0">
	<dependency id="SkiaSharp" version="3.119.0" exclude="Build,Analyzers" />
	<dependency id="BitMiracle.LibTiff.NET" version="2.4.649" exclude="Build,Analyzers" />
	<dependency id="Microsoft.Win32.Registry" version="5.0.0" exclude="Build,Analyzers" />
</group>
```

and for the `net8.0` group:

```xml
<group targetFramework="net8.0">
	<dependency id="SkiaSharp" version="3.119.0" exclude="Build,Analyzers" />
	<dependency id="BitMiracle.LibTiff.NET" version="2.4.649" exclude="Build,Analyzers" />
</group>
```

Neither group lists `System.Text.Encoding.CodePages`, even though the assembly
built for both of those target frameworks is compiled against it and calls into it
unconditionally on first use.

### Why this is a real gap, not a false alarm

1. `Aspose.Foundation/Aspose.Foundation/Aspose.Foundation.csproj` has:
   ```xml
   <ItemGroup Condition="'$(TargetFramework)' != 'net462'">
       <PackageReference Include="SkiaSharp" Version="3.119.0" />
       <PackageReference Include="System.Text.Encoding.CodePages" Version="7.0.0" />
       <PackageReference Include="BitMiracle.LibTiff.NET" Version="2.4.649" />
   </ItemGroup>
   ```
   so both the netstandard2.0 and net8.0 builds of the assembly are compiled against
   `System.Text.Encoding.CodePages` 7.0.0.

2. `Aspose.Foundation/Aspose.Foundation/Base/EncodingUtil.cs`:
   ```csharp
   public static void RegisterEncodings()
   {
   #if NETSTANDARD || NET
       try
       {
           Encoding.GetEncoding(1252);
       }
       catch (System.Exception)
       {
           Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
       }
   #endif
   }
   ```
   `CodePagesEncodingProvider` is a type that lives only in the
   `System.Text.Encoding.CodePages` assembly. On .NET Standard 2.0 / .NET (Core) 8,
   `Encoding.GetEncoding(1252)` throws `NotSupportedException` unless a codepages
   provider is already registered, so this `catch` branch is always taken on first
   call on these two targets, and the `CodePagesEncodingProvider` type must load.

3. `Aspose.Words/Model/Document/Document.cs`:
   ```csharp
   static Document()
   {
       // Register encodings supported in the desktop .NET Framework but not in .NET Standard.
       EncodingUtil.RegisterEncodings();
   }
   ```
   This static constructor runs the first time the `Document` class is touched by
   *any* consumer -- including the very first line of this repository's own README
   Quick Start example (`Document doc = new Document();`).

4. `Aspose.Words/Aspose.Words.csproj`'s `MergeFossAssembly` build target, which
   produces the exact binaries the nuspec packages, explicitly comments:
   > "SkiaSharp and the other NuGet dependencies stay external."

   confirmed by its `MergeInput` list, which only merges
   `Aspose.Foundation.dll`, `Aspose.JavaAttributes.dll`,
   `CodePorting.Translator.Cs2Cpp.Control.dll`, and `BouncyCastle.Crypto.dll` --
   `System.Text.Encoding.CodePages.dll` is not among them, so it is not
   ILRepack-internalized into the shipped `Aspose.Words.FOSS.dll`.

### Impact (corrected 2026-10-21)

The restore-graph gap itself is real and independently reconfirmed: a consumer
targeting .NET Standard 2.0 (e.g. a .NET 6/8/10 application, as the README's own
"Getting started" section documents as a supported scenario) or net8.0 directly, who
does exactly what the README instructs -- `dotnet add package Aspose.Words.FOSS` and
nothing else -- will not have `System.Text.Encoding.CodePages` restored as an
explicit dependency by NuGet, because the nuspec never declares it for those two
target frameworks (`obj/project.assets.json` confirmed to contain no reference to
it).

However, this does **not** translate into the runtime assembly load failure
originally claimed here. Independently tested directly, three times, against that
exact scenario and two further ones: (1) a fresh net8.0 console app, `dotnet add
package Aspose.Words.FOSS`, then `new Document()` as the only statement -- completed
successfully, no exception; (2) `dotnet publish -r win-x64 --self-contained true` of
that same app -- `System.Text.Encoding.CodePages.dll` was present in the publish
output and the app ran cleanly; (3) the same publish with `-p:PublishTrimmed=true`
-- the assembly was still present post-trim and the app still ran cleanly. In all
three cases the type resolves because the .NET SDK's implicit `Microsoft.NETCore.App`
framework reference supplies `System.Text.Encoding.CodePages` for any net5.0+ /
netstandard2.0-via-net8.0 project, and the self-contained/trimmed runtime packs
bundle that same assembly as part of the framework distribution -- independently of
what the consumed package's own nuspec declares.

The gap is therefore real as a packaging-metadata hygiene defect (the nuspec should
still match the actual `PackageReference` set for traceability and for any consumer
on a non-SDK-style build), but it should not be filed or read as "risks a runtime
load failure" -- that specific claim was tested and did not hold under the README's
own documented consumption path, nor under self-contained or trimmed self-contained
publishing. A genuinely failing consumer would have to be using a non-SDK-style
project system or a runtime without the .NET SDK's implicit BCL framework reference;
that narrower scenario was not tested and is not asserted here.

### Suggested fix shape (not a patch; for triage only)

Add `<dependency id="System.Text.Encoding.CodePages" version="7.0.0" exclude="Build,Analyzers" />`
to both the `.NETStandard2.0` and `net8.0` dependency groups in
`Package/Aspose.Words.FOSS.nuspec`, matching the real `PackageReference` set in
`Aspose.Foundation.csproj`.

## Dedup check performed

Run 2026-10-21:
- `gh issue list --repo aspose-words-foss/Aspose.Words-FOSS-for-.NET --state all` -> empty (repository currently has zero issues, open or closed).
- `gh issue list --repo aspose-words-foss/Aspose.Words-FOSS-for-.NET --state all --search "CodePages"` -> empty.
- `gh issue list --repo aspose-words-foss/Aspose.Words-FOSS-for-.NET --state all --search "nuspec"` -> empty.
- `gh issue list --repo aspose-words-foss/Aspose.Words-FOSS-for-.NET --state all --search "dependency"` -> empty.

No existing issue covers this; this cannot be a duplicate.
