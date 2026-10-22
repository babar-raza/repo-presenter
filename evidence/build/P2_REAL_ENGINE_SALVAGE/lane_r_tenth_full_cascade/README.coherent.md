# Aspose.Cells FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-cells-foss.svg)](https://pypi.org/project/aspose-cells-foss/) ![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

Aspose.Cells FOSS for Python reads and writes Excel `.xlsx` workbooks, converts workbooks to CSV, JSON, Markdown, and PDF formats, and supports encryption and decryption of `.xlsx` files. It provides classes such as `Workbook`, `Cell`, `Style`, `Font`, `DataValidation`, `auto_filter`, `conditional_format`, `Chart`, `Picture`, `Shape`, `Table`, and `Sparkline` for programmatic workbook manipulation. The library is a free, open-source, pure-Python implementation distributed under the MIT license and requires Python >=3.10.

Aspose.Cells FOSS for Python is a free, open-source, pure-Python library for creating, reading,
modifying, and exporting Excel `.xlsx` workbooks without requiring Microsoft Excel.

## Navigation

- [At a Glance](#at-a-glance)
- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Scope and Limitations](#scope-and-limitations)

## At a Glance

```mermaid
flowchart LR
Start["An existing XLSX file"]
Start --> Product["Aspose.Cells FOSS for Python"]
Product["Aspose.Cells FOSS for Python"] --> Cap1["Read and write .xlsx workbooks"]
Cap2["Cell value and formula handling"]
Cap3["Styling and formatting"]
Cap4["Data validation and conditional features"]
Cap5["Chart and object support"]
Cap6["Export to multiple formats"]
Cap7["Encryption and protection"]
Product["Aspose.Cells FOSS for Python"] --> Cap2["Cell value and formula handling"]
Product["Aspose.Cells FOSS for Python"] --> Cap3["Styling and formatting"]
Product["Aspose.Cells FOSS for Python"] --> Cap4["Data validation and conditional features"]
Product["Aspose.Cells FOSS for Python"] --> Cap5["Chart and object support"]
Product["Aspose.Cells FOSS for Python"] --> Cap6["Export to multiple formats"]
Product["Aspose.Cells FOSS for Python"] --> Cap7["Encryption and protection"]
Cap1["Read and write .xlsx workbooks"] --> Output["XLSX file"]
Cap2["Cell value and formula handling"] --> Output["XLSX file"]
Cap3["Styling and formatting"] --> Output["XLSX file"]
Cap4["Data validation and conditional features"] --> Output["XLSX file"]
Cap5["Chart and object support"] --> Output["XLSX file"]
Cap6["Export to multiple formats"] --> Output["XLSX file"]
Cap7["Encryption and protection"] --> Output["XLSX file"]
```

## Key Capabilities

- **Read and write .xlsx workbooks.** It reads and writes `.xlsx` workbooks using the `aspose.cells_foss.Workbook` class, supporting both loading existing files and saving new ones.
- **Cell value and formula handling.** It handles cell values and formulas through the `aspose.cells_foss.Cell` class, allowing programmatic reading and writing of data and formulas.
- **Styling and formatting.** It applies styling and formatting using the `aspose.cells_foss.Style` and `aspose.cells_foss.Font` classes to modify cell appearance such as bold, color, and size.
- **Data validation and conditional features.** It supports data validation, `auto_filter`, and `conditional_format` features to enforce input rules and apply dynamic formatting based on cell contents.
- **Chart and object support.** It inserts and manages charts, pictures, shapes, sparklines, and tables within worksheets using their respective classes from the `aspose.cells_foss` module.
- **Export to multiple formats.** It exports workbooks to CSV, JSON, Markdown, and PDF formats using dedicated save methods and `PdfSaveOptions` for format-specific configuration.
- **Encryption and protection.** It encrypts and decrypts `.xlsx` files using `StandardEncryptionParameters` or `AgileEncryptionParameters`, and protects or unprotects workbooks with passwords.

## Installation

Install the published package from PyPI (`aspose-cells-foss`, version 26.10.0):

```bash
pip install aspose-cells-foss
```

To work from a source checkout instead, install the clone with pip:

```bash
git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python.git
cd Aspose.Cells-FOSS-for-Python
pip install .
```

Verify the install:

```bash
python -c "import aspose.cells_foss"
```

The package declares `python_requires` as `>=3.10`.

## Dependencies

### Required Package Dependencies

- `olefile>=0.46`
- `pycryptodome>=3.15.0`

### Native and System Requirements

- Requires Python 3.10 or later (`python_requires=">=3.10"` in `pyproject.toml`).

### Development Dependencies

- `pytest>=7.0.0` (extra `dev`)
- `pytest-cov>=4.0.0` (extra `dev`)

## Quick Start

Create a new workbook, populate cells with headers and data, and save it as an Excel file named `report.xlsx`.

```python
from aspose.cells_foss import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]

worksheet.cells["A1"].value = "Product"
worksheet.cells["B1"].value = "Revenue"
worksheet.cells["A2"].value = "Widget"
worksheet.cells["B2"].value = 1250.50

workbook.save("report.xlsx")
```

Open an existing Excel file, access its first worksheet, and print the value stored in cell B2.

```python
from aspose.cells_foss import Workbook

workbook = Workbook("report.xlsx")
worksheet = workbook.worksheets[0]

print(worksheet.cells["B2"].value)
```

## Additional Examples

Create a workbook, apply cell styling, add data validation, and encrypt a workbook with Aspose.Cells FOSS for Python.

### Encrypt a Workbook with a Password and Load It Back

```python
from aspose.cells_foss import Workbook

workbook = Workbook()
workbook.worksheets[0].cells["A1"].value = "Confidential"
workbook.save("protected.xlsx", password="example-password")

loaded = Workbook("protected.xlsx", password="example-password")
print(loaded.worksheets[0].cells["A1"].value)
```

<details>
<summary>View Additional Examples</summary>

### Apply Bold Red Font Styling to a Cell

```python
from aspose.cells_foss import Workbook

workbook = Workbook()
cell = workbook.worksheets[0].cells["A1"]
cell.value = "Quarterly Report"

style = cell.get_style()
style.font.bold = True
style.font.color = "#FF0000"
style.font.size = 14
cell.apply_style(style)

workbook.save("styled.xlsx")
```

### Add a Yes/No List Validation to Cells A1 Through A10

```python
from aspose.cells_foss import DataValidationType, Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]

validation = worksheet.data_validations.add("A1:A10")
validation.type = DataValidationType.LIST
validation.formula1 = '"Yes,No"'

workbook.save("validation.xlsx")
```

</details>

## API Reference

Aspose.Cells FOSS for Python reads and writes `.xlsx` files using the `aspose.cells_foss.Workbook` class, which manages worksheets and provides methods to create, access, and save workbooks. Each workbook contains one or more `aspose.cells_foss.Worksheet` instances, which hold cells organized in `aspose.cells_foss.Cells` collections.

The verified public surface has 160 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `AgileEncryptionParameters` | Parameters for Agile Encryption (ECMA-376 Part 2, Section 4). |
| `CSVHandler` | Handles CSV import and export operations for workbooks. |
| `CSVLoadOptions` | Options for loading CSV files. |
| `CSVSaveOptions` | Options for saving CSV files. |
| `Cell` | Represents a single cell in a worksheet. |
| `Cells` | Represents a collection of cells in a worksheet. |
| `Chart` | Represents a chart in a worksheet. |
| `ChartAxis` | Represents a chart axis (category, value, or series). |
| `ChartCollection` | Collection of charts in a worksheet. |
| `ChartErrorBars` | Represents error bars attached to a chart series. |
| `ChartSeries` | Represents a single chart series. |
| `ChartView3D` | Represents chart-level 3D view settings. |
| `DataValidation` | Represents data validation settings for a range of cells. |
| `DataValidationCollection` | Represents a collection of DataValidation objects for a worksheet. |
| `DisplayValueOptions` | Options controlling display-text formatting. |
| `Font` | Represents font settings for a cell or range of cells. |
| `FontStrategy` | Resolves effective font families and fallback chains for text measurement. |
| `HorizontalPageBreakCollection` | Collection of manual horizontal page breaks (row breaks). |
| `JsonHandler` | Handles JSON export operations for workbooks. |
| `JsonSaveOptions` | Options for saving JSON files. |
| `MarkdownHandler` | Handles Markdown export operations for workbooks. |
| `MarkdownSaveOptions` | Options for saving Markdown files. |
| `MsoFillFormat` | Fill format properties for a shape. |
| `MsoLineFormat` | Border/outline format properties for a shape. |
| `NSeries` | Collection of series for a chart. |
| `NumberFormat` | Represents number format settings for a cell or range of cells. |
| `PdfCellLayout` | PdfCellLayout represents the layout settings for a cell when rendering to PDF. |
| `PdfDataBarLayout` | PdfDataBarLayout represents the layout settings for data bars when rendering to PDF. |
| `PdfExporter` | Connects workbook models to prepared pages and a PDF renderer. |
| `PdfIconSetLayout` | PdfIconSetLayout represents the layout settings for icon sets when rendering to PDF. |
| `PdfLayoutEngine` | Materializes all worksheet pages before the renderer starts drawing. |
| `PdfPageLayout` | PdfPageLayout represents the page layout settings when rendering to PDF. |
| `PdfSaveOptions` | Controls worksheet selection and basic PDF rendering behavior. |
| `PdfTextRunLayout` | PdfTextRunLayout represents the layout settings for a text run when rendering to PDF. |
| `Picture` | Represents a worksheet picture anchored to cells. |
| `PictureCollection` | Collection of pictures in a worksheet. |
| `RenderBounds` | A 1-based, inclusive rectangular range in worksheet coordinates. |
| `RichTextRun` | One formatted text run from an OOXML shared string. |
| `RowHeightCalculator` | Computes effective row heights without mutating the worksheet. |
| `Shape` | Represents a drawing shape (rectangle, oval, text box, arrow, etc.) on |
| `ShapeCollection` | Collection of Shape objects on a worksheet. |
| `ShapeFont` | Font properties for text inside a shape. |
| `SkiaPdfRenderer` | Draws materialized page layouts without owning layout or pagination. |
| `Sparkline` | One sparkline: a data source range paired with the cell where it appears. |
| `SparklineGroup` | A group of sparklines that share the same visual style. |
| `SparklineGroupCollection` | Collection of SparklineGroup objects (ws.sparkline_groups). |
| `StandardEncryptionParameters` | Parameters for Standard Encryption (ECMA-376 Part 2, Section 3). |
| `Style` | Represents formatting settings for a cell or range of cells. |
| `StyleResolver` | Resolves the effective visual style for worksheet cells. |
| `Table` | Represents an Excel structured table (ECMA-376 §18.5). |
| `TableCollection` | Collection of Table objects belonging to a worksheet (ws.tables). |
| `TableColumn` | Settings for a single table column. |
| `TableStyleInfo` | Visual style settings for an Excel table. |
| `TextMeasurer` | Backend-neutral text measurement service used by layout and rendering. |
| `ValueFormatter` | Formats cells or raw values into display text. |
| `VerticalPageBreakCollection` | Collection of manual vertical page breaks (column breaks). |
| `Workbook` | Represents an Excel workbook. |
| `Worksheet` | Represents a single worksheet in an Excel workbook. |
| `WorksheetBoundsResolver` | Resolve live worksheet bounds without relying on cached XLSX dimensions. |
| `AutoFilter` | Represents auto filters in a worksheet. |
| `FilterColumn` | Represents a filter column in an auto filter. |
| `CellValueHandler` | Handles cell value import and export operations according to ECMA-376 specification. |
| `CFBReader` | Reads encrypted XLSX from CFB format. |
| `cfb_handler.CFBWriter` | Writes encrypted XLSX to CFB format. |
| `cfb_writer.CFBWriter` | Writes CFB (Compound File Binary) files according to MS-CFB specification. |
| `MinimalCFBWriter` | Minimal CFB file writer for encrypted Office documents. |
| `CommentXMLReader` | Handles reading comment data from XML format. |
| `CommentXMLWriter` | Handles writing comment data to XML format. |
| `ConditionalFormat` | Represents a single conditional formatting rule applied to a cell range. |
| `ConditionalFormatCollection` | Represents a collection of conditional formats for a worksheet. |
| `CoreProperties` | Represents core document properties stored in docProps/core.xml. |
| `DocumentProperties` | Container for all document-level properties. |
| `ExtendedProperties` | Represents extended/application properties stored in docProps/app.xml. |
| `EncryptionVerifier` | Encryption verifier generation and validation. |
| `PackageEncryption` | Package data encryption and decryption. |
| `PasswordDerivation` | Password derivation helpers for Agile encryption. |
| `EncryptionParameters` | Base class for encryption parameters. |
| `FormulaEvaluator` | Basic formula evaluator for XLSX cells without cached values. |
| `Hyperlink` | Represents a hyperlink in a worksheet. |
| `Hyperlinks` | Collection of hyperlinks in a worksheet. |
| `PdfChartLayout` | PdfChartLayout represents the layout settings for a chart when rendering to PDF. |
| `PdfChartSeriesLayout` | PdfChartSeriesLayout represents the layout settings for a chart series when rendering to PDF. |
| `PdfPictureLayout` | PdfPictureLayout represents the layout settings for a picture when rendering to PDF. |
| `PdfShapeLayout` | PdfShapeLayout represents the layout settings for a shape when rendering to PDF. |
| `PdfSparklineLayout` | PdfSparklineLayout represents the layout settings for a sparkline when rendering to PDF. |
| `PdfRenderer3DAreaMixin` | PdfRenderer3DAreaMixin provides rendering capabilities for 3D area charts in PDF output. |
| `PdfRenderer3DBarMixin` | PdfRenderer3DBarMixin provides rendering capabilities for 3D bar charts in PDF output. |
| `PdfRenderer3DLineColumnMixin` | PdfRenderer3DLineColumnMixin provides rendering capabilities for 3D line and column charts in PDF output. |
| `PdfRendererDrawingMixin` | PdfRendererDrawingMixin provides rendering capabilities for drawing objects in PDF output. |
| `PdfRendererPieBarMixin` | PdfRendererPieBarMixin provides rendering capabilities for pie and bar charts in PDF output. |
| `PdfRendererSpecialChartsMixin` | PdfRendererSpecialChartsMixin provides rendering capabilities for special charts in PDF output. |
| `PdfRendererStockSurfaceMixin` | PdfRendererStockSurfaceMixin provides rendering capabilities for stock and surface charts in PDF output. |
| `SharedStringTable` | Manages the Shared String Table for XLSX files according to ECMA-376 specification. |
| `Alignment` | Represents alignment settings for a cell or range of cells. |
| `Border` | Represents border settings for a single side of a cell or range of cells. |
| `Borders` | Represents border settings for all sides of a cell or range of cells. |
| `Fill` | Represents fill settings for a cell or range of cells. |
| `Protection` | Represents protection settings for a cell or range of cells. |
| `CalculationProperties` | Represents calculation properties for the workbook. |
| `DefinedName` | Represents a defined name in the workbook. |
| `DefinedNameCollection` | Collection of defined names in the workbook. |
| `FileVersion` | Represents file version information for the workbook. |
| `WorkbookPr` | Represents workbook properties (workbookPr element). |
| `WorkbookProperties` | Container for all workbook-level properties. |
| `WorkbookProtection` | Represents workbook protection settings. |
| `WorkbookView` | Represents a workbook view configuration. |
| `SheetProtectionDictWrapper` | Dictionary-like wrapper around SheetProtection for backward compatibility. |
| `HeaderFooter` | Represents header and footer settings. |
| `PageMargins` | Represents page margins. |
| `PageSetup` | Represents page setup settings. |
| `Pane` | Represents pane (freeze/split) settings. |
| `PrintOptions` | Represents print options. |
| `Selection` | Represents cell selection in a sheet view. |
| `SheetFormatProperties` | Represents sheet format properties. |
| `SheetProtection` | Represents sheet protection settings. |
| `SheetView` | Represents a sheet view configuration. |
| `WorksheetProperties` | Container for all worksheet-level properties. |
| `XLSXDecryptor` | Handles decryption of XLSX files. |
| `XLSXEncryptor` | Handles encryption of XLSX files. |
| `AutoFilterXMLLoader` | Handles loading autofilter data from XML format for .xlsx files. |
| `AutoFilterXMLWriter` | Handles writing autofilter data to XML format for .xlsx files. |
| `ChartXmlLoader` | Loads worksheet chart settings from drawing/chart XML parts. |
| `ChartXmlSaver` | Handles writing chart-related XLSX parts: |
| `ConditionalFormatXMLLoader` | Handles loading conditional formatting data from XML format for .xlsx files. |
| `ConditionalFormatXMLWriter` | Handles writing conditional formatting data to XML format for .xlsx files. |
| `DataValidationXmlLoader` | Loads DataValidation objects from ECMA-376 SpreadsheetML XML format. |
| `DataValidationXmlSaver` | Saves DataValidation objects to ECMA-376 SpreadsheetML XML format. |
| `HyperlinkRelationshipWriter` | Writes hyperlink relationships to _rels files. |
| `HyperlinkXMLLoader` | Loads hyperlinks from worksheet XML and relationship files. |
| `HyperlinkXMLSaver` | Saves hyperlinks to worksheet XML and relationship files. |
| `XMLLoader` | Handles loading of Excel workbook XML files. |
| `PictureXmlLoader` | Loads pictures from worksheet drawing parts. |
| `PictureXmlSaver` | Handles writing picture-related drawing/media XML payloads. |
| `WorkbookPropertiesXMLLoader` | Handles loading workbook properties from XML format for .xlsx files. |
| `WorksheetPropertiesXMLLoader` | Handles loading worksheet properties from XML format for .xlsx files. |
| `WorkbookPropertiesXMLWriter` | Handles writing workbook properties to XML format for .xlsx files. |
| `WorksheetPropertiesXMLWriter` | Handles writing worksheet properties to XML format for .xlsx files. |
| `XMLSaver` | Handles saving workbook data to XML format for .xlsx files. |
| `ShapeXmlLoader` | Loads xdr:sp shape elements from a drawing XML part. |
| `ShapeXmlSaver` | Generates drawing XML and relationship XML for worksheet shapes. |
| `SparklineXmlLoader` | Loads sparkline group data from the <extLst> in a worksheet XML root. |
| `SparklineXmlSaver` | Serialises SparklineGroupCollection to <extLst> XML. |
| `TableXmlLoader` | Loads table definitions from an XLSX ZIP archive into a worksheet. |
| `TableXmlSaver` | Serialises Table objects to ECMA-376 table XML. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `ChartType` | Supported chart types. |
| `CipherAlgorithm` | Cipher algorithm enumeration. |
| `DataValidationAlertStyle` | Specifies the style of the error alert displayed when invalid data is entered. |
| `DataValidationImeMode` | Specifies the Input Method Editor (IME) mode for CJK language input. |
| `DataValidationOperator` | Specifies the comparison operator for data validation. |
| `DataValidationType` | Specifies the type of data validation. |
| `FillType` | Shape fill type (ECMA-376 a:spPr fill child elements). |
| `HashAlgorithm` | Hash algorithm enumeration. |
| `MsoDrawingType` | Shape preset geometry types (maps to ECMA-376 a:prstGeom prst attributes). |
| `MsoLineDashStyle` | Shape border/line dash style (ECMA-376 a:prstDash val attribute). |
| `SaveFormat` | Specifies the format for saving a workbook. |
| `SparklineEmptyCells` | SparklineEmptyCells specifies how empty cells are handled in sparklines. |
| `SparklineType` | SparklineType specifies the type of a sparkline. |
| `TextAlignmentType` | Horizontal text alignment inside a shape (ECMA-376 a:pPr algn attribute). |
| `TextAnchorType` | Vertical text anchor inside a shape (ECMA-376 a:bodyPr anchor attribute). |
| `EncryptionType` | Encryption type enumeration. |

#### Detailed Member Reference

### Workbook

The `aspose.cells_foss.Workbook` class represents a spreadsheet file and provides methods such as `add_worksheet`, `get_worksheet`, save, and `load_csv` to manage its content and structure.

- `add_worksheet`: Adds a new worksheet to the workbook.
- `copy_worksheet`: Copy a worksheet and append the copy to the workbook. Returns the new worksheet.
- `create_worksheet`: Create and add a new worksheet. Alias for add_worksheet().
- `document_properties`: Gets document properties of the workbook.
- `file_path`: Gets the file path of the workbook.
- `font_strategy`: Shared font resolution strategy used by layout and rendering.
- `get_active_worksheet`: Return the currently active worksheet.
- `get_worksheet`: Gets a worksheet by index or name.
- `get_worksheet_by_index`: Return the worksheet at the given 0-based index, or None if out of range.
- `get_worksheet_by_name`: Return the worksheet with the given name, or None if not found.
- `is_protected`: Return True if the workbook has structure or window protection enabled.
- `load_csv`: Loads data from a CSV file into the workbook.
- `properties`: Gets workbook properties.
- `protect`: Protect the workbook structure/windows with an optional password.
- `protection`: Return a dict with the current workbook protection settings.
- `remove_worksheet`: Removes a worksheet from the workbook.
- `save`: Saves the workbook to a file.
- `save_as_csv`: Saves the workbook to a CSV file.
- `save_as_json`: Saves the workbook to a JSON file.
- `save_as_markdown`: Saves the workbook to a Markdown file.
- `save_as_pdf`: Save visible worksheets to PDF using prepared page layouts.
- `set_active_worksheet`: Set the active worksheet by index, name, or Worksheet object.
- `set_font_fallbacks`: Sets workbook-wide fallback font families in priority order.
- `text_measurer`: Shared text measurement service used by layout and rendering.
- `unprotect`: Remove workbook structure/window protection.
- `worksheets`: Gets collection of worksheets in the workbook.

### Worksheet

The `aspose.cells_foss.Worksheet` class represents a single worksheet within a workbook and exposes its cells through the `aspose.cells_foss.Cells` collection, along with properties and methods for formatting, protection, and print settings.

- `activate`: Activates the worksheet (makes it the active worksheet).
- `auto_filter`: Gets the AutoFilter object for this worksheet.
- `calculate_formula`: Calculates formulas in the worksheet.
- `calculate_row_heights`: Return layout-time row heights in points without changing the worksheet.
- `cells`: Gets the Cells collection for this worksheet.
- `charts`: Gets the collection of charts for this worksheet.
- `clear_print_area`: Clears the worksheet print area.
- `clear_print_titles`: Clear repeated rows and columns.
- `clear_tab_color`: Clear the worksheet tab color.
- `conditional_formats`: Gets the collection of conditional formats for this worksheet.
- `copy`: Creates a copy of the worksheet.
- `data_validations`: Gets the collection of data validations for this worksheet.
- `delete`: Deletes the worksheet from the workbook.
- `get_content_bounds`: Return bounds of live renderable content, or None for an empty sheet.
- `get_effective_default_row_height`: Return the workbook-font-derived default row height unless the sheet marks
- `get_effective_style`: Returns the resolved visual style for a cell.
- `get_page_margins`: Return a copy of the page margins dict.
- `get_page_orientation`: Return the page orientation ('portrait', 'landscape', or None).
- `get_paper_size`: Return the paper size integer code.
- `get_print_title_ranges`: Return 1-based inclusive row/column tuples for pagination.
- `get_printable_bounds`: Return printable areas, preserving discontiguous explicit print areas.
- `get_range`: Gets a range of cells.
- `get_render_bounds`: Return the final printable envelope consumed by layout and pagination.
- `get_tab_color`: Return the worksheet tab color (8-char AARRGGBB hex) or None.
- `get_visibility`: Return current worksheet visibility (True, False, or 'veryHidden').
- `horizontal_page_breaks`: Gets manual horizontal page break collection.
- `hyperlinks`: Gets the collection of hyperlinks for this worksheet.
- `is_protected`: Checks if the worksheet is protected.
- `measure_cell_text`: Measure a cell's display text using its resolved effective style.
- `measure_text`: Measure text using the workbook's shared font strategy when available.
- `merged_cells`: Gets merged cell ranges in A1 notation.
- `move`: Moves the worksheet to the specified position in the workbook.
- `name`: Gets or sets the name of the worksheet.
- `page_margins`: Gets the page margins for this worksheet.
- `page_setup`: Gets the page setup settings for this worksheet.
- `pictures`: Gets the collection of pictures for this worksheet.
- `print_area`: Gets or sets print area in A1 notation.
- `print_title_columns`: Columns repeated at the left of each printed page, such as A:C.
- `print_title_rows`: Rows repeated at the top of each printed page, such as 1:3.
- `properties`: Gets the worksheet properties.
- `protect`: Protects the worksheet with optional password and protection options.
- `protection`: Gets the protection settings for this worksheet.
- `rename`: Renames the worksheet.
- `select`: Selects the worksheet.
- `set_fit_to_pages`: Set fit-to-pages: width and height are page counts (0 = auto).
- `set_page_margins`: Set page margins (in inches). Only provided values are updated.
- `set_page_orientation`: Set page orientation. orientation must be 'portrait' or 'landscape'.
- `set_paper_size`: Set the paper size (integer code, e.g. 9 = A4).
- `set_print_area`: Sets the worksheet print area.
- `set_print_scale`: Set print scale percentage (10–400).
- `set_print_titles`: Set repeated print-title rows and columns; None clears an axis.
- `set_tab_color`: Set the worksheet tab color. color must be an 8-char AARRGGBB hex string.
- `set_view`: Sets view options for the worksheet.
- `set_visibility`: Set worksheet visibility. Accepts True, False, or 'veryHidden'.
- `shapes`: Gets the collection of drawing shapes for this worksheet.
- `sparkline_groups`: Gets the collection of sparkline groups for this worksheet.
- `tab_color`: Gets or sets the tab color of the worksheet.
- `tables`: Gets the collection of structured tables (ListObjects) for this worksheet.
- `unprotect`: Unprotects the worksheet.
- `vertical_page_breaks`: Gets manual vertical page break collection.
- `visible`: Gets or sets the visibility state of the worksheet.

### Cell

The `aspose.cells_foss.Cell` class represents an individual cell in a worksheet and allows setting and getting its value, formula, and style through methods such as `get_style` and `apply_style`.

- `apply_style`: Applies a style to the cell.
- `clear`: Clears both the value and formula of the cell.
- `clear_comment`: Clears the comment from the cell.
- `clear_formula`: Clears the formula of the cell (sets it to None).
- `clear_style`: Clears the style of the cell (resets to default).
- `clear_value`: Clears the value of the cell (sets it to None).
- `comment`: Gets the comment associated with the cell.
- `data_type`: Gets the data type of the cell value.
- `formula`: Gets or sets the formula of the cell.
- `get_comment`: Gets the comment from the cell.
- `get_comment_size`: Gets the size of the comment box.
- `get_display_text`: Returns the cell's visible display text using Excel-like formatting rules.
- `get_effective_style`: Returns the effective visual style for this cell.
- `get_style`: Gets the style of the cell.
- `has_comment`: Checks if the cell has a comment.
- `has_formula`: Checks if the cell has a formula.
- `is_boolean_value`: Checks if the cell value is boolean.
- `is_date_time_value`: Checks if the cell value is a date/time.
- `is_empty`: Checks if the cell is empty.
- `is_numeric_value`: Checks if the cell value is numeric.
- `is_text_value`: Checks if the cell value is text.
- `put_value`: Sets the value of the cell. Alias for the value setter, provided for
- `rich_text_runs`: Returns the formatted runs loaded for this cell's rich text.
- `set_comment`: Sets a comment on the cell.
- `set_comment_size`: Sets the size of the comment box.
- `style`: Gets or sets the style of the cell.
- `value`: Gets or sets the value of the cell.

### Style

The `aspose.cells_foss.Style` class defines formatting attributes such as font bold, font color, and font size, which can be applied to a cell using the `apply_style` method.

- `copy`: Creates a deep copy of this Style object.
- `set_border`: Sets complete border properties for a specific side.
- `set_border_color`: Sets the border color for a specific side.
- `set_border_style`: Sets the border line style for a specific side.
- `set_border_weight`: Sets the border line weight for a specific side.
- `set_builtin_number_format`: Sets the number format using a built-in format ID.
- `set_diagonal_border`: Sets diagonal border properties.
- `set_fill_color`: Sets the cell fill color using a solid fill pattern.
- `set_fill_pattern`: Sets the cell fill pattern and colors.
- `set_formula_hidden`: Sets whether the cell's formula is hidden when the worksheet is protected.
- `set_horizontal_alignment`: Sets the horizontal alignment of cell content.
- `set_indent`: Sets the indent level for cell content.
- `set_locked`: Sets whether the cell is locked when the worksheet is protected.
- `set_no_fill`: Removes the cell fill (transparent background).
- `set_number_format`: Sets the number format code for the cell.
- `set_reading_order`: Sets the reading order for cell content.
- `set_shrink_to_fit`: Sets whether text shrinks to fit the cell width.
- `set_text_rotation`: Sets the text rotation angle.
- `set_text_wrap`: Sets whether text wraps within the cell.
- `set_vertical_alignment`: Sets the vertical alignment of cell content.

### DataValidation

The `aspose.cells_foss.DataValidation` class enforces input rules on a range of cells, and the `aspose.cells_foss.DataValidationCollection` provides the add method to create and manage such validations on a worksheet.

- `add`: Configures the data validation with the specified parameters.
- `alert_style`: Gets or sets the style of the error alert.
- `allow_blank`: Gets or sets whether blank/empty entries are valid.
- `copy`: Creates a copy of this DataValidation.
- `delete`: Clears the validation settings (resets to no validation).
- `error`: Alias for error_message (ECMA-376 compatibility).
- `error_message`: Gets or sets the error message displayed when invalid data is entered.
- `error_title`: Gets or sets the title of the error alert dialog.
- `formula1`: Gets or sets the first formula for validation.
- `formula2`: Gets or sets the second formula for validation.
- `ignore_blank`: Alias for allow_blank (Excel VBA compatibility).
- `ime_mode`: Gets or sets the IME (Input Method Editor) mode.
- `in_cell_dropdown`: Alias for show_dropdown (Excel VBA compatibility).
- `input_message`: Gets or sets the input message displayed when the cell is selected.
- `input_title`: Gets or sets the title of the input message dialog.
- `modify`: Modifies the data validation settings.
- `operator`: Gets or sets the comparison operator.
- `prompt`: Alias for input_message (ECMA-376 compatibility).
- `prompt_title`: Alias for input_title (ECMA-376 compatibility).
- `ranges`: Gets the cell range(s) as a list.
- `show_dropdown`: Gets or sets whether to show the dropdown arrow for list validation.
- `show_error`: Alias for show_error_message (Excel VBA compatibility).
- `show_error_message`: Gets or sets whether to show the error alert when invalid data is entered.
- `show_input`: Alias for show_input_message (Excel VBA compatibility).
- `show_input_message`: Gets or sets whether to show the input message when the cell is selected.
- `sqref`: Gets or sets the cell range(s) for this validation.
- `type`: Gets or sets the validation type.

### Chart

The `aspose.cells_foss.Chart` class represents a chart object on a worksheet, and the `aspose.cells_foss.ChartCollection` provides methods to add and manage charts, with `aspose.cells_foss.ChartSeries` defining the data series for a chart.

- `NSeries`: PascalCase alias of n_series.
- `View3D`: PascalCase alias of view_3d.
- `add_axis`: Adds an axis to the chart and returns it.
- `add_series`: Convenience method to add a series.
- `axes`: List of ChartAxis objects defining all axes for the chart.
- `histogram_bin_count`: Number of bins for count-based binning (int or None for auto/size-based).
- `histogram_bin_size`: Bin width for size-based binning (float or None for auto/count-based).
- `histogram_interval_closed`: Which side of each bin interval is closed: 'r' (right) or 'l' (left).
- `histogram_overflow`: Overflow bin boundary value (float or None).
- `histogram_underflow`: Underflow bin boundary value (float or None).
- `radar_style`: Radar chart style: 'standard', 'marker', or 'filled'.
- `sub_charts`: List of sub-chart descriptors for combo charts.
- `wireframe`: Whether the surface chart uses wireframe display mode (<c:wireframe val='1'/>).

### SaveFormat

The `aspose.cells_foss.SaveFormat` class enumerates output formats, and the methods `aspose.cells_foss.save_workbook_as_csv`, `aspose.cells_foss.save_workbook_as_json`, and `aspose.cells_foss.save_workbook_as_markdown` allow saving a workbook in those formats.

- `from_extension`: Determines the save format from file extension.

### PdfSaveOptions

The `aspose.cells_foss.PdfSaveOptions` class configures options for saving a workbook as PDF, and the `aspose.cells_foss.SkiaPdfRenderer` class provides the rendering engine for PDF output.

- `min_scale`: Smallest allowed page scale as a fraction, defaulting to 0.1.
- `page_size`: Optional (width, height) override in PDF points.
- `worksheet_indices`: Optional sequence of zero-based worksheet indexes to export.

### encrypt_xlsx

The `aspose.cells_foss.encrypt_xlsx` method and the `aspose.cells_foss.decrypt_xlsx` method allow saving and loading password-protected `.xlsx` files, as demonstrated by providing a password when creating or opening a workbook.

### workbook_hash_password

The `aspose.cells_foss.workbook_hash_password` method supports password hashing for workbook encryption, and the `aspose.cells_foss.StandardEncryptionParameters` and `aspose.cells_foss.AgileEncryptionParameters` classes define encryption parameter sets.

### Table

The `aspose.cells_foss.Table` class represents a table object on a worksheet, and the `aspose.cells_foss.TableCollection` provides methods to add and manage tables within a worksheet.

### Sparkline

The `aspose.cells_foss.Sparkline` class represents a sparkline graphic, and the `aspose.cells_foss.SparklineGroup` class groups sparklines together, with methods available to manage their creation and layout.

</details>

## Scope and Limitations

Aspose.Cells FOSS for Python reads and writes Excel workbooks in the Open XML `.xlsx` format, preserving formula expressions and cached results without acting as a full Excel calculation engine.

- PDF export uses the optional `aspose.cells_foss.SkiaPdfRenderer`, which is not installed by the core package and must be installed separately.
- Native workbook loading and saving targets the Open XML `.xlsx` format; other spreadsheet formats such as .xls, .ods, and .xlsb are not supported, and some advanced Excel features are preserved as source package parts rather than exposed as editable Python objects.
- XML loading and saving are provided by `aspose.cells_foss.xml_loader` and `aspose.cells_foss.xml_saver`, but the project does not implement a full Excel calculation engine and preserves some advanced features as source package parts.
- PDF output depends on locally available fonts and the optional `aspose.cells_foss.SkiaPdfRenderer`.
