"""reconciliation_narrowing's own parsing/merge helpers, tested directly (the integration-level
behavior -- a real narrowed third ask through run_job -- is tested in tests/test_cascade_s9.py,
where it was found and fixed: aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp, run 41090058316)."""

from __future__ import annotations

import json

from repo_presenter.readme.reconciliation.dispositions import (
    _reconciliation_merge,
    _reconciliation_repeated,
    _rejected_unit_ids,
)

A = "inherited_unit:001.paragraph"
B = "inherited_unit:002.code_block"


def test_a_units_own_prefixed_rejection_line_names_it() -> None:
    assert _rejected_unit_ids([f"{B}: uncited_redundant_defer: DEFER_UNRESOLVED ..."]) == [B]


def test_several_prefixed_lines_name_each_unit_once_in_first_seen_order() -> None:
    rejection = [f"{B}: reason one", f"{A}: reason two", f"{B}: reason three"]
    assert _rejected_unit_ids(rejection) == [B, A]


def test_the_missing_units_line_names_every_unit_it_lists() -> None:
    rejection = [f"no disposition for inherited units: {A}, {B}"]
    assert _rejected_unit_ids(rejection) == [A, B]


def test_the_duplicated_units_line_names_every_unit_it_lists() -> None:
    rejection = [f"more than one disposition for: {A}"]
    assert _rejected_unit_ids(rejection) == [A]


def test_a_line_naming_no_unit_at_all_empties_the_whole_result() -> None:
    """A schema error or an unknown-fact-ID line names no unit a narrowed ask could address --
    the same conservative bail authoring_retry.py's own failing_slots uses: narrow nothing rather
    than guess, and the job fails exactly as it did before this mechanism existed."""
    rejection = [f"{B}: a real reason", "unknown fact ID package:nope"]
    assert _rejected_unit_ids(rejection) == []


def test_no_rejection_at_all_is_nothing_to_narrow() -> None:
    assert _rejected_unit_ids([]) == []


def _entry(unit_id: str, disposition: str = "VERIFIED_PRESERVE", **extra: object) -> dict:
    return {
        "unit_id": unit_id,
        "disposition": disposition,
        "destination_section": extra.get("destination_section"),
        "fact_ids": extra.get("fact_ids", []),
        "rationale": extra.get("rationale", "because"),
    }


def test_merge_replaces_the_named_unit_in_place_and_keeps_order() -> None:
    merged = json.dumps({"dispositions": [_entry(A), _entry(B, "DEFER_UNRESOLVED")]})
    fixed = _entry(B, "VERIFIED_MOVE", destination_section="scope_limitations")
    narrowed = json.dumps({"dispositions": [fixed]})
    result = json.loads(_reconciliation_merge(merged, narrowed, [B]))
    assert [entry["unit_id"] for entry in result["dispositions"]] == [A, B]
    assert result["dispositions"][1]["disposition"] == "VERIFIED_MOVE"


def test_merge_appends_a_unit_the_base_never_had_at_all() -> None:
    merged = json.dumps({"dispositions": [_entry(A)]})
    narrowed = json.dumps({"dispositions": [_entry(B)]})
    result = json.loads(_reconciliation_merge(merged, narrowed, [B]))
    assert {entry["unit_id"] for entry in result["dispositions"]} == {A, B}


def test_merge_refuses_a_narrowed_reply_that_does_not_cover_exactly_what_was_asked() -> None:
    """A narrowed reply naming a different unit than it was asked about is returned unchanged,
    to be refused by the ordinary schema/binding checks rather than quietly repaired."""
    merged = json.dumps({"dispositions": [_entry(A), _entry(B, "DEFER_UNRESOLVED")]})
    narrowed = json.dumps({"dispositions": [_entry(A)]})  # asked for B, answered about A
    result = _reconciliation_merge(merged, narrowed, [B])
    assert result == narrowed


def test_repeated_names_a_unit_whose_two_replies_are_byte_identical() -> None:
    first = json.dumps({"dispositions": [_entry(B, "DEFER_UNRESOLVED")]})
    second = json.dumps({"dispositions": [_entry(B, "DEFER_UNRESOLVED")]})
    assert _reconciliation_repeated(first, second, [B]) == [B]


def test_repeated_is_empty_when_the_second_reply_actually_changed() -> None:
    first = json.dumps({"dispositions": [_entry(B, "DEFER_UNRESOLVED")]})
    second = json.dumps({"dispositions": [_entry(B, "VERIFIED_PRESERVE")]})
    assert _reconciliation_repeated(first, second, [B]) == []
