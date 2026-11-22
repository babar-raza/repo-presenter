"""BL-671: a live fenced block nested in an indented list item is accounted by its unit's disposition.

Real data: aspose-pdf-foss/Aspose-PDF-FOSS-for-Python at 5e122e05, unit ``inherited_unit:280.list`` (the API
Reference's 'Text Extraction And Editing' list; its ``extract_blocks`` item carries a ``with Document(...)``
fenced example indented two spaces under the bullet) and the disposition the hosted run gave it (VERIFIED_REWRITE,
no fact ids, the reconciler's 'Restated: it embeds an unverified code example BC-03 forbids' rationale). Hosted
Lane R run 44959526325 ended REJECT on exactly one finding, 'live_readme_loss ... code block with Document(
"report.pdf") as document:', with 'degrade: nothing kept (0 flag(s) tried)': the Markdown parser reads the
nested block without the item's indentation while the unit's text keeps it on every line, so the plain
substring test never found the block in the unit that accounts for it."""

from __future__ import annotations

from pathlib import Path

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.review.independent_reviewer import live_readme_loss_rule

UNIT_ID = "inherited_unit:280.list"
LIST_TEXT = (Path(__file__).parent / "fixtures" / "pdf_python_280_list.md").read_text(encoding="utf-8")
RESTATED = "Restated: it embeds an unverified code example BC-03 forbids. Kept in the collapsed API Reference."
LIVE = f"# Aspose.PDF FOSS for Python\n\n## API Reference\n\n{LIST_TEXT}\n"
#: The candidate prints the API rows from the facts and the item's words, never the example.
CANDIDATE = (
    "# Aspose.PDF FOSS for Python\n\n## API Reference\n\n"
    "- `Document.extract_blocks(pages=None)` returns `list[ExtractedBlock]` with structure data.\n"
)
FENCE = 'with Document("report.pdf") as document:'


def _document(text: str = LIST_TEXT) -> FactsDocument:
    unit = Fact(
        id=UNIT_ID, kind="inherited_unit", value=text,  # type: ignore[arg-type]
        evidence=(Evidence("README.md", None),), polarity="SUPPORTED",
        attributes={"section": "Aspose.PDF FOSS for Python > API Reference > Text Extraction And Editing"},
    )
    return FactsDocument("aspose-pdf-foss/Aspose-PDF-FOSS-for-Python", "0" * 40, (unit,))


def _lost(row: dict[str, object], live: str = LIVE, candidate: str = CANDIDATE, text: str = LIST_TEXT) -> list[str]:
    findings = live_readme_loss_rule(
        live, candidate, facts=_document(text), dispositions={"dispositions": [{"unit_id": UNIT_ID, **row}]}
    )
    return [finding.evidence for finding in findings]


def test_the_fixture_is_the_real_nested_block() -> None:
    assert "\n  ```python\n  with Document(\"report.pdf\") as document:\n      for block in document.extract_blocks" in LIST_TEXT


def test_the_restated_unit_accounts_for_the_nested_block() -> None:
    assert _lost({"disposition": "VERIFIED_REWRITE", "destination_section": "api_reference", "fact_ids": [], "rationale": RESTATED}) == []


def test_a_superseded_unit_citing_a_fact_accounts_for_the_nested_block() -> None:
    row = {
        "disposition": "SUPERSEDE_REDUNDANT", "destination_section": "api_reference",
        "fact_ids": ["public_symbol:aspose_pdf.document"], "rationale": "The API Reference renders every member.",
    }
    assert _lost(row) == []


def test_negative_control_a_kept_unit_that_prints_none_of_it_still_loses_the_block() -> None:
    row = {"disposition": "VERIFIED_PRESERVE", "destination_section": "api_reference", "fact_ids": [], "rationale": "kept"}
    assert [label for label in _lost(row) if FENCE in label]


def test_negative_control_a_rewrite_without_the_example_rationale_and_without_facts_still_loses_it() -> None:
    row = {"disposition": "VERIFIED_REWRITE", "destination_section": "api_reference", "fact_ids": [], "rationale": "Restated for brevity."}
    assert [label for label in _lost(row) if FENCE in label]


def test_negative_control_a_block_the_accounting_unit_does_not_hold_is_still_lost() -> None:
    # The live README has a block the accounted unit does not contain: that block is real content nobody accounts for.
    other = "```python\nwith Document('other.pdf') as d:\n    d.save('x.pdf')\n```\n"
    row = {"disposition": "VERIFIED_REWRITE", "destination_section": "api_reference", "fact_ids": [], "rationale": RESTATED}
    lost = _lost(row, live=LIVE + "\n" + other)
    assert [label for label in lost if "other.pdf" in label or "with Document('other.pdf')" in label]
    assert not [label for label in lost if FENCE in label]


def test_a_block_changed_inside_the_unit_is_not_accounted() -> None:
    # A live block that differs in one word from the one the unit holds is a different block.
    changed = LIVE.replace('document.export_blocks_json("report-structure.json")', 'document.export_blocks_json("other.json")')
    row = {"disposition": "VERIFIED_REWRITE", "destination_section": "api_reference", "fact_ids": [], "rationale": RESTATED}
    assert [label for label in _lost(row, live=changed) if FENCE in label]


def test_the_block_printed_by_the_candidate_is_not_lost_either_way() -> None:
    printed = CANDIDATE + "\n```python\n" + 'with Document("report.pdf") as document:\n    for block in document.extract_blocks(pages=[1]):\n        print(block.page_index, block.kind, block.text, block.rows)\n    document.export_blocks_json("report-structure.json")\n```\n'
    row = {"disposition": "VERIFIED_PRESERVE", "destination_section": "api_reference", "fact_ids": [], "rationale": "kept"}
    assert not [label for label in _lost(row, candidate=printed) if FENCE in label]
