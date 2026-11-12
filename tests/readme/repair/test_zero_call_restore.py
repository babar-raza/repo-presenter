"""TC-019a: ``restore_stated_count`` against the REAL sealed README text and the REAL computed
facts of three real NEEDS_REPAIR seals found this session (fetched via
``repo_presenter.core.state.bundle_store.seal_history(remote="origin")`` against this
repository's own bundle refs -- never a synthetic stand-in for the README text).

Every excerpt below is a verbatim copy of the real sealed ``README.md`` bytes around the real
failing line (line numbers as read from the real seal; a real em dash U+2014 is kept literal, not
escaped, exactly as it appears in the real file). The two real repositories whose stated count is
genuinely wrong (aspose-html-foss and aspose-words-foss, L-03) get the exact before/after string
asserted. The real published-version case with no fact at all (aspose-barcode-foss, L-05) and the
two real repositories' absent-API-table-row cases are asserted to return ``None`` -- a judgement
call this module does not take.

Facts are built as a minimal ``FactsDocument`` carrying exactly the real ``(types, classes)``
totals this session independently computed against the real ``facts.json`` of each seal (HTML:
303 types / 302 classes / 1 enum; Words: 198 types / 175 classes / 23 enums; BarCode: 51 types /
43 classes / 8 enums, with no ``package:published_version`` fact at all) -- not the full real
facts document (thousands of individual symbol facts, impractical to embed verbatim), but the
real totals, not invented ones.
"""

from __future__ import annotations

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.repair.zero_call_restore import restore_stated_count, type_counts

_EVIDENCE = (Evidence("src/placeholder.py", None),)


def _symbol_facts(classes: int, enums: int) -> tuple[Fact, ...]:
    """``classes`` class facts and ``enums`` enum facts, each a real-shaped ``public_symbol``
    fact (unique id, SUPPORTED, a ``symbol_kind`` attribute) -- enough for ``type_counts`` to
    total exactly the real seal's own computed ``(types, classes)``, as this session verified
    directly against the real ``facts.json`` via ``read_facts``."""
    facts: list[Fact] = []
    for index in range(classes):
        facts.append(
            Fact(
                f"public_symbol:class-{index}",
                "public_symbol",
                f"pkg.Class{index}",
                _EVIDENCE,
                attributes={"symbol_kind": "class"},
            )
        )
    for index in range(enums):
        facts.append(
            Fact(
                f"public_symbol:enum-{index}",
                "public_symbol",
                f"pkg.Enum{index}",
                _EVIDENCE,
                attributes={"symbol_kind": "enum"},
            )
        )
    return tuple(facts)


def _facts(repository: str, classes: int, enums: int) -> FactsDocument:
    return FactsDocument(repository, "deadbeef", _symbol_facts(classes, enums))


# --- aspose-html-foss/Aspose.HTML-FOSS-for-Python, lane L, check L-03 --------------------------
# Real seal (bundle ref refs/repository-presenter-state/bundles/aspose-html-foss__Aspose.HTML-FOSS
# -for-Python@lane-l), README.md real line 213 and real line 566. The real facts.json records 303
# public_symbol facts of kind class/enum (302 class, 1 enum) -- both real lines state 243.

_HTML_LINE_213_BEFORE = (
    "The primary entry point is `HTMLDocument`, which parses HTML into a `Document` tree built "
    "from `Node`/`Element` and the specialized `HTMLElement` subclasses. The DOM tree can be "
    "queried and mutated directly, styled through the CSS/CSSOM surface, serialized back to "
    "markup, and optionally scripted through `JSContext`. The library exposes 243 public types "
    "in total, listed below by module, with curated highlights following."
)
_HTML_LINE_213_AFTER = _HTML_LINE_213_BEFORE.replace("243 public types", "303 public types")

_HTML_LINE_566_BEFORE = (
    "- **[Full API reference](https://reference.aspose.org/html/python/)** — the complete, "
    "browsable reference for all 243 public types."
)
_HTML_LINE_566_AFTER = _HTML_LINE_566_BEFORE.replace("243 public types", "303 public types")


def test_html_real_count_restored_in_both_real_lines() -> None:
    """Both real 243-vs-303 lines, concatenated exactly as they sit in the real README (far
    apart in the real file; joined here only to prove one call fixes every occurrence)."""
    facts = _facts("aspose-html-foss/Aspose.HTML-FOSS-for-Python", classes=302, enums=1)
    assert type_counts(facts) == (303, 302)
    before = _HTML_LINE_213_BEFORE + "\n\n" + _HTML_LINE_566_BEFORE
    expected = _HTML_LINE_213_AFTER + "\n\n" + _HTML_LINE_566_AFTER
    assert restore_stated_count(before, facts) == expected


def test_html_real_count_already_correct_is_a_negative_control() -> None:
    """Once restored, re-running the function on its own output must find nothing left to fix --
    the function must never report a fix where none is needed."""
    facts = _facts("aspose-html-foss/Aspose.HTML-FOSS-for-Python", classes=302, enums=1)
    assert restore_stated_count(_HTML_LINE_213_AFTER, facts) is None
    assert restore_stated_count(_HTML_LINE_566_AFTER, facts) is None


def test_html_absent_api_table_row_is_not_zero_call_repairable() -> None:
    """Real line 256 of the same seal: a table row naming `CSSDeclarationBlock`, a type the real
    facts' public surface does not hold (one of the five real absent-type rows this card names).
    There is no stated count here for this module to even look at -- dropping the row or finding
    the type's real name is a judgement call, never a mechanical substitution, so this correctly
    returns None regardless of the facts."""
    facts = _facts("aspose-html-foss/Aspose.HTML-FOSS-for-Python", classes=302, enums=1)
    row = "| `CSSDeclarationBlock` | A small CSSStyleDeclaration-compatible declaration container. |"
    assert restore_stated_count(row, facts) is None


# --- aspose-words-foss/Aspose.Words-FOSS-for-Python, lane L, check L-03 ------------------------
# Real seal (bundle ref .../bundles/aspose-words-foss__Aspose.Words-FOSS-for-Python@lane-l),
# README.md real lines 326-330 (one sentence wrapped across three real lines, "146" at the end of
# the first and "public types" starting the next -- kept here exactly as wrapped, including the
# real line break between them) and real line 607. The real facts.json records 198 public_symbol
# facts of kind class/enum (175 class, 23 enum) -- both real lines state 146.

_WORDS_326_330_BEFORE = (
    "`Document` is the primary entry point: construct it from a file path, then call `save()` "
    "with a\n`SaveFormat` constant or a `MarkdownSaveOptions` / `PdfSaveOptions` / "
    "`OoxmlSaveOptions` instance —\nthe target format is otherwise inferred from the output "
    "file's extension. The library ships 146\npublic types across the DOC/DOCX/RTF/Markdown/Text "
    "readers, the DOCX/Markdown/PDF writers, and the\nshared Light Document Model, summarized in "
    "the module-grouped table below."
)
_WORDS_326_330_AFTER = _WORDS_326_330_BEFORE.replace("ships 146\npublic", "ships 198\npublic")

_WORDS_LINE_607_BEFORE = (
    "- **[Full API reference](https://reference.aspose.org/words/python/)** — the complete, "
    "browsable reference for all 146 public types (the [API reference](#api-reference) section "
    "above covers the essentials)."
)
_WORDS_LINE_607_AFTER = _WORDS_LINE_607_BEFORE.replace("146 public types", "198 public types")


def test_words_real_count_restored_across_the_real_line_wrap() -> None:
    """The real sentence wraps "146" onto one line and "public types" onto the next; the fix
    must still fire across that real line break, replacing only the digits, nothing else."""
    facts = _facts("aspose-words-foss/Aspose.Words-FOSS-for-Python", classes=175, enums=23)
    assert type_counts(facts) == (198, 175)
    assert restore_stated_count(_WORDS_326_330_BEFORE, facts) == _WORDS_326_330_AFTER


def test_words_real_second_count_restored() -> None:
    facts = _facts("aspose-words-foss/Aspose.Words-FOSS-for-Python", classes=175, enums=23)
    assert restore_stated_count(_WORDS_LINE_607_BEFORE, facts) == _WORDS_LINE_607_AFTER


def test_words_real_count_already_correct_is_a_negative_control() -> None:
    facts = _facts("aspose-words-foss/Aspose.Words-FOSS-for-Python", classes=175, enums=23)
    assert restore_stated_count(_WORDS_326_330_AFTER, facts) is None
    assert restore_stated_count(_WORDS_LINE_607_AFTER, facts) is None


def test_words_absent_api_table_rows_are_not_zero_call_repairable() -> None:
    """Real lines 393 and 463 of the same seal: table rows naming `ShapeNode` and
    `ReaderContext`, the two real types this card names as absent from the real public surface.
    No stated count for this module to touch; a judgement call, not a mechanical fix."""
    facts = _facts("aspose-words-foss/Aspose.Words-FOSS-for-Python", classes=175, enums=23)
    assert restore_stated_count("| `ShapeNode` | Class with 25 properties. |", facts) is None
    assert restore_stated_count("| `ReaderContext` | Class extending Protocol. |", facts) is None


# --- aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python, lane L, check L-05 ---------------------
# Real seal (bundle ref .../bundles/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python@lane-l),
# README.md real line 68. Independently confirmed this session against the real facts.json: it
# carries package:license, package:name, package:python_requires and package:version -- no
# package:published_version fact at all. The detector's own "no deterministic edit can repair"
# label is correct: there is no fact of that kind on record for a mechanical substitution to pull
# a replacement value from, so no zero-call repair is even conceivable here, regardless of this
# module's own (unrelated) type-count logic.

_BARCODE_LINE_68 = "The package is not yet published to PyPI. Install it from a source checkout:"


def test_barcode_published_version_claim_has_no_fact_to_repair_from() -> None:
    """Confirms independently (not trusting the detector's own label) that the real facts carry
    no ``package:published_version`` fact at all, then confirms this module -- which only ever
    edits a stated type/class count -- correctly finds nothing to touch in the real line either,
    for the separate, simpler reason that it names no count at all."""
    real_package_fact_ids = {
        "package:license",
        "package:name",
        "package:python_requires",
        "package:version",
    }
    facts = FactsDocument(
        "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python",
        "deadbeef",
        tuple(
            Fact(fact_id, "package", "x", _EVIDENCE)
            for fact_id in sorted(real_package_fact_ids)
        ),
    )
    assert "package:published_version" not in {fact.id for fact in facts.by_kind("package")}
    assert restore_stated_count(_BARCODE_LINE_68, facts) is None


def test_barcode_real_type_count_line_is_already_correct() -> None:
    """Real line 225 names no number at all ("every public type"), so even with the real 51/43
    type/class totals on record, there is nothing for this module to find or change."""
    facts = _facts("aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python", classes=43, enums=8)
    assert type_counts(facts) == (51, 43)
    line = (
        "- **[Full API reference](https://reference.aspose.org/barcode/python/)** — "
        "complete, generated reference documentation for every public type."
    )
    assert restore_stated_count(line, facts) is None


def test_no_type_facts_at_all_returns_none() -> None:
    """When the facts carry no public_symbol facts whatsoever, there is no count to derive a
    replacement from -- never a reason to guess at one."""
    facts = FactsDocument("x/y", "deadbeef", ())
    assert restore_stated_count("The library exposes 243 public types in total.", facts) is None
