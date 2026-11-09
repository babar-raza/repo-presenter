"""Static format evidence for Python products outside the FileFormat/register_plugin layout.

The source excerpts are VERBATIM from the real repositories (shallow clones, 2026-11-10):
aspose-cells-foss/Aspose.Cells-FOSS-for-Python (aspose/cells_foss/workbook.py),
aspose-page-foss/Aspose.Page-FOSS-for-Python (src/aspose/page/image/{encoders,raster_writer}.py,
src/aspose/page/ps/parser.py shape), aspose-font-foss/Aspose.Font-FOSS-for-Python
(src/aspose_font/batch_workflow.py, loader.py) and aspose-slides-foss/Aspose.Slides-FOSS-for-Python
(aspose/slides_foss/Presentation.py). They exercise the whole path: format_declarations ->
format_facts, so SUPPORTED means exactly what the pipeline would record.
"""

from __future__ import annotations

from pathlib import Path

from repo_presenter.extractors.platforms.python_format_declarations import format_declarations
from repo_presenter.readme.evidence.facts.formats import format_facts


def _facts(tmp_path: Path, files: dict[str, str]) -> dict[str, str]:
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    declarations = format_declarations(tmp_path, sorted(files))
    facts = format_facts([], [], lambda _code: [], "receipts.json", declarations)
    return {fact.id.split(":", 1)[1]: fact.polarity for fact in facts}


CELLS = '''
class SaveFormat(Enum):
    AUTO = auto()       # Auto-detect format from file extension
    XLSX = auto()       # Excel 2007+ format (.xlsx)
    CSV = auto()        # Comma-separated values (.csv)
    TSV = auto()        # Tab-separated values (.tsv)
    MARKDOWN = auto()   # Markdown format (.md)
    JSON = auto()       # JSON format (.json)
    PDF = auto()        # Portable Document Format (.pdf)

    @classmethod
    def from_extension(cls, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        format_map = {
            '.xlsx': cls.XLSX,
            '.xlsm': cls.XLSX,
            '.csv': cls.CSV,
            '.tsv': cls.TSV,
            '.md': cls.MARKDOWN,
            '.markdown': cls.MARKDOWN,
            '.json': cls.JSON,
            '.pdf': cls.PDF,
        }
        if ext in format_map:
            return format_map[ext]
        raise ValueError(f"Unsupported file extension: {ext}")


class Workbook:
    def save(self, file_path, save_format=None, options=None):
        if save_format is None or save_format == SaveFormat.AUTO:
            save_format = SaveFormat.from_extension(file_path)

        if save_format == SaveFormat.XLSX:
            self._save_xlsx(file_path)
        elif save_format == SaveFormat.CSV:
            self.save_as_csv(file_path, options)
        elif save_format == SaveFormat.TSV:
            if options is None:
                options = CSVSaveOptions()
            options.delimiter = '\\t'
            self.save_as_csv(file_path, options)
        elif save_format == SaveFormat.MARKDOWN:
            self.save_as_markdown(file_path, options)
        elif save_format == SaveFormat.JSON:
            self.save_as_json(file_path, options)
        elif save_format == SaveFormat.PDF:
            self.save_as_pdf(file_path, options)
        else:
            raise ValueError(f"Unsupported save format: {save_format}")
'''

PAGE_ENCODERS = '''
def encode_png(surface, dpi=72):
    return _png_bytes(surface, dpi)


def encode_bmp(surface):
    return b"BM" + _bmp_bytes(surface)


def encode_tiff(surface):
    return b"II" + _tiff_bytes(surface)


def encode_jpeg(surface):
    return _jpeg_bytes(surface)
'''

PAGE_WRITER = '''
from .encoders import encode_bmp, encode_jpeg, encode_png, encode_tiff


class RenderModelRasterWriter:
    def write(self, document, options):
        fmt = options.format.lower()
        surface = self._render(document, options)
        if fmt == "png":
            return encode_png(surface, dpi=options.dpi)
        if fmt in ("jpeg", "jpg"):
            return encode_jpeg(surface)
        if fmt == "tiff":
            return encode_tiff(surface)
        if fmt == "bmp":
            return encode_bmp(surface)
        raise ValueError(f"unsupported format {options.format}")
'''


def test_cells_save_dispatch_plus_the_extension_map_make_tsv_and_pdf_supported(tmp_path: Path) -> None:
    polarity = _facts(tmp_path, {"aspose/cells_foss/workbook.py": CELLS})
    for key in ("output.csv", "output.tsv", "output.json", "output.md", "output.markdown",
                "output.pdf", "output.xlsx", "output.xlsm"):
        assert polarity[key] == "SUPPORTED", key
    # SaveFormat.AUTO is a behaviour, and nothing declares a ".auto" extension
    assert "output.auto" not in polarity
    # an output-only dispatch never invents an input direction
    assert not any(key.startswith("input.") for key in polarity)


def test_page_raster_writer_dispatch_corroborated_by_the_codec_functions(tmp_path: Path) -> None:
    polarity = _facts(
        tmp_path,
        {"src/aspose/page/image/encoders.py": PAGE_ENCODERS,
         "src/aspose/page/image/raster_writer.py": PAGE_WRITER},
    )
    for key in ("output.png", "output.bmp", "output.tiff", "output.jpeg"):
        assert polarity[key] == "SUPPORTED", key
    # "jpg" is dispatched but no codec/declaration states it: not a fact at all
    assert "output.jpg" not in polarity


FONT_BATCH = '''
_SUPPORTED_EXTENSIONS = (".ttf", ".otf", ".cff", ".woff", ".woff2", ".eot", ".pfa", ".pfb")


def _is_supported_font_file(path):
    """Check if file has a supported font extension."""
    return path.suffix.lower() in _SUPPORTED_EXTENSIONS
'''

FONT_LOADER = '''
class FontLoader:
    @staticmethod
    def _detect_with_source(source, data):
        if isinstance(source, (str, os.PathLike)):
            source_path = os.fspath(source).lower()
            # Path-based .cff files in this project may be wrapped in a PS container.
            if source_path.endswith(".cff"):
                return FontType.CFF
            if source_path.endswith(".eot"):
                return FontType.EOT
        return FontLoader._detect(data)
'''


def test_font_only_the_extensions_the_loader_actually_dispatches_on_become_supported(tmp_path: Path) -> None:
    polarity = _facts(
        tmp_path,
        {"src/aspose_font/batch_workflow.py": FONT_BATCH, "src/aspose_font/loader.py": FONT_LOADER},
    )
    assert polarity["input.cff"] == "SUPPORTED" and polarity["input.eot"] == "SUPPORTED"
    # .otf/.woff/.woff2/.pfa/.pfb are declared in the batch filter but no extension dispatch wires
    # them (the loader sniffs magic bytes): declared-only is not working, so no fact is made.
    for extension in ("otf", "woff", "woff2", "pfa", "pfb", "ttf"):
        assert not any(key.endswith("." + extension) for key in polarity), extension


SLIDES_PRESENTATION = '''
class Presentation:
    def _detect_source_format(self, path):
        """Detect source format from file extension."""
        lower_path = path.lower()
        if lower_path.endswith('.pptx') or lower_path.endswith('.pptm') or \\
           lower_path.endswith('.ppsx') or lower_path.endswith('.potx'):
            self._source_format = SourceFormat.PPTX
        elif lower_path.endswith('.ppt'):
            self._source_format = SourceFormat.PPT
        elif lower_path.endswith('.odp'):
            self._source_format = SourceFormat.ODP
'''


def test_an_extension_check_that_only_labels_the_source_format_is_not_a_registration(tmp_path: Path) -> None:
    """Slides' real _detect_source_format assigns an enum label and does no loading, and its name
    carries no direction: it must not turn .pptm/.ppsx/.potx (or .ppt/.odp) into facts."""
    assert _facts(tmp_path, {"aspose/slides_foss/Presentation.py": SLIDES_PRESENTATION}) == {}


def test_a_stub_branch_registers_nothing(tmp_path: Path) -> None:
    source = '''
_EXTENSIONS = (".stl", ".obj")


def export(scene, fmt):
    if fmt == "stl":
        raise NotImplementedError("stl export")
    if fmt == "obj":
        return write_obj(scene)
'''
    polarity = _facts(tmp_path, {"pkg/io.py": source})
    assert polarity == {"output.obj": "SUPPORTED"}


def test_a_dispatch_on_a_literal_no_declaration_states_is_not_a_format(tmp_path: Path) -> None:
    """Real Page PostScript tokenizer shape: parse_object dispatches on 'name'/'string' token kinds
    and a read_name()/read_string() parser step exists -- none of it is a file format."""
    source = '''
def parse_object(token):
    if token.kind == "name":
        return Name(token.text)
    if token.kind == "string":
        return String(token.text)


def _read_name(stream):
    return stream.read()
'''
    assert _facts(tmp_path, {"src/aspose/page/ps/parser.py": source}) == {}


def test_test_and_example_directories_are_never_read(tmp_path: Path) -> None:
    source = (
        '_EXTENSIONS = (".stl", ".obj")\n\n\ndef export(scene, fmt):\n'
        '    if fmt == "stl":\n        return write_stl(scene)\n'
    )
    assert _facts(tmp_path, {"tests/test_io.py": source, "examples/io.py": source}) == {}
