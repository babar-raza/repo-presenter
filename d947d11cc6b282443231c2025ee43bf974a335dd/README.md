# Aspose.Imaging FOSS for .NET

![.NET](https://img.shields.io/badge/.net-netstandard2.0_%7C_net8.0-blue.svg) [![Build Status](https://github.com/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET)](https://github.com/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET/graphs/contributors)

[![Aspose.Imaging FOSS for .NET](https://products.aspose.org/media/imaging/net/banner-readme.png)](https://products.aspose.org/imaging/net/)

Aspose.Imaging FOSS for .NET reads image files and writes format information for PNG, JPEG, GIF, BMP, ICO, TIFF, WEBP, PSD, EMF, WMF, DICOM, DJVU, AVIF, and HEIC. It detects image format, extracts dimension, bit-depth, and frame count, and supports both synchronous and asynchronous probing. It produces `ImageFormat` and `ImageInfo` outputs without requiring full image decoding. It covers the full range of formats in one place, including PSD, EMF/WMF, and DICOM, which nothing else in the .NET FOSS ecosystem handles the same way.

*From the maintainers' README (not independently verified):*

Most .NET image libraries make you fully decode an image just to answer "is this a JPEG, and
how big is it?". `ImageSharp.Image.Identify` covers common raster formats well, but nothing
else in the .NET FOSS ecosystem does the same for PSD, EMF/WMF, or DICOM — this library covers
that full range in one place.

## Navigation

- [At a Glance](#at-a-glance)
- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Documentation & Resources](#documentation--resources)
- [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)
- [License](#license)

## At a Glance

```mermaid
flowchart LR
Product["Aspose.Imaging FOSS for .NET"]
Product["Aspose.Imaging FOSS for .NET"] --> Cap1["Format detection"]
Cap2["Header probing"]
Cap3["Multi-frame counting"]
Cap4["Async support"]
Cap5["Robust error handling"]
Cap6["Zero dependencies"]
Product["Aspose.Imaging FOSS for .NET"] --> Cap2["Header probing"]
Product["Aspose.Imaging FOSS for .NET"] --> Cap3["Multi-frame counting"]
Product["Aspose.Imaging FOSS for .NET"] --> Cap4["Async support"]
Product["Aspose.Imaging FOSS for .NET"] --> Cap5["Robust error handling"]
Product["Aspose.Imaging FOSS for .NET"] --> Cap6["Zero dependencies"]
```

## Key Capabilities

- **Format detection.** Format detection identifies 14 image formats by reading only signature bytes and returns an `ImageFormat` value without loading a full imaging stack, using `ImageProbe.DetectFormat()`.
- **Header probing.** Header probing reads a format's real header fields directly into an `ImageInfo` for PNG, JPEG, GIF, BMP, WEBP, ICO, TIFF, PSD, EMF, WMF, DICOM, DJVU, AVIF, and HEIC/HEIF, providing width, height, bit depth, and frame count without decoding.
- **Multi-frame counting.** Multi-frame counting accurately counts real multi-frame content by walking GIF image-descriptor blocks, ICO directory entries, TIFF IFD chains, and bundled multi-page DJVU FORM:DJVU page components rather than reporting inflated file counts.
- **Async support.** Async support provides both synchronous and async entry points for the same operation, with `ProbeFile`/`ProbeFileAsync` and Probe/`ProbeAsync` allowing non-blocking probes on ASP.NET request threads.
- **Robust error handling.** Robust error handling ensures `Probe()` never throws on a signature match it cannot fully parse, returning an `ImageInfo` with only Format set for malformed or truncated input instead of raising an exception.
- **Zero dependencies.** The package has no external runtime dependencies beyond the target frameworks netstandard2.0 and net8.0.

- DICOM parsing covers Implicit VR Little Endian and Explicit VR Little/Big Endian transfer
  syntaxes — including the common compressed ones, whose non-pixel elements are encoded
  Explicit VR Little Endian — and reads `Rows`/`Columns`/`BitsAllocated` directly from the data
  set, stopping rather than guessing if it reaches a sequence or encapsulated pixel data
  element with an undefined length first.

| Format | Detect | Width / Height | Bit depth | Frame count |
|--------|:------:|:---------------:|:---------:|:-----------:|
| PNG    | ✅ | ✅ | ✅ | — |
| JPEG   | ✅ | ✅ | ✅ | — |
| GIF    | ✅ | ✅ | — | ✅ |
| BMP    | ✅ | ✅ | ✅ | — |
| WEBP (lossy / lossless / extended) | ✅ | ✅ | — | — |
| ICO    | ✅ | ✅ | ✅ | ✅ |
| TIFF   | ✅ | ✅ | ✅ | ✅ |
| PSD    | ✅ | ✅ | ✅ | — |
| EMF    | ✅ | ✅ (from bounds) | — | — |
| WMF (placeable) | ✅ | ✅ (assumes 96 DPI) | — | — |
| DICOM  | ✅ | ✅ (Rows/Columns) | ✅ (BitsAllocated) | — |
| DJVU (single-page / multi-page DJVM) | ✅ | ✅ | — | ✅ |
| AVIF (still / animated) | ✅ | ✅ | — | — |
| HEIC / HEIF | ✅ | ✅ | — | — |

## Installation

`Aspose.Imaging.Foss` is not yet published on NuGet; build it from a source checkout instead:

```bash
git clone https://github.com/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET.git
cd Aspose.Imaging-FOSS-for-.NET
dotnet build
```

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `src/Aspose.Imaging.Foss/Aspose.Imaging.Foss.csproj`, no `PackageReference` a consumer would install is declared.

### Native and System Requirements

- Requires .NET `netstandard2.0;net8.0` (`TargetFrameworks` in `src/Aspose.Imaging.Foss/Aspose.Imaging.Foss.csproj`).

## Quick Start

This example uses `ImageProbe.ProbeFile` to inspect an animated GIF and print its format and frame count, demonstrating the simplest way to read image metadata without loading the full image.

```csharp
using Aspose.Imaging.Foss;

var info = ImageProbe.ProbeFile("animation.gif");
Console.WriteLine($"{info.Format}: {info.FrameCount} frame(s)");
```

*From the maintainers' README (not independently verified):*

`Probe` never throws on malformed or truncated input — if a file matches a format's signature
but its header can't be fully parsed, you get back an `ImageInfo` with just the `Format` set
rather than an exception.

## Additional Examples

> **Not verified:** this example is carried over unchanged from the project's existing README. It could not be compiled or run here.

```csharp
using Aspose.Imaging.Foss;

// From a file path
var info = ImageProbe.ProbeFile("photo.jpg");
Console.WriteLine($"{info.Format}: {info.Width}x{info.Height}, {info.BitDepth}-bit");

// From a stream (seekable or not) or a byte array
var format = ImageProbe.DetectFormat(bytes);
var info2 = ImageProbe.Probe(stream);
```

<details>
<summary>View Additional Examples</summary>

> **Not verified:** this example is carried over unchanged from the project's existing README. It could not be compiled or run here.

```csharp
using Aspose.Imaging.Foss;

var info = await ImageProbe.ProbeFileAsync("upload.png", cancellationToken);
Console.WriteLine($"{info.Format}: {info.Width}x{info.Height}");
```

> **Not verified:** this example is carried over unchanged from the project's existing README. It could not be compiled or run here.

```csharp
using Aspose.Imaging.Foss;

using var networkStream = GetUploadStream(); // CanSeek == false
var format = ImageProbe.DetectFormat(networkStream);
```

</details>

## API Reference

Aspose.Imaging FOSS for .NET exposes `ImageProbe` as its single entry point, which returns an `ImageFormat` value and an `ImageInfo` record for every supported format.

The verified public surface has 3 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `ImageInfo` | Aspose.Imaging.Foss.ImageInfo provides metadata about an image including its format, dimensions, bit depth, and frame count. |
| `ImageProbe` | Aspose.Imaging.Foss.ImageProbe detects image formats and extracts image metadata from files, streams, or byte arrays. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `ImageFormat` | Aspose.Imaging.Foss.ImageFormat represents an image file format identifier. |

#### Detailed Member Reference

### Foss

`ImageProbe` provides static methods `DetectFormat`, Probe, `ProbeFile`, `ProbeAsync`, and `ProbeFileAsync` to inspect image headers and return an `ImageFormat` enum and an `ImageInfo` record containing Format, Width, Height, `BitDepth`, and `FrameCount` where available.

`ImageProbe` is the library's single entry point; it returns an `ImageFormat` value and an
`ImageInfo` record for every supported format.

- `ImageFormat` — enum of the 14 detectable formats, plus `Unknown` for anything unmatched.
- `ImageInfo` — immutable result of a probe: `Format`, and the nullable `Width`, `Height`,
  `BitDepth`, and `FrameCount` the format's header actually carried.
- `ImageProbe` — static entry point: `DetectFormat`, `Probe`, `ProbeFile`, `ProbeAsync`, and
  `ProbeFileAsync`.

- `ImageProbe.DetectFormat(Stream stream) -> ImageFormat` / `DetectFormat(byte[] data) -> ImageFormat`
  — signature-only match, no dimension parsing.
- `ImageProbe.Probe(Stream stream) -> ImageInfo` / `Probe(byte[] data) -> ImageInfo` / `Probe(FileInfo file) -> ImageInfo`
  — full header parse for whichever format's signature matches.
- `ImageProbe.ProbeFile(string path) -> ImageInfo` — opens the file and calls `Probe`.
- `ImageProbe.ProbeAsync(Stream stream, CancellationToken cancellationToken = default) -> Task<ImageInfo>` /
  `ProbeFileAsync(string path, CancellationToken cancellationToken = default) -> Task<ImageInfo>`
  — async counterparts of `Probe`/`ProbeFile`.
- `ImageInfo(ImageFormat format, int? width = null, int? height = null, int? bitDepth = null, int? frameCount = null)`
  — the only public constructor; every field besides `Format` is nullable because not every
  format's header carries all four.

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/imaging/net/)** — The getting started guide walks through installation and a first probe step by step.
- **[How-to guides & FAQ](https://kb.aspose.org/imaging/net/)** — The how-to guides and FAQ provide task-focused answers for common format-detection questions.
- **[Full API reference](https://reference.aspose.org/imaging/net/)** — The full API reference offers the complete browsable reference for `ImageFormat`, `ImageInfo`, and `ImageProbe`. It covers all 3 verified public types; the [API Reference](#api-reference) section above covers the essentials.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET/issues).

## Scope and Limitations

Aspose.Imaging FOSS for .NET reads image headers to detect formats and extract metadata, supporting netstandard2.0 and net8.0 targets. It does not render, edit, or convert image data.

- Detection and metadata only: `ImageProbe` identifies a format and reads its header fields; it never decodes pixel data, so there is no rendering, editing, or format-conversion capability anywhere in the library.
- Frame count reflects only what the container itself records: it is a real, computed count for GIF, ICO, TIFF, and bundled multi-page DJVU (DJVM); every other supported format reports a fixed 1 for a successfully parsed header, since none of their headers carry a genuine frame or page count.
- Non-placeable WMF is detected but not dimensioned: the classic (non-placeable) WMF header carries no bounding rectangle, so Probe returns a format-only `ImageInfo` for it; only the placeable WMF header yields Width/Height.
- DICOM parsing stops at the first undefined-length element: a sequence or encapsulated pixel-data element with an undefined length ends the walk rather than being parsed.
- CDR support is planned but not yet implemented: no `CdrFormatHandler` exists in the current source tree.

*From the maintainers' README (not independently verified):*

Frame count is marked ✅ only where the container format genuinely records more than one
frame or page (GIF, ICO, TIFF, and multi-page DJVU); every other format's `FrameCount` comes
back as a fixed `1` on a successful parse, which this table does not count as a real frame
count.

These limitations don't apply to [full-featured Aspose.Imaging for .NET — Enterprise Edition](https://products.aspose.com/imaging/net/). It adds full decoding, editing, rendering, and conversion across a much broader format range.

## Development and Testing

Aspose.Imaging FOSS for .NET targets netstandard2.0 and net8.0 and is built using the .NET CLI. The test project, located under tests/`Aspose.Imaging.Foss.Tests`, targets net9.0 and uses xUnit for testing, with Microsoft.NET.Test.Sdk 17.12.0, xunit 2.9.2, and xunit.runner.visualstudio 2.8.2 as test dependencies, and coverlet.collector 6.0.2 for code-coverage collection. These test dependencies apply only to the test project and are not referenced by the main library project. The test suite is executed from the repository root using dotnet test, and the build uses dotnet build on the solution file.

The suite covers 3 test files under `tests/`. The [ci workflow](.github/workflows/ci.yml) runs on Ubuntu and Windows. Releases run through the [release workflow](.github/workflows/release.yml).

```bash
git clone https://github.com/aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET.git
cd Aspose.Imaging-FOSS-for-.NET
dotnet build src/Aspose.Imaging.Foss/Aspose.Imaging.Foss.csproj -c Release
```

Reference the built assembly from another project, or add the project directly:

```xml
<ProjectReference Include="..\Aspose.Imaging-FOSS-for-.NET\src\Aspose.Imaging.Foss\Aspose.Imaging.Foss.csproj" />
```

Run the test suite from the repository root:

```bash
dotnet test tests/Aspose.Imaging.Foss.Tests/Aspose.Imaging.Foss.Tests.csproj
```

The test project targets `net9.0` and references the library via a plain `ProjectReference` —
no packaged dependency is required to build or test the library itself. A tagged
`v<major>.<minor>.<patch>` push runs [`.github/workflows/release.yml`](.github/workflows/release.yml),
which builds and publishes the package.

*From the maintainers' README (not independently verified):*

Adding a new format means implementing `IFormatHandler` (signature match + header parse) under
`src/Aspose.Imaging.Foss/Formats` and registering it in `ImageProbe`. Pull requests for new
formats or wider tag/chunk coverage on existing ones are welcome.

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
