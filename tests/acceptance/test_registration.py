"""Tests for the A1 registration-building module (TC-022a).

These tests never write a real, committed registration file (that path is denied to a worker
card by ``ops/gatectl.py``'s ``GLOBAL_DENY``): every property is proved either over small,
in-memory fixtures constructed here, or by reading the real, already-committed source files
read-only (no write, no network, no provider call) and asserting on the honest numbers that come
back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_presenter.acceptance.registration import (
    RECALL_CLASSES,
    CaseRecord,
    apply_audit_labels,
    build_a1_from_existing_data,
    canonical_digest,
    cohens_kappa,
    load_audit_labels,
    load_calibration_registration,
    load_sealed_baseline,
    second_labeller_pass,
    select_a1,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_MARKDOWN = REPO_ROOT / "docs/investigations/2026-11-06-unsupported-claim-class-audit.md"
CALIBRATION_REGISTRATION = (
    REPO_ROOT
    / "docs/investigations/2026-11-06-reviewer-calibration-iteration-5-data/registration.json"
)
SEALED_BASELINE = REPO_ROOT / "data/recertification_baseline.json"


def _fixture_records() -> list[CaseRecord]:
    """One hand-audited case per recall class, plus three clean twins."""
    records = [
        CaseRecord(
            case_id=f"fixture:{cls.lower()}/real:unsupported_claim:0",
            source="audited_real_defect",
            role="real_defect",
            is_clean_twin=False,
            digest=f"digest-{cls}",
            recall_class=cls,
            audited=True,
        )
        for cls in RECALL_CLASSES
    ]
    records.extend(
        CaseRecord(
            case_id=f"fixture:clean:{index}",
            source="calibration_registration",
            role="clean",
            is_clean_twin=True,
            digest=f"clean-digest-{index}",
        )
        for index in range(3)
    )
    return records


# --------------------------------------------------------------------------------------------
# (a) determinism: two runs over the same fixed inputs produce a byte-identical digest, pinned
#     against a literal expected value (so a hash-algorithm swap, not just an internal
#     inconsistency, is what the negative control must break).
# --------------------------------------------------------------------------------------------


def test_digest_is_deterministic_and_pinned() -> None:
    records = _fixture_records()
    first = select_a1(records, per_class_min=1, clean_twin_min=1)
    second = select_a1(list(reversed(records)), per_class_min=1, clean_twin_min=1)

    # Same inputs, reordered -> the exact same digest (order-independence).
    assert first.digest == second.digest

    # A literal, pinned SHA-256 value: computed once from this exact fixture and frozen here so a
    # mutation that swaps the hash algorithm (sha256 -> md5) changes the digest this module
    # produces and breaks this assertion, not just an internal self-consistency check that would
    # pass under any hash function.
    assert first.digest == "9919f36a679ccc015bfbde253a6bbea8bf6619dc05f9e3c6cb65555395047fc9"
    assert len(first.digest) == 64  # a SHA-256 hex digest is exactly 64 hex characters


def test_canonical_digest_changes_when_a_case_changes() -> None:
    records = _fixture_records()
    base = select_a1(records, per_class_min=1, clean_twin_min=1)
    mutated_records = list(records)
    mutated_records[0] = CaseRecord(
        case_id=mutated_records[0].case_id,
        source=mutated_records[0].source,
        role=mutated_records[0].role,
        is_clean_twin=mutated_records[0].is_clean_twin,
        digest="a-different-digest",
        recall_class=mutated_records[0].recall_class,
        audited=mutated_records[0].audited,
    )
    changed = select_a1(mutated_records, per_class_min=1, clean_twin_min=1)
    assert changed.digest != base.digest


# --------------------------------------------------------------------------------------------
# (b) the shortfall report is correct against a constructed fixture where the minimums are
#     deliberately not met, and correct again when they are met.
# --------------------------------------------------------------------------------------------


def test_shortfall_report_honestly_reports_a_deliberate_shortfall() -> None:
    records = _fixture_records()  # exactly 1 case per class, 3 clean twins
    registration = select_a1(records, per_class_min=30, clean_twin_min=50)

    assert registration.shortfall.met is False
    assert registration.shortfall.per_class_achieved == {cls: 1 for cls in RECALL_CLASSES}
    assert registration.shortfall.per_class_shortfall == {cls: 29 for cls in RECALL_CLASSES}
    assert registration.shortfall.short_classes() == sorted(RECALL_CLASSES)
    assert registration.shortfall.clean_twin_achieved == 3
    assert registration.shortfall.clean_twin_shortfall == 47

    # Never padded: exactly the 5 audited cases are selected, not 150.
    assert len(registration.labelled_cases) == 5
    assert len(registration.clean_twins) == 3


def test_shortfall_report_is_met_when_minimums_are_reached() -> None:
    records = _fixture_records()
    registration = select_a1(records, per_class_min=1, clean_twin_min=1)
    assert registration.shortfall.met is True
    assert registration.shortfall.per_class_shortfall == {cls: 0 for cls in RECALL_CLASSES}
    assert registration.shortfall.clean_twin_shortfall == 0


# --------------------------------------------------------------------------------------------
# (c) every case in the output selection (the recall-class sample) carries exactly one of the
#     five classes A/B/C/D/E; a clean twin (no single flagged claim) is never force-labelled.
# --------------------------------------------------------------------------------------------


def test_every_labelled_case_carries_exactly_one_of_the_five_classes() -> None:
    records = _fixture_records()
    # Add a record with no recall class at all (e.g. an un-audited mutant); it must never end up
    # in labelled_cases.
    records.append(
        CaseRecord(
            case_id="fixture:unaudited-mutant",
            source="calibration_registration",
            role="mutant",
            is_clean_twin=False,
            digest="mutant-digest",
            recall_class=None,
        )
    )
    registration = select_a1(records, per_class_min=1, clean_twin_min=1)

    assert len(registration.labelled_cases) == 5
    for case in registration.labelled_cases:
        assert case.recall_class in RECALL_CLASSES
        assert case.recall_class is not None

    seen_ids = {case.case_id for case in registration.labelled_cases}
    assert "fixture:unaudited-mutant" not in seen_ids

    # Clean twins are a disjoint pool and never carry a recall class.
    for twin in registration.clean_twins:
        assert twin.recall_class is None
        assert twin.is_clean_twin is True


# --------------------------------------------------------------------------------------------
# Loaders: the audit markdown table, the calibration registration document, the sealed baseline.
# --------------------------------------------------------------------------------------------


def test_load_audit_labels_parses_a_small_fixture_table() -> None:
    markdown = """
# Title

## 5. Every case

| Case | Class | Origin |
|---|---|---|
| `own:x/real:unsupported_claim:0` | A | generated |
| `own:y/real:unsupported_claim:1` | b | inherited |

## 6. Next section

| Case | Class |
|---|---|
| `own:z/real:unsupported_claim:2` | C |
"""
    labels = load_audit_labels(markdown)
    assert labels == {
        "own:x/real:unsupported_claim:0": "A",
        "own:y/real:unsupported_claim:1": "B",
    }


def test_load_audit_labels_rejects_an_unrecognised_class() -> None:
    markdown = """
## 5. Every case

| Case | Class |
|---|---|
| `own:x/real:unsupported_claim:0` | Z |
"""
    with pytest.raises(ValueError):
        load_audit_labels(markdown)


def test_load_calibration_registration_rejects_the_wrong_schema() -> None:
    with pytest.raises(ValueError):
        load_calibration_registration({"schema": "something-else/1", "cases": []})


def test_load_calibration_registration_from_a_small_fixture() -> None:
    document = {
        "schema": "reviewer-calibration-registration/1",
        "cases": [
            {
                "case": "own:x/clean",
                "base": "own:x",
                "role": "clean",
                "klass": None,
                "readme_sha256": "abc123",
                "defect_sha256": None,
            },
            {
                "case": "own:x/real:unsupported_claim:0",
                "base": "own:x",
                "role": "real_defect",
                "klass": "unsupported_claim",
                "readme_sha256": "abc123",
                "defect_sha256": "def456",
            },
        ],
    }
    records = load_calibration_registration(document)
    by_id = {record.case_id: record for record in records}
    assert by_id["own:x/clean"].is_clean_twin is True
    assert by_id["own:x/clean"].digest == "abc123"
    assert by_id["own:x/real:unsupported_claim:0"].is_clean_twin is False
    assert by_id["own:x/real:unsupported_claim:0"].digest == "def456"
    assert by_id["own:x/real:unsupported_claim:0"].recall_class is None  # not yet audited


def test_load_sealed_baseline_treats_recertified_with_no_failing_checks_as_clean() -> None:
    document = {
        "seals": [
            {
                "repository": "a/b",
                "lane": "L",
                "revision": "r1",
                "outcome": "RECERTIFIED",
                "commit": "c1",
                "failing_checks": [],
            },
            {
                "repository": "a/c",
                "lane": "R",
                "revision": "r2",
                "outcome": "NEEDS_REPAIR",
                "commit": "c2",
                "failing_checks": ["BC-07"],
            },
            {
                "repository": "a/d",
                "lane": "L",
                "revision": "r3",
                "outcome": "RECERTIFIED",
                "commit": "c3",
                "failing_checks": ["BC-02"],
            },
        ]
    }
    records = load_sealed_baseline(document)
    by_base = {record.base: record for record in records}
    assert by_base["a/b"].is_clean_twin is True
    assert by_base["a/c"].is_clean_twin is False
    assert by_base["a/d"].is_clean_twin is False  # RECERTIFIED but still has a failing check


def test_apply_audit_labels_reports_unmatched_ids_without_dropping_them() -> None:
    records = [
        CaseRecord(
            case_id="own:x/real:unsupported_claim:0",
            source="calibration_registration",
            role="real_defect",
            is_clean_twin=False,
            digest="d1",
        )
    ]
    updated, unmatched = apply_audit_labels(
        records,
        {
            "own:x/real:unsupported_claim:0": "A",
            "own:ghost/real:unsupported_claim:9": "B",
        },
    )
    assert unmatched == ["own:ghost/real:unsupported_claim:9"]
    assert updated[0].recall_class == "A"
    assert updated[0].audited is True
    assert updated[0].digest == "d1"  # every other field kept exactly as registered


# --------------------------------------------------------------------------------------------
# Cohen's kappa and the second-labeller stand-in.
# --------------------------------------------------------------------------------------------


def test_cohens_kappa_is_one_for_perfect_agreement() -> None:
    pairs = [("A", "A"), ("B", "B"), ("A", "A")]
    assert cohens_kappa(pairs) == pytest.approx(1.0)


def test_cohens_kappa_is_none_for_no_pairs() -> None:
    assert cohens_kappa([]) is None


def test_second_labeller_pass_is_always_marked_as_a_stand_in() -> None:
    records = _fixture_records()
    labelled = [record for record in records if record.recall_class is not None]
    assert len(labelled) == 5
    result = second_labeller_pass(labelled, fraction=0.2)
    assert result.stand_in is True
    assert result.method == "simple_majority_baseline"
    assert result.sample_size == 1  # ceil(5 * 0.2) == 1
    assert result.agreement is not None


def test_second_labeller_pass_handles_an_empty_selection() -> None:
    result = second_labeller_pass([], fraction=0.2)
    assert result.stand_in is True
    assert result.sample_size == 0
    assert result.agreement is None


# --------------------------------------------------------------------------------------------
# The real build, over the real, already-committed source files (read-only; no write, no
# network, no provider call). This is the honest report of the real zero-call floor.
# --------------------------------------------------------------------------------------------


@pytest.mark.skipif(
    not (AUDIT_MARKDOWN.is_file() and CALIBRATION_REGISTRATION.is_file() and SEALED_BASELINE.is_file()),
    reason="the real committed source files are not present in this checkout",
)
def test_real_build_reports_the_honest_zero_call_floor() -> None:
    registration, unmatched = build_a1_from_existing_data(
        audit_markdown_path=AUDIT_MARKDOWN,
        calibration_registration_path=CALIBRATION_REGISTRATION,
        sealed_baseline_path=SEALED_BASELINE,
    )

    # Every one of the 113 hand-audited case ids in the audit markdown matches a case already in
    # the calibration registration -- no drift between the two committed documents.
    assert unmatched == []

    # The real per-class counts found by the 2026-11-06 unsupported-claim-class audit (section 1):
    # unsupported_claim A=13/B=69/C=14/D=4/E=0 and contradiction A=10/B=1/C=0/D=0/E=2.
    assert registration.shortfall.per_class_achieved == {
        "A": 23,
        "B": 70,
        "C": 14,
        "D": 4,
        "E": 2,
    }
    # Only B reaches the n>=30 minimum from existing data alone; this is reported honestly, not
    # padded and not silently lowered.
    assert registration.shortfall.per_class_shortfall == {
        "A": 7,
        "B": 0,
        "C": 16,
        "D": 26,
        "E": 28,
    }
    assert registration.shortfall.met is False
    assert registration.shortfall.short_classes() == ["A", "C", "D", "E"]

    # Clean twins (28 registered "clean" + 23 "unscored_twin" + 27 sealed RECERTIFIED-clean) reach the
    # n>=50 minimum from existing data alone. 27: the sealed baseline now holds 35 seals (re-certified
    # under current code); load_sealed_baseline() counts every RECERTIFIED seal with no failing
    # checks as a clean twin, so the count follows the baseline honestly (60 -> 73 -> 78): a derived
    # number, not a target.
    assert registration.shortfall.clean_twin_achieved == 78
    assert registration.shortfall.clean_twin_shortfall == 0

    assert len(registration.labelled_cases) == 113
    assert registration.second_labeller.stand_in is True
    assert registration.second_labeller.sample_size == 23  # ceil(113 * 0.2)

    # The digest is a real SHA-256 hex digest and is itself deterministic across two builds.
    assert len(registration.digest) == 64
    again, _ = build_a1_from_existing_data(
        audit_markdown_path=AUDIT_MARKDOWN,
        calibration_registration_path=CALIBRATION_REGISTRATION,
        sealed_baseline_path=SEALED_BASELINE,
    )
    assert again.digest == registration.digest


def test_build_a1_from_existing_data_never_writes_anything(tmp_path: Path) -> None:
    """The module's own tests never freeze the real, committed A1 file (TC-022a's closeout is a
    separate, supervisor-direct step) -- this test proves the build function only reads, by
    pointing it at copies of the real documents inside a throwaway temporary directory and
    confirming nothing else appears there afterwards."""
    if not (AUDIT_MARKDOWN.is_file() and CALIBRATION_REGISTRATION.is_file() and SEALED_BASELINE.is_file()):
        pytest.skip("the real committed source files are not present in this checkout")

    work = tmp_path / "work"
    work.mkdir()
    audit_copy = work / "audit.md"
    registration_copy = work / "registration.json"
    baseline_copy = work / "baseline.json"
    audit_copy.write_text(AUDIT_MARKDOWN.read_text(encoding="utf-8"), encoding="utf-8")
    registration_copy.write_text(
        CALIBRATION_REGISTRATION.read_text(encoding="utf-8"), encoding="utf-8"
    )
    baseline_copy.write_text(SEALED_BASELINE.read_text(encoding="utf-8"), encoding="utf-8")

    before = sorted(p.name for p in work.iterdir())
    build_a1_from_existing_data(
        audit_markdown_path=audit_copy,
        calibration_registration_path=registration_copy,
        sealed_baseline_path=baseline_copy,
    )
    after = sorted(p.name for p in work.iterdir())
    assert before == after  # nothing was written
