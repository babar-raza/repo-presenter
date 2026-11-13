"""BC-18 (must-correct): an open findings-register quote still printed fails, and routes to a repair.

The register is a fixture file passed through ``Candidate.findings_path``; the real
``data/readme_findings.json`` is never read or written here.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import test_registry_checks as shared
from repo_presenter.readme.reconciliation.patch import failing_units
from repo_presenter.readme.repair.loop import scope_record
from repo_presenter.readme.repair.targeted import validation_defects
from repo_presenter.readme.validation.blocking import (
    CHECK_NAMES,
    JUDGES,
    blocking_failures,
    validate_candidate,
)
from repo_presenter.readme.validation.must_correct import must_correct_failures
from repo_presenter.readme_findings import (
    LANE_L,
    LANE_R,
    append_finding,
    must_correct_rows,
    read_findings,
    regression_rows,
    resolve_finding,
)

REPO = shared.ENTRY.repository
UNIT_QUOTE = "Kept verbatim from the old README."
SECTION_QUOTE = "Sentence 3 about the API."
TRUTH = "The package also writes glTF, per setup.py."


def _register(tmp_path: Path, **kwargs) -> Path:
    path = tmp_path / "findings.json"
    append_finding(
        path,
        repository=kwargs.pop("repository", REPO),
        description=kwargs.pop("description", "false claim"),
        evidence=kwargs.pop("evidence", "setup.py:12@" + shared.REVISION),
        route=kwargs.pop("route", LANE_R),
        first_seen_at="2026-11-12",
        **kwargs,
    )
    return path


def _candidate(path: Path | None, **overrides):
    return dataclasses.replace(shared._candidate(), findings_path=path, **overrides)


def _validate(candidate, tmp_path: Path):
    return validate_candidate(candidate, tmp_path, ())


def test_check_is_registered() -> None:
    assert JUDGES["BC-18"] is must_correct_failures and "BC-18" in CHECK_NAMES


def test_quote_in_a_placed_unit_fails_and_the_defect_names_the_unit_and_truth(
    tmp_path: Path,
) -> None:
    path = _register(tmp_path, quote=UNIT_QUOTE, truth=TRUTH)
    document = _validate(_candidate(path), tmp_path)
    (check,) = [c for c in blocking_failures(document) if c["id"] == "BC-18"]
    assert check["causal_stage"] == "RECONCILING"
    (failure,) = check["failures"]
    assert failure["unit_id"] == "inherited_unit:002.paragraph"
    assert failure["quote"] == UNIT_QUOTE and TRUTH in failure["instruction"]
    assert TRUTH in failure["detail"]

    (defect,) = [d for d in validation_defects(document, set()) if d.label == "BC-18"]
    assert defect.stage == "S4" and defect.repairable
    assert defect.record["failures"][0]["unit_id"] == "inherited_unit:002.paragraph"
    assert defect.record["quote"] == UNIT_QUOTE and TRUTH in defect.record["instruction"]
    # The S4 patch reads the unit from the failure's field and the quote from the record
    # (repair/loop.py ``_named_units`` / ``_repair_reconciliation``): no prose is parsed.
    assert failing_units(defect.record) == ["inherited_unit:002.paragraph"]
    assert scope_record(defect, failing_units(defect.record))["failures"][0]["unit_id"] == (
        "inherited_unit:002.paragraph"
    )


def test_quote_in_an_authored_section_routes_to_that_section(tmp_path: Path) -> None:
    path = _register(tmp_path, quote=SECTION_QUOTE, truth=TRUTH)
    document = _validate(_candidate(path), tmp_path)
    (check,) = [c for c in blocking_failures(document) if c["id"] == "BC-18"]
    assert check["failures"][0]["section_id"] == "key_capabilities"
    (defect,) = [
        d for d in validation_defects(document, {"key_capabilities"}) if d.label == "BC-18"
    ]
    assert defect.stage == "S6" and defect.section_id == "key_capabilities"
    assert TRUTH in defect.record["instruction"]


def test_matching_is_whitespace_normalised(tmp_path: Path) -> None:
    path = _register(tmp_path, quote="Kept   verbatim\nfrom the old README.", truth=TRUTH)
    assert must_correct_failures(_candidate(path))


def test_quote_absent_passes(tmp_path: Path) -> None:
    path = _register(tmp_path, quote="a sentence the README never prints", truth=TRUTH)
    assert must_correct_failures(_candidate(path)) == []
    assert shared._verdicts(_validate(_candidate(path), tmp_path))["BC-18"] == "PASS"


def test_lane_l_passes(tmp_path: Path) -> None:
    path = _register(tmp_path, quote=UNIT_QUOTE, truth=TRUTH)
    assert must_correct_failures(_candidate(path, lane="L")) == []


def test_resolved_row_quote_reappearing_fails_with_its_truth(tmp_path: Path) -> None:
    """Owner, 2026-11-13: an already caught problem must not reappear. A RESOLVED row is a
    permanent regression check; it is not citable (citations stay OPEN-only), and its stored
    truth is the repair instruction."""
    path = _register(tmp_path, quote=UNIT_QUOTE, truth=TRUTH)
    resolve_finding(path, repository=REPO, description="false claim", resolved_at="2026-11-13")
    assert must_correct_rows(REPO, path) == []
    (failure,) = must_correct_failures(_candidate(path))
    assert failure.quote == UNIT_QUOTE and TRUTH in failure.instruction
    assert "printed again" in failure.detail and "finding:" not in failure.instruction
    document = _validate(_candidate(path), tmp_path)
    assert shared._verdicts(document)["BC-18"] == "FAIL"


def test_resolved_row_whose_quote_is_gone_passes(tmp_path: Path) -> None:
    path = _register(tmp_path, quote="a sentence the README never prints", truth=TRUTH)
    resolve_finding(path, repository=REPO, description="false claim", resolved_at="2026-11-13")
    assert must_correct_failures(_candidate(path)) == []


def test_refuted_row_never_blocks(tmp_path: Path) -> None:
    """A row recorded as REFUTED (its claim was true after all, e.g. the Email .NET 26.7.0 rows)
    must not block the true text it quotes."""
    path = _register(
        tmp_path, quote=UNIT_QUOTE, truth=TRUTH,
        evidence="REFUTED 2026-11-13 by the sealed facts: package:published_version = 26.7.0",
    )
    resolve_finding(path, repository=REPO, description="false claim", resolved_at="2026-11-13")
    assert regression_rows(REPO, LANE_R, path) == []
    assert must_correct_failures(_candidate(path)) == []


def test_lane_l_candidate_is_held_to_lane_l_rows_only(tmp_path: Path) -> None:
    path = _register(tmp_path, quote=UNIT_QUOTE, truth=TRUTH, route=LANE_L)
    (failure,) = must_correct_failures(_candidate(path, lane="L"))
    assert failure.quote == UNIT_QUOTE
    # ...and a Lane R candidate is not held to a lane_l row, nor a Lane L one to a lane_r row.
    assert must_correct_failures(_candidate(path)) == []
    lane_r = _register(tmp_path / "r", quote=UNIT_QUOTE, truth=TRUTH)
    assert must_correct_failures(_candidate(lane_r, lane="L")) == []


def test_lane_l_route_other_repository_and_quoteless_rows_do_not_count(tmp_path: Path) -> None:
    path = _register(tmp_path, quote=UNIT_QUOTE, truth=TRUTH, route=LANE_L)
    append_finding(
        path, repository="other/repo", description="d", evidence="", route=LANE_R,
        first_seen_at="2026-11-12", quote=UNIT_QUOTE, truth=TRUTH,
    )
    append_finding(
        path, repository=REPO, description="no quote", evidence="", route=LANE_R,
        first_seen_at="2026-11-12",
    )
    assert must_correct_rows(REPO, path) == []
    assert must_correct_failures(_candidate(path)) == []


def test_missing_empty_or_unreadable_register_is_a_noop(tmp_path: Path) -> None:
    assert must_correct_failures(_candidate(tmp_path / "absent.json")) == []
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"schema_version": 1, "findings": []}), encoding="utf-8")
    assert must_correct_failures(_candidate(empty)) == []
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert must_correct_failures(_candidate(broken)) == []


def test_old_format_rows_still_load_and_stay_byte_identical(tmp_path: Path) -> None:
    path = tmp_path / "old.json"
    old = {
        "schema_version": 1,
        "findings": [
            {
                "repository": REPO, "description": "d", "evidence": "e", "route": LANE_R,
                "status": "OPEN", "first_seen_at": "2026-11-01", "resolved_at": None,
            }
        ],
    }
    path.write_text(json.dumps(old), encoding="utf-8")
    (row,) = read_findings(path)
    assert row.quote == "" and row.truth == ""
    assert row.to_record() == old["findings"][0]
    # Re-reporting the same row with a quote updates it in place and keeps its age.
    updated = append_finding(
        path, repository=REPO, description="d", evidence="e2", route=LANE_R,
        first_seen_at="2026-11-12", quote="q", truth="t",
    )
    assert updated.first_seen_at == "2026-11-01" and updated.quote == "q"
    assert len(read_findings(path)) == 1
