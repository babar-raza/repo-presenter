"""TC-019c: the cascade applies the zero-call restore (``readme.repair.restore_units``) when the
settled candidate's only blocking failures are BC-05/BC-17, instead of dying at the seal gate with
~80 paid calls spent and no candidate (Email-FOSS-for-Python, first batch run, 2026-11-09).

Real cascade over the fixture ``tests/test_cascade.py`` defines, through a fake client with scripted
replies; the model review is replaced by a recorder, so these tests make no provider call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import repo_presenter.cascade as cascade_module
from repo_presenter.readme.review.independent_reviewer import ReviewVerdict
from repo_presenter.readme.validation.blocking import blocking_failures
from tests.test_cascade import README
from tests.test_cascade_s9 import _first_replies, _Run, _fixed_git_revision  # noqa: F401

GUIDE = "https://widget.example.org/guide"
README_WITH_LINK = README + f"\nRead the [full guide]({GUIDE}) for everything else.\n"
LINK_UNIT = "inherited_unit:007.paragraph"


class _ReachedReview(Exception):
    pass


#: The shared fixture (a synthetic widget with no LICENSE file, an unexecuted example and an
#: unevidenced pip install) fails BC-02/BC-03/BC-06 on its own, which has nothing to do with this
#: card; ``tests/test_cascade_s10.py`` replaces the same gate for the same reason. Every other
#: check, BC-17 included, is the real one.
_FIXTURE_ONLY = frozenset({"BC-02", "BC-03", "BC-06"})
_real_blocking_failures = blocking_failures


def _blocking_without_fixture_noise(validation: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in _real_blocking_failures(validation) if c["id"] not in _FIXTURE_ONLY]


def _reconciliation(link_disposition: str, destination: str | None) -> dict[str, Any]:
    reply = _first_replies()[1]
    reply = json.loads(json.dumps(reply))
    reply["dispositions"].append(
        {
            "unit_id": LINK_UNIT, "disposition": link_disposition,
            "destination_section": destination, "fact_ids": ["package:name"],
            "rationale": "the paragraph points at a guide",
        }
    )
    return reply


def _run_to_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_disposition: str, destination: str | None
) -> tuple[_Run, dict[str, Any]]:
    seen: dict[str, Any] = {}

    def record_review(**kwargs: Any) -> Any:
        seen["blocking"] = [
            check["id"] for check in _blocking_without_fixture_noise(kwargs["validation"])
        ]
        seen["readme"] = kwargs["candidate_readme"]
        raise _ReachedReview

    monkeypatch.setattr(cascade_module, "review_with_model", record_review)
    monkeypatch.setattr(cascade_module, "blocking_failures", _blocking_without_fixture_noise)
    # The fixture's own deterministic verdict is REJECT (heading losses in deterministic sections),
    # as tests/test_cascade_s10.py notes; BC-17, the check under test, is not part of that verdict.
    monkeypatch.setattr(cascade_module, "review_candidate", lambda **kw: ReviewVerdict.folded(()))
    run = _Run(tmp_path, monkeypatch, README_WITH_LINK)
    run.script(_first_replies(reconciliation=_reconciliation(link_disposition, destination)))
    try:
        run.cascade(max_rounds=1)
    except _ReachedReview:
        seen["reached"] = True
    return run, seen


def test_a_candidate_that_loses_only_a_link_the_published_readme_prints_reaches_review_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run, seen = _run_to_review(tmp_path, monkeypatch, "DEFER_UNRESOLVED", None)
    assert seen.get("reached") is True, "the cascade stopped before the model review"
    assert seen["blocking"] == []
    assert GUIDE in seen["readme"]
    restored = run.json("restored_units.json")["restored"]
    assert [change["unit_id"] for change in restored] == [LINK_UNIT]
    assert restored[0]["was"].startswith("DEFER_UNRESOLVED") and "VERIFIED_PRESERVE" in restored[0]["now"]
    assert next(e for e in run.json("dispositions.json")["dispositions"] if e["unit_id"] == LINK_UNIT)[
        "disposition"
    ] == "VERIFIED_PRESERVE"
    assert GUIDE in (run.out / "README.coherent.md").read_text(encoding="utf-8")


def test_negative_control_without_the_restore_the_same_run_is_stopped_at_the_blocking_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cascade_module, "restore_lost_units", lambda d, f, u, h, i=None, **k: (d, []))
    run, seen = _run_to_review(tmp_path, monkeypatch, "DEFER_UNRESOLVED", None)
    assert seen.get("reached") is None  # blocking checks still failed, so no model review was made
    assert "BC-17" in {c["id"] for c in _blocking_without_fixture_noise(run.json("validation.json"))}
    assert not (run.out / "restored_units.json").exists()


# --- which failing sets a restore is attempted for ---------------------------------------------
# Slides Java failed BC-05 AND BC-07 (the line budget); the restore was skipped because BC-07 is
# not a restorable check, although re-rendering with the unit kept is what the pair needs. BC-07 may
# accompany BC-05/BC-17; any other failing check, or BC-07 alone, still leaves the candidate as is.


def _attempted(monkeypatch: pytest.MonkeyPatch, failing_ids: list[str]) -> bool:
    from types import SimpleNamespace

    calls: list[bool] = []
    checks = [{"id": check_id, "details": []} for check_id in failing_ids]
    monkeypatch.setattr(cascade_module, "blocking_failures", lambda validation: checks)
    monkeypatch.setattr(cascade_module, "holdable_sections", lambda document: calls.append(True) or {})
    settled = SimpleNamespace(
        composed=SimpleNamespace(plan={"sections": []}, dispositions={}), validation={}, verdict=None
    )
    try:
        result = cascade_module._restore_lost_content(
            settled, entry=None, document=None, investigation={}, tree_paths=[], original="",
            out_dir=Path("."),
        )
    except Exception:  # noqa: BLE001 - past the gate the fake settled cannot be rendered
        return True
    assert result is settled
    return bool(calls)


def test_a_restore_is_attempted_for_bc05_and_bc17_with_bc07(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _attempted(monkeypatch, ["BC-05", "BC-07"])
    assert _attempted(monkeypatch, ["BC-17", "BC-07"])
    assert _attempted(monkeypatch, ["BC-05", "BC-17"])


def test_a_restore_is_not_attempted_for_bc07_alone_or_with_another_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert not _attempted(monkeypatch, ["BC-07"])
    assert not _attempted(monkeypatch, ["BC-05", "BC-07", "BC-04"])
    assert not _attempted(monkeypatch, ["BC-02", "BC-17"])
    assert not _attempted(monkeypatch, [])


# --- the restore runs inside the S9 settle loop, before any model repair --------------------------
# Hosted Aspose.3D-FOSS-for-TypeScript (head 98a10a9) spent the whole 100-call invocation budget
# sending ~45 restorable BC-17/BC-05 defects to the targeted repair (all rejected) and died before
# the zero-call restore, which ran only after the settle loop, could act.


def _settle_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, restore_in_settle: bool
) -> tuple[_Run, Any, list[list[Any]]]:
    repaired: list[list[Any]] = []

    def record_repair(**kwargs: Any) -> bool:
        repaired.append(list(kwargs["defects"]))
        return False  # nothing changed, so the settle loop ends

    def record_review(**kwargs: Any) -> Any:
        raise _ReachedReview

    monkeypatch.setattr(cascade_module, "_repair_defects", record_repair)
    monkeypatch.setattr(cascade_module, "review_with_model", record_review)
    monkeypatch.setattr(cascade_module, "blocking_failures", _blocking_without_fixture_noise)
    monkeypatch.setattr(cascade_module, "review_candidate", lambda **kw: ReviewVerdict.folded(()))
    if not restore_in_settle:
        real = cascade_module._restore_lost_content
        monkeypatch.setattr(
            cascade_module,
            "_restore_lost_content",
            lambda settled, **kw: settled if kw.get("require_clean_review") else real(settled, **kw),
        )
    run = _Run(tmp_path, monkeypatch, README_WITH_LINK)
    client = run.script(
        _first_replies(reconciliation=_reconciliation("DEFER_UNRESOLVED", None))
    )
    try:
        run.cascade(max_rounds=3)
    except _ReachedReview:
        pass
    return run, client, repaired


def test_restorable_defects_make_zero_model_repair_calls_and_the_candidate_reaches_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run, client, repaired = _settle_run(tmp_path, monkeypatch, restore_in_settle=True)
    assert repaired == []  # the settle loop never reached the model repair
    assert client.chat.completions.replies == []  # only the nine first-pass calls were made
    assert GUIDE in (run.out / "README.coherent.md").read_text(encoding="utf-8")
    assert [c["unit_id"] for c in run.json("restored_units.json")["restored"]] == [LINK_UNIT]


def test_a_restorable_bc17_defect_is_never_sent_to_the_model_but_other_defects_still_are(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the early restore, the settle loop reaches the repair: the restorable BC-17 defect is
    filtered out of it (the next test is the negative control; the one after proves a defect the
    restore cannot answer is still sent)."""
    _run, _client, repaired = _settle_run(tmp_path, monkeypatch, restore_in_settle=False)
    sent = [defect for batch in repaired for defect in batch]
    assert not any(
        defect.label == "BC-17" and LINK_UNIT in json.dumps(defect.record) for defect in sent
    )


def test_without_the_filter_the_same_bc17_defect_is_sent_to_the_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cascade_module, "_without_restorable", lambda defects, **kw: defects)
    _run, _client, repaired = _settle_run(tmp_path, monkeypatch, restore_in_settle=False)
    sent = [defect for batch in repaired for defect in batch]
    assert any(defect.label == "BC-17" and LINK_UNIT in json.dumps(defect.record) for defect in sent)


def test_a_defect_naming_a_unit_the_restore_cannot_keep_is_still_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from repo_presenter.readme.repair.targeted import Defect

    def defect(unit: str) -> Defect:
        line = f"{unit} holds links 'x', which the published README prints and this candidate loses"
        return Defect(
            f"fp-{unit}", "validation", "BC-17", None, "S4",
            {"id": "BC-17", "details": [line], "failures": [{"detail": line, "unit_id": unit}]},
        )

    kept_unit, other = "inherited_unit:001.paragraph", "inherited_unit:002.paragraph"
    # a restore that can keep only the first of the two units
    monkeypatch.setattr(
        cascade_module, "restore_lost_units",
        lambda d, f, ids, h, i=None, **k: (d, [{"unit_id": kept_unit}]),
    )
    monkeypatch.setattr(cascade_module, "holdable_sections", lambda document: set())
    composed = SimpleNamespace(dispositions={}, plan={"sections": []})
    left = cascade_module._without_restorable(
        [defect(kept_unit), defect(other)], composed=composed, document=SimpleNamespace()
    )
    assert [d.fingerprint for d in left] == [f"fp-{other}"]


def test_a_restore_is_attempted_for_bc08_and_not_beside_a_non_restorable_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _attempted(monkeypatch, ["BC-08"])
    assert _attempted(monkeypatch, ["BC-08", "BC-17", "BC-07"])
    assert not _attempted(monkeypatch, ["BC-08", "BC-02"])
