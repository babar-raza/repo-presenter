"""TC-013: ``load_certificates`` fail-closed, against fixture ``data/acceptance_calibration.json``
/``data/acceptance_responsibility.json`` files - never the real paths, which do not exist on disk
yet (TC-022a/TC-022b create and populate them later). REQ-ACCEPT-001/002."""

from __future__ import annotations

import json
from pathlib import Path

from repo_presenter.acceptance.record import load_certificates


def _write(path: Path, document: object) -> Path:
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_both_files_missing_is_unconditionally_incomplete(tmp_path: Path) -> None:
    certificates = load_certificates(
        calibration_path=tmp_path / "missing-calibration.json",
        responsibility_path=tmp_path / "missing-responsibility.json",
    )
    assert certificates.required_mechanisms is None
    assert certificates.complete is False
    assert certificates.problem


def test_responsibility_matrix_missing_is_incomplete_even_with_a_real_calibration_file(
    tmp_path: Path,
) -> None:
    calibration = _write(
        tmp_path / "calibration.json",
        {
            "schema_version": 1,
            "certificates": [{"mechanism_class": "lane_r_pipeline", "status": "PASSED"}],
        },
    )
    certificates = load_certificates(
        calibration_path=calibration,
        responsibility_path=tmp_path / "missing-responsibility.json",
    )
    # A missing matrix is never read as "zero requirements" (vacuously satisfied) - it is
    # unconditionally incomplete, never True on absence.
    assert certificates.required_mechanisms is None
    assert certificates.complete is False


def test_a_malformed_responsibility_matrix_is_incomplete(tmp_path: Path) -> None:
    responsibility = _write(tmp_path / "responsibility.json", {"mechanism_classes": "not-a-list"})
    certificates = load_certificates(
        calibration_path=tmp_path / "missing-calibration.json",
        responsibility_path=responsibility,
    )
    assert certificates.required_mechanisms is None
    assert certificates.complete is False


def test_a_responsibility_matrix_that_is_not_json_is_incomplete(tmp_path: Path) -> None:
    responsibility = tmp_path / "responsibility.json"
    responsibility.write_text("{ not json", encoding="utf-8")
    certificates = load_certificates(
        calibration_path=tmp_path / "missing-calibration.json",
        responsibility_path=responsibility,
    )
    assert certificates.required_mechanisms is None
    assert certificates.complete is False


def test_calibration_file_missing_with_a_real_matrix_is_zero_certificates_not_trust_everything(
    tmp_path: Path,
) -> None:
    responsibility = _write(
        tmp_path / "responsibility.json",
        {"mechanism_classes": ["lane_r_pipeline", "reviewer_calibration"]},
    )
    certificates = load_certificates(
        calibration_path=tmp_path / "missing-calibration.json",
        responsibility_path=responsibility,
    )
    assert certificates.required_mechanisms == frozenset(
        {"lane_r_pipeline", "reviewer_calibration"}
    )
    assert certificates.certified_mechanisms == frozenset()
    assert certificates.complete is False


def test_a_malformed_calibration_file_is_read_as_zero_certificates(tmp_path: Path) -> None:
    responsibility = _write(
        tmp_path / "responsibility.json", {"mechanism_classes": ["lane_r_pipeline"]}
    )
    calibration = _write(tmp_path / "calibration.json", {"certificates": "not-a-list"})
    certificates = load_certificates(
        calibration_path=calibration, responsibility_path=responsibility
    )
    assert certificates.certified_mechanisms == frozenset()
    assert certificates.complete is False


def test_a_complete_matching_pair_is_complete(tmp_path: Path) -> None:
    responsibility = _write(
        tmp_path / "responsibility.json",
        {"mechanism_classes": ["lane_r_pipeline", "reviewer_calibration"]},
    )
    calibration = _write(
        tmp_path / "calibration.json",
        {
            "certificates": [
                {"mechanism_class": "lane_r_pipeline", "status": "PASSED"},
                {"mechanism_class": "reviewer_calibration", "status": "PASSED"},
                {"mechanism_class": "canary_harness", "status": "NOT_PASSED"},
            ]
        },
    )
    certificates = load_certificates(
        calibration_path=calibration, responsibility_path=responsibility
    )
    assert certificates.required_mechanisms == frozenset(
        {"lane_r_pipeline", "reviewer_calibration"}
    )
    assert certificates.certified_mechanisms == frozenset(
        {"lane_r_pipeline", "reviewer_calibration"}
    )
    assert certificates.complete is True


def test_a_not_passed_certificate_for_a_required_class_is_incomplete(tmp_path: Path) -> None:
    responsibility = _write(
        tmp_path / "responsibility.json",
        {"mechanism_classes": ["lane_r_pipeline", "reviewer_calibration"]},
    )
    calibration = _write(
        tmp_path / "calibration.json",
        {
            "certificates": [
                {"mechanism_class": "lane_r_pipeline", "status": "PASSED"},
                {"mechanism_class": "reviewer_calibration", "status": "NOT_PASSED"},
            ]
        },
    )
    certificates = load_certificates(
        calibration_path=calibration, responsibility_path=responsibility
    )
    assert certificates.complete is False
