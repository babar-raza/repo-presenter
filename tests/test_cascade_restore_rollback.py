"""One restored unit that adds a new defect is rolled back alone; the rest of the restore is kept.

Hosted Aspose.3D-FOSS-for-Python run 43411932927 and Aspose.Words-FOSS-for-.NET run 43411924300:
the zero-call restore (``cascade._restore_lost_content``) kept 5 / 9 units, one of which added a NEW
non-restorable failure (BC-02 on a registry install, BC-14 on a maintainers' table row, BC-06 / BC-07
on a kept paragraph), so the whole restore was discarded and every BC-05/BC-17 loss stayed -- and
``_without_restorable`` withheld those same losses from the model repair as "a restore's to answer",
so no stage could ever fix them and the run failed deterministically.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.readme.repair.targeted import Defect

_GOOD, _BAD = "inherited_unit:01.paragraph", "inherited_unit:02.table"
_REFUSED: set[str] = set()


@dataclasses.dataclass(frozen=True)
class _Composed:
    plan: Any
    coherent_units: Any
    dispositions: Any
    readme: str
    tasks: Any
    accounted: Any
    planned_dispositions: Any = None


def _placed(dispositions: dict[str, Any]) -> set[str]:
    return {
        row["unit_id"]
        for row in dispositions["dispositions"]
        if row["disposition"] == "VERIFIED_PRESERVE"
    }


def _restore(d, f, unit_ids, h, i=None, **k):  # noqa: ANN001, ANN202 - restore_lost_units' shape
    out = {"dispositions": [dict(row) for row in d["dispositions"]]}
    changes = []
    for row in out["dispositions"]:
        if row["unit_id"] in unit_ids and row["disposition"] != "VERIFIED_PRESERVE":
            row["disposition"] = "VERIFIED_PRESERVE"
            changes.append({"unit_id": row["unit_id"], "was": "S -> x", "now": "V -> x"})
    return out, changes


def _validate(candidate: Any, *a: Any, **k: Any) -> dict[str, Any]:
    units = _placed(candidate.dispositions)
    checks: list[dict[str, Any]] = []
    lost = [unit for unit in (_GOOD, _BAD) if unit not in units]
    if lost:
        details = [f"{unit} is SUPERSEDE_REDUNDANT, but the README does not state it" for unit in lost]
        checks.append(
            {
                "id": "BC-05",
                "details": details,
                "failures": [{"detail": d, "unit_id": u} for d, u in zip(details, lost)],
            }
        )
    if _BAD in units:
        detail = "the README describes `Stub` as working"
        checks.append(
            {"id": "BC-14", "details": [detail], "failures": [{"detail": detail, "unit_id": _BAD}]}
        )
    return {"checks": checks}


def _drive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, validate: Any = _validate) -> tuple[Any, Any]:
    monkeypatch.setattr(cascade_module, "blocking_failures", lambda validation: validation["checks"])
    monkeypatch.setattr(cascade_module, "holdable_sections", lambda document: {"key_capabilities"})
    monkeypatch.setattr(
        cascade_module,
        "choose_units",
        lambda details, doc, already, mandatory_checks=(), exclude=(): [
            unit for unit in (_GOOD, _BAD) if unit not in already and unit not in exclude
        ],
    )
    monkeypatch.setattr(cascade_module, "restore_lost_units", _restore)
    monkeypatch.setattr(cascade_module, "render_readme", lambda *a, **k: "RESTORED README\n")
    monkeypatch.setattr(cascade_module, "authoring_tasks", lambda *a, **k: [])
    monkeypatch.setattr(
        cascade_module,
        "_candidate",
        lambda entry, doc, plan, units, dispositions, *a, **k: SimpleNamespace(
            dispositions=dispositions
        ),
    )
    monkeypatch.setattr(cascade_module, "account_unprinted_units", lambda c: ({}, []))
    monkeypatch.setattr(cascade_module, "validate_candidate", validate)
    monkeypatch.setattr(
        cascade_module, "review_candidate", lambda **k: SimpleNamespace(blocking_findings=())
    )
    monkeypatch.setattr(
        cascade_module, "write_dispositions", lambda d, p: Path(p).write_text("{}", encoding="utf-8")
    )
    monkeypatch.setattr(cascade_module, "write_review_verdict", lambda v, p: None)
    original = {
        "dispositions": [
            {"unit_id": unit, "disposition": "SUPERSEDE_REDUNDANT"} for unit in (_GOOD, _BAD)
        ]
    }
    composed = _Composed(
        {"sections": [{"section_id": "key_capabilities", "include": True}]},
        {"units": []}, original, "OLD README\n", [], [],
    )
    before = validate(SimpleNamespace(dispositions=original))
    settled = cascade_module._Settled(composed, before, SimpleNamespace(blocking_findings=()), 1)
    _REFUSED.clear()
    result = cascade_module._restore_lost_content(
        settled, entry=None, document=None, investigation={}, tree_paths=[], original="OLD\n",
        out_dir=tmp_path, unrestorable=_REFUSED,
    )
    return settled, result


def test_a_unit_whose_restore_adds_a_new_check_is_rolled_back_and_the_rest_is_kept(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settled, result = _drive(monkeypatch, tmp_path)
    assert result.composed is not settled.composed
    rows = {row["unit_id"]: row["disposition"] for row in result.composed.dispositions["dispositions"]}
    assert rows == {_GOOD: "VERIFIED_PRESERVE", _BAD: "SUPERSEDE_REDUNDANT"}
    assert [c["id"] for c in result.validation["checks"]] == ["BC-05"]  # only _BAD's loss is left
    assert _REFUSED == {_BAD}
    record = json.loads((tmp_path / "restored_units.json").read_text(encoding="utf-8"))
    assert [change["unit_id"] for change in record["restored"]] == [_GOOD]


def _bc05_defect(unit: str) -> Defect:
    line = f"{unit} is SUPERSEDE_REDUNDANT, but the README does not state 1 piece(s) of it"
    return Defect(
        f"fp-{unit}", "validation", "BC-05", None, "S4",
        {"id": "BC-05", "details": [line], "failures": [{"detail": line, "unit_id": unit}]},
    )


def test_a_unit_the_restore_rolled_back_is_sent_to_the_model_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cascade_module,
        "restore_lost_units",
        lambda d, f, u, h, i=None, **k: (d, [{"unit_id": unit} for unit in u]),
    )
    monkeypatch.setattr(cascade_module, "holdable_sections", lambda document: {"key_capabilities"})
    composed = SimpleNamespace(
        plan={"sections": [{"section_id": "key_capabilities", "include": True}]},
        dispositions={"dispositions": []},
    )
    defect = _bc05_defect(_BAD)
    withheld = cascade_module._without_restorable([defect], composed=composed, document=None)
    sent = cascade_module._without_restorable(
        [defect], composed=composed, document=None, unrestorable=frozenset({_BAD})
    )
    assert withheld == [] and sent == [defect]


def _validate_unattributed(candidate: Any, *a: Any, **k: Any) -> dict[str, Any]:
    """The same, but the new failure names no unit (BC-07's badge-row count: PSD Python's kept
    one-per-line badges plus the rendered row read as "expected one badge row; found 5")."""
    checks = _validate(candidate)["checks"]
    for check in checks:
        if check["id"] == "BC-14":
            check.update(
                id="BC-07",
                details=["expected one badge row; found 5"],
                failures=[{"detail": "expected one badge row; found 5"}],
            )
    return {"checks": checks}


def test_a_unit_whose_restore_adds_an_unattributed_failure_is_found_and_rolled_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settled, result = _drive(monkeypatch, tmp_path, _validate_unattributed)
    rows = {row["unit_id"]: row["disposition"] for row in result.composed.dispositions["dispositions"]}
    assert rows == {_GOOD: "VERIFIED_PRESERVE", _BAD: "SUPERSEDE_REDUNDANT"}
    assert [c["id"] for c in result.validation["checks"]] == ["BC-05"]
    assert _REFUSED == {_BAD}


# --- BL-511: a restored unit that is itself a NEW loss is rolled back alone ----------------------
# Hosted PDF TypeScript Lane R (run 44717025933): three restored code blocks became BC-17 losses the
# candidate did not have (their restore took them out of the one place that printed them), and
# ``_strictly_fewer_failures`` refused the restore as a whole: 102 recoverable losses stayed.


def _validate_new_loss(candidate: Any, *a: Any, **k: Any) -> dict[str, Any]:
    """_BAD restored = _BAD is a BC-17 loss; _GOOD restored = clean."""
    checks = _validate(candidate)["checks"]
    checks = [c for c in checks if c["id"] != "BC-14"]
    if _BAD in _placed(candidate.dispositions):
        detail = (
            f"{_BAD} holds code_blocks 'x = 1', which the published README prints and this candidate "
            "loses (technical_content): keep it"
        )
        checks.append(
            {"id": "BC-17", "details": [detail], "failures": [{"detail": detail, "unit_id": _BAD}]}
        )
    return {"checks": checks}


def test_a_restored_unit_that_becomes_a_new_loss_is_rolled_back_and_the_rest_is_kept(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settled, result = _drive(monkeypatch, tmp_path, _validate_new_loss)
    assert result.composed is not settled.composed
    rows = {row["unit_id"]: row["disposition"] for row in result.composed.dispositions["dispositions"]}
    assert rows == {_GOOD: "VERIFIED_PRESERVE", _BAD: "SUPERSEDE_REDUNDANT"}
    assert _REFUSED == {_BAD}  # its loss goes on to the model repair, never withheld
    record = json.loads((tmp_path / "restored_units.json").read_text(encoding="utf-8"))
    assert [change["unit_id"] for change in record["restored"]] == [_GOOD]
    assert {s["unit_id"]: s["reason"] for s in record["skipped_for_pointer"]} == {_BAD: "new_failure:BC-17"}


def test_negative_control_without_the_attribution_the_whole_restore_is_discarded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cascade_module, "_new_loss_units", lambda *a, **k: {})
    settled, result = _drive(monkeypatch, tmp_path, _validate_new_loss)
    assert result.composed is settled.composed  # the guard discarded _GOOD's clean restore too
    assert not (tmp_path / "restored_units.json").exists()


# --- BL-640: a restored unit whose only new failure is BC-07's reference sentence is trimmed, not rolled back ---

_POINTING = "The examples above pass `load_format=False` to run a document from primitives alone."


def _pointing_validate(candidate: Any, *a: Any, **k: Any) -> dict[str, Any]:
    checks = _validate(candidate)["checks"]
    row = next(r for r in candidate.dispositions["dispositions"] if r["unit_id"] == _BAD)
    if row["disposition"] == "VERIFIED_PRESERVE" and "degrade_withheld" not in row:
        detail = f"{_BAD} is kept as written but says 'examples above' but no code precedes it in this section: {_POINTING!r}"
        checks = [c for c in checks if c["id"] != "BC-14"]
        checks.append({"id": "BC-07", "details": [detail], "failures": [{"detail": detail, "unit_id": _BAD}]})
    else:
        checks = [c for c in checks if c["id"] != "BC-14"]
    return {"checks": checks}


def test_a_restored_unit_whose_only_new_failure_is_a_reference_sentence_is_trimmed_not_rolled_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def withhold(dispositions: dict[str, Any], document: Any, wanted: dict[str, list[str]]) -> dict[str, list[str]]:
        done = {}
        for row in dispositions["dispositions"]:
            # the real function records a sentence once (an already-recorded one returns nothing: BL-892 relies on it)
            if row["unit_id"] in wanted and row["unit_id"] == _BAD and "degrade_withheld" not in row:
                row["degrade_withheld"] = list(wanted[row["unit_id"]])
                done[row["unit_id"]] = list(wanted[row["unit_id"]])
        return done

    monkeypatch.setattr(cascade_module, "withhold_reference_sentences", withhold)
    monkeypatch.setattr(cascade_module, "reference_sentences", lambda failing, restored: {_BAD: [_POINTING]})  # parsing: test_reference_sentence_trim_bl640
    settled, result = _drive(monkeypatch, tmp_path, _pointing_validate)
    rows = {row["unit_id"]: row for row in result.composed.dispositions["dispositions"]}
    assert rows[_BAD]["disposition"] == "VERIFIED_PRESERVE" and rows[_BAD]["degrade_withheld"] == [_POINTING]
    assert result.validation["checks"] == []  # nothing left failing: the unit stayed restored, minus the sentence
    assert _REFUSED == set()
    record = json.loads((tmp_path / "restored_units.json").read_text(encoding="utf-8"))
    assert {c["unit_id"] for c in record["restored"]} == {_GOOD, _BAD}
    assert next(c for c in record["restored"] if c["unit_id"] == _BAD)["withheld"] == _POINTING


def test_negative_control_a_reference_sentence_that_cannot_be_withheld_still_rolls_the_unit_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cascade_module, "withhold_reference_sentences", lambda d, doc, wanted: {})
    monkeypatch.setattr(cascade_module, "reference_sentences", lambda failing, restored: {_BAD: [_POINTING]})
    _, result = _drive(monkeypatch, tmp_path, _pointing_validate)
    rows = {row["unit_id"]: row["disposition"] for row in result.composed.dispositions["dispositions"]}
    assert rows[_BAD] == "SUPERSEDE_REDUNDANT" and _REFUSED == {_BAD}
