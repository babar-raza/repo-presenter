# Aspose.Cells FOSS for TypeScript

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](License/LICENSE.txt) [![Contributors](https://img.shields.io/github/contributors/aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript.svg)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript/graphs/contributors)

[![Aspose.Cells FOSS for TypeScript](https://products.aspose.org/media/cells/typescript/banner-readme.png)](https://products.aspose.org/cells/typescript/)

Aspose.Cells FOSS for TypeScript reads and writes Excel files using the .xlsx format. It converts workbooks to `.html` and `.htm` files for output, and loads `.html` and `.htm` files as input. It provides methods to create, modify, and save workbooks, including setting cell values and formulas, applying styles, and managing worksheet elements such as comments, hyperlinks, data validation, and conditional formatting.

Aspose.Cells FOSS for TypeScript is a free, open-source TypeScript library for creating,
loading, editing, and saving Excel `.xlsx` (Office Open XML / SpreadsheetML) workbooks
without requiring Microsoft Excel. It exposes an Aspose.Cells-compatible API surface —
`Workbook`, `Worksheet`, `Cell`, `Style` — and additionally reads and writes HTML, and
exports to CSV, JSON, and Markdown for reporting and data-interchange scenarios.

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
  subgraph StartingPoints["Starting Points"]
    direction TB
    i1["An existing HTM or<br/>HTML file"]
  end
  PRODUCT["Aspose.Cells FOSS for TypeScript"]
  subgraph Capabilities["Core Capabilities"]
    direction TB
    c1["Load and save Excel<br/>workbooks"]
    c2["Read and write cell<br/>data"]
    c3["Apply cell and<br/>worksheet formatting"]
    c4["Configure worksheet<br/>features"]
    c5["Add hyperlinks,<br/>comments, and data<br/>validation"]
    c6["Apply conditional<br/>formatting rules"]
    c7["Export to text formats"]
    c8["Import and export HTML"]
    c1 ~~~ c4
    c2 ~~~ c5
    c3 ~~~ c6
    c4 ~~~ c7
    c5 ~~~ c8
    c6 ~~~ c8
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["HTM or HTML file"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
  classDef product fill:#1f6feb,stroke:#1f6feb,color:#ffffff
  class PRODUCT product
```

## Key Capabilities

- **Load and save Excel workbooks.** It loads Excel workbooks from a file path using `Workbook.load` and saves them with `Workbook.save`, and it constructs new workbooks with `Workbook.constructor`.
- **Read and write cell data.** It reads and writes cell values and formulas using `Cell.putValue` and `Cell.setFormula`, and retrieves cells by reference or coordinate with `Worksheet.getCell2`, exposing their value and formula properties.
- **Apply cell and worksheet formatting.** It applies formatting to cells using `Style`, `Font`, `Fill`, `Border`, `Alignment`, and `Protection` objects, assigning them via `Cell.setStyle`.
- **Configure worksheet features.** It configures worksheet layout and behavior by setting column widths and row heights, merging cells, hiding rows, and enabling auto filters through `Worksheet` methods.
- **Add hyperlinks, comments, and data validation.** It adds hyperlinks, comments, and data validation to worksheets using `Worksheet.addHyperlink`, `Worksheet.addComment`, and `Worksheet.addDataValidation`, referencing `Hyperlink` and `Comment` objects.
- **Apply conditional formatting rules.** It applies conditional formatting rules to cell ranges using `Worksheet.addConditionalFormat` with `ColorScaleRule`, `DataBarRule`, and `IconSetRule` objects.
- **Export to text formats.** It exports workbook data as text using `Workbook.toCsv`, `Workbook.toJson`, and `Workbook.toMarkdown`, each returning a string representation of the data.
- **Import and export HTML.** It imports HTML files with `Workbook.load` and exports workbooks to HTML using `Workbook.toHtml`, supporting the `.html` format for both input and output.

- Read and write cell values, formulas, and shared strings via `Cell.putValue()`/
  `Cell.setFormula()`, with `Worksheet.getCell2()`/`getCell()` lookups by reference or
  coordinate.
- Access embedded pictures and shapes through `Workbook.images` (`ImageInfo[]`) and
  `Worksheet.shapes` (`ShapeInfo[]`).

## Installation

`excel-cells` is not yet published on npm; build it from a source checkout instead:

```bash
git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript.git
cd Aspose.Cells-FOSS-for-TypeScript
npm install
```

## Dependencies

### Required Package Dependencies

- `adm-zip ^0.5.16`
- `@xmldom/xmldom ^0.8.10`
- `@zip.js/zip.js ^2.8.21`

### Development Dependencies

- `ts-node ^10.9.2`
- `tsx ^4.21.0`
- `@types/node ^25.3.3`
- `typescript ^5.9.3`

## Quick Start

Create a new Excel file with product data and formatted headers, then save it as `products.xlsx`.

```typescript
import { Workbook, Style } from "./aspose_cells";

const workbook = new Workbook();
const sheet = workbook.worksheets.get(0)!;

sheet.name = "Products";
sheet.putValue("A1", "Product");
sheet.putValue("B1", "Price");
sheet.putValue("A2", "Apple");
sheet.putValue("B2", 2.99);
sheet.putValue("A3", "Orange");
sheet.putValue("B3", 1.99);
const cellB4 = sheet.getCell2("B4");
cellB4.setFormula("=SUM(B2:B3)");

const headerStyle = new Style();
headerStyle.setBold(true);
headerStyle.setFontColor("FFFFFFFF");
headerStyle.setForegroundColor("FF2278D4");

sheet.getCell2("A1").setStyle(headerStyle);
sheet.getCell2("B1").setStyle(headerStyle);

await workbook.save("products.xlsx");
```

Load an existing Excel file, update a cell value, and save the changes to `updated.xlsx`.

```typescript
import { Workbook } from "./aspose_cells";

const workbook = await Workbook.load("input.xlsx");
const sheet = workbook.worksheets.get(0)!;

sheet.getCell2("A1").putValue("Updated");

await workbook.save("updated.xlsx");
```

## Additional Examples

Aspose.Cells FOSS for TypeScript supports loading Excel workbooks and saving them as HTML. The following examples demonstrate common workflows.

### Load an Excel File and Save It as HTML

```typescript
import { Workbook } from "./aspose_cells";

const workbook = await Workbook.load("input.xlsx");
await workbook.save("output.html", { saveFormat: undefined });
```

## API Reference

Aspose.Cells FOSS for TypeScript provides the `Workbook` class as the main entry point for working with Excel files, and the `Worksheet`, `Cell`, and `Style` classes for manipulating individual sheets, cells, and formatting. It supports loading and saving Excel files and converting them to other formats.

The public API has 31 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `Alignment` | Alignment represents the alignment settings for cell content. |
| `AutoFilter` | AutoFilter provides filtering capabilities for a range of cells in a worksheet. |
| `Border` | Border defines the border properties for a cell or range of cells. |
| `BorderLine` | BorderLine specifies the style and color of a border line. |
| `Cell` | Cell represents a single cell in a worksheet. |
| `CellCoordinates` | CellCoordinates holds the row and column indices of a cell. |
| `CellRange` | CellRange defines a rectangular range of cells in a worksheet. |
| `CellValue` | CellValue represents the data stored in a cell. |
| `Cells` | Cells is a collection of Cell objects in a worksheet. |
| `ColorScaleRule` | ColorScaleRule applies a color scale conditional formatting to a range of cells. |
| `Comment` | Comment represents a comment attached to a cell. |
| `CommentCollection` | CommentCollection is a collection of Comment objects in a worksheet. |
| `ConditionalFormat` | ConditionalFormat applies conditional formatting rules to a range of cells. |
| `ConditionalFormatCollection` | ConditionalFormatCollection is a collection of ConditionalFormat objects in a worksheet. |
| `ConditionalFormatRule` | ConditionalFormatRule defines a rule for conditional formatting. |
| `DataBarRule` | DataBarRule applies a data bar conditional formatting to a range of cells. |
| `DataValidation` | DataValidation enforces data entry restrictions on a range of cells. |
| `DataValidationCollection` | DataValidationCollection is a collection of DataValidation objects in a worksheet. |
| `Fill` | Fill defines the fill properties for a cell or range of cells. |
| `FilterColumn` | FilterColumn represents a filtered column in an AutoFilter range. |
| `Font` | Font specifies the font properties for text in a cell. |
| `Hyperlink` | Hyperlink represents a hyperlink attached to a cell. |
| `HyperlinkCollection` | HyperlinkCollection is a collection of Hyperlink objects in a worksheet. |
| `IconSetRule` | IconSetRule applies an icon set conditional formatting to a range of cells. |
| `Protection` | Protection specifies the protection settings for a cell. |
| `Style` | Style defines the formatting style for a cell or range of cells. |
| `Workbook` | Workbook represents an Excel workbook. |
| `Worksheet` | Worksheet represents a worksheet in a workbook. |
| `WorksheetCollection` | WorksheetCollection is a collection of Worksheet objects in a workbook. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `EncryptionType` | EncryptionType specifies the encryption algorithm used for a workbook. |
| `SaveFormat` | SaveFormat specifies the format used when saving a workbook. |

#### Detailed Member Reference

### Workbook

The `Workbook` class can be created using its constructor, loaded from a file using `Workbook.load`, and saved using `Workbook.save`. It exposes a worksheets collection for accessing individual worksheets, and provides methods to export the workbook to HTML, CSV, JSON, and Markdown formats.

### Worksheet

The `Worksheet` class provides methods to access and modify cell content and formatting, including `Worksheet.getCell2` to retrieve a cell, `Worksheet.putValue` to set a cell value, and `Worksheet.setCellStyle` to apply a style. It also supports adding hyperlinks, comments, data validation rules, conditional formats, and setting an auto filter.

### Cell

The `Cell` class allows reading and writing cell values, formulas, hyperlinks, and shared string map references. It supports setting cell style using `Cell.setStyle` and retrieving the underlying value, formula, hyperlink, and shared string map via their respective properties.

### Style

The `Style` class provides methods to configure font, fill, border, and alignment properties. It supports setting bold, font color, and foreground color, and exposes getters for alignment, border, fill, and font settings.

| Class | Description |
|---|---|
| `AllConnectorShapeInfo` | Class in the Cells TYPESCRIPT API. |
| `AllShapeInfo` | Class in the Cells TYPESCRIPT API. |
| `AutoFilter` | Class that declares the methods addFilterColumn, clear, removeFilterColumn and toXml and the members columns and range. |
| `BasicShapeInfoType` | Class with 1 property. |
| `BasicShapeSubType` | Class in the Cells TYPESCRIPT API. |
| `BentConnectorShapeType` | Class in the Cells TYPESCRIPT API. |
| `BraceShapeType` | Class in the Cells TYPESCRIPT API. |
| `Cell` | A single cell — value, formula, style, and hyperlink. |
| `CellValue` | Class in the Cells TYPESCRIPT API. |
| `CellValue-util` | Class in the Cells TYPESCRIPT API. |
| `Cells` | Per-sheet collection for reading and writing cell values, formulas, and styles. |
| `Chart` | Class with 7 methods and 33 properties. |
| `ChartCollection` | Class with 11 methods and 2 properties. |
| `ChartLoader` | Class with 1 method and 7 properties. |
| `ChartRenderer` | Class with 1 method. |
| `ChartType` | Class in the Cells TYPESCRIPT API. |
| `CircleVariantShapeType` | Class in the Cells TYPESCRIPT API. |
| `Comment` | Class that declares the method toXml and members including author, col, height, ref, row and text. |
| `CommentCollection` | Class that declares the methods add, clear, get, getByCell, remove and toXml and the member count. |
| `ConditionalFormat` | Class that declares the methods addArea, addRule, getRanges, getRules and toXml. |
| `ConditionalFormatCollection` | Class that declares the methods add, clear, get, remove and toXml and the member count. |
| `CurvedConnectorShapeType` | Class in the Cells TYPESCRIPT API. |
| `DOMParser` | Class with 2 methods. |
| `DataRelationship` | Class with 3 methods and 1 property. |
| `DataValidation-validation` | Class with 3 methods and 12 properties. |
| `DataValidationCollection` | Class that declares the methods add, clear, get, remove and toXml and the member count. |
| `EllipseShapeType` | Class in the Cells TYPESCRIPT API. |
| `ExpDrawing` | Class with 9 methods. |
| `HtmlDocument` | Loads and represents an HTML document for conversion into a `Workbook`. |
| `HtmlExporter` | Renders a `Workbook` to a styled HTML document. |
| `HtmlReader` | Reads and parses raw HTML markup into a `HtmlDocument`. |
| `HtmlTable` | Class with 10 methods and 14 properties. |
| `HtmlWriter` | Serializes a `HtmlDocument` back to HTML markup. |
| `Hyperlink` | Class that declares the method toXml and members including address, col, display, ref, row and target. |
| `HyperlinkCollection` | Class that declares the methods add, clear, get, getByCell, remove and toXml and the member count. |
| `ImpDrawing` | Class with 1 method and 5 properties. |
| `LineShapeType` | Class in the Cells TYPESCRIPT API. |
| `MathSymbolShapeType` | Class in the Cells TYPESCRIPT API. |
| `PolygonShapeType` | Class in the Cells TYPESCRIPT API. |
| `QuadrilateralShapeType` | Class in the Cells TYPESCRIPT API. |
| `RectangleShapeType` | Class in the Cells TYPESCRIPT API. |
| `RectangleVariantShapeType` | Class in the Cells TYPESCRIPT API. |
| `SealShapeType` | Class in the Cells TYPESCRIPT API. |
| `Shape3DType` | Class in the Cells TYPESCRIPT API. |
| `SpecialShapeType` | Class in the Cells TYPESCRIPT API. |
| `StarShapeType` | Class in the Cells TYPESCRIPT API. |
| `StraightConnectorShapeType` | Class in the Cells TYPESCRIPT API. |
| `Style` | Font, fill, border, alignment, and number-format settings for a cell. |
| `TriangleShapeType` | Class in the Cells TYPESCRIPT API. |
| `Workbook` | The top-level container — `load()`/`save()`, `worksheets`, `images`, and `toHtml()`/`toCsv()`/`toJson()`/`toMarkdown()`. |
| `Worksheet` | A single sheet — cell access via `Cells`, styling, images/shapes, and layout settings. |
| `WorksheetCollection` | Iterable, array-like collection of `Worksheet` objects. |
| `Alignment` | Interface that declares the members horizontal, vertical and wrapText. |
| `ArrowShapeInfo` | Interface with 1 property. |
| `AxisInfo` | Interface with 8 properties. |
| `BentConnectorShapeInfo` | Interface with 3 properties. |
| `Border` | Interface that declares the members bottom, left, right and top. |
| `BorderLine` | Interface that declares the members color and style. |
| `BraceShapeInfo` | Interface with 1 property. |
| `CellCoordinates` | Interface that declares the members col and row. |
| `CellCoordinates-util` | Interface with 2 properties. |
| `CellRange` | Interface that declares the members endCol, endRow, startCol and startRow. |
| `CellRange-util` | Interface with 4 properties. |
| `CellStyle` | Interface with 23 properties. |
| `ChartArea` | Interface with 4 properties. |
| `ChartInfo` | Interface with 21 properties. |
| `ChartSeries` | Interface with 3 properties. |
| `CircleVariantShapeInfo` | Interface with 1 property. |
| `ColorScaleRule` | Interface that declares the members maxColor, midColor and minColor. |
| `Comment-types` | Interface with 4 properties. |
| `ConditionalFormatRule` | Interface that declares members including colorScale, dataBar, formula1, formula2, iconSet and operator. |
| `CurvedConnectorShapeInfo` | Interface with 3 properties. |
| `DataBarRule` | Interface that declares the members color, direction, maxValue and minValue. |
| `DataValidation` | Interface that declares the methods addArea, getRanges and toXml and members including allowBlank, errorMessage, errorStyle, errorTitle, formula1 and formula2. |
| `EllipseShapeInfo` | Interface with 1 property. |
| `Fill` | Interface that declares the members bgColor, fgColor and patternType. |
| `FilterColumn` | Interface that declares the method filters and the members blank and col. |
| `Font` | Interface that declares members including bold, color, italic, name, size and strikeout. |
| `HtmlParseOptions` | Interface with 2 properties. |
| `HtmlSaveOptions` | Interface with 2 properties. |
| `Hyperlink-types` | Interface with 5 properties. |
| `IconSetRule` | Interface that declares the members iconSet and reverse. |
| `ImageInfo` | Interface with 5 properties. |
| `LegendInfo` | Interface with 2 properties. |
| `LineShapeInfo` | Interface with 3 properties. |
| `MathSymbolShapeInfo` | Interface with 1 property. |
| `PictureInfo` | Interface with 9 properties. |
| `PictureShapeInfo` | Interface with 2 properties. |
| `PlotArea` | Interface with 4 properties. |
| `PolygonShapeInfo` | Interface with 1 property. |
| `Protection` | Interface that declares the members hidden and locked. |
| `QuadrilateralShapeInfo` | Interface with 1 property. |
| `RectangleShapeInfo` | Interface with 1 property. |
| `RectangleVariantShapeInfo` | Interface with 1 property. |
| `SealShapeInfo` | Interface with 1 property. |
| `SeriesInfo` | Interface with 3 properties. |
| `Shape3DInfo` | Interface with 1 property. |
| `ShapeAnchor` | Interface with 10 properties. |
| `ShapeFill` | Interface with 10 properties. |
| `ShapeInfo` | Interface with 26 properties. |
| `SpecialShapeInfo` | Interface with 1 property. |
| `StarShapeInfo` | Interface with 1 property. |
| `StraightConnectorShapeInfo` | Interface with 3 properties. |
| `Style-types` | Interface with 6 properties. |
| `TriangleShapeInfo` | Interface with 1 property. |
| `EncryptionType` | Enum with 1 member. |
| `SaveFormat` | Enum with 5 members. |

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/cells/typescript/)** — installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/cells/typescript/)** — task-focused answers for common spreadsheet-processing questions.
- **[Full API reference](https://reference.aspose.org/cells/typescript/)** — the complete, browsable reference for every public class. It covers all 31 public types; the [API Reference](#api-reference) section above covers the essentials.
- **[examples/](examples/)** — The `examples/` directory in this repository.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript/issues).

## Scope and Limitations

The library ships a real class surface centered on `Workbook`, `Worksheet`, `Cell`, and `Style` — `Workbook.worksheets` is a `WorksheetCollection` of `Worksheet` objects, each exposing a `Cells` collection for reading and writing values, formulas, and styles.

- Text export is available as a returned string, not as a direct file-write helper — pass the result of `toCsv()`, `toJson()`, or `toMarkdown()` to your own file-writing code.
- Text export is one-way — there is no corresponding import path back into a `Workbook`.

See [Aspose.Cells — Enterprise Edition](https://products.aspose.com/cells/). It adds a full commercial spreadsheet engine, broader format coverage, and active support beyond this FOSS TypeScript edition's own scope.

## Development and Testing

A npm package has not been published yet. Install from source.

- `@zip.js/zip.js` ^2.8.21 — reads and writes the XLSX ZIP container.
- `@xmldom/xmldom` ^0.8.10 — parses and serializes the OOXML part XML.
- `adm-zip` ^0.5.16 — used alongside `@zip.js/zip.js` for ZIP entry handling.

- Requires Node.js 18 or later and TypeScript 5 or later.

- `@types/node` ^25.3.3, `typescript` ^5.9.3 — TypeScript compilation and type checking.
- `ts-node` ^10.9.2, `tsx` ^4.21.0 — running TypeScript examples/tests directly.

Build and type-check from the repository root:

```bash
npm install
npx tsc --noEmit
```

See [AGENTS.md](agents.md) for contributor guidance.

## License

This project is licensed under the [MIT License](License/LICENSE.txt). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
