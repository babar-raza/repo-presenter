"""TC-013: ``build_record``/``classify`` - the glue later direct supervisor work (not this card -
``ops/**`` is globally denied to every taskcard) wires ``ops/checks/portfolio_delivery_count.py``
and ``ops/checks/calibration_status.py`` to call. Every fixture here is local; the real
``data/acceptance_calibration.json``/``data/acceptance_responsibility.json`` do not exist yet."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from repo_presenter.acceptance.record import build_record, classify

REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust"
LANE = "R"


def _matrix(tmp_path: Path) -> Path:
    path = tmp_path / "responsibility.json"
    path.write_text(
        json.dumps({"mechanism_classes": ["lane_r_pipeline", "reviewer_calibration"]}),
        encoding="utf-8",
    )
    return path


def _calibration(tmp_path: Path, *, passed: bool) -> Path:
    path = tmp_path / "calibration.json"
    status = "PASSED" if passed else "NOT_PASSED"
    path.write_text(
        json.dumps(
            {
                "certificates": [
                    {"mechanism_class": "lane_r_pipeline", "status": status},
                    {"mechanism_class": "reviewer_calibration", "status": status},
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def test_build_record_with_no_files_and_no_signals_classifies_as_generated(
    tmp_path: Path,
) -> None:
    record = build_record(
        REPOSITORY,
        LANE,
        calibration_path=tmp_path / "missing.json",
        responsibility_path=tmp_path / "also-missing.json",
    )
    assert classify(
        REPOSITORY,
        LANE,
        calibration_path=tmp_path / "missing.json",
        responsibility_path=tmp_path / "also-missing.json",
    ) == "generated"
    assert record.certificates.complete is False


def test_classify_reaches_provisionally_accepted_with_complete_certificates(
    tmp_path: Path,
) -> None:
    responsibility = _matrix(tmp_path)
    calibration = _calibration(tmp_path, passed=True)
    state = classify(
        REPOSITORY,
        LANE,
        mechanism_verdicts={"lane_r_pipeline": True, "reviewer_calibration": True},
        canaries={"c1": True},
        calibration_path=calibration,
        responsibility_path=responsibility,
    )
    assert state == "provisionally-accepted"


def test_classify_never_reaches_independently_accepted_without_a_real_attestation_call(
    tmp_path: Path,
) -> None:
    """audit_passed=True alone is not enough: build_record only sets attested=True after a real
    verify_attestation call, and no attestation_path/expected_workflow was given here."""
    responsibility = _matrix(tmp_path)
    calibration = _calibration(tmp_path, passed=True)
    state = classify(
        REPOSITORY,
        LANE,
        mechanism_verdicts={"lane_r_pipeline": True, "reviewer_calibration": True},
        canaries={"c1": True},
        audit_passed=True,
        calibration_path=calibration,
        responsibility_path=responsibility,
    )
    assert state == "provisionally-accepted"
    assert state != "independently-accepted"


def test_classify_reaches_independently_accepted_with_a_verified_attestation(
    tmp_path: Path,
) -> None:
    responsibility = _matrix(tmp_path)
    calibration = _calibration(tmp_path, passed=True)
    artifact = tmp_path / "bundle.tar.gz"
    artifact.write_bytes(b"fixture")

    def fake_runner(args: list[str]) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args, 0)

    state = classify(
        REPOSITORY,
        LANE,
        mechanism_verdicts={"lane_r_pipeline": True, "reviewer_calibration": True},
        canaries={"c1": True},
        audit_passed=True,
        attestation_path=artifact,
        expected_workflow="babar-raza/repo-presenter/.github/workflows/writer.yml",
        calibration_path=calibration,
        responsibility_path=responsibility,
        gh_runner=fake_runner,
    )
    assert state == "independently-accepted"


def test_a_failed_attestation_verification_never_reaches_independently_accepted(
    tmp_path: Path,
) -> None:
    responsibility = _matrix(tmp_path)
    calibration = _calibration(tmp_path, passed=True)
    artifact = tmp_path / "bundle.tar.gz"
    artifact.write_bytes(b"fixture")

    def failing_runner(args: list[str]) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args, 1)

    state = classify(
        REPOSITORY,
        LANE,
        mechanism_verdicts={"lane_r_pipeline": True, "reviewer_calibration": True},
        canaries={"c1": True},
        audit_passed=True,
        attestation_path=artifact,
        expected_workflow="babar-raza/repo-presenter/.github/workflows/writer.yml",
        calibration_path=calibration,
        responsibility_path=responsibility,
        gh_runner=failing_runner,
    )
    assert state != "independently-accepted"
    assert state == "provisionally-accepted"


def test_an_unpassed_calibration_file_never_reaches_provisionally_accepted(
    tmp_path: Path,
) -> None:
    responsibility = _matrix(tmp_path)
    calibration = _calibration(tmp_path, passed=False)
    state = classify(
        REPOSITORY,
        LANE,
        mechanism_verdicts={"lane_r_pipeline": True, "reviewer_calibration": True},
        canaries={"c1": True},
        calibration_path=calibration,
        responsibility_path=responsibility,
    )
    assert state != "provisionally-accepted"
    assert state != "independently-accepted"
