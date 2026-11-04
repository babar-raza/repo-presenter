"""scripts/scheduled_execution_gate.py (2026-11-04 P0 follow-up directive section 2): the actual
fail-closed boundary for present.yml's `schedule:` trigger. These are real behavioral tests
against the gate's own predicate functions and its CLI entry point, not a marker check -- a
negative control (TC-010's own established pattern) proves each predicate is actually load-
bearing, not vestigial."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from support import init_git_repository, monitor_registry_entry, write_registry_file

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import scheduled_execution_gate as gate  # noqa: E402

REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET"


# --- pure predicate functions -----------------------------------------------------------------


def test_sweep_pause_is_not_lifted_when_no_ruling_exists_at_all() -> None:
    assert gate.sweep_pause_lifted("") is False
    assert gate.sweep_pause_lifted("nothing relevant here") is False


def test_sweep_pause_is_not_lifted_by_an_upheld_ruling() -> None:
    assert gate.sweep_pause_lifted("OWNER_RULING_SWEEP_PAUSE: UPHELD ref=x") is False


def test_sweep_pause_is_lifted_only_by_the_literal_token() -> None:
    assert gate.sweep_pause_lifted("OWNER_RULING_SWEEP_PAUSE: LIFTED ref=x") is True


def test_sweep_pause_uses_only_the_most_recent_ruling() -> None:
    text = (
        "OWNER_RULING_SWEEP_PAUSE: LIFTED ref=a\n"
        "...\n"
        "OWNER_RULING_SWEEP_PAUSE: UPHELD ref=b\n"
    )
    assert gate.sweep_pause_lifted(text) is False  # re-paused after being lifted

    text2 = (
        "OWNER_RULING_SWEEP_PAUSE: UPHELD ref=a\n"
        "...\n"
        "OWNER_RULING_SWEEP_PAUSE: LIFTED ref=b\n"
    )
    assert gate.sweep_pause_lifted(text2) is True


def test_calibration_passed_requires_an_existing_valid_passed_record(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    assert gate.calibration_passed(missing) is False

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    assert gate.calibration_passed(corrupt) is False

    not_passed = tmp_path / "not_passed.json"
    not_passed.write_text(json.dumps({"status": "NOT_PASSED"}), encoding="utf-8")
    assert gate.calibration_passed(not_passed) is False

    passed = tmp_path / "passed.json"
    passed.write_text(json.dumps({"status": "PASSED"}), encoding="utf-8")
    assert gate.calibration_passed(passed) is True


def test_load_policy_fails_closed_on_missing_or_corrupt_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    assert gate.load_policy(missing) == {
        "scheduled_execution_authorized": False,
        "authorized_repositories": [],
    }

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("[not an object", encoding="utf-8")
    assert gate.load_policy(corrupt)["scheduled_execution_authorized"] is False

    not_an_object = tmp_path / "list.json"
    not_an_object.write_text("[1, 2, 3]", encoding="utf-8")
    assert gate.load_policy(not_an_object)["scheduled_execution_authorized"] is False


def test_evaluate_predicates_names_every_unmet_one() -> None:
    reasons = gate.evaluate_predicates(
        decision_log_text="",
        calibration=Path("/does/not/exist.json"),
        policy={"scheduled_execution_authorized": False},
    )
    assert len(reasons) == 3
    assert any("scheduled_execution_authorized" in r for r in reasons)
    assert any("TC-004" in r for r in reasons)
    assert any("TC-007" in r for r in reasons)


def test_evaluate_predicates_is_empty_only_when_all_three_hold(tmp_path: Path) -> None:
    calibration = tmp_path / "cal.json"
    calibration.write_text(json.dumps({"status": "PASSED"}), encoding="utf-8")
    reasons = gate.evaluate_predicates(
        decision_log_text="OWNER_RULING_SWEEP_PAUSE: LIFTED ref=x",
        calibration=calibration,
        policy={"scheduled_execution_authorized": True},
    )
    assert reasons == []


# --- end-to-end CLI: the actual fail-closed boundary ------------------------------------------


@pytest.fixture
def unauthorized_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real, current repository state: no ruling, no calibration pass, no policy
    authorization. Patches the gate module's own path constants directly rather than touching
    the real project files."""
    monkeypatch.setattr(gate, "DECISION_LOG", Path("/does/not/exist/DECISION_LOG.md"))
    monkeypatch.setattr(gate, "CALIBRATION", Path("/does/not/exist/reviewer_calibration.json"))
    monkeypatch.setattr(gate, "POLICY", Path("/does/not/exist/scheduled_execution_policy.json"))


def test_a_scheduled_run_with_no_authorization_is_a_clean_evidenced_no_op(
    unauthorized_env: None, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = gate.main(["--max", "1"])
    out = capsys.readouterr().out
    assert exit_code == 0, "an unauthorized scheduled run must never fail the job red"
    assert "authorized=false" in out
    assert "repository=\n" in out and "ecosystem=\n" in out, (
        "no repository/ecosystem may be emitted when unauthorized -- nothing downstream can "
        "accidentally pick up a stale or partial target"
    )
    assert "TC-004" in out and "TC-007" in out and "scheduled_execution_authorized" in out


@pytest.fixture
def authorized_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every predicate cleared, and the registry/state-remote the gate reads to pick a real
    target. Returns the registry path."""
    decision_log = tmp_path / "DECISION_LOG.md"
    decision_log.write_text("OWNER_RULING_SWEEP_PAUSE: LIFTED ref=x\n", encoding="utf-8")
    monkeypatch.setattr(gate, "DECISION_LOG", decision_log)

    calibration = tmp_path / "reviewer_calibration.json"
    calibration.write_text(json.dumps({"status": "PASSED"}), encoding="utf-8")
    monkeypatch.setattr(gate, "CALIBRATION", calibration)

    policy = tmp_path / "scheduled_execution_policy.json"
    policy.write_text(
        json.dumps(
            {
                "scheduled_execution_authorized": True,
                "authorized_repositories": [REPOSITORY],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "POLICY", policy)

    registry = write_registry_file(
        tmp_path, [monitor_registry_entry(REPOSITORY, mode="dry_run", repository_id=7)]
    )
    init_git_repository(tmp_path / "remote")
    return registry


def test_a_fully_authorized_scheduled_run_selects_the_named_repository(
    authorized_env: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    exit_code = gate.main(
        ["--max", "1", "--remote", str(tmp_path / "remote"), "--registry", str(authorized_env)]
    )
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "authorized=true" in out
    assert f"repository={REPOSITORY}" in out
    assert "ecosystem=net" in out


def test_authorization_alone_is_not_enough_without_sweep_pause_lifted(
    authorized_env: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control: re-pausing after the authorized_env fixture already lifted it must
    block the run again, proving the sweep-pause predicate is actually load-bearing and not a
    check that always happens to pass."""
    decision_log = tmp_path / "DECISION_LOG.md"
    decision_log.write_text("OWNER_RULING_SWEEP_PAUSE: UPHELD ref=x\n", encoding="utf-8")
    monkeypatch.setattr(gate, "DECISION_LOG", decision_log)

    exit_code = gate.main(
        ["--max", "1", "--remote", str(tmp_path / "remote"), "--registry", str(authorized_env)]
    )
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "authorized=false" in out
    assert "TC-004" in out


def test_a_repository_not_named_in_authorized_repositories_is_never_selected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    decision_log = tmp_path / "DECISION_LOG.md"
    decision_log.write_text("OWNER_RULING_SWEEP_PAUSE: LIFTED ref=x\n", encoding="utf-8")
    monkeypatch.setattr(gate, "DECISION_LOG", decision_log)

    calibration = tmp_path / "reviewer_calibration.json"
    calibration.write_text(json.dumps({"status": "PASSED"}), encoding="utf-8")
    monkeypatch.setattr(gate, "CALIBRATION", calibration)

    other_repo = "aspose-words-foss/Aspose.Words-FOSS-for-.NET"
    policy = tmp_path / "scheduled_execution_policy.json"
    policy.write_text(
        json.dumps(
            {"scheduled_execution_authorized": True, "authorized_repositories": [other_repo]}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "POLICY", policy)

    registry = write_registry_file(
        tmp_path, [monitor_registry_entry(REPOSITORY, mode="dry_run", repository_id=7)]
    )
    init_git_repository(tmp_path / "remote")

    exit_code = gate.main(
        ["--max", "1", "--remote", str(tmp_path / "remote"), "--registry", str(registry)]
    )
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "authorized=false" in out
    assert REPOSITORY not in out.split("reason=")[0]  # never emitted as the selected repository
