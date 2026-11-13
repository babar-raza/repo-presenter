# Aspose.Words FOSS for .NET

[![NuGet](https://img.shields.io/nuget/v/Aspose.Words.FOSS.svg)](https://www.nuget.org/packages/Aspose.Words.FOSS/) ![.NET](https://img.shields.io/badge/.net-netstandard2.0_%7C_net8.0_%7C_net462-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[![Aspose.Words FOSS for .NET](https://products.aspose.org/media/words/net/banner-readme.png)](https://products.aspose.org/words/net/)

Aspose.Words FOSS for .NET reads and writes DOCX, DOCM, DOTX, DOTM, Flat OPC, Markdown, and plain TEXT formats using `Aspose.Words.LoadFormat` and `Aspose.Words.SaveFormat`. It processes tracked changes with `Aspose.Words.Revision`, bookmarks with `Aspose.Words.Bookmark`, and table styles with `Aspose.Words.TableStyle`. The library provides a document model based on `Aspose.Words.Document`, `Aspose.Words.DocumentBuilder`, and related types for programmatic document creation and modification.

Most open-source Word libraries start from zero and work their way up the OOXML spec. This one went the other way. It is not a rewrite or a wrapper: it is the actual Aspose.Words for .NET source code, the same document engine that has processed Word documents in production since 2003.

Aspose.Words has been in continuous development for over two decades, and it is older than DOCX itself. The library began with manual reverse engineering of the binary DOC format, at a time when no public specification existed. Then came WordML, the Word 2003 XML dialect, then OOXML when Word 2007 arrived, and one format after another in the years since. To create this FOSS edition, we started from the full commercial source and carefully reduced it: the commercial subsystems (page layout, rendering, the long tail of format converters, and the licensing machinery) were removed, along with internal infrastructure and materials not meant for publication. What remains is the genuine core: the document model, the DOCX reader and writer, and thousands of small fixes for real-world documents that only accumulate after twenty years of production use.

The reduction itself was an interesting engineering project. To carry it out, we built an internal tool, the Full2Foss agent, developed with the help of [Claude](https://claude.com), Anthropic's AI assistant. Full2Foss traces which subsystems each piece of code depends on, cuts what has to go, and keeps thousands of tests honest along the way.

That is also why the source is worth a read. This is production code, not a demonstration. If you have ever wondered what it actually takes to handle Word documents correctly, it is all in here.

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
Product["Aspose.Words FOSS for .NET"]
Product["Aspose.Words FOSS for .NET"] --> Cap1["Create and edit documents"]
Cap2["Format and style content"]
Cap3["Convert document formats"]
Cap4["Process tracked changes"]
Cap5["Merge and combine documents"]
Cap6["Inspect and modify charts"]
Cap7["Verify digital signatures"]
Cap8["Protect documents"]
Product["Aspose.Words FOSS for .NET"] --> Cap2["Format and style content"]
Product["Aspose.Words FOSS for .NET"] --> Cap3["Convert document formats"]
Product["Aspose.Words FOSS for .NET"] --> Cap4["Process tracked changes"]
Product["Aspose.Words FOSS for .NET"] --> Cap5["Merge and combine documents"]
Product["Aspose.Words FOSS for .NET"] --> Cap6["Inspect and modify charts"]
Product["Aspose.Words FOSS for .NET"] --> Cap7["Verify digital signatures"]
Product["Aspose.Words FOSS for .NET"] --> Cap8["Protect documents"]
```

## Key Capabilities

- **Create and edit documents.** Create documents from scratch using the full document object model or the high-level `DocumentBuilder`, and edit existing DOCX files including TEXT, formatting, styles, tables, lists, sections, headers and footers, bookmarks, comments, footnotes, and shapes.
- **Format and style content.** Format and style content using `ParagraphFormat`, `Style`, `PageSetup`, `Border`, and `Shading` to control paragraph properties, character and paragraph styles, page layout, borders, and shading effects.
- **Convert document formats.** Convert documents between DOCX, Markdown, and plain TEXT using `SaveFormat` and `LoadFormat` to read and write files in these formats.
- **Process tracked changes.** Process tracked changes by inspecting, accepting, or rejecting revisions through the `Revision` and `RevisionCollection` classes.
- **Merge and combine documents.** Merge and combine documents by appending, cloning, and importing content between documents using `ImportFormatMode` and `Node` operations.
- **Inspect and modify charts.** Inspect and modify embedded charts by accessing series values, axes, legend, and data-label formatting through `Chart`, `ChartSeries`, `ChartAxis`, and `ChartDataLabel`; chart data round-trips intact.
- **Verify digital signatures.** Verify digital signatures by checking whether a DOCX is signed and untampered, inspecting the certificates, or removing signatures using `DigitalSignatures`.
- **Protect documents.** Protect documents using `ProtectionType` to apply different protection modes and round-trip macro-enabled files with their VBA projects intact using Vba.

- **Find and replace** text with regular expressions and formatting-aware options.
- **Update fields**: the full field evaluation engine is included, though values that depend on page layout (such as page numbers in a TOC) come out as placeholders (see what's not included).

The library is managed C# shipping three targets — **.NET Framework 4.6.2, .NET Standard 2.0, and .NET 8** — so it runs on .NET Framework 4.6.2+, .NET 6/8/10, Windows, Linux, and macOS. No Office automation. On .NET Framework image handling uses the in-box GDI+; on the cross-platform targets it uses [SkiaSharp](https://github.com/mono/SkiaSharp) (on Linux, also add the [SkiaSharp.NativeAssets.Linux](https://www.nuget.org/packages/SkiaSharp.NativeAssets.Linux) package).

## Installation

Install the published package from NuGet (`Aspose.Words.FOSS`, version 26.3.0):

```bash
dotnet add package Aspose.Words.FOSS
```

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `Aspose.Words/Aspose.Words.csproj`, no `PackageReference` a consumer would install is declared.

### Native and System Requirements

- Requires .NET `netstandard2.0;net8.0;net462` (`TargetFrameworks` in `Aspose.Words/Aspose.Words.csproj`).

### Development Dependencies

- `ILRepack 2.0.46`

## Quick Start

```csharp
using Aspose.Words;

// Create a document from scratch.
Document doc = new Document();
DocumentBuilder builder = new DocumentBuilder(doc);

builder.ParagraphFormat.StyleIdentifier = StyleIdentifier.Heading1;
builder.Writeln("Hello from Aspose.Words FOSS!");

builder.ParagraphFormat.StyleIdentifier = StyleIdentifier.BodyText;
builder.Writeln("This document was created entirely in code, no Word installed.");

doc.Save("Hello.docx");

// Convert an existing document to Markdown.
Document report = new Document("Report.docx");
report.Save("Report.md");
```

## Additional Examples

```csharp
using Aspose.Words;

Document doc = new Document("reviewed.docx");
doc.AcceptAllRevisions();
doc.Save("final.docx");
```

<details>
<summary>View Additional Examples</summary>

```csharp
using Aspose.Words;

Document main = new Document("main.docx");
Document appendix = new Document("appendix.docx");
main.AppendDocument(appendix, ImportFormatMode.KeepSourceFormatting);
main.Save("combined.docx");
```

```csharp
using Aspose.Words;

Document doc = new Document("notes.md");
doc.Save("notes.docx");
```

```csharp
using Aspose.Words;
using Aspose.Words.Drawing.Charts;

Chart chart = doc.FirstSection.Body.Shapes[0].Chart;
ChartSeries series = chart.Series[0];

series.HasDataLabels = true;
series.DataLabels.ShowValue = true;

ChartDataLabel label = series.DataLabels[1];
label.ShowCategoryName = true;
label.Position = ChartDataLabelPosition.Below;

doc.Save("chart-updated.docx");
```

</details>

## API Reference

Aspose.Words FOSS for .NET provides the `Document` class as the primary entry point for loading, creating, and manipulating documents, with `DocumentBuilder` offering a cursor-based approach to insert content. The `Document` class supports operations such as appending documents, accepting revisions, and saving to various formats.

The verified public surface has 618 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `AbsolutePositionTab` | An absolute position tab is a character which is used to advance the position on the current line of TEXT when displaying this WordprocessingML content. |
| `Bibliography` | Represents the list of bibliography sources available in the document. |
| `Contributor` | Represents a bibliography source contributor. |
| `ContributorCollection` | Represents bibliography source contributors. |
| `Corporate` | Represents a corporate (an organization) bibliography source contributor. |
| `Person` | Represents individual (a person) bibliography source contributor. |
| `PersonCollection` | Represents a list of persons who are bibliography source contributors. |
| `Source` | Represents an individual source, such as a book, journal article, or interview. |
| `Body` | Represents a container for the main TEXT of a section. |
| `Bookmark` | Represents a single bookmark. |
| `BookmarkCollection` | A collection of Bookmark objects that represent the bookmarks in the specified range. |
| `BookmarkEnd` | Represents an end of a bookmark in a Word document. |
| `BookmarkStart` | Represents a start of a bookmark in a Word document. |
| `Border` | Represents a border of an object. |
| `BorderCollection` | A collection of Border objects. |
| `BuildVersionInfo` | Provides information about the current product name and version. |
| `BuildingBlock` | Aspose.Words.BuildingBlocks.BuildingBlock is a public symbol with members Accept, AcceptEnd, AcceptStart, AppendChild, Behavior, BuildingBlock, Category, and Clone, and its Remove method throws InvalidOperationException conditionally. |
| `BuildingBlockCollection` | A collection of BuildingBlock objects in the document. |
| `GlossaryDocument` | Represents the root element for a glossary document within a Word document. |
| `CleanupOptions` | Allows to specify options for document cleaning. |
| `Comment` | Represents a container for TEXT of a comment. |
| `CommentCollection` | Provides typed access to a collection of Comment nodes. |
| `CommentRangeEnd` | Denotes the end of a region of TEXT that has a comment associated with it. |
| `CommentRangeStart` | Denotes the start of a region of TEXT that has a comment associated with it. |
| `CompositeNode` | Base class for nodes that can contain other nodes. |
| `ConditionalStyle` | Represents special formatting applied to some area of a table with assigned table style. |
| `ConditionalStyleCollection` | Represents a collection of ConditionalStyle objects. |
| `ControlChar` | Control characters often encountered in documents. |
| `ConvertUtil` | Provides helper functions to convert between various measurement units. |
| `CertificateHolder` | Represents a holder of X509Certificate2 instance. |
| `DigitalSignature` | Represents a digital signature on a document and the result of its verification. |
| `DigitalSignatureCollection` | Provides a read-only collection of digital signatures attached to a document. |
| `DigitalSignatureUtil` | Provides methods for signing document. |
| `SignOptions` | Allows to specify options for document signing. |
| `Document` | Aspose.Words.Document is a public symbol with members Accept, AcceptAllRevisions, AcceptEnd, AcceptStart, AppendChild, AppendDocument, AttachedTemplate, and AutomaticallyUpdateStyles, and its BackgroundShape setter throws ArgumentException conditionally, its DefaultTabStop setter throws ArgumentOutOfRangeException conditionally, and its Remove method throws InvalidOperationException conditionally. |
| `DocumentBase` | Provides the abstract base class for a main document and a glossary document of a Word document. |
| `DocumentBuilder` | Provides methods to insert TEXT, images and other content, specify font, paragraph and section formatting. |
| `DocumentBuilderOptions` | Allows to specify additional options for the document building process. |
| `DocumentReaderPluginLoadException` | Thrown during document load, when the plugin required for reading the document format cannot be loaded. |
| `DocumentVisitor` | Base class for custom document visitors. |
| `Adjustment` | Represents adjustment values that are applied to the specified shape. |
| `AdjustmentCollection` | Represents a read-only collection of Adjustment adjust values that are applied to the specified shape. |
| `AxisBound` | Represents minimum or maximum bound of axis values. |
| `AxisDisplayUnit` | Provides access to the scaling options of the display units for the value axis. |
| `AxisScaling` | Represents the scaling options of the axis. |
| `AxisTickLabels` | Represents properties of axis tick mark labels. |
| `BubbleSizeCollection` | Represents a collection of bubble sizes for a chart series. |
| `Chart` | Provides access to the chart shape properties. |
| `ChartAxis` | Represents the axis options of the chart. |
| `ChartAxisCollection` | Represents a collection of chart axes. |
| `ChartAxisTitle` | Provides access to the axis title properties. |
| `ChartDataLabel` | Represents data label on a chart point or trendline. |
| `ChartDataLabelCollection` | Represents a collection of ChartDataLabel. |
| `ChartDataPoint` | Allows to specify formatting of a single data point on the chart. |
| `ChartDataPointCollection` | Represents collection of a ChartDataPoint. |
| `ChartDataTable` | Allows to specify properties of a chart data table. |
| `ChartFormat` | Represents the formatting of a chart element. |
| `ChartLegend` | Represents chart legend properties. |
| `ChartLegendEntry` | Represents a chart legend entry. |
| `ChartLegendEntryCollection` | Represents a collection of chart legend entries. |
| `ChartMarker` | Represents a chart data marker. |
| `ChartMultilevelValue` | Represents a value for charts that display multilevel data. |
| `ChartNumberFormat` | Represents number formatting of the parent element. |
| `ChartSeries` | Represents chart series properties. |
| `ChartSeriesCollection` | Represents collection of a ChartSeries. |
| `ChartSeriesGroup` | Represents properties of a chart series group, that is, the properties of chart series of the same type associated with the same axes. |
| `ChartSeriesGroupCollection` | Represents a collection of ChartSeriesGroup objects. |
| `ChartTitle` | Provides access to the chart title properties. |
| `ChartXValue` | Represents an X value for a chart series. |
| `ChartXValueCollection` | Represents a collection of X values for a chart series. |
| `ChartYValue` | Represents an Y value for a chart series. |
| `ChartYValueCollection` | Represents a collection of Y values for a chart series. |
| `IChartDataPoint` | Contains properties of a single data point on the chart. |
| `Fill` | Represents fill formatting for an object. |
| `GlowFormat` | Represents the glow formatting for an object. |
| `GradientStop` | Represents one gradient stop. |
| `GradientStopCollection` | Contains a collection of GradientStop objects. |
| `GroupShape` | Represents a group of shapes in a document. |
| `HorizontalRuleFormat` | Represents horizontal rule formatting. |
| `ImageData` | Aspose.Words.Drawing.ImageData is a public symbol with members BiLevel, Borders, Brightness, ChromaKey, Contrast, CropBottom, CropLeft, and CropRight, and its Brightness setter throws ArgumentOutOfRangeException conditionally and its Contrast setter throws ArgumentOutOfRangeException conditionally. |
| `ImageSize` | Contains information about image size and resolution. |
| `CheckBoxControl` | The CheckBox control toggles a value. |
| `CommandButtonControl` | The CommandButton control runs a macro that performs an action when a user clicks it. |
| `Forms2OleControl` | Represents Microsoft Forms 2.0 OLE control. |
| `Forms2OleControlCollection` | Represents collection of Forms2OleControl objects. |
| `MorphDataControl` | The MorphDataControl structure is an aggregate of six controls: CheckBox, ComboBox, ListBox, OptionButton, TextBox, and ToggleButton. |
| `OleControl` | Represents OLE ActiveX control. |
| `OptionButtonControl` | The OptionButton control enables a single choice in a limited set of mutually exclusive choices. |
| `TextBoxControl` | The TextBox control displays TEXT from an organized set of data or user input. |
| `OleFormat` | Provides access to the data of an OLE object or ActiveX control. |
| `OlePackage` | Allows to access OLE Package properties. |
| `ReflectionFormat` | Represents the reflection formatting for an object. |
| `ShadowFormat` | Represents shadow formatting for an object. |
| `Shape` | Represents an object in the drawing layer, such as an AutoShape, textbox, freeform, OLE object, ActiveX control, or picture. |
| `ShapeBase` | Base class for objects in the drawing layer, such as an AutoShape, freeform, OLE object, ActiveX control, or picture. |
| `SignatureLine` | Provides access to signature line properties. |
| `SoftEdgeFormat` | Represents the soft edge formatting for an object. |
| `Stroke` | Defines a stroke for a shape. |
| `TextBox` | Defines attributes that specify how a TEXT is displayed inside a shape. |
| `TextPath` | Defines the TEXT and formatting of the TEXT path (of a WordArt object). |
| `EditableRange` | Represents a single editable range. |
| `EditableRangeEnd` | Represents an end of an editable range in a Word document. |
| `EditableRangeStart` | Represents a start of an editable range in a Word document. |
| `BarcodeParameters` | Container class for barcode parameters to pass-through to BarcodeGenerator. |
| `ComparisonEvaluationResult` | The comparison evaluation result. |
| `ComparisonExpression` | The comparison expression. |
| `DropDownItemCollection` | A collection of strings that represent all the items in a drop-down form field. |
| `Field` | Represents a Microsoft Word document field. |
| `FieldAddIn` | Implements the ADDIN field. |
| `FieldAddressBlock` | Implements the ADDRESSBLOCK field. |
| `FieldAdvance` | Implements the ADVANCE field. |
| `FieldArgumentBuilder` | Builds a complex field argument consisting of fields, nodes, and plain TEXT. |
| `FieldAsk` | Implements the ASK field. |
| `FieldAuthor` | Implements the AUTHOR field. |
| `FieldAutoNum` | Implements the AUTONUM field. |
| `FieldAutoNumLgl` | Implements the AUTONUMLGL field. |
| `FieldAutoNumOut` | Implements the AUTONUMOUT field. |
| `FieldAutoText` | Implements the AUTOTEXT field. |
| `FieldAutoTextList` | Implements the AUTOTEXTLIST field. |
| `FieldBarcode` | Implements the BARCODE field. |
| `FieldBibliography` | Implements the BIBLIOGRAPHY field. |
| `FieldBidiOutline` | Implements the BIDIOUTLINE field. |
| `FieldBuilder` | Builds a field from field code tokens (arguments and switches). |
| `FieldChar` | Base class for nodes that represent field characters in a document. |
| `FieldCitation` | Implements the CITATION field. |
| `FieldCollection` | A collection of Field objects that represents the fields in the specified range. |
| `FieldComments` | Implements the COMMENTS field. |
| `FieldCompare` | Implements the COMPARE field. |
| `FieldCreateDate` | Implements the CREATEDATE field. |
| `FieldData` | Implements the DATA field. |
| `FieldDatabase` | Implements the DATABASE field. |
| `FieldDatabaseDataRow` | Provides data for the FieldDatabase field result. |
| `FieldDatabaseDataTable` | Provides data for the FieldDatabase field result. |
| `FieldDate` | Implements the DATE field. |
| `FieldDde` | Implements the DDE field. |
| `FieldDdeAuto` | Implements the DDEAUTO field. |
| `FieldDisplayBarcode` | Implements the DISPLAYBARCODE field. |
| `FieldDocProperty` | Implements the DOCPROPERTY field. |
| `FieldDocVariable` | Implements DOCVARIABLE field. |
| `FieldEQ` | Implements the EQ field. |
| `FieldEditTime` | Implements the EDITTIME field. |
| `FieldEmbed` | Implements the EMBED field. |
| `FieldEnd` | Represents an end of a Word field in a document. |
| `FieldFileName` | Implements the FILENAME field. |
| `FieldFileSize` | Implements the FILESIZE field. |
| `FieldFillIn` | Implements the FILLIN field. |
| `FieldFootnoteRef` | Implements the FOOTNOTEREF field. |
| `FieldFormCheckBox` | Implements the FORMCHECKBOX field. |
| `FieldFormDropDown` | Implements the FORMDROPDOWN field. |
| `FieldFormText` | Implements the FORMTEXT field. |
| `FieldFormat` | Provides typed access to field's numeric, date and time, and general formatting. |
| `FieldFormula` | Implements the = (formula) field. |
| `FieldGlossary` | Implements the GLOSSARY field. |
| `FieldGoToButton` | Implements the GOTOBUTTON field. |
| `FieldGreetingLine` | Implements the GREETINGLINE field. |
| `FieldHyperlink` | Implements the HYPERLINK field To learn more, visit the Working with Fields documentation article. |
| `FieldIf` | Implements the IF field. |
| `FieldImport` | Implements the IMPORT field. |
| `FieldInclude` | Implements the INCLUDE field. |
| `FieldIncludePicture` | Implements the INCLUDEPICTURE field. |
| `FieldIncludeText` | Implements the INCLUDETEXT field. |
| `FieldIndex` | Implements the INDEX field. |
| `FieldInfo` | Implements the INFO field. |
| `FieldKeywords` | Implements the KEYWORDS field. |
| `FieldLastSavedBy` | Implements the LASTSAVEDBY field. |
| `FieldLink` | Implements the LINK field. |
| `FieldListNum` | Implements the LISTNUM field. |
| `FieldMacroButton` | Implements the MACROBUTTON field. |
| `FieldMergeBarcode` | Implements the MERGEBARCODE field. |
| `FieldMergeField` | Implements the MERGEFIELD field. |
| `FieldMergeRec` | Implements the MERGEREC field. |
| `FieldMergeSeq` | Implements the MERGESEQ field. |
| `FieldNext` | Implements the NEXT field. |
| `FieldNextIf` | Implements the NEXTIF field. |
| `FieldNoteRef` | Implements the NOTEREF field. |
| `FieldNumChars` | Implements the NUMCHARS field. |
| `FieldNumPages` | Implements the NUMPAGES field. |
| `FieldNumWords` | Implements the NUMWORDS field. |
| `FieldOcx` | Implements the OCX field. |
| `FieldOptions` | Represents options to control field handling in a document. |
| `FieldPage` | Implements the PAGE field. |
| `FieldPageRef` | Implements the PAGEREF field. |
| `FieldPrint` | Implements the PRINT field. |
| `FieldPrintDate` | Implements the PRINTDATE field. |
| `FieldPrivate` | Implements the PRIVATE field. |
| `FieldQuote` | Implements the QUOTE field. |
| `FieldRD` | Implements the RD field. |
| `FieldRef` | Implements the REF field. |
| `FieldRevNum` | Implements the REVNUM field. |
| `FieldSaveDate` | Implements the SAVEDATE field. |
| `FieldSection` | Implements the SECTION field. |
| `FieldSectionPages` | Implements the SECTIONPAGES field. |
| `FieldSeparator` | Represents a Word field separator that separates the field code from the field result. |
| `FieldSeq` | Implements the SEQ field. |
| `FieldSet` | Implements the SET field. |
| `FieldShape` | Implements the SHAPE field. |
| `FieldSkipIf` | Implements the SKIPIF field. |
| `FieldStart` | Represents a start of a Word field in a document. |
| `FieldStyleRef` | Implements the STYLEREF field. |
| `FieldSubject` | Implements the SUBJECT field. |
| `FieldSymbol` | Implements a SYMBOL field. |
| `FieldTA` | Implements the TA field. |
| `FieldTC` | Implements the TC field. |
| `FieldTemplate` | Implements the TEMPLATE field. |
| `FieldTime` | Implements the TIME field. |
| `FieldTitle` | Implements the TITLE field. |
| `FieldToa` | Implements the TOA field. |
| `FieldToc` | Implements the TOC field. |
| `FieldUnknown` | Implements an unknown or unrecognized field. |
| `FieldUpdatingProgressArgs` | Provides data for the field updating progress event. |
| `FieldUserAddress` | Implements the USERADDRESS field. |
| `FieldUserInitials` | Implements the USERINITIALS field. |
| `FieldUserName` | Implements the USERNAME field. |
| `FieldXE` | Implements the XE field. |
| `FormField` | Represents a single form field. |
| `FormFieldCollection` | A collection of FormField objects that represent all the form fields in a range. |
| `GeneralFormatCollection` | Represents a typed collection of general formats. |
| `IBarcodeGenerator` | Public interface for barcode custom generator. |
| `IBibliographyStylesProvider` | Aspose.Words.Fields.IBibliographyStylesProvider is a public symbol with member GetStyle. |
| `IComparisonExpressionEvaluator` | When implemented, allows to override default comparison expressions evaluation for the FieldIf and FieldCompare fields. |
| `IFieldDatabaseProvider` | Implement this interface to provide data for the FieldDatabase field when it's updated. |
| `IFieldResultFormatter` | Implement this interface if you want to control how the field result is formatted. |
| `IFieldUpdateCultureProvider` | When implemented, provides a CultureInfo object that should be used during the update of a particular field. |
| `IFieldUpdatingCallback` | Implement this interface if you want to have your own custom methods called during a field update. |
| `IFieldUpdatingProgressCallback` | Implement this interface if you want to track field updating progress. |
| `IFieldUserPromptRespondent` | Represents the respondent to user prompts during field update. |
| `MergeFieldImageDimension` | Represents an image dimension. |
| `ToaCategories` | Represents a table of authorities categories. |
| `UserInformation` | Specifies information about the user. |
| `FileCorruptedException` | Thrown during document load, when the document appears to be corrupted and impossible to load. |
| `FileFormatInfo` | Contains data returned by FileFormatUtil document format detection methods. |
| `FileFormatUtil` | Provides utility methods for working with file formats, such as detecting file format or converting file extensions to/from file format enums. |
| `Font` | Contains font attributes (font name, font size, color, and so on) for an object. |
| `FontEmbeddingLicensingRights` | Represents embedding licensing rights for the font. |
| `FontInfo` | Specifies information about a font used in the document. |
| `FontInfoCollection` | Represents a collection of fonts used in a document. |
| `FontSettings` | Specifies font settings for a document. |
| `FrameFormat` | Represents frame related formatting for a paragraph. |
| `Frameset` | Represents a frames page or a single frame on a frames page. |
| `FramesetCollection` | Represents a collection of instances of the Frameset class. |
| `HeaderFooter` | Represents a container for the header or footer TEXT of a section. |
| `HeaderFooterCollection` | Provides typed access to HeaderFooter nodes of a Section. |
| `IDocumentConverterPlugin` | Defines an interface for external converter plugin. |
| `IDocumentMergerPlugin` | Defines an interface for external merger plugin that can merge Pdf documents. |
| `IDocumentReaderPlugin` | Defines an interface for external reader plugins that can read a file into a document. |
| `INodeChangingCallback` | Implement this interface if you want to receive notifications when nodes are inserted or removed in the document. |
| `INodeCollection` | Aspose.Words.INodeCollection is a public symbol. |
| `IRevisionCriteria` | Implement this interface if you want to control when certain Revision should be accepted/rejected or not by the Accept/Reject methods. |
| `IWarningCallback` | Implement this interface if you want to have your own custom method called to capture loss of fidelity warnings that can occur during document loading or saving. |
| `ImageWatermarkOptions` | Contains options that can be specified when adding a watermark with image. |
| `ImportFormatOptions` | Allows to specify various import options to format output. |
| `IncorrectPasswordException` | Thrown if a document is encrypted with a password and the password specified when opening the document is incorrect or missing. |
| `Inline` | Base class for inline-level nodes that can have character formatting associated with them, but cannot have child nodes of their own. |
| `InlineStory` | Base class for inline-level nodes that can contain paragraphs and tables. |
| `InternableComplexAttr` | Base class for internable complex attribute. |
| `JoinRunsOptions` | Provides configuration flags for the join runs operation. |
| `List` | Aspose.Words.Lists.List is a public symbol with members CompareTo, Document, Equals, GetHashCode, HasSameTemplate, IsListStyleDefinition, IsListStyleReference, and IsMultiLevel. |
| `ListCollection` | Stores and manages formatting of bulleted and numbered lists used in a document. |
| `ListFormat` | Allows to control what list formatting is applied to a paragraph. |
| `ListLabel` | Defines properties specific to a list label. |
| `ListLevel` | Defines formatting for a list level. |
| `ListLevelCollection` | A collection of list formatting for each level in a list. |
| `ChmLoadOptions` | Allows to specify additional options when loading CHM document into a Document object. |
| `DocumentLoadingArgs` | An argument passed into Notify. |
| `HtmlLoadOptions` | Allows to specify additional options when loading HTML document into a Document object. |
| `IDocumentLoadingCallback` | Implement this interface if you want to have your own custom method called during loading a document. |
| `IResourceLoadingCallback` | Implement this interface if you want to control how Aspose.Words loads external resource when importing a document and inserting images using DocumentBuilder. |
| `LanguagePreferences` | Allows to set up language preferences. |
| `LoadOptions` | Allows to specify additional options (such as password or base URI) when loading a document into a Document object. |
| `MarkdownLoadOptions` | Allows to specify additional options when loading Markdown document into a Document object. |
| `PdfLoadOptions` | Allows to specify additional options when loading Pdf document into a Document object. |
| `ResourceLoadingArgs` | Provides data for the ResourceLoading method. |
| `RtfLoadOptions` | Allows to specify additional options when loading Rtf document into a Document object. |
| `TxtLoadOptions` | Allows to specify additional options when loading Text document into a Document object. |
| `CustomPart` | Represents a custom (arbitrary content) part, that is not defined by the ISO/IEC 29500 standard. |
| `CustomPartCollection` | Represents a collection of CustomPart objects. |
| `CustomXmlPart` | Represents a Custom XML Data Storage Part (custom XML data within a package). |
| `CustomXmlPartCollection` | Represents a collection of Custom XML Parts. |
| `CustomXmlProperty` | Represents a single custom XML attribute or a smart tag property. |
| `CustomXmlPropertyCollection` | Represents a collection of custom XML attributes or smart tag properties. |
| `CustomXmlSchemaCollection` | A collection of strings that represent XML schemas that are associated with a custom XML part. |
| `IStructuredDocumentTag` | Interface to define a common data for StructuredDocumentTag and StructuredDocumentTagRangeStart. |
| `SdtListItem` | This element specifies a single list item within a parent ComboBox or DropDownList structured document tag. |
| `SdtListItemCollection` | Provides access to SdtListItem elements of a structured document tag. |
| `SmartTag` | This element specifies the presence of a smart tag around one or more inline structures (runs, images, fields,etc.) within a paragraph. |
| `StructuredDocumentTag` | Represents a structured document tag (SDT or content control) in a document. |
| `StructuredDocumentTagCollection` | A collection of IStructuredDocumentTag instances that represent the structured document tags in the specified range. |
| `StructuredDocumentTagRangeEnd` | Represents an end of ranged structured document tag which accepts multi-sections content. |
| `StructuredDocumentTagRangeStart` | Represents a start of ranged structured document tag which accepts multi-sections content. |
| `XmlMapping` | Specifies the information that is used to establish a mapping between the parent structured document tag and an XML element stored within a custom XML data part in the document. |
| `OfficeMath` | Represents an Office Math object such as function, equation, matrix or alike. |
| `Node` | Base class for all nodes of a Word document. |
| `NodeChangingArgs` | Provides data for methods of the INodeChangingCallback interface. |
| `NodeCollection` | Represents a collection of nodes of a specific type. |
| `NodeEnumerator` | Aspose.Words.NodeEnumerator is a public symbol with members Current, Dispose, MoveNext, and Reset. |
| `NodeImporter` | Allows to efficiently perform repeated import of nodes from one document to another. |
| `NodeList` | Represents a collection of nodes matching an XPath query executed using the SelectNodes method. |
| `EndnoteOptions` | Represents the endnote numbering options for a document or section. |
| `Footnote` | Represents a container for TEXT of a footnote or endnote. |
| `FootnoteOptions` | Represents the footnote numbering options for a document or section. |
| `FootnoteSeparator` | Represents a container for the footnote/endnote separator and continuation content of a document. |
| `FootnoteSeparatorCollection` | Provides typed access to FootnoteSeparator nodes of a document. |
| `PageSetup` | Represents the page setup properties of a section. |
| `Paragraph` | Represents a paragraph of TEXT. |
| `ParagraphCollection` | Provides typed access to a collection of Paragraph nodes. |
| `ParagraphFormat` | Represents all the formatting for a paragraph. |
| `PhoneticGuide` | Represents Phonetic Guide. |
| `PlainTextDocument` | Allows to extract plain-text representation of the document's content. |
| `BuiltInDocumentProperties` | A collection of built-in document properties. |
| `CustomDocumentProperties` | A collection of custom document properties. |
| `DocumentProperty` | Represents a custom or built-in document property. |
| `DocumentPropertyCollection` | Base class for BuiltInDocumentProperties and CustomDocumentProperties collections. |
| `Range` | Represents a contiguous area in a document. |
| `FindReplaceOptions` | Specifies options for find/replace operations. |
| `IReplacingCallback` | Implement this interface if you want to have your own custom method called during a find and replace operation. |
| `ReplacingArgs` | Provides data for a custom replace operation. |
| `Revision` | Represents a revision (tracked change) in a document node or style. |
| `RevisionCollection` | A collection of Revision objects that represent revisions in the document. |
| `RevisionGroup` | Represents a group of sequential Revision objects. |
| `RevisionGroupCollection` | A collection of RevisionGroup objects that represent revision groups in the document. |
| `Run` | Represents a run of characters with the same font formatting. |
| `RunCollection` | Provides typed access to a collection of Run nodes. |
| `BookmarksOutlineLevelCollection` | A collection of individual bookmarks outline level. |
| `CssSavingArgs` | Provides data for the CssSaving event. |
| `DigitalSignatureDetails` | Contains details for signing a document with a digital signature. |
| `DocumentPartSavingArgs` | Provides data for the DocumentPartSaving callback. |
| `DocumentSavingArgs` | An argument passed into Notify. |
| `GraphicsQualityOptions` | Allows to specify additional Graphics quality optionsjava.awt.RenderingHints Graphics quality options. |
| `HtmlSaveOptions` | Can be used to specify additional options when saving a document into the Html, Mhtml, Epub, Azw3 or Mobi format. |
| `ICssSavingCallback` | Implement this interface if you want to control how Aspose.Words saves CSS (Cascading Style Sheet) when saving a document to HTML. |
| `IDocumentPartSavingCallback` | Implement this interface if you want to receive notifications and control how Aspose.Words saves document parts when exporting a document to Html or Epub format. |
| `IDocumentSavingCallback` | Implement this interface if you want to have your own custom method called during saving a document. |
| `IImageSavingCallback` | Implement this interface if you want to control how Aspose.Words saves images when saving a document to HTML. |
| `IPageSavingCallback` | Implement this interface if you want to control how Aspose.Words saves separate pages when saving a document to fixed page formats. |
| `IResourceSavingCallback` | Implement this interface if you want to control how Aspose.Words saves external resources (images, fonts and css) when saving a document to fixed page HTML or SVG. |
| `ImageSavingArgs` | Provides data for the ImageSaving event. |
| `MarkdownSaveOptions` | Class to specify additional options when saving a document into the Markdown format. |
| `MultiPageLayout` | Defines a layout for rendering multiple pages into a single output. |
| `OoxmlSaveOptions` | Can be used to specify additional options when saving a document into the Docx, Docm, Dotx, Dotm or FlatOpc format. |
| `OutlineOptions` | Allows to specify outline options. |
| `PageRange` | Represents a continuous range of pages. |
| `PageSavingArgs` | Provides data for the PageSaving event. |
| `PageSet` | Describes a random set of pages. |
| `ResourceSavingArgs` | Provides data for the ResourceSaving event. |
| `SaveOptions` | This is an abstract base class for classes that allow the user to specify additional options when saving a document into a particular format. |
| `SaveOutputParameters` | This object is returned to the caller after a document is saved and contains additional information that has been generated or calculated during the save operation. |
| `TxtListIndentation` | Specifies how list levels are indented when document is exporting to Text format. |
| `TxtSaveOptions` | Can be used to specify additional options when saving a document into the Text format. |
| `TxtSaveOptionsBase` | The base class for specifying additional options when saving a document into a TEXT based formats. |
| `WordML2003SaveOptions` | Can be used to specify additional options when saving a document into the WordML format. |
| `Section` | Represents a single section in a document. |
| `SectionCollection` | A collection of Section objects in the document. |
| `CompatibilityOptions` | Contains compatibility options (that is, the user preferences entered on the Compatibility tab of the Options dialog in Microsoft Word). |
| `HyphenationOptions` | Allows to configure document hyphenation options. |
| `MailMergeSettings` | Specifies all of the mail merge information for a document. |
| `Odso` | Specifies the Office Data Source Object (ODSO) settings for a mail merge data source. |
| `OdsoFieldMapData` | Specifies how a column in the external data source shall be mapped to the predefined merge fields within the document. |
| `OdsoFieldMapDataCollection` | A typed collection of the OdsoFieldMapData objects. |
| `OdsoRecipientData` | Represents information about a single record within an external data source that is to be excluded from the mail merge. |
| `OdsoRecipientDataCollection` | A typed collection of OdsoRecipientData To learn more, visit the Mail Merge and Reporting documentation article. |
| `ViewOptions` | Provides various options that control how a document is shown in Microsoft Word. |
| `WriteProtection` | Specifies write protection settings for a document. |
| `Shading` | Contains shading attributes for an object. |
| `SignatureLineOptions` | Allows to specify options for signature line being inserted. |
| `SpecialChar` | Base class for special characters in the document. |
| `Story` | Base class for elements that contain block-level nodes Paragraph and Table. |
| `Style` | Represents a single built-in or user-defined style. |
| `StyleCollection` | A collection of Style objects that represent both the built-in and user-defined styles in a document. |
| `SubDocument` | Represents a SubDocument - which is a reference to an externally stored document. |
| `TabStop` | Represents a single custom tab stop. |
| `TabStopCollection` | Aspose.Words.TabStopCollection is a public symbol with members Add, After, Before, Clear, Count, Equals, GetHashCode, and GetIndexByPosition, and its Add method throws ArgumentNullException conditionally. |
| `TableStyle` | Represents a table style. |
| `Cell` | Represents a table cell. |
| `CellCollection` | Provides typed access to a collection of Cell nodes. |
| `CellFormat` | Represents all formatting for a table cell. |
| `PreferredWidth` | Represents a value and its unit of measure that is used to specify the preferred width of a table or a cell. |
| `Row` | Represents a table row. |
| `RowCollection` | Provides typed access to a collection of Row nodes. |
| `RowFormat` | Represents all formatting for a table row. |
| `Table` | Represents a table in a Word document. |
| `TableCollection` | Provides typed access to a collection of Table nodes. |
| `TextColumn` | Represents a single TEXT column. |
| `TextColumnCollection` | A collection of TextColumn objects that represent all the columns of TEXT in a section of a document. |
| `TextWatermarkOptions` | Contains options that can be specified when adding a watermark with TEXT. |
| `Theme` | Represents document Theme, and provides access to main theme parts including MajorFonts, MinorFonts and Colors To learn more, visit the Working with Styles and Themes documentation article. |
| `ThemeColors` | Represents the color scheme of the document theme which contains twelve colors. |
| `ThemeFonts` | Represents a collection of fonts in the font scheme, allowing to specify different fonts for different languages Latin, EastAsian and ComplexScript. |
| `UnsupportedFileFormatException` | Thrown during document load, when the document format is not recognized or not supported by Aspose.Words. |
| `VariableCollection` | A collection of document variables. |
| `VbaModule` | Provides access to VBA project module. |
| `VbaModuleCollection` | Represents a collection of VbaModule objects. |
| `VbaProject` | Provides access to VBA project information. |
| `VbaReference` | Implements a reference to an Automation type library or VBA project. |
| `VbaReferenceCollection` | Represents a collection of VbaReference objects. |
| `WarningInfo` | Contains information about a warning that Aspose.Words issued during document loading or saving. |
| `WarningInfoCollection` | Represents a typed collection of WarningInfo objects. |
| `Watermark` | Represents class to work with document watermark. |
| `BaseWebExtensionCollection` | Base class for TaskPaneCollection, WebExtensionBindingCollection, WebExtensionPropertyCollection and WebExtensionReferenceCollection collections. |
| `TaskPane` | Represents an add-in task pane object. |
| `TaskPaneCollection` | Specifies a list of persisted task pane objects. |
| `WebExtension` | Represents a web extension object. |
| `WebExtensionBinding` | Specifies a binding relationship between a web extension and the data in the document. |
| `WebExtensionBindingCollection` | Specifies a list of web extension bindings. |
| `WebExtensionProperty` | Specifies a web extension custom property. |
| `WebExtensionPropertyCollection` | Specifies a set of web extension custom properties. |
| `WebExtensionReference` | Represents the reference to a web extension. |
| `WebExtensionReferenceCollection` | Specifies a list of web extension references. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `BaselineAlignment` | Specifies fonts vertical position on a line. |
| `SourceType` | Represents bibliography source types. |
| `BorderType` | Specifies sides of a border. |
| `BreakType` | Specifies type of a break inside a document. |
| `BuildingBlockBehavior` | Specifies the behavior that shall be applied to the contents of the building block when it is inserted into the main document. |
| `BuildingBlockGallery` | Specifies the predefined gallery into which a building block is classified. |
| `BuildingBlockType` | Specifies a building block type. |
| `CalendarType` | Specifies the type of a calendar. |
| `ChapterPageSeparator` | Defines the separator character that appears between the chapter and page number. |
| `ConditionalStyleType` | Represents possible table areas to which conditional formatting may be defined in a table style. |
| `ContentDisposition` | Enumerates different ways of presenting the document at the client browser. |
| `DigitalSignatureType` | Specifies the type of a digital signature. |
| `XmlDsigLevel` | Specifies the level of a digital signature based on XML-DSig standard. |
| `DocumentPositionMovement` | Aspose.Words.DocumentPositionMovement is a public symbol. |
| `ArrowLength` | Length of the arrow at the end of a line. |
| `ArrowType` | Specifies the type of an arrow at a line end. |
| `ArrowWidth` | Width of the arrow at the end of a line. |
| `AxisBuiltInUnit` | Specifies the display units for an axis. |
| `AxisCategoryType` | Specifies type of a category axis. |
| `AxisCrosses` | Specifies the possible crossing points for an axis. |
| `AxisGroup` | Represents a type of a chart axis group. |
| `AxisScaleType` | Specifies the possible scale types for an axis. |
| `AxisTickLabelPosition` | Specifies the possible positions for tick labels. |
| `AxisTickMark` | Specifies the possible positions for tick marks. |
| `AxisTimeUnit` | Specifies the unit of time for axes. |
| `ChartAxisType` | Specifies type of chart axis. |
| `ChartDataLabelLocationMode` | Specifies how the values ​​that specify the location of a data label - the Left and Top properties - are interpreted. |
| `ChartDataLabelPosition` | Specifies the position for a chart data label. |
| `ChartSeriesType` | Specifies a type of a chart series. |
| `ChartShapeType` | Specifies the shape type of chart elements. |
| `ChartStyle` | Specifies predefined styles of a chart. |
| `ChartType` | Specifies type of a chart. |
| `ChartXValueType` | Allows to specify type of an X value of a chart series. |
| `ChartYValueType` | Allows to specify type of an Y value of a chart series. |
| `LegendPosition` | Specifies the possible positions for a chart legend. |
| `MarkerSymbol` | Specifies marker symbol style. |
| `DashStyle` | Dashed line style. |
| `EndCap` | Specifies line cap style. |
| `FillType` | Specifies fill type for a fillable object. |
| `FlipOrientation` | Possible values for the orientation of a shape. |
| `GradientStyle` | Specifies the style for a gradient fill. |
| `GradientVariant` | Specifies the variant for a gradient fill. |
| `HorizontalAlignment` | Specifies horizontal alignment of a floating shape, TEXT frame or floating table. |
| `HorizontalRuleAlignment` | Represents the alignment for the specified horizontal rule. |
| `ImageType` | Specifies the type (format) of an image in a Microsoft Word document. |
| `JoinStyle` | Line join style. |
| `LayoutFlow` | Determines the flow of the TEXT layout in a textbox. |
| `Forms2OleControlType` | Enumerates types of Forms 2.0 controls. |
| `PatternType` | Specifies the fill pattern to be used to fill a shape. |
| `PresetTexture` | Specifies texture to be used to fill a shape. |
| `RelativeHorizontalPosition` | Specifies to what the horizontal position of a shape or TEXT frame is relative. |
| `RelativeHorizontalSize` | Specifies relatively to what the width of a shape or a TEXT frame is calculated horizontally. |
| `RelativeVerticalPosition` | Specifies to what the vertical position of a shape or TEXT frame is relative. |
| `RelativeVerticalSize` | Specifies relatively to what the height of a shape or a TEXT frame is calculated vertically. |
| `ShadowType` | Aspose.Words.Drawing.ShadowType is a public symbol. |
| `ShapeLineStyle` | Specifies the compound line style of a Shape. |
| `ShapeMarkupLanguage` | Aspose.Words.Drawing.ShapeMarkupLanguage is a public symbol. |
| `ShapeTextOrientation` | Specifies orientation of TEXT in shapes. |
| `ShapeType` | Specifies the type of shape in a Microsoft Word document. |
| `TextBoxAnchor` | Specifies values used for shape TEXT vertical alignment. |
| `TextBoxWrapMode` | Specifies how TEXT wraps inside a shape. |
| `TextPathAlignment` | WordArt alignment. |
| `TextureAlignment` | Specifies the alignment for the tiling of the texture fill. |
| `VerticalAlignment` | Specifies vertical alignment of a floating shape, TEXT frame or a floating table. |
| `WrapSide` | Specifies what side(s) of the shape or picture the TEXT wraps around. |
| `WrapType` | Specifies how TEXT is wrapped around a shape or picture. |
| `DropCapPosition` | Specifies the position for a drop cap TEXT. |
| `EditorType` | Specifies the set of possible aliases (or editing groups) which can be used as aliases to determine if the current user shall be allowed to edit a single range defined by an editable range within a document. |
| `EmphasisMark` | Specifies possible types of emphasis mark. |
| `FieldIfComparisonResult` | Specifies the result of the IF field condition evaluation. |
| `FieldIndexFormat` | Specifies the formatting for the FieldIndex fields in a document. |
| `FieldType` | Specifies Microsoft Word field types. |
| `FieldUpdateCultureSource` | Indicates what culture to use during field update. |
| `GeneralFormat` | Specifies a general format that is applied to a numeric, TEXT, or any field result. |
| `MergeFieldImageDimensionUnit` | Specifies an unit of an image dimension. |
| `TextFormFieldType` | Specifies the type of a TEXT form field. |
| `EmbeddedFontFormat` | Specifies format of particular embedded font inside FontInfo object. |
| `EmbeddedFontStyle` | Specifies the style of an embedded font inside a FontInfo object. |
| `FontEmbeddingUsagePermissions` | Represents the font embedding usage permissions. |
| `FontFamily` | Represents the font family. |
| `FontPitch` | Represents the font pitch. |
| `HeaderFooterType` | Identifies the type of header or footer found in a Word file. |
| `HeightRule` | Specifies the rule for determining the height of an object. |
| `HtmlInsertOptions` | Specifies options for the InsertHtml method. |
| `ImportFormatMode` | Specifies how formatting is merged when importing content from another document. |
| `LineNumberRestartMode` | Determines when automatic line numbering restarts. |
| `LineSpacingRule` | Specifies line spacing values for a paragraph. |
| `LineStyle` | Specifies line style of a Border. |
| `ListLevelAlignment` | Specifies alignment for the list number or bullet. |
| `ListTemplate` | Specifies one of the predefined list formats available in Microsoft Word. |
| `ListTrailingCharacter` | Specifies the character that separates the list label from the TEXT of the paragraph. |
| `LoadFormat` | Indicates the format of the document that is to be loaded. |
| `BlockImportMode` | Specifies how properties of block-level elements are imported from HTML-based documents. |
| `DocumentDirection` | Allows to specify the direction to flow the TEXT in a document. |
| `DocumentRecoveryMode` | Specifies the available recovery options when a document encounters errors during loading. |
| `EditingLanguage` | Specifies the editing language. |
| `HtmlControlType` | Type of document nodes that represent &lt;input&gt; and &lt;select&gt; elements imported from HTML. |
| `ResourceLoadingAction` | Specifies the mode of resource loading. |
| `ResourceType` | Type of loaded resource. |
| `TxtLeadingSpacesOptions` | Specifies available options for leading space handling during import from Text file. |
| `TxtTrailingSpacesOptions` | Specifies available options for trailing spaces handling during import from Text file. |
| `Margins` | Specifies preset margins. |
| `MarkupLevel` | Specifies the level in the document tree where a particular StructuredDocumentTag can occur. |
| `SdtAppearance` | Specifies the appearance of a structured document tag. |
| `SdtCalendarType` | Specifies the possible types of calendars which can be used to specify CalendarType in an Office Open XML document. |
| `SdtDateStorageFormat` | Specifies how the date for a date SDT is stored/retrieved when the SDT is bound to an XML node in the document's data store. |
| `SdtType` | Specifies the type of a structured document tag (SDT) node. |
| `MathObjectType` | Specifies type of an Office Math object. |
| `OfficeMathDisplayType` | Specifies the display format type of the equation. |
| `OfficeMathJustification` | Specifies the justification of the equation. |
| `MeasurementUnits` | Specifies the unit of measurement. |
| `NodeChangingAction` | Specifies the type of node change. |
| `NodeType` | Specifies the type of a Word document node. |
| `EndnotePosition` | Defines the endnote position. |
| `FootnoteNumberingRule` | Determines when automatic footnote or endnote numbering restarts. |
| `FootnotePosition` | Defines the footnote position. |
| `FootnoteSeparatorType` | Specifies the type of the footnote/endnote separator. |
| `FootnoteType` | Specifies whether this is a footnote or an endnote. |
| `NumSpacing` | Specifies possible values in which numeral spacing can be displayed. |
| `NumberStyle` | Specifies the number style for a list, footnotes and endnotes, page numbers. |
| `Orientation` | Specifies page orientation. |
| `OutlineLevel` | Specifies the outline level of a paragraph in the document. |
| `PageBorderAppliesTo` | Specifies which pages the page border is printed on. |
| `PageBorderDistanceFrom` | Specifies the positioning of the page border relative to the page margin. |
| `PageVerticalAlignment` | Specifies vertical justification of TEXT on each page. |
| `PaperSize` | Specifies paper size. |
| `ParagraphAlignment` | Specifies TEXT alignment in a paragraph. |
| `DocumentSecurity` | Used as a value for the Security property. |
| `PropertyType` | Specifies data type of a document property. |
| `ProtectionType` | Protection type for a document. |
| `FindReplaceDirection` | Specifies direction for replace operations. |
| `ReplaceAction` | Allows the user to specify what happens to the current match during a replace operation. |
| `ReplacementFormat` | Specifies the replacement format. |
| `RevisionType` | Aspose.Words.RevisionType is a public symbol. |
| `RevisionsView` | Allows to specify whether to work with the original or revised version of a document. |
| `SaveFormat` | Indicates the format in which the document is saved. |
| `ColorMode` | Specifies how colors are rendered. |
| `CompressionLevel` | Compression level for OOXML files. |
| `CssStyleSheetType` | Specifies how CSS (Cascading Style Sheet) styles are exported to HTML. |
| `Dml3DEffectsRenderingMode` | Specifies how 3D shape effects are rendered. |
| `DmlEffectsRenderingMode` | Specifies how DrawingML effects are rendered to fixed page formats. |
| `DmlRenderingMode` | Specifies how DrawingML shapes are rendered to fixed page formats. |
| `DocumentSplitCriteria` | Specifies how the document is split into parts when saving to Html, Epub or Azw3 format. |
| `EmfPlusDualRenderingMode` | Specifies how Aspose.Words should render EMF+ Dual metafiles. |
| `ExportHeadersFootersMode` | Specifies how headers and footers are exported to HTML, MHTML or EPUB. |
| `ExportListLabels` | Specifies how list labels are exported to HTML, MHTML and EPUB. |
| `HeaderFooterBookmarksExportMode` | Specifies how bookmarks in headers/footers are exported. |
| `HtmlElementSizeOutputMode` | Specifies how Aspose.Words exports element widths and heights to HTML, MHTML and EPUB. |
| `HtmlMetafileFormat` | Indicates the format in which metafiles are saved to HTML documents. |
| `HtmlOfficeMathOutputMode` | Specifies how Aspose.Words exports OfficeMath to HTML, MHTML and EPUB. |
| `HtmlVersion` | Indicates the version of HTML is used when saving the document to Html and Mhtml formats. |
| `ImageBinarizationMethod` | Specifies the method used to binarize image. |
| `ImageColorMode` | Specifies the color mode for the generated images of document pages. |
| `ImagePixelFormat` | Specifies the pixel format for the generated images of document pages. |
| `ImlRenderingMode` | Specifies how ink (InkML) objects are rendered to fixed page formats. |
| `MarkdownEmptyParagraphExportMode` | Specifies how Aspose.Words exports empty paragraphs to Markdown. |
| `MarkdownExportAsHtml` | Allows to specify the elements to be exported to Markdown as raw HTML. |
| `MarkdownLinkExportMode` | Specifies how links are exported into Markdown. |
| `MarkdownListExportMode` | Specifies how lists are exported into Markdown. |
| `MarkdownOfficeMathExportMode` | Specifies how Aspose.Words exports OfficeMath to Markdown. |
| `NumeralFormat` | Indicates the symbol set that is used to represent numbers while rendering to fixed page formats. |
| `OoxmlCompliance` | Allows to specify which OOXML specification will be used when saving in the DOCX format. |
| `SvgTextOutputMode` | Allows to specify how TEXT inside a document should be rendered when saving in SVG format. |
| `TableContentAlignment` | Allows to specify the alignment of the content of the table to be used when exporting into Markdown format. |
| `TiffCompression` | Specifies what type of compression to apply when saving page images into a TIFF file. |
| `TxtExportHeadersFootersMode` | Specifies the way headers and footers are exported to plain TEXT format. |
| `TxtOfficeMathExportMode` | Specifies how Aspose.Words exports OfficeMath to Text. |
| `Zip64Mode` | Specifies when to use ZIP64 format extensions for OOXML files. |
| `SectionLayoutMode` | Specifies the layout mode for a section allowing to define the document grid behavior. |
| `SectionStart` | The type of break at the beginning of the section. |
| `Compatibility` | Specifies names of compatibility options. |
| `JustificationMode` | Specifies the character spacing adjustment for a document. |
| `MailMergeCheckErrors` | Specifies how Microsoft Word will report errors detected during mail merge. |
| `MailMergeDataType` | Specifies the type of an external mail merge data source. |
| `MailMergeDestination` | Specifies the possible results which may be generated when a mail merge is carried out on a document. |
| `MailMergeMainDocumentType` | Specifies the possible types for a mail merge source document. |
| `MsWordVersion` | Allows Aspose.Wods to mimic MS Word version-specific application behavior. |
| `MultiplePagesType` | Specifies how document is printed out. |
| `OdsoDataSourceType` | Specifies the type of the external data source to be connected to as part of the ODSO connection information. |
| `OdsoFieldMappingType` | Specifies the possible types used to indicate if a given mail merge field has been mapped to a column in the given external data source. |
| `ViewType` | Possible values for the view mode in Microsoft Word. |
| `ZoomType` | Possible values for how large or small the document appears on the screen in Microsoft Word. |
| `StoryType` | Text of a Word document is stored in stories. |
| `StyleIdentifier` | Locale independent style identifier. |
| `StyleType` | Represents type of the style. |
| `TabAlignment` | Specifies the alignment/type of a tab stop. |
| `TabLeader` | Specifies the type of the leader line displayed under the tab character. |
| `AutoFitBehavior` | Determines how Aspose.Words resizes the table when you invoke the AutoFit method. |
| `CellMerge` | Specifies how a cell in a table is merged with other cells. |
| `CellVerticalAlignment` | Specifies vertical justification of TEXT inside a table cell. |
| `PreferredWidthType` | Specifies the unit of measurement for the preferred width of a table or cell. |
| `TableAlignment` | Specifies alignment for an inline table. |
| `TableStyleOptions` | Specifies how table style is applied to a table. |
| `TextWrapping` | Specifies how TEXT is wrapped around the table. |
| `TextDmlEffect` | Dml TEXT effect for TEXT runs. |
| `TextEffect` | Animation effect for TEXT runs. |
| `TextOrientation` | Specifies orientation of TEXT on a page, in a table cell or a TEXT frame. |
| `TextureIndex` | Specifies shading texture. |
| `ThemeColor` | Specifies the theme colors for document themes. |
| `ThemeFont` | Specifies the types of theme font names for document themes. |
| `Underline` | Indicates type of the underline applied to a font. |
| `VbaModuleType` | Specifies the type of a model in a VBA project. |
| `VbaReferenceType` | Allows to specify the type of a VbaReference object. |
| `VisitorAction` | Allows the visitor to control the enumeration of nodes. |
| `WarningSource` | Specifies the module that produces a warning during document loading or saving. |
| `WarningType` | Specifies the type of a warning that is issued by Aspose.Words during document loading or saving. |
| `WatermarkLayout` | Defines layout of the watermark relative to the watermark center. |
| `WatermarkType` | Specifies the watermark type. |
| `TaskPaneDockState` | Enumerates available locations of task pane object. |
| `WebExtensionBindingType` | Enumerates available types of binding between a web extension and the data in the document. |
| `WebExtensionStoreType` | Enumerates available types of a web extension store. |

#### Detailed Member Reference

### Document

The `Aspose.Words.Document` class represents a document loaded from a file or stream, or created empty, and provides methods such as `AppendDocument`, `AcceptAllRevisions`, and Save to manipulate and persist its content, with `Paragraph` and `SaveFormat` supporting node-level editing and output formatting.

- `Accept`: Calls VisitDocumentStart, then calls Accept for all child nodes of the document and calls VisitDocumentEnd at the end.
- `AcceptAllRevisions`: Accepts all tracked changes in the document.
- `AcceptEnd`: Accepts a visitor for visiting the end of the document.
- `AcceptStart`: Accepts a visitor for visiting the start of the document.
- `AppendChild`: Adds the specified node to the end of the list of child nodes for this node.
- `AppendDocument`: Appends the specified document to the end of this document.
- `AttachedTemplate`: Gets or sets the full path of the template attached to the document.
- `AutomaticallyUpdateStyles`: Gets or sets a flag indicating whether the styles in the document are updated to match the styles in the attached template each time the document is opened in MS Word.
- `BackgroundShape`: Gets or sets the background shape of the document.
- `Bibliography`: Gets the Bibliography object that represents the list of sources available in the document.
- `BuiltInDocumentProperties`: Returns a collection that represents all the built-in document properties of the document.
- `Cleanup`: Cleans unused styles and lists from the document.
- `Clone`: Performs a deep copy of the Document.
- `CompatibilityOptions`: Provides access to document compatibility options (that is, the user preferences entered on the Compatibility tab of the Options dialog in Word).
- `Compliance`: Gets the OOXML compliance version determined from the loaded document content.
- `CopyStylesFromTemplate`: Copies styles from the specified template to a document.
- `Count`: Gets the number of immediate children of this node.
- `CreateNavigator`: Creates navigator which can be used to traverse and read nodes.
- `CustomDocumentProperties`: Returns a collection that represents all the custom document properties of the document.
- `CustomNodeId`: Specifies custom node identifier.
- `CustomXmlParts`: Gets or sets the collection of Custom XML Data Storage Parts.
- `DefaultTabStop`: Gets or sets the interval (in points) between the default tab stops.
- `DigitalSignatures`: Gets the collection of digital signatures for this document and their validation results.
- `Document`: Creates or loads a document.
- `EndnoteOptions`: Provides options that control numbering and positioning of endnotes in this document.
- `EnsureMinimum`: If the document contains no sections, creates one section with one paragraph.
- `ExpandTableStylesToDirectFormatting`: Converts formatting specified in table styles into direct formatting on tables in the document.
- `FieldOptions`: Gets a FieldOptions object that represents options to control field handling in the document.
- `FirstChild`: Gets the first child of the node.
- `FirstSection`: Gets the first section in the document.
- `FontInfos`: Provides access to properties of fonts used in this document.
- `FontSettings`: Gets or sets document font settings.
- `FootnoteOptions`: Provides options that control numbering and positioning of footnotes in this document.
- `FootnoteSeparators`: Provides access to the footnote/endnote separators defined in the document.
- `Frameset`: Returns a Frameset instance if this document represents a frames page.
- `GetAncestor`: Gets the first ancestor of the specified object type.
- `GetChild`: Returns an Nth child node that matches the specified type.
- `GetChildNodes`: Returns a collection of child nodes that match the specified type.
- `GetEnumerator`: Provides support for the for each style iteration over the child nodes of this node.
- `GetText`: Gets the TEXT of this node and of all its children.
- `GlossaryDocument`: Gets or sets the glossary document within this document or template.
- `GrammarChecked`: Returns true if the document has been checked for grammar.
- `HasChildNodes`: Returns true if this node has any child nodes.
- `HasMacros`: Returns true if the document has a VBA project (macros).
- `HasRevisions`: Returns true if the document has any tracked changes.
- `HyphenationOptions`: Provides access to document hyphenation options.
- `ImportNode`: Imports a node from another document to the current document.
- `IncludeTextboxesFootnotesEndnotesInStat`: Specifies whether to include textboxes, footnotes and endnotes in word count statistics.
- `IndexOf`: Returns the index of the specified child node in the child node array.
- `InsertAfter`: Inserts the specified node immediately after the specified reference node.
- `InsertBefore`: Inserts the specified node immediately before the specified reference node.
- `IsComposite`: Returns true as this node can have child nodes.
- `JoinRunsWithSameFormatting`: Joins runs with same formatting in all paragraphs of the document.
- `JustificationMode`: Gets or sets the character spacing adjustment of a document.
- `LastChild`: Gets the last child of the node.
- `LastSection`: Gets the last section in the document.
- `Lists`: Provides access to the list formatting used in the document.
- `MailMergeSettings`: Gets or sets the object that contains all of the mail merge information for a document.
- `NextPreOrder`: Gets next node according to the pre-order tree traversal algorithm.
- `NextSibling`: Gets the node immediately following this node.
- `NodeChangingCallback`: Called when a node is inserted or removed in the document.
- `NodeType`: Returns Document.
- `NodeTypeToString`: A utility method that converts a node type enum value into a user friendly string.
- `NormalizeFieldTypes`: Changes field type values FieldType of FieldStart, FieldSeparator, FieldEnd in the whole document so that they correspond to the field types contained in the field codes.
- `OriginalFileName`: Gets the original file name of the document.
- `OriginalLoadFormat`: Gets the format of the original document that was loaded into this object.
- `PackageCustomParts`: Gets or sets the collection of custom parts (arbitrary content) that are linked to the OOXML package using "unknown relationships".
- `PageColor`: Gets or sets the page color of the document.
- `ParentNode`: Gets the immediate parent of this node.
- `PrependChild`: Adds the specified node to the beginning of the list of child nodes for this node.
- `PreviousPreOrder`: Gets the previous node according to the pre-order tree traversal algorithm.
- `PreviousSibling`: Gets the node immediately preceding this node.
- `Protect`: Protects the document from changes.
- `ProtectionType`: Gets the currently active document protection type.
- `PunctuationKerning`: Specifies whether kerning applies to both Latin TEXT and punctuation.
- `Range`: Returns a Range object that represents the portion of a document that is contained in this node.
- `Remove`: Removes itself from the parent.
- `RemoveAllChildren`: Removes all the child nodes of the current node.
- `RemoveChild`: Removes the specified child node.
- `RemoveExternalSchemaReferences`: Removes external XML schema references from this document.
- `RemoveMacros`: Removes all macros (the VBA project) as well as toolbars and command customizations from the document.
- `RemovePersonalInformation`: Gets or sets a flag indicating that Microsoft Word will remove all user information from comments, revisions and document properties upon saving the document.
- `RemoveSmartTags`: Removes all SmartTag descendant nodes of the current node.
- `ResourceLoadingCallback`: Allows to control how external resources are loaded.
- `Revisions`: Gets a collection of revisions (tracked changes) that exist in this document.
- `RevisionsView`: Gets or sets a value indicating whether to work with the original or revised version of a document.
- `Save`: Saves the document.
- `Sections`: Returns a collection that represents all sections in the document.
- `SelectNodes`: Selects a list of nodes matching the XPath expression.
- `SelectSingleNode`: Selects the first Node that matches the XPath expression.
- `ShadeFormData`: Specifies whether to turn on the gray shading on form fields.
- `ShowGrammaticalErrors`: Specifies whether to display grammar errors in this document.
- `ShowSpellingErrors`: Specifies whether to display spelling errors in this document.
- `SpellingChecked`: Returns true if the document has been checked for spelling.
- `StartTrackRevisions`: Starts automatically marking all further changes you make to the document programmatically as revision changes.
- `StopTrackRevisions`: Stops automatic marking of document changes as revisions.
- `Styles`: Returns a collection of styles defined in the document.
- `Theme`: Gets the Theme object for this document.
- `ToString`: Exports the content of the node into a string in the specified format.
- `TrackRevisions`: True if changes are tracked when this document is edited in Microsoft Word.
- `UnlinkFields`: Unlinks fields in the whole document.
- `Unprotect`: Removes protection from the document.
- `UpdateActualReferenceMarks`: Updates the ActualReferenceMark property of all footnotes and endnotes in the document.
- `UpdateFields`: Updates the values of fields in the whole document.
- `UpdateListLabels`: Updates list labels for all list items in the document.
- `UpdateTableLayout`: Implements an earlier approach to table column widths re-calculation that has known issues.
- `Variables`: Returns the collection of variables added to a document or template.
- `VbaProject`: Gets or sets a VbaProject.
- `VersionsCount`: Gets the number of document versions that was stored in the DOC document.
- `ViewOptions`: Provides options to control how the document is displayed in Microsoft Word.
- `WarningCallback`: Called during various document processing procedures when an issue is detected that might result in data or formatting fidelity loss.
- `Watermark`: Provides access to the document watermark.
- `WebExtensionTaskPanes`: Returns a collection that represents a list of task pane add-ins.
- `WriteProtection`: Provides access to the document write protection options.

### Revision

The `Aspose.Words.Revision` class represents a tracked change in a document, with methods to accept or reject individual revisions, while `Aspose.Words.RevisionCollection` provides bulk operations such as `AcceptAll` to manage all tracked changes in the document.

- `Accept`: Accepts this revision.
- `Author`: Gets or sets the author of this revision.
- `DateTime`: Gets or sets the date/time of this revision.
- `Group`: Gets the revision group.
- `ParentNode`: Gets the immediate parent node (owner) of this revision.
- `ParentStyle`: Gets the immediate parent style (owner) of this revision.
- `Reject`: Reject this revision.
- `RevisionType`: Gets the type of this revision.

### Drawing

`Aspose.Words.Drawing` provides support for working with shapes and charts in documents, while `Aspose.Words.Fields` and `Aspose.Words.Tables` enable insertion and manipulation of fields and tabular content respectively.

The API is the same as in the commercial Aspose.Words for .NET, so the [official documentation and examples](https://docs.aspose.com/words/net/) largely apply here too, within the supported feature set.

| Class | Description |
|---|---|
| `AbsolutePositionTab` | An absolute position tab is a character which is used to advance the position on the current line of text when displaying this WordprocessingML content. |
| `Adjustment` | Represents adjustment values that are applied to the specified shape. |
| `AdjustmentCollection` | Represents a read-only collection of Adjustment adjust values that are applied to the specified shape. |
| `AxisBound` | Represents minimum or maximum bound of axis values. |
| `AxisDisplayUnit` | Provides access to the scaling options of the display units for the value axis. |
| `AxisScaling` | Represents the scaling options of the axis. |
| `AxisTickLabels` | Represents properties of axis tick mark labels. |
| `BarcodeParameters` | Container class for barcode parameters to pass-through to BarcodeGenerator. |
| `BaseWebExtensionCollection<T>` | Base class for TaskPaneCollection, WebExtensionBindingCollection, WebExtensionPropertyCollection and WebExtensionReferenceCollection collections. |
| `Bibliography` | Represents the list of bibliography sources available in the document. |
| `Body` | Represents a container for the main text of a section. |
| `Bookmark` | Represents a single bookmark. |
| `BookmarkCollection` | A collection of Bookmark objects that represent the bookmarks in the specified range. |
| `BookmarkEnd` | Represents an end of a bookmark in a Word document. |
| `BookmarkStart` | Represents a start of a bookmark in a Word document. |
| `BookmarksOutlineLevelCollection` | A collection of individual bookmarks outline level. |
| `Border` | Represents a border of an object. |
| `BorderCollection` | A collection of Border objects. |
| `BubbleSizeCollection` | Represents a collection of bubble sizes for a chart series. |
| `BuildVersionInfo` | Provides information about the current product name and version. |
| `BuildingBlock` | A single reusable content block (AutoText/Quick Part) stored in a document's `GlossaryDocument`. |
| `BuildingBlockCollection` | A collection of BuildingBlock objects in the document. |
| `BuiltInDocumentProperties` | A collection of built-in document properties. |
| `Cell` | Represents a table cell. |
| `CellCollection` | Provides typed access to a collection of Cell nodes. |
| `CellFormat` | Represents all formatting for a table cell. |
| `CertificateHolder` | Represents a holder of X509Certificate2 instance. |
| `Chart` | Provides access to the chart shape properties. |
| `ChartAxis` | Represents the axis options of the chart. |
| `ChartAxisCollection` | Represents a collection of chart axes. |
| `ChartAxisTitle` | Provides access to the axis title properties. |
| `ChartDataLabel` | Represents data label on a chart point or trendline. |
| `ChartDataLabelCollection` | Represents a collection of ChartDataLabel. |
| `ChartDataPoint` | Allows to specify formatting of a single data point on the chart. |
| `ChartDataPointCollection` | Represents collection of a ChartDataPoint. |
| `ChartDataTable` | Allows to specify properties of a chart data table. |
| `ChartFormat` | Represents the formatting of a chart element. |
| `ChartLegend` | Represents chart legend properties. |
| `ChartLegendEntry` | Represents a chart legend entry. |
| `ChartLegendEntryCollection` | Represents a collection of chart legend entries. |
| `ChartMarker` | Represents a chart data marker. |
| `ChartMultilevelValue` | Represents a value for charts that display multilevel data. |
| `ChartNumberFormat` | Represents number formatting of the parent element. |
| `ChartSeries` | Represents chart series properties. |
| `ChartSeriesCollection` | Represents collection of a ChartSeries. |
| `ChartSeriesGroup` | Represents properties of a chart series group, that is, the properties of chart series of the same type associated with the same axes. |
| `ChartSeriesGroupCollection` | Represents a collection of ChartSeriesGroup objects. |
| `ChartTitle` | Provides access to the chart title properties. |
| `ChartXValue` | Represents an X value for a chart series. |
| `ChartXValueCollection` | Represents a collection of X values for a chart series. |
| `ChartYValue` | Represents an Y value for a chart series. |
| `ChartYValueCollection` | Represents a collection of Y values for a chart series. |
| `CheckBoxControl` | The CheckBox control toggles a value. |
| `ChmLoadOptions` | Allows to specify additional options when loading CHM document into a Document object. |
| `CleanupOptions` | Allows to specify options for document cleaning. |
| `CommandButtonControl` | The CommandButton control runs a macro that performs an action when a user clicks it. |
| `Comment` | Represents a container for text of a comment. |
| `CommentCollection` | Provides typed access to a collection of Comment nodes. |
| `CommentRangeEnd` | Denotes the end of a region of text that has a comment associated with it. |
| `CommentRangeStart` | Denotes the start of a region of text that has a comment associated with it. |
| `ComparisonEvaluationResult` | The comparison evaluation result. |
| `ComparisonExpression` | The comparison expression. |
| `CompatibilityOptions` | Contains compatibility options (that is, the user preferences entered on the Compatibility tab of the Options dialog in Microsoft Word). |
| `CompositeNode` | Base class for nodes that can contain other nodes. |
| `ConditionalStyle` | Represents special formatting applied to some area of a table with assigned table style. |
| `ConditionalStyleCollection` | Represents a collection of ConditionalStyle objects. |
| `Contributor` | Represents a bibliography source contributor. |
| `ContributorCollection` | Represents bibliography source contributors. |
| `ControlChar` | Control characters often encountered in documents. |
| `ConvertUtil` | Provides helper functions to convert between various measurement units. |
| `Corporate` | Represents a corporate (an organization) bibliography source contributor. |
| `CssSavingArgs` | Provides data for the CssSaving event. |
| `CustomDocumentProperties` | A collection of custom document properties. |
| `CustomPart` | Represents a custom (arbitrary content) part, that is not defined by the ISO/IEC 29500 standard. |
| `CustomPartCollection` | Represents a collection of CustomPart objects. |
| `CustomXmlPart` | Represents a Custom XML Data Storage Part (custom XML data within a package). |
| `CustomXmlPartCollection` | Represents a collection of Custom XML Parts. |
| `CustomXmlProperty` | Represents a single custom XML attribute or a smart tag property. |
| `CustomXmlPropertyCollection` | Represents a collection of custom XML attributes or smart tag properties. |
| `CustomXmlSchemaCollection` | A collection of strings that represent XML schemas that are associated with a custom XML part. |
| `DigitalSignature` | Represents a digital signature on a document and the result of its verification. |
| `DigitalSignatureCollection` | Provides a read-only collection of digital signatures attached to a document. |
| `DigitalSignatureDetails` | Contains details for signing a document with a digital signature. |
| `DigitalSignatureUtil` | Provides methods for signing document. |
| `Document` | The Document class constructors let developers create a new empty document or load an existing one from a file path, stream, or with custom load options. |
| `DocumentBase` | Provides the abstract base class for a main document and a glossary document of a Word document. |
| `DocumentBuilder` | Provides methods to insert text, images and other content, specify font, paragraph and section formatting. |
| `DocumentBuilderOptions` | Allows to specify additional options for the document building process. |
| `DocumentLoadingArgs` | An argument passed into Notify(DocumentLoadingArgs). |
| `DocumentPartSavingArgs` | Provides data for the DocumentPartSaving callback. |
| `DocumentProperty` | Represents a custom or built-in document property. |
| `DocumentPropertyCollection` | Base class for BuiltInDocumentProperties and CustomDocumentProperties collections. |
| `DocumentReaderPluginLoadException` | Thrown during document load, when the plugin required for reading the document format cannot be loaded. |
| `DocumentSavingArgs` | An argument passed into Notify(DocumentSavingArgs). |
| `DocumentVisitor` | Base class for custom document visitors. |
| `DropDownItemCollection` | A collection of strings that represent all the items in a drop-down form field. |
| `EditableRange` | Represents a single editable range. |
| `EditableRangeEnd` | Represents an end of an editable range in a Word document. |
| `EditableRangeStart` | Represents a start of an editable range in a Word document. |
| `EndnoteOptions` | Represents the endnote numbering options for a document or section. |
| `Field` | Represents a Microsoft Word document field. |
| `FieldAddIn` | Implements the ADDIN field. |
| `FieldAddressBlock` | Implements the ADDRESSBLOCK field. |
| `FieldAdvance` | Implements the ADVANCE field. |
| `FieldArgumentBuilder` | Builds a complex field argument consisting of fields, nodes, and plain text. |
| `FieldAsk` | Implements the ASK field. |
| `FieldAuthor` | Implements the AUTHOR field. |
| `FieldAutoNum` | Implements the AUTONUM field. |
| `FieldAutoNumLgl` | Implements the AUTONUMLGL field. |
| `FieldAutoNumOut` | Implements the AUTONUMOUT field. |
| `FieldAutoText` | Implements the AUTOTEXT field. |
| `FieldAutoTextList` | Implements the AUTOTEXTLIST field. |
| `FieldBarcode` | Implements the BARCODE field. |
| `FieldBibliography` | Implements the BIBLIOGRAPHY field. |
| `FieldBidiOutline` | Implements the BIDIOUTLINE field. |
| `FieldBuilder` | Builds a field from field code tokens (arguments and switches). |
| `FieldChar` | Base class for nodes that represent field characters in a document. |
| `FieldCitation` | Implements the CITATION field. |
| `FieldCollection` | A collection of Field objects that represents the fields in the specified range. |
| `FieldComments` | Implements the COMMENTS field. |
| `FieldCompare` | Implements the COMPARE field. |
| `FieldCreateDate` | Implements the CREATEDATE field. |
| `FieldData` | Implements the DATA field. |
| `FieldDatabase` | Implements the DATABASE field. |
| `FieldDatabaseDataRow` | Provides data for the FieldDatabase field result. |
| `FieldDatabaseDataTable` | Provides data for the FieldDatabase field result. |
| `FieldDate` | Implements the DATE field. |
| `FieldDde` | Implements the DDE field. |
| `FieldDdeAuto` | Implements the DDEAUTO field. |
| `FieldDisplayBarcode` | Implements the DISPLAYBARCODE field. |
| `FieldDocProperty` | Implements the DOCPROPERTY field. |
| `FieldDocVariable` | Implements DOCVARIABLE field. |
| `FieldEQ` | Implements the EQ field. |
| `FieldEditTime` | Implements the EDITTIME field. |
| `FieldEmbed` | Implements the EMBED field. |
| `FieldEnd` | Represents an end of a Word field in a document. |
| `FieldFileName` | Implements the FILENAME field. |
| `FieldFileSize` | Implements the FILESIZE field. |
| `FieldFillIn` | Implements the FILLIN field. |
| `FieldFootnoteRef` | Implements the FOOTNOTEREF field. |
| `FieldFormCheckBox` | Implements the FORMCHECKBOX field. |
| `FieldFormDropDown` | Implements the FORMDROPDOWN field. |
| `FieldFormText` | Implements the FORMTEXT field. |
| `FieldFormat` | Provides typed access to field's numeric, date and time, and general formatting. |
| `FieldFormula` | Implements the = (formula) field. |
| `FieldGlossary` | Implements the GLOSSARY field. |
| `FieldGoToButton` | Implements the GOTOBUTTON field. |
| `FieldGreetingLine` | Implements the GREETINGLINE field. |
| `FieldHyperlink` | Implements the HYPERLINK field To learn more, visit the Working with Fields documentation article. |
| `FieldIf` | Implements the IF field. |
| `FieldImport` | Implements the IMPORT field. |
| `FieldInclude` | Implements the INCLUDE field. |
| `FieldIncludePicture` | Implements the INCLUDEPICTURE field. |
| `FieldIncludeText` | Implements the INCLUDETEXT field. |
| `FieldIndex` | Implements the INDEX field. |
| `FieldInfo` | Implements the INFO field. |
| `FieldKeywords` | Implements the KEYWORDS field. |
| `FieldLastSavedBy` | Implements the LASTSAVEDBY field. |
| `FieldLink` | Implements the LINK field. |
| `FieldListNum` | Implements the LISTNUM field. |
| `FieldMacroButton` | Implements the MACROBUTTON field. |
| `FieldMergeBarcode` | Implements the MERGEBARCODE field. |
| `FieldMergeField` | Implements the MERGEFIELD field. |
| `FieldMergeRec` | Implements the MERGEREC field. |
| `FieldMergeSeq` | Implements the MERGESEQ field. |
| `FieldNext` | Implements the NEXT field. |
| `FieldNextIf` | Implements the NEXTIF field. |
| `FieldNoteRef` | Implements the NOTEREF field. |
| `FieldNumChars` | Implements the NUMCHARS field. |
| `FieldNumPages` | Implements the NUMPAGES field. |
| `FieldNumWords` | Implements the NUMWORDS field. |
| `FieldOcx` | Implements the OCX field. |
| `FieldOptions` | Represents options to control field handling in a document. |
| `FieldPage` | Implements the PAGE field. |
| `FieldPageRef` | Implements the PAGEREF field. |
| `FieldPrint` | Implements the PRINT field. |
| `FieldPrintDate` | Implements the PRINTDATE field. |
| `FieldPrivate` | Implements the PRIVATE field. |
| `FieldQuote` | Implements the QUOTE field. |
| `FieldRD` | Implements the RD field. |
| `FieldRef` | Implements the REF field. |
| `FieldRevNum` | Implements the REVNUM field. |
| `FieldSaveDate` | Implements the SAVEDATE field. |
| `FieldSection` | Implements the SECTION field. |
| `FieldSectionPages` | Implements the SECTIONPAGES field. |
| `FieldSeparator` | Represents a Word field separator that separates the field code from the field result. |
| `FieldSeq` | Implements the SEQ field. |
| `FieldSet` | Implements the SET field. |
| `FieldShape` | Implements the SHAPE field. |
| `FieldSkipIf` | Implements the SKIPIF field. |
| `FieldStart` | Represents a start of a Word field in a document. |
| `FieldStyleRef` | Implements the STYLEREF field. |
| `FieldSubject` | Implements the SUBJECT field. |
| `FieldSymbol` | Implements a SYMBOL field. |
| `FieldTA` | Implements the TA field. |
| `FieldTC` | Implements the TC field. |
| `FieldTemplate` | Implements the TEMPLATE field. |
| `FieldTime` | Implements the TIME field. |
| `FieldTitle` | Implements the TITLE field. |
| `FieldToa` | Implements the TOA field. |
| `FieldToc` | Implements the TOC field. |
| `FieldUnknown` | Implements an unknown or unrecognized field. |
| `FieldUpdatingProgressArgs` | Provides data for the field updating progress event. |
| `FieldUserAddress` | Implements the USERADDRESS field. |
| `FieldUserInitials` | Implements the USERINITIALS field. |
| `FieldUserName` | Implements the USERNAME field. |
| `FieldXE` | Implements the XE field. |
| `FileCorruptedException` | Thrown during document load, when the document appears to be corrupted and impossible to load. |
| `FileFormatInfo` | Contains data returned by FileFormatUtil document format detection methods. |
| `FileFormatUtil` | Provides utility methods for working with file formats, such as detecting file format or converting file extensions to/from file format enums. |
| `Fill` | Represents fill formatting for an object. |
| `FindReplaceOptions` | Specifies options for find/replace operations. |
| `Font` | Contains font attributes (font name, font size, color, and so on) for an object. |
| `FontEmbeddingLicensingRights` | Represents embedding licensing rights for the font. |
| `FontInfo` | Specifies information about a font used in the document. |
| `FontInfoCollection` | Represents a collection of fonts used in a document. |
| `FontSettings` | Specifies font settings for a document. |
| `Footnote` | Represents a container for text of a footnote or endnote. |
| `FootnoteOptions` | Represents the footnote numbering options for a document or section. |
| `FootnoteSeparator` | Represents a container for the footnote/endnote separator and continuation content of a document. |
| `FootnoteSeparatorCollection` | Provides typed access to FootnoteSeparator nodes of a document. |
| `FormField` | Represents a single form field. |
| `FormFieldCollection` | A collection of FormField objects that represent all the form fields in a range. |
| `Forms2OleControl` | Represents Microsoft Forms 2.0 OLE control. |
| `Forms2OleControlCollection` | Represents collection of Forms2OleControl objects. |
| `FrameFormat` | Represents frame related formatting for a paragraph. |
| `Frameset` | Represents a frames page or a single frame on a frames page. |
| `FramesetCollection` | Represents a collection of instances of the Frameset class. |
| `GeneralFormatCollection` | Represents a typed collection of general formats. |
| `GlossaryDocument` | Represents the root element for a glossary document within a Word document. |
| `GlowFormat` | Represents the glow formatting for an object. |
| `GradientStop` | Represents one gradient stop. |
| `GradientStopCollection` | Contains a collection of GradientStop objects. |
| `GraphicsQualityOptions` | Allows to specify additional Graphics quality optionsjava.awt.RenderingHints Graphics quality options. |
| `GroupShape` | Represents a group of shapes in a document. |
| `HeaderFooter` | Represents a container for the header or footer text of a section. |
| `HeaderFooterCollection` | Provides typed access to HeaderFooter nodes of a Section. |
| `HorizontalRuleFormat` | Represents horizontal rule formatting. |
| `HtmlLoadOptions` | Allows to specify additional options when loading HTML document into a Document object. |
| `HtmlSaveOptions` | Can be used to specify additional options when saving a document into the HTML, MHTML, EPUB, AZW3 or MOBI format. |
| `HyphenationOptions` | Allows to configure document hyphenation options. |
| `ImageData` | Holds and converts a picture shape's raw image data (`SetImage()`, `ToImage()`, `ToStream()`, `ToByteArray()`). |
| `ImageSavingArgs` | Provides data for the ImageSaving event. |
| `ImageSize` | Contains information about image size and resolution. |
| `ImageWatermarkOptions` | Contains options that can be specified when adding a watermark with image. |
| `ImportFormatOptions` | Allows to specify various import options to format output. |
| `IncorrectPasswordException` | Thrown if a document is encrypted with a password and the password specified when opening the document is incorrect or missing. |
| `Inline` | Base class for inline-level nodes that can have character formatting associated with them, but cannot have child nodes of their own. |
| `InlineStory` | Base class for inline-level nodes that can contain paragraphs and tables. |
| `InternableComplexAttr` | Base class for internable complex attribute. |
| `JoinRunsOptions` | Provides configuration flags for the join runs operation - IgnoreSpacing, IgnoreRedundant and IgnoreInsignificant. |
| `LanguagePreferences` | Allows to set up language preferences. |
| `List` | List class exposes ListId, ListLevels, Style and methods like CompareTo and HasSameTemplate, allowing developers to inspect, compare, and manipulate document list definitions. |
| `ListCollection` | Stores and manages formatting of bulleted and numbered lists used in a document. |
| `ListFormat` | Allows to control what list formatting is applied to a paragraph. |
| `ListLabel` | Defines properties specific to a list label. |
| `ListLevel` | Defines formatting for a list level. |
| `ListLevelCollection` | A collection of list formatting for each level in a list. |
| `LoadOptions` | Allows to specify additional options (such as password or base URI) when loading a document into a Document object. |
| `MailMergeSettings` | Specifies all of the mail merge information for a document. |
| `MarkdownLoadOptions` | Allows to specify additional options when loading Markdown document into a Document object. |
| `MarkdownSaveOptions` | Class to specify additional options when saving a document into the Markdown format. |
| `MergeFieldImageDimension` | Represents an image dimension (i.e. |
| `MorphDataControl` | The MorphDataControl structure is an aggregate of six controls: CheckBox, ComboBox, ListBox, OptionButton, TextBox, and ToggleButton. |
| `MultiPageLayout` | Defines a layout for rendering multiple pages into a single output. |
| `Node` | Base class for all nodes of a Word document. |
| `NodeChangingArgs` | Provides data for methods of the INodeChangingCallback interface. |
| `NodeCollection` | Represents a collection of nodes of a specific type. |
| `NodeImporter` | Allows to efficiently perform repeated import of nodes from one document to another. |
| `NodeList` | Represents a collection of nodes matching an XPath query executed using the SelectNodes method. |
| `Odso` | Specifies the Office Data Source Object (ODSO) settings for a mail merge data source. |
| `OdsoFieldMapData` | Specifies how a column in the external data source shall be mapped to the predefined merge fields within the document. |
| `OdsoFieldMapDataCollection` | A typed collection of the OdsoFieldMapData objects. |
| `OdsoRecipientData` | Represents information about a single record within an external data source that is to be excluded from the mail merge. |
| `OdsoRecipientDataCollection` | A typed collection of OdsoRecipientData To learn more, visit the Mail Merge and Reporting documentation article. |
| `OfficeMath` | Represents an Office Math object such as function, equation, matrix or alike. |
| `OleControl` | Represents OLE ActiveX control. |
| `OleFormat` | Provides access to the data of an OLE object or ActiveX control. |
| `OlePackage` | Allows to access OLE Package properties. |
| `OoxmlSaveOptions` | Can be used to specify additional options when saving a document into the DOCX, DOCM, DOTX, DOTM or FlatOpc format. |
| `OptionButtonControl` | The OptionButton control enables a single choice in a limited set of mutually exclusive choices. |
| `OutlineOptions` | Allows to specify outline options. |
| `PageRange` | Represents a continuous range of pages. |
| `PageSavingArgs` | Provides data for the PageSaving event. |
| `PageSet` | Describes a random set of pages. |
| `PageSetup` | Represents the page setup properties of a section. |
| `Paragraph` | Represents a paragraph of text. |
| `ParagraphCollection` | Provides typed access to a collection of Paragraph nodes. |
| `ParagraphFormat` | Represents all the formatting for a paragraph. |
| `PdfLoadOptions` | Allows to specify additional options when loading PDF document into a Document object. |
| `Person` | Represents individual (a person) bibliography source contributor. |
| `PersonCollection` | Represents a list of persons who are bibliography source contributors. |
| `PhoneticGuide` | Represents Phonetic Guide. |
| `PlainTextDocument` | Allows to extract plain-text representation of the document's content. |
| `PreferredWidth` | Represents a value and its unit of measure that is used to specify the preferred width of a table or a cell. |
| `Range` | Represents a contiguous area in a document. |
| `ReflectionFormat` | Represents the reflection formatting for an object. |
| `ReplacingArgs` | Provides data for a custom replace operation. |
| `ResourceLoadingArgs` | Provides data for the ResourceLoading method. |
| `ResourceSavingArgs` | Provides data for the ResourceSaving event. |
| `Revision` | Represents a revision (tracked change) in a document node or style. |
| `RevisionCollection` | A collection of Revision objects that represent revisions in the document. |
| `RevisionGroup` | Represents a group of sequential Revision objects. |
| `RevisionGroupCollection` | A collection of RevisionGroup objects that represent revision groups in the document. |
| `Row` | Represents a table row. |
| `RowCollection` | Provides typed access to a collection of Row nodes. |
| `RowFormat` | Represents all formatting for a table row. |
| `RtfLoadOptions` | Allows to specify additional options when loading RTF document into a Document object. |
| `Run` | Represents a run of characters with the same font formatting. |
| `RunCollection` | Provides typed access to a collection of Run nodes. |
| `SaveOptions` | This is an abstract base class for classes that allow the user to specify additional options when saving a document into a particular format. |
| `SaveOutputParameters` | This object is returned to the caller after a document is saved and contains additional information that has been generated or calculated during the save operation. |
| `SdtListItem` | This element specifies a single list item within a parent ComboBox or DropDownList structured document tag. |
| `SdtListItemCollection` | Provides access to SdtListItem elements of a structured document tag. |
| `Section` | Represents a single section in a document. |
| `SectionCollection` | A collection of Section objects in the document. |
| `Shading` | Contains shading attributes for an object. |
| `ShadowFormat` | Represents shadow formatting for an object. |
| `Shape` | Represents an object in the drawing layer, such as an AutoShape, textbox, freeform, OLE object, ActiveX control, or picture. |
| `ShapeBase` | Base class for objects in the drawing layer, such as an AutoShape, freeform, OLE object, ActiveX control, or picture. |
| `SignOptions` | Allows to specify options for document signing. |
| `SignatureLine` | Provides access to signature line properties. |
| `SignatureLineOptions` | Allows to specify options for signature line being inserted. |
| `SmartTag` | This element specifies the presence of a smart tag around one or more inline structures (runs, images, fields,etc.) within a paragraph. |
| `SoftEdgeFormat` | Represents the soft edge formatting for an object. |
| `Source` | Represents an individual source, such as a book, journal article, or interview. |
| `SpecialChar` | Base class for special characters in the document. |
| `Story` | Base class for elements that contain block-level nodes Paragraph and Table. |
| `Stroke` | Defines a stroke for a shape. |
| `StructuredDocumentTag` | Represents a structured document tag (SDT or content control) in a document. |
| `StructuredDocumentTagCollection` | A collection of IStructuredDocumentTag instances that represent the structured document tags in the specified range. |
| `StructuredDocumentTagRangeEnd` | Represents an end of ranged structured document tag which accepts multi-sections content. |
| `StructuredDocumentTagRangeStart` | Represents a start of ranged structured document tag which accepts multi-sections content. |
| `Style` | Represents a single built-in or user-defined style. |
| `StyleCollection` | A collection of Style objects that represent both the built-in and user-defined styles in a document. |
| `SubDocument` | Represents a SubDocument - which is a reference to an externally stored document. |
| `TabStop` | Represents a single custom tab stop. |
| `TabStopCollection` | A paragraph's collection of tab stops, indexed by position (`GetPositionByIndex()`/`GetIndexByPosition()`). |
| `Table` | Represents a table in a Word document. |
| `TableCollection` | Provides typed access to a collection of Table nodes. |
| `TableStyle` | Represents a table style. |
| `TaskPane` | Represents an add-in task pane object. |
| `TaskPaneCollection` | Specifies a list of persisted task pane objects. |
| `TextBox` | Defines attributes that specify how a text is displayed inside a shape. |
| `TextBoxControl` | The TextBox control displays text from an organized set of data or user input. |
| `TextColumn` | Represents a single text column. |
| `TextColumnCollection` | A collection of TextColumn objects that represent all the columns of text in a section of a document. |
| `TextPath` | Defines the text and formatting of the text path (of a WordArt object). |
| `TextWatermarkOptions` | Contains options that can be specified when adding a watermark with text. |
| `Theme` | Represents document Theme, and provides access to main theme parts including MajorFonts, MinorFonts and Colors To learn more, visit the Working with Styles and Themes documentation article. |
| `ThemeColors` | Represents the color scheme of the document theme which contains twelve colors. |
| `ThemeFonts` | Represents a collection of fonts in the font scheme, allowing to specify different fonts for different languages Latin, EastAsian and ComplexScript. |
| `ToaCategories` | Represents a table of authorities categories. |
| `TxtListIndentation` | Specifies how list levels are indented when document is exporting to Text format. |
| `TxtLoadOptions` | Allows to specify additional options when loading Text document into a Document object. |
| `TxtSaveOptions` | Can be used to specify additional options when saving a document into the Text format. |
| `TxtSaveOptionsBase` | The base class for specifying additional options when saving a document into a text based formats. |
| `UnsupportedFileFormatException` | Thrown during document load, when the document format is not recognized or not supported by Aspose.Words. |
| `UserInformation` | Specifies information about the user. |
| `VariableCollection` | A collection of document variables. |
| `VbaModule` | Provides access to VBA project module. |
| `VbaModuleCollection` | Represents a collection of VbaModule objects. |
| `VbaProject` | Provides access to VBA project information. |
| `VbaReference` | Implements a reference to an Automation type library or VBA project. |
| `VbaReferenceCollection` | Represents a collection of VbaReference objects. |
| `ViewOptions` | Provides various options that control how a document is shown in Microsoft Word. |
| `WarningInfo` | Contains information about a warning that Aspose.Words issued during document loading or saving. |
| `WarningInfoCollection` | Represents a typed collection of WarningInfo objects. |
| `Watermark` | Represents class to work with document watermark. |
| `WebExtension` | Represents a web extension object. |
| `WebExtensionBinding` | Specifies a binding relationship between a web extension and the data in the document. |
| `WebExtensionBindingCollection` | Specifies a list of web extension bindings. |
| `WebExtensionProperty` | Specifies a web extension custom property. |
| `WebExtensionPropertyCollection` | Specifies a set of web extension custom properties. |
| `WebExtensionReference` | Represents the reference to a web extension. |
| `WebExtensionReferenceCollection` | Specifies a list of web extension references. |
| `WordML2003SaveOptions` | Can be used to specify additional options when saving a document into the WordML format. |
| `WriteProtection` | Specifies write protection settings for a document. |
| `XmlMapping` | Specifies the information that is used to establish a mapping between the parent structured document tag and an XML element stored within a custom XML data part in the document. |

| Class | Description |
|---|---|
| `ArrowLength` | Length of the arrow at the end of a line. |
| `ArrowType` | Specifies the type of an arrow at a line end. |
| `ArrowWidth` | Width of the arrow at the end of a line. |
| `AutoFitBehavior` | Determines how Aspose.Words resizes the table when you invoke the AutoFit method. |
| `AxisBuiltInUnit` | Specifies the display units for an axis. |
| `AxisCategoryType` | Specifies type of a category axis. |
| `AxisCrosses` | Specifies the possible crossing points for an axis. |
| `AxisGroup` | Represents a type of a chart axis group. |
| `AxisScaleType` | Specifies the possible scale types for an axis. |
| `AxisTickLabelPosition` | Specifies the possible positions for tick labels. |
| `AxisTickMark` | Specifies the possible positions for tick marks. |
| `AxisTimeUnit` | Specifies the unit of time for axes. |
| `BaselineAlignment` | Specifies fonts vertical position on a line. |
| `BlockImportMode` | Specifies how properties of block-level elements are imported from HTML-based documents. |
| `BorderType` | Specifies sides of a border. |
| `BreakType` | Specifies type of a break inside a document. |
| `BuildingBlockBehavior` | Specifies the behavior that shall be applied to the contents of the building block when it is inserted into the main document. |
| `BuildingBlockGallery` | Specifies the predefined gallery into which a building block is classified. |
| `BuildingBlockType` | Specifies a building block type. |
| `CalendarType` | Specifies the type of a calendar. |
| `CellMerge` | Specifies how a cell in a table is merged with other cells. |
| `CellVerticalAlignment` | Specifies vertical justification of text inside a table cell. |
| `ChapterPageSeparator` | Defines the separator character that appears between the chapter and page number. |
| `ChartAxisType` | Specifies type of chart axis. |
| `ChartDataLabelLocationMode` | Specifies how the values ​​that specify the location of a data label - the Left and Top properties - are interpreted. |
| `ChartDataLabelPosition` | Specifies the position for a chart data label. |
| `ChartSeriesType` | Specifies a type of a chart series. |
| `ChartShapeType` | Specifies the shape type of chart elements. |
| `ChartStyle` | Specifies predefined styles of a chart. |
| `ChartType` | Specifies type of a chart. |
| `ChartXValueType` | Allows to specify type of an X value of a chart series. |
| `ChartYValueType` | Allows to specify type of an Y value of a chart series. |
| `ColorMode` | Specifies how colors are rendered. |
| `Compatibility` | Specifies names of compatibility options. |
| `CompressionLevel` | Compression level for OOXML files. |
| `ConditionalStyleType` | Represents possible table areas to which conditional formatting may be defined in a table style. |
| `ContentDisposition` | Enumerates different ways of presenting the document at the client browser. |
| `CssStyleSheetType` | Specifies how CSS (Cascading Style Sheet) styles are exported to HTML. |
| `DashStyle` | Dashed line style. |
| `DigitalSignatureType` | Specifies the type of a digital signature. |
| `Dml3DEffectsRenderingMode` | Specifies how 3D shape effects are rendered. |
| `DmlEffectsRenderingMode` | Specifies how DrawingML effects are rendered to fixed page formats. |
| `DmlRenderingMode` | Specifies how DrawingML shapes are rendered to fixed page formats. |
| `DocumentDirection` | Allows to specify the direction to flow the text in a document. |
| `DocumentRecoveryMode` | Specifies the available recovery options when a document encounters errors during loading. |
| `DocumentSecurity` | Used as a value for the Security property. |
| `DocumentSplitCriteria` | Specifies how the document is split into parts when saving to HTML, EPUB or AZW3 format. |
| `DropCapPosition` | Specifies the position for a drop cap text. |
| `EditingLanguage` | Specifies the editing language. |
| `EditorType` | Specifies the set of possible aliases (or editing groups) which can be used as aliases to determine if the current user shall be allowed to edit a single range defined by an editable range within a document. |
| `EmbeddedFontFormat` | Specifies format of particular embedded font inside FontInfo object. |
| `EmbeddedFontStyle` | Specifies the style of an embedded font inside a FontInfo object. |
| `EmfPlusDualRenderingMode` | Specifies how Aspose.Words should render EMF+ Dual metafiles. |
| `EmphasisMark` | Specifies possible types of emphasis mark. |
| `EndCap` | Specifies line cap style. |
| `EndnotePosition` | Defines the endnote position. |
| `ExportHeadersFootersMode` | Specifies how headers and footers are exported to HTML, MHTML or EPUB. |
| `ExportListLabels` | Specifies how list labels are exported to HTML, MHTML and EPUB. |
| `FieldIfComparisonResult` | Specifies the result of the IF field condition evaluation. |
| `FieldIndexFormat` | Specifies the formatting for the FieldIndex fields in a document. |
| `FieldType` | Specifies Microsoft Word field types. |
| `FieldUpdateCultureSource` | Indicates what culture to use during field update. |
| `FillType` | Specifies fill type for a fillable object. |
| `FindReplaceDirection` | Specifies direction for replace operations. |
| `FlipOrientation` | Possible values for the orientation of a shape. |
| `FontEmbeddingUsagePermissions` | Represents the font embedding usage permissions. |
| `FontFamily` | Represents the font family. |
| `FontPitch` | Represents the font pitch. |
| `FootnoteNumberingRule` | Determines when automatic footnote or endnote numbering restarts. |
| `FootnotePosition` | Defines the footnote position. |
| `FootnoteSeparatorType` | Specifies the type of the footnote/endnote separator. |
| `FootnoteType` | Specifies whether this is a footnote or an endnote. |
| `Forms2OleControlType` | Enumerates types of Forms 2.0 controls. |
| `GeneralFormat` | Specifies a general format that is applied to a numeric, text, or any field result. |
| `GradientStyle` | Specifies the style for a gradient fill. |
| `GradientVariant` | Specifies the variant for a gradient fill. |
| `HeaderFooterBookmarksExportMode` | Specifies how bookmarks in headers/footers are exported. |
| `HeaderFooterType` | Identifies the type of header or footer found in a Word file. |
| `HeightRule` | Specifies the rule for determining the height of an object. |
| `HorizontalAlignment` | Specifies horizontal alignment of a floating shape, text frame or floating table. |
| `HorizontalRuleAlignment` | Represents the alignment for the specified horizontal rule. |
| `HtmlControlType` | Type of document nodes that represent &lt;input&gt; and &lt;select&gt; elements imported from HTML. |
| `HtmlElementSizeOutputMode` | Specifies how Aspose.Words exports element widths and heights to HTML, MHTML and EPUB. |
| `HtmlInsertOptions` | Specifies options for the InsertHtml(string, HtmlInsertOptions) method. |
| `HtmlMetafileFormat` | Indicates the format in which metafiles are saved to HTML documents. |
| `HtmlOfficeMathOutputMode` | Specifies how Aspose.Words exports OfficeMath to HTML, MHTML and EPUB. |
| `HtmlVersion` | Indicates the version of HTML is used when saving the document to HTML and MHTML formats. |
| `ImageBinarizationMethod` | Specifies the method used to binarize image. |
| `ImageColorMode` | Specifies the color mode for the generated images of document pages. |
| `ImagePixelFormat` | Specifies the pixel format for the generated images of document pages. |
| `ImageType` | Specifies the type (format) of an image in a Microsoft Word document. |
| `ImlRenderingMode` | Specifies how ink (InkML) objects are rendered to fixed page formats. |
| `ImportFormatMode` | Specifies how formatting is merged when importing content from another document. |
| `JoinStyle` | Line join style. |
| `JustificationMode` | Specifies the character spacing adjustment for a document. |
| `LayoutFlow` | Determines the flow of the text layout in a textbox. |
| `LegendPosition` | Specifies the possible positions for a chart legend. |
| `LineNumberRestartMode` | Determines when automatic line numbering restarts. |
| `LineSpacingRule` | Specifies line spacing values for a paragraph. |
| `LineStyle` | Specifies line style of a Border. |
| `ListLevelAlignment` | Specifies alignment for the list number or bullet. |
| `ListTemplate` | Specifies one of the predefined list formats available in Microsoft Word. |
| `ListTrailingCharacter` | Specifies the character that separates the list label from the text of the paragraph. |
| `LoadFormat` | Indicates the format of the document that is to be loaded. |
| `MailMergeCheckErrors` | Specifies how Microsoft Word will report errors detected during mail merge. |
| `MailMergeDataType` | Specifies the type of an external mail merge data source. |
| `MailMergeDestination` | Specifies the possible results which may be generated when a mail merge is carried out on a document. |
| `MailMergeMainDocumentType` | Specifies the possible types for a mail merge source document. |
| `Margins` | Specifies preset margins. |
| `MarkdownEmptyParagraphExportMode` | Specifies how Aspose.Words exports empty paragraphs to Markdown. |
| `MarkdownExportAsHtml` | Allows to specify the elements to be exported to Markdown as raw HTML. |
| `MarkdownLinkExportMode` | Specifies how links are exported into Markdown. |
| `MarkdownListExportMode` | Specifies how lists are exported into Markdown. |
| `MarkdownOfficeMathExportMode` | Specifies how Aspose.Words exports OfficeMath to Markdown. |
| `MarkerSymbol` | Specifies marker symbol style. |
| `MarkupLevel` | Specifies the level in the document tree where a particular StructuredDocumentTag can occur. |
| `MathObjectType` | Specifies type of an Office Math object. |
| `MeasurementUnits` | Specifies the unit of measurement. |
| `MergeFieldImageDimensionUnit` | Specifies an unit of an image dimension (i.e. |
| `MsWordVersion` | Allows Aspose.Wods to mimic MS Word version-specific application behavior. |
| `MultiplePagesType` | Specifies how document is printed out. |
| `NodeChangingAction` | Specifies the type of node change. |
| `NodeType` | Specifies the type of a Word document node. |
| `NumSpacing` | Specifies possible values in which numeral spacing can be displayed. |
| `NumberStyle` | Specifies the number style for a list, footnotes and endnotes, page numbers. |
| `NumeralFormat` | Indicates the symbol set that is used to represent numbers while rendering to fixed page formats. |
| `OdsoDataSourceType` | Specifies the type of the external data source to be connected to as part of the ODSO connection information. |
| `OdsoFieldMappingType` | Specifies the possible types used to indicate if a given mail merge field has been mapped to a column in the given external data source. |
| `OfficeMathDisplayType` | Specifies the display format type of the equation. |
| `OfficeMathJustification` | Specifies the justification of the equation. |
| `OoxmlCompliance` | Allows to specify which OOXML specification will be used when saving in the DOCX format. |
| `Orientation` | Specifies page orientation. |
| `OutlineLevel` | Specifies the outline level of a paragraph in the document. |
| `PageBorderAppliesTo` | Specifies which pages the page border is printed on. |
| `PageBorderDistanceFrom` | Specifies the positioning of the page border relative to the page margin. |
| `PageVerticalAlignment` | Specifies vertical justification of text on each page. |
| `PaperSize` | Specifies paper size. |
| `ParagraphAlignment` | Specifies text alignment in a paragraph. |
| `PatternType` | Specifies the fill pattern to be used to fill a shape. |
| `PreferredWidthType` | Specifies the unit of measurement for the preferred width of a table or cell. |
| `PresetTexture` | Specifies texture to be used to fill a shape. |
| `PropertyType` | Specifies data type of a document property. |
| `ProtectionType` | Protection type for a document. |
| `RelativeHorizontalPosition` | Specifies to what the horizontal position of a shape or text frame is relative. |
| `RelativeHorizontalSize` | Specifies relatively to what the width of a shape or a text frame is calculated horizontally. |
| `RelativeVerticalPosition` | Specifies to what the vertical position of a shape or text frame is relative. |
| `RelativeVerticalSize` | Specifies relatively to what the height of a shape or a text frame is calculated vertically. |
| `ReplaceAction` | Allows the user to specify what happens to the current match during a replace operation. |
| `ReplacementFormat` | Specifies the replacement format. |
| `ResourceLoadingAction` | Specifies the mode of resource loading. |
| `ResourceType` | Type of loaded resource. |
| `RevisionType` | Identifies the kind of tracked change a `Revision` represents — insertion, deletion, formatting change, style-definition change, or a move. |
| `RevisionsView` | Allows to specify whether to work with the original or revised version of a document. |
| `SaveFormat` | Indicates the format in which the document is saved. |
| `SdtAppearance` | Specifies the appearance of a structured document tag. |
| `SdtCalendarType` | Specifies the possible types of calendars which can be used to specify CalendarType in an Office Open XML document. |
| `SdtDateStorageFormat` | Specifies how the date for a date SDT is stored/retrieved when the SDT is bound to an XML node in the document's data store. |
| `SdtType` | Specifies the type of a structured document tag (SDT) node. |
| `SectionLayoutMode` | Specifies the layout mode for a section allowing to define the document grid behavior. |
| `SectionStart` | The type of break at the beginning of the section. |
| `ShadowType` | Specifies the type of a shape shadow. |
| `ShapeLineStyle` | Specifies the compound line style of a Shape. |
| `ShapeMarkupLanguage` | Identifies whether a shape is defined using modern DrawingML (`Dml`) or legacy VML (`Vml`) markup. |
| `ShapeTextOrientation` | Specifies orientation of text in shapes. |
| `ShapeType` | Specifies the type of shape in a Microsoft Word document. |
| `SourceType` | Represents bibliography source types. |
| `StoryType` | Text of a Word document is stored in stories. |
| `StyleIdentifier` | Locale independent style identifier. |
| `StyleType` | Represents type of the style. |
| `SvgTextOutputMode` | Allows to specify how text inside a document should be rendered when saving in SVG format. |
| `TabAlignment` | Specifies the alignment/type of a tab stop. |
| `TabLeader` | Specifies the type of the leader line displayed under the tab character. |
| `TableAlignment` | Specifies alignment for an inline table. |
| `TableContentAlignment` | Allows to specify the alignment of the content of the table to be used when exporting into Markdown format. |
| `TableStyleOptions` | Specifies how table style is applied to a table. |
| `TaskPaneDockState` | Enumerates available locations of task pane object. |
| `TextBoxAnchor` | Specifies values used for shape text vertical alignment. |
| `TextBoxWrapMode` | Specifies how text wraps inside a shape. |
| `TextDmlEffect` | Dml text effect for text runs. |
| `TextEffect` | Animation effect for text runs. |
| `TextFormFieldType` | Specifies the type of a text form field. |
| `TextOrientation` | Specifies orientation of text on a page, in a table cell or a text frame. |
| `TextPathAlignment` | WordArt alignment. |
| `TextWrapping` | Specifies how text is wrapped around the table. |
| `TextureAlignment` | Specifies the alignment for the tiling of the texture fill. |
| `TextureIndex` | Specifies shading texture. |
| `ThemeColor` | Specifies the theme colors for document themes. |
| `ThemeFont` | Specifies the types of theme font names for document themes. |
| `TiffCompression` | Specifies what type of compression to apply when saving page images into a TIFF file. |
| `TxtExportHeadersFootersMode` | Specifies the way headers and footers are exported to plain text format. |
| `TxtLeadingSpacesOptions` | Specifies available options for leading space handling during import from Text file. |
| `TxtOfficeMathExportMode` | Specifies how Aspose.Words exports OfficeMath to Text. |
| `TxtTrailingSpacesOptions` | Specifies available options for trailing spaces handling during import from Text file. |
| `Underline` | Indicates type of the underline applied to a font. |
| `VbaModuleType` | Specifies the type of a model in a VBA project. |
| `VbaReferenceType` | Allows to specify the type of a VbaReference object. |
| `VerticalAlignment` | Specifies vertical alignment of a floating shape, text frame or a floating table. |
| `ViewType` | Possible values for the view mode in Microsoft Word. |
| `VisitorAction` | Allows the visitor to control the enumeration of nodes. |
| `WarningSource` | Specifies the module that produces a warning during document loading or saving. |
| `WarningType` | Specifies the type of a warning that is issued by Aspose.Words during document loading or saving. |
| `WatermarkLayout` | Defines layout of the watermark relative to the watermark center. |
| `WatermarkType` | Specifies the watermark type. |
| `WebExtensionBindingType` | Enumerates available types of binding between a web extension and the data in the document. |
| `WebExtensionStoreType` | Enumerates available types of a web extension store. |
| `WrapSide` | Specifies what side(s) of the shape or picture the text wraps around. |
| `WrapType` | Specifies how text is wrapped around a shape or picture. |
| `XmlDsigLevel` | Specifies the level of a digital signature based on XML-DSig standard. |
| `Zip64Mode` | Specifies when to use ZIP64 format extensions for OOXML files. |
| `ZoomType` | Possible values for how large or small the document appears on the screen in Microsoft Word. |

- `Document`
  - `Document()` / `Document(fileName)` / `Document(fileName, loadOptions)` / `Document(stream)` / `Document(stream, loadOptions)`
  - `Save(fileName)` / `Save(fileName, saveFormat)` / `Save(fileName, saveOptions)` / `Save(stream, saveFormat)` / `Save(stream, saveOptions)`
  - `GetText() -> string`
  - `AppendDocument(srcDoc, importFormatMode)`, `ImportNode(srcNode, isImportChildren)`
  - `StartTrackRevisions(author, dateTime)` / `StopTrackRevisions()` / `AcceptAllRevisions()`
  - `UpdateFields()`, `UpdateTableLayout()`, `UpdateListLabels()`
  - `Protect(type, password)` / `Unprotect(password)`
  - Properties: `FirstSection`, `LastSection`, `Sections -> SectionCollection`, `Styles -> StyleCollection`, `Revisions -> RevisionCollection`, `TrackRevisions: bool`, `HasRevisions: bool`, `DigitalSignatures -> DigitalSignatureCollection`, `BuiltInDocumentProperties`, `ProtectionType`, `OriginalLoadFormat: LoadFormat`

- `DocumentBuilder`
  - `DocumentBuilder()` / `DocumentBuilder(doc)`
  - `Write(text)` / `Writeln(text)` / `Writeln()`
  - `InsertParagraph()`, `InsertBreak(breakType)`, `InsertField(fieldCode)`, `InsertHyperlink(displayText, urlOrBookmark, isBookmark)`
  - `InsertImage(fileName, width, height)`, `InsertChart(chartType, width, height)`
  - `StartTable()` / `InsertCell()` / `EndRow()` / `EndTable()`
  - `StartBookmark(bookmarkName)` / `EndBookmark(bookmarkName)`
  - Properties: `Document -> Document`, `Font -> Font`, `ParagraphFormat -> ParagraphFormat`, `ListFormat -> ListFormat`, `PageSetup -> PageSetup`, `CurrentParagraph -> Paragraph`, `CurrentSection -> Section`

- `SaveFormat` (enum) — `Docx`, `Docm`, `Dotx`, `Dotm`, `FlatOpc`, `FlatOpcMacroEnabled`, `FlatOpcTemplate`, `FlatOpcTemplateMacroEnabled`, `Text`, `Markdown`, plus additional values inherited from the shared engine that are not functional in this edition (see Scope and Limitations)

- `LoadFormat` (enum) — `Auto`, `Docx`, `Docm`, `Dotx`, `Dotm`, `FlatOpc`, `FlatOpcMacroEnabled`, `FlatOpcTemplate`, `FlatOpcTemplateMacroEnabled`, `Text`, `Markdown`, plus additional values inherited from the shared engine that are not functional in this edition

- `LoadOptions` — `LoadOptions()` / `LoadOptions(password)` / `LoadOptions(loadFormat, password, baseUri)`

- `Section`, `Body`, `Paragraph`, `Run` — the core node tree; each `Node` supports `GetText()`, `GetChildNodes(nodeType, isDeep)`, `Clone(isCloneChildren)`, `Remove()`

- `Table`, `Row`, `Cell` — table structure, built with `DocumentBuilder.StartTable()` / `InsertCell()` / `EndRow()` / `EndTable()`, or `DeleteRow(tableIndex, rowIndex)`

- `Bookmark` — `Name: string`, `Text: string`, `BookmarkStart`, `BookmarkEnd`, `Remove()`; `BookmarkCollection`

- `HeaderFooter` — `HeaderFooter(doc, headerFooterType)`, `AppendParagraph(text)`, `GetText()`; reached via `DocumentBuilder.MoveToHeaderFooter(headerFooterType)`

- `Comment`, `Footnote` — inserted via `DocumentBuilder.InsertFootnote(footnoteType, footnoteText)`; comments carry author, date, and reply threading

- `Style`, `StyleCollection` — `Style.Name`, `StyleIdentifier`, `Type: StyleType`, `BaseStyleName`; `Font` — `Name`, `NameAscii/NameBi/NameFarEast/NameOther`, `ClearFormatting()`

- `ParagraphFormat` — `Alignment`, `KeepTogether`, `KeepWithNext`, `PageBreakBefore`, `ClearFormatting()`

- `Field` — `GetFieldCode()`, `Update()`, `Unlink()`, `Remove()`; `Type: FieldType`, `Result: string`; `FieldCollection` — `Remove(field)`, `Clear()`, `Count`

- `Revision` — `Accept()` / `Reject()`; `Author`, `DateTime`, `RevisionType`; `RevisionCollection` — `AcceptAll()` / `RejectAll()`, `Groups -> RevisionGroupCollection`

- `DigitalSignature` — `SignatureType`, `SignTime`, `SubjectName`, `IssuerName`, `IsValid: bool`, `CertificateHolder`; `DigitalSignatureCollection` — read-only, `IsValid: bool`, `Count`

- `CertificateHolder` — `Create(certBytes, password)` / `Create(fileName, password)`; `Certificate -> X509Certificate2`

- `Chart` — `Series -> ChartSeriesCollection`, `Legend -> ChartLegend`, `Title -> ChartTitle`, `AxisX/AxisY/AxisZ -> ChartAxis`, `DataTable -> ChartDataTable`

- `ChartSeries` — `Add(xValue, yValue)`, `Insert(index, xValue, yValue)`, `Remove(index)`, `Clear()`, `ClearValues()`

- `ChartAxis` — `Type`, `CategoryType`, `Crosses`, `MajorUnit`, `MajorTickMark`, `MinorTickMark`

- `ChartLegend` — `LegendEntries -> ChartLegendEntryCollection`, `Position: LegendPosition`, `Font -> Font`

- `ChartDataLabel` — `ShowValue`, `ShowCategoryName`, `ShowPercentage`, `Position`, `ClearFormat()`

The full surface totals 618 public types across the Core API, interfaces, and enumerations. See the [full API reference](#documentation--resources) below for every type.

</details>

## Documentation & Resources

- **[Additional examples](#additional-examples)** — Additional examples demonstrate practical usage scenarios for Aspose.Words FOSS for .NET.
- **[Documentation & resources](#documentation--resources)** — Documentation & resources provides guidance and supporting materials for Aspose.Words FOSS for .NET.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-.NET/issues).

## Scope and Limitations

Aspose.Words FOSS for .NET reads and writes DOCX, DOCM, DOTX, DOTM, Flat OPC, Markdown, and plain TEXT formats, and supports .NET Standard 2.0, .NET 8.0, and .NET Framework 4.62.

- It does not save to PDF, XPS, or images, nor does it support printing, and layout-dependent field values such as page numbers in a table of contents or NUMPAGES evaluate to zero.
- Additional formats such as DOC, RTF, ODT, HTML, and EPUB are not read or written in this edition.
- Mail merge, LINQ Reporting, document comparison, document signing, and embedded-font subsetting are not included.

| Format | Load | Save |
|---|:---:|:---:|
| DOCX / DOCM / DOTX / DOTM | ✅ | ✅ |
| Flat OPC (all variants) | ✅ | ✅ |
| Markdown | ✅ | ✅ |
| Plain text | ✅ | ✅ |

The engine underneath already knows how to handle far more (see the story below), and more formats may be opened over time. If you need a format that is not in the table, you have two options: [open an issue](../../issues) to request it, and we will consider open-sourcing it, or get it right away in the commercial [Aspose.Words for .NET](https://products.aspose.com/words/net/), which reads and writes all of them today.

To keep this edition free, the subsystems that power Aspose's commercial offering were removed. To be upfront about it:

- **Page layout and rendering.** No saving to PDF, XPS, or images, and no printing. This also means layout-dependent field values (such as page numbers in a TOC or `NUMPAGES`) evaluate to `0` rather than being computed.
- **Additional formats.** DOC, RTF, ODT, HTML, EPUB, and others are not read or written in this edition.
- **Mail merge, LINQ Reporting, document comparison, document signing, and embedded-font subsetting** are not included.

One important thing to know: what's included today is the *minimum*, the commercial codebase reduced as far as it would go. It is not the final shape of the project, and the boundary is not set in stone. If a feature you need sits on the wrong side of it, [open an issue](../../issues) and tell us about your use case. Where there is real demand, we will consider opening up more of the code.

- **[Getting started guide](https://docs.aspose.org/words/net/)** — installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/words/net/)** — task-focused answers for common Word-document-processing questions.
- **[Full API reference](https://reference.aspose.org/words/net/)** — the complete, browsable reference for all 618 public types (the [API reference](#api-reference) section above covers the essentials).
- **[Agent and contributor guide](AGENTS.md)** — usage recipes for AI coding assistants, plus build, test, and code-style conventions for anyone changing this repository.
- The public API matches the commercial [Aspose.Words for .NET](https://docs.aspose.com/words/net/), so its official documentation and thousands of examples largely apply here too, within this edition's supported feature set.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-.NET/issues) on GitHub — pull requests are welcome too; for anything non-trivial, open an issue first so the approach can be discussed.

These limitations don't apply to [full-featured Aspose.Words for .NET — Enterprise Edition](https://products.aspose.com/words/net/). If your project grows into needing any of the above, the commercial Aspose.Words for .NET has all of it. And because this library is that codebase, upgrading is essentially swapping the package reference. Your code carries over.

## Development and Testing

The toolchain requires a recent .NET SDK and uses the dotnet CLI to build the solution and run tests. Tests are implemented with NUnit 3 and reside in the `Aspose.Words.Tests/` directory, where many compare generated output against gold files under TestGold/ and report mismatches with diff-style failure messages. The project layout includes Aspose.Words/ as the engine, `Aspose.Foundation`/ as supporting infrastructure, and `Aspose.Words.Tests/` as the test suite, with code-style conventions documented in `AGENTS.md`.

The suite covers 307 test files under `Aspose.Words.Tests/`.

The package ships a single assembly, `Aspose.Words.FOSS.dll`, for all three targets. The namespaces are `Aspose.Words.*` — the same as the commercial product, so existing Aspose.Words code compiles against it as is.

Or build from source:

```bash
git clone https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-.NET.git
cd Aspose.Words-FOSS-for-.NET
dotnet build Aspose.Words.sln -c Release
```

Then add a project reference to `Aspose.Words/Aspose.Words.csproj` from your application.

- `SkiaSharp` 3.119.0 — cross-platform image decoding/encoding, used by the .NET Standard 2.0 and .NET 8 targets. On .NET Framework the in-box GDI+ (System.Drawing) is used instead.
- `BitMiracle.LibTiff.NET` 2.4.649 — TIFF image codec support, used by the .NET Standard 2.0 and .NET 8 targets.
- `System.Text.Encoding.CodePages` 7.0.0 - legacy code-page encodings, used by the .NET Standard 2.0 and .NET 8 targets.
- `Microsoft.Win32.Registry` 5.0.0 — Windows registry access, used only by the .NET Standard 2.0 target (not referenced by the .NET Framework or .NET 8 builds).

Requirements: a recent .NET SDK. Tests use NUnit 3.

```bash
dotnet build Aspose.Words.sln -c Release
dotnet test Aspose.Words.Tests/Aspose.Words.Tests.csproj
```

See [`AGENTS.md`](AGENTS.md) for the project layout (`Aspose.Words/` is the engine, `Aspose.Foundation/` supporting infrastructure, `Aspose.Words.Tests/` the test suite) and code-style conventions.

Bug reports and feature requests are very welcome, please [open an issue](../../issues). Pull requests are considered case by case; for anything non-trivial, it is best to open an issue first so we can discuss the approach.

This project is brand new, and stars are how GitHub decides whether anyone else gets to discover it. If Aspose.Words FOSS for .NET looks useful to you:

- **Star** the repo. It takes one click and helps more than anything else.
- **Watch** it (Releases only is fine) to hear about new features first. The NuGet package and new formats are landing soon.
- **Tell someone.** A mention in a blog post, a team chat, or an answer on Stack Overflow means a lot to a young project.

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
