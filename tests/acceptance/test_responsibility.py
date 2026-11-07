"""Tests for the mechanism-class responsibility matrix (TC-022c).

These tests are the falsifier for ``src/repo_presenter/acceptance/responsibility.py``: they pin
down the exact D1-D16 -> mechanism table transcribed in TC-022c's own card text, assert the
deliberate D7/D9 departures from a literal reading of the design table, and cross-check the
derived ``REQUIRED_MECHANISM_CLASSES`` against the real, imported
``calibration_harness.MECHANISMS`` tuple.
"""

from __future__ import annotations

import json

from repo_presenter.acceptance import calibration_harness
from repo_presenter.acceptance.responsibility import (
    DEFECT_CLASS_OWNERS,
    REQUIRED_MECHANISM_CLASSES,
    build_responsibility_document,
    responsibility_matches_calibration_harness,
)

#: The exact table this card's purpose section transcribes, after its own documented D9
#: correction (real primary "M8", not the design table's literal "M9" -- see the module
#: docstring). D7 is deliberately absent from this expectation, and asserted absent below.
EXPECTED_TABLE: dict[str, tuple[str, str | None]] = {
    "D1": ("M1", None),
    "D2": ("M4", "M2"),
    "D3": ("M4", None),
    "D4": ("M3", "M2"),
    "D5": ("M2", None),
    "D6": ("M2", None),
    "D8": ("M5", "M2"),
    "D9": ("M8", None),
    "D10": ("M5", "M7"),
    "D11": ("M6", None),
    "D12": ("M6", None),
    "D13": ("M7", "M5"),
    "D14": ("M8", None),
    "D15": ("M8", "M9"),
    "D16": ("M10", None),
}


def test_every_expected_defect_class_present_with_exact_entry() -> None:
    for defect_class, expected in EXPECTED_TABLE.items():
        assert defect_class in DEFECT_CLASS_OWNERS, f"{defect_class} missing from DEFECT_CLASS_OWNERS"
        assert DEFECT_CLASS_OWNERS[defect_class] == expected, (
            f"{defect_class}: expected {expected}, got {DEFECT_CLASS_OWNERS[defect_class]}"
        )


def test_no_unexpected_defect_classes() -> None:
    assert set(DEFECT_CLASS_OWNERS) == set(EXPECTED_TABLE)


def test_d7_is_not_present() -> None:
    # D7 ("true claim the facts miss") is owned by the facts extractor, not any acceptance
    # mechanism -- it must never become a mechanism_classes entry.
    assert "D7" not in DEFECT_CLASS_OWNERS


def test_required_mechanism_classes_contains_m1_through_m8_and_m10() -> None:
    required = set(REQUIRED_MECHANISM_CLASSES)
    for mechanism in ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M10"):
        assert mechanism in required, f"{mechanism} missing from REQUIRED_MECHANISM_CLASSES"


def test_required_mechanism_classes_does_not_contain_m9() -> None:
    assert "M9" not in REQUIRED_MECHANISM_CLASSES


def test_required_mechanism_classes_is_sorted_and_deduplicated() -> None:
    assert list(REQUIRED_MECHANISM_CLASSES) == sorted(set(REQUIRED_MECHANISM_CLASSES))


def test_build_responsibility_document_shape() -> None:
    document = build_responsibility_document()
    assert document["schema"] == "acceptance-responsibility/1"
    assert document["mechanism_classes"] == sorted(REQUIRED_MECHANISM_CLASSES)


def test_build_responsibility_document_round_trips_through_json() -> None:
    document = build_responsibility_document()
    round_tripped = json.loads(json.dumps(document))
    assert round_tripped == document


def test_build_responsibility_document_deterministic_across_calls() -> None:
    first = build_responsibility_document()
    second = build_responsibility_document()
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_required_mechanism_classes_minus_m8_is_subset_of_calibration_harness_mechanisms() -> None:
    required_minus_m8 = set(REQUIRED_MECHANISM_CLASSES) - {"M8"}
    assert required_minus_m8.issubset(set(calibration_harness.MECHANISMS))


def test_responsibility_matches_calibration_harness_helper_agrees() -> None:
    assert responsibility_matches_calibration_harness() is True
