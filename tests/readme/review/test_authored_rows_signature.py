"""BL-390: the production review must show the same authored API rows the M9 audit shows.

Hosted M9 round 44588173276 flagged 14 rows of the Aspose.Note Python README (a clean control) that the
seal-time review never saw: ``scope.authored_table_lines`` skipped every type carrying a ``signature``
although ``authoring.undocumented_types`` writes (and the renderer prints) a sentence for it. The rows
below are the exact lines of that README.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.scope import authored_table_lines, authored_type_rows, renderer_row_descriptions
from repo_presenter.readme.validation.code_path_claims import NOT_THROWN_DESCRIPTION


def _type(name: str, signature: str, **attributes: str) -> Fact:
    return Fact(
        f"public_symbol:aspose.note.{name.lower()}", "public_symbol", f"aspose.note.{name}",
        (Evidence("aspose/note/model.py"),), "SUPPORTED",
        attributes={"symbol_kind": "class", "signature": signature, **attributes},
    )


README = """# Aspose.Note FOSS for Python

## API Reference

### Core API

| Class | Description |
| --- | --- |
| `Document` | Document class represents a OneNote document and provides methods to detect layout changes, get page history, and save the document. |
| `License` | License class provides a method to set the license. |
| `IncorrectDocumentStructureException` | Declared; not thrown by library code. |
| `Metered` | Defined as `class Metered`. |
| `Documented` | Represents a documented class. |
"""


def _facts() -> FactsDocument:
    return FactsDocument(
        "o/r", "a" * 40,
        (
            _type("Document", "class Document(CompositeNode)"),
            _type("License", "class License"),
            _type("IncorrectDocumentStructureException", "class IncorrectDocumentStructureException(AsposeNoteError)"),
            _type("Metered", "class Metered"),
            _type("Documented", "class Documented", docstring="Represents a documented class."),
        ),
    )


def test_a_signature_bearing_type_without_a_docstring_has_an_authored_row() -> None:
    rows = README.splitlines()
    authored = authored_table_lines(README, _facts())
    assert [rows[n - 1].split("|")[1].strip() for n in sorted(authored)] == ["`Document`", "`License`"]


def test_the_renderers_own_fact_true_rows_are_not_authored() -> None:
    types = {f.value.rsplit(".", 1)[-1]: f for f in _facts().facts}
    assert NOT_THROWN_DESCRIPTION in renderer_row_descriptions(types["IncorrectDocumentStructureException"])
    assert "Defined as `class Metered`." in renderer_row_descriptions(types["Metered"])
    named = {f.id.rsplit(".", 1)[-1] for f in authored_type_rows(README, _facts()).values()}
    assert named == {"document", "license"}


def test_a_documented_type_stays_the_renderers() -> None:
    assert "`Documented`" not in {
        README.splitlines()[n - 1].split("|")[1].strip() for n in authored_table_lines(README, _facts())
    }
