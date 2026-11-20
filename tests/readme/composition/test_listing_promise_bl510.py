"""BL-510: a kept paragraph that promises its types are listed below stays above the table that lists them.

Hosted Lane R PDF TypeScript (run 44717025933, main d60d709) was rejected by one deterministic finding after 51
provider calls: "the README says its count of public types is listed in what follows, but the table rows that follow
list only 445". The sentence is the maintainers' paragraph (``inherited_unit:501.paragraph``), kept in the API
Reference: "... 533 public types plus 171 functions, classes and constants, grouped below by capability. Every name
`index.ts` exports appears in one of these tables." The renderer's Core API table lists all 533 types above it; P4
prints the maintainers' own tables without the rows that table already prints, so only 445 rows remained under the
paragraph. PDF Python (run 44701575389) is the same defect: "388 public types are organized by module below." over
266 rows. The last-resort degrade could not help: withholding the paragraph (an inherited unit) trades 2 findings for
2 BC-17 losses of the identifiers it names (blocking load 105 -> 105).

The paragraph is the maintainers' text, byte for byte; only its position moves, and only when the rows after it fall
short and the move supplies enough. Every sentence below is a hosted or published line, verbatim.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.composition import renderer
from repo_presenter.readme.composition.renderer import render_readme
from repo_presenter.readme.validation.claims import claim_findings
from repo_presenter.readme.validation.surface_claims import listing_promise
from tests.readme.repair import test_accounting as base

#: PDF TypeScript inherited_unit:501.paragraph (live README at 1d4f649; the count is the maintainers').
PDF_TS = (
    "The public entry points are organized around `Document` and `Page` (the core object model),\n"
    "`Font`/`EmbeddedFont` (text authoring), `Annotation` and `Field` (interactive content), and\n"
    "per-capability builders such as `PageGraphics`, `Flow` and `Table` — 7 public types plus 171\n"
    "functions, classes and constants, grouped below by capability. Every name `index.ts` exports appears in one\n"
    "of these tables."
)
#: PDF Python inherited_unit:258.paragraph (hosted run 44701575389).
PDF_PY = (
    "`PdfFileEditor` provides a boolean-returning facade for file-based concatenate, extract, insert,\n"
    "and delete workflows. 7 public types are organized by module below."
)
#: The maintainers' tables: functions and helpers the Core API table does not print.
TABLE = (
    "| Function | Description |\n|---|---|\n"
    "| `richTextToPlain` | Converts rich text to plain text. |\n"
    "| `Helper` | Helper builder. |\n"
    "| `Other` | Other builder. |"
)
FINDING = "listed in what follows"


def _world(paragraph: str) -> tuple[FactsDocument, dict[str, Any], dict[str, Any], dict[str, Any]]:
    facts = [f for f in base._facts().facts if f.kind != "public_symbol"]
    facts += [
        Fact(f"public_symbol:t{i}", "public_symbol", f"aspose.threed.T{i}",
             (Evidence("x.py", "line 1; class; public by name"),), polarity="SUPPORTED",
             attributes={"symbol_kind": "class"})
        for i in range(7)
    ]
    scene = Fact("public_symbol:aspose.threed.scene", "public_symbol", "aspose.threed.Scene",
                 (Evidence("x.py", "line 1; class; public by name"),), polarity="SUPPORTED",
                 attributes={"symbol_kind": "class"})
    facts = [f for f in facts if f.value != "aspose.threed.T6"] + [scene]
    facts += [base._unit("007.paragraph", paragraph), base._unit("008.table", TABLE)]
    document = FactsDocument(base.ENTRY.repository, base.REVISION, tuple(facts))
    dispositions = base._dispositions()
    dispositions["dispositions"] += [
        base._entry("007.paragraph", "VERIFIED_PRESERVE", "api_reference", []),
        base._entry("008.table", "VERIFIED_PRESERVE", "api_reference", []),
    ]
    return document, base._plan(), copy.deepcopy(base.UNITS), dispositions


def _promise_findings(readme: str, document: FactsDocument) -> list[str]:
    return [f.detail for f in claim_findings(readme, document) if FINDING in f.detail]


@pytest.mark.parametrize("paragraph", [PDF_TS, PDF_PY])
def test_the_paragraph_stays_above_the_table_that_lists_every_type(paragraph: str) -> None:
    document, plan, units, dispositions = _world(paragraph)
    readme = render_readme(base.ENTRY, document, plan, units, dispositions)
    assert paragraph in readme  # the maintainers' words, byte for byte (R14: nothing dropped)
    assert readme.index(paragraph) < readme.index("### Core API")
    assert "`richTextToPlain`" in readme  # the kept table's own rows still print
    assert readme.index("### Core API") < readme.index("`richTextToPlain`")
    assert _promise_findings(readme, document) == []


@pytest.mark.parametrize("paragraph", [PDF_TS, PDF_PY])
def test_without_the_move_the_hosted_finding_is_reproduced(
    paragraph: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # the negative control for the fix itself: the same world, the placement left as P4 printed it
    monkeypatch.setattr(renderer, "_listing_promises_first", lambda lines, placed, facts: (lines, placed))
    document, plan, units, dispositions = _world(paragraph)
    readme = render_readme(base.ENTRY, document, plan, units, dispositions)
    assert readme.index("### Core API") < readme.index(paragraph)
    (detail,) = _promise_findings(readme, document)
    assert "list only 3" in detail


@pytest.mark.parametrize("paragraph, stated", [(PDF_TS, 7), (PDF_PY, 7)])
def test_the_detector_reads_the_promise_the_hosted_lines_make(paragraph: str, stated: int) -> None:
    assert listing_promise(paragraph) == stated


@pytest.mark.parametrize("sentence", [
    # negative controls: no promise to hold the paragraph to the rows below it
    "The library exposes 303 public types in total, 238 of them listed below by module, with curated highlights following.",
    "385 public types — 284 of them organized by module below.",
    "There are 533 public types; see the reference site for the list.",
    "The public API has 533 types.",
    "Every name `index.ts` exports appears in one of these tables.",
])
def test_a_sentence_that_promises_no_listing_is_not_a_promise(sentence: str) -> None:
    assert listing_promise(sentence) is None


def test_a_paragraph_with_enough_rows_after_it_is_not_moved() -> None:
    # a sealed README's shape: the kept tables under the paragraph already list the stated count
    document, *_ = _world(PDF_TS)
    long = "| Class | Description |\n|---|---|\n" + "\n".join(f"| `K{i}` | k. |" for i in range(9))
    lines = ["### Core API", "", "| Class | Description |", "| --- | --- |", "| `A` | a |"]
    assert renderer._listing_promises_first(list(lines), [PDF_TS, long], document) == (lines, [PDF_TS, long])
    # and a paragraph that promises nothing is never moved
    assert renderer._listing_promises_first(list(lines), ["Plain paragraph.", TABLE], document) == (
        lines, ["Plain paragraph.", TABLE])


def test_a_move_that_still_leaves_too_few_rows_is_not_made() -> None:
    # the rendered table is not there (no Core API heading): nothing to put the paragraph above
    document, *_ = _world(PDF_TS)
    lines, placed = renderer._listing_promises_first(["intro", ""], [PDF_TS, TABLE], document)
    assert (lines, placed) == (["intro", ""], [PDF_TS, TABLE])
    # and a table too short to supply the stated count leaves the order alone
    short = ["### Core API", "", "| Class | Description |", "| --- | --- |", "| `A` | a |"]
    lines, placed = renderer._listing_promises_first(list(short), [PDF_TS, TABLE], document)
    assert (lines, placed) == (short, [PDF_TS, TABLE])
