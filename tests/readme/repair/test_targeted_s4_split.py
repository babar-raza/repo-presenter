"""An S4 validation check naming several inherited units is one repairable defect per unit."""

from __future__ import annotations

from repo_presenter.readme.repair.targeted import validation_defects


def _validation(failures):
    return {
        "validator_version": "v",
        "checks": [
            {
                "id": "BC-05",
                "name": "dispositions",
                "verdict": "FAIL",
                "causal_stage": "RECONCILING",
                "details": [f["detail"] for f in failures],
                "failures": failures,
            }
        ],
    }


def test_each_named_unit_is_its_own_defect_with_its_own_fingerprint() -> None:
    failures = [
        {"detail": "a", "unit_id": "inherited_unit:016.paragraph", "causal_stage": "RECONCILING"},
        {"detail": "b", "unit_id": "inherited_unit:036.paragraph", "causal_stage": "RECONCILING"},
        {"detail": "c", "unit_id": "inherited_unit:036.paragraph", "causal_stage": "RECONCILING"},
    ]
    defects = validation_defects(_validation(failures), set())
    assert len(defects) == 2
    assert len({d.fingerprint for d in defects}) == 2
    assert [len(d.record["failures"]) for d in defects] == [1, 2]
    assert all(d.stage == "S4" for d in defects)


def test_unit_less_failures_stay_one_defect_beside_the_units() -> None:
    failures = [
        {"detail": "a", "unit_id": "inherited_unit:016.paragraph"},
        {"detail": "batch-wide"},
    ]
    defects = validation_defects(_validation(failures), set())
    assert len(defects) == 2
    assert defects[-1].record["failures"] == [{"detail": "batch-wide"}]


def test_a_check_naming_no_unit_is_unchanged() -> None:
    defects = validation_defects(_validation([{"detail": "x"}, {"detail": "y"}]), set())
    assert len(defects) == 1
    assert len(defects[0].record["failures"]) == 2


def test_the_scope_record_keeps_the_supersession_marker() -> None:
    from repo_presenter.readme.reconciliation.patch import _loss_units
    from repo_presenter.readme.repair.loop import scope_record
    from repo_presenter.readme.validation.supersession import LOSS_MARKER

    unit = "inherited_unit:004.paragraph"
    failures = [{"detail": f"{unit} {LOSS_MARKER} 1 piece(s) of it", "unit_id": unit}]
    (defect,) = validation_defects(_validation(failures), set())
    assert _loss_units(scope_record(defect, [unit])) == {unit}
