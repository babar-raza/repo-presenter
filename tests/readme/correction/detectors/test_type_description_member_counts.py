"""BL-094: ``type_description`` v3 holds a count cell to the class's own members.

M9 round 43559491132, Words Python Lane L control ab8a03, row 402: ``| `Style` | Class with 11
properties. |`` -- at 2d2efee2 ``aspose/words_foss/light_document_model.py:1012-1027`` declares 15
annotated pydantic fields. The class bodies below are verbatim from that file (``Style``, ``Border``,
``Shading``) and from aspose-pdf-foss/Aspose-PDF-FOSS-for-Python@02b0c0e4 ``src/aspose_pdf/engine/cos.py``
(``PdfStream``, whose base adds members) and ``src/aspose_pdf/visualization.py`` (``PerformanceLogger``);
each type fact's ``member_counts`` is computed from them exactly as re-certification computes it
(``source_detail.class_member_counts_from_source``). The table rows are the live README's.
"""

from __future__ import annotations

from typing import Any

from repo_presenter.readme.correction.detectors.type_description import type_description, true_count_cell
from repo_presenter.readme.evidence.facts.source_detail import class_member_counts_from_source

SOURCE = '''from pydantic import BaseModel, Field


class Border(BaseModel):
    line_style: int = 0
    line_width: float = 0.0
    is_visible: bool = True
    color: str = ""
    distance_from_text: float = 0.0
    shadow: bool = False


class Shading(BaseModel):
    background_pattern_color: str = ""
    foreground_pattern_color: str = ""
    # REMOVED: theme_color, theme_shade, theme_tint, theme_fill,


class Style(BaseModel):
    name: str = ""
    type: int = 0  # 1=paragraph, 2=character, 3=table
    is_heading: bool = False
    base_style_name: str = ""
    next_paragraph_style_name: str = ""
    paragraph_format: ParagraphFormat | None = None
    font: Font | None = None
    table_style_format: TableStyleFormat | None = None
    table_style_properties: list[TableStyleProperty] = Field(default_factory=list)
    style_identifier: int = 0
    built_in: bool = False
    priority: int = 99
    semi_hidden: bool = False
    unhide_when_used: bool = False
    locked: bool = False


class Body(BaseModel, NodeCastMixin):
    type: str = Field(default="Body", alias="_type")
    children: list[BodyChild] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @property
    def paragraphs(self) -> list[Paragraph]:
        return []

    @property
    def tables(self) -> list[Table]:
        return []


class PdfStream(PdfDictionary):
    def __init__(self, entries=None, data: bytes = b"") -> None:
        super().__init__(entries)
        self.data = data
        self.decoded = None

    def __repr__(self) -> str:
        return "PdfStream()"


class PerformanceLogger:
    def __init__(self) -> None:
        self.lines = []
        self.phases = {}

    def log_line(self, line: str) -> None:
        self.lines.append(line)

    def record(self, name: str, seconds: float) -> None:
        self.phases[name] = seconds

    def measure(self, name: str):
        yield

    @property
    def total(self) -> float:
        return 0.0

    def summarise(self) -> list[str]:
        return []
'''
ROWS = {
    "Border": "Class with 3 properties.",
    "Shading": "Class with 2 properties.",
    "Style": "Class with 11 properties.",
    "Body": "Class with 2 properties.",
    "PdfStream": "Class with 3 methods and 2 properties.",
    "PerformanceLogger": "Class with 2 methods and 1 property.",
}


def _line(name: str) -> int:
    return next(n for n, row in enumerate(SOURCE.splitlines(), 1) if row.startswith((f"class {name}(", f"class {name}:")))


def _facts(make_fact: Any, *, counted: bool = True) -> list[Any]:
    facts = []
    for name in ROWS:
        attributes = {"symbol_kind": "class"}
        if counted:
            attributes["member_counts"] = class_member_counts_from_source(SOURCE, f"pkg.{name}", "pkg/model.py", _line(name))
        facts.append(make_fact(f"public_symbol:pkg.{name.lower()}", f"pkg.{name}",
                               evidence=(("pkg/model.py", f"line {_line(name)}; class; public by name"),),
                               attributes=attributes))
    return facts


def _readme() -> str:
    rows = "".join(f"| `{name}` | {cell} |\n" for name, cell in ROWS.items())
    return "# Aspose.Words FOSS for Python\n\n## API Reference\n\n| Type | Description |\n|---|---|\n" + rows


def test_style_and_the_other_refuted_counts_become_the_true_count(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    ctx = make_context(_readme(), make_facts(*_facts(make_fact)))
    edits = {e.original: e.replacement for e in type_description(ctx).edits}
    assert edits == {
        "Class with 11 properties.": "Class with 15 properties.",
        "Class with 3 properties.": "Class with 6 properties.",
        "Class with 2 methods and 1 property.": "Class with 4 methods and 1 property.",
    }
    # R14: every row stays, only the cell's numbers change
    corrected = ctx.readme
    for edit in sorted(type_description(ctx).edits, key=lambda e: -e.start):
        corrected = corrected[: edit.start] + edit.replacement + corrected[edit.end :]
    assert corrected.count("\n| `") == len(ROWS)


def test_negative_controls(make_context: Any, make_facts: Any, make_fact: Any) -> None:
    facts = {f.value.rsplit(".", 1)[-1]: f for f in _facts(make_fact)}
    assert true_count_cell("Class with 2 properties.", facts["Shading"]) is None  # true
    assert true_count_cell("Class with 2 properties.", facts["Body"]) is None  # 2 fields (or 2 @property)
    # PdfStream: 3 methods is above its own (0..2), and its base adds members: not refuted
    assert true_count_cell("Class with 3 methods and 2 properties.", facts["PdfStream"]) is None
    # "members" is never judged (enum-like constants)
    assert true_count_cell("Class with 4 methods and 9 members.", facts["PerformanceLogger"]) is None
    # a type with no member_counts (facts sealed before them, read nothing from source) is never judged
    ctx = make_context(_readme(), make_facts(*_facts(make_fact, counted=False)))
    assert [e for e in type_description(ctx).edits if "propert" in e.original] == []


def test_recertification_reads_member_counts_from_the_pinned_sources(make_fact: Any) -> None:
    """Facts sealed before ``member_counts`` existed gain it from the pinned sources
    (``recertify.current_surface``), so a re-certified seal's Lane L correction can hold the cell."""
    from repo_presenter.core.facts import FactsDocument
    from repo_presenter.recertify import SourceSnapshot, current_surface

    style = make_fact("public_symbol:pkg.style", "pkg.Style",
                      evidence=(("pkg/model.py", f"line {_line('Style')}; class; public by name"),),
                      attributes={"symbol_kind": "class"})
    document = FactsDocument("o/r", "a" * 40, (style,))
    source = SourceSnapshot(tree_paths=("pkg/model.py",), readme=b"", manifests={"pyproject.toml": "[project]\nname='x'\n"},
                            sources={"pkg/model.py": SOURCE})
    updated, clause = current_surface(document, "python", source)
    assert clause and "member_counts" in clause
    assert (updated.facts[0].attributes or {})["member_counts"] == "method=0,dunder=0,init=0,property=0,field=15,inherits=0"
    # negative control: no sources (not a Python build, or over the bounds) -> nothing changes
    assert current_surface(document, "python", SourceSnapshot(tree_paths=(), readme=b""))[1] is None
