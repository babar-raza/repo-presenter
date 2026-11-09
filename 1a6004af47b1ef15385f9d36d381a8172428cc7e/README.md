# Aspose.Cells FOSS for Rust

![Rust edition](https://img.shields.io/badge/rust_edition-2021-blue.svg) [![Build Status](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.txt) [![Rust edition](https://img.shields.io/badge/Rust-2021%20edition-orange.svg)](Cargo.toml)

[![Aspose.Cells FOSS for Rust](https://products.aspose.org/media/cells/rust/banner-readme.png)](https://products.aspose.org/cells/rust/)

Aspose.Cells FOSS for Rust reads and writes `.xlsx` workbooks and provides programmatic access to workbook content including cells, styles, charts, shapes, pictures, tables, validations, conditional formatting, and auto-filters. It supports loading from files or byte arrays, and offers repair options for damaged packages or XML. The product exposes methods to read cell values as strings, doubles, booleans, or date-time values, and to write formulas with cached values. It allows setting worksheet properties such as name, visibility, tab color, zoom level, freeze panes, and page setup paper size, as well as workbook-level features like document properties and protection.

Aspose.Cells FOSS for Rust is a free, open-source, pure-Rust library for creating,
loading, editing, and saving Excel `.xlsx` (Office Open XML / SpreadsheetML) workbooks.
It exposes an API modeled after Aspose.Cells, so
the familiar `Workbook` / `Worksheet` / `Cells` object model is available to Rust
programs with no proprietary runtime, no Microsoft Office installation, and no external
Aspose dependency. The OOXML packaging — ZIP container, relationships, shared strings,
styles, worksheet XML, and charts — is implemented from scratch on top of a small set of
general-purpose crates: `zip` (package container), `roxmltree` (XML parsing), `chrono`
(date/time), `sha2` / `base64` / `getrandom` (protection hashing), and `serde_json`.

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
Start["An existing XLSX file"]
Start --> Product["Aspose.Cells FOSS for Rust"]
Product["Aspose.Cells FOSS for Rust"] --> Cap1["Read and write XLSX files"]
Cap2["Cell value management"]
Cap3["Styling and formatting"]
Cap4["Worksheet management"]
Cap5["Data validation and conditional formatting"]
Cap6["Charts and shapes"]
Cap7["Document properties and protection"]
Cap8["Auto-filters and tables"]
Product["Aspose.Cells FOSS for Rust"] --> Cap2["Cell value management"]
Product["Aspose.Cells FOSS for Rust"] --> Cap3["Styling and formatting"]
Product["Aspose.Cells FOSS for Rust"] --> Cap4["Worksheet management"]
Product["Aspose.Cells FOSS for Rust"] --> Cap5["Data validation and conditional formatting"]
Product["Aspose.Cells FOSS for Rust"] --> Cap6["Charts and shapes"]
Product["Aspose.Cells FOSS for Rust"] --> Cap7["Document properties and protection"]
Product["Aspose.Cells FOSS for Rust"] --> Cap8["Auto-filters and tables"]
Cap1["Read and write XLSX files"] --> Output["XLSX file"]
Cap2["Cell value management"] --> Output["XLSX file"]
Cap3["Styling and formatting"] --> Output["XLSX file"]
Cap4["Worksheet management"] --> Output["XLSX file"]
Cap5["Data validation and conditional formatting"] --> Output["XLSX file"]
Cap6["Charts and shapes"] --> Output["XLSX file"]
Cap7["Document properties and protection"] --> Output["XLSX file"]
Cap8["Auto-filters and tables"] --> Output["XLSX file"]
```

## Key Capabilities

- **Read and write XLSX files.** It reads and writes `.xlsx` workbooks using `Workbook.load_xlsx` from a file path, `load_xlsx_from_bytes` from in-memory bytes, and `save_xlsx` to a file path.
- **Cell value management.** It retrieves typed cell values with `Cell.get_string_value`, `Cell.get_double_value`, `Cell.get_bool_value`, and `Cell.get_date_time_value`, and writes formulas with cached results using `CellMut.put_formula_with_cached_value`.
- **Styling and formatting.** It applies cell styling through `CellStyle` with font, fill, borders, `number_format`, and `horizontal_alignment` settings.
- **Worksheet management.** It manages worksheets by adding new sheets with `WorksheetsMut.add` and configuring each sheet's name, visibility, tab color, and zoom level.
- **Data validation and conditional formatting.** It enforces data validation rules with `Validation.set_type` and `FormatCondition.set_type` for conditional formatting including cell-value, expression, color-scale, data-bar, and icon-set rules.
- **Charts and shapes.** It creates charts with `ChartCollection.add` and `Chart.chart_type`, embeds pictures using `PictureCollection.add_from_file`, and adds shapes via `ShapeCollection.add`.
- **Document properties and protection.** It configures document properties with `Workbook.document_properties`, protects workbooks with `Workbook.protect`, sets page layout with `PageSetup.paper_size`, and freezes panes using `Worksheet.freeze_panes`.
- **Auto-filters and tables.** It applies auto-filters with `AutoFilter.set_range`, sets color filters using `AutoFilterColorFilter.set_cell_color`, defines custom filter operators with `AutoFilterCustomFilter.set_operator`, and creates structured tables via `ListObjectCollection.add`.

- Create a new `Workbook` with `Workbook::new` (starts with one sheet, `"Sheet1"`), or
  load an existing `.xlsx` file from a path (`Workbook::load_xlsx`), a stream
  (`load_xlsx_from_stream`), or in-memory bytes (`load_xlsx_from_bytes`) — with defensive
  repair options via `LoadOptions` (`try_repair_package`, `try_repair_xml`) and structured
  `LoadDiagnostics` for the issues found along the way.
- Manage worksheets through `WorksheetsMut` / `Worksheets` (add, look up by index or
  name, active-sheet state) and `Worksheet` (name, visibility, tab color, gridlines,
  zoom, right-to-left layout, and protection).
- Read and write typed cell values through `Cell` / `CellMut` — `put_value_string`,
  `put_value_i32`, `put_value_bool`, `put_value_decimal`, `put_value_date_time` —
  addressed by A1 name (`get`) or row/column index (`get_by_index`), and enter formulas
  with cached results via `put_formula_with_cached_value`.
- Apply cell styling through `CellStyle` with `Font`, `Fill`, and `Borders`, targeted
  updates via `StyleFlag`, and custom `NumberFormat` strings.
- Size and organize rows, columns, and merged cell areas through `Rows` / `Columns` and `Cells`.
- Enforce data validation rules (`Validation`, `ValidationType`, `OperatorType`) and apply
  conditional formatting — cell-value, expression, color-scale, data-bar, and icon-set
  rules — through `FormatCondition` and `ConditionalFormattingCollection`.
- Build charts through `ChartType` on a worksheet's chart collection — column, line, bar,
  area, pie, doughnut, scatter, radar, bubble, and stock families, plus their stacked and
  3D variants, each rendered as real OOXML chart markup.
- Embed pictures with `Picture` and drawing shapes with `Shape` / `AutoShapeType`
  (rectangles, stars, arrows, and other preset geometries).
- Build structured Excel tables with `ListObject` (table styles, totals), auto-filters
  with `AutoFilter`, and compact in-cell trend charts with `SparklineGroup`.
- Attach hyperlinks (`Hyperlink`), workbook- and sheet-scoped defined names
  (`DefinedName`), and cell comments (`Comment`) with author, note, and visibility
  control.
- Read and write core and extended document properties (`DocumentProperties`,
  `ExtendedDocumentProperties`) and configure print and page layout through `PageSetup`
  (paper size, orientation, margins, page breaks) and `FreezePane`.
- Save back to `.xlsx` — to a file path (`save` / `save_xlsx`), a stream
  (`save_xlsx_to_stream`), or in-memory bytes (`save_xlsx_to_bytes`) — with `SaveOptions`.

## Installation

`aspose-cells-foss-rust` is not published on crates.io yet; to use it, build it from a source checkout:

```bash
git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust.git
cd Aspose.Cells-FOSS-for-Rust
cargo check --all-targets
```

## Dependencies

### Required Package Dependencies

- `base64 0.22`
- `chrono 0.4`
- `getrandom 0.3`
- `roxmltree 0.20`
- `serde_json 1`
- `sha2 0.10`
- `zip 0.6`

### Native and System Requirements

- Requires Rust edition `2021` (`edition` in `Cargo.toml`).

## Quick Start

Create a workbook, write typed values and a formula with a cached result, save it as
XLSX, and load it back:

```rust
use aspose_cells_foss_rust::{CellValue, Workbook};
use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    // Create a new workbook (starts with one sheet, "Sheet1").
    let mut workbook = Workbook::new();
    {
        let mut worksheets = workbook.get_worksheets_mut();
        let sheet = worksheets.get(0)?;
        let mut cells = sheet.get_cells_mut();

        cells.get("A1")?.put_value_string("Hello")?;
        cells.get("B1")?.put_value_i32(123)?;
        cells.get("C1")?.put_value_bool(true)?;
        cells.get("D1")?.put_value_decimal(12.5)?;
        cells.get("F1")?.put_value_i32(10)?;
        cells.get("G1")?
            .put_formula_with_cached_value("=F1*2", CellValue::Number(20.0))?;
    }
    workbook.save("hello.xlsx")?;

    // Load it back.
    let loaded = Workbook::load_xlsx("hello.xlsx")?;
    let sheet = loaded.worksheet("Sheet1")?;
    let cells = sheet.get_cells();
    println!("A1 = {}", cells.get("A1")?.display_string_value());

    Ok(())
}
```

## Additional Examples

```rust
let options = LoadOptions {
    try_repair_package: true,
    try_repair_xml: true,
    ..LoadOptions::default()
};

let loaded = Workbook::load_xlsx_with_options(&valid_path, &options)?;
let sheet = loaded.worksheet("Sheet1")?;
let cells = sheet.get_cells();

println!(
    "Loaded workbook with {} worksheet(s) and {} diagnostic issue(s).",
    loaded.get_worksheets().count(),
    loaded.get_load_diagnostics().issues().len()
);
```

<details>
<summary>View Additional Examples</summary>

```rust
let mut charts = sheet.get_charts();
charts.add(
    ChartType::Column,
    "Charts!$B$1:$B$13".to_string(),
    0, 4, 18, 8,
)?;
charts.add(
    ChartType::Line,
    "Charts!$C$1:$C$13".to_string(),
    0, 9, 18, 13,
)?;

let chart_count = charts.count();
let first = charts.get(0).expect("chart");
println!("Chart count: {}", chart_count);
println!("First chart type: {:?}", first.get_chart_type());
```

```rust
let mut collections = sheet.get_conditional_formattings();

let between_index = collections.add();
let mut between = collections.get(between_index).expect("collection should exist");
between.add_area(CellArea::create_cell_area_a1("A1", "A10")?)?;
let rule_index = between.add_condition_with_details(
    FormatConditionType::CellValue,
    OperatorType::Between,
    "3",
    "7",
);
let mut rule = between.get(rule_index).expect("rule should exist");
rule.set_priority(1)?;
let mut style = rule.get_style();
style.pattern = FillPattern::Solid;
style.fill_color = Some("FFFFC7CE".to_string());
rule.set_style(style);
```

```rust
let mut validations = sheet.get_validations();
let list_index = validations.add(CellArea::create_cell_area_a1("A1", "A3")?)?;
let mut list_validation = validations.get(list_index).expect("validation should exist");
list_validation.set_type(ValidationType::List);
list_validation.set_formula1("\"Open,Closed\"");
list_validation.set_in_cell_drop_down(true);
list_validation.set_show_error(true);
list_validation.set_error_title("Invalid");
list_validation.set_error_message("Choose from the list");
```

```rust
let mut tables = sheet.get_list_objects();
let table_index = tables.add_a1("A1", "D5", true)?;
let mut table = tables.get(table_index as usize).expect("table should exist");
table.set_display_name("Products")?;
table.set_table_style_type(TableStyleType::TableStyleMedium2);
table.set_show_totals(true);

let mut columns = table.get_list_columns();
columns.get(3).expect("quantity column").set_totals_calculation(TotalsCalculation::Sum);
```

```rust
let mut hyperlinks = links_sheet.get_hyperlinks();
let external_index = hyperlinks.add("A1", 1, 1, "https://example.com/docs?q=1")?;
let mut external_link = hyperlinks.get(external_index).expect("hyperlink should exist");
external_link.set_text_to_display("Docs");
external_link.set_screen_tip("External docs");

let mut defined_names = workbook.get_defined_names();
let global_index = defined_names.add("GlobalRange", "='Links'!$A$1:$D$5")?;
defined_names.get(global_index).expect("defined name should exist").set_hidden(true);
```

</details>

## API Reference

Aspose.Cells FOSS for Rust provides the `Workbook` entry point for reading and writing Excel workbooks, and the `Worksheet` entry point for accessing cells, charts, and formatting. The public API surface includes `AutoFilter`, `Cell`, `CellMut`, `CellStyle`, `Chart`, `ChartCollection`, `ChartType`, `ConditionalFormattingCollection`, `DefinedName`, `FormatCondition`, `Hyperlink`, and `LoadOptions`.

The verified public surface has 115 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `AutoFilter` | Represents auto filter. |
| `AutoFilterColorFilter` | Represents auto filter color filter. |
| `AutoFilterCustomFilter` | Represents auto filter custom filter. |
| `AutoFilterCustomFilterCollection` | Represents a collection of auto filter custom filter objects. |
| `AutoFilterDynamicFilter` | Represents auto filter dynamic filter. |
| `AutoFilterSortCondition` | Represents auto filter sort condition. |
| `AutoFilterSortConditionCollection` | Represents a collection of auto filter sort condition objects. |
| `AutoFilterSortState` | Represents auto filter sort state. |
| `AutoFilterTop10` | Represents auto filter top10. |
| `Border` | Represents border. |
| `Borders` | Represents borders. |
| `CalculationProperties` | Represents calculation properties. |
| `Cell` | Represents a single worksheet cell and exposes value, formula, and style operations. |
| `CellArea` | Represents cell area. |
| `CellMut` | Represents a single worksheet cell and exposes value, formula, and style operations. |
| `CellStyle` | Represents a mutable cell style facade that can be applied to one or more cells. |
| `Cells` | Provides access to worksheet cells, rows, columns, and merged ranges. |
| `CellsException` | Represents an error that occurs during cells. |
| `CellsMut` | Provides access to worksheet cells, rows, columns, and merged ranges. |
| `Chart` | Represents a chart embedded in a worksheet. |
| `ChartCollection` | Represents collection of charts on a worksheet. |
| `Color` | Represents color. |
| `Column` | Represents column. |
| `ColumnMut` | Represents column. |
| `ColumnProperties` | Encapsulates a single worksheet and its supported v0.1 worksheet features. |
| `Columns` | Represents a collection of column objects. |
| `ColumnsMut` | Represents a collection of column objects. |
| `Comment` | Represents a worksheet comment (legacy note) anchored to a single cell. |
| `CommentCollection` | Represents the collection of comments (legacy notes) on a worksheet. |
| `ConditionalFormattingCollection` | Represents a collection of conditional formatting objects. |
| `CoreDocumentProperties` | Represents core document properties. |
| `DefinedName` | Represents defined name. |
| `DefinedNameCollection` | Represents a collection of defined name objects. |
| `DocumentProperties` | Represents document properties. |
| `ExtendedDocumentProperties` | Represents extended document properties. |
| `Fill` | Represents a mutable cell style facade that can be applied to one or more cells. |
| `FilterColumn` | Represents filter column. |
| `FilterColumnCollection` | Represents a collection of filter column objects. |
| `FilterValueCollection` | Represents a collection of filter value objects. |
| `Font` | Represents font. |
| `FormatCondition` | Represents format condition. |
| `FormatConditionCollection` | Represents a collection of format condition objects. |
| `FormulaException` | Represents an error that occurs during formula. |
| `FreezePane` | Encapsulates a single worksheet and its supported v0.1 worksheet features. |
| `Hyperlink` | Represents hyperlink. |
| `HyperlinkCollection` | Encapsulates the hyperlinks defined for a worksheet. |
| `IWarningCallback` | Defines a callback that receives load warnings. |
| `InvalidFileFormatException` | Represents an error that occurs during invalid file format. |
| `ListColumn` | Represents a single column in an Excel table. |
| `ListColumnCollection` | Represents the ordered collection of columns in an Excel table. |
| `ListObject` | Represents an Excel table (structured reference / ListObject). |
| `ListObjectCollection` | Represents the collection of Excel tables on a worksheet. |
| `LoadDiagnostics` | Represents load diagnostics. |
| `LoadIssue` | Represents load issue. |
| `LoadOptions` | Specifies how a workbook should be loaded. |
| `NumberFormat` | Provides number format operations. |
| `PageSetup` | Represents worksheet print and page-layout settings. |
| `Picture` | Represents a picture (image) anchored to a worksheet. |
| `PictureCollection` | Represents collection of pictures anchored to a worksheet. |
| `Row` | Represents row. |
| `RowMut` | Represents row. |
| `RowProperties` | Encapsulates a single worksheet and its supported v0.1 worksheet features. |
| `Rows` | Represents a collection of row objects. |
| `RowsMut` | Represents a collection of row objects. |
| `SaveOptions` | Specifies how a workbook should be saved. |
| `Shape` | Represents a drawing object (auto shape) anchored to a worksheet. |
| `ShapeCollection` | Represents collection of drawing objects (shapes) on a worksheet. |
| `SparklineGroup` | A sparkline group contains sparkline items that share type and settings. |
| `SparklineGroupCollection` | Represents a collection of sparkline groups on a worksheet. |
| `StyleException` | Represents an error that occurs during style. |
| `StyleFlag` | Represents flags which indicate applied formatting properties. |
| `UnsupportedFeatureException` | Represents an error that occurs during unsupported feature. |
| `Validation` | Represents validation. |
| `ValidationCollection` | Represents a collection of validation objects. |
| `WarningInfo` | Represents warning info. |
| `Workbook` | Represents the root spreadsheet object used to create, load, modify, and save an XLSX workbook. |
| `WorkbookLoadException` | Represents an error that occurs during workbook load. |
| `WorkbookProperties` | Represents workbook properties. |
| `WorkbookProtection` | Represents workbook protection. |
| `WorkbookSaveException` | Represents an error that occurs during workbook save. |
| `WorkbookSettings` | Represents workbook-level settings that affect date handling and display formatting. |
| `WorkbookView` | Represents workbook view. |
| `Worksheet` | Encapsulates a single worksheet and its supported v0.1 worksheet features. |
| `WorksheetProtection` | Represents worksheet protection. |
| `Worksheets` | Encapsulates the workbook's worksheets and active-sheet state. |
| `WorksheetsMut` | Encapsulates the workbook's worksheets and active-sheet state. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `AutoShapeType` | Specifies the type of an auto shape (preset geometry). |
| `BorderLineStyle` | Represents border. |
| `BorderStyleType` | Specifies border style type. |
| `CellObjectValue` | CellObjectValue represents the type of value stored in a cell. |
| `CellValue` | CellValue holds the actual data content of a cell, such as text, number, boolean, or decimal. |
| `CellValueType` | Specifies cell value type. |
| `CellsError` | CellsError indicates an error condition encountered while processing cell data. |
| `ChartType` | Specifies the chart type. |
| `DateSystem` | DateSystem specifies the date system used for date calculations in a workbook. |
| `DiagnosticSeverity` | DiagnosticSeverity classifies the severity level of a diagnostic issue reported during workbook loading. |
| `FillPattern` | Specifies fill pattern. |
| `FilterOperatorType` | Represents FilterOperatorType. |
| `FontUnderlineType` | Enumerates font underline types. |
| `FormatConditionType` | Specifies format condition type. |
| `HorizontalAlignment` | HorizontalAlignment defines the horizontal alignment of content within a cell. |
| `ImageType` | Represents the format of an image stored in a worksheet. |
| `LoadFormat` | Specifies load format. |
| `OperatorType` | Specifies operator type. |
| `PageOrientationType` | Specifies page orientation type. |
| `PaperSizeType` | Specifies paper size type. |
| `SaveFormat` | Specifies save format. |
| `SparklineType` | Represents SparklineType. |
| `TableStyleType` | Represents the built-in Excel table style types. |
| `TargetModeType` | Specifies target mode type. |
| `TotalsCalculation` | Represents the aggregation function shown in a table totals row cell. |
| `ValidationAlertType` | Specifies validation alert type. |
| `ValidationType` | Specifies validation type. |
| `VerticalAlignment` | VerticalAlignment defines the vertical alignment of content within a cell. |
| `VisibilityType` | Specifies visibility type. |

#### Detailed Member Reference

### AutoFilter

The `AutoFilter` type provides range-based filtering on a worksheet with `AutoFilter.set_range` to define the filtered area, `AutoFilter.get_range` to retrieve it, `AutoFilter.clear` to remove filtering, `AutoFilter.filter_columns` to apply column-specific filters, `AutoFilter.get_filter_columns` to read current filters, and `AutoFilter.get_sort_state` and `AutoFilter.sort_state` to manage sort settings.

- `clear`: Clears the current state.
- `filter_columns`: Gets the filter columns.
- `get_filter_columns`: Gets the filter columns.
- `get_range`: Gets the range.
- `get_sort_state`: Gets the sort state.
- `range`: Gets the range.
- `set_range`: Sets the range.
- `sort_state`: Gets the sort state.

### Cell

The `Cell` type represents a read-only cell with `Cell.get_string_value`, `Cell.get_double_value`, `Cell.get_bool_value`, and `Cell.get_date_time_value` for typed value retrieval, `Cell.value` for the underlying value, and `Cell.formula_cached_value` for cached formula results, while `Cell.style` provides access to the cell's formatting.

- `bool_value`: Gets the associated value.
- `border`: Gets the associated value.
- `column`: Gets the associated value.
- `date_time_value`: Gets the associated value.
- `display_string_value`: Gets the display text generated from the cell value, style, and workbook culture.
- `double_value`: Gets the associated value.
- `formatted_string_value`: Gets the associated value.
- `formula_cached_value`: Gets the associated value.
- `get_bool_value`: Gets the associated value.
- `get_border`: Gets the associated value.
- `get_column`: Gets the associated value.
- `get_date_time_value`: Gets the associated value.
- `get_display_string_value`: Gets the display text generated from the cell value, style, and workbook culture.
- `get_double_value`: Gets the associated value.
- `get_formatted_string_value`: Gets the associated value.
- `get_formula_cached_value`: Gets the associated value.
- `get_int_value`: Gets the associated value.
- `get_long_value`: Gets the associated value.
- `get_name`: Gets the associated value.
- `get_raw_string_value`: Gets the associated value.
- `get_row`: Gets the associated value.
- `get_string_value`: Gets a stable string representation of the cell value without applying style-based display formatting.
- `get_style`: Gets the associated value.
- `get_style_with_borders`: Gets the associated value.
- `get_type`: Gets the current logical cell value type.
- `get_value`: Gets the logical cell value.
- `int_value`: Gets the associated value.
- `long_value`: Gets the associated value.
- `name`: Gets the associated value.
- `raw_string_value`: Gets the associated value.
- `row`: Gets the associated value.
- `string_value`: Gets a stable string representation of the cell value without applying style-based display formatting.
- `style`: Gets the associated value.
- `value`: Gets the logical cell value.
- `value_type`: Gets the current logical cell value type.

### CellMut

The `CellMut` type provides mutable cell operations with `CellMut.put_value_string`, `CellMut.put_value_i32`, `CellMut.put_value_bool`, and `CellMut.put_value_date_time` for setting values, `CellMut.put_formula_with_cached_value` for formulas, `CellMut.set_value` for generic value assignment, and `CellMut.set_style` to update formatting.

- `apply_bold`: Applies bold.
- `apply_border_color`: Applies border color.
- `apply_border_line_style`: Applies border line style.
- `apply_fill`: Applies fill.
- `apply_fill_color`: Applies fill color.
- `apply_font`: Applies font.
- `apply_horizontal_alignment`: Applies horizontal alignment.
- `apply_italic`: Applies italic.
- `apply_number_format`: Applies number format.
- `apply_text_wrap`: Applies text wrap.
- `apply_vertical_alignment`: Applies vertical alignment.
- `bool_value`: Gets the associated value.
- `border`: Gets the associated value.
- `clear_alignment`: Clears alignment.
- `clear_bold`: Clears bold.
- `clear_border`: Clears border.
- `clear_fill`: Clears fill.
- `clear_fill_color`: Clears fill color.
- `clear_font`: Clears font.
- `clear_horizontal_alignment`: Clears horizontal alignment.
- `clear_italic`: Clears italic.
- `clear_number_format`: Clears number format.
- `clear_style`: Clears style.
- `clear_text_wrap`: Clears text wrap.
- `clear_value`: Clears value.
- `clear_vertical_alignment`: Clears vertical alignment.
- `column`: Gets the associated value.
- `date_time_value`: Gets the associated value.
- `display_string_value`: Gets the display text generated from the cell value, style, and workbook culture.
- `double_value`: Gets the associated value.
- `formatted_string_value`: Gets the associated value.
- `formula_cached_value`: Gets the associated value.
- `get_bool_value`: Gets the associated value.
- `get_border`: Gets the associated value.
- `get_column`: Gets the associated value.
- `get_date_time_value`: Gets the associated value.
- `get_display_string_value`: Gets the display text generated from the cell value, style, and workbook culture.
- `get_double_value`: Gets the associated value.
- `get_formatted_string_value`: Gets the associated value.
- `get_formula_cached_value`: Gets the associated value.
- `get_int_value`: Gets the associated value.
- `get_long_value`: Gets the associated value.
- `get_name`: Gets the associated value.
- `get_raw_string_value`: Gets the associated value.
- `get_row`: Gets the associated value.
- `get_string_value`: Gets a stable string representation of the cell value without applying style-based display formatting.
- `get_style`: Gets the associated value.
- `get_style_with_borders`: Gets the associated value.
- `get_type`: Gets the current logical cell value type.
- `get_value`: Gets the logical cell value.
- `int_value`: Gets the associated value.
- `long_value`: Gets the associated value.
- `name`: Gets the associated value.
- `put_bool`: Sets bool.
- `put_date_time`: Sets date time.
- `put_datetime`: Sets datetime.
- `put_formula`: Sets formula.
- `put_formula_with_cached_value`: Sets formula with cached value.
- `put_number`: Sets number.
- `put_string`: Sets string.
- `put_value`: Sets value.
- `put_value_bool`: Sets value bool.
- `put_value_char`: Sets value char.
- `put_value_date_time`: Sets value date time.
- `put_value_decimal`: Sets value decimal.
- `put_value_f32`: Sets value f32.
- `put_value_f64`: Sets value f64.
- `put_value_i16`: Sets value i16.
- `put_value_i32`: Sets value i32.
- `put_value_i64`: Sets value i64.
- `put_value_object`: Sets value object.
- `put_value_string`: Sets value string.
- `put_value_string_converted`: Sets value string converted.
- `put_value_string_converted_with_style`: Sets value string converted with style.
- `put_value_u8`: Sets value u8.
- `raw_string_value`: Gets the associated value.
- `reset_style`: Resets the cell style to the workbook default style.
- `row`: Gets the associated value.
- `set_border`: Sets the associated value.
- `set_style`: Sets the associated value.
- `set_style_with_explicit_flag`: Sets the associated value.
- `set_style_with_flag`: Sets the associated value.
- `set_value`: Sets the logical cell value.
- `string_value`: Gets a stable string representation of the cell value without applying style-based display formatting.
- `style`: Gets the associated value.
- `update_style`: Updates the cell style in place using the provided callback.
- `value`: Gets the logical cell value.
- `value_type`: Gets the current logical cell value type.

### CellStyle

The `CellStyle` type exposes formatting properties including `CellStyle.font` for font settings, `CellStyle.fill` for background patterns, `CellStyle.borders` for border configuration, `CellStyle.number_format` for numeric formatting, `CellStyle.horizontal_alignment` and `CellStyle.vertical_alignment` for text alignment, and `CellStyle.wrap_text` for line wrapping control.

- `borders`: Gets border settings.
- `clear_horizontal_alignment`: Clears horizontal alignment.
- `clear_number_format`: Clears number format.
- `clear_vertical_alignment`: Clears vertical alignment.
- `copy`: Copies data from another style object.
- `copy_from`: Copies all style values from another style instance.
- `fill`: Gets the associated value.
- `font`: Gets the font settings.
- `get_borders`: Gets border settings.
- `get_borders_mut`: Gets mutable border settings, so that borders can be changed in place: style.get_borders_mut().top_mut().set_color("FFFF0000").
- `get_custom`: Gets the custom number format code.
- `get_fill`: Gets the associated value.
- `get_font`: Gets the font settings.
- `get_font_mut`: Gets mutable font settings, so that font properties can be changed in place: style.get_font_mut().set_size(14.0).
- `get_horizontal_alignment`: Gets the horizontal alignment.
- `get_indent_level`: Gets the indentation level.
- `get_is_hidden`: Gets whether the cell formula is hidden when worksheet protection is enabled.
- `get_is_locked`: Gets whether the cell is locked when worksheet protection is enabled.
- `get_is_text_wrapped`: Gets the associated value.
- `get_number`: Gets the numeric format identifier.
- `get_number_format`: Gets the resolved number format string.
- `get_quote_prefix`: Gets whether the cell value starts with a single quote mark.
- `get_reading_order`: Gets the reading order.
- `get_relative_indent`: Gets the relative indent.
- `get_shrink_to_fit`: Gets whether the cell content shrinks to fit.
- `get_text_rotation`: Gets the text rotation.
- `get_vertical_alignment`: Gets the vertical alignment.
- `new`: Initializes a new instance.
- `set_borders`: Sets border settings.
- `set_custom`: Sets the custom number format code.
- `set_fill`: Sets the associated value.
- `set_font`: Sets the font settings.
- `set_horizontal_alignment`: Sets the horizontal alignment.
- `set_indent_level`: Sets the indentation level.
- `set_is_hidden`: Sets whether the cell formula is hidden when worksheet protection is enabled.
- `set_is_locked`: Sets whether the cell is locked when worksheet protection is enabled.
- `set_is_text_wrapped`: Sets the associated value.
- `set_number`: Sets the numeric format identifier.
- `set_number_format`: Sets the resolved number format string.
- `set_quote_prefix`: Sets whether the cell value starts with a single quote mark.
- `set_reading_order`: Sets the reading order.
- `set_relative_indent`: Sets the relative indent.
- `set_shrink_to_fit`: Sets whether the cell content shrinks to fit.
- `set_text_rotation`: Sets the text rotation.
- `set_vertical_alignment`: Sets the vertical alignment.

### Chart

The `Chart` type represents a chart object with `Chart.chart_type` and `Chart.data_range` to define its appearance and data source, `Chart.get_chart_type` and `Chart.get_data_range` to inspect them, and `Chart.delete` to remove the chart from its worksheet.

- `chart_type`: Gets the chart type.
- `data_range`: Gets the chart data range formula.
- `delete`: Deletes the chart from its owning worksheet.
- `get_chart_type`: Gets the chart type.
- `get_data_range`: Gets the chart data range formula.
- `get_extent_cx`: Gets the width extent in EMU.
- `get_extent_cy`: Gets the height extent in EMU.
- `get_lower_right_column`: Gets the zero-based lower-right column of the chart anchor.
- `get_lower_right_row`: Gets the zero-based lower-right row of the chart anchor.
- `get_name`: Gets the chart display name.
- `get_upper_left_column`: Gets the zero-based upper-left column of the chart anchor.
- `get_upper_left_row`: Gets the zero-based upper-left row of the chart anchor.
- `lower_right_column`: Gets the zero-based lower-right column of the chart anchor.
- `lower_right_row`: Gets the zero-based lower-right row of the chart anchor.
- `name`: Gets the chart display name.
- `set_name`: Sets the chart display name.
- `upper_left_column`: Gets the zero-based upper-left column of the chart anchor.
- `upper_left_row`: Gets the zero-based upper-left row of the chart anchor.

### ChartCollection

The `ChartCollection` type manages charts on a worksheet with `ChartCollection.add` to insert new charts, `ChartCollection.count` to retrieve the total, `ChartCollection.get` to access a chart by index, and `ChartCollection.item` as an alias for indexed retrieval.

- `add`: Adds a new chart of the specified type to the worksheet.
- `count`: Gets the number of charts on the worksheet.
- `get`: Gets the chart at the specified zero-based index.
- `get_count`: Gets the number of charts on the worksheet.
- `item`: Gets the chart at the specified zero-based index.
- `remove_at`: Removes the chart at the specified zero-based index.

### ChartType

The `ChartType` enumeration defines supported chart types for use with `ChartCollection.add` and `Chart.chart_type`.

### ConditionalFormattingCollection

The `ConditionalFormattingCollection` type manages conditional formatting rules with `ConditionalFormattingCollection.add` to create new rules, `ConditionalFormattingCollection.count` to list them, and `ConditionalFormattingCollection.get` to access individual rules.

- `add`: Adds the specified item.
- `count`: Gets the number of items.
- `get`: Gets the item from the collection.
- `remove_area`: Removes an item.
- `remove_at`: Removes an item.

### DefinedName

The `DefinedName` type represents a named range with `DefinedName.get_name` and `DefinedName.get_formula` to read its identifier and formula, and `DefinedName.set_name` and `DefinedName.set_formula` to update them.

- `get_comment`: Gets the comment.
- `get_formula`: Gets the formula.
- `get_local_sheet_index`: Gets the local sheet index.
- `get_name`: Gets the name.
- `is_hidden`: Returns whether hidden.
- `set_comment`: Sets the comment.
- `set_formula`: Sets the formula.
- `set_hidden`: Sets a value indicating whether hidden.
- `set_local_sheet_index`: Sets the local sheet index.
- `set_name`: Sets the name.

### FormatCondition

The `FormatCondition` type configures conditional formatting rules with `FormatCondition.set_type` to choose the condition type, `FormatCondition.set_priority` to adjust evaluation order, `FormatCondition.get_style` and `FormatCondition.set_style` to manage the applied formatting.

- `get_above`: Gets a value indicating whether above.
- `get_bar_color`: Gets the bar color.
- `get_bar_length`: Gets the bar length.
- `get_color_scale_count`: Gets the color scale count.
- `get_direction`: Gets the direction.
- `get_duplicate`: Gets a value indicating whether duplicate.
- `get_formula`: Gets the formula.
- `get_formula1`: Gets the formula1.
- `get_formula2`: Gets the formula2.
- `get_icon_set_type`: Gets the icon set type.
- `get_max_color`: Gets the max color.
- `get_mid_color`: Gets the mid color.
- `get_min_color`: Gets the min color.
- `get_negative_bar_color`: Gets the negative bar color.
- `get_operator`: Gets the operator.
- `get_percent`: Gets a value indicating whether percent.
- `get_priority`: Gets the priority.
- `get_rank`: Gets the rank.
- `get_reverse_icons`: Gets a value indicating whether reverse icons.
- `get_show_border`: Gets a value indicating whether show border.
- `get_show_icon_only`: Gets a value indicating whether show icon only.
- `get_standard_deviation`: Gets the standard deviation.
- `get_stop_if_true`: Gets a value indicating whether stop if true.
- `get_style`: Gets the style.
- `get_time_period`: Gets the time period.
- `get_top`: Gets a value indicating whether top.
- `get_type`: Gets the type.
- `remove`: Removes the specified item.
- `set_above`: Sets a value indicating whether above.
- `set_bar_color`: Sets the bar color.
- `set_bar_length`: Sets the bar length.
- `set_color_scale_count`: Sets the color scale count.
- `set_direction`: Sets the direction.
- `set_duplicate`: Sets a value indicating whether duplicate.
- `set_formula`: Sets the formula.
- `set_formula1`: Sets the formula1.
- `set_formula2`: Sets the formula2.
- `set_icon_set_type`: Sets the icon set type.
- `set_max_color`: Sets the max color.
- `set_mid_color`: Sets the mid color.
- `set_min_color`: Sets the min color.
- `set_negative_bar_color`: Sets the negative bar color.
- `set_operator`: Sets the operator.
- `set_percent`: Sets a value indicating whether percent.
- `set_priority`: Sets the priority.
- `set_rank`: Sets the rank.
- `set_reverse_icons`: Sets a value indicating whether reverse icons.
- `set_show_border`: Sets a value indicating whether show border.
- `set_show_icon_only`: Sets a value indicating whether show icon only.
- `set_standard_deviation`: Sets the standard deviation.
- `set_stop_if_true`: Sets a value indicating whether stop if true.
- `set_style`: Sets the style.
- `set_time_period`: Sets the time period.
- `set_top`: Sets a value indicating whether top.
- `set_type`: Sets the type.
- `style`: Gets the style.

### Hyperlink

The `Hyperlink` type represents a clickable link with `Hyperlink.address` and `Hyperlink.area` to define its target and cell range, and `Hyperlink.get_address` and `Hyperlink.get_area` to inspect them.

- `address`: Gets the address.
- `area`: Gets the area.
- `delete`: Performs delete.
- `get_address`: Gets the address.
- `get_area`: Gets the area.
- `get_screen_tip`: Gets the screen tip.
- `get_text_to_display`: Gets the text to display.
- `screen_tip`: Gets the screen tip.
- `set_address`: Sets the address.
- `set_screen_tip`: Sets the screen tip.
- `set_text_to_display`: Sets the text to display.
- `text_to_display`: Gets the text to display.

### LoadOptions

The `LoadOptions` type controls workbook loading behavior with `LoadOptions.default` to create default settings, `LoadOptions.try_repair_package` to enable package-level recovery, and `LoadOptions.try_repair_xml` to enable XML-level recovery.

The library source lives under `src/Aspose.Cells_FOSS/`, one module per public type, with
runnable samples alongside it at the repository root:

```
├── src/
│   ├── lib.rs                      # Crate root; re-exports the public API
│   └── Aspose.Cells_FOSS/
│       ├── api.rs                  # Wires the modules together
│       ├── Core/                   # Internal data models
│       ├── Packaging/              # OOXML package (ZIP) reading/writing
│       ├── Xml/                    # SpreadsheetML XML mappers
│       ├── Validation/             # Workbook validation
│       ├── ChartDefaults/          # Default chart XML templates
│       ├── Workbook.rs             #   Workbook entry point
│       ├── Worksheet.rs            #   Worksheet model
│       ├── Cell.rs / Cells.rs      #   Cell model and collection
│       ├── Style.rs                #   Styles (font, fill, alignment, border)
│       ├── Validation.rs           #   Data validation
│       ├── Chart.rs / ChartLive.rs #   Charts
│       └── ...                     # One module per public type (Comment, Hyperlink, ListObject, ...)
├── samples/                        # Runnable feature examples
│   ├── basic.rs
│   ├── styles.rs
│   ├── charts.rs
│   ├── ...                         # One sample per feature area
│   └── README.md                   # Sample overview
├── License/LICENSE.txt             # MIT license (also mirrored at the repository root)
├── AGENTS.md                       # AI-assisted development guide
├── Cargo.toml
└── README.md
```

- `Workbook`
  - `new() -> Workbook` / `load_xlsx(path)` / `load_xlsx_from_stream(reader)` / `load_xlsx_from_bytes(bytes)`
  - `load_xlsx_with_options(path, &LoadOptions)`
  - `get_worksheets() -> Worksheets` / `get_worksheets_mut() -> WorksheetsMut`
  - `worksheet(name) -> Result<Worksheet, CellsError>`
  - `get_settings() -> WorkbookSettings`, `get_properties() -> WorkbookProperties`
  - `get_document_properties() -> DocumentProperties`
  - `get_defined_names() -> DefinedNameCollection`
  - `get_load_diagnostics() -> LoadDiagnostics`
  - `save(path)` / `save_xlsx(path)` / `save_with_format(path, format)`
  - `save_xlsx_to_stream(writer)` / `save_xlsx_to_bytes() -> Vec<u8>`

- `WorksheetsMut` / `Worksheets`
  - `count() -> usize`, `add(name) -> usize`
  - `get(index)` / `get_by_name(name)`
  - `remove_at(index)` — returns `CellsError::Unsupported` if it is the sole remaining worksheet

- `Worksheet`
  - `get_name()` / `set_name(value)`, `get_visibility_type()` / `set_visibility_type(value)`
  - `get_tab_color()` / `set_tab_color(value)`
  - `get_show_gridlines()`, `get_show_row_column_headers()`, `get_right_to_left()`
  - `get_cells() -> Cells` / `get_cells_mut() -> CellsMut`
  - `get_hyperlinks()`, `get_validations()`, `get_conditional_formattings()`, `get_auto_filter()`
  - `get_page_setup_mut() -> PageSetup`, `get_charts() -> ChartCollection`
  - `get_pictures()`, `get_shapes()`, `get_list_objects()`, `get_sparkline_groups()`

- `PageSetup`
  - `set_left_margin_inch(value)`, `set_right_margin_inch(value)`

- `SaveOptions` — passed to `save_with_options` / `save_xlsx_to_stream_with_options`

- `Validation` — `set_type(ValidationType)`, `set_formula1(value)`, `set_formula2(value)`,
  `set_operator(OperatorType)`, `set_show_error(value)`, `set_error_title(value)`

- `ConditionalFormattingCollection` — `add()`, `add_condition_with_details(FormatConditionType, OperatorType, formula1, formula2)`

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/cells/rust/)** — The getting started guide covers installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/cells/rust/)** — The how-to guides and FAQ provide task-focused answers for common spreadsheet-processing questions.
- **[samples/README.md](samples/README.md)** — The samples overview lists many runnable examples, one per feature area.
- **[Contributor guide](AGENTS.md)** — The contributor guide provides architecture notes, module wiring, and conventions for contributors.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust/issues).

- **[Full API reference](https://reference.aspose.org/cells/rust/)** — the complete, browsable reference for the public API surface (the [API reference](#api-reference) section above covers the essentials).

## Scope and Limitations

Aspose.Cells FOSS for Rust reads and writes `.xlsx` (OOXML/SpreadsheetML) workbooks, supports workbook creation, loading, and saving, and exposes worksheet and cell manipulation through a Rust API.

- Installation uses a git dependency in `Cargo.toml`, and the crate is not yet published to crates.io.
- The repository ships no automated test suite: cargo test --all-targets currently reports 0 tests.
- A recent stable Rust toolchain (2021 edition or later) is required to build and use aspose-cells-foss-rust.
- `WorksheetsMut.remove_at` returns a CellsError::Unsupported error when asked to remove the last remaining worksheet.

More real, runnable examples are collected below — see [`samples/`](samples/) and
[`samples/README.md`](samples/README.md) for the complete set.

- `Cells` / `CellsMut`
  - `get(a1_address) -> Result<Cell, CellsError>` / `get_by_index(row, column)`
  - `get_rows() -> Rows`, `get_columns() -> Columns`

- `Cell` / `CellMut`
  - `put_value_string(value)`, `put_value_i32(value)`, `put_value_f64(value)`,
    `put_value_bool(value)`, `put_value_decimal(value)`, `put_value_date_time(value)`
  - `put_formula_with_cached_value(formula, CellValue)`
  - `display_string_value() -> String`, `value_type() -> CellValueType`
  - `get_style() -> CellStyle` / `set_style(style)`

- `CellStyle`
  - `get_font_mut() -> &mut Font`, `pattern: FillPattern`, `fill_color: Option<String>`

- `Font`
  - `set_color(value)`, `set_is_bold(value)`, `set_is_italic(value)`, `set_underline(value)`

- `Color`
  - `from_argb(a, r, g, b) -> Color`

- `LoadOptions`
  - `try_repair_package: bool`, `try_repair_xml: bool` (`..LoadOptions::default()`)

- `FormatCondition` — `set_priority(value)`, `set_stop_if_true(value)`, `get_style()` / `set_style(style)`

- `CellsError` (enum, 10 members including `Unsupported(&'static str)`, `Io(String)`)

- A workbook must always keep at least one worksheet: `WorksheetsMut::remove_at` returns
  a `CellsError::Unsupported` error when asked to remove the last remaining worksheet.

These limitations don't apply to [full-featured Aspose.Cells — Enterprise Edition](https://products.aspose.com/cells/). It adds broader format coverage (including legacy XLS, CSV, and ODS), full feature completeness, and commercial support.

## Development and Testing

The repository uses the Rust toolchain with edition 2021 and requires no proprietary Aspose runtime or Microsoft Office installation. The package name is aspose-cells-foss-rust and the library imports as `aspose_cells_foss_rust`. The samples/ directory serves as the de-facto verification suite: each sample creates a workbook, saves it under output/samples/, loads it back, and prints what it read. After a change that touches the read/write path, run the core samples and confirm they still round-trip.

The [ci workflow](.github/workflows/ci.yml) runs on Ubuntu, Windows, macOS 14 and macOS 13.

```toml
[dependencies]
aspose-cells-foss-rust = { git = "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust" }
```

For local development against a cloned copy, use a path dependency instead:

```toml
[dependencies]
aspose-cells-foss-rust = { path = "../Aspose.Cells-FOSS-for-Rust" }
```

The package name is `aspose-cells-foss-rust`; the library is imported as
`aspose_cells_foss_rust`. Requires a recent stable Rust toolchain (2021 edition or later).
No proprietary Aspose runtime and no Microsoft Office installation is required.

To build the library directly from a clone:

```bash
git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Rust.git
cd Aspose.Cells-FOSS-for-Rust
cargo build
```

The repository currently has no unit or integration test suite —
`cargo test --all-targets` reports 0 tests.

```bash
cargo build
cargo check --all-targets
cargo fmt --all --check
cargo clippy --all-targets
cargo test --all-targets
cargo run --bin sample_basic
cargo run --bin sample_loading
cargo run --bin sample_styles
```

CI ([`ci.yml`](.github/workflows/ci.yml)) runs `fmt`, `check`, `clippy`, `test`, the three
samples above as smoke tests, and `cargo bench` on Linux x64, Windows x64, macOS ARM, and
macOS x64. The `samples/` directory demonstrates every feature area — `basic.rs`,
`styles.rs`, `worksheet_settings.rs`, `validations.rs`, `conditional_formatting.rs`,
`hyperlinks_and_names.rs`, `pagesetup.rs`, `comments.rs`, `charts.rs`, `list_objects.rs`,
`pictures.rs`, `shapes.rs`, and `document_properties.rs` (see
[`samples/README.md`](samples/README.md) for the full overview). Generate local API docs
with `cargo doc --no-deps --open`; published API docs are deployed by GitHub Pages
through [`pages.yml`](.github/workflows/pages.yml) — enabling
`Settings -> Pages -> GitHub Actions` on the repository makes pushes to `main`
automatically rebuild and publish the rustdoc site.

## License

This project is licensed under the [MIT License](LICENSE.txt). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
