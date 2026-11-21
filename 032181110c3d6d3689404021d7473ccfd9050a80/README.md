# Aspose.OCR FOSS for .NET

[![NuGet version](https://img.shields.io/nuget/v/Aspose.OCR.FOSS.svg)](https://www.nuget.org/packages/Aspose.OCR.FOSS/) ![.NET](https://img.shields.io/badge/.net-netstandard2.0_%7C_net8.0_%7C_net9.0_%7C_net10.0_%7C_net48-blue.svg) [![Build Status](https://github.com/aspose-ocr-foss/Aspose.OCR-FOSS-for-.NET/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/aspose-ocr-foss/Aspose.OCR-FOSS-for-.NET/actions/workflows/build.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[![Aspose.OCR FOSS for .NET](https://products.aspose.org/media/ocr/net/banner-readme.png)](https://products.aspose.org/ocr/net/)

Aspose.OCR FOSS for .NET reads images and PDF documents and converts them into text using optical character recognition. It produces recognition results that include full text and line-level details, supporting multiple input types through the `Aspose.OCR.OcrInput` class. The product exposes its functionality through the `Aspose.OCR.AsposeOcr.Recognize` method, returning `Aspose.OCR.OcrOutput` for multi-page inputs or `Aspose.OCR.RecognitionResult` for single-page inputs. It runs on multiple .NET platforms including .NET Standard and recent .NET versions.

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
flowchart TB
  PRODUCT["Aspose.OCR FOSS for .NET"]
  subgraph Capabilities["Core Capabilities"]
    direction TB
    c1["Local OCR with<br/>embedded models"]
    c2["Multi-format input<br/>support"]
    c3["Line-level output with<br/>coordinates"]
    c4["Latin-script<br/>recognition"]
    c5["Cross-framework<br/>compatibility"]
    c1 ~~~ c4
    c2 ~~~ c5
    c3 ~~~ c5
  end
  PRODUCT --> Capabilities
  classDef product fill:#1f6feb,stroke:#1f6feb,color:#ffffff
  class PRODUCT product
```

## Key Capabilities

- **Local OCR with embedded models.** It performs local OCR using embedded ONNX detection and refinement models, runs entirely on the local CPU without network services or external model files, and returns one `RecognitionResult` per image or PDF page through the `AsposeOcr.Recognize` method.
- **Multi-format input support.** It accepts input through `Aspose.OCR.InputType.SingleImage` for single raster images and `InputType`.PDF for multi-page documents, supports adding multiple files to one `OcrInput` container while preserving their order, and processes each page in source order.
- **Line-level output with coordinates.** It returns line-level results with System.Drawing.Rectangle coordinates through `RecognitionResult.RecognitionLinesResult`, provides individual line text via `LinesResult.TextInLine`, and exposes each line's bounding box through `LinesResult.Line`.
- **Latin-script recognition.** It recognizes Latin-script text including diacritical characters included in the embedded recognition model and returns the complete page text through `RecognitionResult.RecognitionText`.
- **Cross-framework compatibility.** It targets netstandard2.0, net8.0, net9.0, net10.0, and net48, enabling use across multiple .NET implementations and runtime versions.

## Installation

Install the published package from NuGet (`Aspose.OCR.FOSS`, version 26.10.0):

```bash
dotnet add package Aspose.OCR.FOSS
```

## Dependencies

### Required Package Dependencies

- `Aspose.PDF.FOSS 26.10.0`
- `Microsoft.ML.OnnxRuntime 1.22.1`
- `System.Drawing.Common 8.0.0`
- `System.Security.Cryptography.Pkcs 8.0.2`

### Native and System Requirements

- Requires .NET `netstandard2.0;net8.0;net9.0;net10.0;net48` (`TargetFrameworks` in `src/Aspose.Ocr.Foss.csproj`).

## Quick Start

```csharp
using Aspose.OCR;

var api = new AsposeOcr();
using var input = new OcrInput(InputType.PDF);
input.Add("document.pdf");

OcrOutput output = api.Recognize(input);

foreach (RecognitionResult page in output)
{
    Console.WriteLine(page.RecognitionText);

    foreach (RecognitionResult.LinesResult line in page.RecognitionLinesResult)
    {
        Console.WriteLine($"{line.Line}: {line.TextInLine}");
    }
}
```

## Additional Examples

```csharp
using Aspose.OCR;

var api = new AsposeOcr();
using var input = new OcrInput(InputType.SingleImage);
input.Add("scan.png");

RecognitionResult result = api.Recognize(input)[0];
Console.WriteLine(result.RecognitionText);
```

<details>
<summary>View Additional Examples</summary>

```csharp
using Aspose.OCR;

var api = new AsposeOcr();
using var input = new OcrInput(InputType.SingleImage);
input.Add("page-1.jpg");
input.Add("page-2.png");

OcrOutput output = api.Recognize(input);

for (int index = 0; index < output.Count; index++)
{
    Console.WriteLine($"Image {index + 1}");
    Console.WriteLine(output[index].RecognitionText);
}
```

```csharp
using Aspose.OCR;

var api = new AsposeOcr();
using var input = new OcrInput(InputType.SingleImage);
input.Add("document.jpg");

RecognitionResult result = api.Recognize(input)[0];

foreach (RecognitionResult.LinesResult line in result.RecognitionLinesResult)
{
    System.Drawing.Rectangle bounds = line.Line;
    Console.WriteLine(
        $"x={bounds.X}, y={bounds.Y}, width={bounds.Width}, " +
        $"height={bounds.Height}: {line.TextInLine}");
}
```

</details>

## API Reference

Aspose.OCR FOSS for .NET exposes the `AsposeOcr` class as its main entry point for performing OCR operations. It produces `OcrOutput` collections that contain `RecognitionResult` objects for each processed image or PDF page.

The public API has 6 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `AsposeOcr` | Provides the entry point for optical character recognition. |
| `LinesResult` | Represents the recognized text and bounds of one text line. |
| `OcrInput` | Represents input supplied to the OCR engine. |
| `OcrOutput` | Contains OCR recognition results. |
| `RecognitionResult` | Represents the recognition result for one image or one PDF page. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `InputType` | Specifies the type of OCR input. |

#### Detailed Member Reference

### AsposeOcr

The `AsposeOcr` class provides the Recognize method that accepts an `OcrInput` container and returns an `OcrOutput` collection containing one `RecognitionResult` per source image or PDF page.

- `Recognize`: Recognizes all files in the supplied input container.

### OcrInput

The `OcrInput` class is initialized with an `InputType` to specify whether sources are single images or PDF documents, supports adding file paths via the Add method, and clears its contents when disposed.

- `Add`: Adds a file to the input container.
- `Dispose`: Releases the references held by this input container.
- `OcrInput`: Initializes a new input container for the specified input type.

### RecognitionResult

Each `RecognitionResult` provides `RecognitionText` for full recognized content and `RecognitionLinesResult` for ordered line-level text and rectangle coordinates, where each `LinesResult` exposes `TextInLine` and Line properties.

- `RecognitionLinesResult`: Gets recognized lines together with their source-image coordinates.
- `RecognitionText`: Gets or sets all recognized lines joined with line breaks.

- `Recognize(OcrInput input) -> OcrOutput`
  - Returns one result per source image or PDF page.
  - Throws `ArgumentNullException` for a null input.
  - Throws `FileNotFoundException` when a source file does not exist.
  - Throws `NotSupportedException` for an unsupported input type.

- `OcrInput(InputType type)` — creates an input container for one source type.
- `Add(string fullPath)` — adds a relative or absolute file path.
- `Dispose()` — clears all paths held by the container.

- `RecognitionText` — all non-empty recognized lines joined with line breaks.
- `RecognitionLinesResult` — ordered line text and rectangles.

- `TextInLine` — recognized text for one detected line.
- `Line` — `System.Drawing.Rectangle` in source-image pixels.

</details>

## Documentation & Resources

- **[src/](src/)** — library source code, ONNX integration, and embedded models.
- **[tests/](tests/)** — xUnit validation and end-to-end OCR tests with sample documents.
- **[Aspose.Ocr.Foss.sln](Aspose.Ocr.Foss.sln)** — solution for Visual Studio and the .NET CLI.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-ocr-foss/Aspose.OCR-FOSS-for-.NET/issues).

- [`src/`](src/) — library source code, ONNX integration, and embedded models.
- [`tests/`](tests/) — xUnit validation and end-to-end OCR tests with sample documents.
- [`Aspose.Ocr.Foss.sln`](Aspose.Ocr.Foss.sln) — solution for Visual Studio and the .NET CLI.
- [`LICENSE`](LICENSE) — MIT license text.

## Scope and Limitations

1. **Input validation** — all source paths and the selected `InputType` are validated before the ONNX sessions are created.
2. **PDF rendering** — PDF pages are rendered to 24-bit RGB images at 150 DPI with `Aspose.PDF.FOSS`. Raster images are loaded directly.
3. **Detector preprocessing** — the image is converted to Rec. 709 grayscale. If its longest side exceeds 1000 pixels, it is reduced with a separable Lanczos-8 filter. A 32-pixel white strip is appended to match the detector's training-time preprocessing.
4. **Region detection** — the first ONNX model produces text probability maps and intermediate visual features. The refinement model strengthens links between adjacent characters.
5. **Region post-processing** — text and link maps are thresholded, grouped with a four-connected breadth-first flood fill, dilated, fitted with a minimum-area rectangle, scaled back to source coordinates, and reduced to non-nested axis-aligned line rectangles.
6. **Line recognition** — each detected rectangle is padded by two pixels, cropped, resized to fit a 1200×32 white canvas while preserving its aspect ratio, converted to an NHWC grayscale tensor, and passed to the recognition model.
7. **CTC decoding** — greedy CTC decoding collapses repeated classes, removes the blank class, and maps the remaining classes to the model's Latin alphabet.
8. **Result assembly** — recognized lines are paired with their source-image rectangles and joined with platform line breaks to produce `RecognitionText`.

ONNX Runtime uses parallel graph execution with eight intra-operation worker threads. Input files and PDF pages themselves are processed sequentially.

- The public API is intentionally compact and may evolve as recognition capabilities are extended.
- Recognition supports Latin-script text and the diacritical characters present in the embedded recognition alphabet. There is no runtime language-selection API.
- Inputs are limited to raster images supported by `System.Drawing.Common` and PDF documents.
- Image processing is Windows-only because the OCR pipeline depends on `System.Drawing.Common` for bitmap loading, cropping, resizing, and pixel access.
- PDF pages are always rendered at 150 DPI; rendering resolution is not configurable yet.
- The detector returns axis-aligned text-line rectangles. Polygonal regions and layout labels are not part of the public output.
- Searchable PDF generation, text export helpers, confidence scores, font detection, spelling correction, table structure, and barcode detection are not implemented.
- Automatic page rotation, deskewing, color inversion, and user-configurable preprocessing are not implemented.
- GPU execution is not configured; inference uses the CPU execution provider.
- There is no dedicated input-level multithreading API. A single call processes files and PDF pages sequentially, although ONNX Runtime parallelizes operations inside each inference session.
- The NuGet package is large because the three models are embedded into every target-framework assembly.

See [Aspose.OCR for .NET — Enterprise Edition](https://products.aspose.com/ocr/net/).

## Development and Testing

```bash
dotnet add package Aspose.OCR.FOSS --version 26.10.0
```

Or add a `<PackageReference>`:

```xml
<PackageReference Include="Aspose.OCR.FOSS" Version="26.10.0" />
```

Building all five targets from source requires the .NET 10 SDK; use `-f net8.0`, for example, to build one target.

```bash
dotnet build src/Aspose.Ocr.Foss.csproj -c Release
```

- Windows for OCR image processing with `System.Drawing.Common 8.0.0`.
- .NET Framework 4.8, a .NET Standard 2.0-compatible runtime, or .NET 8 or later.
- No separate OCR model download is required; all three ONNX models are embedded resources.
- ONNX Runtime supplies the native runtime binaries through its NuGet package.

The test project uses xUnit and `Microsoft.NET.Test.Sdk`. No separate test runner installation is required when tests are executed with `dotnet test`.

On Windows, run the complete restore, build, test, and package workflow by double-clicking `build-packages.bat` or from a terminal:

```bat
build-packages.bat
```

Use `build-packages.bat --no-pause` in scripts or CI environments.

Restore, build, and run the complete test matrix:

```bash
dotnet restore Aspose.Ocr.Foss.sln
dotnet build Aspose.Ocr.Foss.sln -c Release --no-restore
dotnet test Aspose.Ocr.Foss.sln -c Release --no-build
```

The xUnit test project targets **net48, net8.0, net9.0, and net10.0**. To run one target only:

```bash
dotnet test tests/Aspose.Ocr.Foss.Tests.csproj -c Release -f net8.0
```

Create the NuGet package:

```bash
dotnet pack src/Aspose.Ocr.Foss.csproj -c Release --no-build -o artifacts/packages
```

This creates `Aspose.OCR.FOSS.26.10.0.nupkg` in `artifacts/packages`.

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
