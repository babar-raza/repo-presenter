"""The reviewer's calibration status is a committed file the code reads and never writes, and every
doubt about it reads as NOT_PASSED (fail closed). A verdict records the status it was made under;
an ACCEPT is labelled ``uncalibrated`` unless that status permits; PR eligibility needs it too."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from repo_presenter.readme.review import calibration_status
from repo_presenter.readme.review.calibration_status import (
    DEFAULT_CALIBRATION_PATH,
    PASSED,
    PASSED_WITH_DECLARED_LIMITS,
    load_calibration,
    parse_calibration,
)
from repo_presenter.readme.review.independent_reviewer import (
    REVIEWER_LOGIC_VERSION,
    ReviewVerdict,
    load_review_verdict,
    write_review_verdict,
)

SRC = Path(__file__).resolve().parents[3] / "src" / "repo_presenter"


def document(status: str = PASSED, **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "status": status,
        "reviewer_logic_version": REVIEWER_LOGIC_VERSION,
        "prompt_version": "17",
        "measured": {"recall": {"contradiction": 0.95}},
        "failed_gates": [],
        "owner_acceptance": "",
    }
    base.update(overrides)
    return base


def accept(status: str | None) -> ReviewVerdict:
    return ReviewVerdict.folded(
        (),
        model_verdict="ACCEPT",
        prompt_version="17",
        model_served="qwen3-next",
        request_sha256="a" * 64,
        reply_sha256="b" * 64,
        calibration_status=status,
    )


# --- the committed file -------------------------------------------------------------------------


def test_the_committed_file_is_not_passed_and_carries_measured_numbers() -> None:
    assert (
        DEFAULT_CALIBRATION_PATH
        == SRC.parents[1] / "data" / "reviewer_calibration.json"
    )
    calibration = load_calibration()
    assert calibration.status == "NOT_PASSED" and not calibration.permits
    assert calibration.owner_acceptance == ""
    assert calibration.measured and calibration.failed_gates
    assert calibration.reviewer_logic_version == REVIEWER_LOGIC_VERSION
    assert calibration.label == "uncalibrated"


def test_the_committed_file_never_claims_an_owner_acceptance_nobody_gave() -> None:
    raw = json.loads(DEFAULT_CALIBRATION_PATH.read_text(encoding="utf-8"))
    assert (
        raw["status"] != PASSED_WITH_DECLARED_LIMITS or raw["owner_acceptance"].strip()
    )


# --- fail closed ---------------------------------------------------------------------------------


def test_a_missing_or_unreadable_file_is_not_passed(tmp_path: Path) -> None:
    missing = load_calibration(tmp_path / "nope.json")
    assert missing.status == "NOT_PASSED" and "cannot read" in missing.problem
    broken = tmp_path / "broken.json"
    broken.write_text("{ not json", encoding="utf-8")
    assert load_calibration(broken).status == "NOT_PASSED"
    assert load_calibration(tmp_path).status == "NOT_PASSED"  # a directory


@pytest.mark.parametrize(
    "raw",
    [
        [],
        "PASSED",
        {"status": "PASS"},
        {"status": None},
        {},
        document(measured=None),
        document(failed_gates="recall"),
        document(owner_acceptance=7),
    ],
)
def test_a_malformed_or_unknown_document_is_not_passed(raw: object) -> None:
    assert parse_calibration(raw).status == "NOT_PASSED"


def test_passed_is_trusted_only_when_the_file_lists_no_failed_gate() -> None:
    assert parse_calibration(document(PASSED)).status == PASSED
    contradicted = parse_calibration(
        document(PASSED, failed_gates=["recall[contradiction]"])
    )
    assert contradicted.status == "NOT_PASSED"
    assert "failed gates" in contradicted.problem


@pytest.mark.parametrize("acceptance", ["", "   ", "\n"])
def test_declared_limits_without_an_owner_acceptance_is_not_passed(
    acceptance: str,
) -> None:
    raw = document(
        PASSED_WITH_DECLARED_LIMITS, failed_gates=["recall[unsupported_claim]"]
    )
    raw["owner_acceptance"] = acceptance
    got = parse_calibration(raw)
    assert got.status == "NOT_PASSED" and "owner_acceptance" in got.problem
    del raw["owner_acceptance"]
    assert parse_calibration(raw).status == "NOT_PASSED"


def test_declared_limits_with_an_owner_acceptance_permits() -> None:
    raw = document(
        PASSED_WITH_DECLARED_LIMITS,
        failed_gates=["recall[unsupported_claim]"],
        owner_acceptance="Babar Raza, 2026-11-02: accepts the measured LLM-only recalls",
    )
    got = parse_calibration(raw)
    assert got.status == PASSED_WITH_DECLARED_LIMITS and got.permits
    assert got.label == "calibrated"


def test_a_file_measured_for_another_reviewer_version_is_not_passed() -> None:
    got = parse_calibration(document(PASSED, reviewer_logic_version="5"))
    assert got.status == "NOT_PASSED" and "measured again" in got.problem


# --- the verdict records it, and the label follows -----------------------------------------------


def test_an_accept_is_uncalibrated_unless_its_recorded_status_permits() -> None:
    assert accept(None).acceptance_label == "uncalibrated"
    assert accept("NOT_PASSED").acceptance_label == "uncalibrated"
    assert accept(PASSED).acceptance_label == "calibrated"
    assert accept(PASSED_WITH_DECLARED_LIMITS).acceptance_label == "calibrated"
    assert not accept("NOT_PASSED").pr_eligible and not accept(None).pr_eligible
    assert accept(PASSED).pr_eligible
    assert accept(PASSED_WITH_DECLARED_LIMITS).pr_eligible


def test_a_deterministic_only_accept_is_never_pr_eligible() -> None:
    unreviewed = ReviewVerdict(verdict="ACCEPT", findings=(), calibration_status=PASSED)
    assert not unreviewed.pr_eligible


def test_an_unknown_status_cannot_be_recorded() -> None:
    with pytest.raises(ValueError, match="calibration status"):
        accept("TRUSTED")


def test_the_verdict_file_records_status_and_label_and_reads_them_back(
    tmp_path: Path,
) -> None:
    for status, label in (
        ("NOT_PASSED", "uncalibrated"),
        (PASSED, "calibrated"),
        (None, "uncalibrated"),
    ):
        path = tmp_path / f"{status}.json"
        write_review_verdict(accept(status), path)
        written = json.loads(path.read_text(encoding="utf-8"))
        assert written["calibration_status"] == status
        assert written["acceptance_label"] == label
        assert load_review_verdict(path).calibration_status == status


def test_a_label_in_the_file_is_never_trusted_over_the_recorded_status(
    tmp_path: Path,
) -> None:
    path = tmp_path / "v.json"
    write_review_verdict(accept("NOT_PASSED"), path)
    forged = json.loads(path.read_text(encoding="utf-8"))
    forged["acceptance_label"] = "calibrated"
    path.write_text(json.dumps(forged), encoding="utf-8")
    assert load_review_verdict(path).acceptance_label == "uncalibrated"


# --- code never writes the acceptance ------------------------------------------------------------


def test_no_source_file_writes_the_calibration_file_or_an_owner_acceptance() -> None:
    writers = re.compile(
        r"write_text|write_bytes|\.write\(|json\.dump\(|open\([^)]*['\"][wax]\+?b?['\"]"
    )
    offenders = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "reviewer_calibration" not in text and "owner_acceptance" not in text:
            continue
        if writers.search(text):
            offenders.append(path.relative_to(SRC).as_posix())
    assert offenders == []


def test_the_reader_module_defines_no_writer() -> None:
    names = {name for name in vars(calibration_status) if not name.startswith("_")}
    assert not {n for n in names if "write" in n.lower() or "save" in n.lower()}
