"""TC-014: pure, offline tests for `repo_presenter.acceptance.audit.seed`. No provider call, no
network, no filesystem write - every case operates on in-memory README fixtures."""

from __future__ import annotations

import pytest

from repo_presenter.acceptance.audit.seed import (
    CLEAN_SHAPE,
    DEFECT_SHAPES,
    OPERATORS_BY_SHAPE,
    SHAPE_BY_OPERATOR,
    SeedingError,
    SeedResult,
    SeedSpan,
    clean_control,
    decrypt_seed_manifest,
    encrypt_seed_manifest,
    op_add_promotional_filler,
    op_count_mismatch,
    op_incoherent_reorder,
    op_inject_unsupported_claim,
    op_invent_api_name,
    op_misdescribe_type,
    seed_defect,
    seed_shape,
)

COUNT_README = (
    "# aspose-note-foss\n"
    "\n"
    "A pure-Python library for Aspose.Note files. The package exposes bindings for all 39 "
    "public types.\n"
)

API_TABLE_README = (
    "# aspose-cells-foss\n"
    "\n"
    "## API\n"
    "\n"
    "| Type | Description |\n"
    "|---|---|\n"
    "| `Workbook` | The root object representing a spreadsheet document. |\n"
    "| `Cell` | A single addressable cell inside a worksheet. |\n"
)

MISDESCRIBE_README = (
    "# API\n"
    "\n"
    "| Type | Description |\n"
    "|---|---|\n"
    "| `CellFormatValue` | Represents the numeric format id referenced by a cell style. |\n"
    "| `Row` | Represents one worksheet row and its height. |\n"
)

REORDER_README = (
    "# Guide\n"
    "\n"
    "Step one: install the package.\n"
    "\n"
    "Step two: open a document.\n"
    "\n"
    "Step three: read its pages.\n"
)

PLAIN_PARAGRAPH_README = (
    "# aspose-widgets\n"
    "\n"
    "This library reads and writes widget files without any native dependency.\n"
    "\n"
    "## Installation\n"
    "\n"
    "Install from PyPI.\n"
)

NO_NUMBERS_NO_TABLE_README = "# aspose-widgets\n\nA small library.\n"


# ---------------------------------------------------------------------------
# clean control
# ---------------------------------------------------------------------------


def test_clean_control_returns_the_text_completely_unmodified() -> None:
    result = clean_control("cand-1", COUNT_README)
    assert isinstance(result, SeedResult)
    assert result.seeded_readme == COUNT_README
    assert result.record.shape == CLEAN_SHAPE
    assert result.record.span is None
    assert result.record.line is None
    assert result.record.operator == "clean_control"


# ---------------------------------------------------------------------------
# class A: count_mismatch
# ---------------------------------------------------------------------------


def test_count_mismatch_changes_the_stated_count_to_a_wrong_number() -> None:
    mutation = op_count_mismatch(COUNT_README)
    assert mutation.seeded_text != COUNT_README
    assert "39 public types" not in mutation.seeded_text
    assert "public types" in mutation.seeded_text
    assert mutation.original_text == "39 public types"
    changed = mutation.seeded_text[mutation.span.start : mutation.span.end]
    assert changed != mutation.original_text
    assert changed.endswith("public types")


def test_count_mismatch_never_picks_the_true_count_from_evidence() -> None:
    mutation = op_count_mismatch(COUNT_README, {"public_type_count": 46})
    changed = mutation.seeded_text[mutation.span.start : mutation.span.end]
    assert "46 public types" not in changed
    assert "39 public types" not in changed


def test_count_mismatch_raises_without_a_public_type_count_claim() -> None:
    with pytest.raises(SeedingError):
        op_count_mismatch(NO_NUMBERS_NO_TABLE_README)


# ---------------------------------------------------------------------------
# class A: invent_api_name
# ---------------------------------------------------------------------------


def test_invent_api_name_renames_a_real_table_entry_to_an_unknown_name() -> None:
    mutation = op_invent_api_name(API_TABLE_README)
    assert mutation.original_text == "Workbook"
    changed = mutation.seeded_text[mutation.span.start : mutation.span.end]
    assert changed.startswith(mutation.original_text)
    assert changed.endswith("Ghost")
    # The real name is gone from its own table row, replaced by the invented one.
    assert "`Workbook`" not in mutation.seeded_text
    assert "`WorkbookGhost`" in mutation.seeded_text
    # The untouched second row's real name is still present.
    assert "`Cell`" in mutation.seeded_text


def test_invent_api_name_prefers_a_name_known_to_evidence() -> None:
    mutation = op_invent_api_name(API_TABLE_README, {"exported_types": ["Cell"]})
    assert mutation.original_text == "Cell"
    assert "CellGhost" in mutation.seeded_text


def test_invent_api_name_avoids_colliding_with_an_existing_known_name() -> None:
    # Force the "Ghost" candidate itself to already be a known name, so the operator must fall
    # back to "...Ghost2".
    mutation = op_invent_api_name(
        API_TABLE_README, {"exported_types": ["Cell", "CellGhost"]}
    )
    assert mutation.original_text == "Cell"
    changed = mutation.seeded_text[mutation.span.start : mutation.span.end]
    assert changed == "CellGhost2"


def test_invent_api_name_raises_without_any_api_table_entry() -> None:
    with pytest.raises(SeedingError):
        op_invent_api_name(NO_NUMBERS_NO_TABLE_README)


# ---------------------------------------------------------------------------
# class D: inject_unsupported_claim
# ---------------------------------------------------------------------------


def test_inject_unsupported_claim_inserts_an_invented_verification_sentence() -> None:
    mutation = op_inject_unsupported_claim(PLAIN_PARAGRAPH_README)
    assert mutation.seeded_text != PLAIN_PARAGRAPH_README
    assert mutation.original_text == ""
    inserted = mutation.seeded_text[mutation.span.start : mutation.span.end]
    assert "verified" in inserted.lower() or "exercised" in inserted.lower()
    # Removing exactly the inserted span must recover the original text byte for byte.
    recovered = (
        mutation.seeded_text[: mutation.span.start] + mutation.seeded_text[mutation.span.end :]
    )
    assert recovered == PLAIN_PARAGRAPH_README


def test_inject_unsupported_claim_index_selects_different_sentences() -> None:
    first = op_inject_unsupported_claim(PLAIN_PARAGRAPH_README, index=0)
    second = op_inject_unsupported_claim(PLAIN_PARAGRAPH_README, index=1)
    first_text = first.seeded_text[first.span.start : first.span.end]
    second_text = second.seeded_text[second.span.start : second.span.end]
    assert first_text != second_text


def test_inject_unsupported_claim_never_raises_on_text_without_a_paragraph_break() -> None:
    # No blank-line paragraph break at all: the operator still finds somewhere to insert (the
    # end of the text) rather than failing.
    mutation = op_inject_unsupported_claim("a single line with no blank line at all")
    assert mutation.seeded_text.startswith("a single line with no blank line at all")


# ---------------------------------------------------------------------------
# class D9: misdescribe_type
# ---------------------------------------------------------------------------


def test_misdescribe_type_swaps_in_a_different_real_types_description() -> None:
    mutation = op_misdescribe_type(MISDESCRIBE_README)
    assert mutation.original_text.strip() == (
        "Represents the numeric format id referenced by a cell style."
    )
    changed = mutation.seeded_text[mutation.span.start : mutation.span.end]
    assert changed.strip() == "Represents one worksheet row and its height."
    # The donor row (`Row`) must be left untouched.
    assert "Represents one worksheet row and its height." in mutation.seeded_text
    assert mutation.seeded_text.count("Represents one worksheet row and its height.") == 2


def test_misdescribe_type_raises_with_fewer_than_two_distinct_descriptions() -> None:
    only_one_row = (
        "# API\n\n| Type | Description |\n|---|---|\n"
        "| `Row` | Represents one worksheet row. |\n"
    )
    with pytest.raises(SeedingError):
        op_misdescribe_type(only_one_row)

    identical_descriptions = (
        "# API\n\n| Type | Description |\n|---|---|\n"
        "| `Row` | Does the same thing. |\n"
        "| `Cell` | Does the same thing. |\n"
    )
    with pytest.raises(SeedingError):
        op_misdescribe_type(identical_descriptions)


# ---------------------------------------------------------------------------
# class D14: add_promotional_filler
# ---------------------------------------------------------------------------


def test_add_promotional_filler_inserts_superlative_language() -> None:
    mutation = op_add_promotional_filler(PLAIN_PARAGRAPH_README)
    inserted = mutation.seeded_text[mutation.span.start : mutation.span.end]
    assert any(
        word in inserted.lower()
        for word in ("powerful", "cutting-edge", "best-in-class", "world-class")
    )
    recovered = (
        mutation.seeded_text[: mutation.span.start] + mutation.seeded_text[mutation.span.end :]
    )
    assert recovered == PLAIN_PARAGRAPH_README


# ---------------------------------------------------------------------------
# class D15: incoherent_reorder
# ---------------------------------------------------------------------------


def test_incoherent_reorder_swaps_two_adjacent_steps() -> None:
    mutation = op_incoherent_reorder(REORDER_README)
    assert mutation.seeded_text != REORDER_README
    assert mutation.seeded_text.index("Step two") < mutation.seeded_text.index("Step one")
    assert mutation.seeded_text.index("Step one") < mutation.seeded_text.index("Step three")
    swapped = mutation.seeded_text[mutation.span.start : mutation.span.end]
    assert swapped.startswith("Step two")
    assert mutation.original_text.startswith("Step one")


def test_incoherent_reorder_never_touches_an_h1_title() -> None:
    mutation = op_incoherent_reorder(REORDER_README)
    assert mutation.seeded_text.startswith("# Guide")


def test_incoherent_reorder_raises_with_fewer_than_two_distinct_paragraphs() -> None:
    with pytest.raises(SeedingError):
        op_incoherent_reorder("# Guide\n\nOnly one paragraph here.\n")

    identical_paragraphs = "# Guide\n\nSame text.\n\nSame text.\n"
    with pytest.raises(SeedingError):
        op_incoherent_reorder(identical_paragraphs)


# ---------------------------------------------------------------------------
# dispatch: seed_defect / seed_shape
# ---------------------------------------------------------------------------


def test_every_defect_shape_has_at_least_one_operator() -> None:
    for shape in DEFECT_SHAPES:
        assert shape in OPERATORS_BY_SHAPE
        assert len(OPERATORS_BY_SHAPE[shape]) >= 1


def test_shape_by_operator_is_the_exact_inverse_of_operators_by_shape() -> None:
    for shape, operators in OPERATORS_BY_SHAPE.items():
        for operator in operators:
            assert SHAPE_BY_OPERATOR[operator] == shape


def test_seed_defect_returns_a_full_seed_result_with_a_correct_line_number() -> None:
    result = seed_defect("cand-7", COUNT_README, "count_mismatch")
    assert result.candidate_id == "cand-7"
    assert result.record.shape == "A"
    assert result.record.operator == "count_mismatch"
    assert isinstance(result.record.span, SeedSpan)
    # Line 3 (1-indexed) of COUNT_README is where the count claim lives.
    expected_line = result.seeded_readme.count("\n", 0, result.record.span.start) + 1
    assert result.record.line == expected_line
    assert result.seeded_readme[result.record.span.start : result.record.span.end] == (
        result.record.seeded_text
    )


def test_seed_defect_rejects_an_unknown_operator() -> None:
    with pytest.raises(SeedingError):
        seed_defect("cand-1", COUNT_README, "not_a_real_operator")


def test_seed_shape_falls_back_to_the_next_operator_when_the_first_cannot_apply() -> None:
    # API_TABLE_README has no "<N> public types" claim, so count_mismatch cannot apply, but it
    # does have an API table, so invent_api_name must be tried next and succeed.
    result = seed_shape("cand-9", API_TABLE_README, "A")
    assert result.record.operator == "invent_api_name"
    assert result.record.shape == "A"


def test_seed_shape_raises_when_every_operator_for_the_shape_fails() -> None:
    with pytest.raises(SeedingError):
        seed_shape("cand-1", NO_NUMBERS_NO_TABLE_README, "A")


def test_seed_shape_rejects_an_unknown_shape() -> None:
    with pytest.raises(SeedingError):
        seed_shape("cand-1", COUNT_README, "Z")


# ---------------------------------------------------------------------------
# manifest encryption stub
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_seed_manifest_round_trips_with_the_fixture_key() -> None:
    key = b"\x00" * 32
    manifest = [
        {"candidate_id": "cand-1", "shape": "A", "operator": "count_mismatch", "line": 3},
        {"candidate_id": "cand-2", "shape": CLEAN_SHAPE, "operator": "clean_control", "line": None},
    ]
    blob = encrypt_seed_manifest(manifest, key)
    assert isinstance(blob, bytes)
    recovered = decrypt_seed_manifest(blob, key)
    assert recovered == manifest


def test_decrypt_seed_manifest_fails_closed_on_the_wrong_key() -> None:
    key = b"\x01" * 32
    wrong_key = b"\x02" * 32
    blob = encrypt_seed_manifest({"candidate_id": "cand-1"}, key)
    with pytest.raises(ValueError):
        decrypt_seed_manifest(blob, wrong_key)


def test_decrypt_seed_manifest_fails_closed_on_tampered_ciphertext() -> None:
    key = b"\x03" * 32
    blob = bytearray(encrypt_seed_manifest({"candidate_id": "cand-1"}, key))
    blob[-1] ^= 0xFF
    with pytest.raises(ValueError):
        decrypt_seed_manifest(bytes(blob), key)


def test_decrypt_seed_manifest_rejects_a_too_short_blob() -> None:
    with pytest.raises(ValueError):
        decrypt_seed_manifest(b"short", b"\x04" * 32)
