# Aspose.Cells FOSS for Cpp

[![NuGet version](https://img.shields.io/nuget/v/Aspose.Cells.Cpp.FOSS.svg)](https://www.nuget.org/packages/Aspose.Cells.Cpp.FOSS/) ![C++](https://img.shields.io/badge/c%2B%2B-17-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](License/LICENSE.txt) [![Contributors](https://img.shields.io/github/contributors/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp.svg)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/graphs/contributors) [![Issues](https://img.shields.io/github/issues/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp.svg)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/issues)

[![Aspose.Cells FOSS for Cpp](https://products.aspose.org/media/cells/cpp/banner-readme.png)](https://products.aspose.org/cells/cpp/)

Aspose.Cells FOSS for Cpp reads and writes Excel `.xlsx` workbooks. It provides classes such as `Workbook`, `Worksheet`, and `Cell` to create, modify, and save spreadsheets programmatically. It supports styling with `Style`, `Font`, `Color`, `FillPattern`, and `Borders`.

Aspose.Cells FOSS for Cpp is a free, open-source, MIT-licensed C++ library for creating, loading,
editing, and saving Excel `.xlsx` workbooks without requiring Microsoft Excel. It exposes an
Aspose.Cells-compatible API surface for common XLSX scenarios — the same `Workbook`, `Worksheet`,
and `Cell` object shape used by Aspose's commercial spreadsheet products — built as a
dependency-free, header-and-source C++17 library with no external runtime dependencies.

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
  PRODUCT["Aspose.Cells FOSS for Cpp"]
  subgraph Capabilities["Core Capabilities"]
    direction TB
    c1["Create and save .xlsx<br/>workbooks"]
    c2["Read and write cell<br/>values and formulas"]
    c3["Apply cell styles and<br/>formatting"]
    c4["Manage worksheet<br/>structure and<br/>protection"]
    c5["Apply conditional<br/>formatting and data<br/>validation"]
    c6["Configure page setup<br/>and print options"]
    c7["Manage hyperlinks and<br/>defined names"]
    c8["Access document<br/>properties"]
    c1 ~~~ c4
    c2 ~~~ c5
    c3 ~~~ c6
    c4 ~~~ c7
    c5 ~~~ c8
    c6 ~~~ c8
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["XLSX file"]
  end
  PRODUCT --> Capabilities --> Outputs
  classDef product fill:#1f6feb,stroke:#1f6feb,color:#ffffff
  class PRODUCT product
```

## Key Capabilities

- **Create and save .xlsx workbooks.** It constructs blank workbooks or loads existing `.xlsx` files from paths or in-memory streams, then saves them back to `.xlsx` using `Workbook.Save`, and `WorkbookSaveException` is raised when saving fails.
- **Read and write cell values and formulas.** It writes values of strings, integers, doubles, booleans, and `DateTime` to cells via `Cell.PutValue`, retrieves values as variant-typed `CellValue` with typed accessors, and stores or reads formulas via `Cell.SetFormula` and `Cell.GetFormula`.
- **Apply cell styles and formatting.** It applies cell styles by retrieving and setting `Style` objects that bundle `Font`, `FillPattern`, `Color`, `Borders`, alignment, and text wrap, and `Style` provides clone and getter methods for each formatting component.
- **Manage worksheet structure and protection.** It controls worksheet visibility with `VisibilityType`, manages gridlines and headers, and protects worksheets using `WorksheetProtection`, all exposed directly on `Worksheet`.
- **Apply conditional formatting and data validation.** It applies conditional formatting through `ConditionalFormattingCollection` and `FormatCondition`, and manages data validation via `ValidationCollection` and `Validation`, both scoped to `CellArea` ranges.
- **Configure page setup and print options.** It configures page setup with `PageSetup` for paper size, orientation, margins, scaling, print area, headers, footers, and page breaks, using `PageOrientationType` and `PaperSizeType` enumerations.
- **Manage hyperlinks and defined names.** It attaches hyperlinks to cell ranges via `HyperlinkCollection` and `Hyperlink`, supporting external, internal, and mailto links, and manages workbook- or sheet-scoped named ranges through `DefinedNameCollection` and `DefinedName`.
- **Access document properties.** It exposes core and extended document metadata through `WorkbookProperties`, `DocumentProperties`, and `ExtendedDocumentProperties`, accessible via `Workbook.GetProperties` and `Workbook.GetDocumentProperties`.

- **Read and write cell values and formulas**: `Cell.PutValue()` accepts strings, integers,
  doubles, bools, and `DateTime`; `Cell.GetValue()` returns a variant-typed `CellValue`, and
  `Cell.SetFormula()`/`Cell.GetFormula()` handle Excel formula text with or without a leading `=`.
- **Apply cell styles**: `Cell.GetStyle()`/`Cell.SetStyle()` return and apply a `Style`, which
  bundles `Font` (bold, color), fill (`FillPattern`, foreground/background `Color`), `Borders`,
  alignment, and text wrap into one cloneable value.
- **Merge cell ranges and apply number formats**: `Cells.Merge()` creates merged regions tracked
  as `MergeRegion`s, and `Style.SetNumberFormat()`/`NumberFormat` apply and parse Excel
  display-format patterns, rendered through `DisplayTextFormatter` with locale-directive support.
- **Apply conditional formatting and data validation**: `Worksheet.GetConditionalFormattings()`
  manages rule-driven cell formatting through `FormatCondition`, and
  `Worksheet.GetValidations()` manages input constraints through `Validation`, both scoped to
  one or more `CellArea` ranges.
- **Manage hyperlinks and defined names**: `Worksheet.GetHyperlinks()` attaches external, internal,
  or `mailto:` links to a cell range via `Hyperlink`, and `Workbook.GetDefinedNames()` manages
  workbook- or sheet-scoped named ranges through `DefinedNameCollection`, each of which can carry
  its own descriptive comment string.
- **Configure page setup and print settings**: `Worksheet.GetPageSetup()` returns a `PageSetup` for
  paper size, orientation, margins, scaling, print area/titles, headers/footers, and page breaks.

## Installation

The library is published on NuGet as `Aspose.Cells.Cpp.FOSS`.

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `Aspose.Cells.Foss.Cpp/CMakeLists.txt`, no dependency is on the library target's public link interface, so a consumer links nothing beyond the library itself.

### Native and System Requirements

- Requires C++ `17` (`CMAKE_CXX_STANDARD` in `Aspose.Cells.Foss.Cpp/CMakeLists.txt`).
- Requires CMake 3.16 or later (`cmake_minimum_required` in `Aspose.Cells.Foss.Cpp/CMakeLists.txt`).

## Quick Start

This example creates a new workbook, adds a worksheet named Products, populates it with product names and prices, computes a SUM formula, applies a styled header, and saves the result as `products.xlsx`.

```cpp
#include "aspose/cells_foss/Workbook.h"
#include "aspose/cells_foss/WorksheetCollection.h"
#include "aspose/cells_foss/Worksheet.h"
#include "aspose/cells_foss/Cell.h"
#include "aspose/cells_foss/Style.h"
#include "aspose/cells_foss/Color.h"
#include "aspose/cells_foss/Font.h"

using namespace Aspose::Cells_FOSS;

int main() {
    Workbook workbook;
    Worksheet& sheet = workbook.GetWorksheets()[0];

    sheet.SetName("Products");
    sheet.GetCells()["A1"].PutValue("Product");
    sheet.GetCells()["B1"].PutValue("Price");
    sheet.GetCells()["A2"].PutValue("Apple");
    sheet.GetCells()["B2"].PutValue(2.99);
    sheet.GetCells()["A3"].PutValue("Orange");
    sheet.GetCells()["B3"].PutValue(1.99);
    sheet.GetCells()["B4"].SetFormula("=SUM(B2:B3)");

    Style headerStyle = sheet.GetCells()["A1"].GetStyle();
    Font font;
    font.SetBold(true);
    font.SetColor(Color::FromArgb(255, 255, 255, 255));
    headerStyle.SetFont(font);
    headerStyle.SetPattern(FillPattern::Solid);
    headerStyle.SetForegroundColor(Color::FromArgb(255, 34, 120, 212));
    sheet.GetCells()["A1"].SetStyle(headerStyle);
    sheet.GetCells()["B1"].SetStyle(headerStyle);

    workbook.Save("products.xlsx");
    return 0;
}
```

## Additional Examples

```cpp
auto& formattings = sheet.GetConditionalFormattings();
auto collection = formattings[formattings.Add()];
collection.AddArea(CellArea::CreateCellArea("A1", "A3"));

auto condition = collection[collection.AddCondition(
    FormatConditionType::CellValue, OperatorType::Between, "=1", "=9")];
condition.SetPriority(1);

Style style = condition.GetStyle();
style.SetPattern(FillPattern::Solid);
style.SetForegroundColor(Color::FromArgb(255, 255, 0, 0));
condition.SetStyle(style);
```

<details>
<summary>View Additional Examples</summary>

```cpp
auto& validations = sheet.GetValidations();
auto rule = validations[validations.Add(CellArea::CreateCellArea("A1", "B2"))];

rule.SetType(ValidationType::WholeNumber);
rule.SetOperator(OperatorType::Between);
rule.SetFormula1("=1");
rule.SetFormula2("=10");
rule.SetShowError(true);
rule.SetErrorTitle("Whole Number");
rule.SetErrorMessage("Enter 1-10");
```

```cpp
sheet.GetCells()["A1"].PutValue("Docs");
auto& hyperlinks = sheet.GetHyperlinks();
auto link = hyperlinks[hyperlinks.Add("A1", 1, 1, "https://docs.aspose.org/cells/cpp/")];
link.SetTextToDisplay("Docs");
link.SetScreenTip("Getting started guide");
```

```cpp
PageSetup& pageSetup = sheet.GetPageSetup();
pageSetup.SetOrientation(PageOrientationType::Landscape);
pageSetup.SetPaperSize(PaperSizeType::PaperA4);
pageSetup.SetFitToPagesWide(1);
pageSetup.SetPrintArea("$A$1:$D$20");
pageSetup.SetPrintTitleRows("$1:$2");
pageSetup.SetCenterFooter("Page &P of &N");
```

```cpp
int index = workbook.GetDefinedNames().Add("PriceRange", "=Products!$B$2:$B$3");
DefinedName priceRange = workbook.GetDefinedNames()[index];
priceRange.SetComment("Cell range used by the SUM formula in B4.");
```

</details>

## API Reference

Aspose.Cells FOSS for Cpp provides the `Workbook` class as the root entry point for creating, loading, modifying, and saving XLSX workbooks, with `Worksheet`, `Cells`, and `Cell` forming the primary object graph beneath it. The library exposes additional collections and objects for formatting, validation, hyperlinks, defined names, page setup, and workbook properties.

The public API has 195 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `AutoFilter` | Represents auto filter. |
| `AutoFilterColorFilter` | Represents auto filter color filter. |
| `AutoFilterCustomFilter` | Represents auto filter custom filter. |
| `AutoFilterCustomFilterCollection` | Represents a collection of auto filter custom filter objects. |
| `AutoFilterCustomFilterCollection.Iterator` | Iterator for AutoFilterCustomFilterCollection. |
| `AutoFilterDynamicFilter` | Represents auto filter dynamic filter. |
| `AutoFilterSortCondition` | Represents auto filter sort condition. |
| `AutoFilterSortConditionCollection` | Represents a collection of auto filter sort condition objects. |
| `AutoFilterSortConditionCollection.Iterator` | Iterator for AutoFilterSortConditionCollection. |
| `AutoFilterSortState` | Represents auto filter sort state. |
| `AutoFilterSupport` | Internal helper methods for auto-filter operations. |
| `AutoFilterTop10` | Represents auto filter top10. |
| `Border` | Represents border. |
| `Borders` | Represents borders. |
| `CalculationProperties` | Represents calculation properties. |
| `Cell` | Represents a single worksheet cell and exposes value, formula, and style operations. |
| `CellArea` | Represents cell area. |
| `CellFormatValue` | Represents cell format value. |
| `CellValue` | CellValue class provides methods to access cell values as different types, including AsBool, AsDateTime, AsDouble, AsInteger, AsString, IsBool, and IsDateTime. |
| `Cells` | Provides access to worksheet cells, rows, columns, and merged ranges. |
| `CellsException` | Represents an error that occurs during cells. |
| `Color` | Represents color. |
| `Column` | Represents column. |
| `ColumnCollection` | Represents a collection of column objects. |
| `ConditionalFormattingCollection` | Represents a collection of conditional formatting objects. |
| `AlignmentValue` | Represents alignment value. |
| `AutoFilterColorFilterModel` | Represents auto filter color filter model. |
| `AutoFilterCustomFilterModel` | Represents auto filter custom filter model. |
| `AutoFilterDynamicFilterModel` | Represents auto filter dynamic filter model. |
| `AutoFilterModel` | Represents auto filter model. |
| `AutoFilterSortConditionModel` | Represents auto filter sort condition model. |
| `AutoFilterSortStateModel` | Represents auto filter sort state model. |
| `AutoFilterTop10Model` | Represents auto filter top10 model. |
| `BorderSideValue` | Represents border side value. |
| `BordersValue` | Represents borders value. |
| `CalculationPropertiesModel` | Represents calculation properties model. |
| `CellAddress` | Represents cell address. |
| `CellRecord` | Represents cell record. |
| `ColorValue` | Represents color value. |
| `ColumnRangeModel` | Represents column range model. |
| `ConditionalFormattingModel` | Represents conditional formatting model. |
| `CoreDocumentPropertiesModel` | Represents core document properties model. |
| `DateSerialConverter` | Provides date serial converter operations. |
| `DefinedNameModel` | Represents defined name model. |
| `DiagnosticBag` | Represents diagnostic bag. |
| `DiagnosticEntry` | Represents diagnostic entry. |
| `DocumentPropertiesModel` | Represents document properties model. |
| `ExtendedDocumentPropertiesModel` | Represents extended document properties model. |
| `FilterColumnModel` | Represents filter column model. |
| `FontValue` | Represents font value. |
| `FormatConditionModel` | Represents format condition model. |
| `HeaderFooterModel` | Represents header footer model. |
| `HyperlinkModel` | Represents hyperlink model. |
| `MergeRegion` | Represents merge region. |
| `NumberFormatValue` | Represents number format value. |
| `PageMarginsModel` | Represents page margins model. |
| `PageSetupModel` | Represents page setup model. |
| `PrintOptionsModel` | Represents print options model. |
| `ProtectionValue` | Represents protection value. |
| `RowModel` | Represents row model. |
| `SharedStringRepository` | Represents shared string repository. |
| `StyleRepository` | Represents style repository. |
| `StyleValue` | Represents style value. |
| `ValidationModel` | Represents validation model. |
| `WorkbookModel` | Represents workbook model. |
| `WorkbookPropertiesModel` | Represents workbook properties model. |
| `WorkbookProtectionModel` | Represents workbook protection model. |
| `WorkbookSettingsModel` | Represents workbook settings model. |
| `WorkbookViewModel` | Represents workbook view model. |
| `WorksheetModel` | Represents worksheet model. |
| `WorksheetProtectionModel` | Represents worksheet protection model. |
| `WorksheetViewModel` | Represents worksheet view model. |
| `CoreDocumentProperties` | Represents core document properties. |
| `DateTime` | DateTime class provides methods to construct and compare date-time values, including DateTime, Equals, GetDay, GetHour, GetMinute, GetMonth, GetSecond, and GetTicks. |
| `DefinedName` | Represents defined name. |
| `DefinedNameCollection` | Represents a collection of defined name objects. |
| `DefinedNameUtility` | Provides normalization and validation helpers for defined names. |
| `DisplayFormatSectionInfo` | Represents display format section info. |
| `DisplayTextDateFormatSupport` | Internal helper methods for formatting date/time display text. |
| `DisplayTextFormatter` | Internal static helper for formatting display text of cell values. |
| `DisplayTextFormatterSupport` | Internal helper methods for display-text formatting of numeric, text, and date/time values. |
| `DisplayTextLocaleSupport` | Internal helper for parsing and applying locale directives. |
| `DocumentProperties` | Represents document properties. |
| `ExtendedDocumentProperties` | Represents extended document properties. |
| `FillValue` | Represents fill value. |
| `FilterColumn` | Represents filter column. |
| `FilterColumnCollection` | Represents a collection of filter column objects. |
| `FilterColumnCollection.Iterator` | Iterator for FilterColumnCollection. |
| `FilterValueCollection` | Represents a collection of filter value objects. |
| `Font` | Represents font. |
| `FormatCondition` | Represents format condition. |
| `FormatConditionCollection` | Represents a collection of format condition objects. |
| `FormulaException` | Represents an error that occurs during formula. |
| `Hyperlink` | Represents hyperlink. |
| `HyperlinkCollection` | Encapsulates the hyperlinks defined for a worksheet. |
| `IWarningCallback` | Defines a callback that receives load warnings. |
| `ValidationMessage` | Represents validation message. |
| `WorkbookValidator` | Represents workbook validator. |
| `InvalidFileFormatException` | Represents an error that occurs during invalid file format. |
| `LoadDiagnostics` | Represents load diagnostics. |
| `LoadIssue` | Represents load issue. |
| `LoadOptions` | Specifies how a workbook should be loaded. |
| `NumberFormat` | Provides number format operations. |
| `CaseInsensitiveEqual` | CaseInsensitiveEqual class provides case-insensitive equality comparison for string keys. |
| `CaseInsensitiveHash` | CaseInsensitiveHash class provides case-insensitive hash computation for string keys. |
| `IPackageReader` | Defines a reader for package models. |
| `IPackageWriter` | Defines a writer for package models. |
| `MissingPartException` | Represents an error that occurs during missing part. |
| `PackageLoadContext` | Represents package load context. |
| `PackageModel` | Represents package model. |
| `PackagePartDescriptor` | Represents package part descriptor. |
| `PackageStructureException` | Represents an error that occurs during package structure. |
| `PackagingConventions` | Provides packaging conventions operations. |
| `RelationshipDescriptor` | Represents relationship descriptor. |
| `RelationshipResolutionException` | Represents an error that occurs during relationship resolution. |
| `PageSetup` | Represents worksheet print and page-layout settings. |
| `Row` | Represents row. |
| `RowCollection` | Represents a collection of row objects. |
| `SaveOptions` | Specifies how a workbook should be saved. |
| `Style` | Represents a mutable cell style facade that can be applied to one or more cells. |
| `StyleException` | Represents an error that occurs during style. |
| `StyleValueSanitizer` | Provides normalization helpers for style integer values. |
| `StylesheetLoadContext` | Internal context used during stylesheet loading to accumulate cell formats, differential formats, date style indexes, and the default cell style. |
| `StylesheetSaveContext` | Internal context used during stylesheet saving to hold the built stylesheet document together with style index maps and format counts. |
| `UnsupportedFeatureException` | Represents an error that occurs during unsupported feature. |
| `Validation` | Represents validation. |
| `ValidationCollection` | Represents a collection of validation objects. |
| `WarningInfo` | Represents warning info. |
| `Workbook` | Represents the root spreadsheet object used to create, load, modify, and save an XLSX workbook. |
| `WorkbookLoadException` | Represents an error that occurs during workbook load. |
| `WorkbookProperties` | Represents workbook properties. |
| `WorkbookPropertySupport` | Internal helpers that normalize workbook-level property strings to their canonical XML attribute values, throwing CellsException on unsupported input. |
| `WorkbookProtection` | Represents workbook protection. |
| `WorkbookSaveException` | Represents an error that occurs during workbook save. |
| `WorkbookSettings` | Represents workbook-level settings that affect date handling and display formatting. |
| `WorkbookView` | Represents workbook view. |
| `Worksheet` | Encapsulates a single worksheet and its supported v0.1 worksheet features. |
| `WorksheetCollection` | Encapsulates the workbook's worksheets and active-sheet state. |
| `WorksheetDefinedNamesState` | Stores the defined names state for a worksheet (print area, title rows, title columns). |
| `WorksheetProtection` | Represents worksheet protection. |
| `XNamespace` | Represents an XML namespace, used to construct qualified element names. |
| `XlsxDocumentProperties` | Provides static methods for building and loading XLSX document properties (core and extended) from/to a ZIP archive. |
| `XlsxWorkbookArchiveHelpers` | Internal helper methods for reading XLSX workbook parts from a ZIP archive. |
| `XlsxWorkbookAutoFilter` | Provides static methods for building and loading auto-filter XML elements. |
| `XlsxWorkbookConditionalFormatting` | Provides static methods for building and loading conditional formatting XML elements. |
| `XlsxWorkbookDefinedNames` | Provides static methods for building and loading workbook-level defined names. |
| `XlsxWorkbookHyperlinks` | Provides static methods for building and loading worksheet hyperlink data. |
| `XlsxWorkbookPageSetup` | Provides static methods for building and loading page-setup XML elements. |
| `XlsxWorkbookProperties` | Provides static methods for building and loading workbook-level metadata. |
| `XlsxWorkbookSerializer` | Serializes and deserializes workbook models in XLSX format. |
| `XlsxWorkbookSerializerCommon` | Constants and helpers shared across the XLSX workbook serializer. |
| `XlsxWorkbookStyles` | Provides static methods for building and loading workbook stylesheets. |
| `XlsxWorkbookStylesValueHelpers` | Provides helper methods for workbook style value conversions and comparisons. |
| `XlsxWorkbookStylesXml` | Provides XML read/write methods for the workbook styles part. |
| `XlsxWorkbookValidations` | Provides static methods for building and loading worksheet data validation elements in the XLSX workbook serializer. |
| `XlsxWorkbookWorksheetProtection` | Provides static methods for building and loading worksheet-protection XML elements. |
| `XlsxWorkbookWorksheetViews` | Provides static methods for building and loading worksheet view settings (sheet properties, sheet views) in the XLSX workbook serializer. |
| `SharedStringTableXmlMapper` | Not implemented. |
| `StylesheetXmlMapper` | Not implemented. |
| `WorkbookXmlMapper` | Not implemented. |
| `WorksheetXmlMapper` | Not implemented. |
| `XmlParsingException` | Represents an error that occurs during XML parsing. |
| `XmlAttribute` | Lightweight handle to an XML attribute. |
| `XmlDocument` | Represents a parsed XML document. |
| `XmlElement` | Lightweight handle to an XML element. |
| `XmlNodeData` | Internal node representation shared between XML types. |
| `ZipArchive` | In-memory representation of a ZIP archive. |
| `ZipArchiveEntry` | Represents an entry in a ZipArchive. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `BorderStyleType` | Specifies border style type. |
| `CellValueType` | Specifies cell value type. |
| `BorderStyle` | Specifies border style. |
| `CellValueKind` | Specifies cell value kind. |
| `DateSystem` | Specifies date system. |
| `Core.DiagnosticSeverity` | Specifies diagnostic severity. |
| `FillPatternKind` | Specifies fill pattern kind. |
| `HorizontalAlignment` | Specifies horizontal alignment. |
| `PageOrientation` | Specifies page orientation. |
| `SheetVisibility` | Specifies sheet visibility. |
| `VerticalAlignment` | Specifies vertical alignment. |
| `Cells_FOSS.DiagnosticSeverity` | Specifies diagnostic severity. |
| `FillPattern` | Specifies fill pattern. |
| `FilterOperatorType` | Specifies filter operator type. |
| `FormatConditionType` | Specifies format condition type. |
| `HorizontalAlignmentType` | Specifies horizontal alignment type. |
| `ValidationMessageSeverity` | Specifies validation message severity. |
| `LoadFormat` | Specifies load format. |
| `OperatorType` | Specifies operator type. |
| `PageOrientationType` | Specifies page orientation type. |
| `PaperSizeType` | Specifies paper size type. |
| `SaveFormat` | Specifies save format. |
| `TargetModeType` | Specifies target mode type. |
| `ValidationAlertType` | Specifies validation alert type. |
| `ValidationType` | Specifies validation type. |
| `VerticalAlignmentType` | Specifies vertical alignment type. |
| `VisibilityType` | Specifies visibility type. |

#### Detailed Member Reference

### Workbook

The `Aspose.Cells_FOSS.Workbook` class serves as the root spreadsheet object used to create, load, modify, and save an XLSX workbook, supporting operations such as saving to a file or stream with a specified `Aspose.Cells_FOSS.SaveFormat` and throwing `Aspose.Cells_FOSS.WorkbookSaveException` on save failures or `Aspose.Cells_FOSS.WorkbookLoadException` on load failures.

- `Dispose`: Releases resources associated with the workbook instance.
- `EnsureUniqueDefinedName`: Ensures no other defined name in the workbook shares the given name and scope.
- `EnsureUniqueSheetName`: Ensures no other worksheet in the workbook shares the given name.
- `EnsureValidDefinedNameScope`: Validates that the local sheet index is absent (global scope) or within the valid worksheet range.
- `GetDefinedNames`: Gets the workbook-defined names collection.
- `GetDefinedNamesModel`: Gets the underlying defined names model vector.
- `GetDocumentProperties`: Gets the document properties facade for core and extended metadata.
- `GetLoadDiagnostics`: Gets diagnostics collected while loading the current workbook.
- `GetModel`: Gets the underlying workbook model.
- `GetProperties`: Gets workbook metadata and view settings exposed by the supported public API.
- `GetSettings`: Gets workbook-level settings such as the date system and display culture.
- `GetWorksheets`: Gets the worksheets in workbook order.
- `Save`: Saves the workbook to an XLSX file using default save options.

### Worksheet

The `Aspose.Cells_FOSS.Worksheet` class encapsulates a single worksheet and its supported v0.1 worksheet features, providing access to cells, hyperlinks, validations, conditional formattings, page setup, and protection, with visibility, gridlines, zoom, and right-to-left settings controlled via methods such as `SetName`, `SetVisibilityType`, and `SetZoom`.

- `GetAutoFilter`: Gets auto-filter settings for the worksheet.
- `GetCells`: Gets the cell grid facade for the worksheet.
- `GetConditionalFormattings`: Gets the worksheet conditional formatting collection.
- `GetHyperlinks`: Gets the worksheet hyperlink collection.
- `GetModel`: Gets the underlying worksheet model.
- `GetName`: Gets or sets the worksheet name.
- `GetPageSetup`: Gets page setup settings for the worksheet.
- `GetProtection`: Gets worksheet protection settings.
- `GetRightToLeft`: Gets or sets whether the worksheet view is right-to-left.
- `GetShowGridlines`: Gets or sets whether gridlines are shown in the worksheet view.
- `GetShowRowColumnHeaders`: Gets or sets whether row and column headers are shown in the worksheet view.
- `GetShowZeros`: Gets or sets whether zero values are shown in the worksheet view.
- `GetTabColor`: Gets or sets the worksheet tab color.
- `GetValidations`: Gets the worksheet data validation collection.
- `GetVisibilityType`: Gets or sets the worksheet visibility state.
- `GetWorkbook`: Gets the parent workbook.
- `GetZoom`: Gets or sets the worksheet zoom percentage.
- `Protect`: Marks the worksheet as protected using the current protection settings.
- `Unprotect`: Clears worksheet protection and resets supported protection flags.

### Cell

The `Aspose.Cells_FOSS.Cell` class represents a single worksheet cell and exposes value, formula, and style operations, allowing values of multiple types—including `Aspose.Cells_FOSS.DateTime`—to be written via `PutValue` and retrieved as a variant-typed `Aspose.Cells_FOSS.CellValue`, with style applied and read via `GetStyle` and `SetStyle`.

- `GetColumn`: Gets the column index of the cell.
- `GetDisplayStringValue`: Gets the display text generated from the cell value, style, and workbook culture.
- `GetFormula`: Gets or sets the cell formula.
- `GetRow`: Gets the row index of the cell.
- `GetStringValue`: Gets a stable string representation of the cell value without applying style-based display formatting.
- `GetStyle`: Gets a detached copy of the cell style.
- `GetType`: Gets the current logical cell value type.
- `GetValue`: Gets or sets the logical cell value.
- `PutValue`: Sets the cell value to a string.
- `SetStyle`: Replaces the cell style with the supplied style object.

### ConditionalFormattingCollection

The `Aspose.Cells_FOSS.ConditionalFormattingCollection` class represents a collection of conditional formatting objects, supporting the addition of format conditions with a specified `Aspose.Cells_FOSS.FormatConditionType` and `OperatorType`, and allowing each `Aspose.Cells_FOSS.FormatCondition` to define its priority, stop-if-true behavior, and `Aspose.Cells_FOSS.Style`.

- `Add`: Adds the specified item.
- `GetCount`: Gets the number of items.
- `GetNextPriority`: Gets the next priority for the specified collections.
- `RemoveArea`: Removes the specified item.
- `RemoveAt`: Removes the specified item.

### ValidationCollection

The `Aspose.Cells_FOSS.ValidationCollection` class represents a collection of validation objects, supporting the addition of validation rules to cell areas with a specified `Aspose.Cells_FOSS.ValidationType` and `OperatorType`, and allowing error message and title to be configured via properties such as ShowError, ErrorTitle, and ErrorMessage.

- `Add`: Adds the specified item.
- `AddAreaToValidation`: Adds the specified area to the validation.
- `AreasOverlap`: Determines whether the specified areas overlap.
- `CompareAreas`: Compares two areas for sorting.
- `GetCount`: Gets the number of items.
- `GetValidationInCell`: Gets the validation in cell.
- `RemoveACell`: Removes the specified item.
- `RemoveArea`: Removes the specified item.
- `RemoveAreaFromValidation`: Removes the specified area from the validation.
- `SortAreas`: Sorts the specified areas.

### HyperlinkCollection

The `Aspose.Cells_FOSS.HyperlinkCollection` class encapsulates the hyperlinks defined for a worksheet, supporting the addition of hyperlinks to a cell area with an address, and allowing text to display and screen tip to be set via properties on the `Aspose.Cells_FOSS.Hyperlink` object.

- `Add`: Adds a hyperlink anchored at a cell or rectangular range specified by zero-based coordinates.
- `GetCount`: Gets the number of hyperlinks in the worksheet.
- `RemoveAt`: Removes the hyperlink at the specified zero-based index.

### DefinedNameCollection

The `Aspose.Cells_FOSS.DefinedNameCollection` class represents a collection of defined name objects, supporting the addition of defined names with a formula and optional local sheet index, and allowing a comment to be stored on each `Aspose.Cells_FOSS.DefinedName`.

- `Add`: Adds the specified item.
- `GetCount`: Gets the number of items.
- `GetEnumerator`: Returns a snapshot of all defined names in the collection.
- `RemoveAt`: Removes the specified item.

### PageSetup

The `Aspose.Cells_FOSS.PageSetup` class represents worksheet print and page-layout settings, supporting orientation and paper size via `Aspose.Cells_FOSS.PageOrientationType` and `Aspose.Cells_FOSS.PaperSizeType`, fit-to-page options, print area, title rows or columns, header and footer text, and horizontal or vertical page breaks.

- `AddHorizontalPageBreak`: Adds a horizontal page break at the specified zero-based row index.
- `AddVerticalPageBreak`: Adds a vertical page break at the specified zero-based column index.
- `ClearHorizontalPageBreaks`: Removes all horizontal page breaks.
- `ClearVerticalPageBreaks`: Removes all vertical page breaks.
- `GetBottomMargin`: Gets or sets the bottom margin in centimeters.
- `GetBottomMarginInch`: Gets or sets the bottom margin in inches.
- `GetCenterFooter`: Gets or sets the center footer text.
- `GetCenterHeader`: Gets or sets the center header text.
- `GetCenterHorizontally`: Gets or sets whether content is centered horizontally on the page.
- `GetCenterVertically`: Gets or sets whether content is centered vertically on the page.
- `GetFirstPageNumber`: Gets or sets the first printed page number.
- `GetFitToPagesTall`: Gets or sets the number of pages tall to fit when printing.
- `GetFitToPagesWide`: Gets or sets the number of pages wide to fit when printing.
- `GetFooterMargin`: Gets or sets the footer margin in centimeters.
- `GetFooterMarginInch`: Gets or sets the footer margin in inches.
- `GetHeaderMargin`: Gets or sets the header margin in centimeters.
- `GetHeaderMarginInch`: Gets or sets the header margin in inches.
- `GetHorizontalPageBreaks`: Gets the horizontal page breaks as sorted zero-based row indexes.
- `GetLeftFooter`: Gets or sets the left footer text.
- `GetLeftHeader`: Gets or sets the left header text.
- `GetLeftMargin`: Gets or sets the left margin in centimeters.
- `GetLeftMarginInch`: Gets or sets the left margin in inches.
- `GetOrientation`: Gets or sets the page orientation.
- `GetPaperSize`: Gets or sets the paper size.
- `GetPrintArea`: Gets or sets the print area reference.
- `GetPrintGridlines`: Gets or sets whether gridlines are printed.
- `GetPrintHeadings`: Gets or sets whether row and column headings are printed.
- `GetPrintTitleColumns`: Gets or sets the repeating title columns reference.
- `GetPrintTitleRows`: Gets or sets the repeating title rows reference.
- `GetRightFooter`: Gets or sets the right footer text.
- `GetRightHeader`: Gets or sets the right header text.
- `GetRightMargin`: Gets or sets the right margin in centimeters.
- `GetRightMarginInch`: Gets or sets the right margin in inches.
- `GetScale`: Gets or sets the print scaling percentage.
- `GetTopMargin`: Gets or sets the top margin in centimeters.
- `GetTopMarginInch`: Gets or sets the top margin in inches.
- `GetVerticalPageBreaks`: Gets the vertical page breaks as sorted zero-based column indexes.

### Style

The `Aspose.Cells_FOSS.Style` class represents a mutable cell style facade that can be applied to one or more cells, allowing font, borders, fill pattern, foreground and background colors, number format, horizontal alignment, and wrap text to be configured via dedicated getters and setters.

- `Borders`: Gets the border settings.
- `Clone`: Creates a copy of the current style.
- `Color`: Gets the fill foreground color.
- `FillPattern`: Gets the fill pattern.
- `Font`: Gets the font settings.
- `FromCore`: Creates a Style from a Core StyleValue.
- `GetBackgroundColor`: Gets the fill background color.
- `GetBorders`: Gets the border settings.
- `GetCustom`: Gets the custom number format code.
- `GetFont`: Gets the font settings.
- `GetForegroundColor`: Gets the fill foreground color.
- `GetHorizontalAlignment`: Gets the horizontal alignment.
- `GetIndentLevel`: Gets the indentation level.
- `GetIsHidden`: Gets whether the cell formula is hidden when worksheet protection is enabled.
- `GetIsLocked`: Gets whether the cell is locked when worksheet protection is enabled.
- `GetNumber`: Gets the numeric format identifier.
- `GetNumberFormat`: Gets the resolved number format string.
- `GetPattern`: Gets the fill pattern.
- `GetReadingOrder`: Gets the reading order.
- `GetRelativeIndent`: Gets the relative indent.
- `GetShrinkToFit`: Gets whether the cell content shrinks to fit.
- `GetTextRotation`: Gets the text rotation.
- `GetVerticalAlignment`: Gets the vertical alignment.
- `GetWrapText`: Gets whether text wraps within the cell.
- `HorizontalAlignmentType`: Gets the horizontal alignment.
- `SetBackgroundColor`: Sets the fill background color.
- `SetBorders`: Sets the border settings.
- `SetCustom`: Sets the custom number format code.
- `SetFont`: Sets the font settings.
- `SetForegroundColor`: Sets the fill foreground color.
- `SetHorizontalAlignment`: Sets the horizontal alignment.
- `SetIndentLevel`: Sets the indentation level.
- `SetIsHidden`: Sets whether the cell formula is hidden when worksheet protection is enabled.
- `SetIsLocked`: Sets whether the cell is locked when worksheet protection is enabled.
- `SetNumber`: Sets the numeric format identifier.
- `SetNumberFormat`: Sets the number format.
- `SetPattern`: Sets the fill pattern.
- `SetReadingOrder`: Sets the reading order.
- `SetRelativeIndent`: Sets the relative indent.
- `SetShrinkToFit`: Sets whether the cell content shrinks to fit.
- `SetTextRotation`: Sets the text rotation.
- `SetVerticalAlignment`: Sets the vertical alignment.
- `SetWrapText`: Sets whether text wraps within the cell.
- `ToCore`: Converts this style to a Core StyleValue.
- `VerticalAlignmentType`: Gets the vertical alignment.

### WorkbookProperties

The `Aspose.Cells_FOSS.WorkbookProperties` class represents workbook properties, with `Aspose.Cells_FOSS.DocumentProperties` and `Aspose.Cells_FOSS.ExtendedDocumentProperties` providing access to core and extended metadata, respectively, and `Aspose.Cells_FOSS.WorkbookSettings` controlling workbook-level settings that affect date handling and display formatting.

- `GetBackupFile`: Gets or sets a value indicating whether backup file.
- `GetCalculation`: Gets the calculation.
- `GetCodeName`: Gets or sets the code name.
- `GetDefaultThemeVersion`: Gets or sets the default theme version.
- `GetFilterPrivacy`: Gets or sets a value indicating whether filter privacy.
- `GetHidePivotFieldList`: Gets or sets a value indicating whether hide pivot field list.
- `GetProtection`: Gets the protection.
- `GetSaveExternalLinkValues`: Gets or sets a value indicating whether save external link values.
- `GetShowBorderUnselectedTables`: Gets or sets a value indicating whether show border unselected tables.
- `GetShowInkAnnotation`: Gets or sets a value indicating whether show ink annotation.
- `GetShowObjects`: Gets or sets the show objects.
- `GetUpdateLinks`: Gets or sets the update links.
- `GetView`: Gets the view.

The library's public types live in the `Aspose::Cells_FOSS` namespace, with `Workbook` as the
root entry point and `Worksheet`/`Cells`/`Cell` forming the primary object graph beneath it.

| Class | Description |
|---|---|
| `CellValue` | Variant-typed scalar cell value wrapper over `monostate`/`int`/`double`/`bool`/`std::string`/`DateTime`. |
| `DateTime` | DateTime provides component accessors such as GetYear(), GetMonth(), GetDay(), GetHour(), GetMinute(), and GetSecond() to retrieve individual parts of a date‑time value. |
| `DisplayTextLocaleSupport` | Internal helper for parsing and applying locale directives (e.g. `[$-0409]`, `[$-F800]`) embedded in Excel format strings. |
| `SharedStringTableXmlMapper` | Represents shared string table xml mapper. |
| `StylesheetXmlMapper` | Represents stylesheet xml mapper. |
| `WorkbookXmlMapper` | Represents workbook xml mapper. |
| `WorksheetXmlMapper` | Represents worksheet xml mapper. |
| `XmlParsingException` | Represents an error that occurs during xml parsing. |
| `ZipArchive` | In-memory representation of a ZIP archive, used to read and write the `.xlsx` package's parts. |

- `Workbook`
  - `Workbook()`, `Workbook(fileName)`, `Workbook(fileName, LoadOptions)`, `Workbook(stream, LoadOptions)`
  - `Save(fileName)`, `Save(fileName, SaveFormat)`, `Save(fileName, SaveOptions)`, `Save(stream, SaveFormat)`, `Save(stream, SaveOptions)`
  - Properties: `Worksheets: WorksheetCollection`, `Settings: WorkbookSettings`, `Properties: WorkbookProperties`, `DocumentProperties: DocumentProperties`, `DefinedNames: DefinedNameCollection`, `LoadDiagnostics: LoadDiagnostics`
- `Worksheet`
  - `Protect()`, `Unprotect()`
  - Properties: `Name: string`, `VisibilityType: VisibilityType`, `TabColor: Color`, `ShowGridlines/ShowRowColumnHeaders/ShowZeros/RightToLeft: bool`, `Zoom: int`, `Cells: Cells`, `Hyperlinks: HyperlinkCollection`, `Validations: ValidationCollection`, `ConditionalFormattings: ConditionalFormattingCollection`, `PageSetup: PageSetup`, `Protection: WorksheetProtection`, `AutoFilter: AutoFilter`
- `Cells`
  - `operator[](cellName)`, `operator()(row, column)`, `Merge(firstRow, firstColumn, totalRows, totalColumns)`
  - Properties: `Rows: RowCollection`, `Columns: ColumnCollection`, `MergedCells: vector<CellArea>`
- `Cell`
  - `PutValue(value)` (string/int/double/bool/`DateTime` overloads), `GetValue()`, `SetValue(CellValue)`, `GetStringValue()`, `GetDisplayStringValue()`, `SetFormula(text)`, `GetFormula()`, `GetStyle()`, `SetStyle(Style)`
  - Properties: `Row: int`, `Column: int`, `Type: CellValueType`
- `Style`
  - `GetFont()`/`SetFont(Font)`, `GetBorders()`/`SetBorders(Borders)`, `GetPattern()`/`SetPattern(FillPattern)`, `GetForegroundColor()`/`SetForegroundColor(Color)`, `GetBackgroundColor()`/`SetBackgroundColor(Color)`, `GetNumberFormat()`/`SetNumberFormat(text)`, `GetHorizontalAlignment()`/`SetHorizontalAlignment(...)`, `GetWrapText()`/`SetWrapText(bool)`
- `ConditionalFormattingCollection`
  - `Add()`, `RemoveAt(index)`, `RemoveArea(startRow, startColumn, totalRows, totalColumns)`, `operator[](index) -> FormatConditionCollection`
  - Properties: `Count: int`
- `FormatConditionCollection`
  - `operator[](index) -> FormatCondition`, `AddArea(CellArea)`, `AddCondition(FormatConditionType, OperatorType, formula1, formula2)`, `RemoveArea(CellArea)`, `RemoveCondition(index)`
  - Properties: `Count: int`, `RangeCount: int`
- `FormatCondition`
  - Properties: `Priority: int`, `StopIfTrue: bool`, `Style: Style`, `Formula1: string`, `Formula2: string`, `Type: FormatConditionType`, `Operator: OperatorType`
- `ValidationCollection`
  - `Add(CellArea)`, `operator[](index) -> Validation`, `RemoveACell(row, column)`, `RemoveArea(CellArea)`, `GetValidationInCell(row, column)`
  - Properties: `Count: int`
- `Validation`
  - `AddArea(CellArea)`
  - Properties: `Type: ValidationType`, `Operator: OperatorType`, `Formula1: string`, `Formula2: string`, `ShowError: bool`, `ErrorTitle: string`, `ErrorMessage: string`
- `HyperlinkCollection`
  - `Add(cellName, totalRows, totalColumns, address)`, `RemoveAt(index)`
  - Properties: `Count: int`
- `Hyperlink`
  - Properties: `Area: string`, `Address: string`, `TextToDisplay: string`, `ScreenTip: string`
- `DefinedNameCollection`
  - `Add(name, formula)`, `Add(name, formula, localSheetIndex)`, `RemoveAt(index)`
  - Properties: `Count: int`
- `DefinedName`
  - Properties: `Comment: string`
- `PageSetup`
  - `SetOrientation(PageOrientationType)`, `SetPaperSize(PaperSizeType)`, `SetFitToPagesWide/Tall(int)`, `SetPrintArea(range)`, `SetPrintTitleRows/Columns(range)`, `SetLeftHeader/CenterFooter(text)`, `AddHorizontalPageBreak(row)`, `AddVerticalPageBreak(column)`
  - Properties: `LeftMargin/RightMargin: double`, `Scale: optional<int>`, `PrintGridlines/CenterHorizontally: bool`
- Exceptions
  - `CellsException` — base error type for invalid indices, ranges, and arguments
  - `WorkbookLoadException` / `WorkbookSaveException` — load/save-specific failures
  - `InvalidFileFormatException` — the loaded bytes are not a readable OOXML package
  - `UnsupportedFeatureException` — a requested operation (e.g. non-XLSX save) is not implemented

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/cells/cpp/)** — installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/cells/cpp/)** — task-focused answers for common spreadsheet questions.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/issues).

- **[Full API reference](https://reference.aspose.org/cells/cpp/)** — the complete, browsable reference for all public types (the [API reference](#api-reference) section above covers the essentials).
- **[Contributor guide](AGENTS.md)** — architecture, technology assumptions, and conventions for contributors.

## Scope and Limitations

- **Only `.xlsx` (OOXML) is supported for load and save.** `LoadFormat` and `SaveFormat` each declare a single `Xlsx` member; saving to any other format throws `UnsupportedFeatureException("Only XLSX save is supported.")`. There is no `.xls`, `.xlsb`, `.ods`, or `.csv` read/write support.
- **Legacy SpreadsheetML (the pre-OOXML Excel 2003 XML dialect) is not implemented.** The mapper classes for it (`WorkbookXmlMapper`, `WorksheetXmlMapper`, `StylesheetXmlMapper`, `SharedStringTableXmlMapper`) exist in source but their read/write methods unconditionally throw `UnsupportedFeatureException`.
- **Cell-level comments/notes are not modeled as a distinct object.** The only `Comment` field in the public API belongs to `DefinedName` — a description string on a named range, not an Excel cell note or threaded comment.
- **Some advanced conditional-formatting rule types are recognized on load but not preserved.** An unsupported rule type is dropped with a `WarningInfo` diagnostic rather than failing the load outright.
- **AutoFilter date-group filters using certain patterns are rejected as unsupported during load** rather than approximated.

<details>
<summary>View Other Unimplemented Members</summary>

- `RelationshipResolutionException` is declared but unused by the library's own code.
- `StyleException` is declared but unused by the library's own code.

</details>

See [Aspose.Cells for Cpp — Enterprise Edition](https://products.aspose.com/cells/cpp/).

## Development and Testing

The suite covers 8 test files under `Aspose.Cells.Foss.Cpp.Tests/`.

Aspose.Cells FOSS for Cpp is published on NuGet as `Aspose.Cells.Cpp.FOSS`, but the package ships prebuilt static libraries for **Windows only** (`lib/win_x86`, `lib/win_x86_64`) built with the MSVC `v14x` toolset — its own bundled `aspose.cells.cpp.foss.targets` file errors the build for any other toolset or platform. There are no Linux/macOS binaries in the package.

```bash
nuget install Aspose.Cells.Cpp.FOSS
```

In an MSBuild-based Visual Studio project:

```xml
<PackageReference Include="Aspose.Cells.Cpp.FOSS" Version="26.4.1" />
```

Or in a CMake project on Windows, point at the package's own bundled config, which defines an `Aspose.Cells.Cpp.FOSS` imported target:

```cmake
set(aspose.cells.cpp.foss_DIR "path/to/packages/Aspose.Cells.Cpp.FOSS.26.4.1/build/native/Aspose.Cells.Cpp.FOSS")
find_package(aspose.cells.cpp.foss CONFIG REQUIRED)
target_link_libraries(your_target PRIVATE Aspose.Cells.Cpp.FOSS)
```

On Linux, macOS, or with a non-MSVC toolchain, build from source instead — the library itself is a plain, dependency-free CMake target and targets C++17 on MSVC, GCC, and Clang alike:

```cmake
add_subdirectory(Aspose.Cells.Foss.Cpp)
target_link_libraries(your_target PRIVATE aspose_cells_foss)
```

This links the `aspose_cells_foss` library from `Aspose.Cells.Foss.Cpp` as a CMake subdirectory and uses `FetchContent` to download GoogleTest v1.14.0 during configure; pass `-DASPOSE_CELLS_FOSS_TESTS_USE_SYSTEM_GTEST=ON` to use an installed GTest package instead. See [`Aspose.Cells.Foss.Cpp.Tests/README.md`](Aspose.Cells.Foss.Cpp.Tests/README.md) for that option.

The `samples/` directory builds a standalone executable against the same library:

```bash
cd samples
mkdir build && cd build
cmake ..
cmake --build .
```

## License

This project is licensed under the [MIT License](License/LICENSE.txt). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
