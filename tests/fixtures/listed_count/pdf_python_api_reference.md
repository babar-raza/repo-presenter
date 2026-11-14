The `Document` class is the central entry point — it exposes `pages`, `form`, `outlines`, and
`tagged_content` for structural editing alongside `encrypt`, `decrypt`, `merge`, `optimize`, and
`flatten` operations. `PdfExtractor` handles text, image, and attachment extraction, and
`PdfFileEditor` provides a boolean-returning facade for file-based concatenate, extract, insert,
and delete workflows. 277 public types are organized by module below.

<details>
<summary>View the Core API Surface</summary>

### Core API

| Class | Description |
|---|---|
| `Action` | Base class for an interactive action. |
| `AsposePdfException` | Base class for all aspose_pdf exceptions. |
| `ByteArrayDataSource` | A data source backed by in-memory bytes. |
| `CdrLoadOptions` | Options for loading CDR files. |
| `CertificationLevel` | DocMDP certification level of a signature. |
| `CgmLoadOptions` | Options for loading CGM files. |
| `ColorPrimitive` | Very small color primitive with transparency support. |
| `DataSource` | Base class for plugin inputs and outputs. |
| `DeprecatedFeatureException` | Raised when a deprecated PDF feature is used that is not allowed in newer PDF versions. |
| `Destination` | Base class for a view destination on a document page. |
| `DocFormat` | Target format for a save operation. |
| `Document-document` | Pythonic wrapper for PDF document lifecycle and core operations. |
| `Duplex` | Enum with 4 members. |
| `ExtractedBlock` | Immutable heading, paragraph, list, table or figure snapshot with source page, position anchor and JSON-ready data. |
| `ExtractedTable` | Immutable text-table snapshot with source page, rows, inferred column spans, list conversion and CSV export. |
| `Field` | A field of an interactive form. |
| `FieldType` | Type of form field. |
| `FileDataSource` | A data source backed by a file on disk. |
| `FileFontSource` | Discover the font(s) contained in a single file. |
| `FileSpecification` | An embedded file with typed metadata, for document or page attachments. |
| `FillMode` | Fill mode enumeration for path operations. |
| `FitBDestination` | Fit the page's bounding box in the window. |
| `FitBHDestination` | Fit the bounding-box width with `top` at the top of the window. |
| `FitBVDestination` | Fit the bounding-box height with `left` at the left of the window. |
| `FitDestination` | Fit the whole page in the window. |
| `FitHDestination` | Fit the page width with `top` at the top of the window. |
| `FitRDestination` | Fit the rectangle `(left, bottom, right, top)` in the window. |
| `FitVDestination` | Fit the page height with `left` at the left of the window. |
| `FolderFontSource` | Collect fonts from a directory (optionally recursing into subfolders). |
| `FontDescriptor` | Represents a discoverable font. |
| `FontEmbeddingException` | Raised when there is an error embedding fonts in the PDF. |
| `FontRegistry` | Singleton registry for resolving well-known font names. |
| `FontRepository` | Aggregate font sources and resolve fonts by name. |
| `FontSource` | Base class for external font providers. |
| `FontSubstitutionOptions` | Font sources the renderer may substitute from. |
| `Form` | Represents an interactive form (AcroForm) within a PDF document. |
| `FormFiller` | Creates independently filled PDFs from templates and a batch of records. |
| `FormFillerOptions` | Reusable records, field filling options and data sources for a form batch. |
| `FormType` | Type of PDF form. |
| `GoToAction` | Jump to a destination within this document. |
| `GoToRAction` | Jump to a page view or named destination in another PDF, with an optional window preference. |
| `GradientAxialShading` | Represents axial (linear) gradient shading. |
| `GraphicElement` | A painted path or a placed image, read from a page's content stream. |
| `GraphicElementCollection` | Collection of graphic elements that can be added to or removed from a page. |
| `GraphicsAbsorber` | Absorbs graphic elements from PDF pages. |
| `HideAction` | Hide or show named form fields when a viewer executes an event. |
| `HtmlLoadOptions` | Options for loading HTML documents. |
| `HtmlSaveOptions` | Options for saving PDF documents as HTML. |
| `ImagePlacement-images` | Represent an image placed on a PDF page. |
| `ImagePlacementAbsorber-images` | Absorber to collect image placements from PDF pages. |
| `ImageResolutionIssue` | Immutable location, pixel dimensions and effective DPI for a low-resolution image paint. |
| `IncorrectCMapUsageException` | Raised when there is an incorrect usage of CMap. |
| `InvalidFormTypeOperationException` | Exception thrown when an invalid form type operation is attempted. |
| `InvalidOperationException` | Raised when a graphics element is attached to the wrong parent. |
| `InvalidPasswordException` | Raised when an incorrect password is provided for an encrypted document. |
| `Layer` | One optional content group: its name, intent, whether it is shown, and `add`/`remove`/`contains` for tagging existing content with it. |
| `TextStamp` / `ImageStamp` / `PageNumberStamp` | A mark put over or under a page: text, a picture, or the page's number, with opacity, rotation and alignment. |
| `ViewerPreferences` | The document's `/ViewerPreferences`: the window, the reading direction and the print dialogue, read and written in place. |
| `LayerCollection` | The document's layers: indexable by position or by name, with `add(name, visible)`, `remove(layer)` and `make_exclusive(layers)`. |
| `InvalidPdfFileFormatException` | Raised when the PDF file format is invalid or corrupted. |
| `InvalidValueFormatException` | Raised when an invalid value is encountered during parsing or conversion. |
| `JavaScriptAction` | Run a JavaScript script (serialized verbatim, not validated). |
| `LatexFragment` | Small value object that stores LaTeX source text. |
| `LaunchAction` | Launch an application or open a file (serialized verbatim). |
| `Layer` | One optional content group, and whether it is currently shown. |
| `LayerCollection` | The document's layers, indexable by position or by name. |
| `License` | License management class for Aspose.PDF. |
| `ListItem` | One item of a list: what it says, and what hangs under it. |
| `Margin` | The Margin class provides top, left, bottom, and right properties for defining page margins. |
| `MarkdownSaveOptions` | Class with 1 method and 4 properties. |
| `Matrix3D` | Represents a 3D transformation matrix. |
| `MemoryFontSource` | Expose a font program supplied as in-memory bytes. |
| `MergeOptions` | Options for :class:`Merger`: concatenate all inputs in order. |
| `Merger` | Concatenate every input PDF into a single document. |
| `NamedAction` | A predefined named action. |
| `NamespaceProvider` | Resolve XMP namespace prefixes and URIs. |
| `OfdLoadOptions` | Options for loading OFD files. |
| `OperationResult` | A single result produced by a plugin. |
| `OptimizationOptions` | OptimizationOptions lets developers control stream compression, removal of unused objects, image down‑sampling, and other cleanup actions when optimizing PDFs. |
| `OptimizeOptions` | Options for :class:`Optimizer`. |
| `Optimizer` | Optimize each input PDF (compression + unused-object cleanup). |
| `OutlineCollection` | Top-level collection of :class:`OutlineItem` bookmarks. |
| `OutlineItem` | A single bookmark entry in a PDF outline tree. |
| `PadesLevel` | PAdES baseline conformance level reached by a signature. |
| `Page` | A page of a PDF document. |
| `PageCollection` | A collection to manage PDF pages within a Document. |
| `PageInfo` | Class with 1 property. |
| `PageTextComparison` | Immutable page-pair text report with original strings, match status and a normalized unified diff. |
| `PageVisualComparison` | Immutable page-pair comparison with changed/ignored pixel counts, ratio, bounds, match status and optional difference image. |
| `Paragraph` | One paragraph of a text block: what it says, and how it differs from the block. |
| `PdfAConversionResult` | Result of a PDF/A conversion operation. |
| `PdfAValidateOptions-pdfa` | Container for PDF/A validation settings. |
| `PdfAValidationResult-pdfa` | Detailed result of a PDF/A validation run. |
| `PdfAValidator` | Plugin that runs PDF/A validation on one or more inputs. |
| `PdfConsts` | Class with 2 methods. |
| `PdfException` | Base class for PDF-related exceptions. |
| `PdfExtractor` | Simple PDF text and image extractor. |
| `PdfFileEditor` | Facade for PDF file editing operations. |
| `PdfIOException` | Raised when there is an I/O error during PDF processing. |
| `PdfLoadLimits` | Immutable safety limits for untrusted PDF input and authored assets. |
| `PdfParseException` | Raised when there is an error parsing a PDF document. |
| `PdfPlugin` | Base class for low-code plugins. |
| `PdfResourceLimitException` | Raised when processing a PDF would exceed a configured resource limit. |
| `PdfSecurityException` | Raised when there is an encryption, signature, or permissions error. |
| `PdfSignature` | Represent a PDF digital signature. |
| `PdfUaValidateOptions` | Container for batch PDF/UA validation settings. |
| `PdfUaValidationResult` | Detailed result of a PDF/UA structure check (heuristic). |
| `PdfUaValidator` | Plugin that runs heuristic PDF/UA validation on one or more inputs. |
| `PdfValidationException` | Raised when a PDF document fails validation or compliance checks. |
| `PdfXStandard` | The PDF/X conformance levels this library validates and writes. |
| `PdfXValidateOptions` | Container for batch PDF/X validation settings. |
| `PdfXValidationResult` | Detailed result of a PDF/X validation run (heuristic). |
| `PdfXValidator` | Plugin that runs heuristic PDF/X validation on one or more inputs. |
| `Permissions` | What a reader may do with an encrypted document: `/P`, with names. |
| `PerformanceLogger` | Class with 2 methods and 1 property. |
| `Plugin` | Identifiers for the available low-code plugins. |
| `PluginOptions` | Hold input/output data sources and their PDF resource-limit policy. |
| `Point` | Represents a point in 2D space. |
| `Point3D` | Represents a 3D point. |
| `PrinterSettings` | Class with 11 properties. |
| `PrintRange` | Enum with 4 members. |
| `Recipient` | One certificate that may open the document, and what it may then do. |
| `Rectangle` | Rectangle representing image placement bounds on a PDF page. |
| `RegexResult` | Wraps a single regular-expression match found on a PDF page. |
| `ResetFormAction` | Reset the form's fields to their default values. |
| `ResultContainer` | Holds the ordered results of a plugin operation. |
| `RevocationStatus` | Certificate revocation outcome (OCSP/CRL). |
| `SaveFormat` | Format for saving PDF documents. |
| `SplitOptions` | Select per-page, page-group, or bookmark-level splitting. |
| `Splitter` | Split every input PDF into independent output documents. |
| `StatisticsEntry` | Entry for tracking statistics and timing information. |
| `StreamDataSource` | A data source backed by a binary stream (e.g. ``io.BytesIO``). |
| `StructureElement` | A mutable logical-structure element in a tagged PDF. |
| `StructureTypeStandard` | Enum with 15 members. |
| `SubmitFormAction` | Send the form's field values to a URL. |
| `SvgLoadOptions-load_options` | Options for loading SVG files. |
| `SvgLoadOptions-svg` | Class with 1 method and 2 properties. |
| `SystemFontSource` | Collect fonts from common system font directories. |
| `TaggedContent` | Editable view of a document's logical structure tree. |
| `TaggedContext` | Class with 4 properties. |
| `TextAbsorber` | Absorbs text from PDF pages (legacy class, alias for TextFragmentAbsorber). |
| `TextBlock` | Paragraphs wrapped to a measure, ready to be placed on a page. |
| `TextExtractionOptions` | Options for text extraction from PDF pages. |
| `TextExtractor` | Extract plain text from each input PDF. |
| `TextExtractorOptions` | Options for :class:`TextExtractor`: extract text from each input. |
| `TextFormattingMode` | Text formatting mode for text extraction. |
| `TextFragment` | A text fragment found inside a PDF page. |
| `TextWord` | An immutable positioned word with a page index, bounding box and quadrilateral. |
| `TextFragmentAbsorber-text` | Absorbs text fragments from a PDF page or document. |
| `TextFragmentCollection` | A mutable ordered collection of :class:`TextFragment` objects. |
| `TextLayoutOptions` | Configure complex-text shaping and line layout for ``Page.add_text``. |
| `TextList` | Items ready to be placed on a page, bulleted or numbered. |
| `TextSearchOptions` | Options controlling how text search is performed. |
| `TextSearchMatch` | Immutable search hit with page, offsets, surrounding context and available geometry. |
| `TrustStatus` | Outcome of building/validating the signer's certificate chain. |
| `UnsignedContent-forms` | Represents a collection of unsigned content elements in a PDF document. |
| `UnsignedContentAbsorber-forms` | Extract unsigned form fields and annotations from a PDF document. |
| `UnsupportedFeatureException` | Raised when a compatibility surface names a feature this package lacks. |
| `URIAction` | Resolve a uniform resource identifier (typically a web link). |
| `ValidationMethod` | Selects the signature format / validation algorithm. |
| `ValidationMode` | Controls whether certificate revocation is checked via network. |
| `ValidationOptions` | Configuration for signature validation. |
| `ValidationResult` | Structured result returned by signature validation. |
| `ValidationStatus` | Outcome of a :class:`ValidationResult`. |
| `VirtualizationPerformance` | Class with 5 methods. |
| `WarichuWPElement` | Minimal tagged-element type for API compatibility. |
| `XYZDestination` | Position `(left, top)` at the upper-left with an optional zoom. |



### Annotations

| Class | Description |
|---|---|
| `Annotation` | Live view over a single annotation on a page. |
| `AnnotationCollection` | Mutable sequence-like wrapper over page annotations. |
| `LinkAnnotation` | Concrete annotation type kept for compatibility with tests/API. |
| `LinkValidationIssue` | Immutable local-navigation diagnostic with source location and issue code. |
| `ExtractedLink` | Detached link target/action with source coordinates, URL or destination and diagnostic codes. |
| `MarkupAnnotation` | Base class for markup annotations. |
| `PDF3DAnnotation` | Minimal annotation wrapper for prerelease imports. |
| `PDF3DArtwork` | Container for 3D content and named views. |
| `PDF3DContent` | Reference to 3D content stored on disk. |
| `PDF3DView` | Lightweight description of a saved 3D view. |

#### Enumerations

| Enumeration | Description |
|---|---|
| `AnnotationFlags` | Flags that define annotation behaviour. |
| `AnnotationType` | Known annotation subtype names (PDF 32000-1:2008, Table 169). |
| `PDF3DLightingScheme` | Enum with 5 members. |
| `PDF3DRenderMode` | PDF3DRenderMode and PDF3DLightingScheme enums let developers choose rendering style (SOLID, WIREFRAME, TRANSPARENT) and lighting (HEADLAMP, WHITE, etc.) for 3D annotations. |

---

### Clustering

| Class | Description |
|---|---|
| `Cluster` | Represents a cluster of data points. |
| `ClusterCollection` | A collection of clusters. |
| `DataPoint` | Represents a data point in clustering operations. |

---

### Engine

| Class | Description |
|---|---|
| `AbsorbedElement` | One painted path or placed image, in page (user) space. |
| `AnnotationName` | A ``str`` subclass that marks a value to be serialized as a PDF name. |
| `AuthoredFont` | A normalized embedded font and the mutable CID mapping for authored text. |
| `AuthoredImage` | Prepared image data and PDF image XObject metadata. |
| `BitStream` | Minimal bit-oriented buffer used by compatibility code. |
| `Block` | One piece of exported structure. |
| `CffOutlines` | Decode glyph outlines from a CFF (Type 2 charstring) font program. |
| `ChainResult` | Result of building and validating a certificate path. |
| `CharacterCollection` | A CIDSystemInfo registry, ordering, and supplement triple. |
| `CidTextCodec` | Code codec for a composite (Type0) font's show strings. |
| `Codestream` | Class with 2 methods and 8 properties. |
| `Color` | Represents a color in PDF documents. |
| `CompositeFontMetric` | Advance metrics for a composite (Type0) font. |
| `ContentStreamParser` | Parse a PDF content stream and extract plain text. |
| `CosExtractor` | Extract pages, streams, images and metadata from a PdfDocument. |
| `DecodedImage` | A decoded JPEG 2000 image as interleaved 8-bit samples. |
| `DecodedJpeg` | A decoded JPEG image. |
| `Decoder-ccitt` | Decoder.decode(data, params, limits) returns the raw bytes of a decoded stream for supported codecs like JBIG2 and JPEG 2000. |
| `Decoder-jbig2` | JBIG2 decoder that parses segment structure and extracts bitmap data. |
| `Decoder-jpx` | JPEG 2000 (JPX) Stream Decoder. |
| `DssMaterial` | Validation material destined for (or harvested from) a ``/DSS``. |
| `Encoding` | Class with 1 method and 4 members. |
| `EncodingType` | Enum with 5 members. |
| `EncryptionUtils` | Utility class for PDF-compliant AES-CBC, RC4 encryption, and key derivation. |
| `FilterType` | The FilterType enum lists the supported stream filter names such as FLATE_DECODE, LZW_DECODE, and DCT_DECODE. |
| `FontResolver` | Index external font sources and resolve PDF font names against them. |
| `GeneratedAppearance` | A synthesised appearance: content bytes plus any required ExtGState entries. |
| `GlyphPlacement` | One shaped glyph at an em-relative position within a laid-out line. |
| `ImagePlacement-simple_pdf` | Represents an image placement on a page. |
| `ImagePlacementAbsorber-simple_pdf` | Absorber that finds image placements in a PDF. |
| `IncrementalUpdate` | Generate an incremental update section for an existing PDF. |
| `IncrementalWriter` | Utility that appends incremental updates to an existing PDF. |
| `Jpeg2000Error` | A JPEG 2000 codestream that cannot be decoded. |
| `LayoutElement` | A positioned piece of page content (a text object or an image paint). |
| `LayoutLine` | One visual line with logical replacement text and shaped glyphs. |
| `LayoutResult` | Complete line layout; glyph coordinates and widths are in em units. |
| `LazyImageDict` | Dictionary that decodes image streams on demand to save memory. |
| `LazyPdfObjectStore` | Object-number → COS object map that parses from a :class:`PdfCosParser` on demand. |
| `Matrix` | Matrix supports 2‑D transformations with translate(x, y) and multiply(other) methods, exposing the a‑f components of the affine matrix. |
| `MQDecoder` | The MQ arithmetic decoder of Annex C. |
| `OptionalContent` | The document's optional content groups and their default visibility. |
| `OptionalContentGroup` | One optional content group (`/OCG`) of the document. |
| `ParseWarnings` | Collects warnings during parsing. |
| `PdfArray` | PdfArray provides an items collection and an append method to build PDF array objects. |
| `PdfBoolean` | PdfBoolean represents a PDF boolean value via its 'value' property. |
| `PdfCorruptedError` | Unrecoverable PDF corruption. |
| `PdfCosParser` | Parse a PDF file (bytes) into a :class:`PdfDocument`. |
| `PdfCosWriter` | Serialize a :class:`PdfDocument` to a PDF byte sequence. |
| `PdfDictionary` | PdfDictionary behaves like a mapping with get and pop methods to access entries. |
| `PdfDocument` | Container for a PDF's COS object graph. |
| `PdfEncodingError` | Font or content stream encoding error. |
| `PdfIndirectReference` | PdfIndirectReference exposes the object number and generation number of an indirect PDF object. |
| `PdfMalformedError` | Recoverable malformed PDF structure. |
| `PdfName` | Represents a PDF name object. |
| `PdfNull` | Represent PDF null object. |
| `PdfNumber` | Represents a PDF number primitive (integer or real). |
| `PdfObject` | Base class for all PDF COS objects. |
| `PdfObjectID` | Class with 2 properties. |
| `PdfObjectRegistry` | PdfObjectRegistry.register(obj) returns a PdfObjectID that uniquely identifies the stored PDF object within the registry. |
| `PdfParseError` | Base exception for PDF parsing errors. |
| `PdfParseWarning` | Non-fatal parsing issue that was recovered from. |
| `PdfSecurityError` | Encryption or permission related error. |
| `PdfStream` | Class with 3 methods and 2 properties. |
| `PdfString` | Class with 1 method and 1 property. |
| `PdfTrailerable` | Class with 1 method. |
| `PdfValidationError` | PDF/A or general structural validation error. |
| `PredefinedCMap` | A resolved predefined CMap and its semantic Unicode mapping. |
| `PredefinedCMapEncoding` | Compact code-to-CID view of a predefined CMap. |
| `RasterizedPage` | A rendered PDF page in packed RGB format. |
| `RecipientPayload` | What one opened envelope carries. |
| `Reshaper` | Policy for shaping complex-script replacements during a text edit. |
| `ResolvedFace` | A font program picked for a non-embedded PDF font. |
| `RevocationResult` | Class with 3 properties. |
| `RichRun` | Class with 2 properties. |
| `RichStyle` | The resolved style of a text run. |
| `SfntFace` | Metadata recovered from a single SFNT face. |
| `Shading` | Base class for bounded RGB sampling in a shading's target space. |
| `SignedDataInfo` | Everything we need from a parsed CMS ``SignedData``. |
| `SignerVerification` | Outcome of verifying a single signer. |
| `SigningUtils` | Utility class for generating certificates and PKCS#7 signatures. |
| `SimpleFontMetric` | Advance metrics for a single-byte simple font, in 1000-unit glyph space. |
| `SimplePdf` | Native Python PDF document representation. |
| `StandardFonts` | Utility class for the PDF Standard 14 fonts. |
| `StreamDecoder` | Decode PDF stream data using supported filters. |
| `StreamEncoder` | Encode raw bytes into PDF stream data, the inverse of :class:`StreamDecoder`. |
| `TagTree` | The tag tree of ISO 32000-2 clause 14.8, used for structure inclusion. |
| `TextFragmentAbsorber-simple_pdf` | Absorber that extracts text fragments from a SimplePdf instance. |
| `TextObject` | A ``BT`` ... ``ET`` text object located in a content stream. |
| `TiffPage` | One image in a TIFF file. |
| `TimestampInfo` | Result of verifying an RFC 3161 timestamp token. |
| `TrueTypeOutlines` | Decode glyph outlines from an embedded TrueType (``glyf``) program. |
| `Type1Outlines` | Decode glyph outlines from a Type 1 (``/FontFile``) font program. |
| `XmpArray` | An ordered XMP array value. |
| `XmpField` | A single XMP property. |
| `XmpNamespaceProvider` | Bidirectional XMP namespace prefix URI resolver. |
| `XmpPacket` | An in-memory XMP packet: an ordered collection of properties. |
| `XmpProperty` | A property carrying arbitrary qualifiers. |
| `XmpStruct` | A structured XMP value (an ``rdf:parseType="Resource"`` block). |



### Generated

| Class | Description |
|---|---|
| `Document-generated_document` | Re-export of `aspose_pdf.Document`. |
| `PdfAValidateOptions-generated_pdfa` | Re-export of `aspose_pdf.pdfa.PdfAValidateOptions`. |
| `PdfAValidationResult-generated_pdfa` | Re-export of `aspose_pdf.pdfa.PdfAValidationResult`. |
| `UnsignedContent-generated_forms` | Re-export of `aspose_pdf.forms.UnsignedContent`. |
| `UnsignedContentAbsorber-generated_forms` | Re-export of `aspose_pdf.forms.UnsignedContentAbsorber`. |

---

### Security

| Class | Description |
|---|---|
| `CompromiseCheckResult` | Class with 4 properties. |
| `SignaturesCompromiseDetector` | Detect possible compromise indicators around signed PDFs. |

---

#### Detailed Member Reference

### Document Lifecycle

- `Document`
  - `load_from(source, password, limits) -> Document` / `open_streaming(path, password, limits) -> Document`
  - `save(destination, save_format, overwrite) -> Document` / `merge() -> Document`
  - `optimize(options, compress_streams) -> Document` (alias `optimize_resources(options) -> Document`)
  - `encrypt(user_password, owner_password, permissions) -> Document` / `decrypt(password) -> Document` /
    `change_passwords(old_password, new_user_password, new_owner_password) -> Document`
  - `validate() -> bool` / `check() -> bool` / `repair() -> Document`
  - `validate_pdfa(level) -> PdfAValidationResult` / `convert_to_pdfa(level, font_lookup_directory) -> list[str]`
  - `add_table_of_contents(title, max_level, prefer_structure, source="headings", at, size, margin, font_name, title_size, entry_size, indent, leader, links, page_numbers, tag) -> list[int]`
  - `sanitize(metadata, javascript, attachments, hidden_layers, comments, links, forms) -> SanitizationReport`
  - `save_as_svg(destination, pages, background, draw_annotations, font_substitution, precision, text, overwrite) -> list[Path]`
  - `fonts -> list[DocumentFont]` (name, subtype, encoding, embedded, program size, pages)
  - `embed_fonts(sources, directory) -> list[str]`
  - `validate_pdfua() -> PdfUaValidationResult` / `convert_to_pdfua(language, title, auto_tag) -> list[str]` /
    `auto_tag(image_alt) -> int`
  - `replace_text(search, replacement, page_index, case_sensitive, max_count) -> int` /
    `redact_text(search, page_index, case_sensitive, max_count, overlay, overlay_color) -> int`
  - `highlight_text(search, page_index, case_sensitive, max_count, regex, color, opacity, contents, title) -> TextHighlightResult`
  - `render_page(page_index, dpi, scale, background, antialias, shape_substitute_text, draw_annotations, font_substitution) -> RasterizedPage` /
    `save_page_as_image(page_index, destination, dpi, scale, background, antialias, mode, compression, quality, threshold) -> Path` /
    `save_as_tiff(destination, pages, dpi, scale, background, antialias, mode, compression, threshold) -> Path` /
    `save_as_svg(destination, pages, background, draw_annotations, font_substitution, precision, overwrite) -> list[Path]`
  - `render_contact_sheet(pages, columns, thumbnail_size, margin, spacing, labels, background, page_background, label_color, antialias, include_annotations) -> RasterizedPage` /
    `save_contact_sheet(destination, ..., mode, compression, quality, threshold, lossless, method, dither) -> Path`
  - `render_thumbnail(page_index, size=(160, 220), background=(255, 255, 255), antialias=True, include_annotations=True) -> RasterizedPage` —
    render a one-based page directly within pixel bounds while preserving proportions
  - `rasterized_copy(pages=None, dpi=150, background=(255, 255, 255), antialias=True, include_annotations=True, mode="rgb", threshold=128, dither=False) -> Document` —
    create an independent image-only PDF from selected visible page views
  - `split_spreads(pages=None, layout="horizontal", reverse=False, split_ratio=0.5, gutter=0, flatten_fields=True) -> Document` —
    replace selected spreads with two cropped pages in an independent document
  - `export_pages_zip(destination=None, pages=None, image_format="png", dpi=72, ..., include_manifest=False, overwrite=True) -> bytes` —
    package selected rendered page views as image files with optional source-page metadata
  - `compare_visual(other, pages, other_pages, dpi, tolerance, max_diff_ratio, include_annotations, include_diff_images, ignore_regions=None) -> list[PageVisualComparison]`
  - `compare_text(other, pages=None, other_pages=None, case_sensitive=True, ignore_whitespace=False, skip_artifacts=False, exclude_regions=None) -> list[PageTextComparison]` —
    review extracted page text revisions with normalized unified diffs
  - `to_html(pages, title, embed_images, paragraph_gap, clip_to_page) -> str` /
    `to_markdown(pages, title, embed_images, markdown_format, paragraph_gap, clip_to_page) -> str` /
    `save_as_html(destination, pages, title, embed_images, split_into_pages, resources_directory, paragraph_gap, clip_to_page, overwrite) -> list[Path]` /
    `save_as_markdown(destination, pages, title, embed_images, image_directory, markdown_format, paragraph_gap, clip_to_page, overwrite) -> Path`
  - `flatten(fields=True, annotations=True, pages=None, strict=True) -> Document` /
    `generate_appearances(force) -> int` / `generate_field_appearances() -> int`
  - `split_by_bookmarks(level=1, include_preamble=True) -> list[Document]` —
    split chapters at local bookmarks and retain leading pages in a separate document
  - `export_split_zip(destination=None, pages_per_part=1, compression="deflate", compresslevel=6, include_manifest=False, overwrite=True) -> bytes` —
    package consecutive PDF parts into one archive, optionally recording source page ranges
  - `export_bookmarks_json(destination=None, resolve_named_destinations=True, overwrite=True) -> bytes` /
    `import_bookmarks_json(source, replace=False, page_map=None) -> int` — exchange a
    versioned bookmark tree, preserving supported targets and styles
  - `export_bookmarks_csv(destination=None, delimiter=",", encoding="utf-8", overwrite=True) -> bytes` /
    `import_bookmarks_csv(source, replace=False, page_map=None, delimiter=",", encoding="utf-8-sig") -> int` —
    edit simple bookmark hierarchies and page targets as `level,title,page` rows
  - `split_by_text(pattern, regex=False, case_sensitive=True, include_preamble=True, clip=None) -> list[Document]` —
    split a batch at pages containing a literal or regular expression match
  - `generate_outlines_from_text(pattern, pages=None, regex=False, case_sensitive=True, title_group=0, replace=True, max_count=0, clip=None, exclude_regions=None, skip_artifacts=False) -> int` —
    create flat page bookmarks from extracted text matches and optional capture titles
  - `split_by_blank_pages(keep_separators=False, dpi=72, white_threshold=250, max_ink_ratio=0, include_annotations=True) -> list[Document]` —
    separate scan batches using visibly blank separator pages
  - `interleave(other, reverse_other=False, strict=True) -> Document` — alternate
    front/back scans into a new document, optionally reversing the back-side order
  - `find_blank_pages(pages=None, dpi=72, white_threshold=250, max_ink_ratio=0, include_annotations=True) -> list[int]` —
    find visually blank pages without modifying the document
  - `get_content_bounds(pages=None, dpi=72, white_threshold=250, include_annotations=True) -> dict[int, tuple[float, float, float, float] | None]` —
    measure visible content per selected page without cropping
  - `auto_crop(margin=0, pages=None, uniform=False, dpi=72, white_threshold=250, include_annotations=True, dry_run=False) -> dict[int, tuple[float, float, float, float]]` —
    trim selected pages individually or with one shared frame, with optional preview
  - `find_duplicate_pages(pages=None, dpi=72, include_annotations=True) -> list[list[int]]` —
    group pages with identical rendered views without deleting them
  - `remove_duplicate_pages(pages=None, keep="first", dpi=72, include_annotations=True, dry_run=False) -> list[int]` —
    remove repeated page views and return their original indices
  - `iter_pages() -> Iterator[Page]` / `iter_page_content_streams() -> Generator[bytes, None, None]`
  - `sync_metadata(direction) -> Document` /
    `add_attachment(name, content, mime, description, creation_date, mod_date, compress) -> Document`
  - `export_attachments_zip(destination=None, names=None, compression="deflate", compresslevel=6, include_manifest=False, overwrite=True) -> bytes`
  - `import_attachments_zip(source, names=None, on_conflict="error", use_manifest=True, compress=True) -> int`
  - `export_images_zip(destination=None, pages=None, compression="deflate", compresslevel=6, include_manifest=False, overwrite=True) -> bytes` —
    package reusable image assets with optional page provenance
  - `find_low_resolution_images(min_dpi=150, pages=None) -> list[ImageResolutionIssue]` —
    locate image placements below the requested effective DPI before delivery
  - properties: `pages`, `page_labels`, `form`, `outlines`, `layers`, `tagged_content`, `load_limits`,
    `xmp_metadata`, `embedded_files`, `page_count`, `info`, `is_encrypted`, `permissions`,
    `is_pdfua_compliant`, `font_substitution`, `page_mode`, `page_layout`, `open_action`,
    `viewer_preferences`, `base_uri`, `language`
  - `add_stamp(stamp, pages) -> Document` — stamp the pages named, or every page

### Pages And Content

- `Page`
  - `translate_content(dx, dy) -> Page` — move existing content and annotation geometry in PDF points
  - `add_text(text, x, y, font_size, font_name, font, color, tag, actual_text, layout) -> Page`
  - `add_image(image, x, y, width, height, fit="stretch", anchor="center", pixel_width, pixel_height, color_space, bits_per_component, name, tag, alt, actual_text) -> str` —
    use `fit="contain"` or `fit="cover"` with `anchor` to align an image in a frame while preserving its proportions
  - `draw_rectangle(x, y, width, height, stroke_color, fill_color, line_width, tag, alt, actual_text) -> Page` /
    `draw_line(x1, y1, x2, y2, stroke_color, line_width, tag, alt, actual_text) -> Page`
  - `render(dpi, scale, background, antialias) -> RasterizedPage` /
    `save_as_image(path, dpi, scale, background, antialias) -> Path`
  - `is_blank(dpi=72, white_threshold=250, max_ink_ratio=0, include_annotations=True) -> bool` —
    test the page's rendered appearance on white paper
  - `auto_crop(margin=0, dpi=72, white_threshold=250, include_annotations=True) -> Page` —
    trim white margins around rendered content by shrinking CropBox
  - `get_content_bounds(dpi=72, white_threshold=250, include_annotations=True) -> tuple[float, float, float, float] | None` —
    measure visible content without changing page boxes
  - `add_stamp(stamp) -> Page` — a text, image or page-number stamp over or under the page
  - `render_thumbnail(size=(160, 220), background=(255, 255, 255), antialias=True, include_annotations=True) -> RasterizedPage` —
    create a fitted preview that can be saved in the usual image formats
  - `replace_text(...) -> int` / `redact_text(...) -> int`
  - `highlight_text(...) -> TextHighlightResult` — annotations and a report of unplaceable matches
  - properties: `index`, `label`, `rect`, `media_box`, `crop_box`, `rotation`, `tab_order`, `annotations`, `content`
    Set `tab_order` to `"row"`, `"column"` or `"structure"` for keyboard navigation
    through fields and annotations; `None` clears the page's explicit preference.
- `PageCollection` — `item(index) -> Page`, `add(page) -> Page`, `insert(index, page) -> Page`
  (the page may belong to another document, and is then imported with all it names),
  `delete(index) -> None`, `clear() -> None`, `contains(page) -> bool`, `index_of(page) -> int`,
  `pop(index=None) -> Page` (removes and returns a page, defaulting to the last page)
- `PageLabelCollection` (`Document.page_labels`) — a mutable mapping from the page a label range
  starts at to its `PageLabel(style, prefix, start)`; `NumberingStyle` names the five styles and
  `NONE`; `label(page_index) -> str | None`, `clear()`

### Text Extraction And Editing

- `Document.highlight_text()` / `Page.highlight_text()` find a phrase or regex and add
  highlight annotations. `TextHighlightResult` reports `highlighted_count`, `skipped_count`,
  `matched_count`, editable `annotations`, and `skipped_fragments` with text/page/offsets.

- `Document.auto_link(pages=None, urls=True, emails=True, max_count=0)` /
  `Page.auto_link(urls=True, emails=True, max_count=0)` create clickable addresses.
  `AutoLinkResult` reports `linked_count`, `skipped_count`, `existing_count`,
  `matched_count`, live `annotations`, `skipped_fragments` and `existing_fragments`.

- `Document.replace_link_urls(search, replacement, pages=None, regex=False, case_sensitive=True, dry_run=False)` /
  `Page.replace_link_urls(search, replacement, regex=False, case_sensitive=True, dry_run=False)`
  return the number of changed Link annotations, replacing primary URI URLs.

- `Document.link_text(search, uri=None, *, target=None, pages=None, case_sensitive=True, max_count=0)` /
  `Page.link_text(search, uri=None, *, target=None, case_sensitive=True, max_count=0)`
  link literal phrases to a URI, typed PDF destination or existing destination
  name, and return `AutoLinkResult`.

- `Document.extract_text(pages=None, clip=None, skip_artifacts=False, exclude_regions=None)` /
  `Page.extract_text(clip=None, skip_artifacts=False, exclude_regions=None)` return text,
  with one-based page selection on `Document`,
  optionally selecting glyphs overlapping `(x0, y0, x1, y1)` in unrotated PDF space
  and excluding rectangular regions or explicitly marked Artifact content.

- `Document.extract_words(pages=None, clip=None, skip_artifacts=False)` /
  `Page.extract_words(clip=None, skip_artifacts=False)` return immutable `TextWord`
  snapshots with text, page index, `rect`/`bbox` and `quad`. A region selects
  whole overlapping words in unrotated PDF coordinates.

- `Document.export_words_json(destination=None, pages=None, clip=None, skip_artifacts=False, overwrite=True)` /
  `Page.export_words_json(destination=None, clip=None, skip_artifacts=False, overwrite=True)`
  return versioned UTF-8 word and geometry JSON, optionally writing a file or binary stream.

- `Document.export_words_csv(destination=None, pages=None, clip=None, skip_artifacts=False, delimiter=",", encoding="utf-8", overwrite=True)` /
  `Page.export_words_csv(...)` export the same words and geometry as CSV, with
  one-based page numbers, separate bounding coordinates and a quad cell.

- `Document.extract_tables(pages=None, clip_to_page=True)` / `Page.extract_tables(clip_to_page=True)`
  return `list[ExtractedTable]`; `pages` contains one-based indices. Each result exposes
  `page_index`, immutable `rows` / `column_spans`, `row_count`, `column_count`, `to_list()`,
  `to_csv(delimiter=",")` and `save_csv(path, delimiter=",", encoding="utf-8", overwrite=True)`.

- `Document.export_tables_zip(destination=None, pages=None, clip_to_page=True, delimiter=",", encoding="utf-8", compression="deflate", compresslevel=6, include_manifest=False, overwrite=True)` /
  `Page.export_tables_zip(...)` package detected tables as separate CSV files.
  Return ZIP bytes or save a path/binary stream; an optional manifest retains source-page references.

- `Document.extract_blocks(pages=None, include_images=False, paragraph_gap=None, clip_to_page=True)` /
  `Page.extract_blocks(...)` return `list[ExtractedBlock]` with immutable structure data,
  original page indices and unrotated PDF position anchors.
  `Document.export_blocks_json(destination=None, ..., overwrite=True)` / `Page.export_blocks_json(...)`
  return versioned UTF-8 JSON bytes and optionally write a path or binary stream.

  ```python
  with Document("report.pdf") as document:
      for block in document.extract_blocks(pages=[1]):
          print(block.page_index, block.kind, block.text, block.rows)
      document.export_blocks_json("report-structure.json")
  ```

- `PdfExtractor`
  - `bind_pdf(source, password, limits) -> None`
  - `extract_text(page_numbers=None, clip=None, skip_artifacts=False, exclude_regions=None) -> None` (one-based selection) /
    `get_text() -> str` / `has_next_page_text() -> bool` / `get_next_page_text() -> str`
  - `extract_image() -> None` / `has_next_image() -> bool` / `get_next_image() -> Any`
  - `extract_attachment() -> None` / `get_attachment(name) -> Any` / `get_attach_names() -> list[str]`
- `TextFragmentAbsorber` / `TextAbsorber` — search exact phrases and regex patterns, collecting
  `TextFragment` results with page index, match offsets and, for a page of a document, where the
  text sits: `rect`, `quads`, `font_name`, `font_size`, `color`.
- `PdfFileEditor`
  - `concatenate(inputs, output) -> bool`
  - `extract(source, destination, page_from, page_to) -> bool` /
    `insert(source, insert_file, destination, position) -> bool` /
    `delete(source, destination, pages_to_delete, page_to, page_from) -> bool` /
    `append(source, append_source, destination) -> bool` / `add_page_break(input_path, output_path) -> bool`
  - property: `last_exception: BaseException | None` — the boolean-return / `last_exception` error
    contract this legacy facade keeps.

### Forms And Annotations

- `FormFillerOptions(records, strict=True, flatten=False, password=None, limits=None)` /
  `FormFiller.process(options) -> ResultContainer` generate independent filled PDFs
  for each template/record pair. Add template data sources and optional paired outputs.

- `Form`
  - `add_text_field(name, page=None, rect=None, *, widgets=None, value="", font_size=12, multiline=False, alignment="left", read_only=False, required=False) -> Field`
    accepts either one `page` / `rect` pair or `widgets=[(page, rect), ...]` to repeat
    a text field across pages or several places on one page. All occurrences share
    one value, so filling a customer name once updates every occurrence.
  - `add_checkbox(name, page, rect, checked, on_value, read_only, required) -> Field` /
    `add_radio_group(name, page, options, value, read_only, required) -> Field`
  - `add_list_box(..., top_index=0) -> Field` / `add_combo_box(...) -> Field` /
    `add_push_button(name, page, rect, caption, read_only, required) -> Field`
  - `remove_field(name) -> Field` / `generate_appearances() -> int` /
    `flatten(fields=True, annotations=True, pages=None, strict=True) -> None`
  - `fill(values, strict=True) -> list[str]` / `to_dict() -> dict` /
    `export_json(destination=None) -> bytes` / `import_json(source, strict=True) -> list[str]`
  - `to_schema() -> dict` / `export_schema(destination=None, overwrite=True) -> bytes` —
    versioned template descriptions with field types, effective constraints, choices and defaults.
  - `to_json_schema() -> dict` / `export_json_schema(destination=None, overwrite=True) -> bytes` —
    JSON Schema Draft 2020-12 for normalized flat form answers and standard validation.
  - `reset(fields=None, strict=True) -> list[str]` — restore all or selected fields to template defaults
  - `validate(fields=None, strict=True) -> list[FormValidationIssue]` — inspect stored answers without changing them
  - `calculation_order` — read or replace the viewer's calculation sequence using
    fully qualified field names; assign `[]` or `None` to clear it.
  - `export_fdf(destination) -> bytes` / `export_xfdf(destination) -> bytes` /
    `import_fdf(source) -> list[str]` / `import_xfdf(source) -> list[str]` (form data interchange)
- `Field` — `remove() -> Field`; properties `name`, `value`, `field_type`, `partial_name`,
  `alternate_name`, `mapping_name`, `flags`, `read_only`, `required`, `no_export`, `default_value`,
  `max_length`, `multiline`, `password`, `comb`, `options`, `top_index`, `multi_select`, `editable`,
  `export_values`, `widgets` (`FieldWidget(page_index, rect)`), `page_index`, `rect`
  Configuration setters include `default_value`, `max_length`, `multiline`, `password`,
  `comb`, `options`, `top_index`, `multi_select` and `editable`.
  Assign `rect` to move or resize the first widget on its page, or call
  `set_widget_rect(rect, widget_index=0) -> Field` to select a widget by index.
  Existing appearances scale to fit; text is not reflowed.
  Set `rich_text` on a text field to XHTML with a `<body>` root to update its
  formatting, plain answer and appearance together; set `None` to keep the answer
  with plain formatting. Assigning `value` also replaces rich text with plain text.
- `FormValidationIssue` — an immutable record with `field_name`, `field_type`,
  `code` and `message`; an empty validation report means no covered value issues.
- `HideAction(fields, hide=True)` — attach a show/hide action to a button or event
  using fully qualified field names; `hide=False` shows the fields in a compatible viewer.
- `page.annotations.add_file_attachment(rect, file, contents=None, title=None, icon="PushPin", compress=True)` —
  place a clickable embedded `FileSpecification` on the page; read or save its
  bytes through `FileAttachmentAnnotation.file_specification`.
- `Annotation` — `generate_appearance(force) -> bool`, `get_property(name, default) -> Any`,
  `set_property(name, value) -> None`; properties `subtype`, `rect`, `contents`, `appearance_normal`
- `AnnotationCollection` — `add(subtype, rect, contents, title, appearance_normal, properties) -> Annotation`,
  `insert(...)`, `delete(index) -> None`, `generate_appearances(force) -> int`,
  `to_list(subtypes=None) -> list[dict]`, `export_json(destination=None, subtypes=None, overwrite=True) -> bytes`,
  `export_xfdf(destination=None, subtypes=None, overwrite=True) -> bytes`,
  `import_json(source) -> int`
- `Document.export_annotations_json(destination=None, pages=None, subtypes=None, overwrite=True) -> bytes`
  exports all or selected annotations to a path, binary stream or UTF-8 bytes.
- `Document.export_annotations_xfdf(destination=None, pages=None, subtypes=None, overwrite=True) -> bytes` /
  `Page.annotations.export_xfdf(destination=None, subtypes=None, overwrite=True) -> bytes`
  exports supported review comments and markup as UTF-8 XFDF, optionally writing a path or stream.
- `Document.remove_annotations(pages=None, authors=None, before=None, after=None, date_field="modified", subtypes=None, case_sensitive=True, dry_run=False) -> int` /
  `AnnotationCollection.remove_matching(...) -> int` remove selected review annotations
  by metadata or return the planned count without edits.
- `Document.import_annotations_json(source, page_map=None) -> int` appends supported review
  annotations from a path, UTF-8 bytes or readable binary stream; returns the number added.
- `Document.extract_links(pages=None)` / `Page.extract_links()` return
  `list[ExtractedLink]` for link auditing, navigation review and content migrations.
- `Document.export_links_json(destination=None, pages=None, overwrite=True)` /
  `Page.export_links_json(destination=None, overwrite=True)` /
  `Document.export_links_csv(destination=None, pages=None, delimiter=",", encoding="utf-8", overwrite=True)` /
  `Page.export_links_csv(destination=None, delimiter=",", encoding="utf-8", overwrite=True)`
  return report bytes and optionally save them to a file or binary stream.
- `Document.validate_links(pages=None, include_outlines=True, include_named_destinations=True)` /
  `Page.validate_links()` return `list[LinkValidationIssue]` without editing the PDF.
  Issues expose `source`, `code`, `message`, `page_index`, `annotation_index`,
  `outline_path`, `destination_name` and `target_path`.

### Security And Signatures

- `Document.encrypt(user_password, owner_password, permissions)` / `Document.decrypt(password)` /
  `Document.change_passwords(...)`
- `Document.sign(field=None, *, certificate, private_key, extra_certificates, reason, location,
  contact, signer_name, pades, timestamp_url, timestamp_authority, timestamp_timeout, certify,
  appearance)`,
  `Document.add_ltv(certificates, crls, ocsp_responses)`,
  `Document.add_document_timestamp(timestamp_url | timestamp_authority)` — carried out by `save()`
  as appended revisions (PAdES-B/T/LT/LTA), after which `Document.signatures` lists them
- `PdfSignature.validate(options) -> ValidationResult`; properties `valid`, `name`, `date`, `docmdp_level`
- `ValidationResult` — properties `is_valid`, `status`, `trust_status`, `revocation_status`,
  `certification_level`, `pades_level`
- `PdfLoadLimits` — immutable resource policy; `PdfLoadLimits.unlimited()` disables every field;
  covers `max_input_bytes`, `max_objects`, `max_decoded_stream_bytes`, `max_image_pixels`, and 12
  more bounded resources.

### Low-Code Plugins

- `Merger`, `Splitter`, `Optimizer`, `TextExtractor` — each a `PdfPlugin` subclass exposing
  `process(options) -> ResultContainer`.
- `FileDataSource`, `ByteArrayDataSource`, `StreamDataSource` — `DataSource` implementations for
  path, in-memory bytes, and stream inputs/outputs.
- `PluginOptions` — holds the input/output `DataSource` lists plus the resource-limit policy
  shared by a plugin run.

### Fonts

- `FontRepository` — `add_source(source) -> None`, `get_available_fonts() -> list[FontDescriptor]`,
  `find_font(font_name) -> FontDescriptor | None`, `open_font(font_name) -> bytes | None`
- `FontSource` hierarchy — `FolderFontSource`, `FileFontSource`, `MemoryFontSource`, `SystemFontSource`

</details>

