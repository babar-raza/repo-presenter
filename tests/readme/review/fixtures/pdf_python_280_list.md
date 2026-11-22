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