# Aspose.PSD.FOSS for .NET

Aspose.PSD.FOSS is a free open-source .NET library for loading, inspecting, editing a small subset of PSD/PSB metadata, and saving the file back without rendering.

This library is for metadata-safe PSD/PSB inspection and limited structural editing. It is not a rendering engine, a raster editor, or an open-source replacement for the full commercial Aspose.PSD product.

## Who This Project Is For

Use Aspose.PSD.FOSS when you need to:

- inspect PSD/PSB structure and metadata from .NET code;
- read layer, resource, color-mode, and merged-image summaries;
- make small safe edits to layer metadata;
- save the file back without rendering pixels.

Do not use Aspose.PSD.FOSS when you need to:

- render PSD/PSB content;
- edit pixels or export raster images;
- interpret the full Photoshop feature set semantically;
- replace the commercial Aspose.PSD API surface one-to-one.

## Common Workflows

- Inspect a PSD/PSB document and read structural metadata.
- Enumerate layers and read their basic properties.
- Change supported layer properties such as name, visibility, opacity, clipping, blend mode key, and geometry.
- Save the updated file back while preserving unsupported sections as raw bytes where possible.

## Mental Model

- The library parses only a small supported subset of the PSD/PSB format.
- Known structures are exposed through a compact public API.
- Image resources are exposed through lightweight unknown-only summaries rather than ID-specific semantic reconstruction.
- Unsupported sections are preserved as raw bytes where possible.
- When you mutate supported metadata, the library rewrites only the affected supported structures and keeps the rest of the file in raw-preserved form.

## Highlights

- Aspose.PSD-style API for common PSD metadata scenarios
- Load PSD/PSB from file paths and streams
- Read document properties: `Width`, `Height`, `ChannelsCount`, `BitsPerChannel`, `ColorMode`, Aspose.PSD-compatible `Version`
- Read additional document metadata: `Size`, `Bounds`, `Compression`, `ImageResources`, `IsFlatten`
- Read layer metadata: `Name`, local `Bounds` `Rectangle`, `Width`, `Height`, `Top`, `Left`, `Bottom`, `Right`, `IsVisible`, `Opacity`, `Clipping`, `BlendModeKey`
- Inspect supported official-style resource, channel, mask, and blending-range surfaces
- Change `Name`, `IsVisible`, `Opacity`, `BlendModeKey`, `Clipping`, and layer geometry through coordinate properties
- Save without rendering
- Preserve unsupported sections as raw bytes where possible

## Requirements

- .NET 10.0 SDK or later

## Installation

The package metadata is defined in this repository, but `Aspose.PSD.FOSS` is not published to NuGet yet.

Build the package locally:

```bash
dotnet pack src/Aspose.PSD.FOSS/Aspose.PSD.FOSS.csproj -c Release
```

The package will be created under `src/Aspose.PSD.FOSS/bin/Release/`.

To install it through a NuGet:

```bash
dotnet add package Aspose.PSD.FOSS
```

## Quick Start

```csharp
using Aspose.PSD;
using Aspose.PSD.FileFormats.Core.Blending;
using Aspose.PSD.FileFormats.Psd;
using Aspose.PSD.FileFormats.Psd.Layers;

using var image = (PsdImage)Image.Load("input.psd");

Console.WriteLine(image.Width);
Console.WriteLine(image.Height);
Console.WriteLine(image.ChannelsCount);
Console.WriteLine(image.BitsPerChannel);
Console.WriteLine(image.ColorMode);
Console.WriteLine(image.Version);
Console.WriteLine(image.Compression);
Console.WriteLine(image.Layers.Length);
Console.WriteLine(image.ImageResources.Length);

foreach (Layer layer in image.Layers)
{
    Console.WriteLine(layer.Name);
    Console.WriteLine(layer.Bounds);
    Console.WriteLine(layer.BlendModeKey);
    Console.WriteLine(layer.IsVisible);
    Console.WriteLine(layer.Opacity);
}

image.Layers[0].Name = "Updated layer";
image.Layers[0].IsVisible = false;
image.Layers[0].Left = 10;
image.Layers[0].Top = 20;
image.Layers[0].Right = 110;
image.Layers[0].Bottom = 120;
image.Layers[0].Opacity = 128;
image.Layers[0].BlendModeKey = BlendMode.Multiply;
image.Save("output.psd");
```

## Choosing Between Aspose.PSD.FOSS and Commercial Aspose.PSD

Choose Aspose.PSD.FOSS if you need a small open-source library for structural inspection and limited non-rendering edits.

Choose the commercial Aspose.PSD product if you need broad Photoshop feature support such as rendering, raster editing, export pipelines, richer resource/tag handling, or wider PSD/PSB compatibility.

## Samples

Runnable sample projects are available in the repository `samples/` folder:

- `Aspose.PSD.FOSS.Samples.Basic`
- `Aspose.PSD.FOSS.Samples.Layers`
- `Aspose.PSD.FOSS.Samples.StructuralEditing`
- `Aspose.PSD.FOSS.Samples.Streams`
- `Aspose.PSD.NuGet.Samples.Basic`
- `Aspose.PSD.NuGet.Samples.Layers`
- `Aspose.PSD.NuGet.Samples.StructuralEditing`
- `Aspose.PSD.NuGet.Samples.Streams`

The `Aspose.PSD.FOSS.Samples.*` projects reference this FOSS library. The `Aspose.PSD.NuGet.Samples.*` projects run the same workflows against the official `Aspose.PSD` NuGet package.

Each FOSS sample must have a fully analogous NuGet sample, and the matching `Program.cs` files must always remain identical. Keep only the project files different so the same application source can be compiled and exercised against both libraries for the supported migration scenarios.

This parity requirement applies to sample source and covered workflows, not to byte-for-byte identical runtime output. The commercial `Aspose.PSD` package may report different values or save different bytes for the same input document even when both sample projects successfully run the same scenario.

Sample/workflow matrix:

| FOSS sample | NuGet sample | Main workflow | What it demonstrates |
|---|---|---|---|
| `Aspose.PSD.FOSS.Samples.Basic` | `Aspose.PSD.NuGet.Samples.Basic` | Document inspection | Aspose.PSD-compatible document metadata and supported resource/layer counts |
| `Aspose.PSD.FOSS.Samples.Layers` | `Aspose.PSD.NuGet.Samples.Layers` | Layer inspection | Layer metadata, derived geometry, blend mode key, channel information, mask data, and blending ranges |
| `Aspose.PSD.FOSS.Samples.StructuralEditing` | `Aspose.PSD.NuGet.Samples.StructuralEditing` | Supported metadata editing | Renaming layers, changing visibility, opacity, clipping, blend mode key, and geometry, then saving without rendering |
| `Aspose.PSD.FOSS.Samples.Streams` | `Aspose.PSD.NuGet.Samples.Streams` | Stream-based round trip | Loading from a stream, saving to a stream, and working with in-memory PSD/PSB data |

Example commands:

```bash
dotnet run --project samples/Aspose.PSD.FOSS.Samples.Basic
dotnet run --project samples/Aspose.PSD.FOSS.Samples.Layers
dotnet run --project samples/Aspose.PSD.FOSS.Samples.StructuralEditing
dotnet run --project samples/Aspose.PSD.FOSS.Samples.Streams
dotnet run --project samples/Aspose.PSD.NuGet.Samples.Basic
dotnet run --project samples/Aspose.PSD.NuGet.Samples.Layers
dotnet run --project samples/Aspose.PSD.NuGet.Samples.StructuralEditing
dotnet run --project samples/Aspose.PSD.NuGet.Samples.Streams
```

If you do not pass an input file, the samples try to use the repository PSD test fixture.

If you do not pass an output file to the stream or structural-editing samples, they save into the repository `tmp/` folder by default.

## Documentation

Markdown documentation is available in the repository:

- `documentation/README.md`
- `documentation/getting-started.md`
- `documentation/developer-guide/basic-psd-operations.md`
- `documentation/limitations.md`

## Supported Scope

- Load PSD files
- Load the currently supported PSB subset
- Read document properties from the file header
- Read supported high-level metadata from Color Mode Data, Image Resources, Layer and Mask Information, and merged image data
- Change `Name`, `IsVisible`, `Opacity`, `BlendModeKey`, `Clipping`, and layer geometry through coordinate properties
- Save PSD/PSB without rendering

## Out of Scope

- Rendering
- Pixel editing
- Export to PNG, JPEG, or other raster formats
- Full image resource editing
- Semantic recognition of specific image resource kinds
- Full tagged block editing
- Text, vector, effects, smart filters, and adjustment rendering

## License

MIT
