"""The findings register (TC-025 point 3): every defect either lane detects gets exactly one
durable row, over a path the caller supplies.

Every test here runs against a temporary fixture copy (``tmp_path``) only -- never against
``data/readme_findings.json``, the real file this repository's pipeline runs write to. That file
is seeded empty by the supervisor and is never read or written by this test module.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.readme_findings import (
    LANE_L,
    LANE_R,
    STATUS_OPEN,
    STATUS_RESOLVED,
    FindingRecord,
    FindingsRegisterError,
    append_finding,
    import_review,
    read_findings,
    resolve_finding,
    review_description,
)


@pytest.fixture
def register(tmp_path: Path) -> Path:
    return tmp_path / "readme_findings.json"


# --- reading ------------------------------------------------------------------------------------


def test_a_missing_file_is_an_empty_register(register: Path) -> None:
    assert read_findings(register) == []


def test_a_file_with_the_wrong_schema_version_is_refused(register: Path) -> None:
    register.write_text('{"schema_version": 2, "findings": []}\n', encoding="utf-8")
    with pytest.raises(FindingsRegisterError, match="schema_version"):
        read_findings(register)


def test_a_file_that_is_not_json_is_refused(register: Path) -> None:
    register.write_text("not json\n", encoding="utf-8")
    with pytest.raises(FindingsRegisterError):
        read_findings(register)


# --- appending and deduping ----------------------------------------------------------------------


def test_append_finding_creates_the_file_and_the_schema(register: Path) -> None:
    assert not register.exists()
    row = append_finding(
        register,
        repository="aspose-cells-foss/Aspose.Cells-FOSS-for-.Net",
        description="stale_package_version line 12: pins 26.6.0, registry lists 26.9.0",
        evidence="README.md line 12",
        route=LANE_L,
        first_seen_at="2026-11-07",
    )
    assert row.status == STATUS_OPEN and row.route == LANE_L
    assert register.is_file()
    (loaded,) = read_findings(register)
    assert loaded == row


def test_a_second_report_of_the_same_repository_and_description_updates_in_place(
    register: Path,
) -> None:
    first = append_finding(
        register,
        repository="r/x",
        description="d",
        evidence="e1",
        route=LANE_R,
        first_seen_at="2026-11-01",
    )
    second = append_finding(
        register,
        repository="r/x",
        description="d",
        evidence="e2",
        route=LANE_L,
        first_seen_at="2026-11-07",  # ignored: the row already exists
    )
    assert len(read_findings(register)) == 1
    assert second.first_seen_at == first.first_seen_at == "2026-11-01"
    assert second.evidence == "e2" and second.route == LANE_L


def test_a_different_description_for_the_same_repository_is_a_second_row(register: Path) -> None:
    append_finding(
        register, repository="r/x", description="a", evidence="e", route=LANE_L,
        first_seen_at="2026-11-01",
    )
    append_finding(
        register, repository="r/x", description="b", evidence="e", route=LANE_L,
        first_seen_at="2026-11-01",
    )
    assert len(read_findings(register)) == 2


def test_an_unknown_route_is_refused(register: Path) -> None:
    with pytest.raises(FindingsRegisterError, match="route"):
        append_finding(
            register, repository="r/x", description="a", evidence="e", route="lane_q",
            first_seen_at="2026-11-01",
        )


def test_a_defect_with_no_upstream_trigger_is_still_routed_never_dropped(register: Path) -> None:
    """R5(a): a defect found with no upstream change on record is Lane R's, owned and visible --
    never silently absent from the register for lack of a reason to run Lane L again."""
    row = append_finding(
        register,
        repository="aspose-gis-foss/Aspose.GIS.FOSS-for-.Net",
        description="no README to correct",
        evidence="inventory.readme_path is None",
        route=LANE_R,
        first_seen_at="2026-11-07",
    )
    assert row.route == LANE_R
    assert read_findings(register)[0].status == STATUS_OPEN


# --- resolving -----------------------------------------------------------------------------------


def test_resolve_finding_marks_it_resolved_and_is_idempotent(register: Path) -> None:
    append_finding(
        register, repository="r/x", description="a", evidence="e", route=LANE_L,
        first_seen_at="2026-11-01",
    )
    resolved = resolve_finding(
        register, repository="r/x", description="a", resolved_at="2026-11-07"
    )
    assert resolved is not None
    assert resolved.status == STATUS_RESOLVED and resolved.resolved_at == "2026-11-07"
    again = resolve_finding(
        register, repository="r/x", description="a", resolved_at="2026-11-08"
    )
    assert again is not None and again.resolved_at == "2026-11-08"  # re-resolving still updates
    assert len(read_findings(register)) == 1


def test_resolving_a_finding_never_reported_changes_nothing(register: Path) -> None:
    assert resolve_finding(
        register, repository="r/x", description="never seen", resolved_at="2026-11-07"
    ) is None
    assert read_findings(register) == []


def test_a_resolved_finding_reported_again_reopens_it(register: Path) -> None:
    append_finding(
        register, repository="r/x", description="a", evidence="e", route=LANE_L,
        first_seen_at="2026-11-01",
    )
    resolve_finding(register, repository="r/x", description="a", resolved_at="2026-11-02")
    reopened = append_finding(
        register, repository="r/x", description="a", evidence="e2", route=LANE_L,
        first_seen_at="2026-11-09",
    )
    assert reopened.status == STATUS_OPEN
    # the dedup key preserved the finding's identity: still one row, still its original age.
    assert len(read_findings(register)) == 1
    assert reopened.first_seen_at == "2026-11-01"


# --- age and the record's own invariants ---------------------------------------------------------


def test_age_days_counts_from_first_seen_never_from_a_later_update(register: Path) -> None:
    from datetime import date

    row = append_finding(
        register, repository="r/x", description="a", evidence="e", route=LANE_L,
        first_seen_at="2026-11-01",
    )
    assert row.age_days(today=date(2026, 11, 8)) == 7
    append_finding(
        register, repository="r/x", description="a", evidence="e2", route=LANE_R,
        first_seen_at="2026-11-07",
    )
    (still,) = read_findings(register)
    assert still.age_days(today=date(2026, 11, 8)) == 7


def test_an_open_finding_may_not_carry_a_resolved_at(register: Path) -> None:
    with pytest.raises(FindingsRegisterError, match="OPEN"):
        FindingRecord(
            repository="r/x", description="a", evidence="e", route=LANE_L,
            status=STATUS_OPEN, first_seen_at="2026-11-01", resolved_at="2026-11-02",
        )


def test_a_resolved_finding_must_carry_a_resolved_at(register: Path) -> None:
    with pytest.raises(FindingsRegisterError, match="RESOLVED"):
        FindingRecord(
            repository="r/x", description="a", evidence="e", route=LANE_L,
            status=STATUS_RESOLVED, first_seen_at="2026-11-01",
        )


def test_the_register_file_is_deterministic_json(register: Path) -> None:
    append_finding(
        register, repository="r/b", description="x", evidence="e", route=LANE_L,
        first_seen_at="2026-11-01",
    )
    append_finding(
        register, repository="r/a", description="x", evidence="e", route=LANE_L,
        first_seen_at="2026-11-01",
    )
    first = register.read_text(encoding="utf-8")
    assert first.endswith("\n") and "\r" not in first
    second_register = register.with_name("second.json")
    append_finding(
        second_register, repository="r/b", description="x", evidence="e", route=LANE_L,
        first_seen_at="2026-11-01",
    )
    append_finding(
        second_register, repository="r/a", description="x", evidence="e", route=LANE_L,
        first_seen_at="2026-11-01",
    )
    assert second_register.read_text(encoding="utf-8") == first  # sorted by (repository, description)


# --- importing an independent fact-check review ----------------------------------------------

_README = "Intro.\n\nRun `dotnet build` from the checkout.\n\nThen dotnet build src/A.csproj -c Release.\n"


def _item(quote: str, verdict: str = "FALSE", **extra) -> dict:
    return {"quote": quote, "verdict": verdict, "truth": "t", "evidence": "a.cs:1@abc", **extra}


def test_import_registers_factual_verdicts_and_skips_deterministic_classes(register: Path) -> None:
    registered, skipped = import_review(
        register, repository="o/r", readme=_README, first_seen_at="2026-11-13",
        items=[
            _item("Run `dotnet build` from the checkout."),
            _item("Intro.", "INTERNAL_WORDING"),
            _item("Then dotnet build src/A.csproj", "MISLEADING"),
        ],
    )
    assert [row.quote for row in registered] == [
        "Run `dotnet build` from the checkout.", "Then dotnet build src/A.csproj",
    ]
    assert [item["verdict"] for item, _ in skipped] == ["INTERNAL_WORDING"]
    rows = read_findings(register)
    assert {row.description for row in rows} == {
        review_description("FALSE", "Run `dotnet build` from the checkout."),
        review_description("MISLEADING", "Then dotnet build src/A.csproj"),
    }
    assert all(row.status == STATUS_OPEN and row.route == LANE_R for row in rows)
    # Re-importing the same review updates in place: no duplicate rows.
    import_review(register, repository="o/r", readme=_README, first_seen_at="2026-11-14",
                  items=[_item("Run `dotnet build` from the checkout.")])
    assert len(read_findings(register)) == 2


def test_import_refuses_an_over_broad_or_absent_quote_and_writes_nothing(register: Path) -> None:
    # The 2026-11-13 lesson: the bare "dotnet build" also matches the correct build line.
    for quote in ("dotnet build", "a sentence the README never prints"):
        with pytest.raises(FindingsRegisterError, match="printed"):
            import_review(register, repository="o/r", readme=_README, first_seen_at="2026-11-13",
                          items=[_item("Intro."), _item(quote)])
    assert read_findings(register) == []
    # ...unless the item states the repeat is deliberate (one false claim printed twice).
    registered, _ = import_review(register, repository="o/r", readme=_README,
                                  first_seen_at="2026-11-13",
                                  items=[_item("dotnet build", occurrences=2)])
    assert len(registered) == 1
