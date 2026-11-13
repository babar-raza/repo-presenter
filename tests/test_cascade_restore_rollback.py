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
    result = cascade_module._restore_lost_content(
        settled, entry=None, document=None, investigation={}, tree_paths=[], original="OLD\n",
        out_dir=tmp_path,
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
    assert result.unrestorable == frozenset({_BAD})
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
    assert result.unrestorable == frozenset({_BAD})
