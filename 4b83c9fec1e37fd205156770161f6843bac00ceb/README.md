# Aspose.PDF FOSS for Cpp

![C++](https://img.shields.io/badge/c%2B%2B-20-blue.svg) [![CI](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp/actions/workflows/ci.yml/badge.svg)](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) ![C++20](https://img.shields.io/badge/C%2B%2B-20-00599C?logo=cplusplus) [![CMake](https://img.shields.io/badge/CMake-3.20+-064F8C?logo=cmake)](https://cmake.org/)

[![Aspose.PDF FOSS for Cpp](https://products.aspose.org/media/pdf/cpp/banner-readme.png)](https://products.aspose.org/pdf/cpp/)

Aspose.PDF FOSS for Cpp reads and writes PDF documents, extracts text, and converts pages to image formats such as PNG. It builds documents from scratch, supporting text, tables, vector graphics, watermarks, annotations, AcroForm fields, and bookmarks. It encrypts and decrypts files using AES-256 and handles password-protected documents. It reads document metadata and information such as title, author, and keywords, and writes updated values back to the file.

Aspose.PDF FOSS for Cpp is a free, open-source, modern C++20 library for working with PDF
documents — opening and saving existing files, extracting text, rasterising pages to image
formats, and building documents from scratch (text, tables, vector graphics, watermarks,
annotations, AcroForm fields, and bookmarks). It links against nothing but the C++ standard
library: every primitive, including the TIFF, JPEG, and PNG codecs and the page rasteriser, is
implemented from scratch with no dependency on any commercial PDF stack. Its public API is a
strict subset of the commercial Aspose.PDF for .NET library — class names, method names, and
shapes mirror it where natural for migrants — and spec references throughout follow ISO 32000-1
(PDF 1.7) and ISO 32000-2 (PDF 2.0).

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
- [Third-Party Notices](#third-party-notices)
- [License](#license)

## At a Glance

```mermaid
flowchart TB
  PRODUCT["Aspose.PDF FOSS for Cpp"]
  subgraph Capabilities["Core Capabilities"]
    direction TB
    c1["Open and edit PDF<br/>documents"]
    c5["Create PDFs from<br/>scratch"]
    subgraph cg1["Text"]
      direction TB
      c2["Extract text and<br/>metadata"]
      c6["Support for standard<br/>fonts"]
    end
    subgraph cg2["Devices"]
      direction TB
      c3["Render pages to images"]
    end
    subgraph cg3["Facades"]
      direction TB
      c4["Encrypt and sign<br/>documents"]
      c7["Facades API for legacy<br/>workflows"]
    end
    c1 ~~~ cg1
    c5 ~~~ cg1
    cg1 ~~~ cg2
    cg2 ~~~ cg3
  end
  PRODUCT --> Capabilities
  classDef product fill:#1f6feb,stroke:#1f6feb,color:#ffffff
  class PRODUCT product
```

## Key Capabilities

- **Open and edit PDF documents.** It opens existing PDF files with `Aspose.Pdf.Document`, supports password-protected files by passing a user or owner password to the constructor, and reports encryption status via `IsEncrypted()`; it also allows byte-verbatim round-trips or incremental /Info updates that preserve original bytes.
- **Extract text and metadata.** It extracts text using Aspose.Pdf.Text::TextAbsorber to walk a whole document or a single page, and provides typed access to document information such as title, author, subject, keywords, creator, producer, and dates through `Aspose.Pdf.DocumentInfo`, plus arbitrary custom entries via Add/Remove/`ClearCustomData`.
- **Render pages to images.** It renders pages to raster images using Aspose.Pdf.Devices::PngDevice, `JpegDevice`, and `BmpDevice` for single-page output, and `TiffDevice` for single-page or multi-page ranges with median-cut palette quantisation or caller-supplied palette conversion.
- **Encrypt and sign documents.** It encrypts documents using Document::Encrypt with user and owner passwords, granular `Aspose.Pdf.Permissions` flags, and algorithms including RC4-40, RC4-128, AES-128, and AES-256, and signs documents with Aspose.Pdf.Facades::PdfFileSignature to add detached PKCS#7 signatures.
- **Create PDFs from scratch.** It builds documents from scratch using positioned text via Aspose.Pdf.Text::TextBuilder and `TextFragment`, tabular layout with `Aspose.Pdf.Table` (column widths, borders, background colours, and spanning cells), vector shapes via Aspose.Pdf.Drawing::Graph, and interactive AcroForm fields through `Aspose.Pdf.Forms`.
- **Support for standard fonts.** It supports the Standard-14 fonts without an embedded /FontFile, painting correctly via system fonts and falling back to bundled substitutes so glyphs render even in fontless Linux/CI containers.
- **Facades API for legacy workflows.** It provides the classic `Aspose.Pdf.Facades` API for legacy workflows, including `PdfConverter` for rasterisation, `PdfExtractor` for text extraction with page ranges, `PdfFileSecurity` for encryption and password changes, `PdfFileSignature` for signing, `PdfBookmarkEditor` for bookmarks, `PdfFileEditor` for concatenation and splitting, and `PdfFileStamp` for headers, footers, and page numbers.

- Extract text with `Text::TextAbsorber`, which walks a whole `Document` or a single `Page`, or
  `Text::TextFragmentAbsorber` for positioned fragments with font, size, and colour.
- Render pages to raster images through `PngDevice`, `JpegDevice`, and `BmpDevice` (single page
  per call), or `TiffDevice` (single page, or a full multi-page document range in one call via
  `Process(Document, startPage, endPage, ostream)`) — an anti-aliased renderer with no third-party
  runtime dependency;
  `TiffDevice` supports 1/4/8/24-bpp output with median-cut palette quantisation, or a
  caller-supplied `IIndexBitmapConverter` (`Get1BppImage`/`Get4BppImage`/`Get8BppImage`) for
  caller-controlled palette generation.
- Build documents from scratch: positioned and word-wrapped text through `Text::TextBuilder`,
  `TextFragment`, and `TextParagraph` (with font lookup via `FontRepository::FindFont`), tabular
  layout through `Table`/`Row`/`Cell` (column widths, per-cell and default borders, background
  colours, and column-spanning cells), vector shapes through `Drawing::Graph` (`Line`, `Rectangle`,
  `Circle`, `Ellipse`), and rotated, semi-transparent text overlays through `WatermarkArtifact`.
- References to the Standard-14 fonts (`/Helvetica`, `/Times-Roman`, `/Courier`, four styles
  each) without an embedded `/FontFile` paint correctly via system fonts, falling back to bundled
  Liberation substitutes (SIL OFL 1.1) so glyphs render even in fontless Linux/CI containers; text
  extracted through `TextDevice` goes through a pluggable `Encoding` — a BCL
  `System.Text.Encoding`-style charset codec supporting UTF-8, UTF-16LE, UTF-16BE, Latin-1, and
  Windows-1252 output.
- Add and manage annotations across a gallery of subtypes — `Highlight`, `Underline`, `Squiggly`,
  `StrikeOut`, `Square`, `Circle`, `Line`, `Ink`, `Text` (sticky note), `FreeText`, `Stamp`, `Link`
  (with `GoToAction`/`GoToURIAction`), and `FileAttachment` — each with a pre-generated `/AP`
  appearance stream so it renders in any spec-conforming viewer.
- Add interactive AcroForm fields — `TextBoxField`, `CheckboxField`, `RadioButtonField`,
  `ComboBoxField`, `ListBoxField`, and push-button `ButtonField` — through the `Form` class
  (`Document::Form()`), and flatten every field into static page content with `Form::Flatten()`.
- Define a hierarchical outline (bookmark) tree with `OutlineItemCollection`, bold/italic styling,
  and `XYZExplicitDestination` targets; define reusable `NamedDestination`s; and attach
  document-level companion files via `Document::EmbeddedFiles()`.
- Use the classic `Aspose::Pdf::Facades` API — `PdfConverter` (rasterise a PDF to multi-page TIFF
  or per-page PNG), `PdfExtractor` (text extraction honouring `StartPage`/`EndPage`),
  `PdfFileSecurity` (encrypt/decrypt/change passwords), `PdfFileSignature` (sign),
  `PdfBookmarkEditor` (create/extract bookmarks), `PdfFileEditor` (concatenate and split
  documents via `Concatenate`/`SplitFromFirst`/`SplitToEnd`/`SplitToPages`), and `PdfFileStamp`
  (page header/footer/page-number stamping via `AddHeader`/`AddFooter`/`AddPageNumber`) — each
  binding independently to a `Document`.

## Installation

The library is published on NuGet as `Aspose.PDF.Cpp.FOSS`.

To build it from a source checkout instead:

```bash
git clone https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp.git
cd Aspose.PDF-FOSS-for-Cpp
cmake -S . -B build
cmake --build build
```

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `CMakeLists.txt`, no dependency is on the library target's public link interface, so a consumer links nothing beyond the library itself.

### Native and System Requirements

- Requires C++ `20` (`CMAKE_CXX_STANDARD` in `CMakeLists.txt`).
- Requires CMake 3.20 or later (`cmake_minimum_required` in `CMakeLists.txt`).

### Development Dependencies

- `aspose_pdf_foss`
- `googletest`
- `Python3`

## Quick Start

This example opens a PDF document, prints the page count, extracts all text, and renders the first page as a PNG image at 150 DPI.

```cpp
#include <aspose/pdf/document.hpp>
#include <aspose/pdf/page_collection.hpp>
#include <aspose/pdf/text_absorber.hpp>
#include <aspose/pdf/png_device.hpp>
#include <aspose/pdf/resolution.hpp>
#include <fstream>
#include <iostream>

int main() {
    Aspose::Pdf::Document doc("input.pdf");
    std::cout << "Pages: " << doc.Pages().Count() << "\n";

    Aspose::Pdf::Text::TextAbsorber absorber;
    absorber.Visit(doc);
    std::cout << absorber.Text() << "\n";

    Aspose::Pdf::Devices::PngDevice png(Aspose::Pdf::Devices::Resolution(150));
    std::ofstream out("page1.png", std::ios::binary);
    png.Process(doc.Pages()[1], out);
}
```

## Additional Examples

The following workflows demonstrate opening encrypted files, reading and updating document metadata, and applying AESx256 encryption.

### Apply AESx256 Encryption with User and Owner Passwords

```cpp
#include <aspose/pdf/document.hpp>

int main() {
    Aspose::Pdf::Document doc("input.pdf");
    doc.Encrypt("user-password", "owner-password",
                Aspose::Pdf::Permissions(),
                Aspose::Pdf::CryptoAlgorithm::AESx256);
    doc.Save("encrypted.pdf");
}
```

<details>
<summary>View Additional Examples</summary>

### Open a Password-Protected PDF and Check Encryption Status

```cpp
#include <aspose/pdf/document.hpp>

// Encrypted files: pass the user or owner password
Aspose::Pdf::Document locked("locked.pdf", "secret");
if (locked.IsEncrypted()) {
    // proceed to read pages, extract text, etc.
}
```

### Read and Update Document Metadata, Then Save Changes

```cpp
#include <aspose/pdf/document.hpp>
#include <aspose/pdf/document_info.hpp>
#include <iostream>

int main() {
    Aspose::Pdf::Document doc("input.pdf");
    auto& info = doc.Info();
    std::cout << "Title: " << info.Title() << "\n";
    std::cout << "Author: " << info.Author() << "\n";

    doc.SetTitle("Updated Report Title");
    doc.Save("output.pdf");
}
```

### Include the Main Header to Access the Library

```cpp
#include <aspose.pdf.foss.hpp>
```

### Sign a Document

```cpp
#include <aspose/pdf/facades/pdf_file_signature.hpp>

Aspose::Pdf::Facades::PdfFileSignature sig{"input.pdf", "signed.pdf"};
// configure the signature (certificate + key), then sign and save — a detached PKCS#7
// (adbe.pkcs7.detached) signature with a byte-exact /ByteRange. Output verifies under the
// OpenSSL CLI. See tests/facades_pdf_file_signature_smoke_test.cpp for the full signing flow.
```

See [`tests/facades_pdf_file_signature_smoke_test.cpp`](tests/facades_pdf_file_signature_smoke_test.cpp)
for the full signing flow.

### Add an Annotation

```cpp
#include <aspose/pdf/annotations/highlight_annotation.hpp>

namespace ann = Aspose::Pdf::Annotations;
ann::HighlightAnnotation a(page, pdf::Rectangle(60, 700, 210, 716, true));  // keep alive until Save()
a.Color(pdf::Color::FromRgb(1.0, 0.95, 0.0));
a.Contents("Highlight");
page.Annotations().Add(a);
```

### Build an AcroForm Field

```cpp
#include <aspose/pdf/forms/text_box_field.hpp>

namespace frm = Aspose::Pdf::Forms;
frm::TextBoxField name(doc, pdf::Rectangle(190, 700, 470, 720, true));  // keep alive until Save()
name.PartialName("fullName");
name.Value("Alice Sample");
doc.Form().Add(name, /*pageNumber=*/1);
// doc.Form().Flatten();   // bake every field into static page content
```

### Build an Outline (Bookmark) Tree

```cpp
#include <aspose/pdf/outline_collection.hpp>
#include <aspose/pdf/outline_item_collection.hpp>
#include <aspose/pdf/annotations/xyz_explicit_destination.hpp>

auto& root = doc.Outlines();
pdf::OutlineItemCollection item(root);               // keep alive until Save()
item.Title("Chapter 1");
item.Bold(true);
item.Destination(ann::XYZExplicitDestination(page, 0.0, 842.0, 0.0));
root.Add(item);
```

### Use a Facade (PdfConverter / PdfExtractor)

```cpp
#include <aspose/pdf/facades/pdf_converter.hpp>
#include <aspose/pdf/facades/pdf_extractor.hpp>

namespace facades = Aspose::Pdf::Facades;

// Rasterise every page to a multi-page TIFF via the real Devices::TiffDevice pipeline
facades::PdfConverter converter;
converter.BindPdf("input.pdf");
converter.SaveAsTIFF("output.tiff");

// Extract text honouring a StartPage/EndPage range, via the foundation TextAbsorber
facades::PdfExtractor extractor;
extractor.BindPdf("input.pdf");
extractor.StartPage(1);
extractor.EndPage(1);
extractor.ExtractText();
extractor.GetText("page1.txt");
```

Each [GitHub release](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp/releases) ships
prebuilt archives for Linux x64 (GCC 13) and Windows x64 (MSVC, with Release and Debug libraries).
Each archive contains the public headers, the static library, and a CMake package. Extract it and
point `CMAKE_PREFIX_PATH` at the extracted folder:

```cmake
find_package(aspose_pdf_foss 1.0 CONFIG REQUIRED)
target_link_libraries(your_app PRIVATE aspose_pdf_foss::aspose_pdf_foss)
```

The same package is produced by `cmake --install build --prefix <dir>` from a source build.

Additional Examples below extends this into a from-scratch showcase
([`examples/12_create_features.cpp`](examples/12_create_features.cpp), one of the 12 programs
under `examples/` — see `examples/README.md`, built via `cmake --build build` into
`build/examples/<name>`): `Table`/`Row`/`Cell` layouts, `Drawing::Graph`
shapes (`Line`, `Rectangle`, `Circle`, `Ellipse`), annotations and AcroForm fields with a
pre-generated `/AP` appearance stream, `Form::Flatten()`-ready fields (`TextBoxField`,
`CheckboxField`, `RadioButtonField`, `ComboBoxField`, `ListBoxField`, `ButtonField`), an outline
(bookmark) tree, `CryptoAlgorithm`-based encryption (`RC4x40`/`RC4x128`/`AESx128`/`AESx256`) with
a `[Flags]` `Permissions` enum (not a DRM mechanism), a digital-signature walkthrough (see
`tests/facades_pdf_file_signature_smoke_test.cpp`), the `/Info`-metadata gotcha for from-scratch
documents, and the by-reference lifetime rule for `Paragraphs`/`Annotations`/`Form`/`Artifacts`/
`Outlines` — each parked in a `shared_ptr` until `Save()`.

12 runnable examples live in [`examples/`](examples/), covering the whole public surface —
opening documents, metadata, text extraction, save round-trips, every raster device, and a
from-scratch content-creation showcase. After `cmake --build build`, executables land at
`build/examples/<name>`; run them in numeric order, since each builds on the previous (see
[`examples/README.md`](examples/README.md) for the full tour).

> **Lifetime rule for creation.** `Paragraphs`, `Annotations`, `Form`, `Artifacts`, and `Outlines`
> store the object added to them **by reference**, so every table, graph, annotation, field,
> watermark, and outline item must outlive `Save()`.

| Example | Shows |
|---|---|
| `01_pages` | open a PDF, count pages, iterate the 1-based indexer |
| `02_read_metadata` / `03_write_metadata` | read `DocumentInfo`; edit + incremental-update save |
| `04_text_extraction` | `TextAbsorber::Visit(Document)` |
| `05_save_roundtrip` | byte-verbatim save |
| `06_devices_surface` | construct + round-trip device properties |
| `07_render_png` | end-to-end `PngDevice::Process(Page, ostream)` |
| `08_render_tiff` | multi-page TIFF via `TiffDevice::Process(Document, …)` |
| `09_indexed_tiff` | 8-bpp palettised TIFF (median-cut) |
| `10_render_text_pdf` | render a page with an embedded TrueType font |
| `11_render_standard14` | render `/Helvetica` with no embedded font (fallback path) |
| `12_create_features` | from-scratch 10-page showcase: text, image, tables, graphics, annotations, AcroForm fields, bookmarks |

</details>

## API Reference

Aspose.PDF FOSS for Cpp exposes the `Aspose.Pdf.Text`, `Aspose.Pdf.Devices`, `Aspose.Pdf.Annotations`, `Aspose.Pdf.Forms`, `Aspose.Pdf.Facades`, `Aspose.Pdf.CryptoAlgorithm`, `Aspose.Pdf.Drawing`, `Aspose.Pdf.Table`, `Aspose.Pdf.OutlineCollection`, `Aspose.Pdf.NamedDestinationCollection`, and `Aspose.Pdf.EmbeddedFileCollection` modules. Each module provides dedicated classes for working with specific PDF features.

The public API has 249 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `Annotation` | Annotation class provides the Accept, ActiveState, Alignment, AnnotationType, Border, Characteristics, Color, and Contents members for annotation objects. |
| `AnnotationCollection` | AnnotationCollection class provides the Accept, Add, Clear, Contains, Count, Delete, IsReadOnly, and Remove members for managing a collection of annotations. |
| `AnnotationSelector` | AnnotationSelector class provides the AnnotationSelector constructor and Visit method for selecting annotations. |
| `BleedMarkAnnotation` | BleedMarkAnnotation class provides the Accept method for bleed mark annotations. |
| `Border` | Border class provides the Effect, EffectIntensity, HCornerRadius, Style, VCornerRadius, and Width members for annotation borders. |
| `CaretAnnotation` | CaretAnnotation class provides the Accept, Frame, and Symbol members for caret annotations. |
| `Characteristics` | Characteristics class provides the Characteristics and Rotate members for annotation characteristics. |
| `CircleAnnotation` | CircleAnnotation class provides the Accept method for circle annotations. |
| `ColorBarAnnotation` | ColorBarAnnotation class provides the Accept and ColorOfCMYK members for color bar annotations. |
| `CommonFigureAnnotation` | CommonFigureAnnotation class provides the CommonFigureAnnotation constructor, Frame, and InteriorColor members for common figure annotations. |
| `CornerPrinterMarkAnnotation` | CornerPrinterMarkAnnotation class provides the Position member for corner printer mark annotations. |
| `DefaultAppearance` | DefaultAppearance class provides the DefaultAppearance constructor, FontName, FontResourceName, FontSize, and Text members for default appearance settings. |
| `ExplicitDestination` | ExplicitDestination class provides the ExplicitDestination constructor, PageNumber, and ToString members for explicit destinations. |
| `FileAttachmentAnnotation` | FileAttachmentAnnotation class provides the Accept, File, Icon, and Opacity members for file attachment annotations. |
| `FitBExplicitDestination` | Class that inherits from ExplicitDestination and declares the method ToString. |
| `FitBHExplicitDestination` | Class that inherits from ExplicitDestination and declares the methods Top and ToString. |
| `FitBVExplicitDestination` | Class that inherits from ExplicitDestination and declares the methods Left and ToString. |
| `FitExplicitDestination` | FitExplicitDestination class provides the ToString member for Fit explicit destinations. |
| `FitHExplicitDestination` | Class that inherits from ExplicitDestination and declares the methods Top and ToString. |
| `FitRExplicitDestination` | Class that inherits from ExplicitDestination and declares the methods Bottom, Left, Right, Top and ToString. |
| `FitVExplicitDestination` | Class that inherits from ExplicitDestination and declares the methods Left and ToString. |
| `FreeTextAnnotation` | FreeTextAnnotation class provides the Accept, Callout, DefaultAppearance, DefaultAppearanceObject, DefaultStyle, EndingStyle, Intent, and Justification members for free text annotations. |
| `GoToAction` | Class that inherits from PdfAction and declares the methods Destination, GetECMAScriptString and ToString. |
| `GoToURIAction` | Class that inherits from PdfAction and declares the methods GetECMAScriptString, ToString and URI. |
| `HighlightAnnotation` | HighlightAnnotation class provides the Accept method for highlight annotations. |
| `IAppointment` | IAppointment class provides an interface for appointment annotations. |
| `InkAnnotation` | InkAnnotation class represents an ink annotation that contains freehand drawing. |
| `JavascriptAction` | JavascriptAction class represents a JavaScript action that executes a script. |
| `LineAnnotation` | LineAnnotation class represents a line annotation that displays a straight line. |
| `LinkAnnotation` | LinkAnnotation class represents a link annotation that creates a clickable area. |
| `MarkupAnnotation` | MarkupAnnotation class provides base functionality for markup annotations. |
| `MovieAnnotation` | MovieAnnotation class represents a movie annotation that plays a video clip. |
| `NamedAction` | NamedAction class represents a named action that performs a predefined operation. |
| `NamedDestination` | NamedDestination class represents a named destination that points to a location in the document. |
| `PageInformationAnnotation` | PageInformationAnnotation class represents a page information annotation. |
| `PdfAction` | PdfAction class represents a PDF action that performs an operation. |
| `PolyAnnotation` | PolyAnnotation class provides base functionality for polygon and polyline annotations. |
| `PolygonAnnotation` | PolygonAnnotation class represents a polygon annotation. |
| `PolylineAnnotation` | PolylineAnnotation class represents a polyline annotation. |
| `PopupAnnotation` | PopupAnnotation class represents a popup annotation that displays a note. |
| `PrinterMarkAnnotation` | PrinterMarkAnnotation class provides functionality to add printer marks to a document. |
| `RedactionAnnotation` | RedactionAnnotation class represents a redaction annotation that hides content. |
| `RegistrationMarkAnnotation` | RegistrationMarkAnnotation class represents a registration mark annotation. |
| `RichMediaAnnotation` | RichMediaAnnotation class represents a rich media annotation that embeds interactive content. |
| `ScreenAnnotation` | ScreenAnnotation class represents a screen annotation that creates a media player area. |
| `SoundAnnotation` | SoundAnnotation class represents a sound annotation that plays an audio clip. |
| `SquareAnnotation` | SquareAnnotation class represents a square annotation. |
| `SquigglyAnnotation` | SquigglyAnnotation class represents a squiggly underline annotation. |
| `StampAnnotation` | StampAnnotation class represents a stamp annotation that applies a visual mark. |
| `StrikeOutAnnotation` | StrikeOutAnnotation class represents a strikeout annotation. |
| `SubmitFormAction` | SubmitFormAction class represents a form submission action. |
| `TextAnnotation` | TextAnnotation class represents a text annotation that displays a note. |
| `TextMarkupAnnotation` | TextMarkupAnnotation class provides GetMarkedText, QuadPoints, and TextMarkupAnnotation members for text markup annotations. |
| `TextStyle` | TextStyle class provides Alignment, FontName, FontSize, HorizontalAlignment, and TextStyle members for text styling. |
| `TrimMarkAnnotation` | TrimMarkAnnotation class provides an Accept method for trim mark annotations. |
| `UnderlineAnnotation` | UnderlineAnnotation class provides an Accept method for underline annotations. |
| `WatermarkAnnotation` | WatermarkAnnotation class provides Accept and Opacity methods for watermark annotations. |
| `WidgetAnnotation` | WidgetAnnotation class provides Accept, DefaultAppearance, Exportable, GetCheckedStateName, Highlighting, Parent, ReadOnly, and Required methods for widget annotations. |
| `XYZExplicitDestination` | XYZExplicitDestination class provides Left, ToString, Top, and Zoom methods for XYZ explicit destinations. |
| `Artifact` | Artifact class provides IsBackground, Opacity, Position, Rotation, SetImage, SetTextAndState, Text, and TextState methods for artifacts. |
| `ArtifactCollection` | ArtifactCollection class provides Add, ArtifactCollection, Count, Delete, and Update methods for artifact collections. |
| `BaseParagraph` | BaseParagraph class provides BaseParagraph, HorizontalAlignment, Hyperlink, IsFirstParagraphInColumn, IsInLineParagraph, IsInNewPage, IsKeptWithNext, and Margin methods for base paragraphs. |
| `BitmapInfo` | BitmapInfo class provides BitmapInfo, Format, Height, PixelBytes, PixelFormat, and Width methods for bitmap information. |
| `BorderInfo` | BorderInfo class provides Bottom, Left, Right, RoundedBorderRadius, and Top methods for border information. |
| `Cell` | Cell class provides Alignment, BackgroundColor, BackgroundImage, BackgroundImageFile, Border, ColSpan, DefaultCellTextState, and IsNoBorder methods for table cells. |
| `Cells` | Cells class provides Add, Count, Insert, Remove, and RemoveRange methods for collections of cells. |
| `Color` | Color class provides A, AliceBlue, AntiqueWhite, Aqua, Aquamarine, Azure, Beige, and Bisque methods for color values. |
| `BmpDevice` | BmpDevice class provides a Process method for BMP device rendering. |
| `Device` | Device class provides a Device constructor for device classes. |
| `DocumentDevice` | DocumentDevice class provides a Process method for document device rendering. |
| `ImageDevice` | ImageDevice class provides CoordinateType, FormPresentationMode, GetBitmap, Height, RenderingOptions, Resolution, and Width methods for image device rendering. |
| `JpegDevice` | JpegDevice class provides a Process method for JPEG device rendering. |
| `Margins` | Margins class provides Bottom, Left, Right, and Top methods for margin information. |
| `PageDevice` | PageDevice class provides a Process method for page device rendering. |
| `PngDevice` | PngDevice class provides Process and TransparentBackground methods for PNG device rendering. |
| `Resolution` | Resolution class provides X and Y methods for resolution information. |
| `TextDevice` | TextDevice class provides GetEncoding, Process, and SetEncoding methods for text device rendering. |
| `TiffDevice` | TiffDevice class provides BinarizeBradley, FormPresentationMode, Height, Process, RenderingOptions, Resolution, Settings, and Width methods for TIFF device rendering. |
| `TiffSettings` | TiffSettings class provides Brightness, Compression, CoordinateType, Depth, Margins, Shape, and SkipBlankPages methods for TIFF settings. |
| `Document` | Document class provides Decrypt, Document, EmbeddedFiles, Encrypt, Form, Info, IsEncrypted, and Metadata methods for PDF documents. |
| `DocumentInfo` | DocumentInfo class provides Add, Author, Clear, ClearCustomData, Creator, DocumentInfo, IsPredefinedKey, and Keywords methods for document information. |
| `Circle` | Circle class provides CheckBounds, PosX, PosY, and Radius methods for circle drawing. |
| `Ellipse` | Ellipse class provides Bottom, CheckBounds, Height, Left, and Width methods for ellipse drawing. |
| `Graph` | Graph class provides Border, GraphInfo, Height, IsChangePosition, Left, Shapes, Top, and Width methods for graph drawing. |
| `Line` | Line class provides CheckBounds and PositionArray methods for line drawing. |
| `Drawing.Rectangle` | Rectangle class provides geometric operations and properties for a rectangle, including Bottom, CheckBounds, Height, Left, RoundedCornerRadius, and Width methods. |
| `Shape` | Shape class provides shape drawing capabilities with CheckBounds, GraphInfo, and Shape methods. |
| `EmbeddedFileCollection` | EmbeddedFileCollection class manages embedded files with Add, Count, Delete, DeleteByKey, EmbeddedFileCollection, FindByName, and Keys methods. |
| `AlignmentType` | AlignmentType class provides text alignment options with Center, Left, Right, and ToString methods. |
| `Bookmark` | Bookmark class represents a bookmark with Action, BoldFlag, Bookmark, ChildItem, ChildItems, Destination, ItalicFlag, and Level methods. |
| `Bookmarks` | Bookmarks class provides bookmark collection functionality with the Bookmarks method. |
| `DocumentPrivilege` | DocumentPrivilege class provides document permission methods including AllowAll, AllowAssembly, AllowCopy, AllowDegradedPrinting, AllowFillIn, AllowModifyAnnotations, AllowModifyContents, and AllowPrint. |
| `Facade` | Facade class provides base facade functionality with BindPdf, Close, Dispose, Document, and Facade methods. |
| `FormEditor` | FormEditor class provides form editing methods including AddField, AddFieldScript, AddListItem, AddSubmitBtn, ConvertTo, CopyInnerField, CopyOuterField, and DecorateField. |
| `FormFieldFacade` | FormFieldFacade class provides form field alignment constants including AlignBottom, AlignCenter, AlignJustified, AlignLeft, AlignMiddle, AlignRight, AlignTop, and AlignUndefined. |
| `IFacade` | IFacade interface provides facade contract methods including BindPdf, Close, and IFacade. |
| `ISaveableFacade` | ISaveableFacade interface provides save contract methods including ISaveableFacade and Save. |
| `PdfAnnotationEditor` | PdfAnnotationEditor class provides annotation editing methods including DeleteAnnotation, DeleteAnnotations, FlatteningAnnotations, ImportAnnotationFromXfdf, ImportAnnotations, ImportAnnotationsFromFdf, ImportAnnotationsFromXfdf, and ModifyAnnotations. |
| `PdfBookmarkEditor` | PdfBookmarkEditor class provides bookmark editing methods including CreateBookmarkOfPage, CreateBookmarks, DeleteBookmarks, ExportBookmarksToHtml, ExportBookmarksToXML, ExtractBookmarks, ExtractBookmarksToHTML, and ImportBookmarksWithXML. |
| `PdfContentEditor` | PdfContentEditor class provides content editing methods including AddDocumentAdditionalAction, AddDocumentAttachment, ChangeViewerPreference, DeleteAttachments, DeleteImage, DeleteStamp, DeleteStampById, and DeleteStampByIds. |
| `PdfConverter` | PdfConverter class provides conversion methods including CoordinateType, DoConvert, EndPage, FormPresentationMode, GetNextImage, HasNextImage, PageCount, and Password. |
| `PdfExtractor` | PdfExtractor class provides extraction methods including EndPage, ExtractAttachment, ExtractImage, ExtractText, ExtractTextMode, GetAttachNames, GetAttachment, and GetAttachmentInfo. |
| `PdfFileEditor` | PdfFileEditor class provides file editing methods including AddMargins, AddMarginsPct, AddPageBreak, AllowConcatenateExceptions, Append, CloseConcatenatedStreams, Concatenate, and ConcatenationPacketSize. |
| `PdfFileInfo` | PdfFileInfo class provides file information methods including Author, BindPdf, ClearInfo, CreationDate, Creator, GetMetaInfo, GetPageHeight, and GetPageRotation. |
| `PdfFileSecurity` | PdfFileSecurity class provides file security methods including AllowExceptions, BindPdf, ChangePassword, DecryptFile, EncryptFile, InputFile, OutputFile, and PdfFileSecurity. |
| `PdfFileSignature` | PdfFileSignature class provides signature methods including Certify, ContainsSignature, ContainsUsageRights, CoversWholeDocument, GetAccessPermissions, GetBlankSignNames, GetBlankSignatureNames, and GetContactInfo. |
| `PdfFileStamp` | PdfFileStamp class provides stamping methods including AddFooter, AddHeader, AddPageNumber, ConvertTo, InputFile, KeepSecurity, OptimizeSize, and OutputFile. |
| `PdfPageEditor` | PdfPageEditor class provides page editing members including Alignment, ApplyChanges, BLINDH, BLINDV, BTWIPE, DGLITTER, DISSOLVE, and DisplayDuration. |
| `PdfXmpMetadata` | PdfXmpMetadata class provides XMP metadata methods including Add, Clear, Contains, ContainsKey, Count, GetNamespaceURIByPrefix, GetPrefixByNamespaceURI, and IsFixedSize. |
| `SaveableFacade` | SaveableFacade class provides save functionality with Save and SaveableFacade methods. |
| `SignatureName` | SignatureName class provides signature name functionality with FullName, GetHashCode, HasSignature, Name, SignatureName, and ToString members. |
| `VerticalAlignmentType` | VerticalAlignmentType enum lists the Bottom, Center, and Top vertical alignment values. |
| `FileSpecification` | FileSpecification class provides methods to manage file specification details including AFRelationship, Description, Encoding, FileSystem, IncludeContents, MIMEType, Name, and UnicodeName. |
| `FloatingBox` | FloatingBox class provides methods to manage BackgroundColor, Border, Height, IsNeedRepeating, Paragraphs, and Width members. |
| `BarcodeField` | BarcodeField class provides methods to manage Caption, ECC, Resolution, Symbology, XSymHeight, and XSymWidth members. |
| `ButtonField` | ButtonField class provides methods to manage AlternateCaption, ICPosition, IconFit, NormalCaption, and RolloverCaption members. |
| `CheckboxField` | CheckboxField class provides methods to manage ActiveState, AllowedStates, Checked, Clone, ExportValue, and Style members. |
| `ChoiceField` | ChoiceField class provides methods to manage CommitImmediately, MultiSelect, Options, Selected, SelectedItems, and Value members. |
| `ComboBoxField` | ComboBoxField class provides methods to manage Editable and SpellCheck members. |
| `DateField` | DateField class provides methods to manage DateFormat and Init members. |
| `DocMDPSignature` | DocMDPSignature class provides a method to manage AccessPermissions. |
| `ExternalSignature` | ExternalSignature class represents an external digital signature. |
| `Field` | Field class provides methods to manage AlternateName, AnnotationIndex, Count, FitIntoRectangle, Flatten, IsGroup, IsSharedField, and MappingName members. |
| `FileSelectBoxField` | FileSelectBoxField class provides a method to manage file selection box functionality. |
| `Form` | Form class provides methods to manage Add, AddFieldAppearance, AutoRecalculate, AutoRestoreForm, CalculatedFields, Count, DefaultAppearance, and Delete operations. |
| `IconFit` | IconFit class provides methods to manage IconFit, LeftoverBottom, LeftoverLeft, NameToScalingMode, NameToScalingReason, ScalingMode, ScalingModeToName, and ScalingReason members. |
| `ListBoxField` | ListBoxField class provides methods to manage TopIndex property. |
| `NumberField` | NumberField class provides methods to manage AllowedChars property. |
| `Option` | Option class provides methods to manage Index, Name, Selected, and Value members. |
| `OptionCollection` | OptionCollection class provides methods to manage Add, Clear, Contains, Count, Get, IsReadOnly, and Remove operations. |
| `PKCS1` | PKCS1 class provides a method to manage PKCS#1 signature operations. |
| `PKCS7` | PKCS7 class provides a method to manage PKCS#7 signature operations. |
| `PKCS7Detached` | PKCS7Detached class provides a method to manage detached PKCS#7 signature operations. |
| `PasswordBoxField` | PasswordBoxField class provides a method to manage password box functionality. |
| `RadioButtonField` | RadioButtonField class provides methods to manage Add, AddOption, NoToggleToOff, SetPosition, and Style members. |
| `RadioButtonOptionField` | RadioButtonOptionField class provides methods to manage OptionName and Style members. |
| `RichTextBoxField` | RichTextBoxField class provides methods to manage FormattedValue, Justify, RichTextValue, and Value members. |
| `Signature` | Signature class provides methods to manage Authority, AvoidEstimatingSignatureLength, ByteRange, ContactInfo, CustomAppearance, DefaultSignatureLength, Location, and Reason members. |
| `SignatureCustomAppearance` | SignatureCustomAppearance class provides methods to manage BackgroundColor, ContactInfoLabel, DateSignedAtLabel, DateTimeFormat, DateTimeLocalFormat, DigitalSignedLabel, DigitalSubjectFormat, and FontFamilyName members. |
| `SignatureField` | SignatureField class provides methods to manage Sign and Signature operations. |
| `TextBoxField` | TextBoxField class provides methods to manage AddBarcode, ForceCombs, MaxLen, Multiline, Scrollable, SpellCheck, TextVerticalAlignment, and Value members. |
| `XFA` | Aspose.Pdf.Forms.XFA class provides access to XFA field names and the XFA data stream. |
| `GraphInfo` | Aspose.Pdf.GraphInfo class holds the color, fill color, line width, dash array, dash phase, rotation angle, and scaling information for vector graphics. |
| `Hyperlink` | Aspose.Pdf.Hyperlink class represents a hyperlink object. |
| `IIndexBitmapConverter` | Aspose.Pdf.IIndexBitmapConverter interface provides methods to convert indexed bitmaps to 1-bpp, 4-bpp, and 8-bpp images. |
| `LoadOptions` | Aspose.Pdf.LoadOptions class provides options for loading PDF documents, including disabling font license verifications. |
| `MarginInfo` | Aspose.Pdf.MarginInfo class holds the left, right, top, and bottom margin values. |
| `Metadata` | Aspose.Pdf.Metadata class provides methods to add, remove, and query document metadata, including namespace prefix management. |
| `NamedDestinationCollection` | Aspose.Pdf.NamedDestinationCollection class provides methods to add, remove, and enumerate named destinations. |
| `OutlineCollection` | Aspose.Pdf.OutlineCollection class represents the collection of document outlines. |
| `OutlineItemCollection` | Aspose.Pdf.OutlineItemCollection class provides methods to manage outline items, including action, destination, bold, italic, level, and next item properties. |
| `Outlines` | Aspose.Pdf.Outlines class provides methods to add, remove, and enumerate outline items. |
| `Page` | Aspose.Pdf.Page class provides methods to add images, annotations, and artifacts, and to access page boxes such as MediaBox, CropBox, ArtBox, and BleedBox. |
| `PageCollection` | Aspose.Pdf.PageCollection class provides methods to add, insert, and delete pages. |
| `PageLabel` | Aspose.Pdf.PageLabel class provides methods to set the numbering style, prefix, and starting value for page labels. |
| `PageLabelCollection` | Aspose.Pdf.PageLabelCollection class provides methods to get page labels, retrieve pages for a label, and update or remove labels. |
| `PageSize` | Aspose.Pdf.PageSize class provides methods to access standard page sizes such as A0 through A6 and B5. |
| `Paragraphs` | Aspose.Pdf.Paragraphs class provides methods to add, insert, remove, and clear paragraphs. |
| `Point` | Aspose.Pdf.Point class provides methods to calculate distance, access X and Y coordinates, and check triviality. |
| `Pdf.Rectangle` | Aspose.Pdf.Rectangle class provides methods to check containment of points and lines, compute center, height, and perform intersection. |
| `RenderingOptions` | Aspose.Pdf.RenderingOptions class provides options for rendering, including font analysis, barcode optimization, font conversion, default font name, cache size, and interpolation quality. |
| `Resources` | Aspose.Pdf.Resources class provides access to images and resources. |
| `Row` | Aspose.Pdf.Row class provides methods to set background color, border, cells, default cell properties, fixed row height, and new page behavior. |
| `Rows` | Aspose.Pdf.Rows class provides methods to add, count, index, remove, and remove ranges of rows. |
| `SvgLoadOptions` | Aspose.Pdf.SvgLoadOptions class provides options for loading SVG, including adjusting page size. |
| `Table` | Aspose.Pdf.Table class provides methods to set alignment, background color, border, column widths, and default cell properties. |
| `Encoding` | Aspose.Pdf.Text.Encoding class provides methods to encode and decode text, including BigEndianUnicode, code page, and string conversion. |
| `Font` | Aspose.Pdf.Text.Font class provides methods to access base font, font name, and embedding or subset status. |
| `FontRepository` | Aspose.Pdf.Text.FontRepository class provides methods to find and open fonts. |
| `Position` | Aspose.Pdf.Text.Position class provides methods to set X and Y indentation for text. |
| `TextAbsorber` | Aspose.Pdf.Text.TextAbsorber class provides methods to visit pages, extract text, check for errors, and access the extracted text. |
| `TextBuilder` | Aspose.Pdf.Text.TextBuilder class provides methods to append text and paragraphs to a page. |
| `TextFragment` | Aspose.Pdf.Text.TextFragment class provides methods to set position, rectangle, text, text state, and constructor. |
| `TextFragmentAbsorber` | Aspose.Pdf.Text.TextFragmentAbsorber class provides methods to visit pages and access text fragments. |
| `TextFragmentCollection` | TextFragmentCollection class holds a collection of text fragments and provides a Count method to get the number of items. |
| `TextFragmentState` | TextFragmentState class provides state settings for text fragments and includes a constructor to initialize a new instance. |
| `TextParagraph` | TextParagraph class represents a paragraph of text and provides methods such as AppendLine, FirstLineIndent, HorizontalAlignment, Margin, Position, Rectangle, SubsequentLinesIndent, and VerticalAlignment to configure its content and layout. |
| `TextState` | TextState class defines text appearance settings and provides methods such as BackgroundColor, CharacterSpacing, Font, FontSize, ForegroundColor, HorizontalAlignment, HorizontalScaling, and Invisible to control formatting. |
| `WatermarkArtifact` | WatermarkArtifact class represents a watermark artifact that can be added to a PDF page. |
| `XImage` | XImage class represents an image in a PDF document and provides methods such as ContainsTransparency, GetRawImageData, Height, ImageMask, Name, and Width to access its properties. |
| `XImageCollection` | XImageCollection class manages a collection of XImage objects and provides methods such as Add, Clear, Contains, Count, Delete, GetImageName, Names, and Remove to manipulate the collection. |
| `XmpValue` | XmpValue class represents an XMP value and provides methods such as IsArray, IsDateTime, IsDouble, IsField, IsInteger, IsNamedValue, IsNamedValues, and IsRaw to query its type; IsDateTime, IsField, IsNamedValue, IsNamedValues, IsRaw, and IsStructure always return false. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `AFRelationship` | AFRelationship enum lists the Alternative, Data, EncryptedPayload, None, Source, Supplement, and Unspecified relationship values. |
| `AnnotationFlags` | AnnotationFlags enum lists the Default, Hidden, Invisible, Locked, LockedContents, NoRotate, NoView, NoZoom, Print, ReadOnly, and ToggleNoView flag values. |
| `AnnotationState` | AnnotationState enum lists the Accepted, Cancelled, Completed, Marked, None, Rejected, and Unmarked state values. |
| `AnnotationStateModel` | AnnotationStateModel enum lists the Marked, None, and Review state model values. |
| `AnnotationType` | AnnotationType enum lists the BleedMark, Caret, Circle, ColorBar, FileAttachment, FreeText, Highlight, Ink, Line, Link, Movie, and PDF3D annotation type values. |
| `BorderEffect` | BorderEffect enum lists the Cloudy and None border effect values. |
| `BorderStyle` | BorderStyle enum lists the Beveled, Dashed, Inset, Solid, and Underline border style values. |
| `CapStyle` | CapStyle enum lists the Butt and Rounded cap style values. |
| `CaptionPosition` | CaptionPosition enum lists the Inline and Top caption position values. |
| `CaretSymbol` | CaretSymbol enum lists the None and Paragraph caret symbol values. |
| `ColorsOfCMYK` | ColorsOfCMYK enum lists the Black, Cyan, Magenta, and Yellow color values. |
| `ExplicitDestinationType` | ExplicitDestinationType enum lists the Fit, FitB, FitBH, FitBV, FitH, FitR, FitV, and XYZ destination type values. |
| `FileIcon` | FileIcon enum lists the Graph, Paperclip, PushPin, and Tag file icon values. |
| `FreeTextIntent` | FreeTextIntent enum lists the FreeText, FreeTextCallout, FreeTextTypeWriter, and Undefined intent values. |
| `HighlightingMode` | HighlightingMode enum lists the Invert, None, Outline, Push, and Toggle highlighting mode values. |
| `Justification` | Justification enum lists the Centered, LeftJustify and RightJustify text justification options. |
| `LineEnding` | LineEnding enum lists the Butt, Circle, ClosedArrow, Diamond, None, OpenArrow, RClosedArrow, ROpenArrow, Slash and Square line ending styles. |
| `LineIntent` | LineIntent enum lists the LineArrow, LineDimension and Undefined line intent values. |
| `PolyIntent` | PolyIntent enum lists the PolyLineDimension, PolygonCloud, PolygonDimension and Undefined polygon intent values. |
| `PredefinedAction` | PredefinedAction enum lists the Bookmarks_ExpanCurrentBookmark, Bookmarks_HightlightCurrentBookmark, Document_AttachFile, Document_CropPages, Document_DeletePages, Document_ExtractPages, Document_InsertPages, Document_ReplacePages, Document_RotatePages, Edit_CheckSpelling_InComFieldEdit, Edit_Find and Edit_Preferences predefined actions. |
| `PrinterMarkCornerPosition` | PrinterMarkCornerPosition enum lists the BottomLeft, BottomRight, TopLeft and TopRight corner positions for printer marks. |
| `PrinterMarkSidePosition` | PrinterMarkSidePosition enum lists the Bottom, Left, Right and Top side positions for printer marks. |
| `PrinterMarksKind` | PrinterMarksKind enum lists the All, BleedMarks, ColorBars, None, PageInformation, RegistrationMarks and TrimMarks printer mark kinds. |
| `ReplyType` | ReplyType enum lists the Group, Reply and Undefined reply type values. |
| `RichTextFontStyles` | RichTextFontStyles enum lists the Bold, BoldItalic, Italic and Plain font styles for rich text. |
| `SoundIcon` | SoundIcon enum lists the Mic and Speaker icons for sound annotations. |
| `StampIcon` | StampIcon enum lists the Approved, AsIs, Confidential, Departmental, Draft, Experimental, Expired, Final, ForComment, ForPublicRelease, NotApproved and NotForPublicRelease stamp icons. |
| `TextAlignment` | TextAlignment enum lists the Center, Left and Right text alignment options. |
| `TextIcon` | TextIcon enum lists the Check, Circle, Comment, Cross, Help, Insert, Key, NewParagraph, Note, Paragraph, RightArrow, and RightPointer icon types. |
| `BorderSide` | BorderSide enum lists the All, Bottom, Box, Left, None, Right, and Top border side values. |
| `CryptoAlgorithm` | CryptoAlgorithm enum lists the AESx128, AESx256, RC4x128, and RC4x40 cryptographic algorithm values. |
| `ColorDepth` | ColorDepth enum lists the Default, Format1bpp, Format24bpp, Format4bpp, and Format8bpp color depth values. |
| `CompressionType` | CompressionType enum lists the CCITT3, CCITT4, LZW, None, and RLE compression type values. |
| `FormPresentationMode` | FormPresentationMode enum lists the Editor and Production form presentation mode values. |
| `ShapeType` | ShapeType enum lists the Landscape, None, and Portrait shape type values. |
| `Algorithm` | Algorithm enum lists the AES and RC4 encryption algorithm values. |
| `AutoRotateMode` | AutoRotateMode enum lists the AntiClockWise, ClockWise, and None rotation mode values. |
| `BlendingColorSpace` | BlendingColorSpace enum lists the Auto, DeviceCMYK, DeviceRGB, and DontChange blending color space values. |
| `DataType` | DataType enum lists the FDF, ODBC, OLEDB, PDF, XFDF, and XML data type values. |
| `DefaultMetadataProperties` | DefaultMetadataProperties enum lists the Advisory, BaseURL, CreateDate, CreatorTool, Identifier, MetadataDate, ModifyDate, Nickname, and Thumbnails metadata property values. |
| `EncodingType` | EncodingType enum lists the Cp1250, Cp1252, Cp1257, Identity_h, Identity_v, Macroman, and Winansi encoding type values. |
| `FieldType` | FieldType enum lists the Barcode, CheckBox, ComboBox, DateTime, Image, InvalidNameOrType, ListBox, MultiLineText, Numeric, PushButton, Radio, and Signature field type values. |
| `FontStyle` | FontStyle enum lists the CjkFont, Courier, CourierBold, CourierBoldOblique, CourierOblique, Helvetica, HelveticaBold, HelveticaBoldOblique, HelveticaOblique, Symbol, TimesBold, and TimesBoldItalic font style values. |
| `ImageMergeMode` | ImageMergeMode enum lists the Center, Horizontal, and Vertical image merge mode values. |
| `KeySize` | KeySize enum lists the x128, x256, and x40 key size values. |
| `PositioningMode` | PositioningMode enum lists the Current, Legacy, and ModernLineSpacing positioning mode values. |
| `PropertyFlag` | PropertyFlag enum lists the InvalidFlag, NoExport, ReadOnly, and Required property flag values. |
| `StampType` | StampType enum lists the Form and Image stamp type values. |
| `SubmitFormFlag` | SubmitFormFlag enum lists the Fdf, FdfWithComments, Html, Pdf, Xfdf, and XfdfWithComments submit form flag values. |
| `WordWrapMode` | WordWrapMode enum lists the ByWords and Default word wrap modes. |
| `FileEncoding` | FileEncoding enum lists the None and Zip file encoding options. |
| `BoxStyle` | BoxStyle enum lists the Check, Circle, Cross, Diamond, Square, and Star box style values. |
| `DocMDPAccessPermissions` | DocMDPAccessPermissions enum lists the AnnotationModification, FillingInForms, and NoChanges access permission values. |
| `FormType` | FormType enum lists the Dynamic, Standard, and Static form type values. |
| `IconCaptionPosition` | IconCaptionPosition enum lists the CaptionAboveIcon, CaptionBelowIcon, CaptionOverlaid, CaptionToTheLeft, CaptionToTheRight, NoCaption, and NoIcon caption position values. |
| `ScalingMode` | ScalingMode enum lists the Anamorphic and Proportional scaling mode values. |
| `ScalingReason` | ScalingReason enum lists the Always, IconIsBigger, IconIsSmaller, and Never scaling reason values. |
| `SubjectNameElements` | SubjectNameElements enum lists the C, CN, E, L, O, OU, and S subject name element values. |
| `Symbology` | Symbology enum lists the DataMatrix, PDF417, and QRCode symbology values. |
| `HorizontalAlignment` | Aspose.Pdf.HorizontalAlignment enum lists the Center, FullJustify, Justify, Left, None, and Right horizontal alignment options. |
| `NumberingStyle` | Aspose.Pdf.NumberingStyle enum lists the LettersLowercase, LettersUppercase, None, NumeralsArabic, NumeralsRomanLowercase, and NumeralsRomanUppercase numbering styles. |
| `PageCoordinateType` | Aspose.Pdf.PageCoordinateType enum lists the CropBox and MediaBox coordinate types. |
| `PasswordType` | Aspose.Pdf.PasswordType enum lists the Inaccessible, None, Owner, and User password types. |
| `PdfFormat` | Aspose.Pdf.PdfFormat enum lists the PDF/A and PDF/E format versions such as PDF_A_1A, PDF_A_1B, PDF_A_2A, PDF_A_2B, PDF_A_2U, PDF_A_3A, PDF_A_3B, PDF_A_3U, PDF_A_4, PDF_A_4E, PDF_A_4F, and PDF_E_1. |
| `Permissions` | Aspose.Pdf.Permissions enum lists the document permission flags such as AssembleDocument, ExtractContent, ExtractContentWithDisabilities, FillForm, ModifyContent, ModifyTextAnnotations, PrintDocument, and PrintingQuality. |
| `Rotation` | Aspose.Pdf.Rotation enum lists the None, on90, on180, and on270 rotation values. |
| `VerticalAlignment` | VerticalAlignment enum lists the Bottom, Center, None, and Top vertical alignment options. |

#### Detailed Member Reference

### Text

The `Aspose.Pdf.Text` module provides text extraction and construction capabilities through `TextAbsorber`, `TextFragmentAbsorber`, and `TextBuilder`. `TextAbsorber` visits a page and populates its Text property with the extracted text, while `TextFragmentAbsorber` returns a collection of text fragments via its `TextFragments` property after calling Visit. `TextBuilder` lets developers append paragraphs and text to a page.

### Devices

The `Aspose.Pdf.Devices` module enables rendering pages to image formats via `PageDevice` and `Resolution`. `Resolution` exposes horizontal and vertical DPI values, and `PageDevice` implements the Process method to render a page to a stream.

### Annotations

The `Aspose.Pdf.Annotations` module supports adding and managing annotations through `Annotation` and `AnnotationCollection`. `Annotation` provides properties and methods to configure appearance, position, and behavior, and `AnnotationCollection` offers collection operations such as Add, Remove, and Delete.

### Forms

The `Aspose.Pdf.Forms` module provides form field support through `Field` and `FormType`.

### Facades

The `Aspose.Pdf.Facades` module offers high-level operations through `PdfConverter` and `PdfExtractor`. `PdfConverter` converts PDF pages to raster images, and `PdfExtractor` extracts text from a specified page range.

### CryptoAlgorithm

The `Aspose.Pdf.CryptoAlgorithm` module defines encryption algorithms and permissions for securing PDF documents. `CryptoAlgorithm` enumerates supported algorithms, and `Permissions` provides a flags enum for access control per ISO 32000-1.

### Drawing

The `Aspose.Pdf.Drawing` module enables vector graphics via `Graph` and shape primitives. `Graph` holds a collection of shapes such as `Line`, `Rectangle`, `Circle`, and `Ellipse`.

### Table

The `Aspose.Pdf.Table` module supports tabular content through `Table` and `Row`. `Table` exposes rows and border settings, and `Row` provides cells for adding content.

### OutlineCollection

The `Aspose.Pdf.OutlineCollection` module manages document outlines via `OutlineCollection` and `OutlineItemCollection`. `OutlineItemCollection` supports setting title, bold style, and destination for outline items.

### NamedDestinationCollection

The `Aspose.Pdf.NamedDestinationCollection` module provides named destinations through `NamedDestinationCollection` and `XYZExplicitDestination`. `XYZExplicitDestination` supplies explicit page view coordinates via Left, Top, and Zoom methods.

### EmbeddedFileCollection

The `Aspose.Pdf.EmbeddedFileCollection` module supports embedding files via `EmbeddedFileCollection` and `FileSpecification`. `FileSpecification` enables associating an external file with a PDF document.

Available subtypes: `Highlight`, `Underline`, `Squiggly`, `StrikeOut`, `Square`, `Circle`, `Line`,
`Ink`, `Text`, `FreeText`, `Stamp`, `Link` (with `GoToAction`/`GoToURIAction`), `FileAttachment`.

`PdfConverter` also exposes a per-page cursor — `HasNextImage()`/`GetNextImage(outputFile)` — for
walking pages one at a time as PNGs via `Devices::PngDevice`, and `PageCount()` for the real page
count.

| Enumeration | Description |
|---|---|
| `AFRelationship` | Enumerates Alternative, Data, EncryptedPayload, None, Source, Supplement and Unspecified. |
| `BorderSide` | Enumerates All, Bottom, Box, Left, None, Right and Top. |
| `ColorDepth` | Enumerates Default, Format1bpp, Format24bpp, Format4bpp and Format8bpp. |
| `CompressionType` | Enumerates CCITT3, CCITT4, LZW, None and RLE. |
| `CryptoAlgorithm` | Enumerates AESx128, AESx256, RC4x128 and RC4x40. |
| `FileEncoding` | Enumerates None and Zip. |
| `FormPresentationMode` | Enumerates Editor and Production. |
| `HorizontalAlignment` | Enumerates Center, FullJustify, Justify, Left, None and Right. |
| `NumberingStyle` | Enumerates LettersLowercase, LettersUppercase, None, NumeralsArabic, NumeralsRomanLowercase and NumeralsRomanUppercase. |
| `PageCoordinateType` | PageCoordinateType enum values MediaBox and CropBox let developers choose which page rectangle is used for coordinate calculations. |
| `PasswordType` | Enumerates Inaccessible, None, Owner and User. |
| `PdfFormat` | Enumerates values including PDF_A_1A, PDF_A_1B, PDF_A_2A, PDF_A_2B, PDF_A_2U, PDF_A_3A, PDF_A_3B and PDF_A_3U. |
| `Permissions` | Enumerates AssembleDocument, ExtractContent, ExtractContentWithDisabilities, FillForm, ModifyContent, ModifyTextAnnotations, PrintDocument and PrintingQuality. |
| `Rotation` | Rotation enum provides four orientation values: None, on90, on180, on270. |
| `ShapeType` | Enumerates Landscape, None and Portrait. |
| `VerticalAlignment` | Enumerates Bottom, Center, None and Top. |

| Class | Description |
|---|---|
| `Annotation` | Class that inherits from BaseParagraph and declares methods including Accept, ActiveState, Alignment, AnnotationType, Border and Characteristics. |
| `AnnotationCollection` | Class that declares methods including Accept, Add, Clear, Contains, Count and Delete. |
| `AnnotationSelector` | Class that declares the method Visit. |
| `BleedMarkAnnotation` | BleedMarkAnnotation.Accept(visitor) implements the visitor pattern, allowing external visitor objects to process the annotation without exposing its internal structure. |
| `Border` | Border appearance can be customized by setting its Width, Style, Effect, EffectIntensity, and corner radii via the Border class methods. |
| `CaretAnnotation` | Class that inherits from MarkupAnnotation and declares the methods Accept, Frame and Symbol. |
| `Characteristics` | Class that declares the method Rotate. |
| `CircleAnnotation` | Class that inherits from CommonFigureAnnotation and declares the method Accept. |
| `ColorBarAnnotation` | Class that inherits from PrinterMarkAnnotation and declares the methods Accept and ColorOfCMYK. |
| `CommonFigureAnnotation` | Class that inherits from MarkupAnnotation and declares the methods Frame and InteriorColor. |
| `CornerPrinterMarkAnnotation` | Class that inherits from PrinterMarkAnnotation and declares the method Position. |
| `DefaultAppearance` | Class that declares the methods FontName, FontResourceName, FontSize and Text. |
| `ExplicitDestination` | Class that inherits from IAppointment and declares the methods PageNumber and ToString. |
| `FileAttachmentAnnotation` | FileAttachmentAnnotation.File() gets or sets the attached file via a FileSpecification object, allowing embedding of external resources in a PDF. |
| `FitExplicitDestination` | Class that inherits from ExplicitDestination and declares the method ToString. |
| `FreeTextAnnotation` | Class that inherits from MarkupAnnotation and declares methods including Accept, Callout, DefaultAppearance, DefaultAppearanceObject, DefaultStyle and EndingStyle. |
| `HighlightAnnotation` | Class that inherits from TextMarkupAnnotation and declares the method Accept. |
| `InkAnnotation` | InkAnnotation represents free‑hand ink strokes; its InkList property holds a StrokeList that can be read or replaced. |
| `JavascriptAction` | JavascriptAction encapsulates a JavaScript snippet attached to PDF objects; the script can be retrieved or updated via Script() getter/setter. |
| `LineAnnotation` | Class that inherits from MarkupAnnotation and declares methods including Accept, CaptionOffset, CaptionPosition, Ending, EndingStyle and Intent. |
| `LinkAnnotation` | LinkAnnotation enables clickable areas in a PDF that can trigger a PdfAction or navigate to a named destination. |
| `MarkupAnnotation` | MarkupAnnotation provides methods to set review state, opacity, title, and rich text for comment‑type annotations. |
| `MovieAnnotation` | MovieAnnotation lets you embed a video file in a PDF, with properties for title, poster flag, aspect ratio, and rotation. |
| `NamedAction` | Class that inherits from PdfAction and declares the methods Name and ToString. |
| `NamedDestination` | Class that inherits from IAppointment and declares the methods Name and ToString. |
| `PageInformationAnnotation` | Class that inherits from PrinterMarkAnnotation and declares the method Accept. |
| `PdfAction` | PdfAction.GetECMAScriptString() returns the JavaScript code attached to a PDF action, enabling inspection or modification of interactive scripts. |
| `PolyAnnotation` | Class that inherits from MarkupAnnotation and declares the methods EndingStyle, Intent, InteriorColor, StartingStyle and Vertices. |
| `PolygonAnnotation` | Class that inherits from PolyAnnotation and declares the method Accept. |
| `PolylineAnnotation` | Class that inherits from PolyAnnotation and declares the method Accept. |
| `PopupAnnotation` | Class that inherits from Annotation and declares the methods Accept, Open and Parent. |
| `PrinterMarkAnnotation` | PrinterMarkAnnotation can insert printer marks such as trim, bleed, registration, or colour bars into an entire document or a single page via AddPrinterMarks. |
| `RedactionAnnotation` | RedactionAnnotation lets you permanently remove content while optionally overlaying custom text, fill colour, border colour and font size. |
| `RegistrationMarkAnnotation` | Class that inherits from PrinterMarkAnnotation and declares the methods Accept and Position. |
| `RichMediaAnnotation` | RichMediaAnnotation enables embedding of Flash or other rich media with activation events and custom variables. |
| `ScreenAnnotation` | Class that inherits from Annotation and declares the methods Accept and Title. |
| `SoundAnnotation` | Class that inherits from MarkupAnnotation and declares the methods Accept and Icon. |
| `SquareAnnotation` | Class that inherits from CommonFigureAnnotation and declares the method Accept. |
| `SquigglyAnnotation` | Class that inherits from TextMarkupAnnotation and declares the method Accept. |
| `StampAnnotation` | Class that inherits from MarkupAnnotation and declares the methods Accept, Icon and Image. |
| `StrikeOutAnnotation` | Class that inherits from TextMarkupAnnotation and declares the method Accept. |
| `SubmitFormAction` | Class that inherits from PdfAction and declares the methods Flags, ToString and Url. |
| `TextAnnotation` | Class that inherits from MarkupAnnotation and declares the methods Accept, Icon and Open. |
| `TextMarkupAnnotation` | Class that inherits from MarkupAnnotation and declares the methods GetMarkedText and QuadPoints. |
| `TextStyle` | Class that declares the methods Alignment, FontName, FontSize and HorizontalAlignment. |
| `TrimMarkAnnotation` | TrimMarkAnnotation and UnderlineAnnotation both support the visitor pattern via an Accept method that forwards the annotation to a visitor object. |
| `UnderlineAnnotation` | Class that inherits from TextMarkupAnnotation and declares the method Accept. |
| `WatermarkAnnotation` | WatermarkAnnotation enables adding a visual watermark to a PDF page and lets developers control its transparency. |
| `WidgetAnnotation` | WidgetAnnotation provides access to AcroForm field attributes such as ReadOnly, Required, Exportable, and DefaultAppearance. |
| `XYZExplicitDestination` | XYZExplicitDestination supplies explicit page view coordinates via Left(), Top() and Zoom() methods. |

| Enumeration | Description |
|---|---|
| `AnnotationFlags` | AnnotationFlags enum includes a Locked flag that, when set, prevents further modifications to the annotation's properties. |
| `AnnotationState` | Enumerates Accepted, Cancelled, Completed, Marked, None, Rejected and Unmarked. |
| `AnnotationStateModel` | Enumerates Marked, None and Review. |
| `AnnotationType` | Enumerates values including BleedMark, Caret, Circle, ColorBar, FileAttachment, FreeText, Highlight and Ink. |
| `BorderEffect` | Enumerates Cloudy and None. |
| `BorderStyle` | Enumerates Beveled, Dashed, Inset, Solid and Underline. |
| `CapStyle` | Enumerates Butt and Rounded. |
| `CaptionPosition` | Enumerates Inline and Top. |
| `CaretSymbol` | Enumerates None and Paragraph. |
| `ColorsOfCMYK` | Enumerates Black, Cyan, Magenta and Yellow. |
| `ExplicitDestinationType` | Enumerates Fit, FitB, FitBH, FitBV, FitH, FitR, FitV and XYZ. |
| `FileIcon` | Enumerates Graph, Paperclip, PushPin and Tag. |
| `FreeTextIntent` | Enumerates FreeText, FreeTextCallout, FreeTextTypeWriter and Undefined. |
| `HighlightingMode` | Enumerates Invert, None, Outline, Push and Toggle. |
| `Justification` | Enumerates Centered, LeftJustify and RightJustify. |
| `LineEnding` | Enumerates values including Butt, Circle, ClosedArrow, Diamond, None, OpenArrow, RClosedArrow and ROpenArrow. |
| `LineIntent` | Enumerates LineArrow, LineDimension and Undefined. |
| `PolyIntent` | Enumerates PolyLineDimension, PolygonCloud, PolygonDimension and Undefined. |
| `PredefinedAction` | Enumerates values including Bookmarks_ExpanCurrentBookmark, Bookmarks_HightlightCurrentBookmark, Document_AttachFile, Document_CropPages, Document_DeletePages, Document_ExtractPages, Document_InsertPages and Document_ReplacePages. |
| `PrinterMarkCornerPosition` | Enumerates BottomLeft, BottomRight, TopLeft and TopRight. |
| `PrinterMarkSidePosition` | Enumerates Bottom, Left, Right and Top. |
| `PrinterMarksKind` | Enumerates All, BleedMarks, ColorBars, None, PageInformation, RegistrationMarks and TrimMarks. |
| `ReplyType` | ReplyType enum distinguishes between Reply, Group, and Undefined reply categories. |
| `RichTextFontStyles` | Enumerates Bold, BoldItalic, Italic and Plain. |
| `SoundIcon` | Enumerates Mic and Speaker. |
| `StampIcon` | Enumerates values including Approved, AsIs, Confidential, Departmental, Draft, Experimental, Expired and Final. |
| `TextAlignment` | Enumerates Center, Left and Right. |
| `TextIcon` | Enumerates values including Check, Circle, Comment, Cross, Help, Insert, Key and NewParagraph. |

| Class | Description |
|---|---|
| `Circle` | Class that inherits from Shape and declares the methods CheckBounds, PosX, PosY and Radius. |
| `Ellipse` | Class that inherits from Shape and declares the methods Bottom, CheckBounds, Height, Left and Width. |
| `Graph` | Class that inherits from BaseParagraph and declares methods including Border, GraphInfo, Height, IsChangePosition, Left and Shapes. |
| `Line` | Class that inherits from Shape and declares the methods CheckBounds and PositionArray. |
| `Rectangle-Aspose_Pdf_Drawing` | Class with 11 methods. |
| `Shape` | Class that declares the methods CheckBounds and GraphInfo. |

| Enumeration | Description |
|---|---|
| `Algorithm` | Enumerates AES and RC4. |
| `AutoRotateMode` | Enumerates AntiClockWise, ClockWise and None. |
| `BlendingColorSpace` | Enumerates Auto, DeviceCMYK, DeviceRGB and DontChange. |
| `DataType` | Enumerates FDF, ODBC, OLEDB, PDF, XFDF and XML. |
| `DefaultMetadataProperties` | Enumerates values including Advisory, BaseURL, CreateDate, CreatorTool, Identifier, MetadataDate, ModifyDate and Nickname. |
| `EncodingType` | Enumerates Cp1250, Cp1252, Cp1257, Identity_h, Identity_v, Macroman and Winansi. |
| `FieldType` | Enumerates values including Barcode, CheckBox, ComboBox, DateTime, Image, InvalidNameOrType, ListBox and MultiLineText. |
| `FontStyle` | Enumerates values including CjkFont, Courier, CourierBold, CourierBoldOblique, CourierOblique, Helvetica, HelveticaBold and HelveticaBoldOblique. |
| `ImageMergeMode` | Enumerates Center, Horizontal and Vertical. |
| `KeySize` | Enumerates x128, x256 and x40. |
| `PositioningMode` | Enumerates Current, Legacy and ModernLineSpacing. |
| `PropertyFlag` | Enumerates InvalidFlag, NoExport, ReadOnly and Required. |
| `StampType` | Enumerates Form and Image. |
| `SubmitFormFlag` | Enumerates Fdf, FdfWithComments, Html, Pdf, Xfdf and XfdfWithComments. |
| `WordWrapMode` | WordWrapMode enum defines two text wrapping strategies: Default and ByWords. |

| Class | Description |
|---|---|
| `BarcodeField` | Class that inherits from TextBoxField and declares the methods Caption, ECC, Resolution, Symbology, XSymHeight and XSymWidth. |
| `ButtonField` | Class that inherits from Field and declares the methods AlternateCaption, IconFit, ICPosition, NormalCaption and RolloverCaption. |
| `CheckboxField` | Class that inherits from Field and declares methods including ActiveState, AddOption, AllowedStates, Checked, Clone and ExportValue. |
| `ChoiceField` | Class that inherits from Field and declares methods including AddOption, CommitImmediately, DeleteOption, MultiSelect, Options and Selected. |
| `ComboBoxField` | Class that inherits from ChoiceField and declares the methods Editable and SpellCheck. |
| `DateField` | Class that inherits from TextBoxField and declares the methods DateFormat and Init. |
| `DocMDPSignature` | Class that declares the method AccessPermissions. |
| `ExternalSignature` | Class that inherits from Signature. |
| `Field` | Field.Recalculate() recomputes the value of a form field and returns true on success. |
| `FileSelectBoxField` | Class that inherits from TextBoxField and declares a public no-argument constructor. |
| `Form` | Form text box fields can have a barcode added programmatically by calling `AddBarcode(code)` on a `TextBoxField` instance. |
| `IconFit` | IconFit allows fine‑grained control of form field scaling; developers can set ScalingReason, ScalingMode, and leftover margins before rendering. |
| `ListBoxField` | Class that inherits from ChoiceField and declares the method TopIndex. |
| `NumberField` | Class that inherits from TextBoxField and declares the method AllowedChars. |
| `Option` | Class that declares the methods Index, Name, Selected and Value. |
| `OptionCollection` | Class that declares methods including Add, Clear, Contains, Count, Get and IsReadOnly. |
| `PKCS1` | Class that inherits from Signature and declares a public no-argument constructor. |
| `PKCS7` | Class that inherits from Signature and declares a public no-argument constructor. |
| `PKCS7Detached` | Class that inherits from Signature and declares a public no-argument constructor. |
| `PasswordBoxField` | Class that inherits from TextBoxField and declares a public no-argument constructor. |
| `RadioButtonField` | Class that inherits from ChoiceField and declares the methods Add, AddOption, NoToggleToOff, SetPosition and Style. |
| `RadioButtonOptionField` | Class that inherits from Field and declares the methods OptionName and Style. |
| `RichTextBoxField` | RichTextBoxField provides a form field that stores rich text with styling, justification, and formatted value. |
| `Signature` | Signature objects allow creation and verification of detached PKCS#7 signatures on PDF documents. |
| `SignatureCustomAppearance` | Class that declares methods including BackgroundColor, ContactInfoLabel, DateSignedAtLabel, DateTimeFormat, DateTimeLocalFormat and DigitalSignedLabel. |
| `SignatureField` | Class that inherits from Field and declares the methods Sign and Signature. |
| `TextBoxField` | Class that inherits from Field and declares methods including AddBarcode, ForceCombs, MaxLen, Multiline, Scrollable and SpellCheck. |
| `XFA` | XFA provides access to XML‑based XFA form data; calling FieldNames() yields a list of all field identifiers present in the XFA document. |

| Enumeration | Description |
|---|---|
| `BoxStyle` | Enumerates Check, Circle, Cross, Diamond, Square and Star. |
| `DocMDPAccessPermissions` | The DocMDPAccessPermissions enum defines the allowed modifications on a signed PDF: NoChanges prevents any edits, FillingInForms allows form filling, and AnnotationModification permits annotation changes. |
| `FormType` | Enumerates Dynamic, Standard and Static. |
| `IconCaptionPosition` | Enumerates CaptionAboveIcon, CaptionBelowIcon, CaptionOverlaid, CaptionToTheLeft, CaptionToTheRight, NoCaption and NoIcon. |
| `ScalingMode` | ScalingMode enum defines Proportional and Anamorphic scaling options for image transformations. |
| `ScalingReason` | ScalingReason enum indicates when scaling should be applied: Always, IconIsBigger, IconIsSmaller, or Never. |
| `SubjectNameElements` | Enumerates C, CN, E, L, O, OU and S. |
| `Symbology` | Enumerates DataMatrix, PDF417 and QRCode. |

- `Document` — `Document()` (from scratch), `Document(path)`, `Document(path, password)`
  - `Pages() -> PageCollection` (1-based indexer), `Info() -> DocumentInfo`, `Form() -> Forms::Form`, `Outlines()`, `EmbeddedFiles()`
  - `Save(path)`, `SetTitle(value)`
  - `Encrypt(user, owner, permissions, algorithm)` / `Decrypt(password)`, `IsEncrypted()`

- `Page` — `SetPageSize(width, height)`, `Paragraphs()`, `Annotations()`, `Artifacts()`, `AddImage(bytes, rect)`

- `PageCollection` — `Add()`, `Insert(index)`, `Delete(pageNumber)`, `Count()`

- `PngDevice`, `JpegDevice`, `BmpDevice`, `TiffDevice` — each `Process(page, ostream)`; `TiffDevice` also accepts `TiffSettings` for palettised output

- `Resolution` — horizontal/vertical DPI

- `DocumentDevice`/`PageDevice` — base rendering surfaces

- `Table` — `Rows()`, `ColumnWidths(value)`, `Border(value)`, `DefaultCellBorder(value)`
- `Row`/`Cell` — `Cells().Add(text)`, `Cell::ColSpan`, `BackgroundColor`, `BackgroundImage`
- `Drawing::Graph(width, height)` — `Shapes()` holding `Line`, `Rectangle`, `Circle`, `Ellipse`
- `WatermarkArtifact` — configured via the inherited `Artifact` surface (`SetTextAndState`, `SetImage`, `Position`, `Rotation`, `Opacity`, `IsBackground`)

- `Forms::Form` — `Document::Form()`, `Add(field, pageNumber)`, `Delete(field)`, `Flatten()`
- `Forms::Field` subtypes — `TextBoxField`, `CheckboxField`, `RadioButtonField`, `ComboBoxField`, `ListBoxField`, `ButtonField`, `DateField`, `NumberField`, `PasswordBoxField`, `FileSelectBoxField`, `RichTextBoxField`, `BarcodeField`

- `OutlineCollection`/`OutlineItemCollection` — `Title`, `Bold`, `Destination`, `Add`

- `NamedDestinationCollection`, `ExplicitDestination` subtypes (`XYZExplicitDestination`, `FitExplicitDestination`, and more)

- `DocumentInfo` — `Title`/`Author`/`Creator`/`Producer`/`Subject`/`Keywords`, `Add`/`Remove`/`ClearCustomData`

- `Metadata`/`XmpValue` — dictionary-style XMP property access

- `CryptoAlgorithm` — `RC4x40`, `RC4x128`, `AESx128`, `AESx256`
- `Permissions` — `[Flags]` enum per ISO 32000-1 §7.6.3.2 Table 22
- `Facades::PdfFileSignature` — detached PKCS#7 signing with a byte-exact `/ByteRange`
- `Facades::PdfFileSecurity` — encrypt/decrypt/change passwords

- `Facades::Facade` — base type; `BindPdf` overloads accept a file path or an existing `Document`
- `Facades::PdfConverter` — rasterise a PDF to multi-page TIFF or per-page PNG
- `Facades::PdfExtractor` — `StartPage`/`EndPage`-scoped text extraction
- `Facades::PdfBookmarkEditor` — `CreateBookmarkOfPage(title, pageNumber)`
- `Facades::PdfFileEditor` — `Concatenate(files, out)`, `SplitFromFirst`/`SplitToEnd`/`SplitToPages`/`SplitToBulks`, plus `Try*` non-throwing variants
- `Facades::PdfFileStamp` — `AddHeader(text, margin)`, `AddFooter(text, margin)`, `AddPageNumber(...)`, drawn as real text into each page

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/pdf/cpp/)** — installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/pdf/cpp/)** — task-focused answers for common PDF-processing questions.
- **[Full API reference](https://reference.aspose.org/pdf/cpp/)** — the complete, browsable reference for all 249 public types (the [API Reference](#api-reference) section above covers the essentials).
- **[Changelog](CHANGELOG.md)** — what changed in each release.
- **[Contributing guide](CONTRIBUTING.md)** — how to propose changes and the project's coding conventions.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp/issues).

## Scope and Limitations

> The incremental-update writer patches an existing `/Info` object; a from-scratch document has
> no `/Info` to patch, so setting metadata on one and saving throws.

`CryptoAlgorithm` covers `RC4x40`, `RC4x128`, `AESx128`, and `AESx256`. `Permissions` is a `[Flags]` enum (ISO 32000-1 §7.6.3.2 Table 22) — compose with `|`. Permissions are enforced by viewers; the library itself is not a DRM mechanism.

- A handful of `XmpValue` type-checking helpers — `IsDateTime`, `IsField`, `IsNamedValue`, `IsRaw`, `IsNamedValues`, and `IsStructure` — are stubs that always return `false`; use `IsString`/`IsInteger`/`IsDouble`/`IsArray` instead.
- Standard-14 font fallback covers 12 of the 14 standard fonts (Helvetica, Times-Roman, and Courier, four styles each) via bundled Liberation substitutes; Symbol and ZapfDingbats have no bundled fallback.
- The incremental-update metadata writer patches an existing `/Info` object; a from-scratch document has no `/Info` to patch, so setting metadata on one and saving throws.
- `Permissions` set via encryption are enforced by the consuming PDF viewer, not by this library — the encryption bitfield is written into the file, but the library itself is not a DRM mechanism.

See [Aspose.PDF for Cpp — Enterprise Edition](https://products.aspose.com/pdf/cpp/). It adds full support for every Facades method (including `PdfFileEditor` and `PdfFileStamp`), complete XMP type-checking, and broader format coverage beyond this FOSS edition's v1 scope.

## Development and Testing

The suite covers 176 test files under `tests/`. The [ci workflow](.github/workflows/ci.yml) runs on Ubuntu and Windows. Releases run through the [release workflow](.github/workflows/release.yml).

This library builds as a static library you link into your project. Either way, include the whole public API through the single-entry header, or include individual headers from `aspose/pdf/`.

Install the [`Aspose.PDF.Cpp.FOSS`](https://www.nuget.org/packages/Aspose.PDF.Cpp.FOSS) package into a C++ project (`Install-Package Aspose.PDF.Cpp.FOSS`). It ships static libraries for x64, x86, and ARM64 in Release and Debug. It adds the include path, links the matching library, and raises the project to C++20.

```cmake
add_subdirectory(aspose.pdf-foss-for-cpp)
target_link_libraries(your_app PRIVATE aspose_pdf_foss::aspose_pdf_foss)
```

Both forms of the target make your code compile as C++20.

- A C++20 compiler (clang 16+, gcc 13+, or MSVC 2022 17.5+)
- Python 3, build-time only — a generator step embeds the bundled font outlines into a generated source file

**Runtime dependencies: none.** The test suite alone fetches [GoogleTest](https://github.com/google/googletest) v1.14.0 via CMake `FetchContent` at configure time; it is not needed to build or consume the library itself.

The static library lands at `build/libaspose_pdf_foss.a` (or `aspose_pdf_foss.lib` on MSVC), built out-of-source under `build/`. For a release build, pass `-DCMAKE_BUILD_TYPE=Release` to the configure step. `CMakePresets.json` also carries host-conditional Windows-MSVC presets — e.g. `cmake --preset windows-msvc-debug`.

- `Python3` — required by the CMake configure step (`find_package(Python3 REQUIRED COMPONENTS Interpreter)` in `CMakeLists.txt`) to run a generator script that embeds the bundled Standard-14 font outlines into a generated source file; needed only to configure/build the library, not by the compiled library at runtime.

- `googletest` (1.14.0) — fetched via CMake FetchContent in `CMakeLists.txt`; builds the `aspose_pdf_foss_tests` ctest binary only, never linked into the shipped `aspose_pdf_foss` library.

Field types: `TextBoxField`, `CheckboxField`, `RadioButtonField`, `ComboBoxField`, `ListBoxField`, `ButtonField`.

Public-facing headers and their implementations sit under `include/aspose/pdf/` and `src/public/`; internal foundation primitives (codecs, the rasteriser, crypto) live separately under `include/internal/` and `src/internal/`:

```
├── include/
│   ├── aspose/pdf/            # Public-API headers (consumer-facing)
│   └── internal/              # Foundation primitive headers
├── src/
│   ├── public/                # Public-API implementation
│   └── internal/              # Foundation primitives (codecs, renderer, crypto)
├── tests/                     # GoogleTest unit + smoke tests
├── examples/                  # 12 runnable demo programs
├── pdfs/                      # Tiny sample PDFs for the examples
└── CMakeLists.txt
```

- `Text::TextAbsorber` — `Visit(Document)` / `Visit(Page)`, `Text() -> string`
- `Text::TextFragmentAbsorber` — `TextFragments() -> TextFragmentCollection`
- `Text::TextBuilder(page)` — `AppendText(fragment)`, `AppendParagraph(paragraph)`
- `Text::TextFragment`, `Text::TextParagraph`, `Text::TextState` (font, size, colours, decorations)
- `FontRepository::FindFont(name)`

```bash
cmake --build build
cd build && ctest
```

A GoogleTest suite covers both the public-API surface and the foundation primitives; GoogleTest is fetched at configure time and is the only test-time dependency. Public-API bodies under `src/public/` call directly into foundation primitives under `src/internal/`; foundation primitives never reach back into the public API.

The compiled library links against nothing but the C++ standard library, and all codecs (TIFF,
JPEG, PNG, and more) are implemented from scratch within the library. It bundles the Liberation
font family (SIL Open Font License 1.1) to provide metrically-compatible substitutes for the
Standard-14 PDF fonts — see
[`src/internal/standard14_outlines.fonts/OFL.txt`](src/internal/standard14_outlines.fonts/OFL.txt).
GoogleTest (BSD 3-Clause) is fetched via CMake `FetchContent` for the test suite only and is not
part of the shipped library. Full detail: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

It bundles metric-compatible Liberation fonts (Sans / Serif / Mono), compiled into the static
library to render the PDF Standard-14 fonts when no embedded or system font is available. These
are licensed under the SIL Open Font License 1.1, which permits bundling with software under any
license — see [`src/internal/standard14_outlines.fonts/OFL.txt`](src/internal/standard14_outlines.fonts/OFL.txt).
The MIT license above covers the library's own code (SPDX: `MIT AND OFL-1.1` for the distribution
as a whole).

## Third-Party Notices

See [Third-party notices](THIRD_PARTY_NOTICES.md).

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
