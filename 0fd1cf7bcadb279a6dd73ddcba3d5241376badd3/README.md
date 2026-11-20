# Aspose.Note FOSS for Python

[![PyPI version](https://img.shields.io/pypi/v/aspose-note-foss.svg)](https://pypi.org/project/aspose-note-foss/) ![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg) [![CI](https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/actions/workflows/ci.yml/badge.svg)](https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Python Versions](https://img.shields.io/pypi/pyversions/aspose-note-foss.svg)](https://pypi.org/project/aspose-note-foss/)

[![Aspose.Note FOSS for Python](https://products.aspose.org/media/note/python/banner-readme.png)](https://products.aspose.org/note/python/)

Aspose.Note FOSS for Python reads `.one` files and writes `.pdf` files. It converts documents by loading them with `aspose.note.Document` and saving them with `Document.Save` using `SaveFormat.Pdf` or `PdfSaveOptions`. It extracts content such as images, attached files, tables, and rich text with formatting and tags from loaded documents.

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
  subgraph StartingPoints["Starting Points"]
    direction TB
    i1["An existing ONE file"]
  end
  PRODUCT["Aspose.Note FOSS for Python"]
  subgraph Capabilities["Core Capabilities"]
    direction TB
    c1["Parse OneNote<br/>documents"]
    c2["Extract rich text and<br/>formatting"]
    c3["Extract images and<br/>attachments"]
    c4["Inspect tables and<br/>tags"]
    c5["Export to PDF"]
    c6["Traverse document tree"]
    c7["Inspect numbered lists"]
    c8["Handle document<br/>metadata"]
    c1 ~~~ c4
    c2 ~~~ c5
    c3 ~~~ c6
    c4 ~~~ c7
    c5 ~~~ c8
    c6 ~~~ c8
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["PDF file"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
  classDef product fill:#1f6feb,stroke:#1f6feb,color:#ffffff
  class PRODUCT product
```

## Key Capabilities

- **Parse OneNote documents.** It parses OneNote documents from file paths or binary streams into a document object model, supporting pages, outlines, outline elements, rich text, images, tables, and attached files without requiring Microsoft OneNote or COM automation.
- **Extract rich text and formatting.** It extracts rich text content and per-run formatting including bold, italic, underline, strikethrough, superscript, subscript, font name, font size, font color, and hyperlinks through `TextRun` and `TextStyle` objects.
- **Extract images and attachments.** It extracts embedded images and attached files by providing access to their bytes, file names, and metadata, enabling direct saving to disk.
- **Inspect tables and tags.** It inspects tables through rows, cells, and columns, and reads OneNote tags such as yellow star, question mark, and musical note attached to text, images, and tables.
- **Export to PDF.** It exports documents to PDF format using `SaveFormat.Pdf` or `PdfSaveOptions`, supporting page range control via `PageIndex` and `PageCount` settings.
- **Traverse document tree.** It traverses the document tree using `CompositeNode.GetChildNodes` for type-based node search or the `DocumentVisitor` pattern for comprehensive node-by-node processing.
- **Inspect numbered lists.** It inspects numbered lists by exposing list format, number format, and restart behavior through the `NumberList` object attached to outline elements.
- **Handle document metadata.** It handles document metadata through page properties such as title, author, creation time, and level, plus revision history via `PageHistory` and `Document.GetPageHistory`.

- Read page metadata through `Page.Title`, `Page.Author`, `Page.CreationTime`, and `Page.Level`, plus revision history via `PageHistory` and `Document.GetPageHistory()`.
- Extract rich text with per-run formatting through `TextRun` and `TextStyle` (bold, italic, underline, strikethrough, superscript, subscript, font, color, hyperlinks) and paragraph-level styling via `RichText.ParagraphStyle`.

## Installation

Install the published package from PyPI (`aspose-note-foss`, version 26.9.0):

```bash
pip install aspose-note-foss
```

To work from a source checkout instead, install the clone with pip:

```bash
git clone https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python.git
cd Aspose.Note-FOSS-for-Python
pip install .
```

Verify the install:

```bash
python -c "import aspose.note"
```

Requires Python 3.10 or later.

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `pyproject.toml`, the `project.dependencies` list is empty.

### Optional Dependencies

- `reportlab>=3.6` (extra `pdf`)
- `Pillow>=10.0` (extra `test-pdf`)
- `PyMuPDF>=1.25` (extra `test-pdf`)
- `pypdf>=5.3` (extra `test-pdf`)

### Native and System Requirements

- Requires Python 3.10 or later.

### Development Dependencies

- `build>=1.2` (extra `dev`)
- `twine>=5.0` (extra `dev`)

## Quick Start

This example opens a OneNote file named `SimpleTable.one` and saves it as a PDF document named `out.pdf` using the `SaveFormat.Pdf` option.

```python
from aspose.note import Document, SaveFormat

doc = Document("SimpleTable.one")
doc.Save("out.pdf", SaveFormat.Pdf)
```

PDF export needs the optional `pdf` extra, which pulls in [ReportLab](https://pypi.org/project/reportlab/):

```bash
pip install "aspose-note-foss[pdf]"
```

The PyPI distribution is named `aspose-note-foss`; the import package is
`aspose.note` — `from aspose.note import Document`.

## Additional Examples

The following workflows demonstrate reading, inspecting, and exporting OneNote documents using Aspose.Note FOSS for Python.

### Save Embedded Images to Disk by Iterating over `Image` Nodes and Writing Their Bytes to Files

```python
from pathlib import Path
from aspose.note import Document, Image

out_dir = Path("out_images")
out_dir.mkdir(exist_ok=True)

doc = Document("3ImagesWithDifferentAlignment.one")
for i, img in enumerate(doc.GetChildNodes(Image), start=1):
    name = img.FileName or f"image_{i}.png"
    (out_dir / name).write_bytes(img.Bytes)
```

<details>
<summary>View Additional Examples</summary>

### Load a Document from a Binary Stream by Passing an Open File Handle To `Document`

```python
from aspose.note import Document

with open("SimpleTable.one", "rb") as f:
    doc = Document(f)
print(doc.DisplayName, len(list(doc)))
```

### Traverse Tables, Rows, and Cells to Extract Text from Each Cell by Joining `RichText` Content

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("SimpleTable.one")
for table in doc.GetChildNodes(Table):
    for row in table.GetChildNodes(TableRow):
        cells = row.GetChildNodes(TableCell)
        values = [" ".join(rt.Text for rt in cell.GetChildNodes(RichText)) for cell in cells]
        print(values)
```

### Extract Attached Files from a Document by Iterating over `AttachedFile` Nodes and Writing Their Bytes to Disk

```python
from pathlib import Path
from aspose.note import Document, AttachedFile

doc = Document("OnePageWithFile.one")
for i, af in enumerate(doc.GetChildNodes(AttachedFile), start=1):
    name = af.FileName or f"attachment_{i}.bin"
    Path(name).write_bytes(af.Bytes)
```

### Inspect OneNote Tags on Text by Iterating over `RichText` Nodes and Their Tags, Printing Each Tag's Label and Status

```python
from aspose.note import Document, RichText

doc = Document("TagSizes.one")
for rt in doc.GetChildNodes(RichText):
    for tag in rt.Tags:
        print(tag.Label, tag.Status)
```

### Count Nodes Using a `DocumentVisitor` by Subclassing It and Overriding `VisitPageStart`, `VisitRichTextStart`, And `VisitImageStart`

```python
from aspose.note import Document, DocumentVisitor, Page, Image, RichText

class Counter(DocumentVisitor):
    def __init__(self):
        self.pages = 0
        self.rich_texts = 0
        self.images = 0

    def VisitPageStart(self, page: Page) -> None:
        self.pages += 1

    def VisitRichTextStart(self, rich_text: RichText) -> None:
        self.rich_texts += 1

    def VisitImageStart(self, image: Image) -> None:
        self.images += 1

doc = Document("3ImagesWithDifferentAlignment.one")
counter = Counter()
doc.Accept(counter)
print(counter.pages, counter.rich_texts, counter.images)
```

### Extract All Text from a Document by Collecting the Text Property from Each `RichText` Node

```python
from aspose.note import Document, RichText

doc = Document("FormattedRichText.one")
texts = [rt.Text for rt in doc.GetChildNodes(RichText)]
print("\n".join(texts))
```

### Export to PDF with Custom Options by Passing `PdfSaveOptions` with `JpegQuality` Set To `Document.Save`

```python
from aspose.note import Document, SaveFormat
from aspose.note.saving import PdfSaveOptions

doc = Document("TagSizes.one")
opts = PdfSaveOptions(JpegQuality=90)
doc.Save("out.pdf", opts)
```

### Extract Hyperlinks from Text Runs by Checking `TextRun.Style.IsHyperlink` And `TextRun.Style.HyperlinkAddress`

```python
from aspose.note import Document, RichText

doc = Document("FormattedRichText.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.TextRuns:
        if run.Style.IsHyperlink and run.Style.HyperlinkAddress:
            print(run.Text, "->", run.Style.HyperlinkAddress)
```

### Inspect Numbered List Properties by Reading `NumberList.Format`, `NumberFormat`, and Restart on `OutlineElement` Nodes

```python
from aspose.note import Document, OutlineElement

doc = Document("NumberedListWithTags.one")
for oe in doc.GetChildNodes(OutlineElement):
    nl = oe.NumberList
    if nl is None:
        continue
    print("format=", nl.Format, "number_format=", nl.NumberFormat, "restart=", nl.Restart)
```

More real, runnable scripts are available in [`examples/`](examples/). The most illustrative one
beyond Quick Start is saving every embedded image to disk.

Runnable example scripts have their own setup and usage notes in
[`examples/README.md`](examples/README.md).
[`publish-pypi.yml`](.github/workflows/publish-pypi.yml) shows the exact release-time commands
this project runs in CI.

</details>

## API Reference

The primary entry point is `aspose.note.Document`, which loads a `.one` file and exposes its pages as a tree of nodes; `Document.Save()` writes the document to PDF. The supported public entry points are `aspose.note` and `aspose.note.saving`.

The public API has 37 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `AttachedFile` | AttachedFile class holds the file name, raw bytes, and tags of an attached file. |
| `Document` | Document class represents a OneNote document and provides methods to detect layout changes, get page history, and save the document. |
| `DocumentVisitor` | DocumentVisitor class provides methods to visit document, page, outline, outline element, rich text, image, and title nodes. |
| `FileCorruptedException` | FileCorruptedException class represents an error raised when a file is corrupted. |
| `Image` | Image class holds the image bytes, file name, file path, format, original dimensions, alignment, and tags of an image. |
| `IncorrectDocumentStructureException` | Declared; not thrown by library code. |
| `IncorrectPasswordException` | IncorrectPasswordException class represents an error raised when a document password is incorrect. |
| `License` | License class provides a method to set the license. |
| `LoadOptions` | LoadOptions class holds options for loading a document. |
| `Metered` | Metered class provides a method to set the metered key. |
| `Node` | Node class provides methods to accept a visitor, and read-only properties for the document and parent node. |
| `NoteTag` | NoteTag class holds the creation time, completed time, icon, label, font color, highlight, and status of a note tag. |
| `NumberList` | NumberList class provides a method to get the number list header. |
| `Outline` | Outline class represents an outline node. |
| `OutlineElement` | OutlineElement class represents an outline element node. |
| `Page` | Page class provides a method to clone the page. |
| `PageHistory` | PageHistory class provides methods to add, remove, clear, and query pages, and a read-only property for the current page. |
| `ParagraphStyle` | ParagraphStyle class provides a method to get the default style and a read-only property for the font style. |
| `RichText` | RichText class provides methods to append, insert, clear, and replace text, and properties for alignment and title date. |
| `Table` | Table class holds the columns and tags of a table. |
| `TableCell` | TableCell class represents a table cell node. |
| `TableColumn` | TableColumn class represents a table column. |
| `TableRow` | TableRow class represents a table row node. |
| `TextRun` | TextRun class represents a text run node. |
| `TextStyle` | TextStyle class provides methods to get default styles and properties for font color, font name, font size, and font style. |
| `Title` | Title class holds the title text, title date, and title time of a page title. |
| `UnsupportedFileFormatException` | UnsupportedFileFormatException class represents an error raised when a file format is unsupported, and holds the file format. |
| `UnsupportedSaveFormatException` | UnsupportedSaveFormatException class represents an error raised when a save format is unsupported. |
| `AsposeNoteError` | AsposeNoteError class is the base exception class for Aspose.Note errors. |
| `CompositeNode` | CompositeNode class provides methods to append, insert, and remove child nodes, and read-only properties for the first and last child. |
| `PdfSaveOptions` | PdfSaveOptions class represents options for saving a document to PDF. |
| `SaveOptions` | SaveOptions class provides a read-only property for the save format. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `FileFormat` | FileFormat enum lists the OneNote file format values: OneNote2007, OneNote2010, OneNoteOnline, and Unknown. |
| `HorizontalAlignment` | HorizontalAlignment enum lists the horizontal alignment values: Left, Center, and Right. |
| `NodeType` | NodeType enum lists the node type values: AttachedFile, Document, Image, Outline, OutlineElement, Page, RichText, and Table. |
| `SaveFormat` | SaveFormat enum lists the save format value: Pdf. |
| `TagStatus` | TagStatus enum lists the tag status values: Completed, Disabled, and Open. |

#### Detailed Member Reference

### Document

The `aspose.note.Document` class loads a OneNote file from a path or a binary stream, exposes its pages via iteration, provides `GetPageHistory` to access page version history, and writes the document to PDF using Save with `SaveFormat.Pdf` or `PdfSaveOptions`.

### Page

The `aspose.note.Page` class represents a page in a OneNote document, provides access to its `Title`, and supports cloning; `aspose.note.PageHistory` manages page versions with methods such as Add and Remove and exposes a Current property, while `aspose.note.Title` holds the page's title text, date, and time as `RichText` nodes.

### RichText

The `aspose.note.RichText` class holds formatted text with a Text property, a list of `TextRun` objects, and styling via `TextStyle`; it supports text manipulation methods such as Append, Insert, Remove, and Replace, and exposes alignment, tags, and paragraph style.

### Image

The `aspose.note.Image` class represents an embedded image, exposing its `FileName`, raw Bytes, and dimensions, and supports tags and alternative text; examples show how to extract and save images from a document.

### Table

The `aspose.note.Table` class represents a table with columns and cells, exposing its Columns and border visibility; examples show how to iterate over tables, rows, and cells to extract cell text.

### AttachedFile

The `aspose.note.AttachedFile` class represents an attached file, exposing its `FileName` and raw Bytes, and supports tags; examples show how to extract and save attached files from a document.

### SaveFormat

The `aspose.note.SaveFormat` enumeration lists supported output formats; currently only Pdf is supported, producing `.pdf` files.

### saving

The `aspose.note.saving` module provides `PdfSaveOptions` for PDF export, exposing options such as `JpegQuality` and `ImageCompression`, though only page range settings affect output.

### DocumentVisitor

The `aspose.note.DocumentVisitor` class enables custom traversal of a document's node tree via visitor methods such as `VisitPageStart`, `VisitRichTextStart`, and `VisitImageStart`; examples show how to count pages, rich text nodes, and images.

### NumberList

The `aspose.note.NumberList` class represents a numbered list, exposing properties such as Format, `NumberFormat`, and Restart; examples show how to inspect numbered list settings on outline elements.

### NoteTag

The `aspose.note.NoteTag` class represents a OneNote tag, exposing its Label, Status, and Icon; examples show how to iterate over tags attached to rich text nodes.

### exceptions

The `aspose.note.exceptions` module defines exceptions such as `FileCorruptedException`, `IncorrectPasswordException`, `UnsupportedFileFormatException`, and `UnsupportedSaveFormatException`, which are raised when loading or saving documents encounters unsupported or invalid data.

The
supported public entry points are `aspose.note` and `aspose.note.saving` — everything under
`aspose.note._internal` is an implementation detail and may change.

| Class | Description |
|---|---|
| `AsposeNoteError` | Base exception for the library; all other library exceptions inherit from it. |
| `AttachedFile` | A file attached to a page — exposes its raw `Bytes`, `FileName`, and `Tags`. |
| `CompositeNode` | Base class for every container node (`Document`, `Page`, `Table`, ...); provides child-node access and `GetChildNodes()`. |
| `Document` | The root DOM object — loads a `.one` file or stream, exposes its `Page` children, and is the sole `Save()` entry point. |
| `DocumentVisitor` | Base visitor class for traversing the DOM via `Visit*Start`/`Visit*End` callbacks. |
| `FileCorruptedException` | Raised when the source file's OneStore container is malformed. |
| `Image` | An embedded image — bytes, file name, dimensions, alignment, and OneNote tags. |
| `IncorrectPasswordException` | Raised when `LoadOptions.DocumentPassword` is supplied — password-protected documents are not supported. |
| `License` | Compatibility surface for the commercial licensing API; see Scope and Limitations. |
| `LoadOptions` | Options passed to `Document()` — `DocumentPassword` and `LoadHistory`. |
| `Metered` | Compatibility surface for the commercial metered-licensing API; see Scope and Limitations. |
| `Node` | Base class for every DOM node — `ParentNode`, `Document`, and `Accept()`. |
| `NoteTag` | A OneNote tag (yellow star, question mark, musical note, or custom) attached to text, images, or tables. |
| `NumberList` | Numbered-list formatting applied to an `OutlineElement`. |
| `Outline` | A positioned container of `OutlineElement` nodes on a page. |
| `OutlineElement` | A single outline item — may hold `RichText`, `Image`, `Table`, or nested content, plus an optional `NumberList`. |
| `Page` | A single OneNote page — title, author, timestamps, level, and revision history. |
| `PageHistory` | The ordered revision history for a `Page`, returned by `Document.GetPageHistory()`. |
| `ParagraphStyle` | Default paragraph-level text formatting used by `RichText.ParagraphStyle`. |
| `RichText` | A run of formatted text content — `Text`, `TextRuns`, alignment, and tags. |
| `Table` | A table on a page — columns, border visibility, and tags. |
| `TableCell` | A single cell within a `TableRow`, holding rich text, images, or nested content as child nodes. |
| `TableColumn` | A table column's width and lock state. |
| `TableRow` | A row within a `Table`, containing one `TableCell` per column. |
| `TextRun` | A single formatted run within `RichText.Text` — `Text` plus its `TextStyle`. |
| `TextStyle` | Character-level formatting — bold, italic, underline, font, color, hyperlink, and more. |
| `Title` | A page's title — `TitleText`, `TitleDate`, and `TitleTime`, each a `RichText`. |
| `UnsupportedFileFormatException` | Raised when the source isn't a recognized OneNote format; carries the detected `FileFormat`. |
| `UnsupportedSaveFormatException` | Raised by `Document.Save()` for anything other than `SaveFormat.Pdf`. |

| Enumeration | Description |
|---|---|
| `FileFormat` | The detected OneNote source format (`Unknown`, `OneNote2010`, `OneNoteOnline`, `OneNote2007`). |
| `HorizontalAlignment` | Horizontal text/image alignment (`Left`, `Center`, `Right`). |
| `NodeType` | The DOM node kind used by `CompositeNode.GetChildNodes(node_type)`. |
| `SaveFormat` | The output format accepted by `Document.Save()` — currently only `Pdf`. |
| `TagStatus` | A `NoteTag`'s completion state (`Open`, `Completed`, `Disabled`). |

| Class | Description |
|---|---|
| `AttachmentTagFlowable` | Internal ReportLab `Flowable` that lays out an attachment's tag icon in the generated PDF. |
| `OutlinePrefixFlowable` | Internal ReportLab `Flowable` that lays out an outline element's numbered-list prefix in the generated PDF. |
| `PdfSaveOptions` | Options for PDF export — image compression, JPEG quality, page settings, and page range. |
| `SaveOptions` | Abstract base for save-options types; exposes `SaveFormat`, `PageIndex`, `PageCount`, `FontsSubsystem`. |

- `Document(source=None, load_options=None)`
  - `DisplayName: str | None`, `CreationTime: datetime | None`
  - `FileFormat -> FileFormat` — always reports `OneNote2010`, see Scope and Limitations
  - iteration: `for page in doc: ...`
  - `GetPageHistory(page) -> PageHistory`
  - `DetectLayoutChanges()` — compatibility stub, see Scope and Limitations
  - `Save(target, format_or_options=None)` — `SaveFormat.Pdf` only
- `PageHistory`
  - `Current: Page`, `Count: int`, `IsReadOnly: bool`
  - `Add(page)`, `AddRange(pages)`, `Remove(page)`, `RemoveAt(index)`, iteration/indexing
- `DocumentVisitor` — base visitor:
  - `VisitDocumentStart/End`, `VisitPageStart/End`, `VisitTitleStart/End`, `VisitOutlineStart/End`, `VisitOutlineElementStart/End`, `VisitRichTextStart/End`, `VisitImageStart/End`
- `Node`
  - `ParentNode: Node | None`, `Document: Document | None`, `Accept(visitor)`

- `Page`
  - `Title: Title | None`, `Author: str | None`
  - `CreationTime: datetime | None`, `LastModifiedTime: datetime | None`, `Level: int | None`
  - `Clone(cloneHistory=False) -> Page`

- `Title`
  - `TitleText: RichText | None`, `TitleDate: RichText | None`, `TitleTime: RichText | None`

- `Outline`
  - `HorizontalOffset`, `VerticalOffset`, `MaxWidth`, `MaxHeight`, `MinWidth`, `ReservedWidth`, `IndentPosition`, `DescendantsCannotBeMoved`, `LastModifiedTime`

- `OutlineElement`
  - `NumberList: NumberList | None`

- `RichText(Node)`
  - `Text: str`, `TextRuns: list[TextRun]`, `ParagraphStyle: ParagraphStyle`, `Length: int`
  - `Alignment: HorizontalAlignment | None`, `Tags: list[NoteTag]`
  - `Append(text, style=None)`, `Insert(index, text, style=None)`, `Remove(start, count)`, `Replace(old_value, new_value, style=None)`, `Trim()`/`TrimStart()`/`TrimEnd()`, `IndexOf(value, startIndex, count, comparison) -> int`
- `TextRun`
  - `Text: str`, `Style: TextStyle`
- `ParagraphStyle`
- `TextStyle`
  - `IsBold/IsItalic/IsUnderline/IsStrikethrough/IsSuperscript/IsSubscript: bool`, `IsHidden: bool`, `IsMathFormatting: bool`
  - `FontName: str | None`, `FontSize: float | None`, `FontColor: int | None`, `Highlight: int | None`, `Language: int | None`
  - `IsHyperlink: bool`, `HyperlinkAddress: str | None`, `FontStyle: int`
- `Image`
  - `FileName: str | None`, `Bytes: bytes`, `Width`, `Height`
  - `AlternativeTextTitle`, `AlternativeTextDescription`, `HyperlinkUrl`, `Tags: list[NoteTag]`
  - `Replace(image) -> None`
- `AttachedFile(Node)`
  - `FileName: str | None`, `Bytes: bytes`, `Tags: list[NoteTag]`
- `Table`
  - `Columns: list[TableColumn]`, `IsBordersVisible`, `Tags: list[NoteTag]`
- `TableColumn`
  - `Width: float | None`, `LockedWidth: bool`
- `NoteTag`
  - `Label`, `Icon`, `Status: TagStatus`, `Highlight`, `CreationTime`, `CompletedTime`, `FontColor`
  - `NoteTag.CreateYellowStar(label)`, `.CreateQuestionMark(label)`, `.CreateMusicalNote(label)`
- `NumberList`
  - `Format`, `NumberFormat`, `Font`, `FontSize`, `FontColor`, `IsBold`, `IsItalic`, `Restart`
  - `GetNumberedListHeader(number) -> str`

- `LoadOptions`
  - `DocumentPassword: str | None` — not supported, see Scope and Limitations
  - `LoadHistory: bool`
- `SaveOptions` (base)
  - `SaveFormat: SaveFormat`, `PageIndex: int`, `PageCount: int | None`, `FontsSubsystem`
- `PdfSaveOptions(SaveOptions)`
  - `ImageCompression`, `JpegQuality`, `PageSettings`, `PageSplittingAlgorithm`

- `License.SetLicense(license_path_or_stream)` — no-op in this edition, see Scope and Limitations
- `Metered.SetMeteredKey(public_key, private_key)` — no-op in this edition, see Scope and Limitations

- `FileFormat`: `Unknown`, `OneNote2010`, `OneNoteOnline`, `OneNote2007`

- `SaveFormat`: `Pdf`

- `HorizontalAlignment`: `Left`, `Center`, `Right`

- `NodeType`: `Document`, `Page`, `Outline`, `OutlineElement`, `RichText`, `Image`, `Table`, `AttachedFile`

- `TagStatus`: `Open`, `Completed`, `Disabled`

- `AsposeNoteError` — base exception for the library

- `FileCorruptedException` — the OneStore container is malformed

- `IncorrectDocumentStructureException` — the parsed object graph doesn't match the expected structure

- `IncorrectPasswordException` — a password was supplied; password-protected documents aren't supported

- `UnsupportedFileFormatException` — the source isn't a recognized OneNote format (carries `FileFormat`)

- `UnsupportedSaveFormatException` — `Document.Save()` was called with anything other than `SaveFormat.Pdf`

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/note/python/)** — installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/note/python/)** — task-focused answers for common OneNote-parsing questions.
- **[Full API reference](https://reference.aspose.org/note/python/)** — the complete, browsable reference for all 37 public types (the [API reference](#api-reference) section above covers the essentials).
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/issues).

## Scope and Limitations

- Writing back to `.one` is not implemented — this library only reads OneNote files.
- `LoadOptions.DocumentPassword` / encrypted documents are not supported — supplying a password raises `IncorrectPasswordException`.
- `SaveFormat` currently declares only `Pdf` — `Document.Save()` raises `UnsupportedSaveFormatException` for any other format or options object.
- `License.SetLicense()` and `Metered.SetMeteredKey()` are present for API-shape compatibility with the commercial product but are no-ops in this edition — no license is required to use this library.
- `DetectLayoutChanges()` is a compatibility stub and performs no layout computation.

The optional PDF-export dependency, [ReportLab](https://pypi.org/project/reportlab/), is BSD-3-Clause licensed; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the full text.

<details>
<summary>View Other Unimplemented Members</summary>

- `IncorrectDocumentStructureException` is declared but unused by the library's own code.

</details>

See [Aspose.Note — Enterprise Edition](https://products.aspose.com/note/). It adds full read/write support (including writing OneNote files back out), broader format conversion, and wider OneNote compatibility beyond what this free edition covers.

## Development and Testing

The suite covers 12 test files under `tests/`. The [ci workflow](.github/workflows/ci.yml) runs with Python 3.10, 3.11 and 3.12. Releases run through the [publish-pypi workflow](.github/workflows/publish-pypi.yml). Example programs live under `examples/`.

- `build`, `twine` — used to build and publish the package release; not needed to use or test the library.

Clone the repository and install the package together with the test extras used in CI:

```bash
git clone https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python.git
cd Aspose.Note-FOSS-for-Python
python -m pip install -e ".[pdf,test-pdf]"
```

Run the unit test suite the same way [`ci.yml`](.github/workflows/ci.yml) does:

```bash
python -m unittest tests.test_imports_smoke -v
python -m unittest tests.test_aspose_note_compat_smoke -v
python -m unittest tests.test_aspose_note_dom_content -v
python -m unittest tests.test_aspose_note_dom_document -v
python -m unittest tests.test_aspose_note_exceptions_and_stubs -v
python -m unittest tests.test_aspose_note_richtext_formatting -v
python -m unittest tests.test_aspose_note_save_options -v
python -m unittest tests.test_aspose_note_tags -v
```

The PDF golden-output tests (`tests.test_aspose_note_pdf_goldens`) compare generated PDFs against manifests in `tests/goldens/pdf/`, not raw bytes, so they stay stable across platforms and ReportLab internals. The PDF writer uses deterministic Base-14 fonts by default; set `ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS=1` before export if you want to try Windows system fonts for local inspection instead:

```bash
python -m unittest tests.test_aspose_note_pdf_goldens -v
```

On a mismatch, the generated PDFs and manifests are written to `tests/out/pdf_golden_failures/` for inspection. If `PyMuPDF` is installed, the failing test also renders baseline/generated pages to PNG and writes visual diff artifacts into the same output tree; if `PyMuPDF` is unavailable but `pdftoppm` is on `PATH`, the tests fall back to `pdftoppm` as the renderer.

Regenerate the golden baselines after an intentional PDF-output change with [`tools/regenerate_pdf_goldens.py`](tools/regenerate_pdf_goldens.py):

```bash
python tools/regenerate_pdf_goldens.py
```

Regenerate only selected cases:

```bash
python tools/regenerate_pdf_goldens.py --case formatted_richtext --case simple_table
```

## Third-Party Notices

See [Third-party notices](THIRD_PARTY_NOTICES.md).

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
