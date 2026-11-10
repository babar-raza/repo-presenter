# Aspose.Note FOSS for Python

[![PyPI version](https://img.shields.io/pypi/v/aspose-note-foss.svg)](https://pypi.org/project/aspose-note-foss/) ![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg) [![CI](https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/actions/workflows/ci.yml/badge.svg)](https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Python Versions](https://img.shields.io/pypi/pyversions/aspose-note-foss.svg)](https://pypi.org/project/aspose-note-foss/)

[![Aspose.Note FOSS for Python](https://products.aspose.org/media/note/python/banner-readme.png)](https://products.aspose.org/note/python/)

Aspose.Note FOSS for Python reads `.one` files and writes `.pdf` files. It converts documents to PDF using the `aspose.note.SaveFormat.Pdf` format. It extracts content such as images, attached files, rich text, tables, and note tags from `.one` files. It supports inspection and manipulation of document elements including pages, outlines, outline elements, and text runs.

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
flowchart LR
Start["An existing ONE file"]
Start --> Product["Aspose.Note FOSS for Python"]
Product["Aspose.Note FOSS for Python"] --> Cap1["Parse OneNote files from path or stream"]
Cap2["Traverse document tree structure"]
Cap3["Extract rich text with formatting"]
Cap4["Export pages to PDF"]
Product["Aspose.Note FOSS for Python"] --> Cap2["Traverse document tree structure"]
Product["Aspose.Note FOSS for Python"] --> Cap3["Extract rich text with formatting"]
Product["Aspose.Note FOSS for Python"] --> Cap4["Export pages to PDF"]
Cap1["Parse OneNote files from path or stream"] --> Output["PDF file"]
Cap2["Traverse document tree structure"] --> Output["PDF file"]
Cap3["Extract rich text with formatting"] --> Output["PDF file"]
Cap4["Export pages to PDF"] --> Output["PDF file"]
```

## Key Capabilities

- **Parse OneNote files from path or stream.** It reads `.one` files from a file path or binary stream into a `Document` object, supporting both direct file paths and file-like objects without requiring Microsoft OneNote or COM automation.
- **Traverse document tree structure.** It enables navigation of the document tree using `CompositeNode.GetChildNodes()` to retrieve `Page`, `Outline`, `OutlineElement`, `RichText`, `Image`, `Table`, and `AttachedFile` nodes in a type-safe manner.
- **Extract rich text with formatting.** It exposes rich text content through `TextRun` objects with `TextStyle` properties such as bold, italic, underline, strikethrough, superscript, subscript, font name, font size, font color, highlight color, and hyperlink addresses, along with paragraph-level styling via `ParagraphStyle`.
- **Export pages to PDF.** It exports documents to `.pdf` format using `SaveFormat.Pdf` or `PdfSaveOptions`, allowing control over JPEG image quality and other export settings.
- **Extract embedded images and attachments.** It extracts embedded images and attached files by exposing their raw bytes and file names through `Image.Bytes`/`Image.FileName` and `AttachedFile.Bytes`/`AttachedFile.FileName`, enabling direct saving to disk.
- **Inspect tables, tags, and numbered lists.** It inspects tables through `Table`, `TableRow`, `TableCell`, and `TableColumn` nodes, OneNote tags via `NoteTag` attached to text, images, and tables, and numbered lists through `NumberList` with format, number format, and restart behavior.
- **Support document revision history.** It supports document revision history by exposing `PageHistory` and enabling retrieval of historical page versions through `Document.GetPageHistory()`.

- Parse a `.one` file from a path or a binary stream into an Aspose.Note-compatible DOM via `Document`, with no dependency on Microsoft OneNote or COM automation.
- Traverse the parsed document as a tree of `Page`, `Outline`, `OutlineElement`, `RichText`, `Image`, `Table`, and `AttachedFile` nodes, using `CompositeNode.GetChildNodes()` for type-based search or the `DocumentVisitor` pattern for full traversal.
- Read page metadata through `Page.Title`, `Page.Author`, `Page.CreationTime`, and `Page.Level`, plus revision history via `PageHistory` and `Document.GetPageHistory()`.
- Extract rich text with per-run formatting through `TextRun` and `TextStyle` (bold, italic, underline, strikethrough, superscript, subscript, font, color, hyperlinks) and paragraph-level styling via `RichText.ParagraphStyle`.
- Extract embedded images through `Image` (bytes, file name, dimensions, alignment) and attached files through `AttachedFile` (bytes, file name), ready to save straight to disk.
- Inspect tables through `Table`, `TableRow`, `TableCell`, and `TableColumn` (rows, cells, and their content); OneNote tags through `NoteTag` (yellow star, question mark, musical note, and custom tags) attached to text, images, and tables; and numbered lists through `NumberList`.
- Export pages to PDF through `PdfSaveOptions` (`Document.Save(target, SaveFormat.Pdf)`), tuning image compression, JPEG quality, and page range.

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

The package declares `python_requires` as `>=3.10`.

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `pyproject.toml`, the `project.dependencies` list is empty.

### Optional Dependencies

- `reportlab>=3.6` (extra `pdf`)
- `Pillow>=10.0` (extra `test-pdf`)
- `PyMuPDF>=1.25` (extra `test-pdf`)
- `pypdf>=5.3` (extra `test-pdf`)

### Native and System Requirements

- Requires Python 3.10 or later (`python_requires=">=3.10"` in `pyproject.toml`).

### Development Dependencies

- `build>=1.2` (extra `dev`)
- `twine>=5.0` (extra `dev`)

## Quick Start

The example loads a OneNote file and exports it to PDF using the Save method with `SaveFormat.Pdf`.

```python
from aspose.note import Document, SaveFormat

doc = Document("SimpleTable.one")
doc.Save("out.pdf", SaveFormat.Pdf)
```

The example opens a OneNote file in binary mode, loads it into a `Document` object, and prints its `DisplayName` and page count.

```python
from aspose.note import Document

with open("SimpleTable.one", "rb") as f:
    doc = Document(f)
print(doc.DisplayName, len(list(doc)))
```

PDF export needs the optional `pdf` extra, which pulls in [ReportLab](https://pypi.org/project/reportlab/):

```bash
pip install "aspose-note-foss[pdf]"
```

The PyPI distribution is named `aspose-note-foss`; the import package is
`aspose.note` — `from aspose.note import Document`.

## Additional Examples

The following workflows demonstrate reading images, tables, attached files, tags, hyperlinks, and numbered lists, as well as exporting to PDF and counting document nodes.

### Save Embedded Images to Disk by Iterating over `Document.GetChildNodes`(`Image`), Reading `FileName` and Bytes, and Writing Bytes to Disk

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

### Traverse Tables and Extract Cell Text by Iterating over `Document.GetChildNodes`(`Table`), `TableRow`, `TableCell`, and `RichText`, Joining Text Values

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("SimpleTable.one")
for table in doc.GetChildNodes(Table):
    for row in table.GetChildNodes(TableRow):
        cells = row.GetChildNodes(TableCell)
        values = [" ".join(rt.Text for rt in cell.GetChildNodes(RichText)) for cell in cells]
        print(values)
```

### Extract Attached Files from a Document by Iterating over `Document.GetChildNodes`(`AttachedFile`), Reading `FileName` and Bytes, and Writing Bytes to Disk

```python
from pathlib import Path
from aspose.note import Document, AttachedFile

doc = Document("OnePageWithFile.one")
for i, af in enumerate(doc.GetChildNodes(AttachedFile), start=1):
    name = af.FileName or f"attachment_{i}.bin"
    Path(name).write_bytes(af.Bytes)
```

### Inspect OneNote Tags and Their Status by Iterating over `RichText` Nodes and Their Tags, Printing Label and Status

```python
from aspose.note import Document, RichText

doc = Document("TagSizes.one")
for rt in doc.GetChildNodes(RichText):
    for tag in rt.Tags:
        print(tag.Label, tag.Status)
```

### Count Document Nodes Using a `DocumentVisitor` Subclass That Increments Counters in `VisitPageStart`, `VisitRichTextStart`, and `VisitImageStart`, Then Call `Document.Accept`

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

### Extract All Text from Rich Text Nodes by Iterating over `Document.GetChildNodes`(`RichText`) and Collecting Text Values

```python
from aspose.note import Document, RichText

doc = Document("FormattedRichText.one")
texts = [rt.Text for rt in doc.GetChildNodes(RichText)]
print("\n".join(texts))
```

### Export to PDF with Custom JPEG Quality by Creating `PdfSaveOptions` with `JpegQuality` and Passing It To `Document.Save`

```python
from aspose.note import Document, SaveFormat
from aspose.note.saving import PdfSaveOptions

doc = Document("TagSizes.one")
opts = PdfSaveOptions(JpegQuality=90)
doc.Save("out.pdf", opts)
```

### Extract Hyperlinks and Their Addresses by Iterating over `RichText.TextRuns`, Checking `Style.IsHyperlink` And `Style.HyperlinkAddress`

```python
from aspose.note import Document, RichText

doc = Document("FormattedRichText.one")
for rt in doc.GetChildNodes(RichText):
    for run in rt.TextRuns:
        if run.Style.IsHyperlink and run.Style.HyperlinkAddress:
            print(run.Text, "->", run.Style.HyperlinkAddress)
```

### Inspect Numbered List Formatting Properties by Iterating over `Document.GetChildNodes`(`OutlineElement`), Reading `NumberList.Format`, `NumberFormat`, and Restart

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

</details>

## API Reference

The primary entry point is `aspose.note.Document`, which loads a `.one` file and exposes its pages as a tree of nodes; `Document.Save()` is the sole write path, currently limited to PDF via `aspose.note.saving.PdfSaveOptions`. The supported public entry points are `aspose.note` and `aspose.note.saving`.

The verified public surface has 37 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `AttachedFile` | The aspose.note.AttachedFile class represents an attached file node in a document. |
| `Document` | The aspose.note.Document class represents a document and provides methods to load, save, and access its pages. |
| `DocumentVisitor` | The aspose.note.DocumentVisitor class provides a visitor pattern implementation to traverse document nodes. |
| `FileCorruptedException` | The aspose.note.FileCorruptedException class represents an error raised when a file is corrupted. |
| `Image` | The aspose.note.Image class represents an image node in a document. |
| `IncorrectDocumentStructureException` | The aspose.note.IncorrectDocumentStructureException class represents an error raised when a document structure is incorrect. |
| `IncorrectPasswordException` | The aspose.note.IncorrectPasswordException class represents an error raised when a document password is incorrect. |
| `License` | The aspose.note.License class provides methods to set a license for the product. |
| `LoadOptions` | The aspose.note.LoadOptions class provides options for loading a document. |
| `Metered` | The aspose.note.Metered class provides methods to set metered key for the product. |
| `Node` | The aspose.note.Node class represents a node in a document. |
| `NoteTag` | The aspose.note.NoteTag class represents a note tag in a document. |
| `NumberList` | The aspose.note.NumberList class represents a numbered list in a document. |
| `Outline` | The aspose.note.Outline class represents an outline node in a document. |
| `OutlineElement` | The aspose.note.OutlineElement class represents an outline element node in a document. |
| `Page` | The aspose.note.Page class represents a page node in a document. |
| `PageHistory` | The aspose.note.PageHistory class represents the history of a page. |
| `ParagraphStyle` | The aspose.note.ParagraphStyle class represents the style of a paragraph. |
| `RichText` | The aspose.note.RichText class represents rich text content in a document. |
| `Table` | The aspose.note.Table class represents a table node in a document. |
| `TableCell` | The aspose.note.TableCell class represents a table cell node in a document. |
| `TableColumn` | The aspose.note.TableColumn class represents a table column in a table. |
| `TableRow` | The aspose.note.TableRow class represents a table row node in a document. |
| `TextRun` | The aspose.note.TextRun class represents a run of text with the same formatting. |
| `TextStyle` | The aspose.note.TextStyle class represents the style of text. |
| `Title` | The aspose.note.Title class represents the title of a page. |
| `UnsupportedFileFormatException` | The aspose.note.UnsupportedFileFormatException class represents an error raised when a file format is unsupported. |
| `UnsupportedSaveFormatException` | The aspose.note.UnsupportedSaveFormatException class represents an error raised when a save format is unsupported. |
| `AsposeNoteError` | The aspose.note.exceptions.AsposeNoteError class represents a base error for Aspose.Note operations. |
| `CompositeNode` | The aspose.note.model.CompositeNode class represents a node that can contain child nodes. |
| `PdfSaveOptions` | The aspose.note.model.PdfSaveOptions class provides options for saving a document to PDF format. |
| `SaveOptions` | The aspose.note.model.SaveOptions class provides base options for saving a document. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `FileFormat` | The aspose.note.FileFormat class represents the file format of a document. |
| `HorizontalAlignment` | The aspose.note.HorizontalAlignment class represents horizontal alignment options. |
| `NodeType` | The aspose.note.NodeType class represents the type of a document node. |
| `SaveFormat` | The aspose.note.SaveFormat class represents the format for saving a document. |
| `TagStatus` | The aspose.note.TagStatus class represents the status of a note tag. |

#### Detailed Member Reference

### Document

The `aspose.note.Document` class loads a `.one` file and exposes its pages as a tree of nodes; it provides `DisplayName`, `FileFormat`, `GetPageHistory()`, and `Save()` methods, with iteration over pages and support for loading from a file-like object.

### Page

The `aspose.note.Page` class represents a page in a document and provides `Clone()`, `Title`, Author, and timestamps; the `aspose.note.PageHistory` class manages page revisions with methods such as `Add()`, `Remove()`, Count, and Current.

### RichText

The `aspose.note.RichText` class holds formatted text with properties such as Text, `TextRuns`, Alignment, and Tags, and methods including `Append()`, `Insert()`, `Remove()`, and `Trim()`; each `TextRun` carries a Style of type `aspose.note.TextStyle` that defines font and formatting attributes.

### Image

The `aspose.note.Image` class represents embedded images with properties such as `FileName`, Bytes, Width, and Height, and supports extraction by iterating over `Document.GetChildNodes`(`Image`) and writing Bytes to disk.

### AttachedFile

The `aspose.note.AttachedFile` class represents attached files with properties such as `FileName` and Bytes, and supports extraction by iterating over `Document.GetChildNodes`(`AttachedFile`) and writing Bytes to disk.

### Table

The `aspose.note.Table` class represents tables with columns and cells, and supports reading cell content by iterating over `Table`, `TableRow`, `TableCell`, and `RichText` nodes.

### SaveFormat

The `aspose.note.SaveFormat` class defines output formats for saving documents, currently supporting only `.pdf` via `SaveFormat.Pdf`.

### saving

The `aspose.note.saving` module provides `PdfSaveOptions` for configuring PDF export, including `JpegQuality` and other settings passed to `Document.Save()`.

### NoteTag

The `aspose.note.NoteTag` class represents tags attached to text or other nodes, with properties such as Label, Status, and Icon, and factory methods like `CreateYellowStar()` and `CreateQuestionMark()`.

### NumberList

The `aspose.note.NumberList` class represents numbered lists with properties such as Format, `NumberFormat`, Restart, and Font, and supports retrieving the header string for a given number via `GetNumberedListHeader()`.

### DocumentVisitor

The `aspose.note.DocumentVisitor` class enables custom traversal of a document tree via visitor methods such as `VisitPageStart()`, `VisitRichTextStart()`, and `VisitImageStart()`, with `Document.Accept()` initiating the visit.

### exceptions

The `aspose.note.exceptions` module defines exceptions such as `FileCorruptedException`, `IncorrectPasswordException`, `UnsupportedFileFormatException`, and `UnsupportedSaveFormatException`, raised when loading or saving operations encounter errors.

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
| `IncorrectDocumentStructureException` | Raised when the parsed OneStore object graph doesn't match the expected document structure. |
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
- Container nodes (`Document`, `Page`, `Title`, `Outline`, `OutlineElement`, `Image`, `Table`, `TableRow`, `TableCell`)
  - `FirstChild`, `LastChild`
  - `AppendChildLast(node)`, `AppendChildFirst(node)`, `InsertChild(index, node)`, `RemoveChild(node)`
  - iteration `for child in node: ...`
  - `GetChildNodes(node_type) -> list[TNode]` — recursive search by type

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
  - default paragraph-level text formatting; `ParagraphStyle.Default() -> ParagraphStyle`
- `TextStyle`
  - `IsBold/IsItalic/IsUnderline/IsStrikethrough/IsSuperscript/IsSubscript: bool`, `IsHidden: bool`, `IsMathFormatting: bool`
  - `FontName: str | None`, `FontSize: float | None`, `FontColor: int | None`, `Highlight: int | None`, `Language: int | None`
  - `IsHyperlink: bool`, `HyperlinkAddress: str | None`, `FontStyle: int`
  - `TextStyle.Default()`, `.DefaultMsOneNoteTitleTextStyle()`, `.DefaultMsOneNoteTitleDateStyle()`, `.DefaultMsOneNoteTitleTimeStyle()`
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

- **[Getting started guide](https://docs.aspose.org/note/python/)** — The getting started guide covers installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/note/python/)** — The how-to guides and FAQ provide task-focused answers for common OneNote-parsing questions.
- **[Full API reference](https://reference.aspose.org/note/python/)** — The full API reference offers a complete, browsable reference for all 37 public types. It covers all 37 verified public types; the [API Reference](#api-reference) section above covers the essentials.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/issues).

Runnable example scripts have their own setup and usage notes in
[`examples/README.md`](examples/README.md).
[`publish-pypi.yml`](.github/workflows/publish-pypi.yml) shows the exact release-time commands
this project runs in CI.

## Scope and Limitations

Aspose.Note FOSS for Python reads `OneNote` files and exports them to PDF. It supports Python 3.10 and later.

- Writing back to `.one` files is not implemented — this library only reads `OneNote` files, and `SaveFormat` currently declares only Pdf, so `Document.Save()` raises `UnsupportedSaveFormatException` for any other format or options object.
- `LoadOptions.DocumentPassword` and encrypted documents are not supported — supplying a password raises `IncorrectPasswordException`.
- `License.SetLicense()` and `Metered.SetMeteredKey()` are present for API-shape compatibility with the commercial product but are no-ops in this edition — no license is required to use this library.
- `DetectLayoutChanges()` is a compatibility stub and performs no layout computation.
- `License.SetLicense`(`license_path_or_stream`) and `Metered.SetMeteredKey`(`public_key`, `private_key`) are no-ops in this edition, see Scope and Limitations.

These limitations don't apply to [full-featured Aspose.Note — Enterprise Edition](https://products.aspose.com/note/). It adds full read/write support (including writing OneNote files back out), broader format conversion, and wider OneNote compatibility beyond what this free edition covers.

## Development and Testing

The toolchain requires Python 3.10 or later and uses the standard library's unittest framework for testing. Tests are located in the tests/ directory and cover imports, compatibility, DOM content, document handling, exceptions, rich text formatting, save options, and tags. PDF golden-output tests compare generated PDFs against stored manifests in tests/goldens/PDF/ rather than raw bytes, ensuring stability across platforms and ReportLab internals. Regenerating PDF baselines after intentional changes is done with the `tools/regenerate_pdf_goldens.py` script.

The suite covers 12 test files under `tests/`. The [ci workflow](.github/workflows/ci.yml) runs with Python 3.10, 3.11 and 3.12. Releases run through the [publish-pypi workflow](.github/workflows/publish-pypi.yml).

To build from a clone, run:

```bash
pip install build
python -m build
```

- `reportlab` — pulled in by the `pdf` extra (`pip install "aspose-note-foss[pdf]"`); required only to export pages to PDF via `Document.Save(..., SaveFormat.Pdf)`.
- `pypdf`, `Pillow`, `PyMuPDF` — pulled in by the `test-pdf` extra; used by the PDF golden-output tests to compare generated PDFs against stored manifests, not by the library at runtime.

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

The PDF golden-output tests (`tests.test_aspose_note_pdf_goldens`) compare generated PDFs against
manifests in `tests/goldens/pdf/`, not raw bytes, so they stay stable across platforms and
ReportLab internals. The PDF writer uses deterministic Base-14 fonts by default; set
`ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS=1` before export if you want to try Windows system fonts for
local inspection instead:

```bash
python -m unittest tests.test_aspose_note_pdf_goldens -v
```

On a mismatch, the generated PDFs and manifests are written to
`tests/out/pdf_golden_failures/` for inspection. If `PyMuPDF` is installed, the failing test also
renders baseline/generated pages to PNG and writes visual diff artifacts into the same output
tree; if `PyMuPDF` is unavailable but `pdftoppm` is on `PATH`, the tests fall back to `pdftoppm`
as the renderer.

Regenerate the golden baselines after an intentional PDF-output change with
[`tools/regenerate_pdf_goldens.py`](tools/regenerate_pdf_goldens.py):

```bash
python tools/regenerate_pdf_goldens.py
```

Regenerate only selected cases:

```bash
python tools/regenerate_pdf_goldens.py --case formatted_richtext --case simple_table
```

The optional PDF-export
dependency, [ReportLab](https://pypi.org/project/reportlab/), is BSD-3-Clause licensed; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the full text.

## Third-Party Notices

See [Third-party notices](THIRD_PARTY_NOTICES.md).

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
