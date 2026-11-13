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


def test_a_restore_is_not_attempted_without_a_restorable_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Nothing restore answers is failing: BC-07 alone (it only moves with printed content), or a
    # non-restorable check alone, or nothing at all.
    assert not _attempted(monkeypatch, ["BC-07"])
    assert not _attempted(monkeypatch, ["BC-02"])
    assert not _attempted(monkeypatch, ["BC-04", "BC-07"])
    assert not _attempted(monkeypatch, [])


def test_a_restore_is_attempted_beside_a_non_restorable_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owner directive 2026-11-11 (AGENTS.md rule 9): a restorable loss must not be stranded because
    another, unrelated check also fails. Measured on a fresh Cells Cpp run: BC-02 (unproven
    'cmake --build') + BC-05 + BC-17 -- no restore ran, and the model is never asked about restorable
    defects, so the lost API list was never recovered."""
    assert _attempted(monkeypatch, ["BC-02", "BC-17"])
    assert _attempted(monkeypatch, ["BC-05", "BC-07", "BC-04"])
    assert _attempted(monkeypatch, ["BC-02", "BC-05", "BC-17"])


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


def test_a_restore_is_attempted_for_bc08_alone_and_beside_other_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _attempted(monkeypatch, ["BC-08"])
    assert _attempted(monkeypatch, ["BC-08", "BC-17", "BC-07"])
    assert _attempted(monkeypatch, ["BC-08", "BC-02"])


# --- a unit with a dangling pointer is not restorable, so its defect still goes to the repair --------
# Hosted PDF Go: 025.paragraph's text points at "[Encryption and Signing](#encryption-and-signing)
# below"; restoring it re-triggers BC-07's dangling pointer, so the restore does not keep it and the
# model repair must still be asked about its BC-08/BC-17 lines.

_POINTER = "inherited_unit:025.paragraph"
_PLAIN = "inherited_unit:026.paragraph"


def _pointer_document() -> Any:
    from repo_presenter.core.facts import Evidence, Fact, FactsDocument

    def unit(unit_id: str, text: str) -> Fact:
        return Fact(
            id=unit_id, kind="inherited_unit", value=text,  # type: ignore[arg-type]
            evidence=(Evidence("README.md", None),), polarity="SUPPORTED",  # type: ignore[arg-type]
            attributes={"section": "X > Features"},
        )

    return FactsDocument(
        "r", "0" * 40,
        (
            unit(_POINTER, "Options are covered in [Encryption and Signing](#encryption-and-signing) below."),
            unit(_PLAIN, "Run `go run ./_examples/feature_showcase` to see them."),
            *(unit(f"inherited_unit:09{i}.paragraph", f"Filler {i}.") for i in range(3)),
        ),
    )


def _bc17_defect(unit: str) -> Any:
    from repo_presenter.readme.repair.targeted import Defect

    line = f"{unit} holds commands 'x', which the published README prints and this candidate loses"
    return Defect(
        f"fp-{unit}", "validation", "BC-17", None, "S4",
        {"id": "BC-17", "details": [line], "failures": [{"detail": line, "unit_id": unit}]},
    )


def _without_restorable_left(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from types import SimpleNamespace

    monkeypatch.setattr(cascade_module, "holdable_sections", lambda document: {"key_capabilities"})
    dispositions = {
        "dispositions": [
            {
                "unit_id": unit, "disposition": "VERIFIED_REWRITE",
                "destination_section": "key_capabilities", "fact_ids": [], "rationale": "r",
            }
            for unit in (_POINTER, _PLAIN)
        ]
    }
    composed = SimpleNamespace(
        dispositions=dispositions, plan={"sections": [{"section_id": "key_capabilities", "include": True}]}
    )
    left = cascade_module._without_restorable(
        [_bc17_defect(_POINTER), _bc17_defect(_PLAIN)], composed=composed, document=_pointer_document()
    )
    return [d.fingerprint for d in left]


def test_a_defect_naming_a_unit_with_a_dangling_pointer_is_still_sent_to_the_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 026 (no pointer) is restorable and dropped; 025 (pointer) is not restorable, so it stays
    assert _without_restorable_left(monkeypatch) == [f"fp-{_POINTER}"]


def test_negative_control_without_the_pointer_guard_both_defects_are_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import repo_presenter.readme.reconciliation.dispositions as dispositions_module

    monkeypatch.setattr(dispositions_module, "dangling_pointers", lambda output, facts: [])
    assert _without_restorable_left(monkeypatch) == []


# --- a partial restore is kept when the blocking failures strictly shrink and none is new ---------------


def _check(check_id: str, *details: str) -> dict[str, Any]:
    return {"id": check_id, "details": list(details)}


def _bc17(*items: str) -> dict[str, Any]:
    return _check("BC-17", *(f"inherited_unit:0{i}.paragraph holds links '{i}'" for i in items))


def _drive_restore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, before: list[dict[str, Any]],
    after: list[dict[str, Any]], *, review_blocking: int = 0,
) -> tuple[Any, Any]:
    import dataclasses
    from types import SimpleNamespace

    @dataclasses.dataclass(frozen=True)
    class FakeComposed:
        plan: Any
        coherent_units: Any
        dispositions: Any
        readme: str
        tasks: Any
        accounted: Any
        planned_dispositions: Any = None

    verdict_after = SimpleNamespace(blocking_findings=("f",) * review_blocking)
    verdict_before = SimpleNamespace(blocking_findings=())
    monkeypatch.setattr(cascade_module, "blocking_failures", lambda validation: validation["checks"])
    monkeypatch.setattr(cascade_module, "holdable_sections", lambda document: {"key_capabilities"})
    monkeypatch.setattr(cascade_module, "choose_units", lambda *a, **k: ["inherited_unit:01.paragraph"])
    monkeypatch.setattr(
        cascade_module, "restore_lost_units",
        lambda d, f, u, h, i=None, **k: (d, [{"unit_id": "inherited_unit:01.paragraph", "was": "a", "now": "b"}]),
    )
    monkeypatch.setattr(cascade_module, "render_readme", lambda *a, **k: "RESTORED README\n")
    monkeypatch.setattr(cascade_module, "authoring_tasks", lambda *a, **k: [])
    monkeypatch.setattr(cascade_module, "_candidate", lambda *a, **k: SimpleNamespace())
    monkeypatch.setattr(cascade_module, "account_unprinted_units", lambda c: ({}, []))
    monkeypatch.setattr(cascade_module, "validate_candidate", lambda *a, **k: {"checks": after})
    monkeypatch.setattr(cascade_module, "review_candidate", lambda **k: verdict_after)
    monkeypatch.setattr(
        cascade_module, "write_dispositions", lambda d, p: Path(p).write_text("{}", encoding="utf-8")
    )
    monkeypatch.setattr(cascade_module, "write_review_verdict", lambda v, p: None)
    composed = FakeComposed(
        {"sections": [{"section_id": "key_capabilities", "include": True}]},
        {"units": []}, {"dispositions": []}, "OLD README\n", [], [],
    )
    settled = cascade_module._Settled(composed, {"checks": before}, verdict_before, 1)
    result = cascade_module._restore_lost_content(
        settled, entry=None, document=None, investigation={}, tree_paths=[], original="OLD\n",
        out_dir=tmp_path,
    )
    return settled, result


def test_a_partial_restore_that_clears_two_of_three_items_and_adds_none_is_kept(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pointer = _check("BC-07", "refers to a 'X below' section this README does not have")
    settled, result = _drive_restore(
        monkeypatch, tmp_path, [_bc17("1", "2", "3"), pointer], [_bc17("3"), pointer]
    )
    assert result is not settled and result.composed.readme == "RESTORED README\n"
    assert [c["id"] for c in result.validation["checks"]] == ["BC-17", "BC-07"]
    assert (tmp_path / "restored_units.json").exists()


def test_a_restore_that_introduces_a_new_failing_check_is_discarded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    after = [_bc17("3"), _check("BC-07", "refers to a 'X below' section this README does not have")]
    settled, result = _drive_restore(monkeypatch, tmp_path, [_bc17("1", "2", "3")], after)
    assert result is settled
    assert not (tmp_path / "restored_units.json").exists()


def test_a_restore_that_changes_an_item_without_clearing_any_is_discarded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settled, result = _drive_restore(monkeypatch, tmp_path, [_bc17("1", "2")], [_bc17("1", "9")])
    assert result is settled


def test_a_partial_restore_with_a_new_blocking_review_finding_is_discarded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settled, result = _drive_restore(
        monkeypatch, tmp_path, [_bc17("1", "2")], [_bc17("2")], review_blocking=1
    )
    assert result is settled


def test_a_restore_that_does_not_shrink_the_failures_is_discarded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    same = [_bc17("1", "2")]
    settled, result = _drive_restore(monkeypatch, tmp_path, same, same)
    assert result is settled


# --- a restorable loss is recovered even while a non-restorable check keeps failing ------------------
# Fresh Cells Cpp (2026-11-11): BC-02 'cmake --build build' (a build no run proved) fails beside the
# BC-05/BC-17 losses of inherited_unit:010.list. Restore clears the losses; BC-02 is not restore's to
# answer and goes on to the repair loop. The result is kept because the failures strictly shrink.

_BC02 = ("BC-02", "install_command:cmake: the README prints 'cmake --build build', the source build "
         "of a project whose build no run proved")


def test_a_restore_clears_the_restorable_loss_and_is_kept_while_bc02_survives(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settled, result = _drive_restore(
        monkeypatch, tmp_path, [_check(*_BC02), _bc17("1", "2")], [_check(*_BC02)]
    )
    assert result is not settled and result.composed.readme == "RESTORED README\n"
    assert [c["id"] for c in result.validation["checks"]] == ["BC-02"]  # still the repair loop's
    assert (tmp_path / "restored_units.json").exists()


def test_a_restore_beside_bc02_is_discarded_when_it_adds_a_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    after = [_check(*_BC02), _check("BC-04", "api_reference: unit intro: cites facts outside the set")]
    settled, result = _drive_restore(
        monkeypatch, tmp_path, [_check(*_BC02), _bc17("1", "2")], after
    )
    assert result is settled
    assert not (tmp_path / "restored_units.json").exists()


def test_a_restore_beside_bc02_is_discarded_when_bc02_itself_grows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    grown = _check(*_BC02, "install_command:cmake: a second unproven command")
    settled, result = _drive_restore(monkeypatch, tmp_path, [_check(*_BC02), _bc17("1")], [grown])
    assert result is settled


def test_a_restore_beside_bc02_that_clears_nothing_is_discarded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    same = [_check(*_BC02), _bc17("1", "2")]
    settled, result = _drive_restore(monkeypatch, tmp_path, same, same)
    assert result is settled
