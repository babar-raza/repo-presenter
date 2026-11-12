"""The last S4 ask: a narrowed reply that answers only some of the asked units, and the units still
refused after it (PDF-FOSS-for-Python, batch 1, 2026-11-09).

Real data: unit 132.paragraph's text and its first-ask reply are copied verbatim from the failed
run's call store. The run asked about 128 and 132, the model answered 128 only, and the merge
returned that single entry alone - so the job failed "no disposition for inherited units" naming
the batch's nineteen other, already-accepted units.
"""

from __future__ import annotations

import json

from repo_presenter.core.facts import Evidence, Fact, FactsDocument
from repo_presenter.readme.reconciliation.dispositions import (
    _reconciliation_merge,
    _settle_unresolved,
    reconcile_checks,
)

REPO = "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python"
SECTION = "Aspose.PDF FOSS for Python > Additional Examples > Inventory PDF Links"
U128 = "inherited_unit:128.paragraph"
U132 = "inherited_unit:132.paragraph"
U122 = "inherited_unit:122.code_block"
TEXT_132 = (
    "Read or set `Document.base_uri` to give relative links a common address, for\n"
    'example `document.base_uri = "https://example.com/manuals/"`; assign `None` to\n'
    "clear it. New values are absolute ASCII URIs, with international characters\n"
    "percent-encoded. The setting is saved in the PDF and used by link reports."
)
CODE_122 = (
    '```python\nfrom aspose_pdf import Document\n\nwith Document("manual.pdf") as document:\n'
    '    document.export_bookmarks_json("bookmarks.json")\n```'
)


def _entry(unit: str, disposition: str, destination=None, fact_ids=(), why="because") -> dict:
    return {
        "unit_id": unit, "disposition": disposition, "destination_section": destination,
        "fact_ids": list(fact_ids), "rationale": why,
    }


def _unit(unit: str, text: str) -> Fact:
    return Fact(unit, "inherited_unit", text, (Evidence("README.md", None),), attributes={"section": SECTION})


def _facts(*extra: Fact) -> FactsDocument:
    base = (
        Fact("identity:repository", "identity", REPO, (Evidence("x"),)),
        Fact("identity:ecosystem", "identity", "python", (Evidence("x"),)),
        Fact("build_test_asset:tests", "build_test_asset", "tests/", (Evidence("x"),)),
        _unit(U128, "Levels and page numbers start at one."),
        _unit(U132, TEXT_132),
        *extra,
    )
    return FactsDocument(REPO, "f" * 40, base)


OMIT_132 = _entry(
    U132, "OMIT_UNSUPPORTED", None, [],
    "No fact supports base_uri management; the example and public symbols do not confirm this "
    "capability.",
)


def test_a_partial_narrowed_reply_replaces_what_it_answers_and_keeps_the_rest_of_the_batch() -> None:
    base = json.dumps({"dispositions": [_entry("inherited_unit:001.paragraph", "VERIFIED_PRESERVE", "opening"),
                                        _entry(U128, "OMIT_UNSUPPORTED"), OMIT_132]})
    narrowed = json.dumps({"dispositions": [_entry(U128, "VERIFIED_PRESERVE", "scope_limitations")]})
    result = json.loads(_reconciliation_merge(base, narrowed, [U128, U132]))
    assert [e["unit_id"] for e in result["dispositions"]] == ["inherited_unit:001.paragraph", U128, U132]
    assert result["dispositions"][1]["disposition"] == "VERIFIED_PRESERVE"
    assert result["dispositions"][2] == OMIT_132  # unanswered: exactly what the base had


def test_a_unit_still_refused_after_the_last_ask_is_kept_as_written_not_failed() -> None:
    facts = _facts()
    merged = json.dumps({"dispositions": [_entry(U128, "VERIFIED_PRESERVE", "scope_limitations"), OMIT_132]})
    assert any("uncited_prose_omit" in e for e in reconcile_checks(json.loads(merged), facts))
    settled = json.loads(_settle_unresolved(merged, [U128, U132], facts))
    by = {e["unit_id"]: e for e in settled["dispositions"]}
    assert by[U132]["disposition"] == "PRESERVE_ATTRIBUTED"  # prose, nothing cited: never "verified"
    assert by[U132]["destination_section"] is not None
    assert by[U128]["disposition"] == "VERIFIED_PRESERVE"  # untouched
    assert reconcile_checks(json.loads(json.dumps(settled)), facts) == []


def test_an_uncited_omitted_code_block_is_kept_verified_never_attributed() -> None:
    facts = _facts(_unit(U122, CODE_122))
    merged = json.dumps({"dispositions": [_entry(U122, "OMIT_UNSUPPORTED")]})
    settled = json.loads(_settle_unresolved(merged, [U122], facts))
    assert settled["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_an_omission_citing_a_contradicted_fact_is_a_legitimate_omission_and_is_left_alone() -> None:
    bad = Fact("example:001", "example", "x", (Evidence("README.md", f"unit {U132}"),), polarity="CONTRADICTED")
    facts = _facts(bad)
    omit = _entry(U132, "OMIT_UNSUPPORTED", None, ["example:001"], "its example is contradicted")
    merged = json.dumps({"dispositions": [omit]})
    assert json.loads(_settle_unresolved(merged, [U132], facts))["dispositions"][0] == omit


def test_a_unit_not_asked_about_is_never_touched() -> None:
    facts = _facts()
    merged = json.dumps({"dispositions": [OMIT_132]})
    assert json.loads(_settle_unresolved(merged, [U128], facts))["dispositions"][0] == OMIT_132


def test_when_nothing_is_refused_the_reply_is_returned_unchanged() -> None:
    facts = _facts()
    merged = json.dumps({"dispositions": [_entry(U132, "VERIFIED_PRESERVE", "scope_limitations")]})
    assert _settle_unresolved(merged, [U132], facts) == merged
